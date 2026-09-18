"""Tests für Mehrfachauswahl und Anordnen im Diagramm-Editor
(M9, Teilschritt 3b). Headless.

Aufgeteilt nach dem, was die Bedienerin tut: auswählen, gemeinsam
bewegen, ausrichten, verteilen, stapeln, gruppieren, kopieren.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.canvas import DiagrammCanvas


@pytest.fixture
def flaeche(tmp_path: Path) -> DiagrammCanvas:
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))
    return fenster.zeichenflaeche


@pytest.fixture
def drei(flaeche: DiagrammCanvas) -> list[dict]:
    """Drei Formen an unterschiedlichen Stellen und in unterschiedlicher
    Größe – gleich große Formen würden beim Ausrichten nicht zeigen, ob
    wirklich die richtige Kante genommen wurde."""
    formen = [
        flaeche.form_platzieren("class", 100, 100),
        flaeche.form_platzieren("class", 300, 200),
        flaeche.form_platzieren("class", 500, 400),
    ]
    for form, breite in zip(formen, (120, 160, 200), strict=True):
        form["w"] = breite
    flaeche.auswahl_aufheben()
    return formen


def _maus(x: float, y: float, typ, strg: bool = False) -> QMouseEvent:
    return QMouseEvent(
        typ,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ControlModifier if strg else Qt.KeyboardModifier.NoModifier,
    )


def _taste(taste, strg: bool = False, umschalt: bool = False) -> QKeyEvent:
    modifikatoren = Qt.KeyboardModifier.NoModifier
    if strg:
        modifikatoren |= Qt.KeyboardModifier.ControlModifier
    if umschalt:
        modifikatoren |= Qt.KeyboardModifier.ShiftModifier
    return QKeyEvent(QEvent.Type.KeyPress, taste, modifikatoren)


def _mitte(form: dict) -> tuple[float, float]:
    return form["x"] + form["w"] / 2, form["y"] + form["h"] / 2


def _anklicken(flaeche: DiagrammCanvas, form: dict, strg: bool = False) -> None:
    x, y = _mitte(form)
    flaeche.mousePressEvent(_maus(x, y, QEvent.Type.MouseButtonPress, strg))
    flaeche.mouseReleaseEvent(_maus(x, y, QEvent.Type.MouseButtonRelease, strg))


# -- Auswählen -----------------------------------------------------------


def test_eine_form_anklicken_waehlt_nur_sie(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    _anklicken(flaeche, drei[1])

    assert flaeche.auswahl == (drei[1],)
    assert flaeche.ausgewaehlte_form is drei[1]


def test_strg_klick_nimmt_dazu(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    _anklicken(flaeche, drei[0])
    _anklicken(flaeche, drei[2], strg=True)

    assert set(map(id, flaeche.auswahl)) == {id(drei[0]), id(drei[2])}


def test_strg_klick_nimmt_wieder_heraus(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    _anklicken(flaeche, drei[0])
    _anklicken(flaeche, drei[1], strg=True)

    _anklicken(flaeche, drei[1], strg=True)

    assert flaeche.auswahl == (drei[0],)


def test_die_zuletzt_angeklickte_fuehrt(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    """Woran sich „Ausrichten" orientiert, muss vorhersagbar sein."""
    _anklicken(flaeche, drei[0])
    _anklicken(flaeche, drei[2], strg=True)

    assert flaeche.ausgewaehlte_form is drei[2]


