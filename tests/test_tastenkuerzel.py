"""Tests für die Tastenkürzel-Übersicht und die Hilfeansicht
(M11, Abschnitt 4).

Die Kürzel gab es alle schon – sie standen nur nirgends zusammen. Zwei
Dinge werden hier am genauesten geprüft: dass die Übersicht aus dem
Register erzeugt wird (eine von Hand gepflegte Liste ist nach der
dritten neuen Aktion falsch) und dass die aufgeschriebenen Editortasten
im Editor wirklich etwas tun – eine Übersicht, die etwas Falsches
verspricht, schickt jemanden auf die Suche nach einem Fehler, den es
nicht gibt.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QKeyEvent

from ide.actions import Aktion, Aktionsregister
from ide.shell.hauptfenster import HauptFenster
from ide.shell.quelltexteditor import QuelltextEditor
from ide.shell.tastenkuerzel import EDITORTASTEN, als_markdown, uebersicht
from ide.viewers import HilfeAnsicht


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import pcl.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


def _register(*aktionen: Aktion) -> Aktionsregister:
    register = Aktionsregister()
    for aktion in aktionen:
        register.registrieren(aktion)
    return register


# -- Die Gruppierung -----------------------------------------------------


def test_aktionen_ohne_kuerzel_bleiben_draussen() -> None:
    """Die Übersicht soll die Tasten zeigen, nicht die Menüs noch
    einmal abschreiben."""
    register = _register(
        Aktion("a", "Mit Kürzel", menue="Datei", tastenkuerzel="Ctrl+S"),
        Aktion("b", "Ohne Kürzel", menue="Datei"),
    )

    gruppen = uebersicht(register)

    assert [e[1] for e in gruppen[0].eintraege] == ["Mit Kürzel"]


def test_die_menues_stehen_in_der_reihenfolge_der_menueleiste() -> None:
    """Man sucht das Gesuchte dort, wo man es kennt."""
    register = _register(
        Aktion("a", "Eins", menue="Start", tastenkuerzel="F9"),
        Aktion("b", "Zwei", menue="Datei", tastenkuerzel="Ctrl+S"),
        Aktion("c", "Drei", menue="Ansicht", tastenkuerzel="Ctrl+1"),
    )

    assert [g.titel for g in uebersicht(register)] == ["Datei", "Ansicht", "Start"]


def test_ein_unbekanntes_menue_kommt_hinten_dran() -> None:
    register = _register(
        Aktion("a", "Eins", menue="Datei", tastenkuerzel="Ctrl+S"),
        Aktion("b", "Zwei", menue="Sonstiges", tastenkuerzel="F7"),
    )

    assert [g.titel for g in uebersicht(register)] == ["Datei", "Sonstiges"]


def test_innerhalb_eines_menues_wird_nach_namen_sortiert() -> None:
    register = _register(
        Aktion("a", "Zuletzt", menue="Datei", tastenkuerzel="F8"),
        Aktion("b", "Anfang", menue="Datei", tastenkuerzel="F7"),
    )

    assert [e[1] for e in uebersicht(register)[0].eintraege] == ["Anfang", "Zuletzt"]


# -- Die Hilfeseite ------------------------------------------------------


def test_die_seite_nennt_kuerzel_und_namen() -> None:
    register = _register(
        Aktion("a", "Speichern", menue="Datei", tastenkuerzel="Ctrl+S")
    )

    text = als_markdown(register)

    assert "Strg+S" in text
    assert "Speichern" in text
    assert "## Datei" in text


def test_die_kuerzel_stehen_auf_deutsch_da() -> None:
    """Eine Schülerin sucht auf ihrer Tastatur nach einer Taste namens
    „Ctrl“. Qt schreibt die Namen selbst, sobald seine deutsche
    Übersetzung geladen ist (`ide/deutsch.py`)."""
    from ide.shell.tastenkuerzel import deutsche_taste

    assert deutsche_taste("Ctrl+S") == "Strg+S"
    assert deutsche_taste("Ctrl+Shift+E") == "Strg+Umschalt+E"
    assert deutsche_taste("Del") == "Entf"
    assert deutsche_taste("F5") == "F5"


def test_qts_eigene_texte_sind_deutsch(qtbot) -> None:
    """Nicht nur die Kürzel: auch „Cancel“ in jedem Standarddialog und
    „Undo“ im Kontextmenü jedes Textfelds kamen von Qt und standen auf
    Englisch da."""
    from PySide6.QtWidgets import QDialogButtonBox

    kaesten = QDialogButtonBox(
        QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
    )
    qtbot.addWidget(kaesten)

    assert "Abbrechen" in [knopf.text() for knopf in kaesten.buttons()]


def test_die_uebersetzung_wird_nur_einmal_geladen() -> None:
    """Ein `QTranslator`, der nur in einer lokalen Variablen steht,
    wird wieder eingesammelt – die Oberfläche fiele dann ohne
    Fehlermeldung ins Englische zurück."""
    from ide.deutsch import _UEBERSETZER, deutsch_einschalten

    vorher = len(_UEBERSETZER)

    assert deutsch_einschalten() == vorher
    assert vorher >= 1


def test_die_editortasten_stehen_mit_drauf() -> None:
    """Gerade die Kürzel im Editor stehen in gar keinem Menü – wer sie
    nicht kennt, findet sie sonst nie."""
    text = als_markdown(_register())

    assert "Nur im Quelltexteditor" in text
    for taste, _ in EDITORTASTEN:
        assert taste in text


def test_die_seite_kommt_ohne_aktionen_aus() -> None:
    text = als_markdown(_register())

    assert text.startswith("# Tastenkürzel")


# -- Die aufgeschriebenen Editortasten stimmen ---------------------------


def test_strg_d_dupliziert_wirklich(qtbot) -> None:
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.setPlainText("a = 1\n")

    editor.zeile_duplizieren()

    assert editor.toPlainText() == "a = 1\na = 1\n"


def test_alt_pfeil_verschiebt_wirklich(qtbot) -> None:
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.setPlainText("eins\nzwei\n")

    assert editor.zeile_verschieben(nach_unten=True) is True
    assert editor.toPlainText().startswith("zwei\neins")


def test_f12_loest_die_suche_aus(qtbot) -> None:
    """Die Übersicht verspricht F12 – also muss die Taste auch beim
    Editor ankommen."""
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    gerufen = []
    editor.definition_gesucht.connect(lambda: gerufen.append(True))

    editor.keyPressEvent(
        QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_F12, Qt.KeyboardModifier.NoModifier)
    )

    assert gerufen == [True]


def test_tab_gibt_vier_leerzeichen(qtbot) -> None:
    editor = QuelltextEditor()
    qtbot.addWidget(editor)

    editor.keyPressEvent(
        QKeyEvent(
            QKeyEvent.Type.KeyPress, Qt.Key.Key_Tab, Qt.KeyboardModifier.NoModifier, "\t"
        )
    )

    assert editor.toPlainText() == "    "


def test_strg_mausrad_aendert_die_schriftgroesse(qtbot) -> None:
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    vorher = editor.font().pointSize()

    assert editor.schriftgroesse_aendern(1) == vorher + 1


def test_die_ruecktaste_loescht_eine_ganze_ebene(qtbot) -> None:
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.setPlainText("        ")
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor.setTextCursor(cursor)

    assert editor._einzugsebene_loeschen() is True
    assert editor.toPlainText() == "    "


# -- Im Hauptfenster -----------------------------------------------------


def test_das_hilfemenue_bietet_die_uebersicht(
    einstellungen: QSettings, qtbot
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    titel = [a.text() for a in fenster.menue("Hilfe").actions()]

    assert "Tastenkürzel-Übersicht" in titel
    assert "Erste Schritte" in titel


def test_die_uebersicht_oeffnet_einen_lesbaren_reiter(
    einstellungen: QSettings, qtbot
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    ansicht = fenster._tastenkuerzel_aktion()

    assert isinstance(ansicht, HilfeAnsicht)
    assert ansicht.isReadOnly() is True
    assert "Tastenkürzel" in ansicht.toPlainText()


def test_die_uebersicht_kennt_die_echten_kuerzel_der_ide(
    einstellungen: QSettings, qtbot
) -> None:
    """Erzeugt aus dem Register – nicht von Hand gepflegt."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    text = als_markdown(fenster.aktionen)

    for aktion in fenster.aktionen:
        if aktion.tastenkuerzel:
            assert aktion.name in text


def test_ein_zweiter_aufruf_holt_den_reiter_nach_vorn(
    einstellungen: QSettings, qtbot
) -> None:
    """Sonst sammelten sich nach dem dritten Nachschlagen drei gleiche
    Reiter an."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster._tastenkuerzel_aktion()
    vorher = fenster.editor_tabs.count()
    fenster._tastenkuerzel_aktion()

    assert fenster.editor_tabs.count() == vorher


def test_erste_schritte_oeffnet_keinen_quelltexteditor_mehr(
    einstellungen: QSettings, qtbot
) -> None:
    """Eine Anleitung mit `##` und `*` davor, in einem Fenster, das nach
    Programmieren aussieht und in dem man sie versehentlich ändern
    kann."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    assert fenster._erste_schritte_aktion() is True

    assert isinstance(fenster.editor_tabs.currentWidget(), HilfeAnsicht)


def test_eine_fehlende_hilfeseite_sagt_wo_sie_liegen_muesste(
    einstellungen: QSettings, qtbot
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    assert fenster._hilfedatei_zeigen("gibt_es_nicht.md", "Nichts") is False

    meldung = fenster.statusBar().currentMessage()
    assert "docs/gibt_es_nicht.md" in meldung
    assert "neue Installation" in meldung
