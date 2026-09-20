"""Tests für „Ansicht → Schriftart“ (Gewünscht: „soll bei Ansicht eine Auswahl
der Schriftarten zum Auswählen“).
Gleiches Muster wie tests/test_hauptfenster_design_wechsel.py.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtGui import QFontInfo

from ide.shell.hauptfenster import HauptFenster


def test_ansicht_menu_hat_ein_schriftart_untermenue_mit_drei_optionen() -> None:
    fenster = HauptFenster()
    schriftart_menue = next(
        a.menu() for a in fenster.menue("Ansicht").actions() if a.text() == "Schriftart"
    )
    beschriftungen = [a.text() for a in schriftart_menue.actions()]
    assert beschriftungen == ["Consolas", "Cascadia Code", "Courier New"]
    for aktion in schriftart_menue.actions():
        assert aktion.isCheckable()


def test_consolas_ist_die_voreinstellung_und_angekreuzt() -> None:
    fenster = HauptFenster()
    schriftart_menue = next(
        a.menu() for a in fenster.menue("Ansicht").actions() if a.text() == "Schriftart"
    )
    angekreuzt = [a.text() for a in schriftart_menue.actions() if a.isChecked()]
    assert angekreuzt == ["Consolas"]


def test_schriftart_wechsel_wird_fuer_den_naechsten_start_gemerkt() -> None:
    fenster = HauptFenster()
    fenster._code_schriftart_wechseln("Cascadia Code")

    einstellungen = QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Natter", "Natter-IDE"
    )
    assert einstellungen.value("editor/schriftart") == "Cascadia Code"

    neues_fenster = HauptFenster()
    assert neues_fenster._code_schriftart == "Cascadia Code"


def test_schriftart_menue_aktion_ruft_wechseln_auf() -> None:
    fenster = HauptFenster()
    schriftart_menue = next(
        a.menu() for a in fenster.menue("Ansicht").actions() if a.text() == "Schriftart"
    )
    cascadia_aktion = next(a for a in schriftart_menue.actions() if a.text() == "Cascadia Code")

    cascadia_aktion.trigger()

    assert fenster._code_schriftart == "Cascadia Code"
    assert cascadia_aktion.isChecked()


def test_schriftart_wechsel_wirkt_auf_bereits_offene_editoren(tmp_path: Path) -> None:
    fenster = HauptFenster()
    pfad = tmp_path / "u_main.py"
    pfad.write_text("x = 1\n", encoding="utf-8")
    editor = fenster.datei_oeffnen(pfad)
    assert editor.font().family() == "Consolas"

    fenster._code_schriftart_wechseln("Cascadia Code")

    assert editor.font().family() == "Cascadia Code"


def test_neu_geoeffneter_editor_uebernimmt_die_aktuelle_schriftart(tmp_path: Path) -> None:
    fenster = HauptFenster()
    fenster._code_schriftart_wechseln("Cascadia Code")

    pfad = tmp_path / "u_main.py"
    pfad.write_text("x = 1\n", encoding="utf-8")
    editor = fenster.datei_oeffnen(pfad)

    assert editor.font().family() == "Cascadia Code"


def test_design_wechsel_behaelt_die_gewaehlte_schriftart(tmp_path: Path) -> None:
    """Real beim Bauen der Funktion gefunden: `_design_wechseln` rief
    `ide_qss_erzeugen()` ohne `code_schriftart` auf - ein Themawechsel
    hätte die gewählte Editor-Schrift stillschweigend auf den Standard
    zurückgesetzt."""
    fenster = HauptFenster()
    fenster._code_schriftart_wechseln("Cascadia Code")
    pfad = tmp_path / "u_main.py"
    pfad.write_text("x = 1\n", encoding="utf-8")
    editor = fenster.datei_oeffnen(pfad)

    fenster._design_wechseln("dark")

    assert editor.font().family() == "Cascadia Code"
    assert fenster._code_schriftart == "Cascadia Code"


def test_courier_new_ist_ueber_qfontinfo_tatsaechlich_aufloesbar(tmp_path: Path) -> None:
    fenster = HauptFenster()
    fenster._code_schriftart_wechseln("Courier New")
    pfad = tmp_path / "u_main.py"
    pfad.write_text("x = 1\n", encoding="utf-8")
    editor = fenster.datei_oeffnen(pfad)

    assert QFontInfo(editor.font()).family() == "Courier New"
