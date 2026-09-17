# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Button, Edit, Form, Label, StringGrid


class Form1Design(Form):
    sg_tabelle: StringGrid
    l_name: Label
    l_vorname: Label
    l_geburtsdatum: Label
    b_uebernehmen: Button
    b_zuruecksetzen: Button
    e_name: Edit
    e_vorname: Edit
    e_datum: Edit
    b_schliessen: Button

    def create_components(self):
        self.caption = "StringGrid-Übung"
        self.width = 738
        self.height = 753
        self.theme = "system"
        self.on_create = self.form_create

        self.sg_tabelle = StringGrid(self)
        self.sg_tabelle.left = 256
        self.sg_tabelle.top = 56
        self.sg_tabelle.width = 344
        self.sg_tabelle.height = 492
        self.sg_tabelle.row_count = 2
        self.sg_tabelle.col_count = 4

        self.l_name = Label(self)
        self.l_name.caption = "Name:"
        self.l_name.left = 57
        self.l_name.top = 72
        self.l_name.width = 90
        self.l_name.height = 15

        self.l_vorname = Label(self)
        self.l_vorname.caption = "Vorname:"
        self.l_vorname.left = 42
        self.l_vorname.top = 98
        self.l_vorname.width = 110
        self.l_vorname.height = 15

        self.l_geburtsdatum = Label(self)
        self.l_geburtsdatum.caption = "Geburtsdatum:"
        self.l_geburtsdatum.left = 13
        self.l_geburtsdatum.top = 128
        self.l_geburtsdatum.width = 190
        self.l_geburtsdatum.height = 15

        self.b_uebernehmen = Button(self)
        self.b_uebernehmen.caption = "Daten in Tabelle übernehmen"
        self.b_uebernehmen.left = 24
        self.b_uebernehmen.top = 176
        self.b_uebernehmen.width = 187
        self.b_uebernehmen.height = 25
        self.b_uebernehmen.on_click = self.b_uebernehmen_click

        self.b_zuruecksetzen = Button(self)
        self.b_zuruecksetzen.caption = "Tabelle zurücksetzen"
        self.b_zuruecksetzen.left = 24
        self.b_zuruecksetzen.top = 208
        self.b_zuruecksetzen.width = 185
        self.b_zuruecksetzen.height = 25
        self.b_zuruecksetzen.on_click = self.b_zuruecksetzen_click

        self.e_name = Edit(self)
        self.e_name.left = 96
        self.e_name.top = 67
        self.e_name.width = 120
        self.e_name.height = 23

        self.e_vorname = Edit(self)
        self.e_vorname.left = 96
        self.e_vorname.top = 98
        self.e_vorname.width = 120
        self.e_vorname.height = 23

        self.e_datum = Edit(self)
        self.e_datum.left = 96
        self.e_datum.top = 128
        self.e_datum.width = 120
        self.e_datum.height = 23

        self.b_schliessen = Button(self)
        self.b_schliessen.caption = "Tabelle schließen"
        self.b_schliessen.left = 24
        self.b_schliessen.top = 264
        self.b_schliessen.width = 184
        self.b_schliessen.height = 25
        self.b_schliessen.on_click = self.b_schliessen_click
