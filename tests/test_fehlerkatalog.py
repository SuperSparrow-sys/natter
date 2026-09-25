"""Tests für ide/debugger/fehlerkatalog.py: Wo/Was/Prüfe-Meldungen für
unbehandelte Ausnahmen (Abschnitt 8.3–8.5). Siehe
Arbeitspaket M4, Schritt 2.
"""

from __future__ import annotations

import json

from ide.debugger import fehlermeldung_erzeugen


def _ausloesen(f):
    """Löst `f()` aus und liefert die entstandene Ausnahme."""
    try:
        f()
    except BaseException as fehler:  # noqa: BLE001 - genau das wird hier geprüft
        return fehler
    raise AssertionError("f() hat keine Ausnahme ausgelöst")


def test_zero_division() -> None:
    def f():
        summe, anzahl = 10, 0
        return summe / anzahl

    meldung = fehlermeldung_erzeugen(_ausloesen(f))

    assert "ZeroDivisionError" in meldung.ueberschrift
    assert meldung.was == "Es wurde durch 0 geteilt."
    assert "Teiler" in meldung.pruefe
    assert meldung.markierung is not None


def test_name_error_nennt_den_unbekannten_namen() -> None:
    def f():
        return nicht_definiert  # noqa: F821

    meldung = fehlermeldung_erzeugen(_ausloesen(f))

    assert "NameError" in meldung.ueberschrift
    assert "nicht_definiert" in meldung.was


def test_unbound_local_error() -> None:
    def f():
        x = x + 1  # noqa: F821
        return x

    meldung = fehlermeldung_erzeugen(_ausloesen(f))

    assert "UnboundLocalError" in meldung.ueberschrift
    assert "lokal" in meldung.was.lower() or "x" in meldung.was


def test_attribute_error_auf_gekapseltem_attribut() -> None:
    class Ding:
        def __init__(self):
            self.__geheim = 1

    def f():
        return Ding().__geheim  # noqa: SLF001

    meldung = fehlermeldung_erzeugen(_ausloesen(f))

    assert "AttributeError" in meldung.ueberschrift
    assert "Kapselung" in meldung.was or "Namensumbildung" in meldung.was


def test_attribute_error_auf_normalem_attribut() -> None:
    class Ding:
        pass

    def f():
        return Ding().bar

    meldung = fehlermeldung_erzeugen(_ausloesen(f))

    assert "bar" in meldung.was
    assert "Kapselung" not in meldung.was


def test_value_error_mit_komma_bekommt_dezimalpunkt_hinweis() -> None:
    def f():
        return float("3,5")

    meldung = fehlermeldung_erzeugen(_ausloesen(f))

    assert "ValueError" in meldung.ueberschrift
    assert "Dezimalpunkt" in meldung.pruefe


def test_value_error_ohne_komma_bekommt_generischen_hinweis() -> None:
    def f():
        return int("abc")

    meldung = fehlermeldung_erzeugen(_ausloesen(f))

    assert "Dezimalpunkt" not in meldung.pruefe


def test_index_error() -> None:
    def f():
        werte = [1, 2, 3]
        return werte[10]

    meldung = fehlermeldung_erzeugen(_ausloesen(f))
    assert "IndexError" in meldung.ueberschrift


def test_key_error_nennt_den_fehlenden_schluessel() -> None:
    def f():
        daten = {"a": 1}
        return daten["b"]

    meldung = fehlermeldung_erzeugen(_ausloesen(f))

    assert "KeyError" in meldung.ueberschrift
    assert "'b'" in meldung.was


def test_file_not_found_nennt_den_pfad() -> None:
    def f():
        return open("es_gibt_mich_nicht.txt", encoding="utf-8")

    meldung = fehlermeldung_erzeugen(_ausloesen(f))

    assert "FileNotFoundError" in meldung.ueberschrift
    assert "es_gibt_mich_nicht.txt" in meldung.was


def test_type_error() -> None:
    def f():
        return "text" + 1

    meldung = fehlermeldung_erzeugen(_ausloesen(f))
    assert "TypeError" in meldung.ueberschrift


def test_syntax_error() -> None:
    def f():
        compile("def f(:\n    pass\n", "<test>", "exec")

    meldung = fehlermeldung_erzeugen(_ausloesen(f))
    assert meldung.ueberschrift.startswith("Syntaxfehler")


def test_unbekannter_exception_typ_liefert_none() -> None:
    def f():
        raise RuntimeError("kein Katalogeintrag dafür")

    assert fehlermeldung_erzeugen(_ausloesen(f)) is None


def test_katalogsuche_folgt_der_mro_fuer_unregistrierte_unterklassen() -> None:
    # json.JSONDecodeError ist eine ValueError-Unterklasse, aber nicht
    # selbst im Katalog eingetragen - der Eintrag für ValueError muss
    # trotzdem greifen (MRO-Suche statt exaktem Typvergleich).
    def f():
        return json.loads("das ist kein JSON")

    meldung = fehlermeldung_erzeugen(_ausloesen(f))

    assert meldung is not None
    assert "ValueError" not in meldung.ueberschrift  # echter Typname, nicht die Basisklasse
    assert "JSONDecodeError" in meldung.ueberschrift


def test_wo_zeigt_den_eigenen_code_nicht_die_stdlib_internas() -> None:
    # json.loads() ruft intern tief in json/decoder.py - die Meldung soll
    # trotzdem auf DIESE Datei/Zeile zeigen, nicht auf json-Interna
    # (Abschnitt 8.1: "nur eigener Code").
    def f():
        return json.loads("kaputt")

    meldung = fehlermeldung_erzeugen(_ausloesen(f))

    assert "test_fehlerkatalog.py" in meldung.wo
    assert "json" not in meldung.wo.split(",")[0]


def test_als_text_enthaelt_alle_teile_im_richtigen_aufbau() -> None:
    def f():
        return 1 / 0

    meldung = fehlermeldung_erzeugen(_ausloesen(f))
    text = meldung.als_text()

    assert text.index("Wo:") < text.index("Was:") < text.index("Prüfe:")
    assert meldung.ueberschrift in text


def test_was_enthaelt_niemals_did_you_mean() -> None:
    def f():
        ergebnis = 1  # noqa: F841
        return ergebnis_falsch  # noqa: F821

    meldung = fehlermeldung_erzeugen(_ausloesen(f))
    assert "did you mean" not in meldung.was.lower()
