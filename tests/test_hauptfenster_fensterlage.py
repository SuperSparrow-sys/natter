"""Punkt 299: das Hauptfenster öffnet beim ersten Start maximiert,
merkt sich danach Größe, Lage und Maximiert-Zustand und passt mit
seiner Mindesthöhe auf einen Schulrechner mit 150 % Skalierung."""

from __future__ import annotations

import sys

from PySide6.QtCore import QRect, QSettings, Qt
from PySide6.QtGui import QGuiApplication


def _einstellungen() -> QSettings:
    return QSettings(
        QSettings.Format.IniFormat,
        QSettings.Scope.UserScope,
        "Natter",
        "Natter-IDE",
    )


def test_erster_start_maximiert(hauptfenster_bauen, qtbot) -> None:
    fenster = hauptfenster_bauen()

    fenster.fensterlage_herstellen()
    fenster.show()
    qtbot.waitExposed(fenster)

    assert fenster.isMaximized()


def test_maximiert_bleibt_nach_neustart_maximiert(
    hauptfenster_bauen, qtbot
) -> None:
    erstes = hauptfenster_bauen()
    erstes.show()
    qtbot.waitExposed(erstes)
    erstes.showMaximized()
    qtbot.waitUntil(erstes.isMaximized, timeout=3000)
    assert erstes.close()

    zweites = hauptfenster_bauen()
    zweites.fensterlage_herstellen()
    zweites.show()
    qtbot.waitExposed(zweites)

    assert zweites.isMaximized()


def test_normale_groesse_bleibt_nach_neustart(
    hauptfenster_bauen, qtbot
) -> None:
    flaeche = QGuiApplication.primaryScreen().availableGeometry()
    erstes = hauptfenster_bauen()
    erstes.show()
    qtbot.waitExposed(erstes)
    erstes.setGeometry(
        flaeche.x() + 40, flaeche.y() + 50, 700, 500
    )
    groesse = erstes.size()
    assert erstes.close()

    zweites = hauptfenster_bauen()
    zweites.fensterlage_herstellen()
    zweites.show()
    qtbot.waitExposed(zweites)

    assert not zweites.isMaximized()
    assert zweites.size() == groesse


def test_verschwundener_bildschirm_oeffnet_maximiert(
    hauptfenster_bauen, qtbot, monkeypatch
) -> None:
    """Die gemerkte Lage liegt auf einem Bildschirm, den es nicht mehr
    gibt: das Fenster erscheint trotzdem auf dem vorhandenen."""
    erstes = hauptfenster_bauen()
    erstes.show()
    qtbot.waitExposed(erstes)
    assert erstes.close()

    # Qt rückt eine Lage außerhalb des Bildschirms beim Wiederherstellen
    # selbst zurecht. Ob die eigene Prüfung greift, zeigt sich an einer
    # Lage, die ihr als verloren gemeldet wird.
    zweites = hauptfenster_bauen()
    monkeypatch.setattr(
        type(zweites), "normalGeometry",
        lambda self: QRect(20000, 20000, 800, 600),
    )
    zweites.fensterlage_herstellen()

    assert zweites.windowState() & Qt.WindowState.WindowMaximized


def test_geometrie_wird_beim_schliessen_gemerkt(
    hauptfenster_bauen, qtbot
) -> None:
    fenster = hauptfenster_bauen()
    fenster.show()
    qtbot.waitExposed(fenster)
    assert fenster.close()

    assert _einstellungen().value("fenster/geometrie") is not None


def test_mindesthoehe_passt_bei_150_prozent(hauptfenster_bauen) -> None:
    """1366 × 768 bei 150 % sind 910 × 512 Pixel; nach der Taskleiste
    bleiben rund 480 in der Höhe."""
    fenster = hauptfenster_bauen()

    assert fenster.minimumSizeHint().height() < 480

    fenster.datenbank_dock.show()
    assert fenster.minimumSizeHint().height() < 480


def test_start_stellt_die_fensterlage_her(monkeypatch) -> None:
    """`ide/main.py` ruft `fensterlage_herstellen` vor dem Zeigen auf."""
    import ide.main as modul

    class _Anzeige:
        def __init__(self, version: str) -> None:
            pass

        def show(self) -> None:
            pass

        def melden(self, text: str) -> None:
            pass

        def finish(self, fenster: object) -> None:
            pass

        def close(self) -> None:
            pass

    monkeypatch.setattr(modul, "Ladeanzeige", _Anzeige)
    monkeypatch.setattr(modul, "integritaet_bestaetigen", lambda f: True)
    monkeypatch.setattr(modul, "fehlerhaken_einrichten", lambda: None)
    monkeypatch.setattr(sys, "argv", ["Natter.exe"])

    _app, fenster = modul.starten()
    try:
        assert fenster is not None
        assert fenster.isMaximized()
    finally:
        if fenster is not None:
            fenster.close()
