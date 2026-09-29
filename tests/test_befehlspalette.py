"""Befehlspalette (Punkt 82): README, Aktionsregister und Kommentare
versprachen sie, gebaut war sie nicht."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from ide.shell.befehlspalette import Befehlspalette
from ide.shell.hauptfenster import HauptFenster


def test_findet_befehle_ueber_teile_des_namens(qtbot) -> None:  # noqa: ANN001
    fenster = HauptFenster()
    palette = Befehlspalette(fenster.aktionen)
    qtbot.addWidget(palette)

    palette.suchfeld.setText("speich")
    assert any("Datei → Speichern" in z for z in palette.gefilterte_zeilen())

    palette.suchfeld.setText("zuklappen alles")
    assert palette.gefilterte_zeilen() == ["Quelltext → Alles zuklappen"]


def test_zeigt_das_tastenkuerzel_auf_deutsch(qtbot) -> None:  # noqa: ANN001
    fenster = HauptFenster()
    palette = Befehlspalette(fenster.aktionen)
    qtbot.addWidget(palette)

    palette.suchfeld.setText("Unit öffnen")

    assert any("Strg+P" in z for z in palette.gefilterte_zeilen())


def test_ausgegraute_befehle_fehlen(qtbot) -> None:  # noqa: ANN001
    fenster = HauptFenster()
    fenster._startaktionen_pruefen()
    palette = Befehlspalette(fenster.aktionen)
    qtbot.addWidget(palette)

    # Einzelschritt ist seit Punkt 295 auch vor dem Start anklickbar.
    palette.suchfeld.setText("Fortsetzen")

    assert palette.gefilterte_zeilen() == []


def test_eingabe_fuehrt_den_befehl_aus(qtbot) -> None:  # noqa: ANN001
    fenster = HauptFenster()
    ausgeloest = []
    fenster.aktionen["hilfe.tastenkuerzel"].qaction.triggered.connect(
        lambda *_: ausgeloest.append(True)
    )
    palette = Befehlspalette(fenster.aktionen)
    qtbot.addWidget(palette)

    palette.suchfeld.setText("Tastenkürzel-Übersicht")
    QTest.keyClick(palette.suchfeld, Qt.Key.Key_Return)

    assert palette.gewaehlte_aktion is fenster.aktionen["hilfe.tastenkuerzel"]
    palette.gewaehlte_aktion.qaction.trigger()
    assert ausgeloest == [True]
