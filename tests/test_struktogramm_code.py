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
    alles auffangen – dann lieber der Vergleich. Die Namen bekommen
    hier einen Wert; ohne ihn gelten sie als Text (Punkt 602)."""
    ergebnis = als_python(
        _diagramm(
            _anweisung("rot = 1"),
            _anweisung("gruen = 2"),
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
        "    rot = 1",
        "    gruen = 2",
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
    assert ergebnis.meldung() == (
        "2 Zeilen konnten nicht übernommen werden und stehen als Kommentar im Code."
    )
    _pruefen(ergebnis)


def test_eine_einzelne_zeile_wird_im_singular_gemeldet() -> None:
    ergebnis = als_python(_diagramm(_anweisung("setze zustand auf 1")))

    assert ergebnis.meldung() == (
        "1 Zeile konnte nicht übernommen werden und steht als Kommentar im Code."
    )


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

    assert '    zahl = eingabe_lesen("zahl? ")' in _zeilen(ergebnis)
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


def test_eine_eingabe_die_wie_eine_zahl_benutzt_wird_wird_zur_zahl(
    monkeypatch,
) -> None:  # noqa: ANN001
    """Punkt 579: aus „Eingabe: zahl“ und „zahl > 0?“ entstand Code, der
    beim Vergleich mit TypeError abbrach. Ein Name, der nur als Text
    benutzt wird, bleibt Text."""
    import builtins

    daten = {"name": "probe", "root": {"kind": "sequence", "children": [
        {"kind": "statement", "text": "Eingabe: zahl"},
        {"kind": "statement", "text": "Eingabe: name"},
        {"kind": "branch", "text": "zahl > 0?", "then": [
            {"kind": "statement", "text": 'ergebnis = name + "!"'},
        ], "else": []},
    ]}}
    code = als_python(daten).text
    antworten = iter(["2,5", "Anna"])
    monkeypatch.setattr(builtins, "input", lambda _frage="": next(antworten))
    raum: dict = {}
    exec(code + "\nprobe()\n", raum)

    assert 'name = eingabe_lesen("name? ")' in code
    assert 'zahl = eingabe_lesen("zahl? ")' in code


def test_zaehlschleife_abwaerts_mit_geklammerter_schrittweite() -> None:
    """Punkt 581: „schrittweite (-1)“ lief nur bis 3."""
    ergebnis = als_python(_diagramm(_block(
        "count_loop", "für i von 10 bis 1 schrittweite (-1)",
        children=[_anweisung("spur.append(i)")],
    )))
    assert _ausfuehren(ergebnis) == list(range(10, 0, -1))


def test_vorgabe_zaehlschleife_mit_eingelesenem_n(monkeypatch) -> None:  # noqa: ANN001
    """Punkt 581: „Eingabe: n“ und „für i von 1 bis n“ ergaben
    `range(0)`."""
    import builtins

    ergebnis = als_python(_diagramm(
        _anweisung("Eingabe: n"),
        _block("count_loop", "für i von 1 bis n", children=[_anweisung("spur.append(i)")]),
    ))
    monkeypatch.setattr(builtins, "input", lambda _frage="": "3")
    assert _ausfuehren(ergebnis) == [1, 2, 3]
    assert ergebnis.anzahl == 0


@pytest.mark.parametrize(
    ("etiketten", "x", "erwartet"),
    [
        (["< 0", "= 0", "> 0"], 0, "b"),
        (["1", "sonst", "2"], 2, "c"),
        (["1", "sonst", "2"], 7, "b"),
        (["1", "2", "else"], 9, "c"),
    ],
)
def test_mehrfachauswahl_randfaelle(etiketten: list, x: int, erwartet: str) -> None:
    """Punkt 581: „= 0“ ging verloren, „sonst“ in der Mitte ergab
    `x == sonst`, ein letzter Fall „else“ `elif False`."""
    faelle = [
        {"label": etikett, "children": [_anweisung(f"spur.append({buchstabe!r})")]}
        for etikett, buchstabe in zip(etiketten, "abc", strict=True)
    ]
    ergebnis = als_python(_diagramm(_block("multi_branch", "x", cases=faelle)))
    _pruefen(ergebnis)
    assert _ausfuehren(ergebnis, x=x) == [erwartet]


def _mit_eingaben(monkeypatch, *antworten: str) -> None:  # noqa: ANN001
    import builtins

    folge = iter(antworten)
    monkeypatch.setattr(builtins, "input", lambda _frage="": next(folge))


def _zweig(bedingung: str) -> dict:
    return _block(
        "branch", bedingung,
        then=[_anweisung("spur.append('ja')")],
        **{"else": [_anweisung("spur.append('nein')")]},
    )


@pytest.mark.parametrize(
    ("bloecke", "antworten", "erwartet"),
    [
        # `!=` und ein einzelnes `=` vergleichen mit einer Zahl.
        ([_anweisung("Eingabe: z"), _zweig("z != 0?")], ["0"], ["nein"]),
        ([_anweisung("Eingabe: z"), _zweig("z = 0?")], ["0"], ["ja"]),
        # Fallauswahl mit Zahlen, das Beispiel aus dem Handbuch.
        (
            [
                _anweisung("Eingabe: note"),
                _block("case_of", "note", cases=[
                    {"label": "1", "children": [_anweisung("spur.append('sehr gut')")]},
                    {"label": "2", "children": [_anweisung("spur.append('gut')")]},
                    {"label": "sonst", "children": [_anweisung("spur.append('sonst')")]},
                ]),
            ],
            ["1"],
            ["sehr gut"],
        ),
        # Eine Summe in einer Schleife.
        (
            [
                _anweisung("summe ← 0"),
                _block("count_loop", "für i von 1 bis 2", children=[
                    _anweisung("Eingabe: zahl"),
                    _anweisung("summe ← summe + zahl"),
                ]),
                _anweisung("spur.append(summe)"),
            ],
            ["3", "4,5"],
            [7.5],
        ),
        # Zwei Eingaben addiert, ohne Text in Anführungszeichen.
        (
            [_anweisung("Eingabe: a"), _anweisung("Eingabe: b"),
             _anweisung("spur.append(a + b)")],
            ["3", "5"],
            [8.0],
        ),
    ],
    ids=["ungleich", "gleich", "fallauswahl", "summe", "a_plus_b"],
)
def test_eingaben_werden_zahlen_wo_sie_wie_zahlen_benutzt_werden(
    monkeypatch, bloecke: list, antworten: list, erwartet: list  # noqa: ANN001
) -> None:
    """Punkt 601: bei `!=`, `=`, einer Fallauswahl und `+` blieb die
    Eingabe Text."""
    _mit_eingaben(monkeypatch, *antworten)
    ergebnis = als_python(_diagramm(*bloecke))

    assert _ausfuehren(ergebnis) == erwartet
    assert ergebnis.anzahl == 0


def test_ein_text_mit_plus_bleibt_text(monkeypatch) -> None:  # noqa: ANN001
    """Punkt 601: „"Hallo " + name“ verbindet Texte und macht `name`
    nicht zur Zahl."""
    _mit_eingaben(monkeypatch, "Anna")
    ergebnis = als_python(_diagramm(
        _anweisung("Eingabe: name"), _anweisung('spur.append("Hallo " + name)')
    ))

    assert _ausfuehren(ergebnis) == ["Hallo Anna"]


@pytest.mark.parametrize(
    ("text", "art"),
    [
        ("Anweisung", "statement"),
        ("Initialisierung", "statement"),
        ("Unterprogramm()", "call"),
        ("Ende (Abbruch)", "jump"),
    ],
)
def test_pseudocode_der_zufaellig_python_ist_wird_kommentar(text: str, art: str) -> None:
    """Punkt 602: diese Zeilen nahm Python an, beim Lauf kam
    `NameError`, und gezählt wurde nichts."""
    ergebnis = als_python(_diagramm(_block(art, text)))

    assert ergebnis.nicht_uebernommen == [text]
    _ausfuehren(ergebnis)


def test_wahr_falsch_und_texte_als_faelle(monkeypatch) -> None:  # noqa: ANN001
    """Punkt 602: „fertig ← falsch“ ergab `fertig = falsch`, die Fälle
    „rot“ und „grün“ `farbe == rot`."""
    _mit_eingaben(monkeypatch, "grün")
    ergebnis = als_python(_diagramm(
        _anweisung("fertig ← falsch"),
        _anweisung("Eingabe: farbe"),
        _block("case_of", "farbe", cases=[
            {"label": "rot", "children": [_anweisung("spur.append(fertig)")]},
            {"label": "grün", "children": [_anweisung("spur.append(not fertig)")]},
        ]),
    ))

    assert _ausfuehren(ergebnis) == [True]
    assert ergebnis.anzahl == 0


def test_beispiel_konto_abheben_laeuft_ohne_name_error() -> None:
    """Punkt 602: der Aussprung „Ende (Abbruch)“ im Beispiel 06 wurde
    zum Aufruf einer Funktion `Ende`."""
    import json
    from pathlib import Path

    pfad = (
        Path(__file__).parent.parent
        / "beispielprojekte" / "06_Kontoverwaltung" / "diagramme"
        / "konto_abheben.pdiag"
    )
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    ergebnis = als_python(daten)

    code_zeilen = [z.strip() for z in ergebnis.text.splitlines()]
    assert "Ende (Abbruch)" not in code_zeilen
    assert ergebnis.nicht_uebernommen.count("Ende (Abbruch)") == 2
    _pruefen(ergebnis)


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("Eingabe: a\nEingabe: b", ['a = eingabe_lesen("a? ")', 'b = eingabe_lesen("b? ")']),
        ("x ← 1\ny ← 2", ["x = 1", "y = 2"]),
        ("x = 1\ny ← 2", ["x = 1", "y = 2"]),
    ],
)
def test_mehrzeilige_bloecke_werden_zeilenweise_uebersetzt(
    text: str, code: list
) -> None:
    """Punkt 603: Ein-/Ausgabe und Pfeil-Zuweisung galten nur in
    einzeiligen Blöcken."""
    ergebnis = als_python(_diagramm(_anweisung(text)))

    zeilen = _zeilen(ergebnis)
    # Vor dem Unterprogramm steht bei einer Eingabe `eingabe_lesen`.
    anfang = zeilen.index("def ampel_zeichnen():")
    assert zeilen[anfang + 1:] == [f"    {z}" for z in code]
    assert ergebnis.anzahl == 0


@pytest.mark.parametrize(
    ("kopf", "erwartet"),
    [
        ("für i von 1 bis 10, Schrittweite 2", [1, 3, 5, 7, 9]),
        ("für i von 0,5 bis 2", None),
        ("für i von 1 bis 2,5", None),
        ("i von 1 bis 10 schritt 0,5", None),
    ],
)
def test_komma_in_der_zaehlschleife(kopf: str, erwartet: list | None) -> None:
    """Punkt 604: ein Komma vor „Schrittweite“ ergab ein Tupel als
    Grenze, ein Dezimalkomma einen falschen Bereich oder `TypeError`.
    Was `range` nicht zählen kann, wird Kommentar und gezählt."""
    ergebnis = als_python(_diagramm(
        _block("count_loop", kopf, children=[_anweisung("spur.append(i)")])
    ))

    if erwartet is None:
        assert ergebnis.nicht_uebernommen == [kopf]
        assert _ausfuehren(ergebnis) == []
    else:
        assert _ausfuehren(ergebnis) == erwartet
        assert ergebnis.anzahl == 0


def _programm_mit_eingaben(monkeypatch, ergebnis: Ergebnis, *eingaben: str) -> list:  # noqa: ANN001
    """Führt das erzeugte Programm mit diesen Eingaben aus."""
    import builtins

    rest = iter(eingaben)
    monkeypatch.setattr(builtins, "input", lambda _frage="": next(rest))
    return _ausfuehren(ergebnis)


@pytest.mark.parametrize("schleife", [True, False], ids=["solange", "verzweigung"])
def test_zahlenraten_vergleicht_mit_einem_namen_der_eine_zahl_ist(
    monkeypatch, schleife: bool
) -> None:  # noqa: ANN001
    """Punkt 622: „tipp != geheim“ mit „geheim ← 42“ verglich Text mit
    einer Zahl, und die Schleife endete auch bei 42 nie."""
    if schleife:
        ergebnis = als_python(_diagramm(
            _anweisung("geheim ← 42"),
            _anweisung("Eingabe: tipp"),
            _block("head_loop", "solange tipp != geheim", children=[
                _anweisung("spur.append('falsch')"),
                _anweisung("Eingabe: tipp"),
            ]),
            _anweisung("spur.append('richtig')"),
        ))
        assert _programm_mit_eingaben(monkeypatch, ergebnis, "10", "42") == ["falsch", "richtig"]
    else:
        ergebnis = als_python(_diagramm(
            _anweisung("geheim ← randint(1, 1)"),
            _anweisung("Eingabe: tipp"),
            _block("branch", "tipp == geheim?",
                   then=[_anweisung("spur.append('richtig')")],
                   **{"else": [_anweisung("spur.append('falsch')")]}),
        ))
        from random import randint

        assert 'tipp = eingabe_lesen("tipp? ")' in ergebnis.text
        spur = []
        import builtins

        monkeypatch.setattr(builtins, "input", lambda _frage="": "1")
        raum = {"spur": spur, "randint": randint}
        exec(ergebnis.text, raum)
        raum["ampel_zeichnen"]()
        assert spur == ["richtig"]


@pytest.mark.parametrize(
    ("eingabe", "erwartet"), [("-3", "negativ"), ("0", "null"), ("2,5", "positiv")]
)
def test_fallauswahl_mit_vergleichen_macht_den_kopf_zur_zahl(
    monkeypatch, eingabe: str, erwartet: str
) -> None:  # noqa: ANN001
    """Punkt 626: Fälle wie „< 0“ ließen die Eingabe Text, der Lauf
    endete mit einem TypeError."""
    ergebnis = als_python(_diagramm(
        _anweisung("Eingabe: x"),
        _block("multi_branch", "x", cases=[
            {"label": "< 0", "children": [_anweisung("spur.append('negativ')")]},
            {"label": "= 0", "children": [_anweisung("spur.append('null')")]},
            {"label": "sonst", "children": [_anweisung("spur.append('positiv')")]},
        ]),
    ))
    assert _programm_mit_eingaben(monkeypatch, ergebnis, eingabe) == [erwartet]


def test_fussschleife_mit_bis_bleibt_kommazahl(monkeypatch) -> None:  # noqa: ANN001
    """Punkt 627: „wiederhole bis betrag > 0“ ergab `int(input(…))`,
    und „2,5“ endete mit einem ValueError."""
    ergebnis = als_python(_diagramm(
        _block("foot_loop", "wiederhole bis betrag > 0", children=[
            _anweisung("Eingabe: betrag"),
        ]),
        _anweisung("spur.append(betrag)"),
    ))
    assert "int(input" not in ergebnis.text
    assert _programm_mit_eingaben(monkeypatch, ergebnis, "-1", "2,5") == [2.5]


@pytest.mark.parametrize(
    "block",
    [
        _block("branch", "x > 0 # positiv", then=[_anweisung("pass")]),
        _block("head_loop", "solange x > 5 # zu groß", children=[_anweisung("x = x - 1")]),
        _block("foot_loop", "wiederhole bis x < 3 # klein", children=[_anweisung("x = x - 1")]),
        _block("multi_branch", "x", cases=[
            {"label": "1 # eins", "children": [_anweisung("pass")]},
            {"label": "sonst", "children": [_anweisung("pass")]},
        ]),
    ],
    ids=["verzweigung", "kopfschleife", "fussschleife", "fallauswahl"],
)
def test_ein_kommentar_im_kopf_ergibt_gueltigen_code(block: dict) -> None:
    """Punkt 636: aus „x > 0 # positiv“ wurde `if x > 0 # positiv:`."""
    ergebnis = als_python(_diagramm(_anweisung("x = 9"), block))
    _pruefen(ergebnis)
    assert ergebnis.anzahl == 0
    _ausfuehren(ergebnis)


