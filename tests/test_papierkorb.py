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
        assert "endgültig gelöscht" in gefragt[0]


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


# -- Laufwerke ohne Papierkorb (Punkt 273) ---------------------------------
#
# Auf dem Heimatlaufwerk auf dem Schulserver oder einem USB-Stick löscht
# Windows endgültig und meldet trotzdem Erfolg. Die Windows-Abfragen
# werden hier nachgebildet; ein echtes Netzlaufwerk gibt es im Testlauf
# nicht.


def _ohne_papierkorb(monkeypatch: pytest.MonkeyPatch) -> None:
    """Das Laufwerk ist fest, die Abfrage des Papierkorbs scheitert
    aber, wie unter einem UNC-Pfad."""
    import ide.papierkorb as modul

    monkeypatch.setattr(modul.sys, "platform", "win32")
    monkeypatch.setattr(modul, "_laufwerksart", lambda _w: modul._DRIVE_FIXED)
    monkeypatch.setattr(modul, "_papierkorb_abgeschaltet", lambda: False)
    monkeypatch.setattr(
        modul, "_papierkorb_abfragen", lambda _w: -2147467259  # E_FAIL
    )


def test_ein_unc_pfad_ohne_papierkorb_wird_erkannt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ide.papierkorb as modul

    _ohne_papierkorb(monkeypatch)
    assert not papierkorb_verfuegbar(Path(r"\server\home\p\u_weg.py"))

    monkeypatch.setattr(modul, "_papierkorb_abfragen", lambda _w: 0)
    assert papierkorb_verfuegbar(Path(r"\server\home\p\u_weg.py"))


def test_netzlaufwerk_und_stick_haben_keinen_papierkorb(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ide.papierkorb as modul

    _ohne_papierkorb(monkeypatch)
    monkeypatch.setattr(modul, "_papierkorb_abfragen", lambda _w: 0)
    for art in (2, 4):  # DRIVE_REMOVABLE, DRIVE_REMOTE
        monkeypatch.setattr(modul, "_laufwerksart", lambda _w, a=art: a)
        assert not papierkorb_verfuegbar(Path(r"H:\p\u_weg.py"))


def test_ohne_papierkorb_warnt_die_nachfrage_statt_ihn_zu_versprechen(
    einstellungen: QSettings,
    hauptfenster_bauen,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fenster = hauptfenster_bauen()
    ordner = _projekt_anlegen(tmp_path / "p")
    fenster.projekt_oeffnen(ordner)
    _ohne_papierkorb(monkeypatch)

    gefragt: list[tuple] = []

    def _frage(_eltern, _titel, text, *rest):
        gefragt.append((text, rest))
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", _frage)

    fenster._unit_loeschen(ordner / "u_weg.py")

    assert gefragt
    text, rest = gefragt[0]
    assert "endgültig gelöscht" in text
    assert "Papierkorb und lassen sich von dort" not in text
    # „Nein“ ist vorausgewählt.
    assert QMessageBox.StandardButton.No in rest[1:]
    assert (ordner / "u_weg.py").exists()


def test_ohne_papierkorb_loescht_ja_endgueltig_ohne_papierkorb_versuch(
    einstellungen: QSettings,
    hauptfenster_bauen,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import ide.shell.hauptfenster as modul

    fenster = hauptfenster_bauen()
    ordner = _projekt_anlegen(tmp_path / "p")
    fenster.projekt_oeffnen(ordner)
    _ohne_papierkorb(monkeypatch)
    monkeypatch.setattr(
        QMessageBox, "question", lambda *_a: QMessageBox.StandardButton.Yes
    )
    versucht: list[Path] = []
    monkeypatch.setattr(
        modul, "in_den_papierkorb", lambda p: versucht.append(p) or True
    )

    fenster._unit_loeschen(ordner / "u_weg.py")

    assert versucht == []
    assert not (ordner / "u_weg.py").exists()


def test_nimmt_der_papierkorb_die_datei_nicht_an_bleibt_sie_stehen(
    einstellungen: QSettings,
    hauptfenster_bauen,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Zugesagt war der Papierkorb; ohne weitere Frage endgültig zu
    löschen, wäre das Gegenteil davon."""
    import ide.shell.hauptfenster as modul

    fenster = hauptfenster_bauen()
    ordner = _projekt_anlegen(tmp_path / "p")
    fenster.projekt_oeffnen(ordner)
    monkeypatch.setattr(modul, "papierkorb_verfuegbar", lambda *_a: True)
    monkeypatch.setattr(
        QMessageBox, "question", lambda *_a: QMessageBox.StandardButton.Yes
    )
    monkeypatch.setattr(modul, "in_den_papierkorb", lambda _p: False)

    fenster._unit_loeschen(ordner / "u_weg.py")

    assert (ordner / "u_weg.py").exists()
    assert "nicht gelöscht" in fenster.statusBar().currentMessage()


def test_windows_warnt_selbst_wenn_doch_endgueltig_geloescht_wuerde(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`FOF_WANTNUKEWARNING` ist gesetzt: ist die Datei etwa größer als
    der Papierkorb, fragt Windows nach, statt still zu löschen."""
    import ide.papierkorb as modul

    if not papierkorb_verfuegbar():
        pytest.skip("nur Windows hat einen Papierkorb")
    datei = tmp_path / "wegwerf.txt"
    datei.write_text("inhalt", encoding="utf-8")
    flags: list[int] = []

    class Shell32:
        @staticmethod
        def SHFileOperationW(zeiger) -> int:  # noqa: N802
            flags.append(zeiger._obj.fFlags)
            return 0

    class Windll:
        shell32 = Shell32()

    monkeypatch.setattr(modul.ctypes, "windll", Windll())
    assert in_den_papierkorb(datei)
    assert flags and flags[0] & modul._FOF_WANTNUKEWARNING
