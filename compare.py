"""Comparador por consola: corre TODOS los modelos sobre un video y reporta,
por modelo, con qué frecuencia y confianza detecta cada EPP puesto.

Sirve para 'ver cuál detecta mejor' de forma numérica y descartar los malos.

Uso:
    python compare.py videos/video_2.mp4
    python compare.py videos/video_2.mp4 --sample 40 --conf 0.25
"""
import argparse
from collections import defaultdict

import cv2

from backend.config import config
from backend.detector import get_detector
from backend.registry import MODELS, ITEM_LABELS


def run(video, sample, conf):
    cap = cv2.VideoCapture(video)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, total // sample)
    idxs = list(range(0, total, step))

    frames = []
    for i in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ok, f = cap.read()
        if ok:
            if config.max_width and f.shape[1] > config.max_width:
                h, w = f.shape[:2]
                f = cv2.resize(f, (config.max_width, int(h * config.max_width / w)))
            frames.append(f)
    cap.release()
    print(f"\nVideo: {video}  |  {len(frames)} frames muestreados  |  conf={conf}\n")

    header = f"{'modelo':<20} {'persons':>7} " + " ".join(
        f"{ITEM_LABELS[i][:6]:>7}" for i in ("helmet", "vest", "gloves", "glasses"))
    print(header)
    print("-" * len(header))

    for m in MODELS:
        try:
            det = get_detector(m["key"])
        except Exception as e:
            print(f"{m['key']:<20} ERROR {e}")
            continue
        cnt = defaultdict(int)
        confsum = defaultdict(float)
        pers = 0
        for f in frames:
            persons, heads, dets = det.infer(f, conf)
            pers += len(persons)
            for d in dets:
                if d["state"] == "worn":
                    cnt[d["item"]] += 1
                    confsum[d["item"]] += d["conf"]
        def cell(it):
            n = cnt[it]
            if n == 0:
                return f"{'·':>7}"
            return f"{n}/{confsum[it]/n:.2f}"[:7].rjust(7)
        row = f"{m['key']:<20} {pers/len(frames):>7.1f} " + " ".join(
            cell(i) for i in ("helmet", "vest", "gloves", "glasses"))
        print(row)
    print("\nLeyenda: 'nDet/confProm' de EPP PUESTO por muestra. '·' = no detecta.")
    print("Elige el que mejor marque casco y chaleco con buena confianza.\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--sample", type=int, default=30)
    ap.add_argument("--conf", type=float, default=0.25)
    a = ap.parse_args()
    run(a.video, a.sample, a.conf)
