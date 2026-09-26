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

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from ide.project import Projekt
from ide.prozess import ohne_konsole
from ide.run.interpreter import ruff_befehl
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
NUR_HINWEIS = frozenset({"F401", "F841"})


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
        "Entweder die import-Zeile löschen - oder den Namen dort "
        "benutzen, wo er gebraucht wird.",
    ),
    "F841": (
        "Die Variable {name} bekommt einen Wert, der nie gelesen wird.",
        "Steht der Name weiter unten falsch geschrieben? Sonst kann die "
        "Zuweisung weg.",
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
_SYNTAX_GENAUER: tuple[tuple[str, tuple[str, str]], ...] = (
    (
        "expected an indented block",
        (
            "Nach dem Doppelpunkt in der Zeile darüber fehlt ein "
            "eingerückter Block.",
            "Die Zeile um eine Ebene einrücken (Tab-Taste, vier "
            "Leerzeichen).",
        ),
    ),
    (
        "unexpected indentation",
        (
            "Diese Zeile ist eingerückt, aber davor beginnt kein Block.",
            "Die Zeile so weit ausrücken wie die Zeile davor. Oder "
            "fehlt dort am Ende ein Doppelpunkt?",
        ),
    ),
    (
        "indent",
        (
            "Die Einrückung dieser Zeile passt zu keiner Ebene darüber.",
            "Die Zeile genauso weit einrücken wie die anderen Zeilen "
            "ihres Blocks.",
        ),
    ),
)

#: Wenn Ruff eine Regel meldet, für die hier nichts steht.
_UNBEKANNT = (
    "{meldung}",
    "Die Meldung stammt unübersetzt aus der Prüfung vor dem Start.",
)


@dataclass(frozen=True)
class RuffFund:
    datei: Path
    zeile: int
    spalte: int
    code: str
    meldung: str

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
        return vorlage.format(name=self.name, meldung=self.meldung)

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
        Quelltext."""
        teile = [f"{self.datei.name}, Zeile {self.zeile}: {self.was}"]
        if self.pruefe:
            teile.append(self.pruefe)
        teile.append(f"[{self.code}]")
        return " ".join(teile)


def projekt_pruefen(projekt: Projekt) -> list[RuffFund]:
    """Führt `ruff check` gegen den Projektordner aus. Leere Liste bei
    sauberem Projekt."""
    ergebnis = subprocess.run(
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
            str(projekt.ordner),
        ],
        **ohne_konsole(capture_output=True, text=True),
    )
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
