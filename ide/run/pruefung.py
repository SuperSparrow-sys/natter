"""Ruff-Prüfung vor dem Start (Abschnitt 8.2): Syntaxfehler, unbekannte
Namen, fehlende/ungenutzte Importe, ungenutzte Variablen. Läuft vor jedem
Start; bei Funden wird nicht gestartet, die Funde erscheinen im Panel
„Meldungen“ (Abschnitt 8.2).

`--isolated` ignoriert eine eventuell vorhandene `pyproject.toml`/
`ruff.toml` in der Ordnerhierarchie über dem Projekt (z. B. die von
Natter selbst, wenn ein Beispielprojekt zufällig innerhalb dieses
Repositorys liegt) – die Vorstart-Prüfung soll für jedes Schülerprojekt
gleich streng sein, unabhängig vom Speicherort. Syntaxfehler werden von
Ruff immer gemeldet, auch außerhalb der ausgewählten Regeln.
"""

from __future__ import annotations

import ast
import functools
import json
import re
import subprocess
import sys
import warnings
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from ide.project import Projekt
from ide.prozess import ohne_konsole
from ide.run.interpreter import ruff_befehl
from pcl.fehlerkatalog import self_fehlt_leitfrage
from pcl.pruefungsmodus import laeuft as pruefungsmodus_laeuft

_AUSGEWAEHLTE_REGELN = "E9,F821,F401,F841"

#: Regeln, die als Hinweis im Panel „Meldungen“ stehen, den Start aber
#: nicht verhindern: ein ungenutzter Import und eine ungenutzte
#: Variable sind Unordnung, kein Fehler – das Programm läuft damit
#: einwandfrei.
#:
#: Bewusst eine Liste der Ausnahmen und nicht der Blocker: eine später
#: hinzugefügte Regel verhindert den Start, bis jemand bewusst
#: entscheidet, dass sie es nicht soll. Der umgekehrte Weg würde eine
#: neue, ernste Regel stillschweigend durchlassen (M12).
NUR_HINWEIS = frozenset({"F401", "F841", "natter-modulname", "natter-kodierung"})

#: Regeln, die Natter selbst prüft, weil sie mehr als eine Datei
#: betreffen. Ihre `meldung` ist schon deutsch, und ihre Leitfrage
#: steht im Fund. Import und Ereignis verhindern den Start; ein
#: Dateiname, der ein Modul verdeckt, ist nur ein Hinweis, denn er
#: stört erst, wenn das Programm das Modul importiert.
EIGENE_REGELN = frozenset(
    {"natter-import", "natter-ereignis", "natter-modulname", "natter-kodierung"}
)

#: Die Klammer in Pythons „'(' was never closed“.
_KLAMMER_MUSTER = re.compile(r"'(.)' was never closed")


#: Der erste in Rückstrichen eingefasste Name einer Ruff-Meldung -
#: also `zaehler` in "Undefined name `zaehler`".
_NAME_MUSTER = re.compile(r"`([^`]+)`")

#: Deutsche Fassung der vier Regelfamilien, die Natter vor dem Start
#: prüft: was los ist, und was man dagegen tun kann.
#:
#: Ruff schreibt englisch ("Local variable `x` is assigned to but never
#: used"). Für eine Zehntklässlerin im ersten Python-Jahr ist das eine
#: zweite Hürde vor der eigentlichen: dem Fehler. Die Meldung steht
#: deshalb auf Deutsch da, im selben Aufbau wie im Fehlerkatalog -
#: erst *was*, dann *prüfe*.
_UEBERSETZUNGEN: dict[str, tuple[str, str]] = {
    "F821": (
        "Der Name {name} ist an dieser Stelle nicht bekannt.",
        "Ist er richtig geschrieben? Wurde er vorher zugewiesen oder "
        "importiert?",
    ),
    "F401": (
        "{name} wird importiert, aber nirgends benutzt.",
        "Wird der Import noch gebraucht, oder ist er von einem früheren "
        "Versuch übrig geblieben?",
    ),
    "F841": (
        "Die Variable {name} bekommt einen Wert, der nie gelesen wird.",
        "Steht der Name weiter unten falsch geschrieben? Wird der Wert "
        "überhaupt gebraucht?",
    ),
    "E902": (
        "Die Datei ist nicht in UTF-8 gespeichert, und Python kann sie so "
        "nicht lesen.",
        "Mit einem anderen Editor als UTF-8 speichern, oder in die erste "
        "Zeile „# -*- coding: cp1252 -*-“ schreiben.",
    ),
    "invalid-syntax": (
        "Python versteht diese Zeile nicht.",
        "Fehlt am Zeilenende ein Doppelpunkt, eine schließende Klammer "
        "oder ein Anführungszeichen?",
    ),
}

