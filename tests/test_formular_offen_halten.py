"""Ein gezeigtes Formular lebt, bis es geschlossen ist (Punkt 214),
und seine Timer halten beim Schließen an (Punkt 215). Headless."""

from __future__ import annotations

import gc
import weakref

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QPushButton

from pcl import Button, Form, Timer

_KLICKS: list[str] = []


class _FormSpiel(Form):
    def create_components(self) -> None:
        self.caption = "Spiel 214"
        self.b_ok = Button(self)
        self.b_ok.caption = "OK"
        self.b_ok.on_click = self.b_ok_click

    def b_ok_click(self, sender: object) -> None:
        _KLICKS.append("OK")


def _nur_lokal_zeigen() -> weakref.ref:
    """Wie `spiel = FormSpiel()` und `spiel.show()` in einer
    Klick-Methode: nach dem Ende der Funktion hält nur `pcl` das
    Formular."""
    spiel = _FormSpiel()
    spiel.show()
    return weakref.ref(spiel)


def _fenster(titel: str):
    for widget in QApplication.topLevelWidgets():
        if widget.isVisible() and widget.windowTitle() == titel:
            return widget
    return None


def test_ein_formular_in_einer_lokalen_variablen_bleibt_offen(qtbot) -> None:
    _KLICKS.clear()
    verweis = _nur_lokal_zeigen()
    qtbot.wait(20)
    gc.collect()
    qtbot.wait(20)

    fenster = _fenster("Spiel 214")
    assert fenster is not None
    assert verweis() is not None
    knopf = fenster.findChild(QPushButton)
    qtbot.mouseClick(knopf, Qt.MouseButton.LeftButton)
    assert _KLICKS == ["OK"]

    fenster.close()
    qtbot.wait(20)
    gc.collect()
    assert verweis() is None
    assert _fenster("Spiel 214") is None


class _FormUhr(Form):
    def create_components(self) -> None:
        self.caption = "Uhr 215"
        self.ticks = 0
        self.t_countdown = Timer(self)
        self.t_countdown.interval = 20
        self.t_countdown.on_timer = self.t_countdown_timer
        # Ohne Formular erzeugt, nur als Attribut festgehalten.
        self.t_frei = Timer()
        self.t_frei.interval = 20
        self.t_frei.on_timer = self.t_countdown_timer

    def t_countdown_timer(self, sender: object) -> None:
        self.ticks += 1


def test_ein_timer_haelt_an_wenn_sein_fenster_geschlossen_wird(qtbot) -> None:
    uhr = _FormUhr()
    uhr.show()
    qtbot.waitUntil(lambda: uhr.ticks >= 4, timeout=3000)

    uhr.close()
    qtbot.wait(10)
    stand = uhr.ticks
    qtbot.wait(200)
    assert uhr.ticks == stand
    assert not uhr.t_countdown._qtimer.isActive()
    assert not uhr.t_frei._qtimer.isActive()
    # `enabled` bleibt, wie es war: beim nächsten Zeigen läuft er wieder.
    assert uhr.t_countdown.enabled is True

    uhr.show()
    qtbot.waitUntil(lambda: uhr.ticks >= stand + 4, timeout=3000)
    uhr.close()


def test_ein_abgeschalteter_timer_bleibt_beim_zeigen_aus(qtbot) -> None:
    uhr = _FormUhr()
    uhr.t_countdown.enabled = False
    uhr.t_frei.enabled = False
    uhr.show()
    uhr.close()
    uhr.show()
    qtbot.wait(100)
    assert uhr.ticks == 0
    uhr.close()
