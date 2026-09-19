# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Button, Chart, ComboBox, Form, Label, StringGrid


class Form1Design(Form):
    l_titel: Label
    b_laden: Button
    l_ort: Label
    cb_ort: ComboBox
    b_speichern: Button
    sg_tabelle: StringGrid
    ch_verlauf: Chart
    l_ergebnis: Label

    def create_components(self):
        self.caption = "CSV-Auswertung"
        self.width = 900
        self.height = 620
        self.on_create = self.form_create

        self.l_titel = Label(self)
        self.l_titel.left = 24
        self.l_titel.top = 16
        self.l_titel.width = 420
        self.l_titel.height = 28
        self.l_titel.caption = "Wetterdaten auswerten"

        self.b_laden = Button(self)
        self.b_laden.left = 24
        self.b_laden.top = 56
        self.b_laden.width = 200
        self.b_laden.caption = "Andere CSV laden …"
        self.b_laden.on_click = self.b_laden_click

        self.l_ort = Label(self)
        self.l_ort.left = 248
        self.l_ort.top = 60
        self.l_ort.width = 60
        self.l_ort.caption = "Ort:"

        self.cb_ort = ComboBox(self)
        self.cb_ort.left = 300
        self.cb_ort.top = 56
        self.cb_ort.width = 200
        self.cb_ort.on_change = self.cb_ort_change

        self.b_speichern = Button(self)
        self.b_speichern.left = 520
        self.b_speichern.top = 56
        self.b_speichern.width = 220
        self.b_speichern.caption = "Auswertung speichern"
        self.b_speichern.on_click = self.b_speichern_click

        self.sg_tabelle = StringGrid(self)
        self.sg_tabelle.left = 24
        self.sg_tabelle.top = 104
        self.sg_tabelle.width = 420
        self.sg_tabelle.height = 400
        self.sg_tabelle.row_count = 1
        self.sg_tabelle.col_count = 3

        self.ch_verlauf = Chart(self)
        self.ch_verlauf.left = 464
        self.ch_verlauf.top = 104
        self.ch_verlauf.width = 410
        self.ch_verlauf.height = 400
        self.ch_verlauf.kind = "line"
        self.ch_verlauf.title = "Temperatur im Jahresverlauf"
        self.ch_verlauf.x_label = "Monat"
        self.ch_verlauf.y_label = "Grad Celsius"
        self.ch_verlauf.grid = True

        self.l_ergebnis = Label(self)
        self.l_ergebnis.left = 24
        self.l_ergebnis.top = 520
        self.l_ergebnis.width = 850
        self.l_ergebnis.height = 70
        self.l_ergebnis.caption = ""
