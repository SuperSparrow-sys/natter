"""`plt.show()` aus einem Konsolenprogramm (M5, Schritt 7; belegt in
M15, Abschnitt 6).

Der Punkt stand seit M5 offen mit der Bemerkung, es funktioniere „bereits
umsonst", seit `matplotlib` eine echte Abhängigkeit ist - nur belegt war
es nie. Genau solche Sätze fallen irgendwann um: es genügt, dass jemand
`matplotlib` aus den Abhängigkeiten nimmt oder das Qt-Backend nicht mehr
mitgeliefert wird, und ein Konsolenprogramm mit `plt.show()` stürzt beim
Schüler ab, ohne dass ein Test etwas gemerkt hätte.

Gestartet wird ein **echter Unterprozess** mit demselben Python, das
auch ein Schülerprogramm startet - die Frage ist ja gerade, ob die
ausgelieferte Umgebung das hergibt. `matplotlib` bekommt dafür das
Agg-Backend: ein Fenster ginge im Testlauf nicht auf und bliebe
hängen. Was hier geprüft wird, ist der Weg davor - `import matplotlib`,
Figur bauen, zeichnen, `show()` aufrufen -, und dass dabei nichts
fliegt.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

#: Ein Konsolenprogramm, wie es im Unterricht entstünde: Zahlen
#: ausrechnen, Kurve zeichnen, anzeigen.
PROGRAMM = '''\
import matplotlib

matplotlib.use("Agg")  # nur im Test: sonst ginge hier ein Fenster auf
import matplotlib.pyplot as plt

x = [1, 2, 3, 4, 5]
y = [wert**2 for wert in x]

plt.plot(x, y, marker="o")
plt.title("Quadratzahlen")
plt.xlabel("Zahl")
plt.ylabel("Quadrat")
plt.grid(True)
plt.show()

print("Diagramm angezeigt.")
'''


def _starten(quelltext: str, ordner: Path) -> subprocess.CompletedProcess:
    skript = ordner / "main.py"
    skript.write_text(quelltext, encoding="utf-8")
    return subprocess.run(
        [sys.executable, "main.py"],
        cwd=ordner,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=180,
        env={**os.environ, "PYTHONIOENCODING": "utf-8", "MPLBACKEND": "Agg"},
    )


def test_ein_konsolenprogramm_darf_plt_show_aufrufen(tmp_path: Path) -> None:
    lauf = _starten(PROGRAMM, tmp_path)

    assert lauf.returncode == 0, lauf.stderr
    assert "Diagramm angezeigt." in lauf.stdout


def test_die_kurve_landet_wirklich_in_einer_figur(tmp_path: Path) -> None:
    """Nicht nur „es stürzt nicht ab": die Punkte müssen auch
    ankommen. Gespeichert statt angezeigt - ein Bild lässt sich
    nachmessen, ein Fenster nicht."""
    quelltext = PROGRAMM.replace(
        'plt.show()', 'plt.savefig("kurve.png", dpi=72)\nplt.show()'
    )

    lauf = _starten(quelltext, tmp_path)

    assert lauf.returncode == 0, lauf.stderr
    bild = tmp_path / "kurve.png"
    assert bild.is_file()
    assert bild.stat().st_size > 1000, "die Datei ist zu klein für ein Diagramm"


def test_matplotlib_liegt_wirklich_bei() -> None:
    """Der Grund, warum es „umsonst" geht - und der Tag, an dem jemand
    die Abhängigkeit entfernt, fällt hier auf."""
    import matplotlib

    assert matplotlib.__version__

    pyproject = (Path(__file__).resolve().parent.parent / "pyproject.toml").read_text(
        encoding="utf-8"
    )
    assert "matplotlib" in pyproject


def test_das_qt_backend_ist_da(tmp_path: Path) -> None:
    """Ohne Fenster kein `plt.show()`. Auf einem Rechner mit PySide6 -
    und den hat jeder Natter-Nutzer - muss matplotlib das Qt-Backend
    finden; sonst öffnete sich beim Schüler nichts."""
    quelltext = (
        # `backend_qtagg` ist das Modul, das matplotlib nimmt, wenn ein
        # Fenster aufgehen soll. Lässt es sich importieren, ist alles da.
        # (`rcsetup.all_backends` gäbe die Liste aller Backends - das
        # gibt es in matplotlib 3.11 nicht mehr, nachgemessen.)
        "from matplotlib.backends import backend_qtagg\n"
        'print("Qt-Backend:", backend_qtagg.FigureCanvasQTAgg.__name__)\n'
    )

    lauf = _starten(quelltext, tmp_path)

    assert lauf.returncode == 0, lauf.stderr
    assert "Qt-Backend:" in lauf.stdout


@pytest.mark.parametrize(
    ("aufruf", "erwartet"),
    [
        ("plt.bar([1, 2, 3], [4, 5, 6])", "Balken"),
        ("plt.scatter([1, 2, 3], [4, 5, 6])", "Punktwolke"),
        ("plt.pie([3, 4, 5])", "Kuchen"),
    ],
)
def test_die_ueblichen_diagrammarten_gehen_auch(
    tmp_path: Path, aufruf: str, erwartet: str
) -> None:
    quelltext = (
        "import matplotlib\n"
        'matplotlib.use("Agg")\n'
        "import matplotlib.pyplot as plt\n"
        f"{aufruf}\n"
        "plt.show()\n"
        f'print("{erwartet} gezeichnet.")\n'
    )

    lauf = _starten(quelltext, tmp_path)

    assert lauf.returncode == 0, lauf.stderr
    assert f"{erwartet} gezeichnet." in lauf.stdout
