"""Export und Drucken von Diagrammen (Abschnitt 13.2, M9 Schritt 8).

PNG, SVG, PDF, Zwischenablage und Drucken – alles mit Bordmitteln von
PySide6 (`QSvgGenerator`, `QPdfWriter`, `QPrinter`), also ohne neue
Abhängigkeit.

Gezeichnet wird mit **demselben** Code wie auf dem Bildschirm
(`ide/diagramm/zeichnen.py`), damit der Export nie eine zweite,
abweichende Darstellung erzeugt. Weggelassen wird nur, was zur
Bedienung gehört und nicht zum Diagramm: Raster, Auswahlrahmen,
Hilfslinien und die Warnrahmen der Layout-Hinweise. Maßgeblich ist
immer die im Diagramm gewählte Stilvorlage, nie das Theme der IDE – ein
im dunklen Theme gezeichnetes Klassendiagramm kommt so trotzdem als
Schwarz-Weiß-Abgabe aus dem Drucker.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QMarginsF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter
from PySide6.QtSvg import QSvgGenerator

from ide.diagramm.seite import DPI, seitengroesse
from ide.diagramm.stil import stil as stil_zu_namen
from ide.diagramm.zeichnen import (
    form_rechteck,
    form_zeichnen,
    verbindung_zeichnen,
    verbindungsbeschriftungen_zeichnen,
)

#: Weißer Rand um den Inhalt beim Export „nur Inhalt“ (PNG/SVG).
RAND = 16


def _form_mit_id(daten: dict[str, Any], kennung: str) -> dict[str, Any] | None:
    for form in daten.get("shapes") or []:
        if form.get("id") == kennung:
            return form
    return None


def inhaltsbereich(daten: dict[str, Any]) -> QRectF:
    """Das kleinste Rechteck, das alle Formen umschließt, plus Rand.
    Für PNG/SVG besser als die volle Blattgröße: ein Diagramm mit drei
    Klassen soll kein Bild mit 80 % weißer Fläche ergeben."""
    formen = daten.get("shapes") or []
    if not formen:
        breite, hoehe = seitengroesse(daten.get("page") or {})
        return QRectF(0, 0, breite, hoehe)

    bereich = form_rechteck(formen[0])
    for form in formen[1:]:
        bereich = bereich.united(form_rechteck(form))
    return bereich.adjusted(-RAND, -RAND, RAND, RAND)


def diagramm_zeichnen(maler: QPainter, daten: dict[str, Any]) -> None:
    """Malt das Diagramm ohne jede Bedienhilfe – dieselbe Reihenfolge
    wie `DiagrammCanvas.paintEvent`: erst die Verbindungen, dann die
    Formen darüber, zuletzt die Beschriftungen, damit sie nicht von
    einer Form verdeckt werden."""
    stil = stil_zu_namen(str(daten.get("style", "modern-light")))
    verbindungen = daten.get("connectors") or []

    for verbindung in verbindungen:
        quelle = _form_mit_id(daten, verbindung.get("from"))
        ziel = _form_mit_id(daten, verbindung.get("to"))
        if quelle is not None and ziel is not None:
            verbindung_zeichnen(maler, verbindung, quelle, ziel, stil)

    for form in daten.get("shapes") or []:
        form_zeichnen(maler, form, stil)

    for verbindung in verbindungen:
        quelle = _form_mit_id(daten, verbindung.get("from"))
        ziel = _form_mit_id(daten, verbindung.get("to"))
        if quelle is not None and ziel is not None:
            verbindungsbeschriftungen_zeichnen(maler, verbindung, quelle, ziel, stil)


def _hintergrund(daten: dict[str, Any]) -> QColor:
    return QColor(stil_zu_namen(str(daten.get("style", "modern-light"))).hintergrund)


# -- PNG -----------------------------------------------------------------


def als_png(
    daten: dict[str, Any],
    pfad: Path,
    skalierung: float = 1.0,
    transparent: bool = False,
) -> Path:
    """Rastergrafik des Inhaltsbereichs. `skalierung` = 2.0 ergibt die
    doppelte Auflösung (zum Einfügen in ein Arbeitsblatt, das später
    gedruckt wird), `transparent` lässt den Hintergrund frei."""
    bereich = inhaltsbereich(daten)
    bild = QImage(
        QSize(
            max(1, round(bereich.width() * skalierung)),
            max(1, round(bereich.height() * skalierung)),
        ),
        QImage.Format.Format_ARGB32,
    )
    bild.fill(Qt.GlobalColor.transparent if transparent else _hintergrund(daten))

    maler = QPainter(bild)
    maler.scale(skalierung, skalierung)
    maler.translate(-bereich.left(), -bereich.top())
    diagramm_zeichnen(maler, daten)
    maler.end()

    pfad = Path(pfad)
    if not bild.save(str(pfad), "PNG"):
        raise OSError(f"PNG konnte nicht geschrieben werden: {pfad}")
    return pfad


def als_bild(daten: dict[str, Any], skalierung: float = 1.0) -> QImage:
    """Dasselbe Bild wie `als_png`, aber im Speicher – für die
    Zwischenablage (Einfügen in Word o. Ä., Abschnitt 13.2)."""
    bereich = inhaltsbereich(daten)
    bild = QImage(
        QSize(
            max(1, round(bereich.width() * skalierung)),
            max(1, round(bereich.height() * skalierung)),
        ),
        QImage.Format.Format_ARGB32,
    )
    bild.fill(_hintergrund(daten))
    maler = QPainter(bild)
    maler.scale(skalierung, skalierung)
    maler.translate(-bereich.left(), -bereich.top())
    diagramm_zeichnen(maler, daten)
    maler.end()
    return bild


def in_zwischenablage(daten: dict[str, Any]) -> QImage:
    from PySide6.QtWidgets import QApplication

    bild = als_bild(daten)
    QApplication.clipboard().setImage(bild)
    return bild


# -- SVG -----------------------------------------------------------------


def als_svg(daten: dict[str, Any], pfad: Path) -> Path:
    """Vektorgrafik – verlustfrei skalierbar und in LibreOffice/Word
    weiterverwendbar."""
    bereich = inhaltsbereich(daten)
    pfad = Path(pfad)

    erzeuger = QSvgGenerator()
    erzeuger.setFileName(str(pfad))
    erzeuger.setSize(QSize(round(bereich.width()), round(bereich.height())))
    erzeuger.setViewBox(QRectF(0, 0, bereich.width(), bereich.height()))
    erzeuger.setTitle(str(daten.get("name") or pfad.stem))
    erzeuger.setDescription("Erstellt mit dem Diagramm-Editor von Natter")

    maler = QPainter(erzeuger)
    maler.fillRect(QRectF(0, 0, bereich.width(), bereich.height()), _hintergrund(daten))
    maler.translate(-bereich.left(), -bereich.top())
    diagramm_zeichnen(maler, daten)
    maler.end()
    return pfad


# -- PDF und Drucken -----------------------------------------------------


def _seitenformat(daten: dict[str, Any]) -> tuple[QPageSize, bool]:
    seite = daten.get("page") or {}
    name = str(seite.get("size", "A4")).upper()
    groesse = {
        "A3": QPageSize.PageSizeId.A3,
        "A4": QPageSize.PageSizeId.A4,
        "A5": QPageSize.PageSizeId.A5,
    }.get(name, QPageSize.PageSizeId.A4)
    return QPageSize(groesse), seite.get("orientation") == "landscape"


def als_pdf(daten: dict[str, Any], pfad: Path) -> Path:
    """Seitengetreues PDF – das Format aus der `.pdiag`, nicht der
    Inhaltsbereich. Das ist die Abgabeform aus dem Abnahmekriterium."""
    pfad = Path(pfad)
    schreiber = QPdfWriter(str(pfad))
    seitenformat, quer = _seitenformat(daten)
    schreiber.setPageSize(seitenformat)
    schreiber.setPageOrientation(
        QPageLayout.Orientation.Landscape if quer else QPageLayout.Orientation.Portrait
    )
    # Auflösung auf 96 dpi: dann entspricht eine PDF-Einheit genau einem
    # Pixel der Zeichenfläche und das Diagramm landet ohne Umrechnung an
    # derselben Stelle wie auf dem Bildschirm.
    schreiber.setResolution(int(DPI))
    schreiber.setPageMargins(QMarginsF(0, 0, 0, 0))
    schreiber.setTitle(str(daten.get("name") or pfad.stem))

    maler = QPainter(schreiber)
    diagramm_zeichnen(maler, daten)
    maler.end()
    return pfad


def auf_seite_zeichnen(maler: QPainter, daten: dict[str, Any], breite: float, hoehe: float) -> None:
    """Zeichnet das Diagramm so groß wie möglich auf eine Seite der
    Größe `breite`×`hoehe` – „Anpassen an Seite“ beim Drucken
    (Abschnitt 13.2). Verkleinert nur, vergrößert nie: ein kleines
    Diagramm soll nicht auf Plakatgröße aufgeblasen werden."""
    bereich = inhaltsbereich(daten)
    if bereich.width() <= 0 or bereich.height() <= 0:
        return
    faktor = min(1.0, breite / bereich.width(), hoehe / bereich.height())
    maler.scale(faktor, faktor)
    maler.translate(-bereich.left(), -bereich.top())
    diagramm_zeichnen(maler, daten)
