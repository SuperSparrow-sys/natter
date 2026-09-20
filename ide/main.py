"""Einstiegspunkt der IDE.

Ausführen mit:

 uv run python -m ide
 uv run python -m ide "pfad/zu/projekt.natter"

`erstellen` baut Anwendung und Hauptfenster auf (testbar, ohne die
blockierende Ereignisschleife zu starten); `main` zeigt das Fenster und
startet sie. Ein `.natter`-Pfad als erstes Kommandozeilenargument wird
direkt geöffnet (Gewünscht: „man installiert die
Exe und kann dann auch eine.natter-Datei einfach öffnen" – die
Windows-Dateizuordnung aus `tools/natter.iss` reicht den Pfad genauso
weiter, `_projekt_aus_argv_oeffnen` ist dafür separat testbar).
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from ide.deutsch import deutsch_einschalten
from ide.fehlermeldung import fehlerhaken_einrichten
from ide.integritaet.start_pruefung import installation_pruefen
from ide.run.interpreter import PYTHON_FLAGGE, als_python_ausfuehren
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
    # Ohne Namen legt Qt anwendungseigene Dateien unter „python3“ ab -
    # die Protokolldatei aus `ide/fehlermeldung.py` landete so in einem
    # Ordner, in dem sie niemand vermutet (M11, Abschnitt 5).
    app.setOrganizationName("Natter")
    app.setApplicationName("Natter")
    # Qts eigene Texte auf Deutsch, bevor das Fenster entsteht: die
    # Tastenkürzel in den Menüs („Strg+S“ statt „Ctrl+S“) werden beim
    # Aufbau gesetzt (M11, Abschnitt 4).
    deutsch_einschalten(app)
    fenster = HauptFenster()
    return app, fenster


def _projekt_aus_argv_oeffnen(fenster: HauptFenster, argv: list[str]) -> None:
    """Öffnet `argv[1]` als Projekt, falls es auf `.natter` endet (vom
    Windows-Dateiverknüpfungs-Aufruf `Natter.exe "%1"`). Ein ungültiger
    oder nicht mehr vorhandener Pfad zeigt eine Meldung statt die IDE
    beim Start abstürzen zu lassen."""
    if len(argv) <= 1 or not argv[1].lower().endswith(".natter"):
        return
    # Dieselbe Meldung wie über „Projekt → Öffnen …“ und über „Zuletzt
    # geöffnet“ - drei Wege, ein Verhalten (M11, Abschnitt 5).
    fenster.projekt_oeffnen_gemeldet(Path(argv[1]))


def main() -> int:
    # Ganz am Anfang, noch vor jedem Qt-Aufruf: mit `--python` davor ist
    # dieser Aufruf kein Start der IDE, sondern ein Python-Aufruf. Die
    # gebaute `Natter.exe` enthält einen vollständigen Python, und nur
    # so kommt sie an ihn heran - `sys.executable` ist dort die Exe
    # selbst (M12, siehe `ide/run/interpreter.py`).
    if len(sys.argv) > 1 and sys.argv[1] == PYTHON_FLAGGE:
        return als_python_ausfuehren(sys.argv[2:])

    app, fenster = erstellen()
    # Ab hier endet ein Fehler in Natter selbst in einer deutschen
    # Meldung statt in einem Traceback, den in der gebauten Exe ohnehin
    # niemand zu sehen bekäme (M11, Abschnitt 5). Bewusst erst hier und
    # nicht in `erstellen()`: in den Tests soll ein Fehler weiterhin den
    # Test scheitern lassen und kein Fenster öffnen.
    fehlerhaken_einrichten()
    if not integritaet_bestaetigen(fenster):
        return 1
    _projekt_aus_argv_oeffnen(fenster, sys.argv)
    fenster.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
