# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Button, CheckBox, ComboBox, Edit, Form, Label, ListBox, Memo, RadioButton, ScrollBar


class Form1Design(Form):
    l_Kassenzettel: Label
    l_eingabeSorte: Label
    l_grundpreis: Label
    b_hinzufuegen: Button
    m_zettel: Memo
    b_zettelLeer: Button
    e_eingabeSorte: Edit
    e_Grundpreis: Edit
    Label1: Label
    c_kaese: CheckBox
    c_knoblauch: CheckBox
    sb_behinderung: ScrollBar
    cb_mws: ComboBox
    Label2: Label
    lb_KurzWahl: ListBox
    l_groesse: Label
    rb_small: RadioButton
    rb_normal: RadioButton
    rb_XL: RadioButton
    rb_XXL: RadioButton
    rb_XXXL: RadioButton
    l_mws: Label
    l_kurzwahl: Label
    l_zettel: Label

    def create_components(self):
        self.caption = "Pizza-Kassenzettel"
        self.width = 624
        self.height = 734
        self.on_create = self.form_create

        self.l_Kassenzettel = Label(self)
        self.l_Kassenzettel.left = 61
        self.l_Kassenzettel.top = 32
        self.l_Kassenzettel.width = 166
        self.l_Kassenzettel.height = 38
        self.l_Kassenzettel.caption = "Kassenzettel"
        self.l_Kassenzettel.font.name = "Bodoni MT"
        self.l_Kassenzettel.font.size = 24
        self.l_Kassenzettel.font.bold = True

        self.l_eingabeSorte = Label(self)
        self.l_eingabeSorte.left = 61
        self.l_eingabeSorte.top = 88
        self.l_eingabeSorte.width = 95
        self.l_eingabeSorte.height = 21
        self.l_eingabeSorte.caption = "Pizzasorte: "
        self.l_eingabeSorte.font.size = 12
        self.l_eingabeSorte.font.bold = True

        self.l_grundpreis = Label(self)
        self.l_grundpreis.left = 63
        self.l_grundpreis.top = 124
        self.l_grundpreis.width = 290
        self.l_grundpreis.height = 21
        self.l_grundpreis.caption = "Grundpreis:                        EUR"
        self.l_grundpreis.font.size = 12
        self.l_grundpreis.font.bold = True

        self.b_hinzufuegen = Button(self)
        self.b_hinzufuegen.left = 61
        self.b_hinzufuegen.top = 352
        self.b_hinzufuegen.width = 219
        self.b_hinzufuegen.caption = "zum Kassenzettel hinzufügen"
        self.b_hinzufuegen.on_click = self.b_hinzufuegen_click

        self.m_zettel = Memo(self)
        self.m_zettel.left = 65
        self.m_zettel.top = 408
        self.m_zettel.width = 214
        self.m_zettel.height = 140
        self.m_zettel.read_only = True

        self.b_zettelLeer = Button(self)
        self.b_zettelLeer.left = 64
        self.b_zettelLeer.top = 560
        self.b_zettelLeer.width = 215
        self.b_zettelLeer.caption = "Kassenzettel leeren"
        self.b_zettelLeer.on_click = self.b_zettel_leer_click

        self.e_eingabeSorte = Edit(self)
        self.e_eingabeSorte.left = 152
        self.e_eingabeSorte.top = 88
        self.e_eingabeSorte.width = 128
        self.e_eingabeSorte.height = 23

        self.e_Grundpreis = Edit(self)
        self.e_Grundpreis.left = 158
        self.e_Grundpreis.top = 124
        self.e_Grundpreis.width = 82
        self.e_Grundpreis.height = 23

        self.Label1 = Label(self)
        self.Label1.left = 64
        self.Label1.top = 160
        self.Label1.width = 70
        self.Label1.height = 15
        self.Label1.caption = "Optionen"

        self.c_kaese = CheckBox(self)
        self.c_kaese.left = 150
        self.c_kaese.top = 158
        self.c_kaese.width = 120
        self.c_kaese.height = 19
        self.c_kaese.caption = "Käserand?"

        self.c_knoblauch = CheckBox(self)
        self.c_knoblauch.left = 150
        self.c_knoblauch.top = 182
        self.c_knoblauch.width = 150
        self.c_knoblauch.height = 19
        self.c_knoblauch.caption = "Extra Knoblauch"

        self.sb_behinderung = ScrollBar(self)
        self.sb_behinderung.left = 66
        self.sb_behinderung.top = 616
        self.sb_behinderung.width = 212
        self.sb_behinderung.height = 17
        self.sb_behinderung.minimum = 5
        self.sb_behinderung.maximum = 50
        self.sb_behinderung.position = 5
        self.sb_behinderung.on_change = self.sb_behinderung_change

        self.cb_mws = ComboBox(self)
        self.cb_mws.items = ["7", "19"]
        self.cb_mws.left = 376
        self.cb_mws.top = 240
        self.cb_mws.width = 164
        self.cb_mws.height = 23
        self.cb_mws.item_index = 1
        self.cb_mws.text = "19"

        self.Label2 = Label(self)
        self.Label2.left = 64
        self.Label2.top = 594
        self.Label2.width = 150
        self.Label2.height = 15
        self.Label2.caption = "Schriftgöße andern:"

        self.lb_KurzWahl = ListBox(self)
        self.lb_KurzWahl.left = 376
        self.lb_KurzWahl.top = 80
        self.lb_KurzWahl.width = 164
        self.lb_KurzWahl.height = 120

        self.l_groesse = Label(self)
        self.l_groesse.left = 61
        self.l_groesse.top = 212
        self.l_groesse.width = 130
        self.l_groesse.height = 20
        self.l_groesse.caption = "Größe wählen:"
        self.l_groesse.font.bold = True

        self.rb_small = RadioButton(self)
        self.rb_small.left = 67
        self.rb_small.top = 234
        self.rb_small.width = 120
        self.rb_small.height = 20
        self.rb_small.caption = "Small"

        self.rb_normal = RadioButton(self)
        self.rb_normal.left = 67
        self.rb_normal.top = 256
        self.rb_normal.width = 120
        self.rb_normal.height = 20
        self.rb_normal.caption = "Normal"
        self.rb_normal.checked = True

        self.rb_XL = RadioButton(self)
        self.rb_XL.left = 67
        self.rb_XL.top = 278
        self.rb_XL.width = 120
        self.rb_XL.height = 20
        self.rb_XL.caption = "XL"

        self.rb_XXL = RadioButton(self)
        self.rb_XXL.left = 67
        self.rb_XXL.top = 300
        self.rb_XXL.width = 120
        self.rb_XXL.height = 20
        self.rb_XXL.caption = "XXL"

        self.rb_XXXL = RadioButton(self)
        self.rb_XXXL.left = 67
        self.rb_XXXL.top = 322
        self.rb_XXXL.width = 120
        self.rb_XXXL.height = 20
        self.rb_XXXL.caption = "XXXL"

        self.l_mws = Label(self)
        self.l_mws.left = 376
        self.l_mws.top = 216
        self.l_mws.width = 164
        self.l_mws.height = 18
        self.l_mws.caption = "Mehrwertsteuer (%):"

        self.l_kurzwahl = Label(self)
        self.l_kurzwahl.left = 376
        self.l_kurzwahl.top = 56
        self.l_kurzwahl.width = 164
        self.l_kurzwahl.height = 20
        self.l_kurzwahl.caption = "Pizza-Kurzwahl:"
        self.l_kurzwahl.font.bold = True

        self.l_zettel = Label(self)
        self.l_zettel.left = 65
        self.l_zettel.top = 384
        self.l_zettel.width = 164
        self.l_zettel.height = 20
        self.l_zettel.caption = "Kassenzettel:"
