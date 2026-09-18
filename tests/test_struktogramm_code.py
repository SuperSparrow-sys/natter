"""Tests für ide/diagramm/struktogramm_code.py: Struktogramm als
Python-Quelltext (M9, Schritt 14).

Reine Übersetzung ohne Qt – die Tests brauchen weder Fenster noch
Zeichenfläche. Jedes Ergebnis wird zusätzlich geparst: erzeugter Code,
der nicht läuft, wäre schlimmer als gar keiner.
"""

from __future__ import annotations

import ast
import textwrap

import pytest

from ide.diagramm.bloecke import neuer_block
from ide.diagramm.struktogramm import BLOCK_BESCHRIFTUNGEN
from ide.diagramm.struktogramm_code import Ergebnis, als_python


def _diagramm(*bloecke: dict) -> dict:
    return {
        "format": "pdiag/1",
        "type": "struktogramm",
        "name": "ampel_zeichnen",
        "page": {"size": "A4", "orientation": "portrait"},
        "style": "modern-light",
        "root": {"id": "b0", "kind": "sequence", "children": list(bloecke)},
    }


def _block(art: str, text: str = "", **listen: object) -> dict:
    return {"id": f"b_{art}", "kind": art, "text": text, **listen}


def _anweisung(text: str) -> dict:
    return _block("statement", text)


def _zeilen(ergebnis: Ergebnis) -> list[str]:
    return ergebnis.text.splitlines()


def _pruefen(ergebnis: Ergebnis, *, schnipsel: bool = False) -> None:
    """Ein Schnipsel darf `break` und `return` enthalten – er ist zum
    Einfügen gedacht, also wird er dafür in Funktion und Schleife
    gehüllt geprüft."""
    if schnipsel:
        huelle = "def _huelle():\n    while True:\n"
        ast.parse(huelle + textwrap.indent(ergebnis.text, "        "))
        return
    ast.parse(ergebnis.text)
    # compile() prüft schärfer als ast.parse, etwa auf `break` außerhalb
    # einer Schleife oder ein unerreichbares `case _`.
    compile(ergebnis.text, "<struktogramm>", "exec")


# -- Rahmen --------------------------------------------------------------


def test_ganzes_struktogramm_kommt_in_eine_funktion() -> None:
    ergebnis = als_python(_diagramm(_anweisung("zaehler = 0")))

    assert _zeilen(ergebnis)[0] == "def ampel_zeichnen():"
    assert _zeilen(ergebnis)[1] == "    zaehler = 0"
    _pruefen(ergebnis)


def test_unbrauchbarer_name_wird_zu_einem_gueltigen_bezeichner() -> None:
    daten = _diagramm(_anweisung("x = 1"))
    daten["name"] = "Ampel zeichnen"

    assert _zeilen(als_python(daten))[0] == "def Ampel_zeichnen():"

    daten["name"] = "1. Versuch"
    assert _zeilen(als_python(daten))[0] == "def struktogramm():"


def test_leeres_struktogramm_ergibt_eine_funktion_mit_pass() -> None:
    ergebnis = als_python(_diagramm())

    assert _zeilen(ergebnis) == ["def ampel_zeichnen():", "    pass"]
    _pruefen(ergebnis)


# -- Je Blocktyp ---------------------------------------------------------


def test_anweisung_bleibt_stehen_wie_sie_dasteht() -> None:
    ergebnis = als_python(_diagramm(_anweisung("zaehler = zaehler + 1")))

    assert "    zaehler = zaehler + 1" in _zeilen(ergebnis)
    assert ergebnis.anzahl == 0


def test_unterprogrammaufruf_ist_der_aufruf_selbst() -> None:
    ergebnis = als_python(_diagramm(_block("call", "warte(500)")))

    assert "    warte(500)" in _zeilen(ergebnis)
    _pruefen(ergebnis)


def test_verzweigung_wird_zu_if_und_else() -> None:
    ergebnis = als_python(
        _diagramm(
            _block(
                "branch",
                "zaehler < 3",
                then=[_anweisung("zaehler = zaehler + 1")],
                **{"else": [_anweisung("zaehler = 0")]},
            )
        )
    )

    assert _zeilen(ergebnis)[1:] == [
        "    if zaehler < 3:",
        "        zaehler = zaehler + 1",
        "    else:",
        "        zaehler = 0",
    ]
    _pruefen(ergebnis)


