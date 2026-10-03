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


def _zeile(zeilen: list[str], index: int, was: str) -> str:
    if index >= len(zeilen):
        raise LfmParserError(f"Das Ende {was} fehlt (Dateiende erreicht).")
    return zeilen[index].strip()


def _zeichenkette(text: str) -> tuple[str, bool] | None:
    """Liest eine Zeichenkette in Pascal-Schreibweise: Teile in
    Hochkommas, dazwischen Zeichen als `#13` oder `#$0D`, ohne
    Trennzeichen aneinandergehängt. Liefert den Text und ob die Zeile
    mit `+` endet, also in der nächsten weitergeht - oder `None`, wenn
    `text` keine Zeichenkette ist (Punkt 549)."""
    teile: list[str] = []
    stelle = 0
    text = text.strip()
    if not text or text[0] not in "'#":
        return None
    while stelle < len(text):
        zeichen = text[stelle]
        if zeichen == "'":
            ende = stelle + 1
            stueck: list[str] = []
            while True:
                if ende >= len(text):
                    return None
                if text[ende] == "'":
                    if ende + 1 < len(text) and text[ende + 1] == "'":
                        stueck.append("'")
                        ende += 2
                        continue
                    break
                stueck.append(text[ende])
                ende += 1
            teile.append("".join(stueck))
            stelle = ende + 1
        elif zeichen == "#":
            treffer = re.match(r"#(\$[0-9A-Fa-f]+|\d+)", text[stelle:])
            if treffer is None:
                return None
            zahl = treffer.group(1)
            teile.append(chr(int(zahl[1:], 16) if zahl.startswith("$") else int(zahl)))
            stelle += treffer.end()
        elif text[stelle:].strip() == "+":
            return "".join(teile), True
        elif zeichen.isspace():
            stelle += 1
        else:
            return None
    return "".join(teile), False


def _zeilenumbruch_vereinheitlichen(text: str) -> str:
    # `#13#10` ist der Zeilenumbruch von Windows; in Natter steht
    # dafür wie in Python ein einzelnes Zeilenende.
    return text.replace(chr(13) + chr(10), chr(10))


def _zeichenkette_lesen(
    rohwert: str, zeilen: list[str], index: int
) -> tuple[str, int] | None:
    """Eine Zeichenkette samt Fortsetzungszeilen (`+` am Ende)."""
    gelesen = _zeichenkette(rohwert)
    if gelesen is None:
        return None
    text, weiter = gelesen
    while weiter:
        folge = _zeichenkette(_zeile(zeilen, index, "einer Zeichenkette"))
        if folge is None:
            raise LfmParserError(
                f"Nach '+' wird eine Zeichenkette erwartet: {zeilen[index]!r}"
            )
        text += folge[0]
        weiter = folge[1]
        index += 1
    return _zeilenumbruch_vereinheitlichen(text), index


def _wert_parsen(rohwert: str, zeilen: list[str], index: int) -> tuple[Any, int]:
    rohwert = rohwert.strip()

    if rohwert == "(":
        werte: list[Any] = []
        while True:
            eintrag = _zeile(zeilen, index, "einer Liste")
            index += 1
            if eintrag == ")":
                return werte, index
            # Die schließende Klammer darf auch hinter dem letzten
            # Eintrag stehen: `'b')`.
            schluss = eintrag.endswith(")") and _zeichenkette(eintrag[:-1]) is not None
            if schluss:
                eintrag = eintrag[:-1]
            gelesen = _zeichenkette_lesen(eintrag, zeilen, index)
            if gelesen is not None:
                wert, index = gelesen
                werte.append(wert)
            else:
                werte.append(_skalar_parsen(eintrag))
            if schluss:
                return werte, index

    if rohwert == "{":
        hex_zeilen: list[str] = []
        while True:
            stueck = _zeile(zeilen, index, "eines Binärblocks")
            index += 1
            if stueck == "}":
                return {"binaer": "".join(hex_zeilen)}, index
            if stueck.endswith("}"):
                hex_zeilen.append(stueck[:-1].strip())
                return {"binaer": "".join(hex_zeilen)}, index
            hex_zeilen.append(stueck)

    gelesen = _zeichenkette_lesen(rohwert, zeilen, index)
    if gelesen is not None:
        return gelesen

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
