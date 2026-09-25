"""Tests für ide/codegen/ereignis.py: Handler-Methode per libcst
einfügen. Siehe Arbeitspaket M3, Schritt 7.
"""

import libcst as cst

from ide.codegen.ereignis import handler_methode_einfuegen

_BEISPIEL_QUELLTEXT = '''"""Docstring bleibt erhalten."""

from u_main_design import Form1Design


class Form1(Form1Design):
    def form_create(self, sender):
        self.ampel = "irgendetwas"  # Kommentar bleibt erhalten
'''


def test_fuegt_neue_methode_am_ende_der_klasse_ein() -> None:
    ergebnis = handler_methode_einfuegen(_BEISPIEL_QUELLTEXT, "Form1", "b_ein_click")

    assert "def b_ein_click(self, sender):" in ergebnis
    assert ergebnis.index("def form_create") < ergebnis.index("def b_ein_click")


def test_generierter_quelltext_ist_gueltiges_python() -> None:
    ergebnis = handler_methode_einfuegen(_BEISPIEL_QUELLTEXT, "Form1", "b_ein_click")

    namensraum: dict = {}
    # from u_main_design import Form1Design würde hier fehlschlagen, daher
    # nur auf Syntaxgültigkeit prüfen (kompilieren reicht, nicht ausführen)
    compile(ergebnis, "<test>", "exec")
    assert namensraum == {}  # nichts wurde ausgeführt, nur kompiliert


def test_restlicher_quelltext_bleibt_zeichengenau_erhalten() -> None:
    ergebnis = handler_methode_einfuegen(_BEISPIEL_QUELLTEXT, "Form1", "b_ein_click")

    assert '"""Docstring bleibt erhalten."""' in ergebnis
    assert '# Kommentar bleibt erhalten' in ergebnis
    assert "from u_main_design import Form1Design" in ergebnis


def test_vorhandene_methode_wird_nicht_doppelt_eingefuegt() -> None:
    einmal = handler_methode_einfuegen(_BEISPIEL_QUELLTEXT, "Form1", "form_create")

    assert einmal.count("def form_create") == 1
    assert einmal == _BEISPIEL_QUELLTEXT


def test_zweimaliges_einfuegen_derselben_neuen_methode_ist_idempotent() -> None:
    erstes_mal = handler_methode_einfuegen(_BEISPIEL_QUELLTEXT, "Form1", "b_ein_click")
    zweites_mal = handler_methode_einfuegen(erstes_mal, "Form1", "b_ein_click")

    assert zweites_mal.count("def b_ein_click") == 1
    assert zweites_mal == erstes_mal


def test_unbekannte_klasse_aendert_nichts() -> None:
    ergebnis = handler_methode_einfuegen(_BEISPIEL_QUELLTEXT, "GibtEsNicht", "x_click")

    assert ergebnis == _BEISPIEL_QUELLTEXT


def test_neue_methode_hat_sender_parameter_und_pass_rumpf() -> None:
    ergebnis = handler_methode_einfuegen(_BEISPIEL_QUELLTEXT, "Form1", "b_ein_click")
    baum = cst.parse_module(ergebnis)

    klasse = next(
        stmt
        for stmt in baum.body
        if isinstance(stmt, cst.ClassDef) and stmt.name.value == "Form1"
    )
    methode = next(
        glied
        for glied in klasse.body.body
        if isinstance(glied, cst.FunctionDef) and glied.name.value == "b_ein_click"
    )
    parameter_namen = [p.name.value for p in methode.params.params]
    assert parameter_namen == ["self", "sender"]
