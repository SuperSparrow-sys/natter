"""Vorschläge für die Quelltext-Vervollständigung (M11, Abschnitt 2.2).

Gerechnet wird mit jedi – es versteht Python wirklich, also auch
Typen und Importe. Der Nutzer hat das unter einer
Bedingung entschieden: keine Lizenz, die zu kaufen ist, und keine
sichtbare Veränderung der Oberfläche. Beides geprüft (jedi 0.20.0 und
parso 0.8.7 stehen unter MIT, 13,9 MB, kein Namenszug, keine
Netzverbindung).

Zwei Dinge macht dieses Modul zusätzlich, und das sind die, auf die es
im Unterricht ankommt:

Die Reihenfolge. jedi liefert alles alphabetisch. Für jemanden, der
gerade anfängt, ist aber nicht alles gleich wichtig. Ganz oben stehen
deshalb die eigenen Komponenten des Formulars (`self.b_start`) –
der häufigste Fall überhaupt –, dann die Eigenschaften und Ereignisse
der `pcl`-Komponenten, dann was sonst in der Datei steht, und zuletzt
Schlüsselwörter und eingebaute Funktionen.

Die Erklärung. jedi findet zu `caption` keinen Hilfetext: die
`pcl`-Eigenschaften sind Deskriptoren, ihr `doc=` steht nicht im
Docstring. Genau dort liegt aber der deutsche Text, den eine Schülerin
braucht. Dieses Modul holt ihn direkt aus `pcl.properties`.
"""

from __future__ import annotations

import gc
import html
import re
import sys
import threading
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from pathlib import Path

#: Ab wie vielen getippten Zeichen die Liste erscheint. Ab einem Zeichen
#: springt sie ständig auf und stört mehr, als sie hilft.
MINDESTZEICHEN = 2

#: Wie viele Vorschläge höchstens angezeigt werden. Eine Liste mit
#: dreihundert Einträgen liest niemand.
HOECHSTZAHL = 40

#: Rangstufen – kleiner ist weiter oben.
RANG_KOMPONENTE = 0
RANG_PCL = 1
RANG_DATEI = 2
RANG_PYTHON = 3

#: `self.<name> = ` – so entsteht in einem Natter-Formular eine
#: Komponente. Gesucht wird im Quelltext selbst, weil jedi zwar den
#: Namen kennt, aber nicht, dass er im Unterricht der wichtigste ist.
_KOMPONENTEN_MUSTER = re.compile(
    r"^\s*self\.([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*\(", re.MULTILINE
)

#: Deutsche Erklärungen zu den Schlüsselwörtern, die im Unterricht
#: vorkommen. Pythons eigene Hilfe ist englisch und für die Zielgruppe
#: unbrauchbar.
SCHLUESSELWORT_HILFE: dict[str, str] = {
    "and": "logisches Und: beide Bedingungen müssen zutreffen",
    "as": "gibt einem Import oder einem Kontext einen anderen Namen",
    "assert": "bricht ab, wenn die Bedingung nicht stimmt",
    "break": "verlässt die Schleife sofort",
    "class": "beginnt eine Klasse",
    "continue": "springt zum nächsten Schleifendurchlauf",
    "def": "beginnt eine Funktion oder Methode",
    "del": "löscht einen Namen oder einen Listeneintrag",
    "elif": "weiterer Fall, wenn das vorige „if“ nicht zutraf",
    "else": "was sonst passieren soll",
    "except": "fängt einen Fehler ab",
    "False": "der Wahrheitswert „falsch“",
    "finally": "läuft in jedem Fall, auch nach einem Fehler",
    "for": "Zählschleife über eine Liste oder einen Bereich",
    "from": "holt einzelne Namen aus einem Modul",
    "global": "greift auf eine Variable außerhalb der Funktion zu",
    "if": "führt etwas nur unter einer Bedingung aus",
    "import": "bindet ein Modul ein",
    "in": "prüft, ob etwas enthalten ist – oder gehört zu „for“",
    "is": "prüft, ob es dasselbe Objekt ist - nicht, ob der Wert gleich ist",
    "lambda": "kurze Funktion ohne Namen",
    "None": "„nichts“ – der leere Wert",
    "not": "kehrt eine Bedingung um",
    "or": "logisches Oder: eine der Bedingungen genügt",
    "pass": "tut nichts – Platzhalter, wo Python etwas erwartet",
    "raise": "löst selbst einen Fehler aus",
    "return": "gibt einen Wert zurück und verlässt die Funktion",
    "self": "das eigene Objekt – darüber sind die Komponenten erreichbar",
    "True": "der Wahrheitswert „wahr“",
    "try": "versucht etwas, das schiefgehen kann",
    "while": "Schleife, solange die Bedingung zutrifft",
    "with": "öffnet etwas und schließt es zuverlässig wieder",
}

