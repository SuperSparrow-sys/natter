"""Tests für das Menü „Ansicht“ (Abschnitt 7.2): jedes Dock lässt sich
darüber wieder einblenden, nachdem es geschlossen wurde. Nutzer-Feedback
(September 2026): das Menü war komplett leer, ein geschlossenes Dock
(z. B. „Datenbank“) ließ sich nicht mehr zurückholen.
"""

from ide.shell.hauptfenster import HauptFenster


def test_ansicht_menue_listet_alle_docks() -> None:
    fenster = HauptFenster()
    titel = {aktion.text() for aktion in fenster.menue("Ansicht").actions()}
    assert titel == {
        "Projekt-Explorer",
        "Objektinspektor",
        "Komponentenpalette",
        "Datenbank",
        "Panels",
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
