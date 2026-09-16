"""Exportiert ein Testprotokoll als eigenständige HTML-Datei (Abschnitt
8.6: „Testergebnisse als HTML exportieren“)."""

from __future__ import annotations

from html import escape

from ide.testrunner.ausfuehrung import Testergebnis

_STATUS_FARBE = {
    "bestanden": "#1e8e3e",
    "fehlgeschlagen": "#c0392b",
    "fehler": "#c0392b",
}


def ergebnisse_als_html(ergebnisse: list[Testergebnis], *, titel: str = "Testprotokoll") -> str:
    """Baut ein eigenständiges HTML-Dokument (kein externes CSS/JS) aus
    `ergebnisse`, inklusive Soll/Ist bei fehlgeschlagenen Tests."""
    bestanden = sum(1 for e in ergebnisse if e.status == "bestanden")
    zeilen = "\n".join(_zeile(e) for e in ergebnisse)

    return f"""\
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{escape(titel)}</title>
<style>
  body {{ font-family: sans-serif; margin: 2em; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 10px; text-align: left; }}
  th {{ background: #f0f0f0; }}
</style>
</head>
<body>
<h1>{escape(titel)}</h1>
<p>{bestanden} von {len(ergebnisse)} Test(s) bestanden.</p>
<table>
<tr><th>Test</th><th>Status</th><th>Dauer (s)</th><th>Soll</th><th>Ist</th><th>Meldung</th></tr>
{zeilen}
</table>
</body>
</html>
"""


def _zeile(ergebnis: Testergebnis) -> str:
    farbe = _STATUS_FARBE.get(ergebnis.status, "#000000")
    soll = escape(ergebnis.soll) if ergebnis.soll is not None else ""
    ist = escape(ergebnis.ist) if ergebnis.ist is not None else ""
    nachricht = escape(ergebnis.nachricht) if ergebnis.nachricht else ""
    return (
        "<tr>"
        f"<td>{escape(ergebnis.id)}</td>"
        f'<td style="color: {farbe};">{escape(ergebnis.status)}</td>'
        f"<td>{ergebnis.dauer:.3f}</td>"
        f"<td>{soll}</td>"
        f"<td>{ist}</td>"
        f"<td>{nachricht}</td>"
        "</tr>"
    )
