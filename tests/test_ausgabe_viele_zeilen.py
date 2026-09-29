"""Viele `print()`-Zeilen halten Natter nicht an (Punkt 267).

Bis 0.3.6 ging jede Zeile eines Programms einzeln ins Panel
„Ausgabe“, und die Liste maß dabei jedes Mal alle Zeilenhöhen neu:
1.000 Zeilen brauchten 17 Sekunden, 3.000 zweieinhalb Minuten, und
ein 100-ms-Timer lief in 40 Sekunden dreimal statt 400-mal.

Das Programm ist hier ein Ersatz mit einem Textstrom als Ausgabe: es
geht um die Übernahme ins Panel, nicht um das Starten.
"""

from __future__ import annotations

import io
import time

from PySide6.QtCore import QTimer

ZEILEN = 10_000


class _Programm:
    """Ein Programm, dessen gesamte Ausgabe schon bereitliegt."""

    def __init__(self, text: str) -> None:
        self.stdout = io.StringIO(text)

    def poll(self) -> int | None:
        return None

    def kill(self) -> None:
        pass


def _zeilen(fenster) -> list[str]:  # noqa: ANN001
    liste = fenster.ausgabe_liste
    return [liste.item(i).text() for i in range(liste.count())]


def test_zehntausend_zeilen_in_unter_einer_sekunde(hauptfenster, qtbot) -> None:  # noqa: ANN001
    """10.000 Zeilen stehen nach weniger als einer Sekunde im Panel,
    und ein Timer des Hauptfensters läuft währenddessen weiter."""
    fenster = hauptfenster
    fenster.show()
    text = "".join(f"Zeile {nummer}\n" for nummer in range(ZEILEN))
    fenster.laufender_prozess = _Programm(text)

    takte: list[float] = []
    uhr = QTimer(fenster)
    uhr.setInterval(20)
    uhr.timeout.connect(lambda: takte.append(time.monotonic()))
    uhr.start()

    beginn = time.monotonic()
    fenster._ausgabe_leser_starten()
    qtbot.waitUntil(
        lambda: fenster.ausgabe_liste.count() > 0
        and fenster.ausgabe_liste.item(fenster.ausgabe_liste.count() - 1)
        .text()
        .endswith(f"Zeile {ZEILEN - 1}"),
        timeout=10_000,
    )
    dauer = time.monotonic() - beginn
    uhr.stop()
    fenster.laufender_prozess = None

    assert dauer < 1.0, f"{ZEILEN} Zeilen brauchten {dauer:.2f} s"
    luecken = [b - a for a, b in zip(takte, takte[1:], strict=False)]
    assert takte, "Der Timer lief währenddessen gar nicht."
    assert max(luecken, default=0) < 0.3, (
        f"Der Timer stand bis zu {max(luecken):.2f} s still."
    )


def test_die_aeltesten_zeilen_fallen_mit_hinweis_weg(hauptfenster, qtbot) -> None:  # noqa: ANN001
    from ide.shell.hauptfenster import AUSGABE_GRENZE

    fenster = hauptfenster
    text = "".join(f"Zeile {nummer}\n" for nummer in range(ZEILEN))
    fenster.laufender_prozess = _Programm(text)

    fenster._ausgabe_leser_starten()
    qtbot.waitUntil(
        lambda: _zeilen(fenster)[-1:] != []
        and _zeilen(fenster)[-1].endswith(f"Zeile {ZEILEN - 1}"),
        timeout=10_000,
    )
    fenster.laufender_prozess = None

    zeilen = _zeilen(fenster)
    assert len(zeilen) == AUSGABE_GRENZE
    weggefallen = ZEILEN - (AUSGABE_GRENZE - 1)
    anzahl = f"{weggefallen:,}".replace(",", ".")
    assert f"{anzahl} ältere Zeilen weggefallen" in zeilen[0]
    assert zeilen[1].endswith(f"Zeile {weggefallen}")

    # Weitere Zeilen zählen zum selben Hinweis dazu, statt einen
    # zweiten anzulegen.
    fenster.ausgabe_zeile("Programm beendet (Code 0)")
    zeilen = _zeilen(fenster)
    assert len(zeilen) == AUSGABE_GRENZE
    anzahl = f"{weggefallen + 1:,}".replace(",", ".")
    assert f"{anzahl} ältere Zeilen weggefallen" in zeilen[0]
    assert sum("weggefallen" in zeile for zeile in zeilen) == 1


def test_gescrollt_wird_nur_wenn_die_liste_unten_stand(hauptfenster) -> None:  # noqa: ANN001
    """Wer weiter oben etwas nachliest, wird nicht bei jeder neuen
    Zeile ans Ende gerissen."""
    fenster = hauptfenster
    fenster.show()
    liste = fenster.ausgabe_liste
    fenster.panels.setCurrentWidget(liste)
    fenster._ausgabe_zeilen_anhaengen([f"Zeile {n}" for n in range(300)])
    leiste = liste.verticalScrollBar()
    assert leiste.value() == leiste.maximum() > 0

    leiste.setValue(0)
    fenster._ausgabe_zeilen_anhaengen(["noch eine"])
    assert leiste.value() == 0

    leiste.setValue(leiste.maximum())
    fenster._ausgabe_zeilen_anhaengen(["und noch eine"])
    assert leiste.value() == leiste.maximum()
