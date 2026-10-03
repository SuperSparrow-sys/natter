"""Sicherung ungespeicherter Änderungen eines Projekts (Punkt 344).

Beim Abmelden fragt Natter, ob gespeichert werden soll. Windows wartet
darauf nur wenige Sekunden und bietet dann „Trotzdem abmelden“ an.
Wer das drückt, etwa am Stundenende, verlor bis 0.4.0 jeden
ungespeicherten Text. Natter legt deshalb vor der Frage, und
außerdem wenige Sekunden nach jeder Änderung an einer Unit und alle
zwei Minuten, solange etwas ungespeichert ist, eine Sicherung in den
Projektordner:

    Ampel.natter-sicherung

Sie ist JSON im Format `natter-sicherung/2`
(`schemas/natter-sicherung.schema.json`) und hält je geändertem
Editor oder Diagramm den Pfad relativ zum Projektordner, den
ungespeicherten Inhalt und den Stand der Datei auf der Platte, auf dem
dieser Inhalt beruht. Beim nächsten Öffnen des Projekts bietet Natter
sie an. An der eigenen Endung erkennen Projekt-Explorer, Abgabe-ZIP,
Exe-Export und Aufgabenkopie die Datei und lassen sie aus.

Die Datei liegt im Projektordner und nicht unter `%LOCALAPPDATA%`:
dort ginge sie auf Rechnern verloren, deren Profil beim Abmelden
gelöscht wird, und am nächsten Rechner käme das Projekt ohne sie an.
Der Name des Projekts steht davor, damit eine Lehrkraft im
Windows-Explorer sieht, wozu die Datei gehört.

Ein Projekt kann in zwei Natter-Fenstern zugleich offen sein, auch an
zwei Rechnern (Punkte 400 und 406). Die Datei ist deshalb in Anteile
geteilt, einen je Fenster, und jeder Anteil nennt seine `Herkunft`:
Rechner, Konto, Prozessnummer und Startzeit des Prozesses und eine
Kennung des Fensters. Ein Fenster liest die Datei vor jedem Schreiben
neu und ersetzt oder entfernt nur seinen eigenen Anteil
(`anteil_ersetzen`). Beim Öffnen des Projekts bietet Natter die
Anteile an, deren Fenster nicht mehr läuft (`laeuft`).

Eine Datei im alten Format `natter-sicherung/1` wird weiter gelesen;
sie gilt als ein Anteil ohne Herkunft.

Dieses Modul kennt kein Qt; was in den Editoren steht, sammelt das
Hauptfenster.
"""

from __future__ import annotations

import contextlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath

from ide.atomar import atomar_schreiben
from ide.pfade import daten_ordner
from ide.project import sperre
from ide.schema import json_datei_lesen, schema_fehler
from ide.schema import pruefen as schema_pruefen

#: Endung der Sicherungsdatei, mit Punkt.
ENDUNG = ".natter-sicherung"

FORMAT = "natter-sicherung/2"
#: Wird gelesen, nicht mehr geschrieben.
FORMAT_1 = "natter-sicherung/1"

_SCHEMA = json.loads(
    (daten_ordner("schemas") / "natter-sicherung.schema.json").read_text(
        encoding="utf-8"
    )
)


@dataclass(frozen=True)
class Eintrag:
    """Eine gesicherte Datei.

    `stand` ist die Kennung aus `ide.dateistand` („Änderungszeit in ns:
    Größe“), leer, wenn die Datei beim Sichern fehlte."""

    pfad: str
    art: str
    text: str
    stand: str


@dataclass(frozen=True)
class Herkunft:
    """Das Fenster, das einen Anteil geschrieben hat.

    Rechner, Prozessnummer und Startzeit reichen, um an diesem Rechner
    nachzusehen, ob der Prozess noch läuft; die Startzeit steht dabei,
    weil Windows Prozessnummern wieder vergibt. Die `kennung`
    unterscheidet zwei Fenster in einem Prozess."""

    rechner: str
    konto: str
    pid: int
    start: int
    kennung: str


@dataclass(frozen=True)
class Anteil:
    """Was ein Fenster gesichert hat. `herkunft` ist `None` bei einer
    Sicherung im Format `natter-sicherung/1`."""

    herkunft: Herkunft | None
    zeit: datetime
    eintraege: tuple[Eintrag, ...]


