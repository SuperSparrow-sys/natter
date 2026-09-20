"""Tests für das Zustandsdiagramm (M9, „Danach“). Headless.

Der Kniff dabei ist der Zustand selbst: er trägt in der ersten Zeile
seinen Namen und darunter seine Aktionen (`entry / …`). Dafür gibt es
bewusst kein zweites Eingabefeld – der Doppelklick auf die Form
bearbeitet beides zusammen, wie bei einer Notiz.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage, QPainter

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.canvas import DiagrammCanvas
from ide.diagramm.formen import formen_fuer, verbindungen_fuer
from ide.diagramm.neu import MVP_TYPEN
from ide.diagramm.stil import stil as stil_zu_namen
from ide.diagramm.zeichnen import (
    beschriftungs_rechtecke,
    form_zeichnen,
    mindestbreite,
    mindesthoehe,
    verbindung_zeichnen,
    verbindungsbeschriftungen_zeichnen,
    zustandszeilen,
)


@pytest.fixture
def flaeche(tmp_path: Path) -> DiagrammCanvas:
    fenster = DiagrammFenster(diagramm_erzeugen("state", tmp_path / "z.pdiag", "Ampel"))
    return fenster.zeichenflaeche


def _gemalt(shape: dict, stil_name: str = "modern-light") -> set[str]:
    stil = stil_zu_namen(stil_name)
    bild = QImage(420, 320, QImage.Format.Format_RGB32)
    bild.fill(QColor(stil.hintergrund))
    maler = QPainter(bild)
    form_zeichnen(maler, shape, stil)
    maler.end()
    return {
        bild.pixelColor(x, y).name()
        for x in range(0, bild.width(), 2)
        for y in range(0, bild.height(), 2)
    }


# -- Katalog -------------------------------------------------------------


def test_die_palette_bietet_die_sechs_formen() -> None:
    kinds = [form.kind for form in formen_fuer("state")]

    assert kinds == [
        "initial_state",
        "state",
        "composite_state",
        "decision",
        "final_state",
        "note",
    ]


def test_der_uebergang_hat_eine_offene_spitze() -> None:
    arten = verbindungen_fuer("state")

    assert [art.kind for art in arten] == ["transition"]
    assert arten[0].spitze_am_ziel == "offen"
    assert arten[0].gestrichelt is False


def test_der_typ_laesst_sich_neu_anlegen() -> None:
    assert "state" in MVP_TYPEN


# -- Name und Aktionen ---------------------------------------------------


def test_die_erste_zeile_ist_der_name() -> None:
    kopf, aktionen = zustandszeilen({"name": "Rot\nentry / Licht an\nexit / Licht aus"})

    assert kopf == "Rot"
    assert aktionen == ["entry / Licht an", "exit / Licht aus"]


def test_leere_zeilen_zaehlen_nicht_mit() -> None:
    """Wer beim Tippen eine Leerzeile lässt, soll keine leere
    Aktionszeile bekommen."""
    _, aktionen = zustandszeilen({"name": "Rot\n\n  \nentry / Licht an"})

    assert aktionen == ["entry / Licht an"]


def test_ein_zustand_ohne_aktionen_braucht_nur_eine_kopfhoehe(
    flaeche: DiagrammCanvas,
) -> None:
    ohne = flaeche.form_platzieren("state", 200, 150)
    ohne["name"] = "Rot"
    mit = flaeche.form_platzieren("state", 200, 150)
    mit["name"] = "Rot\nentry / Licht an\nexit / Licht aus"

    assert mindesthoehe(mit) > mindesthoehe(ohne)


def test_die_aktionen_werden_wirklich_gemalt(flaeche: DiagrammCanvas) -> None:
    form = flaeche.form_platzieren("state", 200, 150)
    form["x"], form["y"], form["w"], form["h"] = 20, 20, 300, 100

    ohne = _gemalt({**form, "name": "Rot"})
    mit = _gemalt({**form, "name": "Rot\nentry / Licht an"})

    assert len(mit) > len(ohne)


# -- Darstellung ---------------------------------------------------------


@pytest.mark.parametrize(
    "kind", ["initial_state", "state", "composite_state", "decision", "final_state"]
)
def test_jede_form_malt_wirklich_etwas(flaeche: DiagrammCanvas, kind: str) -> None:
    form = flaeche.form_platzieren(kind, 200, 150)
    form["x"], form["y"] = 30, 30

    assert len(_gemalt(form)) > 1, f"{kind} malt nur den Hintergrund"


def test_der_startzustand_ist_ausgefuellt(flaeche: DiagrammCanvas) -> None:
    stil = stil_zu_namen("modern-light")
    start = flaeche.form_platzieren("initial_state", 100, 100)
    start["x"], start["y"] = 30, 30

    assert QColor(stil.text).name() in _gemalt(start)


def test_der_zusammengesetzte_zustand_ist_nicht_gefuellt(
    flaeche: DiagrammCanvas,
) -> None:
    """Er enthält andere Zustände; eine Füllung würde sie verdecken,
    sobald jemand ihn nach vorn holt."""
    stil = stil_zu_namen("modern-light")
    ober = flaeche.form_platzieren("composite_state", 200, 150)
    ober["x"], ober["y"], ober["w"], ober["h"] = 20, 20, 360, 240

    assert QColor(stil.fuellung).name() not in _gemalt(ober)


def test_ein_oberzustand_voller_zustaende_ist_kein_layout_fehler(
    flaeche: DiagrammCanvas,
) -> None:
    ober = flaeche.form_platzieren("composite_state", 300, 200)
    ober["x"], ober["y"], ober["w"], ober["h"] = 40, 40, 400, 300
    innen = flaeche.form_platzieren("state", 200, 150)
    innen["x"], innen["y"], innen["w"], innen["h"] = 100, 100, 176, 72

    hinweise = flaeche.hinweise_aktualisieren()

    assert not [h for h in hinweise if h.regel == "ueberlappung"]


# -- Aus der Sichtprüfung ------------------------------------------------


def test_die_mindestbreite_misst_die_zeilen_einzeln(flaeche: DiagrammCanvas) -> None:
    """Fund aus der Sichtprüfung: alle Zeilen als eine gemessen
    ergaben 627 px Mindestbreite für einen Kasten, in den jede Zeile
    einzeln bequem passte."""
    form = flaeche.form_platzieren("state", 200, 150)
    form["name"] = "Rot\nentry / rotes Licht an\nexit / rotes Licht aus"

    breite = mindestbreite(form)

    einzeilig = dict(form)
    einzeilig["name"] = "Rot entry / rotes Licht an exit / rotes Licht aus"
    assert breite < mindestbreite({**einzeilig, "kind": "class"}) / 1.5


def test_die_meldung_nennt_nur_die_erste_zeile(flaeche: DiagrammCanvas) -> None:
    """Zweiter Fund: die Meldung druckte den ganzen mehrzeiligen Namen
    und war in der Liste unlesbar."""
    form = flaeche.form_platzieren("state", 200, 150)
    form["name"] = "Rot\nentry / ein sehr langer Text, der ganz sicher nicht passt"
    form["w"] = 80

    hinweise = flaeche.hinweise_aktualisieren()

    schmal = [h for h in hinweise if h.regel == "abgeschnittener_text"]
    assert schmal, "der Hinweis fehlt ganz"
    assert "\n" not in schmal[0].meldung
    assert "„Rot“" in schmal[0].meldung


# -- Übergänge -----------------------------------------------------------


def test_die_beschriftung_der_mitte_steht_auf_der_linie(
    flaeche: DiagrammCanvas,
) -> None:
    """Im Zustandsdiagramm trägt sie den ganzen Übergang:
    „Ereignis [Bedingung] / Aktion“."""
    von = flaeche.form_platzieren("state", 120, 150)
    nach = flaeche.form_platzieren("state", 420, 150)
    uebergang = flaeche.verbindung_erstellen("transition", von, nach)
    uebergang["labels"] = {"mitte": "Taste [gedrückt] / merken"}

    rechtecke = beschriftungs_rechtecke(uebergang, von, nach)

    assert "mitte" in rechtecke
    mitte_x = (von["x"] + von["w"] + nach["x"]) / 2
    assert abs(rechtecke["mitte"].center().x() - mitte_x) < 30


def test_die_beschriftung_der_mitte_wird_gemalt(flaeche: DiagrammCanvas) -> None:
    stil = stil_zu_namen("modern-light")
    von = flaeche.form_platzieren("state", 120, 150)
    nach = flaeche.form_platzieren("state", 420, 150)
    uebergang = flaeche.verbindung_erstellen("transition", von, nach)

    def textpixel(v: dict) -> int:
        bild = QImage(560, 300, QImage.Format.Format_RGB32)
        bild.fill(QColor(stil.hintergrund))
        maler = QPainter(bild)
        verbindung_zeichnen(maler, v, von, nach, stil)
        verbindungsbeschriftungen_zeichnen(maler, v, von, nach, stil)
        maler.end()
        return sum(
            bild.pixelColor(x, y).name() == QColor(stil.text).name()
            for x in range(bild.width())
            for y in range(bild.height())
        )

    ohne = textpixel(uebergang)
    uebergang["labels"] = {"mitte": "nach 20 s"}

    assert textpixel(uebergang) > ohne


def test_die_beschriftung_der_mitte_laesst_sich_verschieben(
    flaeche: DiagrammCanvas,
) -> None:
    von = flaeche.form_platzieren("state", 120, 150)
    nach = flaeche.form_platzieren("state", 420, 150)
    uebergang = flaeche.verbindung_erstellen("transition", von, nach)
    uebergang["labels"] = {"mitte": "nach 20 s"}

    vorher = beschriftungs_rechtecke(uebergang, von, nach)["mitte"].center()
    uebergang["label_offsets"] = {"mitte": [25, -40]}
    nachher = beschriftungs_rechtecke(uebergang, von, nach)["mitte"].center()

    assert nachher.x() - vorher.x() == pytest.approx(25)
    assert nachher.y() - vorher.y() == pytest.approx(-40)


def test_auch_eine_assoziation_darf_eine_mitte_haben(tmp_path: Path) -> None:
    """Die Beschriftung der Mitte gilt für alle Verbindungsarten – im
    Klassendiagramm trägt sie den Namen einer Assoziation."""
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))
    flaeche = fenster.zeichenflaeche
    erste = flaeche.form_platzieren("class", 120, 150)
    zweite = flaeche.form_platzieren("class", 480, 150)
    verbindung = flaeche.verbindung_erstellen("association", erste, zweite)
    verbindung["labels"] = {"mitte": "gehört zu"}

    assert "mitte" in beschriftungs_rechtecke(verbindung, erste, zweite)


# -- Speichern -----------------------------------------------------------


def test_speichern_und_laden(tmp_path: Path) -> None:
    from ide.diagramm.datei import Diagramm

    pfad = tmp_path / "s.pdiag"
    fenster = DiagrammFenster(diagramm_erzeugen("state", pfad, "Ampel"))
    flaeche = fenster.zeichenflaeche
    start = flaeche.form_platzieren("initial_state", 100, 100)
    rot = flaeche.form_platzieren("state", 300, 100)
    rot["name"] = "Rot\nentry / Licht an"
    uebergang = flaeche.verbindung_erstellen("transition", start, rot)
    uebergang["labels"] = {"mitte": "start"}
    fenster.speichern()

    geladen = Diagramm.laden(pfad)

    assert geladen.typ == "state"
    wieder = next(f for f in geladen.daten["shapes"] if f["kind"] == "state")
    assert zustandszeilen(wieder) == ("Rot", ["entry / Licht an"])
    assert geladen.daten["connectors"][0]["labels"]["mitte"] == "start"
