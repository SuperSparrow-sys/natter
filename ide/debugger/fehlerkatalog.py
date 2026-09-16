"""Fehlerkatalog: fester, von Hand gepflegter Katalog für Wo/Was/Prüfe-
Meldungen bei unbehandelten Ausnahmen (Abschnitt 8.3–8.5). Deterministisch,
keine KI – jede Meldung kommt aus einer festen Zuordnung Exception-Typ →
Erklärungstext.

„Was“ wird bewusst nie aus `traceback.format_exception_only()` gebaut,
sondern immer aus `str(exc)`/strukturierten Attributen (`exc.name`,
`exc.filename`, …) – dort hängt Python (ab 3.12) keine „Did you mean …?“-
Vorschläge an, die Abschnitt 8.4 verbietet.

`Wo`/Quelltext/Karett-Markierung kommen dagegen aus
`traceback.StackSummary.format_frame_summary()` für genau den tiefsten
Frame, der zu eigenem Code gehört (nicht `pcl`/Qt/Standardbibliothek) –
das liefert die Spaltenmarkierung ab Python 3.11 automatisch korrekt
ausgerichtet, ohne sie selbst nachzubauen.
"""

from __future__ import annotations

import re
import sysconfig
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType

_STDLIB_PFADE = tuple(
    Path(p).resolve()
    for p in {sysconfig.get_paths()["stdlib"], sysconfig.get_paths()["platstdlib"]}
)


@dataclass(frozen=True)
class Fehlermeldung:
    ueberschrift: str
    wo: str
    quelltext: str | None
    markierung: str | None
    was: str
    pruefe: str

    def als_text(self) -> str:
        zeilen = [self.ueberschrift, "", f"Wo:   {self.wo}"]
        if self.quelltext is not None:
            zeilen.append(f"          {self.quelltext}")
        if self.markierung is not None:
            zeilen.append(f"          {self.markierung}")
        zeilen.append(f"Was:  {self.was}")
        zeilen.append(f"Prüfe: {self.pruefe}")
        return "\n".join(zeilen)


def _ist_eigener_code(dateiname: str) -> bool:
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


def _name_ermitteln(exc: BaseException) -> str | None:
    name = getattr(exc, "name", None)
    if name:
        return name
    treffer = re.search(r"'([^']+)'", str(exc))
    return treffer.group(1) if treffer else None


# Jeder Katalogeintrag liefert (Kurzbeschreibung für die Überschrift, Was,
# Prüfe) – siehe Abschnitt 8.3: "Laufzeitfehler: <Kurz> (<Exception-Typ>)".


def _zero_division(exc: ZeroDivisionError) -> tuple[str, str, str]:
    return (
        "Division durch 0",
        "Es wurde durch 0 geteilt.",
        "Welche Werte kann der Teiler annehmen? Wird der Fall 0 vorher abgefangen?",
    )


def _unbound_local(exc: UnboundLocalError) -> tuple[str, str, str]:
    name = _name_ermitteln(exc)
    ziel = f"„{name}“" if name else "Die Variable"
    return (
        "Lokale Variable vor Zuweisung verwendet",
        f"{ziel} wurde in dieser Funktion verändert, bevor ihr ein Wert zugewiesen "
        "wurde – lokale und globale Variablen mit demselben Namen sind unterschiedliche "
        "Variablen.",
        "Soll wirklich eine neue lokale Variable entstehen, oder war die globale "
        "gemeint (dann `global` verwenden)?",
    )


def _name_error(exc: NameError) -> tuple[str, str, str]:
    name = _name_ermitteln(exc)
    ziel = f"„{name}“" if name else "Der verwendete Name"
    return (
        "Unbekannter Name",
        f"{ziel} ist an dieser Stelle nicht bekannt.",
        "Ist die Schreibweise korrekt? Wurde die Variable vorher zugewiesen? Ist die "
        "Unit eingebunden?",
    )


def _attribute_error(exc: AttributeError) -> tuple[str, str, str]:
    name = _name_ermitteln(exc)
    if name and name.startswith("__") and not name.endswith("__"):
        return (
            "Zugriff auf gekapseltes Attribut",
            f"„{name}“ beginnt mit zwei Unterstrichen und ist damit von außerhalb der "
            "Klasse nicht direkt zugreifbar (Namensumbildung/Kapselung).",
            "Gibt es eine öffentliche Methode oder Eigenschaft, die stattdessen "
            "genutzt werden sollte?",
        )
    ziel = f"„{name}“" if name else "Die verwendete Eigenschaft"
    return (
        "Unbekannte Eigenschaft",
        f"{ziel} existiert bei diesem Objekt nicht.",
        "Ist der Name richtig geschrieben? Ist es wirklich der erwartete Objekttyp?",
    )


def _type_error(exc: TypeError) -> tuple[str, str, str]:
    return (
        "Unpassender Datentyp",
        str(exc),
        "Passen die verwendeten Datentypen zueinander? Stimmt die Anzahl der Argumente?",
    )


