"""Komponentenbaum: alle Komponenten eines Formulars mit Verschachtelung.

Siehe README.md, Abschnitt 7.6: „alle Komponenten mit
Verschachtelung; Auswahl synchron mit dem Designer“. Component-Kinder
werden aus den eigenen Attributen ermittelt (wie sie `create_components`
über `self.<name> = <Typ>(self)` anlegt, Abschnitt 4.3) – es gibt (noch)
keine Container-Komponente mit eigenen Kindern, der Baum ist aktuell
also immer flach, die Rekursion ist aber bereits allgemein für künftige
Container (`GroupBox`, `Panel`, Abschnitt 5.2) vorbereitet.

Jede Zeile trägt das Symbol ihrer Komponente – dasselbe wie in der
Palette. Es stand seit M15, Abschnitt 6 als offener Rest da: die Palette
bekam damals ihre Symbole, der Baum daneben blieb eine Textliste. Auf
einem Formular mit fünfzehn Kindern ist „`b_ok: Button`“ in einer Spalte
gleich langer Zeilen aber schwerer zu finden als ein Knopf-Symbol, und
die Zuordnung zur Palette geht dabei ganz verloren.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QTreeWidget,
    QTreeWidgetItem,
    QTreeWidgetItemIterator,
)

from ide.assets import symbol
from ide.assets.symbole import theme_ermitteln
from ide.shell.explorer import EINRUECKUNG
from pcl.control import Control
from pcl.form import Form

KOMPONENTE_ROLLE = Qt.ItemDataRole.UserRole

#: Das Symbol des Formulars selbst. Es steht in der Palette nicht (man
#: legt kein Formular auf ein Formular), im Baum aber an der Wurzel.
FORM_SYMBOL = "komponente_form"


def symbolname(objekt: Any) -> str:
    """Der Symbolname zu einer Komponente – dieselbe Regel wie in der
    Palette (`ide/palette/palette.py`), damit beide dasselbe Bild zeigen,
    ohne dass es eine Liste gäbe, die auseinanderlaufen kann."""
    if isinstance(objekt, Form):
        return FORM_SYMBOL
    return f"komponente_{type(objekt).__name__.lower()}"


def formular_von(objekt: Any) -> Any:
    """Das Formular, zu dem `objekt` gehört – über die Elternkette."""
    while isinstance(objekt, Control) and objekt.eltern is not None:
        objekt = objekt.eltern
    return objekt


def kind_komponenten(objekt: Any) -> list[tuple[str, Control]]:
    """Die Komponenten, die unmittelbar in `objekt` liegen.

    Gesucht wird in den Attributen des Formulars, gefiltert nach der
    Elternbeziehung. Beides zusammen, weil in Natter zweierlei
    gleichzeitig gilt: die Namen bleiben flach (`self.b_ok`, auch wenn
    der Knopf in einem Panel liegt), die Zugehörigkeit
    ist aber verschachtelt. Wer nur `vars(objekt)` liest, findet an
    einem Panel nichts, weil das Kind als Attribut des Formulars
    dasteht; wer nur `vars(formular)` liest, hängt es ans Formular,
    obwohl es im Panel liegt.
    """
    wurzel = formular_von(objekt)
    return [
        (name, wert)
        for name, wert in vars(wurzel).items()
        if isinstance(wert, Control) and wert.eltern is objekt
    ]


def _kinder_nach_eltern(formular: Any) -> dict[int, list[tuple[str, Control]]]:
    """Für jedes Objekt des Formulars die Komponenten, die unmittelbar
    darin liegen, über `id()` des Elternobjekts - dieselbe Zuordnung
    und Reihenfolge wie `kind_komponenten`, aber in einem Durchgang.
    `kind_komponenten` für jede Komponente einzeln aufzurufen las die
    Attribute des Formulars einmal je Komponente, mit 200 Komponenten
    also 40.000-mal (Punkt 312)."""
    kinder: dict[int, list[tuple[str, Control]]] = {}
    for name, wert in vars(formular).items():
        if isinstance(wert, Control):
            kinder.setdefault(id(wert.eltern), []).append((name, wert))
    return kinder


def _gliederung(formular: Any) -> list[tuple[int, str, str, int]]:
    """Was der Baum zeigt, als Liste: Tiefe, Name, Typ und `id()` jeder
    Komponente in der Reihenfolge der Zeilen."""
    kinder = _kinder_nach_eltern(formular)
    zeilen: list[tuple[int, str, str, int]] = []

    def ablaufen(objekt: Any, tiefe: int) -> None:
        for name, komponente in kinder.get(id(objekt), []):
            zeilen.append(
                (tiefe, name, type(komponente).__name__, id(komponente))
            )
            ablaufen(komponente, tiefe + 1)

    ablaufen(formular, 1)
    return zeilen


class Komponentenbaum(QTreeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setHeaderHidden(True)
        # Dieselbe Einrückung wie im Projekt-Explorer: beide Bäume
        # stehen gleichzeitig im Fenster, und unterschiedlich tiefe
        # Stufen fallen sofort auf (M15, Abschnitt 6).
        self.setIndentation(EINRUECKUNG)
        self._theme = "system"
        self._formular: Form | None = None
        #: Was der Baum gerade zeigt (`_gliederung`), damit
        #: `auffrischen` ihn nur neu aufbaut, wenn sich daran etwas
        #: geändert hat.
        self._gliederung: list[tuple[int, str, str, int]] = []

    def formular_anzeigen(self, formular: Form) -> None:
        self.clear()
        self._formular = formular
        # Das Design einmal für den ganzen Baum auflösen: `symbol` mit
        # „system“ liest dafür jedes Mal die Einstellungen, rund eine
        # Millisekunde je Zeile. Dasselbe Symbol kommt zudem für jede
        # Komponente eines Typs wieder.
        theme = theme_ermitteln(self._theme)
        symbole: dict[str, Any] = {}

        def symbol_zu(name: str) -> Any:
            if name not in symbole:
                symbole[name] = symbol(name, theme)
            return symbole[name]

        wurzel = QTreeWidgetItem([f"{type(formular).__name__}: Form"])
        wurzel.setIcon(0, symbol_zu(FORM_SYMBOL))
        wurzel.setData(0, KOMPONENTE_ROLLE, formular)
        self.addTopLevelItem(wurzel)
        self._kinder_hinzufuegen(
            wurzel, formular, _kinder_nach_eltern(formular), symbol_zu
        )
        self.expandAll()
        self._gliederung = _gliederung(formular)

    def auffrischen(self, auswahl: Any = None) -> None:
        """Baut den Baum aus dem Live-Formular neu auf und markiert
        `auswahl`.

        Bis 0.3.3 entstand der Baum nur beim Öffnen des Formulars. Eine
        neu platzierte, gelöschte oder umbenannte Komponente erschien
        dort erst, nachdem der Designer geschlossen und wieder geöffnet
        war. Während des Neuaufbaus schweigen die Signale: der
        Objektinspektor soll dabei nicht zwischendurch das Formular
        anzeigen.

        Neu aufgebaut wird nur, wenn sich Komponenten, ihre Namen,
        Typen oder Verschachtelung geändert haben. Nach einem
        Verschieben oder einer geänderten Eigenschaft sieht der Baum
        gleich aus; ihn trotzdem neu zu bauen kostete mit 200
        Komponenten rund 140 ms (Punkt 312).
        """
        if self._formular is None:
            return
        if _gliederung(self._formular) != self._gliederung:
            self.blockSignals(True)
            try:
                self.formular_anzeigen(self._formular)
            finally:
                self.blockSignals(False)
        if auswahl is not None:
            self.komponente_markieren(auswahl)

    def komponente_markieren(self, komponente: Any) -> None:
        """Markiert die Zeile dieser Komponente, ohne `currentItemChanged`
        auszulösen - die Auswahl kommt aus dem Designer, der die
        Eigenschaften schon selbst anzeigt."""
        zeilen = QTreeWidgetItemIterator(self)
        while zeilen.value() is not None:
            zeile = zeilen.value()
            if zeile.data(0, KOMPONENTE_ROLLE) is komponente:
                self.blockSignals(True)
                try:
                    self.setCurrentItem(zeile)
                finally:
                    self.blockSignals(False)
                return
            zeilen += 1

    def symbole_erneuern(self, theme: str = "system") -> None:
        """Lädt die Symbole im angegebenen Theme neu – nötig nach
        „Ansicht → Design“, weil ein `QIcon` sich seine Farben merkt
        (dieselbe Falle wie bei der Palette)."""
        self._theme = theme
        if self._formular is not None:
            formular_anzeigen = self._formular
            self.formular_anzeigen(formular_anzeigen)

    def _kinder_hinzufuegen(
        self,
        eltern_element: QTreeWidgetItem,
        objekt: Any,
        kinder: dict[int, list[tuple[str, Control]]],
        symbol_zu: Any,
    ) -> None:
        for name, komponente in kinder.get(id(objekt), []):
            element = QTreeWidgetItem([f"{name}: {type(komponente).__name__}"])
            element.setIcon(0, symbol_zu(symbolname(komponente)))
            element.setData(0, KOMPONENTE_ROLLE, komponente)
            eltern_element.addChild(element)
            self._kinder_hinzufuegen(element, komponente, kinder, symbol_zu)
