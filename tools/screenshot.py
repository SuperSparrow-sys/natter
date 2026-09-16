"""Rendert das `HauptFenster` (optional mit geladenem Projekt/Designer-Tab)
offscreen und speichert es als PNG – ohne sichtbares Fenster, auch ohne
angemeldete Windows-Desktopsitzung.

`QT_QPA_PLATFORM=offscreen` findet unter Windows von sich aus keine
Schriftarten (`QFontDatabase.families()` bleibt leer, Text wird zu
Kästchen bzw. bekommt falsche Glyphen einzelner Buchstaben) – siehe
AGENTS.md, Abschnitt „Tests“. Dieses Skript setzt `QT_QPA_FONTDIR` und
eine konkrete Schriftart deshalb selbst.

Beispiele:
    uv run python -m tools.screenshot leer.png
    uv run python -m tools.screenshot ampel.png \
        --projekt beispielprojekte/Ampel/ampel.natter \
        --designer beispielprojekte/Ampel/u_main.pfm

Achtung bei `--designer`: wie in der echten IDE schreibt jede Änderung im
Designer automatisch in die `.pfm` zurück. Dieses Skript ändert selbst
nichts (öffnet nur), aber bei eingecheckten Beispielprojekten lieber eine
Kopie angeben statt des Originalpfads (siehe AGENTS.md).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

from PySide6.QtGui import QFont  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from ide.shell.hauptfenster import HauptFenster  # noqa: E402


def screenshot_erzeugen(
    ziel: Path,
    *,
    projekt: Path | None = None,
    designer: Path | None = None,
    breite: int = 1600,
    hoehe: int = 950,
) -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 9))

    fenster = HauptFenster()
    fenster.resize(breite, hoehe)
    fenster.show()

    if projekt is not None:
        fenster.projekt_oeffnen(Path(projekt))
    if designer is not None:
        fenster.designer_oeffnen(Path(designer))

    app.processEvents()
    app.processEvents()

    ziel = Path(ziel)
    ziel.parent.mkdir(parents=True, exist_ok=True)
    if not fenster.grab().save(str(ziel)):
        raise RuntimeError(f"Screenshot konnte nicht unter {ziel} gespeichert werden.")


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ziel", type=Path, help="Zieldatei, z. B. screenshot.png")
    parser.add_argument("--projekt", type=Path, default=None, help="Pfad zu einer .natter-Datei")
    parser.add_argument("--designer", type=Path, default=None, help="Pfad zu einer .pfm-Datei")
    parser.add_argument("--breite", type=int, default=1600)
    parser.add_argument("--hoehe", type=int, default=950)
    argumente = parser.parse_args()

    screenshot_erzeugen(
        argumente.ziel,
        projekt=argumente.projekt,
        designer=argumente.designer,
        breite=argumente.breite,
        hoehe=argumente.hoehe,
    )
    print(f"gespeichert: {argumente.ziel}")


if __name__ == "__main__":
    _main()
