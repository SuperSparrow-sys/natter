"""Tests für „Als Tabelle anzeigen“ im Variablen-Panel (Abschnitt 11.6,
Arbeitspaket M5 „Zurückgestellt“).

Drei Ebenen: die reine Umwandlung (`tabelle_aus_wert`), der Ausdruck,
der im angehaltenen Schülerprogramm läuft (`tabellen_ausdruck`, gegen
echtes `debugpy`), und die Anzeige (`TabellenAnsicht`).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.debugger import DapClient
from ide.debugger.tabellenansicht import (
    TabellenFehler,
    tabelle_aus_antwort,
    tabelle_aus_wert,
    tabellen_ausdruck,
)
from ide.viewers import TabellenAnsicht

# -- Umwandlung -----------------------------------------------------------


def test_liste_von_dictionaries_wird_zur_tabelle() -> None:
    tabelle = tabelle_aus_wert([{"name": "Anna", "punkte": 12}, {"name": "Ben", "punkte": 9}])

    assert tabelle.spalten == ["name", "punkte"]
    assert tabelle.zeilen == [["Anna", "12"], ["Ben", "9"]]
    assert tabelle.art == "Liste von Dictionaries"
    assert tabelle.gesamt == 2
    assert not tabelle.gekuerzt


def test_fehlende_schluessel_bleiben_leer() -> None:
    tabelle = tabelle_aus_wert([{"a": 1}, {"b": 2}])

    assert tabelle.spalten == ["a", "b"]
    assert tabelle.zeilen == [["1", ""], ["", "2"]]


def test_liste_von_listen_bekommt_nummerierte_spalten() -> None:
    tabelle = tabelle_aus_wert([[1, 2, 3], [4, 5, 6]])

    assert tabelle.spalten == ["0", "1", "2"]
    assert tabelle.zeilen == [["1", "2", "3"], ["4", "5", "6"]]


def test_unterschiedlich_lange_zeilen_werden_aufgefuellt() -> None:
    tabelle = tabelle_aus_wert([[1, 2], [3]])

    assert tabelle.zeilen == [["1", "2"], ["3", ""]]


def test_flache_liste_bekommt_nummer_und_wert() -> None:
    tabelle = tabelle_aus_wert(["rot", "gelb", "gruen"])

    assert tabelle.spalten == ["#", "Wert"]
    assert tabelle.zeilen == [["0", "rot"], ["1", "gelb"], ["2", "gruen"]]


def test_dictionary_wird_zu_schluessel_und_wert() -> None:
    tabelle = tabelle_aus_wert({"rot": 3, "gelb": 1})

    assert tabelle.spalten == ["Schlüssel", "Wert"]
    assert tabelle.zeilen == [["rot", "3"], ["gelb", "1"]]
    assert tabelle.art == "Dictionary"


def test_dictionary_aus_gleich_langen_listen_wird_spaltenweise_gelesen() -> None:
    tabelle = tabelle_aus_wert({"name": ["Anna", "Ben"], "punkte": [12, 9]})

    assert tabelle.spalten == ["name", "punkte"]
    assert tabelle.zeilen == [["Anna", "12"], ["Ben", "9"]]
    assert tabelle.art == "Dictionary (spaltenweise)"


def test_dataframe_bekommt_index_als_erste_spalte() -> None:
    import pandas as pd

    tabelle = tabelle_aus_wert(pd.DataFrame({"name": ["Anna", "Ben"], "punkte": [12, 9]}))

    assert tabelle.spalten == ["index", "name", "punkte"]
    assert tabelle.zeilen == [["0", "Anna", "12"], ["1", "Ben", "9"]]
    assert tabelle.art == "DataFrame"


def test_pandas_series_wird_zu_index_und_wert() -> None:
    import pandas as pd

    tabelle = tabelle_aus_wert(pd.Series([10, 20], index=["a", "b"]))

    assert tabelle.spalten == ["index", "Wert"]
    assert tabelle.zeilen == [["a", "10"], ["b", "20"]]


def test_lange_liste_wird_gekuerzt_und_meldet_die_gesamtzahl() -> None:
    tabelle = tabelle_aus_wert(list(range(1000)), max_zeilen=5)

    assert len(tabelle.zeilen) == 5
    assert tabelle.gesamt == 1000
    assert tabelle.gekuerzt


def test_sehr_langer_zellwert_wird_gekuerzt() -> None:
    tabelle = tabelle_aus_wert(["x" * 500], max_zellentext=10)

    assert tabelle.zeilen[0][1] == "x" * 10 + " …"


def test_einfacher_wert_laesst_sich_nicht_als_tabelle_anzeigen() -> None:
    with pytest.raises(TabellenFehler, match="int"):
        tabelle_aus_wert(42)


def test_leere_liste_ergibt_eine_leere_tabelle() -> None:
    tabelle = tabelle_aus_wert([])

    assert tabelle.spalten == ["#", "Wert"]
    assert tabelle.zeilen == []
    assert tabelle.gesamt == 0


# -- Antwort des Debuggers ------------------------------------------------


def test_antwort_in_anfuehrungszeichen_wird_ausgepackt() -> None:
    """`debugpy` liefert den `repr` des Rückgabewerts, also den
    JSON-Text in Hochkommata."""
    roh = '\'{"spalten": ["a"], "zeilen": [["1"]], "gesamt": 1, "art": "Liste"}\''

    tabelle = tabelle_aus_antwort(roh)

    assert tabelle.spalten == ["a"]
    assert tabelle.zeilen == [["1"]]


def test_null_antwort_meldet_dass_es_keine_tabelle_gibt() -> None:
    with pytest.raises(TabellenFehler, match="nicht als Tabelle"):
        tabelle_aus_antwort("null")


def test_unverstaendliche_antwort_meldet_einen_fehler() -> None:
    with pytest.raises(TabellenFehler, match="anders geantwortet als erwartet"):
        tabelle_aus_antwort("NameError: name 'daten' is not defined")


# -- Ausdruck im echten, angehaltenen Programm ----------------------------


def test_ausdruck_im_angehaltenen_programm(tmp_path: Path) -> None:
    """Ein Halt, drei Prüfungen: eine Liste von Dictionaries und ein
    DataFrame werden im Schülerprogramm zur Tabelle, und danach ist
    der Namensraum des Programms unberührt. Der Ausdruck führt seinen
    Hilfscode in einem eigenen, leeren Namensraum aus; im Programm
    darf danach nichts Neues stehen."""
    skript = tmp_path / "ziel.py"
    skript.write_text(
        "import pandas as pd\n"
        'schueler = [{"name": "Anna", "punkte": 12}, {"name": "Ben", "punkte": 9}]\n'
        'tabelle = pd.DataFrame({"name": ["Anna", "Ben"], "punkte": [12, 9]})\n'
        "marker = 1  # Breakpoint Zeile 4\n",
        encoding="utf-8",
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [4]})
        ereignis = client.angehalten_abwarten()
        stapel = client.aufrufstapel_lesen(ereignis["threadId"])
        frame_id = stapel[0]["id"]

        antwort = client.auswerten(tabellen_ausdruck("schueler"), frame_id)
        liste = tabelle_aus_antwort(antwort["result"])
        antwort = client.auswerten(tabellen_ausdruck("tabelle"), frame_id)
        rahmen = tabelle_aus_antwort(antwort["result"])

        bereiche = client.bereiche_lesen(frame_id)
        lokale = next(b for b in bereiche if b["name"] == "Locals")
        namen = {v["name"] for v in client.variablen_lesen(lokale["variablesReference"])}
    finally:
        client.beenden()

    assert liste.spalten == ["name", "punkte"]
    assert liste.zeilen == [["Anna", "12"], ["Ben", "9"]]
    assert rahmen.spalten == ["index", "name", "punkte"]
    assert rahmen.zeilen == [["0", "Anna", "12"], ["1", "Ben", "9"]]
    assert rahmen.art == "DataFrame"
    assert "natter_tabelle" not in namen
    assert "_natter_raum" not in namen


# -- Anzeige --------------------------------------------------------------


def test_tabellenansicht_zeigt_spalten_und_zeilen() -> None:
    tabelle = tabelle_aus_wert([{"name": "Anna", "punkte": 12}])

    fenster = TabellenAnsicht("schueler", tabelle)

    widget = fenster.tabelle_widget
    assert widget.columnCount() == 2
    assert widget.horizontalHeaderItem(0).text() == "name"
    assert widget.rowCount() == 1
    assert widget.item(0, 1).text() == "12"
    assert "schueler" in fenster.windowTitle()
    assert "Liste von Dictionaries" in fenster.beschreibung


def test_tabellenansicht_meldet_die_kuerzung() -> None:
    tabelle = tabelle_aus_wert(list(range(50)), max_zeilen=3)

    fenster = TabellenAnsicht("zahlen", tabelle)

    assert "50 Zeilen" in fenster.beschreibung
    assert "ersten 3" in fenster.beschreibung


def test_tabellenansicht_zaehlt_die_zeilen_nicht_doppelt() -> None:
    """Beim Bildschirmfoto gefunden: neben der Spalte „index“ zählte
    Qts eigene Zeilenleiste ein zweites Mal mit (0,1,2 neben 1,2,3)."""
    tabelle = tabelle_aus_wert(["rot", "gelb"])

    fenster = TabellenAnsicht("farben", tabelle)

    widget = fenster.tabelle_widget
    # `isVisible()` wäre hier nutzlos: das Fenster wird im Test nie
    # gezeigt, also ist nichts darin sichtbar. `isVisibleTo` beantwortet
    # die eigentliche Frage - wäre die Zeilenleiste zu sehen, wenn das
    # Fenster offen wäre?
    assert not widget.verticalHeader().isVisibleTo(widget)


def test_tabellenansicht_filtert_zeilen() -> None:
    tabelle = tabelle_aus_wert(["rot", "gelb", "gruen"])
    fenster = TabellenAnsicht("farben", tabelle)

    fenster._filtern("gel")

    widget = fenster.tabelle_widget
    versteckt = [widget.isRowHidden(zeile) for zeile in range(widget.rowCount())]
    assert versteckt == [True, False, True]


def test_die_kopfzeile_sagt_einzahl_bei_einer_zeile() -> None:
    """Beim Bildschirmfoto aufgefallen: „2 Zeile(n), 2 Spalte(n)“.
    Klammerformen sind in einer deutschen Oberfläche für Schülerinnen
    und Schüler fehl am Platz; der Rest von Natter unterscheidet Ein-
    und Mehrzahl ebenfalls."""
    fenster = TabellenAnsicht("nur_eine", tabelle_aus_wert([{"wert": 1}]))

    assert "1 Zeile," in fenster.beschreibung
    assert "1 Spalte" in fenster.beschreibung
    assert "(n)" not in fenster.beschreibung


def test_grosse_werte_ergeben_zusammenhaengende_erste_zeilen(tmp_path: Path) -> None:
    """Punkt 574: debugpy kürzte die Antwort in der Mitte, und nach
    Zeile 83 folgte 157. Jetzt kommen nur so viele Zeilen, wie
    hineinpassen, und alle von vorn."""
    skript = tmp_path / "ziel.py"
    skript.write_text(
        'daten = [{"nr": i, "a": "ä" * 250, "b": "\\"" * 250} for i in range(200)]\n'
        "marker = 1\n",
        encoding="utf-8",
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [2]})
        ereignis = client.angehalten_abwarten()
        frame_id = client.aufrufstapel_lesen(ereignis["threadId"])[0]["id"]
        antwort = client.auswerten(tabellen_ausdruck("daten"), frame_id)
        tabelle = tabelle_aus_antwort(antwort["result"])
    finally:
        client.beenden()

    assert tabelle.gesamt == 200
    assert 0 < len(tabelle.zeilen) < 200
    assert [zeile[0] for zeile in tabelle.zeilen] == [
        str(i) for i in range(len(tabelle.zeilen))
    ]
