"""Eine Datei, die sich auf der Platte geändert hat, während sie in
Natter offen war (Punkt 286).

Bis 0.3.6 schrieb das Speichern den eigenen Stand ohne Nachfrage
darüber: zwei Natter-Fenster auf demselben Projekt überschrieben sich
gegenseitig, und eine Änderung außerhalb von Natter ging verloren.
Die Projekte sind Kopien in `tmp_path`.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from ide.designer.canvas import DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden
from ide.shell.hauptfenster import HauptFenster
from pcl import Button

_BEISPIELE = Path(__file__).resolve().parent.parent / "beispielprojekte"


@pytest.fixture
def projekt(tmp_path: Path) -> Path:
    ordner = tmp_path / "Begruessung"
    shutil.copytree(_BEISPIELE / "01_Begruessung", ordner)
    return ordner


@pytest.fixture
def antworten(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Die Antworten auf die Nachfrage beim Speichern; jede Frage
    nimmt die erste. Beim Schließen am Testende wird verworfen."""
    vorgegeben: list[str] = []
    monkeypatch.setattr(
        HauptFenster,
        "_vor_dem_schliessen_fragen",
        lambda self, namen: QMessageBox.StandardButton.Discard,
    )

    def fragen(self, name):  # noqa: ANN001, ANN202
        vorgegeben.append(f"gefragt:{name}")
        return vorgegeben.pop(0)

    monkeypatch.setattr(
        HauptFenster, "_von_aussen_geaendert_fragen", fragen, raising=False
    )
    return vorgegeben


def _anhaengen(editor, zeile: str) -> None:  # noqa: ANN001
    editor.setPlainText(editor.toPlainText() + zeile)
    editor.document().setModified(True)


def _zwei_fenster(hauptfenster_bauen, projekt: Path):  # noqa: ANN001, ANN202
    unit = projekt / "u_main.py"
    a, b = hauptfenster_bauen(), hauptfenster_bauen()
    editoren = []
    for fenster in (a, b):
        fenster.projekt_oeffnen(projekt / "01_Begruessung.natter")
        editoren.append(fenster.datei_oeffnen(unit))
    return a, b, *editoren, unit


@pytest.mark.parametrize(
    ("antwort", "erwartet_in_datei", "erwartet_im_editor"),
    [
        ("abbrechen", "# aus A", "# aus B"),
        ("ueberschreiben", "# aus B", "# aus B"),
        ("neu_laden", "# aus A", "# aus A"),
    ],
)
def test_zweites_fenster_fragt_vor_dem_ueberschreiben(
    hauptfenster_bauen,  # noqa: ANN001
    projekt: Path,
    antworten: list[str],
    antwort: str,
    erwartet_in_datei: str,
    erwartet_im_editor: str,
) -> None:
    a, b, editor_a, editor_b, unit = _zwei_fenster(
        hauptfenster_bauen, projekt
    )
    _anhaengen(editor_a, "\n# aus A\n")
    assert a.alle_speichern()

    _anhaengen(editor_b, "\n# aus B-Fenster, das länger ist\n")
    antworten.append(antwort)
    gespeichert = b.alle_speichern()

    assert antworten == ["gefragt:u_main.py"]
    assert gespeichert == (antwort == "ueberschreiben")
    assert erwartet_in_datei in unit.read_text(encoding="utf-8")
    assert erwartet_im_editor in editor_b.toPlainText()
    if antwort == "neu_laden":
        assert not editor_b.document().isModified()


def test_ohne_aenderung_von_aussen_wird_nicht_gefragt(
    hauptfenster_bauen,  # noqa: ANN001
    projekt: Path,
    antworten: list[str],
) -> None:
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(projekt / "01_Begruessung.natter")
    editor = fenster.datei_oeffnen(projekt / "u_main.py")
    for zeile in ("\n# eins\n", "# zwei\n"):
        _anhaengen(editor, zeile)
        assert fenster.alle_speichern()
    assert antworten == []


def test_unveraenderter_editor_laedt_die_datei_neu(
    hauptfenster_bauen,  # noqa: ANN001
    projekt: Path,
    antworten: list[str],
) -> None:
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(projekt / "01_Begruessung.natter")
    unit = projekt / "u_main.py"
    editor = fenster.datei_oeffnen(unit)
    unit.write_text(
        unit.read_text(encoding="utf-8") + "\n# von außen\n",
        encoding="utf-8",
    )

    fenster._von_aussen_geaenderte_neu_laden()

    assert "# von außen" in editor.toPlainText()
    assert not editor.document().isModified()
    _anhaengen(editor, "# danach\n")
    assert fenster.alle_speichern()
    assert antworten == []


