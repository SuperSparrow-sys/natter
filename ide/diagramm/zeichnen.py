"""Zeichnen der Diagrammformen (Abschnitt 13.6).

Getrennt von `canvas.py` (Bedienung) und `formen.py` (Katalog), damit
derselbe Code die Zeichenfläche **und** den späteren Export
(PNG/SVG/PDF, Schritt 8) malt – der Export darf keine zweite,
abweichende Darstellung erzeugen.

Gestaltung nach Abschnitt 13.6: 1,5-px-Linien mit Kantenglättung,
eckige UML-Klassen ohne Schatten/Verläufe, Segoe UI für Namen und
Cascadia Code für Attribute/Methoden, Klassennamen fett, abstrakte
kursiv.
"""

from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen

from ide.diagramm.stil import Stil

LINIENBREITE = 1.5
INNENABSTAND = 8
#: Höhe des Namensbereichs einer Klasse bzw. einer Notiz/eines Pakets.
KOPFHOEHE = 28
#: Größe der umgeknickten Ecke einer Notiz bzw. des Paket-Reiters.
ECKE = 16

_NAMENSSCHRIFT = "Segoe UI"
_MONOSCHRIFT = "Consolas"


def fuellfarbe(shape: dict[str, Any], stil: Stil) -> str:
    """Eigene Farbe der Form, sonst die der Stilvorlage (Abschnitt 13.2:
    „Füllung, Linie, Schrift“ im Eigenschaften-Bereich)."""
    return str(shape.get("fill") or stil.fuellung)


def randfarbe(shape: dict[str, Any], stil: Stil) -> str:
    return str(shape.get("line") or stil.rand)


def schriftgroesse(shape: dict[str, Any]) -> float:
    return float(shape.get("font_size") or 10)


def _namensschrift(fett: bool = True, kursiv: bool = False, groesse: float = 10) -> QFont:
    schrift = QFont(_NAMENSSCHRIFT, round(groesse))
    schrift.setBold(fett)
    schrift.setItalic(kursiv)
    return schrift


def _mono_schrift(groesse: float = 9) -> QFont:
    schrift = QFont(_MONOSCHRIFT, round(groesse))
    schrift.setFixedPitch(True)
    return schrift


def _stift(stil: Stil, farbe: str | None = None) -> QPen:
    stift = QPen(QColor(farbe or stil.rand))
    stift.setWidthF(LINIENBREITE)
    stift.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    return stift


def form_rechteck(shape: dict[str, Any]) -> QRectF:
    return QRectF(shape["x"], shape["y"], shape["w"], shape["h"])


def mindesthoehe(shape: dict[str, Any]) -> float:
    """Höhe, ab der der Inhalt vollständig hineinpasst (Abschnitt 13.6:
    „automatische Mindestgröße, damit Text nie abgeschnitten wird“).
    Wird beim Platzieren und beim Ändern des Textes angewandt.

    Attribut- und Methodenbereich zählen **getrennt**: beide werden
    immer mindestens eine Zeile hoch gezeichnet, damit leere Bereiche
    nicht zu Strichen zusammenfallen. Eine gemeinsame Summe hatte real
    dazu geführt, dass bei einem Interface mit zwei Methoden und ohne
    Attribute die letzte Methode abgeschnitten wurde (im Screenshot
    aufgefallen)."""
    kind = shape.get("kind", "class")
    if kind == "note":
        # Eine Notiz bricht ihren Text um (siehe `_notiz_zeichnen`),
        # braucht dafür aber Höhe – sonst verschwinden die unteren
        # Zeilen hinter dem Rand.
        return _umbruchhoehe(shape) + 2 * INNENABSTAND
    if kind not in ("class", "abstract_class", "interface"):
        return KOPFHOEHE + 2 * INNENABSTAND

    text = shape.get("text") or {}
    attribute = max(1, len(text.get("attributes") or []))
    methoden = max(1, len(text.get("methods") or []))
    zeilenhoehe = QFontMetricsF(_mono_schrift()).height()
    kopf = KOPFHOEHE * (2 if kind == "interface" else 1)
    return kopf + (attribute + methoden) * zeilenhoehe + 2 * INNENABSTAND


