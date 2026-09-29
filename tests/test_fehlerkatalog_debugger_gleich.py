"""Mit und ohne Debugger dieselbe Meldung (Punkt 418).

Ohne Debugger baut `fehlermeldung_erzeugen()` die Meldung aus dem
echten Ausnahmeobjekt. Mit Debugger kommt nur Text an, die Antwort von
debugpy auf `exceptionInfo`, und `fehlermeldung_aus_dap_erzeugen()`
muss Name, Schlüssel und Dateiname aus der Meldung zurückgewinnen. Hier
entsteht jede Ausnahme echt und geht dann beide Wege; Überschrift, Was
und Zu prüfen müssen übereinstimmen. Den Ort vergleicht der Test nicht,
der hängt am Stapel und nicht am Katalog.
"""

from __future__ import annotations

import json
import math
import operator
import random
from collections.abc import Callable
from typing import Any

import pytest

from pcl.fehlerkatalog import (
    Fehlermeldung,
    fehlermeldung_aus_dap_erzeugen,
    fehlermeldung_erzeugen,
)


class _Form1:
    pass


class _Klasse:
    pass


def _ohne_return() -> None:
    pass


def _rekursion(n: int) -> int:
    return _rekursion(n + 1)


def _unbound() -> None:
    zaehler += 1  # noqa: F821, F841 - der Fehler wird hier geprüft


_FAELLE: dict[str, Callable[[], Any]] = {
    # AttributeError: das fehlende Attribut steht an zweiter Stelle
    "none_caption": lambda: None.caption,  # type: ignore[attr-defined]
    "int_append": lambda: (3).append(4),  # type: ignore[attr-defined]
    "modul": lambda: random.randInt(1, 6),  # type: ignore[attr-defined]
    "formular": lambda: _Form1().l_ausgab,  # type: ignore[attr-defined]
    "methode": lambda: "abc".upper.lower(),  # type: ignore[attr-defined]
    "klassenattribut": lambda: _Klasse.gibt_es_nicht,  # type: ignore[attr-defined]
    "none_upper": lambda: _ohne_return().upper(),  # type: ignore[func-returns-value]
    # KeyError: str() setzt den Schlüssel schon in Hochkommas
    "key_text": lambda: {"b": 1}["a"],
    "key_zahl": lambda: {1: 1}[2],
    "key_tupel": lambda: {}[(1, 2)],
    # FileNotFoundError und PermissionError: Dateiname in der Meldung
    "datei": lambda: open("gibtsnicht.txt"),  # noqa: SIM115
    "datei_ordner": lambda: open("ordner/gibtsnicht.csv"),  # noqa: SIM115
    "zeichensatz": lambda: bytes([255]).decode("utf-8"),
    # Die übrigen stimmten schon vorher überein und bleiben so.
    "division": lambda: 1 / 0,
    "name": lambda: unbekannt,  # type: ignore[name-defined]  # noqa: F821
    "unbound": _unbound,
    "index_liste": lambda: [1, 2][5],
    "index_text": lambda: "ab"[5],
    "index_zuweisung": lambda: [].__setitem__(0, 1),
    "pop_leer": lambda: [].pop(),
    "plus_int_str": lambda: 1 + "a",  # type: ignore[operator]
    "plus_str_int": lambda: "a" + 1,  # type: ignore[operator]
    "subscript": lambda: (5)[0],  # type: ignore[index]
    "callable": lambda: (5)(),  # type: ignore[operator]
    "iterable": lambda: list(5),  # type: ignore[call-overload]
    "unpack_non_iterable": lambda: [a for a, b in [5]],  # type: ignore[misc]
    "len": lambda: len(5),  # type: ignore[arg-type]
    "vergleich": lambda: 1 < "a",  # type: ignore[operator]
    "fehlende_angabe": lambda: math.sqrt(),  # type: ignore[call-arg]
    "zu_viele": lambda: _ohne_return(1),  # type: ignore[call-arg]
    "text_zuweisung": lambda: operator.setitem("abc", 1, "x"),  # type: ignore[arg-type]
    "unhashable": lambda: {[]: 1},
    "int_leer": lambda: int(""),
    "int_text": lambda: int("abc"),
    "float_text": lambda: float("2,5"),
    "zu_wenige_werte": lambda: [a for a, b, c in [(1, 2)]],
    "remove": lambda: [1].remove(2),
    "wurzel": lambda: math.sqrt(-1),
    "json": lambda: json.loads("{"),
    "randint": lambda: random.randint(5, 1),
    "min_leer": lambda: min([]),
    "rekursion": lambda: _rekursion(0),
    "modul_fehlt": lambda: __import__("u_gibtsnicht"),
}


def _ausloesen(f: Callable[[], Any]) -> BaseException:
    try:
        f()
    except BaseException as fehler:  # noqa: BLE001 - genau das wird geprüft
        return fehler
    raise AssertionError("f() hat keine Ausnahme ausgelöst")


def _exception_id(klasse: type) -> str:
    """So, wie debugpy die Klasse in `exceptionId` benennt: eingebaute
    ohne Modul, alle anderen mit."""
    if klasse.__module__ == "builtins":
        return klasse.__qualname__
    return f"{klasse.__module__}.{klasse.__qualname__}"


def _teile(meldung: Fehlermeldung | None) -> tuple[str, str, str]:
    assert meldung is not None
    return meldung.ueberschrift, meldung.was, meldung.pruefe


@pytest.mark.parametrize("fall", list(_FAELLE))
def test_mit_und_ohne_debugger_dieselbe_meldung(fall: str) -> None:
    fehler = _ausloesen(_FAELLE[fall])
    ohne_debugger = fehlermeldung_erzeugen(fehler)
    info = {
        "exceptionId": _exception_id(type(fehler)),
        "breakMode": "unhandled",
        "description": str(fehler),
        "details": {
            "message": str(fehler),
            "typeName": _exception_id(type(fehler)),
            "stackTrace": "",
        },
    }
    mit_debugger = fehlermeldung_aus_dap_erzeugen(info)

    assert _teile(mit_debugger) == _teile(ohne_debugger)
