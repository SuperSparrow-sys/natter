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

`load_csv`, `load_query` und `load_grid` (M10, Punkt 3) enden alle in
demselben `pandas.DataFrame` unter `dataframe`. Intern gibt es damit nur
**einen** Datenweg: `_daten_zeichnen()` und `add_regression()` müssen
nichts darüber wissen, ob die Zahlen aus einer Datei, aus der Datenbank
oder aus einer Tabelle auf dem Formular kommen. Fehlerfälle (fehlende
Datei, unbekannte Spalte, Spalte ohne Zahlen) ergeben eine deutsche
Meldung aus `pcl.errors` statt eines Tracebacks.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtWidgets import QWidget
from shiboken6 import isValid

from pcl.control import Control
from pcl.errors import NatterDatenDateiError, NatterDatenError
from pcl.properties import Prop
from pcl.theme import _tokens_laden, theme_aufloesen

if TYPE_CHECKING:
    import pandas as pd

    from pcl.analyse import Regressionsergebnis

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


# Anzahl der Stützstellen einer Regressionskurve. Für eine Gerade
# reichten zwei; Exponential- und Logarithmuskurven brauchen mehr, sonst
# sähe man das Polygon statt der Kurve. Eine Zahl für alle Arten, damit
# keine Art heimlich anders gezeichnet wird.
_KURVENPUNKTE = 100

# Schriftgröße der Legende in Punkt (matplotlib-Vorgabe wäre 10).
_LEGENDENSCHRIFT = 8
#: Wie breit ein Zeichen der Titelschrift im Mittel ist, gemessen an
#: der Schriftgröße. Grober, aber verlässlicher Richtwert für
#: Proportionalschriften; genauer ginge es nur mit dem Renderer, den es
#: vor dem ersten Zeichnen noch nicht gibt.
_ZEICHENBREITE = 0.55


def _theme_farben(theme: str) -> dict[str, str]:
    return _tokens_laden()["color"][theme_aufloesen(theme)]


def _spaltenliste(spalten: list[Any]) -> str:
    """Vorhandene Spalten für eine Fehlermeldung – in derselben Form wie
    `SQLQuery._spalten_index()` in `pcl/components/data_access.py`."""
    return ", ".join(str(spalte) for spalte in spalten)


def _trennzeichen_erkennen(datei: Path) -> str:
    """Rät das Spaltentrennzeichen aus der Kopfzeile einer CSV-Datei.

    Nicht `pandas.read_csv(sep=None)`: dessen Erkennung über
    `csv.Sniffer` wirft bei einer leeren oder einspaltigen Datei
    ``_csv.Error: Could not determine delimiter`` – statt einer Meldung
    über die leere Datei sähe eine Schülerin dann einen Traceback aus
    der Standardbibliothek (im Test aufgefallen). Das häufigste Zeichen
    der Kopfzeile genügt; ohne Treffer bleibt es beim Komma.
    """
    with datei.open(encoding="utf-8", errors="replace") as strom:
        kopfzeile = strom.readline()
    haeufigstes = max((";", "\t", ","), key=kopfzeile.count)
    return haeufigstes if kopfzeile.count(haeufigstes) else ","


