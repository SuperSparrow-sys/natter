"""Application: Einstiegspunkt für pcl-Programme (Abschnitt 4.3).

    from pcl import Application
    from u_main import Form1

    app = Application()
    app.run(Form1)
"""

from __future__ import annotations

import sys
from pathlib import Path

import PySide6
from PySide6.QtCore import QLibraryInfo, QTranslator
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from pcl.fehleranzeige import einhaengen as fehleranzeige_einhaengen
from pcl.form import Form
from pcl.theme import NATTER_SYMBOL

#: Hält die geladenen Übersetzer am Leben. Ein `QTranslator`, der nur
#: in einer lokalen Variablen steht, wird wieder eingesammelt, und die
#: Texte fallen ohne Meldung ins Englische zurück.
_UEBERSETZER: list[QTranslator] = []

#: Qt-Eigenschaft der Anwendung, die die IDE setzt, wenn sie Qts
#: deutsche Texte samt eigenen Wörtern eingerichtet hat.
UEBERSETZT_EIGENSCHAFT = "natter_deutsch"

#: Unter dieser Kennung führt Windows ein Programm in der Taskleiste,
#: getrennt von der IDE mit ihrer Kennung `Natter.IDE` (Punkt 416).
ANWENDUNGS_KENNUNG = "Natter.Programm"


def _qt_deutsch_laden(app: QApplication) -> None:
    """Lädt Qts deutsche Texte: „Abbrechen“ in `input_box`,
    „Rückgängig“ im Kontextmenü eines `Edit`.

    Die IDE lädt sie für sich selbst, ein Programm läuft aber in einem
    eigenen Prozess und zeigte deshalb „Cancel“ und „Undo“. Gesucht
    wird am Ort, den Qt dafür kennt, und im Ordner `translations`
    neben PySide6; dort legt PyInstaller die Dateien in einer
    exportierten Exe ab. Fehlen sie, bleiben die Texte englisch.
    """
    # Hat die IDE im selben Prozess ihre Übersetzung schon eingerichtet
    # (`ide/deutsch.py`), bleibt es dabei. Ein zweiter Satz käme nach
    # ihr dran, würde zuerst gefragt und überginge ihre eigenen Wörter:
    # aus „Wiederholen“ wurde wieder „Wiederherstellen“ (Punkt 440).
    if _UEBERSETZER or app.property(UEBERSETZT_EIGENSCHAFT):
        return
    ordner = [
        QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath),
        str(Path(PySide6.__file__).resolve().parent / "translations"),
    ]
    for name in ("qtbase_de", "qt_de"):
        for pfad in ordner:
            uebersetzer = QTranslator()
            if uebersetzer.load(name, pfad):
                app.installTranslator(uebersetzer)
                _UEBERSETZER.append(uebersetzer)
                break


def _natter_symbol_setzen(app: QApplication) -> None:
    """Gibt dem Programm das Symbol von Natter (Punkt 415).

    Ohne Symbol zeigte Windows für ein Formular ohne eigenes `icon`
    ein leeres Fenstersymbol in Titelleiste und Taskleiste. Qt nimmt
    das Symbol der Anwendung für jedes Fenster, das kein eigenes hat;
    ein Formular mit `icon` behält seins. Ein Symbol, das schon
    gesetzt ist, bleibt.
    """
    if not app.windowIcon().isNull() or not NATTER_SYMBOL.is_file():
        return
    app.setWindowIcon(QIcon(str(NATTER_SYMBOL)))


def _anwendungs_kennung_setzen() -> None:
    """Meldet das Programm bei Windows unter eigener Kennung an, bevor
    ein Fenster entsteht (Punkt 416).

    Ohne sie ordnete die Taskleiste das Programm der `pythonw.exe` zu
    und beschriftete den Knopf mit „Python“. Eine als Exe exportierte
    Fassung bleibt ohne: sie ist ein eigenes Programm mit eigenem
    Namen und Symbol und soll nicht mit anderen Natter-Programmen in
    einer Gruppe landen.
    """
    if sys.platform != "win32" or getattr(sys, "frozen", False):
        return
    import ctypes

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            ANWENDUNGS_KENNUNG
        )
    except (AttributeError, OSError):
        pass


class Application:
    def __init__(self) -> None:
        if QApplication.instance() is None:
            _anwendungs_kennung_setzen()
        self._qapp = QApplication.instance() or QApplication(sys.argv)
        _qt_deutsch_laden(self._qapp)
        _natter_symbol_setzen(self._qapp)

    def run(self, form_klasse: type[Form]) -> int:
        """Baut das Formular auf und startet die Ereignisschleife.

        Vorher wird die Fehleranzeige eingehängt: ein GUI-Programm läuft
        ohne Konsolenfenster (Abschnitt 7.8), ein unbehandelter Fehler
        verschwand deshalb spurlos – das Fenster war einfach weg. Jetzt
        steht dieselbe dreiteilige Meldung da, die auch der Debugger
        zeigt (M12).
        """
        fehleranzeige_einhaengen()
        formular = form_klasse()
        formular.show()
        ergebnis = self._qapp.exec()
        if ergebnis != 0:
            # `main.py` ruft `app.run(Form1)` ohne `sys.exit`. Ohne das
            # hier endete ein Programm nach einem Fehler mit Code 0.
            sys.exit(ergebnis)
        return ergebnis
