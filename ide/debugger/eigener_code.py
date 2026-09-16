"""Erkennt, ob eine Datei „eigener Code“ ist (Abschnitt 8.1: „Aufrufstapel
nur mit eigenem Code, `pcl`- und Qt-Interna ausgeblendet“). Gemeinsam
genutzt vom Fehlerkatalog (`fehlerkatalog.py`, Wo-Zeile einer Meldung) und
dem DAP-Client (`dap_client.py`, gefilterter Aufrufstapel).
"""

from __future__ import annotations

import sysconfig
from pathlib import Path

_STDLIB_PFADE = tuple(
    Path(p).resolve()
    for p in {sysconfig.get_paths()["stdlib"], sysconfig.get_paths()["platstdlib"]}
)


def ist_eigener_code(dateiname: str) -> bool:
    """`False` für Dateien aus `site-packages`, dem `pcl`-Ordner oder der
    Python-Standardbibliothek – alles andere gilt als eigener
    Schülercode."""
    pfad = Path(dateiname)
    if not pfad.is_absolute():
        return True
    aufgeloest = pfad.resolve()
    if "site-packages" in aufgeloest.parts or "pcl" in aufgeloest.parts:
        return False
    return not any(_unterhalb(aufgeloest, basis) for basis in _STDLIB_PFADE)


def _unterhalb(pfad: Path, basis: Path) -> bool:
    try:
        pfad.relative_to(basis)
        return True
    except ValueError:
        return False
