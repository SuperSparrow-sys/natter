"""Tests für das Falten von Klassen und Funktionen (M11, Abschnitt 2.3).

In einer Datei mit zehn Methoden ist das Blättern der häufigste Grund,
den Überblick zu verlieren. Gefaltet werden deshalb genau `class` und
`def` – eine zusammengeklappte `if`-Abfrage versteckte dagegen gerade
das, worauf es im Unterricht ankommt.
"""

from __future__ import annotations

import pytest

from ide.shell.quelltexteditor import QuelltextEditor

QUELLE = "\n".join(
    [
        "import os",
        "",
        "",
        "class Ampel:",
        "    def __init__(self):",
        "        self.farbe = 'rot'",
        "",
        "    def weiter(self):",
        "        self.farbe = 'gruen'",
        "",
        "",
        "def haupt():",
        "    ampel = Ampel()",
        "    ampel.weiter()",
        "",
    ]
)


@pytest.fixture
def editor(qtbot) -> QuelltextEditor:
    feld = QuelltextEditor()
    qtbot.addWidget(feld)
    feld.setPlainText(QUELLE)
    return feld


def _sichtbar(feld: QuelltextEditor) -> list[int]:
    """Die sichtbaren Zeilen (ab 1)."""
    dokument = feld.document()
    return [
        nummer + 1
        for nummer in range(dokument.blockCount())
        if dokument.findBlockByNumber(nummer).isVisible()
    ]


# -- Was sich falten lässt -----------------------------------------------


def test_klassen_und_funktionen_lassen_sich_falten(editor: QuelltextEditor) -> None:
    assert set(editor.faltbare_zeilen()) == {4, 5, 8, 12}


def test_zu_jedem_kopf_steht_die_letzte_zeile_des_rumpfes(
    editor: QuelltextEditor,
) -> None:
    faltbar = editor.faltbare_zeilen()

    assert faltbar[5] == 6  # __init__ endet mit seiner einen Zeile
    assert faltbar[4] == 9  # die Klasse reicht bis zur letzten Methode
    assert faltbar[12] == 14


def test_eine_if_abfrage_laesst_sich_nicht_falten(qtbot) -> None:
    """Sie versteckte gerade das, worauf es im Unterricht ankommt."""
    feld = QuelltextEditor()
    qtbot.addWidget(feld)
    feld.setPlainText("if a:\n    b()\n")

    assert feld.faltbare_zeilen() == {}


def test_ein_name_der_mit_def_beginnt_ist_kein_funktionskopf(qtbot) -> None:
    feld = QuelltextEditor()
    qtbot.addWidget(feld)
    feld.setPlainText("definiere = 1\nclasse = 2\n")

    assert feld.faltbare_zeilen() == {}


def test_eine_funktion_ohne_rumpf_zaehlt_nicht(qtbot) -> None:
    """Eine halb getippte Zeile soll kein Faltzeichen bekommen, das
    beim nächsten Anschlag wieder verschwindet."""
    feld = QuelltextEditor()
    qtbot.addWidget(feld)
    feld.setPlainText("def f():\n")

    assert feld.faltbare_zeilen() == {}


# -- Falten und Entfalten ------------------------------------------------


def test_eine_gefaltete_funktion_versteckt_ihren_rumpf(
    editor: QuelltextEditor,
) -> None:
    editor.falten(12)

    assert 12 in _sichtbar(editor)
    assert 13 not in _sichtbar(editor)
    assert 14 not in _sichtbar(editor)


def test_die_kopfzeile_bleibt_stehen(editor: QuelltextEditor) -> None:
    """Sonst wäre die Funktion spurlos verschwunden, und niemand käme
    auf die Idee, dass da noch etwas steht."""
    editor.falten(4)

    assert 4 in _sichtbar(editor)


def test_entfalten_zeigt_alles_wieder(editor: QuelltextEditor) -> None:
    editor.falten(4)

    editor.entfalten(4)

    assert _sichtbar(editor) == list(range(1, len(QUELLE.split("\n")) + 1))


def test_der_umschalter_wechselt_hin_und_her(editor: QuelltextEditor) -> None:
    assert editor.falt_umschalten(12) is True
    assert editor.falt_umschalten(12) is False
    assert 13 in _sichtbar(editor)


def test_eine_nicht_faltbare_zeile_tut_nichts(editor: QuelltextEditor) -> None:
    assert editor.falt_umschalten(1) is False
    assert _sichtbar(editor) == list(range(1, len(QUELLE.split("\n")) + 1))


def test_eine_klasse_nimmt_ihre_methoden_mit(editor: QuelltextEditor) -> None:
    editor.falten(4)

    assert [z for z in (5, 6, 7, 8, 9) if z in _sichtbar(editor)] == []
    assert 12 in _sichtbar(editor)


def test_innen_liegende_faltungen_bleiben_zu(editor: QuelltextEditor) -> None:
    """Wer eine Klasse aufklappt, will nicht gleich alle ihre Methoden
    offen haben."""
    editor.falten(8)
    editor.falten(4)

    editor.entfalten(4)

    assert 8 in _sichtbar(editor)
    assert 9 not in _sichtbar(editor)


def test_alles_entfalten_raeumt_auf(editor: QuelltextEditor) -> None:
    editor.falten(5)
    editor.falten(8)

    editor.alles_entfalten()

    assert _sichtbar(editor) == list(range(1, len(QUELLE.split("\n")) + 1))


# -- Nach einer Änderung -------------------------------------------------


def test_eine_geloeschte_kopfzeile_gibt_den_text_wieder_frei(
    editor: QuelltextEditor,
) -> None:
    """Sonst bliebe Text unsichtbar, den es gar nicht mehr zu falten
    gibt – und niemand käme darauf, dass da noch etwas steht."""
    editor.falten(12)

    editor.setPlainText("x = 1\ny = 2\nz = 3\n")

    assert _sichtbar(editor) == [1, 2, 3, 4]


