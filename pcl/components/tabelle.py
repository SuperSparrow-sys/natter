"""Die Tabelle hinter `StringGrid` und `DBGrid`: eine `QTableView`
mit eigenem Modell.

Bis Punkt 356 waren beide ein `QTableWidget`, und jede Zelle war ein
eigenes `QTableWidgetItem`. 100.000 Zeilen mit vier Spalten belegten
so rund 290 MB, eine Million fast 3 GB, und das Füllen hielt das
Programm sekundenlang an. Das Modell hier hält die Werte einmal als
Listen; Qt fragt nur nach den Zellen, die gerade zu sehen sind.

`TabellenAnsicht` bietet dazu die wenigen Methoden eines
`QTableWidget`, die `StringGrid` und `DBGrid` brauchen (`rowCount`,
`setCurrentCell`, `item` …), damit der Code darum herum und die Tests
so bleiben konnten, wie sie waren.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QPersistentModelIndex,
    Qt,
    Signal,
)
from PySide6.QtWidgets import QTableView, QWidget

_Index = QModelIndex | QPersistentModelIndex


class TabellenModell(QAbstractTableModel):
    """Zeilen als Listen von Werten, dazu die Spaltentitel.

    `anzeige` macht aus einem Wert den Text der Zelle. Ein `DBGrid`
    legt die Zeilen aus der Datenbank unverändert ab und wandelt erst
    beim Anzeigen um; umgewandelt werden so nur die sichtbaren Zellen.
    """

    #: Zeile, Spalte und neuer Text, wenn jemand eine Zelle in der
    #: Tabelle bearbeitet hat. Schreibt das Programm selbst über
    #: `text_setzen`, kommt dieses Signal nicht.
    zelle_bearbeitet = Signal(int, int, str)

    def __init__(
        self, eltern: QWidget, anzeige: Callable[[Any], str] = str
    ) -> None:
        super().__init__(eltern)
        self._anzeige = anzeige
        self._zeilen: list[Any] = []
        self._spalten = 0
        self._titel: list[str] = []

    # -- Qt-Schnittstelle ------------------------------------------

    def rowCount(self, eltern: _Index | None = None) -> int:  # noqa: N802
        if eltern is not None and eltern.isValid():
            return 0
        return len(self._zeilen)

    def columnCount(self, eltern: _Index | None = None) -> int:  # noqa: N802
        if eltern is not None and eltern.isValid():
            return 0
        return self._spalten

    def data(self, index: _Index, rolle: int = 0) -> Any:
        if rolle not in (
            Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole
        ) or not index.isValid():
            return None
        return self.text(index.row(), index.column())

    def setData(  # noqa: N802
        self, index: _Index, wert: Any, rolle: int = Qt.ItemDataRole.EditRole
    ) -> bool:
        if rolle != Qt.ItemDataRole.EditRole or not index.isValid():
            return False
        zeile, spalte = index.row(), index.column()
        text = "" if wert is None else str(wert)
        # Qt schreibt beim Verlassen einer Zelle den Text des Editors
        # auch dann zurück, wenn niemand etwas geändert hat. Ein
        # Doppelklick in die Zelle und ein Klick daneben sind keine
        # Bearbeitung und lösen `on_edit_cell` deshalb nicht aus.
        if text == self.text(zeile, spalte):
            return True
        self.text_setzen(zeile, spalte, text)
        self.zelle_bearbeitet.emit(zeile, spalte, text)
        return True

    def flags(self, index: _Index) -> Qt.ItemFlag:
        return (
            Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsEditable
        )

    def headerData(  # noqa: N802
        self,
        nummer: int,
        richtung: Qt.Orientation,
        rolle: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if rolle != Qt.ItemDataRole.DisplayRole:
            return None
        if richtung == Qt.Orientation.Horizontal:
            titel = self.titel(nummer)
            if titel is not None:
                return titel
        return str(nummer + 1)

    # -- Zugriff für StringGrid und DBGrid -------------------------

    def text(self, zeile: int, spalte: int) -> str:
        return self._anzeige(self._zeilen[zeile][spalte])

    def text_setzen(self, zeile: int, spalte: int, text: str) -> None:
        self._zeilen[zeile][spalte] = text
        index = self.index(zeile, spalte)
        self.dataChanged.emit(index, index)

    def spalte(self, spalte: int) -> list[str]:
        """Die Texte einer ganzen Spalte, von oben nach unten."""
        anzeige = self._anzeige
        return [anzeige(zeile[spalte]) for zeile in self._zeilen]

    def titel(self, spalte: int) -> str | None:
        """Der Titel einer Spalte, `None` ohne eigenen Titel."""
        return self._titel[spalte] if spalte < len(self._titel) else None

    def titel_setzen(self, titel: Sequence[str]) -> None:
        self._titel = list(titel)
        if self._spalten:
            self.headerDataChanged.emit(
                Qt.Orientation.Horizontal, 0, self._spalten - 1
            )

    def inhalt_setzen(self, spalten: int, zeilen: list[Any]) -> None:
        """Ersetzt den ganzen Inhalt auf einmal. Jede Zeile hat
        `spalten` Werte; übernommen wird die Liste selbst, kopiert
        wird nichts."""
        self.beginResetModel()
        self._spalten = spalten
        self._zeilen = zeilen
        self.endResetModel()

    def zeilenzahl_setzen(self, anzahl: int) -> None:
        """Wie `QTableWidget.setRowCount`: neue Zeilen sind leer, was
        über die neue Zahl hinausgeht, entfällt."""
        alt = len(self._zeilen)
        if anzahl > alt:
            self.beginInsertRows(QModelIndex(), alt, anzahl - 1)
            self._zeilen.extend(
                [""] * self._spalten for _ in range(anzahl - alt)
            )
            self.endInsertRows()
        elif anzahl < alt:
            self.beginRemoveRows(QModelIndex(), anzahl, alt - 1)
            del self._zeilen[anzahl:]
            self.endRemoveRows()

    def spaltenzahl_setzen(self, anzahl: int) -> None:
        alt = self._spalten
        if anzahl > alt:
            self.beginInsertColumns(QModelIndex(), alt, anzahl - 1)
            for zeile in self._zeilen:
                zeile.extend([""] * (anzahl - alt))
            self._spalten = anzahl
            self.endInsertColumns()
        elif anzahl < alt:
            self.beginRemoveColumns(QModelIndex(), anzahl, alt - 1)
            for zeile in self._zeilen:
                del zeile[anzahl:]
            self._spalten = anzahl
            self.endRemoveColumns()


class _Zelle:
    """Eine Zelle oder ein Spaltenkopf, wie `QTableWidget.item` und
    `horizontalHeaderItem` sie liefern: mit `text()` und, für Zellen,
    `setText()`. Entsteht erst beim Abfragen und hält nur die
    Stelle, nicht den Text."""

    def __init__(
        self, modell: TabellenModell, zeile: int, spalte: int
    ) -> None:
        self._modell = modell
        self._zeile = zeile
        self._spalte = spalte

    def row(self) -> int:
        return self._zeile

    def column(self) -> int:
        return self._spalte

    def text(self) -> str:
        if self._zeile < 0:
            return self._modell.titel(self._spalte) or ""
        return self._modell.text(self._zeile, self._spalte)

    def setText(self, text: str) -> None:  # noqa: N802
        """Wie eine Eingabe in der Tabelle, also mit
        `zelle_bearbeitet`."""
        index = self._modell.index(self._zeile, self._spalte)
        self._modell.setData(index, text)


class TabellenAnsicht(QTableView):
    """Die `QTableView` zu einem `TabellenModell`, mit den Methoden
    eines `QTableWidget`, die `StringGrid` und `DBGrid` brauchen."""

    #: Wie beim `QTableWidget`: neue Zeile und Spalte, dann die alten.
    currentCellChanged = Signal(int, int, int, int)  # noqa: N815

    def __init__(
        self, eltern: QWidget, anzeige: Callable[[Any], str] = str
    ) -> None:
        super().__init__(eltern)
        self.modell = TabellenModell(self, anzeige)
        self.setModel(self.modell)
        self.selectionModel().currentChanged.connect(self._zelle_gewechselt)

    def _zelle_gewechselt(self, neu: QModelIndex, alt: QModelIndex) -> None:
        self.currentCellChanged.emit(
            neu.row(), neu.column(), alt.row(), alt.column()
        )

    def rowCount(self) -> int:  # noqa: N802
        return self.modell.rowCount()

    def columnCount(self) -> int:  # noqa: N802
        return self.modell.columnCount()

    def setRowCount(self, anzahl: int) -> None:  # noqa: N802
        self.modell.zeilenzahl_setzen(anzahl)

    def setColumnCount(self, anzahl: int) -> None:  # noqa: N802
        self.modell.spaltenzahl_setzen(anzahl)

    def currentRow(self) -> int:  # noqa: N802
        return self.currentIndex().row()

    def currentColumn(self) -> int:  # noqa: N802
        return self.currentIndex().column()

    def setCurrentCell(self, zeile: int, spalte: int) -> None:  # noqa: N802
        # Außerhalb der Tabelle liefert `index` einen ungültigen
        # Index, und der hebt die Auswahl auf wie beim `QTableWidget`.
        self.setCurrentIndex(self.modell.index(zeile, spalte))

    def item(self, zeile: int, spalte: int) -> _Zelle | None:
        if not (
            0 <= zeile < self.rowCount() and 0 <= spalte < self.columnCount()
        ):
            return None
        return _Zelle(self.modell, zeile, spalte)

    def horizontalHeaderItem(  # noqa: N802
        self, spalte: int
    ) -> _Zelle | None:
        if self.modell.titel(spalte) is None:
            return None
        return _Zelle(self.modell, -1, spalte)
