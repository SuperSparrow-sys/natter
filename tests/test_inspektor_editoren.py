"""Farbwähler, Auswahlliste und Schriftauswahl im Objektinspektor
(offener Punkt 59).

Bis dahin kannte der Inspektor nur Häkchen, Zeilendialog und
Textzelle. Farben, Aufzählungen und Schriftnamen ließen sich nur
eintippen, und ein falscher Wert blieb unbemerkt: `shape = "kreis"`
zeichnete stillschweigend ein Rechteck.
"""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QComboBox

import ide.inspector.eigenschaften_tabelle as tabellen_modul
from ide.inspector.eigenschaften_tabelle import EigenschaftenTabelle, _WertMitKnopf
from ide.palette.palette import ALLE_KOMPONENTEN
from pcl import Chart, Form, Label, Shape
from pcl.errors import NatterPropertyError
from pcl.properties import (
    ART_FARBE,
    VERSCHACHTELTE_EIGENSCHAFTEN,
    eigenschaften,
)


class _Formular(Form):
    def create_components(self) -> None:
        pass


def _zeile(tabelle: EigenschaftenTabelle, name: str) -> int:
    return next(
        z for z in range(tabelle.rowCount()) if tabelle.item(z, 0).text() == name
    )


def _editor(tabelle: EigenschaftenTabelle, name: str):
    index = tabelle.model().index(_zeile(tabelle, name), 1)
    return tabelle.itemDelegateForColumn(1).createEditor(
        tabelle.viewport(), None, index
    )


def _faelle() -> list[tuple[type, str, type, str]]:
    """Jede Eigenschaft jeder platzierbaren Komponente, die einen
    eigenen Editor braucht, welchen, und woran er sich entscheidet."""
    faelle = []
    for typ in (Form, *ALLE_KOMPONENTEN):
        for name, prop in eigenschaften(typ).items():
            if prop.werte:
                faelle.append((typ, name, QComboBox, "Prop.werte"))
            elif prop.art:
                faelle.append((typ, name, _WertMitKnopf, f"Prop.art={prop.art}"))
        for name, eintrag in VERSCHACHTELTE_EIGENSCHAFTEN.items():
            if eintrag.art and hasattr(typ, eintrag.attribut):
                faelle.append(
                    (typ, name, _WertMitKnopf, f"verschachtelt.art={eintrag.art}")
                )
    return faelle


FAELLE = _faelle()


def _je_editorart() -> list[tuple[type, str, type, str]]:
    """Ein Fall je Editorart.

    Welcher Editor erscheint, entscheidet
    `_EditorDelegat.createEditor` allein an `werte_von` und `art_von`,
    also an `Prop.werte` und `Prop.art` bzw. an der Art der
    verschachtelten Eigenschaft - Komponente und Name spielen keine
    Rolle. Ein Fall je Art prüft deshalb dasselbe wie alle zusammen."""
    vertreter: dict[str, tuple[type, str, type, str]] = {}
    for fall in FAELLE:
        vertreter.setdefault(fall[3], fall)
    return list(vertreter.values())


JE_EDITORART = _je_editorart()


def test_alle_farben_und_auswahlen_sind_erfasst() -> None:
    """Die Liste darf nicht leer auslaufen: wer eine Farbe ohne
    `art=ART_FARBE` deklariert, soll hier auffallen."""
    namen = {name for _, name, _, _ in FAELLE}
    assert {
        "color",
        "pen_color",
        "brush_color",
        "border_color",
        "shape",
        "kind",
        "theme",
        "font_name",
        "picture",
    } <= namen
    for typ in (Form, *ALLE_KOMPONENTEN):
        for name, prop in eigenschaften(typ).items():
            if "#RRGGBB" in prop.doc:
                assert prop.art == ART_FARBE, f"{typ.__name__}.{name}"


@pytest.mark.parametrize(
    ("typ", "name", "editor_typ", "art"),
    JE_EDITORART,
    ids=[f"{t.__name__}.{n}" for t, n, _, _ in JE_EDITORART],
)
def test_jede_editorart_hat_ihren_editor(typ, name, editor_typ, art) -> None:
    formular = _Formular()
    komponente = formular if typ is Form else typ(formular)
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(komponente)

    editor = _editor(tabelle, name)

    assert isinstance(editor, editor_typ)
    if editor_typ is QComboBox:
        erlaubt = eigenschaften(typ)[name].werte
        assert [editor.itemText(i) for i in range(editor.count())] == list(erlaubt)