def _verzweigung(bedingung: str, ja: str, nein: str) -> dict:
    return _block(
        "branch", bedingung,
        then=[_anweisung(f"spur.append({ja!r})")],
        **{"else": [_anweisung(f"spur.append({nein!r})")]},
    )


@pytest.mark.parametrize(
    ("bloecke", "eingaben", "erwartet"),
    [
        ([_anweisung("Eingabe: x"), _verzweigung("x > 2,5?", "gross", "klein")],
         ["3"], ["gross"]),
        ([_anweisung("Eingabe: x"),
          _block("head_loop", "solange x < 1,5", children=[_anweisung("x ← x + 1")]),
          _anweisung("spur.append(x)")],
         ["0"], [2]),
        ([_anweisung("x ← 0"),
          _block("foot_loop", "wiederhole bis x >= 1,5", children=[_anweisung("x ← x + 1")]),
          _anweisung("spur.append(x)")],
         [], [2]),
        ([_anweisung("Eingabe: note"),
          _block("multi_branch", "note", cases=[
              {"label": "< 2,5", "children": [_anweisung("spur.append('gut')")]},
              {"label": "sonst", "children": [_anweisung("spur.append('rest')")]},
          ])],
         ["1,7"], ["gut"]),
        ([_anweisung("preis ← 2,5"), _anweisung("gesamt ← preis * 4"),
          _anweisung("spur.append(gesamt)")],
         [], [10.0]),
        ([_anweisung("Eingabe: x"),
          _block("case_of", "x", cases=[
              {"label": "2,5", "children": [_anweisung("spur.append('zweieinhalb')")]},
              {"label": "sonst", "children": [_anweisung("spur.append('anders')")]},
          ])],
         ["5"], ["anders"]),
    ],
    ids=["verzweigung", "kopfschleife", "fussschleife", "fall", "zuweisung", "fallwert"],
)
def test_kommazahlen_werden_zahlen(
    monkeypatch, bloecke: list, eingaben: list, erwartet: list
) -> None:  # noqa: ANN001
    """Punkt 637: „x > 2,5“ ergab einen Syntaxfehler, „preis ← 2,5“ ein
    Tupel und der Fall „2,5“ die Fälle 2 und 5."""
    ergebnis = als_python(_diagramm(*bloecke))
    _pruefen(ergebnis)
    assert ergebnis.anzahl == 0
    assert _programm_mit_eingaben(monkeypatch, ergebnis, *eingaben) == erwartet


