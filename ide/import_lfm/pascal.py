"""Einfacher Extraktor für Pascal-Methodenrümpfe aus einer `.pas`-Unit
(Abschnitt 15, Arbeitspaket M8, Schritt 3).

Beim Import eines Lazarus-Formulars verweist die `.lfm` nur auf die
Namen der Ereignis-Handler (`OnClick = b_startClick`); der eigentliche
Pascal-Code steht in der gleichnamigen `.pas`. Dieses Modul liest die
Rümpfe heraus, damit `ide.import_lfm.unit` sie als Kommentar in die neu
angelegte Python-Methode übernehmen kann – der Kurs übersetzt den Code
anschließend von Hand, das ist ausdrücklich Teil der Umstiegsaufgabe
(Abschnitt 15: „Hilfe beim Umstieg, keine automatische Übersetzung“).

Umfang, bewusst eingeschränkt: Pascal wird nicht wirklich geparst,
sondern nur die `begin`/`end`-Verschachtelung gezählt, nachdem
Zeichenketten und Kommentare entfernt wurden. Das deckt den
Unterrichtscode in `tests/daten/lfm/` vollständig ab. Nicht unterstützt
sind lokal (innerhalb einer Methode) deklarierte Unterprogramme – deren
`begin`/`end` würde mitgezählt und der Rumpf zu lang geraten.
"""

from __future__ import annotations

import re
from pathlib import Path

# `procedure TForm1.b_startClick(Sender: TObject);` bzw. `function ...`
_KOPF_MUSTER = re.compile(r"^\s*(?:procedure|function)\s+(\w+)\.(\w+)\b", re.IGNORECASE)
_IMPLEMENTATION_MUSTER = re.compile(r"^\s*implementation\s*$", re.IGNORECASE)

# Schlüsselwörter, die ein zusätzliches `end` verlangen. `if`/`while`/
# `for` gehören nicht dazu (sie enden ohne `end`), `repeat` endet mit
# `until`.
_OEFFNER = ("begin", "case", "try", "record", "asm")
_WORT_MUSTER = re.compile(r"[A-Za-z_]\w*")


def _code_ohne_text(zeile: str, in_block_kommentar: str | None) -> tuple[str, str | None]:
    """Entfernt Zeichenketten (`'...'`) und Kommentare (`//`, `{...}`,
    `(*...*)`) aus einer Zeile, damit `begin`/`end` darin nicht
    mitgezählt werden. `in_block_kommentar` ist `None`, `"{"` oder
    `"(*"` und trägt den Zustand über Zeilengrenzen weiter."""
    ergebnis: list[str] = []
    index = 0
    laenge = len(zeile)
    while index < laenge:
        if in_block_kommentar == "{":
            ende = zeile.find("}", index)
            if ende == -1:
                return "".join(ergebnis), in_block_kommentar
            index = ende + 1
            in_block_kommentar = None
            continue
        if in_block_kommentar == "(*":
            ende = zeile.find("*)", index)
            if ende == -1:
                return "".join(ergebnis), in_block_kommentar
            index = ende + 2
            in_block_kommentar = None
            continue

        zeichen = zeile[index]
        if zeichen == "'":
            index += 1
            while index < laenge:
                if zeile[index] == "'":
                    # '' ist ein einzelnes Hochkomma innerhalb des Texts
                    if index + 1 < laenge and zeile[index + 1] == "'":
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            ergebnis.append(" ")
            continue
        if zeile.startswith("//", index):
            break
        if zeichen == "{":
            in_block_kommentar = "{"
            index += 1
            continue
        if zeile.startswith("(*", index):
            in_block_kommentar = "(*"
            index += 2
            continue

        ergebnis.append(zeichen)
        index += 1

    return "".join(ergebnis), in_block_kommentar


def _tiefe_aendern(code: str, tiefe: int, begonnen: bool) -> tuple[int, bool]:
    for wort in _WORT_MUSTER.findall(code):
        klein = wort.lower()
        if klein in _OEFFNER:
            tiefe += 1
            begonnen = True
        elif klein == "end":
            tiefe -= 1
    return tiefe, begonnen


def _ohne_gemeinsame_einrueckung(zeilen: list[str]) -> list[str]:
    inhalt = [zeile for zeile in zeilen if zeile.strip()]
    if not inhalt:
        return []
    breite = min(len(zeile) - len(zeile.lstrip()) for zeile in inhalt)
    return [zeile[breite:].rstrip() if zeile.strip() else "" for zeile in zeilen]


def pas_text_lesen(pfad: Path) -> str:
    """Liest eine `.pas`-Datei. Lazarus schreibt sie je nach Version als
    UTF-8 oder als Windows-ANSI (CP1252); alle Dateien in
    `tests/daten/lfm/` sind UTF-8, die Rückfallebene deckt ältere
    Schülerprojekte ab."""
    rohdaten = Path(pfad).read_bytes()
    try:
        return rohdaten.decode("utf-8")
    except UnicodeDecodeError:
        return rohdaten.decode("cp1252", errors="replace")


def prozedur_ruempfe_lesen(pas_text: str) -> dict[str, list[str]]:
    """Liefert `{"b_startClick": ["begin", "  ...", "end;"], …}` – je
    Methode der `implementation`-Abschnitt ihres Rumpfes (einschließlich
    eines eigenen `var`-Blocks), gemeinsame Einrückung entfernt.

    Der Schlüssel ist der reine Methodenname ohne Klassenpräfix, also
    genau der Name, den die `.lfm` in `OnClick = …` nennt."""
    zeilen = pas_text.splitlines()
    start = 0
    for index, zeile in enumerate(zeilen):
        if _IMPLEMENTATION_MUSTER.match(zeile):
            start = index + 1
            break

    ruempfe: dict[str, list[str]] = {}
    index = start
    block_kommentar: str | None = None
    while index < len(zeilen):
        code, block_kommentar = _code_ohne_text(zeilen[index], block_kommentar)
        treffer = _KOPF_MUSTER.match(code)
        if treffer is None:
            index += 1
            continue

        methodenname = treffer.group(2)
        rumpf: list[str] = []
        index += 1
        tiefe = 0
        begonnen = False
        while index < len(zeilen):
            code, block_kommentar = _code_ohne_text(zeilen[index], block_kommentar)
            if not begonnen and _KOPF_MUSTER.match(code):
                break  # Vorwärtsdeklaration ohne Rumpf
            rumpf.append(zeilen[index])
            tiefe, begonnen = _tiefe_aendern(code, tiefe, begonnen)
            index += 1
            if begonnen and tiefe <= 0:
                break
        if begonnen:
            ruempfe[methodenname] = _ohne_gemeinsame_einrueckung(rumpf)

    return ruempfe


def rumpf_als_kommentar(rumpf: list[str], *, einrueckung: str = "        ") -> list[str]:
    """Wandelt einen Pascal-Rumpf in Python-Kommentarzeilen um. Leere
    Zeilen werden zu `#` ohne nachfolgendes Leerzeichen, damit `ruff
    format`/`ruff check` keine Leerzeichen am Zeilenende bemängeln."""
    kommentar: list[str] = []
    for zeile in rumpf:
        kommentar.append(f"{einrueckung}# {zeile}" if zeile.strip() else f"{einrueckung}#")
    return kommentar
