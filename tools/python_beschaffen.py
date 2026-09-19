"""Beschafft die CPython, die mit Natter ausgeliefert wird (M13).

Bis M12 wurde Natter mit PyInstaller zu einem Bundle eingefroren. Ein
eingefrorener Python lässt sich nicht mehr auseinandernehmen – deshalb
konnten `pip` und „Als Exe exportieren“ dort grundsätzlich nicht
arbeiten. Seit M13 liegt stattdessen eine **gewöhnliche, verschiebbare**
CPython bei, auf der Natter läuft; damit geht beides wieder.

Die Installation stammt von **python-build-standalone** – derselben
Quelle, aus der auch `uv python install` bedient wird. `uv` liegt im
Entwicklungsbaum ohnehin vor und kümmert sich um Herunterladen und
Prüfsumme; dieses Modul legt nur fest, **welche** Fassung es sein soll,
und räumt das Ergebnis an einen vorhersagbaren Platz.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

#: Die ausgelieferte Python-Fassung. Bewusst festgeschrieben und nicht
#: „die neueste“: der Bau soll heute und in einem Jahr dasselbe
#: ergeben, und ein Sprung auf eine neue Nebenversion will geprüft
#: werden (PySide6 hinkt neuen Python-Versionen regelmäßig hinterher).
PYTHON_FASSUNG = "cpython-3.13.15-windows-x86_64-none"

_PROJEKT_WURZEL = Path(__file__).resolve().parent.parent
_BAU_ORDNER = _PROJEKT_WURZEL / "build"


def python_beschaffen(ziel: Path | None = None, *, neu_laden: bool = False) -> Path:
    """Lädt die Standalone-CPython und liefert den Ordner, in dem sie
    liegt (der mit `python.exe` darin).

    Ein bereits vorhandener Ordner wird wiederverwendet – der Download
    ist 21 MB, und beim Bauen wird er mehrfach gebraucht.
    """
    ziel = ziel if ziel is not None else _BAU_ORDNER / "python-download"
    fertig = ziel / PYTHON_FASSUNG

    if neu_laden and ziel.exists():
        shutil.rmtree(ziel)
    if (fertig / "python.exe").is_file():
        return fertig

    ziel.mkdir(parents=True, exist_ok=True)
    ergebnis = subprocess.run(
        ["uv", "python", "install", "--install-dir", str(ziel), PYTHON_FASSUNG],
        capture_output=True,
        text=True,
    )
    if ergebnis.returncode != 0 or not (fertig / "python.exe").is_file():
        raise RuntimeError(
            "Die Python-Installation konnte nicht beschafft werden:\n"
            f"{ergebnis.stdout}\n{ergebnis.stderr}"
        )
    return fertig


if __name__ == "__main__":
    print(f"Python liegt in: {python_beschaffen()}")
