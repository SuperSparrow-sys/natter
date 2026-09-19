"""Eigenschaften-System: eine Quelle für Objektinspektor und Code.

Siehe README.md, Abschnitt 5.0. Reine Python-Logik ohne Qt; die
Anbindung an echte Widgets kommt mit `pcl.control` (M1, Schritt 2).
"""

from __future__ import annotations

from datetime import date, time
from typing import Any, NamedTuple

from pcl.errors import NatterPropertyError, NatterUnbekannteEigenschaftError

# Deutsche Typbezeichnung samt Artikel für Fehlermeldungen, siehe
# docs/fehlerkatalog.yaml, Eintrag "pcl_property_error". Wird um weitere
# Typen (Color, Font, Align, ...) ergänzt, sobald diese eingeführt werden.
_TYPNAMEN: dict[type, tuple[str, str]] = {
    str: ("Text", "ein"),
    int: ("Zahl", "eine"),
    float: ("Kommazahl", "eine"),
    bool: ("Wahrheitswert", "ein"),
    date: ("Datum", "ein"),
    time: ("Uhrzeit", "eine"),
}


def typ_beschreibung(typ: type) -> str:
    name, artikel = _TYPNAMEN.get(typ, (typ.__name__, "ein"))
    return f"{artikel} {name} ({typ.__name__})"


#: Wie Datum und Uhrzeit **in der Oberfläche** stehen: deutsch.
#: `DateEdit`, `Calendar` und der Objektinspektor zeigen sie so an, und
#: so tippt man sie auch ein (M15, Abschnitt 4).
DATUM_FORMAT = "%d.%m.%Y"
ZEIT_FORMAT = "%H:%M"

#: Wie sie **in der `.pfm`** stehen: ISO, also `2026-09-20` und `14:30`.
#: Eine Datei, die Maschinen lesen, sortiert sich damit richtig und ist
#: unabhängig davon, in welchem Land sie geöffnet wird. Die deutsche
#: Schreibweise gehört auf den Bildschirm, nicht in die Datei.
_DATUM_ISO = "%Y-%m-%d"
_ZEIT_ISO = "%H:%M"


def text_aus_wert(wert: Any) -> str:
    """Der Text, der im Objektinspektor in der Zelle steht."""
    if isinstance(wert, date):
        return wert.strftime(DATUM_FORMAT)
    if isinstance(wert, time):
        return wert.strftime(ZEIT_FORMAT)
    return str(wert)


def wert_aus_text(typ: type, text: str) -> Any:
    """Das Gegenstück: was jemand eingetippt hat, als Wert.

    Löst wie `int("abc")` einen `ValueError` aus, wenn der Text nicht
    passt - der Objektinspektor fängt ihn und lässt die Zelle stehen."""
    from datetime import datetime

    if typ is date:
        return datetime.strptime(text.strip(), DATUM_FORMAT).date()
    if typ is time:
        return datetime.strptime(text.strip(), ZEIT_FORMAT).time()
    return typ(text)


def pfm_wert(wert: Any) -> Any:
    """Der Wert, wie er in der `.pfm` steht - JSON kennt kein Datum."""
    if isinstance(wert, date):
        return wert.strftime(_DATUM_ISO)
    if isinstance(wert, time):
        return wert.strftime(_ZEIT_ISO)
    return wert


def wert_aus_pfm(typ: type, roh: Any) -> Any:
    """Zurück aus der `.pfm`. Alles außer Datum und Uhrzeit steht dort
    schon als das, was es ist."""
    from datetime import datetime

    if typ is date and isinstance(roh, str):
        return datetime.strptime(roh, _DATUM_ISO).date()
    if typ is time and isinstance(roh, str):
        return datetime.strptime(roh, _ZEIT_ISO).time()
    return roh


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


#: Die Maus-Ereignisse, die `pcl.control.Control` jeder sichtbaren
#: Komponente mitgibt (Abschnitt 5.4). Hier und nicht dort, weil
#: `ereignisse()` sie kennen muss und `control` von diesem Modul
#: importiert - nicht umgekehrt.
MAUS_EREIGNISSE: tuple[str, ...] = (
    "on_click",
    "on_double_click",
    "on_mouse_down",
    "on_mouse_move",
    "on_mouse_up",
)


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
    # `property` gehört dazu, weil Sammlungen wie `ListBox.items` als
    # echte Python-`property` mit Setter deklariert sind (siehe
    # SAMMLUNGS_EIGENSCHAFTEN) - ein deklariertes Attribut ist nie ein
    # Tippfehler, die Sperre unten soll nur unbekannte Namen abfangen.
    return isinstance(wert, (Prop, Event, property))


class VerschachtelteEigenschaft(NamedTuple):
    attribut: str
    unter_attribut: str
    typ: type
    standardwert: Any
    #: Wie `Prop.doc`: der Hilfetext, den der Objektinspektor beim
    #: Überfahren der Zeile zeigt. Eine verschachtelte Eigenschaft ist
    #: kein `Prop` und hatte deshalb als Einzige keinen (M11,
    #: Abschnitt 4).
    doc: str = ""


# Standardfüllung einer frisch gezogenen `Shape` (hier statt in
# `pcl.components.additional`, damit Komponente, `.pfm`-Schreiber und
# Objektinspektor denselben Wert aus einer Quelle lesen - ein früher
# verstreutes Duplikat führte real zu einem Testfehler).
STANDARD_BRUSH_FARBE = "#c0c0c0"

