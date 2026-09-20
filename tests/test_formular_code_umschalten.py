"""„Ansicht → Formular und Code wechseln“ (Abschnitt 7.9, Umschalt+F12).

In Lazarus ist das der meistbenutzte Handgriff überhaupt: einen Knopf
ablegen, seinen Code schreiben, wieder aufs Formular schauen. In Natter
stand er seit M2 als Vermerk im Explorer – „folgt später“ – und fehlte
damit genau der Gruppe, für die Natter gebaut ist.

Nicht auf F12. Das gehört im Editor seit M11 zu „Zur Definition
springen“, wie in VS Code; ein Tastenkürzel, das je nach Reiter etwas
anderes tut, ist schlimmer als eins, das man einmal neu lernt.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ide.shell.hauptfenster import HauptFenster
from ide.shell.quelltexteditor import QuelltextEditor

PFM = {
    "format": "pfm/1",
    "class": "Form1",
    "type": "Form",
    "properties": {"caption": "Probe", "width": 320, "height": 240},
    "children": [
        {
            "name": "b_ok",
            "type": "Button",
            "properties": {"left": 20, "top": 20, "caption": "OK"},
            "events": {},
        }
    ],
}

UNIT = '''"""Probe."""

from u_main_design import Form1Design


class Form1(Form1Design):
    pass
'''


@pytest.fixture
def projekt(tmp_path: Path) -> Path:
    (tmp_path / "u_main.pfm").write_text(json.dumps(PFM), encoding="utf-8")
    (tmp_path / "u_main.py").write_text(UNIT, encoding="utf-8")
    return tmp_path


def test_vom_formular_zur_unit(projekt: Path, qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.oeffnen(projekt / "u_main.pfm")

    fenster._formular_code_umschalten()

    editor = fenster.editor_tabs.currentWidget()
    assert isinstance(editor, QuelltextEditor)
    assert editor.toPlainText() == UNIT


def test_von_der_unit_zum_formular(projekt: Path, qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.oeffnen(projekt / "u_main.py")

    fenster._formular_code_umschalten()

    assert "Designer" in fenster.editor_tabs.tabText(fenster.editor_tabs.currentIndex())


def test_hin_und_zurueck_macht_keine_neuen_reiter(projekt: Path, qtbot) -> None:
    """Ein schon offener Reiter kommt nach vorn, statt ein zweites Mal
    aufzugehen - sonst häuften sich beim Arbeiten Dutzende an."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.oeffnen(projekt / "u_main.pfm")

    for _ in range(4):
        fenster._formular_code_umschalten()

    assert fenster.editor_tabs.count() == 2


def test_ohne_unit_kommt_eine_meldung(tmp_path: Path, qtbot) -> None:
    (tmp_path / "u_allein.pfm").write_text(json.dumps(PFM), encoding="utf-8")
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.oeffnen(tmp_path / "u_allein.pfm")

    fenster._formular_code_umschalten()

    assert "u_allein.py" in fenster.statusBar().currentMessage()


def test_ohne_formular_kommt_eine_meldung(tmp_path: Path, qtbot) -> None:
    (tmp_path / "hilfsmittel.py").write_text("x = 1\n", encoding="utf-8")
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.oeffnen(tmp_path / "hilfsmittel.py")

    fenster._formular_code_umschalten()

    assert "hilfsmittel.pfm" in fenster.statusBar().currentMessage()


def test_ohne_offenen_reiter_kommt_eine_meldung(qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster._formular_code_umschalten()

    assert "umzuschalten" in fenster.statusBar().currentMessage()


def test_das_kuerzel_ist_nicht_f12(qtbot) -> None:
    """F12 gehört im Editor zu „Zur Definition springen“."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    assert fenster.formular_code_aktion.shortcut().toString() == "Shift+F12"
    assert not any(aktion.tastenkuerzel == "F12" for aktion in fenster.aktionen)


def test_der_handgriff_ist_nachzuschlagen(qtbot) -> None:
    """Als richtige `Aktion` registriert - sonst stünde er weder in der
    Tastenkürzel-Übersicht noch in der Befehlspalette, und ein
    Kürzel, das nirgends nachzuschlagen ist, findet niemand."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    treffer = [a for a in fenster.aktionen if a.tastenkuerzel == "Shift+F12"]

    assert len(treffer) == 1
    assert treffer[0].name == "Formular und Code wechseln"


def test_der_eintrag_steht_im_ansicht_menue(qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    eintraege = [
        aktion.text() for aktion in fenster._menues["Ansicht"].actions()
    ]

    assert "Formular und Code wechseln" in eintraege


# ------------------------------------------- Ein frisch angelegtes Projekt
#
# Nutzer-Meldung : "wenn ich ein neues Projekt erstelle
# muss auch die u_main.py fuer den code angezeigt werden nicht nur der
# designer". Vorher ging nach dem Anlegen gar kein Reiter auf - man
# landete in einem leeren Fenster.


def _neues_gui_projekt(ordner: Path):
    from ide.project.neu import projekt_erzeugen

    return projekt_erzeugen("gui", ordner, "Probe")


def test_ein_neues_projekt_oeffnet_formular_und_unit(tmp_path: Path, qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    projekt = _neues_gui_projekt(tmp_path)

    fenster._projekt_startdateien_oeffnen(projekt)

    reiter = [
        fenster.editor_tabs.tabText(i) for i in range(fenster.editor_tabs.count())
    ]
    assert "u_main.py" in reiter
    assert "u_main (Designer)" in reiter


def test_vorn_liegt_der_designer(tmp_path: Path, qtbot) -> None:
    """Bei einem GUI-Projekt legt man zuerst die Oberflaeche an; die
    Unit steht als zweiter Reiter daneben."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster._projekt_startdateien_oeffnen(_neues_gui_projekt(tmp_path))

    aktiv = fenster.editor_tabs.tabText(fenster.editor_tabs.currentIndex())
    assert aktiv == "u_main (Designer)"


def test_ein_konsolenprojekt_oeffnet_nur_seine_unit(tmp_path: Path, qtbot) -> None:
    """Es hat kein Formular - und `main.py` bekommt der Schueler nicht
    zu sehen, die traegt nur den Start."""
    from ide.project.neu import projekt_erzeugen

    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster._projekt_startdateien_oeffnen(projekt_erzeugen("console", tmp_path, "Konsole"))

    reiter = [
        fenster.editor_tabs.tabText(i) for i in range(fenster.editor_tabs.count())
    ]
    assert reiter == ["u_main.py"]