#: Genauere Fassungen für `invalid-syntax`, gesucht im englischen Text
#: von Ruff. Ein Einrückungsfehler lief bis 0.3.3 unter der
#: allgemeinen Meldung, die nach Doppelpunkt, Klammer oder
#: Anführungszeichen fragt, und die Einrückung kam darin nicht vor.
#:
#: Seit Punkt 291 kommt der Text eines Syntaxfehlers von Python selbst
#: (`_syntaxfehler_von_python`), Ruffs Fassung nur noch, wenn Python
#: den Quelltext annimmt. Die Stichwörter passen auf beide.
#: Die beiden häufigsten Fehler der ersten Stunden, im Wortlaut des
#: Fehlerkatalogs. Die Prüfung vor dem Start fängt sie ab, bevor der
#: Fehlerkatalog sie je zu sehen bekommt; bis dahin kam nur die
#: allgemeine Meldung. Python und Ruff schreiben sie verschieden.
_DOPPELPUNKT = (
    "Am Ende dieser Zeile fehlt der Doppelpunkt.",
    "Jede Zeile, die einen Block eröffnet (if, else, while, for, def, "
    "class), endet mit einem Doppelpunkt – ist er hier gesetzt?",
)
_ANFUEHRUNGSZEICHEN = (
    "Ein Text wurde geöffnet, aber in derselben Zeile nicht wieder "
    "geschlossen.",
    "Stehen am Anfang und am Ende des Textes dieselben "
    "Anführungszeichen?",
)

_SYNTAX_GENAUER: tuple[tuple[str, tuple[str, str]], ...] = (
    ("expected ':'", _DOPPELPUNKT),
    ("expected `:`", _DOPPELPUNKT),
    ("unterminated string literal", _ANFUEHRUNGSZEICHEN),
    ("missing closing quote", _ANFUEHRUNGSZEICHEN),
    (
        "was never closed",
        (
            "Die Klammer „{klammer}“ in dieser Zeile wird nie geschlossen.",
            "Wo gehört die schließende Klammer hin? Hat jede öffnende "
            "Klammer ihr Gegenstück, meist noch in derselben Zeile?",
        ),
    ),
    (
        "maybe you meant '==' or ':=' instead of '='",
        (
            "In dieser Bedingung steht ein einzelnes Gleichheitszeichen. "
            "Mit = bekommt ein Name einen Wert; verglichen wird mit ==.",
            "Soll hier verglichen werden, ob zwei Werte gleich sind, und "
            "stehen dafür zwei Gleichheitszeichen da?",
        ),
    ),
    (
        "expected an indented block",
        (
            "Nach dem Doppelpunkt in der Zeile darüber fehlt ein "
            "eingerückter Block.",
            "Soll diese Zeile zum Block gehören, der mit dem Doppelpunkt "
            "beginnt? Ist sie dann weiter eingerückt als die Zeile mit "
            "dem Doppelpunkt?",
        ),
    ),
    (
        # Ruff schreibt „unexpected indentation“, Python „unexpected
        # indent“.
        "unexpected indent",
        (
            "Diese Zeile ist eingerückt, aber davor beginnt kein Block.",
            "Steht die Zeile weiter rechts als die Zeile davor, obwohl "
            "sie zu keinem neuen Block gehört? Oder fehlt in der Zeile "
            "davor am Ende ein Doppelpunkt?",
        ),
    ),
    (
        "indent",
        (
            "Die Einrückung dieser Zeile passt zu keiner Ebene darüber.",
            "Zu welchem Block gehört die Zeile, und beginnt sie genau "
            "so weit rechts wie die anderen Zeilen dieses Blocks?",
        ),
    ),
)