def _umbruchhoehe(shape: dict[str, Any]) -> float:
    """Höhe, die der umbrochene Text einer Notiz in der aktuellen Breite
    einnimmt."""
    innen = max(1.0, float(shape.get("w", 0)) - 2 * INNENABSTAND - ECKE)
    metriken = QFontMetricsF(_namensschrift(fett=False, groesse=schriftgroesse(shape)))
    return metriken.boundingRect(
        QRectF(0, 0, innen, 10_000),
        int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
        str((shape.get("text") or {}).get("name", "")),
    ).height()


def mindestbreite(shape: dict[str, Any]) -> float:
    """Breite, ab der keine Textzeile seitlich abgeschnitten wird.
    Anders als `mindesthoehe` wird sie **nicht** automatisch erzwungen –
    eine zu schmale Form ist erlaubt und wird nur als Layout-Hinweis
    gemeldet (Schritt 7), weil sonst jede Eingabe eines langen
    Methodennamens die Form ruckartig breiter zöge.

    Notizen und Pakete brechen ihren Text um und haben deshalb keine
    Mindestbreite – sie wurden sonst reihenweise fälschlich als „zu
    schmal“ gemeldet (im Screenshot-Durchgang aufgefallen); bei ihnen
    zählt nur die Höhe."""
    if shape.get("kind") in ("note", "package"):
        return 0.0

    text = shape.get("text") or {}
    groesse = schriftgroesse(shape)
    name_breite = QFontMetricsF(_namensschrift(groesse=groesse)).horizontalAdvance(
        str(text.get("name", ""))
    )
    mono = QFontMetricsF(_mono_schrift(groesse - 1))
    zeilen = [*(text.get("attributes") or []), *(text.get("methods") or [])]
    zeilen_breite = max((mono.horizontalAdvance(str(z)) for z in zeilen), default=0.0)
    return max(name_breite, zeilen_breite) + 2 * INNENABSTAND


def klassen_bereiche(shape: dict[str, Any]) -> dict[str, QRectF]:
    """Die drei Bereiche einer Klasse (Name, Attribute, Methoden) als
    Rechtecke. Wird sowohl beim Zeichnen als auch beim Bearbeiten
    benutzt, damit die Eingabefelder exakt dort liegen, wo der Text
    steht (Abschnitt 13.3: „bearbeitet direkt in der Form“)."""
    rechteck = form_rechteck(shape)
    kind = shape.get("kind", "class")
    if kind not in ("class", "abstract_class", "interface"):
        return {"name": rechteck}

    text = shape.get("text") or {}
    zeilenhoehe = QFontMetricsF(_mono_schrift()).height()
    kopf_unten = rechteck.top() + KOPFHOEHE * (2 if kind == "interface" else 1)
    attribute = max(1, len(text.get("attributes") or []))
    attribut_unten = kopf_unten + attribute * zeilenhoehe + INNENABSTAND

    return {
        "name": QRectF(
            rechteck.left(), kopf_unten - KOPFHOEHE, rechteck.width(), KOPFHOEHE
        ),
        "attributes": QRectF(
            rechteck.left(), kopf_unten, rechteck.width(), attribut_unten - kopf_unten
        ),
        "methods": QRectF(
            rechteck.left(),
            attribut_unten,
            rechteck.width(),
            max(zeilenhoehe, rechteck.bottom() - attribut_unten),
        ),
    }


def form_zeichnen(
    maler: QPainter, shape: dict[str, Any], stil: Stil, ausgewaehlt: bool = False
) -> None:
    """Malt `shape` in seiner UML-Darstellung. `ausgewaehlt` zeichnet
    zusätzlich den Auswahlrahmen in der Akzentfarbe (Abschnitt 13.6)."""
    maler.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    maler.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

    kind = shape.get("kind", "class")
    if kind in ("class", "abstract_class", "interface"):
        _klasse_zeichnen(maler, shape, stil, kind)
    elif kind == "note":
        _notiz_zeichnen(maler, shape, stil)
    elif kind == "package":
        _paket_zeichnen(maler, shape, stil)
    else:
        # Unbekannte Form nicht verschlucken, sondern sichtbar als
        # schlichtes Rechteck malen - sonst „verschwindet“ sie
        # kommentarlos aus einer von Hand bearbeiteten .pdiag.
        maler.setPen(_stift(stil))
        maler.setBrush(QBrush(QColor(stil.fuellung)))
        maler.drawRect(form_rechteck(shape))

    if ausgewaehlt:
        _auswahl_zeichnen(maler, shape, stil)


