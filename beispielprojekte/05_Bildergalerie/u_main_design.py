# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Button, Form, Image, Label, ListBox


class Form1Design(Form):
    l_titel: Label
    b_hinzufuegen: Button
    b_entfernen: Button
    lb_bilder: ListBox
    i_vorschau: Image
    l_info: Label

    def create_components(self):
        self.caption = "Bildergalerie"
        self.width = 800
        self.height = 560
        self.on_create = self.form_create

        self.l_titel = Label(self)
        self.l_titel.left = 24
        self.l_titel.top = 16
        self.l_titel.width = 300
        self.l_titel.height = 28
        self.l_titel.caption = "Meine Bildergalerie"

        self.b_hinzufuegen = Button(self)
        self.b_hinzufuegen.left = 24
        self.b_hinzufuegen.top = 56
        self.b_hinzufuegen.width = 240
        self.b_hinzufuegen.caption = "Bild hinzufügen …"
        self.b_hinzufuegen.on_click = self.b_hinzufuegen_click

        self.b_entfernen = Button(self)
        self.b_entfernen.left = 24
        self.b_entfernen.top = 96
        self.b_entfernen.width = 240
        self.b_entfernen.caption = "Aus der Galerie nehmen"
        self.b_entfernen.on_click = self.b_entfernen_click

        self.lb_bilder = ListBox(self)
        self.lb_bilder.left = 24
        self.lb_bilder.top = 144
        self.lb_bilder.width = 240
        self.lb_bilder.height = 340
        self.lb_bilder.on_change = self.lb_bilder_change

        self.i_vorschau = Image(self)
        self.i_vorschau.left = 288
        self.i_vorschau.top = 56
        self.i_vorschau.width = 480
        self.i_vorschau.height = 380

        self.l_info = Label(self)
        self.l_info.left = 288
        self.l_info.top = 452
        self.l_info.width = 480
        self.l_info.height = 40
        self.l_info.caption = "Noch kein Bild ausgewählt."
