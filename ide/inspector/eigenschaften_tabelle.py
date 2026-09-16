"""EigenschaftenTabelle: zeigt und bearbeitet die `Prop`-Eigenschaften
einer Komponente – Reiter „Eigenschaften“ des Objektinspektors.

Siehe konzept-natter.md, Abschnitt 5.0 (Eigenschaften-System, Editor je
Datentyp) und 7.6 (Objektinspektor). Live-Wirkung entsteht automatisch,
weil `Prop.__set__` (`pcl/properties.py`) das zugehörige Qt-Widget sofort
aktualisiert (`_bei_prop_aenderung`-Hook) – die Tabelle ruft nur
`setattr` auf, mehr nicht.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from pcl.errors import NatterPropertyError
from pcl.properties import eigenschaften

_SPALTE_NAME = 0
_SPALTE_WERT = 1
_NAME_ROLLE = Qt.ItemDataRole.UserRole


class EigenschaftenTabelle(QTableWidget):
    def __init__(self) -> None:
        super().__init__(0, 2)
        self.setHorizontalHeaderLabels(["Eigenschaft", "Wert"])
        self.fehlertext = ""
        self._komponente: Any = None
        self._aktualisierung_laeuft = False
        self.itemChanged.connect(self._bei_zellenaenderung)

    def komponente_anzeigen(self, komponente: Any) -> None:
        """Füllt die Tabelle mit allen `Prop`-Eigenschaften von
        `komponente`, alphabetisch (Abschnitt 7.6: „alphabetisch oder
        nach Kategorie gruppiert“ – Kategorie folgt später)."""
        self._aktualisierung_laeuft = True
        self._komponente = komponente
        props = eigenschaften(type(komponente))
        namen = sorted(props)
        self.setRowCount(len(namen))

        for zeile, name in enumerate(namen):
            name_element = QTableWidgetItem(name)
            name_element.setFlags(name_element.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.setItem(zeile, _SPALTE_NAME, name_element)

            wert_element = QTableWidgetItem()
            wert_element.setData(_NAME_ROLLE, name)
            self.setItem(zeile, _SPALTE_WERT, wert_element)
            self._zelle_aus_komponente_fuellen(wert_element, props[name].typ, name)

        self._aktualisierung_laeuft = False

    def _zelle_aus_komponente_fuellen(
        self, element: QTableWidgetItem, typ: type, name: str
    ) -> None:
        wert = getattr(self._komponente, name)
        if typ is bool:
            element.setFlags(
                (element.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                & ~Qt.ItemFlag.ItemIsEditable
            )
            element.setCheckState(Qt.CheckState.Checked if wert else Qt.CheckState.Unchecked)
        else:
            element.setText(str(wert))

    def _bei_zellenaenderung(self, element: QTableWidgetItem) -> None:
        if self._aktualisierung_laeuft or element.column() != _SPALTE_WERT:
            return

        name = element.data(_NAME_ROLLE)
        typ = eigenschaften(type(self._komponente))[name].typ

        if typ is bool:
            neuer_wert: Any = element.checkState() == Qt.CheckState.Checked
        else:
            try:
                neuer_wert = typ(element.text())
            except ValueError:
                self.fehlertext = f"{element.text()!r} ist keine gültige Eingabe für {name}."
                self._zelle_zuruecksetzen(element, typ, name)
                return

        try:
            setattr(self._komponente, name, neuer_wert)
        except NatterPropertyError as fehler:
            self.fehlertext = str(fehler)
            self._zelle_zuruecksetzen(element, typ, name)
            return

        self.fehlertext = ""

    def _zelle_zuruecksetzen(self, element: QTableWidgetItem, typ: type, name: str) -> None:
        self._aktualisierung_laeuft = True
        self._zelle_aus_komponente_fuellen(element, typ, name)
        self._aktualisierung_laeuft = False
