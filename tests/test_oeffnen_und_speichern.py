"""Öffnen und Speichern: ein Weg, und Fehler als Meldung (M11, 5).

Der Projekt-Explorer sah sich die Endung an und öffnete eine `.pfm` im
Designer, ein `.pdiag` im Diagramm-Editor, ein Bild in der Vorschau.
„Datei → Öffnen …“ tat das nicht: dort landete dieselbe `.pfm` als roher
JSON-Text im Quelltexteditor, das Diagramm ebenso – und ein PNG brachte
Natter mit einem `UnicodeDecodeError` ganz zum Absturz, weil niemand
damit rechnete, dass jemand ein Bild „öffnet“.

Zwei Wege zur selben Sache, die sich verschieden verhalten, sind
schlimmer als einer. Beide gehen jetzt durch `HauptFenster.oeffnen()`.

Dazu das, was beim Durchgehen derselben Frage noch auffiel: ein Projekt,
dessen `.natter`-Datei fehlt oder beschädigt ist, flog als
`FileNotFoundError` bzw. `JSONDecodeError` aus einem Qt-Signal heraus –
und ein gescheitertes Speichern ebenso. Das ist der schlimmste Fall
von allen: der Text steht noch im Fenster, die Datei auf der Platte ist
die alte, und in der gebauten Exe ohne Konsole sah man gar nichts.
"""

from __future__ import annotations

import json
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


@pytest.fixture
def fenster(einstellungen: QSettings, qtbot) -> HauptFenster:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    return fenster


def _formular_anlegen(ordner: Path) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    pfm = ordner / "u_haupt.pfm"
    pfm.write_text(
        json.dumps(
            {
                "format": "pfm/1",
                "class": "Form1",
                "type": "Form",
                "properties": {},
                "children": [
                    {"name": "b_ein", "type": "Button", "properties": {"left": 8, "top": 8}}
                ],
            }
        ),
        encoding="utf-8",
    )
    return pfm