#: Wenn Ruff eine Regel meldet, für die hier nichts steht.
_UNBEKANNT = (
    "{meldung}",
    "Welche Stelle nennt die Meldung, und was steht dort? Die Meldung "
    "stammt unübersetzt aus der Prüfung vor dem Start - lässt sich an "
    "der Zeile erkennen, was nicht stimmt?",
)


@dataclass(frozen=True)
class RuffFund:
    datei: Path
    zeile: int
    spalte: int
    code: str
    meldung: str
    #: Bei den Prüfungen, die Natter selbst anstellt
    #: (`EIGENE_REGELN`): dort ist `meldung` schon deutsch, und die
    #: Leitfrage hängt vom Einzelfall ab. Bei einem Fund von Ruff
    #: ersetzt sie die feste Leitfrage der Regel, etwa bei einem
    #: unbekannten Namen, vor dem `self.` fehlt (`_self_pruefen`).
    leitfrage: str = ""

    @property
    def name(self) -> str:
        """Der Name, um den es geht - oder leer."""
        treffer = _NAME_MUSTER.search(self.meldung)
        return treffer.group(1) if treffer else ""

    @property
    def blockiert(self) -> bool:
        """Ob dieser Fund den Start verhindert.

        Die Unterscheidung fehlte bis M12: jeder Fund verhinderte
        ihn. Wer `import random` schreibt, bevor er `random` benutzt –
        also so, wie man es lernt –, bekam sein Programm nicht gestartet,
        obwohl es einwandfrei gelaufen wäre. Dasselbe beim Auskommentieren
        einer Zeile zum Ausprobieren: die Variable darüber wird ungenutzt,
        und der Start ist blockiert. Ein ungenutzter Import ist ein Hinweis,
        kein Fehler – das Programm läuft einwandfrei.

        Umgekehrt ist es richtig, bei einem Syntaxfehler oder einem
        unbekannten Namen gar nicht erst zu starten: das Programm würde
        ohnehin abstürzen, und der Fehlerkatalog sagt vorher mehr dazu
        als ein Absturz danach.
        """
        return self.code not in NUR_HINWEIS

    def _vorlage(self) -> tuple[str, str]:
        if self.code in EIGENE_REGELN:
            return "{meldung}", self.leitfrage
        if self.leitfrage:
            return _UEBERSETZUNGEN.get(self.code, _UNBEKANNT)[0], (
                self.leitfrage
            )
        if self.code == "invalid-syntax":
            meldung = self.meldung.lower()
            for stichwort, vorlage in _SYNTAX_GENAUER:
                if stichwort in meldung:
                    return vorlage
        return _UEBERSETZUNGEN.get(self.code, _UNBEKANNT)

    @property
    def was(self) -> str:
        """Was los ist, auf Deutsch."""
        vorlage = self._vorlage()[0]
        klammer = _KLAMMER_MUSTER.search(self.meldung)
        return vorlage.format(
            name=self.name,
            meldung=self.meldung,
            klammer=klammer.group(1) if klammer else "",
        )

    @property
    def pruefe(self) -> str:
        """Was man dagegen tun kann - leer im Prüfungsmodus.

        Genau dieser Teil hilft weiter, und genau deshalb gehört er in
        einer Leistungssituation nicht dazu. *Was* falsch ist, steht
        auch dann noch da.
        """
        if pruefungsmodus_laeuft():
            return ""
        return self._vorlage()[1]

    def __str__(self) -> str:
        """Eine Zeile für das Panel „Meldungen“ und für den Tooltip im
        Quelltext.

        Ohne den Namen der Regel: „[invalid-syntax]“ oder „[F821]“ am
        Ende jeder Zeile sagt einer Siebtklässlerin nichts und stört
        beim Lesen (Punkt 291). Er steht im Tooltip des Eintrags
        (`regel`)."""
        teile = [f"{self.datei.name}, Zeile {self.zeile}: {self.was}"]
        if self.pruefe:
            teile.append(self.pruefe)
        return " ".join(teile)

    @property
    def regel(self) -> str:
        """Der Name der Regel, für den Tooltip im Panel."""
        return f"Regel: {self.code}"


