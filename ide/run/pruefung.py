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
import sys
from dataclasses import dataclass
from pathlib import Path

from ide.project import Projekt
from pcl.pruefungsmodus import laeuft as pruefungsmodus_laeuft

_AUSGEWAEHLTE_REGELN = "E9,F821,F401,F841"

#: Regeln, die als Hinweis im Panel „Meldungen“ stehen, den Start aber
#: **nicht** verhindern: ein ungenutzter Import und eine ungenutzte
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

        Die Unterscheidung fehlte bis M12: **jeder** Fund verhinderte
        ihn. Wer `import random` schreibt, bevor er `random` benutzt –
        also so, wie man es lernt –, bekam sein Programm nicht gestartet,
        obwohl es einwandfrei gelaufen wäre. Dasselbe beim Auskommentieren
        einer Zeile zum Ausprobieren: die Variable darüber wird ungenutzt,
        und der Start ist blockiert. In Lazarus ist eine ungenutzte Unit
        im `uses` ein Hinweis, kein Fehler – das Programm übersetzt und
        läuft.

        Umgekehrt ist es richtig, bei einem Syntaxfehler oder einem
        unbekannten Namen gar nicht erst zu starten: das Programm würde
        ohnehin abstürzen, und der Fehlerkatalog sagt vorher mehr dazu
        als ein Absturz danach.
        """
        return self.code not in NUR_HINWEIS

    @property
    def was(self) -> str:
        """Was los ist, auf Deutsch."""
        vorlage = _UEBERSETZUNGEN.get(self.code, _UNBEKANNT)[0]
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
        return _UEBERSETZUNGEN.get(self.code, _UNBEKANNT)[1]

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
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--isolated",
            f"--select={_AUSGEWAEHLTE_REGELN}",
            "--output-format=json",
            str(projekt.ordner),
        ],
        capture_output=True,
        text=True,
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
