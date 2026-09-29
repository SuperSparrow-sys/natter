"""Der Projekt-Explorer ohne Projekt (Punkt 52 der offenen Punkte).

Ohne offenes Projekt standen die fetten Überschriften „Formulare“,
„Units“ und „Diagramme“ ohne einen Eintrag darunter da. Mit Projekt
blendet der Explorer leere Gruppen schon aus; ohne Projekt sind alle
leer.
"""

from __future__ import annotations

from ide.shell.explorer import ProjektExplorer


def test_ohne_projekt_keine_leeren_ueberschriften(qtbot) -> None:  # noqa: ANN001
    explorer = ProjektExplorer()
    qtbot.addWidget(explorer)

    for gruppe in (explorer.formulare_gruppe, explorer.units_gruppe, explorer.diagramme_gruppe):
        assert gruppe.isHidden(), gruppe.text(0)