def _als_zahlen(spalte: pd.Series, spaltenname: Any, quelle: str) -> pd.Series:
    """Wandelt eine Spalte in Zahlen um oder meldet auf Deutsch, warum
    das nicht geht (M10, Punkt 3: „Spalte enthält keine Zahlen“).

    Zweiter Anlauf mit Dezimalkomma: die eingecheckte Beispiel-CSV des
    Projekts (`beispielprojekte/CsvAuswertung/daten/verkauf.csv`) ist wie
    fast jeder deutsche Tabellenexport `1200,50` statt `1200.50`. Ohne
    diesen Anlauf müsste jede Schülerin `decimal=","` kennen, bevor sie
    ihr erstes Diagramm sieht. Vorsicht bleibt: `1,234` wird dabei als
    1,234 gelesen, nicht als Tausendertrennung.

    Leere Zellen (ein `StringGrid` ist anfangs voll davon) gelten nicht
    als Fehler, sondern als fehlender Wert – matplotlib lässt dort
    einfach eine Lücke.
    """
    import pandas as pd

    leer = spalte.isna() | (spalte.astype(str).str.strip() == "")
    kandidaten = [spalte]
    # Nicht `dtype == object` abfragen: pandas 3 liest Textspalten als
    # eigenen `str`-Datentyp ein, nicht mehr als `object` - die Abfrage
    # wäre für eine CSV-Spalte immer falsch und der zweite Anlauf käme
    # nie zustande.
    if not pd.api.types.is_numeric_dtype(spalte):
        kandidaten.append(spalte.astype(str).str.strip().str.replace(",", ".", regex=False))

    for kandidat in kandidaten:
        zahlen = pd.to_numeric(kandidat, errors="coerce")
        if not (zahlen.isna() & ~leer).any() and zahlen.notna().any():
            return zahlen

    if bool(leer.all()):
        raise NatterDatenError(
            f"Die Spalte „{spaltenname}“ in {quelle} ist leer und enthält keine Zahlen."
        )
    # Hier kommt nur an, wer den ersten Anlauf nicht bestanden hat -
    # diese Werte sind also wirklich die, die sich nicht umwandeln
    # lassen, nicht bloß alle nicht leeren.
    fehlerhafte = spalte[pd.to_numeric(spalte, errors="coerce").isna() & ~leer]
    raise NatterDatenError(
        f"Die Spalte „{spaltenname}“ in {quelle} enthält nicht nur Zahlen. Gefunden "
        f"wurde zum Beispiel der Wert {fehlerhafte.iloc[0]!r}."
    )


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
        # Einziger Datenweg (M10, Abschnitt 7): load_csv/load_query/
        # load_grid enden alle hier, Diagramm und Regression wissen
        # nichts über die Herkunft der Zahlen.
        self._dataframe: pd.DataFrame | None = None
        self._x_spalte: Any = None
        self._y_spalte: Any = None
        self._quelle = ""
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

    # -- Daten laden (M10, Punkt 3) --------------------------------------

    @property
    def dataframe(self) -> pd.DataFrame | None:
        """Die zuletzt geladenen Daten als pandas-`DataFrame`, oder
        `None`, solange nichts geladen wurde. `load_csv`, `load_query`
        und `load_grid` füllen dieselbe Eigenschaft."""
        return self._dataframe

    def load_csv(
        self,
        pfad: str,
        x: str | int,
        y: str | int,
        *,
        sep: str | None = None,
        decimal: str | None = None,
    ) -> None:
        """Liest eine CSV-Datei ein und zeigt sie in der über `kind`
        gewählten Art an.

        `x` und `y` sind Spaltennamen oder Spaltennummern (0 für die
        erste Spalte). Das Trennzeichen wird ohne `sep` selbst erkannt –
        deutsche Tabellen mit Semikolon funktionieren damit genauso wie
        englische mit Komma.

        Beispiel::

            self.ch_diagramm.load_csv("daten/verkauf.csv", "region", "umsatz")
        """
        import pandas as pd

        datei = Path(pfad)
        if not datei.is_file():
            raise NatterDatenDateiError(
                f"Die Datei „{pfad}“ wurde nicht gefunden. Gesucht wurde vom "
                f"Arbeitsverzeichnis {Path.cwd()} aus."
            )
        trennzeichen = sep if sep is not None else _trennzeichen_erkennen(datei)
        if decimal and decimal == trennzeichen:
            raise NatterDatenError(
                f"Trennzeichen und Dezimalzeichen sind beide „{trennzeichen}“ – so "
                "lässt sich nicht unterscheiden, wo eine Spalte endet und wo eine "
                "Nachkommastelle beginnt."
            )
        try:
            daten = pd.read_csv(datei, sep=trennzeichen, decimal=decimal or ".")
        except pd.errors.EmptyDataError as fehler:
            raise NatterDatenError(f"Die Datei „{pfad}“ enthält keine Daten.") from fehler
        except pd.errors.ParserError as fehler:
            raise NatterDatenError(
                f"Die Datei „{pfad}“ lässt sich nicht als Tabelle lesen: {fehler}"
            ) from fehler
        self._daten_uebernehmen(daten, x, y, f"der Datei „{pfad}“")

    def load_query(
        self,
        verbindung: Any,
        sql: str,
        *,
        x: str | int | None = None,
        y: str | int | None = None,
    ) -> None:
        """Füllt das Diagramm aus einer Datenbankabfrage über eine
        `SQLite3Connection` (M5).

        Ohne `x`/`y` werden die ersten beiden Spalten des Ergebnisses
        genommen – ``SELECT region, umsatz FROM verkauf`` liefert dann
        genau das erwartete Diagramm.
        """
        from pcl.components.data_access import SQLQuery

        abfrage = SQLQuery(verbindung)
        abfrage.sql = sql
        self._daten_uebernehmen(abfrage.to_dataframe(), x, y, "der Datenbankabfrage")

    def load_grid(
        self,
        stringgrid: Any,
        *,
        x: str | int | None = None,
        y: str | int | None = None,
    ) -> None:
        """Füllt das Diagramm aus einem `StringGrid` desselben Formulars
        – der häufigste Weg im Unterricht: Daten erst als Tabelle zeigen,
        dann als Diagramm. Die Spaltenköpfe stehen wie bei
        `StringGrid.to_dataframe()` in Zeile 0."""
        self._daten_uebernehmen(stringgrid.to_dataframe(), x, y, "der Tabelle")

    def _daten_uebernehmen(
        self, daten: pd.DataFrame, x: str | int | None, y: str | int | None, quelle: str
    ) -> None:
        x_spalte = self._spalte_waehlen(daten, x, "x", quelle, 0)
        y_spalte = self._spalte_waehlen(daten, y, "y", quelle, 1)
        # Erst prüfen, dann übernehmen: eine unbrauchbare y-Spalte darf
        # das zuvor geladene Diagramm nicht halb überschreiben. Das
        # Ergebnis wird verworfen - `_daten_zeichnen()` rechnet gleich
        # noch einmal, dafür aber immer aus dem aktuellen Zustand.
        _als_zahlen(daten[y_spalte], y_spalte, quelle)

        self._dataframe = daten
        self._x_spalte = x_spalte
        self._y_spalte = y_spalte
        self._quelle = quelle
        self._daten_zeichnen()

    def _spalte_waehlen(
        self,
        daten: pd.DataFrame,
        auswahl: str | int | None,
        rolle: str,
        quelle: str,
        vorgabe: int,
    ) -> Any:
        """Löst eine Spaltenangabe (Name, Nummer oder nichts) in einen
        Spaltennamen auf."""
        spalten = list(daten.columns)
        if auswahl is None:
            if len(spalten) <= vorgabe:
                raise NatterDatenError(
                    f"Für die {rolle}-Werte braucht {quelle} mindestens {vorgabe + 1} "
                    f"Spalten. Vorhanden sind {len(spalten)}: {_spaltenliste(spalten)}."
                )
            return spalten[vorgabe]
        if isinstance(auswahl, int) and not isinstance(auswahl, bool):
            if not -len(spalten) <= auswahl < len(spalten):
                raise NatterDatenError(
                    f"Die Spaltennummer {auswahl} gibt es in {quelle} nicht. Die "
                    f"Tabelle hat {len(spalten)} Spalten (0 bis {len(spalten) - 1}): "
                    f"{_spaltenliste(spalten)}."
                )
            return spalten[auswahl]
        if auswahl in spalten:
            return auswahl
        raise NatterDatenError(
            f"Die Spalte „{auswahl}“ gibt es in {quelle} nicht. Vorhandene Spalten: "
            f"{_spaltenliste(spalten)}."
        )

    def _daten_zeichnen(self) -> None:
        """Zeichnet die geladenen Daten in der über `kind` gewählten Art.

        Geht bewusst über die vorhandenen `add_*_series`-Methoden statt
        selbst zu malen – so gilt für geladene Daten dieselbe Färbung,
        Beschriftung und Legendenbehandlung wie für Daten aus dem Code.

        Rechnet die Zahlen jedes Mal neu aus dem `DataFrame` aus, statt
        sie zu merken: so zeichnet ein späterer Wechsel von `kind`
        dieselben Daten neu, ohne dass die Quelle noch einmal gelesen
        werden müsste.
        """
        titel = str(self._y_spalte)
        x_werte = self._dataframe[self._x_spalte]
        y_werte = _als_zahlen(self._dataframe[self._y_spalte], self._y_spalte, self._quelle)

        self._leeren()
        art = self.kind
        if art == "line":
            self.add_line_series(x_werte, y_werte, title=titel)
        elif art == "pie":
            # matplotlib beschriftet Kreisstücke mit Textobjekten; Zahlen
            # aus einer Spalte müssen dafür erst Text werden.
            self.add_pie_series([str(wert) for wert in x_werte], y_werte, title=titel)
        elif art == "scatter":
            self.add_scatter_series(x_werte, y_werte, title=titel)
        elif art == "histogram":
            self.add_histogram_series(y_werte, title=titel)
        elif art == "boxplot":
            self.add_boxplot_series(y_werte, title=titel)
        else:
            self.add_bar_series(x_werte, y_werte, title=titel)

    # -- Regression (M10, Punkt 5) ---------------------------------------

    def add_regression(
        self,
        x: Any = None,
        y: Any = None,
        art: str = "linear",
        *,
        grad: int = 2,
    ) -> Regressionsergebnis:
        """Legt die Regressionsgerade bzw. -kurve über die vorhandenen
        Punkte und schreibt die Formel in die Legende.

        Ohne `x` und `y` werden die zuletzt geladenen Daten genommen.
        Gibt das `Regressionsergebnis` zurück, damit Steigung,
        Achsenabschnitt und Bestimmtheitsmaß gleich in Beschriftungs-
        felder geschrieben werden können::

            ergebnis = self.ch_diagramm.add_regression()
            self.l_steigung.caption = f"Steigung: {ergebnis.steigung:.2f}"
        """
        import numpy as np

        from pcl.analyse import regression

        x_werte, y_werte = self._regressionsdaten(x, y)
        ergebnis = regression(x_werte, y_werte, art, grad=grad)

        self._beispiel_verwerfen()
        zahlen = np.asarray(x_werte, dtype=float)
        kurve_x = np.linspace(float(zahlen.min()), float(zahlen.max()), _KURVENPUNKTE)
        self._achse.plot(
            kurve_x,
            ergebnis.vorhersage(kurve_x),
            color=self._naechste_farbe(),
            label=ergebnis.formel,
        )
        # Ohne Legende wäre die Formel nirgends zu sehen; das Einschalten
        # gehört deshalb zur Aufgabe dieser Methode und ist keine
        # Nebenwirkung, die der Aufrufer selbst nachholen müsste.
        self.legend = True
        self._nach_serie("")
        return ergebnis

    def _regressionsdaten(self, x: Any, y: Any) -> tuple[Any, Any]:
        if x is not None and y is not None:
            return x, y
        if x is not None or y is not None:
            raise NatterDatenError(
                "add_regression() braucht entweder beide Reihen (x und y) oder gar "
                "keine – dann rechnet sie mit den zuvor geladenen Daten."
            )
        if self._dataframe is None:
            raise NatterDatenError(
                "add_regression() ohne x und y rechnet mit den zuvor geladenen Daten. "
                "Es wurden aber noch keine geladen – erst load_csv(), load_query() "
                "oder load_grid() aufrufen."
            )
        return (
            _als_zahlen(self._dataframe[self._x_spalte], self._x_spalte, self._quelle),
            _als_zahlen(self._dataframe[self._y_spalte], self._y_spalte, self._quelle),
        )

    def clear(self) -> None:
        """Leert das Diagramm vollständig – auch die geladenen Daten.

        Die Daten mitzuvergessen ist nicht selbstverständlich, aber die
        einzige widerspruchsfreie Lesart: bliebe der `DataFrame` stehen,
        würde ein anschließendes ``kind = "line"`` das gerade geleerte
        Diagramm wieder füllen, und ``add_regression()`` ohne Argumente
        würde mit Daten rechnen, von denen nichts mehr zu sehen ist.
        Das Zeichnen geladener Daten braucht dagegen nur die leere
        Achse und nicht das Vergessen – dafür gibt es `_leeren()`.
        """
        self._leeren()
        self._dataframe = None
        self._x_spalte = None
        self._y_spalte = None
        self._quelle = ""

    def _leeren(self) -> None:
        """Leert nur die Zeichenfläche, ohne die geladenen Daten zu
        vergessen."""
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
        # Gitternetz **hinter** die Daten. In der Sichtprüfung gefunden:
        # matplotlib zeichnet es ohne diese Zeile darüber, und bei
        # `grid = True` läuft dann durch jeden Balken eine helle
        # senkrechte Linie, als wäre er zerschnitten.
        self._achse.set_axisbelow(True)
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
        self._achse.set_title(self._umgebrochener_titel(self.title or self._serientitel))
        self._achse.set_xlabel(self.x_label)
        self._achse.set_ylabel(self.y_label)
        if self.grid:
            self._achse.grid(True, color=farben["border"])
        else:
            self._achse.grid(False)

        vorhandene_legende = self._achse.get_legend()
        beschriftete, _ = self._achse.get_legend_handles_labels()
        if self.legend and beschriftete and not self._ist_kreisdiagramm():
            # Kleinere Schrift als matplotlibs Vorgabe (10 pt): in einem
            # 320x240-Diagramm nimmt eine Legendenzeile wie
            # "y = 6,44·x² + 182,31·x + 1014,51" sonst fast die ganze
            # Breite ein, und `loc="best"` findet keinen Platz mehr, der
            # keine Punkte verdeckt. In der Sichtprüfung lag der oberste
            # Messpunkt komplett unter dem Legendenkasten.
            legende = self._achse.legend(fontsize=_LEGENDENSCHRIFT)
            legende.get_frame().set_facecolor(farben["bg"])
            legende.get_frame().set_edgecolor(farben["border"])
            for text in legende.get_texts():
                text.set_color(farben["text"])
        elif vorhandene_legende is not None:
            vorhandene_legende.remove()

    def _umgebrochener_titel(self, text: str) -> str:
        """Bricht einen zu langen Titel auf mehrere Zeilen um.

        In der Sichtprüfung **abgeschnitten**: aus „Schuhgröße nach
        Körpergröße" wurde in einem 320 Pixel breiten Diagramm
        „Schuhgröße nach Körpergroes". matplotlib kürzt einen Titel
        nicht und macht auch keinen Platz dafür – es malt ihn einfach
        über den Rand hinaus, und die Figur schneidet ab. Ein Umbruch
        ist hier besser als eine kleinere Schrift: der Titel steht ganz
        oben und soll lesbar bleiben.
        """
        text = str(text)
        if not text.strip():
            return text
        import textwrap

        # Die Breite kommt aus dem Prop, nicht aus `get_size_inches()`:
        # die Figur erfährt ihre wirkliche Größe erst, wenn Qt das Widget
        # das erste Mal auslegt - beim Setzen des Titels steht dort noch
        # matplotlibs Vorgabe von 6,4 Zoll, und der Umbruch fiele viel zu
        # großzügig aus.
        punkte = self.width * 72 / (self._figure.get_dpi() or 100)
        groesse = self._achse.title.get_fontsize()
        # Etwas Rand lassen, damit der Titel nicht genau an der Kante endet
        je_zeile = max(12, int(punkte * 0.9 / (groesse * _ZEICHENBREITE)))
        if len(text) <= je_zeile:
            return text
        return textwrap.fill(text, je_zeile)

    def _ist_kreisdiagramm(self) -> bool:
        """Ob gerade Kreisstücke gezeichnet sind.

        Ein Kreisdiagramm bekommt **keine** Legende, auch wenn `legend`
        gesetzt ist: seine Stücke tragen ihre Beschriftung schon selbst.
        In der Sichtprüfung standen die Kategorien dadurch doppelt da,
        und der Legendenkasten deckte ein Stück samt Beschriftung zu.
        Gefragt wird nach dem, was wirklich gemalt ist, und nicht nach
        `kind` – sonst würde ein `add_pie_series()` bei `kind = "bar"`
        durchrutschen.
        """
        from matplotlib.patches import Wedge

        return any(isinstance(teil, Wedge) for teil in self._achse.patches)

    def _nach_serie(self, title: str) -> None:
        if title:
            self._serientitel = title
        self._beschriftung_anwenden()
        self._neu_zeichnen()

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "kind":
            # Von Hand über `add_*_series` gezeichnete Serien bleiben
            # stehen: `kind` bestimmt nur, was ohne eigenen Aufruf zu
            # sehen ist. Geladene Daten (M10, Punkt 3) gehören dazu -
            # sie sind ja gerade nach `kind` gezeichnet worden und
            # sollen die neue Art sofort annehmen.
            if self._dataframe is not None:
                self._daten_zeichnen()
            elif self._beispiel_sichtbar:
                self._beispiel_zeichnen()
        elif name in ("title", "x_label", "y_label", "legend", "grid", "width"):
            # `width` ist dabei, weil der Titelumbruch von ihr abhängt
            self._beschriftung_anwenden()
            self._neu_zeichnen()
