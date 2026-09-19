"""Tests für `pcl/components/menus.py`: MainMenu und PopupMenu. Headless.

Vorbild sind `TMainMenu`/`TPopupMenu` aus Lazarus. Bis M15 war ein
Schülerprogramm mit Menüleiste in Natter nicht baubar; diese Tests
halten fest, dass es das jetzt ist – und zwar bis in das laufende
Fenster hinein, nicht nur auf der Ebene der Datensätze.
"""

import pytest

from pcl import Button, Form, MainMenu, PopupMenu
from pcl.components.menus import (
    MENUELEISTE_HOEHE,
    _deutsche_kuerzel_umsetzen,
    eintraege_pruefen,
    eintrag_knapp,
    eintrag_suchen,
    eintrag_vollstaendig,
)
from pcl.errors import NatterPropertyError

DATEI_MENUE = [
    {
        "name": "mi_datei",
        "caption": "&Datei",
        "children": [
            {"name": "mi_neu", "caption": "&Neu", "shortcut": "Strg+N", "on_click": "neu"},
            {"separator": True},
            {"name": "mi_ende", "caption": "B&eenden", "on_click": "beenden"},
        ],
    },
    {"name": "mi_hilfe", "caption": "&Hilfe"},
]


class _Formular(Form):
    def create_components(self) -> None:
        self.b_start = Button(self)
        self.b_start.left = 10
        self.b_start.top = 10
        self.mm_haupt = MainMenu(self)
        self.mm_haupt.entries = DATEI_MENUE
        self.geklickt: list[str] = []

    def neu(self, sender) -> None:
        self.geklickt.append("neu")

    def beenden(self, sender) -> None:
        self.geklickt.append("beenden")


# -- Datensätze ---------------------------------------------------------


def test_ein_knapper_eintrag_wird_vollstaendig_aufgefuellt() -> None:
    voll = eintrag_vollstaendig({"caption": "&Datei"})

    assert voll["caption"] == "&Datei"
    assert voll["name"] == ""
    assert voll["enabled"] is True
    assert voll["checked"] is False
    assert voll["separator"] is False
    assert voll["children"] == []


def test_auffuellen_geht_auch_in_die_untereintraege() -> None:
    voll = eintrag_vollstaendig({"caption": "&Datei", "children": [{"caption": "&Neu"}]})

    assert voll["children"][0]["enabled"] is True


def test_knapp_laesst_alles_weg_was_auf_der_vorgabe_steht() -> None:
    """Sonst stünde hinter jedem Eintrag in der `.pfm` dreimal die
    Vorgabe, und die Datei wäre nicht mehr zu lesen."""
    knapp = eintrag_knapp(eintrag_vollstaendig({"caption": "&Datei"}))

    assert knapp == {"caption": "&Datei"}


def test_knapp_behaelt_was_abweicht() -> None:
    knapp = eintrag_knapp(eintrag_vollstaendig({"caption": "&Neu", "enabled": False}))

    assert knapp == {"caption": "&Neu", "enabled": False}


def test_vollstaendig_und_knapp_sind_hin_und_zurueck_dasselbe() -> None:
    for eintrag in DATEI_MENUE:
        assert eintrag_knapp(eintrag_vollstaendig(eintrag)) == eintrag


def test_eintrag_wird_auch_in_den_untereintraegen_gefunden() -> None:
    treffer = eintrag_suchen(DATEI_MENUE, "mi_ende")

    assert treffer is not None
    assert treffer["caption"] == "B&eenden"


def test_unbekannter_bezeichner_liefert_none() -> None:
    assert eintrag_suchen(DATEI_MENUE, "gibt_es_nicht") is None


# -- Prüfung ------------------------------------------------------------


def test_ein_tippfehler_im_feldnamen_faellt_sofort_auf() -> None:
    """„childs" statt „children" hätte sonst einen ganzen Teilbaum
    verschwinden lassen, ohne dass irgendwo etwas passiert."""
    with pytest.raises(NatterPropertyError, match="childs"):
        eintraege_pruefen([{"caption": "&Datei", "childs": []}])


def test_keine_liste_ist_ein_fehler() -> None:
    with pytest.raises(NatterPropertyError, match="Liste"):
        eintraege_pruefen({"caption": "&Datei"})


def test_ein_text_statt_eines_datensatzes_ist_ein_fehler() -> None:
    with pytest.raises(NatterPropertyError, match="dict"):
        eintraege_pruefen(["&Datei"])


def test_die_dritte_ebene_wird_abgelehnt() -> None:
    tief = [{"children": [{"children": [{"children": [{"caption": "zu tief"}]}]}]}]

    with pytest.raises(NatterPropertyError, match="zweiten Ebene"):
        eintraege_pruefen(tief)


