"""Eigener Formular-Code (Abschnitt 4.3).

Abnahmebeispiel zu Arbeitspaket M10: eine CSV mit zwei Spalten
einlesen, die Punkte als Punktdiagramm zeigen, eine lineare Regression
darüberlegen und Steigung, Achsenabschnitt und Bestimmtheitsmaß in
Beschriftungsfeldern ausgeben.

Das ganze Formular ist im Designer zusammengeklickt – hier steht nur,
was beim Klick passieren soll. Genau das ist der Punkt: die Daten
kommen mit einem einzigen Aufruf ins Diagramm.
"""

from pathlib import Path

from u_main_design import Form1Design

#: Die CSV liegt neben dieser Datei. Ein fester Pfad wäre auf einem
#: anderen Rechner falsch.
MESSWERTE = Path(__file__).resolve().parent / "messwerte.csv"

#: Für welche Körpergröße die Vorhersage angezeigt wird.
BEISPIELGROESSE = 175


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        self.ch_punkte.load_csv(MESSWERTE, "Koerpergroesse", "Schuhgroesse")
        self._tabelle_fuellen()

    def b_rechnen_click(self, sender) -> None:
        ergebnis = self.ch_punkte.add_regression(art="linear")

        self.l_steigung.caption = f"Steigung: {ergebnis.steigung:.3f}"
        self.l_achsenabschnitt.caption = (
            f"Achsenabschnitt: {ergebnis.achsenabschnitt:.2f}"
        )
        self.l_bestimmtheit.caption = (
            f"Bestimmtheitsmaß: {ergebnis.bestimmtheitsmass:.4f}"
        )
        self.l_vorhersage.caption = (
            f"Vorhersage für {BEISPIELGROESSE} cm: "
            f"{ergebnis.vorhersage(BEISPIELGROESSE):.1f}"
        )

    def _tabelle_fuellen(self) -> None:
        """Dieselben Daten noch einmal als Tabelle – so sieht man die
        Zahlen, aus denen das Diagramm entsteht."""
        daten = self.ch_punkte.dataframe
        # cells[spalte, zeile] - Spalte zuerst, wie in der LCL
        self.sg_messwerte.cells[0, 0] = "Körpergröße"
        self.sg_messwerte.cells[1, 0] = "Schuhgröße"
        for zeile, (groesse, schuh) in enumerate(
            zip(daten.iloc[:, 0], daten.iloc[:, 1], strict=True), start=1
        ):
            self.sg_messwerte.cells[0, zeile] = str(groesse)
            self.sg_messwerte.cells[1, zeile] = str(schuh)

