"""Tests für „Werkzeuge → Lazarus-Formular importieren …“ (Abschnitt 15).
Siehe Arbeitspaket M8, Schritt 3. Ein eigenes, minimales `.lfm`
in `tmp_path` (kein Zugriff auf `tests/daten/lfm/`, dessen echte
Dateien sind bereits in tests/test_lfm_parser.py/test_lfm_zuordnung.py
abgedeckt - hier nur die IDE-Verdrahtung).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtWidgets import QFileDialog

from ide.shell.hauptfenster import HauptFenster

_LFM_TEXT = """\
object Form1: TForm1
  Left = 100
  Top = 100
  Width = 400
  Height = 300
  Caption = 'Form1'
  OnCreate = FormCreate
  object b_start: TButton
    Left = 8
    Top = 8
    Width = 75
    Height = 24
    Caption = 'Start'
    OnClick = b_startClick
  end
  object t_x: TTrackBar
    Left = 8
    Top = 40
  end
end
"""


def _dialoge_vorbereiten(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, quelle: Path, ziel: Path
) -> None:
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(quelle), ""))
    )
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(ziel), ""))
    )


def test_import_erzeugt_gueltiges_pfm_und_oeffnet_den_designer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quelle = tmp_path / "unit1.lfm"
    quelle.write_text(_LFM_TEXT, encoding="utf-8")
    ziel = tmp_path / "u_main.pfm"
    _dialoge_vorbereiten(monkeypatch, tmp_path, quelle=quelle, ziel=ziel)
    fenster = HauptFenster()

    fenster._formular_importieren_aktion()

    assert ziel.exists()
    daten = json.loads(ziel.read_text(encoding="utf-8"))
    assert daten["children"][0]["name"] == "b_start"
    assert daten["children"][0]["events"] == {"on_click": "b_start_click"}

    assert fenster.editor_tabs.count() == 1
    formular = fenster._offene_canvases[0].formular
    assert formular.b_start.caption == "Start"


def test_import_zeigt_importbericht_fuer_nicht_unterstuetzte_komponente(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quelle = tmp_path / "unit1.lfm"
    quelle.write_text(_LFM_TEXT, encoding="utf-8")
    ziel = tmp_path / "u_main.pfm"
    _dialoge_vorbereiten(monkeypatch, tmp_path, quelle=quelle, ziel=ziel)
    fenster = HauptFenster()

    fenster._formular_importieren_aktion()

    meldungen = [
        fenster.meldungen_liste.item(i).text() for i in range(fenster.meldungen_liste.count())
    ]
    assert any("TTrackBar" in m for m in meldungen)
    assert fenster.panels.currentWidget() is fenster.meldungen_liste


def test_import_abgebrochen_bei_der_quelle_tut_nichts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
    fenster = HauptFenster()

    fenster._formular_importieren_aktion()

    assert fenster.editor_tabs.count() == 0


def test_import_abgebrochen_beim_ziel_schreibt_keine_datei(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quelle = tmp_path / "unit1.lfm"
    quelle.write_text(_LFM_TEXT, encoding="utf-8")
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(quelle), ""))
    )
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")))
    fenster = HauptFenster()

    fenster._formular_importieren_aktion()

    assert fenster.editor_tabs.count() == 0


def test_import_mit_ungueltigem_lfm_zeigt_fehlermeldung(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quelle = tmp_path / "kaputt.lfm"
    quelle.write_text("das ist kein lfm", encoding="utf-8")
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: (str(quelle), ""))
    )
    fenster = HauptFenster()

    fenster._formular_importieren_aktion()

    assert "fehlgeschlagen" in fenster.statusBar().currentMessage()
    assert fenster.editor_tabs.count() == 0


# -- Pascal-Rümpfe und Bilder aus Picture.Data (M8, Schritt 3) --------------

_REFERENZ = Path(__file__).resolve().parent / "daten" / "lfm"

_PAS_TEXT = """\
unit unit1;

interface

implementation

procedure TForm1.FormCreate(Sender: TObject);
begin
  Caption := 'Start';
end;

procedure TForm1.b_startClick(Sender: TObject);
begin
  ShowMessage('los');
end;

