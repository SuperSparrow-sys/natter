"""Punkt 611: ein Haltepunkt auf einer Leer- oder Kommentarzeile.

debugpy legte ihn auf eine Anweisung davor, der rote Punkt im Editor
blieb, wo er war, und das Programm hielt, bevor die vorige Anweisung
gelaufen war. Jetzt landet er schon im Editor auf der nächsten
Anweisung, und dort hält auch das Programm.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.debugger import DapClient
from ide.shell.quelltexteditor import QuelltextEditor

QUELLTEXT = (
    "def f():\n"
    "    x = 0\n"
    "\n"
    "    # Kommentar\n"
    "    a = 1\n"
    "    return a\n"
    "\n"
    "f()\n"
)


@pytest.mark.parametrize("zeile", [3, 4], ids=["leerzeile", "kommentar"])
def test_editor_legt_den_haltepunkt_auf_die_naechste_anweisung(qtbot, zeile: int) -> None:  # noqa: ANN001
    feld = QuelltextEditor()
    qtbot.addWidget(feld)
    feld.setPlainText(QUELLTEXT)

    feld.breakpoint_umschalten(zeile)
    feld.bedingung_setzen(5, "x == 0")

    assert feld.breakpoints == {5}
    assert feld.bedingungen == {5: "x == 0"}


def test_gewanderter_haltepunkt_kommt_auf_die_anweisung(qtbot) -> None:  # noqa: ANN001
    feld = QuelltextEditor()
    qtbot.addWidget(feld)
    feld.setPlainText(QUELLTEXT)
    feld.breakpoints = {3}
    feld.bedingungen = {3: "True"}

    assert feld.haltepunkte_auf_anweisungen() is True
    assert feld.breakpoints == {5}
    assert feld.bedingungen == {5: "True"}
    assert feld.haltepunkte_auf_anweisungen() is False


def test_editor_und_halt_stimmen_ueberein(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    skript = tmp_path / "ziel.py"
    skript.write_text(QUELLTEXT, encoding="utf-8")
    feld = QuelltextEditor()
    qtbot.addWidget(feld)
    feld.setPlainText(QUELLTEXT)
    feld.breakpoint_umschalten(3)

    client = DapClient()
    try:
        client.starten(
            skript, arbeitsordner=tmp_path,
            anfangs_breakpoints={skript: sorted(feld.breakpoints)},
        )
        ereignis = client.angehalten_abwarten()
        stapel = client.aufrufstapel_lesen(ereignis["threadId"])
    finally:
        client.beenden()

    assert feld.breakpoints == {5}
    assert stapel[0]["line"] == 5
