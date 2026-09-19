# Stufe 8 von 9 - aus Daten eine Regel ableiten.
#
# Neu gegenüber Stufe 7:
#   Regression     legt eine Kurve durch die Messpunkte
#   Bestimmtheitsmaß   sagt, wie gut die Kurve zu den Punkten passt
#   Vorhersage     rechnet mit dieser Kurve einen Wert aus, den
#                  niemand gemessen hat
#
# Bisher hat das Programm angezeigt, was in den Daten steht. Hier zieht
# es zum ersten Mal einen Schluss daraus - das ist der Übergang von
# "Daten anzeigen" zu "aus Daten lernen".
#
# Wichtig zum Mitdenken: eine Vorhersage außerhalb des gemessenen
# Bereichs ist geraten, nicht gewusst. Das Bestimmtheitsmaß sagt nur,
# wie gut die Kurve die *vorhandenen* Punkte trifft.

import csv
from pathlib import Path

from u_main_design import Form1Design

DATEN = Path(__file__).parent / "daten" / "koerpergroesse.csv"

# Die vier Arten, die pcl kennt - in der Reihenfolge, in der man sie
# im Unterricht ausprobiert.
ARTEN = ["linear", "polynomial", "exponentiell", "logarithmisch"]


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        self.groessen: list[float] = []
        self.schuhe: list[float] = []
        self.ergebnis = None

        self.daten_lesen()
        self.cb_art.items = ARTEN
        self.cb_art.item_index = 0  # löst cb_art_change aus

    def daten_lesen(self) -> None:
        with DATEN.open(encoding="utf-8", newline="") as datei:
            for zeile in csv.DictReader(datei, delimiter=";"):
                self.groessen.append(float(zeile["Koerpergroesse"].replace(",", ".")))
                self.schuhe.append(float(zeile["Schuhgroesse"].replace(",", ".")))

    # -- Zeichnen und Rechnen --------------------------------------

    def cb_art_change(self, sender) -> None:
        art = self.cb_art.text or "linear"

        self.ch_punkte.clear()
        self.ch_punkte.add_scatter_series(self.groessen, self.schuhe, title="Messwerte")

        # add_regression legt die Kurve über die Punkte und gibt die
        # Kennzahlen zurück.
        self.ergebnis = self.ch_punkte.add_regression(self.groessen, self.schuhe, art)

        self.l_formel.caption = f"Formel:\n{self.ergebnis.formel}"
        self.l_guete.caption = (
            f"Bestimmtheitsmaß:\n{self.ergebnis.bestimmtheitsmass:.3f}\n"
            f"({self.guete_in_worten()})"
        )
        self.vorhersage_zeigen()
        self.hinweis_zeigen()

    def guete_in_worten(self) -> str:
        """Eine Zahl wie 0,973 sagt Anfängern wenig."""
        wert = self.ergebnis.bestimmtheitsmass
        if wert >= 0.95:
            return "sehr gute Anpassung"
        if wert >= 0.8:
            return "brauchbare Anpassung"
        if wert >= 0.5:
            return "schwache Anpassung"
        return "die Kurve passt nicht zu den Daten"

    def se_groesse_change(self, sender) -> None:
        self.vorhersage_zeigen()
        self.hinweis_zeigen()

    def vorhersage_zeigen(self) -> None:
        if self.ergebnis is None:
            return
        groesse = self.se_groesse.value
        schuh = self.ergebnis.vorhersage(groesse)
        self.l_ergebnis.caption = f"{groesse} cm\n->  Schuhgröße {schuh:.1f}"

    def hinweis_zeigen(self) -> None:
        """Warnt, wenn außerhalb des gemessenen Bereichs vorhergesagt
        wird - genau dort wird eine Regression gern unsinnig."""
        kleinste, groesste = min(self.groessen), max(self.groessen)
        gewaehlt = self.se_groesse.value

        if kleinste <= gewaehlt <= groesste:
            self.l_hinweis.caption = (
                f"Gemessen wurde zwischen {kleinste:.0f} und {groesste:.0f} cm - "
                f"{gewaehlt} cm liegt mittendrin, die Vorhersage steht auf festem Boden."
            )
        else:
            self.l_hinweis.caption = (
                f"Achtung: gemessen wurde nur zwischen {kleinste:.0f} und "
                f"{groesste:.0f} cm. Bei {gewaehlt} cm rechnet die Kurve über die Daten "
                f"hinaus - das ist geraten, nicht gewusst."
            )
