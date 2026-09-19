"""Tests für ide/debugger/eigener_code.py: erkennt eigenen Schülercode
gegenüber `pcl`/Qt/Standardbibliothek (Abschnitt 8.1). Siehe
docs/arbeitspakete/M4.md, Schritt 2/5.
"""

from __future__ import annotations

import json

from pcl.eigener_code import ist_eigener_code


def test_relative_pfade_gelten_als_eigener_code() -> None:
    assert ist_eigener_code("u_main.py") is True


def test_datei_im_pcl_ordner_gilt_nicht_als_eigener_code() -> None:
    assert ist_eigener_code(json.__file__.replace("json", "pcl")) is False


def test_datei_in_site_packages_gilt_nicht_als_eigener_code() -> None:
    import pytest

    assert ist_eigener_code(pytest.__file__) is False


def test_stdlib_datei_gilt_nicht_als_eigener_code() -> None:
    assert ist_eigener_code(json.__file__) is False
