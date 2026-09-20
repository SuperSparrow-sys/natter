"""Zeichenfläche des Entscheidungstabellen-Editors (Abschnitt 13.5,
M9 Schritt 10).

Bedient wird direkt in der Tabelle: ein Klick auf eine Zelle schaltet
ihren Wert weiter (`J → N → * → leer` im Bedingungsteil, `X → leer` im
Aktionsteil), ein Doppelklick auf die Textspalte beschriftet die Zeile.
Regel-Spalten und Zeilen kommen über das Menü dazu.

Bewusst ohne automatische Zusammenfassung oder
Vollständigkeitsprüfung von Regeln – im Konzept so festgehalten.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPaintEvent
from PySide6.QtWidgets import QInputDialog, QWidget

from ide.diagramm.datei import Diagramm
from ide.diagramm.stil import stil as stil_zu_namen
from ide.diagramm.tabelle import (
    AKTIONSWERTE,
    BEDINGUNGSWERTE,
    Zelle,
    regelanzahl,
    tabelle_zeichnen,
    tabellengroesse,
    wert,
    zelle_bei,
)
from ide.diagramm.zoom import ZoomMischung
from ide.kommando import Kommandostapel

VERSATZ = 24

TEIL_BESCHRIFTUNGEN = {"conditions": "Bedingung", "actions": "Aktion"}


class _ZellenKommando:
    def __init__(self, zeile: dict[str, Any], spalte: int, neu: str) -> None:
        self.zeile = zeile
        self.spalte = spalte
        self.neu = neu
        self.alt = wert(zeile, spalte)

    def _setzen(self, inhalt: str) -> None:
        werte = self.zeile.setdefault("values", [])
        while len(werte) <= self.spalte:
            werte.append("")
        werte[self.spalte] = inhalt

    def tun(self) -> None:
        self._setzen(self.neu)

    def rueckgaengig(self) -> None:
        self._setzen(self.alt)


class _TextKommando:
    def __init__(self, zeile: dict[str, Any], neu: str) -> None:
        self.zeile = zeile
        self.neu = neu
        self.alt = zeile.get("text", "")

    def tun(self) -> None:
        self.zeile["text"] = self.neu

    def rueckgaengig(self) -> None:
        self.zeile["text"] = self.alt


class _ZeilenKommando:
    """Zeile einfügen bzw. entfernen – beides ist dieselbe Operation in
    zwei Richtungen."""

    def __init__(
        self,
        liste: list[dict[str, Any]],
        index: int,
        zeile: dict[str, Any],
        entfernen: bool = False,
    ) -> None:
        self.liste = liste
        self.index = index
        self.zeile = zeile
        self.entfernen = entfernen

    def tun(self) -> None:
        if self.entfernen:
            self.liste.pop(self.index)
        else:
            self.liste.insert(self.index, self.zeile)

    def rueckgaengig(self) -> None:
        if self.entfernen:
            self.liste.insert(self.index, self.zeile)
        else:
            self.liste.pop(self.index)


class _SpaltenKommando:
    """Eine Regel-Spalte betrifft alle Zeilen beider Teile – sonst
    liefe die Tabelle auseinander."""

    def __init__(
        self,
        daten: dict[str, Any],
        index: int,
        werte: list[str] | None = None,
        entfernen: bool = False,
    ) -> None:
        self.daten = daten
        self.index = index
        self.entfernen = entfernen
        self.werte = werte or []

    def _zeilen(self) -> list[dict[str, Any]]:
        return [*(self.daten.get("conditions") or []), *(self.daten.get("actions") or [])]

    def tun(self) -> None:
        if self.entfernen:
            self.werte = []
            for zeile in self._zeilen():
                werte = zeile.setdefault("values", [])
                self.werte.append(werte.pop(self.index) if self.index < len(werte) else "")
        else:
            for zeile in self._zeilen():
                werte = zeile.setdefault("values", [])
                while len(werte) < self.index:
                    werte.append("")
                werte.insert(self.index, "")

    def rueckgaengig(self) -> None:
        if self.entfernen:
            for zeile, alt in zip(self._zeilen(), self.werte, strict=False):
                zeile.setdefault("values", []).insert(self.index, alt)
        else:
            for zeile in self._zeilen():
                werte = zeile.setdefault("values", [])
                if self.index < len(werte):
                    werte.pop(self.index)


class _SpaltenTauschKommando:
    """Regel verschieben (Abschnitt 13.5: Spalten „verschieben“)."""

    def __init__(self, daten: dict[str, Any], von: int, nach: int) -> None:
        self.daten = daten
        self.von = von
        self.nach = nach

    def _tauschen(self, a: int, b: int) -> None:
        for zeile in [
            *(self.daten.get("conditions") or []),
            *(self.daten.get("actions") or []),
        ]:
            werte = zeile.setdefault("values", [])
            while len(werte) <= max(a, b):
                werte.append("")
            werte[a], werte[b] = werte[b], werte[a]

    def tun(self) -> None:
        self._tauschen(self.von, self.nach)

    def rueckgaengig(self) -> None:
        self._tauschen(self.von, self.nach)


class TabellenCanvas(ZoomMischung, QWidget):
    auswahl_geaendert = Signal(object)
    geaendert = Signal()
    #: Das Signal muss hier stehen und nicht in `ZoomMischung`:
    #: PySide6 meldet ein `Signal` nur in einer Klasse an, die
    #: wirklich von `QObject` erbt.
    zoom_geaendert = Signal(float)

    def __init__(self, diagramm: Diagramm) -> None:
        super().__init__()
        self.diagramm = diagramm
        self.kommandos = Kommandostapel()
        self.ausgewaehlte_zelle: Zelle | None = None
        self.zoom = 1.0

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.inhaltsgroesse_anpassen()

    # -- Daten ----------------------------------------------------------

    def zeilen(self, teil: str) -> list[dict[str, Any]]:
        return self.diagramm.daten.setdefault(teil, [])

    def zeile(self, zelle: Zelle) -> dict[str, Any] | None:
        liste = self.zeilen(zelle.teil)
        return liste[zelle.zeile] if 0 <= zelle.zeile < len(liste) else None

    def _nach_aenderung(self) -> None:
        self.inhaltsgroesse_anpassen()
        self.geaendert.emit()
        self.update()

    def _inhalt_in_diagrammkoordinaten(self) -> tuple[float, float]:
        """Größe der Tabelle ohne Zoom. `inhaltsgroesse()` und
        `inhaltsgroesse_anpassen()` kommen aus `ZoomMischung` und
        multiplizieren das mit der Zoomstufe."""
        breite, hoehe = tabellengroesse(self.diagramm.daten)
        return breite + 2 * VERSATZ, hoehe + 2 * VERSATZ

    # -- Auswahl --------------------------------------------------------

    def auswaehlen(self, zelle: Zelle | None) -> None:
        self.ausgewaehlte_zelle = zelle
        self.auswahl_geaendert.emit(zelle)
        self.update()

    def zelle_bei(self, x: float, y: float) -> Zelle | None:
        return zelle_bei(self.diagramm.daten, x, y, VERSATZ, VERSATZ)

    # -- Zellen schalten ------------------------------------------------

    def naechster_wert(self, zelle: Zelle) -> str:
        """Der Wert, den ein Klick als nächstes setzt."""
        werte = BEDINGUNGSWERTE if zelle.teil == "conditions" else AKTIONSWERTE
        zeile = self.zeile(zelle)
        aktuell = wert(zeile, zelle.spalte) if zeile else ""
        stelle = werte.index(aktuell) if aktuell in werte else len(werte) - 1
        return werte[(stelle + 1) % len(werte)]

    def zelle_schalten(self, zelle: Zelle) -> None:
        zeile = self.zeile(zelle)
        if zeile is None or zelle.spalte < 0:
            return
        self.kommandos.ausfuehren(
            _ZellenKommando(zeile, zelle.spalte, self.naechster_wert(zelle))
        )
        self._nach_aenderung()

    # -- Zeilen und Spalten ---------------------------------------------

    def zeile_hinzufuegen(self, teil: str, text: str = "") -> dict[str, Any]:
        liste = self.zeilen(teil)
        neue = {
            "text": text or f"Neue {TEIL_BESCHRIFTUNGEN[teil]}",
            "values": [""] * regelanzahl(self.diagramm.daten),
        }
        self.kommandos.ausfuehren(_ZeilenKommando(liste, len(liste), neue))
        self._nach_aenderung()
        return neue

    def zeile_entfernen(self, teil: str, index: int) -> None:
        liste = self.zeilen(teil)
        if not (0 <= index < len(liste)):
            return
        self.kommandos.ausfuehren(_ZeilenKommando(liste, index, liste[index], entfernen=True))
        self.ausgewaehlte_zelle = None
        self._nach_aenderung()

    def regel_hinzufuegen(self, index: int | None = None) -> None:
        stelle = regelanzahl(self.diagramm.daten) if index is None else index
        self.kommandos.ausfuehren(_SpaltenKommando(self.diagramm.daten, stelle))
        self._nach_aenderung()

    def regel_entfernen(self, index: int | None = None) -> None:
        anzahl = regelanzahl(self.diagramm.daten)
        if anzahl <= 1:
            return  # eine Tabelle ohne Regel wäre leer
        stelle = anzahl - 1 if index is None else index
        self.kommandos.ausfuehren(
            _SpaltenKommando(self.diagramm.daten, stelle, entfernen=True)
        )
        self.ausgewaehlte_zelle = None
        self._nach_aenderung()

    def regel_verschieben(self, von: int, nach: int) -> None:
        anzahl = regelanzahl(self.diagramm.daten)
        if not (0 <= von < anzahl and 0 <= nach < anzahl) or von == nach:
            return
        self.kommandos.ausfuehren(_SpaltenTauschKommando(self.diagramm.daten, von, nach))
        self._nach_aenderung()

    def text_setzen(self, zeile: dict[str, Any], text: str) -> None:
        if zeile.get("text", "") == text:
            return
        self.kommandos.ausfuehren(_TextKommando(zeile, text))
        self._nach_aenderung()

    def bearbeiten(self, zelle: Zelle | None = None) -> None:
        zelle = zelle or self.ausgewaehlte_zelle
        if zelle is None:
            return
        zeile = self.zeile(zelle)
        if zeile is None:
            return
        text, ok = QInputDialog.getText(
            self,
            f"{TEIL_BESCHRIFTUNGEN[zelle.teil]} beschriften",
            "Text:",
            text=str(zeile.get("text", "")),
        )
        if ok:
            self.text_setzen(zeile, text)

    def loeschen(self) -> None:
        """„Bearbeiten → Löschen“ entfernt die Zeile der ausgewählten
        Zelle – bei einer Tabelle gibt es nichts anderes zu löschen."""
        if self.ausgewaehlte_zelle is not None:
            self.zeile_entfernen(
                self.ausgewaehlte_zelle.teil, self.ausgewaehlte_zelle.zeile
            )

    def rueckgaengig(self) -> None:
        self.kommandos.rueckgaengig()
        self.ausgewaehlte_zelle = None
        self._nach_aenderung()

    def wiederholen(self) -> None:
        self.kommandos.wiederholen()
        self.ausgewaehlte_zelle = None
        self._nach_aenderung()

    # -- Maus und Tastatur ----------------------------------------------

    def mousePressEvent(self, ereignis: QMouseEvent) -> None:
        punkt = self._diagrammpunkt(ereignis)
        zelle = self.zelle_bei(punkt.x(), punkt.y())
        self.auswaehlen(zelle)
        if zelle is not None and zelle.spalte >= 0:
            self.zelle_schalten(zelle)

    def mouseDoubleClickEvent(self, ereignis: QMouseEvent) -> None:
        punkt = self._diagrammpunkt(ereignis)
        zelle = self.zelle_bei(punkt.x(), punkt.y())
        if zelle is not None and zelle.spalte < 0:
            self.auswaehlen(zelle)
            self.bearbeiten(zelle)

    def keyPressEvent(self, ereignis: QKeyEvent) -> None:
        if ereignis.key() == Qt.Key.Key_F2:
            self.bearbeiten()
            return
        if ereignis.key() == Qt.Key.Key_Delete:
            self.loeschen()
            return
        if ereignis.key() == Qt.Key.Key_Space and self.ausgewaehlte_zelle is not None:
            self.zelle_schalten(self.ausgewaehlte_zelle)
            return
        super().keyPressEvent(ereignis)

    # -- Zeichnen -------------------------------------------------------

    def paintEvent(self, ereignis: QPaintEvent) -> None:
        stil = stil_zu_namen(self.diagramm.stil)
        maler = QPainter(self)
        maler.fillRect(self.rect(), QColor(stil.hintergrund))
        maler.scale(self.zoom, self.zoom)
        tabelle_zeichnen(
            maler, self.diagramm.daten, stil, VERSATZ, VERSATZ, self.ausgewaehlte_zelle
        )