@pytest.mark.parametrize(
    ("text", "erwartet"),
    [("randint(1,6)", "randint(1,6)"), ("1, 2", "1, 2"), ("1,2,3", "1,2,3"),
     ("'2,5'", "'2,5'"), ("x2,5", "x2,5"), ("2,5 * x", "2.5 * x")],
)
def test_ein_komma_als_trennzeichen_bleibt(text: str, erwartet: str) -> None:
    """Punkt 637: in Klammern, in Texten, mit Leerzeichen und in einer
    Aufzählung trennt das Komma Werte."""
    from ide.diagramm.struktogramm_code import _kommazahlen

    assert _kommazahlen(text) == erwartet


def test_raise_mit_eigener_ausnahme_bricht_ab() -> None:
    """Punkt 640: „raise NichtGenugGeld“ wurde Kommentar, und die
    Abbuchung lief weiter."""

    class NichtGenugGeld(Exception):
        pass

    ergebnis = als_python(_diagramm(
        _anweisung("stand ← 10"),
        _anweisung("betrag ← 20"),
        _block("branch", "betrag > stand?", then=[_block("jump", "raise NichtGenugGeld")]),
        _anweisung("spur.append('abgebucht')"),
    ))

    assert "raise NichtGenugGeld" in ergebnis.text
    assert ergebnis.anzahl == 0
    with pytest.raises(NichtGenugGeld):
        _ausfuehren(ergebnis, NichtGenugGeld=NichtGenugGeld)


