"""Komponentenbaum: alle Komponenten eines Formulars mit Verschachtelung.

Siehe README.md, Abschnitt 7.6: „alle Komponenten mit
Verschachtelung; Auswahl synchron mit dem Designer“. Component-Kinder
werden aus den eigenen Attributen ermittelt (wie sie `create_components`
über `self.<name> = <Typ>(self)` anlegt, Abschnitt 4.3) – es gibt (noch)
keine Container-Komponente mit eigenen Kindern, der Baum ist aktuell
also immer flach, die Rekursion ist aber bereits allgemein für künftige
Container (`GroupBox`, `Panel`, Abschnitt 5.2) vorbereitet.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from pcl.control import Control
from pcl.form import Form

KOMPONENTE_ROLLE = Qt.ItemDataRole.UserRole


def kind_komponenten(objekt: Any) -> list[tuple[str, Control]]:
    return [(name, wert) for name, wert in vars(objekt).items() if isinstance(wert, Control)]


class Komponentenbaum(QTreeWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setHeaderHidden(True)

    def formular_anzeigen(self, formular: Form) -> None:
        self.clear()
        wurzel = QTreeWidgetItem([f"{type(formular).__name__}: Form"])
        wurzel.setData(0, KOMPONENTE_ROLLE, formular)
        self.addTopLevelItem(wurzel)
        self._kinder_hinzufuegen(wurzel, formular)
        self.expandAll()

    def _kinder_hinzufuegen(self, eltern_element: QTreeWidgetItem, objekt: Any) -> None:
        for name, komponente in kind_komponenten(objekt):
            element = QTreeWidgetItem([f"{name}: {type(komponente).__name__}"])
            element.setData(0, KOMPONENTE_ROLLE, komponente)
            eltern_element.addChild(element)
            self._kinder_hinzufuegen(element, komponente)
