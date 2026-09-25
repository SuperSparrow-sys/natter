"""Tests für die HTML-Vorschau (Abschnitt 11.3). Siehe
Arbeitspaket M5, Schritt 7. Headless. `open_url` wird gemockt
(kein echter Browser, wie in tests/test_files.py).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.viewers import HtmlVorschau


def test_htmlvorschau_zeigt_gespeicherten_inhalt(tmp_path: Path) -> None:
    datei = tmp_path / "seite.html"
    datei.write_text("<h1>Highscore</h1>", encoding="utf-8")

    vorschau = HtmlVorschau(datei)

    assert "Highscore" in vorschau.browser.toPlainText()


def test_htmlvorschau_aktualisiert_sich_bei_dateiaenderung(tmp_path: Path) -> None:
    """Die tatsächliche Zustellung des Betriebssystem-Ereignisses über
    `QFileSystemWatcher` selbst ist in dieser Entwicklungsumgebung nicht
    zuverlässig genug für einen Test (Zustellung teils über 5s verzögert,
    teils gar nicht beobachtet - vermutlich Sandbox-/Virenscanner-
    Interferenz mit dem Windows-Temp-Ordner). Getestet wird deshalb die
    Reaktion auf das Signal direkt (echte Neuladung mit echtem Inhalt),
    nicht die Zustellung durch das Betriebssystem selbst - die
    Verdrahtung (`fileChanged.connect(self._neu_laden)`) bleibt
    unverändert Produktionscode."""
    datei = tmp_path / "seite.html"
    datei.write_text("<h1>Alt</h1>", encoding="utf-8")
    vorschau = HtmlVorschau(datei)

    datei.write_text("<h1>Neu</h1>", encoding="utf-8")
    vorschau._beobachter.fileChanged.emit(str(datei))

    assert "Neu" in vorschau.browser.toPlainText()


def test_im_browser_oeffnen_ruft_open_url_mit_dem_dateipfad_auf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    datei = tmp_path / "seite.html"
    datei.write_text("<h1>Highscore</h1>", encoding="utf-8")
    vorschau = HtmlVorschau(datei)

    aufgerufen = []
    monkeypatch.setattr("ide.viewers.html_vorschau.open_url", lambda ziel: aufgerufen.append(ziel))

    vorschau._im_browser_oeffnen()

    assert aufgerufen == [str(datei)]
