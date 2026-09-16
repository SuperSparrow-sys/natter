"""Debugger: Fehlerkatalog (Abschnitt 8.3–8.5) und der DAP-Client auf
`debugpy` (Abschnitt 8.1)."""

from ide.debugger.dap_client import DapClient, DapFehler
from ide.debugger.debug_sitzung import DebugSitzung
from ide.debugger.fehlerkatalog import Fehlermeldung, fehlermeldung_erzeugen

__all__ = ["DapClient", "DapFehler", "DebugSitzung", "Fehlermeldung", "fehlermeldung_erzeugen"]
