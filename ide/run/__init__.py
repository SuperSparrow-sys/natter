"""Programmausführung als eigener Prozess (Abschnitt 7.8). Ohne Debugger
(folgt in M4) und ohne die getrennten Paketordner der portablen
Verteilung (folgen mit M2 „Zurückgestellt“, Abschnitt 17.3)."""

from ide.run.pruefung import RuffFund, projekt_pruefen
from ide.run.starter import projekt_starten

__all__ = ["RuffFund", "projekt_pruefen", "projekt_starten"]
