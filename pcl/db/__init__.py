"""pcl/db: dünne Adapterschicht zwischen den SQLdb-Komponenten
(``pcl.components.data_access``) und den eigentlichen Datenbanktreibern.

Jede SQL-Anweisung im Kurs verwendet benannte Platzhalter im Stil
``:name`` (Abschnitt 10.1), unabhängig vom tatsächlich verwendeten
Treiber – dadurch ist SQL-Injection-sicheres Arbeiten mit Parametern der
Standard, ohne dass Treiberdetails bekannt sein müssen. `sqlite3`
versteht ``:name`` bereits nativ (DB-API-Parameterstil ``named``),
PyMySQL braucht dagegen ``%(name)s`` (Stil ``pyformat``, M5 Schritt 2) –
`uebersetze_platzhalter` übernimmt diese Umwandlung rein textuell, ohne
Verbindung zur Datenbank.
"""

from __future__ import annotations

import re

_PLATZHALTER_MUSTER = re.compile(r":([a-zA-Z_][a-zA-Z0-9_]*)")


def uebersetze_platzhalter(sql: str, stil: str) -> str:
    """Übersetzt ``:name``-Platzhalter in `sql` in den von `stil`
    verlangten Parameterstil. ``"named"`` (sqlite3) lässt den Text
    unverändert, ``"pyformat"`` (PyMySQL) ersetzt ``:name`` durch
    ``%(name)s``."""
    if stil == "named":
        return sql
    if stil == "pyformat":
        return _PLATZHALTER_MUSTER.sub(r"%(\1)s", sql)
    raise ValueError(f"Unbekannter Platzhalterstil: {stil!r}")
