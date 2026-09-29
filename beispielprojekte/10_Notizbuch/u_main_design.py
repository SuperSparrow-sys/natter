# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Form, Label, MainMenu, Memo


class Form1Design(Form):
    mm_haupt: MainMenu
    m_text: Memo
    l_status: Label

    def create_components(self):
        self.caption = "Notizbuch"
        self.width = 520
        self.height = 400
        self.on_create = self.form_create
        self.on_close = self.form_close

        self.mm_haupt = MainMenu(self)
        self.mm_haupt.entries = [
            {"caption": "&Datei", "children": [
                {
                    "caption": "&Neu",
                    "name": "mi_neu",
                    "on_click": "mi_neu_click",
                    "shortcut": "Strg+N",
                },
                {
                    "caption": "Ö&ffnen …",
                    "name": "mi_oeffnen",
                    "on_click": "mi_oeffnen_click",
                    "shortcut": "Strg+O",
                },
                {
                    "caption": "&Speichern",
                    "name": "mi_speichern",
                    "on_click": "mi_speichern_click",
                    "shortcut": "Strg+S",
                },
                {
                    "caption": "Speichern &unter …",
                    "name": "mi_speichern_unter",
                    "on_click": "mi_speichern_unter_click",
                },
                {"separator": True},
                {"caption": "&Beenden", "name": "mi_beenden", "on_click": "mi_beenden_click"},
            ]},
            {"caption": "&Hilfe", "children": [
                {"caption": "&Info …", "name": "mi_info", "on_click": "mi_info_click"},
            ]},
        ]
        self.mm_haupt.left = 470
        self.mm_haupt.top = 8

        self.m_text = Memo(self)
        self.m_text.left = 8
        self.m_text.top = 8
        self.m_text.width = 504
        self.m_text.height = 356
        self.m_text.anchors.right = True
        self.m_text.anchors.bottom = True
        self.m_text.on_change = self.m_text_change

        self.l_status = Label(self)
        self.l_status.left = 8
        self.l_status.top = 372
        self.l_status.width = 504
        self.l_status.height = 20
        self.l_status.caption = "Neue Notiz"
        self.l_status.word_wrap = False
        self.l_status.anchors.top = False
        self.l_status.anchors.right = True
        self.l_status.anchors.bottom = True
