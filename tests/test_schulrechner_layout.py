"""Die Voreinstellung auf einem 1366×768-Schulrechner (M11, Abschnitt 4).

Darauf war nie geprüft worden – entwickelt wurde auf einem großen
Bildschirm, auf dem alles Platz hat. Gemessen an einem Bildschirmfoto
blieben von den rund 728 nutzbaren Pixeln Höhe ganze 251 für den
Designer übrig: das Dock „Datenbank“ nahm allein 300, weil sein Inhalt
(SQL-Eingabe, Ergebnistabelle, drei breite Knöpfe) keine kleinere
Mindestgröße zuließ. Das Formular war nach dem ersten Drittel
abgeschnitten, und die Panel-Reiter rechts daneben waren auf 317 Pixel
Breite gequetscht, sodass „Aufrufstapel“ und „Tests“ nur noch über
kleine Pfeile erreichbar waren.

Eine Datenbank braucht im Unterricht erst, wer bei M6/M7 angekommen
ist. Das Dock ist deshalb voreingestellt zu.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from ide.shell.hauptfenster import HauptFenster

#: Ein typischer Schulrechner: 1366×768 abzüglich Taskleiste und
#: Fensterrahmen.
SCHUL_BREITE = 1366
SCHUL_HOEHE = 728

#: So viel Höhe muss der Arbeitsbereich (Editor bzw. Designer)
#: mindestens behalten. Weniger, und ein Formular ist beim Öffnen schon
#: abgeschnitten.
MINDESTHOEHE_ARBEITSBEREICH = 360


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import pcl.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


@pytest.fixture
def schulfenster(einstellungen: QSettings, qtbot) -> HauptFenster:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.resize(SCHUL_BREITE, SCHUL_HOEHE)
    fenster.show()
    return fenster


def test_die_datenbank_ist_voreingestellt_zu(schulfenster: HauptFenster) -> None:
    assert schulfenster.datenbank_dock.isVisible() is False


def test_der_arbeitsbereich_behaelt_genug_hoehe(schulfenster: HauptFenster) -> None:
    """Gemessen an den Mindestmaßen, nicht an der aktuellen Aufteilung:
    was die oben und unten angedockten Fenster mindestens brauchen, geht
    dem Editor in der Mitte unwiderruflich ab. Solange die `Datenbank`
    mit ihren rund 300 Pixeln dazugehörte, blieben für den Designer
    keine 260 mehr übrig."""
    waagerechte_docks = (
        schulfenster.palette_dock,
        schulfenster.datenbank_dock,
        schulfenster.panels_dock,
    )
    belegt = sum(
        dock.minimumSizeHint().height() for dock in waagerechte_docks if dock.isVisible()
    )

    assert SCHUL_HOEHE - belegt >= MINDESTHOEHE_ARBEITSBEREICH


def test_die_panels_haben_die_ganze_breite(schulfenster: HauptFenster) -> None:
    """Sonst verschwinden „Aufrufstapel“ und „Tests“ hinter Pfeilen."""
    assert schulfenster.panels_dock.width() >= SCHUL_BREITE - 20


def test_die_datenbank_laesst_sich_wieder_einblenden(
    schulfenster: HauptFenster,
) -> None:
    """Zu heißt nicht weg: „Ansicht → Datenbank“ holt das Dock zurück,
    und danach bleibt es offen, weil die Sichtbarkeit gemerkt wird."""
    aktion = schulfenster.datenbank_dock.toggleViewAction()

    aktion.trigger()

    assert schulfenster.datenbank_dock.isVisible() is True


def test_die_datenbank_passt_dann_auch_neben_die_panels(
    schulfenster: HauptFenster,
) -> None:
    """Die drei Ausfuhr-Knöpfe hießen einmal „Tabelle als SQL-Dump
    exportieren …“ und Ähnliches; nebeneinander gaben sie dem Dock eine
    Mindestbreite, neben die kaum noch etwas passte."""
    breite = schulfenster.datenbank_panel.minimumSizeHint().width()

    assert breite <= SCHUL_BREITE // 2


def test_layout_zuruecksetzen_fuehrt_zur_selben_voreinstellung(
    schulfenster: HauptFenster,
) -> None:
    """„Fenster → Layout zurücksetzen“ muss beim aufgeräumten Zustand
    landen, nicht beim alten."""
    schulfenster.datenbank_dock.show()

    schulfenster.restoreState(schulfenster._urspruengliches_layout)

    assert schulfenster.datenbank_dock.isVisible() is False


def test_ansicht_menue_holt_ein_schwebendes_dock_ins_fenster(qtbot) -> None:  # noqa: ANN001
    """Das gemerkte Layout enthielt das Dock „Datenbank“ schwebend. Nach
    „Ansicht → Datenbank“ stand es als loses Fenster über dem Editor
    (Punkt 45 der offenen Punkte)."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.resize(1366, 728)
    fenster.show()
    dock = fenster.datenbank_dock
    dock.show()
    dock.setFloating(True)
    dock.hide()

    dock.toggleViewAction().trigger()

    assert dock.isVisible()
    assert not dock.isFloating()
