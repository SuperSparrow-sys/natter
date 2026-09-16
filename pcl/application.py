"""Application: Einstiegspunkt für pcl-Programme (Abschnitt 4.3).

    from pcl import Application
    from u_main import Form1

    app = Application()
    app.run(Form1)
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from pcl.form import Form


class Application:
    def __init__(self) -> None:
        self._qapp = QApplication.instance() or QApplication(sys.argv)

    def run(self, form_klasse: type[Form]) -> int:
        formular = form_klasse()
        formular.show()
        return self._qapp.exec()
