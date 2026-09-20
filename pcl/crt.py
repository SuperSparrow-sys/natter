"""pcl.crt: optionales Hilfsmodul für den Umstieg aus dem CRT-Unterricht
(Abschnitt 9) – Cursorsteuerung und Farben über ANSI-Codes (funktionieren
in Windows Terminal und der Eingabeaufforderung), Tastatureingabe über
`msvcrt` (Windows-Standardbibliothek), Piepton über `winsound`. Reines
Python, keine Voraussetzung für andere `pcl`-Module – deshalb bewusst
nicht in `pcl/__init__.py` re-exportiert, siehe docs/arbeitspakete/M6.md.

Farbnamen sind die klassischen sechzehn Konsolenfarben, wahlweise auch
als Zahl 0–15.

`msvcrt`/`winsound` werden lokal in den jeweiligen Funktionen importiert
(nicht auf Modulebene), damit `pcl.crt` auch auf dem Linux-CI-Runner
importierbar bleibt (siehe .github/workflows/ci.yml) – nur `read_key()`/
`key_pressed()`/`beep()` brauchen tatsächlich Windows.
"""

from __future__ import annotations

import sys
import time

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


def clr_scr() -> None:
    """Löscht den Bildschirm und setzt den Cursor auf die erste Zeile/Spalte."""
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def goto_xy(x: int, y: int) -> None:
    """Setzt den Cursor auf Spalte `x`, Zeile `y` (1-basiert, wie CRT)."""
    sys.stdout.write(f"\033[{y};{x}H")
    sys.stdout.flush()


def text_color(farbe: int | str) -> None:
    """Setzt die Textfarbe (Name oder 0–15, siehe Modul-Docstring)."""
    sys.stdout.write(f"\033[{_VORDERGRUND[_farbnummer(farbe)]}m")
    sys.stdout.flush()


def text_background(farbe: int | str) -> None:
    """Setzt die Hintergrundfarbe (Name oder 0–15)."""
    sys.stdout.write(f"\033[{_HINTERGRUND[_farbnummer(farbe)]}m")
    sys.stdout.flush()


def read_key() -> str:
    """Liest ein einzelnes Zeichen von der Tastatur, ohne Enter und ohne
    Echo (Windows, über `msvcrt`)."""
    import msvcrt

    zeichen = msvcrt.getch()
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
