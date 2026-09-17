"""Tests für ide/shell/explorer.py: ProjektExplorer. Headless. Siehe
docs/arbeitspakete/M2.md, Schritt 6.
"""

from pathlib import Path

from PySide6.QtWidgets import QTreeWidget

from ide.project import Projekt
from ide.shell.explorer import ProjektExplorer

_AMPEL_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "Ampel"


def test_leerer_explorer_hat_beide_gruppen_ohne_kinder() -> None:
    explorer = ProjektExplorer()
    assert explorer.topLevelItemCount() == 2
    assert explorer.formulare_gruppe.childCount() == 0
    assert explorer.units_gruppe.childCount() == 0


def test_doppelklick_loest_kein_natives_qt_umbenennen_aus() -> None:
    # Nutzer-Screenshot: ein Doppelklick zum Öffnen einer Datei
    # aktivierte gleichzeitig Qts eingebautes Inline-Umbenennen
    # (Qt.ItemIsEditable gehört zu den Standard-Flags von
    # QTreeWidgetItem) - ein unstyled, ungewolltes Eingabefeld mitten
    # im Baum, unabhängig von unserer eigenen „⋮ → Umbenennen …“.
    explorer = ProjektExplorer()
    assert explorer.editTriggers() == QTreeWidget.EditTrigger.NoEditTriggers


def test_formular_unit_erscheint_nur_bei_formularen() -> None:
    projekt = Projekt.laden(_AMPEL_ORDNER)
    explorer = ProjektExplorer()

    explorer.projekt_anzeigen(projekt)

    formular_namen = {
        explorer.formulare_gruppe.child(i).text(0)
        for i in range(explorer.formulare_gruppe.childCount())
    }
    unit_namen = {
        explorer.units_gruppe.child(i).text(0)
        for i in range(explorer.units_gruppe.childCount())
    }
    assert formular_namen == {"u_main"}
    assert "u_main.py" not in unit_namen  # gehört zum Formular, nicht separat bei Units


def test_erneutes_anzeigen_ersetzt_den_alten_inhalt() -> None:
    projekt = Projekt.laden(_AMPEL_ORDNER)
    explorer = ProjektExplorer()

    explorer.projekt_anzeigen(projekt)
    explorer.projekt_anzeigen(projekt)

    assert explorer.formulare_gruppe.childCount() == 1
    assert explorer.units_gruppe.childCount() == 2
