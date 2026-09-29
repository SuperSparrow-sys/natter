# Stufe 11 von 11 - mit der Maus auf eine Zeichenfläche malen.
#
# Neu gegenüber den bisherigen Stufen:
#   PaintBox       eine freie Zeichenfläche; gemalt wird über ihre
#                  canvas mit move_to() und line_to()
#   Maus           on_mouse_down, on_mouse_move und on_mouse_up
#                  bekommen x und y dazu, gezählt von der linken oberen
#                  Ecke der Fläche
#   Farben         die vier Farbfelder sind Panels. Alle vier rufen
#                  dieselbe Methode auf; welches geklickt wurde, steht
#                  in sender.
#   color_dialog   fragt nach einer beliebigen Farbe
#
# Die Fläche wächst mit dem Fenster (anchors), was schon gemalt ist,
# bleibt dabei stehen.

from pcl import color_dialog
from u_main_design import Form1Design


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        self.farbe = "#000000"
        # Ob gerade eine Maustaste gedrückt ist. on_mouse_move kommt
        # auch ohne gedrückte Taste; gemalt wird nur dann.
        self.malt = False

    # -- Malen -----------------------------------------------------

    def pb_flaeche_mouse_down(self, sender, x, y) -> None:
        self.malt = True
        stift = self.pb_flaeche.canvas
        stift.pen.color = self.farbe
        stift.pen.width = self.tb_dicke.position
        stift.move_to(x, y)
        # Ein Klick ohne Bewegung soll auch einen Punkt hinterlassen.
        stift.line_to(x + 1, y)

    def pb_flaeche_mouse_move(self, sender, x, y) -> None:
        if self.malt:
            self.pb_flaeche.canvas.line_to(x, y)

    def pb_flaeche_mouse_up(self, sender, x, y) -> None:
        self.malt = False

    # -- Farbe und Dicke -------------------------------------------

    def farbe_click(self, sender) -> None:
        self.farbe = sender.color

    def b_farbe_click(self, sender) -> None:
        neu = color_dialog(self.farbe)
        # Bei „Abbrechen“ kommt ein leerer Text zurück, dann bleibt
        # die bisherige Farbe.
        if neu:
            self.farbe = neu

    def tb_dicke_change(self, sender) -> None:
        self.l_dicke.caption = f"Dicke: {self.tb_dicke.position}"

    def b_leeren_click(self, sender) -> None:
        self.pb_flaeche.clear()
