"""S2: QWebChannel-Brücke zwischen Monaco (JavaScript) und Jedi (Python).

Siehe prototypes/s2_monaco_jedi/README.md.
"""

import jedi
from PySide6.QtCore import QObject, Slot


class EditorBruecke(QObject):
    @Slot(str, int, int, result="QVariantList")
    def vervollstaendigen(self, quelltext: str, zeile: int, spalte: int) -> list[dict]:
        skript = jedi.Script(code=quelltext)
        vorschlaege = skript.complete(line=zeile, column=spalte)
        return [
            {"label": v.name, "kind": v.type, "detail": v.description}
            for v in vorschlaege[:50]
        ]

    @Slot(str, int, int, result="QVariantList")
    def fehler_markieren(self, quelltext: str, zeile: int, spalte: int) -> list[dict]:
        skript = jedi.Script(code=quelltext)
        return [
            {
                "zeile": f.line,
                "spalte": f.column,
                "text": f.get_message(),
            }
            for f in skript.get_syntax_errors()
        ]
