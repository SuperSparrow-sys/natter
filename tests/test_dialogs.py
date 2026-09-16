"""Tests für pcl/dialogs.py: show_message, input_box. Headless über
QTimer.singleShot, das den aktiven modalen Dialog während `exec()`
automatisch bedient. Siehe docs/PLAN.md, M1 Schritt 6.
"""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from pcl.dialogs import input_box, show_message


def test_show_message_zeigt_den_uebergebenen_text() -> None:
    gesehener_text = []

    def bedienen() -> None:
        box = QApplication.activeModalWidget()
        gesehener_text.append(box.text())
        box.accept()

    QTimer.singleShot(0, bedienen)
    show_message("Deinen Eingaben sind zu Lang")

    assert gesehener_text == ["Deinen Eingaben sind zu Lang"]


def test_input_box_liefert_eingegebenen_text() -> None:
    def bedienen() -> None:
        dialog = QApplication.activeModalWidget()
        dialog.setTextValue("Max")
        dialog.accept()

    QTimer.singleShot(0, bedienen)
    ergebnis = input_box("VERLOREN", "Bitte gib deinen Namen ein", "")

    assert ergebnis == "Max"


def test_input_box_liefert_standard_bei_abbruch() -> None:
    def abbrechen() -> None:
        dialog = QApplication.activeModalWidget()
        dialog.reject()

    QTimer.singleShot(0, abbrechen)
    ergebnis = input_box("Titel", "Frage", "Standardname")

    assert ergebnis == "Standardname"
