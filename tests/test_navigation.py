"""„Zuletzt geöffnet“ im Menü, Strg+W, Alt+Links (Punkt 106)."""

from __future__ import annotations

import json
from pathlib import Path


def _projekt(ordner: Path, name: str = "T") -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text("from u_rechnen import summe\nx = summe(1, 2)\n",
                                    encoding="utf-8")
    (ordner / "u_rechnen.py").write_text("\n\ndef summe(a, b):\n    return a + b\n",
                                         encoding="utf-8")
    natter = ordner / f"{name}.natter"
    natter.write_text(json.dumps({
        "format": "natter-project/1", "name": name, "type": "console", "main": "main.py",
    }), encoding="utf-8")
    return natter


def test_zuletzt_geoeffnet_im_menue(qtbot, tmp_path: Path, hauptfenster) -> None:  # noqa: ANN001
    hauptfenster.projekt_oeffnen(_projekt(tmp_path / "eins", "Eins"))
    hauptfenster.projekt_oeffnen(_projekt(tmp_path / "zwei", "Zwei"))

    hauptfenster._zuletzt_menue_aufbauen()
    eintraege = [a.text() for a in hauptfenster._zuletzt_menue.actions()]

    assert eintraege[:2] == ["Zwei", "Eins"]
    hauptfenster._zuletzt_menue.actions()[1].trigger()
    assert hauptfenster.projekt.name == "Eins"


def test_strg_w_schliesst_den_reiter(qtbot, tmp_path: Path, hauptfenster) -> None:  # noqa: ANN001
    natter = _projekt(tmp_path)
    hauptfenster.projekt_oeffnen(natter)
    editor = hauptfenster.datei_oeffnen(tmp_path / "u_rechnen.py")

    hauptfenster.aktionen["fenster.reiter_schliessen"].qaction.trigger()

    assert hauptfenster.editor_tabs.indexOf(editor) == -1


def test_alt_links_fuehrt_nach_f12_zurueck(
    qtbot, tmp_path: Path, hauptfenster
) -> None:  # noqa: ANN001
    hauptfenster.projekt_oeffnen(_projekt(tmp_path))
    editor = hauptfenster.datei_oeffnen(tmp_path / "main.py")
    cursor = editor.textCursor()
    cursor.setPosition(editor.document().findBlockByNumber(1).position() + 5)
    editor.setTextCursor(cursor)

    hauptfenster._zur_definition_springen()
    assert hauptfenster._aktueller_editor() is not editor

    hauptfenster.aktionen["suchen.zurueck"].qaction.trigger()

    assert hauptfenster._aktueller_editor() is editor
    assert editor.textCursor().blockNumber() == 1


def test_alt_links_ohne_verlauf_meldet_sich(qtbot, hauptfenster) -> None:  # noqa: ANN001

    hauptfenster.aktionen["suchen.zurueck"].qaction.trigger()

    assert "keine vorige Stelle" in hauptfenster.statusBar().currentMessage()
