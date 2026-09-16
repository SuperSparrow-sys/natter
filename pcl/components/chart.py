"""Chart-Komponente (Abschnitt 11.6): Balken-, Linien-, Kreis- und
Punktdiagramme über eingebettetes matplotlib (`FigureCanvasQTAgg`).
Nimmt Listen oder pandas-Serien entgegen – matplotlib versteht beide
Formen direkt, eine Umwandlung ist nicht nötig.

Farben kommen aus `design/tokens.json`: Accent/Success/Danger als kleine,
sich wiederholende Serienpalette – die Tokens-Datei definiert bisher
keine eigene, größere Diagrammpalette (nur die drei Statusfarben), daher
diese pragmatische Wiederverwendung statt neuer, nicht freigegebener
Tokens. Ein Diagramm färbt sich beim Erzeugen einmalig nach dem
aktuellen Theme ein; ein späterer Theme-Wechsel zur Laufzeit wirkt (wie
bei allen `pcl`-Komponenten) nicht automatisch auf bereits gezeichnete
Diagramme zurück.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget

from pcl.control import Control
from pcl.theme import _tokens_laden, theme_aufloesen


def _farbpalette(theme: str) -> list[str]:
    farben = _tokens_laden()["color"][theme_aufloesen(theme)]
    return [farben["accent"], farben["success"], farben["danger"]]


class Chart(Control):
    """Diagrammanzeige. Qt-Basis: `FigureCanvasQTAgg` (matplotlib)."""

    def __init__(self, parent: Control, *, theme: str = "system") -> None:
        from matplotlib.figure import Figure

        self._theme = theme
        self._figure = Figure()
        self._achse = self._figure.add_subplot(111)
        self._serienanzahl = 0
        super().__init__(parent)
        self._farben_anwenden()

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

        canvas = FigureCanvasQTAgg(self._figure)
        canvas.setParent(eltern_widget)
        return canvas

    def add_bar_series(self, kategorien: Any, werte: Any, *, title: str = "") -> None:
        self._achse.bar(kategorien, werte, color=self._naechste_farbe())
        self._nach_serie(title)

    def add_line_series(self, x: Any, y: Any, *, title: str = "") -> None:
        self._achse.plot(x, y, color=self._naechste_farbe())
        self._nach_serie(title)

    def add_pie_series(self, labels: Any, werte: Any, *, title: str = "") -> None:
        palette = _farbpalette(self._theme)
        anzahl = len(list(werte))
        farben = [palette[i % len(palette)] for i in range(anzahl)]
        self._achse.pie(werte, labels=labels, colors=farben)
        self._serienanzahl += anzahl
        self._nach_serie(title)

    def add_scatter_series(self, x: Any, y: Any, *, title: str = "") -> None:
        self._achse.scatter(x, y, color=self._naechste_farbe())
        self._nach_serie(title)

    def clear(self) -> None:
        self._achse.clear()
        self._serienanzahl = 0
        self._farben_anwenden()
        self._qwidget.draw_idle()

    def _naechste_farbe(self) -> str:
        palette = _farbpalette(self._theme)
        farbe = palette[self._serienanzahl % len(palette)]
        self._serienanzahl += 1
        return farbe

    def _farben_anwenden(self) -> None:
        farben = _tokens_laden()["color"][theme_aufloesen(self._theme)]
        self._figure.set_facecolor(farben["bg"])
        self._achse.set_facecolor(farben["bg"])
        for seite in self._achse.spines.values():
            seite.set_color(farben["border"])
        self._achse.tick_params(colors=farben["text"])
        self._achse.xaxis.label.set_color(farben["text"])
        self._achse.yaxis.label.set_color(farben["text"])
        self._achse.title.set_color(farben["text"])

    def _nach_serie(self, title: str) -> None:
        if title:
            self._achse.set_title(title)
        self._figure.tight_layout()
        self._qwidget.draw_idle()
