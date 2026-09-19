"""Gelöschte Units landen im Papierkorb (M11, Abschnitt 4).

Beim Durchgehen der Frage „gibt es Stellen, an denen Rückgängig fehlt?“
fiel „⋮ → Löschen …“ im Projekt-Explorer auf: es rief `Path.unlink()`
und sagte dazu ehrlich, die Datei sei danach weg. In einem Klassenraum
ist aber genau das der Fall, in dem jemand die falsche Unit erwischt –
und die Arbeit einer Doppelstunde ist nicht wiederzubekommen. Der
Papierkorb ist hier das „Rückgängig“.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from ide.papierkorb import in_den_papierkorb, papierkorb_verfuegbar
from ide.shell.hauptfenster import HauptFenster


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import pcl.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


def _projekt_anlegen(ordner: Path) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text("print('hallo')\n", encoding="utf-8")
    (ordner / "u_weg.py").write_text("# wird geloescht\n", encoding="utf-8")
    (ordner / "test.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Papierkorbtest",
                "type": "console",
                "main": "main.py",
            }
        ),
        encoding="utf-8",
    )
    return ordner


@pytest.mark.skipif(sys.platform != "win32", reason="nur Windows hat einen Papierkorb")
def test_eine_datei_landet_wirklich_im_papierkorb(tmp_path: Path) -> None:
    datei = tmp_path / "wegwerf.txt"
    datei.write_text("inhalt", encoding="utf-8")

    assert in_den_papierkorb(datei) is True
    assert not datei.exists()


def test_eine_fehlende_datei_meldet_sich_wie_unlink(tmp_path: Path) -> None:
    """Ein fehlender oder gesperrter Pfad ist keine Papierkorb-Frage –
    der Aufrufer soll denselben Fehler sehen wie bei `Path.unlink()`."""
    if not papierkorb_verfuegbar():
        pytest.skip("nur Windows hat einen Papierkorb")

    with pytest.raises(FileNotFoundError):
        in_den_papierkorb(tmp_path / "gibtsnicht.txt")


def test_die_nachfrage_verspricht_den_papierkorb(
    einstellungen: QSettings, qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der Text der Nachfrage muss zu dem passen, was danach wirklich
    geschieht – vorher stand dort „landet nicht im Papierkorb“."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    ordner = _projekt_anlegen(tmp_path / "p")
    fenster.projekt_oeffnen(ordner)

    gefragt: list[str] = []

    def _frage(_eltern, _titel, text, *_rest):
        gefragt.append(text)
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", _frage)

    fenster._unit_loeschen(ordner / "u_weg.py")

    assert gefragt, "Es wurde gar nicht nachgefragt."
    # Mehrzahl seit M14: zu einer Unit mit Formular gehören drei
    # Dateien, und die Nachfrage nennt sie alle.
    if papierkorb_verfuegbar():
        assert "landen im Papierkorb" in gefragt[0]
        assert "zurückholen" in gefragt[0]
    else:
        assert "nicht im Papierkorb" in gefragt[0]


def test_nein_laesst_die_datei_stehen(
    einstellungen: QSettings, qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    ordner = _projekt_anlegen(tmp_path / "p")
    fenster.projekt_oeffnen(ordner)
    monkeypatch.setattr(
        QMessageBox, "question", lambda *_a: QMessageBox.StandardButton.No
    )

    fenster._unit_loeschen(ordner / "u_weg.py")

    assert (ordner / "u_weg.py").exists()


def test_ja_raeumt_die_datei_weg(
    einstellungen: QSettings, qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    ordner = _projekt_anlegen(tmp_path / "p")
    fenster.projekt_oeffnen(ordner)
    monkeypatch.setattr(
        QMessageBox, "question", lambda *_a: QMessageBox.StandardButton.Yes
    )

    fenster._unit_loeschen(ordner / "u_weg.py")

    assert not (ordner / "u_weg.py").exists()
    assert "gelöscht" in fenster.statusBar().currentMessage()


def test_das_loeschen_geht_wirklich_ueber_den_papierkorb(
    einstellungen: QSettings, qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sonst könnte die Nachfrage den Papierkorb versprechen, während
    dahinter weiter `unlink()` stünde."""
    import ide.shell.hauptfenster as modul

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    ordner = _projekt_anlegen(tmp_path / "p")
    fenster.projekt_oeffnen(ordner)
    monkeypatch.setattr(
        QMessageBox, "question", lambda *_a: QMessageBox.StandardButton.Yes
    )

    weggeraeumt: list[Path] = []

    def _spion(pfad: Path) -> bool:
        weggeraeumt.append(pfad)
        pfad.unlink()  # der Papierkorb selbst ist oben schon geprüft
        return True

    monkeypatch.setattr(modul, "in_den_papierkorb", _spion)

    fenster._unit_loeschen(ordner / "u_weg.py")

    assert weggeraeumt == [ordner / "u_weg.py"]
