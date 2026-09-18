"""Ausnahmen der pcl-Laufzeit.

Namen und Bedeutung entsprechen docs/fehlerkatalog.yaml (Einträge
`pcl_property_error`, `attribute_error`).
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
    nicht die Treiberbibliothek kennen müssen."""


class NatterDatenError(ValueError):
    """Daten für Diagramm oder Regression lassen sich nicht wie angegeben
    einlesen oder auswerten (M10, Punkt 3 und 5): unbekannte Spalte,
    Spalte ohne Zahlen, zu wenige Punkte, senkrechte Punktwolke.

    Basis `ValueError`, damit die MRO-Suche in
    `ide/debugger/fehlerkatalog.py` einen Eintrag findet und die deutsche
    Meldung unverändert als „Was“ ausgibt, statt einen rohen Traceback zu
    zeigen. Ein eigener Katalogeintrag wäre genauer, liegt aber in
    `ide/`/`docs/` und damit außerhalb dieses Arbeitspakets."""


class NatterDatenDateiError(FileNotFoundError, NatterDatenError):
    """Die Datei einer Datenquelle gibt es nicht (``Chart.load_csv``).

    Erbt bewusst von beiden Seiten: `FileNotFoundError` steht in der MRO
    vorn, damit der Fehlerkatalog „Datei nicht gefunden“ meldet und nach
    dem Pfad fragt; `NatterDatenError` sorgt dafür, dass ein
    ``except NatterDatenError`` alle Datenfehler auf einmal abfängt."""
