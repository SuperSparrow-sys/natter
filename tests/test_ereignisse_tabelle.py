"""Tests für ide/inspector/ereignisse_tabelle.py: EreignisseTabelle.
Headless. Siehe docs/arbeitspakete/M3.md, Schritt 2.
"""

from ide.inspector.ereignisse_tabelle import KEIN_HANDLER, EreignisseTabelle
from pcl import Button, Form


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)

    def b_ein_click(self, sender) -> None:
        pass

    def unpassende_methode(self, a, b) -> None:
        pass


def test_zeigt_alle_ereignisse_der_komponente() -> None:
    formular = _Formular()
    tabelle = EreignisseTabelle()

    tabelle.anzeigen(formular.b_ein, formular)

    assert tabelle.rowCount() == 1
    assert tabelle.item(0, 0).text() == "on_click"


def test_dropdown_enthaelt_nur_passende_methoden() -> None:
    formular = _Formular()
    tabelle = EreignisseTabelle()

    tabelle.anzeigen(formular.b_ein, formular)

    auswahl = tabelle.cellWidget(0, 1)
    eintraege = [auswahl.itemText(i) for i in range(auswahl.count())]
    assert "b_ein_click" in eintraege
    assert "unpassende_methode" not in eintraege
    assert KEIN_HANDLER in eintraege


def test_ohne_verknuepften_handler_zeigt_kein_handler() -> None:
    formular = _Formular()
    tabelle = EreignisseTabelle()

    tabelle.anzeigen(formular.b_ein, formular)

    auswahl = tabelle.cellWidget(0, 1)
    assert auswahl.currentText() == KEIN_HANDLER


def test_auswahl_verknuepft_den_handler_und_er_wird_beim_klick_aufgerufen() -> None:
    aufgerufen = []

    class _FormularMitAufzeichnung(Form):
        def create_components(self) -> None:
            self.b_ein = Button(self)

        def b_ein_click(self, sender) -> None:
            aufgerufen.append(sender)

    formular = _FormularMitAufzeichnung()
    tabelle = EreignisseTabelle()
    tabelle.anzeigen(formular.b_ein, formular)

    auswahl = tabelle.cellWidget(0, 1)
    auswahl.setCurrentText("b_ein_click")

    assert formular.b_ein.on_click == formular.b_ein_click

    formular.b_ein._qwidget.click()
    assert aufgerufen == [formular.b_ein]


def test_bereits_gesetzter_handler_wird_vorausgewaehlt() -> None:
    formular = _Formular()
    formular.b_ein.on_click = formular.b_ein_click
    tabelle = EreignisseTabelle()

    tabelle.anzeigen(formular.b_ein, formular)

    auswahl = tabelle.cellWidget(0, 1)
    assert auswahl.currentText() == "b_ein_click"


def test_kein_handler_ausgewaehlt_entfernt_die_verknuepfung() -> None:
    formular = _Formular()
    formular.b_ein.on_click = formular.b_ein_click
    tabelle = EreignisseTabelle()
    tabelle.anzeigen(formular.b_ein, formular)

    auswahl = tabelle.cellWidget(0, 1)
    auswahl.setCurrentText(KEIN_HANDLER)

    assert formular.b_ein.on_click is None
