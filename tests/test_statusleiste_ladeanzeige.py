"""Lage der Ladeanzeige in der Statusleiste (Punkt 413).

Bis 0.4.2 bekam der Behälter der Ladeanzeige den ganzen freien Platz
der Leiste: Balken und Text standen in der Mitte, und „Zeile N,
Spalte M“ sprang von rechts in die Mitte, solange ein Programm lud.
"""

from __future__ import annotations


def test_die_ladeanzeige_ist_nur_so_breit_wie_ihr_inhalt(
    hauptfenster, qtbot,  # noqa: ANN001
) -> None:
    fenster = hauptfenster
    fenster.resize(1920, 1000)
    fenster.show()
    qtbot.waitExposed(fenster)
    fenster._cursor_anzeige_aktualisieren()
    fenster.cursor_anzeige.setText("Zeile 8, Spalte 54")
    leiste = fenster.statusBar()
    qtbot.waitUntil(lambda: fenster.cursor_anzeige.x() > 0)
    rechts_vorher = fenster.cursor_anzeige.geometry().right()

    fenster._ladeanzeige_starten(lambda: None, None)
    try:
        anzeige = fenster._lade_anzeige
        qtbot.waitUntil(lambda: anzeige.isVisible() and anzeige.width() > 0)
        qtbot.wait(50)
        assert anzeige.width() <= anzeige.sizeHint().width() + 10, (
            f"Ladeanzeige {anzeige.width()} px breit, "
            f"ihr Inhalt braucht {anzeige.sizeHint().width()} px"
        )
        # Die Anzeige steht rechts in der Leiste, und die Position
        # verschiebt sich höchstens um die Breite der Ladeanzeige.
        assert anzeige.geometry().right() > leiste.width() * 3 // 4
        verschiebung = rechts_vorher - fenster.cursor_anzeige.geometry().right()
        assert verschiebung <= anzeige.width() + 20
    finally:
        fenster._lade_uhr.stop()
