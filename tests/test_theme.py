"""Tests für pcl/theme/: QSS-Generator aus design/tokens.json. Siehe
docs/PLAN.md, M1 Schritt 7.
"""

from pathlib import Path

import pytest

from pcl import Form
from pcl.errors import NatterPropertyError
from pcl.theme import _tokens_pfad_ermitteln, qss_erzeugen, theme_aufloesen


def test_theme_aufloesen_light_und_dark_bleiben_unveraendert() -> None:
    assert theme_aufloesen("light") == "light"
    assert theme_aufloesen("dark") == "dark"


def test_theme_aufloesen_system_liefert_gueltigen_wert() -> None:
    assert theme_aufloesen("system") in ("light", "dark")


def test_theme_aufloesen_lehnt_unbekannten_wert_ab() -> None:
    with pytest.raises(NatterPropertyError):
        theme_aufloesen("knallpink")


def test_tokens_pfad_normal_zeigt_auf_das_design_verzeichnis_im_repo() -> None:
    pfad = _tokens_pfad_ermitteln()
    assert pfad.name == "tokens.json"
    assert pfad.exists()


def test_tokens_pfad_in_einer_pyinstaller_exe_zeigt_in_meipass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real mit einem echten PyInstaller-Bau gefunden (siehe
    `docs/arbeitspakete/M8.md`): ohne diese Fallunterscheidung sucht
    `pcl.theme` in der Exe am falschen Ort und jedes exportierte
    Programm stürzt schon beim Start ab."""
    import sys

    monkeypatch.setattr(sys, "_MEIPASS", r"C:\irgendwo\_internal", raising=False)

    pfad = _tokens_pfad_ermitteln()

    assert pfad == Path(r"C:\irgendwo\_internal") / "design" / "tokens.json"


def test_qss_enthaelt_die_tokens_des_gewaehlten_themes() -> None:
    hell = qss_erzeugen("light")
    dunkel = qss_erzeugen("dark")

    assert "#ffffff" in hell  # color.light.bg
    assert "#1e1e1e" in dunkel  # color.dark.bg
    assert hell != dunkel


def test_form_wendet_stylesheet_beim_erzeugen_an() -> None:
    class FormularDunkel(Form):
        def create_components(self) -> None:
            self.theme = "dark"

    formular = FormularDunkel()
    assert "#1e1e1e" in formular._qwidget.styleSheet()


def test_form_theme_aenderung_wirkt_sofort() -> None:
    formular = Form()
    formular.theme = "dark"
    assert "#1e1e1e" in formular._qwidget.styleSheet()
    formular.theme = "light"
    assert "#ffffff" in formular._qwidget.styleSheet()


def test_form_color_ueberschreibt_die_theme_hintergrundfarbe() -> None:
    # Entspricht Lazarus TForm.Color = clSilver
    # (referenz/lazarus/a_GUI_Komponenten).
    formular = Form()
    formular.color = "#c0c0c0"
    assert "background-color: #c0c0c0" in formular._qwidget.styleSheet()


def test_form_color_leer_faellt_auf_das_theme_zurueck() -> None:
    formular = Form()
    formular.color = "#c0c0c0"
    formular.color = ""
    assert "background-color: #c0c0c0" not in formular._qwidget.styleSheet()


def test_form_theme_wechsel_behaelt_die_color_ueberschreibung() -> None:
    formular = Form()
    formular.color = "#c0c0c0"
    formular.theme = "dark"
    assert "background-color: #c0c0c0" in formular._qwidget.styleSheet()
