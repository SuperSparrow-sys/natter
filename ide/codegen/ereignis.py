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
#: `pass` ist ein rätselhaftes Wort: es sieht aus wie eine Anweisung,
#: tut aber nichts. Die Zeile darüber
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
        # `indent=False`: sonst stünden in der Leerzeile vor der Methode
        # vier Leerzeichen.
        leading_lines=[cst.EmptyLine(indent=False)],
    )


def _nur_pass(anweisung: cst.BaseStatement) -> bool:
    """Ob die Anweisung ein alleinstehendes `pass` ohne Kommentar ist -
    der Platzhalter einer leeren Klasse aus der Projektvorlage."""
    return (
        isinstance(anweisung, cst.SimpleStatementLine)
        and len(anweisung.body) == 1
        and isinstance(anweisung.body[0], cst.Pass)
        and not any(z.comment for z in anweisung.leading_lines)
        and anweisung.trailing_whitespace.comment is None
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
        bisher = list(updated_node.body.body)
        methode = _leere_handler_methode(self.methodenname, self.zusatz_parameter)
        # Die leere Klasse aus der Vorlage besteht nur aus `pass`. Das
        # blieb bis 0.3.4 über der ersten angelegten Methode stehen.
        if len(bisher) == 1 and _nur_pass(bisher[0]):
            bisher = []
            methode = methode.with_changes(leading_lines=[])
        neuer_body = [*bisher, methode]
        return updated_node.with_changes(body=updated_node.body.with_changes(body=neuer_body))


class _MethodeUmbenennen(cst.CSTTransformer):
    """Benennt `alt` in `neu` um - die Methode selbst und jede Stelle,
    an der ihr Name vorkommt."""

    def __init__(self, alt: str, neu: str) -> None:
        self.alt = alt
        self.neu = neu
        self.gefunden = False

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if original_node.name.value != self.alt:
            return updated_node
        self.gefunden = True
        return updated_node.with_changes(name=cst.Name(self.neu))

    def leave_Attribute(
        self, original_node: cst.Attribute, updated_node: cst.Attribute
    ) -> cst.Attribute:
        # `self.cb_ausgabe_change` als Wert, etwa bei einer eigenen
        # Zuweisung im Schülercode.
        if original_node.attr.value != self.alt:
            return updated_node
        return updated_node.with_changes(attr=cst.Name(self.neu))


def syntaxfehler_zeile(quelltext: str) -> int | None:
    """Die Zeile des ersten Syntaxfehlers in `quelltext`, oder `None`,
    wenn er sich übersetzen lässt.

    Geprüft wird mit dem Übersetzer von Python und mit `libcst`, denn
    `libcst` schreibt die Unit hinterher um. Eine Unit mit
    Syntaxfehler ist beim Arbeiten der Normalfall; der Designer fragt
    hier vorher nach und meldet ihn, statt mitten in einer Änderung
    mit einem `ParserSyntaxError` abzubrechen (Punkt 141).
    """
    import ast

    try:
        ast.parse(quelltext)
    except SyntaxError as fehler:
        return fehler.lineno or 1
    except ValueError:
        return 1
    try:
        cst.parse_module(quelltext)
    except cst.ParserSyntaxError as fehler:
        return fehler.raw_line
    return None


def handler_methode_umbenennen(quelltext: str, alt: str, neu: str) -> tuple[str, bool]:
    """Benennt die Ereignismethode `alt` in `neu` um.

    Gebraucht beim Umbenennen einer Komponente im Designer: die
    Ereignismethoden ziehen mit, denn wer `cb_ausgabe` in
    `cb_minus` umbenennt, will nicht `cb_minus.on_change =
    self.cb_ausgabe_change` zurückbehalten.

    Liefert `(quelltext, ob etwas umbenannt wurde)`. Der Aufrufer
    entscheidet, ob umbenannt werden darf - hier wird nur
    gearbeitet.
    """
    modul = cst.parse_module(quelltext)
    umbenenner = _MethodeUmbenennen(alt, neu)
    geaendert = modul.visit(umbenenner)
    return geaendert.code, umbenenner.gefunden


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


def leere_handler_methode_entfernen(
    quelltext: str, klassenname: str, methodenname: str
) -> str | None:
    """Entfernt die Methode `methodenname` aus der Klasse
    `klassenname`, wenn sie noch genau so dasteht, wie
    `handler_methode_einfuegen` sie angelegt hat: mit dem Hinweis und
    `pass` als einzigem Inhalt. Liefert den neuen Quelltext, oder
    `None`, wenn es die Methode nicht gibt oder jemand etwas an ihr
    geändert hat - dann bleibt sie stehen (Punkt 537)."""
    modul = cst.parse_module(quelltext)
    for anweisung in modul.body:
        if not (
            isinstance(anweisung, cst.ClassDef) and anweisung.name.value == klassenname
        ):
            continue
        for glied in anweisung.body.body:
            if not (
                isinstance(glied, cst.FunctionDef) and glied.name.value == methodenname
            ):
                continue
            parameter = tuple(
                p.name.value for p in glied.params.params[2:]
            )
            geruest = _leere_handler_methode(methodenname, parameter)
            if modul.code_for_node(glied.with_changes(leading_lines=[])) != (
                modul.code_for_node(geruest.with_changes(leading_lines=[]))
            ):
                return None
            neuer_rumpf = [g for g in anweisung.body.body if g is not glied]
            if not neuer_rumpf:
                # Wie vor dem ersten Doppelklick: eine leere Klasse
                # braucht ein `pass`.
                neuer_rumpf = [cst.SimpleStatementLine([cst.Pass()])]
            neue_klasse = anweisung.with_changes(
                body=anweisung.body.with_changes(body=neuer_rumpf)
            )
            return modul.deep_replace(anweisung, neue_klasse).code
    return None
