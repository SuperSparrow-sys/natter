"""Bilder aus Dateien laden, eine SVG ohne Verweise nach außen.

Eine SVG darf auf andere Dateien verweisen (`<image href="…">`,
`url(…)`, Stylesheets, externe Entitäten), und Qt lädt sie von jedem
Pfad, auch von einem Netzpfad wie `\\\\server\\freigabe\\bild.png`.
Schon das Öffnen eines fremden Formulars im Designer baute so eine
Verbindung zu einem anderen Rechner auf, samt Anmeldung mit dem
Windows-Konto (Punkt 541). Gezeichnet wird deshalb nur, was in der
Datei selbst steht: eingebettete `data:`-Bilder und Verweise innerhalb
der Datei (`#name`).
"""

from __future__ import annotations

import re
from pathlib import Path

from PySide6.QtGui import QPixmap

#: Ein Attribut `href` oder `xlink:href` mit seinem Wert.
_VERWEIS = re.compile(
    r"""\s(?:xlink:)?href\s*=\s*(?P<q>["'])(?P<wert>.*?)(?P=q)""",
    re.IGNORECASE | re.DOTALL,
)
#: `url(…)` in einem Stilattribut oder einem `<style>`-Block.
_URL = re.compile(r"""url\(\s*(?P<q>["']?)(?P<wert>.*?)(?P=q)\s*\)""", re.IGNORECASE)
#: Anweisungen, die weitere Dateien nachladen.
_NACHLADEN = re.compile(
    r"<!DOCTYPE[^\[>]*(\[.*?\])?\s*>|<\?xml-stylesheet.*?\?>|@import[^;]*;",
    re.IGNORECASE | re.DOTALL,
)


def _innen(wert: str) -> bool:
    wert = wert.strip()
    return wert.startswith("#") or wert.lower().startswith("data:")


def svg_ohne_verweise(text: str) -> str:
    """`text` einer SVG ohne alles, was eine andere Datei lädt."""
    text = _NACHLADEN.sub("", text)
    text = _VERWEIS.sub(lambda m: m.group(0) if _innen(m.group("wert")) else "", text)
    return _URL.sub(lambda m: m.group(0) if _innen(m.group("wert")) else "none", text)


def bild_laden(pfad: str | Path) -> QPixmap:
    """Ein Bild als `QPixmap`; leer, wenn es sich nicht lesen lässt."""
    pfad = Path(pfad)
    if pfad.suffix.lower() != ".svg":
        return QPixmap(str(pfad))
    try:
        text = pfad.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return QPixmap()
    bild = QPixmap()
    bild.loadFromData(svg_ohne_verweise(text).encode("utf-8"), "SVG")
    return bild
