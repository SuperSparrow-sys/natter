"""Ein Fehler in Natter selbst endet in einer Meldung (M11, Abschnitt 5).

Dafür gab es bis hierher gar nichts. Stürzt etwas in einem Slot ab,
schreibt Python den Traceback nach `stderr` – und die gebaute
`Natter.exe` läuft ohne Konsolenfenster. Auf einem Schulrechner hieß das:
das Fenster ist weg, und niemand erfährt, warum.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ide import fehlermeldung


@pytest.fixture
def protokoll(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    pfad = tmp_path / "natter-fehler.log"
    monkeypatch.setattr(fehlermeldung, "protokoll_pfad", lambda: pfad)
    return pfad


def _fehler() -> tuple[type[BaseException], BaseException, object]:
    try:
        raise ValueError("etwas ging schief")
    except ValueError:
        return sys.exc_info()


def test_der_bericht_enthaelt_die_stelle_und_die_meldung() -> None:
    art, wert, spur = _fehler()

    text = fehlermeldung.bericht(art, wert, spur)

    assert "ValueError" in text
    assert "etwas ging schief" in text
    assert "test_fehlermeldung.py" in text


def test_der_fehler_wird_mitgeschrieben(protokoll: Path, qtbot, monkeypatch) -> None:
    """Die Protokolldatei ist das, womit eine Lehrkraft etwas anfangen
    kann – die Meldung auf dem Bildschirm nennt ihren Pfad."""
    gezeigt: list[object] = []
    monkeypatch.setattr(
        fehlermeldung.QMessageBox, "exec", lambda selbst: gezeigt.append(selbst)
    )

    fehlermeldung.fehler_melden(*_fehler())

    assert protokoll.exists()
    inhalt = protokoll.read_text(encoding="utf-8")
    assert "etwas ging schief" in inhalt
    assert gezeigt, "Es wurde keine Meldung gezeigt."


def test_die_meldung_sagt_was_zu_tun_ist(protokoll: Path, qtbot, monkeypatch) -> None:
    kaesten: list[object] = []
    monkeypatch.setattr(
        fehlermeldung.QMessageBox, "exec", lambda selbst: kaesten.append(selbst)
    )

    fehlermeldung.fehler_melden(*_fehler())

    kasten = kaesten[0]
    assert "Natter" in kasten.text()
    assert "ValueError" in kasten.text()
    hinweis = kasten.informativeText()
    assert "nicht in deinem Programm" in hinweis
    assert "Strg+S" in hinweis
    assert str(protokoll) in hinweis
    # Der Traceback bleibt eingeklappt: er hilft der Lehrkraft, nicht
    # der Schülerin.
    assert "ValueError" in kasten.detailedText()


def test_ein_zweiter_fehler_haengt_an_statt_zu_ueberschreiben(
    protokoll: Path, qtbot, monkeypatch
) -> None:
    monkeypatch.setattr(fehlermeldung.QMessageBox, "exec", lambda selbst: None)

    fehlermeldung.fehler_melden(*_fehler())
    fehlermeldung.fehler_melden(*_fehler())

    # Jeder Traceback nennt die Meldung zweimal (Zeile und Schluss) -
    # gezählt wird deshalb die Trennzeile mit dem Zeitstempel.
    assert protokoll.read_text(encoding="utf-8").count("=====") == 4


def test_ohne_schreibrecht_kommt_die_meldung_trotzdem(
    tmp_path: Path, qtbot, monkeypatch
) -> None:
    """Auf einem Schulrechner kann das Schreiben scheitern – die Meldung
    ist das Wichtigere und darf daran nicht hängen."""
    monkeypatch.setattr(
        fehlermeldung, "protokoll_pfad", lambda: tmp_path / "gibtsnicht" / "x.log"
    )

    def _verweigern(*_a, **_k):
        raise OSError("kein Schreibrecht")

    monkeypatch.setattr(Path, "mkdir", _verweigern)
    kaesten: list[object] = []
    monkeypatch.setattr(
        fehlermeldung.QMessageBox, "exec", lambda selbst: kaesten.append(selbst)
    )

    fehlermeldung.fehler_melden(*_fehler())

    assert kaesten, "Ohne Protokolldatei kam gar keine Meldung."
    assert "Protokolldatei:" not in kaesten[0].informativeText()


def test_der_haken_haengt_sich_ein(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "excepthook", sys.__excepthook__)

    fehlermeldung.fehlerhaken_einrichten()

    assert sys.excepthook is fehlermeldung.fehler_melden
