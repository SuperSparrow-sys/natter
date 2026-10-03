"""Achsen mit Dezimalkomma, `add_regression()` über die Punkte im
Diagramm (Punkt 127)."""

import pytest

from pcl import Chart, Form
from pcl.errors import NatterDatenError


def _beschriftungen(achse) -> list[str]:
    return [text.get_text() for text in achse.get_ticklabels()]


def test_die_achsen_zeigen_0_5_mit_komma() -> None:
    diagramm = Chart(Form())
    diagramm.add_line_series([0, 0.5, 1, 1.5], [0, 0.25, 0.5, 0.75])
    # Wo matplotlib seine Striche setzt, hängt von der Größe ab. Die
    # Stellen hier fest, damit der Test den Formatter prüft.
    diagramm._achse.set_xticks([0, 0.5, 1, 1.5])
    diagramm._figure.canvas.draw()

    x_texte = _beschriftungen(diagramm._achse.xaxis)
    y_texte = _beschriftungen(diagramm._achse.yaxis)
    assert "0,5" in x_texte
    assert not any("." in text for text in x_texte + y_texte)


@pytest.mark.parametrize("nach_clear", [False, True])
def test_kategorien_bleiben_beschriftet(nach_clear: bool) -> None:
    """Auch nach `clear()`: dort stand bis 0.4.3 unter den Monaten
    der Wetterdaten aus Beispiel 07 die Zählung 0, 1, 2."""
    diagramm = Chart(Form())
    if nach_clear:
        diagramm.add_line_series([1, 2], [3, 4])
        diagramm.clear()
    diagramm.add_bar_series(["Mo", "Di"], [1.5, 2.5])
    diagramm._figure.canvas.draw()

    assert _beschriftungen(diagramm._achse.xaxis) == ["Mo", "Di"]
    assert any("," in text for text in _beschriftungen(diagramm._achse.yaxis))


def test_add_regression_ohne_argumente_nimmt_die_punkte_der_letzten_serie() -> None:
    diagramm = Chart(Form())
    diagramm.add_scatter_series([1, 2, 3, 4], [2.1, 3.9, 6.2, 7.8])
    ergebnis = diagramm.add_regression()
    assert ergebnis.steigung == pytest.approx(1.94, abs=0.01)


def test_add_regression_auf_leerem_diagramm_meldet_sich() -> None:
    diagramm = Chart(Form())
    diagramm.clear()
    with pytest.raises(NatterDatenError, match="add_scatter_series"):
        diagramm.add_regression()


def test_csv_in_cp1252_mit_komma_in_x_ergibt_eine_regression(tmp_path) -> None:
    """Punkte 572 und 576: eine CSV in der Windows-Kodierung endete in
    einem UnicodeDecodeError, und eine x-Spalte mit Dezimalkomma blieb
    Text, sodass add_regression() scheiterte."""
    datei = tmp_path / "versuch.csv"
    zeilen = ["zeit;weg (Länge)"] + [
        f"{t:.1f};{2.5 * t - 1.9:.2f}".replace(".", ",") for t in (0.5, 1, 1.5, 2, 10)
    ]
    datei.write_bytes(("\r\n".join(zeilen) + "\r\n").encode("cp1252"))
    diagramm = Chart(Form())
    diagramm.kind = "scatter"

    diagramm.load_csv(datei, 0, 1)
    ergebnis = diagramm.add_regression()

    assert ergebnis.steigung == pytest.approx(2.5, abs=0.01)


def test_leeres_kreisdiagramm_meldet_sich_deutsch() -> None:
    """Punkt 592: matplotlib meldete „All wedge sizes are zero“."""
    with pytest.raises(NatterDatenError, match="Kreisdiagramm"):
        Chart(Form()).add_pie_series([], [])


def test_tausenderpunkte_in_der_csv(tmp_path) -> None:
    """Punkt 592: „1.200,50“ galt als „nicht nur Zahlen“."""
    datei = tmp_path / "umsatz.csv"
    datei.write_text("monat;umsatz\nJan;1.200,50\nFeb;980,00\n", encoding="utf-8")
    diagramm = Chart(Form())

    diagramm.load_csv(datei, 0, 1)

    from pcl.components.chart import _als_zahlen

    assert list(_als_zahlen(diagramm._dataframe["umsatz"], "umsatz", "x")) == [1200.5, 980.0]


@pytest.mark.parametrize(
    ("aufruf", "meldung"),
    [
        (lambda d: d.add_line_series([1, 2, 3], [1, 2]), "3 x-Werte, aber 2 y-Werte"),
        (lambda d: d.add_scatter_series([1, 2], [1, 2, 3]), "2 x-Werte, aber 3 y-Werte"),
        (lambda d: d.add_bar_series(["a", "b"], [1, None]), "2. Wert ist None"),
        (lambda d: d.add_pie_series(["a", "b"], [3, -1]), "negativen"),
        (lambda d: d.add_pie_series(["a"], [3, 1]), "1 Beschriftungen, aber 2 Werte"),
        (lambda d: d.add_histogram_series([1, 2, 3], bins=0), "ab 1"),
        (lambda d: d.add_line_series([1, 2], ["10", "zehn"]), "„zehn“ ist keine Zahl"),
    ],
)
def test_eingabefehler_der_reihen_kommen_deutsch(aufruf, meldung: str) -> None:
    """Punkt 598: die Fehler kamen englisch aus matplotlib."""
    with pytest.raises(NatterDatenError, match=meldung):
        aufruf(Chart(Form()))


def test_werte_als_text_werden_zahlen() -> None:
    """Punkt 598: „10“, „9“, „100“ ergab still eine Kategorienachse in
    dieser Reihenfolge. Kreisdiagramm mit Text lief in einen
    numpy-Fehler."""
    diagramm = Chart(Form())
    diagramm.add_line_series([1, 2, 3], ["10", "9", "100,5"])
    diagramm.add_pie_series(["a", "b"], ["3", "1"])

    linie = diagramm._achse.get_lines()[0]
    assert list(linie.get_ydata()) == [10.0, 9.0, 100.5]


def test_ein_einzelner_punkt_und_mehrere_titel() -> None:
    """Punkt 621: eine Linie aus einem Punkt war unsichtbar, und von
    zwei Reihentiteln wurde der letzte zur Überschrift."""
    diagramm = Chart(Form())
    diagramm.add_line_series([1], [5], title="Jungen")
    assert diagramm._achse.get_lines()[0].get_marker() == "o"
    assert diagramm._achse.get_title() == "Jungen"

    diagramm.add_line_series([1, 2], [3, 4], title="Mädchen")
    assert diagramm._achse.get_title() == ""


def test_clear_und_reihe_zeichnen_gebuendelt(monkeypatch) -> None:  # noqa: ANN001
    """Punkt 614: jedes clear() und jede Reihe zeichnete sofort; hundert
    Aktualisierungen dauerten über eine halbe Minute. Jetzt wird je
    Durchlauf der Ereignisschleife einmal gezeichnet."""
    from PySide6.QtWidgets import QApplication

    diagramm = Chart(Form())
    QApplication.processEvents()
    gezeichnet = []
    monkeypatch.setattr(diagramm._qwidget, "draw", lambda: gezeichnet.append(1))

    for _ in range(20):
        diagramm.clear()
        diagramm.add_line_series(list(range(10)), list(range(10)))
    assert gezeichnet == []
    QApplication.processEvents()

    assert gezeichnet == [1]