def _klasse_zeichnen(maler: QPainter, shape: dict, stil: Stil, kind: str) -> None:
    rechteck = form_rechteck(shape)
    gross = schriftgroesse(shape)
    maler.setPen(_stift(stil, randfarbe(shape, stil)))
    maler.setBrush(QBrush(QColor(fuellfarbe(shape, stil))))
    maler.drawRect(rechteck)

    text = shape.get("text") or {}
    abstrakt = kind == "abstract_class" or bool(shape.get("abstract"))
    maler.setPen(QColor(stil.text))

    kopf_unten = rechteck.top() + KOPFHOEHE
    if kind == "interface":
        maler.setFont(_namensschrift(fett=False, groesse=gross))
        maler.drawText(
            QRectF(rechteck.left(), rechteck.top() + 4, rechteck.width(), KOPFHOEHE - 6),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "«interface»",
        )
        kopf_unten = rechteck.top() + 2 * KOPFHOEHE

    name = str(text.get("name", ""))
    maler.setFont(_namensschrift(fett=True, kursiv=abstrakt, groesse=gross))
    namensbereich = QRectF(
        rechteck.left(),
        kopf_unten - KOPFHOEHE,
        rechteck.width(),
        KOPFHOEHE,
    )
    maler.drawText(
        namensbereich,
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        name + ("  {abstract}" if abstrakt else ""),
    )

    maler.setPen(_stift(stil, stil.trennlinie))
    maler.drawLine(rechteck.left(), kopf_unten, rechteck.right(), kopf_unten)

    zeilenhoehe = QFontMetricsF(_mono_schrift()).height()
    attribute = [str(zeile) for zeile in (text.get("attributes") or [])]
    methoden = [str(zeile) for zeile in (text.get("methods") or [])]

    attribut_unten = klassen_bereiche(shape)["methods"].top()
    _zeilen_zeichnen(maler, rechteck, kopf_unten, attribute, stil, zeilenhoehe)

    maler.setPen(_stift(stil, stil.trennlinie))
    maler.drawLine(rechteck.left(), attribut_unten, rechteck.right(), attribut_unten)
    _zeilen_zeichnen(maler, rechteck, attribut_unten, methoden, stil, zeilenhoehe)


def _zeilen_zeichnen(
    maler: QPainter,
    rechteck: QRectF,
    oben: float,
    zeilen: list[str],
    stil: Stil,
    zeilenhoehe: float,
) -> None:
    maler.setFont(_mono_schrift())
    maler.setPen(QColor(stil.text))
    for nummer, zeile in enumerate(zeilen):
        y = oben + INNENABSTAND / 2 + nummer * zeilenhoehe
        if y + zeilenhoehe > rechteck.bottom():
            break  # unterhalb der Form nicht weiterzeichnen
        maler.drawText(
            QRectF(rechteck.left() + INNENABSTAND, y, rechteck.width() - 2 * INNENABSTAND,
                   zeilenhoehe),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            zeile,
        )


def _notiz_zeichnen(maler: QPainter, shape: dict, stil: Stil) -> None:
    rechteck = form_rechteck(shape)
    pfad = QPainterPath()
    pfad.moveTo(rechteck.left(), rechteck.top())
    pfad.lineTo(rechteck.right() - ECKE, rechteck.top())
    pfad.lineTo(rechteck.right(), rechteck.top() + ECKE)
    pfad.lineTo(rechteck.right(), rechteck.bottom())
    pfad.lineTo(rechteck.left(), rechteck.bottom())
    pfad.closeSubpath()

    maler.setPen(_stift(stil, randfarbe(shape, stil)))
    maler.setBrush(QBrush(QColor(fuellfarbe(shape, stil))))
    maler.drawPath(pfad)
    # umgeknickte Ecke
    maler.drawLine(rechteck.right() - ECKE, rechteck.top(),
                   rechteck.right() - ECKE, rechteck.top() + ECKE)
    maler.drawLine(rechteck.right() - ECKE, rechteck.top() + ECKE,
                   rechteck.right(), rechteck.top() + ECKE)

    maler.setPen(QColor(stil.text))
    maler.setFont(_namensschrift(fett=False, groesse=schriftgroesse(shape)))
    maler.drawText(
        rechteck.adjusted(INNENABSTAND, INNENABSTAND, -INNENABSTAND, -INNENABSTAND),
        int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
        str((shape.get("text") or {}).get("name", "")),
    )


