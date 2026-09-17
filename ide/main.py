"""Einstiegspunkt der IDE.

Ausführen mit:

    uv run python -m ide
    uv run python -m ide "pfad/zu/projekt.natter"

`erstellen()` baut Anwendung und Hauptfenster auf (testbar, ohne die
blockierende Ereignisschleife zu starten); `main()` zeigt das Fenster und
startet sie. Ein `.natter`-Pfad als erstes Kommandozeilenargument wird
direkt geöffnet (Nutzer-Feedback September 2026: „man installiert die
Exe und kann dann auch eine .natter-Datei einfach öffnen" – die
Windows-Dateizuordnung aus `tools/natter.iss` reicht den Pfad genauso
weiter, `_projekt_aus_argv_oeffnen()` ist dafür separat testbar).
"""

from __future__ import annotations

import sys
from pathlib import Path

import jsonschema
from PySide6.QtWidgets import QApplication, QMessageBox

from ide.integritaet.start_pruefung import installation_pruefen
from ide.shell.hauptfenster import HauptFenster


def integritaet_bestaetigen(fenster: HauptFenster) -> bool:
    """Prüft die Installation gegen ihr signiertes Prüfsummen-Manifest
    (Abschnitt 17.8). Bei Abweichung entscheidet die Nutzerin, ob Natter
    trotzdem startet; im Entwicklungsbaum passiert nichts."""
    ergebnis = installation_pruefen()
    if ergebnis is None or ergebnis.in_ordnung:
        return True

    antwort = QMessageBox.warning(
        fenster,
        "Natter wurde verändert",
        f"{ergebnis.als_meldung()}\n\nTrotzdem starten?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return antwort == QMessageBox.StandardButton.Yes


def erstellen() -> tuple[QApplication, HauptFenster]:
    app = QApplication.instance() or QApplication(sys.argv)
    fenster = HauptFenster()
    return app, fenster


def _projekt_aus_argv_oeffnen(fenster: HauptFenster, argv: list[str]) -> None:
    """Öffnet `argv[1]` als Projekt, falls es auf `.natter` endet (vom
    Windows-Dateiverknüpfungs-Aufruf `Natter.exe "%1"`). Ein ungültiger
    oder nicht mehr vorhandener Pfad zeigt eine Meldung statt die IDE
    beim Start abstürzen zu lassen."""
    if len(argv) <= 1 or not argv[1].lower().endswith(".natter"):
        return
    try:
        fenster.projekt_oeffnen(Path(argv[1]))
    except (OSError, ValueError, jsonschema.ValidationError) as fehler:
        QMessageBox.warning(fenster, "Projekt konnte nicht geöffnet werden", str(fehler))


def main() -> int:
    app, fenster = erstellen()
    if not integritaet_bestaetigen(fenster):
        return 1
    _projekt_aus_argv_oeffnen(fenster, sys.argv)
    fenster.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
