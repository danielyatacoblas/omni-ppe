"""Carga de configuración desde .env"""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _f(key, default):
    return float(os.getenv(key, default))


def _i(key, default):
    return int(os.getenv(key, default))


def _b(key, default):
    return os.getenv(key, str(default)).strip().lower() in ("1", "true", "yes", "on")


def _fopt(key):
    """Float opcional: devuelve None si la variable está vacía/ausente."""
    v = os.getenv(key, "").strip()
    return float(v) if v else None


@dataclass
class Config:
    default_model: str = os.getenv("DEFAULT_MODEL", "css_ftnabil")
    device: str = os.getenv("DEVICE", "cuda:0")
    img_size: int = _i("IMG_SIZE", 640)
    default_conf: float = _f("DEFAULT_CONF", 0.35)

    target_fps: int = _i("TARGET_FPS", 15)
    jpeg_quality: int = _i("JPEG_QUALITY", 80)
    max_width: int = _i("MAX_WIDTH", 1280)

    ready_threshold: float = _f("READY_THRESHOLD", 0.80)
    strict_mode: bool = _b("STRICT_MODE", False)
    helmet_on_head: bool = _b("HELMET_ON_HEAD", True)

    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = _i("PORT", 8000)
    videos_dir: str = os.getenv("VIDEOS_DIR", "videos")

    # pesos por ítem. Casco+Chaleco=0.90 (basta para >=0.80); lentes/guantes bonus.
    weights: dict = field(default_factory=lambda: {
        "helmet": _f("PPE_WEIGHT_HELMET", 0.45),
        "vest": _f("PPE_WEIGHT_VEST", 0.45),
        "glasses": _f("PPE_WEIGHT_GLASSES", 0.05),
        "gloves": _f("PPE_WEIGHT_GLOVES", 0.05),
    })

    # umbral de confianza por clase (None = usar el umbral base/slider)
    item_conf: dict = field(default_factory=lambda: {
        "helmet": _fopt("CONF_HELMET"),
        "glasses": _fopt("CONF_GLASSES"),
        "gloves": _fopt("CONF_GLOVES"),
        "vest": _fopt("CONF_VEST"),
    })

    @property
    def videos_abs(self):
        p = Path(self.videos_dir)
        return p if p.is_absolute() else ROOT / p


config = Config()
