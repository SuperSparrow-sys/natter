"""Tests für ide/assets/symbole.py: SVG-Symbole als QIcon laden. Headless.
"""

from ide.assets import symbol


def test_bekannte_symbole_laden_ein_gueltiges_icon() -> None:
    for name in ("app", "start", "neu", "oeffnen", "projekt_oeffnen", "speichern"):
        assert not symbol(name).isNull(), name


def test_app_symbol_ist_das_png_maskottchen_nicht_leer() -> None:
    """Nutzer-Feedback (September 2026): eigenes Schlangen-Bild statt
    des bisherigen Vektor-Symbols als Fenster-/Taskleisten-Icon - `.png`
    statt `.svg`, `symbol()` muss deshalb auch `.png` finden."""
    icon = symbol("app")
    assert not icon.isNull()
    assert icon.availableSizes()  # tatsächlich Bilddaten geladen, kein Platzhalter


def test_unbekanntes_symbol_liefert_ein_leeres_icon_statt_fehler() -> None:
    assert symbol("gibt_es_nicht").isNull()


def test_leerer_name_liefert_ein_leeres_icon() -> None:
    assert symbol("").isNull()
