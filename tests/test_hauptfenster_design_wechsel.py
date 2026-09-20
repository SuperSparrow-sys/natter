"""Tests für „Ansicht → Design → Hell/Dunkel/System“ (Rückmeldung: „Hast du bei
Ansicht den Darkmode schon
implementiert?“). Bislang gab es nur ein einziges, fest auf „system“
gesetztes IDE-Theme ohne jede Umschaltmöglichkeit.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings

from ide.shell.hauptfenster import HauptFenster


def test_ansicht_menu_hat_ein_design_untermenue_mit_drei_optionen() -> None:
    fenster = HauptFenster()
    design_menue = None
    for aktion in fenster.menue("Ansicht").actions():
        if aktion.menu() is not None and aktion.text() == "Design":
            design_menue = aktion.menu()
    assert design_menue is not None

    beschriftungen = [a.text() for a in design_menue.actions()]
    assert beschriftungen == ["System (automatisch)", "Hell", "Dunkel"]
    for aktion in design_menue.actions():
        assert aktion.isCheckable()


def test_system_ist_die_voreinstellung_und_angekreuzt() -> None:
    fenster = HauptFenster()
    design_menue = next(
        a.menu() for a in fenster.menue("Ansicht").actions() if a.text() == "Design"
    )
    angekreuzt = [a.text() for a in design_menue.actions() if a.isChecked()]
    assert angekreuzt == ["System (automatisch)"]


def test_design_wechseln_wendet_das_stylesheet_sofort_an() -> None:
    fenster = HauptFenster()
    hell_stylesheet = fenster.styleSheet()

    fenster._design_wechseln("dark")

    assert fenster.styleSheet() != hell_stylesheet
    assert fenster._design_thema == "dark"


def test_design_wechsel_wird_fuer_den_naechsten_start_gemerkt() -> None:
    fenster = HauptFenster()
    fenster._design_wechseln("dark")

    einstellungen = QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Natter", "Natter-IDE"
    )
    assert einstellungen.value("design/thema") == "dark"

    neues_fenster = HauptFenster()
    assert neues_fenster._design_thema == "dark"


def test_design_menue_aktion_ruft_design_wechseln_auf() -> None:
    fenster = HauptFenster()
    design_menue = next(
        a.menu() for a in fenster.menue("Ansicht").actions() if a.text() == "Design"
    )
    dunkel_aktion = next(a for a in design_menue.actions() if a.text() == "Dunkel")

    dunkel_aktion.trigger()

    assert fenster._design_thema == "dark"
    assert dunkel_aktion.isChecked()


def test_design_wechsel_faerbt_bereits_offene_editoren_um(tmp_path: Path) -> None:
    fenster = HauptFenster()
    pfad = tmp_path / "u_main.py"
    pfad.write_text("def f():\n    pass\n", encoding="utf-8")
    editor = fenster.datei_oeffnen(pfad)
    assert editor._hervorhebung._thema == "light"  # noqa: SLF001

    fenster._design_wechseln("dark")

    assert editor._hervorhebung._thema == "dark"  # noqa: SLF001


def test_neu_geoeffneter_editor_uebernimmt_das_aktuelle_thema(tmp_path: Path) -> None:
    fenster = HauptFenster()
    fenster._design_wechseln("dark")

    pfad = tmp_path / "u_main.py"
    pfad.write_text("x = 1\n", encoding="utf-8")
    editor = fenster.datei_oeffnen(pfad)

    assert editor._hervorhebung._thema == "dark"  # noqa: SLF001
