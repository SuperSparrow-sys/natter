"""Eine `.pfm` wird nur als Daten gelesen (Punkt 226).

Aus der `.pfm` entsteht Python-Quelltext, den der Designer im Prozess
der IDE ausführt. Steht in der Datei an der Stelle eines Namens eine
Anweisung, darf sie weder beim Öffnen im Designer noch beim Import
einer `.lfm` noch beim Einfügen aus der Zwischenablage laufen. Jeder
Fall legt dafür eine Anweisung ab, die eine Markierungsdatei
anlegen würde, und prüft, dass die Datei nicht entsteht und eine
Meldung erscheint.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData
from PySide6.QtWidgets import QApplication, QFileDialog

from ide.codegen.design import PfmBeschaedigt, design_code_erzeugen
from ide.designer import DesignerCanvas, formular_fuer_designer_laden
from ide.designer.canvas import ZWISCHENABLAGE_TYP
from ide.import_lfm import lfm_zu_pfm, parse_lfm


def _anweisung(marker: Path) -> str:
    return f"open(r'{marker}', 'w').close()"


def _pfm(marker: Path, stelle: str) -> dict:
    """Ein Formular mit einem Knopf, an `stelle` eine Anweisung statt
    eines Namens."""
    anweisung = _anweisung(marker)
    knopf: dict = {
        "name": "b_ok",
        "type": "Button",
        "properties": {"caption": "OK"},
        "events": {"on_click": "b_ok_click"},
    }
    if stelle == "methode":
        knopf["events"] = {"on_click": f"__init__; {anweisung}"}
    elif stelle == "eigenschaft":
        knopf["properties"] = {
            f"caption = 'a'; {anweisung}; self.b_ok.caption": "OK"
        }
    elif stelle == "komponente":
        knopf["name"] = f"b = None; {anweisung}; b_ok"
    elif stelle == "typ":
        knopf["type"] = f"Button; {anweisung}; from pcl import Label"
    return {
        "format": "pfm/1",
        "class": "TMain",
        "type": "Form",
        "properties": {"caption": "Probe"},
        "children": [knopf],
    }


_STELLEN = ["methode", "eigenschaft", "komponente", "typ"]


@pytest.mark.parametrize("stelle", _STELLEN)
def test_designer_fuehrt_nichts_aus_der_pfm_aus(
    tmp_path: Path, stelle: str
) -> None:
    marker = tmp_path / "ausgefuehrt.txt"
    pfm_pfad = tmp_path / "u_main.pfm"
    pfm_pfad.write_text(
        json.dumps(_pfm(marker, stelle)), encoding="utf-8"
    )

    with pytest.raises(PfmBeschaedigt) as fehler:
        formular_fuer_designer_laden(pfm_pfad)

    assert not marker.exists()
    assert "zulässiger Name" in str(fehler.value) or (
        "keine bekannte Komponente" in str(fehler.value)
    )


def test_beschriftung_mit_zeilenumbruch_laesst_sich_laden(
    tmp_path: Path,
) -> None:
    pfm = _pfm(tmp_path / "unbenutzt.txt", "keine")
    pfm["children"][0]["properties"]["caption"] = 'Zeile 1\nZeile "2"\\'
    pfm_pfad = tmp_path / "u_main.pfm"
    pfm_pfad.write_text(json.dumps(pfm), encoding="utf-8")

    formular = formular_fuer_designer_laden(pfm_pfad)

    assert formular.b_ok.caption == 'Zeile 1\nZeile "2"\\'
    # Der erzeugte Quelltext bleibt eine Zeile je Zuweisung.
    quelltext = design_code_erzeugen(pfm, "u_main.pfm")
    assert 'caption = "Zeile 1\\nZeile \\"2\\"\\\\"' in quelltext


def test_oeffnen_meldet_eine_beschaedigte_pfm(
    tmp_path: Path, hauptfenster
) -> None:
    marker = tmp_path / "ausgefuehrt.txt"
    pfm_pfad = tmp_path / "u_main.pfm"
    pfm_pfad.write_text(
        json.dumps(_pfm(marker, "methode")), encoding="utf-8"
    )

    hauptfenster.oeffnen(pfm_pfad)

    assert not marker.exists()
    meldung = hauptfenster.statusBar().currentMessage()
    assert "lässt sich nicht öffnen" in meldung
    assert "beschädigt" in meldung
    assert hauptfenster.editor_tabs.count() == 0


_LFM = """\
object TMain: TForm1
  Caption = 'Probe'
  object b_ok: TButton
    Left = 8
    Top = 8
    Caption = 'OK'
    OnClick = __init__; open('ausgefuehrt.txt', 'w').close(); self.bClick
  end
