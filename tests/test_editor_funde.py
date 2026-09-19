"""Tests für die Funde direkt im Quelltext (M11, Abschnitt 2.3).

Bis jetzt stand ein Fund der Vorstart-Prüfung **nur** in der Liste unter
dem Editor. Wer gerade erst anfängt, schaut aber nicht nach unten,
sondern auf die Zeile, die er eben getippt hat. Seit M11 wird die Zeile
unterringelt und die deutsche Meldung steht im Tooltip.

Die Liste bleibt trotzdem: sie zeigt auch Funde aus Dateien, die gar
nicht offen sind.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtGui import QTextCharFormat

from ide.project import Projekt
from ide.run.pruefung import RuffFund
from ide.shell.hauptfenster import HauptFenster
from ide.shell.quelltexteditor import QuelltextEditor

QUELLTEXT = "zaehler = 0\nprint(zaehlr)\nprint('fertig')\n"


@pytest.fixture
def editor(qtbot) -> QuelltextEditor:
    feld = QuelltextEditor()
    qtbot.addWidget(feld)
    feld.setPlainText(QUELLTEXT)
    return feld


def _wellenlinien(feld: QuelltextEditor) -> list:
    """Die Markierungen, die eine Wellenlinie tragen - die
    Zeilenhervorhebung läuft über dieselbe Liste."""
    return [
        auswahl
        for auswahl in feld.extraSelections()
        if auswahl.format.underlineStyle()
        == QTextCharFormat.UnderlineStyle.WaveUnderline
    ]


# -- Im Editor -----------------------------------------------------------


def test_ohne_funde_ist_nichts_unterringelt(editor: QuelltextEditor) -> None:
    assert _wellenlinien(editor) == []


def test_ein_fund_unterringelt_seine_zeile(editor: QuelltextEditor) -> None:
    editor.funde_setzen({2: "Der Name zaehlr ist nicht bekannt."})

    assert len(_wellenlinien(editor)) == 1


def test_die_markierung_liegt_auf_der_richtigen_zeile(
    editor: QuelltextEditor,
) -> None:
    editor.funde_setzen({2: "Der Name zaehlr ist nicht bekannt."})

    # Über `extraSelections()` geht das nicht: PySide6 gibt dort einen
    # QTextCursor zurück, dessen C++-Seite schon wieder weg ist
    # („Internal C++ object already deleted“). Qt selbst hält die
    # Markierung als Wert und zeichnet sie richtig - nur die
    # Python-Hülle überlebt den Rückweg nicht. Deshalb die Liste, die
    # der Editor selbst aufbewahrt.
    cursor = editor._fundmarkierungen[0].cursor
    assert cursor.blockNumber() == 1
    assert cursor.selectedText() == "print(zaehlr)"


def test_die_meldung_steht_im_tooltip(editor: QuelltextEditor) -> None:
    editor.funde_setzen({2: "Der Name zaehlr ist nicht bekannt."})

    assert (
        _wellenlinien(editor)[0].format.toolTip()
        == "Der Name zaehlr ist nicht bekannt."
    )


def test_die_meldung_laesst_sich_abfragen(editor: QuelltextEditor) -> None:
    editor.funde_setzen({2: "Der Name zaehlr ist nicht bekannt."})

    assert editor.fund_bei(2) == "Der Name zaehlr ist nicht bekannt."
    assert editor.fund_bei(1) == ""


def test_funde_ausserhalb_des_textes_werden_uebergangen(
    editor: QuelltextEditor,
) -> None:
    """Eine Zeile 99 in einer dreizeiligen Datei darf nicht abstürzen -
    die Datei kann sich seit der Prüfung geändert haben."""
    editor.funde_setzen({99: "irgendwas"})

    assert _wellenlinien(editor) == []


def test_mehrere_funde_werden_alle_unterringelt(editor: QuelltextEditor) -> None:
    editor.funde_setzen({1: "eins", 2: "zwei", 3: "drei"})

    assert len(_wellenlinien(editor)) == 3


def test_funde_loeschen_raeumt_auf(editor: QuelltextEditor) -> None:
    """Sonst stünde nach dem Beheben immer noch der alte Fehler im
    Text."""
    editor.funde_setzen({2: "zwei"})

    editor.funde_loeschen()

    assert _wellenlinien(editor) == []
    assert editor.fund_bei(2) == ""


def test_die_wellenlinien_ueberleben_einen_cursorwechsel(
    editor: QuelltextEditor,
) -> None:
    """Qt führt Zeilenhervorhebung und Wellenlinien über **eine** Liste.
    Sie getrennt zu setzen löschte jeweils die andere: die
    Unterringelungen verschwanden beim ersten Tastendruck wieder.

    Gegenprobe zur Absicherung: setzt man in
    `_aktuelle_zeile_hervorheben` wieder `setExtraSelections(auswahlen)`
    statt `_markierungen_setzen()`, schlägt dieser Test fehl.
    """
    editor.funde_setzen({2: "zwei"})

    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.Down)
    editor.setTextCursor(cursor)

    assert len(_wellenlinien(editor)) == 1


def test_die_zeilenhervorhebung_bleibt_ebenfalls(editor: QuelltextEditor) -> None:
    """Die andere Richtung derselben Falle."""
    editor.funde_setzen({2: "zwei"})

    assert len(editor.extraSelections()) == len(_wellenlinien(editor)) + 1


# -- Zeilenumbruch -------------------------------------------------------


def test_zeilenumbruch_ist_zunaechst_aus(editor: QuelltextEditor) -> None:
    """Wie in Lazarus: in Python trägt die Einrückung Bedeutung, und
    eine umgebrochene Zeile sieht aus wie zwei."""
    assert editor.lineWrapMode() == QuelltextEditor.LineWrapMode.NoWrap


def test_zeilenumbruch_laesst_sich_einschalten(editor: QuelltextEditor) -> None:
    editor.zeilenumbruch_setzen(True)

    assert editor.lineWrapMode() == QuelltextEditor.LineWrapMode.WidgetWidth


# -- Im Hauptfenster -----------------------------------------------------


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    """Eigene Ini - ein Test darf die echten Einstellungen des Rechners
    nicht verstellen."""
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import ide.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


def _projekt(ordner: Path, inhalt: str) -> Projekt:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(inhalt, encoding="utf-8")
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


def test_das_ansichtsmenue_bietet_den_zeilenumbruch(
    einstellungen: QSettings, qtbot
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    titel = [a.text() for a in fenster.menue("Ansicht").actions()]

    assert "Zeilenumbruch" in titel


def test_der_umschalter_wirkt_auf_offene_tabs(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    datei = tmp_path / "a.py"
    datei.write_text("x = 1\n", encoding="utf-8")
    editor = fenster.datei_oeffnen(datei)

    fenster.zeilenumbruch_aktion.setChecked(True)

    assert editor.lineWrapMode() == QuelltextEditor.LineWrapMode.WidgetWidth


def test_funde_landen_im_offenen_tab(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    datei = tmp_path / "a.py"
    datei.write_text("x = 1\ny = z\n", encoding="utf-8")
    editor = fenster.datei_oeffnen(datei)

    fenster._funde_in_editoren_zeigen(
        [RuffFund(datei, 2, 5, "F821", "Undefined name `z`")]
    )

    assert "nicht bekannt" in editor.fund_bei(2)
    assert len(_wellenlinien(editor)) == 1


def test_ein_spaeter_geoeffneter_tab_bekommt_seine_funde(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    """Sonst müsste man erst neu starten, um den Fehler zu sehen."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    datei = tmp_path / "a.py"
    datei.write_text("x = 1\ny = z\n", encoding="utf-8")
    fenster._funde_in_editoren_zeigen(
        [RuffFund(datei, 2, 5, "F821", "Undefined name `z`")]
    )

    editor = fenster.datei_oeffnen(datei)

    assert "nicht bekannt" in editor.fund_bei(2)


