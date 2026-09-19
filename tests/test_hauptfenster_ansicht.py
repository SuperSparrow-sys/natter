"""Tests für das Menü „Ansicht“ (Abschnitt 7.2): jedes Dock lässt sich
darüber wieder einblenden, nachdem es geschlossen wurde. Nutzer-Feedback
(September 2026): das Menü war komplett leer, ein geschlossenes Dock
(z. B. „Datenbank“) ließ sich nicht mehr zurückholen.
"""

from ide.shell.hauptfenster import HauptFenster


def test_ansicht_menue_listet_alle_docks() -> None:
    fenster = HauptFenster()
    titel = {aktion.text() for aktion in fenster.menue("Ansicht").actions()}
    # "Design" und "Schriftart" sind eigene Untermenüs (eigene Tests in
    # test_hauptfenster_design_wechsel.py/test_hauptfenster_schriftart_
    # wechsel.py), "Einrückungslinien", "Vervollständigung",
    # "Zeilenumbruch" und "Leerzeichen anzeigen" sind Anzeigeschalter
    # (M11) – keines davon ist eine Dock-Umschaltung.
    assert titel == {
        "Projekt-Explorer",
        "Objektinspektor",
        "Komponentenpalette",
        "Datenbank",
        "Panels",
        "Einrückungslinien",
        "Vervollständigung",
        "Zeilenumbruch",
        "Leerzeichen anzeigen",
        "Design",
        "Schriftart",
    }


def test_geschlossenes_dock_laesst_sich_ueber_ansicht_wiederherstellen() -> None:
    # .show() ist hier nötig: QDockWidget.isVisible() spiegelt den
    # tatsächlichen Sichtbarkeitszustand wider, der ohne ein gezeigtes
    # Hauptfenster für alle Kind-Widgets False bliebe.
    fenster = HauptFenster()
    fenster.show()
    fenster.datenbank_dock.close()
    assert fenster.datenbank_dock.isVisible() is False

    eintrag = next(
        a for a in fenster.menue("Ansicht").actions() if a.text() == "Datenbank"
    )
    eintrag.trigger()

    assert fenster.datenbank_dock.isVisible() is True


def test_ansicht_eintrag_ist_angekreuzt_wenn_das_dock_sichtbar_ist() -> None:
    fenster = HauptFenster()
    fenster.show()
    eintrag = next(
        a for a in fenster.menue("Ansicht").actions() if a.text() == "Projekt-Explorer"
    )
    assert eintrag.isChecked() is True

    fenster.explorer_dock.close()

    assert eintrag.isChecked() is False


def test_geschlossenes_dock_bleibt_nach_einem_neustart_der_ide_zu() -> None:
    """Nutzer-Feedback (September 2026): „Datenbank soll, wenn es zu
    gemacht wurde, beim nächsten Mal auch zu bleiben. Das Ganze auch bei
    den anderen Feldern.“"""
    fenster = HauptFenster()
    fenster.show()
    fenster.datenbank_dock.close()

    fenster.close()  # löst closeEvent aus, speichert die Anordnung

    neues_fenster = HauptFenster()
    neues_fenster.show()

    assert neues_fenster.datenbank_dock.isVisible() is False


def test_layout_zuruecksetzen_ignoriert_die_gespeicherte_anordnung() -> None:
    # "Layout zurücksetzen" muss zum echten Ausgangszustand zurückkehren,
    # nicht nur zur zuletzt gespeicherten (sonst gäbe es keinen Ausweg,
    # wenn man sich "verklickt" hat).
    fenster = HauptFenster()
    fenster.show()
    fenster.datenbank_dock.close()
    fenster.close()

    neues_fenster = HauptFenster()
    neues_fenster.show()
    assert neues_fenster.datenbank_dock.isVisible() is False

    neues_fenster._layout_zuruecksetzen_aktion()

    assert neues_fenster.datenbank_dock.isVisible() is True
