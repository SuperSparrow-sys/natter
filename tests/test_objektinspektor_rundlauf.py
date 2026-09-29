"""Was der Objektinspektor mit Eingaben tut, die nicht einfach
durchgehen: Sammlungen und unsinnige Werte.

Ob jede Eigenschaft jeder Komponente im Inspektor steht, sich dort
ändern lässt und im laufenden Programm ankommt, prüft
`tests/test_eigenschaften_rundlauf.py` - dort auch der Fall, dass eine
Komponente einen Wert berichtigt, statt ihn zu übernehmen, und die
Zelle danach zeigen muss, was gilt. Hier bleiben die beiden Fälle, in
denen eine Eingabe gar nicht erst übernommen werden darf.

Die Liste der Komponenten kommt aus der Palette, die der Eigenschaften
aus der Tabelle selbst - beide werden nicht von Hand gepflegt, sonst
veraltet der Test bei der nächsten neuen Komponente.

Aufgeteilt wird je Komponente, nicht je Eigenschaft: die Fälle
aufzuzählen hieße, Widgets schon beim Einsammeln der Tests anzulegen,
und zu dem Zeitpunkt gibt es noch keine `QApplication` - Qt beendet den
Prozess dann ohne Meldung.
"""

from __future__ import annotations

from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem

from ide.inspector.eigenschaften_tabelle import EigenschaftenTabelle
from ide.palette.palette import ALLE_KOMPONENTEN
from pcl import Form

KOMPONENTEN = sorted(ALLE_KOMPONENTEN, key=lambda typ: typ.__name__)
NAMEN = [typ.__name__ for typ in KOMPONENTEN]


def _alle_zeilen(tabelle: EigenschaftenTabelle) -> list[tuple[str, QTableWidgetItem]]:
    return [
        (tabelle.item(zeile, 0).text(), tabelle.item(zeile, 1))
        for zeile in range(tabelle.rowCount())
    ]


def _zeilen(tabelle: EigenschaftenTabelle) -> list[tuple[str, QTableWidgetItem]]:
    """Nur die Zeilen, in denen man wirklich etwas eingeben kann.

    Sammlungen (`Memo.lines`, `MainMenu.entries`) haben in der Zelle
    gar kein Textfeld, sondern den „…"-Doppelklick auf einen eigenen
    Dialog. Sie werden hier nicht am Namen erkannt, sondern an
    denselben zwei Dingen, nach denen sich auch Qt beim Zeichnen
    richtet: ein Textfeld gibt es bei `ItemIsEditable`,
    ein Häkchen nur, wenn wirklich ein `CheckStateRole` gesetzt wurde.
    `ItemIsUserCheckable` allein reicht dafür nicht - das Flag
    steht in Qts Voreinstellung für jede Zelle und sagt nichts darüber,
    ob eine zu sehen ist. Eine neue Sammlungseigenschaft fällt damit
    von selbst heraus, ohne dass jemand eine Liste pflegen müsste.
    """
    beschreibbar = []
    for name, element in _alle_zeilen(tabelle):
        bearbeitbar = bool(element.flags() & Qt.ItemFlag.ItemIsEditable)
        hat_haekchen = element.data(Qt.ItemDataRole.CheckStateRole) is not None
        if bearbeitbar or hat_haekchen:
            beschreibbar.append((name, element))
    return beschreibbar


#: Formulare und Tabellen, die über den Test hinaus am Leben bleiben.
#:
#: Ohne das räumt Python das Formular am Ende der Funktion weg, Qt
#: löscht die Widgets darunter mit - und der nächste Zugriff auf eine
#: Eigenschaft fliegt als „libshiboken: Internal C++ object
#: (PySide6.QtWidgets.QSlider) already deleted" heraus. Real passiert:
#: 29 von 29 Komponenten sind daran gescheitert, bevor überhaupt eine
#: Eigenschaft geprüft war.
_AM_LEBEN: list[Any] = []


def _tabelle_fuer(typ: type) -> tuple[EigenschaftenTabelle, Any]:
    formular = Form()
    komponente = typ(formular)
    tabelle = EigenschaftenTabelle()
    tabelle.komponente_anzeigen(komponente)
    _AM_LEBEN.extend((formular, komponente, tabelle))
    return tabelle, komponente


@pytest.mark.parametrize("typ", KOMPONENTEN, ids=NAMEN)
def test_eine_sammlung_laesst_sich_nicht_in_der_zelle_bearbeiten(typ: type) -> None:
    """Sonst stünde nach einem Tippfehler in der Zelle „Probe", während
    die Komponente weiter ihre leere Liste führt - der Inspektor zeigte
    etwas an, das es nicht gibt."""
    tabelle, _ = _tabelle_fuer(typ)

    for name, element in _alle_zeilen(tabelle):
        if tabelle._typ_von(name) is not list:
            continue
        assert not element.flags() & Qt.ItemFlag.ItemIsEditable, name
        assert element.data(Qt.ItemDataRole.CheckStateRole) is None, name


@pytest.mark.parametrize("typ", KOMPONENTEN, ids=NAMEN)
def test_eine_unsinnige_eingabe_wird_abgewiesen_statt_uebernommen(typ: type) -> None:
    """In eine Zahlzeile lässt sich „viel" tippen. Danach muss in der
    Zelle wieder der alte Wert stehen - nicht der Text - und eine
    deutsche Meldung daneben."""
    tabelle, _ = _tabelle_fuer(typ)

    zahlzeilen = [
        (name, element)
        for name, element in _zeilen(tabelle)
        if tabelle._typ_von(name) is int
    ]
    assert zahlzeilen, f"{typ.__name__} hat keine einzige Zahl-Eigenschaft"

    for name, element in zahlzeilen:
        alt = tabelle._wert_lesen(name)

        element.setText("viel")

        assert tabelle._wert_lesen(name) == alt, name
        assert element.text() == str(alt), name
        assert name in tabelle.fehlertext, tabelle.fehlertext
