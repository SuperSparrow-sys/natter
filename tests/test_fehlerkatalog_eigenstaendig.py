"""Die Meldungen erklären Python aus Python heraus (Punkt 435).

Zwei Leitfragen zu einem Einrückungsfehler endeten mit „Python nutzt
die Einrückung anstelle von begin/end.“ Für jemanden, der mit Python
anfängt, sagt „begin/end“ nichts; es verweist auf eine andere
Programmiersprache. Geprüft werden alle Vorlagen des Fehlerkatalogs,
der Prüfung vor dem Start und von `docs/fehlerkatalog.yaml`, dazu die
Meldung, die ein echter Einrückungsfehler bekommt.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from ide.run.pruefung import _SYNTAX_GENAUER, _UEBERSETZUNGEN
from pcl.fehlerkatalog import _STANDARDMELDUNGEN, fehlermeldung_erzeugen

WURZEL = Path(__file__).resolve().parent.parent

#: Wörter, mit denen eine Meldung auf eine andere Sprache oder ein
#: anderes Werkzeug zeigt statt auf Python.
FREMDER_BEZUG = re.compile(
    r"\bbegin\b|\bend\b|\bPascal\b|\bLazarus\b|\bDelphi\b",
    re.IGNORECASE,
)


def _yaml_texte() -> list[str]:
    texte = []
    for zeile in (WURZEL / "docs" / "fehlerkatalog.yaml").read_text(
        "utf-8"
    ).splitlines():
        _, trenner, wert = zeile.partition(": ")
        if trenner and not zeile.lstrip().startswith("#"):
            texte.append(wert)
    return texte


def _ausloesen(quelltext: str) -> SyntaxError:
    try:
        compile(quelltext, "u_main.py", "exec")
    except SyntaxError as fehler:
        return fehler
    raise AssertionError("kein Syntaxfehler")


QUELLEN = [
    pytest.param(
        lambda: [t for m in _STANDARDMELDUNGEN for t in (m.was, m.pruefe)],
        id="fehlerkatalog",
    ),
    pytest.param(
        lambda: [
            t
            for vorlage in (
                *_UEBERSETZUNGEN.values(),
                *(v for _, v in _SYNTAX_GENAUER),
            )
            for t in vorlage
        ],
        id="pruefung-vor-dem-start",
    ),
    pytest.param(_yaml_texte, id="fehlerkatalog-yaml"),
    pytest.param(
        lambda: [
            t
            for quelltext in (
                "x = 1\nif x == 1:\nprint(x)\n",
                "def f():\n\n",
            )
            for m in [fehlermeldung_erzeugen(_ausloesen(quelltext))]
            if m is not None
            for t in (m.was, m.pruefe)
        ],
        id="einrueckungsfehler",
    ),
]


@pytest.mark.parametrize("texte", QUELLEN)
def test_keine_meldung_verweist_auf_eine_andere_sprache(texte) -> None:
    gefunden = texte()

    assert gefunden
    treffer = [t for t in gefunden if FREMDER_BEZUG.search(t)]
    assert not treffer, "\n".join(treffer)
