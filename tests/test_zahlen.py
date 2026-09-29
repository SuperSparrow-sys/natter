"""`pcl.zahl` und `pcl.text`: Zahlen mit Dezimalkomma (Punkt 91)."""

from pathlib import Path

import pytest

from pcl import text, zahl
from pcl.errors import NatterPropertyError, NatterZahlError
from pcl.fehlerkatalog import fehlermeldung_erzeugen


@pytest.mark.parametrize(
    ("eingabe", "erwartet"),
    [
        ("2,5", 2.5),
        ("2.5", 2.5),
        (" -3 ", -3.0),
        ("1.234,5", 1234.5),
        ("0,1", 0.1),
        ("1e3", 1000.0),
    ],
)
def test_zahl_liest_komma_und_punkt(eingabe: str, erwartet: float) -> None:
    ergebnis = zahl(eingabe)
    assert ergebnis == erwartet
    assert isinstance(ergebnis, float)


@pytest.mark.parametrize("eingabe", ["abc", "2,5 Euro", "nan", "inf", "-inf", "²"])
def test_zahl_lehnt_ab_was_keine_zahl_ist(eingabe: str) -> None:
    with pytest.raises(NatterZahlError) as fehler:
        zahl(eingabe)
    assert str(fehler.value) == (
        f"„{eingabe}“ ist keine Zahl. Erwartet wird zum Beispiel 2,5 oder -3."
    )


def test_ein_leeres_feld_bekommt_eine_eigene_meldung() -> None:
    with pytest.raises(NatterZahlError, match="Das Feld ist leer"):
        zahl("   ")


def test_der_fehler_ist_ein_valueerror() -> None:
    with pytest.raises(ValueError):
        zahl("abc")


@pytest.mark.parametrize(
    ("wert", "stellen", "erwartet"),
    [
        (3.5, None, "3,5"),
        (10.0, None, "10"),
        (7, None, "7"),
        (0.1 + 0.2, None, "0,3"),
        (2.5, 2, "2,50"),
        (2.345, 1, "2,3"),
        (-0.001, 2, "0,00"),
        (1234567.0, None, "1234567"),
    ],
)
def test_text_schreibt_mit_komma(wert, stellen, erwartet) -> None:
    assert text(wert, stellen) == erwartet


@pytest.mark.parametrize(
    ("wert", "stellen", "erwartet"),
    [
        (2.5, 0, "3"),
        (0.5, 0, "1"),
        (0.125, 2, "0,13"),
        (1.005, 2, "1,01"),
        (-2.5, 0, "-3"),
        (1e30, 2, "1000000000000000000000000000000,00"),
    ],
)
def test_text_rundet_wie_in_der_schule(wert, stellen, erwartet) -> None:
    """Punkt 171: bei einer 5 wird aufgerundet, nicht zur geraden
    Ziffer, und gerundet wird die Zahl, wie sie im Programm steht."""
    assert text(wert, stellen) == erwartet


@pytest.mark.parametrize("stellen", [-1, 1.5, "2", True])
def test_text_lehnt_unsinnige_stellen_deutsch_ab(stellen) -> None:
    with pytest.raises(NatterPropertyError, match="ganze Zahl ab 0"):
        text(2.5, stellen)


def test_text_lehnt_einen_text_ab() -> None:
    with pytest.raises(NatterZahlError):
        text("3,5")


def test_der_fehlerkatalog_fragt_nicht_nach_dem_dezimalkomma() -> None:
    try:
        zahl("abc")
    except NatterZahlError as fehler:
        meldung = fehlermeldung_erzeugen(fehler)
    assert meldung is not None
    assert "Keine Zahl" in meldung.ueberschrift
    assert "„abc“ ist keine Zahl" in meldung.was
    assert "Dezimalkomma" not in meldung.pruefe
    katalog = Path(__file__).resolve().parent.parent / "docs" / "fehlerkatalog.yaml"
    assert "id: natter_zahl_error" in katalog.read_text(encoding="utf-8")


def test_der_taschenrechner_nimmt_die_funktionen_aus_pcl() -> None:
    quelle = (
        Path(__file__).resolve().parent.parent
        / "beispielprojekte"
        / "03_Taschenrechner"
        / "u_main.py"
    ).read_text(encoding="utf-8")
    assert "from pcl import text, zahl" in quelle
    assert "def zahl" not in quelle
    assert "def text" not in quelle


def test_punkte_zwischen_dreiergruppen_sind_tausendertrennung() -> None:
    """Punkt 219: „1.000“ ist im Deutschen tausend."""
    assert zahl("1.000") == 1000.0
    assert zahl("1.234.567") == 1234567.0
    assert zahl("-12.500") == -12500.0


def test_ein_punkt_ohne_dreiergruppe_bleibt_dezimalpunkt() -> None:
    assert zahl("2.5") == 2.5
    assert zahl("3.14") == 3.14
    assert zahl("0.500") == 0.5
    assert zahl("1.0005") == 1.0005
    with pytest.raises(NatterZahlError):
        zahl("1.234.5")
