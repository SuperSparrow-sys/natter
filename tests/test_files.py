"""Tests für pcl/files.py: `open_url` (Abschnitt 11.3). `webbrowser.open`
wird gemockt (Abschnitt 19: „`open_url` mit gemocktem Browser“) statt
einen echten Browser zu öffnen.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from pcl import open_url


def test_open_url_mit_relativem_pfad_loest_gegen_arbeitsverzeichnis_auf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    datei = tmp_path / "seite.html"
    datei.write_text("<html></html>", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    aufgerufen = []
    monkeypatch.setattr("pcl.files.webbrowser.open", lambda ziel: aufgerufen.append(ziel))

    open_url("seite.html")

    assert aufgerufen == [datei.resolve().as_uri()]


def test_open_url_mit_absolutem_pfad(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    datei = tmp_path / "unterordner" / "seite.html"
    datei.parent.mkdir()
    datei.write_text("<html></html>", encoding="utf-8")
    aufgerufen = []
    monkeypatch.setattr("pcl.files.webbrowser.open", lambda ziel: aufgerufen.append(ziel))

    open_url(str(datei))

    assert aufgerufen == [datei.resolve().as_uri()]


def test_open_url_mit_http_adresse_bleibt_unveraendert(monkeypatch: pytest.MonkeyPatch) -> None:
    aufgerufen = []
    monkeypatch.setattr("pcl.files.webbrowser.open", lambda ziel: aufgerufen.append(ziel))

    open_url("https://example.com/seite")

    assert aufgerufen == ["https://example.com/seite"]


def test_open_url_erkennt_windows_laufwerksbuchstaben_nicht_als_schema(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    datei = tmp_path / "seite.html"
    datei.write_text("<html></html>", encoding="utf-8")
    aufgerufen = []
    monkeypatch.setattr("pcl.files.webbrowser.open", lambda ziel: aufgerufen.append(ziel))

    # str(Path) unter Windows beginnt mit "C:\..." - das ist kein
    # URL-Schema, sondern ein Laufwerksbuchstabe.
    open_url(str(datei))

    assert aufgerufen[0].startswith("file://")
