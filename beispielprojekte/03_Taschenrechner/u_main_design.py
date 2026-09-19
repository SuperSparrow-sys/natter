# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Button, Edit, Form, Label


class Form1Design(Form):
    l_titel: Label
    l_zahl1: Label
    e_zahl1: Edit
    l_zahl2: Label
    e_zahl2: Edit
    b_plus: Button
    b_minus: Button
    b_mal: Button
    b_geteilt: Button
    l_ergebnis: Label

    def create_components(self):
        self.caption = "Taschenrechner"
        self.width = 520
        self.height = 340

        self.l_titel = Label(self)
        self.l_titel.left = 24
        self.l_titel.top = 20
        self.l_titel.width = 300
        self.l_titel.height = 28
        self.l_titel.caption = "Taschenrechner"

        self.l_zahl1 = Label(self)
        self.l_zahl1.left = 24
        self.l_zahl1.top = 72
        self.l_zahl1.width = 110
        self.l_zahl1.caption = "Erste Zahl"

        self.e_zahl1 = Edit(self)
        self.e_zahl1.left = 150
        self.e_zahl1.top = 68
        self.e_zahl1.width = 120
        self.e_zahl1.text = "12"

        self.l_zahl2 = Label(self)
        self.l_zahl2.left = 24
        self.l_zahl2.top = 112
        self.l_zahl2.width = 110
        self.l_zahl2.caption = "Zweite Zahl"

        self.e_zahl2 = Edit(self)
        self.e_zahl2.left = 150
        self.e_zahl2.top = 108
        self.e_zahl2.width = 120
        self.e_zahl2.text = "4"

        self.b_plus = Button(self)
        self.b_plus.left = 24
        self.b_plus.top = 160
        self.b_plus.width = 100
        self.b_plus.caption = "+"
        self.b_plus.on_click = self.b_plus_click

        self.b_minus = Button(self)
        self.b_minus.left = 134
        self.b_minus.top = 160
        self.b_minus.width = 100
        self.b_minus.caption = "-"
        self.b_minus.on_click = self.b_minus_click

        self.b_mal = Button(self)
        self.b_mal.left = 244
        self.b_mal.top = 160
        self.b_mal.width = 100
        self.b_mal.caption = "*"
        self.b_mal.on_click = self.b_mal_click

        self.b_geteilt = Button(self)
        self.b_geteilt.left = 354
        self.b_geteilt.top = 160
        self.b_geteilt.width = 100
        self.b_geteilt.caption = "/"
        self.b_geteilt.on_click = self.b_geteilt_click

        self.l_ergebnis = Label(self)
        self.l_ergebnis.left = 24
        self.l_ergebnis.top = 220
        self.l_ergebnis.width = 440
        self.l_ergebnis.height = 40
        self.l_ergebnis.caption = "Ergebnis: -"