def test_zwei_funde_in_einer_zeile_stehen_untereinander(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    datei = tmp_path / "a.py"
    datei.write_text("import os, sys\n", encoding="utf-8")
    editor = fenster.datei_oeffnen(datei)

    fenster._funde_in_editoren_zeigen(
        [
            RuffFund(datei, 1, 8, "F401", "`os` imported but unused"),
            RuffFund(datei, 1, 12, "F401", "`sys` imported but unused"),
        ]
    )

    text = editor.fund_bei(1)
    assert text.count("\n") == 1
    assert "os" in text and "sys" in text


def test_eine_leere_pruefung_raeumt_die_wellenlinien_ab(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    datei = tmp_path / "a.py"
    datei.write_text("x = 1\ny = z\n", encoding="utf-8")
    editor = fenster.datei_oeffnen(datei)
    fenster._funde_in_editoren_zeigen(
        [RuffFund(datei, 2, 5, "F821", "Undefined name `z`")]
    )

    fenster._funde_in_editoren_zeigen([])

    assert _wellenlinien(editor) == []


def test_funde_einer_anderen_datei_landen_nicht_im_tab(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    datei = tmp_path / "a.py"
    datei.write_text("x = 1\n", encoding="utf-8")
    editor = fenster.datei_oeffnen(datei)

    fenster._funde_in_editoren_zeigen(
        [RuffFund(tmp_path / "b.py", 1, 1, "F821", "Undefined name `q`")]
    )

    assert _wellenlinien(editor) == []


# -- Deutsche Meldungen --------------------------------------------------


@pytest.mark.parametrize(
    ("code", "meldung", "stueck"),
    [
        (
            "F821",
            "Undefined name `zaehler`",
            "zaehler ist an dieser Stelle nicht bekannt",
        ),
        (
            "F401",
            "`os` imported but unused",
            "os wird importiert, aber nirgends benutzt",
        ),
        (
            "F841",
            "Local variable `x` is assigned to but never used",
            "x bekommt einen Wert, der nie gelesen wird",
        ),
        (
            "invalid-syntax",
            "Expected `)`, found newline",
            "Python versteht diese Zeile nicht",
        ),
    ],
)
def test_die_funde_stehen_auf_deutsch_da(
    einstellungen: QSettings, code: str, meldung: str, stueck: str
) -> None:
    """Ruff schreibt englisch. Für eine Zehntklässlerin im ersten
    Python-Jahr ist das eine zweite Hürde vor der eigentlichen."""
    fund = RuffFund(Path("main.py"), 3, 1, code, meldung)

    assert stueck in fund.was


def test_zu_jedem_fund_steht_da_was_man_tun_kann(einstellungen: QSettings) -> None:
    """Vom Nutzer gefordert: „Jede Meldung mit Lösungen.“"""
    fund = RuffFund(Path("main.py"), 3, 1, "F401", "`os` imported but unused")

    assert "import-Zeile löschen" in fund.pruefe
    assert fund.pruefe in str(fund)


def test_im_pruefungsmodus_faellt_der_loesungsteil_weg(
    einstellungen: QSettings,
) -> None:
    from ide.pruefungsmodus import starten

    starten(einstellungen)
    fund = RuffFund(Path("main.py"), 3, 1, "F401", "`os` imported but unused")

    assert fund.pruefe == ""
    assert "nirgends benutzt" in fund.was


def test_eine_unbekannte_regel_wird_durchgereicht(einstellungen: QSettings) -> None:
    """Lieber die englische Meldung als gar keine."""
    fund = RuffFund(Path("main.py"), 3, 1, "E731", "Do not assign a lambda")

    assert "Do not assign a lambda" in fund.was
