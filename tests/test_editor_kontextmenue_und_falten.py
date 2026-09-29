"""Alles zu- und aufklappen (Punkt 76) und das Kontextmenü des
Quelltexteditors (Punkt 77).

`alles_entfalten` gab es, aufgerufen wurde es nur in Tests; Zuklappen
fehlte ganz. „Zur Definition“, „Zeile duplizieren“ und „Zeile
verschieben“ gab es nur als Tastenkürzel.
"""

from __future__ import annotations

import json
from pathlib import Path

from ide.shell.quelltexteditor import QuelltextEditor

QUELLTEXT = (
    "class Konto:\n"
    "    def einzahlen(self, betrag):\n"
    "        self.stand += betrag\n"
    "\n"
    "    def abheben(self, betrag):\n"
    "        self.stand -= betrag\n"
    "\n"
    "\n"
    "def hallo():\n"
    "    print('hallo')\n"
)


def _zeilen(editor: QuelltextEditor, sichtbar: bool) -> list[int]:
    dokument = editor.document()
    return [
        n + 1
        for n in range(dokument.blockCount())
        if dokument.findBlockByNumber(n).isVisible() == sichtbar
    ]


def _sichtbar(editor: QuelltextEditor) -> list[int]:
    return _zeilen(editor, True)


def _verborgen(editor: QuelltextEditor) -> list[int]:
    return _zeilen(editor, False)


def _aktionen(editor: QuelltextEditor) -> dict:
    return {a.text().split("\t")[0]: a for a in editor.kontextmenue().actions() if a.text()}


def test_alles_zuklappen_und_aufklappen(qtbot) -> None:  # noqa: ANN001
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.setPlainText(QUELLTEXT)

    editor.alles_falten()
    assert _verborgen(editor) == [2, 3, 4, 5, 6, 10]

    editor.alles_entfalten()
    assert _verborgen(editor) == []


def test_menue_quelltext_klappt_im_aktiven_editor(
    qtbot, tmp_path: Path, hauptfenster_bauen
) -> None:  # noqa: ANN001
    (tmp_path / "main.py").write_text(QUELLTEXT, encoding="utf-8")
    natter = tmp_path / "t.natter"
    natter.write_text(json.dumps({
        "format": "natter-project/1", "name": "T", "type": "console", "main": "main.py",
    }), encoding="utf-8")
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(natter)
    editor = fenster.datei_oeffnen(tmp_path / "main.py")

    fenster.aktionen["quelltext.alles_zuklappen"].qaction.trigger()
    assert _verborgen(editor) == [2, 3, 4, 5, 6, 10]
    fenster.aktionen["quelltext.alles_aufklappen"].qaction.trigger()
    assert _verborgen(editor) == []


def test_kontextmenue_hat_die_befehle_der_tastenkuerzel(qtbot) -> None:  # noqa: ANN001
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.setPlainText("a = 1\nb = 2\n")
    gesucht = []
    editor.definition_gesucht.connect(lambda: gesucht.append(True))

    aktionen = _aktionen(editor)
    for name in ("Zur Definition springen", "Zeile duplizieren", "Zeile nach oben",
                 "Zeile nach unten", "Kommentar umschalten", "Alles zuklappen",
                 "Alles aufklappen"):
        assert name in aktionen, name

    aktionen["Zeile duplizieren"].trigger()
    assert editor.toPlainText() == "a = 1\na = 1\nb = 2\n"
    _aktionen(editor)["Zur Definition springen"].trigger()
    assert gesucht == [True]


def test_schreibgeschuetzt_sind_die_aendernden_befehle_grau(qtbot) -> None:  # noqa: ANN001
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.setPlainText("a = 1\n")
    editor.setReadOnly(True)

    aktionen = _aktionen(editor)

    assert not aktionen["Zeile duplizieren"].isEnabled()
    assert not aktionen["Kommentar umschalten"].isEnabled()
    assert aktionen["Zur Definition springen"].isEnabled()
    assert aktionen["Alles zuklappen"].isEnabled()
