"""Zeichenfläche für Struktogramme (Abschnitt 13.5, M9 Schritt 9).

Bedient wird nicht über Koordinaten, sondern über Einfügestellen:
Wer einen Block aus der Palette gewählt hat, sieht beim Bewegen der
Maus die Lücke hervorgehoben, in die der Block käme – zwischen zwei
Blöcken, in einen leeren Zweig oder in einen Schleifenkörper. Ein Klick
setzt ihn dorthin. Dadurch kann nie ein Block „daneben“ landen und der
Rahmen bleibt zwangsläufig geschlossen.

Der Kommando-Stapel ist derselbe wie beim Klassendiagramm
(`ide/kommando.py`), Rückgängig/Wiederholen arbeiten also gleich.
"""

from __future__ import annotations

import copy
from typing import Any

from PySide6.QtCore import QPoint, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QInputDialog, QWidget

from ide.diagramm.bloecke import (
    KINDERSCHLUESSEL,
    Einfuegestelle,
    alle_bloecke,
    einfuegen,
    elternteil,
    entfernen,
    fall_entfernen,
    fall_hinzufuegen,
    ist_nachfahre,
    neuer_block,
    stelle_von,
)
from ide.diagramm.datei import Diagramm
from ide.diagramm.kommandos import SammelKommando
from ide.diagramm.stil import stil as stil_zu_namen
from ide.diagramm.struktogramm import (
    KOPFSCHLEIFEN,
    STANDARDBREITE,
    TRY_ABSCHNITTE,
    Kasten,
    struktogramm_layout,
    struktogramm_zeichnen,
)
from ide.diagramm.zoom import ZoomMischung
from ide.kommando import Kommandostapel

#: Abstand des Struktogramms von der linken oberen Ecke der Fläche.
VERSATZ = 24
#: Wie dick die hervorgehobene Einfügestelle gezeichnet wird.
MARKE = 3


class _BaumKommando:
    """Ein Schritt im Blockbaum. Weil Einfügen und Löschen exakt
    zueinander invers sind, reicht ein einziges Kommando für beides –
    `rueckwaerts` dreht nur die Richtung um."""

    def __init__(
        self, stelle: Einfuegestelle, block: dict[str, Any], rueckwaerts: bool = False
    ) -> None:
        self.stelle = stelle
        self.block = block
        self.rueckwaerts = rueckwaerts

    def tun(self) -> None:
        if self.rueckwaerts:
            self.stelle.liste().remove(self.block)
        else:
            einfuegen(self.stelle, self.block)

    def rueckgaengig(self) -> None:
        if self.rueckwaerts:
            einfuegen(self.stelle, self.block)
        else:
            self.stelle.liste().remove(self.block)


class _TextKommando:
    def __init__(self, ziel: dict[str, Any], schluessel: str, neu: Any) -> None:
        self.ziel = ziel
        self.schluessel = schluessel
        self.neu = neu
        self.alt = ziel.get(schluessel)

    def tun(self) -> None:
        self.ziel[self.schluessel] = self.neu

    def rueckgaengig(self) -> None:
        self.ziel[self.schluessel] = self.alt


class _FallKommando:
    """Fall hinzufügen bzw. entfernen (Abschnitt 13.5)."""

    def __init__(self, block: dict[str, Any], nummer: int, fall: dict | None) -> None:
        self.block = block
        self.nummer = nummer
        self.fall = fall  # None = hinzufügen, sonst der entfernte Fall

    def tun(self) -> None:
        if self.fall is None:
            self.fall = fall_hinzufuegen(self.block)
            self.nummer = len(self.block["cases"]) - 1
            self._hinzugefuegt = True
        else:
            self._hinzugefuegt = False
            fall_entfernen(self.block, self.nummer)

    def rueckgaengig(self) -> None:
        if self._hinzugefuegt:
            self.block["cases"].pop(self.nummer)
        else:
            self.block["cases"].insert(self.nummer, self.fall)