#: Deutsche Erklärungen zu den eingebauten Funktionen, die im Unterricht
#: vorkommen. jedi liefert dafür Pythons eigene, englische Hilfe; neben
#: `print` stand „Prints the values to a stream, or to sys.stdout by
#: default." Was hier fehlt, bekommt gar keine Erklärung - lieber keine
#: als eine englische.
PYTHON_HILFE: dict[str, str] = {
    "abs": "Betrag einer Zahl, ohne Vorzeichen",
    "all": "wahr, wenn jedes Element zutrifft",
    "any": "wahr, wenn mindestens ein Element zutrifft",
    "bool": "Wahrheitswert: True oder False",
    "chr": "das Zeichen zu einer Zahl im Zeichensatz",
    "dict": "Wörterbuch aus Schlüsseln und Werten",
    "enumerate": "zählt beim Durchlaufen mit: (Nummer, Element)",
    "float": "Kommazahl",
    "input": "liest eine Eingabe von der Tastatur, als Text",
    "int": "ganze Zahl; wandelt auch Text wie \"42\" um",
    "isinstance": "prüft, ob ein Wert von einem bestimmten Typ ist",
    "len": "Anzahl der Elemente oder Zeichen",
    "list": "Liste",
    "max": "der größte Wert",
    "min": "der kleinste Wert",
    "open": "öffnet eine Datei zum Lesen oder Schreiben",
    "ord": "die Zahl eines Zeichens im Zeichensatz",
    "print": "gibt Werte aus",
    "range": "Zahlenfolge, etwa für eine Zählschleife",
    "reversed": "durchläuft etwas von hinten nach vorn",
    "round": "rundet eine Zahl, auf Wunsch auf Nachkommastellen",
    "set": "Menge ohne doppelte Elemente",
    "sorted": "sortierte Kopie einer Folge",
    "str": "Text; wandelt auch Zahlen in Text um",
    "sum": "Summe aller Elemente",
    "tuple": "unveränderliche Folge",
    "type": "der Typ eines Werts",
    "zip": "durchläuft mehrere Folgen nebeneinander",
}

#: jedi ist nicht dafür gebaut, aus zwei Fäden zugleich benutzt zu
#: werden. Das Aufwärmen und die Vorschläge beim Tippen laufen im
#: Hintergrund, Parameterhilfe und F12 im Hauptfaden.
_JEDI_SPERRE = threading.Lock()

#: Ob `aufwaermen()` in diesem Programmlauf schon angestoßen wurde.
_aufgewaermt = False


def aufwaermen() -> None:
    """Lässt jedi im Hintergrund einmal arbeiten, bevor jemand tippt.

    Der erste Vorschlag kostete 1,2 bis 2,2 Sekunden, weil jedi erst
    seine Daten zu Python selbst einliest - und das geschah im
    Tastendruck, der Editor stand so lange still. Danach sind es 50 bis
    120 Millisekunden. Angestoßen wird das einmal je Programmlauf, beim
    Start von Natter.
    """
    global _aufgewaermt
    if _aufgewaermt:
        return
    _aufgewaermt = True
    _aufwaermen_im_hintergrund()


def _jedi():
    """Das Modul `jedi`, mit einem Hilfsprozess, der nichts erbt.

    jedi startet für übersetzte Module einen Hilfsprozess und gibt ihm
    unter Windows `close_fds=False` mit. Der erbt damit jedes Handle,
    das in diesem Augenblick vererbbar ist - auch die Schreibenden der
    Rohre, die gerade für ruff oder das Schülerprogramm angelegt
    werden. Lief das Aufwärmen genau während der Prüfung vor dem
    Start, hielt der Hilfsprozess die Rohre von ruff offen, und F5
    wartete für immer auf deren Ende (Punkt 224). Mit
    `close_fds=True` reicht Python unter Windows nur die drei
    Standard-Handles des Hilfsprozesses weiter.
    """
    import jedi
    from jedi.inference.compiled import subprocess as jedi_prozess

    if not getattr(jedi_prozess, "_natter_abgesichert", False):
        import subprocess

        def popen(*args, **kwargs):
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
            kwargs["close_fds"] = True
            return subprocess.Popen(*args, **kwargs)

        jedi_prozess._GeneralizedPopen = popen
        jedi_prozess._natter_abgesichert = True
    return jedi