end
"""


def test_lfm_import_uebernimmt_keinen_methodennamen_mit_anweisung() -> None:
    ergebnis = lfm_zu_pfm(parse_lfm(_LFM))

    assert "events" not in ergebnis.pfm["children"][0]
    assert any("gültigen Methodennamen" in w for w in ergebnis.warnungen)


def test_lfm_import_im_hauptfenster_fuehrt_nichts_aus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:
    # Die Markierungsdatei steht relativ im Arbeitsordner: der Import
    # setzt Methodennamen in Kleinbuchstaben um, ein absoluter Pfad
    # käme verändert an.
    monkeypatch.chdir(tmp_path)
    quelle = tmp_path / "unit1.lfm"
    quelle.write_text(_LFM, encoding="utf-8")
    ziel = tmp_path / "u_main.pfm"
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName",
        staticmethod(lambda *a, **k: (str(quelle), "")),
    )
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *a, **k: (str(ziel), "")),
    )

    hauptfenster._formular_importieren_aktion()

    assert not (tmp_path / "ausgefuehrt.txt").exists()
    meldungen = [
        hauptfenster.meldungen_liste.item(i).text()
        for i in range(hauptfenster.meldungen_liste.count())
    ]
    assert any("gültigen Methodennamen" in m for m in meldungen)
    assert "open(" not in (tmp_path / "u_main.py").read_text(
        encoding="utf-8"
    )


@pytest.mark.parametrize("stelle", ["eigenschaft", "komponente", "typ"])
def test_einfuegen_aus_der_zwischenablage_fuehrt_nichts_aus(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stelle: str  # noqa: ANN001
) -> None:
    pfm_pfad = tmp_path / "u_main.pfm"
    pfm_pfad.write_text(
        json.dumps(_pfm(tmp_path / "unbenutzt.txt", "keine")),
        encoding="utf-8",
    )
    formular = formular_fuer_designer_laden(pfm_pfad)
    qtbot.addWidget(formular._qwidget)
    canvas = DesignerCanvas(formular, pfm_pfad=pfm_pfad)
    meldungen: list[str] = []
    monkeypatch.setattr(canvas, "_meldung_zeigen", meldungen.append)

    marker = tmp_path / "ausgefuehrt.txt"
    daten = QMimeData()
    daten.setData(
        ZWISCHENABLAGE_TYP,
        json.dumps(_pfm(marker, stelle)["children"]).encode("utf-8"),
    )
    QApplication.clipboard().setMimeData(daten)

    assert canvas.einfuegen() == []
    assert not marker.exists()
    assert meldungen and "Zwischenablage ist beschädigt" in meldungen[0]


@pytest.mark.parametrize(
    ("stelle", "eigenschaften", "erwartet"),
    [
        ("formular", {"width": 400.5}, "width"),
        ("knopf", {"caption": 5}, "caption"),
        ("knopf", {"foo": 1}, "neueren Fassung"),
        ("formular", {"width": 10**30}, "zu groß"),
    ],
)
def test_falscher_wert_oder_unbekannte_eigenschaft_heisst_beschaedigt(
    tmp_path: Path, stelle: str, eigenschaften: dict, erwartet: str
) -> None:
    """Werte prüft erst das Bauen des Formulars. Ein falscher Typ oder
    eine Eigenschaft aus einer neueren Fassung flog vorher als
    `NatterPropertyError`, `NatterUnbekannteEigenschaftError` oder
    `OverflowError` bis in die allgemeine Fehlermeldung durch."""
    knopf = {"name": "b_ok", "type": "Button", "properties": {"caption": "OK"}}
    formular = {"width": 400, "height": 300}
    (formular if stelle == "formular" else knopf["properties"]).update(eigenschaften)
    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": formular,
        "children": [knopf],
    }
    pfad = tmp_path / "u_main.pfm"
    pfad.write_text(json.dumps(pfm), encoding="utf-8")

    with pytest.raises(PfmBeschaedigt, match=erwartet):
        formular_fuer_designer_laden(pfad)


def _bild_pfm(formular: dict, bild: str, bildkomponente: dict) -> dict:
    return {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": formular,
        "children": [
            {
                "name": "i_bild",
                "type": "Image",
                "properties": {"picture": bild, **bildkomponente},
            }
        ],
    }


@pytest.mark.parametrize(
    ("formular", "bildkomponente"),
    [
        ({"_projektordner": None}, {}),
        ({"_projektordner": "AUSSEN"}, {}),
        ({}, {"_qwidget": 1}),
    ],
)
def test_pfm_setzt_keine_internen_attribute(
    qapp, tmp_path: Path, formular: dict, bildkomponente: dict
) -> None:
    """Ein Name mit `_` am Anfang unter `properties` überschrieb im
    erzeugten Code die Interna des Designers; mit `_projektordner`
    lud er danach Bilder von jedem Pfad (Punkt 669). Ohne die Angabe
    bleibt ein Bild außerhalb des Projektordners weiter ungeladen."""
    from PySide6.QtGui import QColor, QImage

    projekt = tmp_path / "projekt"
    aussen = tmp_path / "aussen"
    projekt.mkdir()
    aussen.mkdir()
    bild = QImage(8, 8, QImage.Format.Format_RGB32)
    bild.fill(QColor("red"))
    bild.save(str(aussen / "bild.png"))
    fremd = str(aussen / "bild.png")
    formular = {
        name: str(aussen) if wert == "AUSSEN" else wert
        for name, wert in formular.items()
    }

    ohne = projekt / "u_ohne.pfm"
    ohne.write_text(json.dumps(_bild_pfm({}, fremd, {})), encoding="utf-8")
    assert formular_fuer_designer_laden(ohne).i_bild.picture.original.isNull()

    mit = projekt / "u_mit.pfm"
    mit.write_text(
        json.dumps(_bild_pfm(formular, fremd, bildkomponente)),
        encoding="utf-8",
    )
    with pytest.raises(PfmBeschaedigt, match="in einer .pfm stehen darf"):
        formular_fuer_designer_laden(mit)


def _tief(ebenen: int) -> object:
    wert: object = "x"
    for _ in range(ebenen):
        wert = [wert]
    return wert


def _mit_kind(kind: dict) -> str:
    return json.dumps(
        {
            "format": "pfm/1",
            "class": "Form1",
            "type": "Form",
            "properties": {},
            "children": [kind],
        }
    )


def test_falscher_grundaufbau_oder_wert_heisst_beschaedigt(
    tmp_path: Path, hauptfenster
) -> None:
    """Grundaufbau (Punkt 681) und Werte, die das Schema durchlässt,
    aus denen aber kein gültiger Formular-Code entsteht (Punkt 671):
    beides endete in der Absturzmeldung statt in „beschädigt“."""
    faelle = {
        "liste": "[]",
        "zahl": "7",
        "properties_zahl": json.dumps(
            {"format": "pfm/1", "class": "Form1", "type": "Form",
             "properties": 7}
        ),
        "children_zahl": json.dumps(
            {"format": "pfm/1", "class": "Form1", "type": "Form",
             "properties": {}, "children": 0.5}
        ),
        "nan": _mit_kind(
            {"name": "lb", "type": "Label",
             "properties": {"top": float("nan")}}
        ),
        "unendlich": _mit_kind(
            {"name": "lb", "type": "Label",
             "properties": {"left": float("-inf")}}
        ),
        "menue_children_zahl": _mit_kind(
            {"name": "mm", "type": "MainMenu", "properties": {
                "entries": [{"caption": "a", "children": 5}]}}
        ),
        "tiefer_wert": _mit_kind(
            {"name": "lb", "type": "ListBox",
             "properties": {"items": _tief(500)}}
        ),
    }
    for fall, inhalt in faelle.items():
        datei = tmp_path / f"u_{fall}.pfm"
        datei.write_text(inhalt, encoding="utf-8")
        hauptfenster.statusBar().clearMessage()
        hauptfenster.oeffnen(datei)
        meldung = hauptfenster.statusBar().currentMessage()
        assert "beschädigt" in meldung, fall


@pytest.mark.parametrize("zahl", [float("nan"), float("inf"), float("-inf")])
def test_keine_endliche_zahl_ergibt_keinen_quelltext(zahl: float) -> None:
    """`NaN` stand im erzeugten Code als Name `nan` statt als Literal
    (Punkt 671)."""
    pfm = json.loads(
        _mit_kind({"name": "lb", "type": "Label",
                   "properties": {"top": zahl}})
    )
    with pytest.raises(PfmBeschaedigt, match="keine zulässige Zahl"):
        design_code_erzeugen(pfm, "u_main.pfm")


def test_untermenue_ohne_beschriftung_ergibt_gueltigen_code(
    qapp, tmp_path: Path
) -> None:
    """Der Menü-Editor schreibt ein Untermenü mit leerer Beschriftung
    als `{"children": [...]}`. Daraus entstand `{, "children": [`
    (Punkt 671); die Datei stammt aber von Natter und ist nicht
    beschädigt."""
    pfad = tmp_path / "u_main.pfm"
    pfad.write_text(
        _mit_kind(
            {"name": "mm", "type": "MainMenu", "properties": {
                "entries": [{"children": [{"caption": "x"}]}]}}
        ),
        encoding="utf-8",
    )
    formular = formular_fuer_designer_laden(pfad)
    assert formular.mm.entries[0]["children"][0]["caption"] == "x"
