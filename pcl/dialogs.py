"""Modale Dialogfunktionen: `show_message`, `input_box`, `open_dialog`.

Siehe README.md, Abschnitt 5.1, 5.2. Weitere Dialoge
(`message_dlg`, `SaveDialog`, `SelectDirectoryDialog`, `ColorDialog`,
`FontDialog`) werden bisher nirgends gebraucht und sind daher
zurückgestellt.
"""

from __future__ import annotations

from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

#: Vorgabefilter von `open_dialog` - Bilddateien.
#:
#: Bilder sind der Fall, für den der Dialog gebraucht wird
#: (Beispielprojekt `05_Bildergalerie`); wer etwas anderes öffnen will,
#: gibt einen eigenen Filter an.
BILDER_FILTER = "Bilder (*.png *.jpg *.jpeg *.bmp *.gif);;Alle Dateien (*.*)"


def show_message(text: str) -> None:
    """Entspricht `ShowMessage` aus der LCL (Abschnitt 5.1)."""
    box = QMessageBox()
    box.setWindowTitle("Natter")
    box.setIcon(QMessageBox.Icon.Information)
    box.setText(text)
    box.exec()


def input_box(titel: str, frage: str, standard: str = "") -> str:
    """Entspricht `InputBox` aus der LCL (Abschnitt 5.1). Liefert bei
    Abbruch `standard` zurück, wie in Lazarus."""
    text, bestaetigt = QInputDialog.getText(None, titel, frage, text=standard)
    return text if bestaetigt else standard


def open_dialog(titel: str = "Datei öffnen", filter: str = BILDER_FILTER) -> str:
    """Lässt eine vorhandene Datei auswählen und liefert ihren Pfad.

    Entspricht Lazarus' `TOpenDialog`: dort zieht man die Komponente
    aufs Formular und ruft `Execute`. Hier genügt ein Funktionsaufruf -
    eine unsichtbare Komponente, die nur zum Öffnen eines Dialogs auf
    dem Formular liegt, wäre für Lernende eher verwirrend als hilfreich.

    Bei Abbruch kommt ein leerer Text zurück; das ist die Antwort, auf
    die ein Programm ohnehin prüfen muss, und erspart eine zweite
    Rückgabe wie Lazarus' `Execute`-Wahrheitswert.
    """
    pfad, _ = QFileDialog.getOpenFileName(None, titel, "", filter)
    return pfad
