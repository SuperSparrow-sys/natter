"""Tests für „⋮ → Umbenennen …“/„Löschen …“ auf Units im Projekt-
Explorer: die Units-Seite hatte
bislang keine Möglichkeit, Dateien umzubenennen oder zu löschen außer
über den Windows-Explorer nebenbei.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from ide.shell.hauptfenster import HauptFenster


def _projekt_kopie(tmp_path: Path) -> Path:
    original = Path(__file__).resolve().parent.parent / "beispielprojekte" / "06_Kontoverwaltung"
    ziel = tmp_path / "06_Kontoverwaltung"
    shutil.copytree(original, ziel)
    return ziel


def test_explorer_zeigt_einen_knopf_fuer_jede_unit(tmp_path: Path) -> None:
    fenster = HauptFenster()
    projekt = fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")

    mit_knopf = set()
    ohne_knopf = set()
    for index in range(fenster.explorer.units_gruppe.childCount()):
        eintrag = fenster.explorer.units_gruppe.child(index)
        ziel = mit_knopf if fenster.explorer.itemWidget(eintrag, 1) else ohne_knopf
        ziel.add(eintrag.text(0))

    assert projekt.units()  # sanity: es gibt überhaupt Units
    assert mit_knopf == {"u_konto.py"}
    # `u_main.py` heisst wie `u_main.pfm`, und das ist keine
    # Schreibweise, sondern die Verbindung zwischen beiden. Eine davon
    # allein umzubenennen zerrisse das Paar - deshalb kein Menue.
    assert ohne_knopf == {"u_main.py"}


def test_unit_umbenennen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fenster = HauptFenster()
    projekt = fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")
    unit_pfad = next(p for p in projekt.units() if p.stem == "u_konto")

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QInputDialog.getInt", lambda *a, **k: (0, False)
    )
    monkeypatch.setattr(
        "ide.shell.hauptfenster.QInputDialog.getText",
        staticmethod(lambda *a, **k: ("u_konto_neu.py", True)),
    )

    fenster._unit_umbenennen(unit_pfad)

    neuer_pfad = unit_pfad.parent / "u_konto_neu.py"
    assert neuer_pfad.exists()
    assert not unit_pfad.exists()
    assert any(p.name == "u_konto_neu.py" for p in fenster.projekt.units())


def test_unit_umbenennen_haelt_offenen_tab_synchron(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    projekt = fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")
    unit_pfad = next(p for p in projekt.units() if p.stem == "u_konto")
    editor = fenster.datei_oeffnen(unit_pfad)

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QInputDialog.getText",
        staticmethod(lambda *a, **k: ("u_konto_neu.py", True)),
    )

    fenster._unit_umbenennen(unit_pfad)

    neuer_pfad = unit_pfad.parent / "u_konto_neu.py"
    from ide.shell.hauptfenster import _PFAD_EIGENSCHAFT

    assert editor.property(_PFAD_EIGENSCHAFT) == str(neuer_pfad)
    index = fenster.editor_tabs.indexOf(editor)
    assert fenster.editor_tabs.tabText(index) == "u_konto_neu.py"


def test_unit_umbenennen_auf_existierenden_namen_wird_abgelehnt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    projekt = fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")
    unit_pfad = next(p for p in projekt.units() if p.stem == "u_konto")
    (unit_pfad.parent / "schon_da.py").write_text("x = 1\n", encoding="utf-8")

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QInputDialog.getText",
        staticmethod(lambda *a, **k: ("schon_da.py", True)),
    )

    fenster._unit_umbenennen(unit_pfad)

    assert unit_pfad.exists()  # unverändert


def test_unit_loeschen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fenster = HauptFenster()
    projekt = fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")
    unit_pfad = next(p for p in projekt.units() if p.stem == "u_konto")
    fenster.datei_oeffnen(unit_pfad)

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )

    fenster._unit_loeschen(unit_pfad)

    assert not unit_pfad.exists()
    assert fenster.editor_tabs.count() == 0
    assert not any(p.name == unit_pfad.name for p in fenster.projekt.units())


def test_unit_loeschen_bei_nein_bleibt_erhalten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    projekt = fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")
    unit_pfad = next(p for p in projekt.units() if p.stem == "u_konto")

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
    )

    fenster._unit_loeschen(unit_pfad)

    assert unit_pfad.exists()
