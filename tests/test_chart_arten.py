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
    # Deutlich mehr Linienpixel als ohne Gitter - die Schranke liegt
    # bei 1,5 und nicht bei 2, weil das Gitter seit der Korrektur
    # **hinter** den Balken liegt und dort verdeckt wird.
    assert _pixel_in(diagramm, _RAHMENFARBE) > ohne * 1.5


def test_das_gitter_liegt_hinter_den_balken(diagramm: Chart) -> None:
    """Fund aus der Sichtprüfung: ohne `set_axisbelow(True)` zeichnet
    matplotlib das Gitternetz über die Daten – durch jeden Balken lief
    eine helle senkrechte Linie, als wäre er zerschnitten.

    Geprüft wird das an der **Serienfarbe**: liegt das Gitter davor,
    frisst es Balkenpixel weg."""
    voll = _pixel_in(diagramm, _SERIENFARBE)

    diagramm.grid = True

    assert _pixel_in(diagramm, _SERIENFARBE) == voll


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


# -- Aus der Sichtprüfung ------------------------------------------------
#
# Drei Fehler, die alle Tests oben bestanden hatten und erst auf dem
# gerenderten Bild auffielen. Deshalb stehen sie hier eigens.


def test_beschriftungen_bleiben_in_der_figur(diagramm: Chart) -> None:
    """Der erste Fund: an der y-Achse stand „.0“ statt „5.0“, und dem
    Titel fehlte die Oberkante.

    Ursache war `tight_layout()`: es rechnet die Ränder einmalig aus und
    hinterlässt feste Bruchteile. Schrumpft das Widget danach auf die
    320x240 der Komponente, brauchen die gleich groß bleibenden
    Beschriftungen einen größeren Anteil und laufen aus der Figur
    heraus.
    """
    diagramm.kind = "line"
    diagramm.title = "Messwerte über die Woche"
    diagramm.y_label = "Anzahl"
    _gerendert(diagramm)

    figur = diagramm._figure.bbox
    aussen = diagramm._achse.get_tightbbox()

    assert aussen.x0 >= -1, "die y-Beschriftung ragt links aus der Figur"
    assert aussen.y1 <= figur.y1 + 1, "der Titel ragt oben aus der Figur"


def test_vier_werte_bekommen_vier_verschiedene_farben(diagramm: Chart) -> None:
    """Der zweite Fund: die Palette bestand aus den drei Statusfarben,
    ein Kreisdiagramm mit vier Werten hatte deshalb zwei gleich gefärbte
    Stücke direkt nebeneinander."""
    diagramm.add_pie_series(["Mo", "Di", "Mi", "Do"], [3, 5, 2, 4])

    farben = [stueck.get_facecolor() for stueck in diagramm._achse.patches]

    assert len({tuple(f) for f in farben}) == 4


def test_kreisbeschriftung_folgt_dem_theme(formular: _Formular) -> None:
    """Der dritte Fund: die Stücke eines Kreisdiagramms werden nicht
    über die Achsen beschriftet, `tick_params()` erreicht sie also
    nicht – im dunklen Theme standen sie fast schwarz auf dunklem
    Grund."""
    from matplotlib.colors import to_hex

    dunkel = Chart(formular, theme="dark")
    dunkel.kind = "pie"

    beschriftungen = [
        to_hex(text.get_color())
        for text in dunkel._achse.texts
        if text.get_text() in ("Mo", "Di", "Mi", "Do")
    ]

    assert beschriftungen, "das Kreisdiagramm hat gar keine Beschriftung"
    assert set(beschriftungen) == {_theme_farben("dark")["text"].lower()}


def test_geschlossenes_formular_wirft_keinen_traceback(formular: _Formular) -> None:
    """Vierter Fund, beim Testlauf auf der Konsole: ein vorgemerktes
    Neuzeichnen traf auf die schon gelöschte Leinwand und brach mit
    `libshiboken: Internal C++ object ... already deleted` ab. In einem
    Schülerprogramm wäre das ein Traceback beim Schließen des
    Fensters."""
    from shiboken6 import delete

    diagramm = formular.ch_diagramm
    delete(diagramm._qwidget)  # was Qt beim Schließen des Fensters tut

    diagramm.title = "nach dem Schließen"  # darf nichts werfen


def test_kreisdiagramm_bekommt_keine_legende(diagramm: Chart) -> None:
    """Fund aus der Sichtprüfung: die Stücke eines Kreisdiagramms tragen
    ihre Beschriftung schon selbst. Mit Legende standen die Kategorien
    doppelt da, und der Kasten deckte ein Stück samt Beschriftung zu."""
    diagramm.legend = True
    diagramm.add_pie_series(["Mo", "Di", "Mi"], [3, 5, 2], title="Woche")

    assert diagramm._achse.get_legend() is None


def test_ein_saeulendiagramm_bekommt_seine_legende_weiterhin(diagramm: Chart) -> None:
    """Gegenprobe: die Regel gilt nur für den Kreis."""
    diagramm.legend = True
    diagramm.add_bar_series(["Mo", "Di"], [3, 5], title="Woche")

    assert diagramm._achse.get_legend() is not None


def test_langer_titel_wird_umgebrochen_statt_abgeschnitten(diagramm: Chart) -> None:
    """Fund aus der Sichtprüfung: aus „Schuhgröße nach Körpergröße"
    wurde in einem 320 Pixel breiten Diagramm „Schuhgröße nach
    Körpergroes". matplotlib kürzt einen Titel nicht und macht auch
    keinen Platz dafür – es malt ihn über den Rand hinaus, und die Figur
    schneidet ab."""
    diagramm.title = "Zusammenhang zwischen Körpergröße und Schuhgröße"

    gesetzt = diagramm._achse.get_title()

    assert "\n" in gesetzt, "der Titel steht immer noch auf einer Zeile"
    assert gesetzt.replace("\n", " ") == diagramm.title
    assert max(len(zeile) for zeile in gesetzt.splitlines()) < len(diagramm.title)


def test_kurzer_titel_bleibt_einzeilig(diagramm: Chart) -> None:
    """Ein umgebrochener Kurztitel wäre eine verschenkte Zeile."""
    diagramm.title = "Woche"

    assert diagramm._achse.get_title() == "Woche"


def test_der_titel_passt_in_die_figur(diagramm: Chart) -> None:
    """Die eigentliche Prüfung: nicht „es gibt einen Umbruch", sondern
    dass der gemalte Titel wirklich innerhalb der Figur liegt."""
    diagramm.title = "Zusammenhang zwischen Körpergröße und Schuhgröße"
    _gerendert(diagramm)

    rahmen = diagramm._achse.title.get_window_extent()
    assert rahmen.x0 >= -1
    assert rahmen.x1 <= diagramm._figure.bbox.x1 + 1
