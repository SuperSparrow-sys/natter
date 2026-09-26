"""Das Panel „Ausgabe“ und „Start → Stopp“ (M11, Abschnitt 5).

Zwei Funde beim Aufräumen:

* Der Reiter „Ausgabe“ war ein leeres graues Feld – angelegt, benannt,
  nie gefüllt. Das Schülerprogramm läuft als eigener Prozess in einem
  eigenen Fenster (README.md, Abschnitt 7.8), seine
  `print`-Zeilen stehen also dort. Laut demselben Abschnitt gehören
  aber Exitcode und Laufzeit in dieses Panel, und die standen
  nirgends.
* „Start → Stopp“ hing allein am Debugger. Wer sein Programm mit
  Strg+F5 gestartet hatte, bekam von Natter sogar den Rat, es „über
  Start → Stopp“ zu beenden – und dort passierte dann nichts.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from ide.shell.hauptfenster import HauptFenster


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import pcl.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


class _Prozess:
    """Ein Programm, das auf Kommando endet – ein echter Prozess würde
    den Test von der Uhr abhängig machen."""

    def __init__(self, code: int | None = None) -> None:
        self.code = code
        self.getoetet = False

    def poll(self) -> int | None:
        return self.code

    def kill(self) -> None:
        self.getoetet = True
        self.code = -1


def _projekt_anlegen(ordner: Path) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text("print('hallo')\n", encoding="utf-8")
    (ordner / "test.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Testprojekt",
                "type": "console",
                "main": "main.py",
            }
        ),
        encoding="utf-8",
    )
    return ordner / "test.natter"


@pytest.fixture
def fenster(einstellungen: QSettings, qtbot, tmp_path: Path) -> HauptFenster:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(_projekt_anlegen(tmp_path / "p").parent)
    return fenster


def _zeilen(fenster: HauptFenster) -> list[str]:
    liste = fenster.ausgabe_liste
    return [liste.item(z).text() for z in range(liste.count())]


def test_der_reiter_ausgabe_ist_nicht_mehr_leer(fenster: HauptFenster) -> None:
    """Er enthielt ein `QWidget()` ohne Inhalt – ein graues Feld mit
    einer Beschriftung, die etwas versprach."""
    index = next(
        i for i in range(fenster.panels.count()) if fenster.panels.tabText(i) == "Ausgabe"
    )

    assert fenster.panels.widget(index) is fenster.ausgabe_liste


def test_das_programmende_nennt_exitcode_und_laufzeit(fenster: HauptFenster) -> None:
    fenster._start_zeitpunkt = None

    fenster.programmende_melden(0)

    assert "Code 0" in _zeilen(fenster)[-1]


def test_ein_exitcode_ungleich_null_wird_erklaert(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """„Code 1“ allein sagt niemandem etwas. Ein Programm mit Fenster
    hat seine Meldung schon gezeigt und geschlossen; bis 0.3.4 hieß es
    auch hier, das Fenster bleibe offen."""
    from ide.project.neu import projekt_erzeugen

    projekt = projekt_erzeugen("gui", tmp_path / "gui", "Fenster")
    fenster.projekt_oeffnen(projekt.ordner / "Fenster.natter")

    fenster.programmende_melden(1)

    zeile = _zeilen(fenster)[-1]
    assert "Code 1" in zeile
    assert "Fehler" in zeile
    assert "eigenen Fenster gezeigt" in zeile
    assert "bleibt dafür offen" not in zeile


def test_im_konsolenprojekt_bleibt_die_konsole_offen(fenster: HauptFenster) -> None:
    """Nur ein Konsolenprogramm lässt sein Fenster für die Meldung
    offen; das Projekt der Fixture ist eines."""
    fenster.programmende_melden(1)

    assert "Konsolenfenster des Programms, es bleibt dafür offen" in _zeilen(fenster)[-1]


def test_jede_zeile_traegt_die_uhrzeit(fenster: HauptFenster) -> None:
    fenster.ausgabe_zeile("Irgendwas")

    zeile = _zeilen(fenster)[-1]
    stunde, minute, rest = zeile.split(":", 2)
    assert stunde.isdigit() and minute.isdigit()
    assert rest[:2].isdigit()


def test_das_ende_wird_von_selbst_bemerkt(fenster: HauptFenster) -> None:
    """Das Programm läuft in einem eigenen Prozess und meldet sich nicht
    zurück – Natter sieht in einem festen Takt nach."""
    prozess = _Prozess(code=None)
    fenster.laufender_prozess = prozess

    fenster._programmende_pruefen()
    assert not any("beendet" in zeile for zeile in _zeilen(fenster))

    prozess.code = 0
    fenster._programmende_pruefen()

    assert "beendet" in _zeilen(fenster)[-1]
    assert fenster.laufender_prozess is None


def test_stopp_beendet_auch_ein_ohne_debugger_gestartetes_programm(
    fenster: HauptFenster,
) -> None:
    prozess = _Prozess(code=None)
    fenster.laufender_prozess = prozess

    fenster._debugger_stoppen_aktion()

    assert prozess.getoetet is True
    assert fenster.laufender_prozess is None
    assert "Stopp" in _zeilen(fenster)[-1]
    assert "Programm gestoppt" in fenster.statusBar().currentMessage()


def test_stopp_ohne_laufendes_programm_sagt_das_auch(fenster: HauptFenster) -> None:
    """Vorher passierte einfach gar nichts – man drückte und war so
    schlau wie zuvor."""
    fenster._debugger_stoppen_aktion()

    assert "nichts" in fenster.statusBar().currentMessage()