def projekt_pruefen(projekt: Projekt) -> list[RuffFund]:
    """Prüft das Projekt vor dem Start. Leere Liste bei sauberem
    Projekt.

    Zuerst `ruff check` gegen die Dateien der obersten Ebene, dann zwei Prüfungen,
    die Ruff nicht kennt, weil sie mehr als eine Datei betreffen: ob
    jeder Name, den eine Unit aus einer anderen importiert, dort auch
    steht (`_importe_pruefen`), und ob jede Methode, die ein Formular
    mit einem Ereignis verknüpft, in seiner Unit steht
    (`_ereignisse_pruefen`)."""
    funde = _kodierung_pruefen(
        _self_pruefen(_syntaxfehler_zusammenfassen(_ruff_pruefen(projekt)))
    )
    funde.extend(_importe_pruefen(projekt))
    funde.extend(_ereignisse_pruefen(projekt))
    funde.extend(_modulnamen_pruefen(projekt))
    return funde


def _kodierung_pruefen(funde: list[RuffFund]) -> list[RuffFund]:
    """Eine Datei, die nicht in UTF-8 vorliegt, liest ruff gar nicht
    (`E902`) und meldete das englisch und blockierend, auch mit einer
    Kodierungsangabe, mit der Python die Datei ausführt (Punkt 608).
    Übersetzt Python die Datei, wird daraus ein Hinweis; sonst bleibt
    es ein Fund mit deutscher Meldung (`_UEBERSETZUNGEN`)."""
    ergebnis: list[RuffFund] = []
    for fund in funde:
        if fund.code == "E902" and _python_liest(fund.datei):
            fund = RuffFund(
                datei=fund.datei,
                zeile=1,
                spalte=1,
                code="natter-kodierung",
                meldung=(
                    f"{fund.datei.name} ist nicht in UTF-8 gespeichert und "
                    "wird deshalb vor dem Start nicht geprüft."
                ),
                leitfrage=(
                    "Der Editor von Natter öffnet nur UTF-8. Soll die Datei "
                    "dort bearbeitet werden, mit einem anderen Editor als "
                    "UTF-8 speichern."
                ),
            )
        ergebnis.append(fund)
    return ergebnis


def _python_liest(datei: Path) -> bool:
    try:
        compile(datei.read_bytes(), str(datei), "exec")
    except (SyntaxError, ValueError, OSError):
        return False
    return True


#: Länger wartet die Prüfung vor dem Start nicht auf ruff. Ein Projekt
#: auf einem Netzlaufwerk, das gerade nicht antwortet, hielt Natter
#: sonst an, bis ruff zurückkam (Punkt 553).
RUFF_ZEITGRENZE_S = 20


class PruefungZuLang(RuntimeError):
    """ruff kam nicht innerhalb von `RUFF_ZEITGRENZE_S` zurück."""


def _ruff_pruefen(projekt: Projekt) -> list[RuffFund]:
    try:
        ergebnis = _ruff_aufrufen(projekt)
    except subprocess.TimeoutExpired as fehler:
        raise PruefungZuLang() from fehler
    if not ergebnis.stdout.strip():
        return []

    return [
        RuffFund(
            datei=Path(fund["filename"]),
            zeile=fund["location"]["row"],
            spalte=fund["location"]["column"],
            code=fund["code"] or fund["name"],
            meldung=fund["message"],
        )
        for fund in json.loads(ergebnis.stdout)
    ]


def _ruff_aufrufen(projekt: Projekt) -> subprocess.CompletedProcess[str]:
    # Nur die Dateien der obersten Ebene: aus ihnen besteht das
    # Programm, und nur sie zeigt der Projekt-Explorer. Mit dem ganzen
    # Ordner hielt eine alte Fassung in `alt/versuch1.py` mit einem
    # Syntaxfehler den Start auf, und die Meldung nannte nur
    # „versuch1.py“ (Punkt 575).
    dateien = sorted(
        str(pfad) for pfad in projekt.ordner.glob("*.py") if pfad.is_file()
    )
    if not dateien:
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")
    return subprocess.run(
        [
            *ruff_befehl(),
            "check",
            "--isolated",
            # Ohne das legt ruff einen `.ruff_cache` im Arbeitsordner
            # von Natter an - in der installierten Fassung also im
            # Programmordner, wo er nach dem Deinstallieren liegen blieb.
            # Bei einem Schülerprojekt bringt der Cache ohnehin nichts.
            "--no-cache",
            f"--select={_AUSGEWAEHLTE_REGELN}",
            "--output-format=json",
            *dateien,
        ],
        # Ruff schreibt UTF-8. Ohne Angabe läse Python das Rohr als
        # cp1252, und aus einem Ordner „Übung“ würde „Ãœbung“ - ein
        # Pfad, den es nicht gibt (Punkt 187).
        **ohne_konsole(
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=RUFF_ZEITGRENZE_S,
        ),
    )


