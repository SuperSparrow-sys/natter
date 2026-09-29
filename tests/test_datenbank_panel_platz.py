"""Punkt 303: das Datenbank-Panel auf einem Beamer mit 1280 × 800.

Neben den Panels bekam es 486 × 300 Pixel. Die Ergebnistabelle zeigte
eine einzige Zeile, der Tabellenbaum schnitt „schueler“ auf „schuel…“
ab, und die Rückmeldung zur Abfrage stand rechts oben neben
„Trennen“."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from ide.project import projekt_erzeugen

#: 1280 × 800 abzüglich Taskleiste und Titelleiste des maximierten
#: Fensters.
BREITE = 1280
HOEHE = 725


def _abfrage(panel, qtbot, sql: str) -> None:  # noqa: ANN001
    panel._sql_eingabe.setPlainText(sql)
    panel._sql_ausfuehren()
    qtbot.waitUntil(lambda: not panel.laeuft, timeout=5000)


def test_fuenf_zeilen_und_volle_namen(
    hauptfenster_bauen, qtbot, tmp_path: Path, monkeypatch
) -> None:
    projekt = projekt_erzeugen("gui", tmp_path / "Schule", "Schule")
    fenster = hauptfenster_bauen()
    fenster.resize(BREITE, HOEHE)
    fenster.show()
    qtbot.waitExposed(fenster)
    fenster.projekt_oeffnen(projekt.ordner / "Schule.natter")
    fenster.designer_oeffnen(projekt.ordner / "u_main.pfm")

    fenster.datenbank_dock.toggleViewAction().trigger()
    QApplication.processEvents()
    assert fenster.datenbank_dock.isVisible()
    assert fenster.datenbank_dock.width() >= BREITE - 20

    panel = fenster.datenbank_panel
    monkeypatch.setattr(panel, "_datei_anlegen_fragen", lambda pfad: True)
    panel._sqlite_pfad.setText("schule.sqlite")
    panel._verbinden()
    _abfrage(
        panel, qtbot,
        "CREATE TABLE schueler (id INTEGER PRIMARY KEY, name TEXT, "
        "note INTEGER, geburtsdatum TEXT)",
    )
    _abfrage(
        panel, qtbot,
        "INSERT INTO schueler (name, note, geburtsdatum) VALUES "
        "('Anna', 1, '2011-03-04'), ('Ben', 2, '2011-05-06'), "
        "('Cem', 3, '2010-12-01'), ('Dora', 2, '2011-07-08'), "
        "('Emil', 1, '2011-01-02'), ('Fritz', 4, '2010-09-10')",
    )
    _abfrage(panel, qtbot, "SELECT * FROM schueler")
    QApplication.processEvents()

    tabelle = panel.ergebnis_tabelle
    assert tabelle.rowCount() == 6
    hoehe = tabelle.viewport().height()
    ganz_sichtbar = [
        zeile
        for zeile in range(tabelle.rowCount())
        if 0 <= tabelle.rowViewportPosition(zeile)
        and tabelle.rowViewportPosition(zeile) + tabelle.rowHeight(zeile)
        <= hoehe
    ]
    assert len(ganz_sichtbar) >= 5

    kopf = tabelle.horizontalHeader()
    for spalte in range(tabelle.columnCount()):
        name = tabelle.horizontalHeaderItem(spalte).text()
        assert kopf.sectionSize(spalte) >= (
            kopf.fontMetrics().horizontalAdvance(name) + 12
        ), name

    baum = panel.tabellenbaum
    metrik = baum.fontMetrics()
    assert baum.width() >= metrik.horizontalAdvance("Tabellen/Spalten") + 24
    eintrag = baum.topLevelItem(0)
    for kind in [eintrag] + [eintrag.child(i) for i in range(eintrag.childCount())]:
        rechts = baum.visualItemRect(kind).left() + metrik.horizontalAdvance(
            kind.text(0)
        )
        assert rechts <= baum.viewport().width(), kind.text(0)

    # Die Rückmeldung steht zwischen SQL-Feld und Ergebnistabelle.
    status = panel._status_label
    assert "6 Zeilen" in status.text()
    oben = status.mapTo(panel, status.rect().topLeft()).y()
    sql_unten = panel._sql_eingabe.mapTo(
        panel, panel._sql_eingabe.rect().bottomLeft()
    ).y()
    tabelle_oben = tabelle.mapTo(panel, tabelle.rect().topLeft()).y()
    assert sql_unten <= oben <= tabelle_oben

    panel.trennen()


def test_datenbank_liegt_als_reiter_bei_den_panels(
    hauptfenster_bauen, qtbot
) -> None:
    fenster = hauptfenster_bauen()
    fenster.show()
    qtbot.waitExposed(fenster)
    fenster.datenbank_dock.toggleViewAction().trigger()

    assert fenster.datenbank_dock in fenster.tabifiedDockWidgets(
        fenster.panels_dock
    )
