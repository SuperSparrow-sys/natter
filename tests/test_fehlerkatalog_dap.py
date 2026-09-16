"""Tests für ide/debugger/fehlerkatalog.py: fehlermeldung_aus_dap_
erzeugen() – Fehlerkatalog-Meldung aus einer DAP-`exceptionInfo`-Antwort
statt einem lokalen Exception-Objekt (Abschnitt 8.1). Formen der Antwort
gegen echtes `debugpy` ermittelt. Siehe docs/arbeitspakete/M4.md,
Schritt 6.
"""

from __future__ import annotations

from ide.debugger import fehlermeldung_aus_dap_erzeugen

_DIESE_DATEI = __file__


def _exception_info(
    exception_id: str, message: str, stack_trace: str, description: str | None = None
) -> dict:
    return {
        "exceptionId": exception_id,
        "breakMode": "unhandled",
        "description": description or message,
        "details": {
            "message": message,
            "typeName": exception_id,
            "stackTrace": stack_trace,
        },
    }


def test_bekannte_eingebaute_ausnahme_wird_erkannt() -> None:
    info = _exception_info(
        "ZeroDivisionError",
        "division by zero",
        f'  File "{_DIESE_DATEI}", line 2, in f\n'
        "    return 1 / 0\n"
        "           ~~^~~\n"
        f'  File "{_DIESE_DATEI}", line 4, in <module>\n'
        "    f()\n"
        "    ~^^\n"
        "ZeroDivisionError: division by zero\n",
    )

    meldung = fehlermeldung_aus_dap_erzeugen(info)

    assert meldung is not None
    assert "ZeroDivisionError" in meldung.ueberschrift
    assert meldung.was == "Es wurde durch 0 geteilt."
    assert "Teiler" in meldung.pruefe


def test_wo_zeigt_den_tiefsten_eigenen_frame_mit_quelltext_und_markierung() -> None:
    info = _exception_info(
        "ZeroDivisionError",
        "division by zero",
        f'  File "{_DIESE_DATEI}", line 2, in f\n'
        "    return 1 / 0\n"
        "           ~~^~~\n"
        f'  File "{_DIESE_DATEI}", line 4, in <module>\n'
        "    f()\n"
        "    ~^^\n"
        "ZeroDivisionError: division by zero\n",
    )

    meldung = fehlermeldung_aus_dap_erzeugen(info)

    assert meldung is not None
    assert "line 2" not in meldung.wo  # deutsche Formatierung, nicht Pythons "line"
    assert "Zeile 2" in meldung.wo
    assert "in f" in meldung.wo
    assert meldung.quelltext == "return 1 / 0"
    assert meldung.markierung is not None


def test_frame_ohne_karett_zeile_wird_trotzdem_korrekt_geparst() -> None:
    # ältere Python-Versionen bzw. manche Fälle liefern keine ^-Zeile
    info = _exception_info(
        "ValueError",
        "invalid literal for int() with base 10: 'abc'",
        f'  File "{_DIESE_DATEI}", line 10, in g\n'
        "    int('abc')\n"
        "ValueError: invalid literal for int() with base 10: 'abc'\n",
    )

    meldung = fehlermeldung_aus_dap_erzeugen(info)

    assert meldung is not None
    assert "Zeile 10" in meldung.wo
    assert meldung.quelltext == "int('abc')"
    assert meldung.markierung is None


def test_unregistrierte_unterklasse_findet_ihre_basisklasse_ueber_die_mro() -> None:
    # json.decoder.JSONDecodeError ist eine ValueError-Unterklasse, aber
    # nicht selbst im Katalog eingetragen (siehe test_fehlerkatalog.py).
    info = _exception_info(
        "json.decoder.JSONDecodeError",
        "Expecting value: line 1 column 1 (char 0)",
        f'  File "{_DIESE_DATEI}", line 5, in h\n    json.loads("x")\n',
    )

    meldung = fehlermeldung_aus_dap_erzeugen(info)

    assert meldung is not None
    assert "JSONDecodeError" in meldung.ueberschrift


def test_unbekannte_exceptionid_liefert_none() -> None:
    info = _exception_info("EinTypDenEsNichtGibt", "irgendwas", "")
    assert fehlermeldung_aus_dap_erzeugen(info) is None


def test_katalogloser_typ_liefert_none() -> None:
    info = _exception_info("RuntimeError", "kein Katalogeintrag dafür", "")
    assert fehlermeldung_aus_dap_erzeugen(info) is None


def test_dateiname_ohne_filename_attribut_faellt_auf_die_nachricht_zurueck() -> None:
    # FileNotFoundError braucht normalerweise exc.filename - das gibt es
    # beim DAP-Nachbau nicht, str(exc) enthält den Pfad aber ohnehin schon.
    info = _exception_info(
        "FileNotFoundError",
        "[Errno 2] No such file or directory: 'nicht_da.txt'",
        f'  File "{_DIESE_DATEI}", line 7, in k\n    open("nicht_da.txt")\n',
    )

    meldung = fehlermeldung_aus_dap_erzeugen(info)

    assert meldung is not None
    assert "nicht_da.txt" in meldung.was