def _paket_zeichnen(maler: QPainter, shape: dict, stil: Stil) -> None:
    rechteck = form_rechteck(shape)
    reiter = QRectF(rechteck.left(), rechteck.top(), rechteck.width() / 2.5, ECKE)
    koerper = QRectF(
        rechteck.left(), rechteck.top() + ECKE, rechteck.width(), rechteck.height() - ECKE
    )

    maler.setPen(_stift(stil, randfarbe(shape, stil)))
    maler.setBrush(QBrush(QColor(fuellfarbe(shape, stil))))
    maler.drawRect(reiter)
    maler.drawRect(koerper)

    maler.setPen(QColor(stil.text))
    maler.setFont(_namensschrift(fett=True, groesse=schriftgroesse(shape)))
    maler.drawText(
        koerper,
        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
        str((shape.get("text") or {}).get("name", "")),
    )


def _auswahl_zeichnen(maler: QPainter, shape: dict, stil: Stil) -> None:
    """Auswahlrahmen plus runde Anfasser in der Akzentfarbe
    (Abschnitt 13.6). Die Anfasser sind hier nur sichtbar; sie werden in
    Schritt 3 auch ziehbar."""
    rechteck = form_rechteck(shape)
    stift = QPen(QColor(stil.akzent))
    stift.setWidthF(LINIENBREITE)
    maler.setPen(stift)
    maler.setBrush(Qt.BrushStyle.NoBrush)
    maler.drawRect(rechteck.adjusted(-2, -2, 2, 2))

    maler.setBrush(QBrush(QColor(stil.akzent)))
    for x, y in anfasser_punkte(shape):
        maler.drawEllipse(QRectF(x - 3.5, y - 3.5, 7, 7))


def _rand_punkt(rechteck: QRectF, richtung_auf: QPointF) -> QPointF:
    """Schnittpunkt der Linie Mitte→`richtung_auf` mit dem Rand von
    `rechteck` – damit Verbindungen am Formrand enden statt in der
    Mitte zu verschwinden."""
    mitte = rechteck.center()
    dx = richtung_auf.x() - mitte.x()
    dy = richtung_auf.y() - mitte.y()
    if dx == 0 and dy == 0:
        return mitte

    halbe_breite = rechteck.width() / 2
    halbe_hoehe = rechteck.height() / 2
    # Skalierung, bei der die Linie zuerst eine der vier Kanten trifft
    skalierungen = []
    if dx != 0:
        skalierungen.append(halbe_breite / abs(dx))
    if dy != 0:
        skalierungen.append(halbe_hoehe / abs(dy))
    skalierung = min(skalierungen)
    return QPointF(mitte.x() + dx * skalierung, mitte.y() + dy * skalierung)


def verbindungs_punkte(
    verbindung: dict[str, Any], quelle: dict[str, Any], ziel: dict[str, Any]
) -> list[QPointF]:
    """Alle Stützpunkte der Linie: Rand der Quelle, gesetzte
    Knickpunkte, Rand des Ziels."""
    zwischen = [QPointF(x, y) for x, y in (verbindung.get("waypoints") or [])]
    quell_rechteck = form_rechteck(quelle)
    ziel_rechteck = form_rechteck(ziel)

    erster_blick = zwischen[0] if zwischen else ziel_rechteck.center()
    letzter_blick = zwischen[-1] if zwischen else quell_rechteck.center()
    start = _rand_punkt(quell_rechteck, erster_blick)
    ende = _rand_punkt(ziel_rechteck, letzter_blick)
    return [start, *zwischen, ende]


