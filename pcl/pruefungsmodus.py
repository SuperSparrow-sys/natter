"""Prüfungsmodus (M11, Abschnitt 6).

Vom Nutzer gefordert: Natter wird im Unterricht auch
in Leistungssituationen benutzt, und dann darf das Programm nicht die
halbe Aufgabe lösen.

Was er tut. Für vier Stunden ab dem Einschalten

* werden keine Lösungsvorschläge angezeigt. Die Fehlermeldung sagt
 weiterhin, was falsch ist – nur nicht mehr, woran es liegen könnte
* ist die Quelltexterzeugung aus dem Klassendiagramm und aus dem
 Struktogramm nicht möglich

Was er nicht tut. Alles andere bleibt. Die Diagramme lassen sich
weiter zeichnen, das Programm weiter starten und schrittweise
ausführen, die Meldungen bleiben deutsch und verständlich. Der Modus
nimmt Werkzeug weg, keine Bedienbarkeit.

Warum ein Endzeitpunkt und kein Schalter. Zwei Dinge sind
entscheidend, und beide folgen daraus:

1. Er muss einen Neustart von Natter überstehen. Ein Schalter im
 Speicher wäre mit einem Schließen und Öffnen ausgehebelt, und der
 Modus damit wertlos.
2. Er muss von selbst auslaufen. Niemand soll daran denken müssen,
 ihn wieder abzuschalten, und ein vergessener Modus darf keinen
 Schulrechner auf Dauer sperren.

Gespeichert wird deshalb, wann er vorbei ist – nicht, dass er an
ist.

Wo und wie gespeichert wird (Punkt 227). Bis 0.3.6 stand das Ende als
Ortszeit in der Ini der IDE. Ein gelöschter Wert, eine andere Zeitzone
(die unter Windows jedes Standardkonto einstellen darf) oder ein
Aufruf aus dem eigenen Programm beendeten den Modus sofort. Jetzt gilt:

* Beginn und Ende stehen als Sekunden seit 1970 in UTC. Die Zeitzone
  ändert daran nichts; die Uhr selbst zu stellen, braucht
  Verwaltungsrechte.
* Derselbe Vermerk steht an drei Stellen im Benutzerprofil: in der
  Ini, in einer Datei unter `%LOCALAPPDATA%\\Natter` und unter
  `HKEY_CURRENT_USER\\Software\\Natter`. Verwaltungsrechte braucht
  keine davon.
* Jeder Vermerk trägt einen Prüfwert (HMAC über Konto, Beginn und
  Ende). Ein von Hand geschriebener oder veränderter Vermerk zählt
  nicht. Das Konto ist die SID, die Windows für den Prozess nennt,
  keine Umgebungsvariable (Punkt 249).
* Der Modus läuft, solange eine gültige Stelle es sagt. Fehlt eine
  andere oder ist sie verändert, wird sie wiederhergestellt.
* Ein Ende, das weiter als vier Stunden nach dem Beginn liegt, gilt
  nur bis vier Stunden nach dem Beginn.
* Es gibt kein vorzeitiges Beenden, weder in der Oberfläche noch als
  Funktion. `pcl` gehört zu jedem Schülerprogramm, und eine Funktion
  zum Beenden wäre dort mit einer Zeile erreichbar. Ein zweiter
  Start, solange der Modus läuft, ändert nichts.

Was sich ohne Verwaltungsrechte grundsätzlich nicht verhindern lässt:
wer alle drei Stellen kennt und löscht, beendet den Modus. Das steht
so im Handbuch, Abschnitt Prüfungsmodus.
"""

from __future__ import annotations

import getpass
import hashlib
import hmac
import os
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Protocol

from PySide6.QtCore import QSettings

#: Wie lange der Modus läuft. Vier Stunden decken auch eine lange
#: Klausur ab, ohne den Rechner über den Schultag hinaus zu binden.
#: Zugleich die Obergrenze: länger läuft er nie.
DAUER = timedelta(hours=4)

#: Schlüssel in der Ini: der Vermerk mit Beginn, Ende und Prüfwert.
ENDE_SCHLUESSEL = "pruefung/ende"

#: Datei unter `%LOCALAPPDATA%\Natter` mit demselben Vermerk.
DATEINAME = "pruefungsmodus.txt"

