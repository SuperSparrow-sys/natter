"""`docs/erste_schritte.md` gegen die Wirklichkeit gehalten (M12).

Die Seite ist für viele das Erste, was sie von Natter lesen. Stimmt
darin eine Taste nicht, drückt jemand sie, es passiert nichts, und er
sucht den Fehler bei sich – eine falsche Anleitung ist schlimmer als
keine. Genau das war der Fall: die Seite nannte **F7/F8** für
Einzelschritt und Prozedurschritt, registriert sind aber **F11/F10**.

Für die Tastenkürzel-Übersicht unter „Hilfe“ war dieser Grundsatz schon
gezogen worden – sie wird aus dem Aktionsregister **erzeugt**. Diese
Seite ist Fließtext und lässt sich nicht erzeugen; also wird sie
geprüft.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from ide.shell.hauptfenster import HauptFenster
from ide.shell.tastenkuerzel import deutsche_taste

SEITE = Path(__file__).resolve().parent.parent / "docs" / "erste_schritte.md"

#: Zeilen der Tastentabelle, die kein Kürzel des Hauptfensters sind und
#: deshalb nicht dagegen geprüft werden können.
NUR_IM_DIAGRAMMEDITOR = ("Strg+Umschalt+E",)


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import pcl.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


def _tastenzeilen() -> list[tuple[str, str]]:
    """Die Zeilen der Tabelle „Die wichtigsten Tasten“ als (Taste, Zweck)."""
    text = SEITE.read_text(encoding="utf-8")
    abschnitt = text.split("## Die wichtigsten Tasten", 1)[1].split("##", 1)[0]
    zeilen = []
    for zeile in abschnitt.splitlines():
        treffer = re.match(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|", zeile)
        if treffer and treffer.group(1) not in ("Taste", "---"):
            zeilen.append((treffer.group(1), treffer.group(2)))
    return zeilen


def _belegte_tasten(fenster: HauptFenster) -> set[str]:
    return {
        deutsche_taste(aktion.tastenkuerzel)
        for aktion in fenster.aktionen
        if aktion.tastenkuerzel
    }


def test_die_tabelle_wurde_ueberhaupt_gefunden() -> None:
    """Sonst prüften die Tests unten stillschweigend nichts."""
    assert len(_tastenzeilen()) >= 8


def test_jede_genannte_taste_ist_auch_belegt(
    einstellungen: QSettings, qtbot
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    belegt = _belegte_tasten(fenster)

    for taste, zweck in _tastenzeilen():
        for einzeln in [teil.strip() for teil in taste.split("/")]:
            if einzeln in NUR_IM_DIAGRAMMEDITOR:
                continue
            assert einzeln in belegt, (
                f"„Erste Schritte“ nennt {einzeln} für „{zweck}“, "
                f"registriert ist diese Taste aber nirgends."
            )


def test_die_starttasten_stehen_an_der_richtigen_aktion(
    einstellungen: QSettings, qtbot
) -> None:
    """Belegt sein reicht nicht – die Taste muss auch das tun, was
    danebensteht."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    zu_taste = {
        deutsche_taste(aktion.tastenkuerzel): aktion.name
        for aktion in fenster.aktionen
        if aktion.tastenkuerzel
    }

    assert zu_taste["F11"] == "Einzelschritt"
    assert zu_taste["F10"] == "Prozedurschritt"
    assert zu_taste["F5"] == "Starten"
    assert zu_taste["Strg+F5"] == "Starten ohne Debugger"
    assert zu_taste["Umschalt+F5"] == "Stopp"


def test_die_genannten_projektdateien_entstehen_wirklich(tmp_path: Path) -> None:
    """Die Tabelle am Anfang zählt vier Dateien auf. Ein neues
    GUI-Projekt muss genau die anlegen."""
    from ide.project import projekt_erzeugen

    # Überall in der Seite, nicht nur in der Tabelle: seit die erzeugten
    # Dateien nicht mehr im Baum stehen, werden sie im Fließtext genannt.
    text = SEITE.read_text(encoding="utf-8")
    genannt = set(re.findall(r"`([a-z_]+\.(?:py|pfm))`", text))

    projekt_erzeugen("gui", tmp_path / "p", "Test")
    vorhanden = {pfad.name for pfad in (tmp_path / "p").iterdir()}

    fehlend = genannt - vorhanden
    assert not fehlend, f"In der Anleitung genannt, aber nicht angelegt: {fehlend}"


def test_der_beschriebene_weg_zur_ereignismethode_gibt_es_auch(
    tmp_path: Path,
) -> None:
    """Die Seite beschrieb einmal, man trage bei `on_click` einen Namen
    ein – der Reiter „Ereignisse“ ist aber eine Auswahlliste
    **vorhandener** Methoden. Der Weg über den Doppelklick ist der
    richtige, und den muss es geben."""
    from ide.designer.canvas import DesignerCanvas
    from pcl import Button, Form

    text = SEITE.read_text(encoding="utf-8")
    assert "Doppelklick auf den Knopf" in text

    class _Formular(Form):
        def create_components(self) -> None:
            pass

    unit = tmp_path / "u_main.py"
    unit.write_text(
        chr(10).join(["from pcl import Form", "", "", "class _Formular(Form):", "    pass", ""]),
        encoding="utf-8",
    )
    canvas = DesignerCanvas(_Formular(), pfm_pfad=tmp_path / "u_main.pfm")
    canvas.unit_pfad = unit
    knopf = canvas.komponente_platzieren(Button, 8, 8)

    name = canvas.ereignis_handler_erzeugen(knopf)

    assert name is not None
    assert f"def {name}" in unit.read_text(encoding="utf-8")
