"""Tests für ide/inspector/eigenschaften_tabelle.py: EigenschaftenTabelle.
Headless. Siehe docs/arbeitspakete/M3.md, Schritt 1.
"""

from PySide6.QtCore import Qt

from ide.inspector import EigenschaftenTabelle
from pcl import Button, CheckBox, Form
from pcl.components.additional import Shape


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)
        self.c_kaese = CheckBox(self)
        self.s_form = Shape(self)


def _zeile_finden(tabelle: EigenschaftenTabelle, name: str) -> int:
    for zeile in range(tabelle.rowCount()):
        if tabelle.item(zeile, 0).text() == name:
            return zeile
    raise AssertionError(f"Zeile {name!r} nicht gefunden")


def test_zeigt_alle_eigenschaften_alphabetisch() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()

    tabelle.komponente_anzeigen(formular.b_ein)

    namen = [tabelle.item(z, 0).text() for z in range(tabelle.rowCount())]
    assert namen == sorted(namen)
    assert "caption" in namen
    assert "left" in namen


def test_zeigt_aktuellen_wert() -> None:
    formular = _Formular()
    formular.b_ein.caption = "Einschalten"
    tabelle = EigenschaftenTabelle()

    tabelle.komponente_anzeigen(formular.b_ein)

    zeile = _zeile_finden(tabelle, "caption")
    assert tabelle.item(zeile, 1).text() == "Einschalten"


def test_bearbeiten_aendert_die_komponente_live() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(formular.b_ein)

    zeile = _zeile_finden(tabelle, "caption")
    tabelle.item(zeile, 1).setText("Neuer Text")

    assert formular.b_ein.caption == "Neuer Text"
    assert formular.b_ein._qwidget.text() == "Neuer Text"


def test_ungueltige_zahl_wird_abgelehnt_und_zelle_zurueckgesetzt() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(formular.b_ein)

    zeile = _zeile_finden(tabelle, "left")
    tabelle.item(zeile, 1).setText("abc")

    assert formular.b_ein.left == 0  # unverändert
    assert tabelle.item(zeile, 1).text() == "0"
    assert "abc" in tabelle.fehlertext


def test_bool_eigenschaft_als_kontrollkaestchen() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(formular.c_kaese)

    zeile = _zeile_finden(tabelle, "checked")
    element = tabelle.item(zeile, 1)
    assert bool(element.flags() & Qt.ItemFlag.ItemIsUserCheckable)
    assert element.checkState() == Qt.CheckState.Unchecked

    element.setCheckState(Qt.CheckState.Checked)

    assert formular.c_kaese.checked is True
    assert formular.c_kaese._qwidget.isChecked() is True


def test_verschachtelte_untereigenschaft_wird_angezeigt() -> None:
    """Nutzer-Feedback (September 2026): „alle Eigenschaften inklusive
    Farbe usw. sollen im Objektinspektor angezeigt werden“ -
    `Shape.brush.color` war bisher komplett unsichtbar, weil es kein
    echter `Prop` ist, sondern eine aufklappbare Untereigenschaft
    (`pcl.properties.VERSCHACHTELTE_EIGENSCHAFTEN`)."""
    formular = _Formular()
    tabelle = EigenschaftenTabelle()

    tabelle.komponente_anzeigen(formular.s_form)

    zeile = _zeile_finden(tabelle, "brush_color")
    assert tabelle.item(zeile, 1).text() == formular.s_form.brush.color


def test_verschachtelte_untereigenschaft_bearbeiten_aendert_sie_live() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(formular.s_form)

    zeile = _zeile_finden(tabelle, "brush_color")
    tabelle.item(zeile, 1).setText("#e53935")

    assert formular.s_form.brush.color == "#e53935"


def test_komponente_wechseln_zeigt_die_neue_komponente() -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()

    tabelle.komponente_anzeigen(formular.b_ein)
    tabelle.komponente_anzeigen(formular.c_kaese)

    namen = [tabelle.item(z, 0).text() for z in range(tabelle.rowCount())]
    assert "checked" in namen
    assert "on_click" not in namen  # Ereignisse gehören zu Schritt 2
