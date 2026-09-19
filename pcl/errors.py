"""Ausnahmen der pcl-Laufzeit.

Namen und Bedeutung entsprechen docs/fehlerkatalog.yaml (Einträge
`pcl_property_error`, `attribute_error`, `natter_datenbank_error`).

**Der Text jeder dieser Ausnahmen erscheint unverändert im „Was“ der
Fehlermeldung** (`ide/debugger/fehlerkatalog.py`). Er ist deutsch und
soll es bleiben: der Katalog übersetzt nur die englischen
Standardmeldungen von Python und erkennt eine `pcl`-Meldung an ihrer
Herkunft. Die Leitfrage („Prüfe“) kommt dagegen aus dem Katalog – hier
gehört keine hin, weil eine Ausnahme nichts darüber weiß, in welchem
Zusammenhang sie ausgelöst wurde.
"""


class NatterPropertyError(TypeError):
    """Einer Eigenschaft oder einem Ereignis wurde ein Wert falschen Typs
    zugewiesen (z. B. ``self.b_ok.caption = 5``)."""


class NatterUnbekannteEigenschaftError(AttributeError):
    """Eine Komponente hat keine Eigenschaft mit diesem Namen (Tippfehler,
    z. B. ``self.b_ok.captoin = "OK"``)."""


class NatterDatenbankError(RuntimeError):
    """Eine Datenbankverbindung oder SQL-Anweisung ist fehlgeschlagen
    (Abschnitt 8.5: „Datenbankverbindung, SQL-Fehler“). Ersetzt die rohe
    Treiberausnahme (z. B. ``sqlite3.OperationalError``), damit Schüler
    nicht die Treiberbibliothek kennen müssen.

    Basis ist `RuntimeError`, und für den gibt es bewusst keinen
    Katalogeintrag. Diese Klasse steht deshalb seit M11 selbst im
    Katalog – sonst lief die MRO-Suche ins Leere und das
    Schülerprogramm zeigte einen rohen Traceback statt einer Meldung.
    Der eingebettete Treibertext bleibt englisch („no such table: …“);
    der Katalog deutscht die gängigen Fälle beim Anzeigen ein."""


class NatterDatenError(ValueError):
    """Daten für Diagramm oder Regression lassen sich nicht wie angegeben
    einlesen oder auswerten (M10, Punkt 3 und 5): unbekannte Spalte,
    Spalte ohne Zahlen, zu wenige Punkte, senkrechte Punktwolke.

    Basis `ValueError`, damit die MRO-Suche in
    `ide/debugger/fehlerkatalog.py` einen Eintrag findet und die deutsche
    Meldung unverändert als „Was“ ausgibt, statt einen rohen Traceback zu
    zeigen. Ein eigener Katalogeintrag wäre genauer; bis dahin liefert
    der `ValueError`-Eintrag die Leitfrage."""


class NatterDatenDateiError(FileNotFoundError, NatterDatenError):
    """Die Datei einer Datenquelle gibt es nicht (``Chart.load_csv``).

    Erbt bewusst von beiden Seiten: `FileNotFoundError` steht in der MRO
    vorn, damit der Fehlerkatalog „Datei nicht gefunden“ meldet und nach
    dem Pfad fragt; `NatterDatenError` sorgt dafür, dass ein
    ``except NatterDatenError`` alle Datenfehler auf einmal abfängt."""
