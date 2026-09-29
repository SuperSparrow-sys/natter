"""Punkt 438: Hilfeseiten lassen sich durchsuchen, die langen Seiten
haben ein Inhaltsverzeichnis, und F1 öffnet die Hilfe.

Die Komponenten-Referenz war rund 90 Bildschirmseiten lang, ohne
Verweis und ohne Suche: Strg+F meldete in ihr, es sei kein
Quelltext-Reiter vorn, und F1 war keiner Aktion zugeordnet."""

from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QUrl
from PySide6.QtWidgets import QApplication

from ide.viewers.hilfe_ansicht import HilfeAnsicht

WURZEL = Path(__file__).resolve().parent.parent
REFERENZ = (WURZEL / "docs" / "komponenten.md").read_text(encoding="utf-8")


def _oberster_block(ansicht: HilfeAnsicht) -> str:
    """Der Text der obersten sichtbaren Zeile."""
    QApplication.processEvents()
    return ansicht.cursorForPosition(QPoint(5, 5)).block().text()


def test_referenz_hat_ein_inhaltsverzeichnis_aus_den_ueberschriften(
    qtbot,
) -> None:
    ansicht = HilfeAnsicht()
    qtbot.addWidget(ansicht)
    ansicht.resize(900, 600)
    ansicht.show()
    ansicht.markdown_setzen(REFERENZ, inhaltsverzeichnis=True)

    ueberschriften = re.findall(r"^## (.+)$", REFERENZ, re.M)
    verweise = re.findall(r'href="#([^"]+)"', ansicht.toHtml())
    anker = {a for _, _, a in ansicht.abschnitte()}
    assert len(verweise) >= len(ueberschriften) > 40
    assert set(verweise) <= anker
    assert "timer" in verweise

    ansicht.setSource(QUrl("#timer"))
    assert _oberster_block(ansicht) == "Timer"


@pytest.fixture
def fenster_mit_beispiel(hauptfenster, tmp_path: Path):
    """Hauptfenster mit einer Kopie von Beispiel 03, Formular im
    Designer. Kopiert, weil der Designer in die .pfm zurückschreibt."""
    ziel = tmp_path / "03_Taschenrechner"
    shutil.copytree(WURZEL / "beispielprojekte" / "03_Taschenrechner", ziel)
    hauptfenster.resize(1280, 720)
    hauptfenster.show()
    hauptfenster.projekt_oeffnen(ziel / "03_Taschenrechner.natter")
    return hauptfenster, ziel


def _button_waehlen(fenster, ziel: Path) -> None:  # noqa: ANN001
    fenster.designer_oeffnen(ziel / "u_main.pfm")
    canvas = fenster._aktueller_canvas
    canvas.auswahl_setzen([canvas.formular.b_plus])


def _timer_im_editor(fenster, ziel: Path) -> None:  # noqa: ANN001
    pfad = ziel / "u_timer.py"
    pfad.write_text(
        "from pcl import Timer\n\nuhr = Timer(None)\n", encoding="utf-8"
    )
    editor = fenster.datei_oeffnen(pfad)
    cursor = editor.textCursor()
    cursor.setPosition(editor.toPlainText().index("Timer(") + 2)
    editor.setTextCursor(cursor)


@pytest.mark.parametrize(
    ("vorbereiten", "abschnitt"),
    [(_button_waehlen, "Button"), (_timer_im_editor, "Timer")],
    ids=["designer_button", "editor_timer"],
)
def test_f1_oeffnet_die_referenz_beim_abschnitt(
    fenster_mit_beispiel, vorbereiten, abschnitt: str
) -> None:
    fenster, ziel = fenster_mit_beispiel
    vorbereiten(fenster, ziel)

    fenster.aktionen["hilfe.zur_auswahl"].qaction.trigger()

    ansicht = fenster.editor_tabs.currentWidget()
    assert isinstance(ansicht, HilfeAnsicht)
    index = fenster.editor_tabs.currentIndex()
    assert fenster.editor_tabs.tabText(index) == "Komponenten-Referenz"
    assert _oberster_block(ansicht) == abschnitt


def test_f1_ohne_komponente_oeffnet_das_handbuch(hauptfenster) -> None:
    aktion = hauptfenster.aktionen["hilfe.zur_auswahl"].qaction
    assert aktion.shortcut().toString() == "F1"
    assert aktion in hauptfenster.menue("Hilfe").actions()
    uebersicht = hauptfenster._tastenkuerzel_aktion().toPlainText()
    assert "F1" in uebersicht
    assert "Hilfe zur Auswahl" in uebersicht

    aktion.trigger()

    index = hauptfenster.editor_tabs.currentIndex()
    assert hauptfenster.editor_tabs.tabText(index) == "Handbuch"


def test_strg_f_sucht_in_der_referenz(hauptfenster, qtbot) -> None:
    hauptfenster.resize(1280, 720)
    hauptfenster.show()
    hauptfenster.aktionen["hilfe.komponenten_referenz"].qaction.trigger()
    ansicht = hauptfenster.editor_tabs.currentWidget()
    assert isinstance(ansicht, HilfeAnsicht)
    hauptfenster.statusBar().clearMessage()

    hauptfenster.aktionen["suchen.suchen"].qaction.trigger()

    assert "Quelltext-Reiter" not in hauptfenster.statusBar().currentMessage()
    assert ansicht.suchleiste.isVisible()
    qtbot.keyClicks(ansicht.suchfeld, "Timer")
    assert ansicht.textCursor().selectedText() == "Timer"
    erster = ansicht.textCursor().position()

    # F3 wie im Editor: der nächste Treffer.
    hauptfenster.aktionen["suchen.weitersuchen"].qaction.trigger()
    assert ansicht.textCursor().selectedText() == "Timer"
    assert ansicht.textCursor().position() > erster

    ansicht.suchfeld.setText("gibt es in der Referenz nicht")
    assert not ansicht.weitersuchen()
    assert ansicht.suchhinweis.text() == "Nicht gefunden"

