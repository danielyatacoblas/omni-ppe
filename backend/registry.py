"""Registro de modelos disponibles + mapeo unificado de clases -> (ítem, estado).

Cada modelo puede usar dos esquemas:
  - "presencia": solo detecta el objeto (SH17: 'helmet', 'safety-vest'...)
  - "puesto/no-puesto": tiene clases negativas (CSS: 'NO-Hardhat', 'head_nohelmet'...)

El parser normaliza cualquier nombre de clase a un ítem canónico + estado
('worn' | 'absent'), así el resto del sistema es agnóstico al modelo.
"""
import re

# ítem canónico -> etiqueta en español (para la UI)
ITEM_LABELS = {
    "helmet": "Casco",
    "vest": "Chaleco",
    "gloves": "Guantes",
    "glasses": "Lentes",
    "boots": "Botas",
    "mask": "Mascarilla",
}

# orden de prueba de keywords (helmet antes que head para 'head_helmet')
_ITEM_KW = [
    ("helmet", ("helmet", "hardhat")),
    ("vest", ("vest",)),
    ("gloves", ("glove",)),
    ("glasses", ("glass", "goggle")),
    ("boots", ("boot",)),
    ("mask", ("mask",)),
]

_NEG_RE = re.compile(r"no[-_ ]?(helmet|hardhat|glove|glass|vest|mask|boot|ear)")


def parse_class(name: str):
    """Devuelve (item, state). item/state = None si no interesa.

    state: 'worn' (puesto/presente) | 'absent' (no puesto) | None (person/head)
    """
    low = name.lower().strip()
    if low == "person":
        return "person", None
    if low == "head":
        return "head", None
    neg = bool(_NEG_RE.search(low)) or bool(re.match(r"no[-_ ]", low))
    state = "absent" if neg else "worn"
    for item, kws in _ITEM_KW:
        if any(k in low for k in kws):
            return item, state
    return None, None


# modelos con pesos ya descargados en weights/
MODELS = [
    {"key": "hafizqaim", "file": "hafizqaim.pt",
     "label": "hafizqaim v8 — casco-en-cabeza + lentes + guantes (puesto/no)"},
    {"key": "css_ftnabil", "file": "css_ftnabil.pt",
     "label": "CSS ftnabil v8s — casco/chaleco/guantes/botas (puesto/no)"},
    {"key": "css_voxdroid", "file": "css_voxdroid.pt",
     "label": "CSS VoxDroid v8s 200ep — casco/chaleco (puesto/no)"},
    {"key": "css_snehilsanyal", "file": "css_snehilsanyal.pt",
     "label": "CSS snehilsanyal v8n — casco/chaleco (puesto/no)"},
    {"key": "css_techaakash", "file": "css_techaakash.pt",
     "label": "CSS tech-aakash v8n — mínimo casco/chaleco (puesto/no)"},
    {"key": "sh17_yolo9e", "file": "sh17_yolo9e.pt",
     "label": "SH17 v9e — detallado (presencia, 17 clases)"},
    {"key": "sh17_yolo8m", "file": "sh17_yolo8m.pt",
     "label": "SH17 v8m — presencia (17 clases)"},
    # sin pesos públicos -> requieren entrenamiento propio
    {"key": "azimjaan21", "file": "azimjaan21.pt", "trainable": True,
     "label": "azimjaan21 — casco/chaleco/cabeza (54k imgs, REQUIERE ENTRENAR)"},
    {"key": "ultralytics_cppe", "file": "ultralytics_cppe.pt", "trainable": True,
     "label": "Ultralytics construction-ppe — casco/chaleco/guantes/lentes (REQUIERE ENTRENAR)"},
]

MODELS_BY_KEY = {m["key"]: m for m in MODELS}
