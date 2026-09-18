"""Tests für das Verschieben von Struktogramm-Blöcken mit der Maus und
für die Kopfzeile mit dem Namen (M9, Schritt 9 – Rest). Headless.

Der Baum konnte Umhängen schon lange (`entfernen` + `einfuegen`); was
fehlte, war das Ziehen mit der Maus und die Frage, welche Ziele dabei
überhaupt erlaubt sind.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.bloecke import Einfuegestelle, stelle_von
from ide.diagramm.stil import stil as stil_zu_namen
from ide.diagramm.struktogramm import KOPFHOEHE, struktogramm_zeichnen
from ide.diagramm.struktogramm_canvas import VERSATZ, StruktogrammCanvas


@pytest.fixture
def flaeche(tmp_path: Path) -> StruktogrammCanvas:
    fenster = DiagrammFenster(diagramm_erzeugen("struktogramm", tmp_path / "s.pdiag", "zaehlen"))
    return fenster.zeichenflaeche


def _wurzelstelle(flaeche: StruktogrammCanvas) -> Einfuegestelle:
    return Einfuegestelle(flaeche.wurzel, "children", len(flaeche.wurzel["children"]))


@pytest.fixture
def drei(flaeche: StruktogrammCanvas) -> list[dict]:
    """Drei Anweisungen untereinander – das einfachste Struktogramm, in
    dem sich eine Reihenfolge überhaupt ändern lässt."""
    bloecke = []
    for text in ("erstens", "zweitens", "drittens"):
        block = flaeche.block_einfuegen("statement", _wurzelstelle(flaeche))
        block["text"] = text
        bloecke.append(block)
    flaeche._nach_aenderung()
    return bloecke


def _maus(x: float, y: float, typ, strg: bool = False) -> QMouseEvent:
    return QMouseEvent(
        typ,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.ControlModifier if strg else Qt.KeyboardModifier.NoModifier,
    )


def _mitte(flaeche: StruktogrammCanvas, block: dict) -> tuple[float, float]:
    kasten = next(k for k in flaeche._layout.alle() if k.block is block)
    mitte = kasten.rechteck.center()
    return mitte.x() + VERSATZ, mitte.y() + VERSATZ


def _texte(flaeche: StruktogrammCanvas) -> list[str]:
    return [block.get("text", "") for block in flaeche.wurzel["children"]]


# -- Ziehen --------------------------------------------------------------


def test_ziehen_aendert_die_reihenfolge(flaeche: StruktogrammCanvas, drei: list[dict]) -> None:
    von_x, von_y = _mitte(flaeche, drei[2])
    nach_x, nach_y = _mitte(flaeche, drei[0])

    flaeche.mousePressEvent(_maus(von_x, von_y, QEvent.Type.MouseButtonPress))
    flaeche.mouseMoveEvent(_maus(nach_x, nach_y - 20, QEvent.Type.MouseMove))
    flaeche.mouseReleaseEvent(_maus(nach_x, nach_y - 20, QEvent.Type.MouseButtonRelease))

    assert _texte(flaeche) == ["drittens", "erstens", "zweitens"]


def test_ein_klick_ohne_bewegung_verschiebt_nichts(
    flaeche: StruktogrammCanvas, drei: list[dict]
) -> None:
    """Sonst würde jeder Klick, bei dem die Hand ein wenig zittert,
    schon etwas umhängen."""
    x, y = _mitte(flaeche, drei[0])

    flaeche.mousePressEvent(_maus(x, y, QEvent.Type.MouseButtonPress))
    flaeche.mouseMoveEvent(_maus(x + 2, y + 2, QEvent.Type.MouseMove))
    flaeche.mouseReleaseEvent(_maus(x + 2, y + 2, QEvent.Type.MouseButtonRelease))

    assert _texte(flaeche) == ["erstens", "zweitens", "drittens"]
    assert flaeche.ausgewaehlter_block is drei[0]


def test_verschieben_ist_ein_undo_schritt(flaeche: StruktogrammCanvas, drei: list[dict]) -> None:
    """Herausnehmen und Einsetzen sind für die Bedienerin **eine**
    Handlung."""
    ziel = Einfuegestelle(flaeche.wurzel, "children", 0)

    flaeche.block_verschieben(drei[2], ziel)
    flaeche.rueckgaengig()

    assert _texte(flaeche) == ["erstens", "zweitens", "drittens"]


def test_der_verschobene_block_bleibt_ausgewaehlt(
    flaeche: StruktogrammCanvas, drei: list[dict]
) -> None:
    flaeche.block_verschieben(drei[2], Einfuegestelle(flaeche.wurzel, "children", 0))

    assert flaeche.ausgewaehlter_block is drei[2]


# -- Was nicht erlaubt ist -----------------------------------------------


def test_ein_block_kann_nicht_in_sich_selbst(flaeche: StruktogrammCanvas) -> None:
    """Das ergäbe einen Kreis, und der Baum hätte kein Ende mehr."""
    schleife = flaeche.block_einfuegen("head_loop", _wurzelstelle(flaeche))

    ziel = Einfuegestelle(schleife, "children", 0)

    assert flaeche.verschieben_moeglich(schleife, ziel) is None
    assert flaeche.block_verschieben(schleife, ziel) is False


def test_ein_block_kann_nicht_in_seinen_eigenen_zweig(
    flaeche: StruktogrammCanvas,
) -> None:
    schleife = flaeche.block_einfuegen("head_loop", _wurzelstelle(flaeche))
    innen = flaeche.block_einfuegen("branch", Einfuegestelle(schleife, "children", 0))

    ziel = Einfuegestelle(innen, "then", 0)

    assert flaeche.verschieben_moeglich(schleife, ziel) is None


def test_dieselbe_stelle_ist_kein_schritt(flaeche: StruktogrammCanvas, drei: list[dict]) -> None:
    """Sonst stünde im Rückgängig-Stapel ein Schritt, der nichts tut."""
    hier = stelle_von(flaeche.diagramm.daten, drei[1])

    assert flaeche.verschieben_moeglich(drei[1], hier) is None


def test_die_luecke_dahinter_ist_auch_dieselbe_stelle(
    flaeche: StruktogrammCanvas, drei: list[dict]
) -> None:
    """Der Knackpunkt beim Umrechnen: die Zielnummer zählt den Block
    noch mit, der gerade herausgenommen wird."""
    dahinter = Einfuegestelle(flaeche.wurzel, "children", 2)

    assert flaeche.verschieben_moeglich(drei[1], dahinter) is None


def test_ziel_hinter_dem_block_rutscht_eine_stelle_vor(
    flaeche: StruktogrammCanvas, drei: list[dict]
) -> None:
    """Ohne diese Umrechnung landete der erste Block beim Ziehen ans
    Ende eine Stelle zu weit vorn."""
    ans_ende = Einfuegestelle(flaeche.wurzel, "children", 3)

    flaeche.block_verschieben(drei[0], ans_ende)

    assert _texte(flaeche) == ["zweitens", "drittens", "erstens"]


def test_ohne_ziel_passiert_nichts(flaeche: StruktogrammCanvas, drei: list[dict]) -> None:
    assert flaeche.block_verschieben(drei[0], None) is False


# -- Kopieren ------------------------------------------------------------


def test_strg_beim_ziehen_kopiert(flaeche: StruktogrammCanvas, drei: list[dict]) -> None:
    von_x, von_y = _mitte(flaeche, drei[0])
    nach_x, nach_y = _mitte(flaeche, drei[2])

    flaeche.mousePressEvent(_maus(von_x, von_y, QEvent.Type.MouseButtonPress, strg=True))
    flaeche.mouseMoveEvent(_maus(nach_x, nach_y, QEvent.Type.MouseMove, strg=True))
    flaeche.mouseReleaseEvent(_maus(nach_x, nach_y, QEvent.Type.MouseButtonRelease, strg=True))

    assert len(flaeche.wurzel["children"]) == 4
    assert _texte(flaeche).count("erstens") == 2


def test_die_kopie_bekommt_neue_kennungen(flaeche: StruktogrammCanvas, drei: list[dict]) -> None:
    """Zwei Blöcke mit derselben `id` würden die Auswahl
    durcheinanderbringen."""
    schleife = flaeche.block_einfuegen("head_loop", _wurzelstelle(flaeche))
    flaeche.block_einfuegen("statement", Einfuegestelle(schleife, "children", 0))

    kopie = flaeche.block_kopieren(schleife, Einfuegestelle(flaeche.wurzel, "children", 0))

    from ide.diagramm.bloecke import alle_bloecke

    kennungen = [block["id"] for block in alle_bloecke(flaeche.diagramm.daten)]
    assert len(kennungen) == len(set(kennungen))
    assert kopie["id"] != schleife["id"]


def test_kopieren_laesst_sich_zuruecknehmen(flaeche: StruktogrammCanvas, drei: list[dict]) -> None:
    flaeche.block_kopieren(drei[0], Einfuegestelle(flaeche.wurzel, "children", 3))

    flaeche.rueckgaengig()

    assert len(flaeche.wurzel["children"]) == 3


# -- Kopfzeile -----------------------------------------------------------


def test_das_layout_beginnt_unter_der_kopfzeile(
    flaeche: StruktogrammCanvas, drei: list[dict]
) -> None:
    """Zeichnen und Trefferprüfung rechnen über dasselbe Layout – der
    Versatz steckt deshalb im Layout und nicht im Zeichencode."""
    assert flaeche._layout.rechteck.top() == KOPFHOEHE


def test_ohne_namen_keine_kopfzeile(tmp_path: Path) -> None:
    fenster = DiagrammFenster(diagramm_erzeugen("struktogramm", tmp_path / "leer.pdiag", "x"))
    flaeche = fenster.zeichenflaeche
    flaeche.diagramm.daten["name"] = ""
    flaeche._layout_erneuern()

    assert flaeche._layout.rechteck.top() == 0


def test_der_name_wird_wirklich_gemalt(flaeche: StruktogrammCanvas) -> None:
    """Nicht „der Text steht im Datenmodell", sondern: auf dem Bild sind
    an der Stelle wirklich Pixel in der Textfarbe."""
    stil = stil_zu_namen(flaeche.diagramm.stil)
    bild = QImage(640, 400, QImage.Format.Format_RGB32)
    bild.fill(QColor(stil.hintergrund))
    maler = QPainter(bild)
    struktogramm_zeichnen(maler, flaeche.diagramm.daten, stil)
    maler.end()

    textfarbe = QColor(stil.text).name()
    in_der_kopfzeile = sum(
        bild.pixelColor(x, y).name() == textfarbe for x in range(640) for y in range(int(KOPFHOEHE))
    )
    assert in_der_kopfzeile > 20, "in der Kopfzeile steht kein Text"


def test_die_kopfzeile_verschluckt_den_text_nicht(flaeche: StruktogrammCanvas) -> None:
    """Derselbe Fehler war in der Entscheidungstabelle schon einmal im
    PDF aufgefallen: mit `stil.trennlinie` hinterlegt ist die Kopfzeile
    in der Schwarz-Weiß-Vorlage schwarz und schluckt den schwarzen Text
    vollständig."""
    stil = stil_zu_namen("black-white")
    bild = QImage(640, 400, QImage.Format.Format_RGB32)
    bild.fill(QColor(stil.hintergrund))
    maler = QPainter(bild)
    struktogramm_zeichnen(maler, flaeche.diagramm.daten, stil)
    maler.end()

    farben = {bild.pixelColor(x, y).name() for x in range(640) for y in range(int(KOPFHOEHE))}
    assert len(farben) > 2, "die Kopfzeile ist einfarbig – der Text fehlt"


def test_loslassen_auf_der_oberen_haelfte_setzt_davor(
    flaeche: StruktogrammCanvas, drei: list[dict]
) -> None:
    """`stelle_bei()` trifft nur die schmalen Fugen – beim Ziehen lässt
    man den Block aber über einem anderen los, nicht in der Fuge."""
    kasten = next(k for k in flaeche._layout.alle() if k.block is drei[1])
    oben = kasten.rechteck.top() + kasten.rechteck.height() * 0.25 + VERSATZ

    ziel = flaeche.zielstelle_beim_ziehen(304, oben)

    assert ziel is not None
    assert ziel.index == 1


def test_loslassen_auf_der_unteren_haelfte_setzt_dahinter(
    flaeche: StruktogrammCanvas, drei: list[dict]
) -> None:
    kasten = next(k for k in flaeche._layout.alle() if k.block is drei[1])
    unten = kasten.rechteck.top() + kasten.rechteck.height() * 0.75 + VERSATZ

    ziel = flaeche.zielstelle_beim_ziehen(304, unten)

    assert ziel is not None
    assert ziel.index == 2


def test_ziehen_auf_einen_block_verschiebt_wirklich(
    flaeche: StruktogrammCanvas, drei: list[dict]
) -> None:
    """Gegenprobe zum Ganzen: der Zug von der dritten auf die erste
    Anweisung muss die Reihenfolge ändern, nicht nur eine Marke
    aufleuchten lassen."""
    von_x, von_y = _mitte(flaeche, drei[2])
    kasten = next(k for k in flaeche._layout.alle() if k.block is drei[0])
    # Obere Hälfte der ersten Anweisung, also „davor“
    nach_x = kasten.rechteck.center().x() + VERSATZ
    nach_y = kasten.rechteck.top() + kasten.rechteck.height() * 0.25 + VERSATZ

    flaeche.mousePressEvent(_maus(von_x, von_y, QEvent.Type.MouseButtonPress))
    flaeche.mouseMoveEvent(_maus(nach_x, nach_y, QEvent.Type.MouseMove))
    flaeche.mouseReleaseEvent(_maus(nach_x, nach_y, QEvent.Type.MouseButtonRelease))

    assert _texte(flaeche)[0] == "drittens"


def test_ein_unbekannter_schluessel_ist_ein_fehler(flaeche: StruktogrammCanvas) -> None:
    """Beim Bauen der Sichtprüfung selbst hineingelaufen: `"otherwise"`
    statt `"else"` legte stillschweigend ein Feld an, das keine
    Darstellung kennt. Der eingefügte Block war danach unsichtbar, stand
    aber in der Datei – und die Schema-Prüfung schlug beim nächsten
    Öffnen zu."""
    verzweigung = flaeche.block_einfuegen("branch", _wurzelstelle(flaeche))

    with pytest.raises(ValueError, match="otherwise"):
        Einfuegestelle(verzweigung, "otherwise", 0).liste()

    assert "otherwise" not in verzweigung
