"""Tests für die Kontextmenüs (M11, Abschnitt 3).

Der Rundlauf der Funktionsprüfung deckte bis jetzt die Menüleiste, die
Werkzeugleiste, die Docks und die Palette ab – die rechte Maustaste
nicht. Genau dort probieren es aber die meisten zuerst: in Lazarus
liegt zu jeder Datei und zu jeder Komponente ein Menü darunter.

Alle drei Menüs werden von einer Methode gebaut, die das Menü
**zurückgibt** statt es zu öffnen (`kontextmenue_fuer`). Ein geöffnetes
`QMenu.exec()` wartet auf einen Klick und bleibt im Test stehen.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, QSettings

from ide.designer import DesignerCanvas
from ide.project import Projekt
from ide.shell.explorer import ProjektExplorer
from ide.shell.hauptfenster import HauptFenster
from pcl.components.standard import Button
from pcl.form import Form


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import pcl.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


def _projekt(ordner: Path) -> Projekt:
    ordner.mkdir(parents=True, exist_ok=True)
    # Wie jedes Natter-Projekt: main.py startet nur, u_main.py traegt
    # den Code, u_hilfe.py ist eine gewoehnliche zweite Unit.
    (ordner / "main.py").write_text(
        "import u_main\n\ndel u_main\n", encoding="utf-8"
    )
    (ordner / "u_main.py").write_text("print('hallo')\n", encoding="utf-8")
    (ordner / "u_hilfe.py").write_text("def rechne(a):\n    return a\n", encoding="utf-8")
    (ordner / "test.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Test",
                "type": "console",
                "main": "main.py",
            }
        ),
        encoding="utf-8",
    )
    return Projekt.laden(ordner / "test.natter")


# -- Projekt-Explorer ----------------------------------------------------


@pytest.fixture
def explorer(qtbot, tmp_path: Path) -> ProjektExplorer:
    baum = ProjektExplorer()
    qtbot.addWidget(baum)
    baum.projekt_anzeigen(_projekt(tmp_path / "p"))
    baum.resize(260, 300)
    baum.show()
    return baum


#: Die Unit, um die es hier geht - eine gewoehnliche, die sich
#: umbenennen und loeschen laesst.
ERSTE_UNIT = "u_hilfe.py"


def _punkt_der_unit(baum: ProjektExplorer) -> QPoint:
    """Die Mitte der `u_hilfe.py`-Zeile.

    **Ueber den Namen gesucht, nicht ueber den Index.** Neben
    `u_hilfe.py` steht `u_main.py` im Baum, und die traegt das Programm:
    sie hat bewusst kein Kontextmenue, weil `main.py` genau diesen Namen
    importiert. Sie steht alphabetisch **nach** `u_hilfe.py`, aber auf
    die Reihenfolge soll sich hier nichts verlassen - `child(0)` war
    schon einmal die falsche Zeile."""
    eintrag = next(
        baum.units_gruppe.child(i)
        for i in range(baum.units_gruppe.childCount())
        if baum.units_gruppe.child(i).text(0) == ERSTE_UNIT
    )
    kasten = baum.visualItemRect(eintrag)
    return kasten.center()


def test_die_unit_die_das_programm_traegt_bietet_kein_menue(
    explorer: ProjektExplorer,
) -> None:
    """`u_main.py` steht im Baum, weil der Schuelercode darin steht -
    aber „Umbenennen …"/„Loeschen …" waeren dort beide ein Projekt, das
    sich nicht mehr starten laesst: `main.py` importiert diesen Namen."""
    eintrag = next(
        explorer.units_gruppe.child(i)
        for i in range(explorer.units_gruppe.childCount())
        if explorer.units_gruppe.child(i).text(0) == "u_main.py"
    )
    punkt = explorer.visualItemRect(eintrag).center()

    assert explorer.kontextmenue_fuer(punkt) is None


def test_die_rechte_maustaste_bietet_dasselbe_wie_der_knopf(
    explorer: ProjektExplorer,
) -> None:
    """Der „⋮“-Knopf steht nur in der Zeile, über der die Maus gerade
    schwebt. Wer ihn nicht bemerkt, probiert die rechte Maustaste."""
    menue = explorer.kontextmenue_fuer(_punkt_der_unit(explorer))

    assert menue is not None
    assert [a.text() for a in menue.actions()] == ["Umbenennen …", "Löschen …"]


def test_umbenennen_meldet_den_pfad(explorer: ProjektExplorer, qtbot) -> None:
    menue = explorer.kontextmenue_fuer(_punkt_der_unit(explorer))

    with qtbot.waitSignal(explorer.umbenennen_angefordert) as gefangen:
        menue.actions()[0].trigger()

    assert Path(gefangen.args[0]).name == ERSTE_UNIT


def test_loeschen_meldet_den_pfad(explorer: ProjektExplorer, qtbot) -> None:
    menue = explorer.kontextmenue_fuer(_punkt_der_unit(explorer))

    with qtbot.waitSignal(explorer.loeschen_angefordert) as gefangen:
        menue.actions()[1].trigger()

    assert Path(gefangen.args[0]).name == ERSTE_UNIT


def test_ueber_einer_gruppenueberschrift_gibt_es_kein_menue(
    explorer: ProjektExplorer,
) -> None:
    """„Umbenennen …“ über der Überschrift „Units“ hätte keinen Sinn."""
    kasten = explorer.visualItemRect(explorer.units_gruppe)

    assert explorer.kontextmenue_fuer(kasten.center()) is None


def test_im_leeren_gibt_es_kein_menue(explorer: ProjektExplorer) -> None:
    assert explorer.kontextmenue_fuer(QPoint(10, 3000)) is None


# -- Designer ------------------------------------------------------------


class _Formular(Form):
    def create_components(self) -> None:
        self.knopf = Button(self)
        self.knopf.left = 16
        self.knopf.top = 16


@pytest.fixture
def canvas(tmp_path: Path) -> DesignerCanvas:
    unit = tmp_path / "u_haupt.py"
    unit.write_text(
        "from pcl.form import Form\n\n\nclass _Formular(Form):\n    pass\n",
        encoding="utf-8",
    )
    flaeche = DesignerCanvas(_Formular(), tmp_path / "haupt.pfm")
    flaeche.unit_pfad = unit
    return flaeche


def _texte(menue) -> list[str]:
    return [a.text().split("\t")[0] for a in menue.actions() if not a.isSeparator()]


def test_das_menue_einer_komponente_nennt_die_drei_wege(
    canvas: DesignerCanvas,
) -> None:
    """Duplizieren, Löschen und die Ereignis-Methode gab es alle schon –
    aber nur über Tasten oder einen Doppelklick."""
    menue = canvas.kontextmenue_fuer(canvas.formular.knopf)

    assert _texte(menue) == [
        "Methode für „click“ anlegen",
        "Duplizieren",
        "Löschen",
        "Rückgängig",
        "Wiederholen",
    ]


def test_die_tastenkuerzel_stehen_daneben(canvas: DesignerCanvas) -> None:
    """Damit man sie beim nächsten Mal direkt benutzt."""
    menue = canvas.kontextmenue_fuer(canvas.formular.knopf)

    texte = [a.text() for a in menue.actions()]
    assert "Duplizieren\tStrg+D" in texte
    assert "Löschen\tEntf" in texte


def test_loeschen_entfernt_die_komponente(canvas: DesignerCanvas) -> None:
    menue = canvas.kontextmenue_fuer(canvas.formular.knopf)

    next(a for a in menue.actions() if a.text().startswith("Löschen")).trigger()

    assert not hasattr(canvas.formular, "knopf")


def test_duplizieren_legt_eine_zweite_an(canvas: DesignerCanvas) -> None:
    menue = canvas.kontextmenue_fuer(canvas.formular.knopf)

    next(a for a in menue.actions() if a.text().startswith("Duplizieren")).trigger()

    assert hasattr(canvas.formular, "knopf_kopie")


def test_die_ereignismethode_landet_in_der_unit(canvas: DesignerCanvas) -> None:
    menue = canvas.kontextmenue_fuer(canvas.formular.knopf)

    menue.actions()[0].trigger()

    assert "def knopf_click" in canvas.unit_pfad.read_text(encoding="utf-8")


def test_am_formular_selbst_sind_die_beiden_eintraege_grau(
    canvas: DesignerCanvas,
) -> None:
    """Ein Menü, das je nach Klickort anders aussieht, verwirrt mehr,
    als es hilft – die Einträge bleiben stehen, nur grau."""
    menue = canvas.kontextmenue_fuer(canvas.formular)

    fuer = {a.text().split("\t")[0]: a for a in menue.actions()}
    assert fuer["Duplizieren"].isEnabled() is False
    assert fuer["Löschen"].isEnabled() is False


def test_rueckgaengig_ist_erst_nach_einer_aenderung_moeglich(
    canvas: DesignerCanvas,
) -> None:
    vorher = canvas.kontextmenue_fuer(canvas.formular.knopf)
    assert not next(
        a for a in vorher.actions() if a.text().startswith("Rückgängig")
    ).isEnabled()

    canvas.verschieben(8, 0, canvas.formular.knopf)

    nachher = canvas.kontextmenue_fuer(canvas.formular.knopf)
    assert next(
        a for a in nachher.actions() if a.text().startswith("Rückgängig")
    ).isEnabled()


def test_rueckgaengig_wirkt(canvas: DesignerCanvas) -> None:
    canvas.verschieben(8, 0, canvas.formular.knopf)
    vorher = canvas.formular.knopf.left

    menue = canvas.kontextmenue_fuer(canvas.formular.knopf)
    next(a for a in menue.actions() if a.text().startswith("Rückgängig")).trigger()

    assert canvas.formular.knopf.left == vorher - 8


def test_ohne_unit_faellt_die_ereignismethode_weg() -> None:
    """Ohne Formular-Unit gäbe es keine Datei, in die die Methode
    geschrieben werden könnte."""
    flaeche = DesignerCanvas(_Formular())

    assert _texte(flaeche.kontextmenue_fuer(flaeche.formular.knopf)) == [
        "Duplizieren",
        "Löschen",
        "Rückgängig",
        "Wiederholen",
    ]


# -- Panel „Variablen“ ---------------------------------------------------


def test_im_leeren_variablenbaum_gibt_es_kein_menue(
    einstellungen: QSettings, qtbot
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    assert fenster.variablen_kontextmenue_fuer(QPoint(5, 5)) is None


def test_ueber_einer_variablen_steht_als_tabelle_anzeigen(
    einstellungen: QSettings, qtbot
) -> None:
    from PySide6.QtWidgets import QTreeWidgetItem

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.variablen_baum.addTopLevelItem(QTreeWidgetItem(["zahlen", "[1, 2, 3]"]))
    fenster.variablen_baum.resize(200, 120)
    fenster.show()

    punkt = fenster.variablen_baum.visualItemRect(
        fenster.variablen_baum.topLevelItem(0)
    ).center()
    menue = fenster.variablen_kontextmenue_fuer(punkt)

    assert menue is not None
    assert [a.text() for a in menue.actions()] == ["Als Tabelle anzeigen"]


def test_ohne_angehaltenes_programm_sagt_der_eintrag_was_fehlt(
    einstellungen: QSettings, qtbot
) -> None:
    from PySide6.QtWidgets import QTreeWidgetItem

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.variablen_baum.addTopLevelItem(QTreeWidgetItem(["zahlen", "[1, 2, 3]"]))
    fenster.variablen_baum.resize(200, 120)
    fenster.show()
    punkt = fenster.variablen_baum.visualItemRect(
        fenster.variablen_baum.topLevelItem(0)
    ).center()

    fenster.variablen_kontextmenue_fuer(punkt).actions()[0].trigger()

    meldung = fenster.statusBar().currentMessage()
    assert "nicht angehalten" in meldung
    assert "Haltepunkt" in meldung


def test_das_menue_haengt_am_fenster_nicht_am_formular(
    canvas: DesignerCanvas, qtbot
) -> None:
    """Das Formular-Widget trägt das pcl-Stylesheet des später
    laufenden Programms (hell). Hinge das Menü daran, erbte es diese
    Farben und stünde im dunklen IDE-Design hell auf dem Bildschirm –
    genau so sah es auf dem Bildschirmfoto aus."""
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    rahmen = QWidget()  # steht hier für das IDE-Hauptfenster
    qtbot.addWidget(rahmen)
    QVBoxLayout(rahmen).addWidget(canvas.formular._qwidget)

    menue = canvas.kontextmenue_fuer(canvas.formular.knopf)

    assert menue.parentWidget() is rahmen
