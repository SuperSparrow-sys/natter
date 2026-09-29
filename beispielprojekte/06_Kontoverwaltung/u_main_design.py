# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Button, Edit, Form, Label, StringGrid


class Form1Design(Form):
    l_titel: Label
    sg_konten: StringGrid
    l_neues_konto: Label
    e_inhaber: Edit
    b_anlegen: Button
    l_buchen: Label
    e_nummer: Edit
    e_betrag: Edit
    b_einzahlen: Button
    b_abheben: Button
    l_suche: Label
    e_mindestens: Edit
    b_filtern: Button
    l_meldung: Label

    def create_components(self):
        self.caption = "Kontoverwaltung"
        self.width = 820
        self.height = 560
        self.on_create = self.form_create

        self.l_titel = Label(self)
        self.l_titel.left = 24
        self.l_titel.top = 16
        self.l_titel.width = 400
        self.l_titel.height = 28
        self.l_titel.caption = "Kontoverwaltung"

        self.sg_konten = StringGrid(self)
        self.sg_konten.left = 24
        self.sg_konten.top = 56
        self.sg_konten.width = 480
        self.sg_konten.height = 380
        self.sg_konten.row_count = 1
        self.sg_konten.col_count = 3

        self.l_neues_konto = Label(self)
        self.l_neues_konto.left = 528
        self.l_neues_konto.top = 56
        self.l_neues_konto.width = 260
        self.l_neues_konto.caption = "Neues Konto anlegen"

        self.e_inhaber = Edit(self)
        self.e_inhaber.left = 528
        self.e_inhaber.top = 84
        self.e_inhaber.width = 260
        self.e_inhaber.text = "Erika Musterfrau"

        self.b_anlegen = Button(self)
        self.b_anlegen.left = 528
        self.b_anlegen.top = 120
        self.b_anlegen.width = 260
        self.b_anlegen.caption = "Konto anlegen"
        self.b_anlegen.on_click = self.b_anlegen_click

        self.l_buchen = Label(self)
        self.l_buchen.left = 528
        self.l_buchen.top = 176
        self.l_buchen.width = 260
        self.l_buchen.caption = "Buchen auf Konto Nr."

        self.e_nummer = Edit(self)
        self.e_nummer.left = 528
        self.e_nummer.top = 204
        self.e_nummer.width = 120
        self.e_nummer.text = "1"

        self.e_betrag = Edit(self)
        self.e_betrag.left = 664
        self.e_betrag.top = 204
        self.e_betrag.width = 124
        self.e_betrag.text = "50"

        self.b_einzahlen = Button(self)
        self.b_einzahlen.left = 528
        self.b_einzahlen.top = 244
        self.b_einzahlen.width = 120
        self.b_einzahlen.caption = "Einzahlen"
        self.b_einzahlen.on_click = self.b_einzahlen_click

        self.b_abheben = Button(self)
        self.b_abheben.left = 664
        self.b_abheben.top = 244
        self.b_abheben.width = 124
        self.b_abheben.caption = "Abheben"
        self.b_abheben.on_click = self.b_abheben_click

        self.l_suche = Label(self)
        self.l_suche.left = 528
        self.l_suche.top = 300
        self.l_suche.width = 260
        self.l_suche.caption = "Nur Konten mit mindestens"

        self.e_mindestens = Edit(self)
        self.e_mindestens.left = 528
        self.e_mindestens.top = 328
        self.e_mindestens.width = 120
        self.e_mindestens.text = "0"

        self.b_filtern = Button(self)
        self.b_filtern.left = 664
        self.b_filtern.top = 328
        self.b_filtern.width = 124
        self.b_filtern.caption = "Anzeigen"
        self.b_filtern.on_click = self.b_filtern_click

        self.l_meldung = Label(self)
        self.l_meldung.left = 24
        self.l_meldung.top = 456
        self.l_meldung.width = 764
        self.l_meldung.height = 60
        self.l_meldung.caption = ""
