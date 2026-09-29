"""Datenbank-Panel: Speichergrenze der Ergebnistabelle, Import und
Export unter Aufsicht, „Ersetzen“ mit Ansicht, Dump mit berechneten
Spalten (Punkte 257, 258, 261, 262 und der Panel-Teil von 263).
Headless gegen echtes SQLite."""

from __future__ import annotations

import json
import os
import sqlite3
import stat
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer

from ide.database import DatenbankPanel
from ide.database import panel as panel_modul

WURZEL = Path(__file__).resolve().parent.parent


def _verbunden(ziel: str = ":memory:") -> DatenbankPanel:
    panel = DatenbankPanel()
    panel._sqlite_pfad.setText(ziel)
    panel._verbinden()
    assert panel.verbindung is not None, panel._status_label.text()
    return panel


def _roh(panel: DatenbankPanel) -> sqlite3.Connection:
    return panel.verbindung.verbindung


def _ausfuehren(panel: DatenbankPanel, sql: str) -> str:
    panel._sql_eingabe.setPlainText(sql)
    panel._sql_ausfuehren()
    return panel._status_label.text()


def _baumnamen(panel: DatenbankPanel) -> list[str]:
    baum = panel.tabellenbaum
    return [baum.topLevelItem(i).text(0) for i in range(baum.topLevelItemCount())]


# -- Punkt 257 ---------------------------------------------------------

#: Die Abfrage aus der Probe, verkleinert: 40 Zeilen mit je 5 MB Text
#: und 5 MB Binärdaten. Ohne Grenze hielt das Panel davon rund 800 MB
#: in Python und noch einmal so viel in den Tabellenzellen.
_GROSSE_WERTE = (
    "WITH RECURSIVE z(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM z "
    "WHERE n < 40) SELECT n, printf('%5000000s', 'x') AS t, "
    "zeroblob(5000000) AS b FROM z"
)

_SPEICHERPROBE = r'''
import ctypes, json, os, sys
from ctypes import wintypes

class Zaehler(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
    ]

kernel32 = ctypes.WinDLL("kernel32")
kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.K32GetProcessMemoryInfo.argtypes = [
    wintypes.HANDLE, ctypes.POINTER(Zaehler), wintypes.DWORD,
]
kernel32.K32GetProcessMemoryInfo.restype = wintypes.BOOL

def spitze():
    zaehler = Zaehler()
    zaehler.cb = ctypes.sizeof(zaehler)
    assert kernel32.K32GetProcessMemoryInfo(
        kernel32.GetCurrentProcess(), ctypes.byref(zaehler), zaehler.cb,
    )
    assert zaehler.PeakPagefileUsage > 0
    return zaehler.PeakPagefileUsage

from PySide6.QtWidgets import QApplication
app = QApplication([])
from ide.database import DatenbankPanel
panel = DatenbankPanel()
panel._sqlite_pfad.setText(":memory:")
panel._verbinden()
panel._sql_eingabe.setPlainText(sys.argv[1])
vorher = spitze()
panel._sql_ausfuehren()
tabelle = panel.ergebnis_tabelle
print(json.dumps({
    "zuwachs": spitze() - vorher,
    "status": panel._status_label.text(),
    "zeilen": tabelle.rowCount(),
    "text": len(tabelle.item(0, 1).text()),
    "binaer": tabelle.item(0, 2).text(),
}))
'''


@pytest.mark.skipif(sys.platform != "win32", reason="misst über psapi")
def test_grosse_werte_bleiben_unter_der_speichergrenze(tmp_path: Path) -> None:
    """Gemessen in einem eigenen Prozess, damit die Spitze des
    Speicherbedarfs allein von dieser Abfrage stammt."""
    probe = tmp_path / "probe.py"
    probe.write_text(_SPEICHERPROBE, encoding="utf-8")
    umgebung = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    lauf = subprocess.run(
        [sys.executable, str(probe), _GROSSE_WERTE],
        cwd=WURZEL, env=umgebung, capture_output=True, text=True,
        timeout=100,
    )
    assert lauf.returncode == 0, lauf.stderr
    ergebnis = json.loads(lauf.stdout.strip().splitlines()[-1])

    assert ergebnis["zuwachs"] < 200 * 1024 * 1024, ergebnis
    assert ergebnis["zeilen"] == 40
    assert ergebnis["text"] == panel_modul.ZEICHEN_JE_ZELLE + 1
    assert ergebnis["binaer"] == "(Binärdaten, 5000000 Bytes)"
    assert ergebnis["status"] == (
        "40 Zeilen. Lange Texte sind nach 500 Zeichen gekürzt."
    )


