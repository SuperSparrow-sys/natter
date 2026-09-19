"""Tests für ide/shell/hauptfenster.py: projekt_oeffnen, datei_oeffnen,
Explorer-Doppelklick. Headless. Siehe docs/arbeitspakete/M2.md,
Schritt 5/6.
"""

from pathlib import Path

from PySide6.QtGui import QTextCursor

from ide.shell.hauptfenster import HauptFenster

_AMPEL_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "Ampel"


def test_projekt_oeffnen_laedt_das_projekt() -> None:
    fenster = HauptFenster()
    projekt = fenster.projekt_oeffnen(_AMPEL_ORDNER / "ampel.natter")
    assert fenster.projekt is projekt
    assert projekt.name == "Ampel"


def test_projekt_oeffnen_fuellt_den_explorer() -> None:
    fenster = HauptFenster()
    fenster.projekt_oeffnen(_AMPEL_ORDNER)

    formulare = [
        fenster.explorer.formulare_gruppe.child(i).text(0)
        for i in range(fenster.explorer.formulare_gruppe.childCount())
    ]
    units = [
        fenster.explorer.units_gruppe.child(i).text(0)
        for i in range(fenster.explorer.units_gruppe.childCount())
    ]
    assert formulare == ["u_main"]
    # Seit M12 steht die Startdatei nicht mehr bei den Units: sie wird
    # erzeugt und nicht bearbeitet, wie die `.lpr` in Lazarus. Erreichbar
    # bleibt sie über „Projekt → Startdatei anzeigen“.
    assert set(units) == {"u_ampel.py"}


def test_datei_oeffnen_zeigt_inhalt_in_neuem_tab() -> None:
    fenster = HauptFenster()
    pfad = _AMPEL_ORDNER / "u_ampel.py"

    editor = fenster.datei_oeffnen(pfad)

    assert fenster.editor_tabs.count() == 1
    assert fenster.editor_tabs.tabText(0) == "u_ampel.py"
    assert "class Ampel" in editor.toPlainText()


def test_datei_oeffnen_zweimal_aktiviert_nur_den_vorhandenen_tab() -> None:
    fenster = HauptFenster()
    pfad = _AMPEL_ORDNER / "u_ampel.py"

    fenster.datei_oeffnen(pfad)
    fenster.datei_oeffnen(pfad)

    assert fenster.editor_tabs.count() == 1


def test_explorer_doppelklick_oeffnet_die_datei() -> None:
    fenster = HauptFenster()
    fenster.projekt_oeffnen(_AMPEL_ORDNER)

    eintrag = fenster.explorer.units_gruppe.child(0)  # u_ampel.py
    fenster.explorer.itemActivated.emit(eintrag, 0)

    assert fenster.editor_tabs.count() == 1
    assert fenster.editor_tabs.tabText(0) == eintrag.text(0)


def test_aenderung_markiert_den_tab_und_speichern_entfernt_die_markierung(tmp_path: Path) -> None:
    pfad = tmp_path / "test.txt"
    pfad.write_text("ursprünglich", encoding="utf-8")

    fenster = HauptFenster()
    editor = fenster.datei_oeffnen(pfad)
    assert fenster.editor_tabs.tabText(0) == "test.txt"

    # setPlainText() lädt nur und markiert nicht als geändert (Qt-Verhalten);
    # eine echte Bearbeitung simulieren wir über insertPlainText() am Ende.
    editor.moveCursor(QTextCursor.MoveOperation.End)
    editor.insertPlainText(" geändert")
    assert fenster.editor_tabs.tabText(0) == "test.txt ●"

    fenster._aktuelle_datei_speichern()

    assert fenster.editor_tabs.tabText(0) == "test.txt"
    assert pfad.read_text(encoding="utf-8") == "ursprünglich geändert"
