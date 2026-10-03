"""Woran ein Test gescheitert ist: Fehlerart, Ort und deutscher Text
im Testlauf (Punkt 661), sichtbar nach einem Klick im Test-Explorer
(Punkt 660)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ide.testrunner import tests_ausfuehren as ausfuehren

_RECHNEN = "def f(x):\n    return x.foo\n"

_TESTDATEI = '''\
import unittest

from rechnen import f


class TestGruende(unittest.TestCase):
    def test_mit_text(self):
        self.assertEqual(2, 3, "Größe stimmt nicht")

    def test_ausnahme(self):
        f(None)

    def test_ohne_text(self):
        self.assertEqual(2, 3)
'''


def _projekt(ordner: Path) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text("pass\n", encoding="utf-8")
    (ordner / "rechnen.py").write_text(_RECHNEN, encoding="utf-8")
    (ordner / "test_gruende.py").write_text(_TESTDATEI, encoding="utf-8")
    daten = {"format": "natter-project/1", "name": "Test", "type": "console", "main": "main.py"}
    pfad = ordner / "test.natter"
    pfad.write_text(json.dumps(daten), encoding="utf-8")
    return pfad


def test_eine_ausnahme_nennt_fehlerart_ort_und_deutschen_text(tmp_path: Path) -> None:
    """Punkt 661: eine Ausnahme in der geprüften Funktion ergab nur
    „'NoneType' object has no attribute 'foo'“ ohne Art und Stelle."""
    _projekt(tmp_path)
    ergebnisse = {e.id.rsplit(".", 1)[-1]: e for e in ausfuehren(tmp_path)}

    fehler = ergebnisse["test_ausnahme"]
    assert fehler.status == "fehler"
    assert fehler.nachricht.startswith("AttributeError: ")
    assert "object has no attribute" not in fehler.nachricht
    assert fehler.ort == "rechnen.py, Zeile 2"
    assert ergebnisse["test_ohne_text"].ort == "test_gruende.py, Zeile 14"


@pytest.mark.parametrize(
    ("test", "erwartet"),
    [
        (
            "test_mit_text",
            ["Soll: 3", "Ist: 2", "Größe stimmt nicht", "test_gruende.py, Zeile 8"],
        ),
        ("test_ausnahme", ["AttributeError", "rechnen.py, Zeile 2"]),
    ],
)
def test_ein_klick_zeigt_den_grund_in_der_statuszeile(
    tmp_path: Path, hintergrund_abwarten, hauptfenster, test: str, erwartet: list[str]
) -> None:  # noqa: ANN001
    """Punkt 660: die Statuszeile versprach, ein Klick zeige den Grund,
    ein Klick tat aber nichts, und der Text aus `assertEqual` fehlte."""
    hauptfenster.projekt_oeffnen(_projekt(tmp_path))
    hauptfenster._alle_tests_ausfuehren_aktion()
    hintergrund_abwarten(hauptfenster)
    assert "zeigt hier, woran es lag" in hauptfenster.statusBar().currentMessage()

    baum = hauptfenster.tests_baum
    modul = next(
        baum.topLevelItem(i)
        for i in range(baum.topLevelItemCount())
        if baum.topLevelItem(i).text(0) == "test_gruende"
    )
    klasse = modul.child(0)
    eintrag = next(
        klasse.child(i) for i in range(klasse.childCount()) if klasse.child(i).text(0) == test
    )
    baum.itemClicked.emit(eintrag, 0)

    meldung = hauptfenster.statusBar().currentMessage()
    for teil in erwartet:
        assert teil in meldung
        assert teil in eintrag.toolTip(0)