def verbindung_zeichnen(
    maler: QPainter,
    verbindung: dict[str, Any],
    quelle: dict[str, Any],
    ziel: dict[str, Any],
    stil: Stil,
    ausgewaehlt: bool = False,
) -> None:
    """Malt eine Verbindung samt UML-Enden und Beschriftungen
    (Abschnitt 13.4, 13.6)."""
    from ide.diagramm.formen import verbindungs_art

    art = verbindungs_art(verbindung["kind"])
    punkte = verbindungs_punkte(verbindung, quelle, ziel)

    maler.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    farbe = QColor(stil.akzent if ausgewaehlt else stil.linie)
    stift = QPen(farbe)
    stift.setWidthF(LINIENBREITE * (2 if ausgewaehlt else 1))
    if art.gestrichelt:
        stift.setStyle(Qt.PenStyle.DashLine)
    maler.setPen(stift)
    maler.setBrush(Qt.BrushStyle.NoBrush)
    for vorher, nachher in zip(punkte, punkte[1:], strict=False):
        maler.drawLine(vorher, nachher)

    # Enden: durchgezogener Stift, damit Pfeilspitze/Raute auch bei
    # gestrichelter Linie sauber aussehen.
    stift.setStyle(Qt.PenStyle.SolidLine)
    maler.setPen(stift)
    if art.spitze_am_ziel != "keine":
        _spitze_zeichnen(maler, punkte[-2], punkte[-1], art.spitze_am_ziel, stil)
    if art.raute_an_quelle != "keine":
        _raute_zeichnen(maler, punkte[1], punkte[0], art.raute_an_quelle, stil, farbe)



def _winkel_punkte(spitze: QPointF, von: QPointF, laenge: float, breite: float):
    """Zwei Punkte, die mit `spitze` ein gleichschenkliges Dreieck
    bilden, ausgerichtet entlang `von`→`spitze`."""
    winkel = math.atan2(spitze.y() - von.y(), spitze.x() - von.x())
    basis = QPointF(
        spitze.x() - laenge * math.cos(winkel), spitze.y() - laenge * math.sin(winkel)
    )
    normal_x = -math.sin(winkel) * breite / 2
    normal_y = math.cos(winkel) * breite / 2
    return (
        QPointF(basis.x() + normal_x, basis.y() + normal_y),
        QPointF(basis.x() - normal_x, basis.y() - normal_y),
    )


def _spitze_zeichnen(
    maler: QPainter, von: QPointF, spitze: QPointF, art: str, stil: Stil
) -> None:
    links, rechts = _winkel_punkte(spitze, von, 12, 10)
    if art == "offen":
        maler.drawLine(spitze, links)
        maler.drawLine(spitze, rechts)
        return

    pfad = QPainterPath()
    pfad.moveTo(spitze)
    pfad.lineTo(links)
    pfad.lineTo(rechts)
    pfad.closeSubpath()
    maler.setBrush(QBrush(QColor(stil.hintergrund)))  # leeres Dreieck
    maler.drawPath(pfad)
    maler.setBrush(Qt.BrushStyle.NoBrush)


def _raute_zeichnen(
    maler: QPainter, von: QPointF, spitze: QPointF, art: str, stil: Stil, farbe: QColor
) -> None:
    links, rechts = _winkel_punkte(spitze, von, 14, 10)
    winkel = math.atan2(spitze.y() - von.y(), spitze.x() - von.x())
    hinten = QPointF(
        spitze.x() - 28 * math.cos(winkel), spitze.y() - 28 * math.sin(winkel)
    )

    pfad = QPainterPath()
    pfad.moveTo(spitze)
    pfad.lineTo(links)
    pfad.lineTo(hinten)
    pfad.lineTo(rechts)
    pfad.closeSubpath()
    maler.setBrush(QBrush(farbe if art == "gefuellt" else QColor(stil.hintergrund)))
    maler.drawPath(pfad)
    maler.setBrush(Qt.BrushStyle.NoBrush)


