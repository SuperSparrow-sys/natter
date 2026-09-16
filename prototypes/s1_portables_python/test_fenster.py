"""S1: minimales Fenster mit WebEngine, um die portable Distribution zu prüfen.

Siehe prototypes/s1_portables_python/README.md.
"""

import sys

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication


def main() -> None:
    app = QApplication(sys.argv)
    ansicht = QWebEngineView()
    ansicht.setWindowTitle("S1 – Portables Python + PySide6 + WebEngine")
    ansicht.setHtml("<h1>Es funktioniert</h1><p>Portable Python-Distribution, PySide6 mit WebEngine.</p>")
    ansicht.resize(500, 300)
    ansicht.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
