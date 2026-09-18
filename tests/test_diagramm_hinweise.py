"""Tests für ide/diagramm/hinweise.py und ide/diagramm/seite.py:
Layout-Hinweise und Seitenbereich (M9, Schritt 7). Headless.

Aufbau wie tests/test_design_pruefer_regeln.py aus M7: je Regel ein
Diagramm, das sie auslöst, und eines, das sie nicht auslöst.
"""

from __future__ import annotations

import pytest

from ide.diagramm.hinweise import (
    abgeschnittener_text,
    ausserhalb_der_seite,
    lose_verbindungsenden,
    pruefen,
    ueberlappende_formen,
)
from ide.diagramm.seite import satzspiegel, seitengroesse


def _diagramm(shapes=(), connectors=(), page=None) -> dict:
    return {
        "format": "pdiag/1",
        "type": "class",
        "page": page or {"size": "A4", "orientation": "landscape"},
        "style": "modern-light",
        "shapes": list(shapes),
        "connectors": list(connectors),
    }


def _klasse(kennung: str, x: float, y: float, w: float = 160, h: float = 120, **text) -> dict:
    return {
        "id": kennung,
        "kind": "class",
        "x": x,
        "y": y,
        "w": w,
        "h": h,
        "text": {"name": text.get("name", kennung), **text},
    }


# -- Seitenbereich -------------------------------------------------------


def test_a4_quer_ist_breiter_als_hoch() -> None:
    breite, hoehe = seitengroesse({"size": "A4", "orientation": "landscape"})

    assert breite > hoehe
    assert (round(breite), round(hoehe)) == (1123, 794)  # 297 x 210 mm bei 96 dpi


def test_a4_hoch_ist_hoeher_als_breit() -> None:
    breite, hoehe = seitengroesse({"size": "A4", "orientation": "portrait"})

    assert (round(breite), round(hoehe)) == (794, 1123)


def test_unbekanntes_format_faellt_auf_a4_zurueck() -> None:
    """Eine von Hand bearbeitete Datei soll den Editor nicht lahmlegen."""
    assert seitengroesse({"size": "Plakat"}) == seitengroesse({"size": "A4"})


def test_satzspiegel_liegt_innerhalb_des_blatts() -> None:
    seite = {"size": "A4", "orientation": "landscape"}
    breite, hoehe = seitengroesse(seite)
    links, oben, satz_breite, satz_hoehe = satzspiegel(seite)

    assert links > 0 and oben > 0
    assert links + satz_breite < breite
    assert oben + satz_hoehe < hoehe


# -- Überlappung ---------------------------------------------------------


def test_uebereinander_liegende_formen_werden_gemeldet() -> None:
    daten = _diagramm([_klasse("s1", 100, 100), _klasse("s2", 180, 150)])

    hinweise = ueberlappende_formen(daten)

    assert len(hinweise) == 1
    assert hinweise[0].elemente == ("s1", "s2")
    assert "überlappen" in hinweise[0].meldung


def test_nebeneinander_liegende_formen_sind_in_ordnung() -> None:
    daten = _diagramm([_klasse("s1", 100, 100), _klasse("s2", 300, 100)])

    assert ueberlappende_formen(daten) == []


def test_ein_paar_pixel_beruehrung_reicht_nicht_fuer_eine_meldung() -> None:
    """Sonst meckert der Editor bei jedem bündig angelegten Kasten."""
    daten = _diagramm([_klasse("s1", 100, 100), _klasse("s2", 258, 100)])

    assert ueberlappende_formen(daten) == []


# -- Abgeschnittener Text ------------------------------------------------


def test_zu_schmale_form_wird_gemeldet() -> None:
    form = _klasse("s1", 100, 100, w=40)
    form["text"] = {"name": "EineSehrLangeKlasse", "attributes": [], "methods": []}
    daten = _diagramm([form])

    hinweise = abgeschnittener_text(daten)

    assert [h.elemente for h in hinweise] == [("s1",)]
    assert "zu schmal" in hinweise[0].meldung


def test_zu_niedrige_form_wird_gemeldet() -> None:
    form = _klasse("s1", 100, 100, w=400, h=40)
    form["text"] = {
        "name": "TAmpel",
        "attributes": ["-a: int", "-b: int", "-c: int"],
        "methods": ["+m1()", "+m2()", "+m3()"],
    }
    daten = _diagramm([form])

    hinweise = abgeschnittener_text(daten)

    assert [h.elemente for h in hinweise] == [("s1",)]
    assert "zu niedrig" in hinweise[0].meldung


