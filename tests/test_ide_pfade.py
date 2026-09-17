"""Tests für ide/pfade.py: Pfadauflösung für mitgelieferte Datenordner
(`schemas/`) - normalerweise relativ zum Quellcode, aber in einer mit
PyInstaller gebauten Exe (`tools/ide_paketieren.py`) im Bundle-Ordner
(`sys._MEIPASS`). Siehe tests/test_theme.py für dasselbe Muster bei
`pcl.theme` (eigenständig, weil `pcl` nicht von `ide` abhängen darf).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ide.pfade import daten_ordner

_PROJEKT_WURZEL = Path(__file__).resolve().parent.parent


def test_ohne_meipass_zeigt_auf_die_projektwurzel() -> None:
    pfad = daten_ordner("schemas")
    assert pfad == _PROJEKT_WURZEL / "schemas"
    assert pfad.exists()


def test_in_einer_pyinstaller_exe_zeigt_in_meipass(monkeypatch: pytest.MonkeyPatch) -> None:
    """Real beim Bau von Natter.exe selbst gefunden (nicht nur beim
    Export eines Schülerprojekts): `ide/codegen/design.py`,
    `ide/designer/pfm_schreiben.py` und `ide/project/projekt.py`
    lasen `schemas/*.json` über einen quellcode-relativen Pfad, der in
    der gebauten Exe nicht existiert - die IDE stürzte beim Start mit
    `FileNotFoundError: ...\\_internal\\schemas\\pfm.schema.json` ab."""
    monkeypatch.setattr(sys, "_MEIPASS", r"C:\irgendwo\_internal", raising=False)

    pfad = daten_ordner("schemas")

    assert pfad == Path(r"C:\irgendwo\_internal") / "schemas"
