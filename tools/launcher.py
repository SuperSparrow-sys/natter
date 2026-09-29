"""Der Starter, aus dem `Natter.exe` gebaut wird (M13).

Seit M13 liegt Natter als gewöhnliche Python-Installation vor (siehe
Arbeitspaket M13). Gestartet wird sie über diesen schlanken
Starter: er sucht die mitgelieferte `pythonw.exe` neben sich und
übergibt ihr `-m ide` samt allem, was an `Natter.exe` übergeben wurde
(etwa der Pfad einer doppelgeklickten `.natter`-Datei).

Warum überhaupt eine eigene Exe, statt im Startmenü direkt auf
`pythonw.exe` zu verweisen: so trägt das Programm sein eigenes Symbol,
seine eigene Versionsangabe und seine eigene Signatur – und im Explorer
steht „Natter“ und nicht „pythonw“.

Bewusst ohne jede Abhängigkeit über die Standardbibliothek hinaus: so
bleibt die gebaute Exe klein und startet ohne spürbare Verzögerung.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

#: Unterordner der Installation, in dem die mitgelieferte Python liegt.
PYTHON_ORDNER = "python"

#: Ohne Konsolenfenster - die IDE ist ein Fensterprogramm.
STARTER = "pythonw.exe"

#: Umgebungsvariablen, die auf eine fremde Python-Installation zeigen.
#:
#: Natter bringt alles mit und soll auch genau das benutzen. Findet die
#: mitgelieferte Python über eine dieser Variablen die Pakete einer
#: anderen Installation, kommen dort eine ältere PySide6-Fassung oder
#: ein halb eingerichtetes NumPy zum Vorschein - und Natter geht auf
#: einem Rechner kaputt, auf dem nie jemand etwas an Natter geändert
#: hat. Auf Entwicklerrechnern ist das der Normalfall; beim Bau der
#: Auslieferung hat genau das zugeschlagen (M13, siehe
#: `tools/ide_paketieren.py`).
FREMDE_UMGEBUNG = ("PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE", "VIRTUAL_ENV")

#: Umgebungsvariablen, über die Qt Plugins oder QML-Module aus einem
#: beliebigen Ordner nachlädt (Punkt 272).
#:
#: Eine Umgebungsvariable für das eigene Konto einzutragen braucht
#: unter Windows keine Verwaltungsrechte. Zeigte eine davon auf einen
#: Ordner im eigenen Profil, liefe dort abgelegter Code in der IDE und
#: in jedem gestarteten Programm mit, an der Integritätsprüfung
#: vorbei. Natter bringt seine Plugins selbst mit und braucht keine.
QT_NACHLADEN = (
    "QT_PLUGIN_PATH",
    "QT_QPA_PLATFORM_PLUGIN_PATH",
    "QML_IMPORT_PATH",
    "QML2_IMPORT_PATH",
)

#: Schalter für die mitgelieferte Python (Punkt 272).
#:
#: `-E` lässt alle `PYTHON*`-Variablen unbeachtet. Ohne ihn liest die
#: IDE etwa `PYTHONPYCACHEPREFIX` aus dem Konto und holt den Bytecode
#: jedes Moduls aus einem Ordner unter diesem Präfix. Eine dort
#: abgelegte `.pyc` ohne Prüfung gegen die Quelle ersetzte dann
#: `pcl.pruefungsmodus` oder jeden anderen Teil der IDE, obwohl im
#: Programmordner keine Datei verändert ist. `-s` steht für
#: `PYTHONNOUSERSITE`, das unter `-E` nicht mehr gelesen wird.
PYTHON_SCHALTER = ("-E", "-s")


def installationsordner() -> Path:
    """Der Ordner, in dem `Natter.exe` liegt."""
    return Path(sys.executable).resolve().parent


def python_pfad(wurzel: Path | None = None) -> Path:
    wurzel = wurzel if wurzel is not None else installationsordner()
    return wurzel / PYTHON_ORDNER / STARTER


def fehlende_installation_melden(pfad: Path) -> None:
    """Sagt, was fehlt – und zwar sichtbar.

    Ein Fensterprogramm ohne Konsole hat sonst keine Möglichkeit dazu;
    ohne diese Meldung würde ein Doppelklick auf `Natter.exe` einfach
    nichts tun.
    """
    text = (
        "Natter ist nicht vollständig installiert.\n\n"
        f"Erwartet wurde:\n{pfad}\n\n"
        "Bitte Natter neu installieren."
    )
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, text, "Natter", 0x10)
    except Exception:
        print(text, file=sys.stderr)


def eigene_umgebung() -> dict[str, str]:
    """Die Umgebung, in der Natter läuft: die des Nutzers, aber ohne
    Verweise auf fremde Python-Installationen, ohne die
    `PYTHON*`-Variablen des Kontos und ohne die Qt-Variablen aus
    `QT_NACHLADEN`.

    Die IDE selbst liest die `PYTHON*`-Variablen wegen `-E` ohnehin
    nicht. Sie gehen aber an jedes Programm weiter, das Natter startet,
    und dort wirkten sie wieder, `PYTHONPYCACHEPREFIX` etwa auch auf
    `pcl`. Was ein gestartetes Programm braucht, setzt die IDE selbst
    (`PYTHONIOENCODING` in `ide/run/interpreter.py`).

    Erbt alles Übrige unverändert - `PATH`, Proxy-Einstellungen und
    was die Schule sonst setzt, wird gebraucht, etwa damit über das
    Menü „Pakete“ Nachinstallieren funktioniert.
    """
    umgebung = {
        name: wert
        for name, wert in os.environ.items()
        if name.upper() not in FREMDE_UMGEBUNG
        and name.upper() not in QT_NACHLADEN
        and not name.upper().startswith("PYTHON")
    }
    umgebung["PYTHONNOUSERSITE"] = "1"
    return umgebung


# -- Startfenster (Punkt 110) ----------------------------------------------
#
# Beim ersten Start nach einer Installation vergehen rund acht Sekunden,
# bis Python und Qt geladen sind und das Ladebild von Natter erscheint
# (Messung zu Punkt 48). In dieser Zeit war nichts zu sehen, und wer ein
# zweites Mal klickte, startete Natter zweimal. Der Starter zeigt deshalb
# sofort ein schlichtes Fenster, gebaut nur mit Windows-Aufrufen - Qt
# wäre hier genau das, worauf gewartet wird.

#: So lange wird höchstens auf das erste Fenster von Natter gewartet.
_GRENZE_SEKUNDEN = 120
#: Name der Sperre, die einen zweiten Start während des Ladens erkennt.
_SPERRE = "Local\\NatterStartetGerade"


def start_laeuft_schon() -> tuple[bool, int | None]:
    """(läuft schon, Griff der Sperre). Solange ein Start lädt, hält
    er eine benannte Sperre; ein zweiter Start sieht sie und endet."""
    if sys.platform != "win32":
        return False, None
    import ctypes

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    griff = kernel32.CreateMutexW(None, False, _SPERRE)
    schon_da = kernel32.GetLastError() == 183  # ERROR_ALREADY_EXISTS
    if schon_da and griff:
        kernel32.CloseHandle(ctypes.c_void_p(griff))
        return True, None
    return False, griff


def sperre_freigeben(griff: int | None) -> None:
    if griff and sys.platform == "win32":
        import ctypes

        ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(griff))


def startfenster_zeigen(text: str = "Natter startet …") -> int | None:
    """Ein kleines Fenster mitten auf dem Bildschirm, ohne Rahmenknöpfe.
    Liefert seinen Griff oder `None`, wenn es sich nicht anlegen ließ -
    dann startet Natter eben ohne."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32
        user32.CreateWindowExW.restype = ctypes.c_void_p
        user32.CreateWindowExW.argtypes = [
            ctypes.c_uint, ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint,
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
        ]
        breite, hoehe = 320, 90
        x = (user32.GetSystemMetrics(0) - breite) // 2
        y = (user32.GetSystemMetrics(1) - hoehe) // 2
        ws_popup, ws_border, ws_visible = 0x80000000, 0x00800000, 0x10000000
        ss_center, ss_centerimage = 0x1, 0x200
        ws_ex_topmost, ws_ex_toolwindow = 0x8, 0x80
        fenster = user32.CreateWindowExW(
            ws_ex_topmost | ws_ex_toolwindow,
            "STATIC",
            text,
            ws_popup | ws_border | ws_visible | ss_center | ss_centerimage,
            x, y, breite, hoehe,
            None, None, None, None,
        )
        if not fenster:
            return None
        gdi32.CreateFontW.restype = ctypes.c_void_p
        schrift = gdi32.CreateFontW(
            -20, 0, 0, 0, 400, 0, 0, 0, 1, 0, 0, 5, 0, "Segoe UI"
        )
        user32.SendMessageW.argtypes = [
            ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p
        ]
        user32.SendMessageW(fenster, 0x0030, schrift, 1)  # WM_SETFONT
        user32.SetWindowTextW(ctypes.c_void_p(fenster), text)
        user32.UpdateWindow(ctypes.c_void_p(fenster))
        _nachrichten_abarbeiten()
        return fenster
    except Exception:
        return None


