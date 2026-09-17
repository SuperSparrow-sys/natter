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

from typing import Any

from PySide6.QtCore import QRectF, Qt
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


def _namensschrift(fett: bool = True, kursiv: bool = False) -> QFont:
    schrift = QFont(_NAMENSSCHRIFT, 10)
    schrift.setBold(fett)
    schrift.setItalic(kursiv)
    return schrift


def _mono_schrift() -> QFont:
    schrift = QFont(_MONOSCHRIFT, 9)
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
    if kind not in ("class", "abstract_class", "interface"):
        return KOPFHOEHE + 2 * INNENABSTAND

    text = shape.get("text") or {}
    attribute = max(1, len(text.get("attributes") or []))
    methoden = max(1, len(text.get("methods") or []))
    zeilenhoehe = QFontMetricsF(_mono_schrift()).height()
    kopf = KOPFHOEHE * (2 if kind == "interface" else 1)
    return kopf + (attribute + methoden) * zeilenhoehe + 2 * INNENABSTAND


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
    maler.setPen(_stift(stil))
    maler.setBrush(QBrush(QColor(stil.fuellung)))
    maler.drawRect(rechteck)

    text = shape.get("text") or {}
    abstrakt = kind == "abstract_class" or bool(shape.get("abstract"))
    maler.setPen(QColor(stil.text))

    kopf_unten = rechteck.top() + KOPFHOEHE
    if kind == "interface":
        maler.setFont(_namensschrift(fett=False))
        maler.drawText(
            QRectF(rechteck.left(), rechteck.top() + 4, rechteck.width(), KOPFHOEHE - 6),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            "«interface»",
        )
        kopf_unten = rechteck.top() + 2 * KOPFHOEHE

    name = str(text.get("name", ""))
    maler.setFont(_namensschrift(fett=True, kursiv=abstrakt))
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

    attribut_unten = kopf_unten + max(1, len(attribute)) * zeilenhoehe + INNENABSTAND
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

    maler.setPen(_stift(stil))
    maler.setBrush(QBrush(QColor(stil.fuellung)))
    maler.drawPath(pfad)
    # umgeknickte Ecke
    maler.drawLine(rechteck.right() - ECKE, rechteck.top(),
                   rechteck.right() - ECKE, rechteck.top() + ECKE)
    maler.drawLine(rechteck.right() - ECKE, rechteck.top() + ECKE,
                   rechteck.right(), rechteck.top() + ECKE)

    maler.setPen(QColor(stil.text))
    maler.setFont(_namensschrift(fett=False))
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

    maler.setPen(_stift(stil))
    maler.setBrush(QBrush(QColor(stil.fuellung)))
    maler.drawRect(reiter)
    maler.drawRect(koerper)

    maler.setPen(QColor(stil.text))
    maler.setFont(_namensschrift(fett=True))
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
