"""Punkt 306: „Projekt → Projekt schließen“ schließt das Projekt,
ohne ein anderes zu öffnen - mit derselben Nachfrage wie beim
Wechsel."""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from ide.project import projekt_erzeugen
from ide.shell.hauptfenster import HauptFenster


def _mit_projekt(hauptfenster_bauen, tmp_path: Path) -> HauptFenster:
    projekt = projekt_erzeugen("gui", tmp_path / "Ampel", "Ampel")
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(projekt.ordner / "Ampel.natter")
    fenster.designer_oeffnen(projekt.ordner / "u_main.pfm")
    fenster.datei_oeffnen(projekt.ordner / "u_main.py")
    return fenster


def test_menueeintrag_steht_im_projektmenue(hauptfenster_bauen) -> None:
    fenster = hauptfenster_bauen()
    texte = [a.text() for a in fenster.menue("Projekt").actions()]

    assert "Projekt schließen" in texte


def test_projekt_schliessen_zeigt_die_startseite(
    hauptfenster_bauen, tmp_path: Path
) -> None:
    fenster = _mit_projekt(hauptfenster_bauen, tmp_path)
    assert fenster.editor_tabs.count() >= 2
    assert fenster.objektinspektor.baum.topLevelItemCount() > 0

    fenster.aktionen["projekt.schliessen"].qaction.trigger()

    assert fenster.projekt is None
    assert fenster.mitte.currentWidget() is fenster.startbild
    assert fenster.editor_tabs.count() == 0
    assert fenster.objektinspektor.formular is None
    assert fenster.objektinspektor.baum.topLevelItemCount() == 0
    assert fenster.objektinspektor.eigenschaften_tabelle.rowCount() == 0
    sichtbar = [
        fenster.explorer.topLevelItem(i)
        for i in range(fenster.explorer.topLevelItemCount())
        if not fenster.explorer.topLevelItem(i).isHidden()
    ]
    assert sichtbar == []
    assert "geschlossen" in fenster.statusBar().currentMessage()