def _value_error(exc: ValueError) -> tuple[str, str, str]:
    text = str(exc)
    if "," in text:
        return (
            "Ungültiger Wert",
            text,
            "Python nutzt einen Dezimalpunkt statt eines Dezimalkommas (3.5 statt "
            "3,5) – wurde das beachtet?",
        )
    return (
        "Ungültiger Wert",
        text,
        "Welcher Wert wurde tatsächlich übergeben, und passt er zum erwarteten Typ?",
    )


def _index_error(exc: IndexError) -> tuple[str, str, str]:
    return (
        "Index außerhalb des gültigen Bereichs",
        str(exc),
        "Welcher Index wurde verwendet, und wie viele Einträge hat die Liste/Tabelle "
        "wirklich?",
    )


def _key_error(exc: KeyError) -> tuple[str, str, str]:
    schluessel = exc.args[0] if exc.args else "?"
    return (
        "Unbekannter Schlüssel",
        f"Der Schlüssel {schluessel!r} existiert nicht.",
        "Welche Schlüssel gibt es wirklich? Tippfehler oder falsche Groß-/"
        "Kleinschreibung?",
    )


def _file_not_found(exc: FileNotFoundError) -> tuple[str, str, str]:
    return (
        "Datei nicht gefunden",
        f"Die Datei {exc.filename!r} wurde nicht gefunden.",
        "Stimmt der Pfad? Ist er relativ zum aktuellen Arbeitsverzeichnis gemeint?",
    )


def _permission_error(exc: PermissionError) -> tuple[str, str, str]:
    return (
        "Kein Zugriff auf die Datei",
        f"Auf {exc.filename!r} besteht kein Zugriff.",
        "Ist die Datei noch in einem anderen Programm (z. B. Excel) geöffnet? Sind "
        "die Schreibrechte vorhanden?",
    )


def _unicode_decode_error(exc: UnicodeDecodeError) -> tuple[str, str, str]:
    return (
        "Datei mit falschem Zeichensatz gelesen",
        f"Die Datei lässt sich nicht als {exc.encoding} lesen.",
        "Welchen Zeichensatz hat die Datei wirklich (z. B. Windows-1252 statt UTF-8)?",
    )


def _syntax_error(exc: SyntaxError) -> tuple[str, str, str]:
    was = exc.msg if exc.msg else str(exc)
    return (
        "Ungültige Quelltextstruktur",
        was,
        "Fehlt ein Doppelpunkt am Blockanfang? Stimmt die Einrückung? Python nutzt "
        "Einrückung statt begin…end.",
    )


# Nachschlagen läuft über die MRO der tatsächlichen Ausnahme (siehe
# _katalog_eintrag), die Reihenfolge hier ist deshalb ohne Bedeutung.
_KATALOG: dict[type[BaseException], Callable[[BaseException], tuple[str, str, str]]] = {
    ZeroDivisionError: _zero_division,
    UnboundLocalError: _unbound_local,
    NameError: _name_error,
    AttributeError: _attribute_error,
    TypeError: _type_error,
    ValueError: _value_error,
    IndexError: _index_error,
    KeyError: _key_error,
    FileNotFoundError: _file_not_found,
    PermissionError: _permission_error,
    UnicodeDecodeError: _unicode_decode_error,
    IndentationError: _syntax_error,
    SyntaxError: _syntax_error,
}


def _katalog_eintrag(
    exc: BaseException,
) -> Callable[[BaseException], tuple[str, str, str]] | None:
    for klasse in type(exc).__mro__:
        if klasse in _KATALOG:
            return _KATALOG[klasse]
    return None


def _wo_quelltext_markierung(tb: TracebackType | None) -> tuple[str, str | None, str | None]:
    stack = traceback.extract_tb(tb)
    eigene = [fs for fs in stack if _ist_eigener_code(fs.filename)]
    ziel = eigene[-1] if eigene else (stack[-1] if stack else None)
    if ziel is None:
        return "?", None, None

    formatiert = stack.format_frame_summary(ziel).rstrip("\n").split("\n")
    quelltext = formatiert[1].strip() if len(formatiert) > 1 else None
    markierung = formatiert[2] if len(formatiert) > 2 else None

    wo = f"{Path(ziel.filename).name}, Zeile {ziel.lineno}, in {ziel.name}"
    return wo, quelltext, markierung


def fehlermeldung_erzeugen(exc: BaseException) -> Fehlermeldung | None:
    """Baut die Wo/Was/Prüfe-Meldung für `exc` (Abschnitt 8.3). `None`,
    wenn kein Katalogeintrag zum Exception-Typ passt (Abschnitt 8.5 ist
    ein MVP-Auszug, kein vollständiger Katalog)."""
    eintrag = _katalog_eintrag(exc)
    if eintrag is None:
        return None

    kurz, was, pruefe = eintrag(exc)
    wo, quelltext, markierung = _wo_quelltext_markierung(exc.__traceback__)

    art = "Syntaxfehler" if isinstance(exc, SyntaxError) else "Laufzeitfehler"
    ueberschrift = f"{art}: {kurz} ({type(exc).__name__})"

    return Fehlermeldung(
        ueberschrift=ueberschrift,
        wo=wo,
        quelltext=quelltext,
        markierung=markierung,
        was=was,
        pruefe=pruefe,
    )
