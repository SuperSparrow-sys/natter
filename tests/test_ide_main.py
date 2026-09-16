"""Tests für ide/main.py: Einstiegspunkt der IDE. Headless – `main()`
selbst startet die blockierende Ereignisschleife und wird hier bewusst
nicht aufgerufen; `erstellen()` baut Anwendung und Fenster ohne zu
blockieren und ist deshalb testbar.
"""

from PySide6.QtWidgets import QApplication

from ide.main import erstellen
from ide.shell.hauptfenster import HauptFenster


def test_erstellen_liefert_anwendung_und_hauptfenster() -> None:
    app, fenster = erstellen()
    assert isinstance(app, QApplication)
    assert isinstance(fenster, HauptFenster)


def test_erstellen_wiederverwendet_vorhandene_anwendung() -> None:
    app1, _ = erstellen()
    app2, _ = erstellen()
    assert app1 is app2


def test_fenster_kann_angezeigt_werden() -> None:
    _, fenster = erstellen()
    fenster.show()
    assert fenster.isVisible() is True
