"""S2: Monaco in QWebEngineView mit QWebChannel und Jedi, offline.

Siehe prototypes/s2_monaco_jedi/README.md.
"""

import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QApplication

from bridge import EditorBruecke

HIER = Path(__file__).resolve().parent


def main() -> None:
    if not (HIER / "monaco" / "vs" / "loader.js").exists():
        print(
            "Monaco fehlt: bitte den Ordner 'vs' aus monaco-editor nach "
            f"{HIER / 'monaco'}/vs kopieren (siehe README.md)."
        )
        sys.exit(1)

    app = QApplication(sys.argv)

    ansicht = QWebEngineView()
    ansicht.setWindowTitle("S2 – Monaco + Jedi (offline)")

    kanal = QWebChannel()
    bruecke = EditorBruecke()
    kanal.registerObject("bruecke", bruecke)
    ansicht.page().setWebChannel(kanal)

    ansicht.load(QUrl.fromLocalFile(str(HIER / "web" / "index.html")))
    ansicht.resize(900, 600)
    ansicht.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