# Eigenschaften, die nur als aufklappbare Untereigenschaft existieren
# (z. B. ``Shape.brush.color`` oder ``Label.font.size``, Abschnitt 5.0),
# aber unter einem flachen Namen in der `.pfm`, im generierten Code und
# im Objektinspektor behandelt werden - eine einzige Quelle für alle drei
# Stellen (`ide/designer/pfm_schreiben.py`, `ide/codegen/design.py`,
# `ide/inspector/eigenschaften_tabelle.py`).
VERSCHACHTELTE_EIGENSCHAFTEN: dict[str, VerschachtelteEigenschaft] = {
    "brush_color": VerschachtelteEigenschaft(
        "brush", "color", str, STANDARD_BRUSH_FARBE, doc="Füllfarbe als #RRGGBB"
    ),
    "font_name": VerschachtelteEigenschaft(
        "font", "name", str, "", doc="Name der Schriftart, leer = Schrift des Formulars"
    ),
    "font_size": VerschachtelteEigenschaft(
        "font", "size", int, 0, doc="Schriftgröße in Punkt, 0 = Größe des Formulars"
    ),
    "font_bold": VerschachtelteEigenschaft("font", "bold", bool, False, doc="Fettschrift"),
    "font_italic": VerschachtelteEigenschaft(
        "font", "italic", bool, False, doc="Kursivschrift"
    ),
}

# Hilfetexte zu den Sammlungen, für den Objektinspektor - das Gegenstück
# zu `Prop.doc` und `VerschachtelteEigenschaft.doc`.
SAMMLUNGS_DOKU: dict[str, str] = {
    "items": "Die Einträge der Liste, einer je Zeile (Doppelklick zum Bearbeiten)",
    "lines": "Der Inhalt des Textfelds, einer je Zeile (Doppelklick zum Bearbeiten)",
}

# Eigenschaften, die statt eines Einzelwerts eine `pcl.strings.Strings`-
# Sammlung tragen (`Memo.lines`, `ListBox.items`, `ComboBox.items`).
# In der `.pfm` stehen sie als Liste von Zeichenketten; im generierten
# Code als Zuweisung einer Liste, die der Setter in die vorhandene
# `Strings`-Sammlung überträgt.
SAMMLUNGS_EIGENSCHAFTEN: tuple[str, ...] = ("items", "lines")

# Eigenschaften, deren Wert ein **Baum strukturierter Datensätze** ist
# statt eines Einzelwerts oder einer Liste von Zeilen: die Einträge
# eines Menüs (`MainMenu.entries`, `PopupMenu.entries`).
#
# Warum eine eigene Kategorie und nicht einfach eine Sammlung: ein
# Menüeintrag ist kein Text, sondern hat Bezeichner, Beschriftung,
# Tastenkürzel und Untereinträge. Derselbe Grundsatz wie bei den
# UML-Attributen im Diagramm-Editor – was Felder hat, wird nicht als
# Zeichenkette gespeichert. In der `.pfm` steht der Baum als
# verschachtelte Liste von Objekten, im erzeugten Code als Zuweisung
# desselben Literals.
BAUM_EIGENSCHAFTEN: tuple[str, ...] = ("entries",)

# Hilfetexte zu den Bäumen, für den Objektinspektor.
BAUM_DOKU: dict[str, str] = {
    "entries": "Die Einträge des Menüs (Doppelklick öffnet den Menü-Editor)",
}


def wert_lesen(komponente: Any, name: str) -> Any:
    """Liest eine Eigenschaft unter ihrem flachen Namen – egal ob echter
    `Prop` (`caption`), verschachtelte Untereigenschaft (`font_size`) oder
    Sammlung (`items`).

    Eine Quelle für Objektinspektor, Undo-Kommandos und `.pfm`-Schreiber:
    diese drei hatten die Fallunterscheidung vorher jeweils selbst, was
    Sammlungen und Schrift-Untereigenschaften an einzelnen Stellen
    stillschweigend übersprungen hat."""
    verschachtelt = VERSCHACHTELTE_EIGENSCHAFTEN.get(name)
    if verschachtelt is not None:
        return getattr(getattr(komponente, verschachtelt.attribut), verschachtelt.unter_attribut)
    if name in SAMMLUNGS_EIGENSCHAFTEN:
        return list(getattr(komponente, name))
    return getattr(komponente, name)


def wert_setzen(komponente: Any, name: str, wert: Any) -> None:
    """Gegenstück zu `wert_lesen`."""
    verschachtelt = VERSCHACHTELTE_EIGENSCHAFTEN.get(name)
    if verschachtelt is not None:
        setattr(
            getattr(komponente, verschachtelt.attribut), verschachtelt.unter_attribut, wert
        )
        return
    setattr(komponente, name, wert)


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
    Objektinspektor.

    **Ohne die Maus-Ereignisse, wenn die Komponente im laufenden
    Programm gar nicht da ist** (`nur_im_designer`: Zeitgeber,
    Hauptmenü, Klappmenü). Sie erben sie von `Control` wie jede andere,
    aber eine Maus kann sie nie treffen - im Objektinspektor stünden
    fünf Zeilen, von denen keine je auslöst.
    """
    ergebnis: dict[str, Event] = {}
    for klasse in reversed(cls.__mro__):
        for name, wert in vars(klasse).items():
            if isinstance(wert, Event):
                ergebnis[name] = wert
    if getattr(cls, "nur_im_designer", False):
        for name in MAUS_EREIGNISSE:
            ergebnis.pop(name, None)
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
