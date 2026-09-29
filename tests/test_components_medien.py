"""`HtmlViewer` und `Sound` (M15, Abschnitt 4).

`HtmlViewer` sitzt bewusst auf `QTextBrowser` und nicht auf
`QWebEngineView`: das kann echtes Web samt JavaScript, wiegt in der
gebauten Exe aber über 100 MB - mehr als das ganze übrige Natter. Die
Tests halten fest, was damit geht (Überschriften, Tabellen, Listen) und
was die Entscheidung kostet.

`Sound` spielt nur `.wav`. Abgespielt wird hier nichts - ein Testlauf
soll still bleiben, und auf einem Rechner ohne Tonausgabe gäbe es
nichts zu hören. Geprüft wird, was davor passiert: dass die Datei
angenommen oder mit einer verständlichen deutschen Meldung abgelehnt
wird.
"""

from __future__ import annotations

import struct
import wave
from pathlib import Path

import pytest

from pcl import Form, HtmlViewer, Sound
from pcl.errors import NatterPropertyError

_AM_LEBEN: list[object] = []


@pytest.fixture
def betrachter():
    formular = Form()
    viewer = HtmlViewer(formular)
    _AM_LEBEN.extend((formular, viewer))
    return viewer


@pytest.fixture
def wav_datei(tmp_path: Path) -> Path:
    """Eine echte, sehr kurze `.wav` - keine Attrappe mit falscher
    Endung, sonst prüfte der Test nur den Dateinamen."""
    pfad = tmp_path / "ton.wav"
    with wave.open(str(pfad), "wb") as datei:
        datei.setnchannels(1)
        datei.setsampwidth(2)
        datei.setframerate(8000)
        datei.writeframes(b"".join(struct.pack("<h", 0) for _ in range(80)))
    return pfad


# -- HtmlViewer ---------------------------------------------------------


def test_html_landet_in_der_anzeige(betrachter) -> None:
    betrachter.html = "<h1>Hallo</h1>"

    assert "Hallo" in betrachter._qwidget.toPlainText()


def test_eine_tabelle_wird_wirklich_als_tabelle_gesetzt(betrachter) -> None:
    """Das ist der Grund, warum es kein einfaches Label tut."""
    betrachter.html = (
        "<table><tr><th>Ort</th><th>Grad</th></tr>"
        "<tr><td>Hamburg</td><td>9,7</td></tr></table>"
    )

    text = betrachter._qwidget.toPlainText()
    assert "Ort" in text and "Hamburg" in text and "9,7" in text


def test_fett_und_kursiv_bleiben_auszeichnung_und_werden_nicht_angezeigt(
    betrachter,
) -> None:
    betrachter.html = "<p>Ein <b>fetter</b> Text</p>"

    text = betrachter._qwidget.toPlainText()
    assert "fetter" in text
    assert "<b>" not in text


def test_eine_datei_laesst_sich_laden(betrachter, tmp_path: Path) -> None:
    datei = tmp_path / "bericht.html"
    datei.write_text("<h2>Bericht</h2><p>Inhalt</p>", encoding="utf-8")

    betrachter.load_from_file(str(datei))

    assert "Bericht" in betrachter._qwidget.toPlainText()
    assert betrachter.html.startswith("<h2>")


def test_eine_fehlende_html_datei_sagt_das_auf_deutsch(
    betrachter, tmp_path: Path
) -> None:
    with pytest.raises(NatterPropertyError, match="gibt es nicht"):
        betrachter.load_from_file(str(tmp_path / "weg.html"))


def test_clear_leert_die_anzeige(betrachter) -> None:
    betrachter.html = "<p>etwas</p>"

    betrachter.clear()

    assert betrachter._qwidget.toPlainText().strip() == ""
    assert betrachter.html == ""


# -- Sound --------------------------------------------------------------


def test_eine_wav_datei_wird_angenommen(wav_datei: Path) -> None:
    klang = Sound()

    klang.load_from_file(str(wav_datei))

    assert klang.file_name == str(wav_datei)


def test_der_dateiname_darf_auch_im_konstruktor_stehen(wav_datei: Path) -> None:
    klang = Sound(str(wav_datei))

    assert klang.file_name == str(wav_datei)


def test_eine_mp3_wird_mit_einem_hinweis_abgelehnt(tmp_path: Path) -> None:
    """`QSoundEffect` spielt nur unkomprimierte Klänge. Die Meldung
    muss sagen, was stattdessen zu tun ist."""
    mp3 = tmp_path / "lied.mp3"
    mp3.write_bytes(b"ID3")
    klang = Sound()

    with pytest.raises(NatterPropertyError) as fehler:
        klang.load_from_file(str(mp3))

    assert ".wav" in str(fehler.value)
    assert "umwandeln" in str(fehler.value)


def test_eine_fehlende_klangdatei_sagt_das_auf_deutsch(tmp_path: Path) -> None:
    klang = Sound()

    with pytest.raises(NatterPropertyError, match="gibt es nicht"):
        klang.load_from_file(str(tmp_path / "weg.wav"))


def test_abspielen_ohne_geladenen_klang_sagt_was_fehlt() -> None:
    klang = Sound()

    with pytest.raises(NatterPropertyError, match="load_from_file"):
        klang.play()


def test_die_lautstaerke_laesst_sich_einstellen(wav_datei: Path) -> None:
    klang = Sound(str(wav_datei))

    klang.volume = 0.3

    assert 0.29 < klang.volume < 0.31


@pytest.mark.parametrize("wert", [-0.5, 1.5, 2])
def test_eine_lautstaerke_ausserhalb_wird_abgelehnt(wert) -> None:
    klang = Sound()

    with pytest.raises(NatterPropertyError, match="0.0 und 1.0"):
        klang.volume = wert


def test_stoppen_ohne_klang_geht_ohne_fehler() -> None:
    Sound().stop()


def test_sound_liegt_nicht_auf_dem_formular() -> None:
    """Wie eine Datenbankverbindung: im Code erzeugt, kein Symbol im
    Designer. Ein Symbol brächte nichts ein, was eine Zeile Code nicht
    auch tut."""
    from ide.palette.palette import ALLE_KOMPONENTEN

    assert Sound not in ALLE_KOMPONENTEN
    assert not hasattr(Sound, "left")
