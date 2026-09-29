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


def _qt_deutsch_laden(app: QApplication) -> None:
    """Lädt Qts deutsche Texte: „Abbrechen“ in `input_box`,
    „Rückgängig“ im Kontextmenü eines `Edit`.

    Die IDE lädt sie für sich selbst, ein Programm läuft aber in einem
    eigenen Prozess und zeigte deshalb „Cancel“ und „Undo“. Gesucht
    wird am Ort, den Qt dafür kennt, und im Ordner `translations`
    neben PySide6; dort legt PyInstaller die Dateien in einer
    exportierten Exe ab. Fehlen sie, bleiben die Texte englisch.
    """
    if _UEBERSETZER:
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


class Application:
    def __init__(self) -> None:
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
