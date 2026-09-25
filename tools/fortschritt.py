"""Fortschrittsanzeige für den Bau der Auslieferung.

Der Bau dauert eine halbe bis eine Dreiviertelstunde, und fast die
ganze Zeit stand in der Konsole dieselbe Zeile. Ob er hing oder
arbeitete, war nicht zu sehen.

Die Anzeige hält drei Zeilen am unteren Rand der Konsole fest:

    Gesamt   ████████████████░░░░░░░░░░░░░░░░   42 %  12:31  noch ~17 min
    [4/11]   ███████████████████▍░░░░░░░░░░░░   61 %  pytest  2512/4107 Tests
             tests/test_hauptfenster_designer.py

Der obere Balken zeigt den ganzen Bau und die Restzeit. Der mittlere
zeigt den laufenden Schritt: grün, wo der Schritt selbst zählt (Tests,
signierte Dateien, gepackte Dateien), gelb und mit „≈" davor, wo nur
die Dauer des letzten Laufs eine Schätzung hergibt. Die dritte Zeile
nennt, woran gerade gearbeitet wird. Darüber laufen die fertigen
Schritte mit ihrer Dauer durch.

Die Schätzungen stammen aus dem letzten erfolgreichen Lauf und liegen
in `build/bau-cache/bauzeiten.json`. Fehlt die Datei, gelten die
Werte aus `_VORGABE_SEKUNDEN`, gemessen im September 2026.

Ist die Ausgabe keine Konsole, sondern eine Datei oder ein Rohr, gibt
es keine Balken, sondern Zeilen - ein Protokoll voller
Steuerzeichen liest niemand.

Reines Entwicklungswerkzeug, ohne Abhängigkeit über die
Standardbibliothek hinaus.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

#: Wie lange die Schritte beim Bau von 0.3.1 gedauert haben. Nur ein
#: Ausgangswert: nach dem ersten Lauf gilt die gemessene Dauer.
_VORGABE_SEKUNDEN: dict[str, float] = {
    "1": 2,
    "2": 1,
    "3": 5,
    "4": 812,
    "5": 600,
    "6": 25,
    "7": 30,
    "8": 900,
    "9": 5,
    "10": 90,
    "11": 60,
}

#: Farben als ANSI-Folgen. Windows 10 und neuer verstehen sie, sobald
#: die Konsole in den VT-Modus geschaltet ist (`_vt_einschalten`).
_GRUEN = "\x1b[32m"
_GELB = "\x1b[33m"
_ROT = "\x1b[31m"
_BLAU = "\x1b[36m"
_GRAU = "\x1b[90m"
_FETT = "\x1b[1m"
_AUS = "\x1b[0m"

#: Achtel-Blöcke für Balken, die sich auch zwischen zwei Zeichen
#: bewegen. Ein Balken aus 40 ganzen Zeichen springt nur alle 2,5 %.
_ACHTEL = " ▏▎▍▌▋▊▉"


def _vt_einschalten() -> bool:
    """Schaltet die Windows-Konsole auf ANSI-Folgen um. Liefert, ob das
    geklappt hat - ältere Konsolen bekommen dann einfache Zeilen."""
    if sys.platform != "win32":
        return True
    try:
        import ctypes

        kernel = ctypes.windll.kernel32
        griff = kernel.GetStdHandle(-11)
        modus = ctypes.c_uint32()
        if not kernel.GetConsoleMode(griff, ctypes.byref(modus)):
            return False
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING
        return bool(kernel.SetConsoleMode(griff, modus.value | 0x0004))
    except (OSError, AttributeError):
        return False


def _balken(anteil: float, breite: int, farbe: str) -> str:
    anteil = min(max(anteil, 0.0), 1.0)
    achtel = int(anteil * breite * 8)
    voll, rest = divmod(achtel, 8)
    teil = _ACHTEL[rest] if voll < breite and rest else ""
    leer = breite - voll - len(teil)
    return f"{farbe}{'█' * voll}{teil}{_GRAU}{'░' * leer}{_AUS}"


def _dauer(sekunden: float) -> str:
    sekunden = int(sekunden)
    if sekunden >= 3600:
        return f"{sekunden // 3600}:{sekunden // 60 % 60:02d}:{sekunden % 60:02d}"
    return f"{sekunden // 60:2d}:{sekunden % 60:02d}"


def _kurz(text: str, breite: int) -> str:
    return text if len(text) <= breite else "…" + text[-(breite - 1):]


class Bauzeiten:
    """Die Dauer der Schritte aus dem letzten Lauf, als Schätzung für
    den nächsten."""

    def __init__(self, datei: Path) -> None:
        self._datei = datei
        self.werte: dict[str, float] = dict(_VORGABE_SEKUNDEN)
        try:
            gelesen = json.loads(datei.read_text(encoding="utf-8"))
            self.werte.update({str(k): float(v) for k, v in gelesen.items()})
        except (OSError, ValueError, AttributeError):
            pass

    def merken(self, schluessel: str, sekunden: float) -> None:
        """Schreibt sofort, nicht erst am Ende: bricht der Bau in
        Schritt 8 ab, sind die Zeiten der ersten sieben trotzdem
        gemessen."""
        self.werte[schluessel] = round(sekunden, 1)
        try:
            self._datei.parent.mkdir(parents=True, exist_ok=True)
            self._datei.write_text(
                json.dumps(self.werte, indent=1, sort_keys=True), encoding="utf-8"
            )
        except OSError:
            pass


class Anzeige:
    """Die Balken am unteren Rand und das Protokoll dahinter.

    Jede Zeile, die ein Schritt ausgibt, geht ins Protokoll. Auf dem
    Bildschirm erscheinen nur die Zeilen, die ein Schritt selbst als
    Ergebnis meldet, und die letzte Rohzeile als Hinweis, woran er
    gerade arbeitet.
    """

    _HOEHE = 3

    def __init__(
        self,
        anzahl: int,
        protokoll: Path,
        zeiten: Bauzeiten,
        *,
        ausgabe: TextIO | None = None,
        live: bool | None = None,
    ) -> None:
        self._aus = ausgabe or sys.stdout
        self._anzahl = anzahl
        self._zeiten = zeiten
        self._sperre = threading.RLock()
        protokoll.parent.mkdir(parents=True, exist_ok=True)
        self._protokoll = protokoll.open("w", encoding="utf-8")
        self.protokoll_pfad = protokoll

        if live is None:
            live = bool(getattr(self._aus, "isatty", lambda: False)()) and _vt_einschalten()
        self.live = live

        self._beginn = time.monotonic()
        self.schritt_offen = False
        self._fertig_sekunden = 0.0
        self._nummer = 0
        self._titel = ""
        self._schritt_beginn = 0.0
        self._anteil: float | None = None
        self._gezaehlt = False
        self._zaehler = ""
        self._hinweis = ""
        self._phase = ""
        self._phase_beginn = 0.0
        self._phasen_offset = 0.0
        self._phasen_anteil = 0.0
        self._phasen_gewichte: dict[str, float] = {}
        self._ergebnisse: list[str] = []
        self._gezeichnet = False
        self._letzter_prozent_hinweis = -1

        self._halt = threading.Event()
        self._faden: threading.Thread | None = None
        if self.live:
            # Neu gezeichnet wird auch ohne neue Ausgabe: sonst stünden
            # Uhr und geschätzter Balken still, solange ein Schritt
            # nichts von sich gibt - und genau dann will man sehen, dass
            # er noch läuft.
            self._faden = threading.Thread(target=self._zeichnen_lassen, daemon=True)
            self._faden.start()

    # ------------------------------------------------------ Schritte

    def _geschaetzt(self, nummer: int) -> float:
        return self._zeiten.werte.get(str(nummer), 60.0)

    def schritt(self, nummer: int, titel: str) -> None:
        with self._sperre:
            self._nummer = nummer
            self.schritt_offen = True
            self._titel = titel
            self._schritt_beginn = time.monotonic()
            self._anteil = None
            self._gezaehlt = False
            self._zaehler = ""
            self._hinweis = ""
            self._phase = ""
            self._phasen_offset = 0.0
            self._phasen_anteil = 0.0
            self._phasen_gewichte = {}
            self._letzter_prozent_hinweis = -1
            self._protokollieren(f"\n[{nummer}/{self._anzahl}] {titel}")
            if not self.live:
                self._schreiben(f"\n[{nummer}/{self._anzahl}] {titel}")
            self._zeichnen()

    def schritt_beendet(self, *, uebersprungen: bool = False) -> float:
        with self._sperre:
            dauer = time.monotonic() - self._schritt_beginn
            if not uebersprungen:
                self._phase_abschliessen()
            self._fertig_sekunden += self._geschaetzt(self._nummer) if uebersprungen else dauer
            if not uebersprungen:
                self._zeiten.merken(str(self._nummer), dauer)
            zeichen = f"{_GRAU}–{_AUS}" if uebersprungen else f"{_GRUEN}✓{_AUS}"
            zusatz = "übersprungen" if uebersprungen else _dauer(dauer).strip()
            text = f"[{self._nummer}/{self._anzahl}] {self._titel}"
            self._protokollieren(f"  fertig nach {_dauer(dauer).strip()}")
            if self.live:
                self._ueber_den_balken(f" {zeichen} {text:<44}{_GRAU}{zusatz:>9}{_AUS}")
                self._ergebnisse_ausgeben()
            else:
                self._schreiben(f"  fertig nach {_dauer(dauer).strip()}")
            self.schritt_offen = False
            return dauer

    def _ergebnisse_ausgeben(self) -> None:
        for zeile in self._ergebnisse:
            self._ueber_den_balken(f"     {_GRAU}{zeile}{_AUS}")
        self._ergebnisse = []

    def phasen_ankuendigen(self, phasen: list[tuple[str, float]]) -> None:
        """Nennt die Abschnitte des laufenden Schritts mit ihrer
        vermuteten Dauer in Sekunden. Gemessene Dauern aus dem letzten
        Lauf gehen vor; daraus ergibt sich, welchen Teil des Balkens
        jeder Abschnitt bekommt."""
        with self._sperre:
            dauern = {
                name: self._zeiten.werte.get(f"{self._nummer}:{name}", vorgabe)
                for name, vorgabe in phasen
            }
            summe = sum(dauern.values()) or 1.0
            self._phasen_gewichte = {name: d / summe for name, d in dauern.items()}

    def _phase_abschliessen(self) -> None:
        if self._phase:
            self._zeiten.merken(
                f"{self._nummer}:{self._phase}", time.monotonic() - self._phase_beginn
            )

    def phase(self, name: str) -> None:
        """Beginnt einen der angekündigten Abschnitte."""
        with self._sperre:
            self._phase_abschliessen()
            gewicht = self._phasen_gewichte.get(
                name, 1.0 / max(len(self._phasen_gewichte), 1)
            )
            self._phasen_offset += self._phasen_anteil
            self._phasen_anteil = gewicht
            self._phase = name
            self._phase_beginn = time.monotonic()
            self._anteil = min(self._phasen_offset, 1.0)
            self._gezaehlt = False
            self._zaehler = ""
            self._hinweis = ""
            self._protokollieren(f"  -- {name}")
            if not self.live:
                self._schreiben(f"  {name} …")
            self._zeichnen()

    def stand(self, erledigt: int, gesamt: int, einheit: str = "") -> None:
        """Meldet einen gezählten Fortschritt, etwa 120 von 377
        signierten Dateien."""
        if gesamt <= 0:
            return
        with self._sperre:
            innen = min(erledigt / gesamt, 1.0)
            self._gezaehlt = True
            if self._phase:
                self._anteil = self._phasen_offset + self._phasen_anteil * innen
            else:
                self._anteil = innen
            self._zaehler = f"{erledigt}/{gesamt} {einheit}".rstrip()
            prozent = int(innen * 10) * 10
            if not self.live and prozent > self._letzter_prozent_hinweis:
                self._letzter_prozent_hinweis = prozent
                if 0 < prozent < 100:
                    self._schreiben(f"    … {prozent} %  ({self._zaehler})")

    def anteil(self, wert: float) -> None:
        """Meldet einen Fortschritt als Bruchteil, wo es nichts zu
        zählen gibt, etwa den Prozentwert, den pytest selbst ausgibt."""
        self.stand(int(wert * 1000), 1000)
        with self._sperre:
            self._zaehler = ""

    # ------------------------------------------------------ Ausgabe

    def zeile(self, text: str) -> None:
        """Eine Zeile Rohausgabe: ins Protokoll, und als Hinweis unter
        den Balken."""
        text = text.rstrip()
        if not text:
            return
        with self._sperre:
            self._protokollieren(text)
            self._hinweis = text.strip()

    def ergebnis(self, text: str) -> None:
        """Eine Zeile, die stehen bleiben soll - das Ergebnis eines
        Schritts, etwa „4089 passed"."""
        with self._sperre:
            self._protokollieren(text)
            if self.live:
                # Erst mit dem Häkchen des Schritts ausgeben, darunter.
                # Sofort gedruckt, stünden sie über der Zeile ihres
                # Schritts und sähen aus wie das Ergebnis des vorigen.
                self._ergebnisse.append(text.strip())
            else:
                self._schreiben(text)

    def fehler(self, text: str) -> None:
        with self._sperre:
            self._protokollieren(f"\nABGEBROCHEN\n{text}")
            if self.live:
                # Was der Schritt bis hierhin gemeldet hat, gehört zur
                # Fehlersuche dazu.
                self._ergebnisse_ausgeben()
                if self._gezeichnet:
                    self._loeschen()
                self._gezeichnet = False
            farbe_an, farbe_aus = (_ROT + _FETT, _AUS) if self.live else ("", "")
            self._schreiben(f"\n{farbe_an}✗ Abgebrochen in Schritt {self._nummer}/"
                            f"{self._anzahl}: {self._titel}{farbe_aus}")
            for zeile in text.splitlines():
                self._schreiben(f"  {zeile}")
            self._schreiben(f"\n  Vollständiges Protokoll: {self.protokoll_pfad}")

    def beenden(self, schlusszeile: str = "") -> None:
        self._halt.set()
        if self._faden is not None:
            self._faden.join(timeout=2)
        with self._sperre:
            if self.live and self._gezeichnet:
                self._loeschen()
                self._gezeichnet = False
            if schlusszeile:
                self._protokollieren(schlusszeile)
                self._schreiben(schlusszeile)
            self._protokoll.close()

    # ------------------------------------------------------ Innenleben

    def _protokollieren(self, text: str) -> None:
        zeit = time.strftime("%H:%M:%S")
        for zeile in text.splitlines() or [""]:
            self._protokoll.write(f"{zeit}  {zeile}\n")
        self._protokoll.flush()

    def _raus(self, text: str) -> None:
        """Schreibt in die Konsole, auch wenn sie ein Zeichen nicht
        kennt. Eine Windows-Konsole auf Codepage 1252 hat kein „✓";
        statt mit einem UnicodeEncodeError abzubrechen, steht dort
        dann ein Fragezeichen."""
        kodierung = getattr(self._aus, "encoding", None) or "utf-8"
        try:
            self._aus.write(text)
        except UnicodeEncodeError:
            self._aus.write(text.encode(kodierung, errors="replace").decode(kodierung))

    def _schreiben(self, text: str) -> None:
        self._raus(text + "\n")
        self._aus.flush()

    def _zeichnen_lassen(self) -> None:
        while not self._halt.wait(0.25):
            self._zeichnen()

    def _loeschen(self) -> None:
        # An den Anfang der ersten Balkenzeile und alles darunter weg.
        self._raus(f"\x1b[{self._HOEHE}F\x1b[J")

    def _ueber_den_balken(self, text: str) -> None:
        if self._gezeichnet:
            self._loeschen()
            self._gezeichnet = False
        self._raus(text + "\n")
        self._zeichnen()

    def _zeichnen(self) -> None:
        if not self.live or self._nummer == 0:
            return
        with self._sperre:
            breite = max(60, min(shutil.get_terminal_size((100, 20)).columns, 140))
            balkenbreite = max(20, breite - 60)
            jetzt = time.monotonic()
            im_schritt = jetzt - self._schritt_beginn
            geschaetzt = self._geschaetzt(self._nummer)

            if self._gezaehlt and self._anteil is not None:
                schritt_anteil, farbe, marke = self._anteil, _GRUEN, " "
            else:
                schritt_anteil = min(im_schritt / geschaetzt, 0.99) if geschaetzt else 0.0
                if self._phase and self._anteil is not None:
                    phasen_dauer = max(geschaetzt * self._phasen_anteil, 1)
                    innen = min((jetzt - self._phase_beginn) / phasen_dauer, 0.99)
                    schritt_anteil = self._phasen_offset + self._phasen_anteil * innen
                farbe, marke = _GELB, "≈"

            gesamt_geschaetzt = sum(
                self._geschaetzt(n) for n in range(1, self._anzahl + 1)
            )
            erledigt = self._fertig_sekunden + geschaetzt * schritt_anteil
            gesamt_anteil = erledigt / gesamt_geschaetzt if gesamt_geschaetzt else 0.0
            vergangen = jetzt - self._beginn
            rest = sum(
                self._geschaetzt(n) for n in range(self._nummer + 1, self._anzahl + 1)
            ) + max(geschaetzt - im_schritt, 0)
            ueberzogen = im_schritt > geschaetzt * 1.1 and not self._gezaehlt

            zeile1 = (
                f"{_FETT}Gesamt {_AUS} {_balken(gesamt_anteil, balkenbreite, _BLAU)} "
                f"{int(gesamt_anteil * 100):3d} %  {_dauer(vergangen)}  "
                f"{_GRAU}noch ~{max(int(rest // 60), 1)} min{_AUS}"
            )
            uhr = (
                f"{_GELB}länger als sonst{_AUS}" if ueberzogen else _dauer(im_schritt).strip()
            )
            zeile2 = (
                f"[{self._nummer}/{self._anzahl}]{marke:>2}"
                f"{_balken(schritt_anteil, balkenbreite, farbe)} "
                f"{int(schritt_anteil * 100):3d} %  {self._titel}  {_GRAU}{uhr}{_AUS}"
            )
            # Die dritte Zeile: Abschnitt, Zähler und die letzte
            # Rohausgabe - das, was sich laufend ändert.
            teile = [teil for teil in (self._phase, self._zaehler) if teil]
            vorne = " · ".join(teile)
            hinweis = _kurz(self._hinweis, max(breite - 14 - len(vorne), 10))
            zeile3 = (
                f"          {vorne}{'  ' if vorne else ''}{_GRAU}{hinweis}{_AUS}"
            )

            if self._gezeichnet:
                self._raus(f"\x1b[{self._HOEHE}F")
            for zeile in (zeile1, zeile2, zeile3):
                self._raus(f"\x1b[2K{zeile}\n")
            self._aus.flush()
            self._gezeichnet = True