def test_mehrfachauswahl_mit_einfachen_werten_wird_zu_match() -> None:
    ergebnis = als_python(
        _diagramm(
            _block(
                "multi_branch",
                "farbe",
                cases=[
                    {"label": "'rot'", "children": [_anweisung("halt()")]},
                    {"label": "'gruen'", "children": [_anweisung("fahr()")]},
                    {"label": "sonst", "children": [_anweisung("warte()")]},
                ],
            )
        )
    )

    assert _zeilen(ergebnis)[1:] == [
        "    match farbe:",
        "        case 'rot':",
        "            halt()",
        "        case 'gruen':",
        "            fahr()",
        "        case _:",
        "            warte()",
    ]
    _pruefen(ergebnis)


def test_mehrfachauswahl_ohne_einfache_werte_wird_zur_wenn_kette() -> None:
    """Ein bloßer Name wäre als `case`-Muster ein Capture und würde
    alles auffangen – dann lieber der Vergleich."""
    ergebnis = als_python(
        _diagramm(
            _block(
                "multi_branch",
                "zustand",
                cases=[
                    {"label": "rot", "children": [_anweisung("halt()")]},
                    {"label": "gruen", "children": [_anweisung("fahr()")]},
                ],
            )
        )
    )

    assert _zeilen(ergebnis)[1:] == [
        "    if zustand == rot:",
        "        halt()",
        "    elif zustand == gruen:",
        "        fahr()",
    ]
    _pruefen(ergebnis)


def test_zaehlschleife_wird_zu_for() -> None:
    ergebnis = als_python(
        _diagramm(_block("count_loop", "i in range(3)", children=[_anweisung("blinke()")]))
    )

    assert _zeilen(ergebnis)[1:] == ["    for i in range(3):", "        blinke()"]
    _pruefen(ergebnis)


def test_kopfgesteuerte_schleife_wird_zu_while() -> None:
    ergebnis = als_python(
        _diagramm(_block("head_loop", "zaehler < 3", children=[_anweisung("blinke()")]))
    )

    assert _zeilen(ergebnis)[1:] == ["    while zaehler < 3:", "        blinke()"]
    _pruefen(ergebnis)


def test_fussgesteuerte_schleife_prueft_erst_am_ende() -> None:
    ergebnis = als_python(
        _diagramm(_block("foot_loop", "fertig", children=[_anweisung("blinke()")]))
    )

    assert _zeilen(ergebnis)[1:] == [
        "    while True:",
        "        blinke()",
        "        if fertig:",
        "            break",
    ]
    _pruefen(ergebnis)


def test_endlosschleife_wird_zu_while_true() -> None:
    """Ihr Kopftext ist nur Aufschrift und taucht im Code nicht auf."""
    ergebnis = als_python(
        _diagramm(_block("forever_loop", "endlos", children=[_anweisung("blinke()")]))
    )

    assert _zeilen(ergebnis)[1:] == ["    while True:", "        blinke()"]
    assert ergebnis.anzahl == 0
    _pruefen(ergebnis)


def test_aussprung_in_der_schleife_wird_zu_break() -> None:
    ergebnis = als_python(
        _diagramm(_block("head_loop", "True", children=[_block("jump", "Abbruch")]))
    )

    assert _zeilen(ergebnis)[1:] == ["    while True:", "        break"]
    _pruefen(ergebnis)


def test_aussprung_ausserhalb_einer_schleife_wird_zu_return() -> None:
    """`break` wäre dort zwar geparst, ließe sich aber nicht
    übersetzen – der erzeugte Code muss laufen."""
    ergebnis = als_python(_diagramm(_block("jump", "Abbruch")))

    assert _zeilen(ergebnis)[1:] == ["    return"]
    _pruefen(ergebnis)


def test_aussprung_kann_auch_weiter_oder_rueckgabe_bedeuten() -> None:
    ergebnis = als_python(
        _diagramm(
            _block(
                "head_loop",
                "True",
                children=[_block("jump", "weiter"), _block("jump", "return summe")],
            )
        )
    )

    assert "        continue" in _zeilen(ergebnis)
    assert "        return summe" in _zeilen(ergebnis)
    _pruefen(ergebnis)


def test_parallelabschnitt_laeuft_nacheinander_mit_hinweis() -> None:
    ergebnis = als_python(
        _diagramm(
            _block(
                "parallel",
                "nebenläufig",
                branches=[[_anweisung("a = 1")], [_anweisung("b = 2")]],
            )
        )
    )

    zeilen = _zeilen(ergebnis)
    assert "nebenläufig" in zeilen[1] and zeilen[1].lstrip().startswith("#")
    assert zeilen[2:] == [
        "    # Strang 1",
        "    a = 1",
        "    # Strang 2",
        "    b = 2",
    ]
    assert ergebnis.anzahl == 0
    _pruefen(ergebnis)


