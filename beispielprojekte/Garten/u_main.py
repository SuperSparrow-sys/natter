"""Eigener Formular-Code. Zeigt Projekte aus mehreren Units (Abschnitt
7.4): `u_pflanzen.py`, `u_garten.py`, `u_main.py`.
"""

from u_garten import Garten
from u_main_design import Form1Design
from u_pflanzen import Pflanze


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        self.garten = Garten()

    def b_pflanzen_click(self, sender) -> None:
        name = self.e_name.text
        try:
            wasserbedarf = int(self.e_wasserbedarf.text)
        except ValueError:
            return

        pflanze = Pflanze(name, wasserbedarf)
        self.garten.pflanzen(pflanze)
        self.lb_beete.items.add(f"{pflanze.name} (Wasserbedarf: {pflanze.wasserbedarf})")

        self.e_name.text = ""
        self.e_wasserbedarf.text = ""
