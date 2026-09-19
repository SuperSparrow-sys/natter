"""Tests für die Komponentenpalette im Hauptfenster: Doppelklick
platziert eine Komponente im aktiven Formular-Designer (Abschnitt 7.3).
Headless. Siehe docs/arbeitspakete/M3.md, Schritt 6.

Wichtig: `designer_oeffnen()` aktiviert automatisches `.pfm`-Speichern
(M3, Schritt 4). Tests, die tatsächlich etwas platzieren/verschieben,
dürfen deshalb NICHT direkt gegen `beispielprojekte/Ampel/u_main.pfm`
laufen, sondern gegen eine Kopie in `tmp_path` – sonst verändert der
Testlauf die eingecheckte Beispieldatei.
"""

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

from ide.shell.hauptfenster import HauptFenster
from pcl import Button

_AMPEL_PFM = (
    Path(__file__).resolve().parent.parent / "beispielprojekte" / "Ampel" / "u_main.pfm"
)


@pytest.fixture
def ampel_pfm_kopie(tmp_path: Path) -> Path:
    ziel = tmp_path / "u_main.pfm"
    ziel.write_text(_AMPEL_PFM.read_text(encoding="utf-8"), encoding="utf-8")
    return ziel


def test_palette_haengt_im_dock() -> None:
    fenster = HauptFenster()
    assert fenster.palette_dock.widget() is fenster.palette


def test_doppelklick_ohne_offenen_designer_zeigt_hinweis() -> None:
    fenster = HauptFenster()
    fenster.palette.standard_liste.setCurrentRow(0)
    eintrag = fenster.palette.standard_liste.currentItem()

    fenster.palette.standard_liste.itemDoubleClicked.emit(eintrag)

    meldung = fenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Formular-Designer geöffnet.")
    assert "Projekt-Explorer" in meldung


def test_doppelklick_platziert_komponente_mittig_im_aktiven_formular(
    ampel_pfm_kopie: Path,
) -> None:
    fenster = HauptFenster()
    formular = fenster.designer_oeffnen(ampel_pfm_kopie)
    namen_vorher = set(vars(formular))

    fenster.palette.standard_liste.setCurrentRow(0)  # Button steht zuerst
    eintrag = fenster.palette.standard_liste.currentItem()
    fenster.palette.standard_liste.itemDoubleClicked.emit(eintrag)

    neue_namen = set(vars(formular)) - namen_vorher
    assert len(neue_namen) == 1
    neue_komponente = getattr(formular, neue_namen.pop())
    assert isinstance(neue_komponente, Button)
    assert neue_komponente.left == formular.width // 2
    assert neue_komponente.top == formular.height // 2


def test_einfacher_klick_macht_die_komponente_scharf_fuer_platzierung(
    ampel_pfm_kopie: Path,
) -> None:
    """Nutzer-Feedback (September 2026): „ich möchte per Klick neue
    Objekte auf der GUI hinzufügen. diese sollen automatisch in den
    code übernommen werden." Einfacher Klick auf ein Palettensymbol
    macht den Typ im aktiven Designer „scharf" (Fadenkreuz-Cursor, wie
    in Lazarus) statt sofort mittig zu platzieren."""
    fenster = HauptFenster()
    fenster.designer_oeffnen(ampel_pfm_kopie)
    fenster.palette.standard_liste.setCurrentRow(0)  # Button steht zuerst
    eintrag = fenster.palette.standard_liste.currentItem()

    fenster.palette.standard_liste.itemClicked.emit(eintrag)

    assert fenster._aktueller_canvas._platzierungs_typ is Button


def test_klick_auf_das_formular_platziert_dort_und_landet_automatisch_im_code(
    ampel_pfm_kopie: Path,
) -> None:
    """Der eigentliche Endzweck: nach dem „scharf machen" landet ein
    Klick auf das Formular genau dort - und `design_datei_erzeugen()`
    (über `_nach_aenderung`) schreibt das sofort in
    `u_main_design.py`, ganz ohne extra Speichern-Schritt."""
    fenster = HauptFenster()
    formular = fenster.designer_oeffnen(ampel_pfm_kopie)
    namen_vorher = set(vars(formular))

    fenster.palette.standard_liste.setCurrentRow(0)
    eintrag = fenster.palette.standard_liste.currentItem()
    fenster.palette.standard_liste.itemClicked.emit(eintrag)

    klick = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(30, 40),
        QPointF(30, 40),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    fenster._aktueller_canvas.eventFilter(formular._qwidget, klick)

    neue_namen = set(vars(formular)) - namen_vorher
    assert len(neue_namen) == 1
    neue_komponente = getattr(formular, neue_namen.pop())
    assert isinstance(neue_komponente, Button)
    assert (neue_komponente.left, neue_komponente.top) == (30, 40)

    design_pfad = ampel_pfm_kopie.with_name("u_main_design.py")
    generierter_code = design_pfad.read_text(encoding="utf-8")
    assert fenster._aktueller_canvas._attributname(neue_komponente) in generierter_code


def test_aktueller_canvas_folgt_dem_tabwechsel(ampel_pfm_kopie: Path) -> None:
    fenster = HauptFenster()
    fenster.designer_oeffnen(ampel_pfm_kopie)
    erster_canvas = fenster._aktueller_canvas

    # Datei als reinen Text öffnen (kein Designer-Tab, kein Schreibzugriff)
    fenster.datei_oeffnen(_AMPEL_PFM)
    assert fenster._aktueller_canvas is None  # aktiver Tab ist kein Designer

    fenster.editor_tabs.setCurrentIndex(0)  # zurück zum Designer-Tab
    assert fenster._aktueller_canvas is erster_canvas
