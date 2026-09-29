"""`DBGrid` und `StringGrid` mit 100.000 Zeilen (Punkt 356).

Vorher war jede Zelle ein eigenes `QTableWidgetItem`: 100.000 Zeilen
mit vier Spalten belegten rund 250 MB und brauchten beim `DBGrid`
über eine Sekunde, beim `StringGrid` mit `load_dataframe` 17 s und
mehr. Gemessen werden die privaten Bytes des Testprozesses; die
Grenze von 100 MB ist viermal so hoch wie das, was jetzt gebraucht
wird.
"""

from __future__ import annotations

import ctypes
import sys
import time
from ctypes import wintypes

import pandas as pd
import pytest

from pcl import (
    DataSource,
    DBGrid,
    DBNavigator,
    DBText,
    Form,
    SQLite3Connection,
    SQLQuery,
    StringGrid,
)

ZEILEN = 100_000

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="misst den Speicher über die Windows-API"
)


class _Zaehler(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def _private_mb() -> float:
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.K32GetProcessMemoryInfo.argtypes = [
        wintypes.HANDLE, ctypes.POINTER(_Zaehler), wintypes.DWORD
    ]
    zaehler = _Zaehler()
    zaehler.cb = ctypes.sizeof(zaehler)
    assert kernel32.K32GetProcessMemoryInfo(
        kernel32.GetCurrentProcess(), ctypes.byref(zaehler), zaehler.cb
    )
    return zaehler.PrivateUsage / 2**20


def _messen(fuellen) -> tuple[float, float]:  # noqa: ANN001
    """Dauer in Sekunden und zusätzlicher Speicher in MB."""
    vorher = _private_mb()
    start = time.perf_counter()
    fuellen()
    return time.perf_counter() - start, _private_mb() - vorher


def test_dbgrid_und_stringgrid_fassen_100000_zeilen(
    qtbot,  # noqa: ANN001
) -> None:
    formular = Form()
    qtbot.addWidget(formular._qwidget)
    formular._qwidget.show()

    db = SQLite3Connection()
    db.connected = True
    db.verbindung.execute(
        "CREATE TABLE messung (nr INTEGER, name TEXT, wert REAL, ort TEXT)"
    )
    db.verbindung.executemany(
        "INSERT INTO messung VALUES (?, ?, ?, ?)",
        ((i, f"Name {i}", i / 4, "Ort") for i in range(ZEILEN)),
    )
    db.verbindung.commit()
    abfrage = SQLQuery(db)
    abfrage.sql = "SELECT * FROM messung"
    abfrage.open()
    df = pd.read_sql("SELECT * FROM messung", db.verbindung)

    quelle = DataSource(abfrage)
    ergebnis: dict[str, object] = {}

    def db_fuellen() -> None:
        ergebnis["dbgrid"] = DBGrid(formular, quelle)

    def sg_fuellen() -> None:
        tabelle = StringGrid(formular)
        tabelle.load_dataframe(df)
        ergebnis["stringgrid"] = tabelle

    for name, fuellen in (("DBGrid", db_fuellen), ("StringGrid", sg_fuellen)):
        dauer, speicher = _messen(fuellen)
        assert speicher < 100, f"{name}: {speicher:.0f} MB"
        assert dauer < 1.0, f"{name}: {dauer:.2f} s"

    # Der Datensatzzeiger läuft weiter zwischen Tabelle, Navigator und
    # Anzeige hin und her.
    gitter = ergebnis["dbgrid"]
    anzeige = DBText(formular, quelle)
    anzeige.field = "name"
    navigator = DBNavigator(formular, quelle)
    navigator.knopf_letzter.click()
    assert abfrage.record_index == ZEILEN - 1
    assert gitter._qwidget.currentRow() == ZEILEN - 1
    assert anzeige._qwidget.text() == f"Name {ZEILEN - 1}"
    gitter._qwidget.setCurrentCell(12_345, 0)
    assert abfrage.record_index == 12_345
    assert anzeige._qwidget.text() == "Name 12345"
    assert gitter._qwidget.item(12_345, 2).text() == "3086,25"

    # `cells` und `to_dataframe` wie bisher.
    tabelle = ergebnis["stringgrid"]
    assert tabelle.row_count == ZEILEN + 1
    assert tabelle.cells[1, 0] == "name"
    assert tabelle.cells[2, 12_346] == "3086,25"
    tabelle.cells[3, ZEILEN] = "Bonn"
    assert tabelle.cells[3, ZEILEN] == "Bonn"
    zurueck = tabelle.to_dataframe()
    assert zurueck.shape == (ZEILEN, 4)
    assert zurueck["nr"].sum() == df["nr"].sum()
    assert zurueck["ort"].iloc[-1] == "Bonn"
    db.connected = False
