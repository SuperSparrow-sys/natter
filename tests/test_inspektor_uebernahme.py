"""Tests dafür, dass eine im Objektinspektor geänderte Eigenschaft
tatsächlich in der `.pfm` und im generierten Code landet.

Real gefunden beim Fertigstellen von M8: der Objektinspektor setzte den
Wert nur am Live-Objekt. Designer-Anzeige und Qt-Widget stimmten sofort -
ein Screenshot sah also völlig richtig aus -, aber `.pfm` und
`u_*_design.py` blieben unverändert. Jede allein über den Inspektor
gesetzte Eigenschaft war nach dem nächsten Öffnen wieder weg und
erreichte das laufende Schülerprogramm nie. Siehe
Arbeitspaket M8, Schritt 6.
"""

import json
import shutil
from pathlib import Path

from ide.designer.canvas import DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden
from ide.inspector import Objektinspektor

_AMPEL = Path(__file__).resolve().parent.parent / "beispielprojekte" / "04_CookieKlicker"


def _designer_oeffnen(tmp_path: Path):
    ziel = tmp_path / "04_CookieKlicker"
    shutil.copytree(_AMPEL, ziel)
    pfm_pfad = ziel / "u_main.pfm"
    formular = formular_fuer_designer_laden(pfm_pfad)
    canvas = DesignerCanvas(formular, pfm_pfad=pfm_pfad)
    inspektor = Objektinspektor()
    inspektor.formular_anzeigen(formular, canvas)
    return formular, canvas, inspektor, ziel


def _zeile(tabelle, name: str) -> int:
    return next(z for z in range(tabelle.rowCount()) if tabelle.item(z, 0).text() == name)


def test_eigenschaft_aus_dem_inspektor_landet_in_pfm_und_code(tmp_path: Path) -> None:
    formular, _canvas, inspektor, ordner = _designer_oeffnen(tmp_path)
    inspektor._eigenschaften_anzeigen(formular.l_titel)
    tabelle = inspektor.eigenschaften_tabelle

    tabelle.item(_zeile(tabelle, "caption"), 1).setText("Neue Überschrift")

    pfm = json.loads((ordner / "u_main.pfm").read_text(encoding="utf-8"))
    titel = next(k for k in pfm["children"] if k["name"] == "l_titel")
    assert titel["properties"]["caption"] == "Neue Überschrift"
    assert "Neue Überschrift" in (ordner / "u_main_design.py").read_text(encoding="utf-8")


def test_inspektor_aenderung_laesst_sich_rueckgaengig_machen(tmp_path: Path) -> None:
    formular, canvas, inspektor, ordner = _designer_oeffnen(tmp_path)
    inspektor._eigenschaften_anzeigen(formular.l_titel)
    tabelle = inspektor.eigenschaften_tabelle
    vorher = formular.l_titel.caption

    tabelle.item(_zeile(tabelle, "caption"), 1).setText("Zwischenstand")
    canvas.rueckgaengig()

    assert formular.l_titel.caption == vorher
    pfm = json.loads((ordner / "u_main.pfm").read_text(encoding="utf-8"))
    titel = next(k for k in pfm["children"] if k["name"] == "l_titel")
    assert titel["properties"].get("caption", vorher) == vorher


def test_verschachtelte_schrift_aus_dem_inspektor_landet_in_der_pfm(tmp_path: Path) -> None:
    formular, _canvas, inspektor, ordner = _designer_oeffnen(tmp_path)
    inspektor._eigenschaften_anzeigen(formular.l_titel)
    tabelle = inspektor.eigenschaften_tabelle

    tabelle.item(_zeile(tabelle, "font_size"), 1).setText("18")

    pfm = json.loads((ordner / "u_main.pfm").read_text(encoding="utf-8"))
    titel = next(k for k in pfm["children"] if k["name"] == "l_titel")
    assert titel["properties"]["font_size"] == 18
    assert formular.l_titel.font.size == 18


def test_sammlung_wird_im_inspektor_als_eigene_zeile_gezeigt(tmp_path: Path) -> None:
    """`items`/`lines` sind keine `Prop`s und fehlten deshalb komplett im
    Objektinspektor - genau wie `brush.color` es einmal tat."""
    from pcl import ComboBox, Form

    class Formular(Form):
        def create_components(self):
            self.cb = ComboBox(self)

    formular = Formular()
    formular.cb.items = ["7", "19"]
    inspektor = Objektinspektor()
    inspektor.formular_anzeigen(formular)
    inspektor._eigenschaften_anzeigen(formular.cb)
    tabelle = inspektor.eigenschaften_tabelle

    assert tabelle.item(_zeile(tabelle, "items"), 1).text() == "(2 Einträge)"
