"""Eigener Formular-Code (Abschnitt 4.3). Nachgebildet aus
referenz/lazarus/q_Würfelspiel/unit1.pas.
"""

import random

from pcl import input_box, open_url
from u_main_design import Form1Design


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        self.leben = 3
        self.punkte = 0
        self.zahl = 0

        self.sg_tabelle.cells[0, 0] = "Name"
        self.sg_tabelle.cells[1, 0] = "Punkte"

        self._anzeige_aktualisieren()

    def b_wuerfeln_click(self, sender) -> None:
        self.zahl = random.randint(1, 6)
        if self.zahl == 6:
            self.leben -= 1
        else:
            self.punkte += self.zahl

        self._anzeige_aktualisieren()

        if self.leben == 0:
            name = input_box("VERLOREN", "Bitte gib deinen Namen ein", "")
            self.b_wuerfeln.enabled = False

            self.sg_tabelle.row_count += 1
            letzte_zeile = self.sg_tabelle.row_count - 1
            self.sg_tabelle.cells[0, letzte_zeile] = name
            self.sg_tabelle.cells[1, letzte_zeile] = str(self.punkte)

            self.punkte = 0
            self.leben = 3
            self._anzeige_aktualisieren()

            self.b_wuerfeln.enabled = True

    def _anzeige_aktualisieren(self) -> None:
        self.l_zahl.caption = f"Gewürfelte Zahl: {self.zahl}"
        self.l_punkte.caption = f"Punkte: {self.punkte}"
        self.l_leben.caption = f"Leben: {self.leben}"

    def b_html_exportieren_click(self, sender) -> None:
        """M5, Schritt 9 (Abnahme): Highscore als HTML im Browser
        (Abschnitt 11.3), originalgetreu nach dem Beispielcode dort."""
        zeilen_html = "\n".join(
            f"<tr><td>{self.sg_tabelle.cells[0, zeile]}</td>"
            f"<td>{self.sg_tabelle.cells[1, zeile]}</td></tr>"
            for zeile in range(1, self.sg_tabelle.row_count)
        )
        with open("highscore.html", "w", encoding="utf-8") as datei:
            datei.write("<!DOCTYPE html>\n<html><body>\n")
            datei.write("<h1>Highscore</h1>\n")
            datei.write("<table border='1'><tr><th>Name</th><th>Punkte</th></tr>\n")
            datei.write(zeilen_html + "\n")
            datei.write("</table>\n</body></html>\n")

        open_url("highscore.html")
