"""Tests für ide/debugger/komponenten_variablen.py: Filtert die
Variablenliste eines pcl-Objekts auf Prop-/Event-Namen (Abschnitt 8.1).
Headless.
"""

from __future__ import annotations

from ide.debugger.komponenten_variablen import komponenten_variablen_filtern


def test_bekannte_eigenschaften_bleiben_erhalten() -> None:
    variablen = [
        {"name": "caption", "value": "'Hallo'"},
        {"name": "on_click", "value": "None"},
        {"name": "width", "value": "75"},
    ]
    ergebnis = komponenten_variablen_filtern(variablen)
    assert {v["name"] for v in ergebnis} == {"caption", "on_click", "width"}


def test_interne_attribute_und_pseudogruppen_werden_entfernt() -> None:
    variablen = [
        {"name": "caption", "value": "'Hallo'"},
        {"name": "_qwidget", "value": "<QWidget ...>"},
        {"name": "_bei_prop_aenderung", "value": "<bound method ...>"},
        {"name": "special variables", "value": ""},
        {"name": "class variables", "value": ""},
        {"name": "neue_attribute_erlaubt", "value": "True"},
    ]
    ergebnis = komponenten_variablen_filtern(variablen)
    assert ergebnis == [{"name": "caption", "value": "'Hallo'"}]


def test_leere_liste_bleibt_leer() -> None:
    assert komponenten_variablen_filtern([]) == []
