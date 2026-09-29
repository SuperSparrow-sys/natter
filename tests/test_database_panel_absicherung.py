"""Datenbank-Panel: Transaktionen, Abbruch, Fehlermeldungen,
Bezeichner, Dump, BOM und Dateipfade (Punkte 234, 237, 239-244).
Headless gegen echtes SQLite."""

from __future__ import annotations

import codecs
import csv
import json
import math
import os
import sqlite3
import stat
import time
from contextlib import closing
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer

from ide.database import DatenbankPanel
from ide.database import panel as panel_modul
from ide.viewers.csv_ansicht import csv_erkennen
from pcl.errors import NatterDatenbankError


@pytest.fixture(autouse=True)
def _im_probeordner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Das Panel verbindet nur mit einer Datei (Punkt 430). Ein Name
    ohne Pfad landet so im Probeordner des Tests."""
    monkeypatch.chdir(tmp_path)


def _verbunden(ziel: str = "probe.sqlite") -> DatenbankPanel:
    if ziel == "probe.sqlite":
        sqlite3.connect(ziel).close()
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


def _tabelle_waehlen(panel: DatenbankPanel, name: str) -> None:
    baum = panel.tabellenbaum
    for i in range(baum.topLevelItemCount()):
        if baum.topLevelItem(i).text(0) == name:
            baum.setCurrentItem(baum.topLevelItem(i))
            return
    raise AssertionError(f"{name} fehlt im Baum")


def _meldungen_sammeln(monkeypatch) -> list[str]:  # noqa: ANN001
    meldungen: list[str] = []
    monkeypatch.setattr(
        "ide.database.panel.QMessageBox.warning",
        staticmethod(lambda _eltern, _titel, text: meldungen.append(text)),
    )
    return meldungen


# -- Punkt 234 ---------------------------------------------------------


def _noten_anlegen(panel: DatenbankPanel) -> list[tuple]:
    _roh(panel).execute("CREATE TABLE noten (fach TEXT, note INTEGER)")
    _roh(panel).execute("INSERT INTO noten VALUES ('Mathe', 2)")
    _roh(panel).commit()
    return _roh(panel).execute("SELECT * FROM noten").fetchall()


def test_import_mit_doppelter_spalte_laesst_die_alte_tabelle_stehen(
    tmp_path: Path,
) -> None:
    panel = _verbunden()
    vorher = _noten_anlegen(panel)
    csv_datei = tmp_path / "noten.csv"
    csv_datei.write_text("fach;fach\nDeutsch;Englisch\n", encoding="utf-8")

    with pytest.raises(NatterDatenbankError, match="zweimal"):
        panel.csv_importieren(csv_datei, "noten", ersetzen=True)

    assert panel._tabellennamen() == ["noten"]
    assert _roh(panel).execute("SELECT * FROM noten").fetchall() == vorher


class _ScheiterndeVerbindung:
    """Reicht alles an die echte Verbindung durch, lässt aber das
    Einfügen scheitern, nachdem es gelaufen ist - wie ein volles
    Laufwerk mitten im Import."""

    def __init__(self, echt: sqlite3.Connection) -> None:
        self._echt = echt

    def __getattr__(self, name: str):  # noqa: ANN204
        return getattr(self._echt, name)

    def executemany(self, *args, **kwargs):  # noqa: ANN002, ANN003, ANN201
        self._echt.executemany(*args, **kwargs)
        raise sqlite3.OperationalError("disk I/O error")


def test_fehler_mitten_im_import_rollt_alles_zurueck(
    tmp_path: Path, monkeypatch
) -> None:
    panel = _verbunden()
    vorher = _noten_anlegen(panel)
    echt = _roh(panel)
    csv_datei = tmp_path / "noten.csv"
    csv_datei.write_text("fach;note\nDeutsch;1\n", encoding="utf-8")
    monkeypatch.setattr(panel, "_roh", lambda: _ScheiterndeVerbindung(echt))

    with pytest.raises(sqlite3.OperationalError):
        panel.csv_importieren(csv_datei, "noten", ersetzen=True)

    assert not echt.in_transaction
    tabellen = echt.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    assert tabellen == [("noten",)]
    assert echt.execute("SELECT * FROM noten").fetchall() == vorher


def test_import_von_5000_zeilen_bleibt_unter_einer_sekunde(
    tmp_path: Path,
) -> None:
    datenbank = tmp_path / "gross.sqlite"
    sqlite3.connect(datenbank).close()
    panel = _verbunden(str(datenbank))
    csv_datei = tmp_path / "gross.csv"
    zeilen = "".join(f"Name {i};{i}\n" for i in range(5000))
    csv_datei.write_text("name;wert\n" + zeilen, encoding="utf-8")

    start = time.perf_counter()
    panel.csv_importieren(csv_datei)
    dauer = time.perf_counter() - start
    panel.trennen()

    assert dauer < 1.0
    with closing(sqlite3.connect(datenbank)) as pruefung:
        assert pruefung.execute("SELECT count(*) FROM gross").fetchone() == (5000,)


# -- Punkt 237 ---------------------------------------------------------


def test_insert_im_panel_ist_festgeschrieben_und_sperrt_nicht(
    tmp_path: Path,
) -> None:
    datenbank = tmp_path / "konten.sqlite"
    with closing(sqlite3.connect(datenbank)) as anlegen:
        anlegen.execute("CREATE TABLE konto (inhaber TEXT)")
        anlegen.execute("INSERT INTO konto VALUES ('Anna')")
        anlegen.commit()
    panel = _verbunden(str(datenbank))

    status = _ausfuehren(panel, "INSERT INTO konto VALUES ('Bo')")

    assert status == "1 Zeile geändert."
    assert not _roh(panel).in_transaction
    zweite = sqlite3.connect(datenbank, timeout=0)
    try:
        assert zweite.execute(
            "SELECT inhaber FROM konto ORDER BY inhaber"
        ).fetchall() == [("Anna",), ("Bo",)]
        # Ohne Festschreiben hielt das Panel die Schreibsperre, und das
        # hier scheiterte mit „database is locked“.
        zweite.execute("INSERT INTO konto VALUES ('Cem')")
        zweite.commit()
    finally:
        zweite.close()
        panel.trennen()


def test_gescheiterte_schreibende_anweisung_laesst_keine_transaktion_offen(
    tmp_path: Path,
) -> None:
    panel = _verbunden()
    _roh(panel).execute("CREATE TABLE t (n INTEGER UNIQUE)")
    _ausfuehren(panel, "INSERT INTO t VALUES (1)")

    status = _ausfuehren(panel, "INSERT INTO t VALUES (1)")

    assert "eindeutig" in status
    assert not _roh(panel).in_transaction


# -- Punkt 239 ---------------------------------------------------------

_OHNE_ENDE = (
    "WITH RECURSIVE z(n) AS (SELECT 1 UNION ALL SELECT n + 1 FROM z) "
)


def test_abfrage_ohne_ende_bricht_nach_der_zeitgrenze_ab() -> None:
    panel = _verbunden()
    panel.zeitgrenze_sekunden = 1.0

    start = time.monotonic()
    status = _ausfuehren(panel, _OHNE_ENDE + "SELECT count(*) FROM z")
    dauer = time.monotonic() - start

    assert dauer < 5
    assert "länger als 1 Sekunde " in status
    assert not panel.laeuft
    # Danach geht es weiter wie vorher.
    assert _ausfuehren(panel, "SELECT 42") == "1 Zeile."
    assert panel.ergebnis_tabelle.item(0, 0).text() == "42"


def test_oberflaeche_bleibt_bedienbar_und_abbrechen_wirkt() -> None:
    panel = _verbunden()
    panel.zeitgrenze_sekunden = 60.0
    waehrenddessen: list[bool] = []

    def klicken() -> None:
        waehrenddessen.append(panel.laeuft)
        panel._abbrechen_knopf.click()

    QTimer.singleShot(300, klicken)
    start = time.monotonic()
    status = _ausfuehren(panel, _OHNE_ENDE + "SELECT count(*) FROM z")

    assert waehrenddessen == [True]
    assert time.monotonic() - start < 5
    assert status == "Die Abfrage wurde abgebrochen."
    assert panel._ausfuehren_knopf.isEnabled()
    assert not panel._abbrechen_knopf.isEnabled()


def test_endlose_zeilen_werden_nach_der_hoechstzahl_abgeschnitten() -> None:
    panel = _verbunden()

    status = _ausfuehren(panel, _OHNE_ENDE + "SELECT n FROM z")

    assert panel.ergebnis_tabelle.rowCount() == panel_modul.HOECHSTZAHL_ZEILEN
    assert status == "Nur die ersten 1.000 Zeilen werden angezeigt."


# -- Punkt 240 ---------------------------------------------------------


def test_verbinden_mit_einer_fremden_datei_meldet_deutsch(tmp_path: Path) -> None:
    fremd = tmp_path / "kaputt.sqlite"
    fremd.write_text("Das ist keine Datenbank.\n" * 100, encoding="utf-8")
    panel = DatenbankPanel()
    panel._sqlite_pfad.setText(str(fremd))

    panel._verbinden()

    assert panel.verbindung is None
    assert "keine Datenbank" in panel._status_label.text()
    fremd.unlink()


@pytest.mark.parametrize("art", ["csv", "sql"])
def test_export_in_gesperrte_datei_meldet_statt_zu_werfen(
    tmp_path: Path, monkeypatch, art: str
) -> None:
    panel = _verbunden()
    _ausfuehren(panel, "CREATE TABLE t (n INTEGER)")
    _tabelle_waehlen(panel, "t")
    ziel = tmp_path / f"gesperrt.{art}"
    ziel.write_text("", encoding="utf-8")
    os.chmod(ziel, stat.S_IREAD)
    monkeypatch.setattr(
        "ide.database.panel.QFileDialog.getSaveFileName",
        staticmethod(lambda *a, **k: (str(ziel), "")),
    )
    meldungen = _meldungen_sammeln(monkeypatch)
    try:
        if art == "csv":
            panel._csv_exportieren_dialog()
        else:
            panel._sql_dump_exportieren_dialog()
    finally:
        os.chmod(ziel, stat.S_IREAD | stat.S_IWRITE)

    assert len(meldungen) == 1
    assert "lässt sich nicht schreiben" in meldungen[0]


def test_sql_fehler_steht_deutsch_in_der_statuszeile() -> None:
    panel = _verbunden()

    status = _ausfuehren(panel, "SELECT * FROM fehlt")

    assert status == (
        "SQL-Fehler: eine Tabelle namens „fehlt“ gibt es in der "
        "Datenbank nicht"
    )


# -- Punkt 241 ---------------------------------------------------------


def test_namen_mit_anfuehrungszeichen(tmp_path: Path) -> None:
    panel = _verbunden()
    _roh(panel).execute('CREATE TABLE "a""b" ("c""d" TEXT)')
    _roh(panel).execute('INSERT INTO "a""b" VALUES (\'x\')')
    _roh(panel).commit()
    panel._tabellenbaum_aktualisieren()

    assert _baumnamen(panel) == ['a"b']
    assert panel.tabellenbaum.topLevelItem(0).child(0).text(0) == 'c"d'

    panel.tabelle_als_csv_exportieren('a"b', tmp_path / "ab.csv")
    with open(tmp_path / "ab.csv", encoding="utf-8-sig", newline="") as datei:
        assert list(csv.reader(datei, delimiter=";")) == [['c"d'], ["x"]]
    panel.tabelle_als_sql_dump_exportieren('a"b', tmp_path / "ab.sql")
    neu = sqlite3.connect(":memory:")
    neu.executescript((tmp_path / "ab.sql").read_text(encoding="utf-8"))
    assert neu.execute('SELECT "c""d" FROM "a""b"').fetchall() == [("x",)]

    csv_datei = tmp_path / "zitat.csv"
    csv_datei.write_text('"x""y";z\n1;2\n', encoding="utf-8")
    name = panel.csv_importieren(csv_datei)
    assert _roh(panel).execute(
        f'SELECT "x""y", z FROM "{name}"'
    ).fetchall() == [(1, 2)]


# -- Punkt 242 ---------------------------------------------------------


def test_dump_laesst_sich_in_eine_leere_datenbank_einspielen(
    tmp_path: Path,
) -> None:
    panel = _verbunden()
    _roh(panel).execute(
        "CREATE TABLE werte (id INTEGER PRIMARY KEY, text TEXT, "
        "zahl REAL, leer TEXT, bild BLOB)"
    )
    zeilen = [
        (1, "O'Brien", 2.5, None, b"\x00\x01'x\""),
        (2, "Änne", math.inf, None, b""),
        (3, "", -math.inf, None, None),
    ]
    _roh(panel).executemany("INSERT INTO werte VALUES (?, ?, ?, ?, ?)", zeilen)
    _roh(panel).commit()
    ziel = tmp_path / "werte.sql"

    panel.tabelle_als_sql_dump_exportieren("werte", ziel)

    neu = sqlite3.connect(":memory:")
    neu.executescript(ziel.read_text(encoding="utf-8"))
    assert neu.execute("SELECT * FROM werte ORDER BY id").fetchall() == zeilen

    panel.tabelle_als_csv_exportieren("werte", tmp_path / "werte.csv")
    assert "b'" not in (tmp_path / "werte.csv").read_text(encoding="utf-8-sig")


# -- Punkt 243 ---------------------------------------------------------


def test_csv_mit_bom_wird_ohne_bom_im_spaltennamen_importiert(
    tmp_path: Path,
) -> None:
    panel = _verbunden()
    csv_datei = tmp_path / "klasse.csv"
    csv_datei.write_text("Name;Punkte\nÄnne;3\n", encoding="utf-8-sig")
    assert csv_erkennen(csv_datei) == (";", "utf-8-sig")

    panel.csv_importieren(csv_datei)

    status = _ausfuehren(panel, "SELECT Name FROM klasse")
    assert status == "1 Zeile."
    assert panel.ergebnis_tabelle.item(0, 0).text() == "Änne"


def test_csv_export_schreibt_eine_bom_fuer_excel(tmp_path: Path) -> None:
    panel = _verbunden()
    _ausfuehren(panel, "CREATE TABLE t (name TEXT)")
    _ausfuehren(panel, "INSERT INTO t VALUES ('Jürgen')")
    ziel = tmp_path / "t.csv"

    panel.tabelle_als_csv_exportieren("t", ziel)

    assert ziel.read_bytes().startswith(codecs.BOM_UTF8)
    assert ziel.read_bytes().decode("utf-8-sig") =="name\r\nJürgen\r\n"


# -- Punkt 244 ---------------------------------------------------------


def _konten_datei(ordner: Path) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    datei = ordner / "konten.sqlite"
    with closing(sqlite3.connect(datei)) as anlegen:
        anlegen.execute("CREATE TABLE konto (inhaber TEXT)")
        anlegen.commit()
    return datei


def test_dateiname_ohne_pfad_gilt_im_projektordner(tmp_path: Path) -> None:
    projekt = tmp_path / "proj"
    datei = _konten_datei(projekt)
    panel = DatenbankPanel()
    panel.projektordner_setzen(projekt)
    panel._sqlite_pfad.setText("konten.sqlite")

    panel._verbinden()

    assert panel.verbindung is not None
    assert Path(panel.verbindung.database_name) == datei
    assert _baumnamen(panel) == ["konto"]

    panel._trennen_knopf.click()
    assert panel.verbindung is None
    datei.unlink()


def test_tippfehler_legt_nicht_still_eine_datei_an(
    tmp_path: Path, monkeypatch
) -> None:
    panel = DatenbankPanel()
    panel.projektordner_setzen(tmp_path)
    gefragt: list[Path] = []

    def fragen(pfad: Path) -> bool:
        gefragt.append(pfad)
        return False

    monkeypatch.setattr(panel, "_datei_anlegen_fragen", fragen)
    panel._sqlite_pfad.setText("kontne.sqlite")
    panel._verbinden()

    assert gefragt == [tmp_path / "kontne.sqlite"]
    assert panel.verbindung is None
    assert not (tmp_path / "kontne.sqlite").exists()


def test_neues_verbinden_schliesst_die_vorige_verbindung(tmp_path: Path) -> None:
    erste = _konten_datei(tmp_path / "a")
    zweite = _konten_datei(tmp_path / "b")
    panel = _verbunden(str(erste))
    alte = panel.verbindung

    panel._sqlite_pfad.setText(str(zweite))
    panel._verbinden()

    assert not alte.connected
    erste.unlink()
    panel.trennen()


def test_projektwechsel_gibt_die_datenbankdatei_frei(
    hauptfenster_bauen, tmp_path: Path
) -> None:
    def projekt(name: str) -> Path:
        ordner = tmp_path / name
        ordner.mkdir()
        (ordner / "main.py").write_text("a = 1\n", encoding="utf-8")
        natter = ordner / f"{name}.natter"
        natter.write_text(json.dumps({
            "format": "natter-project/1", "name": name,
            "type": "console", "main": "main.py",
        }), encoding="utf-8")
        return natter

    alt = projekt("alt")
    neu = projekt("neu")
    datei = _konten_datei(tmp_path / "alt")
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(alt)
    fenster.datenbank_panel._sqlite_pfad.setText("konten.sqlite")
    fenster.datenbank_panel._verbinden()
    assert fenster.datenbank_panel.verbindung is not None

    fenster.projekt_oeffnen(neu)

    assert fenster.datenbank_panel.verbindung is None
    datei.unlink()
    (tmp_path / "alt").rename(tmp_path / "alt_umbenannt")
