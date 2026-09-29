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


def test_explorer_zeigt_einen_knopf_fuer_jede_unit(tmp_path: Path, hauptfenster) -> None:
    projekt = hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")

    mit_knopf = set()
    ohne_knopf = set()
    for index in range(hauptfenster.explorer.units_gruppe.childCount()):
        eintrag = hauptfenster.explorer.units_gruppe.child(index)
        ziel = mit_knopf if hauptfenster.explorer.itemWidget(eintrag, 1) else ohne_knopf
        ziel.add(eintrag.text(0))

    assert projekt.units()  # sanity: es gibt überhaupt Units
    assert mit_knopf == {"u_konto.py"}
    # `u_main.py` heißt wie `u_main.pfm`, und das ist keine
    # Schreibweise, sondern die Verbindung zwischen beiden. Eine davon
    # allein umzubenennen zerrisse das Paar - deshalb kein Menü.
    assert ohne_knopf == {"u_main.py"}


def test_unit_umbenennen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster) -> None:
    projekt = hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")
    unit_pfad = next(p for p in projekt.units() if p.stem == "u_konto")

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QInputDialog.getInt", lambda *a, **k: (0, False)
    )
    monkeypatch.setattr(
        "ide.shell.hauptfenster.QInputDialog.getText",
        staticmethod(lambda *a, **k: ("u_konto_neu.py", True)),
    )

    hauptfenster._unit_umbenennen(unit_pfad)

    neuer_pfad = unit_pfad.parent / "u_konto_neu.py"
    assert neuer_pfad.exists()
    assert not unit_pfad.exists()
    assert any(p.name == "u_konto_neu.py" for p in hauptfenster.projekt.units())


def test_unit_umbenennen_haelt_offenen_tab_synchron(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    projekt = hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")
    unit_pfad = next(p for p in projekt.units() if p.stem == "u_konto")
    editor = hauptfenster.datei_oeffnen(unit_pfad)

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QInputDialog.getText",
        staticmethod(lambda *a, **k: ("u_konto_neu.py", True)),
    )

    hauptfenster._unit_umbenennen(unit_pfad)

    neuer_pfad = unit_pfad.parent / "u_konto_neu.py"
    from ide.shell.hauptfenster import _PFAD_EIGENSCHAFT

    assert editor.property(_PFAD_EIGENSCHAFT) == str(neuer_pfad)
    index = hauptfenster.editor_tabs.indexOf(editor)
    assert hauptfenster.editor_tabs.tabText(index) == "u_konto_neu.py"


def test_unit_umbenennen_auf_existierenden_namen_wird_abgelehnt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    projekt = hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")
    unit_pfad = next(p for p in projekt.units() if p.stem == "u_konto")
    (unit_pfad.parent / "schon_da.py").write_text("x = 1\n", encoding="utf-8")

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QInputDialog.getText",
        staticmethod(lambda *a, **k: ("schon_da.py", True)),
    )

    hauptfenster._unit_umbenennen(unit_pfad)

    assert unit_pfad.exists()  # unverändert


def test_unit_loeschen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster) -> None:
    projekt = hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")
    unit_pfad = next(p for p in projekt.units() if p.stem == "u_konto")
    hauptfenster.datei_oeffnen(unit_pfad)

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )

    hauptfenster._unit_loeschen(unit_pfad)

    assert not unit_pfad.exists()
    assert hauptfenster.editor_tabs.count() == 0
    assert not any(p.name == unit_pfad.name for p in hauptfenster.projekt.units())


def test_unit_loeschen_bei_nein_bleibt_erhalten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    projekt = hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")
    unit_pfad = next(p for p in projekt.units() if p.stem == "u_konto")

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
    )

    hauptfenster._unit_loeschen(unit_pfad)

    assert unit_pfad.exists()