def _self_pruefen(funde: list[RuffFund]) -> list[RuffFund]:
    """Gibt einem unbekannten Namen, der eine Komponente des Formulars
    oder ein Attribut der Klasse ist, die Frage nach dem fehlenden
    `self.` mit (Punkt 431). Die Frage kommt aus dem Fehlerkatalog,
    damit Prüfung und Laufzeitmeldung gleich lauten."""
    ergebnis: list[RuffFund] = []
    for fund in funde:
        if fund.code == "F821" and fund.name:
            leitfrage = self_fehlt_leitfrage(
                fund.datei, fund.zeile, fund.name
            )
            if leitfrage is not None:
                fund = replace(fund, leitfrage=leitfrage)
        ergebnis.append(fund)
    return ergebnis


# -- Syntaxfehler: einer je Datei, mit Pythons eigener Zeile ----------------


def _syntaxfehler_zusammenfassen(funde: list[RuffFund]) -> list[RuffFund]:
    """Ein Syntaxfehler je Datei statt aller, die Ruff findet.

    Ruff meldet einen Syntaxfehler dort, wo der Parser aufgibt, und
    danach jeden Folgefehler. Aus einer offenen Klammer in Zeile 2
    wurden so zwei Meldungen für Zeile 3 und 4, und Zeile 2 kam nicht
    vor; `if a = 3:` ergab vier Meldungen, drei davon wörtlich gleich
    (Punkt 291). Python selbst nennt bei einer offenen Klammer die
    Zeile, in der sie geöffnet wurde, und bei `=` in einer Bedingung
    den Hinweis auf `==`. Deshalb steht hier Pythons Meldung, und nur
    sie. Nimmt Python den Quelltext an, bleibt Ruffs erster Fund.
    """
    ergebnis: list[RuffFund] = []
    erledigt: set[Path] = set()
    for fund in funde:
        if fund.code != "invalid-syntax":
            ergebnis.append(fund)
            continue
        if fund.datei in erledigt:
            continue
        erledigt.add(fund.datei)
        ergebnis.append(_syntaxfehler_von_python(fund.datei) or fund)
    return ergebnis


def _syntaxfehler_von_python(datei: Path) -> RuffFund | None:
    try:
        quelle = datei.read_bytes()
    except OSError:
        return None
    try:
        with warnings.catch_warnings():
            # Eine Zeichenkette wie "\d" ist für Python eine Warnung,
            # die hier niemand sehen soll.
            warnings.simplefilter("ignore")
            compile(quelle, str(datei), "exec", dont_inherit=True)
    except SyntaxError as fehler:
        return RuffFund(
            datei=datei,
            zeile=fehler.lineno or 1,
            spalte=fehler.offset or 1,
            code="invalid-syntax",
            meldung=fehler.msg,
        )
    except ValueError:
        return None
    return None


# -- Namen, die eine Unit aus einer anderen importiert ----------------------


def _baum(datei: Path) -> ast.Module | None:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return ast.parse(datei.read_bytes(), str(datei))
    except (OSError, SyntaxError, ValueError):
        return None


