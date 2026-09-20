"""Tests für ide/diagramm/fenster.py: eigenes Diagramm-Fenster
(M9, Schritt 1). Headless.

Abschnitt 13.1 verlangt ausdrücklich ein eigenes Fenster mit eigenem
Taskleisten-Eintrag statt eines Docks/Tabs in der IDE - der Test dafür
prüft, dass das Fenster kein Elternfenster hat (nur elternlose
Top-Level-Fenster bekommen unter Windows einen eigenen Eintrag).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QDockWidget, QStyle, QStyleOptionDockWidget

from ide.diagramm import Diagramm, DiagrammFenster, diagramm_erzeugen
from ide.diagramm.fenster import DOCK_MINDESTBREITE


def _fenster(tmp_path: Path, typ: str = "class") -> DiagrammFenster:
    return DiagrammFenster(diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", "Testdiagramm"))


def test_fenster_ist_ein_eigenstaendiges_top_level_fenster(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)

    assert fenster.parent() is None
    assert fenster.isWindow() is True


def test_titel_nennt_datei_und_editor(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)

    assert fenster.windowTitle() == "class.pdiag – Diagramm-Editor – Natter"


def test_alle_menues_aus_dem_konzept_sind_vorhanden(tmp_path: Path) -> None:
    """Abschnitt 13.2 listet sechs Menüs - sie werden vollständig
    angelegt, auch wenn die meisten Einträge erst später aktiv werden."""
    fenster = _fenster(tmp_path)

    for erwartet in ("Datei", "Bearbeiten", "Ansicht", "Anordnen", "Format", "Hilfe"):
        assert fenster.menue(erwartet).title() == erwartet


def test_noch_nicht_umgesetzte_eintraege_sind_ausgegraut(tmp_path: Path) -> None:
    """Ehrlicher Zwischenstand: was noch nicht geht, ist sichtbar
    deaktiviert statt so zu tun, als täte es etwas."""
    fenster = _fenster(tmp_path)

    assert fenster.aktionen["Datei/Speichern"].isEnabled() is True
    assert fenster.aktionen["Bearbeiten/Rückgängig"].isEnabled() is True
    # Gruppieren und Kopieren können seit Teilschritt 3b wirklich etwas
    # und sind deshalb aktiv; ausgegraut bleibt, was noch fehlt.
    assert fenster.aktionen["Anordnen/Gruppieren"].isEnabled() is True
    assert fenster.aktionen["Bearbeiten/Kopieren"].isEnabled() is True
    # Seit M15, Abschnitt 5 sind auch „Lineale", „Hilfslinien" und
    # „Minimap" da - das waren die letzten drei ausgegrauten Einträge im
    # Menü „Ansicht". Hier standen sie bis dahin als Beleg dafür, dass
    # ein noch nicht Umgesetztes sichtbar deaktiviert ist statt so zu
    # tun, als täte es etwas.
    for eintrag in ("Lineale", "Hilfslinien", "Minimap"):
        assert fenster.aktionen[f"Ansicht/{eintrag}"].isEnabled() is True
    # „Füllung …“ stand hier einmal als Beispiel für „noch nicht da“.
    # Seit M11, Abschnitt 5 führt der Eintrag in den
    # Eigenschaften-Bereich, der das längst kann.
    assert fenster.aktionen["Format/Füllung …"].isEnabled() is True


def test_bearbeiten_menue_wirkt_auf_die_zeichenflaeche(tmp_path: Path) -> None:
    """Die Menüeinträge müssen dasselbe tun wie die Tastenkürzel auf der
    Fläche – sonst hängt das Menü nur dekorativ daneben."""
    fenster = _fenster(tmp_path, "class")
    fenster.zeichenflaeche.form_platzieren("class", 200, 200)

    fenster.aktionen["Bearbeiten/Duplizieren"].trigger()
    assert len(fenster.zeichenflaeche.formen) == 2

    fenster.aktionen["Bearbeiten/Rückgängig"].trigger()
    assert len(fenster.zeichenflaeche.formen) == 1

    fenster.aktionen["Bearbeiten/Wiederholen"].trigger()
    assert len(fenster.zeichenflaeche.formen) == 2

    fenster.aktionen["Bearbeiten/Löschen"].trigger()
    assert len(fenster.zeichenflaeche.formen) == 1


def test_statusleiste_zeigt_seitenformat_und_stil(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)

    meldung = fenster.statusBar().currentMessage()
    assert "A4 quer" in meldung
    assert "modern-light" in meldung


def test_struktogramm_fenster_zeigt_hochformat(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path, "struktogramm")

    assert "A4 hoch" in fenster.statusBar().currentMessage()


def test_speichern_schreibt_aenderungen_auf_die_platte(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)
    fenster.diagramm.daten["shapes"].append(
        {"id": "s1", "kind": "class", "x": 8, "y": 8, "w": 100, "h": 60}
    )

    fenster.speichern()

    assert Diagramm.laden(tmp_path / "class.pdiag").daten["shapes"][0]["id"] == "s1"


def test_klassendiagramm_hat_eine_formen_palette(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path, "class")

    assert fenster.palette is not None
    assert fenster.palette_dock.windowTitle() == "Formen"


def test_struktogramm_hat_keine_formen_palette(tmp_path: Path) -> None:
    """Struktogramme arbeiten mit einem Blockbaum, nicht mit frei
    platzierten Formen (Abschnitt 13.5) – eine Formen-Palette wäre dort
    irreführend. Seit Schritt 9 steht dort stattdessen die
    Blockpalette."""
    from ide.diagramm.struktogramm_palette import BlockPalette

    fenster = _fenster(tmp_path, "struktogramm")

    assert isinstance(fenster.palette, BlockPalette)
    assert fenster.palette_dock.windowTitle() == "Blöcke"


def test_palettenklick_macht_die_form_auf_der_flaeche_scharf(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path, "class")

    fenster.palette.form_gewaehlt.emit("interface")

    assert fenster.zeichenflaeche._platzierungs_kind == "interface"


def test_statusleiste_zaehlt_formen_und_zeigt_die_auswahl(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path, "class")

    fenster.zeichenflaeche.form_platzieren("class", 200, 200)
    assert "Klasse ausgewählt" in fenster.statusBar().currentMessage()

    fenster.zeichenflaeche.auswahl_aufheben()
    fenster._statusleiste_aktualisieren()
    # Eine Form, nicht „1 Formen".
    assert "1 Form  │" in fenster.statusBar().currentMessage()

    fenster.zeichenflaeche.form_platzieren("class", 400, 200)
    fenster.zeichenflaeche.auswahl_aufheben()
    fenster._statusleiste_aktualisieren()
    assert "2 Formen" in fenster.statusBar().currentMessage()


def test_aenderung_markiert_den_titel_und_speichern_raeumt_ihn_wieder_ab(
    tmp_path: Path,
) -> None:
    fenster = _fenster(tmp_path, "class")

    fenster.zeichenflaeche.form_platzieren("class", 200, 200)
    assert fenster.windowTitle().startswith("*")

    fenster.speichern()
    assert not fenster.windowTitle().startswith("*")


def test_speichern_unter_wechselt_pfad_und_titel(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path)
    ziel = tmp_path / "kopie.pdiag"

    fenster.speichern_unter(ziel)

    assert ziel.exists()
    assert fenster.diagramm.pfad == ziel
    assert fenster.windowTitle().startswith("kopie.pdiag")


def test_fuellung_linie_und_schrift_fuehren_in_den_eigenschaften_bereich(
    tmp_path: Path, monkeypatch
) -> None:
    """Die drei Format-Einträge waren ausgegraut, weil es sie noch nicht
    gab – der Eigenschaften-Bereich rechts kann das inzwischen. Sie
    benutzen bewusst dieselben Bedienelemente und keinen zweiten, eigenen
    Dialog (M11, Abschnitt 5)."""
    fenster = _fenster(tmp_path, "class")
    form = fenster.zeichenflaeche.form_platzieren("class", 40, 40)
    fenster.zeichenflaeche.ausgewaehlte_form = form

    geklickt: list[str] = []
    monkeypatch.setattr(
        fenster.eigenschaften.fuellung, "click", lambda: geklickt.append("fuellung")
    )
    monkeypatch.setattr(
        fenster.eigenschaften.linie, "click", lambda: geklickt.append("linie")
    )

    fenster.aktionen["Format/Füllung …"].trigger()
    fenster.aktionen["Format/Linie …"].trigger()
    fenster.aktionen["Format/Schrift …"].trigger()

    assert geklickt == ["fuellung", "linie"]
    # `hasFocus()` braucht ein aktives Fenster, das es hier nicht gibt;
    # `focusWidget()` sagt dasselbe innerhalb des Bereichs.
    assert fenster.eigenschaften.focusWidget() is fenster.eigenschaften.schrift


def test_ohne_ausgewaehlte_form_sagt_der_eintrag_was_fehlt(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path, "class")

    fenster.aktionen["Format/Füllung …"].trigger()

    assert "Keine Form ausgewählt" in fenster.statusBar().currentMessage()


# ------------------------------- Punkt 9: die Bereiche bleiben lesbar
#
# Auf dem Bildschirmfoto vom 20. September war der Eigenschaften-
# Bereich auf 106 Pixel zusammengedrückt und sein Titel zu „Eigen…"
# gekürzt; in der Palette traf es die Überschriften („…endiagramm"
# statt „Klassendiagramm"). Qt verteilt die Breite nach dem
# Platzbedarf des Inhalts, und der ist bei einem leeren
# Eigenschaften-Bereich klein.

def _mit_echter_schrift(fenster: DiagrammFenster) -> DiagrammFenster:
    """Ohne konkrete Schriftart greift unter `offscreen` eine
    Ersatzschrift mit anderen Buchstabenbreiten (siehe AGENTS.md,
    Abschnitt „Tests"). Für eine Messung, die etwas über den echten
    Bildschirm aussagt, muss die Schrift dieselbe sein. Sie wird nur
    auf dieses Fenster gesetzt und nicht auf die Anwendung, damit die
    übrigen Tests davon nichts merken.
    """
    fenster.setFont(QFont("Segoe UI", 9))
    return fenster


def _docks(fenster: DiagrammFenster) -> list[QDockWidget]:
    return [d for d in fenster.findChildren(QDockWidget) if d.isVisible()]


def _platz_fuer_den_titel(dock: QDockWidget) -> int:
    """Das Rechteck, in das Qt den Titeltext zeichnet.

    Nicht geschätzt, sondern beim Stil erfragt - sonst rechnete der
    Test nur die Formel nach, die er prüfen soll. Passt der Text
    nicht hinein, kürzt Qt ihn mit drei Punkten. `minimumSizeHint()`
    taugt dafür nicht: der plant das Kürzen bereits ein und meldete
    für einen 86 Pixel breiten Titel 66 Pixel als Untergrenze.
    """
    option = QStyleOptionDockWidget()
    option.initFrom(dock)
    option.rect = dock.rect()
    option.title = dock.windowTitle()
    merkmale = dock.features()
    option.closable = bool(merkmale & QDockWidget.DockWidgetFeature.DockWidgetClosable)
    option.floatable = bool(merkmale & QDockWidget.DockWidgetFeature.DockWidgetFloatable)
    feld = dock.style().subElementRect(
        QStyle.SubElement.SE_DockWidgetTitleBarText, option, dock
    )
    return feld.width()


def test_jeder_seitenbereich_hat_eine_mindestbreite(tmp_path: Path, qtbot) -> None:
    fenster = _fenster(tmp_path, "class")
    qtbot.addWidget(fenster)

    for dock in (fenster.palette_dock, fenster.eigenschaften_dock):
        assert dock is not None
        assert dock.widget().minimumWidth() >= DOCK_MINDESTBREITE, dock.windowTitle()


def test_ein_schmal_gezogener_bereich_bleibt_lesbar(tmp_path: Path, qtbot) -> None:
    """Der Fehler, wie er zu sehen war: aus „Eigenschaften" wurde
    „Eigen…".

    Ausgelöst wird er, indem der Trenner zwischen den Bereichen nach
    außen gezogen wird - Qt gibt dem einen Bereich dann alles, was
    der andere nicht selbst beansprucht. Genau dagegen steht die
    Mindestbreite.
    """
    fenster = _mit_echter_schrift(_fenster(tmp_path, "class"))
    qtbot.addWidget(fenster)
    fenster.resize(900, 600)
    fenster.show()
    qtbot.wait(30)

    fenster.resizeDocks([fenster.eigenschaften_dock], [40], Qt.Orientation.Horizontal)
    qtbot.wait(30)

    dock = fenster.eigenschaften_dock
    titel = dock.windowTitle()
    gebraucht = dock.fontMetrics().horizontalAdvance(titel)
    assert _platz_fuer_den_titel(dock) >= gebraucht, (
        f"{titel!r} braucht {gebraucht} px, das Textfeld ist nur "
        f"{_platz_fuer_den_titel(dock)} px breit - Qt kürzt ihn dann "
        f"mit drei Punkten."
    )


def test_die_bereiche_ueberdecken_einander_nicht(tmp_path: Path, qtbot) -> None:
    fenster = _fenster(tmp_path, "class")
    qtbot.addWidget(fenster)
    fenster.resize(900, 600)
    fenster.show()

    bereiche = [(d.windowTitle(), d.geometry()) for d in _docks(fenster)]
    bereiche.append(("Mitte", fenster.centralWidget().geometry()))
    for i, (titel_a, a) in enumerate(bereiche):
        for titel_b, b in bereiche[i + 1 :]:
            assert not a.intersects(b), f"{titel_a} überdeckt {titel_b}"


def test_auch_ein_struktogramm_bleibt_lesbar(tmp_path: Path, qtbot) -> None:
    """Der Blockbaum hat einen anderen Palettentitel („Blöcke") und
    gar keinen Eigenschaften-Bereich."""
    fenster = _mit_echter_schrift(_fenster(tmp_path, "struktogramm"))
    qtbot.addWidget(fenster)
    fenster.resize(900, 600)
    fenster.show()

    assert fenster.palette_dock is not None
    assert fenster.palette_dock.widget().minimumWidth() >= DOCK_MINDESTBREITE
    for dock in _docks(fenster):
        breite = dock.fontMetrics().horizontalAdvance(dock.windowTitle())
        assert _platz_fuer_den_titel(dock) > breite, dock.windowTitle()
