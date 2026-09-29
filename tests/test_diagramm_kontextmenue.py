"""Kontextmenü in den Zeichenflächen der Formen-Diagramme und der
Entscheidungstabelle (Punkt 65 der offenen Punkte).

`contextMenuEvent` gab es nur im Struktogramm. Die rechte Maustaste
tat im Klassen-, Use-Case-, Aktivitäts-, Zustands- und
Sequenzdiagramm sowie in der Entscheidungstabelle nichts.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QInputDialog, QMenu

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.canvas import DiagrammCanvas
from ide.diagramm.datei import FORMEN_TYPEN
from ide.diagramm.formen import formen_fuer, verbindungen_fuer
from ide.diagramm.tabelle import zellen
from ide.diagramm.tabelle_canvas import VERSATZ, TabellenCanvas
from ide.diagramm.zeichnen import verbindungs_punkte


def _fenster(tmp_path: Path, typ: str) -> DiagrammFenster:
    return DiagrammFenster(diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", "k"))


def _eintrag(menue: QMenu, text: str):  # noqa: ANN202
    for aktion in menue.actions():
        if aktion.text() == text:
            return aktion
        if aktion.menu() is not None:
            gefunden = _eintrag(aktion.menu(), text)
            if gefunden is not None:
                return gefunden
    return None


def _texte(menue: QMenu) -> list[str]:
    return [a.text() for a in menue.actions() if a.text()]


def _mitte(form: dict) -> tuple[float, float]:
    return form["x"] + form["w"] / 2, form["y"] + form["h"] / 2


@pytest.mark.parametrize("typ", FORMEN_TYPEN)
def test_jede_formenflaeche_hat_ein_kontextmenue(
    qtbot, tmp_path: Path, typ: str  # noqa: ANN001
) -> None:
    """Das Kriterium aus dem Punkt: für eine Form, für eine Verbindung
    und für die leere Fläche je ein passendes Menü."""
    flaeche: DiagrammCanvas = _fenster(tmp_path, typ).zeichenflaeche
    art = formen_fuer(typ)[0].kind
    a = flaeche.form_platzieren(art, 200, 300)
    b = flaeche.form_platzieren(art, 700, 300)
    verbindung = flaeche.verbindung_erstellen(verbindungen_fuer(typ)[0].kind, a, b)
    flaeche.auswahl_aufheben()

    formmenue = flaeche.kontextmenue_fuer(*_mitte(a))
    assert "Löschen" in _texte(formmenue)
    assert "Duplizieren" in _texte(formmenue)
    assert flaeche.ausgewaehlte_form is a

    leer = flaeche.kontextmenue_fuer(5, 5)
    assert "Alles auswählen" in _texte(leer)
    assert flaeche.ausgewaehlte_form is None

    flaeche._verbindung_auswaehlen(verbindung)
    punkte = verbindungs_punkte(verbindung, a, b)
    x = (punkte[0].x() + punkte[1].x()) / 2
    y = (punkte[0].y() + punkte[1].y()) / 2
    linienmenue = flaeche.kontextmenue_fuer(x, y)
    assert "Art" in _texte(linienmenue)
    assert flaeche.ausgewaehlte_verbindung is verbindung

    _eintrag(linienmenue, "Löschen").trigger()
    assert verbindung not in flaeche.verbindungen


@pytest.fixture
def klassen(qtbot, tmp_path: Path) -> DiagrammFenster:  # noqa: ANN001
    return _fenster(tmp_path, "class")


def test_form_duplizieren_und_loeschen(klassen: DiagrammFenster) -> None:
    flaeche = klassen.zeichenflaeche
    form = flaeche.form_platzieren("class", 200, 200)

    _eintrag(flaeche.kontextmenue_fuer(*_mitte(form)), "Duplizieren").trigger()
    assert len(flaeche.formen) == 2
    kopie = flaeche.formen[-1]

    # Die Kopie liegt versetzt obenauf; ihre Mitte trifft sie
    _eintrag(flaeche.kontextmenue_fuer(*_mitte(kopie)), "Löschen").trigger()
    assert len(flaeche.formen) == 1
    assert flaeche.formen[0] is form


def test_eigenschaften_einer_klasse(
    klassen: DiagrammFenster, monkeypatch: pytest.MonkeyPatch
) -> None:
    flaeche = klassen.zeichenflaeche
    form = flaeche.form_platzieren("class", 200, 200)
    geoeffnet: list[dict] = []
    monkeypatch.setattr(
        flaeche, "eigenschaften_bearbeiten", lambda f=None: geoeffnet.append(f)
    )

    _eintrag(flaeche.kontextmenue_fuer(*_mitte(form)), "Eigenschaften …").trigger()

    assert geoeffnet == [form]


def test_ausrichten_mit_mehreren_formen(klassen: DiagrammFenster) -> None:
    flaeche = klassen.zeichenflaeche
    a = flaeche.form_platzieren("class", 200, 200)
    b = flaeche.form_platzieren("class", 600, 400)
    flaeche._auswahl_setzen([b, a])

    menue = flaeche.kontextmenue_fuer(*_mitte(a))
    assert len(flaeche.auswahl) == 2  # die Auswahl bleibt stehen
    _eintrag(menue, "Oben").trigger()

    assert b["y"] == a["y"]


def test_vordergrund_ueber_das_kontextmenue(klassen: DiagrammFenster) -> None:
    flaeche = klassen.zeichenflaeche
    a = flaeche.form_platzieren("class", 200, 200)
    flaeche.form_platzieren("class", 600, 200)

    _eintrag(flaeche.kontextmenue_fuer(*_mitte(a)), "In den Vordergrund").trigger()

    assert flaeche.formen[-1] is a


def test_knickpunkt_und_art_ueber_das_kontextmenue(klassen: DiagrammFenster) -> None:
    flaeche = klassen.zeichenflaeche
    a = flaeche.form_platzieren("class", 200, 200)
    b = flaeche.form_platzieren("class", 800, 200)
    verbindung = flaeche.verbindung_erstellen("association", a, b)
    x, y = 500, a["y"] + a["h"] / 2

    _eintrag(flaeche.kontextmenue_fuer(x, y), "Knickpunkt einfügen").trigger()
    assert len(verbindung["waypoints"]) == 1

    kx, ky = verbindung["waypoints"][0]
    menue = flaeche.kontextmenue_fuer(kx, ky)
    assert _eintrag(menue, "Knickpunkt einfügen") is None
    _eintrag(menue, "Knickpunkt entfernen").trigger()
    assert verbindung["waypoints"] == []

    menue = flaeche.kontextmenue_fuer(x, y)
    assert _eintrag(menue, "Assoziation").isChecked()
    _eintrag(menue, "Komposition").trigger()
    assert verbindung["kind"] == "composition"
    flaeche.rueckgaengig()
    assert verbindung["kind"] == "association"


def test_einfuegen_nur_mit_passender_zwischenablage(klassen: DiagrammFenster) -> None:
    flaeche = klassen.zeichenflaeche
    form = flaeche.form_platzieren("class", 200, 200)
    flaeche.kopieren()

    menue = flaeche.kontextmenue_fuer(900, 700)
    _eintrag(menue, "Einfügen").trigger()

    assert len(flaeche.formen) == 2
    assert flaeche.formen[0] is form


# -- Entscheidungstabelle ------------------------------------------------


@pytest.fixture
def tabelle(qtbot, tmp_path: Path) -> TabellenCanvas:  # noqa: ANN001
    flaeche = _fenster(tmp_path, "entscheidungstabelle").zeichenflaeche
    flaeche.diagramm.daten["conditions"] = [
        {"text": "Ampel an?", "values": ["J", "N", "*"]}
    ]
    flaeche.diagramm.daten["actions"] = [{"text": "grün", "values": ["X", "", "X"]}]
    return flaeche


def _zellmitte(flaeche: TabellenCanvas, teil: str, zeile: int, spalte: int):  # noqa: ANN202
    zelle = next(
        z
        for z in zellen(flaeche.diagramm.daten, VERSATZ, VERSATZ)
        if (z.teil, z.zeile, z.spalte) == (teil, zeile, spalte)
    )
    return zelle.rechteck.center().x(), zelle.rechteck.center().y()


def test_tabelle_rechtsklick_schaltet_die_zelle_nicht(tabelle: TabellenCanvas) -> None:
    menue = tabelle.kontextmenue_fuer(*_zellmitte(tabelle, "conditions", 0, 1))

    assert tabelle.diagramm.daten["conditions"][0]["values"] == ["J", "N", "*"]
    assert tabelle.ausgewaehlte_zelle.spalte == 1
    assert {"Regel entfernen", "Zeile entfernen", "Regel nach links"} <= set(
        _texte(menue)
    )


def test_tabelle_regel_der_zelle_entfernen_und_verschieben(
    tabelle: TabellenCanvas,
) -> None:
    menue = tabelle.kontextmenue_fuer(*_zellmitte(tabelle, "actions", 0, 1))
    _eintrag(menue, "Regel entfernen").trigger()
    assert tabelle.diagramm.daten["conditions"][0]["values"] == ["J", "*"]

    menue = tabelle.kontextmenue_fuer(*_zellmitte(tabelle, "conditions", 0, 0))
    assert not _eintrag(menue, "Regel nach links").isEnabled()
    _eintrag(menue, "Regel nach rechts").trigger()
    assert tabelle.diagramm.daten["conditions"][0]["values"] == ["*", "J"]


def test_tabelle_zeilen_ueber_das_kontextmenue(
    tabelle: TabellenCanvas, monkeypatch: pytest.MonkeyPatch
) -> None:
    menue = tabelle.kontextmenue_fuer(*_zellmitte(tabelle, "conditions", 0, -1))
    _eintrag(menue, "Bedingung hinzufügen").trigger()
    assert len(tabelle.diagramm.daten["conditions"]) == 2

    monkeypatch.setattr(
        QInputDialog, "getText", staticmethod(lambda *a, **k: ("Taster?", True))
    )
    menue = tabelle.kontextmenue_fuer(*_zellmitte(tabelle, "conditions", 1, -1))
    _eintrag(menue, "Bedingung beschriften …").trigger()
    assert tabelle.diagramm.daten["conditions"][1]["text"] == "Taster?"

    _eintrag(menue, "Zeile entfernen").trigger()
    assert len(tabelle.diagramm.daten["conditions"]) == 1


def test_tabelle_leere_flaeche(tabelle: TabellenCanvas) -> None:
    menue = tabelle.kontextmenue_fuer(2, 2)

    assert tabelle.ausgewaehlte_zelle is None
    assert "Regel entfernen" not in _texte(menue)
    _eintrag(menue, "Regel hinzufügen").trigger()
    assert tabelle.diagramm.daten["conditions"][0]["values"] == ["J", "N", "*", ""]
