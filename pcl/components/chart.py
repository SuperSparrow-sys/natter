"""Chart-Komponente (Abschnitt 11.6): Balken-, Linien-, Kreis-, Punkt-,
Histogramm- und Boxplot-Diagramme über eingebettetes matplotlib
(`FigureCanvasQTAgg`). Nimmt Listen oder pandas-Serien entgegen –
matplotlib versteht beide Formen direkt, eine Umwandlung ist nicht nötig.

Farben kommen aus `design/tokens.json`: Accent/Success/Danger als kleine,
sich wiederholende Serienpalette – die Tokens-Datei definiert bisher
keine eigene, größere Diagrammpalette (nur die drei Statusfarben), daher
diese pragmatische Wiederverwendung statt neuer, nicht freigegebener
Tokens. Ein Diagramm färbt sich beim Erzeugen einmalig nach dem
aktuellen Theme ein; ein späterer Theme-Wechsel zur Laufzeit wirkt (wie
bei allen `pcl`-Komponenten) nicht automatisch auf bereits gezeichnete
Diagramme zurück.

`kind` legt fest, was ohne eigenen `add_*_series`-Aufruf zu sehen ist
(M10, Punkt 2): solange keine echten Daten da sind, zeichnet die
Komponente eine kleine Beispielreihe in der gewählten Art. Im Designer
steht damit ein erkennbares Diagramm statt eines leeren Rechtecks; der
erste `add_*_series`-Aufruf im laufenden Programm wirft sie weg. Eine
eigene Designzeit-Erkennung braucht es dafür nicht – `pcl` hat keine,
und „noch keine Daten“ trifft genau die Fälle, in denen eine Vorschau
hilft.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget
from shiboken6 import isValid

from pcl.control import Control
from pcl.properties import Prop
from pcl.theme import _tokens_laden, theme_aufloesen

# Werte von `Chart.kind`. Histogramm und Boxplot stehen bewusst am Ende
# und sind nicht die Vorgabe (M10, Punkt 7: „mit Auswahl, nicht
# standardmäßig“).
_ARTEN = ("bar", "line", "pie", "scatter", "histogram", "boxplot")

# matplotlibs Sentinel für „diese Serie gehört nicht in die Legende“ –
# ohne ihn landen Serien ohne `title` als leere Zeile in der Legende.
_OHNE_LEGENDE = "_nolegend_"

# Beispielreihe für die Vorschau im Designer. Bewusst wenige, gut
# unterscheidbare Werte: bei 320x240 Pixeln muss auch ein Kreisdiagramm
# noch lesbar sein. Die Messwerte sind eine eigene, breitere Reihe, weil
# Histogramm und Boxplot mit vier Werten nichts Erkennbares ergeben.
_BEISPIEL_KATEGORIEN = ("Mo", "Di", "Mi", "Do")
_BEISPIEL_WERTE = (3, 5, 2, 4)
_BEISPIEL_MESSWERTE = (2, 3, 3, 4, 4, 4, 4, 5, 5, 6, 7, 9)


def _theme_farben(theme: str) -> dict[str, str]:
    return _tokens_laden()["color"][theme_aufloesen(theme)]


def _farbpalette(theme: str) -> list[str]:
    """Serienfarben aus `design/tokens.json`.

    Eigener Eintrag `color.<theme>.chart` statt der drei Statusfarben:
    mit dreien lagen in einem Kreisdiagramm mit vier Werten zwei gleich
    gefärbte Stücke nebeneinander (in der Sichtprüfung aufgefallen). Die
    Liste beginnt mit der Akzentfarbe, damit das übliche Diagramm mit
    einer Serie aussieht wie bisher.
    """
    return list(_theme_farben(theme)["chart"])


class Chart(Control):
    """Diagrammanzeige. Qt-Basis: `FigureCanvasQTAgg` (matplotlib)."""

    # Ein Diagramm braucht von Anfang an mehr Fläche als die 75x25 aus
    # `Control`; so klein wäre nach dem Ablegen aus der Palette nur der
    # Rahmen der Figur zu sehen. Als Prop-Standard statt als Eintrag in
    # `_STANDARDGROESSEN` des Designers, damit auch erzeugter Code und
    # eine von Hand geschriebene Komponente dieselbe Größe bekommen.
    width = Prop(int, 320, kategorie="Layout", doc="Breite in Pixeln")
    height = Prop(int, 240, kategorie="Layout", doc="Höhe in Pixeln")

    kind = Prop(
        str,
        "bar",
        kategorie="Darstellung",
        doc=f"Diagrammart: {', '.join(_ARTEN)}",
    )
    title = Prop(str, "", kategorie="Darstellung", doc="Überschrift über dem Diagramm")
    x_label = Prop(str, "", kategorie="Darstellung", doc="Beschriftung der x-Achse")
    y_label = Prop(str, "", kategorie="Darstellung", doc="Beschriftung der y-Achse")
    legend = Prop(
        bool,
        False,
        kategorie="Darstellung",
        doc="Legende mit den Serientiteln anzeigen",
    )
    grid = Prop(bool, False, kategorie="Darstellung", doc="Gitternetzlinien anzeigen")

    def __init__(self, parent: Control, *, theme: str = "system") -> None:
        from matplotlib.figure import Figure

        self._theme = theme
        # `layout="constrained"` statt `tight_layout()`: die Ränder
        # werden bei **jedem** Zeichnen neu berechnet. `tight_layout()`
        # rechnet einmalig und hinterlässt feste Bruchteile - schrumpft
        # das Widget danach auf die 320x240 der Komponente, brauchen die
        # gleich großen Beschriftungen einen größeren Anteil und laufen
        # aus der Figur heraus. Genau das war zu sehen: aus "5.0" an der
        # y-Achse wurde ".0", und die Oberkante des Titels fehlte.
        self._figure = Figure(layout="constrained")
        self._achse = self._figure.add_subplot(111)
        self._serienanzahl = 0
        # Titel aus dem `title=`-Argument von `add_*_series`. Getrennt vom
        # gleichnamigen Prop, weil sonst jede spätere Beschriftungs-
        # aktualisierung den per Aufruf gesetzten Titel wieder löschen
        # würde (der Prop ist im Normalfall leer).
        self._serientitel = ""
        self._beispiel_sichtbar = False
        super().__init__(parent)
        # Färbt die Achse gleich mit ein, deshalb kein eigener
        # `_farben_anwenden()`-Aufruf davor.
        self._beispiel_zeichnen()

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

        canvas = FigureCanvasQTAgg(self._figure)
        canvas.setParent(eltern_widget)
        return canvas

    def add_bar_series(self, kategorien: Any, werte: Any, *, title: str = "") -> None:
        self._beispiel_verwerfen()
        self._achse.bar(
            kategorien, werte, color=self._naechste_farbe(), label=title or _OHNE_LEGENDE
        )
        self._nach_serie(title)

    def add_line_series(self, x: Any, y: Any, *, title: str = "") -> None:
        self._beispiel_verwerfen()
        self._achse.plot(x, y, color=self._naechste_farbe(), label=title or _OHNE_LEGENDE)
        self._nach_serie(title)

    def add_pie_series(self, labels: Any, werte: Any, *, title: str = "") -> None:
        self._beispiel_verwerfen()
        palette = _farbpalette(self._theme)
        anzahl = len(list(werte))
        farben = [palette[i % len(palette)] for i in range(anzahl)]
        self._achse.pie(werte, labels=labels, colors=farben, textprops=self._textstil())
        self._serienanzahl += anzahl
        self._nach_serie(title)

    def add_scatter_series(self, x: Any, y: Any, *, title: str = "") -> None:
        self._beispiel_verwerfen()
        self._achse.scatter(x, y, color=self._naechste_farbe(), label=title or _OHNE_LEGENDE)
        self._nach_serie(title)

    def add_histogram_series(self, werte: Any, *, bins: int = 10, title: str = "") -> None:
        """Häufigkeitsverteilung einer einzelnen Messreihe – anders als
        `add_bar_series` bekommt die Methode rohe Einzelwerte und zählt
        selbst, wie oft sie in welchen Bereich fallen."""
        self._beispiel_verwerfen()
        self._achse.hist(
            werte, bins=bins, color=self._naechste_farbe(), label=title or _OHNE_LEGENDE
        )
        self._nach_serie(title)

    def add_boxplot_series(self, werte: Any, *, title: str = "") -> None:
        """Kastengrafik einer Messreihe (Median, Quartile, Ausreißer)."""
        self._beispiel_verwerfen()
        self._boxplot_zeichnen(werte, self._naechste_farbe())
        self._nach_serie(title)

    def clear(self) -> None:
        self._achse.clear()
        self._serienanzahl = 0
        self._serientitel = ""
        # Kein Zurückfallen auf die Beispieldaten: `clear()` ruft nur
        # Programmcode auf, und der meint ein leeres Diagramm.
        self._beispiel_sichtbar = False
        self._farben_anwenden()
        self._beschriftung_anwenden()
        self._neu_zeichnen()

    def _boxplot_zeichnen(self, werte: Any, farbe: str) -> None:
        # matplotlib färbt einen Boxplot nicht über ein einzelnes
        # `color=`, sondern über fünf Teil-Stile; ohne sie bliebe die
        # Grafik schwarz und wäre im dunklen Design unsichtbar.
        stil = {"color": farbe}
        self._achse.boxplot(
            werte,
            boxprops=stil,
            whiskerprops=stil,
            capprops=stil,
            medianprops=stil,
            flierprops={"markeredgecolor": farbe},
        )

    def _beispiel_zeichnen(self) -> None:
        """Zeichnet die Vorschaudaten in der über `kind` gewählten Art."""
        self._achse.clear()
        self._serienanzahl = 0
        self._farben_anwenden()
        self._beispiel_sichtbar = True

        farbe = self._naechste_farbe()
        art = self.kind
        if art == "line":
            self._achse.plot(_BEISPIEL_KATEGORIEN, _BEISPIEL_WERTE, color=farbe, label="Beispiel")
        elif art == "pie":
            palette = _farbpalette(self._theme)
            farben = [palette[i % len(palette)] for i in range(len(_BEISPIEL_WERTE))]
            self._achse.pie(
                _BEISPIEL_WERTE,
                labels=_BEISPIEL_KATEGORIEN,
                colors=farben,
                textprops=self._textstil(),
            )
        elif art == "scatter":
            self._achse.scatter(
                _BEISPIEL_KATEGORIEN, _BEISPIEL_WERTE, color=farbe, label="Beispiel"
            )
        elif art == "histogram":
            self._achse.hist(_BEISPIEL_MESSWERTE, bins=5, color=farbe, label="Beispiel")
        elif art == "boxplot":
            self._boxplot_zeichnen(_BEISPIEL_MESSWERTE, farbe)
        else:
            # Unbekannte Werte landen wie bei `Shape.shape` auf der
            # Vorgabe, statt die Anzeige mit einem Fehler abzubrechen.
            self._achse.bar(_BEISPIEL_KATEGORIEN, _BEISPIEL_WERTE, color=farbe, label="Beispiel")

        self._beschriftung_anwenden()
        self._neu_zeichnen()

    def _beispiel_verwerfen(self) -> None:
        """Räumt die Vorschau weg, sobald die erste echte Serie kommt –
        sonst stünden Beispiel- und echte Daten nebeneinander im selben
        Diagramm."""
        if not self._beispiel_sichtbar:
            return
        self._beispiel_sichtbar = False
        self._achse.clear()
        self._serienanzahl = 0
        self._farben_anwenden()

    def _naechste_farbe(self) -> str:
        palette = _farbpalette(self._theme)
        farbe = palette[self._serienanzahl % len(palette)]
        self._serienanzahl += 1
        return farbe

    def _neu_zeichnen(self) -> None:
        """Zeichnet neu – aber nur, solange es das Qt-Widget noch gibt.

        `draw_idle()` merkt sich das Neuzeichnen und führt es erst im
        nächsten Durchlauf der Ereignisschleife aus. Ist das Formular
        bis dahin geschlossen, ist das C++-Objekt der Leinwand weg und
        matplotlib bricht mit `RuntimeError: libshiboken: Internal C++
        object (FigureCanvasQTAgg) already deleted` ab – als Traceback
        auf der Konsole, mitten im Programm einer Schülerin. Deshalb
        wird hier direkt gezeichnet: die Diagramme sind klein, und ein
        nicht eingeplantes Neuzeichnen kann auch nicht zu spät kommen.
        """
        if isValid(self._qwidget):
            self._qwidget.draw()

    def _textstil(self) -> dict[str, str]:
        """Textfarbe für Beschriftungen, die matplotlib selbst erzeugt.

        Die Stücke eines Kreisdiagramms werden nicht über die Achsen
        beschriftet, deshalb erreicht `tick_params()` sie nicht: im
        dunklen Theme standen sie sonst fast schwarz auf dunklem Grund
        (in der Sichtprüfung aufgefallen).
        """
        return {"color": _theme_farben(self._theme)["text"]}

    def _farben_anwenden(self) -> None:
        farben = _theme_farben(self._theme)
        self._figure.set_facecolor(farben["bg"])
        self._achse.set_facecolor(farben["bg"])
        for seite in self._achse.spines.values():
            seite.set_color(farben["border"])
        self._achse.tick_params(colors=farben["text"])
        self._achse.xaxis.label.set_color(farben["text"])
        self._achse.yaxis.label.set_color(farben["text"])
        self._achse.title.set_color(farben["text"])

    def _beschriftung_anwenden(self) -> None:
        """Überträgt `title`, `x_label`, `y_label`, `legend` und `grid`
        auf die Achse – aus einer Hand, damit eine Prop-Änderung nicht
        versehentlich eine der anderen Beschriftungen zurücksetzt."""
        farben = _theme_farben(self._theme)
        # Ein per `add_*_series(title=...)` gesetzter Titel gilt weiter,
        # solange der Prop leer ist - so bleibt vorhandener Schülercode
        # unverändert wirksam.
        self._achse.set_title(self.title or self._serientitel)
        self._achse.set_xlabel(self.x_label)
        self._achse.set_ylabel(self.y_label)
        if self.grid:
            self._achse.grid(True, color=farben["border"])
        else:
            self._achse.grid(False)

        vorhandene_legende = self._achse.get_legend()
        beschriftete, _ = self._achse.get_legend_handles_labels()
        if self.legend and beschriftete:
            legende = self._achse.legend()
            legende.get_frame().set_facecolor(farben["bg"])
            legende.get_frame().set_edgecolor(farben["border"])
            for text in legende.get_texts():
                text.set_color(farben["text"])
        elif vorhandene_legende is not None:
            vorhandene_legende.remove()

    def _nach_serie(self, title: str) -> None:
        if title:
            self._serientitel = title
        self._beschriftung_anwenden()
        self._neu_zeichnen()

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "kind":
            # Echte Daten bleiben stehen: `kind` bestimmt nur, was ohne
            # eigenen `add_*_series`-Aufruf gezeichnet wird.
            if self._beispiel_sichtbar:
                self._beispiel_zeichnen()
        elif name in ("title", "x_label", "y_label", "legend", "grid"):
            self._beschriftung_anwenden()
            self._neu_zeichnen()
