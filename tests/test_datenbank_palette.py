"""Die Datensteuerelemente stehen in der Palette (Punkt 60).

`docs/komponenten.md` sagte, sie ließen sich im Designer platzieren;
in der Palette standen sie nicht. Geprüft wird hier auch, dass ein
Formular mit allen fünf im gestarteten Programm entsteht und ein
DBGrid nach dem Zuweisen der Datenquelle die Zeilen zeigt.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from ide.codegen.design import design_code_erzeugen
from ide.palette.palette import ALLE_KOMPONENTEN, DATENBANK_KOMPONENTEN
from ide.project.neu import projekt_erzeugen


def test_alle_fuenf_stehen_in_der_palette() -> None:
    namen = [typ.__name__ for typ in DATENBANK_KOMPONENTEN]

    assert namen == ["DBGrid", "DBText", "DBEdit", "DBComboBox", "DBNavigator"]
    assert all(typ in ALLE_KOMPONENTEN for typ in DATENBANK_KOMPONENTEN)


def test_ein_formular_mit_datensteuerelementen_laeuft(tmp_path: Path) -> None:
    projekt = projekt_erzeugen("gui", tmp_path / "Konten", "Konten")
    pfm_pfad = projekt.ordner / "u_main.pfm"
    pfm = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    pfm["children"] = [
        {"name": "dbg_konten", "type": "DBGrid",
         "properties": {"left": 8, "top": 8, "width": 260, "height": 150}},
        {"name": "dbt_name", "type": "DBText", "properties": {"left": 8, "top": 170}},
        {"name": "dbe_name", "type": "DBEdit", "properties": {"left": 8, "top": 200}},
        {"name": "dbc_name", "type": "DBComboBox", "properties": {"left": 8, "top": 230}},
        {"name": "dbn_konten", "type": "DBNavigator", "properties": {"left": 8, "top": 260}},
    ]
    pfm_pfad.write_text(json.dumps(pfm), encoding="utf-8")
    (projekt.ordner / "u_main_design.py").write_text(
        design_code_erzeugen(pfm, "u_main.pfm"), encoding="utf-8"
    )
    skript = (
        "from pcl import Application, DataSource, SQLite3Connection, SQLQuery\n"
        "app = Application()\n"
        "from u_main import Form1\n"
        "f = Form1()\n"
        "db = SQLite3Connection(':memory:')\n"
        "db.execute('CREATE TABLE konto (name TEXT)')\n"
        "db.execute(\"INSERT INTO konto VALUES ('Ada'), ('Grace')\")\n"
        "q = SQLQuery(db)\n"
        "q.sql = 'SELECT name FROM konto'\n"
        "q.open()\n"
        "f.dbg_konten.data_source = DataSource(q)\n"
        "print(f.dbg_konten._qwidget.rowCount())\n"
    )
    lauf = subprocess.run(
        [sys.executable, "-c", skript],
        cwd=projekt.ordner,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        check=False,
    )

    assert lauf.returncode == 0, lauf.stderr
    assert lauf.stdout.strip() == "2"