_DEFINITIONEN = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def _oberste_namen(baum: ast.Module) -> set[str] | None:
    """Die Namen, die ein Modul auf oberster Ebene festlegt - auch in
    `if`, `try` oder `with`, nicht aber in Funktionen und Klassen.
    `None`, wenn sich das nicht sicher sagen lässt: bei
    `from x import *` und bei einem modulweiten `__getattr__`."""
    namen: set[str] = set()
    offen: list[ast.AST] = list(baum.body)
    while offen:
        knoten = offen.pop()
        if isinstance(knoten, _DEFINITIONEN):
            namen.add(knoten.name)
        elif isinstance(knoten, (ast.Import, ast.ImportFrom)):
            for alias in knoten.names:
                if alias.name == "*":
                    return None
                namen.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(knoten, ast.Name):
            if isinstance(knoten.ctx, ast.Store):
                namen.add(knoten.id)
        elif not isinstance(knoten, ast.Lambda):
            offen.extend(ast.iter_child_nodes(knoten))
    if "__getattr__" in namen:
        return None
    # Ein Name, den eine Funktion über `global` anlegt, gehört ebenfalls
    # zum Modul, sobald sie läuft (Punkt 608).
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Global):
            namen.update(knoten.names)
    return namen


#: Ausnahmen, deren Behandlung einen Import als „darf fehlen“
#: kennzeichnet.
_IMPORTFEHLER = {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}


def _abgefangene_importe(baum: ast.Module) -> set[int]:
    """Die `id` der Importe in einem `try`, dessen `except` einen
    fehlenden Import abfängt. Solch ein Import darf scheitern; das
    Programm hat einen Ersatz (Punkt 608)."""
    ergebnis: set[int] = set()
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Try):
            continue
        faengt = False
        for behandlung in knoten.handlers:
            typen = behandlung.type
            if typen is None:
                faengt = True
                continue
            namen = typen.elts if isinstance(typen, ast.Tuple) else [typen]
            if any(isinstance(n, ast.Name) and n.id in _IMPORTFEHLER for n in namen):
                faengt = True
        if faengt:
            for teil in knoten.body:
                for innen in ast.walk(teil):
                    if isinstance(innen, ast.ImportFrom):
                        ergebnis.add(id(innen))
    return ergebnis


def modul_verdeckt(name: str) -> bool:
    """Ob eine Unit `name` ein Modul verdecken würde, das ein Programm
    importieren kann: eines der Standardbibliothek oder ein
    mitgeliefertes Paket wie `pcl`, `pandas` oder `matplotlib`.

    Python sucht zuerst im Ordner des Programms. Eine Unit `random.py`
    machte `import random` zur eigenen Datei, und `random.randint`
    endete mit einem AttributeError (Punkt 536).

    Gefragt wird ohne Import und nur nach Standardbibliothek und
    installierten Paketen. Bis 0.4.3 fragte `find_spec` den Suchpfad der
    IDE: Ordner wie `design` oder `docs` galten als Module, und ein Name
    mit Punkt wie `this.x` führte das Modul `this` aus (Punkt 587)."""
    if not name.isidentifier():
        return False
    return name in sys.stdlib_module_names or name in _installierte_module()


@functools.cache
def _installierte_module() -> frozenset[str]:
    """Die Namen der Module und Pakete in `site-packages`, ohne sie zu
    laden, dazu `pcl`. Natters eigenes Paket `ide` braucht kein
    Schülerprogramm."""
    import pkgutil
    import sysconfig

    orte = {sysconfig.get_paths()[art] for art in ("purelib", "platlib")}
    namen = {modul.name for modul in pkgutil.iter_modules(sorted(orte))}
    return frozenset((namen | {"pcl"}) - {"ide"})


def _modulnamen_pruefen(projekt: Projekt) -> list[RuffFund]:
    """Ein Hinweis zu jeder Datei im Projekt, die heißt wie ein Modul
    von Python, etwa eine hineinkopierte `random.py`. Umbenennen in
    Natter lässt solche Namen nicht zu (Punkt 536)."""
    funde: list[RuffFund] = []
    for datei in projekt.alle_python_dateien():
        if datei == projekt.haupt_datei or not modul_verdeckt(datei.stem):
            continue
        funde.append(
            RuffFund(
                datei=datei,
                zeile=1,
                spalte=1,
                code="natter-modulname",
                meldung=(
                    f"Die Datei heißt wie das Python-Modul „{datei.stem}“. "
                    f"Ein „import {datei.stem}“ holt dann diese Datei statt "
                    "des Moduls."
                ),
                leitfrage=(
                    f"Wird „{datei.stem}“ irgendwo importiert? Dann die Datei "
                    f"umbenennen, etwa in u_{datei.stem}."
                ),
            )
        )
    return funde


