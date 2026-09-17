"""Eigener Formular-Code (Abschnitt 4.3). Nachgebildet aus
referenz/lazarus/a_GUI_Komponenten/unit1.pas - ein erstes
Übungsprojekt zum Platzieren und Verknüpfen von GUI-Komponenten
(Label, Edit, Button). Button1-4 und Label1 sind bewusst noch ohne
Funktion, genau wie im Original - sie zeigen nur, wie mehrere gleiche
Komponenten nebeneinander platziert werden.
"""

from u_main_design import Form1Design


class Form1(Form1Design):
    def b_begruessung_click(self, sender) -> None:
        name = self.e_namenseingabe.text
        if name == "":
            self.l_ausgabe.caption = "Bitte Namen im Eingabefeld eingeben."
        else:
            self.l_ausgabe.caption = f"Sei gegrüßt, {name}!"

    def b_schliessen_click(self, sender) -> None:
        self.close()
