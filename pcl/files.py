"""Datei-/Pfad-Hilfen (Abschnitt 11.1, 11.3): ``open_url`` löst relative
Pfade zum Arbeitsverzeichnis auf und öffnet sie im Standardbrowser.
"""

from __future__ import annotations

import webbrowser
from pathlib import Path


def open_url(pfad_oder_adresse: str) -> None:
    """Öffnet `pfad_oder_adresse` im Standardbrowser (Abschnitt 11.3).

    Adressen mit einem Schema (``https://``, ``mailto:`` usw.) werden
    unverändert übergeben; alles andere gilt als Dateipfad und wird bei
    Bedarf gegen das aktuelle Arbeitsverzeichnis zu einem absoluten
    ``file://``-Pfad aufgelöst – dadurch funktioniert ``open_url(...)``
    für lokal erzeugte Dateien genauso ohne absolute Pfade wie
    `open(...)` (Abschnitt 11.1)."""
    if _hat_schema(pfad_oder_adresse):
        ziel = pfad_oder_adresse
    else:
        ziel = Path(pfad_oder_adresse).resolve().as_uri()
    webbrowser.open(ziel)


def _hat_schema(text: str) -> bool:
    # len(schema) >= 2 unterscheidet ein echtes URL-Schema (http, mailto,
    # ...) von einem einzelnen Windows-Laufwerksbuchstaben ("C:\...").
    schema, trenner, _ = text.partition(":")
    return trenner == ":" and len(schema) >= 2 and schema.isalpha()