@dataclass(frozen=True)
class Sicherung:
    anteile: tuple[Anteil, ...]

    @property
    def eintraege(self) -> tuple[Eintrag, ...]:
        """Die Einträge aller Anteile."""
        return tuple(e for a in self.anteile for e in a.eintraege)


#: Die Kennungen der Fenster dieses Prozesses, die noch offen sind.
#: An ihnen erkennt `laeuft` einen Anteil aus dem eigenen Prozess, der
#: zu einem noch offenen Fenster gehört.
_OFFENE_FENSTER: set[str] = set()


def herkunft_anlegen() -> Herkunft:
    """Eine neue Herkunft für ein Fenster dieses Prozesses. Das Fenster
    gilt als offen, bis `fenster_geschlossen` es abmeldet."""
    pid = os.getpid()
    herkunft = Herkunft(
        rechner=sperre.rechnername(),
        konto=sperre.kontoname(),
        pid=pid,
        start=sperre._startzeit(pid) or 0,
        kennung=uuid.uuid4().hex,
    )
    _OFFENE_FENSTER.add(herkunft.kennung)
    return herkunft


def fenster_geschlossen(herkunft: Herkunft) -> None:
    _OFFENE_FENSTER.discard(herkunft.kennung)


def _gleich(a: str, b: str) -> bool:
    return a.casefold() == b.casefold()


def laeuft(herkunft: Herkunft | None, ordner: Path) -> bool:
    """Ob das Fenster, das einen Anteil geschrieben hat, vermutlich
    noch mit dem Projekt in `ordner` arbeitet. Sein Anteil wird dann
    beim Öffnen nicht angeboten.

    An diesem Rechner lässt sich das am Prozess nachsehen. An einem
    anderen nicht; dort zählt ein Anteil aus dem eigenen Konto nie als
    laufend: wer sich hier angemeldet hat, arbeitet in aller Regel
    nicht mehr am anderen Rechner (Punkt 400). Der Anteil eines
    anderen Kontos zählt, solange die Sperrdatei jenen Rechner als
    Besitzer nennt, also höchstens `sperre.ZEITGRENZE` nach der
    letzten Erneuerung. Ohne Herkunft entscheidet die Sperrdatei
    allein, mit derselben Ausnahme für das eigene Konto."""
    if herkunft is None:
        besitzer = sperre.anderer_besitzer(ordner)
        return besitzer is not None and not (
            besitzer.anderer_rechner
            and bool(besitzer.konto)
            and _gleich(besitzer.konto, sperre.kontoname())
        )
    if _gleich(herkunft.rechner, sperre.rechnername()):
        if herkunft.pid == os.getpid():
            eigener_start = sperre._startzeit(herkunft.pid) or 0
            return (
                herkunft.kennung in _OFFENE_FENSTER
                and (not herkunft.start or herkunft.start == eigener_start)
            )
        laufend = sperre._startzeit(herkunft.pid)
        if laufend is None:
            return False
        return not (herkunft.start and laufend and laufend != herkunft.start)
    if herkunft.konto and _gleich(herkunft.konto, sperre.kontoname()):
        return False
    besitzer = sperre.anderer_besitzer(ordner)
    return (
        besitzer is not None and besitzer.anderer_rechner
        and _gleich(besitzer.rechner, herkunft.rechner)
    )


def pfad_fuer(ordner: Path, name: str) -> Path:
    """Die Sicherungsdatei des Projekts `name` im Ordner `ordner`."""
    return Path(ordner) / f"{name}{ENDUNG}"


def ist_sicherung(pfad: Path | str) -> bool:
    return Path(pfad).suffix.lower() == ENDUNG


def _stand_als_daten(stand: str) -> dict[str, int] | None:
    try:
        zeit, groesse = stand.split(":")
        return {"mtime_ns": int(zeit), "size": int(groesse)}
    except ValueError:
        return None


def _dateien_als_daten(eintraege: tuple[Eintrag, ...]) -> list[dict]:
    return [
        {
            "path": eintrag.pfad,
            "kind": eintrag.art,
            "text": eintrag.text,
            "disk": _stand_als_daten(eintrag.stand),
        }
        for eintrag in eintraege
    ]