# -- Tastenkürzel -------------------------------------------------------


@pytest.mark.parametrize(
    ("deutsch", "qt"),
    [
        ("Strg+Q", "Ctrl+Q"),
        ("Strg+Umschalt+S", "Ctrl+Shift+S"),
        ("Entf", "Del"),
        ("F5", "F5"),
        ("Ctrl+Q", "Ctrl+Q"),
    ],
)
def test_deutsche_tastenkuerzel_werden_umgesetzt(deutsch: str, qt: str) -> None:
    """Wer die Oberfläche auf Deutsch bedient, tippt „Strg". Qt macht
    daraus stillschweigend gar kein Kürzel - genau so eine stumme
    Nicht-Wirkung soll es nicht geben."""
    assert _deutsche_kuerzel_umsetzen(deutsch) == qt


# -- Die Komponente -----------------------------------------------------


def test_ein_menue_ist_im_laufenden_programm_unsichtbar() -> None:
    formular = _Formular()

    formular.show()

    assert formular.mm_haupt._qwidget.isVisible() is False


def test_die_eintraege_kommen_als_kopie_zurueck() -> None:
    """Wer `menue.entries[0]["caption"]` ändert, soll nicht aus
    Versehen am Original schrauben, ohne dass das Menü davon erfährt."""
    menue = MainMenu()
    menue.entries = DATEI_MENUE

    menue.entries[0]["caption"] = "kaputt"

    assert menue.entries[0]["caption"] == "&Datei"


def test_eintrag_liefert_das_original_zum_aendern() -> None:
    menue = MainMenu()
    menue.entries = DATEI_MENUE

    menue.eintrag("mi_ende")["enabled"] = False

    assert menue.eintrag("mi_ende")["enabled"] is False


def test_ein_falscher_eintrag_wird_beim_zuweisen_abgelehnt() -> None:
    menue = MainMenu()

    with pytest.raises(NatterPropertyError):
        menue.entries = [{"caption": "&Datei", "tippfehler": 1}]


# -- Die Menüleiste im laufenden Fenster --------------------------------


def test_die_leiste_entsteht_erst_beim_anzeigen() -> None:
    formular = _Formular()

    assert formular._menueleiste is None
    formular.show()
    assert formular._menueleiste is not None


def test_die_leiste_traegt_die_obersten_eintraege() -> None:
    formular = _Formular()
    formular.show()

    beschriftungen = [aktion.text() for aktion in formular._menueleiste.actions()]

    assert beschriftungen == ["&Datei", "&Hilfe"]


def test_untereintraege_stehen_im_untermenue() -> None:
    formular = _Formular()
    formular.show()

    untermenue = formular._menueleiste.actions()[0].menu()
    aktionen = untermenue.actions()

    assert [aktion.text() for aktion in aktionen] == ["&Neu	Strg+N", "", "B&eenden"]
    assert aktionen[1].isSeparator() is True


def test_das_tastenkuerzel_steht_wirklich_an_der_aktion() -> None:
    formular = _Formular()
    formular.show()

    untermenue = formular._menueleiste.actions()[0].menu()

    assert untermenue.actions()[0].shortcut().toString() == "Ctrl+N"


def test_im_menue_steht_das_kuerzel_auf_deutsch() -> None:
    """Beim ersten echten Probelauf stand im Menü „Ctrl+N", obwohl im
    Editor „Strg+N" eingetragen war: Qt schreibt die Tastennamen
    selbst und bräuchte dafür Übersetzungsdateien, die PySide6 nicht
    mitliefert. In einer durchgehend deutschen Oberfläche geht das
    nicht. Die Tests davor hatten es nicht gefunden - sie prüften die
    Tastenfolge, nicht ihre Beschriftung."""
    formular = _Formular()
    formular.show()

    untermenue = formular._menueleiste.actions()[0].menu()

    # Der Tabulator ist Qts eigener Weg: was dahinter steht, zeigt es
    # rechtsbündig als Kürzelspalte, ohne etwas Eigenes hinzuschreiben.
    assert untermenue.actions()[0].text() == "&Neu	Strg+N"


def test_auch_englisch_getipptes_kuerzel_steht_deutsch_im_menue() -> None:
    menue = MainMenu()
    menue.entries = [{"caption": "&Test", "shortcut": "Ctrl+Shift+S"}]
    klapp = PopupMenu()
    klapp.entries = menue.entries

    aktion = klapp.menue().actions()[0]

    assert aktion.text() == "&Test	Strg+Umschalt+S"
    assert aktion.shortcut().toString() == "Ctrl+Shift+S"


def test_ein_klick_ruft_die_methode_des_formulars() -> None:
    formular = _Formular()
    formular.show()

    untermenue = formular._menueleiste.actions()[0].menu()
    untermenue.actions()[2].trigger()

    assert formular.geklickt == ["beenden"]


