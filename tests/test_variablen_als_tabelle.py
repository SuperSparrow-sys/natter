"""Punkt 612: „Als Tabelle anzeigen“ an einer aufgeklappten Variablen.

Ausgewertet wurde der angezeigte Name: das Kind `werte` eines Objekts
`p` ergab die globale Variable `werte`, die Zeile `0` einer Matrix die
Zahl 0. Jetzt gilt `evaluateName` aus der Antwort von debugpy.
"""

from __future__ import annotations

from pathlib import Path

from ide.debugger import DapClient
from ide.debugger.tabellenansicht import tabelle_aus_antwort, tabellen_ausdruck


def test_das_panel_wertet_den_ausdruck_des_eintrags_aus(hauptfenster, monkeypatch) -> None:  # noqa: ANN001
    gefragt: list[str] = []
    monkeypatch.setattr(hauptfenster, "variable_als_tabelle_zeigen", gefragt.append)
    baum = hauptfenster.variablen_baum
    hauptfenster._variablen_eintraege(baum, [
        {"name": "p", "value": "<P>", "variablesReference": 7, "evaluateName": "p"},
        {"name": "matrix", "value": "[[1, 2]]", "variablesReference": 8},
    ])
    p, matrix = baum.topLevelItem(0), baum.topLevelItem(1)
    hauptfenster._variablen_eintraege(p, [
        {"name": "werte", "value": "[[1, 2]]", "evaluateName": "p.werte"},
        {"name": "ohne", "value": "1"},
    ])
    hauptfenster._variablen_eintraege(matrix, [
        {"name": "0", "value": "[1, 2]", "evaluateName": "matrix[0]"},
    ])

    for eintrag in (p.child(0), matrix.child(0), matrix, p.child(1)):
        hauptfenster._eintrag_als_tabelle_zeigen(eintrag)

    # Das Kind „ohne“ hat keinen Ausdruck und bleibt ohne Wirkung.
    assert gefragt == ["p.werte", "matrix[0]", "matrix"]


def test_die_gruppe_globale_variablen_ist_keine_variable(hauptfenster, monkeypatch) -> None:  # noqa: ANN001
    gefragt: list[str] = []
    monkeypatch.setattr(hauptfenster, "variable_als_tabelle_zeigen", gefragt.append)
    hauptfenster._debugger_antwort(
        "global", [{"name": "zahl", "value": "3", "variablesReference": 0}]
    )
    gruppe = hauptfenster.variablen_baum.topLevelItem(
        hauptfenster.variablen_baum.topLevelItemCount() - 1
    )

    hauptfenster._eintrag_als_tabelle_zeigen(gruppe)
    hauptfenster._eintrag_als_tabelle_zeigen(gruppe.child(0))

    # Über den globalen Namensraum (Punkt 632).
    assert gefragt == ["globals()['zahl']"]


def test_matrixzeile_und_attribut_als_tabelle(tmp_path: Path) -> None:
    skript = tmp_path / "ziel.py"
    skript.write_text(
        "class P:\n    pass\n\np = P()\np.werte = [[1, 2], [3, 4]]\n"
        "werte = 'text'\nmatrix = [[1, 2], [3, 4]]\nmarker = 1\n",
        encoding="utf-8",
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [8]})
        ereignis = client.angehalten_abwarten()
        frame = client.aufrufstapel_lesen(ereignis["threadId"])[0]["id"]
        lokale = next(
            b for b in client.bereiche_lesen(frame) if b["name"] == "Locals"
        )
        ausdruecke = {}
        for variable in client.variablen_lesen(lokale["variablesReference"]):
            if variable["name"] in ("p", "matrix"):
                for kind in client.variablen_lesen(variable["variablesReference"]):
                    ausdruecke[(variable["name"], kind["name"])] = kind.get("evaluateName")
        zeile = tabelle_aus_antwort(
            client.auswerten(tabellen_ausdruck(ausdruecke[("matrix", "0")]), frame)["result"]
        )
        attribut = tabelle_aus_antwort(
            client.auswerten(tabellen_ausdruck(ausdruecke[("p", "werte")]), frame)["result"]
        )
    finally:
        client.beenden()

    assert [z[-1] for z in zeile.zeilen] == ["1", "2"]
    assert attribut.gesamt == 2


def test_globale_variable_unter_einem_ueberdeckenden_parameter(
    hauptfenster, monkeypatch, tmp_path: Path
) -> None:  # noqa: ANN001
    """Punkt 632: unter „Globale Variablen“ wertete „Als Tabelle anzeigen“
    den gleichnamigen Parameter aus. Jetzt geht der Ausdruck über
    `globals()`, auch für aufgeklappte Kinder, und ergibt im Frame der
    Funktion die globale Liste."""
    gefragt: list[str] = []
    monkeypatch.setattr(hauptfenster, "variable_als_tabelle_zeigen", gefragt.append)
    hauptfenster._debugger_antwort("global", [
        {"name": "werte", "value": "[[1, 2], [3, 4]]", "variablesReference": 5,
         "evaluateName": "werte"},
    ])
    gruppe = hauptfenster.variablen_baum.topLevelItem(
        hauptfenster.variablen_baum.topLevelItemCount() - 1
    )
    hauptfenster._variablen_eintraege(gruppe.child(0), [
        {"name": "0", "value": "[1, 2]", "evaluateName": "werte[0]"},
    ])
    hauptfenster._eintrag_als_tabelle_zeigen(gruppe.child(0))
    hauptfenster._eintrag_als_tabelle_zeigen(gruppe.child(0).child(0))
    assert gefragt == ["globals()['werte']", "globals()['werte'][0]"]

    skript = tmp_path / "ziel.py"
    skript.write_text(
        "werte = [[1, 2], [3, 4]]\n\ndef f(werte):\n    return werte\n\nf(5)\n",
        encoding="utf-8",
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [4]})
        ereignis = client.angehalten_abwarten()
        frame = client.aufrufstapel_lesen(ereignis["threadId"])[0]["id"]
        tabelle = tabelle_aus_antwort(
            client.auswerten(tabellen_ausdruck(gefragt[0]), frame)["result"]
        )
    finally:
        client.beenden()

    assert tabelle.gesamt == 2
