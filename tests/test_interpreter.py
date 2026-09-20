"""Womit Natter Python-Code startet (M12).

Vom Nutzer im installierten Programm gemeldet: „die Konsole und die GUI
sind beim Start nicht aufgegangen, sondern nur ein weiteres Fenster von
Natter.“

Die Ursache trifft fünf Stellen, nicht nur die auffälligste: das
Schülerprogramm, den Debugger, die Prüfung vor dem Start, die
Paketverwaltung und den Exe-Export. Alle schrieben `sys.executable` –
im Entwicklungsbaum der Python aus `.venv`, in der gebauten
`Natter.exe` aber die Exe selbst. Aus `Natter.exe main.py` wurde
deshalb ein zweites Natter-Fenster.

Eine eigene Python-Installation daneben zu verlangen wäre für einen
Schulrechner der falsche Weg. Die Exe enthält einen vollständigen
Python; mit `--python` davor reicht sie ihn heraus.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from ide.run.interpreter import (
    PYTHON_FLAGGE,
    RUFF_DATEINAME,
    als_python_ausfuehren,
    ist_gebaut,
    python_befehl,
    ruff_befehl,
)


def test_im_entwicklungsbaum_ist_es_der_python() -> None:
    assert python_befehl() == [sys.executable]
    assert ist_gebaut() is False


def test_in_der_gebauten_exe_kommt_die_flagge_davor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`sys.frozen` setzt PyInstaller im Bundle."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)

    assert python_befehl() == [sys.executable, PYTHON_FLAGGE]


def test_ein_skript_wird_ausgefuehrt(tmp_path: Path, capsys) -> None:
    skript = tmp_path / "probe.py"
    skript.write_text('print("gelaufen")' + chr(10), encoding="utf-8")

    rueckgabe = als_python_ausfuehren([str(skript)])

    assert rueckgabe == 0
    assert "gelaufen" in capsys.readouterr().out


def test_das_skript_sieht_sein_eigenes_argv(tmp_path: Path, capsys) -> None:
    """Sonst stünde dort der Natter-Aufruf, und `sys.argv[1]` wäre die
    Flagge statt des ersten echten Arguments."""
    skript = tmp_path / "probe.py"
    skript.write_text("import sys" + chr(10) + "print(sys.argv[1])" + chr(10), encoding="utf-8")

    als_python_ausfuehren([str(skript), "hallo"])

    assert "hallo" in capsys.readouterr().out


def test_ein_modul_wird_ausgefuehrt(capsys) -> None:
    """Der Weg, über den `ruff` und `debugpy` gestartet werden."""
    rueckgabe = als_python_ausfuehren(["-m", "json.tool", "--help"])

    assert rueckgabe == 0
    assert "usage" in capsys.readouterr().out.lower()


def test_quelltext_wird_ausgefuehrt(capsys) -> None:
    """Der Weg, über den die Konsolen-Hülle läuft."""
    als_python_ausfuehren(["-c", 'print("aus -c")'])

    assert "aus -c" in capsys.readouterr().out


def test_der_rueckgabewert_des_programms_bleibt_erhalten(tmp_path: Path) -> None:
    skript = tmp_path / "probe.py"
    skript.write_text("import sys" + chr(10) + "sys.exit(3)" + chr(10), encoding="utf-8")

    assert als_python_ausfuehren([str(skript)]) == 3


def test_ohne_aufruf_dahinter_gibt_es_eine_meldung(capsys) -> None:
    assert als_python_ausfuehren([]) == 2
    assert "fehlt" in capsys.readouterr().err


def test_der_einstiegspunkt_reicht_python_durch() -> None:
    """Gegen den echten Einstiegspunkt, in einem echten Unterprozess -
    genau so ruft sich die gebaute Exe selbst auf."""
    ergebnis = subprocess.run(
        [sys.executable, "-m", "ide", PYTHON_FLAGGE, "-c", 'print("durchgereicht")'],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )

    assert ergebnis.returncode == 0
    assert "durchgereicht" in ergebnis.stdout


@pytest.mark.parametrize(
    "modul",
    ["ide.run.starter", "ide.run.pruefung", "ide.debugger.dap_client"],
)
def test_keine_stelle_ruft_sys_executable_noch_direkt(modul: str) -> None:
    """Der Rundlauf über alle Stellen, die einen Unterprozess starten:
    wer hier `sys.executable` in eine Befehlsliste schreibt, baut den
    gemeldeten Fehler wieder ein."""
    import importlib

    quelle = Path(importlib.import_module(modul).__file__).read_text(encoding="utf-8")

    assert "python_befehl()" in quelle or "ruff_befehl()" in quelle
    assert "sys.executable," not in quelle


# -- ruff ----------------------------------------------------------------


def test_ruff_wird_im_entwicklungsbaum_gefunden() -> None:
    befehl = ruff_befehl()

    assert len(befehl) == 1
    assert Path(befehl[0]).is_file()


def test_ruff_kommt_in_der_exe_aus_dem_bundle(monkeypatch: pytest.MonkeyPatch) -> None:
    """Das Python-Paket `ruff` ist nur ein Finder, der `ruff.exe` in den
    `Scripts`-Ordnern sucht - die gibt es in der Exe nicht. Dort liegt
    die Binärdatei selbst im Bundle."""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", r"C:\Bundle", raising=False)

    assert ruff_befehl() == [str(Path(r"C:\Bundle") / RUFF_DATEINAME)]


def test_die_pruefung_ruft_ruff_ohne_umweg_ueber_python() -> None:
    """Ein `python -m ruff` würde in der Exe wieder den Finder treffen."""
    from ide.run import pruefung

    quelle = Path(pruefung.__file__).read_text(encoding="utf-8")

    assert "ruff_befehl()" in quelle
    assert '"-m",' not in quelle


def test_ein_absturz_fliegt_nicht_durch(
    tmp_path: Path, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In der gebauten Exe darf ein Fehler niemals bis nach oben
    durchfliegen: PyInstallers Bootloader fängt ihn dort selbst ab und
    wartet auf einen Klick in ein Fenster, das hinter dem Programm liegt
    - das sah wie ein Hänger aus (in der gebauten Exe nachgemessen)."""
    import pcl.fehleranzeige as anzeige

    # Wie in einem Konsolenprogramm: dort gibt es keine Qt-Anwendung,
    # die Meldung geht in die Konsole. Ohne diese Festlegung zeigte der
    # Test im Qt-Testlauf ein echtes Fenster und wartete darauf, dass
    # jemand klickt - derselbe Hänger, um den es hier geht.
    monkeypatch.setattr(anzeige, "_in_fenster_zeigen", lambda _text: False)
    skript = tmp_path / "kaputt.py"
    skript.write_text("print(10 / 0)" + chr(10), encoding="utf-8")

    rueckgabe = als_python_ausfuehren([str(skript)])

    assert rueckgabe == 1
    ausgabe = capsys.readouterr()
    assert "Division durch 0" in ausgabe.err
    assert "Wo:" in ausgabe.err


def test_ein_konsolenprogramm_bekommt_die_fehleranzeige(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Es läuft nicht über `Application.run()` und hätte sonst gar
    keine."""
    import pcl.fehleranzeige as anzeige

    monkeypatch.setattr(sys, "excepthook", sys.__excepthook__)
    skript = tmp_path / "gut.py"
    skript.write_text("x = 1" + chr(10), encoding="utf-8")

    als_python_ausfuehren([str(skript)])

    assert sys.excepthook is anzeige.fehler_zeigen
