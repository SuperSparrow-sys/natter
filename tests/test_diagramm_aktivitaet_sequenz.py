"""Tests für Aktivitäts- und Sequenzdiagramm (M9, „Danach“). Headless.

Das Aktivitätsdiagramm teilt sich Start, Ende und Entscheidung mit dem
Zustandsdiagramm; das Sequenzdiagramm ist der einzige Typ mit einer
eigenen Linienführung: seine Nachrichten laufen waagerecht auf einer
festen Höhe, und diese Höhe ist die Reihenfolge.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.canvas import DiagrammCanvas
from ide.diagramm.formen import formen_fuer, verbindungen_fuer, verbindungs_art
from ide.diagramm.neu import MVP_TYPEN
from ide.diagramm.stil import stil as stil_zu_namen
from ide.diagramm.zeichnen import form_zeichnen, nachrichtenhoehe, verbindungs_punkte


def _flaeche(tmp_path: Path, typ: str) -> DiagrammCanvas:
    fenster = DiagrammFenster(diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", "x"))
    return fenster.zeichenflaeche


@pytest.fixture
def aktivitaet(tmp_path: Path) -> DiagrammCanvas:
    return _flaeche(tmp_path, "activity")


@pytest.fixture
def sequenz(tmp_path: Path) -> DiagrammCanvas:
    return _flaeche(tmp_path, "sequence")


def _gemalt(shape: dict) -> set[str]:
    stil = stil_zu_namen("modern-light")
    bild = QImage(480, 460, QImage.Format.Format_RGB32)
    bild.fill(QColor(stil.hintergrund))
    maler = QPainter(bild)
    form_zeichnen(maler, shape, stil)
    maler.end()
    return {
        bild.pixelColor(x, y).name()
        for x in range(0, bild.width(), 2)
        for y in range(0, bild.height(), 2)
    }


def _maus(x: float, y: float, typ) -> QMouseEvent:
    return QMouseEvent(
        typ,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


# -- Aktivitätsdiagramm --------------------------------------------------


def test_die_palette_des_aktivitaetsdiagramms() -> None:
    kinds = [form.kind for form in formen_fuer("activity")]

    assert kinds == [
        "initial_state",
        "action",
        "decision",
        "fork",
        "object_node",
        "swimlane",
        "final_state",
        "flow_final",
        "note",
    ]


def test_start_ende_und_entscheidung_sind_dieselben_objekte() -> None:
    """Sie sehen im Zustands- und im Aktivitätsdiagramm gleich aus und
    heißen in UML auch gleich – zwei Einträge mit derselben Kennung
    würden sich gegenseitig überschreiben."""
    for kind in ("initial_state", "final_state", "decision"):
        aus_zustand = next(f for f in formen_fuer("state") if f.kind == kind)
        aus_aktivitaet = next(f for f in formen_fuer("activity") if f.kind == kind)
        assert aus_zustand is aus_aktivitaet


def test_gabelung_und_vereinigung_sind_ein_eintrag() -> None:
    """In UML dasselbe Zeichen; ob es teilt oder zusammenführt, sagen
    erst die Pfeile daran. Zwei Paletteneinträge für einen Balken wären
    eine Unterscheidung, die es beim Zeichnen nicht gibt."""
    kinds = [form.kind for form in formen_fuer("activity")]

    assert kinds.count("fork") == 1
    assert "join" not in kinds


@pytest.mark.parametrize("kind", ["action", "fork", "object_node", "swimlane", "flow_final"])
def test_jede_neue_form_malt_etwas(aktivitaet: DiagrammCanvas, kind: str) -> None:
    form = aktivitaet.form_platzieren(kind, 240, 200)
    form["x"], form["y"] = 30, 30

    assert len(_gemalt(form)) > 1, f"{kind} malt nur den Hintergrund"


def test_der_objektknoten_ist_eckig_die_aktion_rund(
    aktivitaet: DiagrammCanvas,
) -> None:
    """Genau daran unterscheidet man im Aktivitätsdiagramm ein Objekt
    von einer Aktion. Geprüft an den Ecken des gemalten Bildes."""
    stil = stil_zu_namen("modern-light")

    def ecke_gefuellt(kind: str) -> bool:
        form = {"kind": kind, "x": 40, "y": 40, "w": 200, "h": 100, "name": ""}
        bild = QImage(300, 200, QImage.Format.Format_RGB32)
        bild.fill(QColor(stil.hintergrund))
        maler = QPainter(bild)
        form_zeichnen(maler, form, stil)
        maler.end()
        return bild.pixelColor(42, 42).name() != QColor(stil.hintergrund).name()

    assert ecke_gefuellt("object_node") is True
    assert ecke_gefuellt("action") is False


def test_der_objektfluss_ist_gestrichelt() -> None:
    assert verbindungs_art("object_flow").gestrichelt is True
    assert verbindungs_art("control_flow").gestrichelt is False


def test_ein_bereich_voller_aktionen_ist_kein_layout_fehler(
    aktivitaet: DiagrammCanvas,
) -> None:
    bereich = aktivitaet.form_platzieren("swimlane", 300, 300)
    bereich["x"], bereich["y"], bereich["w"], bereich["h"] = 40, 40, 300, 400
    aktion = aktivitaet.form_platzieren("action", 200, 200)
    aktion["x"], aktion["y"], aktion["w"], aktion["h"] = 80, 120, 176, 56

    hinweise = aktivitaet.hinweise_aktualisieren()

    assert not [h for h in hinweise if h.regel == "ueberlappung"]


# -- Sequenzdiagramm -----------------------------------------------------


def test_die_palette_des_sequenzdiagramms() -> None:
    kinds = [form.kind for form in formen_fuer("sequence")]

    assert kinds == [
        "lifeline",
        "actor_lifeline",
        "activation",
        "fragment",
        "destruction",
        "note",
    ]


def test_alle_vier_nachrichten_sind_waagerecht() -> None:
    for art in verbindungen_fuer("sequence"):
        assert art.waagerecht is True, art.kind


def test_die_synchrone_nachricht_hat_eine_gefuellte_spitze() -> None:
    assert verbindungs_art("sync_message").spitze_am_ziel == "gefuellt"
    assert verbindungs_art("async_message").spitze_am_ziel == "offen"
    assert verbindungs_art("reply_message").gestrichelt is True


def test_eine_nachricht_laeuft_wirklich_waagerecht(sequenz: DiagrammCanvas) -> None:
    """Der Kern des Sequenzdiagramms: von Mitte zu Mitte zu zeigen wäre
    hier sinnlos – bei nebeneinanderstehenden Lebenslinien lägen alle
    Nachrichten übereinander auf halber Höhe, und die Reihenfolge ginge
    verloren."""
    links = sequenz.form_platzieren("lifeline", 120, 240)
    rechts = sequenz.form_platzieren("lifeline", 420, 240)
    nachricht = sequenz.verbindung_erstellen("sync_message", links, rechts)
    nachricht["y"] = 200

    punkte = verbindungs_punkte(nachricht, links, rechts)

    assert len(punkte) == 2
    assert punkte[0].y() == 200
    assert punkte[1].y() == 200
    assert punkte[0].x() < punkte[1].x()


def test_ohne_eigene_hoehe_steht_sie_unter_den_koepfen(
    sequenz: DiagrammCanvas,
) -> None:
    """Sonst läge die erste Nachricht mitten im Namen der
    Lebenslinie."""
    links = sequenz.form_platzieren("lifeline", 120, 240)
    rechts = sequenz.form_platzieren("lifeline", 420, 240)
    nachricht = sequenz.verbindung_erstellen("sync_message", links, rechts)

    hoehe = nachrichtenhoehe(nachricht, links, rechts)

    assert hoehe > max(links["y"], rechts["y"])
    assert hoehe < max(links["y"], rechts["y"]) + 100


def test_die_reihenfolge_ergibt_sich_aus_der_hoehe(sequenz: DiagrammCanvas) -> None:
    links = sequenz.form_platzieren("lifeline", 120, 240)
    rechts = sequenz.form_platzieren("lifeline", 420, 240)
    erste = sequenz.verbindung_erstellen("sync_message", links, rechts)
    zweite = sequenz.verbindung_erstellen("reply_message", rechts, links)
    erste["y"], zweite["y"] = 160, 240

    hoehen = [
        verbindungs_punkte(erste, links, rechts)[0].y(),
        verbindungs_punkte(zweite, rechts, links)[0].y(),
    ]

    assert hoehen == sorted(hoehen)


def test_eine_nachricht_laesst_sich_nach_unten_ziehen(
    sequenz: DiagrammCanvas,
) -> None:
    """Die Höhe über ein Zahlenfeld einzustellen wäre mühsam – man zieht
    sie wie alles andere auch."""
    links = sequenz.form_platzieren("lifeline", 120, 240)
    rechts = sequenz.form_platzieren("lifeline", 420, 240)
    nachricht = sequenz.verbindung_erstellen("sync_message", links, rechts)
    nachricht["y"] = 160
    mitte_x = (links["x"] + links["w"] + rechts["x"]) / 2

    sequenz.mousePressEvent(_maus(mitte_x, 160, QEvent.Type.MouseButtonPress))
    sequenz.mouseMoveEvent(_maus(mitte_x, 240, QEvent.Type.MouseMove))
    sequenz.mouseReleaseEvent(_maus(mitte_x, 240, QEvent.Type.MouseButtonRelease))

    assert nachricht["y"] == 240


def test_das_ziehen_ist_ein_undo_schritt(sequenz: DiagrammCanvas) -> None:
    links = sequenz.form_platzieren("lifeline", 120, 240)
    rechts = sequenz.form_platzieren("lifeline", 420, 240)
    nachricht = sequenz.verbindung_erstellen("sync_message", links, rechts)
    nachricht["y"] = 160
    mitte_x = (links["x"] + links["w"] + rechts["x"]) / 2
    sequenz.mousePressEvent(_maus(mitte_x, 160, QEvent.Type.MouseButtonPress))
    sequenz.mouseMoveEvent(_maus(mitte_x, 200, QEvent.Type.MouseMove))
    sequenz.mouseMoveEvent(_maus(mitte_x, 264, QEvent.Type.MouseMove))
    sequenz.mouseReleaseEvent(_maus(mitte_x, 264, QEvent.Type.MouseButtonRelease))

    sequenz.rueckgaengig()

    assert nachricht["y"] == 160


def test_eine_gewoehnliche_verbindung_laesst_sich_nicht_so_ziehen(
    tmp_path: Path,
) -> None:
    """Gegenprobe: im Klassendiagramm gibt es keine Nachrichtenhöhe."""
    flaeche = _flaeche(tmp_path, "class")
    erste = flaeche.form_platzieren("class", 120, 200)
    zweite = flaeche.form_platzieren("class", 480, 200)
    verbindung = flaeche.verbindung_erstellen("association", erste, zweite)
    mitte_x = (erste["x"] + erste["w"] + zweite["x"]) / 2

    flaeche.mousePressEvent(
        _maus(mitte_x, erste["y"] + erste["h"] / 2, QEvent.Type.MouseButtonPress)
    )

    assert flaeche._zieh_nachricht is None
    assert "y" not in verbindung


@pytest.mark.parametrize("kind", ["lifeline", "activation", "fragment", "destruction"])
def test_jede_sequenzform_malt_etwas(sequenz: DiagrammCanvas, kind: str) -> None:
    form = sequenz.form_platzieren(kind, 200, 200)
    form["x"], form["y"] = 30, 30

    assert len(_gemalt(form)) > 1, f"{kind} malt nur den Hintergrund"


def test_die_lebenslinie_reicht_bis_zum_unteren_rand(sequenz: DiagrammCanvas) -> None:
    """Die ganze Höhe der Form ist die Lebenslinie, nicht nur der Kopf:
    so lang, wie die Form ist, lebt das Objekt."""
    stil = stil_zu_namen("modern-light")
    linie = sequenz.form_platzieren("lifeline", 200, 220)
    linie["x"], linie["y"], linie["w"], linie["h"] = 40, 20, 160, 380

    bild = QImage(480, 460, QImage.Format.Format_RGB32)
    bild.fill(QColor(stil.hintergrund))
    maler = QPainter(bild)
    form_zeichnen(maler, linie, stil)
    maler.end()

    mitte = int(linie["x"] + linie["w"] / 2)
    unten = int(linie["y"] + linie["h"]) - 6
    spalte = [bild.pixelColor(mitte, y).name() for y in range(unten - 40, unten)]
    assert any(farbe != QColor(stil.hintergrund).name() for farbe in spalte)


# -- Beide ---------------------------------------------------------------


@pytest.mark.parametrize("typ", ["activity", "sequence"])
def test_die_typen_lassen_sich_neu_anlegen(typ: str) -> None:
    assert typ in MVP_TYPEN


@pytest.mark.parametrize("typ", ["activity", "sequence"])
def test_speichern_und_laden(tmp_path: Path, typ: str) -> None:
    from ide.diagramm.datei import Diagramm

    pfad = tmp_path / f"{typ}.pdiag"
    fenster = DiagrammFenster(diagramm_erzeugen(typ, pfad, typ))
    flaeche = fenster.zeichenflaeche
    formen = [form.kind for form in formen_fuer(typ)]
    erste = flaeche.form_platzieren(formen[0], 120, 120)
    zweite = flaeche.form_platzieren(formen[1], 400, 120)
    art = verbindungen_fuer(typ)[0].kind
    flaeche.verbindung_erstellen(art, erste, zweite)
    fenster.speichern()

    geladen = Diagramm.laden(pfad)

    assert geladen.typ == typ
    assert len(geladen.daten["shapes"]) == 2
    assert geladen.daten["connectors"][0]["kind"] == art


# -- Aus der Sichtprüfung ------------------------------------------------


def test_der_akteur_bekommt_im_sequenzdiagramm_eine_lebenslinie(
    sequenz: DiagrammCanvas,
) -> None:
    """Fund aus der Sichtprüfung: der Akteur stand als Strichmännchen
    ohne Lebenslinie da, und die Nachrichten an ihn endeten im Leeren.
    Bleibt unter dem Namen Platz übrig, ist er eine Lebenslinie."""
    stil = stil_zu_namen("modern-light")
    akteur = sequenz.form_platzieren("actor_lifeline", 200, 200)
    akteur["x"], akteur["y"], akteur["w"], akteur["h"] = 40, 20, 100, 400
    akteur["name"] = "Leserin"

    bild = QImage(300, 460, QImage.Format.Format_RGB32)
    bild.fill(QColor(stil.hintergrund))
    maler = QPainter(bild)
    form_zeichnen(maler, akteur, stil)
    maler.end()

    mitte = int(akteur["x"] + akteur["w"] / 2)
    unten = int(akteur["y"] + akteur["h"]) - 8
    spalte = [bild.pixelColor(mitte, y).name() for y in range(unten - 60, unten)]
    assert any(farbe != QColor(stil.hintergrund).name() for farbe in spalte), (
        "unter dem Namen ist keine Lebenslinie"
    )


def test_im_use_case_diagramm_bekommt_er_keine(tmp_path: Path) -> None:
    """Gegenprobe: dort ist er nur so hoch wie Männchen und Name."""
    stil = stil_zu_namen("modern-light")
    flaeche = _flaeche(tmp_path, "use_case")
    akteur = flaeche.form_platzieren("actor", 200, 200)
    akteur["x"], akteur["y"] = 40, 20
    akteur["name"] = "Leserin"

    bild = QImage(300, int(akteur["y"] + akteur["h"]) + 20, QImage.Format.Format_RGB32)
    bild.fill(QColor(stil.hintergrund))
    maler = QPainter(bild)
    form_zeichnen(maler, akteur, stil)
    maler.end()

    # Unterhalb des Namens ist bei der Standardhöhe kein Platz mehr -
    # dort darf keine Linie stehen.
    mitte = int(akteur["x"] + akteur["w"] / 2)
    unten = int(akteur["y"] + akteur["h"])
    spalte = [bild.pixelColor(mitte, y).name() for y in range(unten - 2, unten + 8)]
    assert set(spalte) == {QColor(stil.hintergrund).name()}


def test_zwei_formen_duerfen_nicht_dieselbe_kennung_tragen() -> None:
    """Der Wächter zu dem Fund oben: der Akteur des Sequenzdiagramms
    (80×400, mit Lebenslinie) überschrieb stillschweigend den des
    Use-Case-Diagramms (80×104), und dort stand plötzlich ein 400 Pixel
    hoher Akteur mit Lebenslinie."""
    from ide.diagramm.formen import FormArt, _nach_kind

    eine = FormArt("gleich", "A", "", 10, 10, "")
    andere = FormArt("gleich", "B", "", 99, 99, "")

    with pytest.raises(ValueError, match="gleich"):
        _nach_kind({"x": (eine,), "y": (andere,)}, "Formen")


def test_dasselbe_objekt_in_zwei_paletten_ist_erlaubt() -> None:
    """Gegenprobe: `NOTIZ` steht in vier Paletten und ist überall
    dieselbe Form."""
    from ide.diagramm.formen import NOTIZ, _nach_kind

    assert _nach_kind({"x": (NOTIZ,), "y": (NOTIZ,)}, "Formen")["note"] is NOTIZ
