# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Button, Edit, Form, Label


class Form1Design(Form):
    l_ueberschrift: Label
    e_namenseingabe: Edit
    b_begruessung: Button
    l_ausgabe: Label
    label1: Label
    button1: Button
    button2: Button
    button3: Button
    button4: Button
    b_schliessen: Button

    def create_components(self):
        self.caption = "GUI-Komponenten"
        self.width = 520
        self.height = 340

        self.l_ueberschrift = Label(self)
        self.l_ueberschrift.left = 64
        self.l_ueberschrift.top = 30
        self.l_ueberschrift.width = 220
        self.l_ueberschrift.height = 20
        self.l_ueberschrift.caption = "Mein erstes GUI-Projekt"

        self.e_namenseingabe = Edit(self)
        self.e_namenseingabe.left = 64
        self.e_namenseingabe.top = 56
        self.e_namenseingabe.width = 200
        self.e_namenseingabe.height = 23
        self.e_namenseingabe.color = "#ffff00"

        self.b_begruessung = Button(self)
        self.b_begruessung.left = 64
        self.b_begruessung.top = 88
        self.b_begruessung.width = 200
        self.b_begruessung.caption = "Begrüß mich!"
        self.b_begruessung.on_click = self.b_begruessung_click

        self.l_ausgabe = Label(self)
        self.l_ausgabe.left = 62
        self.l_ausgabe.top = 128
        self.l_ausgabe.width = 420
        self.l_ausgabe.height = 15
        self.l_ausgabe.caption = "Bitte Namen im Eingabefeld eingeben."

        self.label1 = Label(self)
        self.label1.left = 68
        self.label1.top = 168
        self.label1.width = 60
        self.label1.height = 15

        self.button1 = Button(self)
        self.button1.left = 68
        self.button1.top = 192
        self.button1.width = 100
        self.button1.caption = "Button1"

        self.button2 = Button(self)
        self.button2.left = 176
        self.button2.top = 192
        self.button2.width = 100
        self.button2.caption = "Button2"

        self.button3 = Button(self)
        self.button3.left = 68
        self.button3.top = 224
        self.button3.width = 100
        self.button3.caption = "Button3"

        self.button4 = Button(self)
        self.button4.left = 176
        self.button4.top = 224
        self.button4.width = 100
        self.button4.caption = "Button4"

        self.b_schliessen = Button(self)
        self.b_schliessen.left = 68
        self.b_schliessen.top = 270
        self.b_schliessen.width = 208
        self.b_schliessen.height = 33
        self.b_schliessen.caption = "Schließen"
        self.b_schliessen.on_click = self.b_schliessen_click
