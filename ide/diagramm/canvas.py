"""DiagrammCanvas: Zeichenfläche des Diagramm-Editors (Abschnitt 13.2,
13.3).

Anders als der Formular-Designer (`ide/designer/canvas.py`, ein echtes
`QWidget` je Komponente) malt der Diagramm-Editor alle Formen selbst in
einem einzigen Widget: Diagrammformen sind keine bedienbaren
Steuerelemente, es können sehr viele werden, und Verbindungen (Schritt
4) lassen sich ohnehin nur frei zeichnen.

Stand M9, Schritt 4: anzeigen, platzieren, auswählen, verschieben,
Größe ändern, löschen, duplizieren und verbinden (sieben UML-
Verbindungsarten, Enden folgen beim Verschieben automatisch, weil sie
beim Zeichnen aus den Formen berechnet werden) – alles über den Kommando-Stapel,
also unbegrenzt rückgängig machbar (Abschnitt 13.3). Beim Ziehen wird
am Raster **und** an Kanten/Mitten anderer Formen eingerastet, mit
Hilfslinien als Rückmeldung.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QWidget

from ide.diagramm.datei import Diagramm
from ide.diagramm.formen import MINDESTGROESSE, form_art, verbindungs_art
from ide.diagramm.kommandos import (
    EinfuegenKommando,
    LoeschenKommando,
    SammelKommando,
    WerteKommando,
)
from ide.diagramm.stil import stil as stil_zu_namen
from ide.diagramm.zeichnen import (
    abstand_zur_verbindung,
    anfasser_punkte,
    form_rechteck,
    form_zeichnen,
    mindesthoehe,
    verbindung_zeichnen,
    verbindungsbeschriftungen_zeichnen,
)
from ide.kommando import Kommandostapel

RASTER = 8
#: Abstand, ab dem beim Ziehen an einer fremden Kante/Mitte eingerastet
#: wird (Abschnitt 13.3: „Einrasten … an Kanten/Mitten anderer Formen“).
FANGABSTAND = 6
#: Klickradius um einen Größenanfasser herum.
ANFASSER_RADIUS = 6

#: Anfasser-Reihenfolge wie in `zeichnen.anfasser_punkte`.
_ANFASSER_NAMEN = ("nw", "n", "ne", "e", "se", "s", "sw", "w")
#: Name -> (links_je_dx, breite_je_dx, oben_je_dy, hoehe_je_dy) – wie im
#: Formular-Designer, damit sich beide Editoren gleich anfühlen.
_ANFASSER_VERHALTEN: dict[str, tuple[int, int, int, int]] = {
    "nw": (1, -1, 1, -1),
    "n": (0, 0, 1, -1),
    "ne": (0, 1, 1, -1),
    "e": (0, 1, 0, 0),
    "se": (0, 1, 0, 1),
    "s": (0, 0, 0, 1),
    "sw": (1, -1, 0, 1),
    "w": (1, -1, 0, 0),
}


def _am_raster(wert: float) -> int:
    return int(round(wert / RASTER) * RASTER)


def _raster_aufrunden(wert: float) -> int:
    """Wie `_am_raster`, aber nie nach unten – für Mindestgrößen, die
    sonst genau unter den nötigen Wert gerundet würden."""
    return int(-(-wert // RASTER) * RASTER)


class DiagrammCanvas(QWidget):
    auswahl_geaendert = Signal(object)  # das ausgewählte shape-dict oder None
    geaendert = Signal()

    def __init__(self, diagramm: Diagramm) -> None:
        super().__init__()
        self.diagramm = diagramm
        self.kommandos = Kommandostapel()
        self.ausgewaehlte_form: dict[str, Any] | None = None
        self.raster_sichtbar = True

        self.ausgewaehlte_verbindung: dict[str, Any] | None = None
        self._platzierungs_kind: str | None = None
        self._verbindungs_kind: str | None = None
        self._verbindungs_quelle: dict[str, Any] | None = None
        self._zieh_form: dict[str, Any] | None = None
        self._zieh_start: QPoint | None = None
        self._zieh_startwerte: dict[str, Any] | None = None
        self._anfasser: str | None = None
        self._hilfslinien: list[tuple[str, float]] = []

        self.setMinimumSize(640, 480)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

    # -- Daten ----------------------------------------------------------

    @property
    def formen(self) -> list[dict[str, Any]]:
        return self.diagramm.daten.setdefault("shapes", [])

    @property
    def verbindungen(self) -> list[dict[str, Any]]:
        return self.diagramm.daten.setdefault("connectors", [])

    def _neue_id(self) -> str:
        vorhandene = {form.get("id") for form in self.formen}
        nummer = 1
        while f"s{nummer}" in vorhandene:
            nummer += 1
        return f"s{nummer}"

    def _neue_verbindungs_id(self) -> str:
        vorhandene = {verbindung.get("id") for verbindung in self.verbindungen}
        nummer = 1
        while f"c{nummer}" in vorhandene:
            nummer += 1
        return f"c{nummer}"

    def form_mit_id(self, kennung: str) -> dict[str, Any] | None:
        for form in self.formen:
            if form.get("id") == kennung:
                return form
        return None

    def verbindungen_von(self, form: dict[str, Any]) -> list[dict[str, Any]]:
        """Alle Verbindungen, die an `form` hängen – beim Löschen einer
        Form müssen sie mit weg, sonst blieben Verweise ins Leere."""
        kennung = form.get("id")
        return [
            verbindung
            for verbindung in self.verbindungen
            if kennung in (verbindung.get("from"), verbindung.get("to"))
        ]

    def _nach_aenderung(self, auswahl: dict[str, Any] | None = None) -> None:
        if auswahl is not None:
            self._auswaehlen(auswahl)
        self.geaendert.emit()
        self.update()

    # -- Platzieren -----------------------------------------------------

    def platzierungsmodus_setzen(self, kind: str | None) -> None:
        """„Form aus der Palette anklicken, dann auf die Fläche klicken“
        (Abschnitt 13.3) – gleiches Muster wie die Komponentenpalette im
        Formular-Designer. `None` bricht ab."""
        self._platzierungs_kind = kind
        if kind is not None:
            self._verbindungs_kind = None
            self._verbindungs_quelle = None
        self.setCursor(Qt.CursorShape.CrossCursor if kind else Qt.CursorShape.ArrowCursor)

    def form_platzieren(self, kind: str, x: float, y: float) -> dict[str, Any]:
        """Legt eine neue Form an. `x`/`y` ist die Mitte (der Klickpunkt),
        damit die Form dort erscheint, wohin geklickt wurde – am Raster
        eingerastet (Abschnitt 13.3)."""
        art = form_art(kind)
        form: dict[str, Any] = {
            "id": self._neue_id(),
            "kind": kind,
            "x": _am_raster(x - art.breite / 2),
            "y": _am_raster(y - art.hoehe / 2),
            "w": art.breite,
            "h": art.hoehe,
            "text": dict(art.standardtext),
        }
        if kind == "abstract_class":
            form["abstract"] = True
        form["h"] = max(form["h"], _raster_aufrunden(mindesthoehe(form)))

        self.kommandos.ausfuehren(EinfuegenKommando(self.formen, form))
        self._nach_aenderung(form)
        return form

    # -- Verbinden ------------------------------------------------------

    def verbindungsmodus_setzen(self, kind: str | None) -> None:
        """„Verbindung aus der Palette wählen, von Form zu Form ziehen“
        (Abschnitt 13.3) – hier als zwei Klicks umgesetzt: erst Quelle,
        dann Ziel, passend zum Platzieren von Formen."""
        self._verbindungs_kind = kind
        self._verbindungs_quelle = None
        if kind is not None:
            self._platzierungs_kind = None
        self.setCursor(Qt.CursorShape.CrossCursor if kind else Qt.CursorShape.ArrowCursor)

    def verbindung_erstellen(
        self, kind: str, quelle: dict[str, Any], ziel: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Legt eine Verbindung zwischen zwei Formen an. Eine Form mit
        sich selbst zu verbinden ergibt hier keine sinnvolle
        Darstellung und wird abgelehnt."""
        verbindungs_art(kind)  # prüft die Art, wirft bei Unbekanntem
        if quelle is ziel:
            return None

        verbindung: dict[str, Any] = {
            "id": self._neue_verbindungs_id(),
            "kind": kind,
            "from": quelle["id"],
            "to": ziel["id"],
        }
        self.kommandos.ausfuehren(EinfuegenKommando(self.verbindungen, verbindung))
        self._verbindung_auswaehlen(verbindung)
        self.geaendert.emit()
        self.update()
        return verbindung

    def verbindung_bei(self, x: float, y: float) -> dict[str, Any] | None:
        """Verbindung nahe (x, y) – Linien sind dünn, deshalb mit einem
        Toleranzabstand statt exaktem Treffer."""
        from PySide6.QtCore import QPointF

        punkt = QPointF(x, y)
        for verbindung in reversed(self.verbindungen):
            quelle = self.form_mit_id(verbindung.get("from"))
            ziel = self.form_mit_id(verbindung.get("to"))
            if quelle is None or ziel is None:
                continue
            if abstand_zur_verbindung(punkt, verbindung, quelle, ziel) <= ANFASSER_RADIUS:
                return verbindung
        return None

    def _verbindung_auswaehlen(self, verbindung: dict[str, Any] | None) -> None:
        if verbindung is not None and self.ausgewaehlte_form is not None:
            self.ausgewaehlte_form = None
            self.auswahl_geaendert.emit(None)
        self.ausgewaehlte_verbindung = verbindung
        self.update()

    def hoehe_anpassen(self, form: dict[str, Any]) -> None:
        """Vergrößert `form`, bis ihr Text vollständig hineinpasst
        (Abschnitt 13.6). Verkleinert nie – eine von Hand größer
        gezogene Form soll groß bleiben."""
        noetig = _raster_aufrunden(mindesthoehe(form))
        if noetig > form["h"]:
            form["h"] = noetig
            self.update()

    # -- Bearbeiten -----------------------------------------------------

    def verschieben(self, dx: int, dy: int, form: dict[str, Any] | None = None) -> None:
        ziel = form or self.ausgewaehlte_form
        if ziel is None:
            return
        self.kommandos.ausfuehren(
            WerteKommando(ziel, {"x": ziel["x"] + dx, "y": ziel["y"] + dy})
        )
        self._nach_aenderung()

    def groesse_aendern(self, dw: int, dh: int, form: dict[str, Any] | None = None) -> None:
        ziel = form or self.ausgewaehlte_form
        if ziel is None:
            return
        breite, hoehe = self._begrenzt(ziel, ziel["w"] + dw, ziel["h"] + dh)
        self.kommandos.ausfuehren(WerteKommando(ziel, {"w": breite, "h": hoehe}))
        self._nach_aenderung()

    def _begrenzt(self, form: dict[str, Any], breite: float, hoehe: float) -> tuple[int, int]:
        """Hält Mindestbreite/-höhe ein, damit kein Text abgeschnitten
        wird (Abschnitt 13.6)."""
        min_breite, min_hoehe = MINDESTGROESSE
        return (
            int(max(min_breite, breite)),
            int(max(min_hoehe, mindesthoehe(form), hoehe)),
        )

    def loeschen(self, form: dict[str, Any] | None = None) -> None:
        """Löscht die angegebene bzw. ausgewählte Form – zusammen mit
        allen Verbindungen, die an ihr hängen, als **ein** Undo-Schritt.
        Ohne ausgewählte Form wird eine ausgewählte Verbindung
        gelöscht."""
        ziel = form or self.ausgewaehlte_form
        if ziel is None:
            if self.ausgewaehlte_verbindung is not None:
                self.kommandos.ausfuehren(
                    LoeschenKommando(self.verbindungen, self.ausgewaehlte_verbindung)
                )
                self._verbindung_auswaehlen(None)
                self._nach_aenderung()
            return

        kommandos = [
            LoeschenKommando(self.verbindungen, verbindung)
            for verbindung in self.verbindungen_von(ziel)
        ]
        kommandos.append(LoeschenKommando(self.formen, ziel))
        self.kommandos.ausfuehren(SammelKommando(kommandos))

        if self.ausgewaehlte_form is ziel:
            self.ausgewaehlte_form = None
            self.auswahl_geaendert.emit(None)
        self._nach_aenderung()

    def duplizieren(self, form: dict[str, Any] | None = None) -> dict[str, Any] | None:
        ziel = form or self.ausgewaehlte_form
        if ziel is None:
            return None
        import copy

        kopie = copy.deepcopy(ziel)
        kopie["id"] = self._neue_id()
        kopie["x"] += RASTER
        kopie["y"] += RASTER
        self.kommandos.ausfuehren(EinfuegenKommando(self.formen, kopie))
        self._nach_aenderung(kopie)
        return kopie

    def rueckgaengig(self) -> None:
        self.kommandos.rueckgaengig()
        self._auswahl_bereinigen()
        self._nach_aenderung()

    def wiederholen(self) -> None:
        self.kommandos.wiederholen()
        # Eine wieder eingefügte Form wird auch wieder ausgewählt -
        # genau wie beim ersten Platzieren. Sonst zeigt „Wiederholen“
        # die Form zwar an, aber „Löschen“ danach liefe ins Leere.
        letztes = self.kommandos.letztes_kommando
        if isinstance(letztes, EinfuegenKommando) and letztes.form in self.formen:
            self._auswaehlen(letztes.form)
        self._auswahl_bereinigen()
        self._nach_aenderung()

    def _auswahl_bereinigen(self) -> None:
        """Nach Undo/Redo kann die ausgewählte Form nicht mehr im
        Diagramm sein – dann gilt nichts mehr als ausgewählt."""
        if self.ausgewaehlte_form is not None and self.ausgewaehlte_form not in self.formen:
            self.ausgewaehlte_form = None
            self.auswahl_geaendert.emit(None)

    # -- Auswahl --------------------------------------------------------

    def form_bei(self, x: float, y: float) -> dict[str, Any] | None:
        """Oberste Form an dieser Stelle (spätere Formen liegen oben)."""
        for form in reversed(self.formen):
            if form_rechteck(form).contains(x, y):
                return form
        return None

    def anfasser_bei(self, x: float, y: float) -> str | None:
        """Name des Größenanfassers der ausgewählten Form an (x, y)."""
        if self.ausgewaehlte_form is None:
            return None
        for name, (px, py) in zip(
            _ANFASSER_NAMEN, anfasser_punkte(self.ausgewaehlte_form), strict=True
        ):
            if abs(px - x) <= ANFASSER_RADIUS and abs(py - y) <= ANFASSER_RADIUS:
                return name
        return None

    def _auswaehlen(self, form: dict[str, Any] | None) -> None:
        if form is not None:
            # Form und Verbindung schließen sich als Auswahl gegenseitig aus
            self.ausgewaehlte_verbindung = None
        if form is self.ausgewaehlte_form:
            return
        self.ausgewaehlte_form = form
        self.auswahl_geaendert.emit(form)
        self.update()

    def auswahl_aufheben(self) -> None:
        self.ausgewaehlte_verbindung = None
        self._auswaehlen(None)
        self.update()

    # -- Einrasten ------------------------------------------------------

    def _einrasten(self, form: dict[str, Any], x: float, y: float) -> tuple[int, int]:
        """Rastet die linke/obere Kante am Raster ein und zusätzlich an
        Kanten/Mitten anderer Formen, wenn sie näher als `FANGABSTAND`
        liegen. Merkt sich die getroffenen Linien für die Anzeige."""
        self._hilfslinien = []
        neu_x, neu_y = _am_raster(x), _am_raster(y)

        breite, hoehe = form["w"], form["h"]
        eigene_x = {"links": x, "mitte": x + breite / 2, "rechts": x + breite}
        eigene_y = {"oben": y, "mitte": y + hoehe / 2, "unten": y + hoehe}

        for andere in self.formen:
            if andere is form:
                continue
            fremde_x = (andere["x"], andere["x"] + andere["w"] / 2, andere["x"] + andere["w"])
            fremde_y = (andere["y"], andere["y"] + andere["h"] / 2, andere["y"] + andere["h"])

            for rolle, eigen in eigene_x.items():
                for kante in fremde_x:
                    if abs(eigen - kante) <= FANGABSTAND:
                        versatz = {"links": 0, "mitte": breite / 2, "rechts": breite}[rolle]
                        neu_x = int(kante - versatz)
                        self._hilfslinien.append(("x", kante))
            for rolle, eigen in eigene_y.items():
                for kante in fremde_y:
                    if abs(eigen - kante) <= FANGABSTAND:
                        versatz = {"oben": 0, "mitte": hoehe / 2, "unten": hoehe}[rolle]
                        neu_y = int(kante - versatz)
                        self._hilfslinien.append(("y", kante))

        return neu_x, neu_y

    # -- Maus -----------------------------------------------------------

    def mousePressEvent(self, ereignis: QMouseEvent) -> None:
        punkt: QPoint = ereignis.position().toPoint()

        if self._platzierungs_kind is not None:
            kind = self._platzierungs_kind
            self.platzierungsmodus_setzen(None)  # einmalig, wie in Lazarus
            self.form_platzieren(kind, punkt.x(), punkt.y())
            return

        if self._verbindungs_kind is not None:
            self._verbindungsklick(punkt)
            return

        anfasser = self.anfasser_bei(punkt.x(), punkt.y())
        if anfasser is not None:
            self._anfasser = anfasser
            self._zieh_form = self.ausgewaehlte_form
            self._zieh_start = punkt
            self._zieh_startwerte = {
                name: self.ausgewaehlte_form[name] for name in ("x", "y", "w", "h")
            }
            return

        getroffen = self.form_bei(punkt.x(), punkt.y())
        if getroffen is None:
            # Linien sind dünn und liegen zwischen Formen - erst wenn keine
            # Form getroffen wurde, eine Verbindung in der Nähe suchen.
            verbindung = self.verbindung_bei(punkt.x(), punkt.y())
            if verbindung is not None:
                self._verbindung_auswaehlen(verbindung)
                return
        self._auswaehlen(getroffen)
        if getroffen is None:
            self.auswahl_aufheben()
        if getroffen is not None:
            self._zieh_form = getroffen
            self._zieh_start = punkt
            self._zieh_startwerte = {name: getroffen[name] for name in ("x", "y", "w", "h")}

    def _verbindungsklick(self, punkt: QPoint) -> None:
        """Erster Klick wählt die Quelle, zweiter das Ziel. Ein Klick ins
        Leere bricht ab, statt eine halbe Verbindung stehen zu lassen."""
        getroffen = self.form_bei(punkt.x(), punkt.y())
        if getroffen is None:
            self.verbindungsmodus_setzen(None)
            self.update()
            return
        if self._verbindungs_quelle is None:
            self._verbindungs_quelle = getroffen
            self._auswaehlen(getroffen)
            return

        kind = self._verbindungs_kind
        quelle = self._verbindungs_quelle
        self.verbindungsmodus_setzen(None)
        self.verbindung_erstellen(kind, quelle, getroffen)

    def mouseMoveEvent(self, ereignis: QMouseEvent) -> None:
        punkt = ereignis.position().toPoint()

        if self._zieh_form is None or self._zieh_start is None:
            self._cursor_aktualisieren(punkt)
            return

        dx = punkt.x() - self._zieh_start.x()
        dy = punkt.y() - self._zieh_start.y()
        start = self._zieh_startwerte

        if self._anfasser is not None:
            links_je_dx, breite_je_dx, oben_je_dy, hoehe_je_dy = _ANFASSER_VERHALTEN[
                self._anfasser
            ]
            breite, hoehe = self._begrenzt(
                self._zieh_form,
                start["w"] + breite_je_dx * dx,
                start["h"] + hoehe_je_dy * dy,
            )
            self._zieh_form["w"] = breite
            self._zieh_form["h"] = hoehe
            self._zieh_form["x"] = _am_raster(start["x"] + links_je_dx * dx)
            self._zieh_form["y"] = _am_raster(start["y"] + oben_je_dy * dy)
        else:
            neu_x, neu_y = self._einrasten(
                self._zieh_form, start["x"] + dx, start["y"] + dy
            )
            self._zieh_form["x"] = neu_x
            self._zieh_form["y"] = neu_y

        self.update()

    def mouseReleaseEvent(self, ereignis: QMouseEvent) -> None:
        if self._zieh_form is None or self._zieh_startwerte is None:
            return

        form = self._zieh_form
        start = self._zieh_startwerte
        neue_werte = {name: form[name] for name in ("x", "y", "w", "h")}
        self._zieh_form = None
        self._zieh_start = None
        self._zieh_startwerte = None
        self._anfasser = None
        self._hilfslinien = []

        if neue_werte != start:
            # Live-Vorschau hat die Form schon verändert - deshalb die
            # Startwerte explizit als „alt“ mitgeben.
            self.kommandos.ausfuehren(WerteKommando(form, neue_werte, alte_werte=start))
            self._nach_aenderung()
        else:
            self.update()

    def _cursor_aktualisieren(self, punkt: QPoint) -> None:
        if self._platzierungs_kind is not None:
            return
        anfasser = self.anfasser_bei(punkt.x(), punkt.y())
        if anfasser in ("nw", "se"):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif anfasser in ("ne", "sw"):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif anfasser in ("n", "s"):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif anfasser in ("e", "w"):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    # -- Tastatur -------------------------------------------------------

    def keyPressEvent(self, ereignis: QKeyEvent) -> None:
        if not self._tastatur_verarbeiten(ereignis):
            super().keyPressEvent(ereignis)

    def _tastatur_verarbeiten(self, ereignis: QKeyEvent) -> bool:
        """Tastenkürzel wie im Formular-Designer (Abschnitt 7.7/13.3):
        Pfeil = Rasterschritt, Alt+Pfeil = 1 px, Umschalt+Pfeil = Größe,
        Entf = löschen, Strg+D = duplizieren, Strg+Z/Strg+Umschalt+Z."""
        taste = ereignis.key()
        modifikatoren = ereignis.modifiers()
        strg = bool(modifikatoren & Qt.KeyboardModifier.ControlModifier)
        umschalt = bool(modifikatoren & Qt.KeyboardModifier.ShiftModifier)
        alt = bool(modifikatoren & Qt.KeyboardModifier.AltModifier)

        if strg and taste == Qt.Key.Key_Z:
            self.wiederholen() if umschalt else self.rueckgaengig()
            return True
        if strg and taste == Qt.Key.Key_Y:
            self.wiederholen()
            return True
        if strg and taste == Qt.Key.Key_D:
            self.duplizieren()
            return True
        if taste == Qt.Key.Key_Delete:
            self.loeschen()
            return True
        if taste == Qt.Key.Key_Escape:
            self.platzierungsmodus_setzen(None)
            self.verbindungsmodus_setzen(None)
            self.auswahl_aufheben()
            return True

        richtungen = {
            Qt.Key.Key_Left: (-1, 0),
            Qt.Key.Key_Right: (1, 0),
            Qt.Key.Key_Up: (0, -1),
            Qt.Key.Key_Down: (0, 1),
        }
        if taste not in richtungen or self.ausgewaehlte_form is None:
            return False

        sx, sy = richtungen[taste]
        schritt = 1 if alt else RASTER
        if umschalt:
            self.groesse_aendern(sx * schritt, sy * schritt)
        else:
            self.verschieben(sx * schritt, sy * schritt)
        return True

    # -- Zeichnen -------------------------------------------------------

    def paintEvent(self, ereignis: QPaintEvent) -> None:
        stil = stil_zu_namen(self.diagramm.stil)
        maler = QPainter(self)
        maler.fillRect(self.rect(), QColor(stil.hintergrund))

        if self.raster_sichtbar:
            self._raster_zeichnen(maler, stil.raster)

        # Verbindungen zuerst: sie enden am Formrand, Formen liegen darüber
        for verbindung in self.verbindungen:
            quelle = self.form_mit_id(verbindung.get("from"))
            ziel = self.form_mit_id(verbindung.get("to"))
            if quelle is None or ziel is None:
                continue  # verwaiste Verbindung aus einer von Hand bearbeiteten Datei
            verbindung_zeichnen(
                maler, verbindung, quelle, ziel, stil,
                ausgewaehlt=verbindung is self.ausgewaehlte_verbindung,
            )

        for form in self.formen:
            form_zeichnen(maler, form, stil, ausgewaehlt=form is self.ausgewaehlte_form)

        for verbindung in self.verbindungen:
            quelle = self.form_mit_id(verbindung.get("from"))
            ziel = self.form_mit_id(verbindung.get("to"))
            if quelle is not None and ziel is not None:
                verbindungsbeschriftungen_zeichnen(maler, verbindung, quelle, ziel, stil)

        self._hilfslinien_zeichnen(maler, stil.akzent)

    def _raster_zeichnen(self, maler: QPainter, farbe: str) -> None:
        """Punktraster (Abschnitt 13.6) statt Gitternetzlinien – ruhiger
        und im dunklen Theme weniger aufdringlich."""
        maler.setPen(QColor(farbe))
        for x in range(0, self.width(), RASTER):
            for y in range(0, self.height(), RASTER):
                maler.drawPoint(x, y)

    def _hilfslinien_zeichnen(self, maler: QPainter, farbe: str) -> None:
        if not self._hilfslinien:
            return
        stift = QPen(QColor(farbe))
        stift.setStyle(Qt.PenStyle.DashLine)
        maler.setPen(stift)
        for richtung, wert in self._hilfslinien:
            if richtung == "x":
                maler.drawLine(int(wert), 0, int(wert), self.height())
            else:
                maler.drawLine(0, int(wert), self.width(), int(wert))
