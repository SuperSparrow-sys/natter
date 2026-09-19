"""Bildvorschau (Abschnitt 11.4): zeigt eine Bilddatei skaliert an, dazu
Abmessungen und Dateigröße.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

_MAX_SEITE = 600


class BildVorschau(QWidget):
    """Zeigt `pfad` skaliert an, darunter Abmessungen und Dateigröße
    (Abschnitt 11.4: „Bilddateien öffnen sich in einem Vorschau-Tab mit
    Größe und Abmessungen“)."""

    def __init__(self, pfad: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._pfad = Path(pfad)
        self._pixmap = QPixmap(str(self._pfad))

        self._bild_label = QLabel()
        self._bild_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._bild_label.setPixmap(
            self._pixmap.scaled(
                _MAX_SEITE,
                _MAX_SEITE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

        groesse_kb = self._pfad.stat().st_size / 1024
        # Dezimalkomma wie ueberall in der Oberflaeche.
        groesse_text = f"{groesse_kb:.1f}".replace(".", ",")
        self._info_label = QLabel(
            f"{self._pixmap.width()} × {self._pixmap.height()} Pixel, {groesse_text} KB"
        )
        self._info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.addWidget(self._bild_label)
        layout.addWidget(self._info_label)

    @property
    def breite(self) -> int:
        return self._pixmap.width()

    @property
    def hoehe(self) -> int:
        return self._pixmap.height()
