"""StringGrid ↔ pandas (Abschnitt 11.6). `pandas` wird hier bewusst
lokal in den Funktionen importiert statt auf Modulebene, damit `import
pcl` für Projekte ohne Datenauswertung keine pandas-Abhängigkeit
mitschleppt.

`StringGrid.load_dataframe`/`.to_dataframe()` delegieren hierher; ein
Grid speichert nur Text, ein Rundgang über `load_dataframe`/
`to_dataframe` ist deshalb auf Textebene verlustfrei (jede Zelle ergibt
denselben Text wie vorher), nicht zwangsläufig auf Ebene der
ursprünglichen pandas-Spaltentypen (int/float/Datum werden beim erneuten
Einlesen wieder als Text interpretiert).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

    from pcl.components.additional import StringGrid


def load_dataframe(grid: StringGrid, df: pd.DataFrame) -> None:
    """Zeigt `df` in `grid` an: Spaltenköpfe in Zeile 0, Werte als Text
    darunter (``StringGrid.load_dataframe(df)``)."""
    import pandas as pd

    grid.col_count = max(len(df.columns), 1)
    grid.row_count = len(df) + 1
    for spalte, name in enumerate(df.columns):
        grid.cells[spalte, 0] = str(name)
    # `itertuples` statt `iterrows`: eine Zeile aus `iterrows` hat einen
    # gemeinsamen Typ, und neben einer Kommazahl wurde aus der ganzen
    # Zahl 1 in derselben Zeile „1.0“.
    for zeile, reihe in enumerate(df.itertuples(index=False), start=1):
        for spalte, wert in enumerate(reihe):
            grid.cells[spalte, zeile] = _zelltext(wert, pd)


def _zelltext(wert: Any, pd: Any) -> str:
    """Der Text für eine Zelle. Kommazahlen mit Dezimalkomma wie überall
    in Natter: bis 0.3.3 stand „2.4“ in der Tabelle, während
    daneben ein von Hand formatierter Mittelwert „9,7“ zeigte."""
    import numpy as np

    if pd.isna(wert):
        return ""
    if isinstance(wert, float | np.floating):
        return str(wert).replace(".", ",")
    return str(wert)


def to_dataframe(grid: StringGrid) -> pd.DataFrame:
    """Liest `grid` zurück in einen `DataFrame` (``StringGrid.to_dataframe()``),
    Spaltenköpfe aus Zeile 0."""
    import pandas as pd

    spalten = [grid.cells[spalte, 0] for spalte in range(grid.col_count)]
    zeilen: list[list[Any]] = [
        [grid.cells[spalte, zeile] for spalte in range(grid.col_count)]
        for zeile in range(1, grid.row_count)
    ]
    return pd.DataFrame(zeilen, columns=spalten)