@pytest.mark.parametrize(
    "bloecke",
    [
        [_anweisung("name ← 'Ada Lovelace'"),
         _anweisung("Vorname, Nachname = name.split()"),
         _anweisung("spur.append(Nachname)")],
        [_anweisung("paare ← [('Ada', 'Lovelace')]"),
         _block("count_loop", "für Vorname, Nachname in paare",
                children=[_anweisung("spur.append(Nachname)")])],
    ],
    ids=["zuweisung", "schleife"],
)
def test_alle_ziele_einer_tupel_zuweisung_haben_einen_wert(bloecke: list) -> None:
    """Punkt 640: nur der erste Name einer Tupel-Zuweisung zählte, und
    „Nachname“ wurde Kommentar."""
    ergebnis = als_python(_diagramm(*bloecke))

    assert ergebnis.anzahl == 0
    assert _ausfuehren(ergebnis) == ["Lovelace"]


@pytest.mark.parametrize(
    "bloecke",
    [
        [_anweisung("fertig ← wahr"),
         _block("case_of", "fertig", cases=[
             {"label": "wahr", "children": [_anweisung("spur.append('ja')")]},
             {"label": "falsch", "children": [_anweisung("spur.append('nein')")]},
         ])],
        [_anweisung("fertig ← wahr"),
         _block("multi_branch", "", cases=[
             {"label": "fertig = wahr", "children": [_anweisung("spur.append('ja')")]},
             {"label": "sonst", "children": [_anweisung("spur.append('nein')")]},
         ])],
        [_anweisung("fertig ← falsch"),
         _anweisung("n ← 0"),
         _block("foot_loop", "wiederhole bis fertig = wahr", children=[
             _anweisung("n ← n + 1"),
             _block("branch", "n >= 2?", then=[_anweisung("fertig ← wahr")]),
             _block("jump", "weiter"),
         ]),
         _anweisung("spur.append('ja')")],
    ],
    ids=["fallauswahl", "mehrfachauswahl", "fussschleife"],
)
def test_wahr_und_falsch_ueberall(bloecke: list) -> None:
    """Punkt 641: „wahr“ als Fall wurde der Text 'wahr', in der
    Mehrfachauswahl und vor dem `continue` der Fußschleife blieb es ein
    Name."""
    ergebnis = als_python(_diagramm(*bloecke))
    code = "\n".join(
        z for z in ergebnis.text.splitlines() if not z.strip().startswith("#")
    )

    assert "wahr" not in code
    assert _ausfuehren(ergebnis) == ["ja"]


