"""Layout und Zeichnen einer Entscheidungstabelle (Abschnitt 13.5,
M9 Schritt 10).

Eine Entscheidungstabelle besteht aus einem Bedingungsteil und einem
Aktionsteil; jede Regel ist eine **Spalte**, die durch beide Teile
läuft (siehe `schemas/pdiag.schema.json`, `conditions`/`actions`).

Gemalt wird mit `QPainter` und nicht mit einem `QTableWidget` – aus
demselben Grund wie beim Struktogramm: Bildschirm, PNG-, SVG- und
PDF-Export sollen denselben Code benutzen, damit die Abgabe genau so
aussieht wie das, was auf dem Bildschirm stand.

Bewusst **ohne** automatische Zusammenfassung oder
Vollständigkeitsprüfung von Regeln (im Konzept so festgehalten): der
Editor zeichnet, er denkt nicht mit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPen

from ide.diagramm.stil import Stil

LINIENBREITE = 1.5
INNENABSTAND = 6
#: Breite der Textspalte links.
TEXTSPALTE = 320
#: Breite einer Regel-Spalte.
REGELSPALTE = 48
ZEILENHOEHE = 26
#: Höhe der beiden Überschriftenzeilen („Bedingungen“/„Aktionen“).
KOPFHOEHE = 26

_SCHRIFT = "Segoe UI"

#: Werte, die eine Bedingungszelle durchläuft (Abschnitt 13.5).
BEDINGUNGSWERTE = ("J", "N", "*", "")
#: Werte, die eine Aktionszelle durchläuft.
AKTIONSWERTE = ("X", "")


@dataclass(frozen=True)
class Zelle:
    """Eine anklickbare Stelle der Tabelle. `spalte = -1` ist die
    Textspalte links, sonst die Nummer der Regel."""

    teil: str  # "conditions" oder "actions"
    zeile: int
    spalte: int
    rechteck: QRectF


def regelanzahl(daten: dict[str, Any]) -> int:
    """Wie viele Regel-Spalten die Tabelle hat. Richtet sich nach der
    längsten Wertezeile – eine von Hand gekürzte Datei soll den Editor
    nicht durcheinanderbringen."""
    zeilen = [*(daten.get("conditions") or []), *(daten.get("actions") or [])]
    return max((len(zeile.get("values") or []) for zeile in zeilen), default=0)


def wert(zeile: dict[str, Any], spalte: int) -> str:
    werte = zeile.get("values") or []
    return str(werte[spalte]) if 0 <= spalte < len(werte) else ""


def _schrift(groesse: int = 9, fett: bool = False) -> QFont:
    schrift = QFont(_SCHRIFT, groesse)
    schrift.setBold(fett)
    return schrift


def tabellengroesse(daten: dict[str, Any]) -> tuple[float, float]:
    bedingungen = daten.get("conditions") or []
    aktionen = daten.get("actions") or []
    breite = TEXTSPALTE + max(1, regelanzahl(daten)) * REGELSPALTE
    hoehe = 2 * KOPFHOEHE + (len(bedingungen) + len(aktionen)) * ZEILENHOEHE
    return breite, hoehe


def zellen(daten: dict[str, Any], x: float = 0, y: float = 0) -> list[Zelle]:
    """Alle Zellen mit ihrer Geometrie – die Zeichenfläche benutzt sie
    für die Treffersuche, das Zeichnen für die Rahmen."""
    ergebnis: list[Zelle] = []
    spalten = max(1, regelanzahl(daten))
    oben = y

    for teil in ("conditions", "actions"):
        oben += KOPFHOEHE  # Überschriftenzeile
        for nummer, _ in enumerate(daten.get(teil) or []):
            ergebnis.append(
                Zelle(teil, nummer, -1, QRectF(x, oben, TEXTSPALTE, ZEILENHOEHE))
            )
            for spalte in range(spalten):
                ergebnis.append(
                    Zelle(
                        teil,
                        nummer,
                        spalte,
                        QRectF(
                            x + TEXTSPALTE + spalte * REGELSPALTE,
                            oben,
                            REGELSPALTE,
                            ZEILENHOEHE,
                        ),
                    )
                )
            oben += ZEILENHOEHE
    return ergebnis


def zelle_bei(daten: dict[str, Any], x: float, y: float, versatz_x: float = 0,
              versatz_y: float = 0) -> Zelle | None:
    for zelle in zellen(daten, versatz_x, versatz_y):
        if zelle.rechteck.contains(x, y):
            return zelle
    return None


# -- Zeichnen ------------------------------------------------------------


def _stift(stil: Stil, dick: bool = False) -> QPen:
    stift = QPen(QColor(stil.rand))
    stift.setWidthF(LINIENBREITE * (2 if dick else 1))
    return stift


def tabelle_zeichnen(
    maler: QPainter,
    daten: dict[str, Any],
    stil: Stil,
    x: float = 0,
    y: float = 0,
    ausgewaehlt: Zelle | None = None,
) -> None:
    maler.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    breite, hoehe = tabellengroesse(daten)
    spalten = max(1, regelanzahl(daten))

    maler.setPen(_stift(stil))
    maler.setBrush(QBrush(QColor(stil.fuellung)))
    maler.drawRect(QRectF(x, y, breite, hoehe))

    oben = y
    for teil, ueberschrift in (("conditions", "Bedingungen"), ("actions", "Aktionen")):
        kopf = QRectF(x, oben, breite, KOPFHOEHE)
        maler.setPen(_stift(stil))
        maler.setBrush(QBrush(QColor(stil.kopf)))
        maler.drawRect(kopf)
        maler.setPen(QColor(stil.text))
        maler.setFont(_schrift(fett=True))
        maler.drawText(
            kopf.adjusted(INNENABSTAND, 0, -INNENABSTAND, 0),
            int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
            ueberschrift,
        )
        # Regelnummern über dem Bedingungsteil
        if teil == "conditions":
            maler.setFont(_schrift(8, fett=True))
            for spalte in range(spalten):
                maler.drawText(
                    QRectF(
                        x + TEXTSPALTE + spalte * REGELSPALTE, oben, REGELSPALTE, KOPFHOEHE
                    ),
                    int(Qt.AlignmentFlag.AlignCenter),
                    f"R{spalte + 1}",
                )
        oben += KOPFHOEHE

        for zeile in daten.get(teil) or []:
            maler.setPen(QColor(stil.text))
            maler.setFont(_schrift())
            maler.drawText(
                QRectF(x + INNENABSTAND, oben, TEXTSPALTE - 2 * INNENABSTAND, ZEILENHOEHE),
                int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter),
                str(zeile.get("text", "")),
            )
            for spalte in range(spalten):
                maler.drawText(
                    QRectF(
                        x + TEXTSPALTE + spalte * REGELSPALTE, oben, REGELSPALTE, ZEILENHOEHE
                    ),
                    int(Qt.AlignmentFlag.AlignCenter),
                    wert(zeile, spalte),
                )
            oben += ZEILENHOEHE
            maler.setPen(_stift(stil))
            trennlinie = QRectF(x, oben, breite, 0)
            maler.drawLine(trennlinie.topLeft(), trennlinie.topRight())

    # Senkrechte Linien: dick zwischen Text- und Regelteil
    maler.setPen(_stift(stil, dick=True))
    maler.drawLine(
        QRectF(x + TEXTSPALTE, y, 0, hoehe).topLeft(),
        QRectF(x + TEXTSPALTE, y, 0, hoehe).bottomLeft(),
    )
    maler.setPen(_stift(stil))
    for spalte in range(1, spalten):
        links = x + TEXTSPALTE + spalte * REGELSPALTE
        maler.drawLine(
            QRectF(links, y, 0, hoehe).topLeft(), QRectF(links, y, 0, hoehe).bottomLeft()
        )

    if ausgewaehlt is not None:
        stift = QPen(QColor(stil.akzent))
        stift.setWidthF(2.0)
        maler.setPen(stift)
        maler.setBrush(Qt.BrushStyle.NoBrush)
        maler.drawRect(ausgewaehlt.rechteck.adjusted(1, 1, -1, -1))


def spaltenbreite_reicht(daten: dict[str, Any]) -> bool:
    """Ob die längste Zeilenbeschriftung noch in die Textspalte passt –
    Grundlage für den Layout-Hinweis „abgeschnittener Text“."""
    metriken = QFontMetricsF(_schrift())
    zeilen = [*(daten.get("conditions") or []), *(daten.get("actions") or [])]
    return all(
        metriken.horizontalAdvance(str(zeile.get("text", ""))) <= TEXTSPALTE - 2 * INNENABSTAND
        for zeile in zeilen
    )
