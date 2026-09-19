"""EreignisseTabelle: zeigt und verknüpft Event-Handler – Reiter
„Ereignisse“ des Objektinspektors.

Siehe konzept-natter.md, Abschnitt 7.6: „Doppelklick erzeugt Methode;
Auswahlliste mit passenden vorhandenen Methoden“. Das Erzeugen einer
neuen Methode per Doppelklick (libcst) folgt in Schritt 7; hier wird nur
unter bereits vorhandenen, passenden Methoden des Formulars ausgewählt.
„Passend“ heißt: genau ein Parameter außer `self` – alle bisher
umgesetzten Ereignisse haben die Signatur `(self, sender)` (Abschnitt
5.4).
"""

from __future__ import annotations

import inspect
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QTableWidget, QTableWidgetItem

from pcl.properties import ereignisse

_SPALTE_NAME = 0
_SPALTE_HANDLER = 1
KEIN_HANDLER = "(kein)"


def passende_methoden(formular: Any) -> list[str]:
    namen = []
    for name in dir(type(formular)):
        if name.startswith("_"):
            continue
        attribut = getattr(type(formular), name, None)
        if not callable(attribut):
            continue
        try:
            signatur = inspect.signature(attribut)
        except (TypeError, ValueError):
            continue
        parameter = [p for p in signatur.parameters if p != "self"]
        if len(parameter) == 1:
            namen.append(name)
    return sorted(namen)


class EreignisseTabelle(QTableWidget):
    def __init__(self) -> None:
        super().__init__(0, 2)
        self.setHorizontalHeaderLabels(["Ereignis", "Handler"])
        self._komponente: Any = None
        self._formular: Any = None

    def anzeigen(self, komponente: Any, formular: Any) -> None:
        self._komponente = komponente
        self._formular = formular
        events = ereignisse(type(komponente))
        namen = sorted(events)
        self.setRowCount(len(namen))
        methoden = passende_methoden(formular)

        for zeile, name in enumerate(namen):
            name_element = QTableWidgetItem(name)
            name_element.setFlags(name_element.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # `on_change` heißt bei jeder Komponente etwas anderes: beim
            # `Edit` jeder Tastendruck, beim `TrackBar` jede Bewegung
            # des Reglers. Der Text dazu steht seit jeher am `Event`,
            # wurde aber nirgends angezeigt (M11, Abschnitt 4).
            name_element.setToolTip(events[name].doc)
            self.setItem(zeile, _SPALTE_NAME, name_element)
            self.setCellWidget(zeile, _SPALTE_HANDLER, self._auswahl_erzeugen(name, methoden))

    def _auswahl_erzeugen(self, ereignis_name: str, methoden: list[str]) -> QComboBox:
        auswahl = QComboBox()
        auswahl.addItem(KEIN_HANDLER)
        auswahl.addItems(methoden)

        aktueller_handler = getattr(self._komponente, ereignis_name)
        if aktueller_handler is not None:
            aktueller_name = aktueller_handler.__name__
            if aktueller_name not in methoden:
                auswahl.addItem(aktueller_name)
            auswahl.setCurrentText(aktueller_name)
        else:
            auswahl.setCurrentText(KEIN_HANDLER)

        auswahl.currentTextChanged.connect(
            lambda text, name=ereignis_name: self._handler_setzen(name, text)
        )
        return auswahl

    def _handler_setzen(self, ereignis_name: str, methoden_name: str) -> None:
        if methoden_name == KEIN_HANDLER:
            setattr(self._komponente, ereignis_name, None)
        else:
            setattr(self._komponente, ereignis_name, getattr(self._formular, methoden_name))
