"""Tests für die Behälter aus `pcl/components/standard.py`: GroupBox,
Panel, RadioGroup. Headless.

Siehe `docs/komponenten.md`, Abschnitt „Behälter: was GroupBox, Panel
und RadioGroup schon können" - und dort „Offene Punkte" für das, was der
Designer dafür noch nicht kann.
"""

import pytest
from PySide6.QtWidgets import QFrame, QGroupBox, QRadioButton

from pcl import Button, CheckBox, Form, GroupBox, Panel, RadioGroup
from pcl.errors import NatterPropertyError


class _Formular(Form):
    def create_components(self) -> None:
        self.g_zahlung = GroupBox(self)
        self.p_feld = Panel(self)
        self.rg_groesse = RadioGroup(self)


# -- GroupBox ----------------------------------------------------------


def test_groupbox_standardwerte() -> None:
    formular = _Formular()
    kasten = formular.g_zahlung

    assert kasten.caption == "GroupBox1"
    assert (kasten.width, kasten.height) == (185, 105)
    assert isinstance(kasten._qwidget, QGroupBox)
    assert kasten._qwidget.title() == "GroupBox1"


def test_groupbox_caption_wirkt_sofort_auf_das_widget() -> None:
    formular = _Formular()
    formular.g_zahlung.caption = "Zahlungsart"

    assert formular.g_zahlung._qwidget.title() == "Zahlungsart"


def test_groupbox_nimmt_eine_komponente_auf() -> None:
    """Der Kern der Behälter-Eigenschaft: das Qt-Widget der
    Kind-Komponente hängt wirklich am Behälter, nicht am Formular."""
    formular = _Formular()

    knopf = Button(formular.g_zahlung)

    assert knopf._qwidget.parent() is formular.g_zahlung._qwidget


def test_kind_eines_behaelters_liegt_relativ_zu_ihm() -> None:
    formular = _Formular()
    formular.g_zahlung.left, formular.g_zahlung.top = 40, 60
    knopf = Button(formular.g_zahlung)

    knopf.left, knopf.top = 10, 20

    # left/top zählen ab der Ecke der GroupBox ...
    assert knopf._qwidget.x() == 10
    assert knopf._qwidget.y() == 20
    # ... und liegen auf dem Formular entsprechend versetzt.
    ecke = knopf._qwidget.mapTo(formular._qwidget, knopf._qwidget.rect().topLeft())
    assert (ecke.x(), ecke.y()) == (50, 80)


def test_gesperrter_behaelter_sperrt_seinen_inhalt_mit() -> None:
    formular = _Formular()
    kaestchen = CheckBox(formular.g_zahlung)

    formular.g_zahlung.enabled = False

    assert kaestchen._qwidget.isEnabled() is False
    # Die Kind-Komponente selbst bleibt auf `True` - gesperrt ist der
    # Behälter, wie in Lazarus.
    assert kaestchen.enabled is True


# -- Panel -------------------------------------------------------------


def test_panel_standardwerte() -> None:
    formular = _Formular()
    feld = formular.p_feld

    assert feld.caption == "Panel1"
    assert feld.color == ""
    assert (feld.width, feld.height) == (185, 105)
    assert isinstance(feld._qwidget, QFrame)


def test_panel_nimmt_eine_komponente_auf() -> None:
    formular = _Formular()

    knopf = Button(formular.p_feld)

    assert knopf._qwidget.parent() is formular.p_feld._qwidget


def test_panel_caption_wird_gezeichnet() -> None:
    """Die Beschriftung ist kein Kind-`QLabel`, sondern wird selbst
    gemalt (sonst läge sie über den Komponenten auf dem Panel und finge
    deren Mausklicks ab). Geprüft wird deshalb am gerenderten Bild."""
    formular = _Formular()
    formular.p_feld.caption = ""
    formular.show()
    ohne = formular.p_feld._qwidget.grab().toImage()

    formular.p_feld.caption = "Steuerung"
    mit = formular.p_feld._qwidget.grab().toImage()

    assert mit != ohne


def test_panel_hat_kein_kind_label_das_klicks_abfangen_wuerde() -> None:
    formular = _Formular()

    assert formular.p_feld._qwidget.children() == []