@pytest.mark.parametrize(("eingabe", "erwartet"), [("J", "ja"), ("N", "nein"), ("x", "?")])
def test_faelle_j_und_n_sind_texte(monkeypatch, eingabe: str, erwartet: str) -> None:  # noqa: ANN001
    """Punkt 642: der Fall „J“ ergab `antwort == J` und `NameError`."""
    ergebnis = als_python(_diagramm(
        _anweisung("Eingabe: antwort"),
        _block("multi_branch", "antwort", cases=[
            {"label": "J", "children": [_anweisung("spur.append('ja')")]},
            {"label": "N", "children": [_anweisung("spur.append('nein')")]},
            {"label": "sonst", "children": [_anweisung("spur.append('?')")]},
        ]),
    ))
    assert _programm_mit_eingaben(monkeypatch, ergebnis, eingabe) == [erwartet]


@pytest.mark.parametrize(
    ("bloecke", "eingaben", "erwartet"),
    [
        ([_anweisung("liste ← ['a', 'b', 'c']"), _anweisung("Eingabe: i"),
          _block("branch", "i < 3?", then=[_anweisung("spur.append(liste[i])")])],
         ["1"], ["b"]),
        ([_anweisung("Eingabe: a"), _anweisung("Eingabe: b"),
          _anweisung("spur.append(str(a + b))")],
         ["3", "5"], ["8"]),
        ([_anweisung("Eingabe: a"), _anweisung("Eingabe: b"),
          _anweisung("spur.append(a + b)")],
         ["2,5", "5"], [7.5]),
        ([_anweisung("Eingabe: n"),
          _block("head_loop", "solange n > 0", children=[
              _anweisung("spur.append(str(n))"), _anweisung("n ← n - 1")])],
         ["3"], ["3", "2", "1"]),
    ],
    ids=["listenindex", "summe", "kommazahl", "countdown"],
)
def test_ganze_zahlen_bleiben_ganz(
    monkeypatch, bloecke: list, eingaben: list, erwartet: list
) -> None:  # noqa: ANN001
    """Punkt 643: jede eingegebene Zahl wurde `float`; ein Listenindex
    endete mit TypeError, 3 + 5 ergab „8.0“."""
    ergebnis = als_python(_diagramm(*bloecke))

    assert ergebnis.text.startswith("def eingabe_lesen(frage):")
    _pruefen(ergebnis)
    assert _programm_mit_eingaben(monkeypatch, ergebnis, *eingaben) == erwartet