def test_kurze_werte_und_reihenfolge_bleiben_wie_sie_sind() -> None:
    panel = _verbunden()
    _roh(panel).execute("CREATE TABLE t (n INTEGER, x REAL, s TEXT)")
    _roh(panel).executemany(
        "INSERT INTO t VALUES (?, ?, ?)",
        [(3, 1.5, "c"), (1, None, "a"), (2, 2.0, None)],
    )
    _roh(panel).commit()

    status = _ausfuehren(panel, "SELECT n, x, s, n FROM t ORDER BY n DESC;")

    tabelle = panel.ergebnis_tabelle
    assert status == "3 Zeilen."
    assert [
        [tabelle.item(z, s).text() for s in range(4)] for z in range(3)
    ] == [["3", "1,5", "c", "3"], ["2", "2", "", "2"], ["1", "", "a", "1"]]


def test_viele_spalten_begrenzen_die_zeichen_insgesamt(monkeypatch) -> None:
    monkeypatch.setattr(panel_modul, "HOECHSTZAHL_ZEICHEN", 3000)
    panel = _verbunden()

    status = _ausfuehren(
        panel,
        "WITH RECURSIVE z(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM z "
        "WHERE n < 100) SELECT printf('%100s', n) FROM z",
    )

    assert panel.ergebnis_tabelle.rowCount() == 30
    assert status == "Nur die ersten 30 Zeilen werden angezeigt."


# -- Punkt 258 ---------------------------------------------------------


def _grosse_csv(ordner: Path, zeilen: int = 200_000) -> Path:
    datei = ordner / "messwerte.csv"
    datei.write_text(
        "zeit;wert\n" + "".join(f"{i};{i * 0.5}\n" for i in range(zeilen)),
        encoding="utf-8",
    )
    return datei


def test_import_laesst_die_oberflaeche_arbeiten(tmp_path: Path) -> None:
    panel = _verbunden()
    takte: list[bool] = []
    uhr = QTimer()
    uhr.setInterval(20)
    uhr.timeout.connect(lambda: takte.append(panel.laeuft))
    uhr.start()
    try:
        panel.csv_importieren(_grosse_csv(tmp_path))
    finally:
        uhr.stop()

    assert takte, "während des Imports kam kein einziges Ereignis an"
    assert all(takte)
    assert not panel.laeuft
    assert _roh(panel).execute(
        "SELECT count(*) FROM messwerte"
    ).fetchone() == (200_000,)


def test_abbrechen_beim_import_laesst_die_datenbank_unveraendert(
    tmp_path: Path,
) -> None:
    datenbank = tmp_path / "daten.sqlite"
    with closing(sqlite3.connect(datenbank)) as anlegen:
        anlegen.execute("CREATE TABLE messwerte (zeit TEXT, wert TEXT)")
        anlegen.execute("INSERT INTO messwerte VALUES ('0', 'alt')")
        anlegen.commit()
    panel = _verbunden(str(datenbank))
    QTimer.singleShot(0, panel._abbrechen_knopf.click)

    with pytest.raises(panel_modul._Abbruch, match="unverändert"):
        panel.csv_importieren(
            _grosse_csv(tmp_path), "messwerte", ersetzen=True
        )

    assert not panel.laeuft
    assert panel._ausfuehren_knopf.isEnabled()
    assert not _roh(panel).in_transaction
    panel.trennen()
    with closing(sqlite3.connect(datenbank)) as pruefung:
        assert pruefung.execute(
            "SELECT name FROM sqlite_master"
        ).fetchall() == [("messwerte",)]
        assert pruefung.execute("SELECT * FROM messwerte").fetchall() == [
            ("0", "alt")
        ]


@pytest.mark.parametrize("art", ["csv", "sql"])
def test_abbrechen_beim_export_laesst_keine_datei_liegen(
    tmp_path: Path, art: str
) -> None:
    panel = _verbunden()
    _roh(panel).execute("CREATE TABLE t (n INTEGER, s TEXT)")
    _roh(panel).executemany(
        "INSERT INTO t VALUES (?, ?)",
        ((i, f"Zeile {i}") for i in range(200_000)),
    )
    _roh(panel).commit()
    ausgabe = tmp_path / "ausgabe"
    ausgabe.mkdir()
    ziel = ausgabe / f"t.{art}"
    QTimer.singleShot(0, panel._abbrechen_knopf.click)

    with pytest.raises(panel_modul._Abbruch):
        if art == "csv":
            panel.tabelle_als_csv_exportieren("t", ziel)
        else:
            panel.tabelle_als_sql_dump_exportieren("t", ziel)

    assert list(ausgabe.iterdir()) == []
    assert not panel.laeuft


