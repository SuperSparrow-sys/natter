"""IDE-Betrachter (Abschnitt 11): CSV-Tabellenansicht, Bildvorschau,
HTML-Vorschau, Hilfeansicht, Tabellenansicht für Debugger-Variablen.
Öffnen die jeweilige Datei bzw. den jeweiligen Wert nur an, ändern sie
nie.
"""

from ide.viewers.bild_vorschau import BildVorschau
from ide.viewers.csv_ansicht import CsvAnsicht, csv_erkennen
from ide.viewers.hilfe_ansicht import HilfeAnsicht
from ide.viewers.html_vorschau import HtmlVorschau
from ide.viewers.tabellen_ansicht import TabellenAnsicht

__all__ = [
    "BildVorschau",
    "CsvAnsicht",
    "HilfeAnsicht",
    "HtmlVorschau",
    "TabellenAnsicht",
    "csv_erkennen",
]
