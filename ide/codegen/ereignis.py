"""Ereignis-Codegenerierung: fügt eine Handler-Methode in eine Formular-
Unit ein, ohne die restliche Formatierung zu verändern.

Siehe README.md, Abschnitt 4.4: „Doppelklick auf Ereignis /
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


#: Steht in jeder frisch erzeugten Ereignis-Methode über dem `pass`.
#:
#: `pass` ist für jemanden, der von Pascal kommt, ein rätselhaftes Wort:
#: es sieht aus wie eine Anweisung, tut aber nichts. Die Zeile darüber
#: sagt, wofür der leere Rumpf da ist, und verschwindet von selbst,
#: sobald die erste eigene Zeile sie ersetzt (M12).
RUMPF_HINWEIS = "Hier steht, was passieren soll."


def _leere_handler_methode(
    methodenname: str, zusatz_parameter: tuple[str, ...] = ()
) -> cst.FunctionDef:
    return cst.FunctionDef(
        name=cst.Name(methodenname),
        params=cst.Parameters(
            params=[
                cst.Param(cst.Name("self")),
                cst.Param(cst.Name("sender")),
                *(cst.Param(cst.Name(name)) for name in zusatz_parameter),
            ]
        ),
        body=cst.IndentedBlock(
            body=[
                cst.SimpleStatementLine(
                    [cst.Pass()],
                    leading_lines=[
                        cst.EmptyLine(comment=cst.Comment(f"# {RUMPF_HINWEIS}"))
                    ],
                )
            ]
        ),
        leading_lines=[cst.EmptyLine()],
    )


class _MethodeAnhaengen(cst.CSTTransformer):
    def __init__(
        self,
        klassenname: str,
        methodenname: str,
        zusatz_parameter: tuple[str, ...] = (),
    ) -> None:
        self.klassenname = klassenname
        self.methodenname = methodenname
        self.zusatz_parameter = zusatz_parameter
        self.eingefuegt = False

    def leave_ClassDef(
        self, original_node: cst.ClassDef, updated_node: cst.ClassDef
    ) -> cst.ClassDef:
        if original_node.name.value != self.klassenname:
            return updated_node
        if _hat_methode(original_node, self.methodenname):
            return updated_node

        self.eingefuegt = True
        neuer_body = list(updated_node.body.body) + [
            _leere_handler_methode(self.methodenname, self.zusatz_parameter)
        ]
        return updated_node.with_changes(body=updated_node.body.with_changes(body=neuer_body))


def handler_methode_einfuegen(
    quelltext: str,
    klassenname: str,
    methodenname: str,
    zusatz_parameter: tuple[str, ...] = (),
) -> str:
    """Fügt `def <methodenname>(self, sender): pass` am Ende der Klasse
    `klassenname` ein, falls dort noch keine Methode mit diesem Namen
    existiert. Der restliche Quelltext bleibt Zeichen für Zeichen
    unverändert (libcst, kein Neuformatieren).

    `zusatz_parameter` sind die Werte, die das Ereignis über `sender`
    hinaus mitbringt - bei den Maus-Ereignissen `x` und `y`. Welche das
    sind, steht in `pcl.control.EREIGNIS_PARAMETER`; hier wird nur
    geschrieben, was dort festgelegt ist."""
    modul = cst.parse_module(quelltext)
    einfueger = _MethodeAnhaengen(klassenname, methodenname, zusatz_parameter)
    geaendertes_modul = modul.visit(einfueger)
    return geaendertes_modul.code
