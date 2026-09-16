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