class KonsolenMelder:
    """Der Melder, wenn niemand eine Anzeige übergibt: schreibt Zeilen
    so, wie es die Werkzeuge vor der Anzeige getan haben. So verhält
    sich `python -m tools.ide_paketieren` unverändert."""

    def zeile(self, text: str) -> None:
        if text.strip():
            print(text.rstrip(), flush=True)

    def ergebnis(self, text: str) -> None:
        print(text, flush=True)

    def phasen_ankuendigen(self, phasen: list[tuple[str, float]]) -> None:
        pass

    def phase(self, name: str) -> None:
        print(f"{name} …", flush=True)

    def stand(self, erledigt: int, gesamt: int, einheit: str = "") -> None:
        pass

    def anteil(self, wert: float) -> None:
        pass


def ausfuehren(
    befehl: list[str],
    melder: object,
    *,
    zeile_auswerten: Callable[[str], None] | None = None,
    **optionen: object,
) -> tuple[int, str]:
    """Führt `befehl` aus und reicht jede Ausgabezeile sofort weiter.

    Liefert Rückgabewert und gesamte Ausgabe. `stderr` läuft in
    denselben Strom wie `stdout`: eine Fehlermeldung gehört an die
    Stelle, an der sie auftrat, und nicht gesammelt ans Ende.

    `zeile_auswerten` bekommt jede Zeile zusätzlich, etwa um aus
    pytests „[ 58%]" einen Balken zu machen.
    """
    prozess = subprocess.Popen(
        befehl,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        **optionen,  # type: ignore[arg-type]
    )
    zeilen: list[str] = []
    assert prozess.stdout is not None
    for zeile in prozess.stdout:
        zeilen.append(zeile)
        melder.zeile(zeile)  # type: ignore[attr-defined]
        if zeile_auswerten is not None:
            zeile_auswerten(zeile)
    return prozess.wait(), "".join(zeilen)
