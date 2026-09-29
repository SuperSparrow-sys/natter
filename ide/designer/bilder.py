"""Bilddateien für den Formular-Designer übernehmen (Abschnitt 11.4:
„automatische Kopie nach `assets/` (Rückfrage bei gleichem Dateinamen)“).

Wird vom Drag & Drop einer Bilddatei aus dem Windows-Explorer bzw. dem
Projekt-Explorer in den Designer benutzt (`DesignerCanvas.bild_ablegen`).
Reine Dateiarbeit ohne Qt, damit sie sich einzeln testen lässt.
"""

from __future__ import annotations

from pathlib import Path

#: Von Qt ohne Zusatzmodul lesbare Bildformate (Abschnitt 11.4).
BILD_ENDUNGEN: tuple[str, ...] = (
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".ico",
    ".svg",
    ".webp",
)

ASSETS_ORDNER = "assets"


def ist_bilddatei(pfad: Path) -> bool:
    """Ob `pfad` nach Endung eine Bilddatei ist (für Drag & Drop wird nur
    die Endung geprüft – die Datei muss beim Überfliegen des Formulars
    noch nicht gelesen werden)."""
    return Path(pfad).suffix.lower() in BILD_ENDUNGEN


def _freier_name(ziel_ordner: Path, quelle: Path) -> Path:
    """Vermeidet, eine gleichnamige, aber andere Bilddatei zu
    überschreiben: `cookie.png` → `cookie_2.png` → `cookie_3.png`. Eine
    bereits vorhandene, inhaltsgleiche Datei wird wiederverwendet."""
    rohdaten = quelle.read_bytes()
    kandidat = ziel_ordner / quelle.name
    nummer = 2
    while kandidat.exists():
        if kandidat.read_bytes() == rohdaten:
            return kandidat
        kandidat = ziel_ordner / f"{quelle.stem}_{nummer}{quelle.suffix}"
        nummer += 1
    return kandidat


def bild_in_assets_uebernehmen(quelle: Path, projektordner: Path) -> tuple[Path, str]:
    """Kopiert `quelle` nach `projektordner/assets/`, sofern sie nicht
    schon im Projektordner liegt.

    Liefert `(absoluter_pfad, projekt_relativer_pfad)`. Den absoluten
    Pfad braucht die Designer-Vorschau (sie läuft mit beliebigem
    Arbeitsordner), den relativen der Code des Schülerprogramms
    (`picture.load_from_file("assets/cookie.png")`, Abschnitt 11.4) – das
    laufende Programm startet im Projektordner."""
    quelle = Path(quelle).resolve()
    projektordner = Path(projektordner).resolve()

    if quelle.is_relative_to(projektordner):
        return quelle, quelle.relative_to(projektordner).as_posix()

    ziel_ordner = projektordner / ASSETS_ORDNER
    ziel_ordner.mkdir(parents=True, exist_ok=True)
    ziel = _freier_name(ziel_ordner, quelle)
    if not ziel.exists():
        ziel.write_bytes(quelle.read_bytes())
    return ziel, ziel.relative_to(projektordner).as_posix()