def test_notiz_mit_langem_text_gilt_nicht_als_zu_schmal() -> None:
    """Im Screenshot-Durchgang aufgefallen: Notizen brechen ihren Text um
    (siehe `_notiz_zeichnen`), wurden aber wie Klassen auf Zeilenbreite
    geprüft und dadurch reihenweise fälschlich gemeldet."""
    notiz = {
        "id": "s1",
        "kind": "note",
        "x": 100,
        "y": 100,
        "w": 160,
        "h": 200,
        "text": {"name": "Zustand: 1=gruen, 2=gelb, 3=rot, 4=gelb"},
    }

    assert abgeschnittener_text(_diagramm([notiz])) == []


def test_zu_flache_notiz_wird_trotzdem_gemeldet() -> None:
    """Umbrechen hilft nur seitlich – nach unten läuft der Text hinaus."""
    notiz = {
        "id": "s1",
        "kind": "note",
        "x": 100,
        "y": 100,
        "w": 120,
        "h": 24,
        "text": {"name": "Zustand: 1=gruen, 2=gelb, 3=rot, 4=gelb"},
    }

    assert [h.regel for h in abgeschnittener_text(_diagramm([notiz]))] == [
        "abgeschnittener_text"
    ]


def test_ausreichend_grosse_form_wird_nicht_gemeldet() -> None:
    form = _klasse("s1", 100, 100, w=400, h=300)
    form["text"] = {"name": "TAmpel", "attributes": ["-a: int"], "methods": ["+m1()"]}

    assert abgeschnittener_text(_diagramm([form])) == []


# -- Lose Enden ----------------------------------------------------------


def test_verbindung_ins_leere_wird_gemeldet() -> None:
    daten = _diagramm(
        [_klasse("s1", 100, 100)],
        [{"id": "c1", "kind": "association", "from": "s1", "to": "weg"}],
    )

    hinweise = lose_verbindungsenden(daten)

    assert len(hinweise) == 1
    assert hinweise[0].elemente == ("c1",)
    assert "Ziel" in hinweise[0].meldung


def test_vollstaendige_verbindung_ist_in_ordnung() -> None:
    daten = _diagramm(
        [_klasse("s1", 100, 100), _klasse("s2", 400, 100)],
        [{"id": "c1", "kind": "association", "from": "s1", "to": "s2"}],
    )

    assert lose_verbindungsenden(daten) == []


# -- Seitenbereich -------------------------------------------------------


def test_form_ausserhalb_des_blatts_wird_gemeldet() -> None:
    daten = _diagramm([_klasse("s1", 2000, 100)])

    hinweise = ausserhalb_der_seite(daten)

    assert [h.elemente for h in hinweise] == [("s1",)]
    assert "Ausdruck" in hinweise[0].meldung


def test_form_die_nur_halb_heraushaengt_wird_auch_gemeldet() -> None:
    breite, _ = seitengroesse({"size": "A4", "orientation": "landscape"})
    daten = _diagramm([_klasse("s1", breite - 80, 100)])

    assert [h.elemente for h in ausserhalb_der_seite(daten)] == [("s1",)]


def test_form_mitten_auf_dem_blatt_ist_in_ordnung() -> None:
    assert ausserhalb_der_seite(_diagramm([_klasse("s1", 200, 200)])) == []


# -- Zusammenspiel -------------------------------------------------------


def test_pruefen_sammelt_alle_regeln() -> None:
    daten = _diagramm(
        [_klasse("s1", 100, 100), _klasse("s2", 180, 150), _klasse("s3", 3000, 100)],
        [{"id": "c1", "kind": "association", "from": "s1", "to": "weg"}],
    )

    regeln = {hinweis.regel for hinweis in pruefen(daten)}

    assert regeln == {"ueberlappung", "loses_ende", "ausserhalb_der_seite"}


def test_sauberes_diagramm_ergibt_keine_hinweise() -> None:
    daten = _diagramm(
        [_klasse("s1", 100, 100, w=300, h=200), _klasse("s2", 500, 100, w=300, h=200)],
        [{"id": "c1", "kind": "association", "from": "s1", "to": "s2"}],
    )

    assert pruefen(daten) == []


@pytest.mark.parametrize("regel", ["ueberlappung", "loses_ende", "ausserhalb_der_seite"])
def test_jeder_hinweis_nennt_ein_element(regel: str) -> None:
    """Die Zeichenfläche markiert anhand von `element` – ohne das
    könnte sie den Hinweis nicht zeigen."""
    daten = _diagramm(
        [_klasse("s1", 100, 100), _klasse("s2", 180, 150), _klasse("s3", 3000, 100)],
        [{"id": "c1", "kind": "association", "from": "s1", "to": "weg"}],
    )

    betroffen = [h for h in pruefen(daten) if h.regel == regel]

    assert betroffen and all(h.elemente for h in betroffen)
