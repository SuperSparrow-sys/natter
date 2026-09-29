"""Optionen aus dem Klassendialog in der Zeichnung (Punkt 70 der
offenen Punkte).

Stereotyp, „Kommentare sichtbar“, „Dokumentationsauszeichnung
anzeigen“ und „Umbruch nach dieser Länge“ für Kommentare ließen sich
einstellen, gelesen hat sie aber nur der Dialog selbst.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.stil import stil as stil_zu_namen
from ide.diagramm.uml_modell import (
    kommentarzeilen,
    operation_zeile,
    stereotyp_text,
    stereotypzeile,
)
from ide.diagramm.zeichnen import (
    KOPFHOEHE,
    form_zeichnen,
    klassen_bereiche,
    klassenkopfhoehe,
    mindesthoehe,
)

KOMMENTAR = "Verwaltet alle Konten einer Bank und bucht zwischen ihnen um."


def _klasse(**werte) -> dict:
    return {
        "id": "s1",
        "kind": "class",
        "x": 10,
        "y": 10,
        "w": 260,
        "h": 220,
        "name": "Bank",
        "comment": KOMMENTAR,
        "attributes": [{"name": "konten", "type": "list", "visibility": "private"}],
        "operations": [{"name": "buchen", "visibility": "public"}],
        **werte,
    }


def _bild(form: dict) -> QImage:
    bild = QImage(300, 260, QImage.Format.Format_ARGB32)
    bild.fill(Qt.GlobalColor.white)
    maler = QPainter(bild)
    form_zeichnen(maler, form, stil_zu_namen("modern-light"))
    maler.end()
    return bild


# -- Stereotyp -----------------------------------------------------------


@pytest.mark.parametrize("roh", ["entity", "«entity»", "<<entity>>", "  entity "])
def test_stereotyp_steht_einmal_in_winkelklammern(roh: str) -> None:
    assert stereotyp_text(roh) == "entity"
    assert stereotypzeile(_klasse(stereotype=roh)) == "«entity»"


def test_interface_mit_eigenem_stereotyp_traegt_beide() -> None:
    assert stereotypzeile({"kind": "interface"}) == "«interface»"
    assert stereotypzeile({"kind": "interface", "stereotype": "remote"}) == (
        "«interface, remote»"
    )
    assert stereotypzeile({"kind": "interface", "stereotype": "Interface"}) == (
        "«interface»"
    )
    assert stereotypzeile({"kind": "class"}) == ""


def test_stereotyp_schiebt_den_namen_eine_zeile_tiefer(qtbot) -> None:  # noqa: ANN001
    ohne = _klasse()
    mit = _klasse(stereotype="entity")

    assert klassenkopfhoehe(mit) == klassenkopfhoehe(ohne) + KOPFHOEHE
    assert klassen_bereiche(mit)["name"].top() == ohne["y"] + KOPFHOEHE
    assert mindesthoehe(mit) == mindesthoehe(ohne) + KOPFHOEHE
    assert _bild(mit) != _bild(ohne)


def test_stereotyp_einer_operation_steht_davor() -> None:
    assert operation_zeile(
        {"name": "__init__", "visibility": "public", "stereotype": "create"}
    ) == "«create» +__init__()"


# -- Kommentar und Dokumentation -----------------------------------------


def test_kommentar_nur_wenn_eingeschaltet() -> None:
    assert kommentarzeilen(_klasse()) == []
    zeilen = kommentarzeilen(_klasse(comments_visible=True, wrap_after_comments=0))
    assert zeilen == [KOMMENTAR]


def test_dokumentation_in_uml_schreibweise() -> None:
    zeilen = kommentarzeilen(_klasse(show_documentation=True, wrap_after_comments=0))

    assert zeilen == [f"{{documentation = {KOMMENTAR}}}"]


def test_umbruch_nach_der_eingestellten_laenge() -> None:
    zeilen = kommentarzeilen(_klasse(comments_visible=True, wrap_after_comments=17))

    assert len(zeilen) > 3
    assert all(len(zeile) <= 17 for zeile in zeilen)
    assert " ".join(zeilen) == KOMMENTAR


def test_ohne_kommentartext_bleibt_der_kasten_wie_er_ist() -> None:
    form = _klasse(comment="", comments_visible=True)

    assert klassenkopfhoehe(form) == KOPFHOEHE


@pytest.mark.parametrize(
    "option",
    [
        {"stereotype": "entity"},
        {"comments_visible": True},
        {"show_documentation": True},
    ],
)
def test_jede_option_aendert_die_zeichnung(qtbot, option: dict) -> None:  # noqa: ANN001
    assert _bild(_klasse(**option)) != _bild(_klasse())


def test_umbruchlaenge_aendert_die_zeichnung(qtbot) -> None:  # noqa: ANN001
    kurz = _klasse(comments_visible=True, wrap_after_comments=12)
    lang = _klasse(comments_visible=True, wrap_after_comments=40)

    assert klassenkopfhoehe(kurz) > klassenkopfhoehe(lang)
    assert _bild(kurz) != _bild(lang)


def test_attribute_rutschen_unter_den_kommentar(qtbot) -> None:  # noqa: ANN001
    form = _klasse(comments_visible=True)

    assert klassen_bereiche(form)["attributes"].top() == pytest.approx(
        form["y"] + klassenkopfhoehe(form)
    )
    assert klassen_bereiche(form)["name"].top() == form["y"]


def test_anwenden_im_dialog_macht_die_klasse_hoch_genug(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))
    flaeche = fenster.zeichenflaeche
    form = flaeche.form_platzieren("class", 300, 300)
    vorher = form["h"]

    dialog = flaeche.eigenschaften_dialog(form)
    dialog.stereotyp.setText("entity")
    dialog.kommentar.setPlainText(KOMMENTAR)
    dialog.kommentare_sichtbar.setChecked(True)
    dialog.anwenden()

    assert form["stereotype"] == "entity"
    assert form["h"] >= mindesthoehe(form) > vorher
