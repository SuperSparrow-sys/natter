# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Chart, ComboBox, Form, Label, SpinEdit


class Form1Design(Form):
    l_titel: Label
    ch_punkte: Chart
    l_art: Label
    cb_art: ComboBox
    l_formel: Label
    l_guete: Label
    l_vorhersage: Label
    se_groesse: SpinEdit
    l_ergebnis: Label
    l_hinweis: Label

    def create_components(self):
        self.caption = "Regression"
        self.width = 900
        self.height = 620
        self.on_create = self.form_create

        self.l_titel = Label(self)
        self.l_titel.left = 24
        self.l_titel.top = 16
        self.l_titel.width = 500
        self.l_titel.height = 28
        self.l_titel.caption = "Körpergröße und Schuhgröße"

        self.ch_punkte = Chart(self)
        self.ch_punkte.left = 24
        self.ch_punkte.top = 56
        self.ch_punkte.width = 560
        self.ch_punkte.height = 440
        self.ch_punkte.kind = "scatter"
        self.ch_punkte.title = "Messwerte mit Ausgleichsgerade"
        self.ch_punkte.x_label = "Körpergröße in cm"
        self.ch_punkte.y_label = "Schuhgröße"
        self.ch_punkte.grid = True

        self.l_art = Label(self)
        self.l_art.left = 608
        self.l_art.top = 60
        self.l_art.width = 260
        self.l_art.caption = "Art der Ausgleichskurve"

        self.cb_art = ComboBox(self)
        self.cb_art.left = 608
        self.cb_art.top = 88
        self.cb_art.width = 260
        self.cb_art.on_change = self.cb_art_change

        self.l_formel = Label(self)
        self.l_formel.left = 608
        self.l_formel.top = 136
        self.l_formel.width = 260
        self.l_formel.height = 50
        self.l_formel.caption = "Formel:"

        self.l_guete = Label(self)
        self.l_guete.left = 608
        self.l_guete.top = 196
        self.l_guete.width = 260
        self.l_guete.height = 50
        self.l_guete.caption = "Bestimmtheitsmaß:"

        self.l_vorhersage = Label(self)
        self.l_vorhersage.left = 608
        self.l_vorhersage.top = 268
        self.l_vorhersage.width = 260
        self.l_vorhersage.caption = "Vorhersage für eine Körpergröße"

        self.se_groesse = SpinEdit(self)
        self.se_groesse.left = 608
        self.se_groesse.top = 296
        self.se_groesse.width = 120
        self.se_groesse.minimum = 120
        self.se_groesse.maximum = 220
        self.se_groesse.value = 180
        self.se_groesse.on_change = self.se_groesse_change

        self.l_ergebnis = Label(self)
        self.l_ergebnis.left = 608
        self.l_ergebnis.top = 336
        self.l_ergebnis.width = 260
        self.l_ergebnis.height = 60
        self.l_ergebnis.caption = ""

        self.l_hinweis = Label(self)
        self.l_hinweis.left = 24
        self.l_hinweis.top = 516
        self.l_hinweis.width = 850
        self.l_hinweis.height = 70
        self.l_hinweis.caption = ""
