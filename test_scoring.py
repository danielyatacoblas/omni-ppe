# -*- coding: utf-8 -*-
"""Pruebas de scoring.py — quién lleva qué, y si eso basta para pasar.

    python -m pytest test_scoring.py -q

Es la única parte del MVP que decide algo con consecuencias: si una persona
entra o no entra a la obra. El detector puede fallar y se ve en pantalla; que
el reparto de ítems por persona falle no se ve, solo sale un porcentaje que
parece razonable y no lo es.

No hace falta modelo ni video: `score_people` recibe cajas y devuelve números.
"""
from __future__ import annotations

import pytest

from backend.config import config
from backend.scoring import score_people


def persona(x1, y1, x2, y2):
    return {"box": (x1, y1, x2, y2)}


def item(nombre, box, estado="worn", conf=0.9):
    return {"item": nombre, "box": box, "state": estado, "conf": conf}


# Una persona de pie, de (100,100) a (200,400). La cabeza cae en el tercio alto.
UNA = [persona(100, 100, 200, 400)]
CASCO = (130, 110, 170, 140)
CHALECO = (110, 200, 190, 300)


# ── el caso normal ──────────────────────────────────────────────────────────

def test_casco_y_chaleco_bastan_para_pasar():
    r = score_people(UNA, [], [item("helmet", CASCO), item("vest", CHALECO)])[0]
    assert r["worn"] == ["helmet", "vest"]
    assert r["missing"] == []
    assert r["ready"] is True
    assert r["pct"] == 90


def test_sin_nada_no_pasa():
    r = score_people(UNA, [], [])[0]
    assert r["pct"] == 0
    assert r["ready"] is False
    assert r["missing"] == ["helmet", "vest"]


def test_solo_casco_no_basta():
    r = score_people(UNA, [], [item("helmet", CASCO)])[0]
    assert r["missing"] == ["vest"]
    assert r["ready"] is False


def test_los_extras_suman_pero_no_se_pasan_de_uno():
    dets = [item("helmet", CASCO), item("vest", CHALECO),
            item("glasses", (135, 115, 165, 130)),
            item("gloves", (105, 290, 130, 320))]
    r = score_people(UNA, [], dets)[0]
    assert r["score"] <= 1.0
    assert r["ready"] is True


# ── lo que de verdad se puede romper ────────────────────────────────────────

def test_el_epp_de_otro_no_cuenta_como_propio():
    """Dos personas separadas: el casco de una no debe puntuar a la otra."""
    dos = [persona(100, 100, 200, 400), persona(400, 100, 500, 400)]
    r = score_people(dos, [], [item("helmet", CASCO), item("vest", CHALECO)])
    assert r[0]["worn"] == ["helmet", "vest"]
    assert r[1]["worn"] == []
    assert r[1]["ready"] is False


def test_un_casco_en_el_suelo_no_cuenta_como_puesto():
    """Presencia sola: el casco tirado a los pies no protege a nadie."""
    en_el_suelo = (130, 370, 170, 395)
    r = score_people(UNA, [], [item("helmet", en_el_suelo),
                               item("vest", CHALECO)],
                     helmet_presence_only=True)[0]
    assert "helmet" not in r["worn"]
    assert r["ready"] is False


def test_con_caja_de_cabeza_manda_la_cabeza():
    cabeza = [{"box": (125, 105, 175, 150)}]
    r = score_people(UNA, cabeza, [item("helmet", CASCO), item("vest", CHALECO)],
                     helmet_presence_only=True)[0]
    assert "helmet" in r["worn"]


def test_no_puesto_explicito_gana_a_una_deteccion_mas_floja():
    """Si el modelo ve 'sin casco' con más confianza que 'con casco', manda."""
    dets = [item("helmet", CASCO, "worn", conf=0.4),
            item("helmet", CASCO, "absent", conf=0.8),
            item("vest", CHALECO)]
    r = score_people(UNA, [], dets)[0]
    assert r["not_worn"] == ["helmet"]
    assert "helmet" not in r["worn"]
    assert r["ready"] is False


def test_una_deteccion_sin_dueno_se_descarta():
    """EPP flotando lejos de cualquier persona no puntúa a nadie."""
    r = score_people(UNA, [], [item("helmet", (900, 900, 950, 950))])[0]
    assert r["worn"] == []


# ── las reglas configurables ────────────────────────────────────────────────

def test_estricto_exige_todo_aunque_el_porcentaje_llegue():
    dets = [item("helmet", CASCO),
            item("glasses", (135, 115, 165, 130)),
            item("gloves", (105, 290, 130, 320))]
    flojo = score_people(UNA, [], dets, strict=False)[0]
    duro = score_people(UNA, [], dets, strict=True)[0]
    assert duro["ready"] is False
    assert duro["missing"] == ["vest"]
    # Sin modo estricto, el chaleco que falta no se recupera con extras.
    assert flojo["pct"] < 100


def test_se_puede_pedir_otro_conjunto_de_epp():
    r = score_people(UNA, [], [item("helmet", CASCO)],
                     required={"helmet"}, strict=True)[0]
    assert r["ready"] is True
    assert r["missing"] == []


def test_sin_personas_no_hay_resultado():
    assert score_people([], [], [item("helmet", CASCO)]) == []


def test_el_umbral_de_config_es_alcanzable_con_los_pesos_de_config():
    """Si alguien cambia los pesos en .env, casco+chaleco debe seguir bastando."""
    alcanzable = config.weights["helmet"] + config.weights["vest"]
    assert alcanzable >= config.ready_threshold, (
        "casco+chaleco ya no llegan al umbral: nadie podría pasar sin extras")
