"""Tests für ide/main.py: Einstiegspunkt der IDE. Headless – `main()`
selbst startet die blockierende Ereignisschleife und wird hier bewusst
nicht aufgerufen; `erstellen()` baut Anwendung und Fenster ohne zu
blockieren und ist deshalb testbar.
"""

from pathlib import Path

from PySide6.QtWidgets import QApplication

from ide.main import _projekt_aus_argv_oeffnen, erstellen
from ide.shell.hauptfenster import HauptFenster

_AMPEL_NATTER = (
    Path(__file__).resolve().parent.parent
    / "beispielprojekte"
    / "Ampel"
    / "ampel.natter"
)


def test_erstellen_liefert_anwendung_und_hauptfenster() -> None:
    app, fenster = erstellen()
    assert isinstance(app, QApplication)
    assert isinstance(fenster, HauptFenster)


def test_erstellen_wiederverwendet_vorhandene_anwendung() -> None:
    app1, _ = erstellen()
    app2, _ = erstellen()
    assert app1 is app2


def test_fenster_kann_angezeigt_werden() -> None:
    _, fenster = erstellen()
    fenster.show()
    assert fenster.isVisible() is True


def test_natter_datei_als_kommandozeilenargument_wird_geoeffnet() -> None:
    """Nutzer-Feedback (September 2026): „man installiert die Exe und
    kann dann auch eine .natter-Datei einfach öffnen" - die Windows-
    Dateizuordnung (`tools/natter.iss`) ruft `Natter.exe "%1"` auf."""
    _, fenster = erstellen()

    _projekt_aus_argv_oeffnen(fenster, ["Natter.exe", str(_AMPEL_NATTER)])

    assert fenster.projekt is not None
    assert fenster.projekt.name == "Ampel"


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
