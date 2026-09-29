"""Ein laufendes Programm beim Start und beim Schließen.

Punkt 429: F5 und Strg+F5 lehnen einen zweiten Start ab, egal über
welchen Weg das erste Programm lief. Punkt 433: wer Natter schließt,
während ein Programm läuft, wird vorher gefragt.

Das laufende Programm ist hier eine Attrappe. Ein echter Start
brauchte einen Prozess oder den Debugger und prüfte nichts, was die
Attrappe nicht auch prüft: ob Natter das Programm für laufend hält.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from ide.shell.hauptfenster import HauptFenster


class _Programm:
    """Steht für ein mit Strg+F5 gestartetes Programm, das läuft."""

    pid = 0

    def poll(self) -> int | None:
        return None


class _Sitzung:
    """Steht für ein mit F5 gestartetes Programm unter dem Debugger."""

    def __init__(self) -> None:
        self.beendet = False

    def beenden(self) -> None:
        self.beendet = True


def _projekt(ordner: Path) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text("pass\n", encoding="utf-8")
    datei = ordner / "test.natter"
    datei.write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Test",
                "type": "gui",
                "main": "main.py",
            }
        ),
        encoding="utf-8",
    )
    return datei


def _laufen_lassen(fenster: HauptFenster, weg: str) -> object:
    """Setzt das Fenster in den Zustand nach einem Start über `weg`."""
    if weg == "F5":
        fenster.debug_sitzung = _Sitzung()
        return fenster.debug_sitzung
    fenster.laufender_prozess = _Programm()
    return fenster.laufender_prozess


@pytest.mark.parametrize("zweiter", ["F5", "Strg+F5"])
@pytest.mark.parametrize("erster", ["F5", "Strg+F5"])
def test_ein_zweiter_start_wird_auf_jedem_weg_abgelehnt(
    hauptfenster, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    erster: str, zweiter: str,
) -> None:
    """Punkt 429: bis 0.4.2 sah F5 nur nach einer Debugger-Sitzung
    und Strg+F5 nur nach einem Prozess. Wer die Tasten wechselte,
    hatte zwei Fenster desselben Programms."""
    fenster = hauptfenster
    fenster.projekt_oeffnen(_projekt(tmp_path / "p"))
    # Jeder Start, der weiterkommt, erreicht die Prüfung vor dem
    # Start. Hier endet er dort, damit nichts wirklich startet.
    weitergekommen: list[str] = []

    def vorstart(self: HauptFenster) -> bool:
        weitergekommen.append(zweiter)
        return True

    monkeypatch.setattr(HauptFenster, "_vorstart_pruefung_blockiert", vorstart)
    erstes = _laufen_lassen(fenster, erster)

    try:
        if zweiter == "F5":
            fenster._projekt_mit_debugger_starten_aktion()
        else:
            fenster._projekt_starten_aktion()

        assert weitergekommen == []
        assert fenster.statusBar().currentMessage() == (
            "Test läuft bereits - zuerst über „Start → Stopp“ beenden."
        )
        assert erstes in (fenster.debug_sitzung, fenster.laufender_prozess)
    finally:
        fenster.debug_sitzung = None
        fenster.laufender_prozess = None


@pytest.mark.parametrize("weg", ["F5", "Strg+F5"])
@pytest.mark.parametrize("beenden", [False, True])
def test_schliessen_fragt_bei_laufendem_programm(
    hauptfenster, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    weg: str, beenden: bool,
) -> None:
    """Punkt 433: „Abbrechen“ lässt Natter und das Programm weiter
    laufen, „Beenden und schließen“ beendet beides. Gefragt wird vor
    der Frage nach ungespeicherten Dateien."""
    fenster = hauptfenster
    fenster.projekt_oeffnen(_projekt(tmp_path / "p"))
    fenster.show()
    fragen: list[str] = []

    def programm_fragen(self: HauptFenster) -> bool:
        fragen.append("programm")
        return beenden

    def speichern_fragen(
        self: HauptFenster, namen: list[str]
    ) -> QMessageBox.StandardButton:
        fragen.append("speichern")
        return QMessageBox.StandardButton.Discard

    beendet: list[object] = []
    monkeypatch.setattr(
        HauptFenster, "_laufendes_programm_fragen", programm_fragen
    )
    monkeypatch.setattr(
        HauptFenster, "_ungespeicherte_namen", lambda self: ["u_main.py"]
    )
    monkeypatch.setattr(
        HauptFenster, "_vor_dem_schliessen_fragen", speichern_fragen
    )
    monkeypatch.setattr(
        "ide.shell.hauptfenster.prozessbaum_beenden", beendet.append
    )
    programm = _laufen_lassen(fenster, weg)

    try:
        fenster.close()

        if beenden:
            assert fragen == ["programm", "speichern"]
            assert not fenster.isVisible()
            assert fenster.debug_sitzung is None
            assert fenster.laufender_prozess is None
            if weg == "F5":
                assert programm.beendet
            else:
                assert beendet == [programm]
        else:
            assert fragen == ["programm"]
            assert fenster.isVisible()
            assert programm in (
                fenster.debug_sitzung, fenster.laufender_prozess
            )
            assert beendet == []
    finally:
        fenster.debug_sitzung = None
        fenster.laufender_prozess = None


def test_ohne_laufendes_programm_fragt_schliessen_nicht(
    hauptfenster, monkeypatch: pytest.MonkeyPatch
) -> None:
    gefragt: list[bool] = []
    monkeypatch.setattr(
        HauptFenster, "_laufendes_programm_fragen",
        lambda self: gefragt.append(True) or False,
    )
    hauptfenster.show()

    hauptfenster.close()

    assert gefragt == []
    assert not hauptfenster.isVisible()


def test_am_ende_der_windows_sitzung_wird_nicht_gefragt(
    hauptfenster, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Beim Abmelden fragt Natter nur nach ungespeicherten Dateien;
    das Programm endet ohne Frage mit dem Aufräumen."""
    gefragt: list[bool] = []
    monkeypatch.setattr(
        HauptFenster, "_laufendes_programm_fragen",
        lambda self: gefragt.append(True) or False,
    )

    class _Verwalter:
        abgebrochen = False

        def allowsInteraction(self) -> bool:  # noqa: N802
            return True

        def release(self) -> None:
            pass

        def cancel(self) -> None:
            self.abgebrochen = True

    verwalter = _Verwalter()
    sitzung = _laufen_lassen(hauptfenster, "F5")

    hauptfenster._sitzungsende_klaeren(verwalter)
    hauptfenster._beim_beenden_aufraeumen()

    assert gefragt == []
    assert not verwalter.abgebrochen
    assert sitzung.beendet
    assert hauptfenster.debug_sitzung is None