#: Die Python, mit der jedi rechnet. Einmal gebaut und dann für jeden
#: Aufruf dieselbe, weil jedi seinen Hilfsprozess an diesem Objekt
#: festhält; eine neue Umgebung je Tastendruck hieße ein neuer Prozess.
_umgebung = None


def _eigene_umgebung():
    """Die Umgebung der Python, in der Natter selbst läuft.

    Ohne Angabe fragt jedi die Variablen `VIRTUAL_ENV` und
    `CONDA_PREFIX` ab und startet die Python, die dort genannt ist.
    Natter bringt seine eigene mit; welche daneben installiert ist,
    spielt für die Vorschläge keine Rolle.
    """
    global _umgebung
    if _umgebung is None:
        from jedi.api.environment import (
            Environment,
            InterpreterEnvironment,
            SameEnvironment,
        )

        name = Path(sys.executable).name.lower()
        if name.startswith("python"):
            _umgebung = SameEnvironment()
        else:
            # Eingebettet, etwa als Natter.exe: dann liegt die
            # python.exe neben der Laufzeit. Gibt es keine, rechnet
            # jedi im eigenen Prozess.
            python = Path(sys.exec_prefix) / "python.exe"
            if python.is_file():
                _umgebung = Environment(str(python))
            else:
                _umgebung = InterpreterEnvironment()
    return _umgebung


def _skript(
    jedi,  # noqa: ANN001
    quelltext: str,
    pfad: Path | str | None,
    projekt: Path | str | None = None,
):
    """Ein `jedi.Script` mit Projekt und Umgebung aus Natter.

    Ohne `project` sucht jedi im Ordner der Datei und in jedem Ordner
    darüber bis zur Laufwerkswurzel nach `.jedi/project.json` und
    startet die Python, die dort unter `environment_path` steht - im
    Konto dessen, der gerade tippt. Eine abgegebene Projektmappe oder
    ein Ordner `C:\\.jedi`, den unter Windows jedes Konto anlegen darf,
    brachte so ein fremdes Programm zum Laufen (Punkt 277). Das
    Projekt baut Natter deshalb selbst: der Projektordner oder, ohne
    Projekt, der Ordner der Datei, ohne `environment_path` und ohne
    Erweiterungen aus dem Projektordner.
    """
    if projekt is not None:
        wurzel = Path(projekt)
    elif pfad:
        wurzel = Path(pfad).parent
    else:
        wurzel = Path.cwd()
    projekt_fuer_jedi = jedi.Project(
        wurzel.absolute(),
        environment_path=None,
        load_unsafe_extensions=False,
    )
    return jedi.Script(
        code=quelltext,
        path=str(pfad) if pfad else None,
        project=projekt_fuer_jedi,
        environment=_eigene_umgebung(),
    )


def _aufwaermen_im_hintergrund() -> None:
    threading.Thread(
        target=_aufwaermen_jetzt, name="jedi-aufwaermen", daemon=True
    ).start()


#: Wie viele Nebenfäden gerade mit jedi rechnen, und wie Speicher-
#: bereinigung und Umschaltzeit vorher standen.
_rechnende = 0
_bereinigung_war_an = False
_umschaltzeit_vorher = 0.005
_RECHNENDE_SPERRE = threading.Lock()

#: Nach wie vielen Sekunden ein Faden, der auf Python wartet, den
#: rechnenden ablöst, solange jedi im Hintergrund läuft. Python
#: wechselt sonst erst nach 5 ms. Für einen Tastendruck ruft Qt
#: mehrmals in Python zurück, und jedes Mal wartete der Hauptfaden bis
#: zu diesen 5 ms auf jedi: in einer Unit mit 5.000 Zeilen kam ein
#: Tastendruck während der Rechnung so auf bis zu 90 ms, mit 0,5 ms
#: auf höchstens 16 ms.
_UMSCHALTZEIT_S = 0.0005


