"""Jede Eigenschaft jeder Komponente im Objektinspektor ändern und
nachsehen, ob die Änderung ankommt.

Das war die letzte Zeile in `docs/pruefbericht.md` unter „Was diese
Prüfung nicht abdeckt": die Funktionsprüfung aus M11, Abschnitt 3
löst jeden Menüeintrag, jeden Werkzeugknopf und jeden Kontextmenü-
Eintrag wirklich aus – am Objektinspektor hörte sie auf. Dabei ist er
die Stelle, an der im Unterricht am meisten passiert: Beschriftung,
Position, Farbe, Häkchen.

Wonach geprüft wird. Nicht „der neue Wert steht danach in der
Komponente" – das wäre zu streng. Manche Komponenten *berichtigen*
einen Wert, statt ihn abzulehnen: `RadioGroup.item_index = 6` ohne
sechste Option fällt auf -1 zurück, weil eine Auswahl, die niemand
sieht, schlimmer wäre. Geprüft wird deshalb die Eigenschaft, die in
beiden Fällen gelten muss: Zelle und Komponente sind sich danach
einig. Zeigte der Inspektor eine 6 an, während die Komponente längst
-1 führt, stünde dort etwas, das es nicht gibt.

Die Liste der Komponenten kommt aus der Palette, die der Eigenschaften
aus der Tabelle selbst – beide werden nicht von Hand gepflegt, sonst
veraltet der Test bei der nächsten neuen Komponente.

Aufgeteilt wird je Komponente, nicht je Eigenschaft: die Fälle
aufzuzählen hieße, Widgets schon beim Einsammeln der Tests anzulegen,
und zu dem Zeitpunkt gibt es noch keine `QApplication` – Qt beendet den
Prozess dann ohne Meldung.
"""

from __future__ import annotations

from datetime import date, time
from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidgetItem

from ide.inspector.eigenschaften_tabelle import EigenschaftenTabelle
from ide.palette.palette import ALLE_KOMPONENTEN
from pcl import Form
from pcl.properties import text_aus_wert, wert_aus_text

KOMPONENTEN = sorted(ALLE_KOMPONENTEN, key=lambda typ: typ.__name__)
NAMEN = [typ.__name__ for typ in KOMPONENTEN]


def _neuer_wert(typ: type, alt: Any) -> Any:
    """Ein Wert, der sich vom bisherigen unterscheidet und zum Typ
    passt."""
    if typ is bool:
        return not alt
    if typ is int:
        return alt + 1
    if typ is float:
        return round(alt + 0.5, 2)
    if typ is date:
        return date(2026, 12, 24)
    if typ is time:
        return time(9, 45)
    return "Probe"


def _alle_zeilen(tabelle: EigenschaftenTabelle) -> list[tuple[str, QTableWidgetItem]]:
    return [
        (tabelle.item(zeile, 0).text(), tabelle.item(zeile, 1))
        for zeile in range(tabelle.rowCount())
    ]


def _zeilen(tabelle: EigenschaftenTabelle) -> list[tuple[str, QTableWidgetItem]]:
    """Nur die Zeilen, in denen man wirklich etwas eingeben kann.

    Sammlungen (`Memo.lines`, `MainMenu.entries`) haben in der Zelle
    gar kein Textfeld, sondern den „…"-Doppelklick auf einen eigenen
    Dialog - genau wie in Lazarus. Sie werden hier nicht am Namen
    erkannt, sondern an denselben zwei Dingen, nach denen sich auch Qt
    beim Zeichnen richtet: ein Textfeld gibt es bei `ItemIsEditable`,
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
def test_jede_eigenschaft_steht_im_inspektor(typ: type) -> None:
    """Eine Komponente ohne eine einzige Zeile wäre ein stiller
    Ausfall - der Rundlauf unten liefe für sie leer durch."""
    tabelle, _ = _tabelle_fuer(typ)

    assert _zeilen(tabelle), f"{typ.__name__} zeigt im Inspektor gar nichts"


@pytest.mark.parametrize("typ", KOMPONENTEN, ids=NAMEN)
def test_jede_aenderung_im_inspektor_kommt_an(typ: type) -> None:
    tabelle, _ = _tabelle_fuer(typ)

    for name, element in _zeilen(tabelle):
        feld_typ = tabelle._typ_von(name)
        neu = _neuer_wert(feld_typ, tabelle._wert_lesen(name))

        if feld_typ is bool:
            element.setCheckState(
                Qt.CheckState.Checked if neu else Qt.CheckState.Unchecked
            )
        else:
            element.setText(text_aus_wert(neu))

        jetzt = tabelle._wert_lesen(name)
        if jetzt == neu:
            continue

        # Die Komponente hat den Wert berichtigt. Dann muss die Zelle
        # das zeigen, statt weiter die Eingabe anzuzeigen.
        if feld_typ is bool:
            gezeigt: Any = element.checkState() == Qt.CheckState.Checked
        else:
            gezeigt = wert_aus_text(feld_typ, element.text())
        assert gezeigt == jetzt, (
            f"{typ.__name__}.{name}: Zelle zeigt {gezeigt!r}, "
            f"die Komponente führt {jetzt!r}"
        )


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
