"""Jede Meldung sagt auch, was man tun kann (M11, Abschnitt 4:
„jede Meldung mit Lösungen“).

Der Nutzer hat es so formuliert: nicht nur dort, wo es leichtfällt –
eine Meldung ohne Lösungsteil ist ab jetzt ein Mangel. Diese Datei
hält drei Regeln fest, die beim Durchsehen des Bestands als die
lohnenden übriggeblieben sind. Jede hat einen Fund im Bestand, den sie
festnagelt:

1. **Jede Fehlermeldung kommt auf Deutsch an.** Gefunden: 22 von 27
   geprüften Schülerfehlern zeigten im Feld „Was“ den englischen
   Originaltext von Python („list index out of range“). Prüfbar ist das
   ohne Wörterbuch, weil `ide/debugger/fehlerkatalog.py` eine
   unübersetzte Meldung immer mit `ORIGINALMELDUNG_PRAEFIX`
   kennzeichnet: steht das Präfix nicht in der Meldung, ist sie
   übersetzt.
2. **Jeder Befund und jeder Hinweis trägt seinen Lösungsteil.** Weil
   ein einzelner Testfall nur die Regeln abdeckt, die er zufällig
   auslöst, prüft der Test stattdessen die Bauweise: in
   `ide/lint/regeln.py` und `ide/diagramm/hinweise.py` darf kein
   `Befund(…)`/`Hinweis(…)` mehr von Hand entstehen, sondern nur über
   die Hilfsfunktion, die den Lösungsteil erzwingt. Eine neue Regel
   ohne Lösung fällt damit auf, auch wenn niemand einen Testfall dafür
   schreibt.
3. **Keine Klammerform.** Gefunden: „3 Fund(e) vor dem Start“, „2
   Test(s), 1 nicht bestanden“, „5 Hinweis(e) im Importbericht“. Die
   Zielgruppe liest ganze Sätze leichter als Formulare;
   `ide/viewers/tabellen_ansicht.py` hat das für sich schon
   entschieden, der Rest der Oberfläche zieht hier nach.

Die didaktische Grenze aus dem Kopf von `docs/fehlerkatalog.yaml`
bleibt: „Lösung“ heißt Leitfrage, nicht korrigierter Code. Deshalb
prüft hier nichts auf einen bestimmten Wortlaut, sondern nur darauf,
dass der Teil überhaupt da ist.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from ide.debugger.fehlerkatalog import (
    _STANDARDMELDUNGEN,
    ORIGINALMELDUNG_PRAEFIX,
    fehlermeldung_erzeugen,
)
from ide.diagramm import hinweise as diagramm_hinweise
from ide.lint import pruefen as design_pruefen

WURZEL = Path(__file__).resolve().parents[1]


def _ausloesen(f):
    """Löst `f()` wirklich aus – ohne echten Traceback kann der Katalog
    kein „Wo“ ermitteln."""
    try:
        f()
    except BaseException as fehler:  # noqa: BLE001 - genau das wird hier geprüft
        return fehler
    raise AssertionError("f() hat keine Ausnahme ausgelöst")


# -- 1. Jede Fehlermeldung kommt auf Deutsch an ----------------------------

#: Absichtlich falsch benutzt: als Funktion aufgerufen, obwohl es eine
#: Zahl ist. Als Literal `(5)()` wuerde Python schon beim Uebersetzen
#: des Tests warnen.
_EINE_ZAHL = 5


def _f2(a, b):
    return a + b


def _zu_wenige_werte():
    a, b = [1]
    return a, b


def _zu_viele_werte():
    a, b = [1, 2, 3]
    return a, b


#: Fehler, die im Unterricht wirklich vorkommen. Die Liste ist der
#: Korpus, gegen den „auf Deutsch und mit Lösungsteil“ geprüft wird –
#: ein Test, der nur die drei Fälle nimmt, für die schon eine
#: Übersetzung existiert, bestätigt nur sich selbst.
KORPUS = [
    ("Liste zu kurz", lambda: [1, 2][5]),
    ("Text zu kurz", lambda: "abc"[9]),
    ("Tupel zu kurz", lambda: (1, 2)[7]),
    ("Zahl plus Text", lambda: 1 + "a"),
    ("Text plus Zahl", lambda: "a" + 1),
    ("Zahl mit eckigen Klammern", lambda: [1, 2, 3][0][0]),
    ("Zahl aufgerufen", lambda: _EINE_ZAHL()),
    ("len einer Zahl", lambda: len(5)),
    ("Schleife über eine Zahl", lambda: [x for x in 5]),
    ("Text mit Zahl verglichen", lambda: "a" < 1),
    ("int aus Buchstaben", lambda: int("abc")),
    ("float mit Dezimalkomma", lambda: float("3,5")),
    ("Aufruf mit zu wenigen Werten", lambda: _f2(1)),
    ("Aufruf mit zu vielen Werten", lambda: _f2(1, 2, 3)),
    ("Zuweisung mit zu wenigen Werten", _zu_wenige_werte),
    ("Zuweisung mit zu vielen Werten", _zu_viele_werte),
    ("remove ohne Treffer", lambda: [1, 2].remove(9)),
    ("index ohne Treffer", lambda: "abc".index("z")),
    ("fehlender Schlüssel", lambda: {"a": 1}["b"]),
    ("Datei fehlt", lambda: open("es_gibt_mich_wirklich_nicht.txt", encoding="utf-8")),
    ("Doppelpunkt fehlt", lambda: compile("if x\n  pass", "<t>", "exec")),
    ("Block nicht eingerückt", lambda: compile("if x:\npass", "<t>", "exec")),
    ("Text nicht geschlossen", lambda: compile("print('a", "<t>", "exec")),
    ("Zuweisung an eine Zahl", lambda: compile("1 = 2", "<t>", "exec")),
    ("Klammer nie geschlossen", lambda: compile("print(1", "<t>", "exec")),
    ("Klammer zu viel", lambda: compile("x = 1)", "<t>", "exec")),
    ("kaputte Funktionsdefinition", lambda: compile("def f(:\n pass", "<t>", "exec")),
    ("JSON kaputt", lambda: json.loads("das ist kein JSON")),
]

#: Wörter, die in einer Standardmeldung von Python vorkommen und in
#: keinem der deutschen Texte dieses Projekts. Sie sind die Notbremse
#: für den Fall, dass die Kennzeichnung über `ORIGINALMELDUNG_PRAEFIX`
#: einmal umgangen wird.
ENGLISCHE_VERRAETER = (
    "unsupported",
    "operand",
    "positional",
    "unpack",
    "iterable",
    "callable",
    "subscriptable",
    "concatenate",
    "unmatched",
    "unindent",
    "substring",
    "literal",
    "indented",
    "instances",
    "out of range",
    "not in list",
    "was never closed",
)


@pytest.mark.parametrize("bezeichnung,ausloeser", KORPUS, ids=[k[0] for k in KORPUS])
def test_haeufige_schuelerfehler_kommen_auf_deutsch_an(bezeichnung, ausloeser) -> None:
    meldung = fehlermeldung_erzeugen(_ausloesen(ausloeser))

    assert meldung is not None, f"{bezeichnung}: gar keine Meldung, also roher Traceback"
    assert ORIGINALMELDUNG_PRAEFIX not in meldung.was, (
        f"{bezeichnung}: unübersetzte Standardmeldung von Python – {meldung.was}"
    )
    kleingeschrieben = meldung.was.lower()
    for verraeter in ENGLISCHE_VERRAETER:
        assert verraeter not in kleingeschrieben, (
            f"{bezeichnung}: englisches Wort „{verraeter}“ in der Meldung – {meldung.was}"
        )


@pytest.mark.parametrize("bezeichnung,ausloeser", KORPUS, ids=[k[0] for k in KORPUS])
def test_jeder_schuelerfehler_sagt_auch_was_man_tun_kann(bezeichnung, ausloeser) -> None:
    meldung = fehlermeldung_erzeugen(_ausloesen(ausloeser))

    assert meldung is not None
    assert meldung.pruefe.strip(), f"{bezeichnung}: „Prüfe“ ist leer"
    # Eine Leitfrage, kein Befehl: der Katalog sagt, woran es liegen
    # kann, und nicht, welche Zeile hinzuschreiben ist
    # (docs/fehlerkatalog.yaml, Kopf).
    assert "?" in meldung.pruefe, f"{bezeichnung}: „Prüfe“ ist keine Leitfrage"


def test_unuebersetzte_meldung_wird_als_zitat_gekennzeichnet() -> None:
    """Die Kennzeichnung ist die Grundlage des Deutsch-Tests oben: sie
    muss wirklich greifen, sonst prüft er nichts."""

    def f():
        raise TypeError("some message python has never actually produced")

    meldung = fehlermeldung_erzeugen(_ausloesen(f))

    assert ORIGINALMELDUNG_PRAEFIX in meldung.was
    assert meldung.was.startswith("Die verwendeten Datentypen")


def test_pythons_namensvorschlaege_werden_auch_aus_syntaxfehlern_entfernt() -> None:
    """`SyntaxError.msg` trägt „Maybe you meant '==' instead of '='?“ –
    ein Vorschlag, den Abschnitt 8.4 verbietet."""
    meldung = fehlermeldung_erzeugen(_ausloesen(lambda: compile("1 = 2", "<t>", "exec")))

    assert "maybe you meant" not in meldung.was.lower()
    assert "did you mean" not in meldung.was.lower()


def test_datenbankfehler_bekommt_ueberhaupt_eine_meldung() -> None:
    """`NatterDatenbankError` erbt von `RuntimeError`, und für den gibt
    es keinen Katalogeintrag – bis M11 fiel die Suche über die MRO
    durch, und das Schülerprogramm zeigte einen rohen Traceback."""
    from pcl.errors import NatterDatenbankError

    def f():
        raise NatterDatenbankError("SQL-Fehler: no such table: kunden")

    meldung = fehlermeldung_erzeugen(_ausloesen(f))

    assert meldung is not None
    assert "kunden" in meldung.was
    assert "no such table" not in meldung.was
    assert meldung.pruefe.strip()


def test_dezimalpunkt_hinweis_nur_bei_einer_zahl_mit_komma() -> None:
    """Der Hinweis hing an „enthält der Meldungstext ein Komma?“ – und
    traf damit auch „not enough values to unpack (expected 2, got 1)“,
    wo er nichts zu suchen hat."""
    mit_komma = fehlermeldung_erzeugen(_ausloesen(lambda: float("3,5")))
    ohne_komma = fehlermeldung_erzeugen(_ausloesen(_zu_wenige_werte))

    assert "Dezimalkomma" in mit_komma.pruefe
    assert "Dezimalkomma" not in ohne_komma.pruefe


def test_jede_uebersetzte_standardmeldung_hat_was_und_pruefe() -> None:
    for eintrag in _STANDARDMELDUNGEN:
        assert eintrag.was.strip(), f"{eintrag.muster.pattern}: „Was“ ist leer"
        assert eintrag.pruefe.strip(), f"{eintrag.muster.pattern}: „Prüfe“ ist leer"
        assert "?" in eintrag.pruefe, f"{eintrag.muster.pattern}: „Prüfe“ ist keine Leitfrage"


def _katalogeintraege() -> list[dict[str, str]]:
    """Liest `docs/fehlerkatalog.yaml` ohne PyYAML – die Datei ist flach
    genug dafür, und eine Abhängigkeit nur für einen Test wäre keine
    wert (AGENTS.md, Abschnitt „Lizenzen von Abhängigkeiten“)."""
    eintraege: list[dict[str, str]] = []
    for zeile in (WURZEL / "docs" / "fehlerkatalog.yaml").read_text("utf-8").splitlines():
        if zeile.startswith("  - "):
            eintraege.append({})
            zeile = "    " + zeile[4:]
        if not eintraege or not zeile.startswith("    ") or zeile.lstrip().startswith("#"):
            continue
        schluessel, _, wert = zeile.strip().partition(": ")
        eintraege[-1][schluessel] = wert.strip().strip('"')
    return eintraege


def test_jeder_eintrag_im_fehlerkatalog_hat_ein_nicht_leeres_pruefe() -> None:
    eintraege = _katalogeintraege()

    assert len(eintraege) >= 15, f"Nur {len(eintraege)} Einträge gelesen - Parser kaputt?"
    for eintrag in eintraege:
        assert eintrag.get("was", "").strip(), f"{eintrag.get('id')}: „was“ fehlt"
        assert eintrag.get("pruefe", "").strip(), f"{eintrag.get('id')}: „pruefe“ fehlt"


# -- 2. Jeder Befund und jeder Hinweis trägt seinen Lösungsteil -------------


def _direkte_aufrufe(modul_pfad: Path, klasse: str, erlaubt_in: str) -> list[int]:
    """Zeilen, in denen `klasse(...)` außerhalb von `erlaubt_in`
    aufgerufen wird."""
    baum = ast.parse(modul_pfad.read_text(encoding="utf-8"))
    hilfsfunktion = next(
        (
            knoten
            for knoten in ast.walk(baum)
            if isinstance(knoten, ast.FunctionDef) and knoten.name == erlaubt_in
        ),
        None,
    )
    assert hilfsfunktion is not None, f"{modul_pfad.name}: {erlaubt_in}() gibt es nicht"
    erlaubte_zeilen = {
        knoten.lineno for knoten in ast.walk(hilfsfunktion) if hasattr(knoten, "lineno")
    }
    return [
        knoten.lineno
        for knoten in ast.walk(baum)
        if isinstance(knoten, ast.Call)
        and isinstance(knoten.func, ast.Name)
        and knoten.func.id == klasse
        and knoten.lineno not in erlaubte_zeilen
    ]


def test_design_pruefer_baut_jeden_befund_ueber_die_hilfsfunktion() -> None:
    """Nicht „die heutigen Regeln haben eine Lösung“, sondern „eine neue
    Regel kann gar keine ohne bekommen“: `_befund()` verlangt den
    Lösungsteil als Parameter."""
    zeilen = _direkte_aufrufe(WURZEL / "ide" / "lint" / "regeln.py", "Befund", "_befund")

    assert not zeilen, (
        f"ide/lint/regeln.py, Zeile(n) {zeilen}: Befund(...) von Hand gebaut – "
        "dabei fehlt der Lösungsteil. Stattdessen _befund(...) verwenden."
    )


def test_layout_hinweise_bauen_jeden_hinweis_ueber_die_hilfsfunktion() -> None:
    zeilen = _direkte_aufrufe(WURZEL / "ide" / "diagramm" / "hinweise.py", "Hinweis", "_hinweis")

    assert not zeilen, (
        f"ide/diagramm/hinweise.py, Zeile(n) {zeilen}: Hinweis(...) von Hand gebaut – "
        "dabei fehlt der Lösungsteil. Stattdessen _hinweis(...) verwenden."
    )


#: Ein Formular, das möglichst viele Regeln des Design-Prüfers auf
#: einmal auslöst.
UNSAUBERES_FORMULAR = {
    "name": "Form1",
    "type": "Form",
    "properties": {"width": 300, "height": 200},
    "children": [
        {"type": "Button", "name": "Button1", "properties": {"caption": "Button1"}},
        {
            "type": "Button",
            "name": "b_ok",
            "properties": {"left": 3, "top": 5, "width": 20, "height": 12},
        },
        {
            "type": "Edit",
            "name": "eingabe",
            "properties": {"left": 200, "top": 180, "width": 200, "height": 25},
        },
        {
            "type": "Label",
            "name": "l_titel",
            "properties": {"left": 8, "top": 120, "color": "#fefefe"},
        },
    ],
}


def test_jeder_befund_endet_mit_seinem_loesungsteil() -> None:
    befunde = design_pruefen(UNSAUBERES_FORMULAR)

    assert len(befunde) >= 5, "Das Testformular löst zu wenige Regeln aus"
    for befund in befunde:
        assert befund.loesung.strip(), f"{befund.regel}: kein Lösungsteil"
        assert befund.meldung.endswith(befund.loesung), (
            f"{befund.regel}: die Meldung endet nicht mit ihrem Lösungsteil – "
            "der Prüfungsmodus könnte ihn sonst nicht abschneiden"
        )


#: Ein Diagramm, das alle vier Layout-Regeln auf einmal auslöst.
UNSAUBERES_DIAGRAMM = {
    "page": {"size": "A4", "orientation": "portrait"},
    "shapes": [
        {"id": "a", "kind": "class", "x": 40, "y": 40, "w": 120, "h": 60, "name": "Ampel"},
        {"id": "b", "kind": "class", "x": 60, "y": 60, "w": 120, "h": 60, "name": "Auto"},
        {"id": "c", "kind": "class", "x": 40, "y": 400, "w": 8, "h": 8, "name": "Sehrlangername"},
        {"id": "d", "kind": "class", "x": -500, "y": 40, "w": 100, "h": 40, "name": "Weg"},
    ],
    "connectors": [{"id": "v1", "kind": "association", "from": "a", "to": "gibtsnicht"}],
}


def test_jeder_layout_hinweis_endet_mit_seinem_loesungsteil() -> None:
    hinweise = diagramm_hinweise.pruefen(UNSAUBERES_DIAGRAMM)

    gefundene_regeln = {hinweis.regel for hinweis in hinweise}
    assert gefundene_regeln == {
        "ueberlappung",
        "abgeschnittener_text",
        "loses_ende",
        "ausserhalb_der_seite",
    }, f"Das Testdiagramm löst nicht alle Regeln aus, sondern {gefundene_regeln}"
    for hinweis in hinweise:
        assert hinweis.loesung.strip(), f"{hinweis.regel}: kein Lösungsteil"
        assert hinweis.meldung.endswith(hinweis.loesung), (
            f"{hinweis.regel}: die Meldung endet nicht mit ihrem Lösungsteil"
        )


# -- 3. Keine Klammerform --------------------------------------------------

#: „Fund(e)“, „Test(s)“, „Zeile(n)“ – ein Buchstabe, dann eine Endung in
#: Klammern.
KLAMMERFORM = re.compile(r"[A-Za-zÄÖÜäöüß]\((?:e|s|n|en|er|nen|innen)\)")

#: Bekannte Stellen, die die Regel noch verletzen und außerhalb dieses
#: Arbeitspakets liegen. Die Liste soll leer werden, nicht wachsen.
KLAMMERFORM_AUSNAHMEN = {
    # „{bestanden} von {len(ergebnisse)} Test(s) bestanden.“ im
    # HTML-Testprotokoll. Einzeiler, aber die Datei gehört zu einem
    # anderen Arbeitspaket.
    Path("ide/testrunner/html_export.py"),
}


def _sichtbare_texte(pfad: Path) -> list[str]:
    """Alle Zeichenketten eines Moduls außer Docstrings – nur die
    landen überhaupt auf dem Bildschirm."""
    baum = ast.parse(pfad.read_text(encoding="utf-8"))
    docstrings = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            erster = knoten.body[0] if knoten.body else None
            if (
                isinstance(erster, ast.Expr)
                and isinstance(erster.value, ast.Constant)
                and isinstance(erster.value.value, str)
            ):
                docstrings.add(id(erster.value))
    return [
        knoten.value
        for knoten in ast.walk(baum)
        if isinstance(knoten, ast.Constant)
        and isinstance(knoten.value, str)
        and id(knoten) not in docstrings
    ]


def test_keine_klammerform_in_sichtbaren_texten() -> None:
    """„3 Fund(e) vor dem Start“ war die Meldung, an der der Nutzer den
    Mangel festgemacht hat: ein Formular statt eines Satzes."""
    funde: list[str] = []
    for pfad in sorted([*(WURZEL / "ide").rglob("*.py"), *(WURZEL / "pcl").rglob("*.py")]):
        if pfad.relative_to(WURZEL) in KLAMMERFORM_AUSNAHMEN:
            continue
        for text in _sichtbare_texte(pfad):
            for treffer in KLAMMERFORM.findall(text):
                funde.append(f"{pfad.relative_to(WURZEL)}: …{treffer}… in {text!r}")

    assert not funde, "Klammerform statt Ein-/Mehrzahl:\n" + "\n".join(funde)
