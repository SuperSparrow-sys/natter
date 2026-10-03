"""Tests für ide/run/pruefung.py: Ruff-Prüfung vor dem Start (Abschnitt
8.2). Läuft gegen echtes `ruff`, kein Mock. Siehe
Arbeitspaket M4, Schritt 1.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

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


def test_fund_als_text_enthaelt_dateiname_zeile_und_meldung(tmp_path: Path) -> None:
    """Der Name der Regel steht seit Punkt 291 nur noch im Tooltip."""
    projekt = _projekt_schreiben(tmp_path, "def f():\n    return nicht_definiert\n")
    fund = projekt_pruefen(projekt)[0]
    text = str(fund)
    assert "main.py" in text
    assert "nicht_definiert" in text
    assert str(fund.zeile) in text
    assert "F821" not in text
    assert "[" not in text
    assert "F821" in fund.regel


def test_die_pruefung_hinterlaesst_keinen_ruff_cache(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    """Offener Punkt 21: nach dem Deinstallieren blieb ein
    `.ruff_cache` im Programmordner liegen. ruff legte ihn im
    Arbeitsordner von Natter an, und das ist in der Installation der
    Programmordner. Hier steht `arbeitsordner` für ihn."""
    arbeitsordner = tmp_path / "programmordner"
    arbeitsordner.mkdir()
    monkeypatch.chdir(arbeitsordner)
    projekt = _projekt_schreiben(tmp_path / "projekt", "print('hallo')\n")

    projekt_pruefen(projekt)

    assert not (arbeitsordner / ".ruff_cache").exists()
    assert not (projekt.ordner / ".ruff_cache").exists()


def test_eine_datei_mit_dem_namen_eines_moduls_ergibt_einen_hinweis(tmp_path: Path) -> None:
    """Punkt 536: Eine hineinkopierte `random.py` verdeckt das Modul.
    Das ist ein Hinweis und kein Grund, den Start zu verhindern."""
    projekt = _projekt_schreiben(tmp_path, "print(1)\n")
    (tmp_path / "random.py").write_text("x = 1\n", encoding="utf-8")

    funde = [f for f in projekt_pruefen(projekt) if f.code == "natter-modulname"]

    assert len(funde) == 1
    assert funde[0].datei.name == "random.py"
    assert not funde[0].blockiert
    assert "u_random" in str(funde[0])


def test_ein_ruff_ohne_antwort_haelt_die_pruefung_nicht_auf(
    tmp_path: Path, monkeypatch
) -> None:  # noqa: ANN001
    """Punkt 553: ruff lief ohne Zeitgrenze; auf einem Netzlaufwerk, das
    nicht antwortet, stand Natter."""
    import subprocess

    import pytest

    import ide.run.pruefung as pruefung

    projekt = _projekt_schreiben(tmp_path, "print(1)\n")

    def haengt(*_a, **k):  # noqa: ANN002, ANN003, ANN202
        raise subprocess.TimeoutExpired("ruff", k.get("timeout"))

    monkeypatch.setattr(pruefung.subprocess, "run", haengt)

    with pytest.raises(pruefung.PruefungZuLang):
        projekt_pruefen(projekt)


def test_eine_fehlerhafte_datei_im_unterordner_haelt_den_start_nicht_auf(
    tmp_path: Path,
) -> None:
    """Punkt 575: `alt/versuch1.py` mit einem Syntaxfehler blockierte
    den Start, obwohl das Programm sie nicht benutzt."""
    projekt = _projekt_schreiben(tmp_path, "def f() -> int:\n    return 1\n")
    (tmp_path / "alt").mkdir()
    (tmp_path / "alt" / "versuch1.py").write_text("def f(:\n", encoding="utf-8")

    assert projekt_pruefen(projekt) == []


@pytest.mark.parametrize(
    ("name", "verdeckt"),
    [("random", True), ("pandas", True), ("pcl", True), ("design", False),
     ("docs", False), ("ide", False), ("u_konto", False)],
)
def test_modul_verdeckt_kennt_nur_echte_module(name: str, verdeckt: bool) -> None:
    """Punkt 587: Ordner der IDE wie `design` oder `docs` galten als
    Module."""
    from ide.run.pruefung import modul_verdeckt

    assert modul_verdeckt(name) is verdeckt


def test_modul_verdeckt_fuehrt_nichts_aus() -> None:
    """Punkt 587: `this.x` ließ `find_spec` das Modul `this` ausführen."""
    import sys

    from ide.run.pruefung import modul_verdeckt

    sys.modules.pop("this", None)
    assert modul_verdeckt("this.x") is False
    assert "this" not in sys.modules
