"""Eigenschaften-System: eine Quelle für Objektinspektor und Code.

Siehe konzept-natter.md, Abschnitt 5.0. Reine Python-Logik ohne Qt; die
Anbindung an echte Widgets kommt mit `pcl.control` (M1, Schritt 2).
"""

from __future__ import annotations

from typing import Any

from pcl.errors import NatterPropertyError, NatterUnbekannteEigenschaftError

# Deutsche Typbezeichnung samt Artikel für Fehlermeldungen, siehe
# docs/fehlerkatalog.yaml, Eintrag "pcl_property_error". Wird um weitere
# Typen (Color, Font, Align, ...) ergänzt, sobald diese eingeführt werden.
_TYPNAMEN: dict[type, tuple[str, str]] = {
    str: ("Text", "ein"),
    int: ("Zahl", "eine"),
    float: ("Kommazahl", "eine"),
    bool: ("Wahrheitswert", "ein"),
}


def typ_beschreibung(typ: type) -> str:
    name, artikel = _TYPNAMEN.get(typ, (typ.__name__, "ein"))
    return f"{artikel} {name} ({typ.__name__})"


class Prop:
    """Eine Eigenschaft einer Komponente.

    Definiert einmal in der Komponentenklasse, daraus ergeben sich
    automatisch das Python-Attribut, die Zeile im Objektinspektor, der
    Standardwert und der Hilfetext (Abschnitt 5.0).
    """

    def __init__(
        self,
        typ: type,
        standardwert: Any = None,
        *,
        kategorie: str = "Allgemein",
        doc: str = "",
    ) -> None:
        self.typ = typ
        self.standardwert = standardwert
        self.kategorie = kategorie
        self.doc = doc
        self.name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def _speicher_name(self) -> str:
        return f"_prop_{self.name}"

    def __get__(self, instance: object | None, owner: type | None = None):
        if instance is None:
            return self
        return instance.__dict__.get(self._speicher_name(), self.standardwert)

    def __set__(self, instance: object, wert: Any) -> None:
        if not self._passt_typ(wert):
            raise NatterPropertyError(
                f"{type(instance).__name__}.{self.name} erwartet "
                f"{typ_beschreibung(self.typ)}, erhalten wurde {typ_beschreibung(type(wert))}."
            )
        instance.__dict__[self._speicher_name()] = wert
        # Live-Wirkung (Abschnitt 5.0): Unterklassen mit Qt-Anbindung
        # (pcl.control.Control, pcl.form.Form) überschreiben diesen Hook,
        # um das zugehörige QWidget sofort zu aktualisieren.
        verarbeiten = getattr(instance, "_bei_prop_aenderung", None)
        if verarbeiten is not None:
            verarbeiten(self.name, wert)

    def _passt_typ(self, wert: Any) -> bool:
        if self.typ is bool:
            return isinstance(wert, bool)
        if isinstance(wert, bool):
            # bool ist in Python eine Unterklasse von int, soll aber nie
            # stillschweigend für int-/float-/str-Eigenschaften durchgehen.
            return False
        if isinstance(wert, self.typ):
            return True
        return self.typ is float and isinstance(wert, int)


class Event:
    """Ein Ereignis einer Komponente, z. B. ``on_click`` (Abschnitt 5.0,
    5.4). Der zugewiesene Wert ist der aufrufbare Ereignis-Handler."""

    def __init__(self, *, doc: str = "") -> None:
        self.doc = doc
        self.name: str | None = None

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    def _speicher_name(self) -> str:
        return f"_ereignis_{self.name}"

    def __get__(self, instance: object | None, owner: type | None = None):
        if instance is None:
            return self
        return instance.__dict__.get(self._speicher_name())

    def __set__(self, instance: object, wert: Any) -> None:
        if wert is not None and not callable(wert):
            raise NatterPropertyError(
                f"{type(instance).__name__}.{self.name} erwartet einen aufrufbaren "
                f"Ereignis-Handler, erhalten wurde {typ_beschreibung(type(wert))}."
            )
        instance.__dict__[self._speicher_name()] = wert


def _ist_deklariert(cls: type, name: str) -> bool:
    wert = getattr(cls, name, None)
    return isinstance(wert, (Prop, Event))


# Eigenschaften, die nur als aufklappbare Untereigenschaft existieren
# (z. B. ``Shape.brush.color``, Abschnitt 5.0), aber unter einem flachen
# Namen in der `.pfm`, im generierten Code und im Objektinspektor
# behandelt werden - eine einzige Quelle für alle drei Stellen
# (`ide/designer/pfm_schreiben.py`, `ide/codegen/design.py`,
# `ide/inspector/eigenschaften_tabelle.py`), nachdem eine frühere,
# verstreute Kopie real zu einem Testfehler geführt hatte.
VERSCHACHTELTE_EIGENSCHAFTEN: dict[str, tuple[str, str]] = {
    "brush_color": ("brush", "color"),
}


def eigenschaften(cls: type) -> dict[str, Prop]:
    """Alle `Prop`-Eigenschaften einer Klasse inkl. Basisklassen, für den
    Objektinspektor."""
    ergebnis: dict[str, Prop] = {}
    for klasse in reversed(cls.__mro__):
        for name, wert in vars(klasse).items():
            if isinstance(wert, Prop):
                ergebnis[name] = wert
    return ergebnis


def ereignisse(cls: type) -> dict[str, Event]:
    """Alle `Event`-Ereignisse einer Klasse inkl. Basisklassen, für den
    Objektinspektor."""
    ergebnis: dict[str, Event] = {}
    for klasse in reversed(cls.__mro__):
        for name, wert in vars(klasse).items():
            if isinstance(wert, Event):
                ergebnis[name] = wert
    return ergebnis


class Komponente:
    """Basisklasse für Objekte mit Prop/Event-System.

    Unbekannte Eigenschaften lösen beim Zuweisen sofort einen Fehler aus,
    statt still ein neues Attribut anzulegen (Tippfehlerschutz, Abschnitt
    5.0). `Form` hebt diese Sperre über `neue_attribute_erlaubt = True`
    auf, weil eigene Attribute auf dem Formular (``self.ampel = Ampel()``)
    erlaubt bleiben; die Sperre gilt nur für Komponenten.
    """

    neue_attribute_erlaubt = False

    def __setattr__(self, name: str, wert: Any) -> None:
        if name.startswith("_") or _ist_deklariert(type(self), name):
            object.__setattr__(self, name, wert)
            return
        if type(self).neue_attribute_erlaubt:
            object.__setattr__(self, name, wert)
            return
        raise NatterUnbekannteEigenschaftError(
            f"{type(self).__name__} besitzt keine Eigenschaft {name!r}."
        )