def test_abbrechen_laesst_das_projekt_offen(
    hauptfenster_bauen, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = _mit_projekt(hauptfenster_bauen, tmp_path)
    editor = fenster.editor_tabs.currentWidget()
    editor.insertPlainText("# geändert\n")
    monkeypatch.setattr(
        HauptFenster,
        "_vor_dem_schliessen_fragen",
        lambda self, namen: QMessageBox.StandardButton.Cancel,
    )

    assert not fenster.projekt_schliessen()

    assert fenster.projekt is not None
    assert fenster.editor_tabs.count() >= 2


def test_ohne_projekt_nur_ein_hinweis(hauptfenster_bauen) -> None:
    fenster = hauptfenster_bauen()

    assert not fenster.projekt_schliessen()
    assert "kein Projekt" in fenster.statusBar().currentMessage()


def _formular_nicht_geschrieben(
    fenster: HauptFenster, monkeypatch: pytest.MonkeyPatch
):
    """Setzt im Designer einen Knopf, dessen Änderung nicht in die
    `.pfm` kommt, wie bei einem abgezogenen USB-Stick."""
    import ide.designer.canvas as modul
    from pcl import Button

    canvas = fenster._aktueller_canvas
    monkeypatch.setattr(
        modul.DesignerCanvas, "_meldung_zeigen", lambda self, text: None
    )

    def verweigert(*_a, **_k) -> None:
        raise OSError(2, "weg")

    with monkeypatch.context() as m:
        m.setattr(modul, "formular_als_pfm_speichern", verweigert)
        canvas.komponente_platzieren(Button, 32, 128)
        canvas.jetzt_schreiben()
    assert canvas.ungespeichert
    return canvas


@pytest.mark.parametrize("weg", ["fenster", "projekt", "wechsel"])
def test_ungeschriebenes_formular_steht_in_der_frage_und_abbrechen_haelt_es(
    hauptfenster_bauen, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    weg: str,
) -> None:
    """Punkt 673: ein Formular, das nicht in die `.pfm` kam, steht in
    der gemeinsamen Nachfrage beim Schließen von Fenster und Projekt
    und beim Wechsel. „Abbrechen“ lässt Projekt und Reiter offen, und
    der Reiter fragt nicht noch einmal."""
    fenster = _mit_projekt(hauptfenster_bauen, tmp_path)
    fenster.designer_oeffnen(tmp_path / "Ampel" / "u_main.pfm")
    canvas = _formular_nicht_geschrieben(fenster, monkeypatch)
    anderes = projekt_erzeugen("console", tmp_path / "Zwei", "Zwei")
    gefragt: list[list[str]] = []
    monkeypatch.setattr(
        HauptFenster, "_vor_dem_schliessen_fragen",
        lambda self, namen: gefragt.append(list(namen))
        or QMessageBox.StandardButton.Cancel,
    )
    reiterfrage: list[int] = []
    monkeypatch.setattr(
        HauptFenster, "_reiter_schliessen_fragen",
        lambda self: reiterfrage.append(1) or QMessageBox.StandardButton.Cancel,
    )
    fenster.show()

    if weg == "fenster":
        fenster.close()
    elif weg == "projekt":
        fenster.projekt_schliessen()
    else:
        fenster.projekt_oeffnen(anderes.ordner / "Zwei.natter")

    assert gefragt == [["u_main.pfm"]]
    assert reiterfrage == []
    assert fenster.isVisible()
    assert fenster.projekt is not None and fenster.projekt.name == "Ampel"
    assert fenster._tab_index(canvas.formular._qwidget) != -1
    assert canvas.ungespeichert


def test_ungeschriebenes_formular_kommt_in_die_sicherung_und_zurueck(
    hauptfenster_bauen, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Punkt 673: die Formularänderung steht als eigener Eintrag in der
    Sicherung, und ein Natter nach dem Absturz stellt sie wieder her."""
    from ide.project import sicherung

    fenster = _mit_projekt(hauptfenster_bauen, tmp_path)
    fenster.designer_oeffnen(tmp_path / "Ampel" / "u_main.pfm")
    _formular_nicht_geschrieben(fenster, monkeypatch)
    ordner = tmp_path / "Ampel"
    vorher = (ordner / "u_main.pfm").read_text(encoding="utf-8")

    assert fenster._sicherung_bald.isActive()
    fenster._sicherung_bald.timeout.emit()

    gesichert = sicherung.lesen(sicherung.pfad_fuer(ordner, "Ampel"))
    eintrag = next(e for e in gesichert.eintraege if e.pfad == "u_main.pfm")
    assert eintrag.art == "form" and '"top": 128' in eintrag.text
    assert (ordner / "u_main.pfm").read_text(encoding="utf-8") == vorher

    sicherung.fenster_geschlossen(fenster._sicherung_herkunft)
    monkeypatch.setattr(
        HauptFenster, "_sicherung_wiederherstellen_fragen",
        lambda self, text: True,
    )
    danach = hauptfenster_bauen()
    danach.projekt_oeffnen(ordner / "Ampel.natter")

    assert '"top": 128' in (ordner / "u_main.pfm").read_text(encoding="utf-8")
    assert "128" in (ordner / "u_main_design.py").read_text(encoding="utf-8")
    assert danach._aktueller_canvas is not None


def test_von_aussen_geaenderte_pfm_wird_im_designer_neu_geladen(
    hauptfenster_bauen, tmp_path: Path,
) -> None:
    """Punkt 673: ein zweites Natter schreibt die `.pfm`. Ein Designer
    ohne eigene ungeschriebene Änderung lädt sie beim Wechsel ins
    Fenster neu, statt beim nächsten Schreiben zu fragen."""
    import json

    fenster = _mit_projekt(hauptfenster_bauen, tmp_path)
    pfm = tmp_path / "Ampel" / "u_main.pfm"
    fenster.designer_oeffnen(pfm)
    daten = json.loads(pfm.read_text(encoding="utf-8"))
    daten.setdefault("children", []).append({
        "name": "b_von_a", "type": "Button",
        "properties": {"left": 8, "top": 8},
    })
    pfm.write_text(json.dumps(daten), encoding="utf-8")

    neu_laden = getattr(
        fenster, "_von_aussen_geaenderte_formulare_neu_laden", None
    )
    if neu_laden is not None:
        neu_laden()

    canvas = fenster._aktueller_canvas
    assert canvas is not None and not canvas.ungespeichert
    assert hasattr(canvas.formular, "b_von_a")


@pytest.mark.parametrize("beenden", [True, False], ids=["beenden", "abbrechen"])
@pytest.mark.parametrize("weg", ["schliessen", "wechsel"])
def test_laufendes_programm_beim_schliessen_und_wechsel_des_projekts(
    hauptfenster_bauen, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    weg: str, beenden: bool,
) -> None:
    """Punkt 695: Schließen und Wechseln des Projekts fragen bei
    laufendem Programm wie das Schließen des Fensters. Nach „Beenden“
    endet das Programm, nach „Abbrechen“ bleibt alles, wie es war."""
    fenster = _mit_projekt(hauptfenster_bauen, tmp_path)
    anderes = projekt_erzeugen("console", tmp_path / "Zwei", "Zwei")
    laeuft = [True]
    gefragt: list[str] = []
    monkeypatch.setattr(HauptFenster, "_programm_laeuft", lambda self: laeuft[0])
    monkeypatch.setattr(
        HauptFenster, "_laufendes_programm_fragen",
        lambda self: gefragt.append(
            getattr(self, "_programm_frage_anlass", ("",))[0]
        ) or beenden,
    )
    echt = HauptFenster.kindprozesse_beenden

    def beenden_merken(self: HauptFenster) -> int:
        laeuft[0] = False
        return echt(self)

    monkeypatch.setattr(HauptFenster, "kindprozesse_beenden", beenden_merken)

    if weg == "schliessen":
        fenster.projekt_schliessen()
    else:
        fenster.projekt_oeffnen(anderes.ordner / "Zwei.natter")

    assert len(gefragt) == 1 and "Projekt" in gefragt[0]
    assert laeuft[0] is not beenden
    if beenden:
        erwartet = None if weg == "schliessen" else "Zwei"
        assert (fenster.projekt and fenster.projekt.name) == erwartet
    else:
        assert fenster.projekt.name == "Ampel"
