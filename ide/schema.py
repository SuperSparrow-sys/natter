"""Lesen von `.pfm`, `.pdiag` und `.natter` und Prüfung gegen ihr
JSON-Schema.

Eine eigene Stelle dafür, damit `jsonschema` erst geladen wird, wenn
eine Datei tatsächlich geprüft werden soll. Am Kopf der fünf Module,
die es benutzten, kostete es beim Start der IDE rund 80 Millisekunden -
und zwar auch dann, wenn jemand die IDE nur öffnet und wieder schließt,
ohne eine einzige Datei anzufassen.

Wer die Ausnahme abfangen will, nimmt `schema_fehler()`. Eine Klasse,
die `jsonschema.ValidationError` erst beim Zugriff nachlädt, wäre
hübscher gewesen, funktioniert aber nicht: Python entscheidet bei
`except` auf C-Ebene mit einem direkten Typvergleich und fragt weder
`__instancecheck__` noch `__subclasscheck__`. Eine solche Klasse hätte
in keinem einzigen `except` gegriffen, ohne dass irgendetwas
fehlgeschlagen wäre - der Fehler wäre erst beim Schüler aufgefallen,
als Absturz statt als Meldung.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

#: Ein Prüfer je Schema, über `id()` des Schema-Objekts. Das Schema
#: liegt mit im Eintrag, damit die Kennung nicht an ein neues Objekt
#: weitergegeben werden kann, solange der Eintrag besteht.
_PRUEFER: dict[int, tuple[dict[str, Any], Any]] = {}


def _pruefer(schema: dict[str, Any]) -> Any:
    """Der Prüfer zu `schema`, beim ersten Aufruf gebaut.

    `jsonschema.validate` prüft bei jedem Aufruf zuerst das Schema
    selbst gegen das Metaschema und baut einen neuen Prüfer. Mit 200
    Komponenten kostete das im Designer rund 80 ms je Pfeiltaste
    (Punkt 312), obwohl sich das Schema zur Laufzeit nie ändert. Die
    Schemas liegen als Konstanten in den Modulen, die sie benutzen;
    dasselbe Objekt kommt also immer wieder.
    """
    eintrag = _PRUEFER.get(id(schema))
    if eintrag is not None and eintrag[0] is schema:
        return eintrag[1]
    import jsonschema

    klasse = jsonschema.validators.validator_for(schema)
    klasse.check_schema(schema)
    pruefer = klasse(schema)
    _PRUEFER[id(schema)] = (schema, pruefer)
    return pruefer


def pruefen(daten: Any, schema: dict[str, Any]) -> None:
    """Prüft `daten` gegen `schema`.

    Löst `jsonschema.ValidationError` aus, wenn die Datei nicht dazu
    passt - abzufangen über `schema_fehler()`. Welcher Fehler gemeldet
    wird, entscheidet wie in `jsonschema.validate` `best_match`.
    """
    import jsonschema

    fehler = jsonschema.exceptions.best_match(
        _pruefer(schema).iter_errors(daten)
    )
    if fehler is not None:
        raise fehler


def schema_fehler() -> type[Exception]:
    """Die Ausnahme, die `pruefen()` bei einer unpassenden Datei wirft.

    Gedacht für ein `except`::

        except (json.JSONDecodeError, schema_fehler(), KeyError) as fehler:

    Der Aufruf lädt `jsonschema` nach. Das ist an dieser Stelle
    unbedenklich: wer eine Datei öffnet, hat es ohnehin schon geladen.
    """
    import jsonschema

    return jsonschema.ValidationError


def json_datei_lesen(pfad: Path) -> Any:
    """Liest eine `.natter`, `.pfm` oder `.pdiag`.

    Gelesen wird mit `utf-8-sig`: der Editor von Windows 10 bis
    Version 1809 speichert UTF-8 immer mit den drei Bytes BOM am
    Anfang, andere Editoren auf Wunsch. Mit `utf-8` scheiterte
    `json.loads` daran, und eine unveränderte Datei galt als
    beschädigt (Punkt 280). Geschrieben wird weiter ohne BOM.

    Wirft `json.JSONDecodeError`, `UnicodeDecodeError` oder `OSError`;
    `fehler_beschreiben()` macht daraus eine deutsche Meldung.
    """
    text = Path(pfad).read_text(encoding="utf-8-sig")
    # Zwei Arten kaputter Dateien kommen nicht als `JSONDecodeError`:
    # sehr tief verschachtelte Klammern (`RecursionError`) und eine Zahl
    # mit mehr als 4300 Ziffern (`ValueError`). Beide flogen bis 0.4.3
    # aus dem Öffnen heraus und beendeten beim Start über die
    # Dateiverknüpfung Natter (Punkt 548).
    try:
        return json.loads(text)
    except RecursionError as fehler:
        raise JsonUebergross("zu tief verschachtelt", text) from fehler
    except json.JSONDecodeError:
        raise
    except ValueError as fehler:
        raise JsonUebergross("eine Zahl mit zu vielen Ziffern", text) from fehler


class JsonUebergross(json.JSONDecodeError):
    """Eine Datei, die sich als JSON nicht lesen lässt, weil sie viel
    größer gebaut ist, als Natter je schreibt. Erbt von
    `json.JSONDecodeError`, damit jede Stelle, die eine beschädigte
    Datei meldet, auch diese meldet."""

    def __init__(self, grund: str, text: str) -> None:
        super().__init__(grund, text, 0)
        self.grund = grund


def fehler_beschreiben(fehler: BaseException) -> str:
    """Ein Satz auf Deutsch dazu, warum sich eine Datei nicht lesen
    ließ.

    `json` und `jsonschema` melden englisch („Expecting ',' delimiter:
    line 3 column 5“). Dieser Text stand vorher unverändert in der
    Meldung.
    """
    if isinstance(fehler, JsonUebergross):
        return (
            f"Der Inhalt ist {fehler.grund}; so sieht keine Datei aus, die "
            "Natter geschrieben hat."
        )
    if isinstance(fehler, json.JSONDecodeError):
        return (
            f"Ab Zeile {fehler.lineno}, Spalte {fehler.colno} ist der "
            "Inhalt unvollständig oder verändert."
        )
    if isinstance(fehler, UnicodeDecodeError):
        return "Die Datei ist nicht als UTF-8 gespeichert."
    if isinstance(fehler, KeyError):
        return f"Die Angabe „{fehler.args[0] if fehler.args else ''}“ fehlt."
    if isinstance(fehler, schema_fehler()):
        stelle = "/".join(str(teil) for teil in fehler.absolute_path)
        if fehler.validator == "required":
            if stelle:
                return f"Im Eintrag „{stelle}“ fehlt eine Pflichtangabe."
            return "Es fehlt eine Pflichtangabe."
        if stelle:
            return f"Der Eintrag „{stelle}“ passt nicht zum Dateiformat."
        return "Der Aufbau passt nicht zum Dateiformat."
    # Natters eigene Ausnahmen (`PfmBeschaedigt`,
    # `ProjektdateiUngueltig`) tragen schon einen deutschen Text.
    text = str(fehler)
    if text and text[-1] not in ".!?":
        text += "."
    return text
