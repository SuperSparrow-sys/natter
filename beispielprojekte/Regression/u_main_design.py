# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Button, Chart, Form, Label, StringGrid


class Form1Design(Form):
    l_titel: Label
    sg_messwerte: StringGrid
    ch_punkte: Chart
    b_rechnen: Button
    l_steigung: Label
    l_achsenabschnitt: Label
    l_bestimmtheit: Label
    l_vorhersage: Label

    def create_components(self):
        self.caption = "Körpergröße und Schuhgröße"
        self.width = 860
        self.height = 560
        self.on_create = self.form_create

        self.l_titel = Label(self)
        self.l_titel.left = 16
        self.l_titel.top = 12
        self.l_titel.width = 420
        self.l_titel.caption = "Hängt die Schuhgröße von der Körpergröße ab?"

        self.sg_messwerte = StringGrid(self)
        self.sg_messwerte.left = 16
        self.sg_messwerte.top = 44
        self.sg_messwerte.width = 300
        self.sg_messwerte.height = 380
        self.sg_messwerte.col_count = 2
        self.sg_messwerte.row_count = 16

        self.ch_punkte = Chart(self)
        self.ch_punkte.left = 332
        self.ch_punkte.top = 44
        self.ch_punkte.width = 500
        self.ch_punkte.height = 380
        self.ch_punkte.kind = "scatter"
        self.ch_punkte.title = "Messwerte mit Regressionsgerade"
        self.ch_punkte.x_label = "Körpergröße in cm"
        self.ch_punkte.y_label = "Schuhgröße"
        self.ch_punkte.legend = True
        self.ch_punkte.grid = True

        self.b_rechnen = Button(self)
        self.b_rechnen.left = 16
        self.b_rechnen.top = 440
        self.b_rechnen.width = 170
        self.b_rechnen.caption = "Regression berechnen"
        self.b_rechnen.on_click = self.b_rechnen_click

        self.l_steigung = Label(self)
        self.l_steigung.left = 204
        self.l_steigung.top = 446
        self.l_steigung.width = 200
        self.l_steigung.caption = "Steigung: –"

        self.l_achsenabschnitt = Label(self)
        self.l_achsenabschnitt.left = 204
        self.l_achsenabschnitt.top = 472
        self.l_achsenabschnitt.width = 200
        self.l_achsenabschnitt.caption = "Achsenabschnitt: –"

        self.l_bestimmtheit = Label(self)
        self.l_bestimmtheit.left = 204
        self.l_bestimmtheit.top = 498
        self.l_bestimmtheit.width = 260
        self.l_bestimmtheit.caption = "Bestimmtheitsmaß: –"

        self.l_vorhersage = Label(self)
        self.l_vorhersage.left = 480
        self.l_vorhersage.top = 446
        self.l_vorhersage.width = 340
        self.l_vorhersage.caption = "Vorhersage für 175 cm: –"
