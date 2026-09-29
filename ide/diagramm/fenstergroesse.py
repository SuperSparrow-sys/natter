"""Startgröße der Fenster des Diagramm-Editors (Punkte 300 und 304).

Diagramm-Editor, Quelltext-Fenster und Klassendialog öffneten mit
festen Maßen. Auf 1366 × 768 bei 125 % bleiben nach Taskleiste etwa
1093 × 575 Pixel; die Fenster ragten unten heraus, samt Statuszeile
und Knöpfen. Hier wird die gewünschte Größe auf die verfügbare Fläche
des Bildschirms begrenzt und das Fenster in diese Fläche gelegt.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSettings, QSize
from PySide6.QtWidgets import QApplication, QWidget

#: Was Titelleiste und Rahmen eines Fensters ungefähr brauchen. Vor
#: dem ersten Zeigen kennt Qt die Rahmengröße noch nicht.
_RAHMEN_BREITE = 16
_RAHMEN_HOEHE = 40


def _einstellungen() -> QSettings:
    return QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Natter", "Natter-IDE"
    )


def verfuegbare_flaeche(fenster: QWidget) -> QRect | None:
    """Die Arbeitsfläche (ohne Taskleiste) des Bildschirms, auf dem das
    Elternfenster steht, sonst des Hauptbildschirms."""
    eltern = fenster.parentWidget()
    bildschirm = (
        eltern.window().screen() if eltern is not None else None
    ) or QApplication.primaryScreen()
    if bildschirm is None:
        return None
    return bildschirm.availableGeometry()


def einpassen(
    fenster: QWidget,
    breite: int,
    hoehe: int,
    schluessel: str | None = None,
) -> None:
    """Setzt `fenster` auf `breite` × `hoehe` oder auf die unter
    `schluessel` gemerkte Größe, höchstens aber auf die verfügbare
    Fläche, und legt es mittig hinein."""
    if schluessel is not None:
        gemerkt = _einstellungen().value(schluessel)
        if isinstance(gemerkt, QSize) and gemerkt.isValid():
            breite, hoehe = gemerkt.width(), gemerkt.height()
    flaeche = verfuegbare_flaeche(fenster)
    if flaeche is None or flaeche.isEmpty():
        fenster.resize(breite, hoehe)
        return
    breite = max(200, min(breite, flaeche.width() - _RAHMEN_BREITE))
    hoehe = max(150, min(hoehe, flaeche.height() - _RAHMEN_HOEHE))
    fenster.resize(breite, hoehe)
    fenster.move(
        flaeche.x() + (flaeche.width() - breite - _RAHMEN_BREITE) // 2,
        flaeche.y() + (flaeche.height() - hoehe - _RAHMEN_HOEHE) // 2,
    )


def merken(fenster: QWidget, schluessel: str) -> None:
    """Merkt die Größe von `fenster` für das nächste `einpassen`."""
    _einstellungen().setValue(schluessel, fenster.size())
