"""Das Schülerprogramm zeigt seine Fehler selbst (M12).

Der Fehlerkatalog ist das didaktische Kernstück von Natter: statt eines
englischen Tracebacks eine Meldung in drei Teilen – Wo, Was, Prüfe.
Benutzt wurde er bis M12 aber nur vom Debugger. Wer sein Programm
mit Strg+F5 startete – also so, wie man ein fertiges Programm startet –,
bekam im Konsolenprogramm den rohen englischen Traceback und im
GUI-Programm gar nichts: es läuft ohne Konsolenfenster, das Fenster
verschwand einfach.

Nachgemessen war das so: ein `ZeroDivisionError` in `create_components`
ergab zwölf Zeilen Traceback, davon elf aus `pcl` und Qt.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from pcl.fehleranzeige import UNBEKANNT, einhaengen, fehler_zeigen, fehlertext


def _ausgeloest(aufruf) -> tuple:
    try:
        aufruf()
    except BaseException:  # noqa: BLE001 - genau darum geht es
        return sys.exc_info()
    raise AssertionError("Der Aufruf hat gar keinen Fehler ausgelöst.")


def test_ein_bekannter_fehler_wird_zur_drei_teile_meldung() -> None:
    text = fehlertext(*_ausgeloest(lambda: 1 / 0))

    assert "Wo:" in text
    assert "Was:" in text
    assert "Prüfe:" in text
    assert "Division durch 0" in text


def test_die_meldung_nennt_die_zeile_im_schuelercode() -> None:
    """Nicht die Zeile in `pcl` oder Qt – das ist der halbe Wert der
    Meldung."""

    def rechnen() -> None:
        summe, anzahl = 10, 0
        print(summe / anzahl)

    text = fehlertext(*_ausgeloest(rechnen))

    assert "test_fehleranzeige_im_programm.py" in text
    assert "summe / anzahl" in text


def test_ein_unbekannter_fehler_bekommt_wenigstens_eine_erklaerung() -> None:
    class _EigenerFehler(Exception):
        pass

    def werfen() -> None:
        raise _EigenerFehler("etwas Eigenes")

    text = fehlertext(*_ausgeloest(werfen))

    assert UNBEKANNT in text
    assert "etwas Eigenes" in text  # der Traceback steht darunter


def test_im_pruefungsmodus_faellt_der_pruefe_teil_weg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der Prüfungsmodus muss auch im laufenden Programm greifen –
    sonst wäre er über den Umweg „Programm starten“ auszuhebeln."""
    import pcl.pruefungsmodus as modul

    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    modul.starten()

    text = fehlertext(*_ausgeloest(lambda: 1 / 0))

    assert "Was:" in text
    assert "Prüfe:" not in text


def test_einhaengen_setzt_den_haken(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "excepthook", sys.__excepthook__)

    einhaengen()

    assert sys.excepthook is fehler_zeigen


def test_ein_gui_programm_zeigt_die_meldung_im_fenster(
    qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    from PySide6.QtWidgets import QMessageBox

    gezeigt: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "exec", lambda selbst: gezeigt.append(selbst.informativeText())
    )

    fehler_zeigen(*_ausgeloest(lambda: 1 / 0))

    assert gezeigt, "Es kam kein Fenster."
    assert "Division durch 0" in gezeigt[0]


def test_application_run_haengt_die_anzeige_ein(
    qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der Weg, über den es im echten GUI-Programm passiert."""
    from pcl import Application, Form

    monkeypatch.setattr(sys, "excepthook", sys.__excepthook__)

    class _Formular(Form):
        def create_components(self) -> None:
            pass

    anwendung = Application()
    monkeypatch.setattr(anwendung._qapp, "exec", lambda: 0)

    anwendung.run(_Formular)

    assert sys.excepthook is fehler_zeigen


@pytest.mark.parametrize(
    ("quelltext", "erwartet"),
    [
        ("zahlen = [1, 2, 3]" + chr(10) + "print(zahlen[5])" + chr(10), "Index"),
        ("print(10 / 0)" + chr(10), "Division durch 0"),
    ],
    ids=["index", "division"],
)
def test_ein_konsolenprogramm_meldet_sich_auf_deutsch(
    tmp_path: Path, quelltext: str, erwartet: str
) -> None:
    """Gegen die echte Hülle aus `ide/run/starter.py`, in einem echten
    Unterprozess – hier hängt zu viel davon ab, als dass eine Attrappe
    reichte."""
    from ide.run.starter import _KONSOLEN_HUELLE

    (tmp_path / "main.py").write_text(quelltext, encoding="utf-8")
    # Das abschließende input() würde den Test anhalten.
    huelle = _KONSOLEN_HUELLE.replace(
        "    try:\n        input(", "    try:\n        pass  # input("
    )

    ergebnis = subprocess.run(
        [sys.executable, "-c", huelle, "Titel", "main.py"],
        cwd=tmp_path,
        capture_output=True,
        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        timeout=60,
        check=False,
    )

    ausgabe = ergebnis.stderr.decode("utf-8", "replace")
    assert "Wo:" in ausgabe
    assert erwartet in ausgabe
    assert "Traceback (most recent call last)" not in ausgabe
    assert ergebnis.returncode == 1