# -- Punkt 261 ---------------------------------------------------------


def test_ersetzen_trotz_ansicht_auf_die_tabelle(tmp_path: Path) -> None:
    panel = _verbunden()
    _roh(panel).executescript(
        "CREATE TABLE konto (inhaber TEXT, stand INTEGER);"
        "INSERT INTO konto VALUES ('Anna', 5), ('Bo', 500);"
        "CREATE VIEW reich AS SELECT inhaber FROM konto "
        "WHERE CAST(stand AS INTEGER) > 100;"
    )
    csv_datei = tmp_path / "konto.csv"
    csv_datei.write_text(
        "inhaber;stand\nCem;900\nDana;1\n", encoding="utf-8"
    )

    assert panel.csv_importieren(csv_datei, "konto", ersetzen=True) == "konto"

    assert _roh(panel).execute("SELECT * FROM reich").fetchall() == [("Cem",)]
    assert _roh(panel).execute(
        "SELECT count(*) FROM konto"
    ).fetchone() == (2,)


def test_ansicht_ohne_passende_spalte_meldet_sich_deutsch() -> None:
    """Scheitert eine Änderung doch an einer Ansicht, nennt die
    Meldung sie."""
    panel = _verbunden()
    _roh(panel).executescript(
        "CREATE TABLE t (a); CREATE TABLE x (b);"
        "CREATE VIEW v AS SELECT b FROM x; DROP TABLE x;"
    )

    status = _ausfuehren(panel, "ALTER TABLE t RENAME TO t2")

    assert status == (
        "SQL-Fehler: die Ansicht „v“ passt nicht zur geänderten Tabelle: "
        "eine Tabelle namens „main.x“ gibt es in der Datenbank nicht"
    )


# -- Punkt 262 ---------------------------------------------------------


def test_dump_mit_berechneter_spalte_laesst_sich_einspielen(
    tmp_path: Path,
) -> None:
    panel = _verbunden()
    _roh(panel).executescript(
        "CREATE TABLE r (b INTEGER, c INTEGER GENERATED ALWAYS AS (b * 2), "
        "d INTEGER GENERATED ALWAYS AS (b + 1) STORED);"
        "INSERT INTO r (b) VALUES (1), (5);"
        "CREATE TABLE k (nr INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT);"
        "INSERT INTO k (name) VALUES ('Anna');"
    )
    panel._tabellenbaum_aktualisieren()
    ziel = tmp_path / "r.sql"

    panel.tabelle_als_sql_dump_exportieren("r", ziel)
    panel.tabelle_als_sql_dump_exportieren("k", tmp_path / "k.sql")

    neu = sqlite3.connect(":memory:")
    neu.executescript(ziel.read_text(encoding="utf-8"))
    neu.executescript((tmp_path / "k.sql").read_text(encoding="utf-8"))
    assert neu.execute("SELECT b, c, d FROM r ORDER BY b").fetchall() == [
        (1, 2, 2), (5, 10, 6),
    ]
    assert neu.execute("SELECT * FROM k").fetchall() == [(1, "Anna")]
    assert _baumnamen(panel) == ["k", "r"]


def test_dump_von_sqlite_sequence_meldet_sich_deutsch(tmp_path: Path) -> None:
    panel = _verbunden()
    _roh(panel).execute(
        "CREATE TABLE k (nr INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)"
    )
    _roh(panel).execute("INSERT INTO k (name) VALUES ('Anna')")
    _roh(panel).commit()

    with pytest.raises(panel_modul.NatterDatenbankError, match="interne"):
        panel.tabelle_als_sql_dump_exportieren(
            "sqlite_sequence", tmp_path / "s.sql"
        )
    assert not (tmp_path / "s.sql").exists()


# -- Punkt 263, Teil des Panels -----------------------------------------


def test_schreibgeschuetzte_datei_meldet_sich_deutsch(tmp_path: Path) -> None:
    datenbank = tmp_path / "material.sqlite"
    with closing(sqlite3.connect(datenbank)) as anlegen:
        anlegen.execute("CREATE TABLE t (n INTEGER)")
        anlegen.commit()
    os.chmod(datenbank, stat.S_IREAD)
    try:
        panel = _verbunden(str(datenbank))
        status = _ausfuehren(panel, "INSERT INTO t VALUES (1)")
        panel.trennen()
    finally:
        os.chmod(datenbank, stat.S_IREAD | stat.S_IWRITE)

    assert "schreibgeschützt" in status
    assert "readonly" not in status
