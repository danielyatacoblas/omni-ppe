"""Procesamiento de video en hilo con modelo intercambiable (comparador).

Lee frames, corre el modelo activo a TARGET_FPS, dibuja cajas por estado
(worn=verde / absent=rojo) + barra de % por persona, y publica el JPEG anotado.
"""
import threading
import time

import cv2

from .config import config
from .detector import get_detector
from .registry import ITEM_LABELS
from .scoring import score_people

GREEN = (60, 200, 60)
RED = (40, 40, 220)
YELLOW = (40, 210, 235)
GRAY = (140, 140, 140)


class VideoStreamer:
    def __init__(self):
        self.detector = None
        self.model_key = None
        self.cap = None
        self.thread = None
        self.running = False
        self.lock = threading.Lock()
        self.latest_jpeg = None
        self.latest_status = {"people": [], "fps": 0.0, "source": None, "model": None}

        self.conf = config.default_conf
        self.required = {"helmet", "vest"}
        self.strict = config.strict_mode
        self.source = None

    def set_model(self, model_key: str):
        """Carga (cachea) el modelo indicado."""
        self.detector = get_detector(model_key)
        self.model_key = model_key
        # limita 'required' a lo que el modelo puede detectar
        self.required = {i for i in self.required if i in self.detector.available_items} \
            or set(self.detector.available_items[:2])

    def start(self, source: str, model_key: str):
        self.stop()
        if model_key != self.model_key or self.detector is None:
            self.set_model(model_key)
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise RuntimeError(f"No se pudo abrir: {source}")
        self.source = source
        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.cap:
            self.cap.release()
        self.cap = None

    def update_params(self, conf=None, required=None, strict=None):
        if conf is not None:
            self.conf = float(conf)
        if required is not None:
            self.required = set(required)
        if strict is not None:
            self.strict = bool(strict)

    def _loop(self):
        interval = 1.0 / max(1, config.target_fps)
        last_t = time.time()
        fps_ema = 0.0
        while self.running and self.cap:
            ok, frame = self.cap.read()
            if not ok:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

            frame = self._resize(frame)
            persons, heads, dets = self.detector.infer(frame, self.conf)
            people = score_people(persons, heads, dets, self.required, self.strict,
                                  self.detector.helmet_presence_only)
            self._draw(frame, dets, people)

            now = time.time()
            dt = now - last_t
            last_t = now
            if dt > 0:
                fps_ema = 0.9 * fps_ema + 0.1 * (1.0 / dt) if fps_ema else 1.0 / dt

            ok, buf = cv2.imencode(
                ".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, config.jpeg_quality])
            if ok:
                with self.lock:
                    self.latest_jpeg = buf.tobytes()
                    self.latest_status = {
                        "people": [{k: v for k, v in p.items() if k != "box"}
                                   for p in people],
                        "fps": round(fps_ema, 1),
                        "source": self.source,
                        "model": self.model_key,
                    }

            sleep = interval - (time.time() - now)
            if sleep > 0:
                time.sleep(sleep)

    def _resize(self, frame):
        if config.max_width and frame.shape[1] > config.max_width:
            h, w = frame.shape[:2]
            frame = cv2.resize(frame, (config.max_width, int(h * config.max_width / w)))
        return frame

    def _draw(self, frame, dets, people):
        for d in dets:
            x1, y1, x2, y2 = map(int, d["box"])
            worn = d["state"] == "worn"
            color = GREEN if worn else RED
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 1)
            tag = ITEM_LABELS.get(d["item"], d["item"])
            pre = "" if worn else "NO-"
            cv2.putText(frame, f"{pre}{tag} {d['conf']:.2f}", (x1, y1 - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

        for p in people:
            x1, y1, x2, y2 = map(int, p["box"])
            cv2.rectangle(frame, (x1, y1), (x2, y2),
                          GREEN if p["ready"] else RED, 2)
            self._draw_bar(frame, p, x1, y1, x2)

    def _draw_bar(self, frame, p, x1, y1, x2):
        pct, ready = p["pct"], p["ready"]
        color = GREEN if ready else (YELLOW if pct >= 50 else RED)
        bw = max(70, x2 - x1)
        by = y1 - 26 if y1 - 26 > 2 else y1 + 4
        cv2.rectangle(frame, (x1, by), (x1 + bw, by + 12), GRAY, -1)
        cv2.rectangle(frame, (x1, by), (x1 + int(bw * pct / 100), by + 12), color, -1)
        cv2.rectangle(frame, (x1, by), (x1 + bw, by + 12), (30, 30, 30), 1)
        state = "LISTO" if ready else "NO LISTO"
        cv2.putText(frame, f"{pct}%  {state}", (x1, by - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
        if p["missing"]:
            miss = ",".join(ITEM_LABELS[m] for m in p["missing"])
            cv2.putText(frame, f"falta: {miss}", (x1, by + 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, RED, 1, cv2.LINE_AA)

    def mjpeg_frames(self):
        while True:
            with self.lock:
                data = self.latest_jpeg
            if data is None:
                time.sleep(0.03)
                continue
            yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + data + b"\r\n")
            time.sleep(1.0 / max(1, config.target_fps))

    def status(self):
        with self.lock:
            return dict(self.latest_status)