def verbindungsbeschriftungen_zeichnen(
    maler: QPainter,
    verbindung: dict[str, Any],
    quelle: dict[str, Any],
    ziel: dict[str, Any],
    stil: Stil,
) -> None:
    """Multiplizitäten/Rollen an den Enden (Abschnitt 13.3).

    Eigene Funktion, die **nach** den Formen gezeichnet wird: vorher lag
    die Beschriftung halb in der Zielform und wurde von ihr überdeckt
    („0..*“ erschien als „0..“), und an Aggregation/Komposition saß sie
    unter der Raute (beides im Screenshot aufgefallen). Jetzt steht sie
    entlang der Linie von der Form weg – hinter einer Raute oder
    Pfeilspitze weiter entfernt – und seitlich neben der Linie.
    """
    from ide.diagramm.formen import verbindungs_art

    labels = verbindung.get("labels") or {}
    if not any(str(wert).strip() for wert in labels.values()):
        return

    art = verbindungs_art(verbindung["kind"])
    punkte = verbindungs_punkte(verbindung, quelle, ziel)
    schrift = _namensschrift(fett=False)
    metrik = QFontMetricsF(schrift)
    maler.setFont(schrift)
    maler.setPen(QColor(stil.text))

    for schluessel, punkt, nachbar, hat_ende in (
        ("from", punkte[0], punkte[1], art.raute_an_quelle != "keine"),
        ("to", punkte[-1], punkte[-2], art.spitze_am_ziel != "keine"),
    ):
        text = str(labels.get(schluessel, "")).strip()
        if not text:
            continue
        dx, dy = nachbar.x() - punkt.x(), nachbar.y() - punkt.y()
        laenge = math.hypot(dx, dy) or 1.0
        ex, ey = dx / laenge, dy / laenge
        abstand = (32 if hat_ende else 12) + metrik.horizontalAdvance(text) / 2
        # senkrecht zur Linie, immer auf dieselbe Seite (oben bzw. links)
        nx, ny = ey, -ex
        if ny > 0 or (ny == 0 and nx > 0):
            nx, ny = -nx, -ny
        mitte_x = punkt.x() + ex * abstand + nx * (metrik.height() * 0.8)
        mitte_y = punkt.y() + ey * abstand + ny * (metrik.height() * 0.8)
        breite = metrik.horizontalAdvance(text) + 4
        hoehe = metrik.height()
        maler.drawText(
            QRectF(mitte_x - breite / 2, mitte_y - hoehe / 2, breite, hoehe),
            Qt.AlignmentFlag.AlignCenter,
            text,
        )


def abstand_zur_verbindung(
    punkt: QPointF, verbindung: dict[str, Any], quelle: dict, ziel: dict
) -> float:
    """Kürzester Abstand von `punkt` zur Linie – für das Anklicken einer
    Verbindung."""
    punkte = verbindungs_punkte(verbindung, quelle, ziel)
    kleinster = float("inf")
    for a, b in zip(punkte, punkte[1:], strict=False):
        dx, dy = b.x() - a.x(), b.y() - a.y()
        laenge_quadrat = dx * dx + dy * dy
        if laenge_quadrat == 0:
            abstand = math.hypot(punkt.x() - a.x(), punkt.y() - a.y())
        else:
            t = max(
                0.0,
                min(
                    1.0,
                    ((punkt.x() - a.x()) * dx + (punkt.y() - a.y()) * dy) / laenge_quadrat,
                ),
            )
            nah_x, nah_y = a.x() + t * dx, a.y() + t * dy
            abstand = math.hypot(punkt.x() - nah_x, punkt.y() - nah_y)
        kleinster = min(kleinster, abstand)
    return kleinster


def anfasser_punkte(shape: dict[str, Any]) -> list[tuple[float, float]]:
    """Die acht Größenanfasser (Ecken + Kantenmitten), wie im Designer."""
    rechteck = form_rechteck(shape)
    links, oben = rechteck.left(), rechteck.top()
    rechts, unten = rechteck.right(), rechteck.bottom()
    mitte_x, mitte_y = rechteck.center().x(), rechteck.center().y()
    return [
        (links, oben), (mitte_x, oben), (rechts, oben),
        (rechts, mitte_y), (rechts, unten), (mitte_x, unten),
        (links, unten), (links, mitte_y),
    ]
