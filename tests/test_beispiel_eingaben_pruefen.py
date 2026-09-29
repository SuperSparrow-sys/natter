"""„nan“, „inf“ und „²“ ergeben in den Beispielen eine Meldung statt
eines Abbruchs (Punkt 116).

Die Kontoverwaltung legt ihre Datenbank neben dem Programm an. Der
Test arbeitet deshalb auf einer Kopie in `tmp_path` und lässt das
Repository unberührt."""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BEISPIELE = Path(__file__).resolve().parent.parent / "beispielprojekte"
_AM_LEBEN: list[object] = []


def _u_module_vergessen() -> None:
    for name in [n for n in sys.modules if n.startswith("u_")]:
        sys.modules.pop(name, None)


@pytest.fixture
def konten(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    ordner = tmp_path / "06_Kontoverwaltung"
    shutil.copytree(BEISPIELE / "06_Kontoverwaltung", ordner)
    (ordner / "konten.sqlite").unlink(missing_ok=True)
    monkeypatch.syspath_prepend(str(ordner))
    monkeypatch.chdir(ordner)
    _u_module_vergessen()
    formular = importlib.import_module("u_main").Form1()
    _AM_LEBEN.append(formular)
    formular.form_create(formular)
    formular.e_inhaber.text = "Anna"
    formular.b_anlegen_click(formular)
    formular.e_nummer.text = "1"
    yield formular
    formular.db.verbindung.close()
    _u_module_vergessen()


@pytest.mark.parametrize("betrag", ["nan", "inf", "-inf", "NaN"])
@pytest.mark.parametrize("knopf", ["b_einzahlen_click", "b_abheben_click"])
def test_kein_endlicher_betrag_ergibt_eine_meldung(konten, betrag, knopf) -> None:
    konten.e_betrag.text = betrag
    getattr(konten, knopf)(konten)

    assert konten.l_meldung.caption == "Der Betrag muss eine Zahl sein."
    zeile = konten.db.query_one("SELECT stand FROM konto WHERE nummer = 1")
    assert zeile["stand"] == 0


def test_eine_hochgestellte_zwei_als_kontonummer_ergibt_eine_meldung(konten) -> None:
    konten.e_nummer.text = "²"
    konten.e_betrag.text = "5"
    konten.b_einzahlen_click(konten)

    assert konten.l_meldung.caption == "Bitte eine Kontonummer eintragen."


def test_die_klasse_konto_lehnt_nan_selbst_ab(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.syspath_prepend(str(BEISPIELE / "06_Kontoverwaltung"))
    _u_module_vergessen()
    u_konto = importlib.import_module("u_konto")
    konto = u_konto.Konto(1, "Anna", 10.0)
    with pytest.raises(ValueError):
        konto.einzahlen(float("nan"))
    with pytest.raises(ValueError):
        konto.abheben(float("nan"))
    _u_module_vergessen()


def test_zahlenraten_nimmt_eine_hochgestellte_zwei_nicht_als_zahl() -> None:
    lauf = subprocess.run(
        [sys.executable, "main.py"],
        cwd=BEISPIELE / "02_Zahlenraten",
        input="²\n" * 7,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )

    assert lauf.returncode == 0, lauf.stderr
    assert "Das war keine Zahl." in lauf.stdout
