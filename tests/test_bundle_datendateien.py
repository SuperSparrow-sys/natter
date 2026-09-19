"""Jede Datei, die Natter zur Laufzeit liest, muss in die Auslieferung
(M12, auf die Bauweise von M13 umgestellt).

Der Fehler, gegen den dieser Test steht, ist derselbe geblieben: eine
Datei wird über einen **Pfad** gelesen statt importiert, und niemand
trägt sie in `tools/ide_paketieren.py` ein. Im Entwicklungsbaum liegt
sie ja da - auffallen kann es erst in der installierten Fassung. In der
gebauten Exe nachgemessen fehlten so **drei** Pfade, und jeder kostete
eine ganze Funktion:

* `templates/` - „Neues Projekt ..." endete in einem `FileNotFoundError`.
  In der installierten Natter ließ sich überhaupt kein Projekt anlegen.
* `ide/testrunner/harness.py` - der Testrunner startet sie als eigenen
  Prozess; ohne sie lief „Alle Tests ausführen" ins Leere.
* die Schriftdatei Cascadia Code - der Editor fiel auf eine andere
  Schrift zurück, obwohl Natter sie ausdrücklich mitbringen soll, damit
  nichts installiert werden muss.

Seit M13 gibt es zwei Wege in die Auslieferung, und der Test prüft
beide getrennt:

* Liegt die Datei **innerhalb** von `ide/` oder `pcl/`, nimmt `pip`
  sie von selbst mit - vorausgesetzt, sie liegt wirklich dort und nicht
  daneben (`[tool.hatch.build.targets.wheel] packages`).
* Liegt sie als eigener Ordner **neben** den Paketen (`templates/`,
  `docs/`, ...), muss `_datenordner_kopieren()` sie kopieren.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
PAKETIERSKRIPT = WURZEL / "tools" / "ide_paketieren.py"

#: Ordner, die `ide/pfade.daten_ordner()` eine Ebene über dem
#: `ide`-Paket sucht - in der Installation also in `site-packages`.
#: Dorthin kommen sie nur durch `_datenordner_kopieren()`.
DATEN_ORDNER = ("design", "schemas", "docs", "beispielprojekte", "templates")

#: Dateien, die zur Laufzeit über einen Pfad gelesen werden und
#: innerhalb der Pakete liegen. `pip` nimmt sie mit, solange sie das
#: auch bleiben.
PAKET_DATEIEN = (
    "ide/assets/icons",
    "ide/assets/fonts",
    "ide/testrunner/harness.py",
)


def _paketierskript() -> str:
    return PAKETIERSKRIPT.read_text(encoding="utf-8")


def _wheel_pakete() -> list[str]:
    inhalt = tomllib.loads((WURZEL / "pyproject.toml").read_text(encoding="utf-8"))
    return inhalt["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]


@pytest.mark.parametrize("name", DATEN_ORDNER)
def test_der_datenordner_gibt_es_im_quellbaum(name: str) -> None:
    """Sonst prüfte der Test unten gegen einen Pfad, den es nicht
    mehr gibt."""
    assert (WURZEL / name).is_dir()


@pytest.mark.parametrize("name", DATEN_ORDNER)
def test_der_datenordner_wird_mitkopiert(name: str) -> None:
    """Der eigentliche Punkt: steht er in `_datenordner_kopieren()`?"""
    text = _paketierskript()
    eintrag = f'_PROJEKT_WURZEL / "{name}"'

    assert eintrag in text, (
        f"{name}/ wird zur Laufzeit über daten_ordner() gelesen, wird in "
        f"tools/ide_paketieren.py aber nirgends aus der Projektwurzel geholt."
    )


@pytest.mark.parametrize("pfad", PAKET_DATEIEN)
def test_die_laufzeitdatei_liegt_in_einem_ausgelieferten_paket(pfad: str) -> None:
    """Sie muss existieren **und** innerhalb von `ide/` bzw. `pcl/`
    liegen - nur was dort liegt, packt `pip install` mit ein."""
    assert (WURZEL / pfad).exists(), f"{pfad} wird zur Laufzeit gelesen, gibt es aber nicht."

    oberstes = pfad.split("/")[0]
    assert oberstes in _wheel_pakete(), (
        f"{pfad} wird zur Laufzeit gelesen, liegt aber in '{oberstes}' - "
        f"das steht nicht in [tool.hatch.build.targets.wheel] packages und "
        f"landet damit nicht in der Auslieferung."
    )


def test_die_vorlagen_werden_ueber_daten_ordner_gesucht() -> None:
    """Ein quellcode-relativer Pfad zeigt in der Installation ins Leere.
    `ide/pfade.daten_ordner()` gibt es genau dafür."""
    quelle = (WURZEL / "ide" / "project" / "neu.py").read_text(encoding="utf-8")

    assert 'daten_ordner("templates")' in quelle
    assert "parent.parent.parent" not in quelle


def test_pyinstaller_liegt_der_auslieferung_bei() -> None:
    """„Projekt -> Als Exe exportieren" startet PyInstaller in der
    mitgelieferten Python. Im Entwicklungsbaum steht er in der
    dev-Gruppe und käme sonst nie mit."""
    assert '("PyInstaller", ["pyinstaller"])' in _paketierskript()


def test_ruff_ist_eine_laufzeitabhaengigkeit() -> None:
    """Natter prüft **vor jedem Start** mit ruff - das ist keine
    Entwicklerspielerei, sondern gehört zum Programm. Stünde ruff nur
    in der dev-Gruppe, käme es nicht in die Auslieferung und die
    Prüfung vor dem Start fiele dort aus (M13)."""
    inhalt = tomllib.loads((WURZEL / "pyproject.toml").read_text(encoding="utf-8"))
    abhaengigkeiten = " ".join(inhalt["project"]["dependencies"])

    assert "ruff" in abhaengigkeiten
