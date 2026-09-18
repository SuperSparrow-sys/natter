"""Tests für die Diagrammarten und die Designer-Vorschau der
Chart-Komponente (M10, Punkt 1 und 2). Headless, gegen echtes matplotlib.

Die Pixelprüfung (`_gemalte_farben`, wie in
tests/test_diagramm_stilvorlagen.py) ist hier der Kern: ob eine
Diagrammart wirklich etwas Sichtbares ergibt, zeigt erst das gerenderte
Bild. Ein gefülltes `ax.patches`/`ax.lines` beweist das nicht – ein
Boxplot etwa hat auch dann Linien im Objektbaum, wenn sie in der Farbe
des Hintergrunds gezeichnet werden.
"""

from __future__ import annotations

import pytest
from PySide6.QtGui import QImage

from ide.assets import symbol
from pcl import Chart, Form
from pcl.components.chart import _ARTEN, _farbpalette, _theme_farben

# Farbe der ersten Serie bzw. Rahmenfarbe im Standard-Theme der Tests.
_SERIENFARBE = _farbpalette("system")[0]
_RAHMENFARBE = _theme_farben("system")["border"]
_TEXTFARBE = _theme_farben("system")["text"]


class _Formular(Form):
    def create_components(self) -> None:
        self.ch_diagramm = Chart(self)


@pytest.fixture
def formular() -> _Formular:
    # Das Formular muss am Leben bleiben: fällt die letzte Referenz weg,
    # räumt Python es weg und Qt löscht das QWidget des Diagramms mit.
    return _Formular()


@pytest.fixture
def diagramm(formular: _Formular) -> Chart:
    return formular.ch_diagramm


def _gerendert(diagramm: Chart) -> QImage:
    widget = diagramm._qwidget
    widget.resize(diagramm.width, diagramm.height)
    diagramm._figure.canvas.draw()
    return widget.grab().toImage()


def _gemalte_farben(diagramm: Chart) -> set[str]:
    """Rendert das Diagramm wirklich und gibt die vorkommenden Farben
    zurück."""
    bild = _gerendert(diagramm)
    return {
        bild.pixelColor(x, y).name()
        for x in range(0, bild.width(), 2)
        for y in range(0, bild.height(), 2)
    }


def _pixel_in(diagramm: Chart, farbe: str) -> int:
    """Wie viele Pixel genau diese Farbe tragen. Zählen statt nur
    Vergleichen, weil sich die Farbmenge zweier Renderdurchgänge schon
    durch minimal verschobene Beschriftungen (Kantenglättung) unter-
    scheidet – ein `!=` darauf wäre immer erfüllt und würde nichts
    prüfen."""
    bild = _gerendert(diagramm)
    return sum(
        bild.pixelColor(x, y).name() == farbe
        for x in range(bild.width())
        for y in range(bild.height())
    )


# -- Symbol --------------------------------------------------------------


def test_symbol_wird_gefunden_und_gerendert() -> None:
    # War bei anderen Komponenten real schon kaputt (M8): ein Tippfehler
    # im Dateinamen liefert nur ein leeres QIcon statt eines Fehlers.
    icon = symbol("komponente_chart")
    assert not icon.isNull()
    assert not icon.pixmap(22, 22).isNull()
    assert not icon.pixmap(22, 22).toImage().allGray()


# -- Diagrammarten -------------------------------------------------------


@pytest.mark.parametrize("art", _ARTEN)
def test_jede_diagrammart_zeichnet_sichtbar(art: str, diagramm: Chart) -> None:
    diagramm.kind = art

    farben = _gemalte_farben(diagramm)

    assert len(farben) > 1, f"{art} malt nur eine einzige Farbe"
    assert _SERIENFARBE in farben, f"{art} malt nur Achsen, keine Daten"


def test_ohne_daten_fehlt_die_serienfarbe(diagramm: Chart) -> None:
    """Gegenprobe zum Test darüber: Achsen, Ticks und Beschriftungen
    allein ergeben schon über 200 verschiedene Farben – „mehr als eine
    Farbe“ wäre also auch bei einem leeren Diagramm erfüllt. Erst die
    Serienfarbe zeigt, dass wirklich Daten gezeichnet wurden."""
    diagramm.clear()

    farben = _gemalte_farben(diagramm)

    assert len(farben) > 1
    assert _SERIENFARBE not in farben