def test_ein_unbekannter_methodenname_nimmt_das_fenster_nicht_mit() -> None:
    """Der Aufbau des Fensters darf an einem Tippfehler im
    Ereignisnamen nicht scheitern - sonst startet das Programm gar
    nicht mehr, und niemand sieht, woran es lag."""

    class MitTippfehler(_Formular):
        def create_components(self) -> None:
            super().create_components()
            self.mm_haupt.entries = [{"caption": "&Datei", "on_click": "gibt_es_nicht"}]

    formular = MitTippfehler()
    formular.show()

    assert formular._menueleiste.actions()[0].text() == "&Datei"


def test_der_arbeitsbereich_rutscht_um_die_leiste_nach_unten() -> None:
    """Wie in Lazarus: `Top = 0` ist der obere Rand des
    Arbeitsbereichs, nicht des Fensters. Wer einen Knopf an den oberen
    Rand setzt, findet ihn im laufenden Programm auch dort wieder und
    nicht hinter dem Menü."""
    formular = _Formular()

    formular.show()

    assert formular.b_start._qwidget.y() == 10 + MENUELEISTE_HOEHE


def test_zweimal_anzeigen_verschiebt_nicht_zweimal() -> None:
    formular = _Formular()

    formular.show()
    formular.show()

    assert formular.b_start._qwidget.y() == 10 + MENUELEISTE_HOEHE


def test_eine_groessenaenderung_zur_laufzeit_frisst_die_leiste_nicht(qtbot) -> None:
    """`height` ist die Höhe des Arbeitsbereichs. Ohne die Leiste
    obendrauf schrumpfte das Fenster bei einem `self.height = 400` um
    die Leistenhöhe, und die unterste Zeile verschwände."""
    formular = _Formular()
    formular.show()

    formular.height = 400

    assert formular._qwidget.height() == 400 + MENUELEISTE_HOEHE


def test_ohne_menue_bleibt_alles_wo_es_war() -> None:
    class OhneMenue(Form):
        def create_components(self) -> None:
            self.b_start = Button(self)
            self.b_start.top = 10

    formular = OhneMenue()
    formular.show()

    assert formular._menueleiste is None
    assert formular.b_start._qwidget.y() == 10


def test_eine_aenderung_nach_dem_anzeigen_wirkt_sofort() -> None:
    formular = _Formular()
    formular.show()

    formular.mm_haupt.entries = [{"caption": "&Anders"}]

    assert [aktion.text() for aktion in formular._menueleiste.actions()] == ["&Anders"]


# -- PopupMenu ----------------------------------------------------------


def test_ein_klappmenue_baut_seine_aktionen() -> None:
    klapp = PopupMenu()
    klapp.entries = [{"caption": "&Kopieren"}, {"separator": True}, {"caption": "&Einfügen"}]

    menue = klapp.menue()

    assert [aktion.text() for aktion in menue.actions()] == ["&Kopieren", "", "&Einfügen"]


def test_ein_klappmenue_haengt_an_einer_komponente() -> None:
    class MitKlappmenue(Form):
        def create_components(self) -> None:
            self.pm_liste = PopupMenu(self)
            self.pm_liste.entries = [{"caption": "&Löschen"}]
            self.b_ziel = Button(self)
            self.b_ziel.popup_menu = self.pm_liste

    formular = MitKlappmenue()

    assert formular.b_ziel.popup_menu is formular.pm_liste


def test_ohne_zuordnung_ist_popup_menu_leer() -> None:
    """Ein Klappmenü ohne Ort, an dem es aufklappt, ist kein Fehler,
    sondern nur noch nicht fertig."""
    assert Button().popup_menu is None


# -- Die Entwurfszeit-Symbole -------------------------------------------


def test_die_beiden_menues_zeigen_verschiedene_symbole() -> None:
    """Zwei gleich aussehende Symbole auf dem Formular wären schlimmer
    als gar keines: man könnte Haupt- und Klappmenü nicht mehr
    auseinanderhalten."""
    assert type(MainMenu()._qwidget) is not type(PopupMenu()._qwidget)


def test_das_symbol_zeichnet_wirklich_etwas() -> None:
    """Ein `paintEvent`, das nichts malt, fällt sonst erst auf dem
    Bildschirm auf - und ein leeres Kästchen sieht aus wie ein Fehler."""
    from PySide6.QtGui import QColor

    menue = MainMenu()
    menue.width = 32
    menue.height = 32
    bild = menue._qwidget.grab().toImage()

    farben = {QColor(bild.pixel(x, y)).name() for x in range(32) for y in range(32)}
    assert len(farben) > 2