def test_die_auswahlliste_setzt_den_wert() -> None:
    formular = _Formular()
    form = Shape(formular)
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(form)
    index = tabelle.model().index(_zeile(tabelle, "shape"), 1)
    delegat = tabelle.itemDelegateForColumn(1)
    auswahl = delegat.createEditor(tabelle.viewport(), None, index)

    auswahl.setCurrentText("circle")
    delegat.setModelData(auswahl, tabelle.model(), index)

    assert form.shape == "circle"


def test_der_farbwaehler_setzt_die_farbe(monkeypatch) -> None:
    formular = _Formular()
    label = Label(formular)
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(label)
    monkeypatch.setattr(tabellen_modul, "farbe_erfragen", lambda *_: "#ff8800")
    index = tabelle.model().index(_zeile(tabelle, "color"), 1)
    delegat = tabelle.itemDelegateForColumn(1)
    editor = delegat.createEditor(tabelle.viewport(), None, index)

    editor.dialog_oeffnen()
    delegat.setModelData(editor, tabelle.model(), index)

    assert label.color == "#ff8800"


def test_die_schriftauswahl_setzt_den_namen(monkeypatch) -> None:
    formular = _Formular()
    label = Label(formular)
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(label)
    monkeypatch.setattr(tabellen_modul, "schrift_erfragen", lambda *_: "Arial")
    index = tabelle.model().index(_zeile(tabelle, "font_name"), 1)
    delegat = tabelle.itemDelegateForColumn(1)
    editor = delegat.createEditor(tabelle.viewport(), None, index)

    editor.dialog_oeffnen()
    delegat.setModelData(editor, tabelle.model(), index)

    assert label.font.name == "Arial"


def test_abbrechen_im_dialog_aendert_nichts(monkeypatch) -> None:
    formular = _Formular()
    label = Label(formular)
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(label)
    monkeypatch.setattr(tabellen_modul, "farbe_erfragen", lambda *_: None)
    editor = _editor(tabelle, "color")

    editor.dialog_oeffnen()

    assert editor.feld.text() == ""
    assert label.color == ""


# ------------------------------------------------- ungültige Werte


@pytest.mark.parametrize(
    ("typ", "name", "text", "meldung"),
    [
        (Shape, "shape", "kreis", "kennt den Wert 'kreis' nicht"),
        (Chart, "kind", "torte", "kennt den Wert 'torte' nicht"),
        (Label, "color", "rot", "„rot“ ist keine Farbe"),
        (Shape, "pen_color", "#12", "„#12“ ist keine Farbe"),
        (Shape, "pen_color", "", "pen_color braucht eine Farbe"),
        (Shape, "brush_color", "gelblich", "„gelblich“ ist keine Farbe"),
    ],
)
def test_ungueltige_werte_werden_deutsch_abgelehnt(typ, name, text, meldung) -> None:
    formular = _Formular()
    komponente = typ(formular)
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(komponente)
    zeile = _zeile(tabelle, name)
    vorher = tabelle.item(zeile, 1).text()

    tabelle.item(zeile, 1).setText(text)

    assert meldung in tabelle.fehlertext
    assert tabelle.item(zeile, 1).text() == vorher


def test_eine_leere_farbe_heisst_theme_standard() -> None:
    formular = _Formular()
    label = Label(formular)
    label.color = "#ffffff"
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(label)

    tabelle.item(_zeile(tabelle, "color"), 1).setText("")

    assert label.color == ""
    assert tabelle.fehlertext == ""


def test_farbnamen_gelten_auch() -> None:
    formular = _Formular()
    label = Label(formular)
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(label)

    tabelle.item(_zeile(tabelle, "color"), 1).setText("red")

    assert label.color == "red"
    assert tabelle.fehlertext == ""


def test_auch_im_code_wird_ein_unbekannter_wert_abgelehnt() -> None:
    formular = _Formular()
    form = Shape(formular)

    with pytest.raises(NatterPropertyError, match="Möglich sind: 'rectangle'"):
        form.shape = "kreis"

    assert form.shape == "rectangle"


def test_der_objektinspektor_zeigt_die_meldung() -> None:
    from ide.inspector.objektinspektor import Objektinspektor

    inspektor = Objektinspektor()
    formular = _Formular()
    form = Shape(formular)
    inspektor.eigenschaften_tabelle.komponente_anzeigen(form)
    tabelle = inspektor.eigenschaften_tabelle

    tabelle.item(_zeile(tabelle, "shape"), 1).setText("kreis")

    assert "kreis" in inspektor.meldung.text()
    assert not inspektor.meldung.isHidden()

    tabelle.item(_zeile(tabelle, "shape"), 1).setText("circle")

    assert inspektor.meldung.isHidden()
