"""Tests für ide/run/pruefung.py: Ruff-Prüfung vor dem Start (Abschnitt
8.2). Läuft gegen echtes `ruff`, kein Mock. Siehe
docs/arbeitspakete/M4.md, Schritt 1.
"""

from __future__ import annotations

import json
from pathlib import Path

from ide.project import Projekt
from ide.run import projekt_pruefen


def _projekt_schreiben(ordner: Path, main_inhalt: str) -> Projekt:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(main_inhalt, encoding="utf-8")
    daten = {"format": "natter-project/1", "name": "Test", "type": "gui", "main": "main.py"}
    natter_pfad = ordner / "test.natter"
    natter_pfad.write_text(json.dumps(daten), encoding="utf-8")
    return Projekt.laden(natter_pfad)


def test_sauberes_projekt_liefert_keine_funde(tmp_path: Path) -> None:
    projekt = _projekt_schreiben(tmp_path, "def f() -> int:\n    return 1\n")
    assert projekt_pruefen(projekt) == []


def test_syntaxfehler_wird_gefunden(tmp_path: Path) -> None:
    projekt = _projekt_schreiben(tmp_path, "def f(:\n    pass\n")
    funde = projekt_pruefen(projekt)
    assert len(funde) >= 1
    assert funde[0].zeile == 1


def test_unbekannter_name_wird_gefunden(tmp_path: Path) -> None:
    projekt = _projekt_schreiben(tmp_path, "def f():\n    return nicht_definiert\n")
    funde = projekt_pruefen(projekt)
    assert any(f.code == "F821" for f in funde)


def test_ungenutzter_import_wird_gefunden(tmp_path: Path) -> None:
    projekt = _projekt_schreiben(tmp_path, "import os\n\ndef f():\n    return 1\n")
    funde = projekt_pruefen(projekt)
    assert any(f.code == "F401" for f in funde)


def test_ungenutzte_variable_wird_gefunden(tmp_path: Path) -> None:
    projekt = _projekt_schreiben(tmp_path, "def f():\n    x = 1\n    return 2\n")
    funde = projekt_pruefen(projekt)
    assert any(f.code == "F841" for f in funde)


def test_reine_stilfragen_wie_unsortierte_importe_werden_nicht_gemeldet(tmp_path: Path) -> None:
    projekt = _projekt_schreiben(
        tmp_path, "import sys\nimport os\n\ndef f():\n    return sys.path and os.getcwd()\n"
    )
    assert projekt_pruefen(projekt) == []


def test_fund_als_text_enthaelt_dateiname_zeile_code_und_meldung(tmp_path: Path) -> None:
    projekt = _projekt_schreiben(tmp_path, "def f():\n    return nicht_definiert\n")
    fund = projekt_pruefen(projekt)[0]
    text = str(fund)
    assert "main.py" in text
    assert "F821" in text
    assert str(fund.zeile) in text
