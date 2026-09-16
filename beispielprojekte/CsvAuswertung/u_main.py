"""CSV-Auswertung (M5, Schritt 9 - Abnahme): liest eine Beispiel-CSV
ein, wertet sie mit pandas aus (Abschnitt 11.6), zeigt das Ergebnis in
`StringGrid` und `Chart` an - originalgetreu nach dem Beispielcode aus
Abschnitt 11.6.

Kein `u_main_design.py` (wie bei der Kontoverwaltung): für ein
einzelnes, zweckgebundenes Übungsprojekt spart ein `.pfm` hier keine
Arbeit gegenüber dem direkten Aufbau in `create_components()`.
"""

from __future__ import annotations

import pandas as pd

from pcl import Button, Chart, Form, Label, StringGrid


class Form1(Form):
    caption = "CSV-Auswertung"
    width = 640
    height = 340

    def create_components(self) -> None:
        self.l_titel = Label(self)
        self.l_titel.caption = "CSV-Auswertung: Umsatz je Region"
        self.l_titel.left = 16
        self.l_titel.top = 12
        self.l_titel.width = 300

        self.b_auswerten = Button(self)
        self.b_auswerten.caption = "Auswerten"
        self.b_auswerten.left = 16
        self.b_auswerten.top = 44
        self.b_auswerten.width = 100
        self.b_auswerten.on_click = self.b_auswerten_click

        self.sg_auswertung = StringGrid(self)
        self.sg_auswertung.left = 16
        self.sg_auswertung.top = 84
        self.sg_auswertung.width = 280
        self.sg_auswertung.height = 220

        self.ch_umsatz = Chart(self, theme=self.theme)
        self.ch_umsatz.left = 320
        self.ch_umsatz.top = 84
        self.ch_umsatz.width = 300
        self.ch_umsatz.height = 220

    def b_auswerten_click(self, sender) -> None:
        df = pd.read_csv("daten/verkauf.csv", sep=";", decimal=",")
        umsatz = df.groupby("region")["umsatz"].sum()

        self.sg_auswertung.load_dataframe(umsatz.reset_index())
        self.ch_umsatz.clear()
        self.ch_umsatz.add_bar_series(umsatz.index, umsatz.values, title="Umsatz je Region")