end.
"""


def test_import_uebernimmt_pascal_ruempfe_als_kommentar_in_die_unit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quelle = tmp_path / "unit1.lfm"
    quelle.write_text(_LFM_TEXT, encoding="utf-8")
    (tmp_path / "unit1.pas").write_text(_PAS_TEXT, encoding="utf-8")
    ziel = tmp_path / "u_main.pfm"
    _dialoge_vorbereiten(monkeypatch, tmp_path, quelle=quelle, ziel=ziel)
    fenster = HauptFenster()

    fenster._formular_importieren_aktion()

    unit = tmp_path / "u_main.py"
    assert unit.exists()
    quelltext = unit.read_text(encoding="utf-8")
    assert "class Form1(Form1Design):" in quelltext
    assert "def b_start_click(self, sender):" in quelltext
    assert "# Pascal-Rumpf von b_startClick aus unit1.pas," in quelltext
    assert "#   ShowMessage('los');" in quelltext
    assert "def form_create(self, sender):" in quelltext
    assert "#   Caption := 'Start';" in quelltext
    # gültiges Python, nicht nur Text
    compile(quelltext, str(unit), "exec")


def test_import_ohne_pas_datei_meldet_das_und_legt_leere_methoden_an(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quelle = tmp_path / "unit1.lfm"
    quelle.write_text(_LFM_TEXT, encoding="utf-8")
    ziel = tmp_path / "u_main.pfm"
    _dialoge_vorbereiten(monkeypatch, tmp_path, quelle=quelle, ziel=ziel)
    fenster = HauptFenster()

    fenster._formular_importieren_aktion()

    meldungen = [
        fenster.meldungen_liste.item(i).text() for i in range(fenster.meldungen_liste.count())
    ]
    assert any("unit1.pas nicht gefunden" in m for m in meldungen)
    quelltext = (tmp_path / "u_main.py").read_text(encoding="utf-8")
    assert "def b_start_click(self, sender):" in quelltext
    assert "Pascal-Rumpf" not in quelltext


def test_import_ueberschreibt_vorhandene_unit_nicht(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    quelle = tmp_path / "unit1.lfm"
    quelle.write_text(_LFM_TEXT, encoding="utf-8")
    (tmp_path / "unit1.pas").write_text(_PAS_TEXT, encoding="utf-8")
    ziel = tmp_path / "u_main.pfm"
    unit = tmp_path / "u_main.py"
    unit.write_text("# eigener Code\n", encoding="utf-8")
    _dialoge_vorbereiten(monkeypatch, tmp_path, quelle=quelle, ziel=ziel)
    fenster = HauptFenster()

    fenster._formular_importieren_aktion()

    assert unit.read_text(encoding="utf-8") == "# eigener Code\n"
    meldungen = [
        fenster.meldungen_liste.item(i).text() for i in range(fenster.meldungen_liste.count())
    ]
    assert any("nicht überschrieben" in m for m in meldungen)


def test_import_schreibt_bilder_aus_picture_data_nach_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Gegen eine echte Lazarus-Datei aus `tests/daten/lfm/`: erst
    in `tmp_path` kopieren (AGENTS.md - eingecheckte Dateien nie im
    Test verändern), dann importieren."""
    quelle = tmp_path / "u_quelle.lfm"
    quelle.write_bytes((_REFERENZ / "l_Pet" / "u_main.lfm").read_bytes())
    (tmp_path / "u_quelle.pas").write_bytes((_REFERENZ / "l_Pet" / "u_main.pas").read_bytes())
    ziel = tmp_path / "u_main.pfm"
    _dialoge_vorbereiten(monkeypatch, tmp_path, quelle=quelle, ziel=ziel)
    fenster = HauptFenster()

    fenster._formular_importieren_aktion()

    bild = tmp_path / "assets" / "Image1.png"
    assert bild.exists()
    assert bild.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    # Geprüft wird, dass eine vollständige PNG-Datei herauskommt -
    # die Größe der Vorlage ist dafür ohne Belang (M14).
    assert b"IEND" in bild.read_bytes()

    quelltext = (tmp_path / "u_main.py").read_text(encoding="utf-8")
    assert 'self.Image1.picture.load_from_file("assets/Image1.png")' in quelltext
    assert "#   meinPet.nameaendern(e_name.text);" in quelltext
    compile(quelltext, "u_main.py", "exec")

    meldungen = [
        fenster.meldungen_liste.item(i).text() for i in range(fenster.meldungen_liste.count())
    ]
    assert any("assets/Image1.png" in m for m in meldungen)
