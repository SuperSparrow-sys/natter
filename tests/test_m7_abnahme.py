"""Abnahmetest für M7 (docs/arbeitspakete/M7.md, Schritt 4): „alle
Prüfregeln erkennen ihre Testformulare“.

Jede Regel einzeln (mit sauberem Gegenbeispiel) ist bereits durch
`tests/test_design_pruefer.py` abgedeckt; „Paket über das Menü
installierbar“ (gegen echtes, aber gemocktes `pip`) durch
`tests/test_hauptfenster_pakete.py`. Hier zusätzlich, nicht doppelt:
ein einziges, absichtlich durchgehend fehlerhaftes Testformular, das
*alle* implementierten Regeln gleichzeitig auslöst - das prüft, dass
sich die Regeln bei gemeinsamem Auftreten nicht gegenseitig maskieren.
"""

from __future__ import annotations

from ide.lint.regeln import pruefen

_ALLE_REGEL_IDS = {
    "geometrie.ausserhalb_formular",
    "geometrie.ueberlappung",
    "geometrie.kante_nicht_buendig",
    "geometrie.uneinheitliche_abstaende",
    "lesbarkeit.kontrast",
    "konsistenz.button_groesse",
    "konsistenz.label_ausrichtung",
    "bedienbarkeit.klickflaeche",
    "bedienbarkeit.ohne_beschriftung",
    "bedienbarkeit.tab_reihenfolge",
    "namenskonvention.praefix",
    "namenskonvention.standardname",
    "namenskonvention.standardtext",
}

_DURCHGEHEND_FEHLERHAFTES_TESTFORMULAR = {
    "format": "pfm/1",
    "class": "Form1",
    "type": "Form",
    "properties": {"caption": "Form1", "width": 300, "height": 200, "color": "#202020"},
    "children": [
        # zu klein, nicht am Raster, Standardname/-text, kein Label -
        # löst Bedienbarkeit/Namenskonvention/Geometrie aus
        {
            "name": "button1",
            "type": "Button",
            "properties": {"left": 5, "top": 150, "width": 16, "height": 16, "caption": "Button1"},
        },
        # deutlich anders große Schwester-Button, weit außerhalb des
        # Formulars, fast (aber nicht exakt) linksbündig zu button1 -
        # löst Geometrie/Konsistenz aus, und die Tab-Reihenfolge stimmt
        # nicht mit der visuellen Lesereihenfolge überein (steht unten
        # im Formular, aber vor label1 oben deklariert)
        {
            "name": "b_gross",
            "type": "Button",
            "properties": {"left": 280, "top": 8, "width": 150, "height": 60},
        },
        {
            "name": "label1",
            "type": "Label",
            "properties": {"left": 8, "top": 8, "width": 60, "height": 20},
        },
        # überlappt mit label1 und ist nicht mit e_x auf gleicher Höhe -
        # löst Geometrie/Konsistenz aus; e_x selbst hat kein Label in
        # der Nähe und löst Bedienbarkeit aus
        {
            "name": "l_ueberlappt",
            "type": "Label",
            "properties": {"left": 16, "top": 16, "width": 40, "height": 20},
        },
        {
            "name": "e_x",
            "type": "Edit",
            "properties": {"left": 200, "top": 60, "width": 80, "height": 24},
        },
        # drei Buttons in einer Zeile mit uneinheitlichen Abständen
        {
            "name": "b_r1",
            "type": "Button",
            "properties": {"left": 8, "top": 120, "width": 24, "height": 24},
        },
        {
            "name": "b_r2",
            "type": "Button",
            "properties": {"left": 40, "top": 120, "width": 24, "height": 24},
        },
        {
            "name": "b_r3",
            "type": "Button",
            "properties": {"left": 200, "top": 120, "width": 24, "height": 24},
        },
    ],
}


def test_alle_implementierten_regeln_erkennen_das_gemeinsame_testformular() -> None:
    gefundene_regeln = {b.regel for b in pruefen(_DURCHGEHEND_FEHLERHAFTES_TESTFORMULAR)}

    fehlend = _ALLE_REGEL_IDS - gefundene_regeln
    assert not fehlend, f"Regeln ohne Fund im gemeinsamen Testformular: {fehlend}"


def test_befunde_im_gemeinsamen_testformular_sind_nie_fehler() -> None:
    befunde = pruefen(_DURCHGEHEND_FEHLERHAFTES_TESTFORMULAR)
    assert all(b.schweregrad in ("hinweis", "warnung") for b in befunde)