@contextmanager
def nebenfaden_rechnet() -> Iterator[None]:
    """Rahmen für jede Rechnung mit jedi in einem Nebenfaden, und für
    das Neuladen der CSV-Ansicht (Punkt 355).

    Keine automatische Speicherbereinigung (Punkt 136). Sie läuft in
    dem Faden, der gerade Speicher anfordert - hier also im
    Hintergrund -, und könnte dort ein altes Fenster abräumen, das als
    Zyklus übrig ist. Ein Qt-Widget, das außerhalb des Hauptfadens
    zerstört wird, lässt Qt mit „Aborted“ abbrechen.

    Dazu eine kurze Umschaltzeit (`_UMSCHALTZEIT_S`), damit Tippen
    während der Rechnung nicht auf jedi wartet (Punkt 313).

    Gezählt wird, weil das Aufwärmen, eine Anfrage aus dem Editor und
    ein Neuladen zugleich laufen können; zurückgestellt wird erst,
    wenn alle fertig sind.
    """
    global _rechnende, _bereinigung_war_an, _umschaltzeit_vorher
    with _RECHNENDE_SPERRE:
        if _rechnende == 0:
            _bereinigung_war_an = gc.isenabled()
            _umschaltzeit_vorher = sys.getswitchinterval()
            gc.disable()
            sys.setswitchinterval(_UMSCHALTZEIT_S)
        _rechnende += 1
    try:
        yield
    finally:
        with _RECHNENDE_SPERRE:
            _rechnende -= 1
            if _rechnende == 0:
                sys.setswitchinterval(_umschaltzeit_vorher)
                if _bereinigung_war_an:
                    gc.enable()


def im_hintergrund(
    rechnen: Callable[[], object], fertig: Callable[[object], None]
) -> None:
    """Ruft `rechnen()` in einem Nebenfaden auf und übergibt das
    Ergebnis an `fertig`, noch im Nebenfaden.

    Für die Vorschläge beim Tippen (Punkt 313): jedi liest dafür die
    ganze Datei, bei 5.000 Zeilen dauert das eine Drittelsekunde und
    länger. `fertig` darf deshalb kein Widget anfassen, sondern nur ein
    Signal senden; Qt stellt es dem Hauptfaden zu.
    """

    def laufen() -> None:
        with nebenfaden_rechnet():
            fertig(rechnen())

    threading.Thread(target=laufen, name="jedi-vorschlaege", daemon=True).start()


def _aufwaermen_jetzt() -> None:
    # Das Aufwärmen dauert wenige Sekunden; so lange wartet die
    # Speicherbereinigung.
    with nebenfaden_rechnet():
        _aufwaermen_ohne_aufraeumen()


def _aufwaermen_ohne_aufraeumen() -> None:
    try:
        with _JEDI_SPERRE:
            jedi = _jedi()

            # Nicht nur die Namen: Unterschrift und Hilfetext liest die
            # Vorschlagsliste auch, und erst dabei lädt jedi die
            # Beschreibung der eingebauten Funktionen. Nur mit
            # `complete()` aufgewärmt, dauerte der erste echte Vorschlag
            # noch 600 ms.
            for eintrag in _skript(jedi, "pri", None).complete(1, 3):
                eintrag.docstring(raw=True)
                eintrag.get_signatures()
            _skript(jedi, "print(", None).get_signatures(1, 6)
        # Die deutschen Texte der Komponenten: beim ersten Aufruf wird
        # dafür jede `pcl`-Komponente einmal durchgesehen.
        _pcl_hilfetexte()
    except Exception:  # noqa: BLE001 - Aufwärmen darf nie etwas stören
        pass


def _ist_eigener_code(modul_pfad: Path | None, pfad: Path | str | None) -> bool:
    """Ob eine Fundstelle zum Projekt gehört statt zu Python oder einer
    Bibliothek.

    Nur dort steht ein Docstring, den jemand aus dem Kurs geschrieben
    hat und der sich als Erklärung eignet. Ohne Pfad (eine noch nicht
    gespeicherte Datei) liegt eigener Code in keiner Datei; alles aus
    einer Datei im selben Ordner gehört ebenfalls dazu - eine andere
    Unit desselben Projekts.
    """
    if modul_pfad is None:
        return True
    if not pfad:
        return False
    try:
        return Path(modul_pfad).resolve().parent == Path(pfad).resolve().parent
    except OSError:
        return False


