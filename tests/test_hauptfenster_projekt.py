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


def _maus(widget, art, pos) -> None:
    """Ein Ereignis der linken Maustaste, wie es Windows zustellt."""
    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication

    gedrueckt = (
        Qt.MouseButton.NoButton if art == QEvent.Type.MouseButtonRelease
        else Qt.MouseButton.LeftButton
    )
    QApplication.sendEvent(widget, QMouseEvent(
        art, QPointF(pos), QPointF(widget.mapToGlobal(pos)),
        Qt.MouseButton.LeftButton, gedrueckt,
        Qt.KeyboardModifier.NoModifier,
    ))


def test_doppelklick_mit_der_maus_oeffnet_die_unit(
    hauptfenster, qtbot, tmp_path: Path
) -> None:
    """Punkt 410: an der installierten 0.4.0 öffnete ein Doppelklick
    per UI Automation eine Unit fast nie. Das lag an der
    Automatisierung: pywinauto schickt beide Klicks mit demselben
    Zeitstempel, und daraus macht Qt keinen Doppelklick, auch in
    einem gewöhnlichen `QTreeWidget` nicht. Mit 20 ms zwischen
    Drücken und Loslassen öffnete die installierte Fassung jede Unit.

    Hier kommen die Ereignisse in der Folge, in der Windows sie
    schickt: Drücken, Loslassen, Doppelklick, Loslassen. Zwischen den
    beiden Klicks schlagen die Uhren, die im Hintergrund laufen, und
    das Fenster wird aktiv. Baute dabei etwas den Baum neu auf,
    verlöre der Doppelklick seinen Eintrag.

    `QTest.mouseDClick` allein taugt dafür nicht: es schickt nur das
    Doppelklick-Ereignis ohne das Drücken davor, und Qt übergeht
    einen Doppelklick auf einen Eintrag, der vorher nicht gedrückt
    wurde.

    Danach liegt der Fokus im Editor, nicht mehr im Explorer
    (Punkt 472): wer nach dem Doppelklick lostippt, schreibt in die
    Unit."""
    import shutil

    from PySide6.QtCore import QEvent

    ordner = tmp_path / "06_Kontoverwaltung"
    shutil.copytree(_AMPEL_ORDNER, ordner)
    hauptfenster.show()
    qtbot.waitExposed(hauptfenster)
    hauptfenster.projekt_oeffnen(ordner)
    baum = hauptfenster.explorer
    flaeche = baum.viewport()
    tabs = hauptfenster.editor_tabs

    for i in range(baum.units_gruppe.childCount()):
        eintrag = baum.units_gruppe.child(i)
        rechteck = baum.visualItemRect(eintrag)
        pos = rechteck.center()
        pos.setX(rechteck.left() + 20)
        baum.setFocus()
        _maus(flaeche, QEvent.Type.MouseButtonPress, pos)
        _maus(flaeche, QEvent.Type.MouseButtonRelease, pos)
        hauptfenster._sperre_uhr.timeout.emit()
        hauptfenster._sicherung_uhr.timeout.emit()
        hauptfenster.changeEvent(QEvent(QEvent.Type.ActivationChange))
        _maus(flaeche, QEvent.Type.MouseButtonDblClick, pos)
        _maus(flaeche, QEvent.Type.MouseButtonRelease, pos)

        assert tabs.count() == i + 1
        assert tabs.tabText(tabs.currentIndex()) == eintrag.text(0)
        # Das Widget, das den Fokus hat, sobald das Fenster aktiv ist;
        # offscreen wird kein Fenster aktiv.
        assert hauptfenster.focusWidget() is tabs.currentWidget()


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


def test_eine_hineinkopierte_klasse_und_ein_diagramm_erscheinen(
    hauptfenster, tmp_path: Path
) -> None:
    """Punkte 503 und 504: eine Klasse, die die Lehrkraft verteilt und
    die im Windows-Explorer in den offenen Projektordner kopiert wird,
    erschien erst nach erneutem Öffnen; ein Diagramm neben `u_main.py`
    erschien nie. Ohne Änderung wird der Baum nicht neu gebaut."""
    import shutil

    ordner = tmp_path / "06_Kontoverwaltung"
    shutil.copytree(_AMPEL_ORDNER, ordner)
    hauptfenster.projekt_oeffnen(ordner)
    assert hauptfenster.explorer.auffrischen(hauptfenster.projekt) is False

    (ordner / "konto_lehrkraft.py").write_text("class K:\n    pass\n", encoding="utf-8")
    (ordner / "aufgabe.pdiag").write_text(
        '{"format": "pdiag/1", "type": "class", "name": "aufgabe", '
        '"page": {"size": "A4", "orientation": "landscape"}, '
        '"style": "modern-light", "shapes": [], "connectors": []}',
        encoding="utf-8",
    )
    assert hauptfenster.explorer.auffrischen(hauptfenster.projekt) is True

    units = [
        hauptfenster.explorer.units_gruppe.child(i).text(0)
        for i in range(hauptfenster.explorer.units_gruppe.childCount())
    ]
    diagramme = [
        hauptfenster.explorer.diagramme_gruppe.child(i).text(0)
        for i in range(hauptfenster.explorer.diagramme_gruppe.childCount())
    ]
    assert "konto_lehrkraft.py" in units
    assert "aufgabe" in diagramme