def test_draussen_geloeschte_datei_gilt_als_ungespeichert(
    hauptfenster_bauen,  # noqa: ANN001
    projekt: Path,
    antworten: list[str],
) -> None:
    """Punkt 515: der Text stand nur noch im Editor, der Reiter galt
    aber als gespeichert, und beim Schließen kam keine Frage."""
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(projekt / "01_Begruessung.natter")
    unit = projekt / "u_main.py"
    editor = fenster.datei_oeffnen(unit)
    text = editor.toPlainText()
    unit.unlink()

    fenster._von_aussen_geaenderte_neu_laden()

    assert editor.document().isModified()
    assert editor.toPlainText() == text
    assert "gibt es auf der Platte nicht mehr" in (
        fenster.statusBar().currentMessage()
    )
    assert fenster.alle_speichern()
    assert unit.read_text(encoding="utf-8") == text


def test_methode_aus_dem_designer_zaehlt_nicht_als_fremde_aenderung(
    hauptfenster_bauen,  # noqa: ANN001
    tmp_path: Path,
    antworten: list[str],
) -> None:
    ordner = tmp_path / "Rechner"
    shutil.copytree(_BEISPIELE / "03_Taschenrechner", ordner)
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(ordner / "03_Taschenrechner.natter")
    unit = ordner / "u_main.py"
    editor = fenster.datei_oeffnen(unit)
    _anhaengen(editor, "\n# noch nicht gespeichert\n")
    fenster.designer_oeffnen(ordner / "u_main.pfm")
    canvas = fenster._aktueller_canvas
    knopf = canvas.komponente_platzieren(Button, 10, 10)

    assert canvas.ereignis_handler_erzeugen(knopf)
    assert fenster.alle_speichern()
    assert antworten == []
    assert "# noch nicht gespeichert" in unit.read_text(encoding="utf-8")


@pytest.mark.parametrize("ueberschreiben", [False, True])
def test_designer_fragt_vor_dem_ueberschreiben_der_pfm(
    qtbot,  # noqa: ANN001
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    ueberschreiben: bool,
) -> None:
    ordner = tmp_path / "Rechner"
    shutil.copytree(_BEISPIELE / "03_Taschenrechner", ordner)
    pfm = ordner / "u_main.pfm"
    formular = formular_fuer_designer_laden(pfm)
    qtbot.addWidget(formular._qwidget)
    canvas = DesignerCanvas(formular, pfm_pfad=pfm)
    gefragt: list[bool] = []

    def fragen(self) -> bool:  # noqa: ANN001
        gefragt.append(True)
        return ueberschreiben

    monkeypatch.setattr(
        DesignerCanvas, "_von_aussen_geaendert_fragen", fragen, raising=False
    )
    canvas.komponente_platzieren(Button, 10, 10)
    canvas.jetzt_schreiben()
    assert gefragt == []
    von_aussen = pfm.read_text(encoding="utf-8").replace(
        '"format"', '"format"   ', 1
    )
    pfm.write_text(von_aussen, encoding="utf-8")

    canvas.komponente_platzieren(Button, 10, 60)
    canvas.jetzt_schreiben()
    canvas.komponente_platzieren(Button, 10, 110)
    canvas.jetzt_schreiben()

    # Nach „Nein“ fragt die nächste Änderung nicht noch einmal.
    assert gefragt == [True]
    assert (pfm.read_text(encoding="utf-8") == von_aussen) != ueberschreiben
    assert canvas.ungespeichert != ueberschreiben


