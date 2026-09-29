"""Die Hilfe-Ansicht setzt Code-Stellen in eine Schrift, die es gibt.

Qt setzt beim Umwandeln von Markdown die Gattungsfamilie „monospace“ -
die es unter Windows nicht gibt. Aus `u_main_design.py` wurde dadurch
unleserliches Zeug, auf jeder Hilfeseite (M12, am Bildschirmfoto
gefunden).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from ide.shell.hauptfenster import HauptFenster


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import pcl.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


def _familien(ansicht) -> set[str]:
    """Alle Schriftfamilien, die im dargestellten Dokument vorkommen."""
    gefunden: set[str] = set()
    dokument = ansicht.document()
    block = dokument.begin()
    while block.isValid():
        teil = block.begin()
        while not teil.atEnd():
            stueck = teil.fragment()
            if stueck.isValid():
                gefunden.update(stueck.charFormat().fontFamilies() or [])
            teil += 1
        block = block.next()
    return gefunden


def test_code_stellen_bekommen_eine_schrift_die_es_gibt(qtbot) -> None:
    """Qt setzt Code-Stellen beim Umwandeln von Markdown auf die
    Gattungsfamilie „monospace“ - die es unter Windows nicht gibt. Aus
    `u_main_design.py` wurde dadurch unleserliches Zeug, auf jeder
    Hilfeseite (M12, am Bildschirmfoto gefunden)."""
    from PySide6.QtGui import QFontDatabase

    from ide.viewers.hilfe_ansicht import HilfeAnsicht

    ansicht = HilfeAnsicht()
    qtbot.addWidget(ansicht)

    ansicht.markdown_setzen(
        "Text mit `u_main_design.py` darin." + chr(10) * 2
        + "```python" + chr(10) + "x = 1" + chr(10) + "```" + chr(10)
    )

    familien = _familien(ansicht)
    assert "monospace" not in familien
    vorhanden = set(QFontDatabase.families())
    if vorhanden:  # ohne geladene Schriften ist nichts zu prüfen
        assert familien & vorhanden, f"Keine der Familien {familien} gibt es wirklich"


def test_die_gewaehlte_schrift_gibt_es_auch(qtbot) -> None:
    from PySide6.QtGui import QFontDatabase

    from ide.viewers.hilfe_ansicht import code_schriftart

    vorhanden = set(QFontDatabase.families())
    if not vorhanden:
        pytest.skip("Keine Schriften geladen")

    assert code_schriftart() in vorhanden


def test_der_fliesstext_bleibt_unangetastet(qtbot) -> None:
    """Nur die Code-Stellen werden umgestellt - sonst sähe die ganze
    Seite aus wie Quelltext."""
    from ide.viewers.hilfe_ansicht import HilfeAnsicht, code_schriftart

    ansicht = HilfeAnsicht()
    qtbot.addWidget(ansicht)

    ansicht.markdown_setzen("Ganz normaler Fließtext ohne Code." + chr(10))

    assert code_schriftart() not in _familien(ansicht)


def test_die_komponenten_referenz_hat_keine_unaufgeloeste_schrift(
    einstellungen: QSettings, qtbot
) -> None:
    """Der Fall, um den es geht: eine Seite voller Code-Stellen."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster._komponenten_referenz_aktion()

    ansicht = fenster.editor_tabs.currentWidget()
    assert "monospace" not in _familien(ansicht)
