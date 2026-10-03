"""Tests für ide/diagramm/struktogramm_code.py: Struktogramm als
Python-Quelltext (M9, Schritt 14).

Reine Übersetzung ohne Qt – die Tests brauchen weder Fenster noch
Zeichenfläche. Jedes Ergebnis wird zusätzlich geparst: erzeugter Code,
der nicht läuft, wäre schlimmer als gar keiner.
"""

from __future__ import annotations

import ast
import subprocess
import sys
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
    block = _anweisung("erhöhe zustand um 1")
    ergebnis = als_python(_diagramm(block), block)

    assert _zeilen(ergebnis) == ["# erhöhe zustand um 1", "pass"]
    _pruefen(ergebnis, schnipsel=True)


# -- Pseudocode ----------------------------------------------------------


def test_pseudocode_wird_kommentar_und_gezaehlt() -> None:
    ergebnis = als_python(
        _diagramm(
            _anweisung("erhöhe zustand um 1"),
            _anweisung("setze ausgabe auf rot"),
            _anweisung("x = 1"),
        )
    )

    assert "    # erhöhe zustand um 1" in _zeilen(ergebnis)
    assert ergebnis.nicht_uebernommen == [
        "erhöhe zustand um 1",
        "setze ausgabe auf rot",
    ]
    assert ergebnis.meldung() == "2 Zeilen konnten nicht übernommen werden."
    _pruefen(ergebnis)


