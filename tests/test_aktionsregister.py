"""Tests für ide/actions/: Aktion, Aktionsregister. Headless. Siehe
Arbeitspaket M2, Schritt 2.
"""

import pytest
from PySide6.QtWidgets import QMainWindow, QMenu, QToolBar

from ide.actions import Aktion, AktionsKonfliktError, Aktionsregister


class _SchlankesFenster(QMainWindow):
    """Hat nur, was `an_hauptfenster_anhaengen` braucht: Menüs nach
    Titel und eine Werkzeugleiste. Ein ganzes Hauptfenster baut Docks,
    Editoren und Uhren, die diese Tests nicht ansehen."""

    def __init__(self) -> None:
        super().__init__()
        self._menues = {
            titel: self.menuBar().addMenu(titel)
            for titel in ("Datei", "Bearbeiten", "Projekt")
        }
        self.werkzeugleiste: QToolBar = self.addToolBar("Werkzeuge")

    def menue(self, titel: str) -> QMenu:
        return self._menues[titel]


@pytest.fixture
def fenster(qtbot) -> _SchlankesFenster:  # noqa: ANN001
    fenster = _SchlankesFenster()
    qtbot.addWidget(fenster)
    return fenster


def test_registrieren_und_abrufen() -> None:
    register = Aktionsregister()
    aktion = register.registrieren(Aktion("datei.neue_unit", "Neue Unit", tastenkuerzel="Ctrl+N"))
    assert register["datei.neue_unit"] is aktion
    assert len(register) == 1


def test_doppelte_id_wird_abgelehnt() -> None:
    register = Aktionsregister()
    register.registrieren(Aktion("datei.neue_unit", "Neue Unit"))
    with pytest.raises(AktionsKonfliktError):
        register.registrieren(Aktion("datei.neue_unit", "Neue Unit (anders)"))


def test_tastenkuerzel_konflikt_wird_abgelehnt() -> None:
    register = Aktionsregister()
    register.registrieren(Aktion("datei.speichern", "Speichern", tastenkuerzel="Ctrl+S"))
    with pytest.raises(AktionsKonfliktError):
        register.registrieren(
            Aktion("datei.alles_speichern", "Alles speichern", tastenkuerzel="Ctrl+S")
        )


def test_aktion_ohne_tastenkuerzel_verursacht_keinen_konflikt() -> None:
    register = Aktionsregister()
    register.registrieren(Aktion("a", "A"))
    register.registrieren(Aktion("b", "B"))  # darf nicht scheitern


def test_callback_wird_beim_ausloesen_aufgerufen() -> None:
    aufrufe = []
    aktion = Aktion("test.aktion", "Test", callback=lambda: aufrufe.append(True))
    aktion.qaction.trigger()
    assert aufrufe == [True]


def test_an_hauptfenster_anhaengen_fuegt_ins_richtige_menue_ein(fenster) -> None:
    register = Aktionsregister()
    register.registrieren(Aktion("datei.neue_unit", "Neue Unit", menue="Datei"))
    register.registrieren(Aktion("projekt.oeffnen", "Projekt öffnen …", menue="Projekt"))

    register.an_hauptfenster_anhaengen(fenster)

    datei_eintraege = [a.text() for a in fenster.menue("Datei").actions()]
    projekt_eintraege = [a.text() for a in fenster.menue("Projekt").actions()]
    assert "Neue Unit" in datei_eintraege
    assert "Projekt öffnen …" in projekt_eintraege


def test_aktion_ohne_menue_wird_nicht_angehaengt(fenster) -> None:
    register = Aktionsregister()
    register.registrieren(Aktion("intern.ohne_menue", "Ohne Menü"))

    register.an_hauptfenster_anhaengen(fenster)

    for titel in ("Datei", "Bearbeiten", "Projekt"):
        assert "Ohne Menü" not in [a.text() for a in fenster.menue(titel).actions()]


def test_aktion_mit_symbol_traegt_ein_icon() -> None:
    aktion = Aktion("start.ohne_debugger", "Starten ohne Debugger", symbol="start")
    assert not aktion.qaction.icon().isNull()


def test_aktion_ohne_symbol_hat_kein_icon() -> None:
    aktion = Aktion("datei.unit_oeffnen", "Unit öffnen …")
    assert aktion.qaction.icon().isNull()


def test_an_hauptfenster_anhaengen_fuegt_symbol_aktionen_in_die_werkzeugleiste(
    fenster: _SchlankesFenster,
) -> None:
    register = Aktionsregister()
    register.registrieren(Aktion("test.mit_symbol", "Test mit Symbol", symbol="start"))
    register.registrieren(Aktion("test.ohne_symbol", "Test ohne Symbol"))  # kein Symbol

    register.an_hauptfenster_anhaengen(fenster)

    werkzeugleisten_eintraege = [a.text() for a in fenster.werkzeugleiste.actions()]
    assert "Test mit Symbol" in werkzeugleisten_eintraege
    assert "Test ohne Symbol" not in werkzeugleisten_eintraege
