"""QSS-Generator aus `design/tokens.json` für `pcl`-Programme.

Siehe README.md, Abschnitt 6 und 23.2. Die Tokens-Datei ist die
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

    # Gemeldet: 12pt (sizes_pt[1]) wirkte zu groß
    # - dieselbe Korrektur wie zuvor für die IDE-Hülle
    # (ide/shell/theme.py). Real gefunden: bei 12pt passte "Button1"
    # nicht mehr in einen 52px breiten Button, der Text wurde
    # abgeschnitten.
    basis_pt = schrift["sizes_pt"][0]

    return f"""\
QWidget {{
    background-color: {farben["bg"]};
    color: {farben["text"]};
    font-family: "{schrift["family"]}", "{schrift["family_fallback"]}";
    font-size: {basis_pt}pt;
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

/* `QSpinBox`/`QDoubleSpinBox` (SpinEdit, FloatSpinEdit) stehen hier
   bewusst NICHT. Dieselbe Falle wie bei Kästchen und Optionsfeldern
   weiter unten, nur mit umgekehrtem Ausgang: sobald die Komponente auch
   nur eine Rahmenregel bekommt, zeichnet Qt sie vollständig aus dem
   Stylesheet - und die beiden Pfeilspitzen fallen ersatzlos weg. Im
   Bildvergleich standen an ihrer Stelle nur noch zwei Striche. Ein
   Nachbau der Pfeile über `::up-arrow`/`::down-arrow` scheiterte
   ebenfalls: Qt versteht den CSS-Trick „Dreieck aus Rahmen" nicht und
   malte zwei schwarze Quadrate. Ohne eigene Regel rendert Qt beide
   Komponenten von sich aus in den Farben des Themes, samt Fokusrahmen
   und ausgegrautem Zustand. */

/* Ohne diesen Block sieht eine gesperrte Komponente genauso aus wie eine
   bedienbare: die Regel `QWidget {{ color: ... }}` ganz oben schlägt die
   Farbe, die Qt sonst aus der Palette für den Zustand „disabled" nimmt.
   Beim Bildvergleich einer `GroupBox` mit `enabled = False` aufgefallen -
   Inhalt und Beschriftung standen in voller Schwärze da (M-Schritt 6,
   Behälter). Bisher gab es nur `QPushButton:disabled`. */
QWidget:disabled {{
    color: {farben["text_muted"]};
}}

QLineEdit:disabled, QPlainTextEdit:disabled, QComboBox:disabled,
QListWidget:disabled, QTableWidget:disabled {{
    background-color: {farben["surface"]};
    border-color: {farben["text_muted"]};
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

/* Sobald überhaupt ein Stylesheet gesetzt ist, zeichnet Qt Kästchen und
   Optionsfelder nicht mehr über den nativen Windows-Stil, sondern aus dem
   Stylesheet - ohne diese Regeln blieb der Markierungspunkt einfach weg.
   Real erst beim Start eines echten Programms auf dem Windows-Ziel
   sichtbar geworden (im Designer sah dieselbe Komponente korrekt aus),
   siehe docs/arbeitspakete/M8.md, Schritt 6. */
QCheckBox::indicator, QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    background-color: {farben["bg"]};
    border: 1px solid {farben["border"]};
}}
QCheckBox::indicator {{
    border-radius: 3px;
}}
QRadioButton::indicator {{
    border-radius: 8px;
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border: 1px solid {farben["focus"]};
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {farben["accent"]};
    border: 1px solid {farben["accent"]};
}}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
    background-color: {farben["surface"]};
    border-color: {farben["text_muted"]};
}}

QScrollBar:horizontal {{
    background: {farben["surface"]};
    height: 14px;
    border-radius: 7px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {farben["border"]};
    border-radius: 5px;
    min-width: 24px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {farben["accent"]};
}}
QScrollBar:vertical {{
    background: {farben["surface"]};
    width: 14px;
    border-radius: 7px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {farben["border"]};
    border-radius: 5px;
    min-height: 24px;
    margin: 2px;
}}
QScrollBar::handle:vertical:hover {{
    background: {farben["accent"]};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0;
    height: 0;
}}

/* Behälter (GroupBox, RadioGroup). Ohne eigene Regel setzte Qt die
   Beschriftung über den Rahmen statt auf seine obere Kante; gewollt ist,
   dass der Rahmen genau durch die Schrift läuft. */
QGroupBox {{
    border: 1px solid {farben["border"]};
    border-radius: {radius["panel"]}px;
    margin-top: 7px;
    padding: 6px 4px 4px 4px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 4px;
}}
QGroupBox:disabled {{
    border-color: {farben["text_muted"]};
}}

/* TrackBar: nur der Griff wird umgefärbt, Rille und Teilstriche
   bleiben dem Stil des Systems überlassen. Im Bildvergleich nachgemessen
   (September 2026): sobald auch `QSlider::groove` eine Regel bekommt,
   zeichnet Qt den Schieber vollständig aus dem Stylesheet - und QSS
   kennt keine Teilstriche. `TrackBar.frequency` wäre damit wirkungslos
   geworden, denn jedes pcl-Formular hat ein Stylesheet. Mit einer Regel
   allein für den Griff bleiben die Teilstriche stehen. */
QSlider::handle:horizontal {{
    background: {farben["accent"]};
    width: 12px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:disabled {{
    background: {farben["text_muted"]};
}}
"""
