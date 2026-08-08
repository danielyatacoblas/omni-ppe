"""Descarga pesos pre-entrenados SH17 (PPE, 17 clases) desde los releases oficiales.

Uso:
    python download_weights.py            # descarga el default (yolo9e)
    python download_weights.py yolo8m     # descarga otra variante
    python download_weights.py --list     # muestra las variantes disponibles

Fuente: https://github.com/ahmadmughees/SH17dataset/releases/tag/v1
Licencia del dataset: CC BY-NC-SA 4.0 (uso NO comercial — solo para prototipo/prueba).
"""
import sys
import urllib.request
from pathlib import Path

BASE = "https://github.com/ahmadmughees/SH17dataset/releases/download/v1"
WEIGHTS_DIR = Path(__file__).parent / "weights"

# alias local -> asset remoto
VARIANTS = {
    "yolo8n": "yolo8n.pt",
    "yolo8s": "yolo8s.pt",
    "yolo8m": "yolo8m.pt",
    "yolo8l": "yolo8l.pt",
    "yolo8x": "yolo8x.pt",
    "yolo9e": "yolo9e.pt",   # mejor mAP reportado (70.9)
    "yolo10x": "yolo10x.pt",
}


def _progress(block, block_size, total):
    if total > 0:
        pct = min(100, block * block_size * 100 // total)
        print(f"\r  descargando... {pct}%", end="", flush=True)


def download(variant: str) -> Path:
    if variant not in VARIANTS:
        raise SystemExit(f"Variante desconocida '{variant}'. Usa --list para ver opciones.")
    WEIGHTS_DIR.mkdir(exist_ok=True)
    dest = WEIGHTS_DIR / f"sh17_{variant}.pt"
    if dest.exists():
        print(f"Ya existe: {dest}")
        return dest
    url = f"{BASE}/{VARIANTS[variant]}"
    print(f"Descargando {variant} desde {url}")
    urllib.request.urlretrieve(url, dest, _progress)
    print(f"\nGuardado en: {dest}")
    return dest


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else "yolo9e"
    if arg in ("--list", "-l"):
        print("Variantes disponibles:")
        for k in VARIANTS:
            print(f"  - {k}")
    else:
        download(arg)