#: Schlüssel und Wert unter `HKEY_CURRENT_USER` mit demselben Vermerk.
REGISTRY_SCHLUESSEL = r"Software\Natter\Pruefungsmodus"
REGISTRY_WERT = "Vermerk"

#: Schlüssel für den Prüfwert. Er steht im Quelltext und ist damit
#: kein Geheimnis. Er verhindert, dass ein Vermerk mit einem
#: Texteditor geändert oder in eine andere Stelle abgeschrieben wird,
#: nicht mehr.
_SCHLUESSEL = b"natter-pruefungsmodus/1"

#: Wie weit der Beginn in der Zukunft liegen darf, bevor der Vermerk
#: nicht mehr zählt. Etwas Spielraum für eine Uhr, die Windows nach
#: dem Einschalten nachstellt; mehr nicht, sonst liefe ein Modus mit
#: einem späteren Beginn länger als vier Stunden ab jetzt.
_SPIELRAUM = 5 * 60


def einstellungen() -> QSettings:
    """Dieselbe Ini wie der Rest der IDE – der Modus muss einen
    Neustart überstehen."""
    return QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Natter", "Natter-IDE"
    )


class Ablage(Protocol):
    """Eine Stelle, an der der Vermerk steht."""

    def lesen(self) -> str | None: ...

    def schreiben(self, text: str) -> None: ...


class IniAblage:
    def __init__(self, werte: QSettings) -> None:
        self.werte = werte

    def lesen(self) -> str | None:
        try:
            roh = self.werte.value(ENDE_SCHLUESSEL, "", type=str)
        except (TypeError, ValueError):
            return None
        return roh or None

    def schreiben(self, text: str) -> None:
        self.werte.setValue(ENDE_SCHLUESSEL, text)
        self.werte.sync()


class DateiAblage:
    def __init__(self, pfad: Path) -> None:
        self.pfad = Path(pfad)

    def lesen(self) -> str | None:
        try:
            return self.pfad.read_text(encoding="ascii").strip() or None
        except (OSError, ValueError):
            return None

    def schreiben(self, text: str) -> None:
        try:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            self.pfad.write_text(text, encoding="ascii")
        except OSError:
            pass


class RegistryAblage:
    """`HKEY_CURRENT_USER`, nur unter Windows. Anderswo bleibt die
    Stelle leer, und die beiden anderen tragen den Modus."""

    def lesen(self) -> str | None:
        if sys.platform != "win32":
            return None
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, REGISTRY_SCHLUESSEL
            ) as schluessel:
                wert, _ = winreg.QueryValueEx(schluessel, REGISTRY_WERT)
        except OSError:
            return None
        return wert if isinstance(wert, str) and wert else None

    def schreiben(self, text: str) -> None:
        if sys.platform != "win32":
            return
        import winreg

        try:
            with winreg.CreateKey(
                winreg.HKEY_CURRENT_USER, REGISTRY_SCHLUESSEL
            ) as schluessel:
                winreg.SetValueEx(
                    schluessel, REGISTRY_WERT, 0, winreg.REG_SZ, text
                )
        except OSError:
            pass


def _datei_pfad() -> Path:
    basis = os.environ.get("LOCALAPPDATA") or str(
        Path.home() / "AppData" / "Local"
    )
    return Path(basis) / "Natter" / DATEINAME


def _weitere_ablagen() -> list[Ablage]:
    """Die Stellen außer der Ini. Tests legen sie auf eigene um."""
    return [DateiAblage(_datei_pfad()), RegistryAblage()]


def _ablagen(werte: QSettings | None) -> list[Ablage]:
    return [IniAblage(werte or einstellungen()), *_weitere_ablagen()]


