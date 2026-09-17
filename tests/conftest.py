"""Tests laufen headless (Abschnitt 19: pytest-qt headless), damit sie ohne
Bildschirm/CI-Runner funktionieren. Muss vor jedem PySide6-Import gesetzt
sein, daher hier auf Modulebene."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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
