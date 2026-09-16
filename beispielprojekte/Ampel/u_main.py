"""Eigener Formular-Code (Abschnitt 4.3). Nachgebildet aus
referenz/lazarus/k_Ampel/u_main.pas.
"""

from u_ampel import Ampel
from u_main_design import Form1Design

_FARBE_AUS = "#000000"
_FARBE_ROT = "#ff0000"
_FARBE_GELB = "#ffff00"
_FARBE_GRUEN = "#008000"


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        self.ampel = Ampel(True, 1)
        self.ampel_zeichnen()

    def b_einschalten_click(self, sender) -> None:
        self.ampel.einschalten()
        self.ampel_zeichnen()

    def b_wechseln_click(self, sender) -> None:
        self.ampel.umschalten()
        self.ampel_zeichnen()

    def b_auschalten_click(self, sender) -> None:
        self.ampel.ausschalten()
        self.ampel_zeichnen()

    def ampel_zeichnen(self) -> None:
        if not self.ampel.get_eingeschaltet():
            self.s_gruen.brush.color = _FARBE_AUS
            self.s_rot.brush.color = _FARBE_AUS
            self.s_gelb.brush.color = _FARBE_AUS
            return

        phase = self.ampel.get_zustand()
        if phase == 1:
            self.s_gruen.brush.color = _FARBE_GRUEN
            self.s_rot.brush.color = _FARBE_AUS
            self.s_gelb.brush.color = _FARBE_AUS
        elif phase == 3:
            self.s_gruen.brush.color = _FARBE_AUS
            self.s_rot.brush.color = _FARBE_ROT
            self.s_gelb.brush.color = _FARBE_AUS
        else:  # Phase 2 oder 4
            self.s_gruen.brush.color = _FARBE_AUS
            self.s_rot.brush.color = _FARBE_AUS
            self.s_gelb.brush.color = _FARBE_GELB
