"""Tests für ide/shell/hauptfenster.py: projekt_oeffnen, datei_oeffnen,
Explorer-Doppelklick. Headless. Siehe Arbeitspaket M2,
Schritt 5/6.
"""

from pathlib import Path

from PySide6.QtGui import QTextCursor

_AMPEL_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "06_Kontoverwaltung"


def test_projekt_oeffnen_laedt_das_projekt(hauptfenster) -> None:
    projekt = hauptfenster.projekt_oeffnen(_AMPEL_ORDNER / "06_Kontoverwaltung.natter")
    assert hauptfenster.projekt is projekt
    assert projekt.name == "06_Kontoverwaltung"


def test_projekt_oeffnen_fuellt_den_explorer(hauptfenster) -> None:
    hauptfenster.projekt_oeffnen(_AMPEL_ORDNER)

    formulare = [
        hauptfenster.explorer.formulare_gruppe.child(i).text(0)
        for i in range(hauptfenster.explorer.formulare_gruppe.childCount())
    ]
    units = [
        hauptfenster.explorer.units_gruppe.child(i).text(0)
        for i in range(hauptfenster.explorer.units_gruppe.childCount())
    ]
    assert formulare == ["u_main"]
    # Seit M12 steht die Startdatei nicht mehr bei den Units: sie wird
    # erzeugt und nicht bearbeitet, wie die `.lpr` in Lazarus. Erreichbar
    # bleibt sie über „Projekt → Startdatei anzeigen“.
    #
    # `u_main.py` steht seither dabei: unter „Formulare"
    # liegt die Oberfläche, hier der Code - und genau der ist die Datei,
    # in die der Schüler schreibt.
    assert set(units) == {"u_main.py", "u_konto.py"}


def test_datei_oeffnen_zeigt_inhalt_in_neuem_tab(hauptfenster) -> None:
    pfad = _AMPEL_ORDNER / "u_konto.py"

    editor = hauptfenster.datei_oeffnen(pfad)

    assert hauptfenster.editor_tabs.count() == 1
    assert hauptfenster.editor_tabs.tabText(0) == "u_konto.py"
    assert "class Konto" in editor.toPlainText()


def test_datei_oeffnen_zweimal_aktiviert_nur_den_vorhandenen_tab(hauptfenster) -> None:
    pfad = _AMPEL_ORDNER / "u_konto.py"

    hauptfenster.datei_oeffnen(pfad)
    hauptfenster.datei_oeffnen(pfad)

    assert hauptfenster.editor_tabs.count() == 1


def test_explorer_doppelklick_oeffnet_die_datei(hauptfenster) -> None:
    hauptfenster.projekt_oeffnen(_AMPEL_ORDNER)

    eintrag = hauptfenster.explorer.units_gruppe.child(0)  # u_konto.py
    hauptfenster.explorer.itemActivated.emit(eintrag, 0)

    assert hauptfenster.editor_tabs.count() == 1
    assert hauptfenster.editor_tabs.tabText(0) == eintrag.text(0)


def test_aenderung_markiert_den_tab_und_speichern_entfernt_die_markierung(
    tmp_path: Path, hauptfenster_bauen
) -> None:
    pfad = tmp_path / "test.txt"
    pfad.write_text("ursprünglich", encoding="utf-8")

    fenster = hauptfenster_bauen()
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
