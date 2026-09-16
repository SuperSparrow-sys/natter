# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Button, Form, Label, StringGrid


class Form1Design(Form):
    l_titel: Label
    b_wuerfeln: Button
    l_zahl: Label
    l_punkte: Label
    l_leben: Label
    sg_tabelle: StringGrid
    b_speichern: Button
    b_html_exportieren: Button

    def create_components(self):
        self.caption = "Würfelspiel"
        self.width = 469
        self.height = 611
        self.theme = "system"
        self.on_create = self.form_create

        self.l_titel = Label(self)
        self.l_titel.caption = "Würfelspiel"
        self.l_titel.left = 88
        self.l_titel.top = 64
        self.l_titel.width = 101
        self.l_titel.height = 25

        self.b_wuerfeln = Button(self)
        self.b_wuerfeln.caption = "Würfeln"
        self.b_wuerfeln.left = 264
        self.b_wuerfeln.top = 128
        self.b_wuerfeln.width = 75
        self.b_wuerfeln.height = 25
        self.b_wuerfeln.on_click = self.b_wuerfeln_click

        self.l_zahl = Label(self)
        self.l_zahl.caption = "Gewürfelte Zahl:"
        self.l_zahl.left = 72
        self.l_zahl.top = 133
        self.l_zahl.width = 116
        self.l_zahl.height = 20

        self.l_punkte = Label(self)
        self.l_punkte.caption = "Punkte: "
        self.l_punkte.left = 132
        self.l_punkte.top = 176
        self.l_punkte.width = 57
        self.l_punkte.height = 20

        self.l_leben = Label(self)
        self.l_leben.caption = "Leben:"
        self.l_leben.left = 132
        self.l_leben.top = 216
        self.l_leben.width = 46
        self.l_leben.height = 20

        self.sg_tabelle = StringGrid(self)
        self.sg_tabelle.left = 64
        self.sg_tabelle.top = 272
        self.sg_tabelle.width = 312
        self.sg_tabelle.height = 144
        self.sg_tabelle.row_count = 1
        self.sg_tabelle.col_count = 2

        self.b_speichern = Button(self)
        self.b_speichern.caption = "Speichern und Beenden"
        self.b_speichern.left = 112
        self.b_speichern.top = 448
        self.b_speichern.width = 232
        self.b_speichern.height = 32

        self.b_html_exportieren = Button(self)
        self.b_html_exportieren.caption = "Highscore als HTML exportieren"
        self.b_html_exportieren.left = 88
        self.b_html_exportieren.top = 496
        self.b_html_exportieren.width = 280
        self.b_html_exportieren.height = 32
        self.b_html_exportieren.on_click = self.b_html_exportieren_click
