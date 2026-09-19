# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Chart, Form, Label, SpinEdit


class Form1Design(Form):
    l_titel: Label
    ch_streuung: Chart
    l_training: Label
    l_wichtigkeit: Label
    l_frage: Label
    l_gewicht: Label
    se_gewicht: SpinEdit
    l_laenge: Label
    se_laenge: SpinEdit
    l_breite: Label
    se_breite: SpinEdit
    l_antwort: Label
    l_erklaerung: Label

    def create_components(self):
        self.caption = "Obst-Sortierer"
        self.width = 920
        self.height = 640
        self.on_create = self.form_create

        self.l_titel = Label(self)
        self.l_titel.left = 24
        self.l_titel.top = 16
        self.l_titel.width = 560
        self.l_titel.height = 28
        self.l_titel.caption = "Obst-Sortierer: ein Random Forest lernt Apfel, Banane, Orange"

        self.ch_streuung = Chart(self)
        self.ch_streuung.left = 24
        self.ch_streuung.top = 56
        self.ch_streuung.width = 540
        self.ch_streuung.height = 420
        self.ch_streuung.kind = "scatter"
        self.ch_streuung.title = "Die Lernbeispiele"
        self.ch_streuung.x_label = "Länge in mm"
        self.ch_streuung.y_label = "Breite in mm"
        self.ch_streuung.legend = True
        self.ch_streuung.grid = True

        self.l_training = Label(self)
        self.l_training.left = 588
        self.l_training.top = 56
        self.l_training.width = 300
        self.l_training.height = 70
        self.l_training.caption = "Noch nicht gelernt."

        self.l_wichtigkeit = Label(self)
        self.l_wichtigkeit.left = 588
        self.l_wichtigkeit.top = 136
        self.l_wichtigkeit.width = 300
        self.l_wichtigkeit.height = 90
        self.l_wichtigkeit.caption = ""

        self.l_frage = Label(self)
        self.l_frage.left = 588
        self.l_frage.top = 244
        self.l_frage.width = 300
        self.l_frage.caption = "Was ist das für eine Frucht?"

        self.l_gewicht = Label(self)
        self.l_gewicht.left = 588
        self.l_gewicht.top = 276
        self.l_gewicht.width = 110
        self.l_gewicht.caption = "Gewicht in g"

        self.se_gewicht = SpinEdit(self)
        self.se_gewicht.left = 708
        self.se_gewicht.top = 272
        self.se_gewicht.width = 110
        self.se_gewicht.minimum = 50
        self.se_gewicht.maximum = 400
        self.se_gewicht.value = 150
        self.se_gewicht.on_change = self.se_wert_change

        self.l_laenge = Label(self)
        self.l_laenge.left = 588
        self.l_laenge.top = 312
        self.l_laenge.width = 110
        self.l_laenge.caption = "Länge in mm"

        self.se_laenge = SpinEdit(self)
        self.se_laenge.left = 708
        self.se_laenge.top = 308
        self.se_laenge.width = 110
        self.se_laenge.minimum = 30
        self.se_laenge.maximum = 300
        self.se_laenge.value = 80
        self.se_laenge.on_change = self.se_wert_change

        self.l_breite = Label(self)
        self.l_breite.left = 588
        self.l_breite.top = 348
        self.l_breite.width = 110
        self.l_breite.caption = "Breite in mm"

        self.se_breite = SpinEdit(self)
        self.se_breite.left = 708
        self.se_breite.top = 344
        self.se_breite.width = 110
        self.se_breite.minimum = 20
        self.se_breite.maximum = 200
        self.se_breite.value = 75
        self.se_breite.on_change = self.se_wert_change

        self.l_antwort = Label(self)
        self.l_antwort.left = 588
        self.l_antwort.top = 396
        self.l_antwort.width = 300
        self.l_antwort.height = 80
        self.l_antwort.caption = ""

        self.l_erklaerung = Label(self)
        self.l_erklaerung.left = 24
        self.l_erklaerung.top = 496
        self.l_erklaerung.width = 864
        self.l_erklaerung.height = 110
        self.l_erklaerung.caption = ""
