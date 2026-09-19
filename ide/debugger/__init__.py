"""Debugger: Fehlerkatalog (Abschnitt 8.3–8.5), der DAP-Client auf
`debugpy` (Abschnitt 8.1) und „Als Tabelle anzeigen“ für Variablen
(Abschnitt 11.6)."""

from ide.debugger.dap_client import DapClient, DapFehler
from ide.debugger.debug_sitzung import DebugSitzung
from ide.debugger.fehlerkatalog import (
    Fehlermeldung,
    fehlermeldung_aus_dap_erzeugen,
    fehlermeldung_erzeugen,
)
from ide.debugger.tabellenansicht import (
    Tabelle,
    TabellenFehler,
    tabelle_aus_antwort,
    tabelle_aus_wert,
    tabellen_ausdruck,
)

__all__ = [
    "DapClient",
    "DapFehler",
    "DebugSitzung",
    "Fehlermeldung",
    "Tabelle",
    "TabellenFehler",
    "fehlermeldung_aus_dap_erzeugen",
    "fehlermeldung_erzeugen",
    "tabelle_aus_antwort",
    "tabelle_aus_wert",
    "tabellen_ausdruck",
]
