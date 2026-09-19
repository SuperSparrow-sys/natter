"""Tests für den Prüfungsmodus (M11, Abschnitt 6). Headless.

Vom Nutzer gefordert: Natter wird im Unterricht auch in
Leistungssituationen benutzt, und dann darf das Programm nicht die
halbe Aufgabe lösen.

Zwei Eigenschaften sind entscheidend und werden deshalb am genauesten
geprüft: er muss einen **Neustart überstehen** – sonst wäre er mit
einem Schließen und Öffnen ausgehebelt – und er muss **von selbst
auslaufen**, damit kein vergessener Modus einen Schulrechner sperrt.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

from ide.debugger.fehlerkatalog import Fehlermeldung
from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.pruefungsmodus import (
    DAUER,
    ENDE_SCHLUESSEL,
    beenden,
    laeuft,
    restzeit,
    restzeit_text,
    starten,
)
from ide.shell.hauptfenster import HauptFenster

JETZT = datetime(2026, 9, 19, 9, 0, 0)


@pytest.fixture
def werte(tmp_path: Path) -> QSettings:
    """Eigene Einstellungsdatei – ein Test darf den echten Rechner
    nicht vier Stunden in den Prüfungsmodus versetzen."""
    return QSettings(str(tmp_path / "pruefung.ini"), QSettings.Format.IniFormat)


@pytest.fixture
def echte_einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    """Legt auch die IDE-weite Fassung auf eine Testdatei um, damit die
    Oberflächen-Tests nicht in die echten Einstellungen schreiben."""
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import ide.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


# -- Grundverhalten ------------------------------------------------------


def test_am_anfang_laeuft_keine_pruefung(werte: QSettings) -> None:
    assert laeuft(werte) is False
    assert restzeit(werte) is None
    assert restzeit_text(werte) == ""


def test_nach_dem_start_laeuft_er(werte: QSettings) -> None:
    starten(werte, jetzt=JETZT)

    assert laeuft(werte, jetzt=JETZT + timedelta(hours=1)) is True


def test_er_laeuft_nach_vier_stunden_von_selbst_aus(werte: QSettings) -> None:
    """Niemand soll daran denken müssen, ihn abzuschalten, und ein
    vergessener Modus darf keinen Schulrechner auf Dauer sperren."""
    starten(werte, jetzt=JETZT)

    assert laeuft(werte, jetzt=JETZT + DAUER - timedelta(minutes=1)) is True
    assert laeuft(werte, jetzt=JETZT + DAUER + timedelta(seconds=1)) is False


def test_er_uebersteht_einen_neustart(tmp_path: Path) -> None:
    """Der Kern der Sache: ein Schalter im Speicher wäre mit einem
    Schließen und Öffnen ausgehebelt."""
    pfad = str(tmp_path / "pruefung.ini")
    starten(QSettings(pfad, QSettings.Format.IniFormat), jetzt=JETZT)

    # Frisch geladen, als wäre Natter neu gestartet worden
    danach = QSettings(pfad, QSettings.Format.IniFormat)

    assert laeuft(danach, jetzt=JETZT + timedelta(hours=2)) is True


def test_gespeichert_wird_das_ende_nicht_ein_schalter(werte: QSettings) -> None:
    starten(werte, jetzt=JETZT)

    gespeichert = werte.value(ENDE_SCHLUESSEL, "", type=str)

    assert gespeichert.startswith("2026-09-19T13:00")


def test_ein_kaputter_wert_sperrt_nicht(werte: QSettings) -> None:
    """Lieber die Werkzeuge freigeben, als eine kaputte
    Einstellungsdatei zu einer Dauersperre werden zu lassen."""
    werte.setValue(ENDE_SCHLUESSEL, "kein Datum")

    assert laeuft(werte) is False


def test_er_laesst_sich_beenden(werte: QSettings) -> None:
    starten(werte, jetzt=JETZT)

    beenden(werte)

    assert laeuft(werte, jetzt=JETZT + timedelta(minutes=5)) is False


def test_die_restzeit_steht_als_text_bereit(werte: QSettings) -> None:
    """Wer nicht sieht, dass der Modus an ist, sucht den Fehler bei
    sich."""
    starten(werte, jetzt=JETZT)

    text = restzeit_text(werte, jetzt=JETZT + timedelta(hours=1, minutes=15))

    assert text == "Prüfungsmodus – noch 2:45 h"


# -- Keine Lösungsvorschläge ---------------------------------------------


def _meldung() -> Fehlermeldung:
    return Fehlermeldung(
        ueberschrift="Fehler",
        wo="u_main.py, Zeile 12, in b_start_click",
        quelltext="    print(zaehler)",
        markierung="          ^^^^^^^",
        was="Der Name zaehler ist an dieser Stelle nicht bekannt.",
        pruefe="Ist der Name richtig geschrieben? Wurde er vorher zugewiesen?",
    )


def test_normalerweise_steht_pruefe_in_der_meldung(
    echte_einstellungen: QSettings,
) -> None:
    text = _meldung().als_text()

    assert "Prüfe:" in text
    assert "richtig geschrieben" in text


def test_im_pruefungsmodus_faellt_pruefe_weg(
    echte_einstellungen: QSettings,
) -> None:
    """„Prüfe“ ist genau der Teil, der weiterhilft – und genau deshalb
    gehört er in einer Leistungssituation nicht dazu."""
    starten(echte_einstellungen)

    text = _meldung().als_text()

    assert "Prüfe:" not in text
    assert "richtig geschrieben" not in text


def test_wo_und_was_bleiben_auch_im_pruefungsmodus(
    echte_einstellungen: QSettings,
) -> None:
    """Eine Schülerin soll sehen, dass und wo etwas schiefgegangen ist
    – nur nicht, woran es liegen könnte."""
    starten(echte_einstellungen)

    text = _meldung().als_text()

    assert "Wo:" in text
    assert "Zeile 12" in text
    assert "Was:" in text
    assert "nicht bekannt" in text


# -- Keine Quelltexterzeugung --------------------------------------------


@pytest.mark.parametrize("typ", ["class", "struktogramm"])
def test_quelltexterzeugung_ist_normalerweise_moeglich(
    echte_einstellungen: QSettings, tmp_path: Path, typ: str
) -> None:
    fenster = DiagrammFenster(diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", "d"))

    assert fenster.aktionen["Quelltext/Erzeugen …"].isEnabled() is True


@pytest.mark.parametrize("typ", ["class", "struktogramm"])
def test_im_pruefungsmodus_ist_sie_gesperrt(
    echte_einstellungen: QSettings, tmp_path: Path, typ: str
) -> None:
    """Aus einem Klassendiagramm Python erzeugen zu lassen wäre in
    einer Leistungssituation die halbe Aufgabe."""
    starten(echte_einstellungen)

    fenster = DiagrammFenster(diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", "d"))

    aktion = fenster.aktionen["Quelltext/Erzeugen …"]
    assert aktion.isEnabled() is False
    assert "Prüfungsmodus" in aktion.toolTip()


def test_der_eintrag_bleibt_sichtbar(echte_einstellungen: QSettings, tmp_path: Path) -> None:
    """Ein spurlos verschwundener Menüeintrag wäre verwirrender als ein
    erklärter."""
    starten(echte_einstellungen)

    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))

    assert fenster.aktionen["Quelltext/Erzeugen …"].isVisible() is True


def test_zeichnen_bleibt_moeglich(echte_einstellungen: QSettings, tmp_path: Path) -> None:
    """Der Modus nimmt Werkzeug weg, keine Bedienbarkeit."""
    starten(echte_einstellungen)
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))

    form = fenster.zeichenflaeche.form_platzieren("class", 200, 200)

    assert form in fenster.zeichenflaeche.formen
    assert fenster.aktionen["Datei/Speichern"].isEnabled() is True


def test_die_restzeit_steht_in_der_statusleiste_des_diagramms(
    echte_einstellungen: QSettings, tmp_path: Path
) -> None:
    starten(echte_einstellungen)

    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))

    assert "Prüfungsmodus" in fenster.statusBar().currentMessage()


# -- Im Hauptfenster -----------------------------------------------------


def test_das_werkzeugmenue_bietet_den_start(echte_einstellungen: QSettings, qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    titel = [a.text() for a in fenster.menue("Werkzeuge").actions()]

    assert "Prüfungsmodus starten …" in titel


def test_ohne_bestaetigung_startet_er_nicht(
    echte_einstellungen: QSettings, qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Er lässt sich vier Stunden lang nicht abschalten – das fragt man
    vorher."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.No),
    )

    assert fenster._pruefungsmodus_aktion() is False
    assert laeuft(echte_einstellungen) is False


def test_mit_bestaetigung_startet_er(
    echte_einstellungen: QSettings, qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )

    assert fenster._pruefungsmodus_aktion() is True
    assert laeuft(echte_einstellungen) is True
    assert "Prüfungsmodus" in fenster.pruefungsanzeige.text()


def test_ein_zweiter_start_verlaengert_nicht(
    echte_einstellungen: QSettings, qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ein zweiter Start würde die Zeit verlängern – das will in einer
    Klausur niemand."""
    starten(echte_einstellungen)
    vorher = echte_einstellungen.value(ENDE_SCHLUESSEL, "", type=str)
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )

    assert fenster._pruefungsmodus_aktion() is False
    assert echte_einstellungen.value(ENDE_SCHLUESSEL, "", type=str) == vorher


def test_die_anzeige_bleibt_leer_ohne_pruefung(echte_einstellungen: QSettings, qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    assert fenster.pruefungsanzeige.text() == ""
