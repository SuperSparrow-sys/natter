"""Tests für ide/shell/schnellauswahl.py: SchnellAuswahl („Unit öffnen
…“, Strg+P). Headless, ohne `exec()` (siehe Modul-Docstring). Siehe
docs/arbeitspakete/M2.md, Schritt 8.
"""

from pathlib import Path

from PySide6.QtWidgets import QDialog

from ide.shell.hauptfenster import HauptFenster
from ide.shell.schnellauswahl import SchnellAuswahl

_PROJEKT = (
    Path(__file__).resolve().parent.parent / "beispielprojekte" / "06_Kontoverwaltung"
)

_DATEIEN = [
    Path("u_konto.py"),
    Path("u_main.py"),
    Path("main.py"),
    Path("u_main.pfm"),
]


def test_ohne_suchtext_stehen_alle_dateien_alphabetisch_da() -> None:
    dialog = SchnellAuswahl(_DATEIEN)
    assert dialog.gefilterte_namen() == ["main.py", "u_konto.py", "u_main.pfm", "u_main.py"]


def test_suchtext_filtert_die_liste() -> None:
    dialog = SchnellAuswahl(_DATEIEN)
    dialog.suchfeld.setText("konto")
    assert dialog.gefilterte_namen() == ["u_konto.py"]


def test_auswahl_per_aktivierung_setzt_ausgewaehlte_datei_und_akzeptiert() -> None:
    dialog = SchnellAuswahl(_DATEIEN)
    dialog.suchfeld.setText("u_konto")

    dialog._uebernehmen(dialog.liste.item(0))

    assert dialog.ausgewaehlte_datei == Path("u_konto.py")
    assert dialog.result() == QDialog.DialogCode.Accepted


def test_enter_im_suchfeld_uebernimmt_die_erste_zeile() -> None:
    dialog = SchnellAuswahl(_DATEIEN)
    dialog.suchfeld.setText("u_main")

    dialog.suchfeld.returnPressed.emit()

    assert dialog.ausgewaehlte_datei == Path("u_main.pfm")  # erste alphabetisch


def test_projekt_dateien_liefert_units_und_formulare() -> None:
    fenster = HauptFenster()
    assert fenster.projekt_dateien() == []

    fenster.projekt_oeffnen(_PROJEKT)
    namen = {p.name for p in fenster.projekt_dateien()}
    # Seit M12 steht die Startdatei nicht mehr bei den Units: sie wird
    # erzeugt und nicht bearbeitet, wie die `.lpr` in Lazarus. Erreichbar
    # bleibt sie über „Projekt → Startdatei anzeigen“.
    assert namen == {"u_konto.py", "u_main.py", "u_main.pfm"}