class StruktogrammCanvas(ZoomMischung, QWidget):
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
        self.ausgewaehlter_block: dict[str, Any] | None = None
        self.breite = STANDARDBREITE
        self.zoom = 1.0

        self._einfuegeart: str | None = None
        self._vorschau: Einfuegestelle | None = None
        #: Block, der mit der Maus gezogen wird, und wo der Zug begann
        self._zieh_block: dict[str, Any] | None = None
        self._zieh_start: QPoint | None = None
        self._zieht = False
        self._layout: Kasten | None = None

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self._layout_erneuern()
        self.inhaltsgroesse_anpassen()

    # -- Größe der Fläche -----------------------------------------------

    def _inhalt_in_diagrammkoordinaten(self) -> tuple[float, float]:
        """Größe des Struktogramms ohne Zoom. `inhaltsgroesse()` und
        `inhaltsgroesse_anpassen()` kommen aus `ZoomMischung` und
        multiplizieren das mit der Zoomstufe."""
        rechteck = (self._layout or self._layout_erneuern()).rechteck
        return rechteck.right() + 2 * VERSATZ, rechteck.bottom() + 2 * VERSATZ

    # -- Daten ----------------------------------------------------------

    @property
    def wurzel(self) -> dict[str, Any]:
        return self.diagramm.daten.setdefault(
            "root", {"id": "b0", "kind": "sequence", "children": []}
        )

    def _layout_erneuern(self) -> Kasten:
        self._layout = struktogramm_layout(self.diagramm.daten, self.breite)
        return self._layout

    def _nach_aenderung(self, auswahl: dict[str, Any] | None = None) -> None:
        self._layout_erneuern()
        self.inhaltsgroesse_anpassen()
        if auswahl is not None:
            self.auswaehlen(auswahl)
        self.geaendert.emit()
        self.update()

    # -- Auswahl --------------------------------------------------------

    def auswaehlen(self, block: dict[str, Any] | None) -> None:
        self.ausgewaehlter_block = block
        self.auswahl_geaendert.emit(block)
        self.update()

    def block_bei(self, x: float, y: float) -> dict[str, Any] | None:
        """Der innerste Block unter dem Punkt – sonst träfe man
        immer nur den äußeren Behälter."""
        treffer = None
        for kasten in (self._layout or self._layout_erneuern()).alle():
            if kasten.block.get("kind") == "sequence":
                continue
            if kasten.rechteck.contains(x - VERSATZ, y - VERSATZ):
                if treffer is None or _flaeche(kasten.rechteck) <= _flaeche(treffer.rechteck):
                    treffer = kasten
        return treffer.block if treffer else None

    # -- Einfügen -------------------------------------------------------

    def einfuegemodus_setzen(self, art: str | None) -> None:
        """„Block aus der Palette anklicken, dann auf die Einfügestelle
        klicken“ – gleiches Muster wie die Formen-Palette des
        Klassendiagramms. `None` bricht ab."""
        self._einfuegeart = art
        self._vorschau = None
        self.setCursor(Qt.CursorShape.CrossCursor if art else Qt.CursorShape.ArrowCursor)
        self.update()

    def einfuegestellen(self) -> list[tuple[Einfuegestelle, QRectF]]:
        """Alle Lücken des Baums mit dem Streifen, der sie anzeigt."""
        stellen: list[tuple[Einfuegestelle, QRectF]] = []
        for kasten in (self._layout or self._layout_erneuern()).alle():
            block = kasten.block
            art = block.get("kind")
            if art == "multi_branch":
                for nummer, bereich in enumerate(b for _, b in kasten.zweige):
                    stellen.extend(
                        self._stellen_einer_liste(
                            block,
                            "children",
                            (block.get("cases") or [])[nummer].get("children") or [],
                            bereich,
                            kasten,
                            fall=nummer,
                        )
                    )
            elif art == "branch":
                for schluessel, (_, bereich) in zip(
                    ("then", "else"), kasten.zweige, strict=False
                ):
                    stellen.extend(
                        self._stellen_einer_liste(
                            block, schluessel, block.get(schluessel) or [], bereich, kasten
                        )
                    )
            elif art == "parallel":
                for nummer, (_, bereich) in enumerate(kasten.zweige):
                    stellen.extend(
                        self._stellen_einer_liste(
                            block,
                            "branches",
                            (block.get("branches") or [])[nummer] or [],
                            bereich,
                            kasten,
                            fall=nummer,
                        )
                    )
            elif art == "try":
                for (schluessel, _), (_, bereich) in zip(
                    TRY_ABSCHNITTE, kasten.zweige, strict=False
                ):
                    stellen.extend(
                        self._stellen_einer_liste(
                            block, schluessel, block.get(schluessel) or [], bereich, kasten
                        )
                    )
            elif art in ("sequence", "foot_loop", *KOPFSCHLEIFEN):
                bereich = kasten.rechteck if art == "sequence" else _koerperbereich(kasten)
                stellen.extend(
                    self._stellen_einer_liste(
                        block, "children", block.get("children") or [], bereich, kasten
                    )
                )
        return stellen

    def _stellen_einer_liste(
        self,
        eltern: dict[str, Any],
        schluessel: str,
        bloecke: list[dict[str, Any]],
        bereich: QRectF,
        kasten: Kasten,
        fall: int | None = None,
    ) -> list[tuple[Einfuegestelle, QRectF]]:
        if not bloecke:
            # Leerer Zweig/Körper: die ganze Fläche ist die Einfügestelle
            return [(Einfuegestelle(eltern, schluessel, 0, fall), QRectF(bereich))]

        kaesten = [k for k in kasten.kinder if any(k.block is b for b in bloecke)]
        kaesten.sort(key=lambda k: k.rechteck.top())
        stellen = []
        for index, kind in enumerate(kaesten):
            stellen.append(
                (
                    Einfuegestelle(eltern, schluessel, index, fall),
                    QRectF(
                        kind.rechteck.left(),
                        kind.rechteck.top() - MARKE,
                        kind.rechteck.width(),
                        2 * MARKE,
                    ),
                )
            )
        letzter = kaesten[-1]
        stellen.append(
            (
                Einfuegestelle(eltern, schluessel, len(kaesten), fall),
                QRectF(
                    letzter.rechteck.left(),
                    letzter.rechteck.bottom() - MARKE,
                    letzter.rechteck.width(),
                    2 * MARKE,
                ),
            )
        )
        return stellen

    def stelle_bei(self, x: float, y: float) -> Einfuegestelle | None:
        """Die Einfügestelle, die dem Punkt am nächsten liegt. Leere
        Flächen gewinnen nur, wenn wirklich hineingezeigt wird."""
        punkt_x, punkt_y = x - VERSATZ, y - VERSATZ
        beste: tuple[float, Einfuegestelle] | None = None
        for stelle, bereich in self.einfuegestellen():
            if not (bereich.left() <= punkt_x <= bereich.right()):
                continue
            abstand = abs(bereich.center().y() - punkt_y)
            if bereich.contains(punkt_x, punkt_y):
                abstand = 0 if bereich.height() <= 4 * MARKE else abstand
            elif abstand > 3 * MARKE:
                continue
            if beste is None or abstand < beste[0]:
                beste = (abstand, stelle)
        return beste[1] if beste else None

    def block_einfuegen(self, art: str, stelle: Einfuegestelle) -> dict[str, Any]:
        block = neuer_block(self.diagramm.daten, art)
        self.kommandos.ausfuehren(_BaumKommando(stelle, block))
        self._nach_aenderung(block)
        return block

    # -- Bearbeiten -----------------------------------------------------

    def loeschen(self, block: dict[str, Any] | None = None) -> None:
        block = block or self.ausgewaehlter_block
        if block is None or block is self.wurzel:
            return
        stelle = entfernen(self.diagramm.daten, block)
        if stelle is None:
            return
        # Schon entfernt – als Kommando nachtragen, damit „Rückgängig“
        # den Block wieder an genau dieselbe Stelle setzt.
        einfuegen(stelle, block)
        self.kommandos.ausfuehren(_BaumKommando(stelle, block, rueckwaerts=True))
        self.ausgewaehlter_block = None
        self._nach_aenderung()
        self.auswahl_geaendert.emit(None)

    def text_setzen(self, block: dict[str, Any], text: str) -> None:
        if block.get("text", "") == text:
            return
        self.kommandos.ausfuehren(_TextKommando(block, "text", text))
        self._nach_aenderung()

    def bearbeiten(self, block: dict[str, Any] | None = None) -> None:
        """Beschriftung des Blocks ändern. Bewusst ein kleiner Dialog
        statt eines Feldes direkt im Block: Blöcke sind oft nur eine
        Zeile hoch und stehen dicht an dicht."""
        block = block or self.ausgewaehlter_block
        if block is None or block is self.wurzel:
            return
        text, ok = QInputDialog.getText(
            self, "Block beschriften", "Text:", text=str(block.get("text", ""))
        )
        if ok:
            self.text_setzen(block, text)

    def fall_hinzufuegen(self, block: dict[str, Any] | None = None) -> None:
        block = block or self.ausgewaehlter_block
        if block is None or block.get("kind") != "multi_branch":
            return
        self.kommandos.ausfuehren(_FallKommando(block, 0, None))
        self._nach_aenderung()

    def fall_entfernen(self, block: dict[str, Any] | None = None) -> None:
        block = block or self.ausgewaehlter_block
        if block is None or block.get("kind") != "multi_branch":
            return
        faelle = block.get("cases") or []
        if len(faelle) <= 1:
            return
        self.kommandos.ausfuehren(_FallKommando(block, len(faelle) - 1, faelle[-1]))
        self._nach_aenderung()

    def rueckgaengig(self) -> None:
        self.kommandos.rueckgaengig()
        self._auswahl_bereinigen()
        self._nach_aenderung()

    def wiederholen(self) -> None:
        self.kommandos.wiederholen()
        self._auswahl_bereinigen()
        self._nach_aenderung()

    def _auswahl_bereinigen(self) -> None:
        """Nach Undo/Redo kann der ausgewählte Block aus dem Baum
        verschwunden sein."""
        if self.ausgewaehlter_block is None:
            return
        if not any(b is self.ausgewaehlter_block for b in alle_bloecke(self.diagramm.daten)):
            self.ausgewaehlter_block = None
            self.auswahl_geaendert.emit(None)

    # -- Blöcke mit der Maus verschieben (Schritt 9) ---------------------

    #: Ab wie vielen Pixeln ein Ziehen beginnt. Ohne diese Schwelle
    #: würde jeder Klick, bei dem die Hand ein wenig zittert, schon als
    #: Verschieben gelten.
    ZIEHSCHWELLE = 6

    def zielstelle_beim_ziehen(self, x: float, y: float) -> Einfuegestelle | None:
        """Wo ein gezogener Block landen würde.

        `stelle_bei()` trifft nur die schmalen Lücken zwischen den
        Blöcken – beim Einfügen aus der Palette zielt man genau dorthin.
        Beim Ziehen ist das zu wenig: man lässt den Block über einem
        anderen los, nicht in der Fuge. Deshalb hier zusätzlich: liegt
        der Zeiger in der oberen Hälfte eines Blocks, kommt der
        gezogene davor, sonst dahinter.
        """
        genau = self.stelle_bei(x, y)
        if genau is not None:
            return genau

        unter_dem_zeiger = self.block_bei(x, y)
        if unter_dem_zeiger is None:
            return None
        stelle = stelle_von(self.diagramm.daten, unter_dem_zeiger)
        if stelle is None:
            return None
        kasten = next(
            (k for k in (self._layout or self._layout_erneuern()).alle()
             if k.block is unter_dem_zeiger),
            None,
        )
        if kasten is None:
            return None
        obere_haelfte = (y - VERSATZ) < kasten.rechteck.center().y()
        index = stelle.index if obere_haelfte else stelle.index + 1
        return Einfuegestelle(stelle.eltern, stelle.schluessel, index, stelle.fall)

    def verschieben_moeglich(
        self, block: dict[str, Any], ziel: Einfuegestelle | None
    ) -> Einfuegestelle | None:
        """Prüft ein Ziel und rechnet es auf den Stand nach dem
        Herausnehmen um. Liefert `None`, wenn dort nichts abzulegen ist.

        Drei Fälle sind abzulehnen:

        * ein Block in sich selbst oder in einen seiner eigenen Zweige –
          das ergäbe einen Kreis, und der Baum hätte kein Ende mehr
        * genau die Stelle, an der der Block ohnehin schon steht – das
          wäre ein Undo-Schritt, der nichts tut
        * kein Ziel unter der Maus
        """
        if ziel is None:
            return None
        if ziel.eltern is block or ist_nachfahre(block, ziel.eltern):
            return None

        alt = stelle_von(self.diagramm.daten, block)
        if alt is None:
            return None

        gleiche_liste = (
            ziel.eltern is alt.eltern
            and ziel.schluessel == alt.schluessel
            and ziel.fall == alt.fall
        )
        if gleiche_liste:
            # Die Zielnummer zählt den Block noch mit, der gerade
            # herausgenommen wird - alles dahinter rutscht eine Stelle
            # nach vorn.
            index = ziel.index - 1 if ziel.index > alt.index else ziel.index
            if index == alt.index:
                return None
            ziel = Einfuegestelle(ziel.eltern, ziel.schluessel, index, ziel.fall)
        return ziel

    def block_verschieben(
        self, block: dict[str, Any], ziel: Einfuegestelle | None
    ) -> bool:
        """Verschiebt `block` an die Einfügestelle `ziel` – Herausnehmen
        und Einsetzen zusammen als ein Undo-Schritt."""
        stelle = self.verschieben_moeglich(block, ziel)
        if stelle is None:
            return False
        alt = stelle_von(self.diagramm.daten, block)
        self.kommandos.ausfuehren(
            SammelKommando(
                [
                    _BaumKommando(alt, block, rueckwaerts=True),
                    _BaumKommando(stelle, block),
                ]
            )
        )
        self._nach_aenderung(block)
        return True

    def block_kopieren(
        self, block: dict[str, Any], ziel: Einfuegestelle | None
    ) -> dict[str, Any] | None:
        """Wie `block_verschieben`, aber das Original bleibt stehen
        (Strg beim Ziehen). Die Kopie bekommt durchweg neue Kennungen –
        zwei Blöcke mit derselben `id` würden die Auswahl
        durcheinanderbringen."""
        if ziel is None or ziel.eltern is block or ist_nachfahre(block, ziel.eltern):
            return None
        kopie = self._mit_neuen_kennungen(copy.deepcopy(block))
        self.kommandos.ausfuehren(_BaumKommando(ziel, kopie))
        self._nach_aenderung(kopie)
        return kopie

    def _mit_neuen_kennungen(self, block: dict[str, Any]) -> dict[str, Any]:
        vergeben = {vorhanden.get("id") for vorhanden in alle_bloecke(self.diagramm.daten)}

        def neue_kennung() -> str:
            nummer = 1
            while f"b{nummer}" in vergeben:
                nummer += 1
            vergeben.add(f"b{nummer}")
            return f"b{nummer}"

        def durchgehen(eintrag: dict[str, Any]) -> dict[str, Any]:
            eintrag["id"] = neue_kennung()
            for schluessel in KINDERSCHLUESSEL:
                for kind in eintrag.get(schluessel) or []:
                    durchgehen(kind)
            for fall in eintrag.get("cases") or []:
                for kind in fall.get("children") or []:
                    durchgehen(kind)
            for strang in eintrag.get("branches") or []:
                for kind in strang:
                    durchgehen(kind)
            return eintrag

        return durchgehen(block)

    # -- Maus und Tastatur ----------------------------------------------

    def mousePressEvent(self, ereignis: QMouseEvent) -> None:
        punkt = self._diagrammpunkt(ereignis)
        if self._einfuegeart is not None:
            stelle = self.stelle_bei(punkt.x(), punkt.y())
            if stelle is not None:
                self.block_einfuegen(self._einfuegeart, stelle)
            self.einfuegemodus_setzen(None)
            return
        block = self.block_bei(punkt.x(), punkt.y())
        self.auswaehlen(block)
        # Noch nicht ziehen: erst ab `ZIEHSCHWELLE` Pixeln. Sonst würde
        # jeder Klick, bei dem die Hand ein wenig zittert, schon als
        # Verschieben gelten.
        self._zieh_block = block
        self._zieh_start = punkt
        self._zieht = False

    def mouseMoveEvent(self, ereignis: QMouseEvent) -> None:
        punkt = self._diagrammpunkt(ereignis)

        if self._einfuegeart is not None:
            self._vorschau = self.stelle_bei(punkt.x(), punkt.y())
            self.update()
            return

        if self._zieh_block is None or self._zieh_start is None:
            return
        if not self._zieht:
            weit_genug = (
                abs(punkt.x() - self._zieh_start.x()) >= self.ZIEHSCHWELLE
                or abs(punkt.y() - self._zieh_start.y()) >= self.ZIEHSCHWELLE
            )
            if not weit_genug:
                return
            self._zieht = True
            self.setCursor(Qt.CursorShape.DragMoveCursor)

        # Nur Stellen anzeigen, an denen der Block wirklich landen kann -
        # sonst leuchtet eine Marke auf, und beim Loslassen passiert
        # nichts.
        ziel = self.zielstelle_beim_ziehen(punkt.x(), punkt.y())
        self._vorschau = (
            ziel if self.verschieben_moeglich(self._zieh_block, ziel) else None
        )
        self.update()

    def mouseReleaseEvent(self, ereignis: QMouseEvent) -> None:
        block, zog = self._zieh_block, self._zieht
        self._zieh_block = None
        self._zieh_start = None
        self._zieht = False
        self._vorschau = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        if block is None or not zog:
            self.update()
            return

        punkt = self._diagrammpunkt(ereignis)
        ziel = self.zielstelle_beim_ziehen(punkt.x(), punkt.y())
        if ereignis.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.block_kopieren(block, ziel)
        else:
            self.block_verschieben(block, ziel)
        self.update()

    def mouseDoubleClickEvent(self, ereignis: QMouseEvent) -> None:
        punkt = self._diagrammpunkt(ereignis)
        block = self.block_bei(punkt.x(), punkt.y())
        if block is not None:
            self.auswaehlen(block)
            self.bearbeiten(block)

    def keyPressEvent(self, ereignis: QKeyEvent) -> None:
        if not self._tastatur_verarbeiten(ereignis):
            super().keyPressEvent(ereignis)

    def _tastatur_verarbeiten(self, ereignis: QKeyEvent) -> bool:
        taste = ereignis.key()
        if taste == Qt.Key.Key_Escape and self._einfuegeart is not None:
            self.einfuegemodus_setzen(None)
            return True
        if taste == Qt.Key.Key_Delete:
            self.loeschen()
            return True
        if taste == Qt.Key.Key_F2:
            self.bearbeiten()
            return True
        if taste == Qt.Key.Key_Return and self.ausgewaehlter_block is not None:
            # Wie im Quelltexteditor: Enter legt eine Anweisung darunter an
            gefunden = elternteil(self.diagramm.daten, self.ausgewaehlter_block)
            if gefunden is not None:
                eltern, liste = gefunden
                index = next(
                    i for i, b in enumerate(liste) if b is self.ausgewaehlter_block
                )
                schluessel, fall = _schluessel(eltern, liste)
                self.block_einfuegen(
                    "statement", Einfuegestelle(eltern, schluessel, index + 1, fall)
                )
            return True
        return False

    # -- Zeichnen -------------------------------------------------------

    def paintEvent(self, ereignis: QPaintEvent) -> None:
        stil = stil_zu_namen(self.diagramm.stil)
        maler = QPainter(self)
        maler.fillRect(self.rect(), QColor(stil.hintergrund))
        maler.scale(self.zoom, self.zoom)
        maler.translate(VERSATZ, VERSATZ)

        self._layout = struktogramm_zeichnen(
            maler, self.diagramm.daten, stil, self.breite, self.ausgewaehlter_block
        )

        if self._vorschau is not None:
            for stelle, bereich in self.einfuegestellen():
                if stelle == self._vorschau:
                    stift = QPen(QColor(stil.akzent))
                    stift.setWidth(MARKE)
                    maler.setPen(stift)
                    maler.setBrush(Qt.BrushStyle.NoBrush)
                    if bereich.height() <= 4 * MARKE:
                        maler.drawLine(
                            bereich.left(),
                            bereich.center().y(),
                            bereich.right(),
                            bereich.center().y(),
                        )
                    else:
                        maler.drawRect(bereich.adjusted(2, 2, -2, -2))
                    break


def _flaeche(rechteck: QRectF) -> float:
    return rechteck.width() * rechteck.height()


def _koerperbereich(kasten: Kasten) -> QRectF:
    """Der eingerückte Teil einer Schleife – dort hinein wird
    eingefügt, nicht in den Schleifenkopf."""
    if kasten.block.get("kind") == "foot_loop":
        return QRectF(
            kasten.rechteck.left(),
            kasten.rechteck.top(),
            kasten.rechteck.width(),
            kasten.kopf.top() - kasten.rechteck.top(),
        )
    return QRectF(
        kasten.rechteck.left(),
        kasten.kopf.bottom(),
        kasten.rechteck.width(),
        kasten.rechteck.bottom() - kasten.kopf.bottom(),
    )


def _schluessel(eltern: dict[str, Any], liste: list) -> tuple[str, int | None]:
    for schluessel in KINDERSCHLUESSEL:
        if eltern.get(schluessel) is liste:
            return schluessel, None
    for nummer, fall in enumerate(eltern.get("cases") or []):
        if fall.get("children") is liste:
            return "children", nummer
    for nummer, strang in enumerate(eltern.get("branches") or []):
        if strang is liste:
            return "branches", nummer
    return "children", None
