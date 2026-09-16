"""Tests für ide/inspector/objektinspektor.py: Objektinspektor
(Komponentenbaum + Eigenschaften-/Ereignisse-Reiter). Headless. Siehe
docs/arbeitspakete/M3.md, Schritt 2.
"""

from ide.inspector import Objektinspektor
from pcl import Button, Form


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)

    def b_ein_click(self, sender) -> None:
        pass


def test_formular_anzeigen_waehlt_die_wurzel_automatisch_aus() -> None:
    formular = _Formular()
    inspektor = Objektinspektor()

    inspektor.formular_anzeigen(formular)

    eigenschaften_namen = [
        inspektor.eigenschaften_tabelle.item(z, 0).text()
        for z in range(inspektor.eigenschaften_tabelle.rowCount())
    ]
    assert "caption" in eigenschaften_namen  # Form-Eigenschaft


def test_auswahlwechsel_im_baum_aktualisiert_beide_reiter() -> None:
    formular = _Formular()
    inspektor = Objektinspektor()
    inspektor.formular_anzeigen(formular)

    knopf_element = inspektor.baum.topLevelItem(0).child(0)
    inspektor.baum.setCurrentItem(knopf_element)

    eigenschaften_namen = [
        inspektor.eigenschaften_tabelle.item(z, 0).text()
        for z in range(inspektor.eigenschaften_tabelle.rowCount())
    ]
    assert "caption" in eigenschaften_namen
    assert "checked" not in eigenschaften_namen  # Button hat kein checked

    assert inspektor.ereignisse_tabelle.rowCount() == 1
    assert inspektor.ereignisse_tabelle.item(0, 0).text() == "on_click"


def test_eigenschaft_ueber_den_inspektor_aendern_wirkt_auf_die_komponente() -> None:
    formular = _Formular()
    inspektor = Objektinspektor()
    inspektor.formular_anzeigen(formular)

    knopf_element = inspektor.baum.topLevelItem(0).child(0)
    inspektor.baum.setCurrentItem(knopf_element)

    tabelle = inspektor.eigenschaften_tabelle
    for zeile in range(tabelle.rowCount()):
        if tabelle.item(zeile, 0).text() == "caption":
            tabelle.item(zeile, 1).setText("Einschalten")
            break

    assert formular.b_ein.caption == "Einschalten"
    assert formular.b_ein._qwidget.text() == "Einschalten"
