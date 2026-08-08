#!/usr/bin/env python3
"""Descarga los pesos a weights/. Un solo sitio del que bajarlos.

    python download_models.py                # el que usa la app: SH17 yolo9e
    python download_models.py --variant yolo8m   # otra variante de SH17
    python download_models.py --all          # todos, para el comparador
    python download_models.py --list         # qué hay disponible

Los pesos no están en el repositorio porque son entrada, no código: pasan de
los 100 MB que GitHub rechaza y clonar pasaría de segundos a minutos.

Dos familias distintas, y conviene no confundirlas:

  SH17  — 17 clases de EPP, es lo que usa la app por defecto. Licencia
          CC BY-NC-SA 4.0: **no comercial**, solo prototipo.
  CSS   — varios modelos «worn / not-worn» de terceros. Sirven para comparar
          con compare.py, no para producción.
"""
from __future__ import annotations

import argparse
import sys
import urllib.request
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WEIGHTS = Path(__file__).resolve().parent / "weights"

SH17_BASE = "https://github.com/ahmadmughees/SH17dataset/releases/download/v1"
# alias local -> asset remoto
SH17 = {
    "yolo8n": "yolo8n.pt",
    "yolo8s": "yolo8s.pt",
    "yolo8m": "yolo8m.pt",     # más rápido
    "yolo8l": "yolo8l.pt",
    "yolo8x": "yolo8x.pt",
    "yolo9e": "yolo9e.pt",     # mejor mAP reportado (70.9) — el de por defecto
    "yolo10x": "yolo10x.pt",
}
POR_DEFECTO = "yolo9e"

# Modelos de terceros «worn / not-worn», solo para compare.py.
CSS = {
    "css_snehilsanyal.pt":
        "https://raw.githubusercontent.com/snehilsanyal/"
        "Construction-Site-Safety-PPE-Detection/main/models/best.pt",
    "css_ftnabil.pt":
        "https://raw.githubusercontent.com/ftnabil97/"
        "Construction-Site-Safety-Gears-Detection-Model-Yolov8/main/models/best.pt",
    "css_techaakash.pt":
        "https://raw.githubusercontent.com/tech-aakash/"
        "AI-Safety-Monitor-YOLO-v8-Based-PPE-Detection-in-Video-Footage/main/best.pt",
    "css_voxdroid.pt":
        "https://raw.githubusercontent.com/VoxDroid/"
        "Construction-Site-Safety-PPE-Detection/main/Model-Training/Outputs/"
        "runs/detect/yolov8s_ppe_css_200_epochs/weights/best.pt",
    "hafizqaim.pt":
        "https://github.com/hafizqaim/Workspace-Safety-Detection-using-YOLOv8/"
        "releases/download/v1.0.0/best.pt",
}


def _progreso(bloque, tam, total):
    if total > 0:
        pct = min(100, bloque * tam * 100 // total)
        print(f"\r    {pct}%", end="", flush=True)


def bajar(url: str, destino: Path) -> bool:
    if destino.exists():
        print(f"  · {destino.name} ya está")
        return True
    WEIGHTS.mkdir(exist_ok=True)
    print(f"  ↓ {destino.name}")
    try:
        urllib.request.urlretrieve(url, destino, _progreso)
        print(f"\r    {destino.stat().st_size // 1024 // 1024} MB")
        return True
    except Exception as e:
        print(f"\r    falló: {e}")
        # Medio archivo es peor que ninguno: el modelo cargaría y reventaría
        # mucho más adelante con un error que no dice nada.
        destino.unlink(missing_ok=True)
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--variant", default=POR_DEFECTO,
                    help=f"variante de SH17 (por defecto {POR_DEFECTO})")
    ap.add_argument("--all", action="store_true",
                    help="además, los modelos CSS que usa compare.py")
    ap.add_argument("--list", action="store_true",
                    help="lista lo disponible y sale")
    args = ap.parse_args()

    if args.list:
        print("SH17 (el que usa la app):")
        for k in SH17:
            print(f"  {k}{'   ← por defecto' if k == POR_DEFECTO else ''}")
        print("\nCSS (solo para compare.py, con --all):")
        for k in CSS:
            print(f"  {k}")
        return 0

    if args.variant not in SH17:
        print(f"Variante desconocida '{args.variant}'. Usa --list.")
        return 1

    print("SH17 — CC BY-NC-SA 4.0, uso no comercial:")
    ok = bajar(f"{SH17_BASE}/{SH17[args.variant]}",
               WEIGHTS / f"sh17_{args.variant}.pt")

    if args.all:
        print("\nModelos CSS para el comparador:")
        for nombre, url in CSS.items():
            bajar(url, WEIGHTS / nombre)

    if ok:
        print(f"\nListo. Apunta MODEL_WEIGHTS a "
              f"weights/sh17_{args.variant}.pt en tu .env si no es el "
              f"de por defecto.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
