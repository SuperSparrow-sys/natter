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
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QMessageBox

from ide.deutsch import deutsch_einschalten
from ide.fehlermeldung import fehlerhaken_einrichten
from ide.integritaet.start_pruefung import installation_pruefen
from ide.ladeanzeige import Ladeanzeige
from ide.run.interpreter import PYTHON_FLAGGE, als_python_ausfuehren

if TYPE_CHECKING:
    from ide.shell.hauptfenster import HauptFenster

#: Steht auf dem Startbild. Von Hand gepflegt und nicht über
#: `importlib.metadata` gelesen: die Paketangaben nachzuschlagen dauert
#: länger als das Bild, das sie zeigen soll.
VERSION = "0.3.0"


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


def anwendung_erzeugen() -> QApplication:
    """Die `QApplication`, fertig benannt und auf Deutsch gestellt.

    Getrennt von `erstellen()`, damit das Startbild schon stehen kann,
    bevor die Module der IDE geladen werden - vorher gibt es kein Qt,
    das etwas anzeigen könnte, und nachher ist es zu spät.
    """
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
    return app


def erstellen(anzeige: Ladeanzeige | None = None) -> tuple[QApplication, HauptFenster]:
    """Baut Anwendung und Hauptfenster auf, ohne sie zu zeigen.

    Der Import des Hauptfensters steht bewusst hier und nicht am Kopf
    der Datei: er zieht die halbe IDE nach sich und dauert rund 200
    Millisekunden. Am Kopf liefe er, bevor irgendetwas auf dem
    Bildschirm steht - hier läuft er, während das Startbild schon
    sichtbar ist.
    """
    app = anwendung_erzeugen()
    if anzeige is not None:
        anzeige.melden("Oberfläche wird geladen …")

    from ide.shell.hauptfenster import HauptFenster

    if anzeige is not None:
        anzeige.melden("Fenster wird aufgebaut …")
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


def starten() -> tuple[QApplication, HauptFenster | None]:
    """Alles bis zum sichtbaren Fenster - ohne die Ereignisschleife.

    Getrennt von `main()`, damit sich der Start prüfen lässt, ohne
    `app.exec()` aufzurufen. Ein Test, der das tut und sich darauf
    verlässt, dass eine Attrappe die Ereignisschleife abfängt, hängt
    für immer, sobald die Attrappe einmal nicht greift - genau das ist
    im September 2026 passiert, und zwar nur im vollständigen
    Testlauf, nicht wenn die Datei allein lief.

    Liefert `None` als Fenster, wenn die Prüfung der Installation den
    Start abgelehnt hat.
    """
    app = anwendung_erzeugen()
    # Ab hier endet ein Fehler in Natter selbst in einer deutschen
    # Meldung statt in einem Traceback, den in der gebauten Exe ohnehin
    # niemand zu sehen bekäme (M11, Abschnitt 5).
    #
    # Der Haken stand bis September 2026 erst hinter `erstellen()`, und
    # damit genau hinter der Stelle, an der am meisten schiefgehen
    # kann: beim Aufbau des Hauptfensters. Scheiterte der, gab es
    # keinen Dialog und keine Protokolldatei - die Ladeanzeige blitzte
    # auf, und das Programm verschwand. Auf einem fremden Rechner war
    # damit nicht einmal zu erkennen, dass überhaupt ein Fehler
    # vorlag. Er steht deshalb vor allem anderen; `anwendung_erzeugen()`
    # muss nur davor bleiben, weil ohne `QApplication` kein Dialog
    # aufgehen kann.
    fehlerhaken_einrichten()

    # Der Ladekreis am Zeiger, solange gebaut wird. Windows zeigt ihn
    # von sich aus nur die ersten Augenblicke nach dem Doppelklick und
    # nimmt ihn dann wieder weg - ausgerechnet in der Zeit, in der
    # noch nichts zu sehen ist.
    QApplication.setOverrideCursor(QCursor(Qt.CursorShape.BusyCursor))

    anzeige = Ladeanzeige(VERSION)
    anzeige.show()
    anzeige.melden("Natter wird gestartet …")

    try:
        app, fenster = erstellen(anzeige)
    except BaseException:
        # Die Ladeanzeige bleibt sonst als Feld ohne Fenster stehen,
        # und der Mauszeiger dreht sich weiter, während der
        # Fehlerdialog auf eine Antwort wartet.
        anzeige.close()
        QApplication.restoreOverrideCursor()
        raise

    if not integritaet_bestaetigen(fenster):
        anzeige.finish(fenster)
        QApplication.restoreOverrideCursor()
        return app, None

    anzeige.melden("Projekt wird geöffnet …")
    _projekt_aus_argv_oeffnen(fenster, sys.argv)
    fenster.show()
    # `finish` blendet das Bild genau dann aus, wenn das Hauptfenster
    # zu sehen ist - sonst blitzt der Schreibtisch dazwischen auf.
    anzeige.finish(fenster)
    QApplication.restoreOverrideCursor()
    return app, fenster


def main() -> int:
    # Ganz am Anfang, noch vor jedem Qt-Aufruf: mit `--python` davor ist
    # dieser Aufruf kein Start der IDE, sondern ein Python-Aufruf. Die
    # gebaute `Natter.exe` enthält einen vollständigen Python, und nur
    # so kommt sie an ihn heran - `sys.executable` ist dort die Exe
    # selbst (M12, siehe `ide/run/interpreter.py`).
    if len(sys.argv) > 1 and sys.argv[1] == PYTHON_FLAGGE:
        return als_python_ausfuehren(sys.argv[2:])

    app, fenster = starten()
    if fenster is None:
        return 1
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