@pytest.mark.parametrize(
    ("anzahl", "satz"),
    [(1, "1 Zeile konnte nicht übernommen werden und steht als Kommentar im Code."),
     (2, "2 Zeilen konnten nicht übernommen werden und stehen als Kommentar im Code.")],
)
def test_hinweis_nach_anzahl_ohne_anrede(anzahl: int, satz: str) -> None:
    """Punkt 652: „1 Zeile … Sie stehen als Kommentar im Code“."""
    bloecke = [_anweisung(f"rechne Teil {i} aus") for i in range(anzahl)]
    assert als_python(_diagramm(*bloecke)).meldung() == satz


@pytest.mark.parametrize(
    ("bedingung", "jahr", "erwartet"),
    [
        ("jahr % 4 = 0 und jahr % 100 != 0 oder jahr % 400 = 0?", "2000", "ja"),
        ("jahr % 4 = 0 und jahr % 100 != 0 oder jahr % 400 = 0?", "1900", "nein"),
        ("jahr % 4 = 0 und jahr % 100 != 0 oder jahr % 400 = 0?", "2024", "ja"),
        ("jahr > 0 UND jahr < 10", "5", "ja"),
        ("nicht (jahr > 10)", "11", "nein"),
    ],
)
def test_und_oder_nicht_in_bedingungen(
    bedingung: str, jahr: str, erwartet: str, monkeypatch
) -> None:  # noqa: ANN001
    """Punkt 655: „und“, „oder“ und „nicht“ ergaben `if False:`; das
    Schaltjahr nahm immer den Nein-Zweig."""
    import builtins

    ergebnis = als_python(_diagramm(
        _anweisung("Eingabe: jahr"),
        _block("branch", bedingung,
               then=[_anweisung('spur.append("ja")')],
               **{"else": [_anweisung('spur.append("nein")')]}),
    ))
    monkeypatch.setattr(builtins, "input", lambda _frage="": jahr)

    assert ergebnis.anzahl == 0
    assert _ausfuehren(ergebnis) == [erwartet]


def test_und_in_einem_text_bleibt() -> None:
    """Wörter in Anführungszeichen bleiben, wie sie sind."""
    ergebnis = als_python(_diagramm(
        _anweisung('name ← "Tom und Jerry"'),
        _block("branch", 'name == "Tom und Jerry"',
               then=[_anweisung('spur.append("ja")')]),
    ))
    assert 'if name == "Tom und Jerry":' in ergebnis.text
    assert _ausfuehren(ergebnis) == ["ja"]


def test_eine_eingabe_als_listenindex_wird_zahl(monkeypatch) -> None:  # noqa: ANN001
    """Punkt 656: „Eingabe: i“ und „liste[i]“ endeten mit TypeError."""
    import builtins

    ergebnis = als_python(_diagramm(
        _anweisung("Eingabe: i"),
        _anweisung("liste ← [1, 2, 3]"),
        _anweisung("spur.append(liste[i])"),
    ))
    monkeypatch.setattr(builtins, "input", lambda _frage="": "1")

    assert _ausfuehren(ergebnis) == [2]


def test_ein_text_als_schluessel_eines_woerterbuchs_bleibt_text(monkeypatch) -> None:  # noqa: ANN001
    """Ein Wörterbuch mit Texten als Schlüsseln liest den Namen weiter
    als Text."""
    import builtins

    ergebnis = als_python(_diagramm(
        _anweisung("Eingabe: name"),
        _anweisung('telefon ← {"Anna": 123}'),
        _anweisung("spur.append(telefon[name])"),
    ))
    monkeypatch.setattr(builtins, "input", lambda _frage="": "Anna")

    assert _ausfuehren(ergebnis) == [123]


def _mit_eingaben(monkeypatch, *eingaben: str) -> None:  # noqa: ANN001
    import builtins

    folge = iter(eingaben)
    monkeypatch.setattr(builtins, "input", lambda _frage="": next(folge))


