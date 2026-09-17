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


def test_klassendiagramm_hat_eine_formen_palette(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path, "class")

    assert fenster.palette is not None
    assert fenster.palette_dock.windowTitle() == "Formen"


def test_struktogramm_hat_keine_formen_palette(tmp_path: Path) -> None:
    """Struktogramme arbeiten mit einem Blockbaum, nicht mit frei
    platzierten Formen (Abschnitt 13.5) – eine Formen-Palette wäre dort
    irreführend."""
    fenster = _fenster(tmp_path, "struktogramm")

    assert fenster.palette is None
    assert fenster.palette_dock is None


def test_palettenklick_macht_die_form_auf_der_flaeche_scharf(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path, "class")

    fenster.palette.form_gewaehlt.emit("interface")

    assert fenster.zeichenflaeche._platzierungs_kind == "interface"


def test_statusleiste_zaehlt_formen_und_zeigt_die_auswahl(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path, "class")

    fenster.zeichenflaeche.form_platzieren("class", 200, 200)
    assert "Klasse ausgewählt" in fenster.statusBar().currentMessage()

    fenster.zeichenflaeche.auswahl_aufheben()
    fenster._statusleiste_aktualisieren()
    assert "1 Formen" in fenster.statusBar().currentMessage()


def test_aenderung_markiert_den_titel_und_speichern_raeumt_ihn_wieder_ab(
    tmp_path: Path,
) -> None:
    fenster = _fenster(tmp_path, "class")

    fenster.zeichenflaeche.form_platzieren("class", 200, 200)
    assert fenster.windowTitle().startswith("*")

    fenster.speichern()
    assert not fenster.windowTitle().startswith("*")


def test_speichern_unter_wechselt_pfad_und_titel(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)
    ziel = tmp_path / "kopie.pdiag"

    fenster.speichern_unter(ziel)

    assert ziel.exists()
    assert fenster.diagramm.pfad == ziel
    assert fenster.windowTitle().startswith("kopie.pdiag")
