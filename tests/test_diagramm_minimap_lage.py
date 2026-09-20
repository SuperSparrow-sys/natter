"""Die Minimap bleibt in ihrer Ecke.

Punkt 9 der offenen Punkte. Nach einem Neustart stand sie an der
falschen Stelle - ein weißer Kasten mitten auf der Zeichenfläche, über
dem Lineal.

Zwei Ursachen. Sie hing am Rollbereich, wurde aber nach den Maßen des
Viewports verschoben; ein `move()` gilt aber im Koordinatensystem des
Elternteils, und die beiden unterscheiden sich um die Rahmenbreite.
Und `_minimap_einpassen()` lief nur beim Rollen und beim Zoomen, nicht
beim Ändern der Fenstergröße - nach einem Neustart mit anderer Größe
saß sie also dort, wo sie beim letzten Mal gerechnet worden war.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.fenster import MINIMAP_RAND


@pytest.fixture
def fenster(tmp_path: Path, qtbot) -> DiagrammFenster:
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "probe.pdiag", "probe"))
    qtbot.addWidget(fenster)
    fenster.resize(1000, 700)
    fenster.show()
    return fenster


def _in_der_ecke(fenster: DiagrammFenster) -> bool:
    """Sitzt die Minimap unten rechts im sichtbaren Bereich?

    Genau gerechnet und nicht überschlagen: „linke Kante hinter der
    Mitte" wäre bei einem schmalen Viewport falsch, weil die Minimap
    dort mehr als die halbe Breite einnimmt. Gemeint ist der Abstand
    zur rechten und zur unteren Kante.
    """
    sicht = fenster.rollbereich.viewport()
    lage = fenster.minimap.geometry()
    return (
        sicht.width() - lage.right() - 1 == MINIMAP_RAND
        and sicht.height() - lage.bottom() - 1 == MINIMAP_RAND
    )


def test_die_minimap_haengt_am_viewport(fenster: DiagrammFenster) -> None:
    """Sonst rechnet `move()` in einem anderen Koordinatensystem als
    `_minimap_einpassen()`."""
    assert fenster.minimap.parent() is fenster.rollbereich.viewport()


def test_die_minimap_sitzt_in_der_ecke(fenster: DiagrammFenster, qtbot) -> None:
    fenster._minimap_an = True
    fenster.minimap.show()
    fenster._minimap_einpassen()
    qtbot.wait(20)

    assert _in_der_ecke(fenster)


def test_sie_bleibt_dort_wenn_das_fenster_kleiner_wird(
    fenster: DiagrammFenster, qtbot
) -> None:
    """Der eigentliche Fehler: ohne diese Nachführung blieb sie
    stehen, wo sie beim letzten Rollen berechnet worden war."""
    fenster._minimap_an = True
    fenster.minimap.show()
    fenster._minimap_einpassen()

    fenster.resize(800, 600)
    qtbot.wait(50)

    assert _in_der_ecke(fenster), (
        f"Minimap bei {fenster.minimap.geometry()}, Viewport "
        f"{fenster.rollbereich.viewport().size()}"
    )


def test_bei_zu_kleinem_fenster_verschwindet_sie(
    fenster: DiagrammFenster, qtbot
) -> None:
    """Sonst ragte sie links über den Rand hinaus - ein weißer Kasten
    quer über dem Lineal. Und eine Übersichtskarte, die den halben
    Ausschnitt verdeckt, hilft ohnehin niemandem."""
    fenster._minimap_an = True
    fenster.minimap.show()
    fenster._minimap_einpassen()
    assert fenster.minimap.isVisible()

    fenster.resize(200, 200)
    qtbot.wait(50)

    assert not fenster.minimap.isVisible()


def test_sie_bleibt_dort_wenn_das_fenster_groesser_wird(
    fenster: DiagrammFenster, qtbot
) -> None:
    fenster._minimap_an = True
    fenster.minimap.show()
    fenster._minimap_einpassen()

    fenster.resize(1400, 1000)
    qtbot.wait(50)

    assert _in_der_ecke(fenster)


def test_sie_ragt_nie_ueber_den_sichtbaren_bereich_hinaus(
    fenster: DiagrammFenster, qtbot
) -> None:
    """Ein Kasten, der halb über dem Rand liegt, verdeckt das Lineal."""
    fenster.minimap.show()

    fenster._minimap_an = True
    for breite, hoehe in ((1200, 800), (700, 500), (1600, 1100), (500, 400)):
        fenster.resize(breite, hoehe)
        qtbot.wait(30)
        sicht = fenster.rollbereich.viewport()
        if not fenster.minimap.isVisible():
            continue  # passt nicht hin, also ausgeblendet
        lage = fenster.minimap.geometry()
        assert lage.left() >= 0 and lage.top() >= 0, f"{breite}x{hoehe}: {lage}"
        assert lage.right() <= sicht.width(), f"{breite}x{hoehe}: {lage}"
        assert lage.bottom() <= sicht.height(), f"{breite}x{hoehe}: {lage}"