def _konto_sid() -> str:
    """Die SID des Kontos, unter dem Natter läuft, von Windows erfragt.

    Leer, wenn Windows sie nicht herausgibt. Sie kommt aus dem
    Zugriffstoken des Prozesses und lässt sich ohne Verwaltungsrechte
    nicht ändern.
    """
    import ctypes
    from ctypes import wintypes

    advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    advapi32.OpenProcessToken.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)
    ]
    advapi32.GetTokenInformation.argtypes = [
        wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    advapi32.ConvertSidToStringSidW.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(wintypes.LPWSTR)
    ]
    token_query, token_user = 0x0008, 1

    token = wintypes.HANDLE()
    if not advapi32.OpenProcessToken(
        kernel32.GetCurrentProcess(), token_query, ctypes.byref(token)
    ):
        return ""
    try:
        groesse = wintypes.DWORD()
        advapi32.GetTokenInformation(
            token, token_user, None, 0, ctypes.byref(groesse)
        )
        if not groesse.value:
            return ""
        puffer = ctypes.create_string_buffer(groesse.value)
        if not advapi32.GetTokenInformation(
            token, token_user, puffer, groesse, ctypes.byref(groesse)
        ):
            return ""
        # TOKEN_USER beginnt mit SID_AND_ATTRIBUTES, dessen erstes
        # Feld der Zeiger auf die SID ist.
        sid = ctypes.c_void_p.from_buffer(puffer).value
        text = wintypes.LPWSTR()
        if not advapi32.ConvertSidToStringSidW(sid, ctypes.byref(text)):
            return ""
        try:
            return text.value or ""
        finally:
            kernel32.LocalFree(text)
    finally:
        kernel32.CloseHandle(token)


def _konto() -> str:
    """Das Konto, an das der Prüfwert gebunden ist (Punkt 249).

    Bis 0.3.6 kam es aus `getpass.getuser()`, und das liest zuerst
    `LOGNAME`, `USER`, `LNAME` und `USERNAME`. Eine davon kann jedes
    Konto für sich setzen, und mit einem anderen Wert passte der
    Prüfwert nirgends mehr: der Modus war aus. Deshalb zählt unter
    Windows nur die SID aus dem Zugriffstoken, anderswo die
    Benutzernummer des Prozesses. Beides liest keine
    Umgebungsvariable.
    """
    try:
        if sys.platform == "win32":
            return _konto_sid()
        return str(os.getuid())
    except Exception:  # noqa: BLE001 - ohne Konto bleibt es beim Leeren
        return ""


def _pruefwert(beginn: int, ende: int, konto: str | None = None) -> str:
    konto = _konto() if konto is None else konto
    text = f"{konto}|{beginn}|{ende}".encode()
    return hmac.new(_SCHLUESSEL, text, hashlib.sha256).hexdigest()


def _konto_bis_036() -> str | None:
    """Das Konto, wie 0.3.6 und früher es in den Prüfwert rechneten.

    Nur, damit ein Modus, der beim Update auf diese Fassung läuft,
    weiterläuft. Ein so gelesener Vermerk wird sofort in der neuen
    Form an alle Stellen geschrieben; danach hängt nichts mehr an der
    Umgebung. Einen Modus beenden kann dieser Weg nicht: er macht
    höchstens einen Vermerk mehr gültig, keinen weniger.
    """
    try:
        return getpass.getuser()
    except Exception:  # noqa: BLE001 - dann gibt es keinen alten Vermerk
        return None


def _vermerk(beginn: int, ende: int) -> str:
    return f"{beginn}|{ende}|{_pruefwert(beginn, ende)}"


@dataclass(frozen=True)
class _Zeitraum:
    beginn: int
    ende: int


def _lesen(text: str | None) -> _Zeitraum | None:
    """Der Zeitraum aus einem Vermerk, oder `None`, wenn er fehlt, sich
    nicht lesen lässt oder der Prüfwert nicht stimmt."""
    if not text:
        return None
    teile = text.strip().split("|")
    if len(teile) != 3:
        return None
    try:
        beginn, ende = int(teile[0]), int(teile[1])
    except ValueError:
        return None
    if not hmac.compare_digest(teile[2], _pruefwert(beginn, ende)):
        alt = _konto_bis_036()
        if alt is None or not hmac.compare_digest(
            teile[2], _pruefwert(beginn, ende, alt)
        ):
            return None
    # Nie länger als vier Stunden ab dem Beginn, auch wenn der Vermerk
    # etwas anderes sagt.
    return _Zeitraum(beginn, min(ende, beginn + int(DAUER.total_seconds())))


def _epoche(jetzt: datetime | float | None) -> float:
    """`jetzt` als Sekunden seit 1970 (UTC). Ein `datetime` ohne
    Zeitzone gilt als Ortszeit."""
    if jetzt is None:
        return time.time()
    if isinstance(jetzt, datetime):
        return jetzt.timestamp()
    return float(jetzt)


