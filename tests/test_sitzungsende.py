"""Abmelden und Herunterfahren bei offenem Natter (Punkt 338).

Qt 6 ruft dabei kein `closeEvent` auf, sondern sendet nur
`commitDataRequest` und `aboutToQuit`. Geprüft wird ohne echtes
Abmelden: `commitDataRequest` lässt sich nur mit einem echten
`QSessionManager` senden, den allein Qt anlegt; der Test ruft den
verbundenen Empfänger deshalb mit einer Attrappe auf. `aboutToQuit`
wird tatsächlich gesendet."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from ide.project.sperre import SPERRDATEI
from ide.shell.hauptfenster import HauptFenster


class _Sitzung:
    """Steht für den `QSessionManager` beim Abmelden."""

    def __init__(self, *, rueckfrage_erlaubt: bool) -> None:
        self.rueckfrage_erlaubt = rueckfrage_erlaubt
        self.abgebrochen = False

    def allowsInteraction(self) -> bool:  # noqa: N802
        return self.rueckfrage_erlaubt

    def release(self) -> None:
        pass

    def cancel(self) -> None:
        self.abgebrochen = True


@pytest.fixture
def fenster(hauptfenster_bauen, tmp_path: Path) -> HauptFenster:
    (tmp_path / "main.py").write_text("a = 1\n", encoding="utf-8")
    natter = tmp_path / "t.natter"
    natter.write_text(json.dumps({
        "format": "natter-project/1", "name": "T", "type": "console",
        "main": "main.py",
    }), encoding="utf-8")
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(natter)
    fenster.show()
    editor = fenster.datei_oeffnen(tmp_path / "main.py")
    editor.setPlainText("a = 42\n")
    editor.document().setModified(True)
    return fenster


@pytest.mark.parametrize(
    ("rueckfrage_erlaubt", "antwort", "abgebrochen", "text"),
    [
        (True, QMessageBox.StandardButton.Cancel, True, "a = 1\n"),
        (True, QMessageBox.StandardButton.Save, False, "a = 42\n"),
        (True, QMessageBox.StandardButton.Discard, False, "a = 1\n"),
        (False, None, False, "a = 42\n"),
    ],
    ids=["abbrechen", "speichern", "verwerfen", "ohne_rueckfrage"],
)
def test_abmelden_fragt_wie_beim_schliessen(
    fenster: HauptFenster, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch, rueckfrage_erlaubt: bool,
    antwort: QMessageBox.StandardButton | None, abgebrochen: bool,
    text: str,
) -> None:
    gefragt = []

    def fragen(self, namen):  # noqa: ANN001, ANN202
        gefragt.append(namen)
        return antwort

    monkeypatch.setattr(HauptFenster, "_vor_dem_schliessen_fragen", fragen)
    sitzung = _Sitzung(rueckfrage_erlaubt=rueckfrage_erlaubt)

    fenster._sitzungsende_klaeren(sitzung)

    assert gefragt == ([["main.py"]] if rueckfrage_erlaubt else [])
    assert sitzung.abgebrochen is abgebrochen
    assert (tmp_path / "main.py").read_text(encoding="utf-8") == text
    # Aufgeräumt wird erst mit `aboutToQuit`: bricht ein anderes
    # Programm das Abmelden ab, arbeitet Natter weiter.
    assert fenster.isVisible()
    assert (tmp_path / SPERRDATEI).exists()


def test_abmelden_haengt_am_signal_der_anwendung(
    fenster: HauptFenster,
) -> None:
    """Der Empfänger ist tatsächlich mit `commitDataRequest`
    verbunden, und das Schließen löst ihn wieder."""
    signal = "2commitDataRequest(QSessionManager&)"
    anwendung = QApplication.instance()
    vorher = anwendung.receivers(signal)

    fenster.close()

    assert vorher >= 1
    assert anwendung.receivers(signal) == vorher - 1


def test_ende_der_sitzung_raeumt_auf(
    fenster: HauptFenster, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    beendet = []
    monkeypatch.setattr(
        HauptFenster, "kindprozesse_beenden",
        lambda self: beendet.append(self) or 0,
    )
    assert (tmp_path / SPERRDATEI).exists()

    QApplication.instance().aboutToQuit.emit()

    assert not (tmp_path / SPERRDATEI).exists()
    assert beendet == [fenster]
    # Danach ist das Fenster von der Anwendung gelöst; ein zweites
    # Signal räumt nicht noch einmal auf.
    QApplication.instance().aboutToQuit.emit()
    assert beendet == [fenster]


def test_windows_nennt_beim_abmelden_den_grund(
    fenster: HauptFenster, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Punkt 344: solange die Frage offen ist, steht auf der Seite von
    Windows mit „Trotzdem abmelden“, dass ungespeicherte Änderungen
    verloren gehen. Danach wird der Grund wieder entfernt.

    Windows selbst wird dabei nicht angesprochen: unter `offscreen`
    liefert `_user32` nichts, und der Test setzt eine Attrappe ein."""
    from ide.shell import abmeldegrund

    assert abmeldegrund._user32() is None
    ablauf: list[tuple] = []

    class _User32:
        def ShutdownBlockReasonCreate(self, kennung, grund):  # noqa: ANN001, ANN202, N802
            ablauf.append(("gesetzt", kennung, grund))
            return 1

        def ShutdownBlockReasonDestroy(self, kennung):  # noqa: ANN001, ANN202, N802
            ablauf.append(("entfernt", kennung))
            return 1

    def fragen(self, namen):  # noqa: ANN001, ANN202
        ablauf.append(("gefragt",))
        return QMessageBox.StandardButton.Cancel

    monkeypatch.setattr(abmeldegrund, "_user32", _User32)
    monkeypatch.setattr(HauptFenster, "_vor_dem_schliessen_fragen", fragen)

    fenster._sitzungsende_klaeren(_Sitzung(rueckfrage_erlaubt=True))

    kennung = int(fenster.winId())
    assert ablauf == [
        ("gesetzt", kennung, abmeldegrund.GRUND),
        ("gefragt",),
        ("entfernt", kennung),
    ]
    assert "Ungespeicherte Änderungen" in abmeldegrund.GRUND
