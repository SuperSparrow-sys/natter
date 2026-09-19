"""Die Umstiegs-Referenz Pascal → Python (M12).

`konzept-natter.md` sieht sie seit jeher vor – Abschnitt 7.2 führt
„Umstieg Pascal → Python“ im Menü „Hilfe“ auf, Abschnitt 5 verspricht
eine vollständige Referenz offline. Gebaut war sie nie. Dabei ist sie
für die Zielgruppe das, was am häufigsten nachgeschlagen wird:
`begin…end` gegen Einrückung, `:=` gegen `=`, `writeln` gegen `print`.
Die Tabellen standen nur im Konzeptdokument und waren damit für genau
die Leute unerreichbar, die sie brauchen.

Zwei Dinge hält dieser Test fest: dass die Seite erreichbar ist, und
dass nichts darin falsch ist – jedes gezeigte Stück Python muss sich
übersetzen lassen, und jeder genannte `pcl`-Name muss es wirklich
geben. Eine Referenz, die etwas Falsches zeigt, schickt jemanden auf
die Suche nach einem Fehler, den es nicht gibt.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

import pcl
from ide.shell.hauptfenster import HauptFenster

SEITE = Path(__file__).resolve().parent.parent / "docs" / "umstieg_pascal_python.md"


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import pcl.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


def _text() -> str:
    return SEITE.read_text(encoding="utf-8")


def _python_bloecke() -> list[str]:
    return re.findall(r"```python\n(.*?)```", _text(), re.DOTALL)


def test_die_seite_gibt_es() -> None:
    assert SEITE.exists()


def test_sie_steht_im_menue_hilfe(einstellungen: QSettings, qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    eintraege = [a.text() for a in fenster.menue("Hilfe").actions()]

    assert "Umstieg Pascal → Python" in eintraege


def test_der_eintrag_oeffnet_die_seite(einstellungen: QSettings, qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    assert fenster._umstieg_aktion() is True

    titel = {
        fenster.editor_tabs.tabText(i) for i in range(fenster.editor_tabs.count())
    }
    assert "Umstieg Pascal → Python" in titel


def test_die_versprochenen_themen_kommen_vor() -> None:
    """Das Konzept nennt: Datentypen, Strings, Arrays/Records, Dateien,
    Klassen, Vererbung."""
    text = _text()

    for thema in ("Datentypen", "Strings", "Listen", "Klassen", "Dateien", "Units"):
        assert f"## {thema}" in text or thema in text, f"{thema} fehlt"
    assert "Vererbung" in text


def test_die_stolpersteine_stehen_drin() -> None:
    """Die drei, an denen in dieser Umstellung wirklich jeder hängt."""
    text = _text()

    assert "Einrückung" in text  # begin/end
    assert "==" in text  # Vergleich gegen Zuweisung
    assert "int(input(" in text  # input() liefert immer Text


def test_jedes_gezeigte_python_laesst_sich_uebersetzen() -> None:
    """Ein Tippfehler in der Referenz lehrt etwas Falsches."""
    bloecke = _python_bloecke()
    assert len(bloecke) >= 5, "Die Blöcke wurden gar nicht gefunden."

    for nummer, block in enumerate(bloecke, start=1):
        compile(block, f"<umstieg-block-{nummer}>", "exec")


def test_jeder_genannte_pcl_name_existiert_wirklich() -> None:
    """Die Seite nennt `show_message`, `input_box`, `pcl.crt`-Funktionen
    und Komponenten-Eigenschaften. Verschwindet eine davon, muss der
    Test rot werden und nicht die Schülerin suchen."""
    text = _text()

    for name in ("show_message", "input_box"):
        if name in text:
            assert hasattr(pcl, name), f"{name} steht in der Referenz, gibt es aber nicht"

    from pcl import crt

    treffer = re.search(r"from pcl\.crt import ([^\n]+)", text)
    assert treffer is not None, "Der crt-Import wurde nicht gefunden."
    for name in (teil.strip() for teil in treffer.group(1).split(",")):
        assert hasattr(crt, name), f"pcl.crt.{name} steht in der Referenz, gibt es aber nicht"


def test_die_genannten_komponenten_eigenschaften_gibt_es() -> None:
    """`caption`, `text`, `lines`, `items` und `picture` werden als
    Gegenstück zu den Lazarus-Namen gezeigt."""
    from pcl import Button, Edit, Image, ListBox, Memo
    from pcl.properties import eigenschaften

    assert "caption" in eigenschaften(Button)
    assert "text" in eigenschaften(Edit)
    assert hasattr(Memo, "lines")
    assert hasattr(ListBox, "items")
    assert hasattr(Image, "picture")


# -- Darstellung ---------------------------------------------------------


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
    `u_main_design.py` wurde dadurch unleserliches Zeug, auf **jeder**
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
    if vorhanden:  # ohne geladene Schriften ist nichts zu pruefen
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


def test_die_umstiegsseite_hat_keine_unaufgeloeste_schrift(
    einstellungen: QSettings, qtbot
) -> None:
    """Der Fall, um den es geht: die Seite besteht fast nur aus
    Code-Stellen."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster._umstieg_aktion()

    ansicht = fenster.editor_tabs.currentWidget()
    assert "monospace" not in _familien(ansicht)
