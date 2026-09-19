"""Tests für die letzten Meldungen ohne Lösungsteil (M11, Abschnitt 4).

Der Durchgang durch alle nutzersichtbaren Texte hatte sechs Stellen
übrig gelassen, weil sie außerhalb des damaligen Änderungsbereichs
lagen. Sie sind hier nachgeholt:

* das HTML-Testprotokoll (letzte Klammerform im Bestand)
* „Als Tabelle anzeigen“ – sagte nur, dass es nicht geht
* die Integritätsprüfung – sagte nicht, ob man weiterarbeiten kann
* der Haltegrund des Debuggers – stand englisch in der Statusleiste
* die Karett-Zeile im Panel „Meldungen“ – zeigte in der
  Proportionalschrift der Liste auf die falsche Stelle
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.debugger.haltegruende import haltegrund_deutsch
from ide.debugger.tabellenansicht import (
    GEEIGNETE_WERTE,
    TabellenFehler,
    tabelle_aus_antwort,
    tabelle_aus_wert,
)
from ide.integritaet.manifest import WAS_ZU_TUN_IST, PruefErgebnis
from ide.shell.hauptfenster import HauptFenster
from ide.testrunner import Testergebnis, ergebnisse_als_html


def _ergebnis(kennung: str, status: str) -> Testergebnis:
    return Testergebnis(id=kennung, status=status, dauer=0.01)


# -- HTML-Testprotokoll --------------------------------------------------


def test_ein_einzelner_test_heisst_test() -> None:
    """„1 von 1 Test(s) bestanden“ las sich in keiner der beiden
    Zahlformen richtig – und das Protokoll geht an die Lehrkraft."""
    html = ergebnisse_als_html([_ergebnis("t1", "bestanden")])

    assert "1 von 1 Test bestanden." in html
    assert "Test(s)" not in html


def test_mehrere_tests_heissen_tests() -> None:
    html = ergebnisse_als_html(
        [_ergebnis("t1", "bestanden"), _ergebnis("t2", "fehlgeschlagen")]
    )

    assert "1 von 2 Tests bestanden." in html


def test_auch_ohne_tests_steht_ein_satz_da() -> None:
    html = ergebnisse_als_html([])

    assert "0 von 0 Tests bestanden." in html


# -- Als Tabelle anzeigen ------------------------------------------------


def test_ein_untauglicher_wert_nennt_die_tauglichen() -> None:
    """„Geht nicht“ allein lässt jemanden raten, welcher Wert denn dann
    gemeint war."""
    with pytest.raises(TabellenFehler) as fehler:
        tabelle_aus_wert(42)

    assert GEEIGNETE_WERTE in str(fehler.value)


def test_auch_die_antwort_null_nennt_die_tauglichen() -> None:
    with pytest.raises(TabellenFehler) as fehler:
        tabelle_aus_antwort("null")

    assert GEEIGNETE_WERTE in str(fehler.value)


def test_eine_unverstaendliche_antwort_sagt_was_zu_tun_ist() -> None:
    """Der rohe Antworttext bleibt stehen – er ist das Einzige, was
    hier weiterhilft. Davor gehört aber, was man tun kann."""
    with pytest.raises(TabellenFehler) as fehler:
        tabelle_aus_antwort("{kein JSON")

    text = str(fehler.value)
    assert "noch einmal mit dem Debugger starten" in text
    assert "{kein JSON" in text


def test_die_liste_der_tauglichen_werte_nennt_die_gaengigen() -> None:
    for stueck in ("Liste", "Dictionary", "Datenbankabfrage", "DataFrame"):
        assert stueck in GEEIGNETE_WERTE


# -- Integritätsprüfung --------------------------------------------------


def test_eine_veraenderte_installation_sagt_was_zu_tun_ist() -> None:
    """Dass etwas nicht stimmt, sagt der feste Anfang aus Abschnitt
    17.8. Wer das an einem Schulrechner liest, weiß ohne den Zusatz
    nicht, ob er weiterarbeiten kann."""
    ergebnis = PruefErgebnis(signatur_gueltig=True, veraendert=["ide/main.py"])

    meldung = ergebnis.als_meldung()

    assert meldung.startswith("Natter wurde nach der Erstellung verändert:")
    assert "ide/main.py" in meldung
    assert WAS_ZU_TUN_IST in meldung


def test_auch_eine_ungueltige_signatur_sagt_es() -> None:
    ergebnis = PruefErgebnis(signatur_gueltig=False)

    assert WAS_ZU_TUN_IST in ergebnis.als_meldung()


def test_eine_heile_installation_meldet_nichts() -> None:
    assert PruefErgebnis(signatur_gueltig=True).als_meldung() == ""


def test_der_zusatz_nimmt_die_sorge_um_eigene_projekte() -> None:
    assert "Eigene Projekte sind davon nicht betroffen" in WAS_ZU_TUN_IST


# -- Haltegrund des Debuggers --------------------------------------------


@pytest.mark.parametrize(
    ("grund", "deutsch"),
    [
        ("breakpoint", "an einem Haltepunkt"),
        ("step", "nach einem Einzelschritt"),
        ("exception", "wegen eines Fehlers im Programm"),
        ("pause", "angehalten über „Start → Pause“"),
    ],
)
def test_der_haltegrund_steht_auf_deutsch_da(grund: str, deutsch: str) -> None:
    """„Angehalten (breakpoint)“ stand an genau der Stelle, an der man
    wissen will, warum das Programm gerade nicht weiterläuft."""
    assert haltegrund_deutsch(grund) == deutsch


def test_ein_unbekannter_grund_kommt_unveraendert_durch() -> None:
    """debugpy kann Gründe melden, die hier noch nicht stehen – ein
    englisches Wort ist immer noch besser als gar keines."""
    assert haltegrund_deutsch("was-ganz-neues") == "was-ganz-neues"


def test_die_statusleiste_zeigt_den_deutschen_grund(qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster._debugger_angehalten({"threadId": None, "reason": "breakpoint"})

    assert (
        fenster.statusBar().currentMessage() == "Angehalten: an einem Haltepunkt"
    )


# -- Karett-Zeile im Panel „Meldungen“ -----------------------------------


def test_eine_katalogmeldung_steht_in_festbreitenschrift(qtbot) -> None:
    """Die Meldung enthält die Quelltextzeile und darunter eine Zeile
    mit ^^^, die auf die Stelle zeigt. In der Proportionalschrift der
    Liste stand die Markierung irgendwo – und war damit wertlos."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster._katalogmeldung_anzeigen("Fehler\n\nWo:   main.py, Zeile 1")

    eintrag = fenster.meldungen_liste.item(0)
    assert eintrag.font().family() == fenster._code_schriftart


