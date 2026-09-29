"""Tests für ide/designer/kommando.py: Kommando-Muster für Undo/Redo.
Siehe Arbeitspaket M3, Schritt 5.
"""

from ide.designer.kommando import EigenschaftKommando, Kommandostapel


class _Ding:
    def __init__(self, x: int = 0, y: int = 0) -> None:
        self.x = x
        self.y = y


def test_ausfuehren_wendet_das_kommando_an() -> None:
    ding = _Ding()
    stapel = Kommandostapel()

    stapel.ausfuehren(EigenschaftKommando(ding, {"x": 10}))

    assert ding.x == 10


def test_rueckgaengig_stellt_den_vorherigen_wert_wieder_her() -> None:
    ding = _Ding(x=5)
    stapel = Kommandostapel()
    stapel.ausfuehren(EigenschaftKommando(ding, {"x": 10}))

    stapel.rueckgaengig()

    assert ding.x == 5


def test_wiederholen_wendet_es_erneut_an() -> None:
    ding = _Ding(x=5)
    stapel = Kommandostapel()
    stapel.ausfuehren(EigenschaftKommando(ding, {"x": 10}))
    stapel.rueckgaengig()

    stapel.wiederholen()

    assert ding.x == 10


def test_neues_kommando_nach_rueckgaengig_leert_den_wiederholen_stapel() -> None:
    ding = _Ding(x=5)
    stapel = Kommandostapel()
    stapel.ausfuehren(EigenschaftKommando(ding, {"x": 10}))
    stapel.rueckgaengig()

    stapel.ausfuehren(EigenschaftKommando(ding, {"x": 20}))

    assert stapel.kann_wiederholen is False
    stapel.wiederholen()  # darf nichts tun
    assert ding.x == 20


def test_rueckgaengig_ohne_verlauf_tut_nichts() -> None:
    stapel = Kommandostapel()
    stapel.rueckgaengig()  # darf nicht fehlschlagen
    assert stapel.kann_rueckgaengig is False


def test_mehrere_schritte_vollstaendig_rueckgaengig_ergibt_ausgangszustand() -> None:
    ding = _Ding(x=0, y=0)
    stapel = Kommandostapel()

    stapel.ausfuehren(EigenschaftKommando(ding, {"x": 8}))
    stapel.ausfuehren(EigenschaftKommando(ding, {"y": 8}))
    stapel.ausfuehren(EigenschaftKommando(ding, {"x": 16, "y": 16}))

    stapel.rueckgaengig()
    stapel.rueckgaengig()
    stapel.rueckgaengig()

    assert (ding.x, ding.y) == (0, 0)
    assert stapel.kann_rueckgaengig is False


def test_kann_rueckgaengig_und_wiederholen_spiegeln_den_zustand() -> None:
    ding = _Ding()
    stapel = Kommandostapel()
    assert stapel.kann_rueckgaengig is False
    assert stapel.kann_wiederholen is False

    stapel.ausfuehren(EigenschaftKommando(ding, {"x": 1}))
    assert stapel.kann_rueckgaengig is True
    assert stapel.kann_wiederholen is False

    stapel.rueckgaengig()
    assert stapel.kann_rueckgaengig is False
    assert stapel.kann_wiederholen is True


def test_eigenschaft_kommando_setzt_mehrere_werte_gleichzeitig() -> None:
    ding = _Ding(x=1, y=1)
    stapel = Kommandostapel()

    stapel.ausfuehren(EigenschaftKommando(ding, {"x": 5, "y": 6}))
    assert (ding.x, ding.y) == (5, 6)

    stapel.rueckgaengig()
    assert (ding.x, ding.y) == (1, 1)
