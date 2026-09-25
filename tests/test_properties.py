"""Tests für pcl/properties.py: Standardwert, Typprüfung, Tippfehler-
Erkennung, Lesen liefert aktuellen Wert. Siehe PLAN.md (Git-Historie), M1 Schritt 1.
"""

import pytest

from pcl.errors import NatterPropertyError, NatterUnbekannteEigenschaftError
from pcl.properties import Event, Komponente, Prop, eigenschaften, ereignisse


class Steuerelement(Komponente):
    """Gemeinsame Basis, wie z. B. `Control` in Abschnitt 5.2."""

    left = Prop(int, 0, kategorie="Layout", doc="Position von links")
    top = Prop(int, 0, kategorie="Layout", doc="Position von oben")


class Beispielknopf(Steuerelement):
    caption = Prop(str, "Button", kategorie="Darstellung", doc="Beschriftung des Buttons")
    enabled = Prop(bool, True, kategorie="Verhalten", doc="Anklickbar?")
    anteil = Prop(float, 0.0, kategorie="Darstellung")
    on_click = Event(doc="Wird beim Klicken ausgelöst")


class BeispielFormular(Komponente):
    neue_attribute_erlaubt = True

    caption = Prop(str, "Form1")


def test_standardwert() -> None:
    knopf = Beispielknopf()
    assert knopf.caption == "Button"
    assert knopf.enabled is True
    assert knopf.left == 0


def test_zuweisung_aendert_und_liest_aktuellen_wert() -> None:
    knopf = Beispielknopf()
    knopf.caption = "OK"
    assert knopf.caption == "OK"
    knopf.caption = "Abbrechen"
    assert knopf.caption == "Abbrechen"


def test_geerbte_eigenschaft_funktioniert() -> None:
    knopf = Beispielknopf()
    knopf.left = 24
    assert knopf.left == 24


def test_typpruefung_lehnt_falschen_typ_ab() -> None:
    knopf = Beispielknopf()
    with pytest.raises(NatterPropertyError) as fehler:
        knopf.caption = 5
    text = str(fehler.value)
    assert "Beispielknopf.caption erwartet" in text
    assert "Text (str)" in text
    assert "Zahl (int)" in text


def test_bool_wird_nicht_fuer_int_eigenschaft_akzeptiert() -> None:
    knopf = Beispielknopf()
    with pytest.raises(NatterPropertyError):
        knopf.left = True


def test_int_wird_nicht_fuer_bool_eigenschaft_akzeptiert() -> None:
    knopf = Beispielknopf()
    with pytest.raises(NatterPropertyError):
        knopf.enabled = 1


def test_float_eigenschaft_akzeptiert_int() -> None:
    knopf = Beispielknopf()
    knopf.anteil = 3
    assert knopf.anteil == 3


def test_unbekannte_eigenschaft_tippfehler_wird_gemeldet() -> None:
    knopf = Beispielknopf()
    with pytest.raises(NatterUnbekannteEigenschaftError):
        knopf.captoin = "OK"


def test_neue_attribute_auf_formular_bleiben_erlaubt() -> None:
    formular = BeispielFormular()
    formular.ampel = "irgendein eigenes Objekt"
    assert formular.ampel == "irgendein eigenes Objekt"


def test_neue_attribute_auf_komponente_bleiben_gesperrt() -> None:
    knopf = Beispielknopf()
    with pytest.raises(NatterUnbekannteEigenschaftError):
        knopf.irgendwas = 1


def test_event_speichert_und_liest_handler() -> None:
    knopf = Beispielknopf()
    assert knopf.on_click is None

    def handler() -> None:
        pass

    knopf.on_click = handler
    assert knopf.on_click is handler


def test_event_lehnt_nicht_aufrufbaren_wert_ab() -> None:
    knopf = Beispielknopf()
    with pytest.raises(NatterPropertyError):
        knopf.on_click = "kein Handler"


def test_eigenschaften_helper_liefert_eigene_und_geerbte_props() -> None:
    props = eigenschaften(Beispielknopf)
    assert set(props) == {"left", "top", "caption", "enabled", "anteil"}
    assert props["caption"].standardwert == "Button"
    assert props["caption"].kategorie == "Darstellung"
    assert props["caption"].doc == "Beschriftung des Buttons"


def test_ereignisse_helper_liefert_events() -> None:
    events = ereignisse(Beispielknopf)
    assert set(events) == {"on_click"}
    assert events["on_click"].doc == "Wird beim Klicken ausgelöst"