def test_eine_faltung_ueberlebt_eine_aenderung_woanders(
    editor: QuelltextEditor,
) -> None:
    editor.falten(12)
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.Start)
    cursor.insertText("# Kommentar\n")

    # Die Kopfzeile ist jetzt Zeile 13 - die alte Faltung ist damit
    # hinfällig und wird aufgehoben, statt fremden Text zu verstecken.
    assert 14 in _sichtbar(editor)


# -- Anzeige im Rand -----------------------------------------------------


def test_der_rand_macht_platz_fuer_die_faltzeichen(editor: QuelltextEditor) -> None:
    from ide.shell.quelltexteditor import _FALT_SPALTE_BREITE

    schmaler = QuelltextEditor()
    schmaler.setPlainText("x = 1\n")

    assert editor.zeilennummernrand_breite() >= _FALT_SPALTE_BREITE + 10
    schmaler.deleteLater()


def _mitte_von(feld: QuelltextEditor, zeile: int) -> float:
    """Die senkrechte Mitte einer Zeile im Rand. Nicht über die
    Schrifthöhe gerechnet: Qt gibt einem Block etwas mehr Platz, und
    die Rechnung lag damit eine Zeile daneben."""
    block = feld.document().findBlockByNumber(zeile - 1)
    kasten = feld.blockBoundingGeometry(block).translated(feld.contentOffset())
    return kasten.top() + kasten.height() / 2


def test_ein_klick_rechts_im_rand_faltet(editor: QuelltextEditor) -> None:
    """Links der Haltepunkt, rechts das Falten - ein Klick auf die
    Zeilennummer darf keine Funktion zuklappen."""
    editor.resize(600, 420)
    editor.show()
    breite = editor.zeilennummernrand_breite()

    editor._rand_klick_verarbeiten(breite - 3, _mitte_von(editor, 12))

    assert editor._gefaltet == {12}


def test_ein_klick_links_im_rand_setzt_einen_haltepunkt(
    editor: QuelltextEditor,
) -> None:
    editor.resize(600, 420)
    editor.show()

    editor._rand_klick_verarbeiten(4.0, _mitte_von(editor, 12))

    assert editor.breakpoints == {12}
    assert editor._gefaltet == set()


# -- Zeilen verschieben und verdoppeln bei zugeklappten Funktionen ------


def _cursor_auf(feld: QuelltextEditor, zeile: int) -> None:
    cursor = feld.textCursor()
    cursor.setPosition(feld.document().findBlockByNumber(zeile - 1).position())
    feld.setTextCursor(cursor)


def test_alt_pfeil_bewegt_eine_zugeklappte_funktion_als_ganzes(
    editor: QuelltextEditor,
) -> None:
    """Vorher tauschte nur die Kopfzeile mit der ersten versteckten
    Zeile, und die Datei hatte einen Einrückungsfehler."""
    import ast

    editor.falten(5)
    _cursor_auf(editor, 5)

    assert editor.zeile_verschieben(True)
    ast.parse(editor.toPlainText())
    zeilen = editor.toPlainText().split("\n")
    assert zeilen[4:7] == ["", "    def __init__(self):", "        self.farbe = 'rot'"]
    assert editor._gefaltet == {6}
    assert 7 not in _sichtbar(editor)

    assert editor.zeile_verschieben(False)
    assert editor.toPlainText() == QUELLE
    assert editor._gefaltet == {5}


def test_eine_zeile_springt_ueber_eine_zugeklappte_funktion(
    editor: QuelltextEditor,
) -> None:
    editor.falten(12)
    _cursor_auf(editor, 11)

    assert editor.zeile_verschieben(True)

    zeilen = editor.toPlainText().split("\n")
    assert zeilen[10:14] == ["def haupt():", "    ampel = Ampel()", "    ampel.weiter()", ""]
    assert editor._gefaltet == {11}
    assert [12, 13] == [z for z in (12, 13) if z not in _sichtbar(editor)]


def test_verschieben_woanders_laesst_faltungen_zu(editor: QuelltextEditor) -> None:
    """Der Rumpf wurde wieder sichtbar, `_gefaltet` meldete ihn aber
    weiter als zugeklappt."""
    editor.falten(12)
    _cursor_auf(editor, 1)

    editor.zeile_verschieben(True)

    assert editor._gefaltet == {12}
    assert 13 not in _sichtbar(editor)


def test_strg_d_verdoppelt_eine_zugeklappte_funktion_ganz(
    editor: QuelltextEditor,
) -> None:
    import ast

    editor.falten(12)
    _cursor_auf(editor, 12)

    editor.zeile_duplizieren()

    ast.parse(editor.toPlainText())
    assert editor.toPlainText().count("def haupt():") == 2
    assert editor.toPlainText().count("    ampel.weiter()") == 2
    assert editor._gefaltet == {12, 15}


def test_haltepunkt_wandert_mit_seiner_zeile(qtbot) -> None:  # noqa: ANN001
    """Der Haltepunkt blieb an seiner Zeilennummer und stand danach
    auf einer anderen Anweisung."""
    feld = QuelltextEditor()
    qtbot.addWidget(feld)
    feld.setPlainText("a = 1\nb = 2\nc = 3\n")
    feld.breakpoints = {1}
    feld.bedingungen = {1: "a > 0"}
    _cursor_auf(feld, 1)

    feld.zeile_verschieben(True)
    assert feld.breakpoints == {2}
    assert feld.bedingungen == {2: "a > 0"}

    feld.zeile_verschieben(False)
    assert feld.breakpoints == {1}
    assert feld.bedingungen == {1: "a > 0"}

