"""Tests für das Menü „Ansicht“ (Abschnitt 7.2): jedes Dock lässt sich
darüber wieder einblenden, nachdem es geschlossen wurde. Rückmeldung
: das Menü war komplett leer, ein geschlossenes Dock
(z. B. „Datenbank“) ließ sich nicht mehr zurückholen.
"""


def test_ansicht_menue_listet_alle_docks(hauptfenster) -> None:
    titel = {aktion.text() for aktion in hauptfenster.menue("Ansicht").actions()}
    # "Formular und Code wechseln" (Abschnitt 7.9) ist keine Dock-Umschaltung,
    # sondern der Handgriff, der zwischen Designer und Unit springt.
    # "Design" und "Schriftart" sind eigene Untermenüs (eigene Tests in
    # test_hauptfenster_design_wechsel.py/test_hauptfenster_schriftart_
    # wechsel.py), "Einrückungslinien", "Vervollständigung",
    # "Zeilenumbruch" und "Leerzeichen anzeigen" sind Anzeigeschalter
    # (M11) – keines davon ist eine Dock-Umschaltung.
    assert titel == {
        "Formular und Code wechseln",
        # „Startseite“ führt von einem offenen Projekt zurück zum
        # Startbild - auch keine Dock-Umschaltung, eigener Test in
        # test_startseite_wechseln.py.
        "Startseite",
        "",  # die Trennlinie dahinter
        "Projekt-Explorer",
        "Objektinspektor",
        "Komponentenpalette",
        "Datenbank",
        "Panels",
        "Einrückungslinien",
        "Vervollständigung",
        "Zeilenumbruch",
        "Leerzeichen anzeigen",
        # Schriftgröße im Editor (Punkt 101) - ebenfalls keine Docks.
        "Schrift größer",
        "Schrift kleiner",
        "Normale Schriftgröße",
        "Design",
        "Schriftart",
    }


def test_jedes_geschlossene_dock_laesst_sich_ueber_ansicht_wiederherstellen(
    hauptfenster,
) -> None:
    # .show() ist hier nötig: QDockWidget.isVisible() spiegelt den
    # tatsächlichen Sichtbarkeitszustand wider, der ohne ein gezeigtes
    # Hauptfenster für alle Kind-Widgets False bliebe.
    hauptfenster.show()
    eintraege = {a.text(): a for a in hauptfenster.menue("Ansicht").actions()}
    for titel, dock in (
        ("Projekt-Explorer", hauptfenster.explorer_dock),
        ("Objektinspektor", hauptfenster.inspektor_dock),
        ("Komponentenpalette", hauptfenster.palette_dock),
        ("Datenbank", hauptfenster.datenbank_dock),
        ("Panels", hauptfenster.panels_dock),
    ):
        if not dock.isVisible():
            eintraege[titel].trigger()
        dock.close()
        assert dock.isVisible() is False, titel

        eintraege[titel].trigger()

        assert dock.isVisible() is True, titel


def test_ansicht_eintrag_ist_angekreuzt_wenn_das_dock_sichtbar_ist(hauptfenster) -> None:
    hauptfenster.show()
    eintrag = next(
        a for a in hauptfenster.menue("Ansicht").actions() if a.text() == "Projekt-Explorer"
    )
    assert eintrag.isChecked() is True

    hauptfenster.explorer_dock.close()

    assert eintrag.isChecked() is False


def test_geschlossenes_dock_bleibt_nach_einem_neustart_der_ide_zu(hauptfenster_bauen) -> None:
    """Gemeldet: „Datenbank soll, wenn es zu
 gemacht wurde, beim nächsten Mal auch zu bleiben. Das Ganze auch bei
 den anderen Feldern.“"""
    fenster = hauptfenster_bauen()
    fenster.show()
    fenster.datenbank_dock.close()

    fenster.close()  # löst closeEvent aus, speichert die Anordnung

    neues_fenster = hauptfenster_bauen()
    neues_fenster.show()

    assert neues_fenster.datenbank_dock.isVisible() is False


