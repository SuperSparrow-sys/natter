"""Ereignis-Codegenerierung: fügt eine Handler-Methode in eine Formular-
Unit ein, ohne die restliche Formatierung zu verändern.

Siehe konzept-natter.md, Abschnitt 4.4: „Doppelklick auf Ereignis /
Komponente → Methode `def <name>_<ereignis>(self, sender):` in
`u_main.py` einfügen (libcst), Editor springt hin.“ Der Sprung zur neuen
Stelle im Editor ist Sache der aufrufenden Stelle (`ide/designer/`); hier
steht nur die reine Textumwandlung.
"""

from __future__ import annotations

import libcst as cst


def _hat_methode(klasse: cst.ClassDef, methodenname: str) -> bool:
    return any(
        isinstance(glied, cst.FunctionDef) and glied.name.value == methodenname
        for glied in klasse.body.body
    )


def _leere_handler_methode(methodenname: str) -> cst.FunctionDef:
    return cst.FunctionDef(
        name=cst.Name(methodenname),
        params=cst.Parameters(
            params=[cst.Param(cst.Name("self")), cst.Param(cst.Name("sender"))]
        ),
        body=cst.IndentedBlock(body=[cst.SimpleStatementLine([cst.Pass()])]),
        leading_lines=[cst.EmptyLine()],
    )


class _MethodeAnhaengen(cst.CSTTransformer):
    def __init__(self, klassenname: str, methodenname: str) -> None:
        self.klassenname = klassenname
        self.methodenname = methodenname
        self.eingefuegt = False

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if original_node.name.value != self.klassenname:
            return updated_node
        if _hat_methode(original_node, self.methodenname):
            return updated_node

        self.eingefuegt = True
        neuer_body = list(updated_node.body.body) + [_leere_handler_methode(self.methodenname)]
        return updated_node.with_changes(body=updated_node.body.with_changes(body=neuer_body))


def handler_methode_einfuegen(quelltext: str, klassenname: str, methodenname: str) -> str:
    """Fügt `def <methodenname>(self, sender): pass` am Ende der Klasse
    `klassenname` ein, falls dort noch keine Methode mit diesem Namen
    existiert. Der restliche Quelltext bleibt Zeichen für Zeichen
    unverändert (libcst, kein Neuformatieren)."""
    modul = cst.parse_module(quelltext)
    einfueger = _MethodeAnhaengen(klassenname, methodenname)
    geaendertes_modul = modul.visit(einfueger)
    return geaendertes_modul.code
