"""Die vier Kleinigkeiten aus M15, Abschnitt 6.

Kleinigkeiten, aber keine Nebensächlichkeiten: ein Fehlerkatalog, der
auf die falsche Fährte führt, kostet eine Schülerin eine
Unterrichtsstunde, und ein Objektinspektor, in dem jede zweite Zeile
anders eingerückt ist als der Baum daneben, sieht nach Versehen aus.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.inspector.eigenschaften_tabelle import EigenschaftenTabelle
from ide.inspector.komponentenbaum import Komponentenbaum
from ide.shell.explorer import EINRUECKUNG, ProjektExplorer
from pcl.analyse import regression
from pcl.errors import NatterDatenDateiError, NatterDatenError
from pcl.fehlerkatalog import fehlermeldung_erzeugen

KATALOG = Path(__file__).resolve().parent.parent / "docs" / "fehlerkatalog.yaml"


# -- NatterDatenError hat einen eigenen Eintrag -------------------------


def test_ein_datenfehler_bekommt_die_passende_ueberschrift() -> None:
    """Vorher griff der `ValueError`-Eintrag - `NatterDatenError` erbt
    von ihm - und die Überschrift hieß „Ungültiger Wert"."""
    with pytest.raises(NatterDatenError) as fehler:
        regression([1.0], [2.0], "linear")

    meldung = fehlermeldung_erzeugen(fehler.value)

    assert meldung is not None
    assert "Daten passen nicht" in meldung.ueberschrift
    assert "NatterDatenError" in meldung.ueberschrift


def test_die_deutsche_meldung_aus_pcl_steht_unveraendert_im_was() -> None:
    with pytest.raises(NatterDatenError) as fehler:
        regression([1.0], [2.0], "linear")

    meldung = fehlermeldung_erzeugen(fehler.value)

    assert "mindestens 2 Punkte" in meldung.was
    assert "Übergeben wurden 1" in meldung.was


def test_der_pruefe_text_fuehrt_nicht_mehr_aufs_dezimalkomma() -> None:
    """Der `ValueError`-Eintrag fragt nach „Leerzeichen, Einheit oder
    Dezimalkomma". Wer zu wenige Punkte für eine Regression hat, sucht
    danach vergeblich - und zwar lange."""
    with pytest.raises(NatterDatenError) as fehler:
        regression([1.0], [2.0], "linear")

    meldung = fehlermeldung_erzeugen(fehler.value)

    assert "Dezimalkomma" not in meldung.pruefe
    assert "Spalte" in meldung.pruefe


def test_eine_fehlende_datendatei_bleibt_beim_dateifehler() -> None:
    """`NatterDatenDateiError` erbt von beiden Seiten. `FileNotFoundError`
    steht in der MRO vorn und soll das auch bleiben: „Datei nicht
    gefunden" ist dort die hilfreichere Auskunft."""
    meldung = fehlermeldung_erzeugen(NatterDatenDateiError("daten.csv gibt es nicht"))

    assert meldung is not None
    assert "Daten passen nicht" not in meldung.ueberschrift


def test_der_eintrag_steht_auch_in_der_dokumentation() -> None:
    """`docs/fehlerkatalog.yaml` beschreibt den Katalog für Menschen -
    Code liest sie nicht (deshalb hier auch kein PyYAML als
    Abhängigkeit, nur um eine Doku-Datei zu prüfen). Steht ein Eintrag
    nur im Python-Katalog, weiß niemand davon."""
    text = KATALOG.read_text(encoding="utf-8")

    assert "id: natter_daten_error" in text
    assert "exception: NatterDatenError" in text

    # Der Abschnitt bis zum nächsten Eintrag - dort darf der
    # Dezimalkomma-Hinweis nicht stehen.
    abschnitt = text.split("id: natter_daten_error", 1)[1].split("- id:", 1)[0]
    assert "Dezimalkomma" not in abschnitt
    assert "Spalte" in abschnitt


# -- Abstände und Ausrichtung -------------------------------------------


def test_beide_baeume_ruecken_gleich_tief_ein(qtbot) -> None:
    """Sie stehen gleichzeitig im Fenster - der Projekt-Explorer links,
    der Komponentenbaum rechts. Unterschiedlich tiefe Stufen fallen
    sofort auf."""
    explorer = ProjektExplorer()
    baum = Komponentenbaum()
    qtbot.addWidget(explorer)
    qtbot.addWidget(baum)

    assert explorer.indentation() == baum.indentation() == EINRUECKUNG


def test_die_eigenschaften_zeigen_keine_zeilennummern(qtbot) -> None:
    """Niemand spricht eine Eigenschaft als „Nummer 3" an, und in
    Lazarus' Objektinspektor steht dort auch nichts. Die Spalte kostete
    nur Platz - links vom Namen, wo der Dock am knappsten ist."""
    tabelle = EigenschaftenTabelle()
    qtbot.addWidget(tabelle)

    assert not tabelle.verticalHeader().isVisible()


def test_die_wertspalte_fuellt_die_breite(qtbot) -> None:
    """Sonst endete die Tabelle mitten im Dock, während der Wert
    daneben abgeschnitten war."""
    tabelle = EigenschaftenTabelle()
    qtbot.addWidget(tabelle)
    tabelle.resize(300, 200)

    assert tabelle.horizontalHeader().stretchLastSection()