def _nachrichten_abarbeiten() -> None:
    import ctypes
    import ctypes.wintypes as wt

    user32 = ctypes.windll.user32
    nachricht = wt.MSG()
    while user32.PeekMessageW(ctypes.byref(nachricht), None, 0, 0, 1):  # PM_REMOVE
        user32.TranslateMessage(ctypes.byref(nachricht))
        user32.DispatchMessageW(ctypes.byref(nachricht))


def startfenster_schliessen(fenster: int | None) -> None:
    if fenster and sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.DestroyWindow(ctypes.c_void_p(fenster))


def hat_sichtbares_fenster(pid: int) -> bool:
    """Zeigt der Prozess `pid` schon ein Fenster (das Ladebild oder das
    Hauptfenster)?"""
    if sys.platform != "win32":
        return True
    import ctypes
    import ctypes.wintypes as wt

    user32 = ctypes.windll.user32
    gefunden = []

    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def pruefen(fenster, _):  # noqa: ANN001, ANN202
        besitzer = wt.DWORD()
        user32.GetWindowThreadProcessId(fenster, ctypes.byref(besitzer))
        if besitzer.value == pid and user32.IsWindowVisible(fenster):
            gefunden.append(fenster)
            return False
        return True

    user32.EnumWindows(pruefen, 0)
    return bool(gefunden)