def test_eine_gewoehnliche_meldung_bleibt_proportional(qtbot) -> None:
    """Ein deutscher Satz liest sich proportional besser – die Schrift
    bekommen nur die Einträge, die eine Markierung tragen."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster.meldungen_liste.addItem("[Umgebung] requirements.txt")

    eintrag = fenster.meldungen_liste.item(0)
    assert eintrag.font().family() != fenster._code_schriftart


def test_die_katalogmeldung_holt_das_panel_nach_vorn(qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster._katalogmeldung_anzeigen("Fehler")

    assert fenster.panels.currentWidget() is fenster.meldungen_liste


def test_die_karettzeile_steht_unter_der_quelltextzeile(qtbot) -> None:
    """Gegenprobe zur Absicherung: ohne die Festbreitenschrift sind die
    beiden Zeilen verschieden breit, obwohl sie gleich viele Zeichen
    haben."""
    from PySide6.QtGui import QFontMetrics

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster._katalogmeldung_anzeigen("          print(zaehler)\n          " + "^" * 14)

    masse = QFontMetrics(fenster.meldungen_liste.item(0).font())
    quelltext, markierung = fenster.meldungen_liste.item(0).text().split("\n")
    assert masse.horizontalAdvance(quelltext) == masse.horizontalAdvance(markierung)


# -- Keine Klammerform mehr ----------------------------------------------


def test_das_html_protokoll_steht_nicht_mehr_auf_der_ausnahmeliste() -> None:
    """Die Liste der bekannten Verstöße sollte leer werden, nicht
    wachsen."""
    from tests.test_meldungen_mit_loesung import KLAMMERFORM_AUSNAHMEN

    assert KLAMMERFORM_AUSNAHMEN == set()
    assert Path("ide/testrunner/html_export.py").exists()
