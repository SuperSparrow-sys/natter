"""Modale Dialogfunktionen: `show_message`, `input_box`.

Siehe konzept-natter.md, Abschnitt 5.1, 5.2. Weitere Dialoge
(`message_dlg`, `OpenDialog`, `SaveDialog`, `SelectDirectoryDialog`,
`ColorDialog`, `FontDialog`) sind in keinem Referenzprojekt genutzt und
daher zurückgestellt.
"""

from __future__ import annotations

from PySide6.QtWidgets import QInputDialog, QMessageBox


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
