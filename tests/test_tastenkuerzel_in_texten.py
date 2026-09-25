"""Jedes Tastenkürzel in einem gelesenen Text muss es geben.

Punkt 11 der offenen Punkte. Im allerersten Beispielprogramm stand
„Drücke F9, um das Programm zu starten." - F9 tut in Natter nichts,
gestartet wird mit F5. Eine Schülerin, die dem Kommentar folgt,
drückt eine Taste ohne Wirkung und weiß nicht, woran es liegt.

Die meisten Texte lassen sich nicht maschinell prüfen. Ein
Tastenkürzel schon: es steht entweder im Aktionsregister, ist eine
Editor- oder Designertaste aus `ide/shell/tastenkuerzel.py`, oder es
gibt es nicht.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from ide.shell.hauptfenster import HauptFenster
from ide.shell.tastenkuerzel import DESIGNERTASTEN, EDITORTASTEN, deutsche_taste

WURZEL = Path(__file__).resolve().parent.parent

#: Texte, die jemand liest und in denen ein Kürzel stehen kann.
TEXTE = [
    WURZEL / "docs" / "erste_schritte.md",
    WURZEL / "docs" / "handbuch.md",
    WURZEL / "docs" / "komponenten.md",
    *sorted((WURZEL / "templates").rglob("*.template")),
    *sorted(WURZEL.glob("beispielprojekte/*/u_main.py")),
    *sorted(WURZEL.glob("beispielprojekte/*/u_*.py")),
]

#: „Strg+Umschalt+E", „Alt+Pfeil hoch", „F11" - und nichts, was nur
#: zufällig so aussieht. `Form1` enthält kein Kürzel, weil vor der
#: Ziffer ein Buchstabe steht.
KUERZEL = re.compile(
    r"\b(?:Strg|Umschalt|Alt)(?:\+[\wÄÖÜäöüß]+)+|\bF(?:[1-9]|1[0-2])\b"
)


#: Kürzel, die nicht Natter bedient, sondern das Programm, das jemand
#: damit schreibt. In `komponenten.md` steht bei der Eigenschaft
#: `shortcut` eines Menüeintrags ein Beispielwert, und `&Datei` ergibt
#: im eigenen Menü den Zugriffsbuchstaben Alt+D. Solche Werte müssen
#: in Natter nichts tun.
EIGENE_PROGRAMME = {
    "docs/komponenten.md": {"Strg+Q", "Strg+Umschalt+S", "Alt+D"},
}


def _erlaubte_kuerzel() -> set[str]:
    """Was es wirklich gibt: aus dem Register, aus den Quelltexten
    aller Fenster und aus der Liste der Editortasten.

    Das Register des Hauptfensters allein genügt nicht - der
    Diagramm-Editor ist ein eigenes Fenster und setzt seine Kürzel
    mit `setShortcut()`. Die werden aus dem Syntaxbaum gelesen statt
    aus einer zweiten Liste, die veralten könnte.
    """
    erlaubt: set[str] = set()

    for pfad in (WURZEL / "ide").rglob("*.py"):
        if "__pycache__" in pfad.parts:
            continue
        try:
            baum = ast.parse(pfad.read_text(encoding="utf-8"))
        except SyntaxError:  # pragma: no cover - faellt anderswo auf
            continue
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.Constant) and isinstance(knoten.value, str):
                continue
            if not isinstance(knoten, ast.Call):
                continue
            werte = [
                a.value
                for a in knoten.args
                if isinstance(a, ast.Constant) and isinstance(a.value, str)
            ]
            werte += [
                k.value.value
                for k in knoten.keywords
                if k.arg == "tastenkuerzel"
                and isinstance(k.value, ast.Constant)
                and isinstance(k.value.value, str)
            ]
            if isinstance(knoten.func, ast.Attribute) and knoten.func.attr not in (
                "setShortcut",
                "Aktion",
            ):
                werte = [
                    k.value.value
                    for k in knoten.keywords
                    if k.arg == "tastenkuerzel"
                    and isinstance(k.value, ast.Constant)
                    and isinstance(k.value.value, str)
                ]
            for wert in werte:
                if wert:
                    erlaubt.add(wert)
                    erlaubt.add(deutsche_taste(wert))

    for taste, _zweck in (*EDITORTASTEN, *DESIGNERTASTEN):
        erlaubt.add(taste)
        # „Alt+Pfeil hoch/runter" steht als eine Zeile, gefunden wird
        # sie einzeln.
        for teil in taste.replace("/", " ").split():
            erlaubt.add(teil)
        if "/" in taste:
            kopf = taste.split("+")[0]
            for rest in taste.split("+", 1)[1].split("/"):
                erlaubt.add(f"{kopf}+{rest}")

    return {k for k in erlaubt if k}


@pytest.fixture(scope="module")
def erlaubt(qapp) -> set[str]:
    menge = _erlaubte_kuerzel()
    fenster = HauptFenster()
    for aktion in fenster.aktionen:
        if aktion.tastenkuerzel:
            menge.add(aktion.tastenkuerzel)
            menge.add(deutsche_taste(aktion.tastenkuerzel))
    fenster.close()
    return menge


def test_die_liste_der_texte_stimmt() -> None:
    """Sonst prüfte der Test unten stillschweigend nichts."""
    assert len(TEXTE) >= 12
    for pfad in TEXTE:
        assert pfad.exists(), pfad


def test_es_gibt_ueberhaupt_kuerzel_zu_pruefen(erlaubt: set[str]) -> None:
    assert "F5" in erlaubt, "Das Startkürzel fehlt - dann prüft der Test nichts."
    assert "F9" not in erlaubt, "F9 ist in Natter nicht belegt."


@pytest.mark.parametrize("pfad", TEXTE, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_jedes_genannte_kuerzel_gibt_es(pfad: Path, erlaubt: set[str]) -> None:
    eigene = EIGENE_PROGRAMME.get(pfad.relative_to(WURZEL).as_posix(), set())
    unbekannt = []
    for nummer, zeile in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
        for treffer in KUERZEL.findall(zeile):
            if treffer not in erlaubt and treffer not in eigene:
                unbekannt.append(f"Zeile {nummer}: {treffer} in {zeile.strip()[:70]}")

    assert not unbekannt, (
        f"{pfad.name} nennt Tasten, die in Natter nichts tun:\n"
        + "\n".join(unbekannt[:5])
    )


def test_die_ausnahmen_sind_nicht_veraltet() -> None:
    """Ein Beispielwert, der aus der Seite verschwunden ist, soll
    hier nicht weiter als Ausnahme stehen."""
    for datei, kuerzel in EIGENE_PROGRAMME.items():
        text = (WURZEL / datei).read_text(encoding="utf-8")
        for eintrag in kuerzel:
            assert eintrag in text, f"{eintrag} steht nicht mehr in {datei}"
