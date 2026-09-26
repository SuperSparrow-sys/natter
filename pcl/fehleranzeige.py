"""Unbehandelte Fehler im Schülerprogramm anzeigen (M12).

Der Fehlerkatalog (`pcl/fehlerkatalog.py`) ist das didaktische Kernstück
von Natter: statt eines englischen Tracebacks eine Meldung in drei
Teilen – Wo, Was, Prüfe. Benutzt wurde er bis M12 aber nur
vom Debugger. Wer sein Programm mit Strg+F5 startete – also so, wie
man ein fertiges Programm startet –, bekam:

* im Konsolenprogramm den rohen englischen Traceback, in dem vor der
  einen wichtigen Zeile ein Dutzend Zeilen aus `pcl` und Qt stehen,
* im GUI-Programm gar nichts: es läuft ohne Konsolenfenster
  (Abschnitt 7.8), das Fenster verschwand einfach.

Hier hängt sich das Schülerprogramm selbst in `sys.excepthook` ein und
zeigt dieselbe Meldung, die der Debugger zeigt. Der Prüfungsmodus wirkt
mit, weil `Fehlermeldung.als_text()` ihn schon berücksichtigt.
"""

from __future__ import annotations

import sys
import traceback
from types import TracebackType

from pcl.fehlerkatalog import fehlermeldung_erzeugen

#: Steht über der Meldung im Fenster eines GUI-Programms.
TITEL = "Das Programm wurde mit einem Fehler beendet"

#: Wenn der Katalog den Fehler nicht kennt, steht wenigstens das hier
#: davor - sonst wäre die englische Zeile darunter das Einzige.
UNBEKANNT = (
    "Zu diesem Fehler gibt es noch keine deutsche Erklärung. "
    "Die Originalmeldung von Python steht darunter."
)


def fehlertext(
    art: type[BaseException], wert: BaseException, spur: TracebackType | None
) -> str:
    """Die Wo/Was/Prüfe-Meldung als Text, oder – wenn der Katalog den
    Fehler nicht kennt – der Traceback mit einem erklärenden Satz
    davor."""
    wert.__traceback__ = spur
    meldung = fehlermeldung_erzeugen(wert)
    if meldung is not None:
        return meldung.als_text()
    return UNBEKANNT + "\n\n" + "".join(traceback.format_exception(art, wert, spur))


def _in_fenster_zeigen(text: str) -> bool:
    """Zeigt `text` in einem Fenster, wenn es überhaupt eines gibt.

    Liefert `False`, wenn keine Qt-Anwendung läuft – dann ist es ein
    Konsolenprogramm, und die Meldung gehört in die Konsole.
    """
    from PySide6.QtCore import QThread
    from PySide6.QtWidgets import QApplication, QMessageBox

    if QApplication.instance() is None:
        return False
    kasten = QMessageBox()
    kasten.setIcon(QMessageBox.Icon.Warning)
    kasten.setWindowTitle(TITEL)
    kasten.setText(TITEL)
    kasten.setInformativeText(text)
    kasten.exec()
    # Die Überschrift sagt „beendet“, also endet das Programm auch,
    # und zwar mit einem Rückgabewert, der einen Fehler meldet. Bis
    # 0.3.3 lief es weiter, und nach dem Schließen stand im Panel
    # „Programm beendet (Code 0)“. Nur aus einer laufenden
    # Ereignisschleife heraus: ohne sie merkte Qt sich das Ende und
    # beendete die nächste Schleife sofort, die jemand startet.
    if QThread.currentThread().loopLevel() > 0:
        QApplication.exit(1)
    return True


def fehler_zeigen(
    art: type[BaseException], wert: BaseException, spur: TracebackType | None
) -> None:
    """`sys.excepthook` für Schülerprogramme."""
    text = fehlertext(art, wert, spur)
    if not _in_fenster_zeigen(text):
        print(text, file=sys.stderr)


def einhaengen() -> None:
    """Hängt `fehler_zeigen` als `sys.excepthook` ein.

    Wird von `Application.run()` gerufen und von der Konsolen-Hülle in
    `ide/run/starter.py`. Bewusst nicht beim Import von `pcl`: in den
    Tests soll ein Fehler weiterhin den Test scheitern lassen.
    """
    sys.excepthook = fehler_zeigen
