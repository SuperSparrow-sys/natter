"""Natter benutzt seine eigene Python - und nur die (M13).

Auf einem Rechner, auf dem schon mit Python gearbeitet wurde, stehen
Umgebungsvariablen herum, die auf eine andere Installation zeigen.
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
beide Seiten - den Bau und den Starter.
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


# -- Tcl/Tk fliegt aus der Auslieferung ----------------
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


# Die Auslieferung muss das enthalten, was geprueft wurde. Bis
# rief das Bauskript schlicht `pip install <projekt>`,
# und pip loeste frisch gegen PyPI auf - in `dist` landete pandas
# 3.0.6, waehrend alle Tests gegen 3.0.5 gruen waren. Aufgefallen ist
# es erst, weil Windows Smart App Control die brandneuen, noch ohne
# Reputation dastehenden `pandas._libs` blockierte.


class _Aufruf:
    """Merkt sich, womit `subprocess.run` gerufen wurde."""

    def __init__(self) -> None:
        self.befehle: list[list[str]] = []

    def __call__(self, befehl, **kwargs):  # noqa: ANN001, ANN204
        self.befehle.append([str(teil) for teil in befehl])

        class Ergebnis:
            returncode = 0
            stdout = "pandas==3.0.5 --hash=sha256:abc\npyside6==6.9.4\n"
            stderr = ""

        return Ergebnis()


def test_die_versionen_kommen_aus_uv_lock(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tools import ide_paketieren

    aufruf = _Aufruf()
    monkeypatch.setattr(ide_paketieren.subprocess, "run", aufruf)

    datei = ide_paketieren._gesperrte_versionen(tmp_path)

    assert datei == tmp_path / "requirements-auslieferung.txt"
    assert "pandas==3.0.5" in datei.read_text(encoding="utf-8")
    assert aufruf.befehle == [
        ["uv", "export", "--format", "requirements-txt", "--no-dev", "--no-emit-project"]
    ]


def test_ohne_uv_bricht_der_bau_nicht_ab(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Auf einem Baurechner ohne `uv` bleibt es beim bisherigen Weg -
    mit einer Warnung, aber ohne Abbruch."""
    from tools import ide_paketieren

    class Fehlschlag:
        returncode = 2
        stdout = ""
        stderr = "uv: command not found"

    monkeypatch.setattr(ide_paketieren.subprocess, "run", lambda *a, **k: Fehlschlag())

    assert ide_paketieren._gesperrte_versionen(tmp_path) is None
    assert not list(tmp_path.iterdir())


def test_die_geprueften_versionen_werden_zuerst_installiert(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Die Reihenfolge ist der Kern: steht die Auflösung aus `uv.lock`
    erst einmal da, hat pip beim Auflösen von Natters eigenen
    Abhängigkeiten nichts mehr nachzuladen."""
    from tools import ide_paketieren

    aufruf = _Aufruf()
    monkeypatch.setattr(ide_paketieren.subprocess, "run", aufruf)
    (tmp_path / "python").mkdir()

    ide_paketieren._natter_installieren(tmp_path / "python" / "python.exe")

    pip_aufrufe = [b for b in aufruf.befehle if "pip" in b]
    assert [b[-1] for b in pip_aufrufe][-2:] == [
        str(ide_paketieren._PROJEKT_WURZEL),
        "pyinstaller",
    ]
    assert pip_aufrufe[0][-2:] == ["-r", str(tmp_path / "python" / "requirements-auslieferung.txt")]
