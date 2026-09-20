"""Datenbank-Panel (Abschnitt 10.2): eine SQLite-Datei öffnen,
Tabellen-/Spaltenbaum anzeigen, SQL-Abfragen ausführen und das Ergebnis
als Tabelle anzeigen; dazu „CSV in Datenbank importieren“ sowie Export
einer Tabelle als CSV oder SQL-Dump.

Seit gibt es hier keine Treiberauswahl und keine
Zugangsdaten mehr: Natter kennt nur noch SQLite (siehe den Modulkopf von
`pcl/components/data_access.py`). Eine Datenbankdatei braucht weder
Server noch Benutzer noch Passwort – und ein Passwortfeld, dessen Inhalt
irgendwo bleiben müsste, gibt es damit auch nicht mehr.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ide.viewers.csv_ansicht import csv_erkennen
from pcl import SQLite3Connection, SQLQuery
from pcl.errors import NatterDatenbankError


def _tabellenname_aus_dateiname(pfad: Path) -> str:
    name = Path(pfad).stem
    bereinigt = "".join(zeichen if zeichen.isalnum() else "_" for zeichen in name)
    return bereinigt or "import"


def _sql_literal(wert: Any) -> str:
    if wert is None:
        return "NULL"
    if isinstance(wert, (int, float)):
        return str(wert)
    escaped = str(wert).replace("'", "''")
    return f"'{escaped}'"


class DatenbankPanel(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._verbindung: SQLite3Connection | None = None

        self._sqlite_pfad = QLineEdit()
        self._sqlite_pfad.setPlaceholderText("Datenbankdatei oder :memory:")
        self._sqlite_datei_waehlen_knopf = QPushButton("Datei wählen …")
        self._sqlite_datei_waehlen_knopf.clicked.connect(self._sqlite_datei_waehlen)
        self._sqlite_widget = QWidget()
        sqlite_layout = QHBoxLayout(self._sqlite_widget)
        sqlite_layout.setContentsMargins(0, 0, 0, 0)
        sqlite_layout.addWidget(self._sqlite_pfad)
        sqlite_layout.addWidget(self._sqlite_datei_waehlen_knopf)

        self._verbinden_knopf = QPushButton("Verbinden")
        self._verbinden_knopf.clicked.connect(self._verbinden)
        self._status_label = QLabel("Nicht verbunden")

        verbindungs_zeile = QHBoxLayout()
        verbindungs_zeile.addWidget(self._sqlite_widget, 1)
        verbindungs_zeile.addWidget(self._verbinden_knopf)
        verbindungs_zeile.addWidget(self._status_label)

        self._tabellenbaum = QTreeWidget()
        self._tabellenbaum.setHeaderLabels(["Tabellen/Spalten"])

        self._sql_eingabe = QPlainTextEdit()
        self._sql_eingabe.setPlaceholderText("SELECT * FROM ...")
        self._ausfuehren_knopf = QPushButton("Ausführen")
        self._ausfuehren_knopf.clicked.connect(self._sql_ausfuehren)
        self._ergebnis_tabelle = QTableWidget()

        # Kurze Beschriftungen, der ganze Satz steht als Kurzhinweis
        # daneben: die drei langen Namen nebeneinander gaben dem Dock
        # eine Mindestbreite, mit der auf einem 1366-Pixel-Bildschirm
        # für die Panels daneben kaum noch etwas übrig blieb (M11,
        # Abschnitt 4).
        self._csv_importieren_knopf = QPushButton("CSV importieren …")
        self._csv_importieren_knopf.setToolTip(
            "Eine CSV-Datei als neue Tabelle in die Datenbank übernehmen"
        )
        self._csv_importieren_knopf.clicked.connect(self._csv_importieren_dialog)
        self._csv_exportieren_knopf = QPushButton("CSV exportieren …")
        self._csv_exportieren_knopf.setToolTip(
            "Die gewählte Tabelle als CSV-Datei speichern (z. B. für Excel)"
        )
        self._csv_exportieren_knopf.clicked.connect(self._csv_exportieren_dialog)
        self._sql_dump_exportieren_knopf = QPushButton("SQL-Dump …")
        self._sql_dump_exportieren_knopf.setToolTip(
            "Die gewählte Tabelle als SQL-Datei speichern – CREATE TABLE und INSERTs, "
            "mit denen sie sich anderswo wieder anlegen lässt"
        )
        self._sql_dump_exportieren_knopf.clicked.connect(self._sql_dump_exportieren_dialog)
        werkzeuge_zeile = QHBoxLayout()
        werkzeuge_zeile.addWidget(self._csv_importieren_knopf)
        werkzeuge_zeile.addWidget(self._csv_exportieren_knopf)
        werkzeuge_zeile.addWidget(self._sql_dump_exportieren_knopf)

        rechte_seite = QVBoxLayout()
        rechte_seite.addWidget(self._sql_eingabe)
        rechte_seite.addWidget(self._ausfuehren_knopf)
        rechte_seite.addWidget(self._ergebnis_tabelle)
        rechte_seite.addLayout(werkzeuge_zeile)
        rechtes_widget = QWidget()
        rechtes_widget.setLayout(rechte_seite)

        aufteilung = QSplitter()
        aufteilung.addWidget(self._tabellenbaum)
        aufteilung.addWidget(rechtes_widget)

        layout = QVBoxLayout(self)
        layout.addLayout(verbindungs_zeile)
        layout.addWidget(aufteilung)

    @property
    def verbindung(self) -> SQLite3Connection | None:
        return self._verbindung

    @property
    def tabellenbaum(self) -> QTreeWidget:
        return self._tabellenbaum

    @property
    def ergebnis_tabelle(self) -> QTableWidget:
        return self._ergebnis_tabelle

    def _sqlite_datei_waehlen(self) -> None:
        pfad, _ = QFileDialog.getOpenFileName(self, "Datenbankdatei wählen")
        if pfad:
            self._sqlite_pfad.setText(pfad)

    def _verbinden(self) -> None:
        verbindung = SQLite3Connection()
        verbindung.database_name = self._sqlite_pfad.text() or ":memory:"
        try:
            verbindung.connected = True
        except NatterDatenbankError as fehler:
            self._status_label.setText(f"Verbindung fehlgeschlagen: {fehler}")
            return

        self._verbindung = verbindung
        self._status_label.setText("Verbunden")
        self._tabellenbaum_aktualisieren()

    def _tabellenbaum_aktualisieren(self) -> None:
        self._tabellenbaum.clear()
        if self._verbindung is None:
            return
        for tabelle in self._tabellennamen():
            eintrag = QTreeWidgetItem([tabelle])
            for spalte in self._spaltennamen(tabelle):
                eintrag.addChild(QTreeWidgetItem([spalte]))
            self._tabellenbaum.addTopLevelItem(eintrag)
        self._tabellenbaum.expandAll()

    def _tabellennamen(self) -> list[str]:
        zeilen = self._verbindung.query(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
        )
        return [str(zeile["name"]) for zeile in zeilen]

    def _spaltennamen(self, tabelle: str) -> list[str]:
        # PRAGMA kennt keine Platzhalter fuer den Tabellennamen; der Name
        # kommt aus sqlite_master, nicht aus einer Eingabe.
        zeilen = self._verbindung.query(f'PRAGMA table_info("{tabelle}")')
        return [str(zeile["name"]) for zeile in zeilen]

    def _sql_ausfuehren(self) -> None:
        if self._verbindung is None:
            self._status_label.setText("Nicht verbunden.")
            return
        abfrage = SQLQuery(self._verbindung)
        abfrage.sql = self._sql_eingabe.toPlainText()
        try:
            abfrage.open()
        except NatterDatenbankError as fehler:
            self._status_label.setText(str(fehler))
            return
        self._ergebnis_anzeigen(abfrage)
        self._tabellenbaum_aktualisieren()

    def _ergebnis_anzeigen(self, abfrage: SQLQuery) -> None:
        spalten = abfrage.column_names
        zeilen = abfrage.all_rows()
        self._ergebnis_tabelle.setColumnCount(len(spalten))
        self._ergebnis_tabelle.setHorizontalHeaderLabels(spalten)
        self._ergebnis_tabelle.setRowCount(len(zeilen))
        for zeile_index, zeile in enumerate(zeilen):
            for spalten_index, wert in enumerate(zeile):
                text = "" if wert is None else str(wert)
                self._ergebnis_tabelle.setItem(zeile_index, spalten_index, QTableWidgetItem(text))

    def _csv_importieren_dialog(self) -> None:
        pfad, _ = QFileDialog.getOpenFileName(self, "CSV-Datei wählen", filter="CSV (*.csv)")
        if pfad:
            self.csv_importieren(Path(pfad))

    def csv_importieren(self, pfad: Path, tabellenname: str | None = None) -> str:
        """Liest `pfad` in eine neue Tabelle ein (Abschnitt 11.6: „CSV in
        Datenbank importieren“, wiederverwendet die Erkennung aus
        `ide.viewers.csv_ansicht.csv_erkennen`). Liefert den
        verwendeten Tabellennamen."""
        if self._verbindung is None:
            raise NatterDatenbankError("Keine offene Datenbankverbindung.")
        pfad = Path(pfad)
        delimiter, encoding = csv_erkennen(pfad)
        with open(pfad, encoding=encoding, newline="") as datei:
            zeilen = list(csv.reader(datei, delimiter=delimiter))
        if not zeilen:
            raise NatterDatenbankError(f"{pfad} ist leer.")
        kopf, *daten = zeilen
        tabellenname = tabellenname or _tabellenname_aus_dateiname(pfad)

        spalten_sql = ", ".join(f'"{spalte}" TEXT' for spalte in kopf)
        loeschen = SQLQuery(self._verbindung)
        loeschen.sql = f'DROP TABLE IF EXISTS "{tabellenname}"'
        loeschen.exec_sql()
        anlegen = SQLQuery(self._verbindung)
        anlegen.sql = f'CREATE TABLE "{tabellenname}" ({spalten_sql})'
        anlegen.exec_sql()

        platzhalter = ", ".join(f":s{i}" for i in range(len(kopf)))
        for zeile in daten:
            einfuegen = SQLQuery(self._verbindung)
            einfuegen.sql = f'INSERT INTO "{tabellenname}" VALUES ({platzhalter})'
            for i, wert in enumerate(zeile):
                einfuegen.params[f"s{i}"] = wert
            einfuegen.exec_sql()
        self._verbindung.verbindung.commit()
        self._tabellenbaum_aktualisieren()
        return tabellenname

    def _csv_exportieren_dialog(self) -> None:
        tabelle = self._ausgewaehlte_tabelle()
        if tabelle is None:
            self._status_label.setText("Keine Tabelle im Baum ausgewählt.")
            return
        pfad, _ = QFileDialog.getSaveFileName(self, "CSV exportieren", filter="CSV (*.csv)")
        if pfad:
            self.tabelle_als_csv_exportieren(tabelle, Path(pfad))

    def tabelle_als_csv_exportieren(self, tabelle: str, ziel: Path) -> None:
        abfrage = SQLQuery(self._verbindung)
        abfrage.sql = f'SELECT * FROM "{tabelle}"'
        abfrage.open()
        with open(ziel, "w", encoding="utf-8", newline="") as datei:
            schreiber = csv.writer(datei, delimiter=";")
            schreiber.writerow(abfrage.column_names)
            for zeile in abfrage.all_rows():
                schreiber.writerow(["" if wert is None else wert for wert in zeile])

    def _sql_dump_exportieren_dialog(self) -> None:
        tabelle = self._ausgewaehlte_tabelle()
        if tabelle is None:
            self._status_label.setText("Keine Tabelle im Baum ausgewählt.")
            return
        pfad, _ = QFileDialog.getSaveFileName(self, "SQL-Dump exportieren", filter="SQL (*.sql)")
        if pfad:
            self.tabelle_als_sql_dump_exportieren(tabelle, Path(pfad))

    def tabelle_als_sql_dump_exportieren(self, tabelle: str, ziel: Path) -> None:
        abfrage = SQLQuery(self._verbindung)
        abfrage.sql = f'SELECT * FROM "{tabelle}"'
        abfrage.open()
        spalten_sql = ", ".join(f'"{spalte}"' for spalte in abfrage.column_names)
        zeilen_sql = [
            f'INSERT INTO "{tabelle}" ({spalten_sql}) VALUES '
            f"({', '.join(_sql_literal(wert) for wert in zeile)});"
            for zeile in abfrage.all_rows()
        ]
        Path(ziel).write_text("\n".join(zeilen_sql) + "\n", encoding="utf-8")

    def _ausgewaehlte_tabelle(self) -> str | None:
        eintrag = self._tabellenbaum.currentItem()
        if eintrag is None:
            return None
        while eintrag.parent() is not None:
            eintrag = eintrag.parent()
        return eintrag.text(0)
