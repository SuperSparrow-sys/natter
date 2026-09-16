"""Einstiegspunkt der IDE.

Ausführen mit:

    uv run python -m ide

`erstellen()` baut Anwendung und Hauptfenster auf (testbar, ohne die
blockierende Ereignisschleife zu starten); `main()` zeigt das Fenster und
startet sie.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from ide.shell.hauptfenster import HauptFenster


def erstellen() -> tuple[QApplication, HauptFenster]:
    app = QApplication.instance() or QApplication(sys.argv)
    fenster = HauptFenster()
    return app, fenster


def main() -> int:
    app, fenster = erstellen()
    fenster.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
