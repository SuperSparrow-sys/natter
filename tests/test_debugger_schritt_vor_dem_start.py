"""Einzelschritt und Prozedurschritt vor dem Start (Punkt 295). Gegen
echtes `debugpy`.

Bis 0.3.5 waren beide Befehle ohne laufendes Programm grau, und F11
tat nichts, genau beim ersten Versuch, eine Schleife Schritt für
Schritt zu verfolgen. Jetzt starten sie das Programm mit dem Debugger
und halten in der ersten Zeile von `main()` in `u_main.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.project.neu import projekt_erzeugen
from ide.run import erste_zeile_der_haupt_unit
from tests.conftest import DEBUG_ZEITGRENZE

_SCHLEIFE = (
    "# Eine Schleife zum Verfolgen.\n"
    "\n"
    "\n"
    "def main():\n"
    "    summe = 0\n"
    "    for i in range(3):\n"
    "        summe = summe + i\n"
    "    print(summe)\n"
)


def _projekt(ordner: Path) -> Path:
    projekt = projekt_erzeugen("console", ordner, "Schleife")
    (projekt.ordner / "u_main.py").write_text(_SCHLEIFE, encoding="utf-8")
    return projekt.ordner


def test_die_erste_zeile_ist_die_erste_in_main(tmp_path: Path) -> None:
    from ide.project import Projekt

    projekt = Projekt.laden(_projekt(tmp_path / "p"))

    assert erste_zeile_der_haupt_unit(projekt) == (
        projekt.ordner / "u_main.py",
        5,
    )


@pytest.mark.parametrize(
    "kennung", ["start.einzelschritt", "start.prozedurschritt"]
)
def test_schritt_ohne_laufendes_programm_haelt_in_u_main(
    tmp_path: Path, qtbot, hauptfenster, kennung: str  # noqa: ANN001
) -> None:
    ordner = _projekt(tmp_path / "p")
    hauptfenster.projekt_oeffnen(ordner / "Schleife.natter")
    aktion = hauptfenster.aktionen[kennung].qaction
    assert aktion.isEnabled()

    try:
        aktion.trigger()
        assert hauptfenster.debug_sitzung is not None
        assert "u_main.py, Zeile 5" in hauptfenster.statusBar().currentMessage()
        qtbot.waitUntil(
            lambda: hauptfenster._aktueller_thread_id is not None,
            timeout=DEBUG_ZEITGRENZE,
        )
        qtbot.waitUntil(
            lambda: hauptfenster._aktueller_editor() is not None
            and str(hauptfenster._aktueller_editor().property("pfad") or "")
            .endswith("u_main.py"),
            timeout=DEBUG_ZEITGRENZE,
        )
        editor = hauptfenster._aktueller_editor()
        assert editor.textCursor().blockNumber() + 1 == 5

        # Aus dem Halt heraus ist es wieder der gewöhnliche Schritt.
        aktion.trigger()
        qtbot.waitUntil(
            lambda: hauptfenster._aktueller_thread_id is not None
            and editor.textCursor().blockNumber() + 1 == 6,
            timeout=DEBUG_ZEITGRENZE,
        )
    finally:
        if hauptfenster.debug_sitzung is not None:
            hauptfenster._debugger_stoppen_aktion()
