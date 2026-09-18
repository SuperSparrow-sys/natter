"""Die Datenfehler aus `pcl.errors` müssen im Fehlerkatalog des
Debuggers landen (M10, Punkt 3: „Fehlerfälle gehören in den Fehlerkatalog
und nicht in einen Python-Traceback“).

Einen eigenen Katalogeintrag haben sie nicht – der stünde in
`ide/debugger/fehlerkatalog.py` und `docs/fehlerkatalog.yaml`, beide
außerhalb dieses Arbeitspakets. Stattdessen sind die Basisklassen so
gewählt, dass die MRO-Suche des Katalogs von allein einen passenden
Eintrag findet. Genau das prüfen diese Tests: ohne sie fiele ein
Wechsel der Basisklasse (etwa auf `RuntimeError` wie bei
`NatterDatenbankError`) nicht auf – dort liefert der Katalog nämlich
gar keine Meldung, und der Schüler sähe den rohen Traceback.
"""

from __future__ import annotations

import pytest

from ide.debugger.fehlerkatalog import fehlermeldung_erzeugen
from pcl.analyse import regression
from pcl.errors import NatterDatenDateiError, NatterDatenError


def _meldung(fehler: BaseException):
    """Wirft `fehler` wirklich, damit er einen Traceback bekommt - ohne
    den kann der Katalog kein „Wo“ ermitteln."""
    try:
        raise fehler
    except BaseException as ausnahme:
        return fehlermeldung_erzeugen(ausnahme)


def test_datenfehler_bekommt_eine_wo_was_pruefe_meldung() -> None:
    with pytest.raises(NatterDatenError) as gefangen:
        regression([1, 2, 3], ["eins", "zwei", "drei"])

    meldung = fehlermeldung_erzeugen(gefangen.value)

    assert meldung is not None
    assert "müssen Zahlen sein" in meldung.was
    assert meldung.pruefe


def test_fehlende_datendatei_meldet_datei_nicht_gefunden() -> None:
    meldung = _meldung(NatterDatenDateiError("Die Datei „daten.csv“ wurde nicht gefunden."))

    assert meldung is not None
    assert "Datei nicht gefunden" in meldung.ueberschrift
    assert "daten.csv" in meldung.was
