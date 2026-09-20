"""Kurzhinweise („Tooltips“) überall (M11, Abschnitt 4).

Die Oberfläche war an vielen Stellen stumm: die Werkzeugleiste zeigt nur
Symbole, die Palette zeigte beim Überfahren nur „Button“ – also genau
das, was man ohnehin vermutet –, und die Zeilen des Objektinspektors
erklärten sich gar nicht, obwohl jede Eigenschaft seit jeher einen
deutschen Hilfetext trägt (`Prop(doc=...)`). Er wurde nur nirgends
angezeigt.

Die Texte werden überall aus der vorhandenen Quelle geholt statt
zweitgeschrieben: die Palette nimmt den ersten Satz aus dem Docstring
der Komponente, der Objektinspektor den `doc` der Eigenschaft, die
Werkzeugleiste Name und Tastenkürzel aus dem Aktionsregister. Eine
zweite, von Hand gepflegte Beschreibung wäre nach der ersten Änderung
falsch.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from ide.actions import Aktion
from ide.inspector import EigenschaftenTabelle
from ide.inspector.ereignisse_tabelle import EreignisseTabelle
from ide.palette.palette import (
    ALLE_KOMPONENTEN,
    TYP_ROLLE,
    Komponentenpalette,
    kurzbeschreibung,
)
from ide.shell.hauptfenster import DOCK_HINWEISE, PANEL_REITER, HauptFenster
from pcl import Button, Form
from pcl.components.additional import Shape, TrackBar


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import pcl.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)
        self.s_form = Shape(self)
        self.t_regler = TrackBar(self)


# -- Werkzeugleiste ------------------------------------------------------


def test_eine_aktion_nennt_ihr_tastenkuerzel_im_hinweis(qtbot) -> None:
    """In der Werkzeugleiste steht nur das Symbol. Das Kürzel daneben im
    Menü sieht nur, wer das Menü aufklappt."""
    aktion = Aktion("datei.speichern", "Speichern", tastenkuerzel="Ctrl+S")

    assert "Speichern" in aktion.qaction.toolTip()
    assert "S" in aktion.qaction.toolTip().split("(")[1]


def test_eine_aktion_ohne_kuerzel_nennt_nur_den_namen(qtbot) -> None:
    aktion = Aktion("datei.irgendwas", "Irgendwas")

    assert aktion.qaction.toolTip() == "Irgendwas"


# -- Komponentenpalette --------------------------------------------------


@pytest.mark.parametrize("typ", ALLE_KOMPONENTEN, ids=lambda t: t.__name__)
def test_jede_palettenkachel_erklaert_ihre_komponente(typ: type) -> None:
    hinweis = kurzbeschreibung(typ)

    assert hinweis.startswith(f"{typ.__name__} – ")
    assert len(hinweis) > len(typ.__name__) + 5
    # Das zugrunde liegende Qt-Widget hilft beim Bauen eines Formulars
    # niemandem und steht deshalb bewusst nicht dabei.
    assert "Qt-Basis" not in hinweis
    assert "`" not in hinweis


def test_die_kacheln_tragen_den_hinweis_auch_wirklich(qtbot) -> None:
    palette = Komponentenpalette()
    qtbot.addWidget(palette)

    for liste in palette.listen:
        for zeile in range(liste.count()):
            eintrag = liste.item(zeile)
            assert eintrag.toolTip() == kurzbeschreibung(eintrag.data(TYP_ROLLE))


# -- Objektinspektor -----------------------------------------------------


def _hinweis(tabelle: EigenschaftenTabelle, name: str) -> str:
    for zeile in range(tabelle.rowCount()):
        if tabelle.item(zeile, 0).text() == name:
            return tabelle.item(zeile, 0).toolTip()
    raise AssertionError(f"Zeile {name!r} nicht gefunden")


def test_jede_eigenschaft_erklaert_sich(qtbot) -> None:
    """`increment`, `frequency`, `item_index` – das musste man raten."""
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    qtbot.addWidget(tabelle)

    tabelle.komponente_anzeigen(formular.t_regler)

    for zeile in range(tabelle.rowCount()):
        name = tabelle.item(zeile, 0).text()
        assert tabelle.item(zeile, 0).toolTip(), f"{name} hat keinen Hinweis"
        # Der Hinweis hängt an beiden Spalten: die Maus steht beim
        # Eintippen in der rechten.
        assert tabelle.item(zeile, 1).toolTip() == tabelle.item(zeile, 0).toolTip()


def test_auch_die_untereigenschaften_erklaeren_sich(qtbot) -> None:
    """`font_size` und `brush_color` sind keine `Prop`s, sondern
    aufklappbare Untereigenschaften – sie hatten als Einzige keinen
    Hilfetext."""
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    qtbot.addWidget(tabelle)

    tabelle.komponente_anzeigen(formular.s_form)

    assert "Punkt" in _hinweis(tabelle, "font_size")
    assert "RRGGBB" in _hinweis(tabelle, "brush_color")


def test_die_zeile_name_erklaert_den_unterschied_zu_caption(qtbot) -> None:
    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    qtbot.addWidget(tabelle)

    tabelle.komponente_anzeigen(
        formular.b_ein, name="b_ein", name_setzen=lambda _neu: None
    )

    hinweis = _hinweis(tabelle, "name")
    assert "Quelltext" in hinweis
    assert "caption" in hinweis


def test_jedes_ereignis_erklaert_sich(qtbot) -> None:
    """`on_change` heißt bei jeder Komponente etwas anderes."""
    formular = _Formular()
    tabelle = EreignisseTabelle()
    qtbot.addWidget(tabelle)

    tabelle.anzeigen(formular.t_regler, formular)

    for zeile in range(tabelle.rowCount()):
        assert tabelle.item(zeile, 0).toolTip()


# -- Docks und Panels ----------------------------------------------------


def test_jedes_dock_sagt_wofuer_es_da_ist(einstellungen: QSettings, qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    for dock in (
        fenster.explorer_dock,
        fenster.inspektor_dock,
        fenster.palette_dock,
        fenster.datenbank_dock,
        fenster.panels_dock,
    ):
        assert dock.toolTip() == DOCK_HINWEISE[dock.windowTitle()]
        assert dock.toolTip() != dock.windowTitle()


def test_jeder_panel_reiter_sagt_wofuer_er_da_ist(
    einstellungen: QSettings, qtbot
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    for index in range(fenster.panels.count()):
        titel = fenster.panels.tabText(index)
        assert titel in PANEL_REITER
        assert fenster.panels.tabToolTip(index)
        assert fenster.panels.tabToolTip(index) != titel
