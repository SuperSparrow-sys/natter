"""Tests für ide/project/projekt.py. Siehe docs/arbeitspakete/M2.md,
Schritt 3. Gegen die echten Beispielprojekte aus `beispielprojekte/`
geprüft.
"""

from pathlib import Path

import jsonschema
import pytest

from ide.project import Projekt

_AMPEL_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "04_CookieKlicker"


def test_laden_ueber_natter_datei() -> None:
    projekt = Projekt.laden(_AMPEL_ORDNER / "04_CookieKlicker.natter")
    assert projekt.name == "04_CookieKlicker"
    assert projekt.typ == "gui"


def test_laden_ueber_ordner_findet_die_natter_datei() -> None:
    projekt = Projekt.laden(_AMPEL_ORDNER)
    assert projekt.name == "04_CookieKlicker"


def test_laden_unbekannter_ordner_ohne_natter_datei(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Projekt.laden(tmp_path)


def test_haupt_datei_und_haupt_unit() -> None:
    projekt = Projekt.laden(_AMPEL_ORDNER)
    assert projekt.haupt_datei == _AMPEL_ORDNER / "main.py"
    assert projekt.haupt_unit == "u_main"


def test_units_ohne_design_dateien() -> None:
    projekt = Projekt.laden(_AMPEL_ORDNER)
    namen = [p.name for p in projekt.units()]
    assert "u_main_design.py" not in namen
    # Seit M12 steht die Startdatei nicht mehr bei den Units: sie wird
    # erzeugt und nicht bearbeitet, wie die `.lpr` in Lazarus. Erreichbar
    # bleibt sie über „Projekt → Startdatei anzeigen“.
    assert set(namen) == {"u_main.py"}
    assert "main.py" in {p.name for p in projekt.alle_python_dateien()}


def test_formulare() -> None:
    projekt = Projekt.laden(_AMPEL_ORDNER)
    namen = [p.name for p in projekt.formulare()]
    assert namen == ["u_main.pfm"]


def test_speichern_und_erneut_laden(tmp_path: Path) -> None:
    projekt = Projekt.laden(_AMPEL_ORDNER)
    projekt.ordner = tmp_path
    projekt.daten["name"] = "Kopie"

    ziel = tmp_path / "kopie.natter"
    projekt.speichern(ziel)

    erneut_geladen = Projekt.laden(ziel)
    assert erneut_geladen.name == "Kopie"


def test_ungueltige_projektdatei_wird_abgelehnt(tmp_path: Path) -> None:
    kaputt = tmp_path / "kaputt.natter"
    kaputt.write_text('{"format": "natter-project/1"}', encoding="utf-8")
    with pytest.raises(jsonschema.ValidationError):
        Projekt.laden(kaputt)
