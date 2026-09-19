"""`HtmlViewer` und `Sound` (Abschnitt 5.2, 11.3).

Zwei Komponenten, die nichts miteinander zu tun haben außer dem
Umstand, dass beide etwas abspielen statt etwas zu rechnen: die eine
zeigt eine Seite, die andere gibt einen Ton.

**`HtmlViewer` auf `QTextBrowser`, nicht auf `QWebEngineView`.** Die
Entscheidung steht in `docs/arbeitspakete/M15.md` und hat einen
handfesten Grund: `QWebEngineView` kann echtes Web samt JavaScript,
wiegt in der gebauten Exe aber über 100 MB - mehr als das ganze übrige
Natter. Für das, was im Unterricht vorkommt (eine Tabelle, ein paar
Überschriften, ein Bild, eine Highscore-Liste aus dem eigenen
Programm), reicht das eingebaute HTML-Teilstück von Qt vollständig.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtWidgets import QTextBrowser, QWidget

from pcl.control import Control
from pcl.errors import NatterPropertyError
from pcl.properties import Komponente, Prop


class HtmlViewer(Control):
    """Zeigt HTML an, ohne den Browser zu öffnen (entspricht
    ``THtmlViewer`` bzw. `TIpHtmlPanel` in Lazarus). Qt-Basis:
    `QTextBrowser`.

    Zwei Wege hinein::

        self.hv_seite.html = "<h1>Hallo</h1><p>Das ist fett: <b>ja</b></p>"
        self.hv_seite.load_from_file("bericht.html")

    Was geht: Überschriften, Absätze, Listen, Tabellen, Fett/Kursiv,
    Bilder, Links. Was nicht geht: JavaScript und alles, was eine
    Seite erst im Browser zusammenbaut.
    """

    width = Prop(int, 320, kategorie="Layout", doc="Breite in Pixeln")
    height = Prop(int, 220, kategorie="Layout", doc="Höhe in Pixeln")

    html = Prop(str, "", kategorie="Darstellung", doc="Der angezeigte HTML-Text")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QTextBrowser(eltern_widget)
        widget.setOpenExternalLinks(True)
        widget.setHtml(self.html)
        return widget

    def load_from_file(self, pfad: str) -> None:
        """Lädt eine `.html`-Datei von der Festplatte."""
        if not isinstance(pfad, str):
            raise NatterPropertyError(
                "HtmlViewer.load_from_file erwartet einen Text (str) mit dem Dateinamen."
            )
        datei = Path(pfad)
        if not datei.is_file():
            raise NatterPropertyError(
                f"HtmlViewer.load_from_file: die Datei {pfad!r} gibt es nicht."
            )
        # Über die Prop, damit `html` danach auch wirklich den Inhalt
        # führt - sonst stünde dort weiter der alte Text.
        self.html = datei.read_text(encoding="utf-8")

    def clear(self) -> None:
        """Leert die Anzeige."""
        self.html = ""

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "html":
            self._qwidget.setHtml(wert)


class Sound(Komponente):
    """Spielt einen Klang ab (entspricht ``TSoundPlayer``/`PlaySound`).
    Qt-Basis: `QSoundEffect` für `.wav`.

    `Sound` ist **keine** `Control`: sie liegt nicht auf dem Formular,
    sondern wird im Code erzeugt - wie eine Datenbankverbindung. Ein
    Symbol im Designer brächte nichts ein, was eine Zeile Code nicht
    auch tut::

        self.klang = Sound()
        self.klang.load_from_file("treffer.wav")
        self.klang.play()

    Für den einfachsten Fall - einmal „piep" - braucht es gar keine
    Datei::

        Sound.beep()          # oder Sound.beep(440, 500)

    `.wav` und sonst nichts: `QSoundEffect` spielt nur unkomprimierte
    Klänge, dafür ohne Zusatzpakete und ohne Verzögerung beim ersten
    Ton. MP3 bräuchte `QMediaPlayer` samt Codecs, die auf einem
    verwalteten Schulrechner nicht sicher da sind.
    """

    neue_attribute_erlaubt = True

    def __init__(self, dateiname: str | None = None) -> None:
        self._effekt = QSoundEffect()
        self._pfad: str | None = None
        if dateiname is not None:
            self.load_from_file(dateiname)

    @property
    def file_name(self) -> str | None:
        """Die geladene Klangdatei, oder `None`."""
        return self._pfad

    @property
    def volume(self) -> float:
        """Lautstärke zwischen 0,0 und 1,0."""
        return float(self._effekt.volume())

    @volume.setter
    def volume(self, wert: float) -> None:
        if not isinstance(wert, int | float) or isinstance(wert, bool):
            raise NatterPropertyError(
                "Sound.volume erwartet eine Kommazahl zwischen 0.0 und 1.0."
            )
        if not 0.0 <= wert <= 1.0:
            raise NatterPropertyError(
                f"Sound.volume erwartet einen Wert zwischen 0.0 und 1.0, erhalten wurde {wert}."
            )
        self._effekt.setVolume(float(wert))

    def load_from_file(self, pfad: str) -> None:
        """Lädt eine `.wav`-Datei."""
        if not isinstance(pfad, str):
            raise NatterPropertyError(
                "Sound.load_from_file erwartet einen Text (str) mit dem Dateinamen."
            )
        datei = Path(pfad)
        if not datei.is_file():
            raise NatterPropertyError(
                f"Sound.load_from_file: die Datei {pfad!r} gibt es nicht."
            )
        if datei.suffix.lower() != ".wav":
            raise NatterPropertyError(
                f"Sound spielt nur .wav-Dateien ab, {datei.name!r} ist keine. "
                "Ein Audioprogramm kann eine MP3 in eine .wav umwandeln."
            )
        self._pfad = str(datei)
        self._effekt.setSource(QUrl.fromLocalFile(str(datei.resolve())))

    def play(self) -> None:
        """Spielt den geladenen Klang ab."""
        if self._pfad is None:
            raise NatterPropertyError(
                "Sound.play(): es ist noch kein Klang geladen. "
                'Zuerst load_from_file("…wav") aufrufen.'
            )
        self._effekt.play()

    def stop(self) -> None:
        """Bricht das Abspielen ab."""
        self._effekt.stop()

    @staticmethod
    def beep(frequenz: int = 800, dauer_ms: int = 200) -> None:
        """Ein kurzer Ton - ohne Datei, ohne Vorbereitung.

        Reicht an `pcl.crt.beep()` weiter, das es für Konsolenprogramme
        schon gibt. Hier steht es noch einmal, damit ein GUI-Programm
        für einen Piepser nicht ausgerechnet das Konsolenmodul
        importieren muss."""
        from pcl.crt import beep as crt_beep

        crt_beep(frequenz, dauer_ms)
