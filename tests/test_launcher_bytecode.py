"""Eine Umgebungsvariable des Kontos lädt keinen fremden Bytecode in
die IDE (Punkt 272).

Mit gesetztem `PYTHONPYCACHEPREFIX` holt Python die `.pyc` jedes
Moduls aus einem Ordner unter diesem Präfix. Eine dort abgelegte
`.pyc` mit `unchecked-hash` ersetzte `pcl.pruefungsmodus`, ohne dass
sich im Programmordner eine Datei ändert. Der Test startet die
Python so, wie `Natter.exe` es tut - mit denselben Schaltern und
derselben Umgebung -, und legt vorher eine abweichende `.pyc` unter
das Präfix.
"""

from __future__ import annotations

import importlib.util
import py_compile
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QIcon

from ide.integritaet import start_pruefung
from tools import launcher

WURZEL = Path(__file__).resolve().parent.parent
QUELLE = WURZEL / "pcl" / "pruefungsmodus.py"


def _pyc_unter_praefix(praefix: Path) -> Path:
    """Der Ort, an dem Python mit `praefix` die `.pyc` von
    `pcl/pruefungsmodus.py` sucht."""
    alt = sys.pycache_prefix
    sys.pycache_prefix = str(praefix)
    try:
        return Path(importlib.util.cache_from_source(str(QUELLE)))
    finally:
        sys.pycache_prefix = alt


def test_ein_fremdes_pycache_praefix_ersetzt_den_pruefungsmodus_nicht(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    praefix = tmp_path / "praefix"
    gefaelscht = tmp_path / "gefaelscht.py"
    gefaelscht.write_text(
        "def laeuft():\n    return 'GEFAELSCHT'\n", encoding="utf-8"
    )
    ziel = _pyc_unter_praefix(praefix)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    py_compile.compile(
        str(gefaelscht),
        cfile=str(ziel),
        doraise=True,
        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH,
    )
    monkeypatch.setenv("PYTHONPYCACHEPREFIX", str(praefix))

    befehl = launcher.startbefehl(Path(sys.executable), [])
    schalter = befehl[1:befehl.index("-m")]
    ergebnis = subprocess.run(
        [
            sys.executable,
            *schalter,
            "-c",
            "import pcl.pruefungsmodus as m; "
            "print(m.__cached__); print(m.laeuft())",
        ],
        cwd=str(WURZEL),
        env=launcher.eigene_umgebung(),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert ergebnis.returncode == 0, ergebnis.stderr
    herkunft, wert = ergebnis.stdout.strip().splitlines()[-2:]
    assert wert != "GEFAELSCHT"
    assert Path(herkunft).resolve().is_relative_to(WURZEL / "pcl")


def test_die_ide_python_liest_keine_python_variablen() -> None:
    befehl = launcher.startbefehl(Path("pythonw.exe"), ["a.natter"])
    assert befehl[:5] == ["pythonw.exe", "-E", "-s", "-m", "ide"]
    assert befehl[5:] == ["a.natter"]


@pytest.mark.parametrize(
    "name",
    [
        "PYTHONPYCACHEPREFIX",
        "PYTHONSTARTUP",
        "PYTHONINSPECT",
        "QT_PLUGIN_PATH",
        "QT_QPA_PLATFORM_PLUGIN_PATH",
        "QML2_IMPORT_PATH",
    ],
)
def test_nachladende_variablen_gehen_nicht_an_gestartete_programme(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(name, r"C:\woanders")
    assert name not in launcher.eigene_umgebung()


def test_die_startpruefung_meldet_ein_pycache_praefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "pycache_prefix", str(tmp_path))
    ergebnis = start_pruefung.installation_pruefen(tmp_path)
    assert ergebnis is not None
    assert not ergebnis.in_ordnung
    assert "Bytecode" in ergebnis.als_meldung()
    assert str(tmp_path) in ergebnis.als_meldung()


def test_qt_bekommt_keine_befehlszeilenschalter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`-platformpluginpath <Ordner>` hinter `Natter.exe` lüde Plugins
    aus einem beliebigen Ordner; an Qt geht nur der Programmname."""
    from ide import main

    uebergeben: list[list[str]] = []

    class Attrappe:
        @staticmethod
        def instance() -> None:
            return None

        def __init__(self, argv: list[str]) -> None:
            uebergeben.append(list(argv))

        def setOrganizationName(self, _: str) -> None:  # noqa: N802
            pass

        def setApplicationName(self, _: str) -> None:  # noqa: N802
            pass

        def windowIcon(self) -> QIcon:  # noqa: N802
            return QIcon()

        def setWindowIcon(self, _: QIcon) -> None:  # noqa: N802
            pass

    monkeypatch.setattr(main, "QApplication", Attrappe)
    monkeypatch.setattr(main, "deutsch_einschalten", lambda _: None)
    monkeypatch.setattr(
        sys, "argv", ["ide", "-platformpluginpath", r"C:\woanders"]
    )
    main.anwendung_erzeugen()
    assert uebergeben == [["ide"]]
