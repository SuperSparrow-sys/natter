# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Button, Form, Label, Shape


class Form1Design(Form):
    b_einschalten: Button
    b_wechseln: Button
    b_auschalten: Button
    l_titel: Label
    s_gehaeuse: Shape
    s_rot: Shape
    s_gelb: Shape
    s_gruen: Shape

    def create_components(self):
        self.caption = "Ampel"
        self.width = 620
        self.height = 736
        self.theme = "system"
        self.on_create = self.form_create

        self.b_einschalten = Button(self)
        self.b_einschalten.caption = "Einschalten"
        self.b_einschalten.left = 392
        self.b_einschalten.top = 184
        self.b_einschalten.width = 75
        self.b_einschalten.height = 25
        self.b_einschalten.on_click = self.b_einschalten_click

        self.b_wechseln = Button(self)
        self.b_wechseln.caption = "Wechseln"
        self.b_wechseln.left = 400
        self.b_wechseln.top = 223
        self.b_wechseln.width = 75
        self.b_wechseln.height = 25
        self.b_wechseln.on_click = self.b_wechseln_click

        self.b_auschalten = Button(self)
        self.b_auschalten.caption = "Auschalten"
        self.b_auschalten.left = 413
        self.b_auschalten.top = 262
        self.b_auschalten.width = 75
        self.b_auschalten.height = 25
        self.b_auschalten.on_click = self.b_auschalten_click

        self.l_titel = Label(self)
        self.l_titel.caption = "Ampel Simulator"
        self.l_titel.left = 128
        self.l_titel.top = 67
        self.l_titel.width = 192
        self.l_titel.height = 32

        self.s_gehaeuse = Shape(self)
        self.s_gehaeuse.shape = "rectangle"
        self.s_gehaeuse.left = 135
        self.s_gehaeuse.top = 160
        self.s_gehaeuse.width = 169
        self.s_gehaeuse.height = 330
        self.s_gehaeuse.brush.color = "#808080"

        self.s_rot = Shape(self)
        self.s_rot.shape = "circle"
        self.s_rot.left = 170
        self.s_rot.top = 176
        self.s_rot.width = 96
        self.s_rot.height = 89
        self.s_rot.brush.color = "#000000"

        self.s_gelb = Shape(self)
        self.s_gelb.shape = "circle"
        self.s_gelb.left = 169
        self.s_gelb.top = 272
        self.s_gelb.width = 97
        self.s_gelb.height = 89
        self.s_gelb.brush.color = "#000000"

        self.s_gruen = Shape(self)
        self.s_gruen.shape = "circle"
        self.s_gruen.left = 176
        self.s_gruen.top = 376
        self.s_gruen.width = 90
        self.s_gruen.height = 80
        self.s_gruen.brush.color = "#000000"