def test_panel_color_faerbt_nur_das_panel_nicht_seinen_inhalt() -> None:
    formular = _Formular()
    knopf = Button(formular.p_feld)

    formular.p_feld.color = "#ffd7a0"

    assert "#ffd7a0" in formular.p_feld._qwidget.styleSheet()
    # Ein Stylesheet kaskadiert in Qt auf die Kinder. Als nackte
    # Anweisung („background-color: …;", wie bei `Label.color`) bekäme
    # jede Komponente auf dem Panel den orangen Grund, deshalb eine
    # Regel auf den Objektnamen genau dieses Widgets.
    assert "QFrame#pcl_panel" in formular.p_feld._qwidget.styleSheet()
    assert knopf._qwidget.styleSheet() == ""


# -- RadioGroup --------------------------------------------------------


def test_radiogroup_standardwerte() -> None:
    formular = _Formular()
    gruppe = formular.rg_groesse

    assert gruppe.caption == "RadioGroup1"
    assert list(gruppe.items) == []
    assert gruppe.item_index == -1
    assert (gruppe.width, gruppe.height) == (185, 105)


def test_radiogroup_erzeugt_je_eintrag_ein_optionsfeld() -> None:
    formular = _Formular()

    formular.rg_groesse.items = ["Klein", "Mittel", "Groß"]

    felder = formular.rg_groesse._qwidget.findChildren(QRadioButton)
    assert [feld.text() for feld in felder] == ["Klein", "Mittel", "Groß"]


def test_radiogroup_items_add_ergaenzt_ein_optionsfeld() -> None:
    formular = _Formular()
    formular.rg_groesse.items = ["Klein"]

    formular.rg_groesse.items.add("Mittel")

    felder = formular.rg_groesse._qwidget.findChildren(QRadioButton)
    assert [feld.text() for feld in felder] == ["Klein", "Mittel"]


def test_radiogroup_item_index_waehlt_wirklich_aus() -> None:
    formular = _Formular()
    formular.rg_groesse.items = ["Klein", "Mittel", "Groß"]

    formular.rg_groesse.item_index = 1

    felder = formular.rg_groesse._qwidget.findChildren(QRadioButton)
    assert [feld.isChecked() for feld in felder] == [False, True, False]


def test_radiogroup_klick_auf_ein_optionsfeld_setzt_item_index() -> None:
    formular = _Formular()
    formular.rg_groesse.items = ["Klein", "Mittel", "Groß"]

    formular.rg_groesse._qwidget.findChildren(QRadioButton)[2].setChecked(True)

    assert formular.rg_groesse.item_index == 2


def test_radiogroup_ist_wirklich_gegenseitig_ausschliessend() -> None:
    """Der Unterschied zu einzelnen `RadioButton`-Komponenten, die sich
    bisher nur optisch gruppieren."""
    formular = _Formular()
    formular.rg_groesse.items = ["Klein", "Mittel", "Groß"]
    felder = formular.rg_groesse._qwidget.findChildren(QRadioButton)

    felder[0].setChecked(True)
    felder[2].setChecked(True)

    assert [feld.isChecked() for feld in felder] == [False, False, True]
    assert formular.rg_groesse.item_index == 2


def test_radiogroup_on_change_feuert_beim_wechsel() -> None:
    formular = _Formular()
    formular.rg_groesse.items = ["Klein", "Mittel", "Groß"]
    empfangen: list[int] = []
    formular.rg_groesse.on_change = lambda sender: empfangen.append(sender.item_index)

    formular.rg_groesse._qwidget.findChildren(QRadioButton)[1].setChecked(True)

    assert empfangen == [1]


def test_radiogroup_neue_items_loesen_kein_on_change_aus() -> None:
    """Beim Neuaufbau meldet jedes erzeugte und jedes gelöschte
    Optionsfeld ein `toggled`. Ohne die Sperre in
    `_optionen_neu_aufbauen` käme das als Auswahl des Benutzers an."""
    formular = _Formular()
    formular.rg_groesse.items = ["Klein", "Mittel"]
    formular.rg_groesse.item_index = 1
    empfangen: list[int] = []
    formular.rg_groesse.on_change = lambda sender: empfangen.append(sender.item_index)

    formular.rg_groesse.items = ["Klein", "Mittel", "Groß"]

    assert empfangen == []


