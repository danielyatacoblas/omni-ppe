"""Servidor FastAPI — Comparador de modelos PPE.

Rutas:
  GET  /               -> UI
  GET  /api/videos     -> lista de videos
  GET  /api/models     -> lista de modelos + ítems disponibles por modelo
  POST /api/start      -> inicia procesamiento {video, model}
  POST /api/stop       -> detiene
  POST /api/params     -> conf / required / strict en vivo
  GET  /stream         -> MJPEG anotado
  GET  /api/status     -> estado por persona + fps + modelo
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import config
from .detector import get_detector
from .registry import MODELS, ITEM_LABELS
from .streamer import VideoStreamer

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
VIDEO_EXT = (".mp4", ".avi", ".mov", ".mkv", ".webm")

app = FastAPI(title="PPE Model Comparator")
streamer = VideoStreamer()


class StartReq(BaseModel):
    video: str
    model: str


class ParamsReq(BaseModel):
    conf: float | None = None
    required: list[str] | None = None
    strict: bool | None = None


@app.get("/api/videos")
def list_videos():
    vids = []
    if config.videos_abs.exists():
        vids = sorted(f.name for f in config.videos_abs.iterdir()
                      if f.suffix.lower() in VIDEO_EXT)
    return {"videos": vids, "default_conf": config.default_conf,
            "device": config.device, "item_labels": ITEM_LABELS,
            "default_model": config.default_model}


@app.get("/api/models")
def list_models():
    """Lista modelos; para cada uno intenta reportar sus ítems detectables.

    Los ítems se leen del modelo (lazy): si aún no está cargado se marca
    'items': null y se resuelven al seleccionarlo.
    """
    from .detector import _cache
    out = []
    for m in MODELS:
        weights = ROOT / "weights" / m["file"]
        entry = {"key": m["key"], "label": m["label"],
                 "available": weights.exists(), "items": None,
                 "trainable": m.get("trainable", False),
                 "helmet_presence_only": None}
        if m["key"] in _cache:
            d = _cache[m["key"]]
            entry["items"] = d.available_items
            entry["helmet_presence_only"] = d.helmet_presence_only
        out.append(entry)
    return {"models": out}


@app.get("/api/models/{key}")
def model_info(key: str):
    """Carga el modelo (si hace falta) y devuelve sus ítems detectables."""
    try:
        d = get_detector(key)
    except (KeyError, FileNotFoundError) as e:
        return JSONResponse({"error": str(e)}, status_code=404)
    return {"key": key, "items": d.available_items,
            "item_labels": {i: ITEM_LABELS[i] for i in d.available_items},
            "helmet_presence_only": d.helmet_presence_only,
            "classes": list(d.names.values())}


@app.post("/api/start")
def start(req: StartReq):
    path = config.videos_abs / req.video
    if not path.exists():
        return JSONResponse({"error": "video no encontrado"}, status_code=404)
    try:
        streamer.start(str(path), req.model)
    except (KeyError, FileNotFoundError, RuntimeError) as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    return {"ok": True, "video": req.video, "model": req.model,
            "items": streamer.detector.available_items,
            "required": sorted(streamer.required)}


@app.post("/api/stop")
def stop():
    streamer.stop()
    return {"ok": True}


@app.post("/api/params")
def params(req: ParamsReq):
    streamer.update_params(conf=req.conf, required=req.required, strict=req.strict)
    return {"ok": True}


@app.get("/stream")
def stream():
    return StreamingResponse(
        streamer.mjpeg_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame")


@app.get("/api/status")
def status():
    return streamer.status()


@app.get("/")
def index():
    return FileResponse(FRONTEND / "index.html")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")
