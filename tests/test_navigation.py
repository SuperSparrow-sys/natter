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


def test_f12_auf_eine_komponente_oeffnet_den_designer(
    qtbot, tmp_path: Path, hauptfenster  # noqa: ANN001
) -> None:
    """Punkt 545: F12 auf `self.e_zahl1` öffnete die erzeugte
    `u_main_design.py` zum Bearbeiten, und jede Änderung dort ging beim
    nächsten Schreiben des Designers verloren."""
    import shutil

    from ide.shell.quelltexteditor import QuelltextEditor

    quelle = Path(__file__).resolve().parent.parent / "beispielprojekte" / "03_Taschenrechner"
    ziel = tmp_path / "03"
    shutil.copytree(quelle, ziel, ignore=shutil.ignore_patterns("__pycache__"))
    hauptfenster.projekt_oeffnen(ziel / "03_Taschenrechner.natter")
    editor = hauptfenster.datei_oeffnen(ziel / "u_main.py")
    text = editor.toPlainText()
    cursor = editor.textCursor()
    cursor.setPosition(text.index("self.e_zahl1") + len("self.e_"))
    editor.setTextCursor(cursor)

    meldung = hauptfenster._zur_definition_springen()

    offen = [
        hauptfenster.editor_tabs.widget(i) for i in range(hauptfenster.editor_tabs.count())
    ]
    assert not any(
        isinstance(w, QuelltextEditor) and str(w.property("pfad")).endswith("_design.py")
        for w in offen
    )
    canvas = hauptfenster._aktueller_canvas
    assert canvas is not None and canvas.ausgewaehlte_komponente is canvas.formular.e_zahl1
    assert "ausgewählt" in meldung


def test_strg_p_oeffnet_ein_formular_im_designer(
    qtbot, tmp_path: Path, hauptfenster, monkeypatch  # noqa: ANN001
) -> None:
    """Punkt 558: Die Wahl einer `.pfm` in „Unit öffnen …“ öffnete sie
    als JSON-Text im Editor."""
    import shutil

    from PySide6.QtWidgets import QDialog

    from ide.shell import hauptfenster as modul
    from ide.shell.quelltexteditor import QuelltextEditor

    quelle = Path(__file__).resolve().parent.parent / "beispielprojekte" / "03_Taschenrechner"
    ziel = tmp_path / "03"
    shutil.copytree(quelle, ziel, ignore=shutil.ignore_patterns("__pycache__"))
    hauptfenster.projekt_oeffnen(ziel / "03_Taschenrechner.natter")

    def waehlen(dialog) -> QDialog.DialogCode:  # noqa: ANN001
        dialog.ausgewaehlte_datei = ziel / "u_main.pfm"
        return QDialog.DialogCode.Accepted

    monkeypatch.setattr(modul.SchnellAuswahl, "exec", waehlen)

    hauptfenster.aktionen["datei.unit_oeffnen"].qaction.trigger()

    assert hauptfenster._aktueller_canvas is not None
    assert not any(
        isinstance(hauptfenster.editor_tabs.widget(i), QuelltextEditor)
        for i in range(hauptfenster.editor_tabs.count())
    )
