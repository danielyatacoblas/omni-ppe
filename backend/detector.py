"""Detector YOLO unificado + cache de modelos para el comparador.

Cada Detector carga un modelo y, leyendo sus nombres de clase, arma:
  - class_map: id -> (item, state)     (via registry.parse_class)
  - available_items: ítems canónicos que el modelo sabe detectar
  - helmet_presence_only: True si el modelo NO tiene clase negativa de casco
    (entonces se valida casco-sobre-cabeza por geometría)
"""
from pathlib import Path

from ultralytics import YOLO

from .config import config
from .registry import parse_class, MODELS_BY_KEY

ROOT = Path(__file__).resolve().parent.parent
SCORED_ITEMS = ("helmet", "vest", "gloves", "glasses", "boots", "mask")


class Detector:
    def __init__(self, weights_path: str):
        self.model = YOLO(weights_path)
        self.names = self.model.names

        self.class_map = {}          # id -> (item, state)
        self.person_ids = set()
        self.head_ids = set()
        items, neg_items = set(), set()
        for i, name in self.names.items():
            item, state = parse_class(name)
            if item == "person":
                self.person_ids.add(i)
            elif item == "head":
                self.head_ids.add(i)
            elif item in SCORED_ITEMS:
                self.class_map[i] = (item, state)
                items.add(item)
                if state == "absent":
                    neg_items.add(item)

        self.available_items = [it for it in SCORED_ITEMS if it in items]
        # casco solo por presencia si el modelo no distingue "no-casco"
        self.helmet_presence_only = ("helmet" in items) and ("helmet" not in neg_items)

    def _item_threshold(self, item, base):
        ov = config.item_conf.get(item)
        return ov if ov is not None else base

    def infer(self, frame, conf: float):
        """Devuelve persons, heads, dets.

        dets: [{box, conf, item, state, cls_name}]  (state: worn|absent)
        """
        overrides = [v for v in config.item_conf.values() if v is not None]
        base_pred = min([conf, *overrides]) if overrides else conf

        res = self.model.predict(
            frame, conf=base_pred, imgsz=config.img_size,
            device=config.device, verbose=False,
        )[0]

        persons, heads, dets = [], [], []
        if res.boxes is None:
            return persons, heads, dets

        for b in res.boxes:
            cls = int(b.cls[0])
            xyxy = tuple(float(v) for v in b.xyxy[0])
            c = float(b.conf[0])
            if cls in self.person_ids:
                if c >= conf:
                    persons.append({"box": xyxy, "conf": c})
            elif cls in self.head_ids:
                heads.append({"box": xyxy, "conf": c})
            elif cls in self.class_map:
                item, state = self.class_map[cls]
                # umbral propio solo a los "worn" chicos; los "absent" con base
                thr = self._item_threshold(item, conf) if state == "worn" else conf
                if c >= thr:
                    dets.append({"box": xyxy, "conf": c, "item": item,
                                 "state": state, "cls_name": self.names[cls]})
        return persons, heads, dets


# ---- cache de detectores (comparador) ----
_cache: dict[str, Detector] = {}


def get_detector(model_key: str) -> Detector:
    if model_key not in _cache:
        meta = MODELS_BY_KEY.get(model_key)
        if not meta:
            raise KeyError(f"modelo desconocido: {model_key}")
        path = ROOT / "weights" / meta["file"]
        if not path.exists():
            raise FileNotFoundError(f"faltan pesos: {path} (corre download_models.py)")
        _cache[model_key] = Detector(str(path))
    return _cache[model_key]