@dataclass(frozen=True)
class Vorschlag:
    """Ein Eintrag der Vorschlagsliste."""

    name: str
    art: str
    erklaerung: str
    signatur: str
    rang: int

    def anzeige_text(self, mit_erklaerung: bool = True) -> str:
        """Die Zeile, wie sie in der Liste steht.

        Die Signatur nur, wenn sie auch mit dem Namen anfängt: bei einem
        Ereignis wie `on_click` liefert jedi `NoneType()` – der Typ des
        Standardwerts, nicht der Name. Im Bildschirmfoto stand dort
        wirklich „NoneType()   –   Wird beim Klicken ausgelöst“, und
        niemand hätte erraten, dass das `on_click` ist.

        `mit_erklaerung=False` lässt den deutschen Hilfetext weg – im
        Prüfungsmodus (M11, Abschnitt 6). Die Liste selbst bleibt: sie
        ist Schreibhilfe, kein Lösungshinweis. „Wird beim Klicken
        ausgelöst“ neben `on_click`
        ist dagegen nah an der Antwort auf genau die Frage, die in einer
        Klausur gestellt wird.
        """
        links = self.signatur if self.signatur.startswith(self.name) else self.name
        if not mit_erklaerung or not self.erklaerung:
            return links
        return f"{links}   –   {self.erklaerung}"

    @property
    def anzeige(self) -> str:
        """Die vollständige Zeile, mit Erklärung."""
        return self.anzeige_text()


@cache
def _pcl_hilfetexte() -> dict[str, str]:
    """Name einer `pcl`-Eigenschaft oder eines Ereignisses → deutscher
    Hilfetext.

    Über alle Komponenten hinweg: `caption` heißt überall dasselbe, und
    eine Liste je Komponente wäre beim Tippen ohnehin nicht zu
    unterscheiden. Wo sich zwei Texte unterscheiden, gewinnt der erste –
    besser ein leicht unscharfer Hinweis als gar keiner.
    """
    import pcl
    from pcl.control import Control
    from pcl.properties import eigenschaften, ereignisse

    texte: dict[str, str] = {}
    for name in dir(pcl):
        typ = getattr(pcl, name)
        if not isinstance(typ, type) or not issubclass(typ, Control):
            continue
        for feldname, feld in eigenschaften(typ).items():
            texte.setdefault(feldname, getattr(feld, "doc", "") or "")
        for feldname, feld in ereignisse(typ).items():
            texte.setdefault(feldname, getattr(feld, "doc", "") or "")
    return {name: text for name, text in texte.items() if text}


def eigene_komponenten(quelltext: str) -> dict[str, str]:
    """Die Namen, die im Formular als `self.<name> = Typ(...)`
    entstehen, mit ihrem Typ.

    Der Typ ist die Erklärung, die im Unterricht zählt: „b_start“ sagt
    einer Schülerin wenig, „Button auf diesem Formular“ sagt ihr, was
    sie damit machen kann.
    """
    return dict(_KOMPONENTEN_MUSTER.findall(quelltext))


def _erklaerung(
    name: str,
    docstring: str,
    komponenten: dict[str, str],
    *,
    modul: str = "",
    eigen: bool = True,
) -> str:
    """Eine kurze deutsche Erklärung. Eine Liste aus nackten Namen
    hilft niemandem, der gerade erst anfängt.

    Der Docstring zählt nur bei eigenem Code. Aus Python selbst und aus
    Bibliotheken kommt er auf Englisch; für die eingebauten Funktionen
    steht deshalb ein eigener deutscher Text in `PYTHON_HILFE`, alles
    andere bleibt ohne Erklärung.
    """
    if name in komponenten:
        return f"{komponenten[name]} auf diesem Formular"
    if name in SCHLUESSELWORT_HILFE:
        return SCHLUESSELWORT_HILFE[name]
    aus_pcl = _pcl_hilfetexte().get(name)
    if aus_pcl:
        return aus_pcl
    if modul == "builtins":
        return PYTHON_HILFE.get(name, "")
    if not eigen:
        return ""
    erste_zeile = (docstring or "").strip().splitlines()
    return erste_zeile[0].strip() if erste_zeile else ""


