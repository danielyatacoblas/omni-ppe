"""Asociación detección->persona y cálculo del % de EPP por persona (unificado).

Por cada persona y cada ítem se decide su estado:
  - WORN     : puesto (verde)
  - NOT_WORN : detectado explícitamente sin poner (clase negativa) -> rojo
  - UNKNOWN  : no detectado

Score = suma de pesos de los ítems WORN (absoluto, tope 1.0). Con casco+chaleco
se llega a >=0.80 (verde); lentes/guantes suman como bonus.
Para modelos de solo-presencia se valida casco-sobre-cabeza por geometría.
"""
from .config import config
from .registry import ITEM_LABELS


def _center(box):
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2, (y1 + y2) / 2


def _contains(person_box, cx, cy):
    x1, y1, x2, y2 = person_box
    return x1 <= cx <= x2 and y1 <= cy <= y2


def _overlap_ratio(a, b):
    """Fracción de 'a' que cae dentro de 'b'."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0.0, ix2 - ix1), max(0.0, iy2 - iy1)
    area = max(1e-6, (ax2 - ax1) * (ay2 - ay1))
    return iw * ih / area


def _assign(box, people):
    cx, cy = _center(box)
    best_i, best_r = -1, 0.0
    for i, p in enumerate(people):
        if not _contains(p["box"], cx, cy):
            continue
        r = _overlap_ratio(box, p["box"])
        if r > best_r:
            best_r, best_i = r, i
    return best_i


def _helmet_on_head(box, head_boxes, person_box):
    if head_boxes:
        for hb in head_boxes:
            if _overlap_ratio(box, hb) > 0.05 or _overlap_ratio(hb, box) > 0.05:
                return True
        return False
    x1, y1, x2, y2 = person_box
    return (box[1] + box[3]) / 2 <= y1 + 0.35 * (y2 - y1)


def score_people(persons, heads, dets, required=None, strict=None,
                 helmet_presence_only=False):
    if required is None:
        required = {"helmet", "vest"}
    else:
        required = set(required)
    if strict is None:
        strict = config.strict_mode
    heads = heads or []

    people = [{"box": p["box"], "worn": {}, "absent": {}, "heads": []}
              for p in persons]

    for h in heads:
        i = _assign(h["box"], people)
        if i >= 0:
            people[i]["heads"].append(h["box"])

    for d in dets:
        i = _assign(d["box"], people)
        if i < 0:
            continue
        item, state = d["item"], d["state"]
        # casco por presencia -> exigir que esté sobre la cabeza
        if item == "helmet" and state == "worn" and helmet_presence_only \
                and config.helmet_on_head:
            if not _helmet_on_head(d["box"], people[i]["heads"], people[i]["box"]):
                continue
        bucket = people[i][state]
        bucket[item] = max(bucket.get(item, 0.0), d["conf"])

    out = []
    for p in people:
        status = {}
        for item in ITEM_LABELS:
            w = p["worn"].get(item, 0.0)
            a = p["absent"].get(item, 0.0)
            if w > 0 and w >= a:
                status[item] = "worn"
            elif a > 0:
                status[item] = "not_worn"
            # else: unknown -> no aparece
        worn = {it for it, s in status.items() if s == "worn"}
        score = min(1.0, sum(config.weights.get(it, 0.0) for it in worn))
        req_worn = required & worn
        if strict:
            ready = required.issubset(worn)
        else:
            ready = score >= config.ready_threshold
        out.append({
            "box": p["box"],
            "worn": sorted(worn),
            "not_worn": sorted(it for it, s in status.items() if s == "not_worn"),
            "missing": sorted(required - worn),
            "score": round(score, 3),
            "pct": int(round(score * 100)),
            "ready": ready,
        })
    return out
