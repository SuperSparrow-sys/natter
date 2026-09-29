"""„Neues Projekt …“ mit Namen, die Windows als Ordnernamen nicht
annimmt: der Dialog, `projekt_erzeugen` und das Hauptfenster lehnen sie
mit einem deutschen Hinweis ab, und es bleibt kein Ordner zurück."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from ide.project import projekt_erzeugen
from ide.project.neu import _TEMPLATES_DIR, _vorlagendatei_rendern, name_pruefen
from ide.project.neu_dialog import NeuesProjektDialog

UNGUELTIGE_NAMEN = ["Ampel?", 'Ampel "neu"', "Zins: Rechner", "Klasse7\\Ampel"]


@pytest.mark.parametrize("name", UNGUELTIGE_NAMEN + ["Ampel.", "Ampel ", "con"])
def test_name_pruefen_lehnt_ab(name: str) -> None:
    assert name_pruefen(name)


@pytest.mark.parametrize("name", ["Ampel", "Zins-Rechner 2", "Übung_3", "v1.2"])
def test_name_pruefen_nimmt_an(name: str) -> None:
    assert name_pruefen(name) is None


@pytest.mark.parametrize("vorlage", ["gui", "console"])
@pytest.mark.parametrize("name", UNGUELTIGE_NAMEN)
def test_projekt_erzeugen_lehnt_ab_ohne_ordner(
    tmp_path: Path, vorlage: str, name: str
) -> None:
    with pytest.raises(ValueError):
        projekt_erzeugen(vorlage, tmp_path / name, name)

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("name", UNGUELTIGE_NAMEN)
def test_hauptfenster_meldet_ungueltigen_namen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str, hauptfenster_bauen
) -> None:
    class _Attrappe:
        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        def werte(self) -> tuple[str, Path, str]:
            return "console", tmp_path / name, name

    monkeypatch.setattr(
        "ide.shell.hauptfenster.NeuesProjektDialog",
        lambda parent=None: _Attrappe(),
    )
    fenster = hauptfenster_bauen()

    fenster._neues_projekt_dialog()

    assert fenster.projekt is None
    assert "konnte nicht angelegt werden" in (
        fenster.statusBar().currentMessage()
    )
    assert list(tmp_path.iterdir()) == []


def test_hauptfenster_meldet_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster_bauen
) -> None:
    class _Attrappe:
        def exec(self) -> int:
            return QDialog.DialogCode.Accepted

        def werte(self) -> tuple[str, Path, str]:
            return "console", tmp_path / "Ampel", "Ampel"

    def _scheitern(*_args: object) -> None:
        raise PermissionError(13, "Zugriff verweigert")

    monkeypatch.setattr(
        "ide.shell.hauptfenster.NeuesProjektDialog",
        lambda parent=None: _Attrappe(),
    )
    monkeypatch.setattr("ide.project.neu._dateien_schreiben", _scheitern)
    fenster = hauptfenster_bauen()

    fenster._neues_projekt_dialog()

    assert "Zugriff verweigert" in fenster.statusBar().currentMessage()
    assert not (tmp_path / "Ampel").exists()


def test_dialog_bleibt_bei_ungueltigem_namen_offen(qtbot) -> None:
    dialog = NeuesProjektDialog()
    qtbot.addWidget(dialog)
    dialog.name_eingabe.setText("Ampel?")

    dialog.accept()

    assert dialog.result() != QDialog.DialogCode.Accepted
    assert "?" in dialog.hinweis.text()
    assert not dialog.hinweis.isHidden()

    dialog.name_eingabe.setText("Ampel")
    dialog.accept()
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_dialog_bleibt_ohne_namen_offen(qtbot) -> None:
    """Punkt 296: „OK“ ohne Namen lässt den Dialog offen und zeigt
    den Hinweis dort, wo der Name einzugeben ist."""
    dialog = NeuesProjektDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    dialog.name_eingabe.setText("")

    dialog.knopfleiste.button(QDialogButtonBox.StandardButton.Ok).click()

    assert dialog.isVisible()
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert dialog.hinweis.isVisible()
    assert "Namen" in dialog.hinweis.text()
    assert dialog.focusWidget() is dialog.name_eingabe


def test_dialog_bleibt_ohne_ordner_offen(qtbot) -> None:
    dialog = NeuesProjektDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    dialog.name_eingabe.setText("Ampel")
    dialog.ordner_eingabe.setText("  ")

    dialog.knopfleiste.button(QDialogButtonBox.StandardButton.Ok).click()

    assert dialog.isVisible()
    assert dialog.hinweis.isVisible()
    assert "Ordner" in dialog.hinweis.text()
    assert dialog.focusWidget() is dialog.ordner_eingabe


@pytest.mark.parametrize(
    ("datei", "erwartet"),
    [
        ("Ampel.natter", "Ein Projekt „Ampel“ gibt es in diesem Ordner schon."),
        ("notizen.txt", "schon etwas mit dem Namen „Ampel“"),
    ],
)
def test_dialog_bleibt_bei_vorhandenem_ordner_offen(
    qtbot, tmp_path: Path, datei: str, erwartet: str
) -> None:
    """Punkt 432: bis 0.4.2 schloss sich der Dialog, und die Meldung
    stand nur in der Statusleiste. Jetzt steht sie im Dialog, und der
    Name ist zum Überschreiben markiert."""
    (tmp_path / "Ampel").mkdir()
    (tmp_path / "Ampel" / datei).write_text("x", encoding="utf-8")
    dialog = NeuesProjektDialog()
    qtbot.addWidget(dialog)
    dialog.show()
    qtbot.waitExposed(dialog)
    dialog.name_eingabe.setText("Ampel")
    dialog.ordner_eingabe.setText(str(tmp_path))

    dialog.knopfleiste.button(QDialogButtonBox.StandardButton.Ok).click()

    assert dialog.isVisible()
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert dialog.hinweis.isVisible()
    assert erwartet in dialog.hinweis.text()
    assert dialog.focusWidget() is dialog.name_eingabe
    assert dialog.name_eingabe.selectedText() == "Ampel"


def test_vorlagen_maskieren_den_namen() -> None:
    name = 'a"b\\c'
    natter = _vorlagendatei_rendern(
        _TEMPLATES_DIR / "console", "project.natter", name
    )
    assert json.loads(natter)["name"] == name

    pfm = _vorlagendatei_rendern(_TEMPLATES_DIR / "gui", "u_main.pfm", name)
    assert json.loads(pfm)["properties"]["caption"] == name

    code = _vorlagendatei_rendern(_TEMPLATES_DIR / "console", "u_main.py", name)
    assert any(
        isinstance(knoten, ast.Constant) and name in str(knoten.value)
        for knoten in ast.walk(ast.parse(code))
    )
