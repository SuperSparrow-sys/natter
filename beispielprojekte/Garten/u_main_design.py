# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Button, Edit, Form, ListBox


class Form1Design(Form):
    e_name: Edit
    e_wasserbedarf: Edit
    b_pflanzen: Button
    lb_beete: ListBox

    def create_components(self):
        self.caption = "Garten"
        self.width = 400
        self.height = 300
        self.theme = "system"
        self.on_create = self.form_create

        self.e_name = Edit(self)
        self.e_name.left = 16
        self.e_name.top = 16
        self.e_name.width = 150
        self.e_name.height = 23

        self.e_wasserbedarf = Edit(self)
        self.e_wasserbedarf.left = 180
        self.e_wasserbedarf.top = 16
        self.e_wasserbedarf.width = 80
        self.e_wasserbedarf.height = 23

        self.b_pflanzen = Button(self)
        self.b_pflanzen.caption = "Pflanzen"
        self.b_pflanzen.left = 270
        self.b_pflanzen.top = 16
        self.b_pflanzen.width = 100
        self.b_pflanzen.height = 25
        self.b_pflanzen.on_click = self.b_pflanzen_click

        self.lb_beete = ListBox(self)
        self.lb_beete.left = 16
        self.lb_beete.top = 56
        self.lb_beete.width = 354
        self.lb_beete.height = 200