def _herkunft_als_daten(herkunft: Herkunft | None) -> dict | None:
    if herkunft is None:
        return None
    return {
        "computer": herkunft.rechner,
        "account": herkunft.konto,
        "pid": herkunft.pid,
        "start": herkunft.start,
        "id": herkunft.kennung,
    }


def _schreiben(pfad: Path, anteile: list[Anteil]) -> None:
    daten = {
        "format": FORMAT,
        "parts": [
            {
                "window": _herkunft_als_daten(anteil.herkunft),
                "saved": anteil.zeit.isoformat(timespec="seconds"),
                "files": _dateien_als_daten(anteil.eintraege),
            }
            for anteil in anteile
        ],
    }
    atomar_schreiben(
        pfad, json.dumps(daten, indent=2, ensure_ascii=False) + "\n"
    )


def schreiben(
    pfad: Path,
    eintraege: list[Eintrag],
    herkunft: Herkunft | None = None,
    zeit: datetime | None = None,
) -> None:
    """Schreibt eine Sicherung mit einem einzigen Anteil atomar nach
    `pfad` und ersetzt dabei alles, was dort lag. Für Tests und für
    eine neue Datei; ein Fenster nimmt `anteil_ersetzen`."""
    zeit = zeit or datetime.now().astimezone()
    _schreiben(pfad, [Anteil(herkunft, zeit, tuple(eintraege))])


def anteil_ersetzen(
    pfad: Path,
    herkunft: Herkunft,
    eintraege: list[Eintrag],
    zeit: datetime | None = None,
) -> None:
    """Ersetzt den Anteil von `herkunft` in der Sicherung durch
    `eintraege` und lässt die Anteile anderer Fenster stehen. Ohne
    Einträge verschwindet der eigene Anteil, und ohne Anteile die
    Datei.

    Die Datei wird dafür neu gelesen, auch wenn dieses Fenster sie
    eben erst geschrieben hat: inzwischen kann ein anderes Fenster
    seinen Anteil ergänzt haben. Steht der eigene Anteil schon so da,
    wird nichts geschrieben. Eine Datei, die sich nicht lesen lässt,
    wird mit einem Anteil ersetzt und beim Entfernen stehen gelassen.
    Wirft `OSError`, wenn das Schreiben scheitert; die vorige Datei
    bleibt dann unverändert.

    Lesen und Schreiben sind zwei Schritte. Schreiben zwei Fenster im
    selben Augenblick, kann der Anteil des einen fehlen, bis es das
    nächste Mal sichert: es findet dann seinen Anteil nicht vor und
    schreibt ihn wieder."""
    fremde: list[Anteil] = []
    eigener: Anteil | None = None
    lesbar = True
    if pfad.exists():
        try:
            vorhanden = lesen(pfad)
        except (OSError, ValueError, schema_fehler()):
            lesbar = False
        else:
            for anteil in vorhanden.anteile:
                if anteil.herkunft == herkunft:
                    eigener = anteil
                else:
                    fremde.append(anteil)
    if not eintraege:
        if eigener is None or not lesbar:
            return
        if not fremde:
            entfernen(pfad)
            return
        _schreiben(pfad, fremde)
        return
    if eigener is not None and list(eigener.eintraege) == eintraege:
        return
    zeit = zeit or datetime.now().astimezone()
    _schreiben(pfad, [*fremde, Anteil(herkunft, zeit, tuple(eintraege))])


def anteile_entfernen(pfad: Path, weg: list[Herkunft | None]) -> None:
    """Entfernt die Anteile, deren Herkunft in `weg` steht, etwa nach
    dem Wiederherstellen oder Verwerfen beim Öffnen. Die übrigen
    bleiben; bleibt keiner, verschwindet die Datei. Scheitert das,
    bleibt die Datei, wie sie ist, und wird beim nächsten Öffnen noch
    einmal angeboten."""
    try:
        vorhanden = lesen(pfad)
    except (OSError, ValueError, schema_fehler()):
        return
    rest = [a for a in vorhanden.anteile if a.herkunft not in weg]
    if len(rest) == len(vorhanden.anteile):
        return
    if not rest:
        entfernen(pfad)
        return
    with contextlib.suppress(OSError):
        _schreiben(pfad, rest)



