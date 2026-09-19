"""Tests für pcl/strings.py: Strings (Abschnitt 5.0, 11.2). Siehe
docs/PLAN.md, M1 Schritt 6.
"""

from pathlib import Path

import pytest

from pcl.errors import NatterPropertyError
from pcl.strings import Strings


def test_leer_bei_erzeugung() -> None:
    assert len(Strings()) == 0
    assert list(Strings()) == []


def test_add_und_iteration() -> None:
    zeilen = Strings()
    zeilen.add("erste")
    zeilen.add("zweite")
    assert list(zeilen) == ["erste", "zweite"]
    assert zeilen[0] == "erste"
    assert zeilen[1] == "zweite"


def test_add_lehnt_falschen_typ_ab() -> None:
    zeilen = Strings()
    with pytest.raises(NatterPropertyError):
        zeilen.add(5)


def test_clear() -> None:
    zeilen = Strings()
    zeilen.add("x")
    zeilen.clear()
    assert len(zeilen) == 0


def test_bei_aenderung_wird_bei_add_und_clear_aufgerufen() -> None:
    aufrufe = []
    zeilen = Strings(bei_aenderung=lambda: aufrufe.append(True))
    zeilen.add("x")
    zeilen.clear()
    assert aufrufe == [True, True]


def test_gleichheit_mit_liste() -> None:
    zeilen = Strings()
    zeilen.add("a")
    zeilen.add("b")
    assert zeilen == ["a", "b"]


def test_load_and_save_to_file(tmp_path: Path) -> None:
    datei = tmp_path / "test.txt"
    zeilen = Strings()
    zeilen.add("Zeile 1")
    zeilen.add("Ümlaut äöü")
    zeilen.save_to_file(datei)

    geladen = Strings()
    geladen.load_from_file(datei)
    assert geladen == ["Zeile 1", "Ümlaut äöü"]


def test_eine_zeichenkette_wird_an_den_umbruechen_getrennt() -> None:
    """In der Sichtprüfung real passiert: eine `RadioGroup` zeigte
    vierzehn Optionsfelder mit je einem Buchstaben, weil Python eine
    Zeichenkette gern Zeichen für Zeichen hergibt. `Items.Text` in
    Lazarus trennt an den Zeilenumbrüchen – genau das tut es jetzt
    auch."""
    sammlung = Strings()

    sammlung.zuweisen("rot\ngelb\ngruen")

    assert list(sammlung) == ["rot", "gelb", "gruen"]


def test_eine_liste_bleibt_eine_liste() -> None:
    sammlung = Strings()

    sammlung.zuweisen(["rot", "gelb"])

    assert list(sammlung) == ["rot", "gelb"]


def test_eine_einzelne_zeile_ohne_umbruch_ergibt_einen_eintrag() -> None:
    sammlung = Strings()

    sammlung.zuweisen("nur eine Zeile")

    assert list(sammlung) == ["nur eine Zeile"]
