"""Ein Programm, das 20 Sekunden ohne Zeilenende schreibt (Punkt 275).

Bis 0.3.6 blieb das Panel „Ausgabe“ dabei die ganze Zeit leer, der
Speicher von Natter wuchs um rund 3 MB je Sekunde, und beim
Programmende kam eine einzige Zeile mit über 80 Millionen Zeichen
an, deren Anzeige Natter minutenlang anhielt.
"""

from __future__ import annotations

import subprocess
import sys
import time

import pytest
from PySide6.QtCore import QTimer

from ide.shell.hauptfenster import AUSGABE_GRENZE
from ide.shell.hintergrund import ZEILEN_GRENZE

DAUER_S = 20

_PROGRAMM = f"""
import time
ende = time.monotonic() + {DAUER_S}
i = 0
while time.monotonic() < ende:
    print(i, end=" ")
    i += 1
"""


@pytest.mark.timeout(90)
def test_zwanzig_sekunden_ohne_zeilenende(hauptfenster, qtbot) -> None:
    fenster = hauptfenster
    fenster.show()
    optionen: dict[str, object] = {}
    if sys.platform == "win32":
        optionen["creationflags"] = subprocess.CREATE_NO_WINDOW
    prozess = subprocess.Popen(
        [sys.executable, "-c", _PROGRAMM],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        **optionen,
    )
    fenster.laufender_prozess = prozess

    takte: list[float] = []
    uhr = QTimer(fenster)
    uhr.setInterval(20)
    uhr.timeout.connect(lambda: takte.append(time.monotonic()))

    groesster_speicher = 0
    zeilen_waehrend_des_laufs = 0

    def nachsehen() -> None:
        nonlocal groesster_speicher, zeilen_waehrend_des_laufs
        leser = fenster._ausgabe_leser
        if leser is not None:
            with leser._sperre:
                zeichen = sum(len(zeile) for zeile in leser._zeilen)
            groesster_speicher = max(groesster_speicher, zeichen)
        if prozess.poll() is None:
            zeilen_waehrend_des_laufs = fenster.ausgabe_liste.count()

    pruefer = QTimer(fenster)
    pruefer.setInterval(200)
    pruefer.timeout.connect(nachsehen)

    try:
        fenster._ausgabe_leser_starten()
        uhr.start()
        pruefer.start()
        qtbot.waitUntil(
            lambda: prozess.poll() is not None, timeout=(DAUER_S + 30) * 1000
        )
        uhr.stop()
        pruefer.stop()
    finally:
        if prozess.poll() is None:
            prozess.kill()
        prozess.wait(10)
        fenster._ausgabe_leser_beenden()
        fenster.laufender_prozess = None

    assert zeilen_waehrend_des_laufs > 100, (
        "Während des Laufs stand kaum etwas im Panel: "
        f"{zeilen_waehrend_des_laufs} Zeilen."
    )
    assert groesster_speicher <= AUSGABE_GRENZE * ZEILEN_GRENZE
    liste = fenster.ausgabe_liste
    assert liste.count() <= AUSGABE_GRENZE
    laengste = max(
        len(liste.item(i).text()) for i in range(liste.count())
    )
    assert laengste <= ZEILEN_GRENZE + 100
    luecken = [b - a for a, b in zip(takte, takte[1:], strict=False)]
    assert takte, "Der Timer lief währenddessen gar nicht."
    assert max(luecken, default=0) < 0.3, (
        f"Der Timer stand bis zu {max(luecken):.2f} s still."
    )