def test_radiogroup_behaelt_die_auswahl_beim_neuaufbau() -> None:
    formular = _Formular()
    formular.rg_groesse.items = ["Klein", "Mittel", "Groß"]
    formular.rg_groesse.item_index = 1

    formular.rg_groesse.items = ["Klein", "Mittel", "Groß", "Riesig"]

    assert formular.rg_groesse.item_index == 1
    felder = formular.rg_groesse._qwidget.findChildren(QRadioButton)
    assert [feld.isChecked() for feld in felder] == [False, True, False, False]


def test_radiogroup_setzt_einen_ungueltig_gewordenen_index_zurueck() -> None:
    formular = _Formular()
    formular.rg_groesse.items = ["Klein", "Mittel", "Groß"]
    formular.rg_groesse.item_index = 2

    formular.rg_groesse.items = ["Klein"]

    assert formular.rg_groesse.item_index == -1
    felder = formular.rg_groesse._qwidget.findChildren(QRadioButton)
    assert [feld.isChecked() for feld in felder] == [False]


def test_behaelter_lehnen_unbekannte_eigenschaften_ab() -> None:
    # Tippfehlerschutz aus Abschnitt 5.0 gilt auch für die neuen
    # Komponenten - sie erben ihn über `Komponente`.
    formular = _Formular()
    for komponente in (formular.g_zahlung, formular.p_feld, formular.rg_groesse):
        with pytest.raises(Exception):  # noqa: B017 - NatterUnbekannteEigenschaftError
            komponente.gibt_es_nicht = 1


def test_behaelter_pruefen_den_typ_ihrer_eigenschaften() -> None:
    formular = _Formular()
    with pytest.raises(NatterPropertyError):
        formular.g_zahlung.caption = 7
    with pytest.raises(NatterPropertyError):
        formular.rg_groesse.item_index = "zwei"


def test_radiogroup_index_ohne_passende_option_faellt_auf_minus_eins() -> None:
    """Sonst stünde `item_index` auf 2, angehakt wäre aber nichts -
    ein Zustand, den man am Bildschirm nicht sehen kann."""
    formular = _Formular()
    formular.rg_groesse.items = ["Klein", "Mittel"]

    formular.rg_groesse.item_index = 5

    assert formular.rg_groesse.item_index == -1
    felder = formular.rg_groesse._qwidget.findChildren(QRadioButton)
    assert [feld.isChecked() for feld in felder] == [False, False]


def test_radiogroup_minus_eins_hebt_die_auswahl_auf() -> None:
    formular = _Formular()
    formular.rg_groesse.items = ["Klein", "Mittel"]
    formular.rg_groesse.item_index = 1

    formular.rg_groesse.item_index = -1

    assert formular.rg_groesse.item_index == -1
    felder = formular.rg_groesse._qwidget.findChildren(QRadioButton)
    assert [feld.isChecked() for feld in felder] == [False, False]


def test_radiogroup_aus_einer_zeichenkette(qtbot) -> None:
    """Fund aus der Sichtprüfung: `items = "rot\ngelb\ngruen"` ergab
    vierzehn Optionsfelder mit je einem Buchstaben. Eine Zeichenkette
    wird jetzt an den Zeilenumbrüchen getrennt, wie `Items.Text` in
    Lazarus."""
    formular = _Formular()
    qtbot.addWidget(formular._qwidget)

    formular.rg_groesse.items = "rot\ngelb\ngruen"

    assert [o.text() for o in formular.rg_groesse._optionen] == ["rot", "gelb", "gruen"]


def test_die_optionsfelder_fuellen_die_breite(qtbot) -> None:
    """Gegenprobe zum selben Fund: bei einem Optionsfeld je Buchstabe
    passten die Beschriftungen nicht mehr nebeneinander und brachen um.
    Mit ganzen Wörtern muss jede Beschriftung in eine Zeile passen."""
    formular = _Formular()
    qtbot.addWidget(formular._qwidget)
    formular.rg_groesse.width = 200
    formular.rg_groesse.items = ["rot", "gelb", "gruen"]

    for option in formular.rg_groesse._optionen:
        assert option.sizeHint().width() <= 200
        assert option.sizeHint().height() < 24, "die Beschriftung bricht um"