def test_zweites_oeffnen_desselben_projekts_zeigt_einen_hinweis(
    hauptfenster_bauen,  # noqa: ANN001
    projekt: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ide.project import sperre

    hinweise: list[str] = []
    monkeypatch.setattr(
        HauptFenster,
        "_projekt_schon_offen_melden",
        lambda self, name, wer=None: hinweise.append(name),
        raising=False,
    )
    datei = projekt / sperre.SPERRDATEI
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(projekt / "01_Begruessung.natter")
    assert hinweise == []
    assert datei.read_text(encoding="utf-8").split()[0] == str(os.getpid())

    # Ein anderes Natter hält das Projekt offen.
    eltern = os.getppid()
    datei.write_text(
        f"{eltern} {sperre._startzeit(eltern) or 0}\n", encoding="utf-8"
    )
    zweites = hauptfenster_bauen()
    zweites.projekt_oeffnen(projekt / "01_Begruessung.natter")
    assert len(hinweise) == 1
    zweites.close()
    assert datei.read_text(encoding="utf-8").split()[0] == str(eltern)

    # Ohne das andere Natter bleibt es beim eigenen, und beim Schließen
    # verschwindet die Sperrdatei.
    datei.unlink()
    fenster.projekt_oeffnen(projekt / "01_Begruessung.natter")
    assert datei.exists()
    fenster.close()
    assert not datei.exists()
    assert len(hinweise) == 1


def test_sperre_eines_anderen_rechners_zeigt_den_hinweis_bis_sie_veraltet(
    hauptfenster_bauen,  # noqa: ANN001
    projekt: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Punkt 322: ein Projekt in einem Tauschordner, das an Rechner
    PC-R07 offen ist. Die Prozessnummer dort ist hier bedeutungslos,
    auch wenn sie zufällig die eigene ist."""
    import time

    from ide.project import sperre

    gemeldet: list[sperre.Besitzer | None] = []
    monkeypatch.setattr(
        HauptFenster,
        "_projekt_schon_offen_melden",
        lambda self, name, wer=None: gemeldet.append(wer),
        raising=False,
    )
    datei = projekt / sperre.SPERRDATEI

    def fremde_sperre(alter: float) -> str:
        text = (
            f"{os.getpid()} 1\nrechner=PC-R07\nkonto=mueller.anna\n"
            f"erneuert={int(time.time() - alter)}\n"
        )
        datei.write_text(text, encoding="utf-8")
        return text

    fremd = fremde_sperre(60)
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(projekt / "01_Begruessung.natter")
    assert len(gemeldet) == 1
    wer = gemeldet[0]
    assert wer is not None and wer.anderer_rechner
    assert (wer.rechner, wer.konto) == ("PC-R07", "mueller.anna")
    # Weder überschrieben noch beim Schließen entfernt.
    assert datei.read_text(encoding="utf-8") == fremd
    fenster._sperre_erneuern()
    assert datei.read_text(encoding="utf-8") == fremd
    fenster.projekt_schliessen()
    assert datei.read_text(encoding="utf-8") == fremd

    # Liegengeblieben: seit über einer halben Stunde nicht erneuert.
    fremde_sperre(sperre.ZEITGRENZE + 60)
    fenster.projekt_oeffnen(projekt / "01_Begruessung.natter")
    assert len(gemeldet) == 1
    eigene = datei.read_text(encoding="utf-8")
    assert f"rechner={sperre.rechnername()}" in eigene


@pytest.mark.parametrize("weg", ["natter", "explorer"])
def test_kopie_eines_offenen_projekts_erbt_keine_sperre(
    hauptfenster_bauen,  # noqa: ANN001
    projekt: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    weg: str,
) -> None:
    """Punkt 327: Die Aufgabe ist am Rechner der Lehrkraft offen, und
    eine Schülerin arbeitet an einer Kopie. Natter kopiert die
    Sperrdatei nicht mit; im Explorer kommt sie mit, gilt in der Kopie
    aber nicht, weil darin der Ordner des Originals steht. Die Sperre
    im Original zählt weiter."""
    import time

    from ide.project import sperre
    from ide.shell.startbild import beispiel_kopieren

    gemeldet: list[sperre.Besitzer | None] = []
    monkeypatch.setattr(
        HauptFenster,
        "_projekt_schon_offen_melden",
        lambda self, name, wer=None: gemeldet.append(wer),
        raising=False,
    )
    fremd = (
        f"4711 1\nrechner=LEHRER-PC\nkonto=lehrer\n"
        f"erneuert={int(time.time())}\n"
    )
    if weg == "natter":
        # Die Probe aus dem Punkt: eine Sperrdatei ohne Ordnerangabe.
        (projekt / sperre.SPERRDATEI).write_text(fremd, encoding="utf-8")
        datei = beispiel_kopieren(
            projekt / "01_Begruessung.natter", tmp_path / "Dokumente"
        )
    else:
        fremd += f"ordner={projekt.resolve()}\n"
        (projekt / sperre.SPERRDATEI).write_text(fremd, encoding="utf-8")
        kopie = tmp_path / "Dokumente" / projekt.name
        shutil.copytree(projekt, kopie)
        datei = kopie / "01_Begruessung.natter"

    assert sperre.anderer_besitzer(projekt) is not None
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(datei)
    assert gemeldet == []
    eigene = (datei.parent / sperre.SPERRDATEI).read_text(encoding="utf-8")
    assert eigene.split()[0] == str(os.getpid())
    assert f"rechner={sperre.rechnername()}" in eigene
    assert (projekt / sperre.SPERRDATEI).read_text(
        encoding="utf-8"
    ) == fremd
