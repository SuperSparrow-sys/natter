"""Punkt 221: Formulare und Diagramme im Projekt-Explorer umbenennen
und löschen.

Bis 0.3.6 hatten nur Units ohne Formular einen „⋮“-Knopf. Ein über
„Neues Formular …“ angelegtes Formular blieb, bis jemand im
Windows-Explorer drei Dateien von Hand löschte, und für Diagramme
gab es gar nichts.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from ide.shell.hauptfenster import HauptFenster

WURZEL = Path(__file__).resolve().parent.parent


def _projekt_kopie(tmp_path: Path) -> Path:
    original = WURZEL / "beispielprojekte" / "06_Kontoverwaltung"
    ziel = tmp_path / "06_Kontoverwaltung"
    shutil.copytree(original, ziel)
    return ziel / "06_Kontoverwaltung.natter"


def _eintraege(fenster: HauptFenster) -> dict[str, object]:
    baum = fenster.explorer
    ergebnis = {}
    for gruppe in (
        baum.formulare_gruppe, baum.units_gruppe, baum.diagramme_gruppe
    ):
        for i in range(gruppe.childCount()):
            eintrag = gruppe.child(i)
            ergebnis[f"{gruppe.text(0)}/{eintrag.text(0)}"] = eintrag
    return ergebnis


def _aktion(fenster: HauptFenster, schluessel: str, text: str):
    eintrag = _eintraege(fenster)[schluessel]
    knopf = fenster.explorer.itemWidget(eintrag, 1)
    assert knopf is not None, schluessel
    return next(a for a in knopf.menu().actions() if a.text() == text)


@pytest.fixture
def ja(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )
    monkeypatch.setattr(
        "ide.shell.hauptfenster.papierkorb_verfuegbar", lambda *_a: False
    )


def _name_eingeben(monkeypatch: pytest.MonkeyPatch, name: str) -> list[str]:
    monkeypatch.setattr(
        "ide.shell.hauptfenster.QInputDialog.getText",
        staticmethod(lambda *a, **k: (name, True)),
    )
    meldungen: list[str] = []
    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.warning",
        staticmethod(lambda _e, _t, text: meldungen.append(text)),
    )
    return meldungen


def test_formulare_und_diagramme_haben_knopf_und_menue(
    tmp_path: Path, hauptfenster,
) -> None:
    hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path))
    hauptfenster.formular_erzeugen("u_zweit")
    baum = hauptfenster.explorer
    baum.resize(260, 600)
    baum.show()

    eintraege = _eintraege(hauptfenster)
    mit_menue = {
        name
        for name, eintrag in eintraege.items()
        if baum.itemWidget(eintrag, 1) is not None
        and baum.kontextmenue_fuer(baum.visualItemRect(eintrag).center())
        is not None
    }
    assert mit_menue == {
        "Formulare/u_zweit",
        "Units/u_konto.py",
        "Units/u_zweit.py",
        "Diagramme/konto_abheben",
        "Diagramme/konto_entscheidung",
        "Diagramme/konto_klassen",
    }
    # Das Hauptformular startet main.py; weder das Formular noch
    # seine Unit bieten Umbenennen oder Löschen an.
    assert "Formulare/u_main" in eintraege
    assert "Units/u_main.py" in eintraege


def test_formular_loeschen_ueber_den_explorer(
    tmp_path: Path, ja: None, hauptfenster_bauen
) -> None:
    from pcl import Button

    fenster = hauptfenster_bauen()
    projekt = fenster.projekt_oeffnen(_projekt_kopie(tmp_path))
    pfm = fenster.formular_erzeugen("u_zweit")
    canvas = fenster._aktueller_canvas
    fenster.datei_oeffnen(pfm.with_suffix(".py"))
    dateien = [
        pfm, pfm.with_suffix(".py"), projekt.ordner / "u_zweit_design.py"
    ]

    _aktion(fenster, "Formulare/u_zweit", "Löschen …").trigger()

    assert [d for d in dateien if d.exists()] == []
    titel = [
        fenster.editor_tabs.tabText(i)
        for i in range(fenster.editor_tabs.count())
    ]
    assert not any("u_zweit" in t for t in titel)
    assert not any("u_zweit" in s for s in _eintraege(fenster))
    canvas.komponente_platzieren(Button, 10, 10)
    assert [d for d in dateien if d.exists()] == []


def test_formular_loeschen_ueber_seine_unit(
    tmp_path: Path, ja: None, hauptfenster
) -> None:
    projekt = hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path))
    pfm = hauptfenster.formular_erzeugen("u_zweit")

    _aktion(hauptfenster, "Units/u_zweit.py", "Löschen …").trigger()

    assert not pfm.exists()
    assert not (projekt.ordner / "u_zweit.py").exists()
    assert not (projekt.ordner / "u_zweit_design.py").exists()


def test_das_hauptformular_laesst_sich_nicht_loeschen(
    tmp_path: Path, ja: None, hauptfenster
) -> None:
    projekt = hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path))

    hauptfenster._unit_loeschen(projekt.ordner / "u_main.pfm")
    hauptfenster._unit_loeschen(projekt.ordner / "u_main.py")

    for name in ("u_main.pfm", "u_main.py", "u_main_design.py"):
        assert (projekt.ordner / name).exists()


def test_formular_umbenennen_nimmt_alle_drei_dateien_und_die_importe_mit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster_bauen
) -> None:
    from pcl import Button

    fenster = hauptfenster_bauen()
    projekt = fenster.projekt_oeffnen(_projekt_kopie(tmp_path))
    ordner = projekt.ordner
    pfm = fenster.formular_erzeugen("u_zweit")
    alter_canvas = fenster._aktueller_canvas
    unit_editor = fenster.datei_oeffnen(pfm.with_suffix(".py"))
    haupt = ordner / "u_main.py"
    haupt.write_text(
        "from u_zweit import Form2\n" + haupt.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    _name_eingeben(monkeypatch, "u_dritt")

    _aktion(fenster, "Formulare/u_zweit", "Umbenennen …").trigger()

    for name in ("u_zweit.pfm", "u_zweit.py", "u_zweit_design.py"):
        assert not (ordner / name).exists(), name
    unit = (ordner / "u_dritt.py").read_text(encoding="utf-8")
    assert "from u_dritt_design import Form2Design" in unit
    assert "#     from u_dritt import Form2" in unit
    assert "u_zweit" not in unit.split("from u_dritt_design")[1]
    design = (ordner / "u_dritt_design.py").read_text(encoding="utf-8")
    assert "u_dritt.pfm" in design and "u_zweit" not in design
    assert (ordner / "u_dritt.pfm").exists()
    assert "from u_dritt import Form2" in haupt.read_text(encoding="utf-8")

    # Der offene Reiter der Unit zeigt auf die neue Datei, der
    # Designer ist unter dem neuen Namen wieder offen.
    assert unit_editor.toPlainText() == unit
    titel = [
        fenster.editor_tabs.tabText(i)
        for i in range(fenster.editor_tabs.count())
    ]
    assert "u_dritt.py" in titel
    assert "u_dritt (Designer)" in titel
    assert not any("u_zweit" in t for t in titel)
    assert set(_eintraege(fenster)) >= {
        "Formulare/u_dritt", "Units/u_dritt.py"
    }
    # Der alte Designer legt nichts wieder an, der neue schreibt in
    # die neuen Dateien.
    alter_canvas.komponente_platzieren(Button, 10, 10)
    alter_canvas.jetzt_schreiben()
    assert not (ordner / "u_zweit.pfm").exists()
    fenster._aktueller_canvas.komponente_platzieren(Button, 20, 20)
    fenster._aktueller_canvas.jetzt_schreiben()
    assert "Button" in (ordner / "u_dritt_design.py").read_text(
        encoding="utf-8"
    )
    assert not (ordner / "u_zweit_design.py").exists()

    umgebung = dict(
        os.environ, PYTHONPATH=str(WURZEL), QT_QPA_PLATFORM="offscreen"
    )
    lauf = subprocess.run(
        [sys.executable, "-c", "import u_main, u_dritt"],
        cwd=ordner, env=umgebung, capture_output=True, text=True,
        timeout=60,
    )
    assert lauf.returncode == 0, lauf.stderr


@pytest.mark.parametrize(
    "name", ["zweit", "u_konto", "U_MAIN", "u_x_design", "u zwei", "u_konto.py"]
)
def test_formular_umbenennen_prueft_den_namen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, hauptfenster
) -> None:
    projekt = hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path))
    pfm = hauptfenster.formular_erzeugen("u_zweit")
    meldungen = _name_eingeben(monkeypatch, name)

    hauptfenster._unit_umbenennen(pfm.with_suffix(".py"))

    assert len(meldungen) == 1
    for datei in ("u_zweit.pfm", "u_zweit.py", "u_zweit_design.py"):
        assert (projekt.ordner / datei).exists()
    assert (projekt.ordner / "u_konto.py").read_text(
        encoding="utf-8"
    ) == (
        WURZEL / "beispielprojekte" / "06_Kontoverwaltung" / "u_konto.py"
    ).read_text(encoding="utf-8")


def test_diagramm_loeschen_schliesst_sein_fenster(
    tmp_path: Path, ja: None, hauptfenster
) -> None:
    projekt = hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path))
    pfad = projekt.diagramm_ordner / "konto_klassen.pdiag"
    diagrammfenster = hauptfenster.diagramm_oeffnen(pfad)
    diagrammfenster._geaendert = True

    _aktion(hauptfenster, "Diagramme/konto_klassen", "Löschen …").trigger()

    assert not pfad.exists()
    assert not diagrammfenster.isVisible()
    assert str(pfad) not in hauptfenster._offene_diagramme
    assert "Diagramme/konto_klassen" not in _eintraege(hauptfenster)


def test_diagramm_umbenennen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    projekt = hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path))
    pfad = projekt.diagramm_ordner / "konto_klassen.pdiag"
    hauptfenster.diagramm_oeffnen(pfad)
    _name_eingeben(monkeypatch, "klassen")

    _aktion(hauptfenster, "Diagramme/konto_klassen", "Umbenennen …").trigger()

    ziel = projekt.diagramm_ordner / "klassen.pdiag"
    assert ziel.exists() and not pfad.exists()
    assert "Diagramme/klassen" in _eintraege(hauptfenster)
    offen = [Path(p).name for p in hauptfenster._offene_diagramme]
    assert offen == ["klassen.pdiag"]


@pytest.mark.parametrize("name", ["konto_abheben", "a/b", "con", "x."])
def test_diagramm_umbenennen_prueft_den_namen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, hauptfenster
) -> None:
    projekt = hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path))
    pfad = projekt.diagramm_ordner / "konto_klassen.pdiag"
    meldungen = _name_eingeben(monkeypatch, name)

    hauptfenster._unit_umbenennen(pfad)

    assert len(meldungen) == 1
    assert pfad.exists()


def test_die_frage_vor_dem_loeschen_nennt_importe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    """Punkt 514: ein Formular, das `u_main.py` noch importiert, ließ
    sich ohne Hinweis löschen, und das Programm startete danach nicht
    mehr. Ein auskommentierter Import zählt nicht. Punkt 513: vor zwei
    weiteren Dateien steht „gehören“."""
    projekt = hauptfenster.projekt_oeffnen(_projekt_kopie(tmp_path))
    hauptfenster.formular_erzeugen("u_zweit")
    haupt = projekt.ordner / f"{projekt.haupt_unit}.py"
    haupt.write_text(
        "from u_zweit import Form2\n" + haupt.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    fragen: list[str] = []
    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.question",
        staticmethod(
            lambda _e, _t, text, *a: fragen.append(text)
            or QMessageBox.StandardButton.No
        ),
    )

    _aktion(hauptfenster, "Formulare/u_zweit", "Löschen …").trigger()

    assert "Dazu gehören „u_zweit.pfm“ und „u_zweit_design.py“." in fragen[0]
    assert f"„{haupt.name}“ importiert „u_zweit“ noch" in fragen[0]
    assert (projekt.ordner / "u_zweit.py").exists()
