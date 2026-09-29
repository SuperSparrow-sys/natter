"""Tests für „×“ auf einem Editor-Tab (Abschnitt 7.9). Beim
Durchspielen der Bedienung entdeckt: `editor_tabs.tabCloseRequested`
war nie mit irgendeiner Methode verbunden – der Schließen-Knopf tat
buchstäblich nichts.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from ide.shell.hauptfenster import HauptFenster


def _editor_mit_text(fenster: HauptFenster, tmp_path: Path, text: str, name: str = "u_main.py"):
    pfad = tmp_path / name
    pfad.write_text(text, encoding="utf-8")
    return fenster.datei_oeffnen(pfad)


def test_unveraenderter_tab_schliesst_sofort(tmp_path: Path, hauptfenster) -> None:
    _editor_mit_text(hauptfenster, tmp_path, "x = 1\n")
    assert hauptfenster.editor_tabs.count() == 1

    hauptfenster._tab_schliessen(0)

    assert hauptfenster.editor_tabs.count() == 0


def test_veraenderter_tab_fragt_nach_und_speichert_bei_save(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    editor = _editor_mit_text(hauptfenster, tmp_path, "x = 1\n")
    editor.insertPlainText("zusatz")
    pfad = tmp_path / "u_main.py"

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Save),
    )

    hauptfenster._tab_schliessen(0)

    assert hauptfenster.editor_tabs.count() == 0
    assert "zusatz" in pfad.read_text(encoding="utf-8")


def test_veraenderter_tab_bei_discard_verwirft_aenderungen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    editor = _editor_mit_text(hauptfenster, tmp_path, "x = 1\n")
    editor.insertPlainText("zusatz")
    pfad = tmp_path / "u_main.py"

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Discard),
    )

    hauptfenster._tab_schliessen(0)

    assert hauptfenster.editor_tabs.count() == 0
    assert "zusatz" not in pfad.read_text(encoding="utf-8")


def test_veraenderter_tab_bei_cancel_bleibt_offen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    editor = _editor_mit_text(hauptfenster, tmp_path, "x = 1\n")
    editor.insertPlainText("zusatz")

    monkeypatch.setattr(
        "ide.shell.hauptfenster.QMessageBox.question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Cancel),
    )

    hauptfenster._tab_schliessen(0)

    assert hauptfenster.editor_tabs.count() == 1


def test_designer_tab_schliesst_ohne_nachfrage_und_raeumt_buchhaltung_auf(
    tmp_path: Path, hauptfenster_bauen,
) -> None:
    import shutil

    projekt_original = (
        Path(__file__).resolve().parent.parent / "beispielprojekte" / "04_CookieKlicker"
    )
    projekt_kopie = tmp_path / "CookieKlicker"
    shutil.copytree(projekt_original, projekt_kopie)

    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(projekt_kopie / "04_CookieKlicker.natter")
    formular = fenster.designer_oeffnen(projekt_kopie / "u_main.pfm")
    assert fenster.editor_tabs.count() == 1
    assert formular._qwidget in fenster._widget_zu_canvas

    fenster._tab_schliessen(0)

    assert fenster.editor_tabs.count() == 0
    assert formular._qwidget not in fenster._widget_zu_canvas
    assert str(projekt_kopie / "u_main.pfm") not in fenster._pfad_zu_formular


def test_geschlossene_reiter_werden_freigegeben(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot, hauptfenster,
) -> None:  # noqa: ANN001
    """Punkt 376: `removeTab` nahm die Seite nur aus der Leiste. Editor,
    Designer und CSV-Ansicht blieben als verborgene Kinder des
    Hauptfensters bestehen, und die CSV-Ansicht las ihre Datei bei
    jeder Änderung weiter neu ein."""
    import shutil

    import shiboken6

    from ide.viewers import csv_ansicht
    from ide.viewers.csv_ansicht import CsvAnsicht

    projekt = tmp_path / "CookieKlicker"
    shutil.copytree(
        Path(__file__).resolve().parent.parent
        / "beispielprojekte" / "04_CookieKlicker",
        projekt,
    )
    tabelle = projekt / "punkte.csv"
    tabelle.write_text("Name;Punkte\nAnna;3\n", encoding="utf-8")
    hauptfenster.projekt_oeffnen(projekt / "04_CookieKlicker.natter")
    hauptfenster.designer_oeffnen(projekt / "u_main.pfm")
    hauptfenster.oeffnen(tabelle)
    hauptfenster.datei_oeffnen(projekt / "u_main.py")
    # Der Suchdialog zeigt auf den Editor und darf ihn nach dem
    # Schließen nicht mehr benutzen.
    hauptfenster._suchen_aktion()
    reiter = hauptfenster.editor_tabs
    assert reiter.count() == 3
    seiten = [reiter.widget(i) for i in range(3)]
    inhalte = [hauptfenster._tab_inhalt(seite) for seite in seiten]
    assert any(isinstance(inhalt, CsvAnsicht) for inhalt in inhalte)
    gelesen: list[Path] = []
    echt = csv_ansicht._datei_lesen
    monkeypatch.setattr(
        csv_ansicht, "_datei_lesen",
        lambda pfad, *args: gelesen.append(pfad) or echt(pfad, *args),
    )

    while reiter.count():
        hauptfenster._tab_schliessen(0)
    qtbot.waitUntil(
        lambda: not any(shiboken6.isValid(w) for w in seiten + inhalte),
        timeout=5000,
    )
    tabelle.write_text("Name;Punkte\nAnna;4\n", encoding="utf-8")
    qtbot.wait(csv_ansicht.NEU_LADEN_PAUSE_MS * 3)

    assert hauptfenster.findChildren(CsvAnsicht) == []
    assert gelesen == []
    assert not hauptfenster._suchen_dialog.isVisible()