def test_alles_auswaehlen(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche.keyPressEvent(_taste(Qt.Key.Key_A, strg=True))

    assert len(flaeche.auswahl) == 3


def test_rahmen_nimmt_nur_was_ganz_drin_liegt(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    """Nur Berühren würde beim Aufziehen über ein dicht gestelltes
    Diagramm ständig Nachbarn mitnehmen, die man nicht meint.

    Der Rahmen deckt die erste Form ganz ab und **schneidet die zweite
    an** – genau daran entscheidet sich die Frage.
    """
    assert drei[0]["x"] + drei[0]["w"] < 300 < drei[1]["x"] + drei[1]["w"]

    flaeche.mousePressEvent(_maus(0, 0, QEvent.Type.MouseButtonPress))
    flaeche.mouseMoveEvent(_maus(300, 300, QEvent.Type.MouseMove))
    flaeche.mouseReleaseEvent(_maus(300, 300, QEvent.Type.MouseButtonRelease))

    assert set(map(id, flaeche.auswahl)) == {id(drei[0])}


def test_klick_ins_leere_hebt_die_auswahl_auf(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche.alles_auswaehlen()

    flaeche.mousePressEvent(_maus(900, 900, QEvent.Type.MouseButtonPress))
    flaeche.mouseReleaseEvent(_maus(900, 900, QEvent.Type.MouseButtonRelease))

    assert flaeche.auswahl == ()


# -- Gemeinsam bewegen ---------------------------------------------------


def test_ziehen_bewegt_die_ganze_auswahl(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche.alles_auswaehlen()
    vorher = [(form["x"], form["y"]) for form in drei]
    x, y = _mitte(drei[0])

    flaeche.mousePressEvent(_maus(x, y, QEvent.Type.MouseButtonPress))
    flaeche.mouseMoveEvent(_maus(x + 40, y + 24, QEvent.Type.MouseMove))
    flaeche.mouseReleaseEvent(_maus(x + 40, y + 24, QEvent.Type.MouseButtonRelease))

    versatz = {
        (form["x"] - alt_x, form["y"] - alt_y)
        for form, (alt_x, alt_y) in zip(drei, vorher, strict=True)
    }
    assert len(versatz) == 1, "die Formen sind unterschiedlich weit gewandert"
    assert versatz != {(0, 0)}


def test_ziehen_der_auswahl_ist_ein_undo_schritt(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche.alles_auswaehlen()
    vorher = [(form["x"], form["y"]) for form in drei]
    x, y = _mitte(drei[0])
    flaeche.mousePressEvent(_maus(x, y, QEvent.Type.MouseButtonPress))
    flaeche.mouseMoveEvent(_maus(x + 40, y + 24, QEvent.Type.MouseMove))
    flaeche.mouseReleaseEvent(_maus(x + 40, y + 24, QEvent.Type.MouseButtonRelease))

    flaeche.rueckgaengig()

    assert [(form["x"], form["y"]) for form in drei] == vorher


def test_eine_form_aus_der_auswahl_anzuklicken_behaelt_sie(
    flaeche: DiagrammCanvas, drei: list[dict]
) -> None:
    """Sonst könnte man mehrere Formen nie gemeinsam ziehen: der Klick
    zum Anfassen würde die Auswahl schon zusammenfallen lassen."""
    flaeche.alles_auswaehlen()
    x, y = _mitte(drei[1])

    flaeche.mousePressEvent(_maus(x, y, QEvent.Type.MouseButtonPress))

    assert len(flaeche.auswahl) == 3


def test_pfeiltaste_bewegt_die_ganze_auswahl(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche.alles_auswaehlen()
    vorher = [form["x"] for form in drei]

    flaeche.keyPressEvent(_taste(Qt.Key.Key_Right))

    assert [form["x"] for form in drei] == [x + 8 for x in vorher]


def test_loeschen_nimmt_die_ganze_auswahl(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche.alles_auswaehlen()

    flaeche.loeschen()

    assert flaeche.formen == []
    flaeche.rueckgaengig()
    assert len(flaeche.formen) == 3


# -- Ausrichten ----------------------------------------------------------


@pytest.mark.parametrize(
    ("art", "achse"),
    [("links", "x"), ("oben", "y")],
)
def test_ausrichten_an_der_fuehrenden_form(
    flaeche: DiagrammCanvas, drei: list[dict], art: str, achse: str
) -> None:
    flaeche.alles_auswaehlen()
    bezug = flaeche.ausgewaehlte_form

    assert flaeche.ausrichten(art) is True

    assert {form[achse] for form in drei} == {bezug[achse]}


def test_rechtsbuendig_rechnet_die_breite_mit(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    """Der Knackpunkt: unterschiedlich breite Formen müssen an ihrer
    **rechten** Kante bündig stehen, nicht an ihrer linken."""
    flaeche.alles_auswaehlen()
    bezug = flaeche.ausgewaehlte_form

    flaeche.ausrichten("rechts")

    kanten = {form["x"] + form["w"] for form in drei}
    assert kanten == {bezug["x"] + bezug["w"]}


def test_senkrecht_mittig(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche.alles_auswaehlen()

    flaeche.ausrichten("senkrechte_mitte")

    mitten = {form["x"] + form["w"] / 2 for form in drei}
    assert max(mitten) - min(mitten) <= 1  # ganzzahlige Koordinaten


def test_ausrichten_ist_ein_undo_schritt(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche.alles_auswaehlen()
    vorher = [form["x"] for form in drei]

    flaeche.ausrichten("links")
    flaeche.rueckgaengig()

    assert [form["x"] for form in drei] == vorher


def test_ausrichten_braucht_zwei_formen(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche._auswaehlen(drei[0])

    assert flaeche.ausrichten("links") is False


def test_unbekannte_ausrichtung_tut_nichts(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche.alles_auswaehlen()

    assert flaeche.ausrichten("diagonal") is False


# -- Verteilen -----------------------------------------------------------


def test_verteilen_ergibt_gleiche_abstaende(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    """Gleiche **Lücken**, nicht gleiche Mittenabstände – bei
    unterschiedlich breiten Klassen sieht nur das gleichmäßig aus."""
    flaeche.alles_auswaehlen()

    assert flaeche.verteilen("waagerecht") is True

    sortiert = sorted(drei, key=lambda f: f["x"])
    luecken = [
        naechste["x"] - (form["x"] + form["w"])
        for form, naechste in zip(sortiert, sortiert[1:], strict=False)
    ]
    assert max(luecken) - min(luecken) <= 1


def test_verteilen_laesst_die_aeusseren_stehen(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    """Sonst wanderte die ganze Reihe bei jedem Aufruf davon."""
    flaeche.alles_auswaehlen()
    sortiert = sorted(drei, key=lambda f: f["x"])
    links, rechts = sortiert[0]["x"], sortiert[-1]["x"]

    flaeche.verteilen("waagerecht")

    assert sortiert[0]["x"] == links
    assert sortiert[-1]["x"] == rechts


def test_verteilen_braucht_drei_formen(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    """Mit zweien gibt es nichts zu verteilen – der Abstand dazwischen
    ist, was er ist."""
    flaeche._auswaehlen(drei[0])
    flaeche.auswahl_umschalten(drei[1])

    assert flaeche.verteilen("waagerecht") is False


def test_senkrecht_verteilen(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche.alles_auswaehlen()

    assert flaeche.verteilen("senkrecht") is True

    sortiert = sorted(drei, key=lambda f: f["y"])
    luecken = [
        naechste["y"] - (form["y"] + form["h"])
        for form, naechste in zip(sortiert, sortiert[1:], strict=False)
    ]
    assert max(luecken) - min(luecken) <= 1


# -- Gleiche Größe -------------------------------------------------------


def test_gleiche_breite(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche.alles_auswaehlen()
    bezug = flaeche.ausgewaehlte_form
    hoehen = [form["h"] for form in drei]

    assert flaeche.gleiche_groesse("breite") is True

    assert {form["w"] for form in drei} == {bezug["w"]}
    assert [form["h"] for form in drei] == hoehen


def test_gleiche_groesse_haelt_die_mindestgroesse_ein(
    flaeche: DiagrammCanvas, drei: list[dict]
) -> None:
    """Eine Klasse mit vielen Attributen lässt sich nicht auf die Höhe
    einer Notiz stauchen – sonst wäre der Text abgeschnitten."""
    gross = drei[0]
    gross["attributes"] = [{"name": f"wert{nummer}", "type": "int"} for nummer in range(8)]
    flaeche._auswaehlen(gross)
    flaeche.auswahl_umschalten(drei[1])
    drei[1]["h"] = 40

    flaeche.gleiche_groesse("hoehe")

    assert gross["h"] > 40


# -- Zeichenreihenfolge --------------------------------------------------


def test_in_den_vordergrund(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche._auswaehlen(drei[0])

    assert flaeche.nach_vorne() is True

    assert flaeche.formen[-1] is drei[0]


def test_in_den_hintergrund(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche._auswaehlen(drei[2])

    flaeche.nach_hinten()

    assert flaeche.formen[0] is drei[2]


def test_reihenfolge_laesst_sich_zuruecknehmen(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    vorher = list(flaeche.formen)
    flaeche._auswaehlen(drei[0])
    flaeche.nach_vorne()

    flaeche.rueckgaengig()

    assert flaeche.formen == vorher


def test_vordergrund_ohne_auswahl_tut_nichts(flaeche: DiagrammCanvas) -> None:
    assert flaeche.nach_vorne() is False


def test_oberste_form_wird_zuerst_getroffen(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    """Die Reihenfolge ist keine Kosmetik: sie entscheidet, welche Form
    ein Klick auf die Überlappung trifft."""
    drei[1]["x"], drei[1]["y"] = drei[0]["x"], drei[0]["y"]
    assert flaeche.form_bei(*_mitte(drei[0])) is drei[1]

    flaeche._auswaehlen(drei[0])
    flaeche.nach_vorne()

    assert flaeche.form_bei(*_mitte(drei[0])) is drei[0]


# -- Gruppieren ----------------------------------------------------------


def test_gruppieren_gibt_allen_dieselbe_kennung(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche.alles_auswaehlen()

    assert flaeche.gruppieren() is True

    kennungen = {form["group"] for form in drei}
    assert len(kennungen) == 1 and kennungen != {""}


def test_eine_gruppe_wird_gemeinsam_ausgewaehlt(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    """Der Sinn der Sache: eine Gruppe fasst man als Ganzes an."""
    flaeche._auswaehlen(drei[0])
    flaeche.auswahl_umschalten(drei[1])
    flaeche.gruppieren()
    flaeche.auswahl_aufheben()

    _anklicken(flaeche, drei[0])

    assert set(map(id, flaeche.auswahl)) == {id(drei[0]), id(drei[1])}


def test_die_angeklickte_form_der_gruppe_fuehrt(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche._auswaehlen(drei[0])
    flaeche.auswahl_umschalten(drei[1])
    flaeche.gruppieren()
    flaeche.auswahl_aufheben()

    _anklicken(flaeche, drei[1])

    assert flaeche.ausgewaehlte_form is drei[1]


def test_gruppierung_aufheben(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche.alles_auswaehlen()
    flaeche.gruppieren()

    assert flaeche.gruppierung_aufheben() is True

    assert {form["group"] for form in drei} == {""}


def test_zweite_gruppe_bekommt_eine_andere_kennung(
    flaeche: DiagrammCanvas, drei: list[dict]
) -> None:
    flaeche._auswaehlen(drei[0])
    flaeche.auswahl_umschalten(drei[1])
    flaeche.gruppieren()
    erste = drei[0]["group"]

    vierte = flaeche.form_platzieren("class", 700, 700)
    flaeche._auswaehlen(drei[2])
    flaeche.auswahl_umschalten(vierte)
    flaeche.gruppieren()

    assert drei[2]["group"] != erste


def test_gruppieren_braucht_zwei_formen(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche._auswaehlen(drei[0])

    assert flaeche.gruppieren() is False


# -- Zwischenablage ------------------------------------------------------


def test_kopieren_und_einfuegen(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche._auswaehlen(drei[0])

    assert flaeche.kopieren() is True
    assert flaeche.einfuegen() is True

    assert len(flaeche.formen) == 4


def test_eingefuegtes_bekommt_eine_neue_kennung(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    """Zwei Formen mit derselben `id` würden Verbindungen ins Nichts
    laufen lassen."""
    flaeche._auswaehlen(drei[0])
    flaeche.kopieren()

    flaeche.einfuegen()

    kennungen = [form["id"] for form in flaeche.formen]
    assert len(kennungen) == len(set(kennungen))


def test_eingefuegtes_liegt_versetzt(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    """Genau übereinander wäre die Kopie unsichtbar."""
    flaeche._auswaehlen(drei[0])
    flaeche.kopieren()

    flaeche.einfuegen()

    kopie = flaeche.formen[-1]
    assert (kopie["x"], kopie["y"]) != (drei[0]["x"], drei[0]["y"])


def test_eingefuegtes_ist_ausgewaehlt(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche._auswaehlen(drei[0])
    flaeche.kopieren()

    flaeche.einfuegen()

    assert flaeche.auswahl == (flaeche.formen[-1],)


def test_verbindung_kommt_mit_wenn_beide_enden_mitkommen(
    flaeche: DiagrammCanvas, drei: list[dict]
) -> None:
    flaeche.verbindung_erstellen("association", drei[0], drei[1])
    flaeche._auswaehlen(drei[0])
    flaeche.auswahl_umschalten(drei[1])
    flaeche.kopieren()

    flaeche.einfuegen()

    assert len(flaeche.verbindungen) == 2
    neu = flaeche.verbindungen[-1]
    kennungen = {form["id"] for form in flaeche.formen[-2:]}
    assert {neu["from"], neu["to"]} == kennungen


def test_verbindung_bleibt_zurueck_wenn_nur_ein_ende_mitkommt(
    flaeche: DiagrammCanvas, drei: list[dict]
) -> None:
    """Eine Verbindung ins Nichts wäre beim Einfügen wertlos."""
    flaeche.verbindung_erstellen("association", drei[0], drei[1])
    flaeche._auswaehlen(drei[0])
    flaeche.kopieren()

    flaeche.einfuegen()

    assert len(flaeche.verbindungen) == 1


def test_ausschneiden_entfernt_das_original(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche._auswaehlen(drei[0])

    assert flaeche.ausschneiden() is True

    assert len(flaeche.formen) == 2
    flaeche.einfuegen()
    assert len(flaeche.formen) == 3


def test_fremder_text_in_der_zwischenablage_wird_uebergangen(
    flaeche: DiagrammCanvas, drei: list[dict]
) -> None:
    """Wer aus einem Browser kopiert hat und dann Strg+V drückt, soll
    keinen Fehler sehen."""
    QApplication.clipboard().setText("Hallo Welt")

    assert flaeche.einfuegen() is False
    assert len(flaeche.formen) == 3


def test_kaputtes_json_wird_uebergangen(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    QApplication.clipboard().setText('{"natter_diagramm": 1, kaputt')

    assert flaeche.einfuegen() is False


def test_einfuegen_ist_ein_undo_schritt(flaeche: DiagrammCanvas, drei: list[dict]) -> None:
    flaeche.alles_auswaehlen()
    flaeche.kopieren()
    flaeche.einfuegen()

    flaeche.rueckgaengig()

    assert len(flaeche.formen) == 3


def test_kopieren_ohne_auswahl_tut_nichts(flaeche: DiagrammCanvas) -> None:
    assert flaeche.kopieren() is False


# -- Menü ----------------------------------------------------------------


def test_menue_ausrichten_hat_ein_untermenue(tmp_path: Path) -> None:
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "m.pdiag", "m"))

    assert "Anordnen/Ausrichten/links" in fenster.aktionen
    assert fenster.aktionen["Anordnen/Ausrichten/links"].isEnabled() is True


def test_menue_ausrichten_wirkt_auf_die_flaeche(tmp_path: Path) -> None:
    """Sonst hängt das Menü nur dekorativ daneben."""
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "m.pdiag", "m"))
    flaeche = fenster.zeichenflaeche
    erste = flaeche.form_platzieren("class", 100, 100)
    zweite = flaeche.form_platzieren("class", 400, 300)
    flaeche._auswaehlen(erste)
    flaeche.auswahl_umschalten(zweite)

    fenster.aktionen["Anordnen/Ausrichten/oben"].trigger()

    assert erste["y"] == zweite["y"]


def test_struktogramm_hat_kein_anordnen(tmp_path: Path) -> None:
    """Ein Struktogramm kennt keine frei beweglichen Formen – der
    Eintrag ist deshalb ausgegraut statt wirkungslos."""
    fenster = DiagrammFenster(diagramm_erzeugen("struktogramm", tmp_path / "s.pdiag", "s"))

    assert fenster.aktionen["Anordnen/Gruppieren"].isEnabled() is False
    assert fenster.aktionen["Bearbeiten/Kopieren"].isEnabled() is False


def test_statusleiste_nennt_die_anzahl(tmp_path: Path) -> None:
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "m.pdiag", "m"))
    fenster.zeichenflaeche.form_platzieren("class", 100, 100)
    fenster.zeichenflaeche.form_platzieren("class", 400, 300)

    fenster.zeichenflaeche.alles_auswaehlen()

    assert "2 Formen ausgewählt" in fenster.statusBar().currentMessage()


# -- Aus der Sichtprüfung ------------------------------------------------


def test_ansicht_folgt_dem_ausrichten(tmp_path: Path) -> None:
    """Fund aus der Sichtprüfung: richtet man an einer weit rechts
    liegenden Klasse aus, wandern alle anderen aus dem sichtbaren
    Ausschnitt heraus – die Fläche sah danach leer aus, als wären die
    Formen verschwunden."""
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "r.pdiag", "r"))
    fenster.resize(700, 500)
    fenster.show()
    flaeche = fenster.zeichenflaeche
    nah = flaeche.form_platzieren("class", 150, 150)
    weit = flaeche.form_platzieren("class", 1400, 200)
    flaeche._auswaehlen(nah)
    flaeche.auswahl_umschalten(weit)
    fenster.rollbereich.horizontalScrollBar().setValue(0)

    flaeche.ausrichten("links")

    balken = fenster.rollbereich.horizontalScrollBar()
    assert balken.value() > 0, "die Ansicht ist stehengeblieben"
    assert balken.value() <= nah["x"]


def test_eigenschaften_nennen_die_mitausgewaehlten(tmp_path: Path) -> None:
    """Zweiter Fund: die Felder zeigen immer nur die führende Form. Ohne
    Zusatz sah es so aus, als gälte „Breite" für alle drei."""
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "e.pdiag", "e"))
    flaeche = fenster.zeichenflaeche
    flaeche.form_platzieren("class", 150, 150)
    flaeche.form_platzieren("class", 450, 150)

    flaeche.alles_auswaehlen()

    assert "1 weitere ausgewählt" in fenster.eigenschaften.hinweis.text()
