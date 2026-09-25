"""Tests für ide/designer/laden.py: formular_fuer_designer_laden(). Siehe
Arbeitspaket M3, Schritt 3. Gegen die echte
`beispielprojekte/04_CookieKlicker/u_main.pfm` geprüft.
"""

from pathlib import Path

from ide.designer import DesignerCanvas, formular_fuer_designer_laden

_PFM = (
    Path(__file__).resolve().parent.parent / "beispielprojekte" / "04_CookieKlicker" / "u_main.pfm"
)


def test_laedt_form_mit_allen_kindern_und_werten_aus_der_pfm() -> None:
    formular = formular_fuer_designer_laden(_PFM)

    assert formular.caption == "Cookie-Klicker"
    assert formular.b_teig.caption == "Besserer Teig"
    assert formular.i_keks.width == 300
    assert formular.t_helfer.interval == 1000


def test_referenzierte_handler_existieren_als_wirkungslose_platzhalter() -> None:
    formular = formular_fuer_designer_laden(_PFM)

    # löst weder AttributeError (fehlende Methode) noch eine echte
    # Programmwirkung aus - reine Designer-Vorschau (Abschnitt 4.2)
    formular.b_teig.on_click(formular.b_teig)


def test_platzhalter_tragen_den_echten_handlernamen() -> None:
    """Regressionstest: die Platzhalter waren zuerst anonyme Lambdas mit
    `__name__ == "<lambda>"`, das brach das Zurückschreiben in die .pfm
    (ide/designer/pfm_schreiben.py liest `handler.__name__` aus)."""
    formular = formular_fuer_designer_laden(_PFM)

    assert formular.on_create.__name__ == "form_create"
    assert formular.b_teig.on_click.__name__ == "b_teig_click"


def test_kann_in_einen_designer_canvas_eingehaengt_werden() -> None:
    formular = formular_fuer_designer_laden(_PFM)
    canvas = DesignerCanvas(formular)

    getroffen = canvas.klick_bei(
        formular.b_teig.left + 5, formular.b_teig.top + 5
    )

    assert getroffen is formular.b_teig
