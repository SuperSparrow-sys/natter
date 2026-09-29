"""Seitenformat und Ausrichtung nachträglich ändern (Punkt 67 der
offenen Punkte).

`page` wurde nur beim Anlegen geschrieben. Dazu fiel beim Nachsehen
auf: der Drucker bekam nur die Ausrichtung, nicht die Blattgröße.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from PySide6.QtGui import QPageLayout, QPageSize

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.seite import seitengroesse
from ide.diagramm.seitendialog import SeitenDialog


def _fenster(tmp_path: Path, typ: str = "class") -> DiagrammFenster:
    return DiagrammFenster(diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", "k"))


def _mediabox(pfad: Path) -> tuple[float, float]:
    """Breite und Höhe der ersten Seite eines PDF in Punkt."""
    treffer = re.search(
        rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", pfad.read_bytes()
    )
    assert treffer is not None
    return float(treffer[1]), float(treffer[2])


def test_dialog_zeigt_die_aktuelle_seite_und_liefert_die_neue(qtbot) -> None:  # noqa: ANN001
    dialog = SeitenDialog({"size": "A4", "orientation": "landscape"})
    assert dialog.format.currentData() == "A4"
    assert dialog.quer.isChecked()

    dialog.format.setCurrentIndex(dialog.format.findData("A3"))
    dialog.hoch.setChecked(True)

    assert dialog.seite() == {"size": "A3", "orientation": "portrait"}


def test_menueeintrag_uebernimmt_den_dialog(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    fenster = _fenster(tmp_path)

    def bestaetigen(dialog: SeitenDialog) -> int:
        dialog.format.setCurrentIndex(dialog.format.findData("A5"))
        dialog.hoch.setChecked(True)
        return SeitenDialog.DialogCode.Accepted

    monkeypatch.setattr(SeitenDialog, "exec", bestaetigen)
    fenster.aktionen["Datei/Seite einrichten …"].trigger()

    assert fenster.diagramm.daten["page"] == {"size": "A5", "orientation": "portrait"}
    assert "A5 hoch" in fenster.statusBar().currentMessage()


def test_abbrechen_aendert_nichts(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    fenster = _fenster(tmp_path)
    vorher = dict(fenster.diagramm.daten["page"])
    monkeypatch.setattr(
        SeitenDialog, "exec", lambda self: SeitenDialog.DialogCode.Rejected
    )

    fenster.aktionen["Datei/Seite einrichten …"].trigger()

    assert fenster.diagramm.daten["page"] == vorher
    assert not fenster.zeichenflaeche.kommandos.kann_rueckgaengig


def test_zeichenflaeche_und_rueckgaengig(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    fenster = _fenster(tmp_path)
    flaeche = fenster.zeichenflaeche
    breite_vorher = flaeche.inhaltsgroesse()[0]

    assert fenster.seite_einrichten({"size": "A3", "orientation": "landscape"})
    assert flaeche.inhaltsgroesse()[0] > breite_vorher
    assert seitengroesse(fenster.diagramm.daten["page"])[0] > 1500

    flaeche.rueckgaengig()
    assert fenster.diagramm.daten["page"]["size"] == "A4"
    assert flaeche.inhaltsgroesse()[0] == breite_vorher


def test_form_ausserhalb_der_seite_passt_nach_groesserem_format(
    qtbot, tmp_path: Path  # noqa: ANN001
) -> None:
    """Genau das rät der Layout-Hinweis."""
    fenster = _fenster(tmp_path)
    flaeche = fenster.zeichenflaeche
    flaeche.form_platzieren("class", 1200, 500)
    assert any(h.regel == "ausserhalb_der_seite" for h in flaeche.hinweise)

    fenster.seite_einrichten({"size": "A3"})

    assert not any(h.regel == "ausserhalb_der_seite" for h in flaeche.hinweise)


@pytest.mark.parametrize("typ", ["class", "struktogramm", "entscheidungstabelle"])
def test_pdf_nutzt_das_neue_format(qtbot, tmp_path: Path, typ: str) -> None:  # noqa: ANN001
    fenster = _fenster(tmp_path, typ)
    fenster.seite_einrichten({"size": "A3", "orientation": "portrait"})

    pfad = fenster.exportieren(tmp_path / "blatt.pdf")

    breite, hoehe = _mediabox(pfad)
    assert round(breite) == 842 and round(hoehe) == 1191  # A3 hoch in Punkt


def test_drucker_bekommt_groesse_und_ausrichtung(qtbot, tmp_path: Path) -> None:  # noqa: ANN001
    """Ohne echten Drucker: der erste `QPrinter` durchsucht unter
    Windows alle Drucker, das dauert. Die Attrappe merkt sich nur,
    was eingestellt wird."""

    class Drucker:
        groesse: QPageSize | None = None
        ausrichtung: QPageLayout.Orientation | None = None

        def setPageSize(self, groesse: QPageSize) -> None:  # noqa: N802
            self.groesse = groesse

        def setPageOrientation(self, ausrichtung) -> None:  # noqa: ANN001, N802
            self.ausrichtung = ausrichtung

    fenster = _fenster(tmp_path)
    fenster._drucker = Drucker()
    fenster.seite_einrichten({"size": "A3", "orientation": "portrait"})

    drucker = fenster._drucker_vorbereiten()

    assert drucker.groesse.id() == QPageSize.PageSizeId.A3
    assert drucker.ausrichtung == QPageLayout.Orientation.Portrait