def _importe_pruefen(projekt: Projekt) -> list[RuffFund]:
    """Findet `from u_main import main`, wenn `main` in `u_main.py`
    fehlt.

    Bis 0.3.5 fiel das erst beim Import auf, also nachdem das Programm
    schon gelaufen war: wer in einem Konsolenprojekt `def main():`
    löschte, sah das ganze Programm laufen und danach eine Meldung,
    die Unit „u_main“ lasse sich nicht laden (Punkt 289). Geprüft wird
    nur, was sicher zu sagen ist: Units, die als `.py` im
    Projektordner liegen, ohne Sternchen-Import.

    Importiert die Startdatei den Namen, steht der Fund in der Unit,
    denn an der Startdatei ist nichts zu ändern. Sonst steht er in
    der Zeile des Imports.
    """
    baeume: dict[Path, ast.Module | None] = {}

    def baum(datei: Path) -> ast.Module | None:
        if datei not in baeume:
            baeume[datei] = _baum(datei)
        return baeume[datei]

    funde: list[RuffFund] = []
    for datei in projekt.alle_python_dateien():
        importierend = baum(datei)
        if importierend is None:
            continue
        abgefangen = _abgefangene_importe(importierend)
        for knoten in ast.walk(importierend):
            if not isinstance(knoten, ast.ImportFrom) or knoten.level:
                continue
            if id(knoten) in abgefangen:
                continue
            if not knoten.module:
                continue
            unit_datei = projekt.ordner / f"{knoten.module}.py"
            if not unit_datei.is_file():
                continue
            unit_baum = baum(unit_datei)
            if unit_baum is None:
                continue
            vorhanden = _oberste_namen(unit_baum)
            if vorhanden is None:
                continue
            for alias in knoten.names:
                # Ein Stern-Import nennt keinen Namen, den es geben
                # müsste (Punkt 608).
                if alias.name == "*" or alias.name in vorhanden:
                    continue
                funde.append(
                    _import_fund(
                        datei == projekt.haupt_datei,
                        datei,
                        knoten.lineno,
                        unit_datei,
                        unit_baum,
                        alias.name,
                    )
                )
    return funde


def _import_fund(
    aus_der_startdatei: bool,
    datei: Path,
    zeile: int,
    unit_datei: Path,
    unit_baum: ast.Module,
    name: str,
) -> RuffFund:
    aehnlich = next(
        (
            knoten
            for knoten in unit_baum.body
            if isinstance(knoten, _DEFINITIONEN)
            and knoten.name.lower() == name.lower()
        ),
        None,
    )
    leitfrage = (
        f"Steht in {unit_datei.name} eine Zeile „def {name}():“ oder "
        f"„class {name}“, ganz links am Rand und mit genau dieser "
        "Groß- und Kleinschreibung? Wurde sie gelöscht oder umbenannt?"
    )
    if not aus_der_startdatei:
        return RuffFund(
            datei=datei,
            zeile=zeile,
            spalte=1,
            code="natter-import",
            meldung=(
                f"Aus der Unit {unit_datei.stem} wird {name} importiert, "
                f"aber in {unit_datei.name} gibt es keine Funktion, "
                "Klasse oder Variable dieses Namens."
            ),
            leitfrage=leitfrage,
        )
    meldung = (
        f"In {unit_datei.name} gibt es keine Funktion oder Klasse "
        f"{name}. {datei.name} ruft sie beim Start auf."
    )
    if aehnlich is not None:
        # Der richtige Name gehört zur Hilfe, nicht zur Meldung: im
        # Prüfungsmodus entfällt nur der Teil „Zu prüfen“, und dort
        # stand er sonst weiter als fertige Lösung.
        leitfrage = (
            f"Steht sie dort als {aehnlich.name}, also mit anderer "
            "Groß- und Kleinschreibung, die mitzählt?"
        )
    return RuffFund(
        datei=unit_datei,
        zeile=aehnlich.lineno if aehnlich is not None else 1,
        spalte=1,
        code="natter-import",
        meldung=meldung,
        leitfrage=leitfrage,
    )


# -- Methoden, die ein Formular mit einem Ereignis verknüpft ----------------