def test_try_block_wird_zu_try_except_finally() -> None:
    ergebnis = als_python(
        _diagramm(
            _block(
                "try",
                "ZeroDivisionError",
                children=[_anweisung("x = 1 / n")],
                catch=[_anweisung("x = 0")],
                **{"finally": [_anweisung("melde()")]},
            )
        )
    )

    assert _zeilen(ergebnis)[1:] == [
        "    try:",
        "        x = 1 / n",
        "    except ZeroDivisionError:",
        "        x = 0",
        "    finally:",
        "        melde()",
    ]
    _pruefen(ergebnis)


def test_try_block_ohne_abschluss_laesst_finally_weg() -> None:
    ergebnis = als_python(
        _diagramm(_block("try", "Exception", children=[_anweisung("x = 1")], catch=[]))
    )

    assert "finally:" not in ergebnis.text
    assert "    except Exception:" in _zeilen(ergebnis)
    _pruefen(ergebnis)


def test_unverstaendlicher_fehlertext_faengt_alles_ab() -> None:
    ergebnis = als_python(_diagramm(_block("try", "Division durch Null", catch=[])))

    assert "    except Exception:" in _zeilen(ergebnis)
    assert ergebnis.nicht_uebernommen == ["Division durch Null"]
    _pruefen(ergebnis)


# -- Verschachtelung und Einrückung --------------------------------------


def test_verschachtelung_rueckt_je_stufe_weiter_ein() -> None:
    ergebnis = als_python(
        _diagramm(
            _block(
                "head_loop",
                "läuft",
                children=[
                    _block(
                        "branch",
                        "zaehler < 3",
                        then=[_block("foot_loop", "fertig", children=[_anweisung("tick()")])],
                    )
                ],
            )
        )
    )

    assert _zeilen(ergebnis) == [
        "def ampel_zeichnen():",
        "    while läuft:",
        "        if zaehler < 3:",
        "            while True:",
        "                tick()",
        "                if fertig:",
        "                    break",
    ]
    _pruefen(ergebnis)


# -- Ausschnitt ----------------------------------------------------------


def test_ausschnitt_hat_beide_zweige_aber_keinen_funktionskopf() -> None:
    verzweigung = _block(
        "branch",
        "zaehler < 3",
        then=[_anweisung("halt()")],
        **{"else": [_anweisung("fahr()")]},
    )
    daten = _diagramm(_anweisung("zaehler = 0"), verzweigung)

    ergebnis = als_python(daten, verzweigung)

    assert _zeilen(ergebnis) == [
        "if zaehler < 3:",
        "    halt()",
        "else:",
        "    fahr()",
    ]
    assert "def " not in ergebnis.text
    assert "zaehler = 0" not in ergebnis.text
    _pruefen(ergebnis, schnipsel=True)


def test_ausschnitt_einer_schleife_nimmt_den_koerper_mit() -> None:
    schleife = _block("head_loop", "läuft", children=[_anweisung("tick()")])
    ergebnis = als_python(_diagramm(schleife), schleife)

    assert _zeilen(ergebnis) == ["while läuft:", "    tick()"]
    _pruefen(ergebnis, schnipsel=True)


def test_ausschnitt_aus_lauter_pseudocode_ist_trotzdem_gueltig() -> None:
    block = _anweisung("zustand := zustand + 1")
    ergebnis = als_python(_diagramm(block), block)

    assert _zeilen(ergebnis) == ["# zustand := zustand + 1", "pass"]
    _pruefen(ergebnis, schnipsel=True)


# -- Pseudocode ----------------------------------------------------------


def test_pseudocode_wird_kommentar_und_gezaehlt() -> None:
    ergebnis = als_python(
        _diagramm(
            _anweisung("zustand := zustand + 1"),
            _anweisung("ausgabe := 'rot'"),
            _anweisung("x = 1"),
        )
    )

    assert "    # zustand := zustand + 1" in _zeilen(ergebnis)
    assert ergebnis.nicht_uebernommen == [
        "zustand := zustand + 1",
        "ausgabe := 'rot'",
    ]
    assert ergebnis.meldung() == "2 Zeilen konnten nicht übernommen werden."
    _pruefen(ergebnis)


def test_eine_einzelne_zeile_wird_im_singular_gemeldet() -> None:
    ergebnis = als_python(_diagramm(_anweisung("zustand := 1")))

    assert ergebnis.meldung() == "1 Zeile konnte nicht übernommen werden."


def test_ohne_pseudocode_gibt_es_nichts_zu_melden() -> None:
    assert als_python(_diagramm(_anweisung("x = 1"))).meldung() == ""


