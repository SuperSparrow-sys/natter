"""Tests für ide/main.py: Einstiegspunkt der IDE. Headless – `main()`
selbst startet die blockierende Ereignisschleife und wird hier bewusst
nicht aufgerufen; `erstellen()` baut Anwendung und Fenster ohne zu
blockieren und ist deshalb testbar.
"""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from ide.main import _projekt_aus_argv_oeffnen, erstellen
from ide.shell.hauptfenster import HauptFenster

_AMPEL_NATTER = (
    Path(__file__).resolve().parent.parent
    / "beispielprojekte"
    / "04_CookieKlicker"
    / "04_CookieKlicker.natter"
)


def test_erstellen_liefert_anwendung_und_hauptfenster() -> None:
    app, fenster = erstellen()
    assert isinstance(app, QApplication)
    assert isinstance(fenster, HauptFenster)


def test_die_anwendung_hat_einen_namen() -> None:
    """Ohne Namen legt Qt anwendungseigene Dateien unter „python3“ ab -
    die Protokolldatei aus `ide/fehlermeldung.py` landete so in einem
    Ordner, in dem sie niemand vermutet (M11, Abschnitt 5)."""
    app, _ = erstellen()

    assert app.applicationName() == "Natter"
    assert app.organizationName() == "Natter"


def test_erstellen_wiederverwendet_vorhandene_anwendung() -> None:
    app1, _ = erstellen()
    app2, _ = erstellen()
    assert app1 is app2


def test_fenster_kann_angezeigt_werden() -> None:
    _, fenster = erstellen()
    fenster.show()
    assert fenster.isVisible() is True


def test_natter_datei_als_kommandozeilenargument_wird_geoeffnet() -> None:
    """Gemeldet: „man installiert die Exe und
 kann dann auch eine.natter-Datei einfach öffnen" - die Windows-
 Dateizuordnung (`tools/natter.iss`) ruft `Natter.exe "%1"` auf."""
    _, fenster = erstellen()

    _projekt_aus_argv_oeffnen(fenster, ["Natter.exe", str(_AMPEL_NATTER)])

    assert fenster.projekt is not None
    assert fenster.projekt.name == "04_CookieKlicker"


def test_ohne_natter_argument_bleibt_kein_projekt_offen() -> None:
    _, fenster = erstellen()

    _projekt_aus_argv_oeffnen(fenster, ["Natter.exe"])

    assert fenster.projekt is None


def test_anderes_argument_als_natter_datei_wird_ignoriert() -> None:
    _, fenster = erstellen()

    _projekt_aus_argv_oeffnen(fenster, ["Natter.exe", "irgendwas.txt"])

    assert fenster.projekt is None


def test_ungueltiger_natter_pfad_zeigt_meldung_statt_abzustuerzen(
    tmp_path, monkeypatch
) -> None:
    from PySide6.QtWidgets import QMessageBox

    gezeigt = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda *a, **k: gezeigt.append(a) or QMessageBox.StandardButton.Ok
    )

    _, fenster = erstellen()
    fehlender_pfad = tmp_path / "gibt_es_nicht.natter"

    _projekt_aus_argv_oeffnen(fenster, ["Natter.exe", str(fehlender_pfad)])

    assert gezeigt
    assert fenster.projekt is None


# ------------------- Ein Fehler beim Start bleibt nicht unsichtbar
#
# Auf einem Schulrechner blitzte im September 2026 die Ladeanzeige auf,
# und danach verschwand Natter - kein Dialog, keine Protokolldatei,
# kein Hinweis. Der Grund stand in der Reihenfolge: `starten()` richtete
# den Fehlerhaken erst hinter `erstellen()` ein, also hinter der
# Stelle, an der am meisten schiefgehen kann. Wer auf einem fremden
# Rechner nicht sieht, dass ein Fehler vorliegt, kann ihn auch nicht
# melden.


def test_der_fehlerhaken_steht_bevor_das_fenster_gebaut_wird(monkeypatch) -> None:
    """Der eigentliche Punkt: nicht dass es einen Haken gibt, sondern
    dass er schon hängt, wenn der Aufbau scheitert."""
    import sys

    import ide.main as modul

    beim_aufbau: list[bool] = []
    vorher = sys.excepthook

    def _kaputt(anzeige=None):  # noqa: ANN001, ANN202
        beim_aufbau.append(sys.excepthook is not vorher)
        raise RuntimeError("Aufbau gescheitert")

    monkeypatch.setattr(modul, "erstellen", _kaputt)
    monkeypatch.setattr(sys, "excepthook", vorher)

    with pytest.raises(RuntimeError):
        modul.starten()

    assert beim_aufbau == [True], (
        "Der Fehlerhaken hing noch nicht - ein Fehler beim Aufbau bliebe "
        "ohne Meldung und ohne Protokolldatei."
    )


def test_die_ladeanzeige_bleibt_bei_einem_fehler_nicht_stehen(monkeypatch) -> None:
    """Sonst steht das Feld mit der Versionsnummer ohne Fenster da,
    während der Fehlerdialog auf eine Antwort wartet."""
    import ide.main as modul

    offen: list[object] = []

    class _Anzeige:
        def __init__(self, version: str) -> None:
            offen.append(self)
            self.geschlossen = False

        def show(self) -> None:
            pass

        def melden(self, text: str) -> None:
            pass

        def close(self) -> None:
            self.geschlossen = True

    def _kaputt(anzeige=None):  # noqa: ANN001, ANN202
        raise RuntimeError("Aufbau gescheitert")

    monkeypatch.setattr(modul, "Ladeanzeige", _Anzeige)
    monkeypatch.setattr(modul, "erstellen", _kaputt)

    with pytest.raises(RuntimeError):
        modul.starten()

    assert offen and offen[0].geschlossen, "Die Ladeanzeige blieb stehen."
    assert QApplication.overrideCursor() is None, "Der Ladekreis dreht weiter."
