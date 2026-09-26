"""EreignisseTabelle: zeigt und verknüpft Event-Handler – Reiter
„Ereignisse“ des Objektinspektors.

Siehe README.md, Abschnitt 7.6: „Doppelklick erzeugt Methode;
Auswahlliste mit passenden vorhandenen Methoden“. Das Erzeugen einer
neuen Methode per Doppelklick (libcst) folgt in Schritt 7; hier wird nur
unter bereits vorhandenen, passenden Methoden des Formulars ausgewählt.
„Passend“ heißt: genau ein Parameter außer `self` – alle bisher
umgesetzten Ereignisse haben die Signatur `(self, sender)` (Abschnitt
5.4).
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QTableWidget, QTableWidgetItem

from pcl.control import EREIGNIS_PARAMETER
from pcl.properties import ereignisse

_SPALTE_NAME = 0
_SPALTE_HANDLER = 1
KEIN_HANDLER = "(kein)"


def erwartete_parameter(ereignis_name: str) -> int:
    """Wie viele Parameter eine Methode für dieses Ereignis hat.

    `sender` hat jede, dazu kommt, was das Ereignis mitbringt:
    `on_mouse_down` die beiden Koordinaten, `on_edit_cell` Spalte,
    Zeile und Text. Die Liste steht in `EREIGNIS_PARAMETER`.
    """
    return 1 + len(EREIGNIS_PARAMETER.get(ereignis_name, ()))


def passende_methoden(formular: Any, ereignis_name: str = "") -> list[str]:
    """Die Methoden des Formulars, die zu diesem Ereignis passen.

    „Passend" hieß bis September 2026 „genau ein Parameter außer
    `self`". Das stimmte, solange jedes Ereignis `(self, sender)` war.
    Mit den Maus-Ereignissen aus M15 stimmt es nicht mehr: eine
    richtig geschriebene Methode `(self, sender, x, y)` hat zwei und
    fiel damit durch den Filter. Sie erschien nie im Auswahlfeld, und
    zwar ohne jede Meldung - wer nicht wusste, warum, konnte das
    Ereignis im Objektinspektor überhaupt nicht verknüpfen.

    Ohne `ereignis_name` bleibt es beim alten Maßstab; das ist der
    Fall für Aufrufer, die kein bestimmtes Ereignis meinen.
    """
    erwartet = erwartete_parameter(ereignis_name) if ereignis_name else 1
    # Methoden, die seit dem Öffnen des Designers in der Unit
    # dazugekommen sind. Die Funktion hängt der Designer an die
    # Klasse (`ide/designer/laden.py`); ein Formular ohne Unit hat
    # sie nicht.
    nachladen = getattr(type(formular), "_methoden_nachladen", None)
    if nachladen is not None:
        nachladen()
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
        if len(parameter) == erwartet:
            namen.append(name)
    return sorted(namen)


class EreignisseTabelle(QTableWidget):
    def __init__(self) -> None:
        super().__init__(0, 2)
        self.setHorizontalHeaderLabels(["Ereignis", "Handler"])
        self._komponente: Any = None
        self._formular: Any = None
        self._bei_aenderung: Callable[[Any, str, Any, Any], None] | None = None
        #: Legt die Methode zu einem Ereignis an und liefert ihren
        #: Namen. Wird von außen gesetzt, weil die Tabelle die
        #: Unit-Datei nicht kennt - das weiß der Designer.
        self._methode_anlegen: Callable[[Any, str], str | None] | None = None
        # Ein Doppelklick auf eine Zeile legt die Methode an. Dieselbe
        # Geste wie im Designer, wo ein Doppelklick auf die Komponente
        # die Methode zum kennzeichnenden Ereignis schreibt.
        self.cellDoubleClicked.connect(self._bei_doppelklick)

    def _bei_doppelklick(self, zeile: int, _spalte: int) -> None:
        """Legt die Methode zu dieser Zeile an, wenn es sie noch nicht
        gibt, und verknüpft sie.

        Gibt es sie schon, passiert nichts - der Designer hält es
        genauso, und ein zweiter Doppelklick soll keine zweite Methode
        schreiben.
        """
        if self._methode_anlegen is None or self._komponente is None:
            return
        element = self.item(zeile, _SPALTE_NAME)
        if element is None:
            return
        name = self._methode_anlegen(self._komponente, element.text())
        if name is None:
            return
        self.anzeigen(
            self._komponente,
            self._formular,
            self._bei_aenderung,
            methode_anlegen=self._methode_anlegen,
        )

    def anzeigen(
        self,
        komponente: Any,
        formular: Any,
        bei_aenderung: Callable[[Any, str, Any, Any], None] | None = None,
        *,
        methode_anlegen: Callable[[Any, str], str | None] | None = None,
    ) -> None:
        """`bei_aenderung` meldet eine hier gewählte Verknüpfung an den
        Designer weiter, damit sie in die `.pfm` und den erzeugten Code
        kommt.

        Ohne diese Meldung landete eine im Reiter „Ereignisse“ gesetzte
        Verknüpfung nur am Live-Objekt: der Designer zeigte sie an,
        die `.pfm` und `u_*_design.py` erfuhren nichts davon, und im
        gestarteten Programm tat der Knopf nichts. Manchmal kam sie doch
        an – nämlich dann, wenn die Schülerin danach zufällig noch eine
        Eigenschaft änderte, denn dabei wird die `.pfm` komplett aus dem
        Live-Formular neu geschrieben. „Mal geht mein Knopf, mal nicht“
        ist für jemanden, der programmieren lernt, der denkbar
        schlechteste Fehler (M12).
        """
        self._komponente = komponente
        self._formular = formular
        self._bei_aenderung = bei_aenderung
        self._methode_anlegen = methode_anlegen
        events = ereignisse(type(komponente))
        namen = sorted(events)
        self.setRowCount(len(namen))

        for zeile, name in enumerate(namen):
            name_element = QTableWidgetItem(name)
            name_element.setFlags(name_element.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # `on_change` heißt bei jeder Komponente etwas anderes: beim
            # `Edit` jeder Tastendruck, beim `TrackBar` jede Bewegung
            # des Reglers. Der Text dazu steht seit jeher am `Event`,
            # wurde aber nirgends angezeigt (M11, Abschnitt 4).
            name_element.setToolTip(events[name].doc)
            self.setItem(zeile, _SPALTE_NAME, name_element)
            # Je Zeile eine eigene Liste: eine Methode für `on_click`
            # passt nicht auf `on_mouse_down`.
            self.setCellWidget(
                zeile,
                _SPALTE_HANDLER,
                self._auswahl_erzeugen(name, passende_methoden(formular, name)),
            )

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
        alt = getattr(self._komponente, ereignis_name)
        neu = (
            None
            if methoden_name == KEIN_HANDLER
            else getattr(self._formular, methoden_name)
        )
        setattr(self._komponente, ereignis_name, neu)
        if self._bei_aenderung is not None:
            self._bei_aenderung(self._komponente, ereignis_name, alt, neu)
