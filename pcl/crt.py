"""pcl.crt: optionales Hilfsmodul für den Umstieg aus dem CRT-Unterricht
(Abschnitt 9) – Cursorsteuerung und Farben über ANSI-Codes (funktionieren
in Windows Terminal und der Eingabeaufforderung), Tastatureingabe über
`msvcrt` (Windows-Standardbibliothek), Piepton über `winsound`. Reines
Python, keine Voraussetzung für andere `pcl`-Module – deshalb bewusst
nicht in `pcl/__init__.py` re-exportiert, siehe Arbeitspaket M6.

Farbnamen sind die klassischen sechzehn Konsolenfarben, wahlweise auch
als Zahl 0–15.

`msvcrt`/`winsound` werden lokal in den jeweiligen Funktionen importiert
(nicht auf Modulebene), damit `pcl.crt` auch auf dem Linux-CI-Runner
importierbar bleibt (siehe .github/workflows/ci.yml) – nur `read_key()`/
`key_pressed()`/`beep()` brauchen tatsächlich Windows.

Die Steuerzeichen wirken im Konsolenfenster von Windows erst, wenn es
sie verarbeiten soll. Windows Terminal tut das von sich aus, das
klassische Konsolenfenster (`conhost`), das Natter für ein
Konsolenprogramm öffnet, nicht ohne Weiteres. `_konsole_vorbereiten`
schaltet den Modus vor der ersten Ausgabe ein.
"""

from __future__ import annotations

import ctypes
import sys
import time
from typing import Any

#: Aus der Windows-API (`processenv.h`, `consoleapi.h`).
_STD_OUTPUT_HANDLE = -11
_ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

#: Ob `_konsole_vorbereiten` schon gelaufen ist. Einmal je Programm
#: genügt; die Konsole behält den Modus.
_konsole_bereit = False

_FARBEN: dict[str, int] = {
    "black": 0,
    "blue": 1,
    "green": 2,
    "cyan": 3,
    "red": 4,
    "magenta": 5,
    "brown": 6,
    "light_gray": 7,
    "dark_gray": 8,
    "light_blue": 9,
    "light_green": 10,
    "light_cyan": 11,
    "light_red": 12,
    "light_magenta": 13,
    "yellow": 14,
    "white": 15,
}

# ANSI-SGR-Codes je CRT-Farbnummer (0-7 normale, 8-15 helle Varianten).
_VORDERGRUND = (30, 34, 32, 36, 31, 35, 33, 37, 90, 94, 92, 96, 91, 95, 93, 97)
_HINTERGRUND = (40, 44, 42, 46, 41, 45, 43, 47, 100, 104, 102, 106, 101, 105, 103, 107)


def _farbnummer(farbe: int | str) -> int:
    if isinstance(farbe, str):
        try:
            return _FARBEN[farbe.lower()]
        except KeyError:
            raise ValueError(f"Unbekannte Farbe: {farbe!r}.") from None
    if 0 <= farbe <= 15:
        return farbe
    raise ValueError(f"Farbe muss 0 bis 15 sein, erhalten wurde {farbe!r}.")


def virtuelles_terminal_einschalten(kernel32: Any) -> bool:
    """Schaltet an der Standardausgabe die Verarbeitung der
    Steuerzeichen ein. Liefert, ob sie danach an ist.

    `False`, wenn die Ausgabe gar keine Konsole ist - umgeleitet in
    eine Datei, in das Ausgabefenster der IDE oder in einen Test.
    Dann gibt es nichts einzuschalten, und die Steuerzeichen gehen
    unverändert weiter.

    `kernel32` wird hereingereicht, damit sich das ohne echte Konsole
    prüfen lässt.
    """
    griff = kernel32.GetStdHandle(_STD_OUTPUT_HANDLE)
    if not griff or griff == -1:
        return False
    modus = ctypes.c_uint32()
    if not kernel32.GetConsoleMode(griff, ctypes.byref(modus)):
        return False
    if modus.value & _ENABLE_VIRTUAL_TERMINAL_PROCESSING:
        return True
    return bool(
        kernel32.SetConsoleMode(
            griff, modus.value | _ENABLE_VIRTUAL_TERMINAL_PROCESSING
        )
    )


