"""QSS-Generator aus `design/tokens.json` für `pcl`-Programme.

Siehe konzept-natter.md, Abschnitt 6 und 23.2. Die Tokens-Datei ist die
einzige Quelle; ein eigener, ähnlich aufgebauter Generator für die IDE
selbst folgt in M2.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from pcl.errors import NatterPropertyError


def _tokens_pfad_ermitteln() -> Path:
    """In einer mit PyInstaller gebauten Exe (Abschnitt 16) liegt
    `design/tokens.json` nicht mehr drei Ebenen über dieser Datei,
    sondern im Bundle-Ordner (`sys._MEIPASS`) – der Exporter bindet den
    `design`-Ordner dafür über `--add-data` ein, siehe
    `ide/export/exporter.py`."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass is not None:
        return Path(meipass) / "design" / "tokens.json"
    return Path(__file__).resolve().parent.parent.parent / "design" / "tokens.json"


_TOKENS_PFAD = _tokens_pfad_ermitteln()


def _tokens_laden() -> dict[str, Any]:
    return json.loads(_TOKENS_PFAD.read_text(encoding="utf-8"))


def theme_aufloesen(theme: str) -> str:
    """Löst `system` auf `light` oder `dark` auf (Abschnitt 6). Ohne
    laufende `QApplication` oder bei unbekanntem Farbschema des
    Betriebssystems ist `light` der Ausweich-Standard."""
    if theme in ("light", "dark"):
        return theme
    if theme != "system":
        raise NatterPropertyError(
            f"theme erwartet 'system', 'light' oder 'dark', erhalten wurde {theme!r}."
        )

    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None and app.styleHints().colorScheme() == Qt.ColorScheme.Dark:
        return "dark"
    return "light"


def qss_erzeugen(theme: str, tokens: dict[str, Any] | None = None) -> str:
    """Erzeugt das QSS-Stylesheet für ein Theme (`system`/`light`/`dark`)."""
    aufgeloest = theme_aufloesen(theme)
    daten = tokens if tokens is not None else _tokens_laden()
    farben = daten["color"][aufgeloest]
    radius = daten["radius"]
    schrift = daten["font"]

    return f"""\
QWidget {{
    background-color: {farben["bg"]};
    color: {farben["text"]};
    font-family: "{schrift["family"]}", "{schrift["family_fallback"]}";
    font-size: {schrift["sizes_pt"][1]}pt;
}}

QPushButton {{
    background-color: {farben["surface"]};
    border: 1px solid {farben["border"]};
    border-radius: {radius["button"]}px;
    padding: 4px 12px;
}}

QPushButton:hover {{
    background-color: {farben["accent"]};
    color: {farben["bg"]};
}}

QPushButton:disabled {{
    color: {farben["text_muted"]};
}}

QLineEdit, QPlainTextEdit, QComboBox, QListWidget, QTableWidget {{
    background-color: {farben["bg"]};
    border: 1px solid {farben["border"]};
    border-radius: {radius["input"]}px;
    selection-background-color: {farben["accent"]};
}}

QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
    border: 1px solid {farben["focus"]};
}}

QTableWidget::item, QListWidget::item {{
    background-color: {farben["bg"]};
    color: {farben["text"]};
}}
QTableWidget::item:selected, QListWidget::item:selected {{
    background-color: {farben["accent"]};
    color: {farben["bg"]};
}}
QHeaderView::section {{
    background-color: {farben["surface"]};
    color: {farben["text"]};
    border: 1px solid {farben["border"]};
    padding: 2px 4px;
}}

QLabel {{
    background-color: transparent;
}}
"""
