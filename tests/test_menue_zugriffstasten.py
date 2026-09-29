"""Zugriffstasten der Menütitel (Punkt 439).

Unter Windows öffnet Alt und der unterstrichene Buchstabe ein Menü,
Alt+D etwa „Datei“. Bis 0.4.2 hatte kein Menütitel des Hauptfensters
und des Diagramm-Editors eine Zugriffstaste.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMenuBar

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.neu import MVP_TYPEN


def _zugriffstaste(text: str) -> str | None:
    """Der Buchstabe hinter dem ersten einzelnen `&`, klein."""
    stelle = 0
    while (stelle := text.find("&", stelle)) != -1:
        folgt = text[stelle + 1 : stelle + 2]
        if folgt and folgt != "&":
            return folgt.lower()
        stelle += 2
    return None


def _fehler_der_leiste(name: str, leiste: QMenuBar) -> list[str]:
    fehler = []
    gesehen: dict[str, str] = {}
    for aktion in leiste.actions():
        text = aktion.text()
        taste = _zugriffstaste(text)
        if taste is None:
            fehler.append(f"{name}: „{text}“ hat keine Zugriffstaste")
        elif taste in gesehen:
            fehler.append(
                f"{name}: „{text}“ und „{gesehen[taste]}“ teilen "
                f"sich Alt+{taste.upper()}"
            )
        else:
            gesehen[taste] = text
    return fehler


def test_jede_menueleiste_hat_eindeutige_zugriffstasten(
    hauptfenster, tmp_path: Path
) -> None:
    fehler = _fehler_der_leiste("Hauptfenster", hauptfenster.menuBar())
    for typ in MVP_TYPEN:
        fenster = DiagrammFenster(
            diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", "Test")
        )
        try:
            fehler += _fehler_der_leiste(typ, fenster.menuBar())
        finally:
            fenster._geaendert = False
            fenster.close()
            fenster.deleteLater()

    assert fehler == []


def test_alt_d_oeffnet_das_menue_datei(
    hauptfenster, qtbot, tmp_path: Path
) -> None:
    """Auch aus dem Quelltexteditor heraus, wo Alt+Buchstabe sonst
    als Eingabe gelten könnte."""
    fenster = hauptfenster
    datei = tmp_path / "u_main.py"
    datei.write_text("x = 1\n", encoding="utf-8")
    with qtbot.waitActive(fenster):
        fenster.show()
        fenster.activateWindow()
    fenster.oeffnen(datei)
    editor = fenster.editor_tabs.currentWidget()
    editor.setFocus()
    assert QApplication.focusWidget() is not None

    qtbot.keyClick(
        QApplication.focusWidget() or fenster,
        Qt.Key.Key_D,
        Qt.KeyboardModifier.AltModifier,
    )
    try:
        qtbot.waitUntil(
            lambda: fenster.menuBar().activeAction() is not None,
            timeout=5000,
        )
        aktiv = fenster.menuBar().activeAction()
        assert aktiv.text().replace("&", "") == "Datei"
    finally:
        fenster.menue("Datei").close()
