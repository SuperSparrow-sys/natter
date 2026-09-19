"""Schüler sehen nur die Dateien, an denen sie arbeiten (M12).

Nutzer-Hinweis September 2026: „`main.py` wird automatisch erzeugt und
soll von den Schülern ja auch nicht bearbeitet werden. Muss man es da
überhaupt sehen als Schüler?“ – Nein. In Lazarus steht die Projektdatei
`.lpr` aus demselben Grund nicht im Projektinspektor, sondern nur hinter
einem eigenen Menüweg.

Ein Kommentar „hier änderst du nichts“ in einer Datei, die man besser
gar nicht erst zu Gesicht bekommt, ist die schlechtere Lösung.

Der zweite Teil desselben Hinweises: was doch sichtbar ist, braucht eine
feste Abfolge und Struktur wie in Lazarus. Dafür steht
`test_neue_unit.py`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from ide.project import Projekt, projekt_erzeugen
from ide.shell.explorer import ProjektExplorer
from ide.shell.hauptfenster import HauptFenster


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import pcl.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


@pytest.fixture
def projekt(tmp_path: Path) -> Projekt:
    return projekt_erzeugen("gui", tmp_path / "p", "Test")


def test_die_startdatei_steht_nicht_bei_den_units(projekt: Projekt) -> None:
    namen = [pfad.name for pfad in projekt.units()]

    assert "main.py" not in namen


def test_die_erzeugte_design_datei_auch_nicht(projekt: Projekt) -> None:
    namen = [pfad.name for pfad in projekt.units()]

    assert "u_main_design.py" not in namen


def test_beide_liegen_aber_weiterhin_im_ordner(projekt: Projekt) -> None:
    """Ausgeblendet heißt nicht weg – das Programm braucht sie."""
    namen = {pfad.name for pfad in projekt.alle_python_dateien()}

    assert {"main.py", "u_main_design.py"} <= namen


def test_der_explorer_zeigt_sie_ebenfalls_nicht(projekt: Projekt, qtbot) -> None:
    baum = ProjektExplorer()
    qtbot.addWidget(baum)

    baum.projekt_anzeigen(projekt)

    gezeigt = {
        baum.units_gruppe.child(i).text(0)
        for i in range(baum.units_gruppe.childCount())
    }
    assert "main.py" not in gezeigt
    assert "u_main_design.py" not in gezeigt


def test_die_startdatei_ist_ueber_das_menue_erreichbar(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    """Wie „Projekt → Quelltext anzeigen“ in Lazarus: nicht im Baum,
    aber auch nicht unauffindbar."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    projekt_erzeugen("gui", tmp_path / "p", "Test")
    fenster.projekt_oeffnen(tmp_path / "p")

    fenster.aktionen["projekt.startdatei_zeigen"].qaction.trigger()

    offene = {
        fenster.editor_tabs.tabText(i) for i in range(fenster.editor_tabs.count())
    }
    assert "main.py" in offene
    assert "nichts zu ändern" in fenster.statusBar().currentMessage()


def test_ohne_projekt_sagt_der_eintrag_was_fehlt(
    einstellungen: QSettings, qtbot
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster.aktionen["projekt.startdatei_zeigen"].qaction.trigger()

    assert "Kein Projekt offen" in fenster.statusBar().currentMessage()


def test_ein_neuer_unitname_kollidiert_nicht_mit_der_startdatei(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    """Die Namensprüfung muss gegen **alle** Dateien laufen. Liefe sie
    nur gegen die sichtbaren, ließe sich eine Unit „main“ anlegen und
    die Startdatei damit überschreiben."""
    ordner = tmp_path / "p"
    ordner.mkdir()
    (ordner / "main.py").write_text("print('start')" + chr(10), encoding="utf-8")
    (ordner / "u_neu1.py").write_text("", encoding="utf-8")
    (ordner / "t.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "T",
                "type": "console",
                "main": "main.py",
            }
        ),
        encoding="utf-8",
    )
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(ordner)

    neu = fenster.unit_erzeugen()

    assert neu.name == "u_neu2.py"  # u_neu1 ist belegt, auch wenn unsichtbar
    assert (ordner / "main.py").read_text(encoding="utf-8") == "print('start')" + chr(10)


