"""Prüfung vor dem Start für drei Fehler aus dem ersten Jahr
(Punkte 289, 290 und 291): `def main()` fehlt, die Methode zu einem
Ereignis fehlt, und ein Syntaxfehler erzeugt mehrere Meldungen mit der
falschen Zeile.

Die Projekte entstehen aus den echten Vorlagen in `tmp_path`.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from ide.project import Projekt
from ide.project.neu import projekt_erzeugen
from ide.run.pruefung import projekt_pruefen


def _konsole(ordner: Path, u_main: str) -> Projekt:
    projekt = projekt_erzeugen("console", ordner, "Hallo")
    (projekt.ordner / "u_main.py").write_text(u_main, encoding="utf-8")
    return projekt


# -- Punkt 289 --------------------------------------------------------------


def test_ohne_def_main_startet_ein_konsolenprogramm_nicht(tmp_path: Path) -> None:
    projekt = _konsole(
        tmp_path / "p", 'name = input("Name? ")\nprint("Hallo", name)\n'
    )

    funde = projekt_pruefen(projekt)

    assert len(funde) == 1
    fund = funde[0]
    assert fund.blockiert
    assert fund.datei.name == "u_main.py"
    assert "keine Funktion oder Klasse main" in fund.was
    assert "def main():" in fund.pruefe
    assert "main.py ruft sie beim Start auf" in str(fund)


def test_falsch_geschriebenes_main_wird_gezeigt(tmp_path: Path) -> None:
    projekt = _konsole(
        tmp_path / "p", '# Kopf\n\n\ndef Main():\n    print("x")\n'
    )

    fund = projekt_pruefen(projekt)[0]

    assert fund.zeile == 4
    assert "Steht sie dort als Main" in fund.pruefe


def test_im_pruefungsmodus_nennt_die_meldung_den_richtigen_namen_nicht(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Im Prüfungsmodus sagt eine Meldung nur, was falsch ist. Der
    richtige Name stand aber im Teil „Was“ und blieb deshalb stehen."""
    projekt = _konsole(
        tmp_path / "p", '# Kopf\n\n\ndef Main():\n    print("x")\n'
    )
    monkeypatch.setattr(
        "ide.run.pruefung.pruefungsmodus_laeuft", lambda: True
    )

    fund = projekt_pruefen(projekt)[0]

    assert "Main" not in fund.was
    assert "Main" not in str(fund)


def test_ein_fehlender_name_in_einer_eigenen_unit(tmp_path: Path) -> None:
    projekt = _konsole(
        tmp_path / "p",
        "from u_rechnen import verdoppeln\n\n\ndef main():\n"
        "    print(verdoppeln(2))\n",
    )
    (projekt.ordner / "u_rechnen.py").write_text(
        "def verdopple(x):\n    return 2 * x\n", encoding="utf-8"
    )

    funde = projekt_pruefen(projekt)

    assert [(f.datei.name, f.zeile) for f in funde] == [("u_main.py", 1)]
    assert "verdoppeln" in funde[0].was


@pytest.mark.parametrize(
    "u_main",
    [
        "def main():\n    pass\n",
        "try:\n    from math import pi as main\nexcept ImportError:\n"
        "    main = None\n",
        "from math import *\n",
        "if True:\n    def main():\n        pass\n",
    ],
    ids=["def", "import_as", "sternchen", "im_if"],
)
def test_vorhandene_namen_sind_kein_fund(tmp_path: Path, u_main: str) -> None:
    projekt = _konsole(tmp_path / "p", u_main)

    assert [f for f in projekt_pruefen(projekt) if f.blockiert] == []


# -- Punkt 290 --------------------------------------------------------------


def _fenster_projekt(ordner: Path, u_main: str) -> Projekt:
    projekt = projekt_erzeugen("gui", ordner, "Fenster")
    pfm_pfad = projekt.ordner / "u_main.pfm"
    pfm = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    pfm["children"].append(
        {
            "name": "button",
            "type": "Button",
            "properties": {"left": 10, "top": 10},
            "events": {"on_click": "button_click"},
        }
    )
    pfm_pfad.write_text(json.dumps(pfm), encoding="utf-8")
    (projekt.ordner / "u_main.py").write_text(u_main, encoding="utf-8")
    return projekt


