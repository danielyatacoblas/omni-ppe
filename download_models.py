"""Descarga TODOS los pesos del comparador a weights/.

Uso:  python download_models.py
"""
import urllib.request
from pathlib import Path

WEIGHTS = Path(__file__).parent / "weights"

URLS = {
    # SH17 (CC BY-NC-SA 4.0 — solo prototipo)
    "sh17_yolo8m.pt": "https://github.com/ahmadmughees/SH17dataset/releases/download/v1/yolo8m.pt",
    "sh17_yolo9e.pt": "https://github.com/ahmadmughees/SH17dataset/releases/download/v1/yolo9e.pt",
    # CSS worn/not-worn
    "css_snehilsanyal.pt": "https://raw.githubusercontent.com/snehilsanyal/Construction-Site-Safety-PPE-Detection/main/models/best.pt",
    "css_ftnabil.pt": "https://raw.githubusercontent.com/ftnabil97/Construction-Site-Safety-Gears-Detection-Model-Yolov8/main/models/best.pt",
    "css_techaakash.pt": "https://raw.githubusercontent.com/tech-aakash/AI-Safety-Monitor-YOLO-v8-Based-PPE-Detection-in-Video-Footage/main/best.pt",
    "css_voxdroid.pt": "https://raw.githubusercontent.com/VoxDroid/Construction-Site-Safety-PPE-Detection/main/Model-Training/Outputs/runs/detect/yolov8s_ppe_css_200_epochs/weights/best.pt",
    "hafizqaim.pt": "https://github.com/hafizqaim/Workspace-Safety-Detection-using-YOLOv8/releases/download/v1.0.0/best.pt",
}


def main():
    WEIGHTS.mkdir(exist_ok=True)
    for name, url in URLS.items():
        dest = WEIGHTS / name
        if dest.exists():
            print(f"ya existe  {name}")
            continue
        print(f"bajando    {name} ...")
        urllib.request.urlretrieve(url, dest)
        print(f"  ok -> {dest} ({dest.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
