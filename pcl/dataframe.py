"""StringGrid ↔ pandas (Abschnitt 11.6). `pandas` wird hier bewusst
lokal in den Funktionen importiert statt auf Modulebene, damit `import
pcl` für Projekte ohne Datenauswertung keine pandas-Abhängigkeit
mitschleppt.

`StringGrid.load_dataframe`/`.to_dataframe()` delegieren hierher. Ein
Grid speichert nur Text; `to_dataframe` macht aus Spalten, die nur
Zahlen enthalten, wieder Zahlen. Andere Typen wie Datum oder
Wahrheitswert kommen als Text zurück.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd

    from pcl.components.additional import StringGrid

#: Beginnt ein Wert so, ist er eine Kennung wie „01067“ oder „0351 …“:
#: eine Postleitzahl oder Telefonnummer, keine Zahl. Dieselbe Regel
#: gilt beim CSV-Import im Datenbank-Panel (`ide/database/panel.py`),
#: damit ein Grid und ein Import dieselben Daten liefern.
_FUEHRENDE_NULL = re.compile(r"[+-]?0\d")

#: So schreibt `text()` eine Zahl ab 10^21 oder unter 10^-10, etwa
#: „2,5 · 10^21“; `load_dataframe` schreibt sie so in die Zelle.
_ZEHNERPOTENZ = re.compile(r"([+-]?\d+(?:,\d+)?) · 10\^([+-]?\d+)")

#: Größer ist eine ganze Zahl in pandas als `int64` nicht. Längere
#: Ziffernfolgen (Kontonummern, Kennungen) bleiben Text.
_GROESSTE_GANZZAHL = 2**63 - 1


def load_dataframe(grid: StringGrid, df: pd.DataFrame) -> None:
    """Zeigt `df` in `grid` an: Spaltenköpfe in Zeile 0, Werte als Text
    darunter (``StringGrid.load_dataframe(df)``)."""
    spaltenzahl = max(len(df.columns), 1)
    grid.col_count = spaltenzahl
    grid.row_count = len(df) + 1
    # Die Werte kommen spaltenweise und unverändert ins Modell; Text
    # wird erst beim Anzeigen daraus (`_zelltext` in
    # `pcl/components/additional.py`). Zelle für Zelle über `cells[…]`
    # brauchten 100.000 Zeilen mit vier Spalten 17 s (Punkt 356).
    spalten = [
        _spaltenwerte(df.iloc[:, nummer]) for nummer in range(len(df.columns))
    ]
    if spalten:
        kopf = [str(name) for name in df.columns]
        zeilen = [kopf, *map(list, zip(*spalten, strict=True))]
    else:
        zeilen = [[""] for _ in range(len(df) + 1)]
    grid._qwidget.modell.inhalt_setzen(spaltenzahl, zeilen)


def _spaltenwerte(spalte: pd.Series) -> list[Any]:
    """Die Werte einer Spalte für die Zellen: fehlende als leerer
    Text, Kommazahlen aus numpy als `float`, damit sie wie jede andere
    Kommazahl mit Dezimalkomma erscheinen.

    `tolist()` liefert jeden Wert mit seinem eigenen Typ, wie eine
    Zeile aus `itertuples`: neben einer Kommazahl bleibt die ganze
    Zahl 1 „1“. Eine Zeile aus `iterrows` hat einen gemeinsamen Typ,
    und daraus wurde „1.0“."""
    import numpy as np

    werte = spalte.tolist()
    fehlt = spalte.isna().tolist()
    if spalte.dtype == object:
        # Nur hier kann ein numpy-Wert stehen bleiben; `tolist()`
        # wandelt die übrigen Spalten selbst in Python-Werte.
        return [
            "" if leer else float(wert) if isinstance(wert, np.floating)
            else wert
            for wert, leer in zip(werte, fehlt, strict=True)
        ]
    if any(fehlt):
        return [
            "" if leer else wert
            for wert, leer in zip(werte, fehlt, strict=True)
        ]
    return werte


def to_dataframe(grid: StringGrid) -> pd.DataFrame:
    """Liest `grid` zurück in einen `DataFrame` (``StringGrid.to_dataframe()``),
    Spaltenköpfe aus Zeile 0.

    Eine Spalte, in der jede Zelle leer oder mit `zahl()` lesbar ist,
    kommt als Zahlen zurück, damit `df["Anzahl"].sum()` rechnet statt
    die Texte aneinanderzuhängen: ganze Zahlen als `int`, sonst als
    Kommazahl, leere Zellen als fehlender Wert. Jede andere Spalte,
    auch eine ganz leere, bleibt Text. Ebenso eine Spalte, in der ein
    Wert mit „0“ und einer weiteren Ziffer beginnt wie „01067“: sonst
    verlöre eine Postleitzahl ihre führende Null."""
    import pandas as pd

    modell = grid._qwidget.modell
    spalten = [grid.cells[spalte, 0] for spalte in range(grid.col_count)]
    daten = {
        nummer: _spalte_lesen(modell.spalte(nummer)[1:], pd)
        for nummer in range(grid.col_count)
    }
    df = pd.DataFrame(daten)
    df.columns = spalten
    return df


def _spalte_lesen(texte: list[str], pd: Any) -> Any:
    """Die Zellen einer Spalte als Zahlen, wenn alle Zahlen sind (oder
    leer), sonst unverändert als Text."""
    gefuellt = [t.strip() for t in texte if t.strip()]
    if not gefuellt or any(_FUEHRENDE_NULL.match(t) for t in gefuellt):
        return texte
    if all(_ganzzahlig(t) for t in gefuellt):
        # Die Ziffern selbst und nicht über `zahl()`: ein `float` hat
        # nur 15 bis 17 gültige Stellen, und aus 12345678901234567890
        # würde 12345678901234567168.
        ganz = [
            int(t.strip().replace(" ", "").replace(".", ""))
            if t.strip() else None
            for t in texte
        ]
        if any(w is not None and abs(w) > _GROESSTE_GANZZAHL for w in ganz):
            return texte
        # Mit Lücken braucht eine ganzzahlige Spalte den Typ „Int64“,
        # der fehlende Werte kennt; `int64` kann das nicht.
        typ = "Int64" if None in ganz else "int64"
        return pd.array(ganz, dtype=typ)
    werte: list[float | None] = []
    for t in texte:
        if not t.strip():
            werte.append(None)
            continue
        try:
            werte.append(_zelle_lesen(t.strip()))
        except ValueError:
            return texte
    return pd.array(werte, dtype="float64")


def _zelle_lesen(zelltext: str) -> float:
    """Die Zahl in einer Zelle, auch in der Schreibweise „2,5 · 10^21“,
    die `zahl()` nicht kennt."""
    from pcl.zahlen import zahl

    treffer = _ZEHNERPOTENZ.fullmatch(zelltext)
    if treffer:
        mantisse = treffer[1].replace(",", ".")
        return float(f"{mantisse}e{treffer[2]}")
    return zahl(zelltext)


def _ganzzahlig(zelltext: str) -> bool:
    """Ob der Text eine ganze Zahl ohne Nachkommastellen ist, auch mit
    Tausenderpunkten wie „1.000“."""
    bereinigt = zelltext.strip().replace(" ", "")
    return re.fullmatch(r"[+-]?(\d+|[1-9]\d{0,2}(\.\d{3})+)", bereinigt) is not None
