"""Variablen aufklappen und globale Variablen (Punkt 99), überwachte
Ausdrücke, bedingte Haltepunkte und Werte unter der Maus (Punkt 100).
Gegen echtes debugpy."""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QPoint

from ide.shell.hauptfenster import HauptFenster
from tests.conftest import DEBUG_ZEITGRENZE

PROGRAMM = (
    "zahlen = [3, 1, 4]\n"
    "\n"
    "def summe(liste):\n"
    "    ergebnis = 0\n"
    "    for i in range(len(liste)):\n"
    "        ergebnis += liste[i]\n"
    "    return ergebnis\n"
    "\n"
    "print(summe(zahlen))\n"
)


def _projekt(fenster: HauptFenster, ordner: Path) -> Path:
    (ordner / "main.py").write_text(PROGRAMM, encoding="utf-8")
    natter = ordner / "t.natter"
    natter.write_text(json.dumps({
        "format": "natter-project/1", "name": "T", "type": "console", "main": "main.py",
    }), encoding="utf-8")
    fenster.projekt_oeffnen(natter)
    return ordner / "main.py"


def _eintrag(baum, name: str):  # noqa: ANN001, ANN202
    for i in range(baum.topLevelItemCount()):
        if baum.topLevelItem(i).text(0) == name:
            return baum.topLevelItem(i)
    return None


def test_liste_aufklappen_globale_und_bedingter_haltepunkt(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    main = _projekt(fenster, tmp_path)
    editor = fenster.datei_oeffnen(main)
    editor.bedingung_setzen(6, "i == 2")
    fenster.ausdruck_ueberwachen("ergebnis * 10")

    fenster._projekt_mit_debugger_starten_aktion()
    try:
        qtbot.waitUntil(
            lambda: _eintrag(fenster.variablen_baum, "i") is not None, timeout=DEBUG_ZEITGRENZE
        )
        # Bedingung: gehalten erst bei i == 2
        assert _eintrag(fenster.variablen_baum, "i").text(1) == "2"
        assert _eintrag(fenster.variablen_baum, "ergebnis").text(1) == "4"

        # Überwachter Ausdruck
        qtbot.waitUntil(
            lambda: fenster.ueberwachen_baum.topLevelItem(0).text(1) == "40",
            timeout=DEBUG_ZEITGRENZE,
        )

        # Globale Variablen als eigener Zweig, die Liste darin aufklappbar
        qtbot.waitUntil(
            lambda: _eintrag(fenster.variablen_baum, "Globale Variablen") is not None,
            timeout=DEBUG_ZEITGRENZE,
        )
        globale = _eintrag(fenster.variablen_baum, "Globale Variablen")
        zahlen = next(
            globale.child(i) for i in range(globale.childCount())
            if globale.child(i).text(0) == "zahlen"
        )
        zahlen.setExpanded(True)
        qtbot.waitUntil(lambda: zahlen.childCount() >= 3, timeout=DEBUG_ZEITGRENZE)
        werte = [zahlen.child(i).text(1) for i in range(zahlen.childCount())]
        assert werte[:3] == ["3", "1", "4"]

        # Wert unter der Maus
        assert editor.debugger_haelt
        editor.wert_gefragt.emit("ergebnis", QPoint(0, 0))
        qtbot.waitUntil(
            lambda: getattr(fenster, "letzter_hinweis", None) == ("ergebnis", "4"),
            timeout=DEBUG_ZEITGRENZE,
        )
    finally:
        if fenster.debug_sitzung is not None:
            fenster._debugger_stoppen_aktion()


def test_bedingung_wandert_mit_der_zeile(qtbot) -> None:  # noqa: ANN001
    from ide.shell.quelltexteditor import QuelltextEditor

    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.setPlainText("a = 1\nb = 2\n")
    editor.bedingung_setzen(2, "a > 0")

    cursor = editor.textCursor()
    cursor.setPosition(0)
    cursor.insertText("neu = 0\n")

    assert editor.bedingungen == {3: "a > 0"}
    assert editor.breakpoints == {3}


def test_randmenue_bietet_die_bedingung_an(qtbot) -> None:  # noqa: ANN001
    from ide.shell.quelltexteditor import QuelltextEditor

    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.setPlainText("a = 1\n")
    editor.bedingung_setzen(1, "a == 1")

    texte = [a.text() for a in editor._haltepunkt_menue(1).actions()]

    assert texte == ["Haltepunkt entfernen", "Bedingung festlegen …", "Bedingung entfernen"]
