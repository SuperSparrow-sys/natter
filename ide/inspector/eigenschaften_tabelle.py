"""EigenschaftenTabelle: zeigt und bearbeitet die `Prop`-Eigenschaften
einer Komponente – Reiter „Eigenschaften“ des Objektinspektors.

Siehe konzept-natter.md, Abschnitt 5.0 (Eigenschaften-System, Editor je
Datentyp) und 7.6 (Objektinspektor). Live-Wirkung entsteht automatisch,
weil `Prop.__set__` (`pcl/properties.py`) das zugehörige Qt-Widget sofort
aktualisiert (`_bei_prop_aenderung`-Hook) – die Tabelle ruft dafür nur
`setattr` (bzw. bei aufklappbaren Untereigenschaften wie
`Shape.brush.color` denselben Mechanismus eine Ebene tiefer) auf, mehr
nicht.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem

from pcl.errors import NatterPropertyError
from pcl.properties import VERSCHACHTELTE_EIGENSCHAFTEN, eigenschaften

_SPALTE_NAME = 0
_SPALTE_WERT = 1
_NAME_ROLLE = Qt.ItemDataRole.UserRole

# Sentinel für die "Name"-Zeile (Bezeichner im Code, z. B. "b_anmelden") -
# keine echte Prop, deshalb ein eigener Marker statt eines Eigenschafts-
# namens in _NAME_ROLLE.
_NAME_ZEILE = object()


class EigenschaftenTabelle(QTableWidget):
    def __init__(self) -> None:
        super().__init__(0, 2)
        self.setHorizontalHeaderLabels(["Eigenschaft", "Wert"])
        self.fehlertext = ""
        self._komponente: Any = None
        self._name_setzen: Callable[[str], None] | None = None
        self._aktueller_name: str | None = None
        self._aktualisierung_laeuft = False
        self.itemChanged.connect(self._bei_zellenaenderung)

    def komponente_anzeigen(
        self,
        komponente: Any,
        *,
        name: str | None = None,
        name_setzen: Callable[[str], None] | None = None,
    ) -> None:
        """Füllt die Tabelle mit allen `Prop`-Eigenschaften von
        `komponente`, alphabetisch (Abschnitt 7.6: „alphabetisch oder
        nach Kategorie gruppiert“ – Kategorie folgt später), plus allen
        aufklappbaren Untereigenschaften, die diese Komponente besitzt
        (z. B. `Shape.brush.color`, Nutzer-Feedback September 2026: „alle
        Eigenschaften inklusive Farbe usw. sollen im Objektinspektor
        angezeigt werden“ – `brush.color` fehlte bisher komplett, weil es
        kein echter `Prop` ist, sondern eine Untereigenschaft).

        `name`/`name_setzen` zeigen zusätzlich ganz oben die Zeile „name“
        (der Bezeichner im generierten Code, z. B. `b_anmelden`) –
        getrennt von `caption`/`text` (dem Anzeigetext), wie in Lazarus
        (Nutzer-Feedback September 2026: „caption und name sind
        unterschiedlich und der Name muss vom Nutzer frei veränderbar
        sein“). Ohne beide Argumente (z. B. außerhalb eines offenen
        Designers) bleibt die Zeile weg, weil es dann nichts umzubenennen
        gibt."""
        self._aktualisierung_laeuft = True
        self._komponente = komponente
        self._name_setzen = name_setzen
        self._aktueller_name = name
        props = eigenschaften(type(komponente))
        verschachtelt = [
            eigenschaft_name
            for eigenschaft_name, (attribut, _) in VERSCHACHTELTE_EIGENSCHAFTEN.items()
            if hasattr(komponente, attribut)
        ]
        namen = sorted([*props, *verschachtelt])
        zeigt_name_zeile = name is not None and name_setzen is not None
        self.setRowCount(len(namen) + (1 if zeigt_name_zeile else 0))

        zeile = 0
        if zeigt_name_zeile:
            self._zeile_anlegen(zeile, "name", _NAME_ZEILE)
            self.item(zeile, _SPALTE_WERT).setText(name)
            zeile += 1

        for eigenschaft_name in namen:
            self._zeile_anlegen(zeile, eigenschaft_name, eigenschaft_name)
            if eigenschaft_name in VERSCHACHTELTE_EIGENSCHAFTEN:
                typ = str
            else:
                typ = props[eigenschaft_name].typ
            wert_element = self.item(zeile, _SPALTE_WERT)
            self._zelle_aus_komponente_fuellen(wert_element, typ, eigenschaft_name)
            zeile += 1

        self._aktualisierung_laeuft = False

    def _zeile_anlegen(self, zeile: int, anzeige_name: str, rollen_wert: Any) -> None:
        name_element = QTableWidgetItem(anzeige_name)
        name_element.setFlags(name_element.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.setItem(zeile, _SPALTE_NAME, name_element)

        wert_element = QTableWidgetItem()
        wert_element.setData(_NAME_ROLLE, rollen_wert)
        self.setItem(zeile, _SPALTE_WERT, wert_element)

    def _wert_lesen(self, name: str) -> Any:
        if name in VERSCHACHTELTE_EIGENSCHAFTEN:
            attribut, unter_attribut = VERSCHACHTELTE_EIGENSCHAFTEN[name]
            return getattr(getattr(self._komponente, attribut), unter_attribut)
        return getattr(self._komponente, name)

    def _wert_setzen(self, name: str, wert: Any) -> None:
        if name in VERSCHACHTELTE_EIGENSCHAFTEN:
            attribut, unter_attribut = VERSCHACHTELTE_EIGENSCHAFTEN[name]
            setattr(getattr(self._komponente, attribut), unter_attribut, wert)
            return
        setattr(self._komponente, name, wert)

    def _zelle_aus_komponente_fuellen(
        self, element: QTableWidgetItem, typ: type, name: str
    ) -> None:
        wert = self._wert_lesen(name)
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
        if name is _NAME_ZEILE:
            self._name_zeile_bearbeiten(element)
            return

        if name in VERSCHACHTELTE_EIGENSCHAFTEN:
            typ = str
        else:
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
            self._wert_setzen(name, neuer_wert)
        except NatterPropertyError as fehler:
            self.fehlertext = str(fehler)
            self._zelle_zuruecksetzen(element, typ, name)
            return

        self.fehlertext = ""

    def _name_zeile_bearbeiten(self, element: QTableWidgetItem) -> None:
        """Zeile „name“ (Bezeichner im Code, Nutzer-Feedback September
        2026): Umbenennen läuft über `DesignerCanvas.komponente_umbenennen`
        (Undo, `.pfm`/Code-Aktualisierung), nicht über `setattr` – deshalb
        der eigene `name_setzen`-Rückruf statt `_wert_setzen`."""
        neuer_name = element.text()
        try:
            self._name_setzen(neuer_name)
        except ValueError as fehler:
            self.fehlertext = str(fehler)
            self._aktualisierung_laeuft = True
            element.setText(self._aktueller_name)
            self._aktualisierung_laeuft = False
            return
        self._aktueller_name = neuer_name
        self.fehlertext = ""

    def _zelle_zuruecksetzen(self, element: QTableWidgetItem, typ: type, name: str) -> None:
        self._aktualisierung_laeuft = True
        self._zelle_aus_komponente_fuellen(element, typ, name)
        self._aktualisierung_laeuft = False