@pytest.mark.parametrize(
    ("eingabe", "erwartet"),
    [("nicht bestanden", ["B"]), ("bestanden", ["A"]), ("krank", ["C"])],
)
def test_fall_aus_woertern_ohne_wert_ist_ein_text(
    monkeypatch, eingabe: str, erwartet: list
) -> None:  # noqa: ANN001
    """Punkt 658: aus dem Fall „nicht bestanden“ wurde `not bestanden`,
    und die Eingabe „nicht bestanden“ endete mit NameError."""
    ergebnis = als_python(_diagramm(
        _anweisung("Eingabe: status"),
        _block("case_of", "status", cases=[
            {"label": "bestanden", "children": [_anweisung("spur.append('A')")]},
            {"label": "nicht bestanden", "children": [_anweisung("spur.append('B')")]},
            {"label": "sonst", "children": [_anweisung("spur.append('C')")]},
        ]),
    ))
    _mit_eingaben(monkeypatch, eingabe)

    assert _ausfuehren(ergebnis) == erwartet
    assert ergebnis.anzahl == 0


@pytest.mark.parametrize(
    ("bloecke", "eingaben", "gezaehlt", "erwartet"),
    [
        # Ohne Zuweisung an `fertig` ist „nicht fertig“ Pseudocode.
        ([_block("branch", "nicht fertig", then=[_anweisung("spur.append('A')")],
                 **{"else": [_anweisung("spur.append('B')")]})], [], 1, ["B"]),
        # Mit Zuweisung bleibt es `not fertig`.
        ([_anweisung("fertig ← falsch"),
          _block("branch", "nicht fertig", then=[_anweisung("spur.append('A')")],
                 **{"else": [_anweisung("spur.append('B')")]})], [], 0, ["A"]),
        ([_anweisung("Eingabe: x"),
          _block("branch", "x > 0 und gerade", then=[_anweisung("spur.append('A')")],
                 **{"else": [_anweisung("spur.append('B')")]})], ["4"], 1, ["B"]),
        ([_block("foot_loop", "bis nicht weiter",
                 children=[_anweisung("spur.append(1)")])], [], 1, [1]),
    ],
    ids=["ohne_wert", "mit_wert", "und_ohne_wert", "fussschleife"],
)
def test_logikwoerter_mit_namen_ohne_wert_werden_kommentar(
    monkeypatch, bloecke: list, eingaben: list, gezaehlt: int, erwartet: list
) -> None:  # noqa: ANN001
    """Punkt 658: „nicht fertig“ und „x > 0 und gerade“ ohne Wert für
    `fertig` und `gerade` ergaben Code, der mit NameError abbrach, und
    über dem Code stand, alles sei übernommen."""
    ergebnis = als_python(_diagramm(*bloecke))
    _mit_eingaben(monkeypatch, *eingaben)

    assert _ausfuehren(ergebnis) == erwartet
    assert ergebnis.anzahl == gezaehlt


@pytest.mark.parametrize(
    ("bloecke", "eingaben", "erwartet"),
    [
        ([_anweisung("liste ← [3, 7, 5]"), _anweisung("Eingabe: gesucht"),
          _anweisung("stelle ← -1"),
          _block("count_loop", "für i von 0 bis 2", children=[
              _block("branch", "liste[i] = gesucht",
                     then=[_anweisung("stelle ← i")])]),
          _anweisung("spur.append(stelle)")], ["5"], [2]),
        ([_anweisung("zahlen ← [3, 7, 5]"), _anweisung("Eingabe: x"),
          _block("branch", "x in zahlen", then=[_anweisung("spur.append('drin')")],
                 **{"else": [_anweisung("spur.append('nicht drin')")]})],
         ["7"], ["drin"]),
        ([_anweisung("liste ← []"),
          _block("count_loop", "für i von 1 bis 3", children=[
              _anweisung("Eingabe: z"), _anweisung("liste.append(z)")]),
          _anweisung("maximum ← liste[0]"),
          _block("count_loop", "für i von 1 bis len(liste) - 1", children=[
              _block("branch", "liste[i] > maximum",
                     then=[_anweisung("maximum ← liste[i]")])]),
          _anweisung("spur.append(maximum)")], ["9", "10", "3"], [10]),
        ([_anweisung("liste ← []"), _anweisung("summe ← 0"),
          _block("count_loop", "für i von 1 bis 3", children=[
              _anweisung("Eingabe: z"), _anweisung("liste.append(z)")]),
          _block("count_loop", "für i von 0 bis 2", children=[
              _anweisung("summe ← summe + liste[i]")]),
          _anweisung("spur.append(summe)")], ["9", "10", "3"], [22]),
        # Eine Liste aus Texten bleibt Text.
        ([_anweisung("namen ← []"),
          _block("count_loop", "für i von 1 bis 2", children=[
              _anweisung("Eingabe: name"), _anweisung("namen.append(name)")]),
          _anweisung("spur.append(namen)")], ["Anna", "Ben"], [["Anna", "Ben"]]),
    ],
    ids=["lineare_suche", "in_liste", "maximum", "summe", "textliste"],
)
def test_eingaben_in_und_aus_zahlenlisten_sind_zahlen(
    monkeypatch, bloecke: list, eingaben: list, erwartet: list
) -> None:  # noqa: ANN001
    """Punkt 659: eine Eingabe, die mit Elementen einer Zahlenliste
    verglichen, in ihr gesucht oder in sie eingelesen wird, blieb Text:
    die Suche fand nichts, das Maximum von 9, 10, 3 war 9, die Summe
    brach mit TypeError ab."""
    ergebnis = als_python(_diagramm(*bloecke))
    _mit_eingaben(monkeypatch, *eingaben)

    assert _ausfuehren(ergebnis) == erwartet