def test_fehlende_ereignismethode_verhindert_den_start(tmp_path: Path) -> None:
    projekt = _fenster_projekt(
        tmp_path / "p",
        "from u_main_design import Form1Design\n\n\n"
        "class Form1(Form1Design):\n    pass\n",
    )

    funde = projekt_pruefen(projekt)

    assert len(funde) == 1
    fund = funde[0]
    assert fund.blockiert
    assert (fund.datei.name, fund.zeile) == ("u_main.py", 4)
    assert "button_click" in fund.was
    assert "on_click" in fund.was
    assert "button" in fund.was
    assert "Doppelklick" in fund.pruefe


def test_die_eigenen_leitfragen_sind_fragen(tmp_path: Path) -> None:
    """Dieselbe Regel wie für die übersetzten Funde (Punkt 51): jeder
    Satz im Teil „Zu prüfen“ endet mit einem Fragezeichen."""
    funde = projekt_pruefen(
        _konsole(tmp_path / "k", "def Main():\n    pass\n")
    ) + projekt_pruefen(
        _fenster_projekt(
            tmp_path / "g",
            "from u_main_design import Form1Design\n\n\n"
            "class Form1(Form1Design):\n    pass\n",
        )
    )

    assert {f.code for f in funde} == {"natter-import", "natter-ereignis"}
    for fund in funde:
        saetze = re.split(r"(?<=[.?!])\s+", fund.pruefe.strip())
        assert all(s.endswith("?") for s in saetze), fund.pruefe


def test_vorhandene_ereignismethode_ist_kein_fund(tmp_path: Path) -> None:
    projekt = _fenster_projekt(
        tmp_path / "p",
        "from u_main_design import Form1Design\n\n\n"
        "class Form1(Form1Design):\n"
        "    def button_click(self, sender) -> None:\n"
        "        pass\n",
    )

    assert projekt_pruefen(projekt) == []


# -- Punkt 291 --------------------------------------------------------------


def test_offene_klammer_ergibt_eine_meldung_fuer_ihre_zeile(
    tmp_path: Path,
) -> None:
    projekt = _konsole(
        tmp_path / "p",
        'def main():\n    name = input("Name? "\n    print(name)\n'
        '    print("fertig")\n',
    )

    funde = projekt_pruefen(projekt)

    assert len(funde) == 1
    assert funde[0].zeile == 2
    assert "nie geschlossen" in funde[0].was
    assert "„(“" in funde[0].was


def test_gleichheitszeichen_in_der_bedingung_ergibt_eine_meldung(
    tmp_path: Path,
) -> None:
    projekt = _konsole(
        tmp_path / "p",
        "def main():\n    a = 1\n    if a = 3:\n        print(a)\n",
    )

    funde = projekt_pruefen(projekt)

    assert len(funde) == 1
    assert funde[0].zeile == 3
    assert "==" in funde[0].was
    assert "Gleichheitszeichen" in funde[0].pruefe


def test_die_zeile_im_panel_nennt_keine_regel(tmp_path: Path) -> None:
    projekt = _konsole(tmp_path / "p", "def main():\n    if a = 3:\n        pass\n")

    fund = projekt_pruefen(projekt)[0]

    assert "invalid-syntax" not in str(fund)
    assert "invalid-syntax" in fund.regel


@pytest.mark.parametrize(
    ("zeile", "erwartet"),
    [
        ("    if 3 > 2\n        print(1)\n", "fehlt der Doppelpunkt"),
        ("    print('Hallo)\n", "nicht wieder geschlossen"),
    ],
)
def test_doppelpunkt_und_anfuehrungszeichen_bekommen_die_genaue_meldung(
    tmp_path: Path, zeile: str, erwartet: str
) -> None:
    """Vor dem Start kam für beide nur die allgemeine Meldung, obwohl
    der Fehlerkatalog es genauer weiß."""
    projekt = _konsole(tmp_path / "p", "def main():\n" + zeile)

    funde = [f for f in projekt_pruefen(projekt) if f.blockiert]

    assert erwartet in funde[0].was