def _rang(name: str, art: str, komponenten: dict[str, str]) -> int:
    if name in komponenten:
        return RANG_KOMPONENTE
    if name in _pcl_hilfetexte():
        return RANG_PCL
    if art in ("keyword", "instance") or name in SCHLUESSELWORT_HILFE:
        return RANG_PYTHON
    if art == "module":
        return RANG_PYTHON
    return RANG_DATEI


def _vorschlag_aus(eintrag, komponenten: dict[str, str], pfad) -> Vorschlag:  # noqa: ANN001
    try:
        docstring = eintrag.docstring(raw=True)
        signatur = eintrag.name
        unterschriften = eintrag.get_signatures()
        if unterschriften:
            signatur = unterschriften[0].to_string()
        modul = eintrag.module_name or ""
        eigen = _ist_eigener_code(eintrag.module_path, pfad)
    except Exception:  # noqa: BLE001
        docstring, signatur, modul, eigen = "", eintrag.name, "", False
    return Vorschlag(
        name=eintrag.name,
        art=eintrag.type,
        erklaerung=_erklaerung(
            eintrag.name, docstring, komponenten, modul=modul, eigen=eigen
        ),
        signatur=signatur,
        rang=_rang(eintrag.name, eintrag.type, komponenten),
    )


def vorschlaege(
    quelltext: str,
    zeile: int,
    spalte: int,
    pfad: Path | str | None = None,
    hoechstzahl: int = HOECHSTZAHL,
) -> list[Vorschlag]:
    """Vorschläge für die Stelle (`zeile` ab 1, `spalte` ab 0).

    Eine leere Liste bedeutet „nichts anzubieten“ – auch dann, wenn
    jedi selbst stolpert. Eine halb getippte Zeile ist syntaktisch fast
    immer kaputt; ein Fehler darf die Eingabe nie unterbrechen.
    """
    komponenten = eigene_komponenten(quelltext)
    ergebnis: list[Vorschlag] = []
    try:
        with _JEDI_SPERRE:
            jedi = _jedi()

            skript = _skript(jedi, quelltext, pfad)
            gefunden = skript.complete(zeile, spalte)
            for eintrag in gefunden:
                # Alles mit führendem Unterstrich bleibt draußen. In
                # Python heißt das „geht dich nichts an“, und für die
                # Zielgruppe wären `_qwidget` oder
                # `_bei_prop_aenderung` zwischen `caption` und `width`
                # nicht nur Rauschen, sondern eine Einladung, an den
                # Innereien zu drehen.
                if eintrag.name.startswith("_"):
                    continue
                ergebnis.append(_vorschlag_aus(eintrag, komponenten, pfad))
    except Exception:  # noqa: BLE001 - beim Tippen darf nichts hochgehen
        return []

    ergebnis.sort(key=lambda v: (v.rang, v.name.lower()))
    return ergebnis[:hoechstzahl]


def parameterhilfe(
    quelltext: str, zeile: int, spalte: int, pfad: Path | str | None = None
) -> str:
    """Welche Parameter hier erwartet werden – für die Anzeige beim
    Tippen der öffnenden Klammer. Leer, wenn es nichts zu sagen gibt."""
    try:
        with _JEDI_SPERRE:
            jedi = _jedi()

            skript = _skript(jedi, quelltext, pfad)
            unterschriften = skript.get_signatures(zeile, spalte)
    except Exception:  # noqa: BLE001
        return ""
    if not unterschriften:
        return ""
    return unterschriften[0].to_string()