def _ereignisse_pruefen(projekt: Projekt) -> list[RuffFund]:
    """Findet ein Ereignis in der `.pfm`, dessen Methode in der Unit
    fehlt.

    Der Designer legt die Methode als gewöhnliche Bearbeitung im
    Editor an. Mehrmals Strg+Z nimmt sie deshalb wieder weg, die
    Verknüpfung in der `.pfm` bleibt, und das Programm brach beim
    Öffnen des Fensters in `u_main_design.py` ab, einer Datei, die im
    Projekt-Explorer gar nicht steht (Punkt 290).

    Geprüft wird nur die Klasse, die die `.pfm` nennt, und nur, wenn
    sie allein von ihrer Design-Klasse erbt. Eine Methode aus einer
    weiteren Basisklasse wäre hier nicht zu sehen.
    """
    funde: list[RuffFund] = []
    for pfm_datei in projekt.formulare():
        unit_datei = pfm_datei.with_suffix(".py")
        try:
            pfm = json.loads(pfm_datei.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        if not isinstance(pfm, dict) or not unit_datei.is_file():
            continue
        baum = _baum(unit_datei)
        if baum is None:
            continue
        klasse = next(
            (
                knoten
                for knoten in baum.body
                if isinstance(knoten, ast.ClassDef)
                and knoten.name == pfm.get("class")
            ),
            None,
        )
        if klasse is None or not _erbt_nur_vom_design(klasse):
            continue
        methoden = _namen_in_der_klasse(klasse)
        for komponente, ereignis, methode in _verknuepfungen(pfm):
            if methode not in methoden:
                funde.append(
                    _ereignis_fund(
                        unit_datei, klasse, komponente, ereignis, methode
                    )
                )
    return funde


def _erbt_nur_vom_design(klasse: ast.ClassDef) -> bool:
    namen = [
        basis.id if isinstance(basis, ast.Name) else None
        for basis in klasse.bases
    ]
    return namen == [f"{klasse.name}Design"]


def _namen_in_der_klasse(klasse: ast.ClassDef) -> set[str]:
    namen: set[str] = set()
    for knoten in klasse.body:
        if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
            namen.add(knoten.name)
        elif isinstance(knoten, ast.Assign):
            namen.update(
                ziel.id
                for ziel in knoten.targets
                if isinstance(ziel, ast.Name)
            )
    return namen


def _verknuepfungen(
    pfm: dict[str, Any],
) -> list[tuple[str | None, str, str]]:
    """(Komponente, Ereignis, Methode) für jede Verknüpfung der `.pfm`.
    Die Komponente ist `None` beim Formular selbst."""
    ergebnis: list[tuple[str | None, str, str]] = []

    def sammeln(eintrag: dict[str, Any], name: str | None) -> None:
        ereignisse = eintrag.get("events")
        if isinstance(ereignisse, dict):
            for ereignis, methode in ereignisse.items():
                if isinstance(methode, str) and methode:
                    ergebnis.append((name, ereignis, methode))
        for kind in eintrag.get("children") or []:
            if isinstance(kind, dict):
                sammeln(kind, kind.get("name"))

    sammeln(pfm, None)
    return ergebnis


def _ereignis_fund(
    unit_datei: Path,
    klasse: ast.ClassDef,
    komponente: str | None,
    ereignis: str,
    methode: str,
) -> RuffFund:
    if komponente is None:
        wer = "des Formulars"
        wohin = "auf die freie Fläche des Formulars"
    else:
        wer = f"der Komponente {komponente}"
        wohin = f"auf {komponente}"
    return RuffFund(
        datei=unit_datei,
        zeile=klasse.lineno,
        spalte=1,
        code="natter-ereignis",
        meldung=(
            f"Die Methode {methode} fehlt in der Klasse {klasse.name}. "
            f"Das Formular verknüpft sie mit dem Ereignis {ereignis} "
            f"{wer}."
        ),
        leitfrage=(
            f"Wurde {methode} gelöscht, umbenannt oder mit Strg+Z "
            f"zurückgenommen, und fehlt nur ein Doppelklick {wohin} im "
            f"Designer oder auf {ereignis} im Objektinspektor (Reiter "
            "„Ereignisse“), der sie neu anlegt?"
        ),
    )
