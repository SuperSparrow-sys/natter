"""Tests für die Bildvorschau (Abschnitt 11.4). Siehe
docs/arbeitspakete/M5.md, Schritt 7. Headless.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QPixmap

from ide.viewers import BildVorschau


def _bild_erzeugen(pfad: Path, breite: int, hoehe: int) -> None:
    pixmap = QPixmap(breite, hoehe)
    pixmap.fill(QColor("red"))
    pixmap.save(str(pfad), "PNG")


def test_bildvorschau_zeigt_abmessungen(tmp_path: Path) -> None:
    datei = tmp_path / "bild.png"
    _bild_erzeugen(datei, 40, 20)

    vorschau = BildVorschau(datei)

    assert vorschau.breite == 40
    assert vorschau.hoehe == 20
    assert "40" in vorschau._info_label.text()
    assert "20" in vorschau._info_label.text()


def test_bildvorschau_skaliert_grosse_bilder_herunter(tmp_path: Path) -> None:
    datei = tmp_path / "gross.png"
    _bild_erzeugen(datei, 2000, 1000)

    vorschau = BildVorschau(datei)

    angezeigt = vorschau._bild_label.pixmap()
    assert angezeigt.width() <= 600
    assert angezeigt.height() <= 600
