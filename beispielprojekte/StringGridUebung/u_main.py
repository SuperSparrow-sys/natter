"""Eigener Formular-Code (Abschnitt 4.3). Nachgebildet aus
referenz/lazarus/g_StringGrid/unit1.pas.
"""

from pcl import show_message
from u_main_design import Form1Design


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        self.zeile = 1
        self.sg_tabelle.cells[0, 0] = "Nr."
        self.sg_tabelle.cells[1, 0] = "Name"
        self.sg_tabelle.cells[2, 0] = "Vorname"
        self.sg_tabelle.cells[3, 0] = "Geb.-Dat."

    def b_uebernehmen_click(self, sender) -> None:
        name = self.e_name.text
        vorname = self.e_vorname.text
        datum = self.e_datum.text

        self.sg_tabelle.row_count = self.zeile + 1

        if len(name) > 10 or len(vorname) > 10:
            show_message("Deinen Eingaben sind zu Lang")
            self.zeile -= 1
        else:
            self.sg_tabelle.cells[0, self.zeile] = str(self.zeile)
            self.sg_tabelle.cells[1, self.zeile] = name
            self.sg_tabelle.cells[2, self.zeile] = vorname
            self.sg_tabelle.cells[3, self.zeile] = datum

        self.zeile += 1

    def b_zuruecksetzen_click(self, sender) -> None:
        self.zeile = 1
        self.sg_tabelle.row_count = self.zeile + 1
        self.sg_tabelle.cells[0, self.zeile] = ""
        self.sg_tabelle.cells[1, self.zeile] = ""
        self.sg_tabelle.cells[2, self.zeile] = ""
        self.sg_tabelle.cells[3, self.zeile] = ""

    def b_schliessen_click(self, sender) -> None:
        self.close()
