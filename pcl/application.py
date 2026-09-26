"""Application: Einstiegspunkt für pcl-Programme (Abschnitt 4.3).

    from pcl import Application
    from u_main import Form1

    app = Application()
    app.run(Form1)
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from pcl.fehleranzeige import einhaengen as fehleranzeige_einhaengen
from pcl.form import Form


class Application:
    def __init__(self) -> None:
        self._qapp = QApplication.instance() or QApplication(sys.argv)

    def run(self, form_klasse: type[Form]) -> int:
        """Baut das Formular auf und startet die Ereignisschleife.

        Vorher wird die Fehleranzeige eingehängt: ein GUI-Programm läuft
        ohne Konsolenfenster (Abschnitt 7.8), ein unbehandelter Fehler
        verschwand deshalb spurlos – das Fenster war einfach weg. Jetzt
        steht dieselbe Wo/Was/Prüfe-Meldung da, die auch der Debugger
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
