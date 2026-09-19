"""Ein Fehler in Natter selbst endet in einer Meldung, nicht in einem
Traceback (M11, Abschnitt 5).

Bis hierher gab es dafür gar nichts. Stürzt etwas in einem Slot ab,
schreibt Python den Traceback nach `stderr` – und die mit PyInstaller
gebaute `Natter.exe` läuft ohne Konsolenfenster (`--windowed`,
`tools/ide_paketieren.py`). Auf einem Schulrechner heißt das: das
Fenster ist weg, und niemand erfährt, warum. Wer aus der Entwicklung
heraus startet, sieht stattdessen einen englischen Traceback, mit dem
eine Schülerin nichts anfangen kann.

Nicht zu verwechseln mit `ide/debugger/fehlerkatalog.py`: der erklärt
Fehler im **Schülerprogramm**. Hier geht es um Fehler in Natter selbst.
"""

from __future__ import annotations

import sys
import traceback
from datetime import datetime
from pathlib import Path
from types import TracebackType

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QMessageBox

#: Was in der Meldung steht. Bewusst ohne Schuldzuweisung an die
#: Nutzerin: ein Absturz in der IDE ist nie ihr Fehler.
UEBERSCHRIFT = "In Natter ist etwas schiefgegangen"

WAS_ZU_TUN_IST = (
    "Das ist ein Fehler in Natter selbst, nicht in deinem Programm.\n\n"
    "Was du tun kannst:\n"
    "• Speichere deine Arbeit (Strg+S) und probiere es noch einmal.\n"
    "• Hilft das nicht, starte Natter neu.\n"
    "• Sag deiner Lehrkraft Bescheid."
)

#: Wird angehängt, sobald der Fehler auch mitgeschrieben werden konnte.
#: Getrennt, weil der Satz sonst auf eine Datei verwiese, die es auf
#: einem Rechner ohne Schreibrecht gar nicht gibt.
PROTOKOLL_HINWEIS = (
    "In dieser Datei steht, was genau passiert ist – sie hilft beim Nachsehen:"
)


def protokoll_pfad() -> Path:
    """Die Datei, in der Abstürze mitgeschrieben werden. Liegt dort, wo
    Windows anwendungseigene Daten erwartet, damit sie auch dann
    schreibbar ist, wenn Natter selbst im Programmordner liegt (auf
    einem Schulrechner ohne Schreibrecht)."""
    ordner = Path(
        QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        or Path.home()
    )
    return ordner / "natter-fehler.log"


def _mitschreiben(text: str) -> Path | None:
    """Hängt den Bericht an die Protokolldatei an. Schlägt das fehl (kein
    Schreibrecht, volle Platte), ist das kein Grund, die Meldung ganz
    ausfallen zu lassen – sie ist das Wichtigere."""
    pfad = protokoll_pfad()
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        with pfad.open("a", encoding="utf-8") as datei:
            datei.write(f"\n===== {datetime.now():%d.%m.%Y %H:%M:%S} =====\n{text}")
    except OSError:
        return None
    return pfad


def bericht(
    art: type[BaseException], wert: BaseException, spur: TracebackType | None
) -> str:
    return "".join(traceback.format_exception(art, wert, spur))


def fehler_melden(
    art: type[BaseException], wert: BaseException, spur: TracebackType | None
) -> None:
    """Zeigt den Fehler als Meldung und schreibt ihn mit."""
    text = bericht(art, wert, spur)
    pfad = _mitschreiben(text)

    meldung = QMessageBox()
    meldung.setIcon(QMessageBox.Icon.Critical)
    meldung.setWindowTitle(UEBERSCHRIFT)
    meldung.setText(f"{UEBERSCHRIFT}: {art.__name__}")
    hinweis = WAS_ZU_TUN_IST
    if pfad is not None:
        hinweis += f"\n\n{PROTOKOLL_HINWEIS}\nProtokolldatei: {pfad}"
    meldung.setInformativeText(hinweis)
    # Der Traceback selbst bleibt eingeklappt: er hilft der Lehrkraft,
    # nicht der Schülerin - und eine Wand aus englischem Text als Erstes
    # zu sehen, schreckt nur ab.
    meldung.setDetailedText(text)
    meldung.exec()


def fehlerhaken_einrichten() -> None:
    """Hängt `fehler_melden` als `sys.excepthook` ein.

    Wird nur von `ide/main.py` gerufen, nicht beim Import: in den Tests
    soll ein Fehler weiterhin den Test scheitern lassen und kein
    Fenster öffnen, auf das niemand klickt.
    """
    sys.excepthook = fehler_melden
