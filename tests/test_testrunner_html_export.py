"""Tests für ide/testrunner/html_export.py: Testprotokoll als HTML
(Abschnitt 8.6). Headless.
"""

from __future__ import annotations

from ide.testrunner import Testergebnis, ergebnisse_als_html


def test_html_enthaelt_titel_und_zusammenfassung() -> None:
    ergebnisse = [
        Testergebnis(id="m.K.test_a", status="bestanden", dauer=0.01),
        Testergebnis(
            id="m.K.test_b",
            status="fehlgeschlagen",
            dauer=0.02,
            nachricht="45 != 50",
            soll="50",
            ist="45",
        ),
    ]

    html = ergebnisse_als_html(ergebnisse, titel="Meine Tests")

    assert "<title>Meine Tests</title>" in html
    assert "1 von 2 Test(s) bestanden." in html


def test_html_enthaelt_soll_ist_bei_fehlschlag() -> None:
    ergebnisse = [
        Testergebnis(
            id="m.K.test_b", status="fehlgeschlagen", dauer=0.0, soll="50", ist="45"
        )
    ]

    html = ergebnisse_als_html(ergebnisse)

    assert "<td>50</td>" in html
    assert "<td>45</td>" in html


def test_html_entkommt_sonderzeichen_in_der_nachricht() -> None:
    ergebnisse = [
        Testergebnis(
            id="m.K.test_c", status="fehler", dauer=0.0, nachricht="<script>böse</script>"
        )
    ]

    html = ergebnisse_als_html(ergebnisse)

    assert "<script>böse</script>" not in html
    assert "&lt;script&gt;" in html


def test_leere_ergebnisliste_erzeugt_gueltiges_html() -> None:
    html = ergebnisse_als_html([])
    assert "0 von 0 Test(s) bestanden." in html
    assert "<html" in html
