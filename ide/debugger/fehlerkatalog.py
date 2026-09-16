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

import builtins
import importlib
import re
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any

from ide.debugger.eigener_code import ist_eigener_code

_STAPEL_ZEILE_MUSTER = re.compile(
    r'^  File "(?P<datei>[^"]+)", line (?P<zeile>\d+), in (?P<name>.+)$'
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
    # exc.filename ist nur gesetzt, wenn Python die Ausnahme selbst
    # erzeugt hat - beim DAP-Nachbau (fehlermeldung_aus_dap_erzeugen())
    # fehlt es, str(exc) enthält den Pfad aber ohnehin schon als Text.
    was = f"Die Datei {exc.filename!r} wurde nicht gefunden." if exc.filename else str(exc)
    return (
        "Datei nicht gefunden",
        was,
        "Stimmt der Pfad? Ist er relativ zum aktuellen Arbeitsverzeichnis gemeint?",
    )


def _permission_error(exc: PermissionError) -> tuple[str, str, str]:
    was = f"Auf {exc.filename!r} besteht kein Zugriff." if exc.filename else str(exc)
    return (
        "Kein Zugriff auf die Datei",
        was,
        "Ist die Datei noch in einem anderen Programm (z. B. Excel) geöffnet? Sind "
        "die Schreibrechte vorhanden?",
    )


def _unicode_decode_error(exc: UnicodeDecodeError) -> tuple[str, str, str]:
    was = f"Die Datei lässt sich nicht als {exc.encoding} lesen." if exc.encoding else str(exc)
    return (
        "Datei mit falschem Zeichensatz gelesen",
        was,
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


def _katalog_eintrag_fuer_klasse(
    klasse: type[BaseException],
) -> Callable[[BaseException], tuple[str, str, str]] | None:
    for basisklasse in klasse.__mro__:
        if basisklasse in _KATALOG:
            return _KATALOG[basisklasse]
    return None


def _katalog_eintrag(
    exc: BaseException,
) -> Callable[[BaseException], tuple[str, str, str]] | None:
    return _katalog_eintrag_fuer_klasse(type(exc))


def _wo_quelltext_markierung(tb: TracebackType | None) -> tuple[str, str | None, str | None]:
    stack = traceback.extract_tb(tb)
    eigene = [fs for fs in stack if ist_eigener_code(fs.filename)]
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


class _DapAusnahme:
    """Attrappe für eine Ausnahme aus einer DAP-`exceptionInfo`-Antwort
    (Abschnitt 8.1: unbehandelte Ausnahme im per DAP verbundenen
    Schülerprogramm-Prozess – dort gibt es kein lokales Exception-Objekt,
    nur Text). Trägt nur die Felder, die die Katalogfunktionen oben
    tatsächlich lesen (`str(exc)`, `.name`, `.filename`, `.encoding`,
    `.args`, `.msg`), ohne über den – bei manchen Typen wie
    `UnicodeDecodeError` mehrargumentigen – echten Exception-Konstruktor
    zu gehen."""

    def __init__(self, nachricht: str) -> None:
        self._nachricht = nachricht
        self.name: str | None = None
        self.filename: str | None = None
        self.encoding: str | None = None
        self.args = (nachricht,)
        self.msg = nachricht

    def __str__(self) -> str:
        return self._nachricht


def _exception_klasse_aufloesen(exception_id: str) -> type[BaseException] | None:
    """Löst einen DAP-`exceptionId`-String (z. B. `"ZeroDivisionError"`
    oder `"json.decoder.JSONDecodeError"`) auf die tatsächliche Klasse
    auf, damit dieselbe MRO-Katalogsuche wie bei echten Ausnahmen greift
    (auch unregistrierte Unterklassen finden über ihre Basisklasse einen
    Eintrag, siehe `fehlermeldung_erzeugen`)."""
    eingebaut = getattr(builtins, exception_id, None)
    if isinstance(eingebaut, type) and issubclass(eingebaut, BaseException):
        return eingebaut
    if "." not in exception_id:
        return None
    modulname, _, klassenname = exception_id.rpartition(".")
    try:
        modul = importlib.import_module(modulname)
    except ImportError:
        return None
    klasse = getattr(modul, klassenname, None)
    return klasse if isinstance(klasse, type) and issubclass(klasse, BaseException) else None


def _dap_stapel_parsen(
    text: str,
) -> list[tuple[str, int, str, str | None, str | None]]:
    """Zerlegt den von `debugpy` gelieferten Text-Stacktrace
    (`exceptionInfo`-Antwort, `details.stackTrace`) in (Datei, Zeile,
    Methode, Quelltext, Karett-Markierung)-Tupel – dasselbe, was
    `traceback.extract_tb()`/`format_frame_summary()` für eine lokale
    Ausnahme liefern, nur aus reinem Text statt einem echten Traceback-
    Objekt gewonnen. Jeder „File …“-Zeile folgt im selben Format wie
    Pythons eigene Ausgabe die Quellzeile, optional darunter eine
    `^`/`~`-Karett-Zeile (Python 3.11+)."""
    zeilen = text.split("\n")
    frames: list[tuple[str, int, str, str | None, str | None]] = []
    i = 0
    while i < len(zeilen):
        treffer = _STAPEL_ZEILE_MUSTER.match(zeilen[i])
        if treffer is None:
            i += 1
            continue
        quelltext = zeilen[i + 1].strip() if i + 1 < len(zeilen) else None
        markierung = None
        naechste = zeilen[i + 2] if i + 2 < len(zeilen) else ""
        if naechste.strip() and set(naechste.strip()) <= set("^~"):
            markierung = naechste
        frames.append(
            (
                treffer.group("datei"),
                int(treffer.group("zeile")),
                treffer.group("name"),
                quelltext,
                markierung,
            )
        )
        i += 3 if markierung else 2
    return frames


def fehlermeldung_aus_dap_erzeugen(exception_info: dict[str, Any]) -> Fehlermeldung | None:
    """Wie `fehlermeldung_erzeugen()`, aber für eine unbehandelte Ausnahme
    im per DAP verbundenen Schülerprogramm-Prozess: `exception_info` ist
    die Antwort auf den DAP-`exceptionInfo`-Request (Abschnitt 8.1).
    `None`, wenn `exceptionId` keiner bekannten Klasse zugeordnet werden
    kann oder kein Katalogeintrag passt."""
    exception_id = exception_info.get("exceptionId", "")
    klasse = _exception_klasse_aufloesen(exception_id)
    if klasse is None:
        return None
    eintrag = _katalog_eintrag_fuer_klasse(klasse)
    if eintrag is None:
        return None

    details = exception_info.get("details") or {}
    nachricht = details.get("message") or exception_info.get("description") or ""
    kurz, was, pruefe = eintrag(_DapAusnahme(nachricht))

    # Achtung, anders herum als traceback.extract_tb(): debugpys
    # exceptionInfo-Stacktrace listet den tiefsten (innersten) Frame
    # zuerst, nicht zuletzt - "eigener Code" ist deshalb der erste
    # Treffer, nicht der letzte.
    stapel = _dap_stapel_parsen(details.get("stackTrace") or "")
    eigene = [f for f in stapel if ist_eigener_code(f[0])]
    ziel = eigene[0] if eigene else (stapel[0] if stapel else None)
    if ziel is not None:
        datei, zeile, methode, quelltext, markierung = ziel
        wo = f"{Path(datei).name}, Zeile {zeile}, in {methode}"
    else:
        wo, quelltext, markierung = "?", None, None

    art = "Syntaxfehler" if issubclass(klasse, SyntaxError) else "Laufzeitfehler"
    ueberschrift = f"{art}: {kurz} ({klasse.__name__})"

    return Fehlermeldung(
        ueberschrift=ueberschrift,
        wo=wo,
        quelltext=quelltext,
        markierung=markierung,
        was=was,
        pruefe=pruefe,
    )