def _zeit_lesen(text: str) -> datetime:
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(
            f"Der Zeitpunkt „{text}“ ist keine gültige Angabe."
        ) from None


def _eintraege_lesen(dateien: list[dict]) -> tuple[Eintrag, ...]:
    eintraege = []
    for datei in dateien:
        teile = PurePosixPath(datei["path"]).parts
        if ".." in teile:
            raise ValueError(
                f"Der Pfad „{datei['path']}“ führt aus dem Projektordner "
                "hinaus."
            )
        stand = datei["disk"]
        eintraege.append(Eintrag(
            pfad=datei["path"],
            art=datei["kind"],
            text=datei["text"],
            stand=(
                f"{stand['mtime_ns']}:{stand['size']}" if stand else ""
            ),
        ))
    return tuple(eintraege)


def lesen(pfad: Path) -> Sicherung:
    """Liest und prüft eine Sicherung im Format `natter-sicherung/2`
    oder `/1`.

    Wirft `OSError`, `ValueError` (auch `json.JSONDecodeError` und
    `UnicodeDecodeError`) oder den Fehler aus `schema_fehler()`;
    `fehler_beschreiben()` macht daraus einen deutschen Satz. Ein Pfad,
    der aus dem Projektordner hinausführt, gilt als Fehler: über ihn
    schriebe das nächste Speichern eine fremde Datei."""
    daten = json_datei_lesen(pfad)
    schema_pruefen(daten, _SCHEMA)
    if daten["format"] == FORMAT_1:
        return Sicherung(anteile=(Anteil(
            herkunft=None,
            zeit=_zeit_lesen(daten["saved"]),
            eintraege=_eintraege_lesen(daten["files"]),
        ),))
    anteile = []
    for teil in daten["parts"]:
        fenster = teil["window"]
        anteile.append(Anteil(
            herkunft=None if fenster is None else Herkunft(
                rechner=fenster["computer"],
                konto=fenster["account"],
                pid=fenster["pid"],
                start=fenster["start"],
                kennung=fenster["id"],
            ),
            zeit=_zeit_lesen(teil["saved"]),
            eintraege=_eintraege_lesen(teil["files"]),
        ))
    return Sicherung(anteile=tuple(anteile))


def entfernen(pfad: Path) -> None:
    """Löscht die Sicherung. Lässt sie sich nicht löschen, bleibt sie
    liegen und wird beim nächsten Öffnen noch einmal angeboten; ein
    Fenster deswegen hälfe niemandem."""
    with contextlib.suppress(OSError):
        Path(pfad).unlink(missing_ok=True)


def zeit_text(zeit: datetime) -> str:
    """„29.09.2026, 14:05 Uhr“, in der Zeitzone dieses Rechners."""
    if zeit.tzinfo is not None:
        zeit = zeit.astimezone()
    return zeit.strftime("%d.%m.%Y, %H:%M Uhr")


def frage_text(
    projekt: str,
    zeit: datetime,
    dateien: list[tuple[str, bool]],
) -> str:
    """Der Text der Frage beim Öffnen. `dateien` nennt je Datei den
    Pfad und ob sie seit der Sicherung auf der Platte geändert wurde."""
    zeilen = []
    for pfad, seither_geaendert in dateien:
        zusatz = (
            " (seit der Sicherung auf der Platte geändert)"
            if seither_geaendert else ""
        )
        zeilen.append(f"  {pfad}{zusatz}")
    liste = "\n".join(zeilen)
    return (
        f"Für das Projekt „{projekt}“ liegt eine Sicherung "
        f"ungespeicherter Änderungen vom {zeit_text(zeit)} vor. "
        "Natter wurde damals beendet, ohne dass diese Dateien "
        f"gespeichert wurden:\n\n{liste}\n\n"
        "„Wiederherstellen“ öffnet sie mit dem gesicherten Inhalt als "
        "ungespeicherte Änderung; in die Datei kommt er erst mit "
        "„Speichern“. „Verwerfen“ löscht die Sicherung, und die "
        "Dateien bleiben, wie sie auf der Platte sind."
    )
