"""Tests für den Eigenschaften-Dialog einer UML-Klasse
(M9, Schritt 12). Headless.

Der Dialog wird nie mit `exec()` geöffnet – das würde blockieren.
Stattdessen benutzen die Tests `canvas.eigenschaften_dialog()`, das
denselben, fertig verdrahteten Dialog liefert, ihn aber nicht anzeigt.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.diagramm import diagramm_erzeugen
from ide.diagramm.canvas import DiagrammCanvas
from ide.diagramm.klassendialog import KlassenDialog
from ide.diagramm.uml_modell import attributzeilen, operationszeilen


@pytest.fixture
def canvas(tmp_path: Path) -> DiagrammCanvas:
    return DiagrammCanvas(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))


@pytest.fixture
def klasse(canvas: DiagrammCanvas) -> dict:
    return canvas.form_platzieren("class", 300, 300)


@pytest.fixture
def dialog(canvas: DiagrammCanvas, klasse: dict) -> KlassenDialog:
    return canvas.eigenschaften_dialog(klasse)


# -- Aufbau --------------------------------------------------------------


def test_dialog_hat_die_fuenf_reiter(dialog: KlassenDialog) -> None:
    """Wie im Vorbild (Dia): Klasse, Attribute, Operationen, Vorlagen,
    Stil."""
    titel = [dialog.reiter.tabText(i).replace("&", "") for i in range(dialog.reiter.count())]

    assert titel == ["Klasse", "Attribute", "Operationen", "Vorlagen", "Stil"]


def test_dialog_hat_schliessen_anwenden_und_ok(dialog: KlassenDialog) -> None:
    beschriftungen = {
        knopf.text().replace("&", "")
        for knopf in (dialog.schliessen_knopf, dialog.anwenden_knopf, dialog.ok_knopf)
    }

    assert beschriftungen == {"Schließen", "Anwenden", "OK"}


def test_notiz_bekommt_keinen_dialog(canvas: DiagrammCanvas) -> None:
    """Nutzer-Entscheidung: Notiz und Paket haben nur ein Textfeld und
    werden weiterhin direkt in der Fläche beschriftet."""
    notiz = canvas.form_platzieren("note", 300, 300)

    assert canvas.eigenschaften_dialog(notiz) is None


def test_klasse_oeffnet_den_dialog_statt_des_direkteditors(
    canvas: DiagrammCanvas, klasse: dict
) -> None:
    """`bearbeiten_starten` ist der gemeinsame Einstieg – für eine
    Klasse muss er den Dialog nehmen."""
    assert canvas._editor is None
    dialog = canvas.eigenschaften_dialog(klasse)

    assert isinstance(dialog, KlassenDialog)


def test_notiz_oeffnet_weiterhin_den_direkteditor(canvas: DiagrammCanvas) -> None:
    notiz = canvas.form_platzieren("note", 300, 300)

    editor = canvas.bearbeiten_starten(notiz)

    assert editor is not None
    assert canvas._editor is editor


# -- Attribute -----------------------------------------------------------


def test_attribut_anlegen_und_ausfuellen(dialog: KlassenDialog, klasse: dict) -> None:
    dialog._attribut_neu()
    dialog.attribut_name.setText("zustand")
    dialog.attribut_typ.setText("int")
    dialog.attribut_wert.setText("1")
    dialog.anwenden()

    assert klasse["attributes"][0]["name"] == "zustand"
    assert klasse["attributes"][0]["type"] == "int"
    assert attributzeilen(klasse) == ["-zustand: int = 1"]


def test_attributliste_zieht_beim_tippen_mit(dialog: KlassenDialog) -> None:
    """Sonst sähe man die Wirkung erst nach einem Wechsel."""
    dialog._attribut_neu()
    dialog.attribut_name.setText("zaehler")

    assert dialog.attributliste.liste.item(0).text() == "-zaehler"


def test_attribut_umsortieren(dialog: KlassenDialog, klasse: dict) -> None:
    dialog._attribut_neu()
    dialog.attribut_name.setText("erstes")
    dialog._attribut_neu()
    dialog.attribut_name.setText("zweites")

    dialog.attributliste.liste.setCurrentRow(1)
    dialog._attribut_schieben(-1)
    dialog.anwenden()

    assert [a["name"] for a in klasse["attributes"]] == ["zweites", "erstes"]


def test_attribut_loeschen(dialog: KlassenDialog, klasse: dict) -> None:
    dialog._attribut_neu()
    dialog.attribut_name.setText("weg")
    dialog.attributliste.liste.setCurrentRow(0)

    dialog._attribut_loeschen()
    dialog.anwenden()

    assert klasse["attributes"] == []


def test_attributfelder_sind_ohne_auswahl_ausgegraut(dialog: KlassenDialog) -> None:
    assert dialog.attributdaten.isEnabled() is False


# -- Operationen und Parameter -------------------------------------------


def test_operation_mit_parameter(dialog: KlassenDialog, klasse: dict) -> None:
    dialog._operation_neu()
    dialog.operation_name.setText("setzen")
    dialog.operation_typ.setText("None")
    dialog._parameter_neu()
    dialog.parameter_name.setText("farbe")
    dialog.parameter_typ.setText("str")
    dialog.anwenden()

    assert operationszeilen(klasse) == ["+setzen(farbe: str): None"]


def test_parameter_gehoeren_zur_ausgewaehlten_operation(dialog: KlassenDialog) -> None:
    """Zwei Operationen dürfen sich ihre Parameter nicht teilen."""
    dialog._operation_neu()
    dialog.operation_name.setText("erste")
    dialog._parameter_neu()
    dialog.parameter_name.setText("a")

    dialog._operation_neu()
    dialog.operation_name.setText("zweite")

    assert dialog.parameterliste.liste.count() == 0


def test_abstrakte_operation_wird_gemerkt(dialog: KlassenDialog, klasse: dict) -> None:
    from ide.diagramm.uml_modell import kursive_operationen

    dialog._operation_neu()
    dialog.operation_name.setText("zeichnen")
    dialog.operation_vererbung.setCurrentIndex(
        dialog.operation_vererbung.findData("abstract")
    )
    dialog.anwenden()

    assert kursive_operationen(klasse) == {0}


# -- Reiter „Klasse“ -----------------------------------------------------


def test_klassenname_ueberlebt_einen_reiterwechsel(
    dialog: KlassenDialog, klasse: dict
) -> None:
    """Real aufgefallen: der getippte Name war wieder weg, sobald man
    ein Attribut anlegte – `_anzeigen()` hatte die Felder aus dem
    Entwurf überschrieben."""
    dialog.klassenname.setText("Ampel")
    dialog._attribut_neu()
    dialog.anwenden()

    assert klasse["name"] == "Ampel"


def test_anzeigeschalter_wirken(dialog: KlassenDialog, klasse: dict) -> None:
    dialog._attribut_neu()
    dialog.attribut_name.setText("a")
    dialog.attribute_sichtbar.setChecked(False)
    dialog.anwenden()

    assert attributzeilen(klasse) == []


def test_umbruchlaengen_haben_die_vorgaben_aus_dem_vorbild(
    dialog: KlassenDialog,
) -> None:
    assert dialog.umbruch_operationen.value() == 40
    assert dialog.umbruch_kommentare.value() == 17


# -- Vorlagen und Stil ---------------------------------------------------

def test_vorlageklasse_mit_parameter(dialog: KlassenDialog, klasse: dict) -> None:
    dialog.vorlageklasse.setChecked(True)
    dialog._vorlage_neu()
    dialog.vorlage_name.setText("T")
    dialog.anwenden()

    assert klasse["template"] is True
    assert klasse["template_parameters"][0]["name"] == "T"


def test_leere_farbe_bedeutet_stilvorlage(dialog: KlassenDialog, klasse: dict) -> None:
    """Leer wird als leerer Wert gespeichert, nicht als fehlender
    Schlüssel – ein `WerteKommando` kann nur setzen, und ein entferntes
    `fill` käme beim Zurücknehmen nicht wieder."""
    from ide.diagramm.stil import MODERN_HELL
    from ide.diagramm.zeichnen import fuellfarbe

    dialog.fuellfarbe.setText("#ffe0b2")
    dialog.anwenden()
    assert fuellfarbe(klasse, MODERN_HELL) == "#ffe0b2"

    dialog.fuellfarbe.setText("")
    dialog.anwenden()
    assert fuellfarbe(klasse, MODERN_HELL) == MODERN_HELL.fuellung


# -- Undo ----------------------------------------------------------------


def test_ein_dialogdurchgang_ist_ein_undo_schritt(
    canvas: DiagrammCanvas, dialog: KlassenDialog, klasse: dict
) -> None:
    """Egal wie viele Felder geändert wurden."""
    dialog.klassenname.setText("Ampel")
    dialog._attribut_neu()
    dialog.attribut_name.setText("zustand")
    dialog._operation_neu()
    dialog.operation_name.setText("ein")
    dialog.anwenden()

    canvas.rueckgaengig()

    assert klasse["name"] == "Klasse"
    assert klasse["attributes"] == []
    assert klasse["operations"] == []


def test_zweimal_anwenden_ergibt_zwei_schritte(
    canvas: DiagrammCanvas, dialog: KlassenDialog, klasse: dict
) -> None:
    dialog.klassenname.setText("Erst")
    dialog.anwenden()
    dialog.klassenname.setText("Dann")
    dialog.anwenden()

    canvas.rueckgaengig()
    assert klasse["name"] == "Erst"
    canvas.rueckgaengig()
    assert klasse["name"] == "Klasse"


def test_ohne_anwenden_bleibt_die_form_unberuehrt(
    dialog: KlassenDialog, klasse: dict
) -> None:
    """„Schließen“ verwirft alles seit dem letzten Anwenden – der Dialog
    arbeitet dafür auf einer Kopie."""
    dialog.klassenname.setText("Verworfen")
    dialog._attribut_neu()

    assert klasse["name"] == "Klasse"
    assert klasse["attributes"] == []


def test_die_form_waechst_mit_ihrem_inhalt(
    dialog: KlassenDialog, klasse: dict
) -> None:
    vorher = klasse["h"]
    for i in range(8):
        dialog._operation_neu()
        dialog.operation_name.setText(f"methode{i}")

    dialog.anwenden()

    assert klasse["h"] > vorher
