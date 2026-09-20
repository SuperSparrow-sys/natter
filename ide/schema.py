"""Prüfung von `.pfm`, `.pdiag` und `.natter` gegen ihr JSON-Schema.

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

from typing import Any


def pruefen(daten: Any, schema: dict[str, Any]) -> None:
    """Prüft `daten` gegen `schema`.

    Löst `jsonschema.ValidationError` aus, wenn die Datei nicht dazu
    passt - abzufangen über `schema_fehler()`.
    """
    import jsonschema

    jsonschema.validate(daten, schema)


def schema_fehler() -> type[Exception]:
    """Die Ausnahme, die `pruefen()` bei einer unpassenden Datei wirft.

    Gedacht für ein `except`::

        except (json.JSONDecodeError, schema_fehler(), KeyError) as fehler:

    Der Aufruf lädt `jsonschema` nach. Das ist an dieser Stelle
    unbedenklich: wer eine Datei öffnet, hat es ohnehin schon geladen.
    """
    import jsonschema

    return jsonschema.ValidationError
