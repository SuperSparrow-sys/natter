"""`.lfm`-Parser (Abschnitt 15): zeilenbasierter rekursiver Parser für
das Lazarus-Formulartextformat (`object Name: Klasse … end`).

Geprüft gegen alle 19 echten `.lfm`-Dateien in `tests/daten/lfm/`
(siehe `tests/test_lfm_parser.py`) – das reale Format ist überraschend
regelmäßig: eine Anweisung pro Zeile, keine mehrzeiligen String-
Verkettungen, keine mehrzeiligen Mengen (`[...]` steht immer komplett
auf einer Zeile). Nur Sammlungen (`(...)`, z. B. `Items.Strings`) und
Binärblöcke (`{...}`, z. B. `Picture.Data`) spannen mehrere Zeilen.

Liefert eine reine Datenstruktur (`dict`), keine `pcl`-Objekte – die
Zuordnung nach `.pfm` übernimmt `ide.import_lfm.zuordnung`.
"""

from __future__ import annotations

import re
from typing import Any

_OBJEKT_MUSTER = re.compile(r"^\s*object\s+(\w+)\s*:\s*(\w+)\s*$")
_EIGENSCHAFT_MUSTER = re.compile(r"^\s*([\w.]+)\s*=\s*(.*)$")


class LfmParserError(ValueError):
    """Der Text ist kein gültiges `.lfm`-Format (Abschnitt 15)."""


def parse_lfm(text: str) -> dict[str, Any]:
    """Parst den Inhalt einer `.lfm`-Datei. Liefert `{"name", "class",
    "properties", "children"}` für das Wurzelobjekt (üblicherweise das
    Formular selbst)."""
    zeilen = text.splitlines()
    index = _naechste_inhaltszeile(zeilen, 0)
    if index >= len(zeilen) or not _OBJEKT_MUSTER.match(zeilen[index]):
        raise LfmParserError("Erwartet eine 'object Name: Klasse'-Zeile am Anfang.")
    objekt, index = _objekt_parsen(zeilen, index)
    return objekt


def _naechste_inhaltszeile(zeilen: list[str], index: int) -> int:
    while index < len(zeilen) and not zeilen[index].strip():
        index += 1
    return index


def _objekt_parsen(zeilen: list[str], index: int) -> tuple[dict[str, Any], int]:
    treffer = _OBJEKT_MUSTER.match(zeilen[index])
    if treffer is None:
        raise LfmParserError(f"Erwartete 'object Name: Klasse', erhalten: {zeilen[index]!r}")
    name, klasse = treffer.group(1), treffer.group(2)
    index += 1

    eigenschaften: dict[str, Any] = {}
    kinder: list[dict[str, Any]] = []
    while True:
        if index >= len(zeilen):
            raise LfmParserError(f"'end' für Objekt {name!r} fehlt (Dateiende erreicht).")
        zeile = zeilen[index]
        if not zeile.strip():
            index += 1
            continue
        if zeile.strip() == "end":
            index += 1
            break
        if _OBJEKT_MUSTER.match(zeile):
            kind, index = _objekt_parsen(zeilen, index)
            kinder.append(kind)
            continue
        eig_treffer = _EIGENSCHAFT_MUSTER.match(zeile)
        if eig_treffer is None:
            raise LfmParserError(f"Unerwartete Zeile in Objekt {name!r}: {zeile!r}")
        schluessel, rohwert = eig_treffer.groups()
        wert, index = _wert_parsen(rohwert, zeilen, index + 1)
        eigenschaften[schluessel] = wert

    return {"name": name, "class": klasse, "properties": eigenschaften, "children": kinder}, index


def _wert_parsen(rohwert: str, zeilen: list[str], index: int) -> tuple[Any, int]:
    rohwert = rohwert.strip()

    if rohwert == "(":
        werte: list[Any] = []
        while zeilen[index].strip() != ")":
            werte.append(_skalar_parsen(zeilen[index].strip()))
            index += 1
        return werte, index + 1

    if rohwert == "{":
        hex_zeilen: list[str] = []
        while zeilen[index].strip() != "}":
            hex_zeilen.append(zeilen[index].strip())
            index += 1
        return {"binaer": "".join(hex_zeilen)}, index + 1

    if rohwert.startswith("[") and rohwert.endswith("]"):
        innen = rohwert[1:-1].strip()
        werte = [teil.strip() for teil in innen.split(",")] if innen else []
        return werte, index

    return _skalar_parsen(rohwert), index


def _skalar_parsen(text: str) -> Any:
    text = text.strip()
    if len(text) >= 2 and text.startswith("'") and text.endswith("'"):
        return text[1:-1].replace("''", "'")
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text  # Bezeichner/Enum-Konstante, z. B. clBlack, stCircle, b_startClick
