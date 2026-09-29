"""Lineale, Hilfslinien und Minimap (M9, Teilschritt 2b; M15,
Abschnitt 5).

Das waren die drei letzten ausgegrauten Einträge im Menü „Ansicht" des
Diagramm-Fensters - Zoom, Raster, Seitenränder und Layout-Hinweise
waren längst aktiv.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QSize, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

from ide.diagramm.datei import Diagramm
from ide.diagramm.fenster import DiagrammFenster
from ide.diagramm.lineale import (
    LINEALBREITE,
    Lineal,
    hilfslinien_lesen,
    mm_in_pixel,
    pixel_in_mm,
)
from ide.diagramm.minimap import Minimap, abbild_erzeugen

_AM_LEBEN: list[object] = []


def _diagramm(tmp_path: Path, typ: str = "class") -> Diagramm:
    """Ein kleines Diagramm in `tmp_path` - nie gegen eine eingecheckte
    `.pdiag` arbeiten, das Fenster schreibt beim Speichern zurück."""
    daten = {
        "format": "pdiag/1",
        "type": typ,
        "name": "Probe",
        "page": {"size": "A4", "orientation": "portrait"},
        "style": "modern-light",
        "shapes": [
            {
                "id": "s1",
                "kind": "class",
                "x": 100,
                "y": 80,
                "w": 200,
                "h": 120,
                "text": {"name": "Konto", "attributes": [], "operations": []},
            }
        ],
        "connectors": [],
    }
    pfad = tmp_path / "probe.pdiag"
    pfad.write_text(json.dumps(daten, ensure_ascii=False), encoding="utf-8")
    return Diagramm.laden(pfad)


@pytest.fixture
def fenster(tmp_path: Path, qtbot):
    f = DiagrammFenster(_diagramm(tmp_path))
    qtbot.addWidget(f)
    f.resize(900, 600)
    _AM_LEBEN.append(f)
    return f


# -- Die drei Einträge sind nicht mehr ausgegraut -----------------------


@pytest.mark.parametrize("eintrag", ["Lineale", "Hilfslinien", "Minimap"])
def test_der_eintrag_laesst_sich_ausloesen(fenster, eintrag: str) -> None:
    aktion = fenster.aktionen[f"Ansicht/{eintrag}"]

    assert aktion.isEnabled(), f"{eintrag} ist noch ausgegraut"
    assert aktion.isCheckable()


# -- Lineale ------------------------------------------------------------


def test_die_lineale_liegen_neben_der_flaeche_nicht_darauf(fenster) -> None:
    """In den `paintEvent` gemalt hätten sie die obersten und linkesten
    Zentimeter des Blatts unter sich begraben."""
    assert fenster.lineal_oben.height() == LINEALBREITE
    assert fenster.lineal_links.width() == LINEALBREITE
    assert fenster.lineal_oben.parent() is not fenster.zeichenflaeche


def test_die_lineale_lassen_sich_abschalten(fenster) -> None:
    fenster.aktionen["Ansicht/Lineale"].setChecked(True)
    assert not fenster.lineal_oben.isHidden()

    fenster.aktionen["Ansicht/Lineale"].setChecked(False)

    assert fenster.lineal_oben.isHidden()
    assert fenster.lineal_links.isHidden()
    assert fenster.lineal_ecke.isHidden()


def test_das_lineal_rechnet_millimeter_in_pixel_und_zurueck() -> None:
    """Gezählt wird in Millimetern, passend zum Seitenformat - ein
    Diagramm-Editor, der in Pixeln misst, hilft beim Drucken nicht."""
    assert pixel_in_mm(mm_in_pixel(100.0)) == pytest.approx(100.0)
    # 96 dpi wie in `seite.py`: 25,4 mm sind ein Zoll.
    assert mm_in_pixel(25.4) == pytest.approx(96.0)


def test_das_lineal_folgt_zoom_und_rollstand(qtbot) -> None:
    lineal = Lineal(waagerecht=True)
    qtbot.addWidget(lineal)

    lineal.stand_setzen(2.0, 150)

    assert lineal.zoom == 2.0
    assert lineal.versatz == 150


def test_eine_marke_folgt_der_maus(qtbot) -> None:
    lineal = Lineal(waagerecht=True)
    qtbot.addWidget(lineal)

    lineal.marke_setzen(42)
    assert lineal.marke == 42

    lineal.marke_setzen(None)
    assert lineal.marke is None


def test_das_lineal_zeichnet_wirklich_striche(qtbot) -> None:
    lineal = Lineal(waagerecht=True)
    qtbot.addWidget(lineal)
    lineal.resize(400, LINEALBREITE)

    bild = lineal.grab().toImage()

    dunkel = sum(
        1
        for x in range(bild.width())
        for y in range(bild.height())
        if bild.pixelColor(x, y).lightness() < 200
    )
    assert dunkel > 50, "auf dem Lineal steht nichts"


# -- Hilfslinien --------------------------------------------------------


def test_aus_dem_lineal_gezogen_entsteht_eine_hilfslinie(fenster) -> None:
    fenster._hilfslinie_anlegen(240.0, waagerecht=False)

    assert fenster.diagramm.daten["guides"] == [{"orientation": "v", "pos": 240.0}]


def test_waagerecht_und_senkrecht_werden_unterschieden(fenster) -> None:
    fenster._hilfslinie_anlegen(240.0, waagerecht=False)
    fenster._hilfslinie_anlegen(180.0, waagerecht=True)

    richtungen = [linie["orientation"] for linie in fenster.diagramm.daten["guides"]]
    assert richtungen == ["v", "h"]


def test_eine_hilfslinie_ist_ein_undo_schritt(fenster) -> None:
    """Wie jede andere Änderung am Diagramm - wer sie versehentlich
    zieht, drückt Strg+Z."""
    fenster._hilfslinie_anlegen(240.0, waagerecht=False)
    fenster._hilfslinie_anlegen(180.0, waagerecht=True)

    fenster.zeichenflaeche.rueckgaengig()

    assert fenster.diagramm.daten["guides"] == [{"orientation": "v", "pos": 240.0}]


def test_eine_hilfslinie_ueberlebt_speichern_und_laden(fenster, tmp_path: Path) -> None:
    fenster._hilfslinie_anlegen(240.0, waagerecht=False)
    ziel = tmp_path / "mit_hilfslinie.pdiag"

    fenster.diagramm.speichern(ziel)
    wieder = Diagramm.laden(ziel)

    assert hilfslinien_lesen(wieder.daten) == [{"orientation": "v", "pos": 240.0}]


def test_eine_pdiag_ohne_guides_bleibt_gueltig(tmp_path: Path) -> None:
    """Jede `.pdiag` aus der Zeit vor M15 hat kein `guides` - die soll
    sich weiter öffnen lassen, ohne dass jemand die Datei anfasst."""
    diagramm = _diagramm(tmp_path)

    assert "guides" not in diagramm.daten
    assert hilfslinien_lesen(diagramm.daten) == []


def test_unsinn_im_guides_feld_wird_uebergangen() -> None:
    """Eine von Hand verbogene Datei soll den Editor nicht mitnehmen."""
    assert hilfslinien_lesen({"guides": "keine Liste"}) == []
    assert hilfslinien_lesen({"guides": [{"orientation": "schräg", "pos": 3}]}) == []
    assert hilfslinien_lesen({"guides": [{"orientation": "v"}]}) == []
    assert hilfslinien_lesen({"guides": [42, None]}) == []


def test_die_hilfslinie_wird_wirklich_gezeichnet(fenster) -> None:
    fenster._hilfslinie_anlegen(120.0, waagerecht=False)

    bild = fenster.zeichenflaeche.grab().toImage()

    gruen = sum(
        1
        for y in range(0, bild.height(), 3)
        for x in range(0, bild.width(), 3)
        if bild.pixelColor(x, y).name() == "#1e8e3e"
    )
    assert gruen > 10, "die Hilfslinie steht nicht auf der Fläche"


def test_hilfslinien_lassen_sich_ausblenden(fenster) -> None:
    fenster._hilfslinie_anlegen(120.0, waagerecht=False)

    fenster.aktionen["Ansicht/Hilfslinien"].setChecked(False)

    assert fenster.zeichenflaeche.hilfslinien_sichtbar is False
    bild = fenster.zeichenflaeche.grab().toImage()
    gruen = sum(
        1
        for y in range(0, bild.height(), 3)
        for x in range(0, bild.width(), 3)
        if bild.pixelColor(x, y).name() == "#1e8e3e"
    )
    assert gruen == 0


# -- Minimap ------------------------------------------------------------


def test_die_minimap_ist_zunaechst_aus(fenster) -> None:
    """Sie nimmt eine Ecke der Zeichenfläche weg - wer sie will, schaltet
    sie ein."""
    assert fenster.aktionen["Ansicht/Minimap"].isChecked() in (True, False)
    fenster.aktionen["Ansicht/Minimap"].setChecked(False)
    assert fenster.minimap.isHidden()


def test_eingeschaltet_zeigt_die_minimap_das_diagramm(fenster) -> None:
    fenster.aktionen["Ansicht/Minimap"].setChecked(True)

    assert fenster._minimap_an is True
    assert fenster.minimap._abbild is not None


def test_das_abbild_entsteht_aus_der_zeichenflaeche_selbst(fenster) -> None:
    """Keine zweite Zeichenroutine: jede Form sieht in der Minimap
    automatisch so aus wie im Diagramm."""
    breite, hoehe = fenster.zeichenflaeche.inhaltsgroesse()
    abbild = abbild_erzeugen(fenster.zeichenflaeche, QSize(int(breite), int(hoehe)))

    bild = abbild.toImage()
    gezeichnet = sum(
        1
        for y in range(0, bild.height(), 5)
        for x in range(0, bild.width(), 5)
        if bild.pixelColor(x, y).name() != "#ffffff"
    )
    assert gezeichnet > 100, "das Abbild ist leer"


def test_das_abbild_haengt_nicht_an_der_zoomstufe(fenster) -> None:
    """Sonst zeigte die Minimap beim Hineinzoomen immer weniger vom
    Diagramm - genau das Gegenteil dessen, wofür sie da ist."""
    fenster.zeichenflaeche.zoom_setzen(3.0)
    vorher = fenster.zeichenflaeche.zoom

    breite, hoehe = fenster.zeichenflaeche.inhaltsgroesse()
    abbild_erzeugen(fenster.zeichenflaeche, QSize(int(breite), int(hoehe)))

    assert fenster.zeichenflaeche.zoom == vorher


def test_ein_klick_in_die_minimap_springt_dorthin(fenster) -> None:
    fenster.aktionen["Ansicht/Minimap"].setChecked(True)
    fenster.show()
    vorher = fenster.rollbereich.verticalScrollBar().value()

    fenster._zur_stelle_springen(QPoint(0, 800))

    assert fenster.rollbereich.verticalScrollBar().value() != vorher


def test_die_minimap_meldet_die_stelle_in_diagrammkoordinaten(qtbot) -> None:
    minimap = Minimap()
    qtbot.addWidget(minimap)
    minimap.abbild_setzen(None, QSize(1600, 1200))
    gemeldet: list[QPoint] = []
    minimap.sprung_gewuenscht.connect(gemeldet.append)

    # Ein Klick in die Mitte der Minimap meint die Mitte des Diagramms.
    mitte = QPointF(minimap.width() / 2, minimap.height() / 2)
    ereignis = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        mitte,
        mitte,
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(minimap, ereignis)

    assert gemeldet, "kein Sprung gemeldet"
    assert 700 < gemeldet[0].x() < 900


def test_der_ausschnittsrahmen_laesst_sich_setzen(qtbot) -> None:
    minimap = Minimap()
    qtbot.addWidget(minimap)

    minimap.ausschnitt_setzen(QRect(10, 20, 300, 200))

    assert minimap._ausschnitt == QRect(10, 20, 300, 200)


def test_ansicht_steht_in_der_ini_der_ide(tmp_path: Path) -> None:
    """Punkt 45 der offenen Punkte: Lineale und Minimap standen über
    `QSettings("Natter", "Diagramm")` in einem eigenen Speicher, unter
    Windows in der Registry, und blieben nach dem Deinstallieren
    zurück. Jetzt stehen sie in derselben INI wie alles andere."""
    from PySide6.QtCore import QSettings

    fenster = DiagrammFenster(_diagramm(tmp_path))
    _AM_LEBEN.append(fenster)

    fenster.aktionen["Ansicht/Minimap"].setChecked(True)
    fenster.aktionen["Ansicht/Lineale"].setChecked(False)

    ini = QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Natter", "Natter-IDE"
    )
    assert ini.value("diagramm/ansicht/minimap", type=bool) is True
    assert ini.value("diagramm/ansicht/lineale", type=bool) is False
    assert not (tmp_path / "Natter" / "Diagramm.ini").exists()