def test_eine_einzelne_zeile_wird_im_singular_gemeldet() -> None:
    ergebnis = als_python(_diagramm(_anweisung("setze zustand auf 1")))

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
        _diagramm(_block("branch", "zaehler < 3", then=[_anweisung("setze zustand auf 1")]))
    )

    assert _zeilen(ergebnis)[1:] == [
        "    if zaehler < 3:",
        "        # setze zustand auf 1",
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


# -- Punkt 128: Fehler, die erst beim Übersetzen auffallen ------------------


def test_break_im_anweisungsblock_ausserhalb_einer_schleife() -> None:
    """Vorher stand `break` im Funktionsrumpf: „'break' outside loop“."""
    ergebnis = als_python(_diagramm(_anweisung("x = 1"), _anweisung("break")))

    _pruefen(ergebnis)
    assert "    return" in _zeilen(ergebnis)
    assert "    break" not in _zeilen(ergebnis)


def test_break_im_anweisungsblock_in_einer_schleife_bleibt() -> None:
    ergebnis = als_python(
        _diagramm(_block("forever_loop", children=[_anweisung("break")]))
    )

    _pruefen(ergebnis)
    assert "        break" in _zeilen(ergebnis)


@pytest.mark.parametrize("text", ["await x", "nonlocal x"])
def test_nur_beim_uebersetzen_ungueltige_anweisung_wird_kommentar(
    text: str,
) -> None:
    ergebnis = als_python(_diagramm(_anweisung(text)))

    _pruefen(ergebnis)
    assert ergebnis.nicht_uebernommen == [text]
    assert f"    # {text}" in _zeilen(ergebnis)


def test_global_nach_zuweisung_wird_kommentar() -> None:
    """Jeder Block für sich ist gültig, erst zusammen scheitern sie:
    „name 'x' is assigned to before global declaration“."""
    ergebnis = als_python(
        _diagramm(
            _anweisung("x = 1"),
            _block("branch", "x > 0", then=[_anweisung("global x")]),
            _anweisung("y = 2"),
        )
    )

    _pruefen(ergebnis)
    assert ergebnis.nicht_uebernommen == ["global x"]
    zeilen = _zeilen(ergebnis)
    assert "        # global x" in zeilen
    assert "    x = 1" in zeilen and "    y = 2" in zeilen


# -- Durchsicht September 2026 (Punkte 156, 157, 177) --------------------


def test_zusaetze_aus_den_vorgabetexten_fallen_weg() -> None:
    """Punkt 156: wer dem Muster der Vorgabetexte folgt, bekam
    `if False:`, `while False:` und in der Fußschleife `if True:
    break`."""
    ergebnis = als_python(
        _diagramm(
            _block("branch", "x > 0?", then=[_anweisung("y = 1")]),
            _block(
                "head_loop", "solange x < 10", children=[_anweisung("x += 1")]
            ),
            _block(
                "foot_loop",
                "wiederhole bis x >= 20",
                children=[_anweisung("x += 1")],
            ),
        )
    )

    zeilen = [z.strip() for z in _zeilen(ergebnis)]
    assert "if x > 0:" in zeilen
    assert "while x < 10:" in zeilen
    assert zeilen[zeilen.index("if x >= 20:") + 1] == "break"
    assert ergebnis.nicht_uebernommen == []
    _pruefen(ergebnis)


def test_nur_bis_und_verneinte_zusaetze() -> None:
    """„bis“ allein zählt auch; „solange“ am Fuß und „bis“ im Kopf
    werden verneint, damit die Schleife tut, was dasteht. Der
    unveränderte Vorgabetext bleibt dagegen Platzhalter."""
    ergebnis = als_python(
        _diagramm(
            _block("foot_loop", "bis fertig", children=[_anweisung("x += 1")]),
            _block("head_loop", "bis x >= 3", children=[_anweisung("x += 1")]),
            _block(
                "foot_loop", "solange x < 5", children=[_anweisung("x += 1")]
            ),
            _block("head_loop", "solange Bedingung"),
        )
    )

    zeilen = [z.strip() for z in _zeilen(ergebnis)]
    assert "if fertig:" in zeilen
    assert "while not (x >= 3):" in zeilen
    assert "if not (x < 5):" in zeilen
    assert "while False:" in zeilen
    assert ergebnis.nicht_uebernommen == ["solange Bedingung"]
    _pruefen(ergebnis)


def test_weiter_in_der_fussschleife_prueft_die_bedingung() -> None:
    """Punkt 157: das `continue` sprang an der Abbruchbedingung vorbei,
    und die Schleife endete nie."""
    ergebnis = als_python(
        _diagramm(
            _anweisung("i = 0"),
            _block(
                "foot_loop",
                "bis i >= 3",
                children=[_anweisung("i += 1"), _block("jump", "weiter")],
            ),
            _anweisung("print(i)"),
        )
    )
    _pruefen(ergebnis)

    # In einem eigenen Prozess mit Zeitgrenze: ohne die Änderung läuft
    # die Schleife endlos.
    lauf = subprocess.run(
        [sys.executable, "-c", ergebnis.text + "\nampel_zeichnen()\n"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert lauf.stdout.strip() == "3"


def test_fallbeschriftungen_ohne_gueltiges_muster() -> None:
    """Punkt 177: `...` und `a().b` sind Ausdrücke, aber keine Muster
    für `case`; daraus wurde ein Syntaxfehler."""
    auswahl = _block(
        "multi_branch",
        "x",
        cases=[
            {"label": "...", "children": [_anweisung("y = 1")]},
            {"label": "a().b", "children": [_anweisung("y = 2")]},
            {"label": "sonst", "children": [_anweisung("y = 3")]},
        ],
    )

    ergebnis = als_python(_diagramm(auswahl))

    _pruefen(ergebnis)
    assert "match" not in ergebnis.text
    zeilen = [z.strip() for z in _zeilen(ergebnis)]
    assert "if x == ...:" in zeilen
    assert "elif x == a().b:" in zeilen


@pytest.mark.parametrize(
    ("art", "text", "erwartet"),
    [
        ("branch", "x = 0?", ["    if x == 0:", "        y = 1"]),
        ("branch", "x = 0", ["    if x == 0:", "        y = 1"]),
        ("head_loop", "solange x = 0", ["    while x == 0:", "        y = 1"]),
        ("head_loop", "bis x = 0", ["    while not (x == 0):", "        y = 1"]),
        (
            "foot_loop",
            "bis eingabe = 'q'",
            [
                "    while True:",
                "        y = 1",
                "        if eingabe == 'q':",
                "            break",
            ],
        ),
    ],
)
def test_einfaches_gleichheitszeichen_wird_zur_bedingung(
    art: str, text: str, erwartet: list[str]
) -> None:
    """Punkt 212: `x = 0` wird auch in Verzweigung und Schleife zu
    `x == 0`, nicht nur in der Mehrfachauswahl."""
    kinder = [_anweisung("y = 1")]
    if art == "branch":
        block = _block(art, text, then=kinder)
    else:
        block = _block(art, text, children=kinder)

    ergebnis = als_python(_diagramm(block))

    assert _zeilen(ergebnis)[1:] == erwartet
    assert ergebnis.nicht_uebernommen == []
    _pruefen(ergebnis)


def _ausfuehren(ergebnis: Ergebnis, **werte: object) -> list:
    """Führt die erzeugte Funktion aus. Die Kinder der Tests schreiben
    mit `spur.append(…)` mit, welcher Zweig gelaufen ist."""
    spur: list = []
    namensraum: dict = {"spur": spur, **werte}
    exec(compile(ergebnis.text, "<struktogramm>", "exec"), namensraum)
    namensraum["ampel_zeichnen"]()
    return spur


def _auswahl_mit_faellen(*etiketten: str) -> dict:
    return _block(
        "multi_branch",
        "x",
        cases=[
            {"label": e, "children": [_anweisung(f"spur.append({e!r})")]}
            for e in etiketten
        ],
    )


@pytest.mark.parametrize(
    ("etiketten", "kopf", "anderer_wert", "anderer_zweig"),
    [
        (("1, 2", "3", "sonst"), "        case 1 | 2:", 4, "sonst"),
        (("1, 2", "< 5", "sonst"), "    if x in (1, 2):", 3, "< 5"),
    ],
)
def test_ein_fall_mit_mehreren_werten_trifft_jeden_davon(
    etiketten: tuple[str, ...],
    kopf: str,
    anderer_wert: int,
    anderer_zweig: str,
) -> None:
    """Punkt 282: „1, 2“ wurde im `match` zu `case 1, 2:`, einem
    Sequenzmuster, und `x = 1` lief in den „sonst“-Fall. In der Kette
    aus `if`/`elif` entstand `if x == 1, 2:`, und das ließ sich nicht
    übersetzen."""
    ergebnis = als_python(_diagramm(_auswahl_mit_faellen(*etiketten)))

    assert kopf in _zeilen(ergebnis)
    _pruefen(ergebnis)
    assert _ausfuehren(ergebnis, x=1) == ["1, 2"]
    assert _ausfuehren(ergebnis, x=2) == ["1, 2"]
    assert _ausfuehren(ergebnis, x=anderer_wert) == [anderer_zweig]


_BIS_ZEHN = list(range(1, 11))


@pytest.mark.parametrize(
    ("text", "kopf", "erwartet"),
    [
        ("für i von 1 bis 10", "for i in range(1, 10 + 1):", _BIS_ZEHN),
        ("Für i von 1 bis 10", "for i in range(1, 10 + 1):", _BIS_ZEHN),
        ("i von a bis b", "for i in range(a, b + 1):", [2, 3, 4]),
        ("für i = 1 bis 10", "for i in range(1, 10 + 1):", _BIS_ZEHN),
        (
            "für i von 1 bis 10 Schrittweite 3",
            "for i in range(1, 10 + 1, 3):",
            [1, 4, 7, 10],
        ),
        (
            "für i von 5 bis 1 Schrittweite -2",
            "for i in range(5, 1 - 1, -2):",
            [5, 3, 1],
        ),
        ("für i in range(1, 11)", "for i in range(1, 11):", _BIS_ZEHN),
        ("for i in range(1, 11)", "for i in range(1, 11):", _BIS_ZEHN),
        ("i in range(1, 11)", "for i in range(1, 11):", _BIS_ZEHN),
    ],
)
def test_zaehlschleife_in_ueblicher_schreibweise_laeuft(
    text: str, kopf: str, erwartet: list[int]
) -> None:
    """Punkt 284: wer der Vorgabe „für i von 1 bis n“ folgte, bekam
    `for _ in range(0):`, und der Rumpf lief nie."""
    ergebnis = als_python(
        _diagramm(
            _block(
                "count_loop", text, children=[_anweisung("spur.append(i)")]
            )
        )
    )

    assert _zeilen(ergebnis)[1] == f"    {kopf}"
    assert ergebnis.nicht_uebernommen == []
    _pruefen(ergebnis)
    assert _ausfuehren(ergebnis, a=2, b=4) == erwartet


@pytest.mark.parametrize("kopf", ["für jedes x in liste", "für jeden x in liste", "for x in liste"])
def test_fuer_jedes_wird_zu_einer_schleife_ueber_die_liste(kopf: str) -> None:
    """„für jedes x in liste“ fiel auf den Platzhalter `range(0)`
    zurück: der Rumpf lief nie."""
    ergebnis = als_python(
        _diagramm(_block("count_loop", kopf, children=[_anweisung("print(x)")]))
    )

    assert _zeilen(ergebnis)[1:] == ["    for x in liste:", "        print(x)"]
    _pruefen(ergebnis)


def test_eingabe_und_ausgabe_werden_uebersetzt_und_annotationen_verworfen() -> None:
    """„Eingabe: zahl“ und „Ausgabe: zahl“ sind für Python gültige
    Annotationen ohne Wert. Sie standen wörtlich im Code und bewirkten
    nichts; die Schleife lief dann endlos."""
    ergebnis = als_python(
        _diagramm(
            _anweisung("Eingabe: zahl"),
            _anweisung("Ausgabe: zahl"),
            _anweisung("Ergebnis: summe"),
        )
    )

    assert '    zahl = input("zahl? ")' in _zeilen(ergebnis)
    assert "    print(zahl)" in _zeilen(ergebnis)
    assert ergebnis.nicht_uebernommen == ["Ergebnis: summe"]
    _pruefen(ergebnis)


def test_zuweisung_mit_pfeil_wird_python() -> None:
    """Punkt 481: „zahl ← zahl - 1“ wurde zum Kommentar, und der
    Countdown aus Punkt 456 lief endlos. „x <- 5“ bleibt, was es in
    Python ist: ein Vergleich."""
    ergebnis = als_python(_diagramm(
        _anweisung("zahl := 3"),
        _block("head_loop", "solange zahl > 0", children=[
            _anweisung("spur.append(zahl)"),
            _anweisung("zahl ← zahl - 1"),
        ]),
        _anweisung("liste[0] ← zahl"),
    ))

    assert ergebnis.nicht_uebernommen == []
    liste = [None]
    assert _ausfuehren(ergebnis, liste=liste) == [3, 2, 1]
    assert liste == [0]


def test_zaehlschleife_von_groesser_bis_kleiner_zaehlt_abwaerts() -> None:
    """Punkt 482: „für i von 3 bis 1“ ergab `range(3, 2)` und lief
    nie. „von 1 bis n“ zählt weiter aufwärts."""
    ergebnis = als_python(_diagramm(
        _block("count_loop", "für i von 3 bis 1", children=[
            _anweisung("spur.append(i)"),
        ]),
        _block("count_loop", "für k von 1 bis n", children=[
            _anweisung("spur.append(k)"),
        ]),
    ))

    assert _ausfuehren(ergebnis, n=2) == [3, 2, 1, 1, 2]
