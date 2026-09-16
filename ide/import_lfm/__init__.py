"""Lazarus-Import (Abschnitt 15): `.lfm`-Parser und Zuordnung nach `.pfm`."""

from ide.import_lfm.parser import LfmParserError, parse_lfm
from ide.import_lfm.zuordnung import LfmImportErgebnis, LfmZuordnungError, lfm_zu_pfm

__all__ = [
    "LfmImportErgebnis",
    "LfmParserError",
    "LfmZuordnungError",
    "lfm_zu_pfm",
    "parse_lfm",
]
