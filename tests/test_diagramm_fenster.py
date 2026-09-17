"""Tests für ide/diagramm/fenster.py: eigenes Diagramm-Fenster
(M9, Schritt 1). Headless.

Abschnitt 13.1 verlangt ausdrücklich ein eigenes Fenster mit eigenem
Taskleisten-Eintrag statt eines Docks/Tabs in der IDE - der Test dafür
prüft, dass das Fenster kein Elternfenster hat (nur elternlose
Top-Level-Fenster bekommen unter Windows einen eigenen Eintrag).
"""

from __future__ import annotations

from pathlib import Path

from ide.diagramm import Diagramm, DiagrammFenster, diagramm_erzeugen


def _fenster(tmp_path: Path, typ: str = "class") -> DiagrammFenster:
    return DiagrammFenster(diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", "Testdiagramm"))


def test_fenster_ist_ein_eigenstaendiges_top_level_fenster(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)

    assert fenster.parent() is None
    assert fenster.isWindow() is True


def test_titel_nennt_datei_und_editor(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)

    assert fenster.windowTitle() == "class.pdiag – Diagramm-Editor – Natter"


def test_alle_menues_aus_dem_konzept_sind_vorhanden(tmp_path: Path) -> None:
    """Abschnitt 13.2 listet sechs Menüs - sie werden vollständig
    angelegt, auch wenn die meisten Einträge erst später aktiv werden."""
    fenster = _fenster(tmp_path)

    for erwartet in ("Datei", "Bearbeiten", "Ansicht", "Anordnen", "Format", "Hilfe"):
        assert fenster.menue(erwartet).title() == erwartet


def test_noch_nicht_umgesetzte_eintraege_sind_ausgegraut(tmp_path: Path) -> None:
    """Ehrlicher Zwischenstand: was noch nicht geht, ist sichtbar
    deaktiviert statt so zu tun, als täte es etwas."""
    fenster = _fenster(tmp_path)

    assert fenster.aktionen["Datei/Speichern"].isEnabled() is True
    assert fenster.aktionen["Datei/Drucken …"].isEnabled() is False
    assert fenster.aktionen["Bearbeiten/Rückgängig"].isEnabled() is False
    assert fenster.aktionen["Format/Stilvorlage …"].isEnabled() is False


def test_statusleiste_zeigt_seitenformat_und_stil(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)

    meldung = fenster.statusBar().currentMessage()
    assert "A4 quer" in meldung
    assert "modern-light" in meldung


def test_struktogramm_fenster_zeigt_hochformat(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path, "struktogramm")

    assert "A4 hoch" in fenster.statusBar().currentMessage()


def test_speichern_schreibt_aenderungen_auf_die_platte(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)
    fenster.diagramm.daten["shapes"].append(
        {"id": "s1", "kind": "class", "x": 8, "y": 8, "w": 100, "h": 60}
    )

    fenster.speichern()

    assert Diagramm.laden(tmp_path / "class.pdiag").daten["shapes"][0]["id"] == "s1"


def test_speichern_unter_wechselt_pfad_und_titel(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)
    ziel = tmp_path / "kopie.pdiag"

    fenster.speichern_unter(ziel)

    assert ziel.exists()
    assert fenster.diagramm.pfad == ziel
    assert fenster.windowTitle().startswith("kopie.pdiag")
