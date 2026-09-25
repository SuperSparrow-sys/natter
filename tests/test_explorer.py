"""Tests für ide/shell/explorer.py: ProjektExplorer. Headless. Siehe
Arbeitspaket M2, Schritt 6.
"""

from pathlib import Path

from PySide6.QtWidgets import QTreeWidget

from ide.project import Projekt
from ide.shell.explorer import ProjektExplorer

_AMPEL_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "06_Kontoverwaltung"


def test_leerer_explorer_hat_alle_gruppen_ohne_kinder() -> None:
    explorer = ProjektExplorer()
    # Formulare, Units, Diagramme (Diagramme seit M9, Schritt 1)
    assert explorer.topLevelItemCount() == 3
    assert explorer.formulare_gruppe.childCount() == 0
    assert explorer.units_gruppe.childCount() == 0
    assert explorer.diagramme_gruppe.childCount() == 0


def test_doppelklick_loest_kein_natives_qt_umbenennen_aus() -> None:
    # Nutzer-Screenshot: ein Doppelklick zum Öffnen einer Datei
    # aktivierte gleichzeitig Qts eingebautes Inline-Umbenennen
    # (Qt.ItemIsEditable gehört zu den Standard-Flags von
    # QTreeWidgetItem) - ein unstyled, ungewolltes Eingabefeld mitten
    # im Baum, unabhängig von unserer eigenen „⋮ → Umbenennen …“.
    explorer = ProjektExplorer()
    assert explorer.editTriggers() == QTreeWidget.EditTrigger.NoEditTriggers


def test_die_unit_zum_formular_steht_auch_bei_den_units() -> None:
    """Früher stand sie nicht dort - das Formular habe
 sie ja schon. Die beiden sind aber nicht dasselbe: unter „Formulare"
 liegt die Oberfläche, unter „Units" der Code, und genau der ist die
 Datei, in die der Schüler schreibt. Wer ein neues Projekt anlegte, sah
 deshalb nur den Designer (Gemeldet: „wenn ich ein neues Projekt erstelle
 muss auch die u_main.py für
 den code angezeigt werden nicht nur der designer")."""
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
    assert "u_main.py" in unit_namen
    # Die Startdatei bleibt draußen: sie wird erzeugt, nicht bearbeitet.
    assert "main.py" not in unit_namen


def test_erneutes_anzeigen_ersetzt_den_alten_inhalt() -> None:
    projekt = Projekt.laden(_AMPEL_ORDNER)
    explorer = ProjektExplorer()

    explorer.projekt_anzeigen(projekt)
    explorer.projekt_anzeigen(projekt)

    assert explorer.formulare_gruppe.childCount() == 1
    # `u_main.py` und `u_konto.py`; die Startdatei `main.py` steht seit
    # M12 gar nicht mehr im Baum.
    assert explorer.units_gruppe.childCount() == 2
