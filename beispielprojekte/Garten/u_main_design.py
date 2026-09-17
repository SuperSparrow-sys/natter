# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Button, Edit, Form, Label, ListBox


class Form1Design(Form):
    l_name: Label
    l_wasserbedarf: Label
    e_name: Edit
    e_wasserbedarf: Edit
    b_pflanzen: Button
    lb_beete: ListBox

    def create_components(self):
        self.caption = "Garten"
        self.width = 400
        self.height = 320
        self.theme = "system"
        self.on_create = self.form_create

        # Beschriftungen für die beiden Eingabefelder (Nutzer-Feedback
        # September 2026: ohne sie war nicht erkennbar, wofür die
        # Felder gedacht sind).
        self.l_name = Label(self)
        self.l_name.caption = "Name:"
        self.l_name.left = 16
        self.l_name.top = 12
        self.l_name.width = 150
        self.l_name.height = 15

        self.l_wasserbedarf = Label(self)
        self.l_wasserbedarf.caption = "Wasserbedarf:"
        self.l_wasserbedarf.left = 180
        self.l_wasserbedarf.top = 12
        self.l_wasserbedarf.width = 180
        self.l_wasserbedarf.height = 15

        self.e_name = Edit(self)
        self.e_name.left = 16
        self.e_name.top = 30
        self.e_name.width = 150
        self.e_name.height = 23

        self.e_wasserbedarf = Edit(self)
        self.e_wasserbedarf.left = 180
        self.e_wasserbedarf.top = 30
        self.e_wasserbedarf.width = 80
        self.e_wasserbedarf.height = 23

        self.b_pflanzen = Button(self)
        self.b_pflanzen.caption = "Pflanzen"
        self.b_pflanzen.left = 270
        self.b_pflanzen.top = 30
        self.b_pflanzen.width = 100
        self.b_pflanzen.height = 25
        self.b_pflanzen.on_click = self.b_pflanzen_click

        self.lb_beete = ListBox(self)
        self.lb_beete.left = 16
        self.lb_beete.top = 70
        self.lb_beete.width = 354
        self.lb_beete.height = 200