def _laufen(bloecke: list, eingaben: list, monkeypatch) -> list:  # noqa: ANN001
    """Übersetzt, führt mit diesen Eingaben aus und liefert `spur`."""
    import builtins

    ergebnis = als_python(_diagramm(*bloecke))
    _pruefen(ergebnis)
    antworten = iter(eingaben)
    monkeypatch.setattr(builtins, "input", lambda _frage="": next(antworten))
    spur: list = []
    raum: dict = {"spur": spur}
    exec(compile(ergebnis.text, "<struktogramm>", "exec"), raum)
    raum["ampel_zeichnen"]()
    return spur


def test_namen_einlesen_und_sortieren(monkeypatch) -> None:  # noqa: ANN001
    """Punkt 662: Namen, die in eine Liste kamen und verglichen wurden,
    galten als Zahlen, und „Cem“ brach mit ValueError ab."""
    bloecke = [
        _anweisung("namen ← []"),
        _block("count_loop", "für i von 1 bis 3", children=[
            _anweisung("Eingabe: name"), _anweisung("namen.append(name)")]),
        _block("count_loop", "für i von 0 bis 1", children=[
            _block("count_loop", "für j von 0 bis 1 - i", children=[
                _block("branch", "namen[j] > namen[j + 1]", then=[
                    _anweisung("namen[j], namen[j + 1] ← namen[j + 1], namen[j]"),
                ], **{"else": []}),
            ]),
        ]),
        _anweisung("spur.append(namen)"),
    ]
    assert _laufen(bloecke, ["Cem", "Anna", "Ben"], monkeypatch) == [["Anna", "Ben", "Cem"]]


def test_maximum_dreier_zahlen_mit_pfeil(monkeypatch) -> None:  # noqa: ANN001
    """Punkt 663: mit „maximum ← a“ blieb a Text, b und c wurden Zahlen."""
    bloecke = [
        _anweisung("Eingabe: a"), _anweisung("Eingabe: b"), _anweisung("Eingabe: c"),
        _anweisung("maximum ← a"),
        _block("branch", "b > maximum", then=[_anweisung("maximum ← b")], **{"else": []}),
        _block("branch", "c > maximum", then=[_anweisung("maximum ← c")], **{"else": []}),
        _anweisung("spur.append(maximum)"),
    ]
    assert _laufen(bloecke, ["3", "12", "9"], monkeypatch) == [12]


@pytest.mark.parametrize(
    ("ausdruck", "erwartet"),
    [("max(zahlen)", 10), ("sum(zahlen)", 22), ("sum(zahlen) / len(zahlen)", 22 / 3)],
)
def test_max_und_sum_ueber_eingelesene_zahlen(
    monkeypatch, ausdruck: str, erwartet: float
) -> None:  # noqa: ANN001
    """Punkt 664: über eingelesene Zahlen rechneten max und sum mit Text."""
    bloecke = [
        _anweisung("zahlen ← []"),
        _block("count_loop", "für i von 1 bis 3", children=[
            _anweisung("Eingabe: z"), _anweisung("zahlen.append(z)")]),
        _anweisung(f"spur.append({ausdruck})"),
    ]
    assert _laufen(bloecke, ["9", "10", "3"], monkeypatch) == [erwartet]


def test_tausch_mit_pfeil_wird_uebersetzt(monkeypatch) -> None:  # noqa: ANN001
    """Punkt 665: „a, b ← b, a“ wurde Kommentar."""
    bloecke = [
        _anweisung("a ← 1"), _anweisung("b ← 2"),
        _anweisung("a, b ← b, a"),
        _anweisung("spur.append((a, b))"),
    ]
    ergebnis = als_python(_diagramm(*bloecke))
    assert ergebnis.anzahl == 0
    assert _laufen(bloecke, [], monkeypatch) == [(2, 1)]


@pytest.mark.parametrize(
    ("eingabe", "erwartet"),
    [
        ("8", 8), ("-3", -3), ("2,5", 2.5), ("2.5", 2.5),
        ("Cem", "Cem"), ("1,2,3", "1,2,3"), ("", ""),
    ],
)
def test_eingabe_lesen_entscheidet_beim_lauf(
    monkeypatch, eingabe: str, erwartet: object
) -> None:  # noqa: ANN001
    """Eine Zahl wird Zahl, alles andere bleibt Text."""
    gelesen = _laufen(
        [_anweisung("Eingabe: x"), _anweisung("spur.append(x)")], [eingabe], monkeypatch
    )
    assert gelesen == [erwartet] and type(gelesen[0]) is type(erwartet)
