"""Tests für die restlichen Editor-Hilfen aus M11, Abschnitt 2.1/2.3:

* Leerzeichen und Tabulatoren sichtbar machen
* beim Einfügen aus der Zwischenablage die Einrückung anpassen
* zu einer Definition springen (F12)

Alle drei zielen auf denselben Punkt: in Python trägt die Einrückung
Bedeutung, und wer den Faden verliert, verliert ihn an einer Stelle, an
der am Bildschirm nichts zu sehen ist.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QTextOption

from ide.project import Projekt
from ide.shell.hauptfenster import HauptFenster
from ide.shell.quelltexteditor import QuelltextEditor
from ide.shell.vervollstaendigung import definition


@pytest.fixture
def editor(qtbot) -> QuelltextEditor:
    feld = QuelltextEditor()
    qtbot.addWidget(feld)
    return feld


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import ide.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


def _flags(feld: QuelltextEditor) -> QTextOption.Flag:
    return feld.document().defaultTextOption().flags()


# -- Leerzeichen sichtbar machen -----------------------------------------


def test_leerzeichen_sind_zunaechst_unsichtbar(editor: QuelltextEditor) -> None:
    """Das Bild wird sonst unruhig, und wer es nicht braucht, soll es
    nicht sehen."""
    assert not _flags(editor) & QTextOption.Flag.ShowTabsAndSpaces


def test_leerzeichen_lassen_sich_einschalten(editor: QuelltextEditor) -> None:
    editor.leerzeichen_setzen(True)

    assert _flags(editor) & QTextOption.Flag.ShowTabsAndSpaces
    assert editor.leerzeichen_sichtbar is True


def test_leerzeichen_lassen_sich_wieder_ausschalten(
    editor: QuelltextEditor,
) -> None:
    editor.leerzeichen_setzen(True)

    editor.leerzeichen_setzen(False)

    assert not _flags(editor) & QTextOption.Flag.ShowTabsAndSpaces


def test_das_ansichtsmenue_bietet_die_leerzeichen(
    einstellungen: QSettings, qtbot
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    titel = [a.text() for a in fenster.menue("Ansicht").actions()]

    assert "Leerzeichen anzeigen" in titel


def test_der_umschalter_wirkt_auf_offene_tabs(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    datei = tmp_path / "a.py"
    datei.write_text("x = 1\n", encoding="utf-8")
    geoeffnet = fenster.datei_oeffnen(datei)

    fenster.leerzeichen_aktion.setChecked(True)

    assert _flags(geoeffnet) & QTextOption.Flag.ShowTabsAndSpaces


# -- Einfügen mit passender Einrückung -----------------------------------


def _einfuegen(editor: QuelltextEditor, vorhanden: str, text: str) -> str:
    """Fügt `text` am Ende von `vorhanden` ein und liefert, was danach
    im Editor steht.

    Geprüft wird bewusst das Ergebnis im Text und nicht die
    Zwischenrechnung: der Einzug, den der Cursor schon vor sich hat,
    gehört zum Ergebnis dazu – und genau dort entstand beim Bauen der
    Fehler, dass er ein zweites Mal davorkam.
    """
    from PySide6.QtCore import QMimeData

    editor.setPlainText(vorhanden)
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor.setTextCursor(cursor)
    daten = QMimeData()
    daten.setText(text)
    editor.insertFromMimeData(daten)
    return editor.toPlainText()


def test_ein_block_wird_auf_die_ebene_der_zielstelle_gehoben(
    editor: QuelltextEditor,
) -> None:
    """Aus einer Aufgabenstellung kopierter Quelltext bringt die
    Einrückung seiner alten Umgebung mit."""
    ergebnis = _einfuegen(
        editor, "def f():\n    ", "summe = 0\nfor i in range(3):\n    summe += i"
    )

    assert ergebnis == (
        "def f():\n    summe = 0\n    for i in range(3):\n        summe += i"
    )


def test_die_relative_einrueckung_bleibt_erhalten(editor: QuelltextEditor) -> None:
    ergebnis = _einfuegen(editor, "        ", "if a:\n    b()\nc()")

    assert ergebnis == "        if a:\n            b()\n        c()"


def test_eine_schon_eingerueckte_quelle_wird_nicht_doppelt_eingerueckt(
    editor: QuelltextEditor,
) -> None:
    """Der gemeinsame Einzug des kopierten Stücks wird abgezogen, bevor
    der neue draufkommt – sonst wandert der Block bei jedem Einfügen
    weiter nach rechts."""
    ergebnis = _einfuegen(editor, "    ", "        a = 1\n        b = 2")

    assert ergebnis == "    a = 1\n    b = 2"


def test_tabulatoren_werden_zu_leerzeichen(editor: QuelltextEditor) -> None:
    """Gemischte Einrückung ist der Fehler, den man am Bildschirm am
    schlechtesten sieht."""
    ergebnis = _einfuegen(editor, "", "a = 1\n\tb = 2")

    assert "\t" not in ergebnis
    assert ergebnis == "a = 1\n    b = 2"


def test_leerzeilen_bleiben_leer(editor: QuelltextEditor) -> None:
    """Eine Leerzeile mit Leerzeichen darin meldet ruff als Fund – und
    sie sieht man nicht."""
    ergebnis = _einfuegen(editor, "    ", "a = 1\n\nb = 2")

    assert ergebnis == "    a = 1\n\n    b = 2"


def test_mitten_in_einer_zeile_schliesst_das_erste_stueck_an(
    editor: QuelltextEditor,
) -> None:
    ergebnis = _einfuegen(editor, "    wert = ", "42\nprint(wert)")

    assert ergebnis == "    wert = 42\n    print(wert)"


def test_eine_einzelne_zeile_geht_unveraendert_durch(
    editor: QuelltextEditor,
) -> None:
    """Ein Wort aus dem Browser soll nicht plötzlich eingerückt
    ankommen."""
    assert _einfuegen(editor, "        ", "zaehler") == "        zaehler"


# -- Zu einer Definition springen (F12) ----------------------------------

QUELLE = "def gruessen(name):\n    print(name)\n\n\ngruessen('Welt')\n"


def test_eine_definition_in_derselben_datei_wird_gefunden() -> None:
    fundstelle = definition(QUELLE, 5, 2)

    assert fundstelle is not None
    assert fundstelle.name == "gruessen"
    assert fundstelle.zeile == 1
    assert fundstelle.in_dieser_datei is True


def test_ohne_treffer_kommt_nichts_zurueck() -> None:
    assert definition("   \n", 1, 1) is None


def test_ein_kaputter_quelltext_laesst_nichts_hochgehen() -> None:
    """F12 darf nie etwas auslösen – eine halb getippte Zeile ist
    syntaktisch fast immer kaputt."""
    definition("def (((", 1, 5)


def test_python_selbst_gilt_als_fremd() -> None:
    """Wer auf `print` steht und F12 drückt, landete sonst in
    `builtins.pyi` – Quelltext in einer Sprache, die im Unterricht nie
    vorkommt."""
    fundstelle = definition("print('hallo')\n", 1, 2)

    assert fundstelle is not None
    assert fundstelle.fremd is True
    assert fundstelle.in_dieser_datei is False


def test_eine_datei_im_projekt_gilt_nicht_als_fremd(tmp_path: Path) -> None:
    (tmp_path / "hilfe.py").write_text("def rechne(a):\n    return a\n", encoding="utf-8")
    quelle = tmp_path / "main.py"
    quelle.write_text("from hilfe import rechne\n\nrechne(1)\n", encoding="utf-8")

    fundstelle = definition(
        quelle.read_text(encoding="utf-8"), 3, 2, pfad=quelle, projekt=tmp_path
    )

    assert fundstelle is not None
    assert fundstelle.fremd is False
    assert Path(fundstelle.pfad).name == "hilfe.py"


def test_der_editor_springt_zur_zeile(editor: QuelltextEditor) -> None:
    editor.setPlainText("\n".join(f"zeile {i}" for i in range(1, 30)))

    editor.zu_zeile_springen(12, 3)

    assert editor.textCursor().blockNumber() == 11
    assert editor.textCursor().positionInBlock() == 3


def test_eine_zeile_ausserhalb_der_datei_tut_nichts(editor: QuelltextEditor) -> None:
    editor.setPlainText("a = 1\n")
    vorher = editor.textCursor().position()

    editor.zu_zeile_springen(999)

    assert editor.textCursor().position() == vorher


# -- F12 im Hauptfenster -------------------------------------------------


def _projekt_anlegen(ordner: Path) -> Projekt:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(
        "def gruessen(name):\n    print(name)\n\n\ngruessen('Welt')\n",
        encoding="utf-8",
    )
    (ordner / "test.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Test",
                "type": "console",
                "main": "main.py",
            }
        ),
        encoding="utf-8",
    )
    return Projekt.laden(ordner / "test.natter")


def test_f12_springt_zur_definition(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt = _projekt_anlegen(tmp_path / "p")
    editor = fenster.datei_oeffnen(tmp_path / "p" / "main.py")
    editor.zu_zeile_springen(5, 2)

    meldung = fenster._zur_definition_springen()

    assert "gruessen" in meldung
    assert "Zeile 1" in meldung
    assert editor.textCursor().blockNumber() == 0


def test_f12_auf_python_selbst_sagt_woher_der_name_kommt(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt = _projekt_anlegen(tmp_path / "p")
    editor = fenster.datei_oeffnen(tmp_path / "p" / "main.py")
    editor.zu_zeile_springen(2, 6)  # auf „print“

    meldung = fenster._zur_definition_springen()

    assert "gehört nicht zum Projekt" in meldung


def test_f12_im_leeren_sagt_was_zu_pruefen_ist(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt = _projekt_anlegen(tmp_path / "p")
    editor = fenster.datei_oeffnen(tmp_path / "p" / "main.py")
    editor.zu_zeile_springen(3, 0)

    meldung = fenster._zur_definition_springen()

    assert "keine Definition im Projekt" in meldung
    assert "richtig geschrieben" in meldung


def test_f12_ohne_editor_tut_nichts(einstellungen: QSettings, qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    assert fenster._zur_definition_springen() == ""