def parameterhilfe_anzeige(
    quelltext: str, zeile: int, spalte: int, pfad: Path | str | None = None
) -> str:
    """Die Parameterhilfe als Kurzhinweis in HTML: jeder Parameter mit
    seinem Typ, der gerade einzugebende fett und unterstrichen, dahinter
    der Rückgabetyp und darunter die Erklärung.

    Typen stehen nur da, wo sie im Quelltext angegeben sind. Ohne
    Angabe weiß niemand, was erwartet wird, und ein erfundener Typ
    wäre schlimmer als keiner.

    Leer, wenn es nichts zu sagen gibt.
    """
    try:
        with _JEDI_SPERRE:
            jedi = _jedi()

            skript = _skript(jedi, quelltext, pfad)
            unterschriften = skript.get_signatures(zeile, spalte)
            if not unterschriften:
                return ""
            unterschrift = unterschriften[0]
            parameter = [p.to_string() for p in unterschrift.params]
            aktuell = unterschrift.index
            ganz = unterschrift.to_string()
            docstring = unterschrift.docstring(raw=True)
            modul = unterschrift.module_name or ""
            eigen = _ist_eigener_code(unterschrift.module_path, pfad)
            name = unterschrift.name
    except Exception:  # noqa: BLE001
        return ""

    teile = []
    for nummer, text in enumerate(parameter):
        text = html.escape(text)
        teile.append(f"<b><u>{text}</u></b>" if nummer == aktuell else text)
    zeile_oben = f"{html.escape(name)}({', '.join(teile)})"
    _, pfeil, rueckgabe = ganz.rpartition(") -> ")
    if pfeil and rueckgabe:
        zeile_oben += f" → {html.escape(rueckgabe)}"

    erklaerung = _erklaerung(name, docstring, {}, modul=modul, eigen=eigen)
    if erklaerung:
        return f"{zeile_oben}<br><i>{html.escape(erklaerung)}</i>"
    return zeile_oben


@dataclass(frozen=True)
class Fundstelle:
    """Wo eine Definition steht – für „Zu Definition springen“ (F12)."""

    pfad: Path | None
    zeile: int
    spalte: int
    name: str
    #: Die Definition liegt ausserhalb des Projektordners – in Python
    #: selbst oder in einem installierten Paket. Dorthin wird nicht
    #: gesprungen; der Editor sagt stattdessen, woher der Name kommt.
    fremd: bool = False

    @property
    def in_dieser_datei(self) -> bool:
        return self.pfad is None and not self.fremd


def definition(
    quelltext: str,
    zeile: int,
    spalte: int,
    pfad: Path | str | None = None,
    projekt: Path | str | None = None,
) -> Fundstelle | None:
    """Wo das, was unter dem Cursor steht, definiert wurde.

    `None`, wenn es nichts zu finden gibt – bei einem Schlüsselwort, im
    Leeren, oder wenn jedi an einer halb getippten Zeile scheitert.
    Eine Fundstelle in derselben Datei trägt `pfad=None`: der Editor
    braucht dann nur zu springen, nicht zu öffnen.

    Kein Sprung in Pythons Standardbibliothek. Wer auf `print`
    steht und F12 drückt, landete sonst in `builtins.pyi` – Quelltext
    in einer Sprache, die im Unterricht nie vorkommt, in einem Ordner,
    den niemand wiederfindet. Liegt die Definition ausserhalb von
    `projekt`, kommt sie mit `fremd=True` zurück: der Editor sagt dann,
    woher der Name stammt, statt die Datei zu öffnen.
    """
    try:
        with _JEDI_SPERRE:
            jedi = _jedi()

            skript = _skript(jedi, quelltext, pfad, projekt)
            gefunden = skript.goto(zeile, spalte, follow_imports=True)
    except Exception:  # noqa: BLE001 - F12 darf nie etwas hochgehen lassen
        return None
    if not gefunden:
        return None

    treffer = gefunden[0]
    if treffer.line is None:
        return None
    ziel = Path(treffer.module_path) if treffer.module_path else None
    eigene = Path(pfad).resolve() if pfad else None
    if ziel is not None and eigene is not None and ziel.resolve() == eigene:
        return Fundstelle(None, treffer.line, treffer.column, treffer.name)
    if ziel is not None and not _gehoert_zum_projekt(ziel, projekt):
        return Fundstelle(ziel, treffer.line, treffer.column, treffer.name, fremd=True)
    return Fundstelle(
        pfad=ziel, zeile=treffer.line, spalte=treffer.column, name=treffer.name
    )


def _gehoert_zum_projekt(ziel: Path, projekt: Path | str | None) -> bool:
    """Ob `ziel` im Projektordner liegt. Ohne Projekt gilt jede Datei
    als fremd – ausserhalb eines Projekts gibt es nichts, wohin ein
    Sprung sinnvoll führen könnte."""
    if projekt is None:
        return False
    try:
        return Path(ziel).resolve().is_relative_to(Path(projekt).resolve())
    except OSError:
        return False
