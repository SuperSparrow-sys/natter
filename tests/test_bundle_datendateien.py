"""Jede Datei, die Natter zur Laufzeit liest, muss auch in die Exe (M12).

PyInstaller bindet nur ein, was **importiert** wird. Alles, was über
einen Pfad gelesen wird – Vorlagen, Symbole, Schemas, eine Schriftdatei,
ein Hilfsskript für den Testrunner –, muss von Hand in
`tools/ide_paketieren.py` eingetragen werden. Wird das vergessen, merkt
es niemand: im Entwicklungsbaum liegt die Datei ja da, und der Fehler
zeigt sich erst in der installierten Version.

In der gebauten Exe nachgemessen fehlten **drei** Pfade, und jeder
kostete eine ganze Funktion:

* `templates/` – „Neues Projekt …“ endete in einem `FileNotFoundError`.
  In der installierten Natter ließ sich überhaupt kein Projekt anlegen.
* `ide/testrunner/harness.py` – der Testrunner startet sie als eigenen
  Prozess; ohne sie lief „Alle Tests ausführen“ ins Leere.
* die Schriftdatei Cascadia Code – der Editor fiel auf eine andere
  Schrift zurück, obwohl Natter sie ausdrücklich mitbringen soll, damit
  nichts installiert werden muss.

Dieser Test hält die Liste der zur Laufzeit gelesenen Pfade gegen das,
was das Paketierskript wirklich einpackt.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent
PAKETIERSKRIPT = WURZEL / "tools" / "ide_paketieren.py"

#: Was Natter zur Laufzeit liest, mit dem Ziel im Bundle. Der Schlüssel
#: ist der Pfad im Quellbaum, der Wert das `--add-data`-Ziel, unter dem
#: die Datei im Bundle liegen muss.
LAUFZEIT_DATEIEN = {
    "design": "design",
    "schemas": "schemas",
    "docs": "docs",
    "beispielprojekte": "beispielprojekte",
    "templates": "templates",
    "ide/assets/icons": "ide/assets/icons",
    "ide/assets/fonts": "ide/assets/fonts",
    "ide/testrunner/harness.py": "ide/testrunner",
}


def _paketierskript() -> str:
    return PAKETIERSKRIPT.read_text(encoding="utf-8")


@pytest.mark.parametrize("quelle", sorted(LAUFZEIT_DATEIEN), ids=lambda q: q)
def test_die_datei_gibt_es_im_quellbaum(quelle: str) -> None:
    """Sonst prüfte der Test unten gegen einen Pfad, den es nicht
    mehr gibt."""
    assert (WURZEL / quelle).exists()


@pytest.mark.parametrize(
    ("quelle", "ziel"), sorted(LAUFZEIT_DATEIEN.items()), ids=lambda w: str(w)
)
def test_die_datei_wird_ins_bundle_gepackt(quelle: str, ziel: str) -> None:
    """Der eigentliche Punkt: steht sie in `--add-data`?"""
    text = _paketierskript()

    assert f'{{os.pathsep}}{ziel}"' in text, (
        f"{quelle} wird zur Laufzeit gelesen, steht aber in "
        f"tools/ide_paketieren.py in keinem --add-data auf {ziel}."
    )


def test_die_vorlagen_werden_ueber_daten_ordner_gesucht() -> None:
    """Ein quellcode-relativer Pfad zeigt im Bundle ins Leere.
    `ide/pfade.daten_ordner()` gibt es genau dafür."""
    quelle = (WURZEL / "ide" / "project" / "neu.py").read_text(encoding="utf-8")

    assert 'daten_ordner("templates")' in quelle
    assert "parent.parent.parent" not in quelle


def test_ruff_und_debugpy_kommen_mit() -> None:
    """Beide werden nur als Unterprozess aufgerufen, nie importiert -
    PyInstaller findet sie deshalb nicht von allein."""
    text = _paketierskript()

    assert "_ruff_binaerdatei()" in text  # die Binärdatei, nicht nur der Finder
    assert re.search(r'"--collect-all",\s*\n\s*"debugpy"', text)
