"""IDE-Betrachter (Abschnitt 11): CSV-Tabellenansicht, Bildvorschau,
HTML-Vorschau. Öffnen die jeweilige Datei nur an, ändern sie nie.
"""

from ide.viewers.bild_vorschau import BildVorschau
from ide.viewers.csv_ansicht import CsvAnsicht, csv_erkennen
from ide.viewers.html_vorschau import HtmlVorschau

__all__ = ["BildVorschau", "CsvAnsicht", "HtmlVorschau", "csv_erkennen"]