def test_unbekannte_art_faellt_auf_saeulen_zurueck(diagramm: Chart) -> None:
    # Wie `Shape.shape`: ein Tippfehler zeichnet die Vorgabe, statt die
    # Anzeige mit einem Fehler abzubrechen.
    diagramm.kind = "bar"
    saeulen = len(diagramm._achse.containers[0])

    diagramm.kind = "gibt_es_nicht"

    assert len(diagramm._achse.containers[0]) == saeulen
    assert len(_gemalte_farben(diagramm)) > 1


def test_histogram_zaehlt_die_werte_selbst(diagramm: Chart) -> None:
    diagramm.add_histogram_series([1, 1, 1, 5, 5, 9], bins=3)

    hoehen = [balken.get_height() for balken in diagramm._achse.patches]
    assert hoehen == [3, 2, 1]


def test_boxplot_zeichnet_kasten_und_median(diagramm: Chart) -> None:
    diagramm.add_boxplot_series([1, 2, 3, 4, 5, 6, 7, 8])

    # Kasten, zwei Antennen, zwei Abschlüsse, Median, Ausreißer.
    assert len(diagramm._achse.lines) == 7


# -- Beispieldaten im Designer -------------------------------------------


def test_frisches_diagramm_zeigt_beispieldaten(diagramm: Chart) -> None:
    # Ohne das stünde im Designer ein leeres graues Rechteck.
    assert diagramm._achse.patches


def test_echte_daten_ersetzen_die_beispieldaten(diagramm: Chart) -> None:
    diagramm.add_bar_series(["A", "B"], [1, 2])

    assert len(diagramm._achse.patches) == 2


def test_kind_aendert_bereits_gezeichnete_daten_nicht(diagramm: Chart) -> None:
    diagramm.add_bar_series(["A", "B"], [1, 2])

    diagramm.kind = "pie"

    assert len(diagramm._achse.patches) == 2


def test_clear_zeigt_keine_beispieldaten_mehr(diagramm: Chart) -> None:
    diagramm.add_bar_series(["A", "B"], [1, 2])

    diagramm.clear()

    assert not diagramm._achse.patches


# -- Beschriftungs-Props -------------------------------------------------


def test_title_wirkt_sofort(diagramm: Chart) -> None:
    diagramm.title = "Umsatz je Wochentag"

    assert diagramm._achse.get_title() == "Umsatz je Wochentag"


def test_achsenbeschriftungen_wirken_sofort(diagramm: Chart) -> None:
    diagramm.x_label = "Tag"
    diagramm.y_label = "Euro"

    assert diagramm._achse.get_xlabel() == "Tag"
    assert diagramm._achse.get_ylabel() == "Euro"


def test_grid_wirkt_sofort_und_sichtbar(diagramm: Chart) -> None:
    ohne = _pixel_in(diagramm, _RAHMENFARBE)

    diagramm.grid = True

    assert diagramm._achse.xaxis.get_gridlines()[0].get_visible()
    assert _pixel_in(diagramm, _RAHMENFARBE) > ohne * 2


def test_legend_wirkt_sofort_und_sichtbar(diagramm: Chart) -> None:
    ohne = _pixel_in(diagramm, _TEXTFARBE)

    diagramm.legend = True

    assert diagramm._achse.get_legend() is not None
    # Der Legendentext ist wirklich im Bild, nicht nur im Objektbaum.
    assert _pixel_in(diagramm, _TEXTFARBE) > ohne


def test_legend_laesst_sich_wieder_abschalten(diagramm: Chart) -> None:
    diagramm.legend = True

    diagramm.legend = False

    assert diagramm._achse.get_legend() is None


def test_legend_ohne_beschriftete_serie_bleibt_leer(diagramm: Chart) -> None:
    # Ein `add_*_series`-Aufruf ohne `title` darf keine leere Zeile in
    # der Legende erzeugen (matplotlib warnt hier sonst).
    diagramm.add_bar_series(["A"], [1])

    diagramm.legend = True

    assert diagramm._achse.get_legend() is None


def test_serientitel_gilt_weiter_wenn_der_prop_leer_ist(diagramm: Chart) -> None:
    diagramm.add_bar_series(["A"], [1], title="Aus dem Aufruf")

    assert diagramm._achse.get_title() == "Aus dem Aufruf"


def test_prop_titel_sticht_den_serientitel(diagramm: Chart) -> None:
    diagramm.title = "Aus dem Inspektor"

    diagramm.add_bar_series(["A"], [1], title="Aus dem Aufruf")

    assert diagramm._achse.get_title() == "Aus dem Inspektor"


# -- Standardgröße -------------------------------------------------------


def test_standardgroesse_ist_groesser_als_ein_knopf(diagramm: Chart) -> None:
    assert (diagramm.width, diagramm.height) == (320, 240)
