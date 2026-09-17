"""Tests für die reine Logik hinter „Quelltext → Kommentar umschalten“
(Strg+#, Abschnitt 7.2). Siehe ide/shell/hauptfenster.py,
`_kommentar_umschalten_zeilen`.
"""

from ide.shell.hauptfenster import _kommentar_umschalten_zeilen


def test_unkommentierte_zeilen_werden_kommentiert() -> None:
    ergebnis = _kommentar_umschalten_zeilen(["x = 1", "y = 2"])
    assert ergebnis == ["# x = 1", "# y = 2"]


def test_kommentierte_zeilen_werden_unkommentiert() -> None:
    ergebnis = _kommentar_umschalten_zeilen(["# x = 1", "# y = 2"])
    assert ergebnis == ["x = 1", "y = 2"]


def test_kommentar_ohne_leerzeichen_wird_ebenfalls_entfernt() -> None:
    ergebnis = _kommentar_umschalten_zeilen(["#x = 1"])
    assert ergebnis == ["x = 1"]


def test_einzug_bleibt_erhalten() -> None:
    ergebnis = _kommentar_umschalten_zeilen(["    x = 1"])
    assert ergebnis == ["    # x = 1"]

    zurueck = _kommentar_umschalten_zeilen(ergebnis)
    assert zurueck == ["    x = 1"]


def test_leere_zeilen_bleiben_unveraendert_und_zaehlen_nicht_mit() -> None:
    ergebnis = _kommentar_umschalten_zeilen(["# x = 1", "", "# y = 2"])
    assert ergebnis == ["x = 1", "", "y = 2"]


def test_gemischte_auswahl_wird_komplett_kommentiert() -> None:
    # Nicht ALLE Zeilen sind bereits kommentiert -> alle bekommen "# ",
    # wie in VS Code üblich (kein teilweises Entfernen).
    ergebnis = _kommentar_umschalten_zeilen(["x = 1", "# y = 2"])
    assert ergebnis == ["# x = 1", "# # y = 2"]


def test_leere_liste_bleibt_leer() -> None:
    assert _kommentar_umschalten_zeilen([]) == []


def test_nur_leere_zeilen_bleiben_unveraendert() -> None:
    assert _kommentar_umschalten_zeilen(["", "   "]) == ["", "   "]
