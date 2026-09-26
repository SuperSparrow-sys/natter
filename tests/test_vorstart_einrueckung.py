"""Ein Einrückungsfehler heißt vor dem Start auch so (Punkt 45 der
offenen Punkte).

Bis 0.3.3 lief jeder Syntaxfehler unter derselben Meldung: „Fehlt am
Zeilenende ein Doppelpunkt, eine schließende Klammer oder ein
Anführungszeichen?“ Bei einer vergessenen Einrückung stand das
eigentliche Problem nicht darin. Geprüft mit dem echten Ruff.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ide.project import Projekt
from ide.run.pruefung import projekt_pruefen


def _pruefen(ordner: Path, quelltext: str) -> list[str]:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(quelltext, encoding="utf-8")
    (ordner / "p.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Probe",
                "type": "console",
                "main": "main.py",
            }
        ),
        encoding="utf-8",
    )
    return [str(f) for f in projekt_pruefen(Projekt.laden(ordner))]


@pytest.mark.parametrize(
    ("quelltext", "zeile"),
    [
        ('zahl = 5\nif zahl > 3:\nprint("groß")\n', 3),
        ("x = 1\n    y = 2\n", 2),
        ("if True:\n        x = 1\n    y = 2\n", 3),
    ],
    ids=["block_fehlt", "zu_weit_eingerueckt", "passt_zu_keiner_ebene"],
)
def test_einrueckungsfehler_nennt_die_einrueckung(
    tmp_path: Path, quelltext: str, zeile: int
) -> None:
    meldungen = _pruefen(tmp_path / "p", quelltext)

    erste = meldungen[0]
    assert f"Zeile {zeile}:" in erste
    assert "einr" in erste.lower() or "ausr" in erste.lower()
    assert "Anführungszeichen" not in erste


def test_fehlender_doppelpunkt_bleibt_bei_der_allgemeinen_meldung(
    tmp_path: Path,
) -> None:
    meldungen = _pruefen(tmp_path / "p", 'if 5 > 3\n    print("x")\n')

    assert "Doppelpunkt" in meldungen[0]