def test_oeffnen_zeigt_ein_formular_im_designer(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Über „Datei → Öffnen …“ stand hier vorher das rohe JSON."""
    pfm = _formular_anlegen(tmp_path / "p")

    fenster.oeffnen(pfm)

    assert fenster.editor_tabs.tabText(0) == "u_haupt (Designer)"
    assert fenster._aktueller_canvas is not None


def test_oeffnen_zeigt_ein_bild_in_der_vorschau(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Ein PNG im Quelltexteditor war nicht nur unsinnig, sondern ein
    Absturz: `read_text` scheitert an den Binärdaten."""
    from PySide6.QtGui import QImage

    bild = tmp_path / "logo.png"
    QImage(4, 4, QImage.Format.Format_RGB32).save(str(bild), "PNG")

    fenster.oeffnen(bild)

    assert fenster.editor_tabs.count() == 1
    assert fenster.editor_tabs.tabText(0) == "logo.png"


def test_der_dialog_und_der_explorer_gehen_denselben_weg(
    fenster: HauptFenster, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der eigentliche Punkt: „Datei → Öffnen …“ ruft dieselbe Stelle
    wie ein Doppelklick im Projekt-Explorer."""
    from PySide6.QtWidgets import QFileDialog

    pfm = _formular_anlegen(tmp_path / "p")
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", lambda *_a, **_k: (str(pfm), "")
    )

    fenster._datei_oeffnen_dialog()

    assert fenster.editor_tabs.tabText(0) == "u_haupt (Designer)"


def test_eine_nicht_lesbare_datei_meldet_sich_statt_abzustuerzen(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Eine alte, nicht in UTF-8 gespeicherte Pascal-Datei oder eine
    `.exe` – vorher flog der `UnicodeDecodeError` bis nach oben durch."""
    datei = tmp_path / "alt.pas"
    datei.write_bytes(b"program Gru\xdf;\n")  # ISO-8859-1, kein UTF-8

    ergebnis = fenster.datei_oeffnen(datei)

    assert ergebnis is None
    assert fenster.editor_tabs.count() == 0
    meldung = fenster.statusBar().currentMessage()
    assert "alt.pas" in meldung
    assert "UTF-8" in meldung


def test_eine_gewoehnliche_unit_geht_weiter_in_den_editor(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    datei = tmp_path / "u_hilfe.py"
    datei.write_text("x = 1\n", encoding="utf-8")

    fenster.oeffnen(datei)

    assert fenster.editor_tabs.tabText(0) == "u_hilfe.py"


def test_ein_beschaedigtes_formular_meldet_sich_statt_abzustuerzen(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Eine von Hand verbogene oder abgeschnittene `.pfm` flog vorher
    als `JSONDecodeError` bis nach oben durch – in der gebauten Exe
    hieße das: Natter ist weg."""
    kaputt = tmp_path / "u_kaputt.pfm"
    kaputt.write_text('{"format": "pfm/1", "class": "Form1",', encoding="utf-8")

    fenster.oeffnen(kaputt)

    assert fenster.editor_tabs.count() == 0
    meldung = fenster.statusBar().currentMessage()
    assert "u_kaputt.pfm" in meldung
    assert "beschädigt" in meldung


def test_ein_formular_mit_falschem_inhalt_meldet_sich_auch(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Gueltiges JSON, aber nicht das, was eine `.pfm` sein muss – das
    fängt das Schema ab."""
    kaputt = tmp_path / "u_falsch.pfm"
    kaputt.write_text('{"format": "pfm/1", "children": "keine Liste"}', encoding="utf-8")

    fenster.oeffnen(kaputt)

    assert fenster.editor_tabs.count() == 0
    assert "beschädigt" in fenster.statusBar().currentMessage()


def test_ein_beschaedigtes_diagramm_meldet_sich_ebenfalls(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    kaputt = tmp_path / "ablauf.pdiag"
    kaputt.write_text("{kein json", encoding="utf-8")

    fenster.oeffnen(kaputt)

    assert "beschädigt" in fenster.statusBar().currentMessage()


# -- Projekte ------------------------------------------------------------


def _meldungen_abfangen(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Die Warnung als Text statt als Fenster, auf das niemand klickt."""
    from PySide6.QtWidgets import QMessageBox

    gezeigt: list[str] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda _eltern, _titel, text, *_rest: gezeigt.append(text),
    )
    return gezeigt


def test_ein_beschaedigtes_projekt_meldet_sich_statt_abzustuerzen(
    fenster: HauptFenster, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Eine `.natter`-Datei, die jemand in einem Editor offen hatte – der
    `JSONDecodeError` flog vorher aus einem Qt-Signal heraus."""
    gezeigt = _meldungen_abfangen(monkeypatch)
    kaputt = tmp_path / "kaputt.natter"
    kaputt.write_text('{"format": "natter-project/1",', encoding="utf-8")

    assert fenster.projekt_oeffnen_gemeldet(kaputt) is None
    assert fenster.projekt is None
    assert "beschädigt" in gezeigt[0]


def test_ein_verschwundenes_projekt_nennt_den_wahrscheinlichen_grund(
    fenster: HauptFenster, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der häufigste Fall im Unterricht: der Stick steckt nicht mehr."""
    gezeigt = _meldungen_abfangen(monkeypatch)

    assert fenster.projekt_oeffnen_gemeldet(tmp_path / "weg.natter") is None
    assert "USB-Stick" in gezeigt[0]


def test_ein_gutes_projekt_geht_weiterhin_auf(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    ordner = tmp_path / "p"
    ordner.mkdir()
    (ordner / "main.py").write_text("x = 1" + chr(10), encoding="utf-8")
    (ordner / "gut.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Gut",
                "type": "console",
                "main": "main.py",
            }
        ),
        encoding="utf-8",
    )

    projekt = fenster.projekt_oeffnen_gemeldet(ordner / "gut.natter")

    assert projekt is not None
    assert projekt.name == "Gut"


# -- Speichern -----------------------------------------------------------


def test_ein_gescheitertes_speichern_meldet_sich_und_behaelt_den_text(
    fenster: HauptFenster, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Der schlimmste Fall von allen: der Text steht im Fenster, die
    Datei auf der Platte ist die alte – und vorher flog nur ein
    Traceback, in der gebauten Exe also gar nichts."""
    gezeigt = _meldungen_abfangen(monkeypatch)
    datei = tmp_path / "u_arbeit.py"
    datei.write_text("alt" + chr(10), encoding="utf-8")
    editor = fenster.datei_oeffnen(datei)
    # Wie von Hand getippt: `setPlainText` gilt Qt als Laden und setzt
    # die Änderungsmarke gerade zurück.
    editor.selectAll()
    editor.insertPlainText("neu" + chr(10))

    def _verweigern(*_a, **_k):
        raise OSError("Der Datenträger ist schreibgeschützt")

    monkeypatch.setattr(Path, "write_text", _verweigern)

    fenster._aktuelle_datei_speichern()

    assert gezeigt, "Es kam keine Meldung."
    assert "u_arbeit.py" in gezeigt[0]
    assert "schreibgeschützt" in gezeigt[0]
    # Der Tab bleibt als geändert markiert - sonst glaubte man, es sei
    # gespeichert.
    assert editor.document().isModified() is True
    assert editor.toPlainText() == "neu" + chr(10)


def test_ein_gelungenes_speichern_raeumt_die_aenderungsmarke_weg(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    datei = tmp_path / "u_arbeit.py"
    datei.write_text("alt" + chr(10), encoding="utf-8")
    editor = fenster.datei_oeffnen(datei)
    editor.selectAll()
    editor.insertPlainText("neu" + chr(10))

    fenster._aktuelle_datei_speichern()

    assert datei.read_text(encoding="utf-8") == "neu" + chr(10)
    assert editor.document().isModified() is False


def test_auch_der_testprotokoll_export_meldet_sich(
    fenster: HauptFenster, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Alles, was Natter auf Wunsch auf die Platte schreibt, geht durch
    dieselbe Stelle – sonst hätte jede ihre eigene (oder gar keine)
    Behandlung."""
    from PySide6.QtWidgets import QFileDialog

    from ide.testrunner.ausfuehrung import Testergebnis

    gezeigt = _meldungen_abfangen(monkeypatch)
    fenster._letzte_testergebnisse = [
        Testergebnis(id="t.T.test_eins", status="bestanden", dauer=0.1, nachricht="")
    ]
    ziel = tmp_path / "protokoll.html"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", lambda *_a, **_k: (str(ziel), "")
    )
    monkeypatch.setattr(
        Path, "write_text", lambda *_a, **_k: (_ for _ in ()).throw(OSError("voll"))
    )

    fenster._testergebnisse_exportieren_aktion()

    assert gezeigt, "Es kam keine Meldung."
    assert "protokoll.html" in gezeigt[0]
    assert "voll" in gezeigt[0]


def test_der_hinweis_nennt_die_haeufigen_gruende(
    fenster: HauptFenster, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gezeigt = _meldungen_abfangen(monkeypatch)
    monkeypatch.setattr(
        Path, "write_text", lambda *_a, **_k: (_ for _ in ()).throw(OSError("nein"))
    )

    geklappt = fenster.datei_schreiben_gemeldet(tmp_path / "x.txt", "inhalt")

    assert geklappt is False
    assert "USB-Stick" in gezeigt[0]
    assert "schreibgeschützt" in gezeigt[0]


# -- Rueckgaengig ---------------------------------------------------------


def test_das_menue_macht_auch_im_designer_rueckgaengig(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Der Designer hörte auf Strg+Z, solange die Zeichenfläche den
    Fokus hatte – der Menüeintrag daneben tat in einem Designer-Tab
    gar nichts, weil er einen Texteditor suchte und keinen fand."""
    fenster.oeffnen(_formular_anlegen(tmp_path / "p"))
    canvas = fenster._aktueller_canvas
    knopf = canvas.formular.b_ein
    vorher = knopf.left
    canvas.verschieben(16, 0, knopf)
    assert knopf.left == vorher + 16

    fenster._bearbeiten_rueckgaengig()

    assert knopf.left == vorher


def test_das_menue_wiederholt_auch_im_designer(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    fenster.oeffnen(_formular_anlegen(tmp_path / "p"))
    canvas = fenster._aktueller_canvas
    knopf = canvas.formular.b_ein
    vorher = knopf.left
    canvas.verschieben(16, 0, knopf)
    fenster._bearbeiten_rueckgaengig()
    assert knopf.left == vorher  # sonst prüft das Wiederholen unten nichts

    fenster._bearbeiten_wiederholen()

    assert knopf.left == vorher + 16


def test_im_editor_bleibt_rueckgaengig_beim_text(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Der Fall, der vorher schon ging, muss weiter gehen."""
    datei = tmp_path / "u_hilfe.py"
    datei.write_text("alt" + chr(10), encoding="utf-8")
    editor = fenster.datei_oeffnen(datei)
    editor.selectAll()
    editor.insertPlainText("neu" + chr(10))

    fenster._bearbeiten_rueckgaengig()

    assert "alt" in editor.toPlainText()