def test_bedingung_in_pseudocode_wird_zum_platzhalter() -> None:
    """Der Kommentar steht über dem Kopf, damit zu sehen ist, was dort
    hingehört – und der Platzhalter verhindert, dass der Zweig
    stillschweigend genommen wird."""
    ergebnis = als_python(
        _diagramm(_block("branch", "Ampel ist rot?", then=[_anweisung("halt()")]))
    )

    assert _zeilen(ergebnis)[1:3] == ["    # Ampel ist rot?", "    if False:"]
    assert ergebnis.anzahl == 1
    _pruefen(ergebnis)


def test_zaehlschleife_in_pseudocode_laeuft_lieber_gar_nicht() -> None:
    ergebnis = als_python(
        _diagramm(_block("count_loop", "für i von 1 bis n", children=[_anweisung("tick()")]))
    )

    assert _zeilen(ergebnis)[1:] == [
        "    # für i von 1 bis n",
        "    for _ in range(0):",
        "        tick()",
    ]
    assert ergebnis.anzahl == 1
    _pruefen(ergebnis)


def test_fussschleife_in_pseudocode_bricht_lieber_ab_als_ewig_zu_laufen() -> None:
    ergebnis = als_python(
        _diagramm(
            _block("foot_loop", "wiederhole bis Bedingung", children=[_anweisung("tick()")])
        )
    )

    assert "        if True:" in _zeilen(ergebnis)
    _pruefen(ergebnis)


# -- Leere Zweige --------------------------------------------------------


def test_leerer_zweig_ergibt_pass() -> None:
    ergebnis = als_python(
        _diagramm(_block("branch", "zaehler < 3", then=[], **{"else": [_anweisung("halt()")]}))
    )

    assert _zeilen(ergebnis)[1:] == [
        "    if zaehler < 3:",
        "        pass",
        "    else:",
        "        halt()",
    ]
    _pruefen(ergebnis)


def test_leerer_schleifenkoerper_ergibt_pass() -> None:
    ergebnis = als_python(_diagramm(_block("head_loop", "läuft", children=[])))

    assert _zeilen(ergebnis)[1:] == ["    while läuft:", "        pass"]
    _pruefen(ergebnis)


def test_zweig_aus_lauter_pseudocode_bekommt_auch_ein_pass() -> None:
    ergebnis = als_python(
        _diagramm(_block("branch", "zaehler < 3", then=[_anweisung("zustand := 1")]))
    )

    assert _zeilen(ergebnis)[1:] == [
        "    if zaehler < 3:",
        "        # zustand := 1",
        "        pass",
    ]
    _pruefen(ergebnis)


# -- Gültigkeit ----------------------------------------------------------


@pytest.mark.parametrize("art", sorted(set(BLOCK_BESCHRIFTUNGEN) - {"sequence"}))
def test_frisch_angelegter_block_ergibt_gueltiges_python(art: str) -> None:
    """Auch mit den Standardtexten aus der Palette – das ist der
    Zustand, den jemand als Erstes vor sich hat."""
    daten = _diagramm()
    daten["root"]["children"].append(neuer_block(daten, art))

    ganzes = als_python(daten)
    ausschnitt = als_python(daten, daten["root"]["children"][0])

    _pruefen(ganzes)
    _pruefen(ausschnitt, schnipsel=True)


def test_ampel_struktogramm_ergibt_gueltiges_python() -> None:
    """Das vollständige Beispiel aus M9: alle Blockarten in einem
    Struktogramm."""
    daten = _diagramm(
        _anweisung("zaehler = 0"),
        _block(
            "forever_loop",
            "endlos",
            children=[
                _block(
                    "multi_branch",
                    "zaehler % 3",
                    cases=[
                        {"label": "0", "children": [_anweisung("rot()")]},
                        {"label": "1", "children": [_anweisung("gelb()")]},
                        {"label": "sonst", "children": [_anweisung("gruen()")]},
                    ],
                ),
                _block(
                    "try",
                    "Exception",
                    children=[_anweisung("warte(1)")],
                    catch=[_block("jump", "Abbruch")],
                ),
                _block(
                    "parallel",
                    "nebenläufig",
                    branches=[[_anweisung("blinke()")], [_anweisung("summe = 0")]],
                ),
                _block(
                    "branch",
                    "zaehler > 10",
                    then=[_block("jump", "Abbruch")],
                    **{"else": [_anweisung("zaehler = zaehler + 1")]},
                ),
            ],
        ),
        _block("count_loop", "i in range(3)", children=[_block("call", "piep()")]),
    )

    ergebnis = als_python(daten)

    assert ergebnis.anzahl == 0
    _pruefen(ergebnis)
