"""Der Designer bleibt mit vielen Komponenten bedienbar (Punkt 312).

Bis 0.3.6 schrieb jede einzelne Änderung `.pfm` und `_design.py`,
prüfte die `.pfm` gegen ihr Schema, ließ die Design-Prüfung laufen
und baute den Komponentenbaum neu auf. Mit 200 Komponenten kostete
eine Pfeiltaste rund eine Sekunde, zwanzigmal Rückgängig über zwanzig
Sekunden. Jeder Teil hat hier einen eigenen Test; der letzte prüft das
Ganze am Hauptfenster gegen die Grenzen aus dem Punkt.
"""

from __future__ import annotations

import json
import shutil
import statistics
import time
from pathlib import Path

import jsonschema
import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from ide import schema
from ide.designer.canvas import RASTER, DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden
from ide.designer.pfm_schreiben import formular_als_pfm_speichern
from ide.inspector.komponentenbaum import KOMPONENTE_ROLLE, Komponentenbaum
from ide.lint import regeln
from pcl import Button, Edit, Form, Label

_TYPEN = (Label, Edit, Button)


def _formular(anzahl: int) -> Form:
    """Label, Edit und Button im Wechsel, zehn je Zeile."""

    class Viele(Form):
        def create_components(self) -> None:
            self.width = 920
            self.height = 8 + (anzahl // 10 + 1) * 32
            for i in range(anzahl):
                komponente = _TYPEN[i % 3](self)
                komponente.left = 8 + (i % 10) * 90
                komponente.top = 8 + (i // 10) * 32
                komponente.width = 80
                komponente.height = 24
                setattr(self, f"k{i}", komponente)

    return Viele()


def _pfm_anlegen(qtbot, ordner: Path, anzahl: int) -> Path:  # noqa: ANN001
    formular = _formular(anzahl)
    qtbot.addWidget(formular._qwidget)
    pfm = ordner / "u_main.pfm"
    formular_als_pfm_speichern(formular, pfm)
    return pfm


def _links_in_der_pfm(pfm: Path, name: str) -> int:
    daten = json.loads(pfm.read_text(encoding="utf-8"))
    kind = next(k for k in daten["children"] if k["name"] == name)
    return kind["properties"]["left"]


def _pfeil_rechts() -> QKeyEvent:
    return QKeyEvent(
        QEvent.Type.KeyPress, Qt.Key.Key_Right, Qt.KeyboardModifier.NoModifier
    )


# -- Schema --------------------------------------------------------------


def test_das_schema_selbst_wird_nur_einmal_geprueft(monkeypatch) -> None:  # noqa: ANN001
    """`jsonschema.validate` prüfte bei jedem Aufruf auch das Schema
    gegen das Metaschema. Ein Fehler in den Daten wird weiter gemeldet."""
    eigenes = {
        "type": "object",
        "properties": {"left": {"type": "integer"}},
    }
    klasse = jsonschema.validators.validator_for(eigenes)
    original = klasse.check_schema
    aufrufe: list[int] = []

    def zaehlen(cls, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
        aufrufe.append(1)
        return original(*args, **kwargs)

    monkeypatch.setattr(klasse, "check_schema", classmethod(zaehlen))

    for _ in range(3):
        schema.pruefen({"left": 8}, eigenes)
    with pytest.raises(schema.schema_fehler()):
        schema.pruefen({"left": "acht"}, eigenes)

    assert len(aufrufe) == 1


# -- Design-Prüfung ------------------------------------------------------


def test_die_geometriepruefung_vergleicht_nicht_jede_mit_jeder(
    monkeypatch,  # noqa: ANN001
) -> None:
    """Überlappung und fast bündige Kanten wurden für jedes Paar
    geprüft, bei 200 Komponenten rund 20.000-mal. Gefunden wird
    weiterhin beides."""
    kinder = [
        {
            "name": f"k{i}",
            "type": "Button",
            "properties": {
                "left": 8 + (i % 10) * 90,
                "top": 8 + (i // 10) * 32,
                "width": 80,
                "height": 24,
            },
        }
        for i in range(200)
    ]
    # Eine Überlappung und eine um 2 Pixel verschobene Kante.
    kinder[1]["properties"]["left"] = 60
    kinder[10]["properties"]["left"] = 10
    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {"width": 920, "height": 700},
        "children": kinder,
    }
    vergleiche: list[int] = []
    rechtecke: list[int] = []
    ueberlappen = regeln._ueberlappen
    rechteck = regeln._rechteck
    monkeypatch.setattr(
        regeln, "_ueberlappen",
        lambda a, b: vergleiche.append(1) or ueberlappen(a, b),
    )
    monkeypatch.setattr(
        regeln, "_rechteck", lambda k: rechtecke.append(1) or rechteck(k)
    )

    befunde = regeln._geometrie_pruefen(pfm)

    regeln_gefunden = {(b.regel, b.komponente) for b in befunde}
    assert ("geometrie.ueberlappung", "k0") in regeln_gefunden
    assert ("geometrie.kante_nicht_buendig", "k0") in regeln_gefunden
    assert len(vergleiche) < 2_000
    assert len(rechtecke) < 10 * len(kinder)


# -- Komponentenbaum ------------------------------------------------------


def test_der_komponentenbaum_baut_nur_bei_neuer_gliederung_neu(qtbot) -> None:  # noqa: ANN001
    formular = _formular(3)
    qtbot.addWidget(formular._qwidget)
    baum = Komponentenbaum()
    qtbot.addWidget(baum)
    baum.formular_anzeigen(formular)
    marke = Qt.ItemDataRole.UserRole + 7
    baum.topLevelItem(0).child(0).setData(0, marke, "vorher")

    formular.k1.left += RASTER
    baum.auffrischen(formular.k1)

    assert baum.topLevelItem(0).child(0).data(0, marke) == "vorher"
    assert baum.currentItem().data(0, KOMPONENTE_ROLLE) is formular.k1

    formular.k3 = Button(formular)
    baum.auffrischen(formular.k3)

    wurzel = baum.topLevelItem(0)
    assert wurzel.childCount() == 4
    assert wurzel.child(0).data(0, marke) is None
    assert baum.currentItem().data(0, KOMPONENTE_ROLLE) is formular.k3


# -- Objektinspektor mit Unit (Punkt 354) ---------------------------------


def test_pfeiltaste_liest_die_unit_nicht_bei_jedem_schritt(
    qtbot, tmp_path: Path, monkeypatch  # noqa: ANN001
) -> None:
    """Der Taschenrechner mit einer Unit von gut 1.000 Zeilen. Bis
    Punkt 354 las und übersetzte der Reiter „Ereignisse“ die Unit nach
    jedem Schritt einmal je Ereignis, beim Button sechsmal; lokal
    kostete ein Schritt so rund 29 ms. Eine danach gespeicherte
    Methode erscheint beim nächsten Schritt in der Auswahl."""
    from ide.designer import laden
    from ide.inspector.objektinspektor import Objektinspektor

    quelle = Path(__file__).parents[1] / "beispielprojekte" / "03_Taschenrechner"
    for datei in quelle.iterdir():
        if datei.is_file():
            shutil.copy2(datei, tmp_path / datei.name)
    unit = tmp_path / "u_main.py"
    text = unit.read_text(encoding="utf-8") + "".join(
        f"\n    def hilfe_{i}(self, sender):\n        pass\n"
        for i in range(333)
    )
    unit.write_text(text, encoding="utf-8")

    pfm = tmp_path / "u_main.pfm"
    formular = laden.formular_fuer_designer_laden(pfm)
    qtbot.addWidget(formular._qwidget)
    canvas = DesignerCanvas(formular, pfm_pfad=pfm)
    inspektor = Objektinspektor()
    qtbot.addWidget(inspektor)
    inspektor.formular_anzeigen(formular, canvas)
    canvas.auswahl_beobachten(inspektor._eigenschaften_anzeigen)
    canvas._auswaehlen(formular.b_plus)

    gelesen = []
    original = laden.unit_lesen

    def zaehlen(pfad):  # noqa: ANN001, ANN202
        gelesen.append(pfad)
        return original(pfad)

    monkeypatch.setattr(laden, "unit_lesen", zaehlen)
    vorher = formular.b_plus.left
    zeiten = []
    for _ in range(20):
        beginn = time.perf_counter()
        canvas._tastatur_verarbeiten(_pfeil_rechts())
        qtbot.wait(0)
        zeiten.append(time.perf_counter() - beginn)

    assert formular.b_plus.left == vorher + 20 * RASTER
    assert len(gelesen) <= 1
    assert statistics.median(zeiten) < 0.033, zeiten

    tabelle = inspektor.ereignisse_tabelle
    zeile = next(
        z for z in range(tabelle.rowCount())
        if tabelle.item(z, 0).text() == "on_click"
    )

    def angeboten() -> list[str]:
        auswahl = tabelle.cellWidget(zeile, 1)
        return [auswahl.itemText(i) for i in range(auswahl.count())]

    assert "hilfe_7" in angeboten()
    unit.write_text(
        text + "\n    def neu_click(self, sender):\n        pass\n",
        encoding="utf-8",
    )
    canvas._tastatur_verarbeiten(_pfeil_rechts())
    qtbot.wait(0)

    assert "neu_click" in angeboten()
    canvas.jetzt_schreiben()


# -- Schreiben ------------------------------------------------------------


def test_eine_folge_von_aenderungen_wird_einmal_geschrieben(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    pfm = _pfm_anlegen(qtbot, tmp_path, 12)
    formular = formular_fuer_designer_laden(pfm)
    qtbot.addWidget(formular._qwidget)
    canvas = DesignerCanvas(formular, pfm_pfad=pfm)
    geschrieben: list[int] = []
    speichern = canvas.speichern

    def zaehlen() -> bool:
        geschrieben.append(1)
        return speichern()

    canvas.speichern = zaehlen
    vorher = formular.k4.left

    for _ in range(10):
        canvas.verschieben(RASTER, 0, formular.k4)

    assert geschrieben == []
    assert canvas.schreiben_ausstehend
    qtbot.waitUntil(lambda: not canvas.schreiben_ausstehend, timeout=10_000)
    assert geschrieben == [1]
    assert _links_in_der_pfm(pfm, "k4") == vorher + 10 * RASTER


@pytest.mark.parametrize(
    "anlass", ["alle_speichern", "reiter_schliessen", "fenster_schliessen"]
)
def test_eine_wartende_aenderung_geht_nicht_verloren(
    anlass: str, qtbot, tmp_path: Path, hauptfenster  # noqa: ANN001
) -> None:
    """Speichern, Starten (über `alle_speichern`) und Schließen warten
    nicht auf die Uhr des Designers, sondern schreiben sofort."""
    pfm = _pfm_anlegen(qtbot, tmp_path, 3)
    formular = hauptfenster.designer_oeffnen(pfm)
    canvas = hauptfenster._offene_canvases[0]
    vorher = formular.k1.left

    canvas.verschieben(RASTER, 0, formular.k1)
    assert canvas.schreiben_ausstehend

    if anlass == "alle_speichern":
        assert hauptfenster.alle_speichern()
    elif anlass == "reiter_schliessen":
        hauptfenster._tab_schliessen(hauptfenster.editor_tabs.currentIndex())
    else:
        assert hauptfenster.close()

    assert _links_in_der_pfm(pfm, "k1") == vorher + RASTER
    design = (tmp_path / "u_main_design.py").read_text(encoding="utf-8")
    assert f"self.k1.left = {vorher + RASTER}" in design


def test_pfeiltaste_und_rueckgaengig_mit_200_komponenten(
    qtbot, tmp_path: Path, hauptfenster  # noqa: ANN001
) -> None:
    """Die Grenzen aus Punkt 312: ein Schritt mit der Pfeiltaste unter
    0,1 s, zwanzigmal Rückgängig zusammen unter 2 s. Vorher waren es
    rund 1 s und 22 s. Die `.pfm` enthält danach den letzten Stand."""
    pfm = _pfm_anlegen(qtbot, tmp_path, 200)
    formular = hauptfenster.designer_oeffnen(pfm)
    canvas = hauptfenster._offene_canvases[0]
    canvas._auswaehlen(formular.k55)
    vorher = formular.k55.left
    qtbot.wait(10)

    zeiten = []
    for _ in range(20):
        beginn = time.perf_counter()
        canvas._tastatur_verarbeiten(_pfeil_rechts())
        qtbot.wait(0)
        zeiten.append(time.perf_counter() - beginn)

    beginn = time.perf_counter()
    for _ in range(20):
        canvas.rueckgaengig()
        qtbot.wait(0)
    rueckgaengig = time.perf_counter() - beginn

    for _ in range(3):
        canvas.wiederholen()

    assert statistics.median(zeiten) < 0.1, zeiten
    assert rueckgaengig < 2.0
    assert formular.k55.left == vorher + 3 * RASTER
    qtbot.waitUntil(lambda: not canvas.schreiben_ausstehend, timeout=10_000)
    assert _links_in_der_pfm(pfm, "k55") == vorher + 3 * RASTER
    design = (tmp_path / "u_main_design.py").read_text(encoding="utf-8")
    assert f"self.k55.left = {vorher + 3 * RASTER}" in design
