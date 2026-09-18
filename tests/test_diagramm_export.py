"""Tests für ide/diagramm/export.py: PNG, SVG, PDF, Zwischenablage und
Drucken (M9, Schritt 8). Headless.

Geprüft wird nicht nur, dass eine Datei entsteht, sondern dass sie
wieder einlesbar ist und die erwarteten Abmessungen hat – eine leere
oder kaputte Datei zu schreiben wäre sonst ein grüner Test.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.export import (
    als_bild,
    als_pdf,
    als_png,
    als_svg,
    in_zwischenablage,
    inhaltsbereich,
)
from ide.diagramm.seite import seitengroesse


@pytest.fixture
def fenster(tmp_path: Path) -> DiagrammFenster:
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "ampel.pdiag", "ampel"))
    flaeche = fenster.zeichenflaeche
    ampel = flaeche.form_platzieren("class", 240, 200)
    ampel["text"] = {
        "name": "TAmpel",
        "attributes": ["-zustand: int"],
        "methods": ["+umschalten()"],
    }
    lampe = flaeche.form_platzieren("class", 620, 200)
    lampe["text"] = {"name": "TLampe", "attributes": [], "methods": ["+setzen()"]}
    verbindung = flaeche.verbindung_erstellen("composition", ampel, lampe)
    verbindung["labels"] = {"from": "1", "to": "3"}
    flaeche.auswahl_aufheben()
    return fenster


@pytest.fixture
def daten(fenster: DiagrammFenster) -> dict:
    return fenster.diagramm.daten


# -- Inhaltsbereich ------------------------------------------------------


def test_inhaltsbereich_umschliesst_alle_formen(daten: dict) -> None:
    bereich = inhaltsbereich(daten)

    for form in daten["shapes"]:
        assert bereich.left() < form["x"]
        assert bereich.right() > form["x"] + form["w"]


def test_leeres_diagramm_exportiert_die_leere_seite(tmp_path: Path) -> None:
    """Sonst wäre der Bereich 0×0 und der Export stürzte ab."""
    leer = diagramm_erzeugen("class", tmp_path / "leer.pdiag", "leer").daten
    bereich = inhaltsbereich(leer)

    assert (bereich.width(), bereich.height()) == seitengroesse(leer["page"])


# -- PNG -----------------------------------------------------------------


def test_png_ist_lesbar_und_hat_die_groesse_des_inhalts(daten: dict, tmp_path: Path) -> None:
    pfad = als_png(daten, tmp_path / "ampel.png")

    bild = QImage(str(pfad))
    assert not bild.isNull()
    bereich = inhaltsbereich(daten)
    assert (bild.width(), bild.height()) == (round(bereich.width()), round(bereich.height()))


def test_png_enthaelt_wirklich_gezeichnete_formen(daten: dict, tmp_path: Path) -> None:
    """Ein reinweißes Bild wäre technisch gültig und trotzdem falsch."""
    bild = QImage(str(als_png(daten, tmp_path / "ampel.png")))

    farben = {
        bild.pixelColor(x, y).name()
        for x in range(0, bild.width(), 3)
        for y in range(0, bild.height(), 3)
    }
    assert len(farben) > 2


def test_doppelte_aufloesung_ergibt_doppelt_so_viele_pixel(daten: dict, tmp_path: Path) -> None:
    einfach = QImage(str(als_png(daten, tmp_path / "a.png")))
    doppelt = QImage(str(als_png(daten, tmp_path / "b.png", skalierung=2.0)))

    assert doppelt.width() == pytest.approx(einfach.width() * 2, abs=2)


def test_transparenter_hintergrund_bleibt_durchsichtig(daten: dict, tmp_path: Path) -> None:
    bild = QImage(str(als_png(daten, tmp_path / "a.png", transparent=True)))

    assert bild.pixelColor(1, 1).alpha() == 0


def test_undurchsichtiger_hintergrund_ist_die_farbe_der_stilvorlage(
    daten: dict, tmp_path: Path
) -> None:
    bild = QImage(str(als_png(daten, tmp_path / "a.png")))

    assert bild.pixelColor(1, 1).name() == "#ffffff"  # modern-light


# -- SVG -----------------------------------------------------------------


def test_svg_ist_gueltiges_xml_mit_passender_groesse(daten: dict, tmp_path: Path) -> None:
    import xml.etree.ElementTree as ET

    pfad = als_svg(daten, tmp_path / "ampel.svg")
    wurzel = ET.parse(pfad).getroot()

    assert wurzel.tag.endswith("svg")
    # width/height stehen in Millimetern, die viewBox in unseren Pixeln
    bereich = inhaltsbereich(daten)
    assert wurzel.get("viewBox") == f"0 0 {bereich.width():g} {bereich.height():g}"


def test_svg_enthaelt_zeichenbefehle(daten: dict, tmp_path: Path) -> None:
    inhalt = als_svg(daten, tmp_path / "ampel.svg").read_text(encoding="utf-8")

    assert "<path" in inhalt or "<rect" in inhalt or "<polyline" in inhalt
    assert "TAmpel" in inhalt  # Text wird als solcher exportiert, nicht als Bild


# -- PDF -----------------------------------------------------------------


def test_pdf_hat_eine_seite_im_richtigen_format(daten: dict, tmp_path: Path) -> None:
    pdf = pytest.importorskip("PySide6.QtPdf")

    pfad = als_pdf(daten, tmp_path / "ampel.pdf")
    dokument = pdf.QPdfDocument()
    dokument.load(str(pfad))

    assert dokument.pageCount() == 1
    groesse = dokument.pagePointSize(0)
    # A4 quer = 842 x 595 pt
    assert round(groesse.width()) == pytest.approx(842, abs=2)
    assert round(groesse.height()) == pytest.approx(595, abs=2)


def test_pdf_ist_nicht_leer(daten: dict, tmp_path: Path) -> None:
    pfad = als_pdf(daten, tmp_path / "ampel.pdf")

    assert pfad.read_bytes().startswith(b"%PDF")
    assert pfad.stat().st_size > 1000


def test_hochformat_ergibt_ein_hochformatiges_pdf(daten: dict, tmp_path: Path) -> None:
    pdf = pytest.importorskip("PySide6.QtPdf")
    daten["page"]["orientation"] = "portrait"

    dokument = pdf.QPdfDocument()
    dokument.load(str(als_pdf(daten, tmp_path / "hoch.pdf")))

    groesse = dokument.pagePointSize(0)
    assert groesse.height() > groesse.width()


# -- Zwischenablage ------------------------------------------------------


def test_als_bild_liefert_dasselbe_wie_der_png_export(daten: dict, tmp_path: Path) -> None:
    aus_datei = QImage(str(als_png(daten, tmp_path / "a.png")))
    im_speicher = als_bild(daten)

    assert (im_speicher.width(), im_speicher.height()) == (
        aus_datei.width(),
        aus_datei.height(),
    )


def test_zwischenablage_bekommt_das_bild(daten: dict) -> None:
    bild = in_zwischenablage(daten)

    aus_ablage = QApplication.clipboard().image()
    assert not aus_ablage.isNull()
    assert aus_ablage.size() == bild.size()


# -- Menü im Fenster -----------------------------------------------------


@pytest.mark.parametrize("endung", [".png", ".svg", ".pdf"])
def test_exportieren_waehlt_das_format_an_der_endung(
    fenster: DiagrammFenster, tmp_path: Path, endung: str
) -> None:
    pfad = fenster.exportieren(tmp_path / f"ausgabe{endung}")

    assert pfad is not None and pfad.exists() and pfad.stat().st_size > 0
    assert "Exportiert" in fenster.statusBar().currentMessage()


def test_unbekannte_endung_meldet_das_und_schreibt_nichts(
    fenster: DiagrammFenster, tmp_path: Path
) -> None:
    ziel = tmp_path / "ausgabe.docx"

    assert fenster.exportieren(ziel) is None
    assert not ziel.exists()
    assert "Unbekanntes Exportformat" in fenster.statusBar().currentMessage()


def test_png_einstellungen_wirken_beim_export(
    fenster: DiagrammFenster, tmp_path: Path
) -> None:
    """Abschnitt 13.2: „PNG-Export mit wählbarer Auflösung, transparenter
    oder weißer Hintergrund“."""
    from ide.diagramm.exportdialog import PngEinstellungen

    normal = QImage(str(fenster.exportieren(tmp_path / "a.png")))
    gross = QImage(
        str(
            fenster.exportieren(
                tmp_path / "b.png", PngEinstellungen(skalierung=2.0, transparent=True)
            )
        )
    )

    assert gross.width() == pytest.approx(normal.width() * 2, abs=2)
    assert gross.pixelColor(1, 1).alpha() == 0


def test_png_dialog_liefert_die_gewaehlten_werte() -> None:
    from ide.diagramm.exportdialog import AUFLOESUNGEN, PngDialog

    dialog = PngDialog()
    dialog.aufloesung.setCurrentText("4× (Plakat)")
    dialog.transparent.setChecked(True)

    einstellungen = dialog.einstellungen()

    assert einstellungen.skalierung == AUFLOESUNGEN["4× (Plakat)"]
    assert einstellungen.transparent is True


def test_als_bild_kopieren_haengt_am_menue(fenster: DiagrammFenster) -> None:
    fenster.aktionen["Bearbeiten/Als Bild kopieren"].trigger()

    assert not QApplication.clipboard().image().isNull()
    assert "Zwischenablage" in fenster.statusBar().currentMessage()


@pytest.mark.drucker
def test_drucken_zeichnet_auf_den_uebergebenen_drucker(
    fenster: DiagrammFenster, tmp_path: Path
) -> None:
    """Drucken selbst lässt sich headless nicht auslösen – geprüft wird
    deshalb der Weg dorthin: derselbe Rückruf, der auch die Vorschau
    füllt, auf einen PDF-Drucker angewandt."""
    from PySide6.QtPrintSupport import QPrinter

    ziel = tmp_path / "druck.pdf"
    drucker = QPrinter(QPrinter.PrinterMode.HighResolution)
    drucker.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    drucker.setOutputFileName(str(ziel))

    fenster.drucken(drucker)

    assert ziel.exists() and ziel.read_bytes().startswith(b"%PDF")


@pytest.mark.drucker
def test_drucker_wird_nur_einmal_gesucht(fenster: DiagrammFenster) -> None:
    """Real gemessen: der **erste** `QPrinter` eines Prozesses lässt
    Windows alle Drucker durchsuchen und brauchte dafür fast eine
    Minute, in der die Oberfläche stand. Der fertige Drucker wird
    deshalb gemerkt – ein zweiter Aufruf darf keinen neuen anlegen."""
    erster = fenster._drucker_vorbereiten()
    zweiter = fenster._drucker_vorbereiten()

    assert erster is zweiter


@pytest.mark.drucker
def test_drucker_uebernimmt_die_ausrichtung_des_diagramms(fenster: DiagrammFenster) -> None:
    from PySide6.QtGui import QPageLayout

    fenster.diagramm.daten["page"]["orientation"] = "portrait"

    assert fenster._drucker_vorbereiten().pageLayout().orientation() == (
        QPageLayout.Orientation.Portrait
    )


def test_export_nimmt_die_stilvorlage_des_diagramms_nicht_das_ide_theme(
    fenster: DiagrammFenster, tmp_path: Path
) -> None:
    """Abschnitt 13.6: „Export verwendet immer die im Diagramm gewählte
    Vorlage“ – sonst käme ein im dunklen Theme gezeichnetes Diagramm
    schwarz aus dem Drucker."""
    fenster.stil_setzen("black-white")

    bild = QImage(str(fenster.exportieren(tmp_path / "sw.png")))

    farben = {
        bild.pixelColor(x, y).name()
        for x in range(0, bild.width(), 4)
        for y in range(0, bild.height(), 4)
    }
    assert all(f[1:3] == f[3:5] == f[5:7] for f in farben)
