# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Button, Form, Image, Label, Timer


class Form1Design(Form):
    l_titel: Label
    i_keks: Image
    l_hinweis: Label
    l_punkte: Label
    l_rang: Label
    l_werte: Label
    b_teig: Button
    b_helfer: Button
    b_risiko: Button
    b_neu: Button
    l_stil: Label
    i_stil_hell: Image
    i_stil_dunkel: Image
    i_stil_bunt: Image
    t_helfer: Timer

    def create_components(self):
        self.caption = "Cookie-Klicker"
        self.width = 780
        self.height = 560
        self.on_create = self.form_create

        self.l_titel = Label(self)
        self.l_titel.left = 24
        self.l_titel.top = 16
        self.l_titel.width = 300
        self.l_titel.height = 28
        self.l_titel.caption = "Cookie-Klicker"

        self.i_keks = Image(self)
        self.i_keks.left = 24
        self.i_keks.top = 56
        self.i_keks.width = 300
        self.i_keks.height = 300
        self.i_keks.on_click = self.i_keks_click

        self.l_hinweis = Label(self)
        self.l_hinweis.left = 24
        self.l_hinweis.top = 366
        self.l_hinweis.width = 300
        self.l_hinweis.caption = "Klicke auf den Keks."

        self.l_punkte = Label(self)
        self.l_punkte.left = 360
        self.l_punkte.top = 56
        self.l_punkte.width = 380
        self.l_punkte.height = 40
        self.l_punkte.caption = "0 Kekse"

        self.l_rang = Label(self)
        self.l_rang.left = 360
        self.l_rang.top = 104
        self.l_rang.width = 380
        self.l_rang.caption = "Rang: Anfänger"

        self.l_werte = Label(self)
        self.l_werte.left = 360
        self.l_werte.top = 132
        self.l_werte.width = 380
        self.l_werte.caption = "Pro Klick: 1   Helfer: 0"

        self.b_teig = Button(self)
        self.b_teig.left = 360
        self.b_teig.top = 176
        self.b_teig.width = 380
        self.b_teig.caption = "Besserer Teig"
        self.b_teig.on_click = self.b_teig_click

        self.b_helfer = Button(self)
        self.b_helfer.left = 360
        self.b_helfer.top = 216
        self.b_helfer.width = 380
        self.b_helfer.caption = "Helfer anstellen"
        self.b_helfer.on_click = self.b_helfer_click

        self.b_risiko = Button(self)
        self.b_risiko.left = 360
        self.b_risiko.top = 256
        self.b_risiko.width = 380
        self.b_risiko.caption = "Risiko: verdoppeln oder alles verlieren"
        self.b_risiko.on_click = self.b_risiko_click

        self.b_neu = Button(self)
        self.b_neu.left = 360
        self.b_neu.top = 296
        self.b_neu.width = 380
        self.b_neu.caption = "Von vorn anfangen"
        self.b_neu.on_click = self.b_neu_click

        self.l_stil = Label(self)
        self.l_stil.left = 360
        self.l_stil.top = 348
        self.l_stil.width = 380
        self.l_stil.caption = "Aussehen des Kekses:"

        self.i_stil_hell = Image(self)
        self.i_stil_hell.left = 360
        self.i_stil_hell.top = 376
        self.i_stil_hell.width = 72
        self.i_stil_hell.height = 72
        self.i_stil_hell.on_click = self.i_stil_hell_click

        self.i_stil_dunkel = Image(self)
        self.i_stil_dunkel.left = 444
        self.i_stil_dunkel.top = 376
        self.i_stil_dunkel.width = 72
        self.i_stil_dunkel.height = 72
        self.i_stil_dunkel.on_click = self.i_stil_dunkel_click

        self.i_stil_bunt = Image(self)
        self.i_stil_bunt.left = 528
        self.i_stil_bunt.top = 376
        self.i_stil_bunt.width = 72
        self.i_stil_bunt.height = 72
        self.i_stil_bunt.on_click = self.i_stil_bunt_click

        self.t_helfer = Timer(self)
        self.t_helfer.left = 700
        self.t_helfer.top = 392
        self.t_helfer.width = 32
        self.t_helfer.height = 32
        self.t_helfer.enabled = False
        self.t_helfer.interval = 1000
        self.t_helfer.on_timer = self.t_helfer_timer
