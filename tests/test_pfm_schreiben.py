"""Tests für ide/designer/pfm_schreiben.py: Formular → `.pfm`. Siehe
Arbeitspaket M3, Schritt 4. Rundreise-Test gegen die echte
`beispielprojekte/04_CookieKlicker/u_main.pfm`.
"""

import json
from pathlib import Path

from ide.designer import formular_fuer_designer_laden
from ide.designer.pfm_schreiben import formular_als_pfm_speichern, pfm_aus_formular

_AMPEL_PFM = (
    Path(__file__).resolve().parent.parent / "beispielprojekte" / "04_CookieKlicker" / "u_main.pfm"
)


def test_rundreise_ohne_aenderung_liefert_aequivalente_daten() -> None:
    urspruenglich = json.loads(_AMPEL_PFM.read_text(encoding="utf-8"))
    formular = formular_fuer_designer_laden(_AMPEL_PFM)

    neu = pfm_aus_formular(formular)

    assert neu["class"] == urspruenglich["class"]
    # Standardwerte werden nicht gespeichert (Abschnitt 4.2); die Ampel-
    # .pfm setzt "theme": "system" explizit, obwohl das der Standardwert
    # ist - das darf beim Zurückschreiben entfallen, daher Teilmenge statt
    # exakter Gleichheit.
    assert neu["properties"].items() <= urspruenglich["properties"].items()
    assert urspruenglich["properties"]["caption"] == neu["properties"]["caption"]
    assert neu["events"] == urspruenglich["events"]

    kinder_namen = {kind["name"] for kind in neu["children"]}
    urspruenglich_namen = {kind["name"] for kind in urspruenglich["children"]}
    assert kinder_namen == urspruenglich_namen

    kind_nach_name = {kind["name"]: kind for kind in neu["children"]}
    urspruenglich_nach_name = {kind["name"]: kind for kind in urspruenglich["children"]}
    for name in kinder_namen:
        assert kind_nach_name[name]["type"] == urspruenglich_nach_name[name]["type"]
        # wieder Teilmenge statt Gleichheit: explizit im Standardwert
        # gespeicherte Eigenschaften (z. B. brush_color = "#000000" bei
        # s_gelb/s_gruen) dürfen beim Zurückschreiben entfallen.
        assert (
            kind_nach_name[name]["properties"].items()
            <= urspruenglich_nach_name[name]["properties"].items()
        )


def test_geaenderte_eigenschaft_erscheint_im_ergebnis() -> None:
    formular = formular_fuer_designer_laden(_AMPEL_PFM)
    formular.b_teig.left = 500

    neu = pfm_aus_formular(formular)

    kind = next(k for k in neu["children"] if k["name"] == "b_teig")
    assert kind["properties"]["left"] == 500


def test_standardwert_wird_nicht_gespeichert() -> None:
    formular = formular_fuer_designer_laden(_AMPEL_PFM)
    assert formular.b_teig.enabled is True  # Standardwert von Control

    neu = pfm_aus_formular(formular)

    kind = next(k for k in neu["children"] if k["name"] == "b_teig")
    assert "enabled" not in kind["properties"]


def test_formular_als_pfm_speichern_schreibt_eine_datei(tmp_path: Path) -> None:
    formular = formular_fuer_designer_laden(_AMPEL_PFM)
    formular.b_teig.caption = "AN"
    ziel = tmp_path / "kopie.pfm"

    formular_als_pfm_speichern(formular, ziel)

    gespeichert = json.loads(ziel.read_text(encoding="utf-8"))
    kind = next(k for k in gespeichert["children"] if k["name"] == "b_teig")
    assert kind["properties"]["caption"] == "AN"

    # gespeicherte Datei lässt sich wieder laden (gültig gegen das Schema)
    erneut = formular_fuer_designer_laden(ziel)
    assert erneut.b_teig.caption == "AN"
