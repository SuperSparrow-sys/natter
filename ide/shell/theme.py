"""IDE-Shell-Theme (Abschnitt 6, 7.1): QSS für das Hauptfenster selbst –
Menüleiste, Werkzeugleisten, Docks, Reiter, Baum-/Listenansichten,
Statusleiste, Eingabefelder, Rollbalken.

Getrennt von `pcl.theme` (Abschnitt 6), das nur die von Schülern
geschriebenen *Programme* einfärbt: dieselben Design-Tokens aus
`design/tokens.json`, aber ein eigener, umfangreicherer Regelsatz für
die zusätzlichen Qt-Widget-Typen, die im IDE-Rahmen selbst vorkommen
(`QMenuBar`, `QDockWidget`, `QTabWidget`, `QTreeWidget`, `QScrollBar`,
…) und die `pcl.theme` bewusst nicht kennt.

Bisher stand die IDE selbst komplett ohne eigenes Stylesheet da (nur der
Designer-Auswahlrahmen war gestylt) – deshalb wirkte sie farblos/grau
(Nutzer-Feedback, September 2026, siehe docs/PLAN.md, „Visueller
Feinschliff“).
"""

from __future__ import annotations

from typing import Any

from pcl.theme import _tokens_laden, theme_aufloesen


def _mit_alpha(farbe_hex: str, alpha: float) -> str:
    """Wandelt eine `#rrggbb`-Farbe in `rgba(...)` mit gegebener Deckkraft
    um – für sanfte, helle Auswahl-/Hover-Flächen (wie in Lazarus/Windows
    11), bei denen farbige Symbole lesbar bleiben müssen, statt einer
    deckenden Akzentfarbe wie bei Menüs/Tabs."""
    r = int(farbe_hex[1:3], 16)
    g = int(farbe_hex[3:5], 16)
    b = int(farbe_hex[5:7], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


def ide_qss_erzeugen(theme: str = "system", tokens: dict[str, Any] | None = None) -> str:
    """Erzeugt das QSS-Stylesheet für das IDE-Hauptfenster (`system`/
    `light`/`dark`, wie `pcl.theme.qss_erzeugen`)."""
    aufgeloest = theme_aufloesen(theme)
    daten = tokens if tokens is not None else _tokens_laden()
    farben = daten["color"][aufgeloest]
    radius = daten["radius"]
    schrift = daten["font"]
    basis_pt = schrift["sizes_pt"][1]

    return f"""\
QMainWindow, QDialog {{
    background-color: {farben["bg"]};
    color: {farben["text"]};
}}

QWidget {{
    background-color: {farben["bg"]};
    color: {farben["text"]};
    font-family: "{schrift["family"]}", "{schrift["family_fallback"]}";
    font-size: {basis_pt}pt;
}}

QMenuBar {{
    background-color: {farben["surface"]};
    border-bottom: 1px solid {farben["border"]};
    padding: 2px 4px;
}}
QMenuBar::item {{
    padding: 4px 10px;
    border-radius: {radius["button"]}px;
    background: transparent;
}}
QMenuBar::item:selected, QMenuBar::item:pressed {{
    background-color: {farben["accent"]};
    color: #ffffff;
}}

QMenu {{
    background-color: {farben["bg"]};
    border: 1px solid {farben["border"]};
    padding: 4px;
}}
QMenu::item {{
    padding: 5px 24px 5px 12px;
    border-radius: {radius["button"]}px;
}}
QMenu::item:selected {{
    background-color: {farben["accent"]};
    color: #ffffff;
}}
QMenu::item:disabled {{
    color: {farben["text_muted"]};
}}
QMenu::separator {{
    height: 1px;
    background: {farben["border"]};
    margin: 4px 8px;
}}

QToolBar {{
    background-color: {farben["surface"]};
    border: none;
    border-bottom: 1px solid {farben["border"]};
    spacing: 2px;
    padding: 3px;
}}
QToolButton {{
    border: none;
    border-radius: {radius["button"]}px;
    padding: 4px;
}}
QToolButton:hover {{
    background-color: {farben["border"]};
}}
QToolButton:pressed {{
    background-color: {farben["accent"]};
}}

QDockWidget {{
    font-weight: 600;
    titlebar-close-icon: none;
}}
QDockWidget::title {{
    background-color: {farben["surface"]};
    border-bottom: 1px solid {farben["border"]};
    padding: 5px 8px;
}}

QTabWidget::pane {{
    border: 1px solid {farben["border"]};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {farben["surface"]};
    border: 1px solid {farben["border"]};
    border-bottom: none;
    padding: 6px 14px;
    margin-right: 1px;
}}
QTabBar::tab:selected {{
    background-color: {farben["bg"]};
    border-bottom: 2px solid {farben["accent"]};
    color: {farben["accent"]};
    font-weight: 600;
}}
QTabBar::tab:!selected:hover {{
    background-color: {farben["border"]};
}}

QTreeWidget, QListWidget, QTableWidget {{
    background-color: {farben["bg"]};
    border: 1px solid {farben["border"]};
    border-radius: {radius["input"]}px;
    font-size: {basis_pt}pt;
    show-decoration-selected: 1;
}}
QTreeWidget::item, QListWidget::item {{
    padding: 3px 2px;
    border: 1px solid transparent;
    border-radius: {radius["input"]}px;
}}
QTreeView::item:hover, QListView::item:hover, QTableView::item:hover {{
    background-color: {_mit_alpha(farben["accent"], 0.08)};
}}
QTreeView::item:selected, QListView::item:selected, QTableView::item:selected {{
    background-color: {_mit_alpha(farben["accent"], 0.18)};
    color: {farben["text"]};
    border: 1px solid {_mit_alpha(farben["accent"], 0.45)};
}}
QTreeView::branch {{
    background-color: transparent;
}}
QHeaderView::section {{
    background-color: {farben["surface"]};
    color: {farben["text"]};
    border: none;
    border-bottom: 1px solid {farben["border"]};
    padding: 4px 6px;
}}

QStatusBar {{
    background-color: {farben["surface"]};
    border-top: 1px solid {farben["border"]};
}}

QPushButton {{
    background-color: {farben["surface"]};
    border: 1px solid {farben["border"]};
    border-radius: {radius["button"]}px;
    padding: 5px 14px;
}}
QPushButton:hover {{
    background-color: {farben["accent"]};
    color: #ffffff;
    border-color: {farben["accent"]};
}}
QPushButton:pressed {{
    background-color: {farben["focus"]};
    color: #ffffff;
}}
QPushButton:disabled {{
    color: {farben["text_muted"]};
}}

QLineEdit, QPlainTextEdit, QComboBox, QSpinBox {{
    background-color: {farben["bg"]};
    border: 1px solid {farben["border"]};
    border-radius: {radius["input"]}px;
    padding: 3px 6px;
    selection-background-color: {farben["accent"]};
    selection-color: #ffffff;
}}
QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
    border: 1px solid {farben["focus"]};
}}

QScrollBar:vertical {{
    background: transparent;
    width: 12px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {farben["border"]};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {farben["accent"]};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 12px;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {farben["border"]};
    border-radius: 5px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: {farben["accent"]};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}
"""