def _konsole_vorbereiten() -> None:
    """Einmal vor der ersten Ausgabe: unter Windows die Steuerzeichen
    im Konsolenfenster einschalten. Anderswo tut das nichts."""
    global _konsole_bereit
    if _konsole_bereit:
        return
    _konsole_bereit = True
    if sys.platform != "win32":
        return
    try:
        kernel32 = ctypes.windll.kernel32
    except (AttributeError, OSError):
        return
    virtuelles_terminal_einschalten(kernel32)


def _ausgeben(steuerzeichen: str) -> None:
    _konsole_vorbereiten()
    sys.stdout.write(steuerzeichen)
    sys.stdout.flush()


def clr_scr() -> None:
    """Löscht den Bildschirm und setzt den Cursor auf die erste Zeile/Spalte."""
    _ausgeben("\033[2J\033[H")


def goto_xy(x: int, y: int) -> None:
    """Setzt den Cursor auf Spalte `x`, Zeile `y` (1-basiert, wie CRT)."""
    _ausgeben(f"\033[{y};{x}H")


def text_color(farbe: int | str) -> None:
    """Setzt die Textfarbe (Name oder 0–15, siehe Modul-Docstring)."""
    _ausgeben(f"\033[{_VORDERGRUND[_farbnummer(farbe)]}m")


def text_background(farbe: int | str) -> None:
    """Setzt die Hintergrundfarbe (Name oder 0–15)."""
    _ausgeben(f"\033[{_HINTERGRUND[_farbnummer(farbe)]}m")


#: Windows meldet Pfeil-, F- und andere Sondertasten als zwei Bytes:
#: erst 0xE0 oder 0x00, dann diesen Code. Die Namen sind dieselben wie
#: bei `on_key_press` in einem Fenster.
_SONDERTASTEN: dict[int, str] = {
    72: "Oben",
    80: "Unten",
    75: "Links",
    77: "Rechts",
    71: "Pos1",
    79: "Ende",
    73: "Bild auf",
    81: "Bild ab",
    82: "Einfg",
    83: "Entf",
    **{59 + nummer: f"F{nummer + 1}" for nummer in range(10)},
    133: "F11",
    134: "F12",
}

#: Die Bytes, mit denen `getch` eine Sondertaste ankündigt.
_VORZEICHEN = (bytes([0xE0]), bytes([0x00]))


def read_key() -> str:
    """Liest eine Taste von der Tastatur, ohne Enter und ohne Echo
    (Windows, über `msvcrt`).

    Ein Zeichen kommt als das Zeichen selbst („a“, „7“, „ä“). Pfeil-
    und F-Tasten und die übrigen Sondertasten kommen mit ihrem Namen
    wie bei `on_key_press`: „Oben“, „Unten“, „Links“, „Rechts“,
    „Pos1“, „Ende“, „Bild auf“, „Bild ab“, „Einfg“, „Entf“ und „F1“
    bis „F12“. Eine andere Sondertaste, etwa Strg zusammen mit einem
    Pfeil, ergibt einen leeren Text."""
    import msvcrt

    zeichen = msvcrt.getch()
    if zeichen in _VORZEICHEN:
        return _SONDERTASTEN.get(msvcrt.getch()[0], "")
    try:
        return zeichen.decode("cp850")
    except UnicodeDecodeError:
        return zeichen.decode("latin-1")


def key_pressed() -> bool:
    """True, wenn eine Taste wartet, ohne zu blockieren (Windows, über
    `msvcrt`)."""
    import msvcrt

    return msvcrt.kbhit()


def delay(millisekunden: int) -> None:
    """Wartet `millisekunden` Millisekunden."""
    time.sleep(millisekunden / 1000)


def beep(frequenz: int = 800, dauer_ms: int = 200) -> None:
    """Gibt einen Piepton aus (Windows, über `winsound.Beep`)."""
    import winsound

    winsound.Beep(frequenz, dauer_ms)
