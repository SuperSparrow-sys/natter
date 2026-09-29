"""Pfade: mitgelieferte Datenordner der IDE und der Ort, an dem die
Arbeit der Schülerin liegt.

Der erste Teil löst Datenordner (`schemas/`, `templates/` …) auf,
die zur Laufzeit gelesen werden statt importiert zu werden. Sie liegen
eine Ebene über dem Paket `ide`: im Entwicklungsbaum ist das die
Projektwurzel, in der Installation `Lib/site-packages`, wohin
`tools/ide_paketieren.py` sie kopiert. Eine einzige Quelle für alle
Stellen, die solche Dateien lesen, statt je einer eigenen Kopie.

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
import re
import sys
import tempfile
from ctypes import wintypes
from pathlib import Path

_PROJEKT_WURZEL = Path(__file__).resolve().parent.parent


def daten_ordner(name: str) -> Path:
    """`name` (z. B. `"schemas"`) eine Ebene über dem Paket `ide`."""
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


def _bekannter_ordner(kennung: str, rueckfall: Path) -> Path:
    """Der Ordner mit der Windows-Kennung `kennung`, so wie Windows ihn
    kennt, auch wenn er umgeleitet ist. `rueckfall`, wenn die Abfrage
    nichts liefert oder das Programm nicht unter Windows läuft."""
    if sys.platform != "win32":
        return rueckfall

    zeiger = ctypes.c_wchar_p()
    try:
        ergebnis = ctypes.windll.shell32.SHGetKnownFolderPath(
            ctypes.byref(_guid(kennung)), 0, None, ctypes.byref(zeiger)
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


def dokumente_ordner() -> Path:
    """Der Dokumente-Ordner, wie Windows ihn kennt.

    Fällt auf `~/Documents` zurück, wenn die Abfrage nichts liefert
    oder das Programm nicht unter Windows läuft - dann ist geraten
    immer noch besser als gar nichts.
    """
    return _bekannter_ordner(
        _FOLDERID_DOCUMENTS, Path.home() / "Documents"
    )


def temp_ordner() -> Path:
    """Der Ordner für temporäre Dateien (`%TEMP%`). Dorthin legt der
    Explorer eine Datei, die jemand direkt in einer ZIP-Datei
    doppelklickt, etwa nach `Temp1_Ampel.zip\\Ampel`."""
    return Path(tempfile.gettempdir())


#: Ordner, in die ein Packprogramm ein Archiv vorläufig entpackt,
#: wenn eine Datei darin direkt doppelgeklickt wird: der Explorer nach
#: `Temp1_Ampel.zip` (neuere Fassungen von Windows auch `.7z`, `.rar`
#: und `.tar`), 7-Zip nach `7zO4A1B2C3D` (`7zE…` beim Herausziehen)
#: und WinRAR nach `Rar$DIa12345.6789` (`Rar$EX…`, `Rar$DR…`).
#: 7-Zip ist an vielen Schulrechnern für ZIP-Dateien eingetragen
#: (Punkt 402).
_VORLAEUFIG_ENTPACKT = re.compile(
    r"temp\d+_.+\.(zip|7z|rar|tar|tgz|gz|bz2|xz)"
    r"|7z[oe][0-9a-f]+"
    r"|rar\$(di|ex|dr).+",
    re.IGNORECASE,
)


def vorlaeufig_entpackt(pfad: Path | str) -> bool:
    """Ob `pfad` in einem Ordner liegt, in den der Explorer, 7-Zip
    oder WinRAR ein Archiv nur vorläufig entpackt hat, etwa
    `%TEMP%\\Temp1_Ampel.zip\\Ampel` (Punkte 391, 402).

    Das geschieht, wenn jemand die `.natter` direkt in der ZIP-Datei
    doppelklickt. Das Packprogramm holt dann oft nur diese eine Datei
    heraus und räumt den Ordner später wieder weg, 7-Zip und WinRAR
    schon beim Schließen des Archivs; was dort gespeichert wird, ist
    danach verloren."""
    ziel = einheitlicher_pfad(pfad)
    temp = einheitlicher_pfad(temp_ordner())
    if not ziel.is_relative_to(temp):
        return False
    return any(
        _VORLAEUFIG_ENTPACKT.fullmatch(teil)
        for teil in ziel.relative_to(temp).parts
    )


def natter_ordner() -> Path:
    """`<Dokumente>/Natter` - dort sammelt Natter, was jemand anlegt.

    Wird nicht angelegt: wer nur nachsieht, wo etwas hingehört, soll
    keinen leeren Ordner hinterlassen. Angelegt wird beim Schreiben.
    """
    return dokumente_ordner() / NATTER_ORDNER


def dialog_startordner(*kandidaten: Path | str | None) -> Path:
    """Der Ordner, in dem ein Datei-Dialog beginnt.

    Der erste Kandidat, der als Ordner existiert, sonst
    `natter_ordner()`, sonst die Dokumente. Ohne Startordner zeigt ein
    Dialog den Arbeitsordner des Prozesses, und den setzt der
    Startmenü-Eintrag auf den Programmordner von Natter - dort sucht
    niemand seine Projekte (Punkt 408). Ein Ordner, den es nicht
    gibt, führte zum selben Ergebnis, deshalb die Prüfung.
    """
    for kandidat in (*kandidaten, natter_ordner()):
        if kandidat is None or kandidat == "":
            continue
        pfad = Path(kandidat)
        if pfad.is_dir():
            return pfad
    return dokumente_ordner()


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


def einheitlicher_pfad(pfad: Path | str) -> Path:
    """`pfad` in der einen Form, in der Natter Ordner speichert und
    vergleicht: in „Zuletzt geöffnet“, in `.natter-quelle` einer
    kopierten Aufgabe und in der Sperrdatei.

    Ein Tauschordner ist an Schulen meist als Laufwerk verbunden
    (`K:\\Ampel`) und zugleich über den Netzpfad erreichbar
    (`\\\\server\\tausch\\Ampel`). `resolve()` macht aus dem Laufwerk
    den Netzpfad. Bis Punkt 364 tat das nur ein Teil der Stellen, und
    dieselbe Aufgabe hatte zwei Herkunftsangaben: die eigene Kopie
    wurde nicht wiedererkannt, und es entstand „Ampel 2“. Ist der Pfad
    gerade nicht auflösbar, bleibt es beim absoluten Pfad."""
    try:
        return Path(pfad).resolve()
    except OSError:
        return Path(pfad).absolute()
