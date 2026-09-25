"""Pfade: mitgelieferte Datenordner der IDE und der Ort, an dem die
Arbeit der Schülerin liegt.

Der erste Teil löst Datenordner (`schemas/`),
die zur Laufzeit gelesen werden statt importiert zu werden. In einer
mit PyInstaller gebauten Exe (`tools/ide_paketieren.py`) liegen diese
Ordner nicht mehr relativ zum Quellcode, sondern im Bundle-Ordner
(`sys._MEIPASS`) - dasselbe Muster wie `pcl/theme/__init__.py` für
`design/tokens.json` (dort eigenständig, weil `pcl` nicht von `ide`
abhängen darf). Eine einzige Quelle für `ide/codegen/design.py`,
`ide/designer/pfm_schreiben.py` und `ide/project/projekt.py`, statt
drei eigenen Kopien.

Der zweite Teil sagt, wohin die Arbeit der Schülerin gehört. Bis
September 2026 stand dafür `Path.home() / "Documents" / "Natter"` im
Quelltext - geraten, nicht ermittelt. Auf einem Rechner mit OneDrive,
und das ist auf Schulrechnern wie auf privaten die Regel, liegt der
Dokumente-Ordner woanders:

    Windows sagt:  C:\\Users\\…\\OneDrive\\Dokumente
    Natter riet:   C:\\Users\\…\\Documents

Natter legte damit einen zweiten Ordner an, den im Explorer niemand
findet, weil dort unter „Dokumente" der andere steht. Auf dem
Rechner, auf dem es auffiel, war es noch unglücklicher: unter diesem
Pfad lag der Entwicklungsbaum von Natter selbst, und die
Arbeitskopien der Beispiele landeten zwischen `ide`, `pcl` und
`docs`.

Den richtigen Pfad kennt Windows selbst. `SHGetKnownFolderPath` ist
der dafür vorgesehene Weg und folgt jeder Umleitung - OneDrive,
Netzlaufwerk, verschobener Ordner. Gefragt wird über `ctypes` aus der
Standardbibliothek; eine zusätzliche Abhängigkeit wäre für einen
Systemaufruf zu viel."""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

_PROJEKT_WURZEL = Path(__file__).resolve().parent.parent


def daten_ordner(name: str) -> Path:
    """`name` (z. B. `"schemas"`) relativ zur Projektwurzel, oder im
    Bundle-Ordner, falls als PyInstaller-Exe eingefroren."""
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass is not None:
        return Path(meipass) / name
    return _PROJEKT_WURZEL / name


#: Der Name des Ordners, in dem Natter die Projekte sammelt. Unter
#: „Dokumente" und nicht im Benutzerprofil: dort sucht unter Windows
#: jeder seine eigenen Dateien, und dorthin sichern Schulen.
NATTER_ORDNER = "Natter"

#: FOLDERID_Documents aus den Windows-Kopfdateien.
_FOLDERID_DOCUMENTS = "{FDD39AD0-238F-46AF-ADB4-6C85480369C7}"


class _GUID(ctypes.Structure):
    _fields_ = (
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_byte * 8),
    )


def _guid(text: str) -> _GUID:
    kennung = _GUID()
    if ctypes.windll.ole32.CLSIDFromString(text, ctypes.byref(kennung)) != 0:
        raise OSError(f"{text} ist keine gültige GUID.")
    return kennung


def dokumente_ordner() -> Path:
    """Der Dokumente-Ordner, wie Windows ihn kennt.

    Fällt auf `~/Documents` zurück, wenn die Abfrage nichts liefert
    oder das Programm nicht unter Windows läuft - dann ist geraten
    immer noch besser als gar nichts.
    """
    rueckfall = Path.home() / "Documents"
    if sys.platform != "win32":
        return rueckfall

    zeiger = ctypes.c_wchar_p()
    try:
        ergebnis = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(_guid(_FOLDERID_DOCUMENTS)), 0, None, ctypes.byref(zeiger)
        )
    except (OSError, AttributeError):  # pragma: no cover - sehr alte Systeme
        return rueckfall

    try:
        if ergebnis != 0 or not zeiger.value:
            return rueckfall
        return Path(zeiger.value)
    finally:
        if zeiger.value:
            ctypes.windll.ole32.CoTaskMemFree(zeiger)


def natter_ordner() -> Path:
    """`<Dokumente>/Natter` - dort sammelt Natter, was jemand anlegt.

    Wird nicht angelegt: wer nur nachsieht, wo etwas hingehört, soll
    keinen leeren Ordner hinterlassen. Angelegt wird beim Schreiben.
    """
    return dokumente_ordner() / NATTER_ORDNER


#: Unterordner von `natter_ordner()` für die Kopien der Beispiele.
BEISPIELKOPIEN_ORDNER = "Beispielprojekte"


def beispielkopien_ordner() -> Path:
    """`<Dokumente>/Natter/Beispielprojekte` - die Arbeitskopien der
    mitgelieferten Beispiele.

    Eine Ebene unter den eigenen Projekten: neun Beispiele zwischen
    zwei, drei eigenen Projekten machen den Ordner unübersichtlich, und
    wer sein Projekt sucht, soll nicht erst an ihnen vorbei müssen.
    """
    return natter_ordner() / BEISPIELKOPIEN_ORDNER
