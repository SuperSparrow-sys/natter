"""Natter benutzt seine eigene Python - und nur die (M13).

Auf einem Rechner, auf dem schon mit Python gearbeitet wurde, stehen
Umgebungsvariablen herum, die auf eine **andere** Installation zeigen.
Die unauffälligste davon ist `PYTHONUSERBASE`: aus ihr rechnet *jede*
Python 3.13 ihr Benutzer-Paketverzeichnis aus, auch eine frisch
ausgepackte. Die sieht dann die Pakete des fremden Rechners als ihre
eigenen.

Beim Bau der Auslieferung hat genau das zugeschlagen. `pip` meldete
Zeile für Zeile „Requirement already satisfied", installierte nur
Natter selbst und gab 0 zurück - der Bau lief fehlerfrei durch. In der
fertigen Auslieferung fehlten `ruff`, `scipy`, `scikit-learn`,
`cryptography`, `setuptools` und ein Dutzend weiterer Pakete, und damit
die Prüfung vor dem Start, die Integritätsprüfung und der Exe-Export.
Gemerkt hat es niemand, bis die Pakete in `dist` nachgezählt wurden.

Dieselbe Falle steht auf dem Schulrechner: findet die ausgelieferte
Python dort eine fremde PySide6-Fassung, geht Natter auf einem Rechner
kaputt, an dem nie jemand etwas geändert hat. Deshalb prüft dieser Test
**beide** Seiten - den Bau und den Starter.
"""

from __future__ import annotations

import pytest

from tools.ide_paketieren import _saubere_umgebung
from tools.launcher import eigene_umgebung

#: Alle zeigen auf eine fremde Python-Installation.
FREMDE = ("PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE", "VIRTUAL_ENV")

#: Beide Seiten müssen dasselbe tun; der Test beschreibt sie gemeinsam.
UMGEBUNGEN = {"Bau": _saubere_umgebung, "Starter": eigene_umgebung}


@pytest.fixture
def verseuchte_umgebung(monkeypatch: pytest.MonkeyPatch) -> None:
    """So sieht die Umgebung auf einem Rechner aus, auf dem schon eine
    andere Python steht."""
    for name in FREMDE:
        monkeypatch.setenv(name, r"C:\woanders")
    monkeypatch.setenv("PATH", r"C:\Windows\system32")


@pytest.mark.parametrize("seite", sorted(UMGEBUNGEN))
@pytest.mark.parametrize("name", FREMDE)
def test_der_verweis_auf_fremdes_python_faellt_weg(
    seite: str, name: str, verseuchte_umgebung: None
) -> None:
    assert name not in UMGEBUNGEN[seite](), (
        f"{name} zeigt auf eine fremde Python-Installation und darf "
        f"({seite}) nicht durchgereicht werden."
    )


@pytest.mark.parametrize("seite", sorted(UMGEBUNGEN))
def test_das_benutzerverzeichnis_ist_abgeschaltet(seite: str, verseuchte_umgebung: None) -> None:
    """`PYTHONUSERBASE` zu löschen genügt nicht: das
    Benutzer-Paketverzeichnis hat auch ohne sie einen Vorgabewert."""
    assert UMGEBUNGEN[seite]().get("PYTHONNOUSERSITE") == "1"


@pytest.mark.parametrize("seite", sorted(UMGEBUNGEN))
def test_der_rest_der_umgebung_bleibt(seite: str, verseuchte_umgebung: None) -> None:
    """Nur die vier Verweise sollen weg. `PATH`, Proxy-Einstellungen
    und was die Schule sonst setzt, werden gebraucht - unter anderem
    damit Nachinstallieren über das Menü „Pakete" funktioniert."""
    assert UMGEBUNGEN[seite]()["PATH"] == r"C:\Windows\system32"


# -- Tcl/Tk fliegt aus der Auslieferung (September 2026) ----------------
#
# "Tk Inter kann komplett raus aus der Installation." Tcl/Tk ist Pythons
# zweite Fenstertechnik - Natter baut jede Oberflaeche mit Qt, und `pcl`
# importiert `tkinter` nirgends. Mitgehen wuerde es trotzdem, weil es zur
# Standardbibliothek gehoert: rund 13 MB, davon 9 MB Tcl-Skripte.


def test_tcl_tk_wird_aus_der_mitgelieferten_python_entfernt(tmp_path) -> None:
    from tools.ide_paketieren import _tcl_tk_entfernen

    python = tmp_path / "python"
    (python / "tcl" / "tk8.6").mkdir(parents=True)
    (python / "tcl" / "tk8.6" / "ttk.tcl").write_text("x" * 1000, encoding="utf-8")
    (python / "Lib" / "tkinter").mkdir(parents=True)
    (python / "Lib" / "tkinter" / "__init__.py").write_text("y" * 500, encoding="utf-8")
    (python / "Lib" / "turtle.py").write_text("z" * 300, encoding="utf-8")
    (python / "DLLs").mkdir()
    (python / "DLLs" / "tcl86t.dll").write_bytes(b"0" * 200)
    (python / "DLLs" / "_tkinter.pyd").write_bytes(b"0" * 100)
    # Was bleiben muss:
    (python / "Lib" / "json").mkdir()
    (python / "DLLs" / "_sqlite3.pyd").write_bytes(b"0" * 50)

    gespart = _tcl_tk_entfernen(python)

    assert not (python / "tcl").exists()
    assert not (python / "Lib" / "tkinter").exists()
    assert not (python / "Lib" / "turtle.py").exists()
    assert not (python / "DLLs" / "tcl86t.dll").exists()
    assert not (python / "DLLs" / "_tkinter.pyd").exists()
    assert gespart == 2100

    # Der Rest der Standardbibliothek bleibt unangetastet.
    assert (python / "Lib" / "json").is_dir()
    assert (python / "DLLs" / "_sqlite3.pyd").is_file()


def test_eine_fehlende_datei_laesst_den_bau_nicht_scheitern(tmp_path) -> None:
    """Die Standalone-Python liefert je nach Fassung nicht immer
    dieselben Hilfs-DLLs mit."""
    from tools.ide_paketieren import _tcl_tk_entfernen

    python = tmp_path / "python"
    python.mkdir()

    assert _tcl_tk_entfernen(python) == 0


def test_natter_selbst_fasst_tkinter_nirgends_an() -> None:
    """Der Grund, warum es weg darf. Faellt jemand spaeter darauf
    zurueck, bricht die Auslieferung - deshalb steht es hier."""
    from pathlib import Path

    wurzel = Path(__file__).resolve().parent.parent
    treffer = []
    for ordner in ("ide", "pcl"):
        for datei in (wurzel / ordner).rglob("*.py"):
            text = datei.read_text(encoding="utf-8", errors="ignore")
            for zeile in text.splitlines():
                nackt = zeile.strip()
                if nackt.startswith(("import tkinter", "from tkinter", "import turtle")):
                    treffer.append(f"{datei.name}: {nackt}")

    assert not treffer, f"tkinter wird doch benutzt: {treffer}"
