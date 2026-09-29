# Automatisch erzeugt aus u_info.pfm - nicht bearbeiten
from pcl import Button, Form, Label


class FormInfoDesign(Form):
    l_titel: Label
    l_text: Label
    b_ok: Button

    def create_components(self):
        self.caption = "Über das Notizbuch"
        self.width = 320
        self.height = 150

        self.l_titel = Label(self)
        self.l_titel.left = 16
        self.l_titel.top = 16
        self.l_titel.width = 288
        self.l_titel.height = 24
        self.l_titel.caption = "Notizbuch"
        self.l_titel.font.size = 12
        self.l_titel.font.bold = True

        self.l_text = Label(self)
        self.l_text.left = 16
        self.l_text.top = 48
        self.l_text.width = 288
        self.l_text.height = 48
        self.l_text.caption = "Ein Beispiel für ein Menü, eine Textdatei und ein zweites Fenster."

        self.b_ok = Button(self)
        self.b_ok.left = 229
        self.b_ok.top = 112
        self.b_ok.caption = "OK"
        self.b_ok.default = True
        self.b_ok.on_click = self.b_ok_click
