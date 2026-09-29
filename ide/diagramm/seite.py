"""Seitenbereich eines Diagramms (Abschnitt 13.2: „Seitenformat A4/A3,
hoch/quer“).

Die Zeichenfläche rechnet in Pixeln, das Seitenformat ist aber in
Millimetern festgelegt. Umgerechnet wird mit 96 dpi – derselbe Wert,
den Qt für Bildschirmkoordinaten annimmt. Ein Diagramm, das auf dem
Bildschirm innerhalb des Seitenbereichs liegt, passt dadurch auch beim
Export und beim Drucken (Schritt 8) ohne Verkleinern auf das Blatt.
"""

from __future__ import annotations

from typing import Any

#: Blattgrößen in Millimetern (Hochformat).
FORMATE_MM: dict[str, tuple[float, float]] = {
    "A4": (210.0, 297.0),
    "A3": (297.0, 420.0),
    "A5": (148.0, 210.0),
}

#: Bildschirmauflösung, mit der Qt Koordinaten in Millimeter umrechnet.
DPI = 96.0

#: Nicht bedruckbarer Rand, wie ihn übliche Drucker freilassen.
RAND_MM = 10.0


def _in_pixel(millimeter: float) -> float:
    return millimeter / 25.4 * DPI


def seitengroesse(page: dict[str, Any]) -> tuple[float, float]:
    """Breite und Höhe des Blatts in Pixeln, Ausrichtung eingerechnet."""
    breite_mm, hoehe_mm = FORMATE_MM.get(str(page.get("size", "A4")), FORMATE_MM["A4"])
    if page.get("orientation") == "landscape":
        breite_mm, hoehe_mm = hoehe_mm, breite_mm
    return _in_pixel(breite_mm), _in_pixel(hoehe_mm)


def satzspiegel(page: dict[str, Any]) -> tuple[float, float, float, float]:
    """Der bedruckbare Bereich als `(links, oben, breite, höhe)` in
    Pixeln – das Blatt abzüglich des Druckerrands."""
    breite, hoehe = seitengroesse(page)
    rand = _in_pixel(RAND_MM)
    return rand, rand, breite - 2 * rand, hoehe - 2 * rand