# -- Konsolenprojekte: dort ist main.py das ganze Programm --------------
#
# Die Regel "was nicht bearbeitet wird, wird nicht gezeigt" galt
# unterschiedslos, obwohl sie fuer GUI-Projekte gedacht war. Bei einem
# Konsolenprojekt gibt es nur `main.py`, und genau darin steht der Code
# der Schuelerin - die ersten beiden Stufen des Lehrgangs oeffneten sich
# deshalb mit einem voellig leeren Projekt-Explorer.


@pytest.fixture
def konsolenprojekt(tmp_path: Path) -> Projekt:
    return projekt_erzeugen("console", tmp_path / "k", "Konsole")


def test_bei_einem_konsolenprojekt_ist_die_startdatei_die_unit(
    konsolenprojekt: Projekt,
) -> None:
    assert [pfad.name for pfad in konsolenprojekt.units()] == ["main.py"]


def test_der_explorer_eines_konsolenprojekts_ist_nicht_leer(
    konsolenprojekt: Projekt, qtbot
) -> None:
    baum = ProjektExplorer()
    qtbot.addWidget(baum)

    baum.projekt_anzeigen(konsolenprojekt)

    gezeigt = {
        baum.units_gruppe.child(i).text(0)
        for i in range(baum.units_gruppe.childCount())
    }
    assert gezeigt == {"main.py"}


def test_die_startdatei_eines_konsolenprojekts_hat_kein_kontextmenue(
    konsolenprojekt: Projekt, qtbot
) -> None:
    """„Löschen …“ hiesse, das einzige Stueck Programm zu entfernen;
    „Umbenennen …“ zoege einen Eintrag in der `.natter` nach sich, den
    es nicht nachfuehrt."""
    baum = ProjektExplorer()
    qtbot.addWidget(baum)

    baum.projekt_anzeigen(konsolenprojekt)

    eintrag = baum.units_gruppe.child(0)
    assert eintrag.text(0) == "main.py"
    assert baum.itemWidget(eintrag, 1) is None


def test_eine_gewoehnliche_unit_behaelt_ihr_kontextmenue(
    projekt: Projekt, qtbot, tmp_path: Path
) -> None:
    (tmp_path / "p" / "u_extra.py").write_text("# etwas\n", encoding="utf-8")
    baum = ProjektExplorer()
    qtbot.addWidget(baum)

    baum.projekt_anzeigen(projekt)

    eintrag = next(
        baum.units_gruppe.child(i)
        for i in range(baum.units_gruppe.childCount())
        if baum.units_gruppe.child(i).text(0) == "u_extra.py"
    )
    assert baum.itemWidget(eintrag, 1) is not None


# -- Leere Gruppen stehen nicht als leere Ueberschrift da ----------------


def test_ein_konsolenprojekt_zeigt_keine_gruppe_formulare(
    konsolenprojekt: Projekt, qtbot
) -> None:
    """Ein Konsolenprojekt kann ueberhaupt keine Formulare haben."""
    baum = ProjektExplorer()
    qtbot.addWidget(baum)

    baum.projekt_anzeigen(konsolenprojekt)

    assert baum.formulare_gruppe.isHidden()
    assert baum.diagramme_gruppe.isHidden()
    assert not baum.units_gruppe.isHidden()


def test_ein_guiprojekt_ohne_diagramme_zeigt_die_gruppe_nicht(
    projekt: Projekt, qtbot
) -> None:
    baum = ProjektExplorer()
    qtbot.addWidget(baum)

    baum.projekt_anzeigen(projekt)

    assert baum.diagramme_gruppe.isHidden()
    assert not baum.formulare_gruppe.isHidden()


def test_eine_gruppe_taucht_wieder_auf_sobald_sie_etwas_enthaelt(
    projekt: Projekt, qtbot, tmp_path: Path
) -> None:
    """Das Ausblenden darf nicht kleben bleiben: wer ein Diagramm
    anlegt, muss es danach im Baum sehen."""
    baum = ProjektExplorer()
    qtbot.addWidget(baum)
    baum.projekt_anzeigen(projekt)
    assert baum.diagramme_gruppe.isHidden()

    ordner = tmp_path / "p" / "diagramme"
    ordner.mkdir()
    (ordner / "ablauf.pdiag").write_text("{}", encoding="utf-8")
    baum.projekt_anzeigen(projekt)

    assert not baum.diagramme_gruppe.isHidden()
    assert baum.diagramme_gruppe.child(0).text(0) == "ablauf"
