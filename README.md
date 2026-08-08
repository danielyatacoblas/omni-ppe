# MVP PPE — Detección de EPP en vivo

Detecta por persona si lleva **casco, lentes, guantes y chaleco** sobre videos de
prueba, con streaming fluido y una **barra de % de cumplimiento** que se pone
**verde (LISTO)** al superar el umbral o **rojo (NO LISTO)** si falta EPP.

- **Modelo:** pesos pre-entrenados **SH17** (17 clases PPE) — no se entrena desde 0.
- **Aceleración:** CUDA (RTX 3060). Cambia a CPU en `.env` si hace falta.
- **Streaming:** FastAPI + MJPEG, con paso de FPS/skip como en `vision-node`.

> ⚠️ SH17 es **CC BY-NC-SA 4.0 (no comercial)** — úsalo solo para este prototipo.
> Para entrega comercial ver la ruta con *Ultralytics construction-ppe* / Roboflow.

## 1. Instalar

```bash
cd first_mvp_ppe
python -m venv .venv
.venv\Scripts\activate            # Windows
# GPU (RTX 3060) — instala torch CUDA primero:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

## 2. Descargar pesos SH17

```bash
python download_weights.py            # yolo9e (máx precisión) -> weights/sh17_yolo9e.pt
# alternativas: python download_weights.py yolo8m   (más rápido)
```

## 3. Poner videos de prueba

Copia tus `.mp4` a la carpeta `videos/`. Aparecen en el selector de la UI.

## 4. Ejecutar

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

Abre <http://localhost:8000>, elige un video, ajusta confianza / EPP requerido y
pulsa **Iniciar**.

## Ajustes (`.env`)

| Clave | Descripción |
| ----- | ----------- |
| `MODEL_WEIGHTS` | Ruta a los pesos (`weights/sh17_yolo9e.pt`) |
| `DEVICE` | `cuda:0` o `cpu` |
| `TARGET_FPS` | FPS de inferencia (fluidez) |
| `PPE_WEIGHT_*` | Peso de cada ítem: casco `.40`, lentes `.25`, guantes `.20`, chaleco `.15` |
| `READY_THRESHOLD` | % mínimo para "LISTO" (default `0.80`) |
| `STRICT_MODE` | Exige TODOS los ítems requeridos presentes |

## Cómo se calcula el %

Cada ítem detectado se asigna a la persona que lo contiene; se suma el peso de los
ítems presentes / peso total requerido → score 0..100 %. Verde si ≥ umbral.
Los pesos y el umbral se editan en `.env` sin tocar código.
