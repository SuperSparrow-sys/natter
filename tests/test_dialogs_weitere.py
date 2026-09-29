"""Die Dialoge aus Punkt 90: `ask_yes_no`, `save_dialog`,
`color_dialog`, `input_number`.

Kein Dialog wird wirklich gezeigt. `pcl.dialogs._zeigen` ist die
eine Stelle, an der ein Dialog modal wartet; die Tests ersetzen sie
und bedienen den eingerichteten Dialog selbst.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QDialog, QInputDialog, QMessageBox

import pcl
from pcl import dialogs


def _bedienen(
    monkeypatch: pytest.MonkeyPatch, handlung: Callable[[QDialog], int]
) -> list[QDialog]:
    gesehen: list[QDialog] = []

    def zeigen(dialog: QDialog) -> int:
        gesehen.append(dialog)
        return handlung(dialog)

    monkeypatch.setattr(dialogs, "_zeigen", zeigen)
    return gesehen


def _knopf(box: QMessageBox, text: str):
    return next(knopf for knopf in box.buttons() if knopf.text() == text)


def test_alle_vier_stehen_in_pcl() -> None:
    for name in ("ask_yes_no", "save_dialog", "color_dialog", "input_number"):
        assert name in pcl.__all__
        assert callable(getattr(pcl, name))


# -- ask_yes_no ---------------------------------------------------------


def test_ask_yes_no_liefert_true_fuer_ja(monkeypatch) -> None:
    gesehen = _bedienen(monkeypatch, lambda box: _knopf(box, "Ja").click() or 0)
    assert dialogs.ask_yes_no("Alles löschen?") is True
    assert gesehen[0].text() == "Alles löschen?"


def test_ask_yes_no_liefert_false_fuer_nein(monkeypatch) -> None:
    _bedienen(monkeypatch, lambda box: _knopf(box, "Nein").click() or 0)
    assert dialogs.ask_yes_no("Alles löschen?") is False


def test_ask_yes_no_ohne_antwort_ist_nein(monkeypatch) -> None:
    _bedienen(monkeypatch, lambda box: 0)
    assert dialogs.ask_yes_no("Alles löschen?") is False


def test_ask_yes_no_hat_deutsche_knoepfe(monkeypatch) -> None:
    gesehen = _bedienen(monkeypatch, lambda box: 0)
    dialogs.ask_yes_no("Weiter?", "Frage")
    box = gesehen[0]
    assert sorted(knopf.text() for knopf in box.buttons()) == ["Ja", "Nein"]
    assert box.windowTitle() == "Frage"


# -- save_dialog --------------------------------------------------------


def test_save_dialog_liefert_den_gewaehlten_pfad(monkeypatch, tmp_path: Path) -> None:
    ziel = tmp_path / "notizen.txt"

    def waehlen(dialog) -> int:
        dialog.selectFile(str(ziel))
        return QDialog.DialogCode.Accepted.value

    gesehen = _bedienen(monkeypatch, waehlen)
    pfad = dialogs.save_dialog()

    assert Path(pfad) == ziel
    assert gesehen[0].windowTitle() == "Datei speichern"
    assert gesehen[0].defaultSuffix() == "txt"


def test_save_dialog_bei_abbruch_leer(monkeypatch) -> None:
    _bedienen(monkeypatch, lambda dialog: QDialog.DialogCode.Rejected.value)
    assert dialogs.save_dialog("Speichern unter", dateiname="a.txt") == ""


def test_save_dialog_nimmt_die_endung_aus_dem_filter() -> None:
    assert dialogs._erste_endung("CSV-Dateien (*.csv)") == "csv"
    assert dialogs._erste_endung("Alle Dateien (*.*)") == ""
    assert dialogs._erste_endung("Irgendwas") == ""


# -- color_dialog -------------------------------------------------------


def test_color_dialog_liefert_rrggbb(monkeypatch) -> None:
    def waehlen(dialog) -> int:
        dialog.setCurrentColor(QColor("#E53935"))
        dialog.accept()
        return QDialog.DialogCode.Accepted.value

    gesehen = _bedienen(monkeypatch, waehlen)
    assert dialogs.color_dialog("#00ff00") == "#e53935"
    assert gesehen[0].windowTitle() == "Farbe auswählen"


def test_color_dialog_startet_mit_der_uebergebenen_farbe(monkeypatch) -> None:
    gesehen = _bedienen(monkeypatch, lambda dialog: QDialog.DialogCode.Rejected.value)
    assert dialogs.color_dialog("#123456") == ""
    assert gesehen[0].currentColor().name() == "#123456"


# -- input_number -------------------------------------------------------


def test_input_number_liefert_eine_ganze_zahl(monkeypatch) -> None:
    def eingeben(dialog: QInputDialog) -> int:
        dialog.setIntValue(42)
        return QDialog.DialogCode.Accepted.value

    gesehen = _bedienen(monkeypatch, eingeben)
    ergebnis = dialogs.input_number("Anmeldung", "Alter:", 16, 6, 99)

    assert ergebnis == 42
    assert isinstance(ergebnis, int)
    dialog = gesehen[0]
    assert (dialog.intMinimum(), dialog.intMaximum()) == (6, 99)
    assert dialog.labelText() == "Alter:"
    assert dialog.cancelButtonText() == "Abbrechen"


def test_input_number_haelt_den_bereich_ein(monkeypatch) -> None:
    def eingeben(dialog: QInputDialog) -> int:
        dialog.setIntValue(500)
        return QDialog.DialogCode.Accepted.value

    _bedienen(monkeypatch, eingeben)
    assert dialogs.input_number("T", "F", 5, 0, 10) == 10


def test_input_number_mit_stellen_liefert_eine_kommazahl(monkeypatch) -> None:
    def eingeben(dialog: QInputDialog) -> int:
        dialog.setDoubleValue(2.345)
        return QDialog.DialogCode.Accepted.value

    gesehen = _bedienen(monkeypatch, eingeben)
    ergebnis = dialogs.input_number("Kasse", "Preis:", 1.5, 0, 100, stellen=2)

    assert ergebnis == pytest.approx(2.35, abs=0.006)
    assert isinstance(ergebnis, float)
    assert gesehen[0].locale().decimalPoint() == ","


def test_input_number_bei_abbruch_der_standard(monkeypatch) -> None:
    _bedienen(monkeypatch, lambda dialog: QDialog.DialogCode.Rejected.value)
    assert dialogs.input_number("T", "F", 7) == 7