def _aktiver_zeitraum(
    werte: QSettings | None, jetzt: datetime | float | None
) -> _Zeitraum | None:
    """Der Zeitraum, der gerade gilt, und stellt fehlende oder
    veränderte Stellen wieder her. `None`, wenn keine Prüfung läuft."""
    sekunden = _epoche(jetzt)
    ablagen = _ablagen(werte)
    gelesen = [(ablage, ablage.lesen()) for ablage in ablagen]
    aktiv: _Zeitraum | None = None
    for _, roh in gelesen:
        zeitraum = _lesen(roh)
        if zeitraum is None:
            continue
        if zeitraum.beginn - _SPIELRAUM > sekunden:
            continue
        if sekunden < zeitraum.ende and (
            aktiv is None or zeitraum.ende > aktiv.ende
        ):
            aktiv = zeitraum
    if aktiv is None:
        return None
    # Immer in der Form dieser Fassung zurückschreiben: ein Vermerk
    # aus 0.3.6 hängt noch an einer Umgebungsvariablen (Punkt 249).
    roh_aktiv = _vermerk(aktiv.beginn, aktiv.ende)
    for ablage, roh in gelesen:
        if roh != roh_aktiv:
            ablage.schreiben(roh_aktiv)
    return aktiv


def ende(
    werte: QSettings | None = None, jetzt: datetime | float | None = None
) -> datetime | None:
    """Wann der laufende Prüfungsmodus ausläuft (in UTC), oder `None`."""
    zeitraum = _aktiver_zeitraum(werte, jetzt)
    if zeitraum is None:
        return None
    return datetime.fromtimestamp(zeitraum.ende, UTC)


def laeuft(
    werte: QSettings | None = None, jetzt: datetime | float | None = None
) -> bool:
    """Ob gerade eine Prüfung läuft."""
    return _aktiver_zeitraum(werte, jetzt) is not None


def restzeit(
    werte: QSettings | None = None, jetzt: datetime | float | None = None
) -> timedelta | None:
    """Wie lange noch – `None`, wenn kein Prüfungsmodus läuft."""
    zeitraum = _aktiver_zeitraum(werte, jetzt)
    if zeitraum is None:
        return None
    verbleibend = zeitraum.ende - _epoche(jetzt)
    return timedelta(seconds=verbleibend) if verbleibend > 0 else None


def starten(
    werte: QSettings | None = None,
    dauer: timedelta = DAUER,
    jetzt: datetime | float | None = None,
) -> datetime:
    """Startet den Prüfungsmodus und gibt seinen Endzeitpunkt (UTC)
    zurück.

    Läuft er schon, bleibt es bei dem bisherigen Ende: ein zweiter
    Start könnte ihn sonst verlängern oder, mit einer kürzeren
    `dauer`, verkürzen. `dauer` ist höchstens `DAUER`.
    """
    laufend = _aktiver_zeitraum(werte, jetzt)
    if laufend is not None:
        return datetime.fromtimestamp(laufend.ende, UTC)
    beginn = int(_epoche(jetzt))
    sekunden = min(dauer, DAUER).total_seconds()
    # Auf ganze Sekunden, aufgerundet: ein Test mit einer Dauer von
    # Bruchteilen einer Sekunde soll nicht schon beim Start vorbei sein.
    schluss = beginn + max(1, int(-(-sekunden // 1)))
    vermerk = _vermerk(beginn, schluss)
    for ablage in _ablagen(werte):
        ablage.schreiben(vermerk)
    return datetime.fromtimestamp(schluss, UTC)


def restzeit_text(
    werte: QSettings | None = None, jetzt: datetime | float | None = None
) -> str:
    """Für die Statusleiste: „Prüfungsmodus – noch 2:45 h“.

    Leer, wenn keine Prüfung läuft. Wer nicht sieht, dass der Modus an
    ist, sucht den Fehler bei sich.
    """
    verbleibend = restzeit(werte, jetzt)
    if verbleibend is None:
        return ""
    minuten = int(verbleibend.total_seconds() // 60)
    return f"Prüfungsmodus – noch {minuten // 60}:{minuten % 60:02d} h"


#: Einheitlicher Hinweis an allem, was der Prüfungsmodus sperrt. Ein
#: spurlos verschwundener Menüeintrag wäre verwirrender als ein
#: erklärter.
GESPERRT_HINWEIS = (
    "Während des Prüfungsmodus nicht verfügbar. Er läuft nach vier "
    "Stunden von selbst aus."
)
