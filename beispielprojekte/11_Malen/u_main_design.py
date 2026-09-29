# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Button, Form, Label, PaintBox, Panel, TrackBar


class Form1Design(Form):
    p_schwarz: Panel
    p_rot: Panel
    p_gruen: Panel
    p_blau: Panel
    b_farbe: Button
    l_dicke: Label
    tb_dicke: TrackBar
    b_leeren: Button
    pb_flaeche: PaintBox

    def create_components(self):
        self.caption = "Malen"
        self.width = 560
        self.height = 420
        self.on_create = self.form_create

        self.p_schwarz = Panel(self)
        self.p_schwarz.left = 8
        self.p_schwarz.top = 10
        self.p_schwarz.width = 28
        self.p_schwarz.height = 28
        self.p_schwarz.caption = ""
        self.p_schwarz.color = "#000000"
        self.p_schwarz.hint = "Schwarz"
        self.p_schwarz.on_click = self.farbe_click

        self.p_rot = Panel(self)
        self.p_rot.left = 40
        self.p_rot.top = 10
        self.p_rot.width = 28
        self.p_rot.height = 28
        self.p_rot.caption = ""
        self.p_rot.color = "#e53935"
        self.p_rot.hint = "Rot"
        self.p_rot.on_click = self.farbe_click

        self.p_gruen = Panel(self)
        self.p_gruen.left = 72
        self.p_gruen.top = 10
        self.p_gruen.width = 28
        self.p_gruen.height = 28
        self.p_gruen.caption = ""
        self.p_gruen.color = "#43a047"
        self.p_gruen.hint = "Grün"
        self.p_gruen.on_click = self.farbe_click

        self.p_blau = Panel(self)
        self.p_blau.left = 104
        self.p_blau.top = 10
        self.p_blau.width = 28
        self.p_blau.height = 28
        self.p_blau.caption = ""
        self.p_blau.color = "#1e88e5"
        self.p_blau.hint = "Blau"
        self.p_blau.on_click = self.farbe_click

        self.b_farbe = Button(self)
        self.b_farbe.left = 142
        self.b_farbe.top = 11
        self.b_farbe.width = 90
        self.b_farbe.caption = "Farbe …"
        self.b_farbe.hint = "Eine beliebige Farbe auswählen"
        self.b_farbe.on_click = self.b_farbe_click

        self.l_dicke = Label(self)
        self.l_dicke.left = 246
        self.l_dicke.top = 14
        self.l_dicke.width = 70
        self.l_dicke.caption = "Dicke: 3"
        self.l_dicke.word_wrap = False

        self.tb_dicke = TrackBar(self)
        self.tb_dicke.left = 316
        self.tb_dicke.top = 8
        self.tb_dicke.width = 130
        self.tb_dicke.minimum = 1
        self.tb_dicke.maximum = 20
        self.tb_dicke.position = 3
        self.tb_dicke.frequency = 0
        self.tb_dicke.on_change = self.tb_dicke_change

        self.b_leeren = Button(self)
        self.b_leeren.left = 477
        self.b_leeren.top = 11
        self.b_leeren.caption = "Leeren"
        self.b_leeren.anchors.left = False
        self.b_leeren.anchors.right = True
        self.b_leeren.on_click = self.b_leeren_click

        self.pb_flaeche = PaintBox(self)
        self.pb_flaeche.left = 8
        self.pb_flaeche.top = 48
        self.pb_flaeche.width = 544
        self.pb_flaeche.height = 364
        self.pb_flaeche.anchors.right = True
        self.pb_flaeche.anchors.bottom = True
        self.pb_flaeche.on_mouse_down = self.pb_flaeche_mouse_down
        self.pb_flaeche.on_mouse_move = self.pb_flaeche_mouse_move
        self.pb_flaeche.on_mouse_up = self.pb_flaeche_mouse_up
