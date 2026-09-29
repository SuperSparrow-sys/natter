"""Anleitungen in den Kommentaren der Beispiele und Vorlagen passen
zur Bedienung (Punkt 436).

Beispiel 03 beschrieb das Platzieren einer Schaltfläche als Ziehen aus
der Palette und das Öffnen des Designers als Doppelklick auf
`u_main.pfm`. Beides gibt es nicht: die Kacheln lassen sich nur
anklicken, und der Projekt-Explorer zeigt unter „Formulare“ den Namen
ohne `.pfm`. `tests/test_hilfeseiten_abgleich.py` hält dasselbe für das
Handbuch fest.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent


def _kommentarbloecke(pfad: Path) -> list[tuple[int, str]]:
    """(erste Zeile, Text) je Folge von Kommentarzeilen."""
    bloecke: list[tuple[int, str]] = []
    anfang, zeilen = 0, []
    for nummer, zeile in enumerate(
        pfad.read_text(encoding="utf-8-sig").splitlines(), 1
    ):
        if zeile.lstrip().startswith("#"):
            if not zeilen:
                anfang = nummer
            zeilen.append(zeile.lstrip().lstrip("#").strip())
        elif zeilen:
            bloecke.append((anfang, " ".join(zeilen)))
            zeilen = []
    if zeilen:
        bloecke.append((anfang, " ".join(zeilen)))
    return bloecke


QUELLEN = sorted(
    [
        *(
            p
            for p in (WURZEL / "beispielprojekte").rglob("*.py")
            if not p.name.endswith("_design.py")
        ),
        *(WURZEL / "templates").rglob("*.template"),
    ]
)

FALSCHE_ANLEITUNGEN = [
    pytest.param(
        re.compile(r"Palette.*\b(zieh|gezogen)|\b(zieh|gezogen).*Palette"),
        id="ziehen-aus-der-palette",
    ),
    pytest.param(
        re.compile(r"Doppelklick auf \S+\.pfm"),
        id="doppelklick-auf-pfm",
    ),
]


@pytest.mark.parametrize("muster", FALSCHE_ANLEITUNGEN)
def test_kein_kommentar_beschreibt_eine_bedienung_die_es_nicht_gibt(
    muster: re.Pattern[str],
) -> None:
    assert QUELLEN
    treffer = [
        f"{pfad.relative_to(WURZEL)}:{zeile}: {text[:80]}"
        for pfad in QUELLEN
        for zeile, text in _kommentarbloecke(pfad)
        if muster.search(text)
    ]

    assert not treffer, "\n".join(treffer)


def test_die_kacheln_der_palette_lassen_sich_nicht_ziehen(qtbot) -> None:
    """Die Bedienung, gegen die die Kommentare oben stehen: kommt
    irgendwann Ziehen dazu, fällt dieser Test auf und die Kommentare
    lassen sich wieder anders schreiben."""
    from ide.palette.palette import Komponentenpalette

    palette = Komponentenpalette()
    qtbot.addWidget(palette)

    assert palette.listen
    assert not any(liste.dragEnabled() for liste in palette.listen)
