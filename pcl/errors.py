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
