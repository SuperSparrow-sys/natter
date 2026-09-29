"""Datei-/Pfad-Hilfen (Abschnitt 11.1, 11.3): ``open_url`` löst relative
Pfade zum Arbeitsverzeichnis auf und öffnet sie im Standardbrowser.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import webbrowser
from pathlib import Path


def open_url(pfad_oder_adresse: str) -> None:
    """Öffnet `pfad_oder_adresse` im Standardbrowser (Abschnitt 11.3).

    Adressen mit einem Schema (``https://``, ``mailto:`` usw.) werden
    unverändert übergeben; alles andere gilt als Dateipfad und wird bei
    Bedarf gegen das aktuelle Arbeitsverzeichnis zu einem absoluten
    ``file://``-Pfad aufgelöst – dadurch funktioniert ``open_url(...)``
    für lokal erzeugte Dateien genauso ohne absolute Pfade wie
    `open(...)` (Abschnitt 11.1).

    Eine Adresse ohne Schema, so wie sie meist getippt wird
    (``www.schule.de``, ``schule.de/stundenplan``), bekommt
    ``https://`` vorangestellt, sofern es keine Datei dieses Namens
    gibt. Sie galt sonst als Dateipfad, und der Browser meldete eine
    fehlende Datei."""
    if _hat_schema(pfad_oder_adresse):
        ziel = pfad_oder_adresse
    elif _sieht_aus_wie_webadresse(pfad_oder_adresse):
        ziel = "https://" + pfad_oder_adresse
    else:
        ziel = Path(pfad_oder_adresse).resolve().as_uri()
    _oeffnen(ziel)


def _oeffnen(ziel: str) -> None:
    """Übergibt `ziel` an das zuständige Programm, unter Windows
    möglichst außerhalb des Auftragsobjekts, in dem Natter das
    Programm laufen lässt (Punkt 285).

    Die Shell startet das zuständige Programm als Kind des aufrufenden
    Prozesses. War der Browser noch nicht offen, kam er so in den
    Auftrag und wurde mit „Stopp“ beendet, samt allen Tabs, die
    inzwischen darin geöffnet waren. Gelingt die Übergabe an den
    Explorer nicht, öffnet der eigene Prozess wie bisher."""
    if not _ausserhalb_des_auftrags_oeffnen(ziel):
        webbrowser.open(ziel)


def _ausserhalb_des_auftrags_oeffnen(ziel: str) -> bool:
    """Lässt den laufenden Explorer `ziel` öffnen, falls der eigene
    Prozess in einem Auftragsobjekt läuft. Liefert, ob das
    gestartet wurde.

    Ein neu gestartetes `explorer.exe` gibt das Öffnen an den
    Explorer der Anmeldung weiter und endet. Das zuständige Programm
    entsteht dann als dessen Kind und damit außerhalb des Auftrags.
    Den Auftrag selbst durchlässig zu machen
    (`JOB_OBJECT_LIMIT_BREAKAWAY_OK`), hätte jedem Programm erlaubt,
    sich mit `CREATE_BREAKAWAY_FROM_JOB` aus ihm zu lösen.

    Läuft kein Explorer als Oberfläche, bleibt der gestartete darin
    und öffnet selbst; das ist nicht schlechter als vorher. Rohre
    bekommt er keine, sonst hielte das geöffnete Programm die Ausgabe
    offen."""
    if sys.platform != "win32" or not _in_einem_auftrag():
        return False
    explorer = Path(os.environ.get("SystemRoot", r"C:\Windows"))
    try:
        subprocess.Popen(
            [str(explorer / "explorer.exe"), ziel],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    except OSError:
        return False
    return True


def _in_einem_auftrag() -> bool:
    """Ob der eigene Prozess in einem Auftragsobjekt läuft."""
    try:
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        kernel32.IsProcessInJob.argtypes = [
            ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int)
        ]
        kernel32.IsProcessInJob.restype = ctypes.c_int
        drin = ctypes.c_int(0)
        if not kernel32.IsProcessInJob(
            kernel32.GetCurrentProcess(), None, ctypes.byref(drin)
        ):
            return False
    except (OSError, AttributeError):
        return False
    return bool(drin.value)


def _hat_schema(text: str) -> bool:
    # len(schema) >= 2 unterscheidet ein echtes URL-Schema (http, mailto,
    # ...) von einem einzelnen Windows-Laufwerksbuchstaben ("C:\...").
    schema, trenner, _ = text.partition(":")
    return trenner == ":" and len(schema) >= 2 and schema.isalpha()


def _sieht_aus_wie_webadresse(text: str) -> bool:
    """Ob `text` ein Rechnername mit Punkt ist, etwa „www.schule.de“
    oder „schule.de/plan“, und keine vorhandene Datei. Ein Dateiname
    wie „bericht.html“ bleibt ein Dateiname, auch wenn die Datei
    fehlt: „html“ ist keine Endung einer Webadresse."""
    if Path(text).exists() or "\\" in text:
        return False
    rechner = text.split("/", 1)[0]
    teile = rechner.split(".")
    if len(teile) < 2 or not all(teile):
        return False
    if teile[0].lower() == "www":
        return True
    endung = teile[-1]
    return endung.isalpha() and endung.lower() in _ENDUNGEN_VON_WEBADRESSEN


#: Die Endungen, an denen eine Adresse ohne „www.“ erkannt wird. Nur
#: die im Unterricht üblichen; „html“ oder „txt“ gehören nicht dazu.
_ENDUNGEN_VON_WEBADRESSEN = frozenset(
    {"de", "at", "ch", "com", "org", "net", "info", "eu", "edu", "io"}
)