def test_unit_loeschen_schliesst_auch_den_designer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster_bauen
) -> None:
    """Punkt 139: der Designer-Reiter blieb offen, und die nächste
    Änderung darin schrieb `.pfm` und `_design.py` wieder auf die
    Platte, die Unit aber nicht."""
    from pcl import Button

    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")
    pfm = fenster.formular_erzeugen("u_zweit")
    canvas = fenster._aktueller_canvas
    assert canvas is not None and canvas.pfm_pfad == pfm
    dateien = [pfm, pfm.with_suffix(".py"), pfm.parent / "u_zweit_design.py"]
    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )
    monkeypatch.setattr("ide.shell.hauptfenster.papierkorb_verfuegbar", lambda *_a: False)

    fenster._unit_loeschen(pfm.with_suffix(".py"))

    titel = [fenster.editor_tabs.tabText(i) for i in range(fenster.editor_tabs.count())]
    assert not any("u_zweit" in t for t in titel)
    assert str(pfm) not in fenster._pfad_zu_formular
    # Auch eine Änderung, die den Designer noch erreicht, legt nichts
    # wieder an.
    canvas.komponente_platzieren(Button, 10, 10)
    assert [d for d in dateien if d.exists()] == []


def _umbenennen(fenster: HauptFenster, pfad: Path, name: str, monkeypatch) -> list[str]:
    monkeypatch.setattr(
        "ide.shell.hauptfenster.QInputDialog.getText",
        staticmethod(lambda *a, **k: (name, True)),
    )
    meldungen: list[str] = []
    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.warning",
        staticmethod(lambda _eltern, _titel, text: meldungen.append(text)),
    )
    fenster._unit_umbenennen(pfad)
    return meldungen


@pytest.mark.parametrize("name", ["mein konto", "u_konto_design", "2konto", "class"])
def test_unit_umbenennen_lehnt_ungueltige_namen_ab(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, hauptfenster
) -> None:
    """Punkt 154: „mein konto“ ließ sich nicht importieren, und
    „u_konto_design“ verschwand als vermeintlich erzeugte Datei aus
    dem Explorer."""
    projekt = hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")
    unit_pfad = projekt.ordner / "u_konto.py"

    meldungen = _umbenennen(hauptfenster, unit_pfad, name, monkeypatch)

    assert unit_pfad.exists()
    assert not (projekt.ordner / f"{name}.py").exists()
    assert len(meldungen) == 1 and name in meldungen[0]


def test_unit_umbenennen_fuehrt_die_importe_nach(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster_bauen
) -> None:
    import os
    import subprocess
    import sys

    fenster = hauptfenster_bauen()
    projekt = fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "06_Kontoverwaltung.natter")
    ordner = projekt.ordner
    # Eine zweite Datei mit einfachem `import`, das `u_konto.euro`
    # weiter benutzen können muss.
    (ordner / "u_hilfe.py").write_text(
        "import u_konto  # Kontoklasse\n\nWERT = u_konto.euro(2)\n", encoding="utf-8"
    )
    editor = fenster.datei_oeffnen(ordner / "u_main.py")

    _umbenennen(fenster, ordner / "u_konto.py", "u_konten", monkeypatch)

    assert (ordner / "u_konten.py").exists()
    haupt = (ordner / "u_main.py").read_text(encoding="utf-8")
    assert "from u_konten import Konto, NichtGenugGeld, euro" in haupt
    assert "from u_konto import" not in haupt
    assert editor.toPlainText() == haupt
    assert not editor.document().isModified()
    hilfe = (ordner / "u_hilfe.py").read_text(encoding="utf-8")
    assert hilfe.startswith("import u_konten as u_konto  # Kontoklasse\n")
    assert "u_main.py" in fenster.statusBar().currentMessage()

    wurzel = Path(__file__).resolve().parent.parent
    umgebung = dict(os.environ, PYTHONPATH=str(wurzel), QT_QPA_PLATFORM="offscreen")
    lauf = subprocess.run(
        [sys.executable, "-c", "import u_main, u_hilfe"],
        cwd=ordner, env=umgebung, capture_output=True, text=True, timeout=60,
    )
    assert lauf.returncode == 0, lauf.stderr
