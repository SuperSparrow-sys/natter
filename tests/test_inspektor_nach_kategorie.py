"""Objektinspektor alphabetisch oder nach Kategorie (offener Punkt 79).

Jede Eigenschaft trägt eine Kategorie (`Prop.kategorie`), gelesen
wurde sie bis dahin nirgends.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings

from ide.inspector.eigenschaften_tabelle import EigenschaftenTabelle
from ide.inspector.objektinspektor import Objektinspektor
from pcl import Button, Form, Memo


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ok = Button(self)
        self.m_notiz = Memo(self)


def _namen(tabelle: EigenschaftenTabelle) -> list[str]:
    return [tabelle.item(z, 0).text() for z in range(tabelle.rowCount())]


def _ueberschriften(tabelle: EigenschaftenTabelle) -> list[str]:
    return [
        tabelle.item(z, 0).text()
        for z in range(tabelle.rowCount())
        if tabelle.columnSpan(z, 0) == 2
    ]


def test_alphabetisch_ist_die_vorgabe() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(formular.b_ok)

    namen = _namen(tabelle)
    assert namen == sorted(namen)
    assert _ueberschriften(tabelle) == []


def test_nach_kategorie_gruppiert() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(formular.b_ok)

    tabelle.ansicht_setzen(True)

    assert _ueberschriften(tabelle) == [
        "Darstellung",
        "Layout",
        "Schrift",
        "Verhalten",
    ]
    namen = _namen(tabelle)
    layout = namen.index("Layout")
    assert namen[layout + 1 : layout + 9] == [
        "anchors_bottom",
        "anchors_left",
        "anchors_right",
        "anchors_top",
        "height",
        "left",
        "top",
        "width",
    ]
    schrift = namen.index("Schrift")
    assert namen[schrift + 1 : schrift + 6] == [
        "font_bold",
        "font_color",
        "font_italic",
        "font_name",
        "font_size",
    ]
    verhalten = namen.index("Verhalten")
    assert {"enabled", "popup_menu", "visible"} <= set(namen[verhalten:])


def test_die_sammlung_steht_unter_daten() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    tabelle.ansicht_setzen(True)
    tabelle.komponente_anzeigen(formular.m_notiz)

    namen = _namen(tabelle)
    assert namen[namen.index("Daten") + 1] == "lines"


def test_in_beiden_ansichten_dieselben_eigenschaften() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(formular.b_ok)
    alphabetisch = set(_namen(tabelle))

    tabelle.ansicht_setzen(True)
    gruppiert = set(_namen(tabelle)) - set(_ueberschriften(tabelle))

    assert gruppiert == alphabetisch


def test_bearbeiten_geht_auch_gruppiert() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    tabelle.ansicht_setzen(True)
    tabelle.komponente_anzeigen(formular.b_ok)
    zeile = _namen(tabelle).index("caption")

    tabelle.item(zeile, 1).setText("Los")

    assert formular.b_ok.caption == "Los"


def test_die_ueberschrift_ist_nicht_bearbeitbar() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    tabelle.ansicht_setzen(True)
    tabelle.komponente_anzeigen(formular.b_ok)
    zeile = _namen(tabelle).index("Layout")

    from PySide6.QtCore import Qt

    assert not tabelle.item(zeile, 0).flags() & Qt.ItemFlag.ItemIsEditable
    assert not tabelle.item(zeile, 1).flags() & Qt.ItemFlag.ItemIsEditable


def test_der_umschalter_merkt_sich_die_wahl() -> None:
    formular = _Formular()
    inspektor = Objektinspektor()
    inspektor.formular_anzeigen(formular)
    assert inspektor.alphabetisch_knopf.isChecked()

    inspektor.kategorie_knopf.click()

    assert inspektor.eigenschaften_tabelle.nach_kategorie
    einstellungen = QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Natter", "Natter-IDE"
    )
    assert einstellungen.value("inspektor/nach_kategorie", type=bool) is True

    wieder = Objektinspektor()
    assert wieder.kategorie_knopf.isChecked()
    assert wieder.eigenschaften_tabelle.nach_kategorie

    wieder.alphabetisch_knopf.click()
    assert not wieder.eigenschaften_tabelle.nach_kategorie
    assert Objektinspektor().alphabetisch_knopf.isChecked()
