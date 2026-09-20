"""Tests laufen headless (Abschnitt 19: pytest-qt headless), damit sie ohne
Bildschirm/CI-Runner funktionieren. Muss vor jedem PySide6-Import gesetzt
sein, daher hier auf Modulebene."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Ohne dies findet die "offscreen"-Plattform KEINE echten Windows-
# Systemschriften (auch nicht Consolas!) und weicht auf irgendeine
# zufällig verfügbare Ersatzschrift aus - Tests, die Schriftmetriken
# prüfen (z. B. "passt diese Beschriftung in den Button?"), maßen dann
# gegen eine andere Schrift als die echte App auf dem Bildschirm nutzt
# (real gefunden: Rückmeldung zur Editor-Schriftart, September
# 2026 - `QFontInfo` löste ohne dies fälschlich auf die mitgelieferte
# Cascadia-Code-Datei statt auf das eigentlich angeforderte Consolas
# auf, weil Consolas selbst gar nicht auffindbar war).
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

#: Zeitgrenze für alle Debugger-Tests, die auf einen echten
#: Unterprozess warten (debugpy-Handshake, Haltepunkt erreichen).
#:
#: Real gemessen: einzeln laufen diese Tests in gut einer Sekunde und
#: sind dreimal hintereinander grün. Am Ende der vollen Suite - nach über
#: tausend Qt-Tests im selben Prozess - reichten 15 Sekunden dagegen
#: nicht mehr zuverlässig: in vier Durchläufen fiel jedes Mal ein
#: *anderer* Debugger-Test um. Das war nie ein Fehler im Debugger,
#: sondern eine zu knappe Grenze unter Last.
DEBUG_ZEITGRENZE = 45000

import pytest  # noqa: E402
from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _qt_anwendung():
    """Eine QWidget-Erzeugung ohne vorherige QApplication stürzt den
    Prozess fataler ab, ohne saubere Python-Ausnahme. Diese Fixture stellt
    sicher, dass für die gesamte Testsitzung immer genau eine
    QApplication existiert, bevor irgendein Test ein Widget erzeugt."""
    anwendung = QApplication.instance() or QApplication([])
    # Wie im echten Start (`ide/main.py`): Qts eigene Texte auf Deutsch.
    # Sonst prüften die Tests eine englische Oberfläche - genau das,
    # was M11 Abschnitt 4 abstellen sollte.
    from ide.deutsch import deutsch_einschalten

    deutsch_einschalten(anwendung)
    yield anwendung


@pytest.fixture(autouse=True)
def _qsettings_isoliert(tmp_path):
    """`HauptFenster` speichert die Design-Wahl (Hell/Dunkel/System) über
    `QSettings("Natter", "Natter-IDE")`. Ohne diese Umleitung würden
    Tests in die echte Windows-Registry des Nutzers schreiben und sich
    gegenseitig über den zuletzt gespeicherten Wert beeinflussen."""
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    yield
