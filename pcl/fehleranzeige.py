"""Unbehandelte Fehler im Schülerprogramm anzeigen (M12).

Der Fehlerkatalog (`pcl/fehlerkatalog.py`) ist das didaktische Kernstück
von Natter: statt eines englischen Tracebacks eine Meldung in drei
Teilen – Wo, Was, Zu prüfen. Benutzt wurde er bis M12 aber nur
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
import threading
import traceback
from pathlib import Path
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
    """Die dreiteilige Meldung als Text, oder – wenn der Katalog den
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


def _an_debugger_geben(
    art: type[BaseException], wert: BaseException, spur: TracebackType | None
) -> None:
    """Hält unter dem Debugger (F5) an der Fehlerzeile an, wenn der
    Fehler in einer Methode steckt, die Qt aufgerufen hat (Punkt 688).

    debugpy hält nur bei einem Fehler, der bis zum äußersten Rahmen
    durchläuft. Eine Ereignismethode ruft aber Qt aus der
    Ereignisschleife; dahinter stehen noch `Application.run()` und
    `main.py`, der Fehler endet in Qt und kommt hier an. debugpy sah
    ihn nie als unbehandelt, auch ohne diesen Haken. Läuft keine
    Ereignisschleife, ist der Fehler bis nach außen gelaufen, und
    debugpy hat schon selbst angehalten."""
    debugpy = sys.modules.get("debugpy")
    if debugpy is None:
        return
    try:
        from PySide6.QtCore import QThread

        if not debugpy.is_client_connected():
            return
        if QThread.currentThread().loopLevel() == 0:
            return
        debugpy.trigger_exception_handler((art, wert, spur))
    except Exception:  # noqa: BLE001 - die Meldung danach kommt trotzdem
        pass


def fehler_zeigen(
    art: type[BaseException], wert: BaseException, spur: TracebackType | None
) -> None:
    """`sys.excepthook` für Schülerprogramme."""
    _an_debugger_geben(art, wert, spur)
    text = fehlertext(art, wert, spur)
    if not _in_fenster_zeigen(text):
        print(text, file=sys.stderr)


def _faden_fehler_zeigen(args: threading.ExceptHookArgs) -> None:
    """`threading.excepthook`: ein Fehler in einem Faden bekommt
    dieselbe Meldung wie einer im Hauptfaden (Punkt 670). Vorher kam
    Pythons Traceback samt „Did you mean“, auch im Prüfungsmodus.

    Ein Fenster gibt es dafür nicht: Qt erlaubt Fenster nur im
    Hauptfaden. Die Meldung kommt auf die Fehlerausgabe, bei einem
    Programm mit Fenster also ins Panel „Ausgabe“."""
    if issubclass(args.exc_type, SystemExit):
        return
    wert = args.exc_value
    if wert is None:
        wert = args.exc_type()
    print(
        fehlertext(args.exc_type, wert, args.exc_traceback),
        file=sys.stderr,
        flush=True,
    )


def einhaengen() -> None:
    """Hängt `fehler_zeigen` als `sys.excepthook` ein, für Fäden
    `_faden_fehler_zeigen` als `threading.excepthook`.

    Wird von `Application.run()` gerufen und von der Konsolen-Hülle in
    `ide/run/starter.py`. Bewusst nicht beim Import von `pcl`: in den
    Tests soll ein Fehler weiterhin den Test scheitern lassen.
    """
    sys.excepthook = fehler_zeigen
    threading.excepthook = _faden_fehler_zeigen


def im_projekt_gestartet() -> bool:
    """Ob das laufende Programm das Hauptprogramm eines Natter-Projekts
    ist: `__main__` stammt aus einem Ordner mit einer `.natter`.

    Unter pytest, in der IDE selbst und im Testlauf ist das nicht so;
    dort bleibt `sys.excepthook`, wie er ist."""
    datei = getattr(sys.modules.get("__main__"), "__file__", None)
    if not datei:
        return False
    try:
        return any(Path(datei).resolve().parent.glob("*.natter"))
    except OSError:
        return False


def beim_import_einhaengen() -> None:
    """Wird beim Import von `pcl` gerufen. In einem gestarteten
    Projekt hängt sich die Anzeige sofort ein, nicht erst in
    `Application.run()`: `main.py` importiert die Units vor
    `Application()`, und ein Fehler beim Laden von `u_main.py` (ein
    fehlendes Modul, eine fehlende Datei) kam bis Punkt 696 als
    englischer Traceback. Ohne Qt-Anwendung steht die Meldung auf der
    Fehlerausgabe, bei Strg+F5 also im Panel „Ausgabe“."""
    if im_projekt_gestartet():
        einhaengen()