def test_layout_zuruecksetzen_ignoriert_die_gespeicherte_anordnung(hauptfenster_bauen) -> None:
    # "Layout zurücksetzen" muss zum echten Ausgangszustand zurückkehren,
    # nicht nur zur zuletzt gespeicherten (sonst gäbe es keinen Ausweg,
    # wenn man sich "verklickt" hat).
    # Beispiel ist der Projekt-Explorer und nicht mehr die Datenbank:
    # die ist seit M11, Abschnitt 4 voreingestellt zu, taugt hier also
    # nicht als „war offen, wurde geschlossen, kommt zurück“.
    fenster = hauptfenster_bauen()
    fenster.show()
    fenster.explorer_dock.close()
    fenster.close()

    neues_fenster = hauptfenster_bauen()
    neues_fenster.show()
    assert neues_fenster.explorer_dock.isVisible() is False

    neues_fenster._layout_zuruecksetzen_aktion()

    assert neues_fenster.explorer_dock.isVisible() is True


def test_konsolenprojekt_laesst_dem_editor_die_halbe_breite(
    hauptfenster, tmp_path, qtbot,  # noqa: ANN001
) -> None:
    """Punkt 348: 853 × 500 logische Pixel sind 1280 × 800 bei 150 %
    ohne Taskleiste. `QT_SCALE_FACTOR` ändert nur die Gerätepixel, die
    Aufteilung in logischen Pixeln bleibt dieselbe. Mit Palette und
    Objektinspektor blieben dem Editor 241 Pixel Breite; beide haben
    im Konsolenprojekt nichts zu tun. Mit dem ersten Formular kommen
    sie wieder."""
    from ide.project.neu import projekt_erzeugen

    projekt = projekt_erzeugen("console", tmp_path / "Rechnen", "Rechnen")
    hauptfenster.resize(853, 500)
    hauptfenster.show()
    hauptfenster.projekt_oeffnen(projekt.ordner / "Rechnen.natter")
    hauptfenster.datei_oeffnen(projekt.ordner / "u_main.py")
    qtbot.wait(50)

    editor = hauptfenster._aktueller_editor()
    assert editor is not None
    assert editor.viewport().width() >= 853 / 2, editor.viewport().width()
    assert not hauptfenster.palette_dock.isVisible()
    assert not hauptfenster.inspektor_dock.isVisible()

    gui = projekt_erzeugen("gui", tmp_path / "Fenster", "Fenster")
    hauptfenster.projekt_oeffnen(gui.ordner / "Fenster.natter")

    assert hauptfenster.palette_dock.isVisible()
    assert hauptfenster.inspektor_dock.isVisible()


def test_verborgene_formular_docks_kommen_nach_neustart_zurueck(
    hauptfenster_bauen, tmp_path,  # noqa: ANN001
) -> None:
    """Die Sichtbarkeit steht im gespeicherten Layout. Endete Natter im
    Konsolenprojekt, fehlten Palette und Objektinspektor sonst auch im
    nächsten GUI-Projekt. Ein Dock, das jemand selbst geschlossen hat,
    bleibt dagegen zu."""
    from ide.project.neu import projekt_erzeugen

    konsole = projekt_erzeugen("console", tmp_path / "Rechnen", "Rechnen")
    gui = projekt_erzeugen("gui", tmp_path / "Fenster", "Fenster")
    fenster = hauptfenster_bauen()
    fenster.show()
    fenster.inspektor_dock.close()
    fenster.projekt_oeffnen(konsole.ordner / "Rechnen.natter")
    fenster.close()

    neues_fenster = hauptfenster_bauen()
    neues_fenster.show()
    assert not neues_fenster.palette_dock.isVisible()
    neues_fenster.projekt_oeffnen(gui.ordner / "Fenster.natter")

    assert neues_fenster.palette_dock.isVisible()
    assert not neues_fenster.inspektor_dock.isVisible()