def warten_bis_sichtbar(prozess: subprocess.Popen, fenster: int | None) -> None:
    """Hält das Startfenster am Leben, bis Natter selbst etwas zeigt,
    beendet ist oder die Zeitgrenze erreicht ist."""
    import time

    ende = time.monotonic() + _GRENZE_SEKUNDEN
    while time.monotonic() < ende and prozess.poll() is None:
        if hat_sichtbares_fenster(prozess.pid):
            return
        if fenster:
            _nachrichten_abarbeiten()
        time.sleep(0.05)


def startbefehl(ziel: Path, argumente: list[str]) -> list[str]:
    """Der Befehl, mit dem `ziel` (die mitgelieferte `pythonw.exe`)
    die IDE startet, samt den an `Natter.exe` übergebenen
    Argumenten."""
    return [str(ziel), *PYTHON_SCHALTER, "-m", "ide", *argumente]


def main() -> int:
    ziel = python_pfad()
    if not ziel.is_file():
        fehlende_installation_melden(ziel)
        return 1

    # Ohne Argument ist es ein zweiter Klick aufs Symbol, während der
    # erste Start noch lädt: der wird nicht verdoppelt. Mit einer
    # Projektdatei (Doppelklick auf eine .natter) ist es gewollt.
    laeuft_schon, sperre = start_laeuft_schon()
    if laeuft_schon and len(sys.argv) <= 1:
        return 0

    befehl = startbefehl(ziel, sys.argv[1:])
    # `cwd` auf den Installationsordner: ein relativer Pfad in argv
    # kommt vom Explorer immer absolut, und so landen etwaige
    # Hilfsdateien nicht im zuletzt benutzten Ordner des Nutzers.
    fenster = startfenster_zeigen()
    try:
        prozess = subprocess.Popen(
            befehl, cwd=str(installationsordner()), env=eigene_umgebung()
        )
        warten_bis_sichtbar(prozess, fenster)
    finally:
        startfenster_schliessen(fenster)
        sperre_freigeben(sperre)
    return prozess.wait()


if __name__ == "__main__":
    sys.exit(main())
