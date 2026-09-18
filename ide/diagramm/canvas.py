"""DiagrammCanvas: Zeichenfläche des Diagramm-Editors (Abschnitt 13.2,
13.3).

Anders als der Formular-Designer (`ide/designer/canvas.py`, ein echtes
`QWidget` je Komponente) malt der Diagramm-Editor alle Formen selbst in
einem einzigen Widget: Diagrammformen sind keine bedienbaren
Steuerelemente, es können sehr viele werden, und Verbindungen (Schritt
4) lassen sich ohnehin nur frei zeichnen.

Stand M9, Schritt 5: anzeigen, platzieren, auswählen, verschieben,
Größe ändern, löschen, duplizieren und verbinden (sieben UML-
Verbindungsarten, Enden folgen beim Verschieben automatisch, weil sie
beim Zeichnen aus den Formen berechnet werden) und beschriften
(Doppelklick, Eingabefelder direkt in der Form) – alles über den Kommando-Stapel,
also unbegrenzt rückgängig machbar (Abschnitt 13.3). Beim Ziehen wird
am Raster **und** an Kanten/Mitten anderer Formen eingerastet, mit
Hilfslinien als Rückmeldung.
"""

from __future__ import annotations

import copy
import json
from typing import Any

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QApplication, QScrollArea, QWidget

from ide.diagramm.datei import Diagramm
from ide.diagramm.formen import MINDESTGROESSE, form_art, verbindungs_art
from ide.diagramm.hinweise import Hinweis, pruefen
from ide.diagramm.klassendialog import KlassenDialog
from ide.diagramm.kommandos import (
    EinfuegenKommando,
    LoeschenKommando,
    ReihenfolgeKommando,
    SammelKommando,
    WerteKommando,
)
from ide.diagramm.seite import satzspiegel, seitengroesse
from ide.diagramm.stil import stil as stil_zu_namen
from ide.diagramm.textbearbeitung import FormEditor
from ide.diagramm.uml_modell import ist_klasse
from ide.diagramm.zeichnen import (
    abstand_zur_verbindung,
    anfasser_punkte,
    beschriftungs_rechtecke,
    form_rechteck,
    form_zeichnen,
    knickpunkt_bei,
    knickpunkte_zeichnen,
    mindesthoehe,
    segment_bei,
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
#: Warnfarbe der Layout-Hinweise – bewusst in allen drei Stilvorlagen
#: dieselbe, damit ein Hinweis nicht mit einer eigenen Formfarbe
#: verwechselt wird. Er wird ohnehin nie mitexportiert.
HINWEIS_FARBE = "#d97706"
#: Zusätzlicher Platz rechts und unten neben dem Blatt, damit sich eine
#: Form auch über den bisherigen Rand hinaus ziehen lässt.
SICHTRAND = 240
#: Grenzen der Zoomstufe (Abschnitt 13.2). Darunter ist nichts mehr zu
#: erkennen, darüber verliert man die Übersicht völlig.
MIN_ZOOM = 0.25
MAX_ZOOM = 4.0

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
    zoom_geaendert = Signal(float)

    def __init__(self, diagramm: Diagramm) -> None:
        super().__init__()
        self.diagramm = diagramm
        self.kommandos = Kommandostapel()
        #: Die Auswahl ist eine **Liste** (Teilschritt 3b). Die letzte
        #: Form darin ist die führende: an ihr richtet sich „Ausrichten“
        #: aus, und nur sie bekommt Anfasser. `ausgewaehlte_form` liefert
        #: genau diese - so bleibt aller Code gültig, der nur eine Form
        #: kennt.
        self._auswahl: list[dict[str, Any]] = []
        self.zoom = 1.0
        self.raster_sichtbar = True
        #: Layout-Hinweise (Schritt 7) sind wie der Design-Prüfer (M7)
        #: abschaltbar – sie melden nur, blockieren nie.
        self.hinweise_sichtbar = True
        self.seitenrand_sichtbar = True
        self.hinweise: list[Hinweis] = []

        self.ausgewaehlte_verbindung: dict[str, Any] | None = None
        self._platzierungs_kind: str | None = None
        self._verbindungs_kind: str | None = None
        self._verbindungs_quelle: dict[str, Any] | None = None
        self._zieh_form: dict[str, Any] | None = None
        self._zieh_formen: list[dict[str, Any]] = []
        self._zieh_startwerte_alle: list[dict[str, Any]] = []
        self._zieh_start: QPoint | None = None
        self._zieh_startwerte: dict[str, Any] | None = None
        self._anfasser: str | None = None
        self._hilfslinien: list[tuple[str, float]] = []
        #: Auswahlrahmen (von-Punkt, Bis-Punkt) während des Aufziehens
        self._rahmen: tuple[QPoint, QPoint] | None = None
        #: Gezogener Knickpunkt: (Verbindung, Nummer, Startwert)
        self._zieh_knick: tuple[dict[str, Any], int, list] | None = None
        #: Gezogene Beschriftung: (Verbindung, „from“/„to“, Startversatz)
        self._zieh_beschriftung: tuple[dict[str, Any], str, tuple] | None = None
        self._editor: FormEditor | None = None
        #: Ansicht verschieben (Leertaste gedrückt bzw. mittlere Taste)
        self._leertaste = False
        self._greif_start: QPoint | None = None

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.inhaltsgroesse_anpassen()

    # -- Zoom ------------------------------------------------------------

    def zoom_setzen(self, wert: float) -> None:
        """Zoomstufe setzen (Abschnitt 13.2/13.3). Begrenzt, damit sich
        niemand aus Versehen so weit heraus- oder hineinzoomt, dass
        nichts mehr zu erkennen ist."""
        neu = max(MIN_ZOOM, min(MAX_ZOOM, wert))
        if abs(neu - self.zoom) < 0.001:
            return
        self.zoom = neu
        self.inhaltsgroesse_anpassen()
        self.zoom_geaendert.emit(neu)
        self.update()

    def zoom_aendern(self, faktor: float) -> None:
        self.zoom_setzen(self.zoom * faktor)

    def alles_anzeigen(self, breite: float, hoehe: float) -> None:
        """„Alles anzeigen“ (Strg+0): so weit herauszoomen, dass alle
        Formen in `breite`×`hoehe` passen. Ohne Formen bleibt es beim
        ganzen Blatt, damit die Ansicht nicht ins Leere springt."""
        inhalt = self._inhalt_in_diagrammkoordinaten()
        if inhalt[0] <= 0 or inhalt[1] <= 0:
            return
        self.zoom_setzen(min(breite / inhalt[0], hoehe / inhalt[1]))

    def _diagrammpunkt(self, ereignis: QMouseEvent) -> QPoint:
        """Mausposition in Diagrammkoordinaten. Alles unterhalb rechnet
        in Diagrammkoordinaten, nur das Zeichnen skaliert – sonst müsste
        jede einzelne Trefferprüfung den Zoom kennen."""
        punkt = ereignis.position()
        return QPoint(int(punkt.x() / self.zoom), int(punkt.y() / self.zoom))

    def wheelEvent(self, ereignis) -> None:
        """Strg+Mausrad zoomt, ohne Strg rollt der Rollbereich wie
        gewohnt weiter."""
        if ereignis.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_aendern(1.1 if ereignis.angleDelta().y() > 0 else 1 / 1.1)
            ereignis.accept()
            return
        ereignis.ignore()

    # -- Ansicht verschieben ---------------------------------------------

    def rollbereich(self) -> QScrollArea | None:
        """Der `QScrollArea`, in dem die Fläche steckt. Sie hängt dort im
        Viewport, der eigentliche Rollbereich ist also der Großelternteil."""
        eltern = self.parentWidget()
        while eltern is not None:
            if isinstance(eltern, QScrollArea):
                return eltern
            eltern = eltern.parentWidget()
        return None

    def ansicht_verschieben(self, dx: int, dy: int) -> None:
        """Verschiebt den sichtbaren Ausschnitt (Leertaste+Ziehen bzw.
        mittlere Maustaste, Abschnitt 13.3)."""
        rollbereich = self.rollbereich()
        if rollbereich is None:
            return
        waagerecht = rollbereich.horizontalScrollBar()
        senkrecht = rollbereich.verticalScrollBar()
        waagerecht.setValue(waagerecht.value() - dx)
        senkrecht.setValue(senkrecht.value() - dy)

    def zur_auswahl_rollen(self) -> None:
        """Rollt so weit, dass die Auswahl zu sehen ist.

        Ohne das wirkt „Ausrichten" wie ein Verschwinden: richtet man an
        einer weit rechts liegenden Klasse aus, wandern alle anderen
        aus dem sichtbaren Ausschnitt heraus, und die Fläche sieht leer
        aus (in der Sichtprüfung zu Teilschritt 3b genau so
        passiert).
        """
        rollbereich = self.rollbereich()
        if rollbereich is None or not self._auswahl:
            return
        umfassend = form_rechteck(self._auswahl[0])
        for form in self._auswahl[1:]:
            umfassend = umfassend.united(form_rechteck(form))

        sichtbar = rollbereich.viewport().rect()
        waagerecht = rollbereich.horizontalScrollBar()
        senkrecht = rollbereich.verticalScrollBar()
        self._balken_nachfuehren(
            waagerecht,
            umfassend.left() * self.zoom,
            umfassend.right() * self.zoom,
            sichtbar.width(),
        )
        self._balken_nachfuehren(
            senkrecht,
            umfassend.top() * self.zoom,
            umfassend.bottom() * self.zoom,
            sichtbar.height(),
        )

    @staticmethod
    def _balken_nachfuehren(balken, von: float, bis: float, breite: int) -> None:
        """Rollt nur so weit wie nötig. Die Auswahl in die Mitte zu
        rücken würde die Ansicht auch dann verspringen lassen, wenn
        ohnehin schon alles zu sehen ist."""
        rand = 16
        if von - rand < balken.value():
            balken.setValue(int(von - rand))
        elif bis + rand > balken.value() + breite:
            balken.setValue(int(bis + rand - breite))

    def _greifen_beginnen(self, punkt: QPoint) -> None:
        self._greif_start = punkt
        self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def _greifen_beenden(self) -> None:
        self._greif_start = None
        self.setCursor(
            Qt.CursorShape.OpenHandCursor
            if self._leertaste
            else Qt.CursorShape.ArrowCursor
        )

    # -- Größe der Fläche -----------------------------------------------

    def _inhalt_in_diagrammkoordinaten(self) -> tuple[float, float]:
        """Das ganze Blatt und darüber hinaus alles, was jemand daneben
        gelegt hat. `SICHTRAND` lässt rechts und unten Platz, damit sich
        eine Form auch über den bisherigen Rand hinaus ziehen lässt."""
        breite, hoehe = seitengroesse(self.diagramm.daten.get("page") or {})
        for form in self.formen:
            breite = max(breite, form["x"] + form["w"])
            hoehe = max(hoehe, form["y"] + form["h"])
        return breite + SICHTRAND, hoehe + SICHTRAND

    def inhaltsgroesse(self) -> tuple[int, int]:
        """Wie groß die Zeichenfläche mindestens sein muss – in Pixeln
        auf dem Bildschirm, also mit dem Zoom multipliziert."""
        breite, hoehe = self._inhalt_in_diagrammkoordinaten()
        return int(breite * self.zoom), int(hoehe * self.zoom)

    def inhaltsgroesse_anpassen(self) -> None:
        """Setzt die Mindestgröße neu. Zusammen mit einer `QScrollArea`
        (`setWidgetResizable(True)`) heißt das: passt der Inhalt ins
        Fenster, füllt die Fläche das Fenster; passt er nicht, erscheinen
        Rollbalken. Ohne das war alles außerhalb des Fensters schlicht
        nicht erreichbar."""
        self.setMinimumSize(*self.inhaltsgroesse())

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
        self.inhaltsgroesse_anpassen()
        self.hinweise_aktualisieren()
        self.geaendert.emit()
        self.update()

    def hinweise_aktualisieren(self) -> list[Hinweis]:
        """Layout-Hinweise neu berechnen (Schritt 7). Ausgeschaltet
        bleibt die Liste leer, damit nichts markiert wird und die
        Prüfung auch keine Rechenzeit kostet."""
        self.hinweise = pruefen(self.diagramm.daten) if self.hinweise_sichtbar else []
        return self.hinweise

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
            "name": art.standardname,
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
        # dasselbe Signal wie bei Formen: der Eigenschaften-Bereich
        # fragt die Auswahl ohnehin selbst bei der Fläche ab
        self.auswahl_geaendert.emit(None if verbindung is not None else self.ausgewaehlte_form)
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
        """Verschiebt die angegebene Form oder die **ganze** Auswahl –
        letzteres als ein einziger Undo-Schritt."""
        ziele = [form] if form is not None else list(self._auswahl)
        if not ziele:
            return
        self._sammeln(
            [
                WerteKommando(ziel, {"x": ziel["x"] + dx, "y": ziel["y"] + dy})
                for ziel in ziele
            ]
        )

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
        ziele = [form] if form is not None else list(self._auswahl)
        if not ziele:
            if self.ausgewaehlte_verbindung is not None:
                self.kommandos.ausfuehren(
                    LoeschenKommando(self.verbindungen, self.ausgewaehlte_verbindung)
                )
                self._verbindung_auswaehlen(None)
                self._nach_aenderung()
            return

        # Erst alle Verbindungen, dann alle Formen - und jede Verbindung
        # nur einmal, sonst stolpert das Rueckgaengig ueber sich selbst,
        # wenn beide Enden mitgeloescht werden.
        kommandos = []
        gesehen: list[dict[str, Any]] = []
        for ziel in ziele:
            for verbindung in self.verbindungen_von(ziel):
                if not any(v is verbindung for v in gesehen):
                    gesehen.append(verbindung)
                    kommandos.append(LoeschenKommando(self.verbindungen, verbindung))
        kommandos.extend(LoeschenKommando(self.formen, ziel) for ziel in ziele)
        self.kommandos.ausfuehren(SammelKommando(kommandos))

        self._auswahl = [
            uebrig for uebrig in self._auswahl if not any(z is uebrig for z in ziele)
        ]
        self.auswahl_geaendert.emit(self.ausgewaehlte_form)
        self._nach_aenderung()

    def duplizieren(self, form: dict[str, Any] | None = None) -> dict[str, Any] | None:
        ziel = form or self.ausgewaehlte_form
        if ziel is None:
            return None

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
        """Nach Undo/Redo können ausgewählte Formen nicht mehr im
        Diagramm sein – die fallen aus der Auswahl heraus."""
        uebrig = [form for form in self._auswahl if any(f is form for f in self.formen)]
        if len(uebrig) != len(self._auswahl):
            self._auswahl = uebrig
            self.auswahl_geaendert.emit(self.ausgewaehlte_form)

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

    @property
    def ausgewaehlte_form(self) -> dict[str, Any] | None:
        """Die **führende** Form der Auswahl – bei Mehrfachauswahl die
        zuletzt angeklickte."""
        return self._auswahl[-1] if self._auswahl else None

    @ausgewaehlte_form.setter
    def ausgewaehlte_form(self, form: dict[str, Any] | None) -> None:
        self._auswahl = [form] if form is not None else []

    @property
    def auswahl(self) -> tuple[dict[str, Any], ...]:
        """Alle ausgewählten Formen, führende zuletzt."""
        return tuple(self._auswahl)

    @staticmethod
    def _gleiche_auswahl(
        eine: list[dict[str, Any]], andere: list[dict[str, Any]]
    ) -> bool:
        """Vergleich über Identität, nicht über `==`. Zwei Formen mit
        gleichem Inhalt sind als `dict` gleich, aber trotzdem zwei
        verschiedene Formen im Diagramm."""
        return len(eine) == len(andere) and all(
            a is b for a, b in zip(eine, andere, strict=True)
        )

    def _auswahl_setzen(self, formen: list[dict[str, Any]]) -> None:
        if formen:
            # Form und Verbindung schließen sich als Auswahl gegenseitig aus
            self.ausgewaehlte_verbindung = None
        if self._gleiche_auswahl(formen, self._auswahl):
            return
        self._auswahl = formen
        self.auswahl_geaendert.emit(self.ausgewaehlte_form)
        self.update()

    def _auswaehlen(self, form: dict[str, Any] | None) -> None:
        self._auswahl_setzen(self._mit_gruppe([form]) if form is not None else [])

    def auswahl_umschalten(self, form: dict[str, Any]) -> None:
        """Strg+Klick: nimmt die Form dazu oder wieder heraus. Eine
        bereits ausgewählte Form wandert dabei **nicht** ans Ende – wer
        eine falsch getroffene Form wieder abwählt, will die Führung
        nicht verschieben."""
        neu = [vorhanden for vorhanden in self._auswahl if vorhanden is not form]
        if len(neu) == len(self._auswahl):
            neu = self._auswahl + [
                dazu for dazu in self._mit_gruppe([form]) if dazu not in self._auswahl
            ]
        self._auswahl_setzen(neu)

    def alles_auswaehlen(self) -> None:
        self._auswahl_setzen(list(self.formen))

    def auswahl_aufheben(self) -> None:
        self.ausgewaehlte_verbindung = None
        self._auswahl_setzen([])
        self.update()

    def _mit_gruppe(self, formen: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ergänzt jede Form um ihre Gruppengeschwister. Eine Gruppe ist
        genau dafür da, dass man sie als Ganzes anfasst."""
        gruppen = {form.get("group") for form in formen if form.get("group")}
        if not gruppen:
            return list(formen)
        ergebnis = list(formen)
        for form in self.formen:
            if form.get("group") in gruppen and form not in ergebnis:
                ergebnis.append(form)
        # Die angeklickte Form bleibt die führende
        if formen:
            ergebnis.remove(formen[-1])
            ergebnis.append(formen[-1])
        return ergebnis

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
        # Ansicht verschieben geht allem anderen vor: wer die Leertaste
        # hält oder die mittlere Taste drückt, will nichts auswählen.
        if self._leertaste or ereignis.button() == Qt.MouseButton.MiddleButton:
            self._greifen_beginnen(ereignis.position().toPoint())
            return

        punkt: QPoint = self._diagrammpunkt(ereignis)

        if self._platzierungs_kind is not None:
            kind = self._platzierungs_kind
            self.platzierungsmodus_setzen(None)  # einmalig, wie in Lazarus
            self.form_platzieren(kind, punkt.x(), punkt.y())
            return

        if self._verbindungs_kind is not None:
            self._verbindungsklick(punkt)
            return

        # Knickpunkt der ausgewählten Verbindung geht vor: er liegt
        # mitten auf der Linie und wäre sonst nicht zu treffen.
        if self.ausgewaehlte_verbindung is not None:
            nummer = knickpunkt_bei(self.ausgewaehlte_verbindung, punkt.x(), punkt.y())
            if nummer is not None:
                knicke = self.ausgewaehlte_verbindung.get("waypoints") or []
                self._zieh_knick = (
                    self.ausgewaehlte_verbindung,
                    nummer,
                    [list(paar) for paar in knicke],
                )
                self._zieh_start = punkt
                return

        beschriftung = self.beschriftung_bei(punkt.x(), punkt.y())
        if beschriftung is not None:
            verbindung, schluessel = beschriftung
            versatz = (verbindung.get("label_offsets") or {}).get(schluessel, (0, 0))
            self._verbindung_auswaehlen(verbindung)
            self._zieh_beschriftung = (verbindung, schluessel, tuple(versatz))
            self._zieh_start = punkt
            return

        anfasser = self.anfasser_bei(punkt.x(), punkt.y())
        if anfasser is not None:
            # Größe ändern gilt immer nur der führenden Form - ein
            # gemeinsames Skalieren mehrerer Formen wäre etwas anderes
            # als „Gleiche Größe“ und würde damit verwechselt.
            self._anfasser = anfasser
            self._zieh_formen = [self.ausgewaehlte_form]
            self._zieh_form = self.ausgewaehlte_form
            self._zieh_start = punkt
            self._zieh_startwerte = {
                name: self.ausgewaehlte_form[name] for name in ("x", "y", "w", "h")
            }
            self._zieh_startwerte_alle = [dict(self._zieh_startwerte)]
            return

        strg = bool(ereignis.modifiers() & Qt.KeyboardModifier.ControlModifier)
        getroffen = self.form_bei(punkt.x(), punkt.y())

        if getroffen is None:
            # Linien sind dünn und liegen zwischen Formen - erst wenn keine
            # Form getroffen wurde, eine Verbindung in der Nähe suchen.
            verbindung = self.verbindung_bei(punkt.x(), punkt.y())
            if verbindung is not None:
                self._verbindung_auswaehlen(verbindung)
                return
            if not strg:
                self.auswahl_aufheben()
            # Ins Leere gedrückt: von hier an einen Auswahlrahmen ziehen
            self._rahmen = (punkt, punkt)
            return

        if strg:
            self.auswahl_umschalten(getroffen)
        elif not any(form is getroffen for form in self._auswahl):
            # Eine Form aus einer bestehenden Mehrfachauswahl anzuklicken
            # darf die Auswahl nicht zusammenfallen lassen - sonst könnte
            # man mehrere Formen nie gemeinsam ziehen.
            self._auswaehlen(getroffen)

        self._ziehen_beginnen(punkt)

    def _ziehen_beginnen(self, punkt: QPoint) -> None:
        """Merkt sich die Startwerte **aller** ausgewählten Formen – ein
        Ziehen bewegt die ganze Auswahl und bleibt trotzdem ein einziger
        Undo-Schritt."""
        self._zieh_formen = list(self._auswahl)
        self._zieh_form = self.ausgewaehlte_form
        self._zieh_start = punkt
        self._zieh_startwerte = (
            {name: self._zieh_form[name] for name in ("x", "y", "w", "h")}
            if self._zieh_form is not None
            else None
        )
        self._zieh_startwerte_alle = [
            {name: form[name] for name in ("x", "y", "w", "h")}
            for form in self._zieh_formen
        ]

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

    def mouseDoubleClickEvent(self, ereignis: QMouseEvent) -> None:
        """Doppelklick beschriftet die Form direkt (Abschnitt 13.3) –
        auf einer Verbindung setzt er dagegen einen Knickpunkt bzw.
        nimmt ihn wieder weg (Teilschritt 4b)."""
        punkt = self._diagrammpunkt(ereignis)
        getroffen = self.form_bei(punkt.x(), punkt.y())
        if getroffen is not None:
            self._auswaehlen(getroffen)
            self.bearbeiten_starten(getroffen)
            return

        verbindung = self.verbindung_bei(punkt.x(), punkt.y())
        if verbindung is None:
            return
        self._verbindung_auswaehlen(verbindung)
        nummer = knickpunkt_bei(verbindung, punkt.x(), punkt.y())
        if nummer is not None:
            self.knickpunkt_entfernen(verbindung, nummer)
        else:
            self.knickpunkt_setzen(verbindung, punkt)

    # -- Beschriften ----------------------------------------------------

    def bearbeiten_starten(self, form: dict[str, Any] | None = None):
        """Beschriften. Für Klassen, abstrakte Klassen und Interfaces
        öffnet sich der Eigenschaften-Dialog (M9 Schritt 12,
        Nutzer-Entscheidung); Notiz und Paket haben nur ein Textfeld und
        werden weiterhin direkt in der Fläche beschriftet – ein Dialog
        mit fünf Reitern wäre dafür überzogen."""
        ziel = form or self.ausgewaehlte_form
        if ziel is None:
            return None
        if ist_klasse(ziel):
            return self.eigenschaften_bearbeiten(ziel)

        self.bearbeiten_beenden()
        editor = FormEditor(ziel, self, self.zoom)
        editor.fertig.connect(lambda text, f=ziel: self._text_uebernehmen(f, text))
        editor.abgebrochen.connect(self.bearbeiten_beenden)
        editor.show()
        editor.setFocus()
        self._editor = editor
        return editor

    def bearbeiten_beenden(self) -> None:
        if self._editor is not None:
            editor, self._editor = self._editor, None
            editor.stilllegen()
            editor.hide()
            editor.setParent(None)
            editor.deleteLater()
            self.setFocus()

    def _text_uebernehmen(self, form: dict[str, Any], text: dict[str, Any]) -> None:
        """Rückmeldung des Direkteditors – nur noch für Notiz und Paket,
        die haben ausschließlich einen Namen."""
        self.bearbeiten_beenden()
        neuer_name = str(text.get("name", ""))
        if neuer_name == str(form.get("name", "")):
            return
        # Höhe gleich mit anpassen, damit neue Zeilen nicht abgeschnitten
        # werden - beides zusammen als ein Undo-Schritt.
        probe = dict(form)
        probe["name"] = neuer_name
        neue_hoehe = max(form["h"], _raster_aufrunden(mindesthoehe(probe)))
        self.kommandos.ausfuehren(
            WerteKommando(form, {"name": neuer_name, "h": neue_hoehe})
        )
        self._nach_aenderung()

    def eigenschaften_dialog(self, form: dict[str, Any] | None = None):
        """Baut den Eigenschaften-Dialog und hängt ihn an den
        Kommando-Stapel – **ohne** ihn anzuzeigen. Getrennt vom Anzeigen,
        weil `exec()` blockiert und Tests sonst hängen blieben."""
        ziel = form or self.ausgewaehlte_form
        if ziel is None or not ist_klasse(ziel):
            return None

        dialog = KlassenDialog(ziel, self)
        dialog.angewendet = lambda werte, f=ziel: self._eigenschaften_uebernehmen(f, werte)
        return dialog

    def eigenschaften_bearbeiten(self, form: dict[str, Any] | None = None):
        """Öffnet den Eigenschaften-Dialog für eine UML-Klasse. Jeder
        Druck auf „Anwenden“ ist **ein** Undo-Schritt, egal wie viele
        Felder im Dialog geändert wurden."""
        dialog = self.eigenschaften_dialog(form)
        if dialog is not None:
            dialog.exec()
        return dialog

    def _eigenschaften_uebernehmen(
        self, form: dict[str, Any], werte: dict[str, Any]
    ) -> None:
        geaendert = {k: v for k, v in werte.items() if form.get(k) != v}
        if not geaendert:
            return
        probe = {**form, **geaendert}
        geaendert["h"] = max(form["h"], _raster_aufrunden(mindesthoehe(probe)))
        self.kommandos.ausfuehren(WerteKommando(form, geaendert))
        self._nach_aenderung()

    def mouseMoveEvent(self, ereignis: QMouseEvent) -> None:
        if self._greif_start is not None:
            jetzt = ereignis.position().toPoint()
            self.ansicht_verschieben(
                jetzt.x() - self._greif_start.x(), jetzt.y() - self._greif_start.y()
            )
            return

        punkt = self._diagrammpunkt(ereignis)

        if self._rahmen is not None:
            self._rahmen = (self._rahmen[0], punkt)
            self.update()
            return

        if self._zieh_knick is not None:
            verbindung, nummer, anfang = self._zieh_knick
            knicke = [list(paar) for paar in anfang]
            knicke[nummer] = [_am_raster(punkt.x()), _am_raster(punkt.y())]
            verbindung["waypoints"] = knicke
            self.update()
            return

        if self._zieh_beschriftung is not None and self._zieh_start is not None:
            verbindung, schluessel, anfang = self._zieh_beschriftung
            versatz = dict(verbindung.get("label_offsets") or {})
            versatz[schluessel] = [
                anfang[0] + punkt.x() - self._zieh_start.x(),
                anfang[1] + punkt.y() - self._zieh_start.y(),
            ]
            verbindung["label_offsets"] = versatz
            self.update()
            return

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
            # Eingerastet wird an der führenden Form; alle anderen folgen
            # ihr um denselben Betrag. Würde jede Form einzeln einrasten,
            # zerfiele eine sauber angeordnete Gruppe beim ersten Ziehen.
            neu_x, neu_y = self._einrasten(
                self._zieh_form, start["x"] + dx, start["y"] + dy
            )
            versatz_x = neu_x - start["x"]
            versatz_y = neu_y - start["y"]
            for form, anfang in zip(
                self._zieh_formen, self._zieh_startwerte_alle, strict=True
            ):
                form["x"] = anfang["x"] + versatz_x
                form["y"] = anfang["y"] + versatz_y

        self.update()

    def mouseReleaseEvent(self, ereignis: QMouseEvent) -> None:
        if self._greif_start is not None:
            self._greifen_beenden()
            return
        if self._rahmen is not None:
            self._rahmen_beenden()
            return
        if self._zieh_knick is not None:
            verbindung, _, anfang = self._zieh_knick
            self._zieh_knick = None
            self._zieh_start = None
            jetzt = [list(paar) for paar in (verbindung.get("waypoints") or [])]
            if jetzt != anfang:
                # Live-Vorschau hat die Linie schon verändert - deshalb
                # die Startwerte ausdrücklich als „alt“ mitgeben.
                self.kommandos.ausfuehren(
                    WerteKommando(
                        verbindung, {"waypoints": jetzt}, alte_werte={"waypoints": anfang}
                    )
                )
                self._nach_aenderung()
            return
        if self._zieh_beschriftung is not None:
            verbindung, schluessel, anfang = self._zieh_beschriftung
            self._zieh_beschriftung = None
            self._zieh_start = None
            versatz = dict(verbindung.get("label_offsets") or {})
            if tuple(versatz.get(schluessel, (0, 0))) != tuple(anfang):
                alt_versatz = dict(versatz)
                alt_versatz[schluessel] = list(anfang)
                self.kommandos.ausfuehren(
                    WerteKommando(
                        verbindung,
                        {"label_offsets": versatz},
                        alte_werte={"label_offsets": alt_versatz},
                    )
                )
                self._nach_aenderung()
            return
        if self._zieh_form is None or self._zieh_startwerte is None:
            return

        formen = self._zieh_formen
        anfaenge = self._zieh_startwerte_alle
        self._zieh_form = None
        self._zieh_formen = []
        self._zieh_start = None
        self._zieh_startwerte = None
        self._zieh_startwerte_alle = []
        self._anfasser = None
        self._hilfslinien = []

        # Live-Vorschau hat die Formen schon verändert - deshalb die
        # Startwerte explizit als „alt“ mitgeben. Alle zusammen als ein
        # Kommando, damit ein Ziehen ein einziger Undo-Schritt bleibt.
        kommandos = []
        for form, anfang in zip(formen, anfaenge, strict=True):
            neue_werte = {name: form[name] for name in ("x", "y", "w", "h")}
            if neue_werte != anfang:
                kommandos.append(WerteKommando(form, neue_werte, alte_werte=anfang))
        if kommandos:
            self.kommandos.ausfuehren(
                kommandos[0] if len(kommandos) == 1 else SammelKommando(kommandos)
            )
            self._nach_aenderung()
        else:
            self.update()

    def _rahmen_beenden(self) -> None:
        """Wählt alles aus, was **vollständig** im aufgezogenen Rahmen
        liegt. Nur Berühren würde beim Aufziehen über ein dicht
        gestelltes Diagramm ständig Nachbarn mitnehmen, die man gar
        nicht meint."""
        von, bis = self._rahmen
        self._rahmen = None
        rahmen = QRectF(
            min(von.x(), bis.x()),
            min(von.y(), bis.y()),
            abs(bis.x() - von.x()),
            abs(bis.y() - von.y()),
        )
        if rahmen.width() < 3 and rahmen.height() < 3:
            self.update()  # nur ein Klick ins Leere, kein Rahmen
            return
        getroffen = [
            form for form in self.formen if rahmen.contains(form_rechteck(form))
        ]
        self._auswahl_setzen(self._mit_gruppe(getroffen) if getroffen else [])
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

    def keyReleaseEvent(self, ereignis: QKeyEvent) -> None:
        if ereignis.key() == Qt.Key.Key_Space and not ereignis.isAutoRepeat():
            self._leertaste = False
            self._greifen_beenden()
            return
        super().keyReleaseEvent(ereignis)

    def keyPressEvent(self, ereignis: QKeyEvent) -> None:
        if not self._tastatur_verarbeiten(ereignis):
            super().keyPressEvent(ereignis)

    def _tastatur_verarbeiten(self, ereignis: QKeyEvent) -> bool:
        if ereignis.key() == Qt.Key.Key_Space and self._editor is None:
            # Nicht während des Beschriftens - dort ist ein Leerzeichen
            # ein Leerzeichen.
            self._leertaste = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            return True

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
        if strg and taste == Qt.Key.Key_A:
            self.alles_auswaehlen()
            return True
        if strg and taste == Qt.Key.Key_C:
            self.kopieren()
            return True
        if strg and taste == Qt.Key.Key_X:
            self.ausschneiden()
            return True
        if strg and taste == Qt.Key.Key_V:
            self.einfuegen()
            return True
        if strg and taste == Qt.Key.Key_G:
            self.gruppierung_aufheben() if umschalt else self.gruppieren()
            return True
        if taste == Qt.Key.Key_Delete:
            self.loeschen()
            return True
        if taste == Qt.Key.Key_F2:
            self.bearbeiten_starten()
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
        if taste not in richtungen or not self._auswahl:
            return False

        sx, sy = richtungen[taste]
        schritt = 1 if alt else RASTER
        if umschalt:
            # Größe ändern gilt nur der führenden Form - wie beim Ziehen
            # am Anfasser.
            self.groesse_aendern(sx * schritt, sy * schritt)
        else:
            self.verschieben(sx * schritt, sy * schritt)
        return True

    # -- Knickpunkte und Beschriftungen (Teilschritt 4b) -----------------

    def knickpunkt_setzen(self, verbindung: dict[str, Any], punkt: QPoint) -> bool:
        """Fügt an dieser Stelle einen Knickpunkt ein – und zwar in dem
        Linienstück, auf das geklickt wurde. Immer ans Ende zu hängen
        wäre bei einer schon zweimal geknickten Linie ein Sprung quer
        durchs Diagramm."""
        quelle = self.form_mit_id(verbindung.get("from"))
        ziel = self.form_mit_id(verbindung.get("to"))
        if quelle is None or ziel is None:
            return False
        stelle = segment_bei(QPointF(punkt.x(), punkt.y()), verbindung, quelle, ziel)
        knicke = [list(paar) for paar in (verbindung.get("waypoints") or [])]
        knicke.insert(stelle, [_am_raster(punkt.x()), _am_raster(punkt.y())])
        self.kommandos.ausfuehren(WerteKommando(verbindung, {"waypoints": knicke}))
        self._nach_aenderung()
        return True

    def knickpunkt_entfernen(self, verbindung: dict[str, Any], nummer: int) -> bool:
        knicke = [list(paar) for paar in (verbindung.get("waypoints") or [])]
        if not 0 <= nummer < len(knicke):
            return False
        del knicke[nummer]
        self.kommandos.ausfuehren(WerteKommando(verbindung, {"waypoints": knicke}))
        self._nach_aenderung()
        return True

    def beschriftung_bei(self, x: float, y: float) -> tuple[dict[str, Any], str] | None:
        """Beschriftung an dieser Stelle, als (Verbindung, „from"/„to")."""
        for verbindung in reversed(self.verbindungen):
            quelle = self.form_mit_id(verbindung.get("from"))
            ziel = self.form_mit_id(verbindung.get("to"))
            if quelle is None or ziel is None:
                continue
            for schluessel, rechteck in beschriftungs_rechtecke(
                verbindung, quelle, ziel
            ).items():
                if rechteck.contains(x, y):
                    return verbindung, schluessel
        return None

    # -- Anordnen (Teilschritt 3b) --------------------------------------

    #: Ausgerichtet wird immer an der **führenden** Form, also der
    #: zuletzt angeklickten - dasselbe Verhalten wie in Lazarus und in
    #: Dia. Sonst müsste man raten, welche Form stehen bleibt.
    AUSRICHTUNGEN = (
        "links",
        "rechts",
        "oben",
        "unten",
        "senkrechte_mitte",
        "waagerechte_mitte",
    )

    def ausrichten(self, art: str) -> bool:
        """Richtet alle ausgewählten Formen an der führenden aus.
        Liefert `False`, wenn nichts zu tun war."""
        if art not in self.AUSRICHTUNGEN or len(self._auswahl) < 2:
            return False
        bezug = self.ausgewaehlte_form
        kommandos = []
        for form in self._auswahl:
            if form is bezug:
                continue
            if art == "links":
                werte = {"x": bezug["x"]}
            elif art == "rechts":
                werte = {"x": bezug["x"] + bezug["w"] - form["w"]}
            elif art == "oben":
                werte = {"y": bezug["y"]}
            elif art == "unten":
                werte = {"y": bezug["y"] + bezug["h"] - form["h"]}
            elif art == "senkrechte_mitte":
                werte = {"x": int(bezug["x"] + bezug["w"] / 2 - form["w"] / 2)}
            else:  # waagerechte_mitte
                werte = {"y": int(bezug["y"] + bezug["h"] / 2 - form["h"] / 2)}
            if any(form.get(name) != wert for name, wert in werte.items()):
                kommandos.append(WerteKommando(form, werte))
        return self._sammeln(kommandos)

    def verteilen(self, richtung: str) -> bool:
        """Verteilt die ausgewählten Formen mit **gleichen Abständen**
        zwischen der ersten und der letzten.

        Gleiche Abstände statt gleicher Mittenabstände: bei
        unterschiedlich breiten Klassen sieht nur das gleichmäßig aus.
        Die äußeren beiden Formen bleiben stehen - sonst wanderte die
        ganze Reihe bei jedem Aufruf davon.
        """
        if richtung not in ("waagerecht", "senkrecht") or len(self._auswahl) < 3:
            return False
        achse, laenge = ("x", "w") if richtung == "waagerecht" else ("y", "h")
        sortiert = sorted(self._auswahl, key=lambda f: f[achse])

        anfang = sortiert[0][achse]
        ende = sortiert[-1][achse] + sortiert[-1][laenge]
        belegt = sum(form[laenge] for form in sortiert)
        luecke = (ende - anfang - belegt) / (len(sortiert) - 1)

        kommandos = []
        stelle = float(anfang)
        for form in sortiert[:-1]:
            if int(stelle) != form[achse]:
                kommandos.append(WerteKommando(form, {achse: int(stelle)}))
            stelle += form[laenge] + luecke
        return self._sammeln(kommandos)

    def gleiche_groesse(self, art: str) -> bool:
        """Gibt allen ausgewählten Formen die Größe der führenden.
        Die Mindestgröße gilt weiter - eine Klasse mit vielen Attributen
        lässt sich nicht auf die Höhe einer Notiz stauchen."""
        if art not in ("breite", "hoehe", "beide") or len(self._auswahl) < 2:
            return False
        bezug = self.ausgewaehlte_form
        kommandos = []
        for form in self._auswahl:
            if form is bezug:
                continue
            breite = bezug["w"] if art in ("breite", "beide") else form["w"]
            hoehe = bezug["h"] if art in ("hoehe", "beide") else form["h"]
            breite, hoehe = self._begrenzt(form, breite, hoehe)
            werte = {"w": breite, "h": hoehe}
            if any(form.get(name) != wert for name, wert in werte.items()):
                kommandos.append(WerteKommando(form, werte))
        return self._sammeln(kommandos)

    # -- Zeichenreihenfolge ---------------------------------------------

    def nach_vorne(self) -> bool:
        """Holt die Auswahl ans Ende der Liste – spätere Formen werden
        später gezeichnet und liegen damit oben."""
        return self._umsortieren(nach_vorne=True)

    def nach_hinten(self) -> bool:
        return self._umsortieren(nach_vorne=False)

    def _umsortieren(self, nach_vorne: bool) -> bool:
        if not self._auswahl:
            return False
        bewegt = [form for form in self.formen if any(a is form for a in self._auswahl)]
        rest = [form for form in self.formen if not any(a is form for a in self._auswahl)]
        neu = rest + bewegt if nach_vorne else bewegt + rest
        if self._gleiche_auswahl(neu, list(self.formen)):
            return False
        self.kommandos.ausfuehren(ReihenfolgeKommando(self.formen, neu))
        self._nach_aenderung()
        return True

    # -- Gruppieren ------------------------------------------------------

    def gruppieren(self) -> bool:
        """Fasst die Auswahl zu einer Gruppe zusammen.

        Eine Gruppe ist kein eigenes Element, sondern nur eine
        gemeinsame Kennung an den Formen. So bleibt die Datei auch ohne
        Kenntnis von Gruppen lesbar, und ein Diagramm, das jemand mit
        einer älteren Natter-Version öffnet, sieht unverändert aus.
        """
        if len(self._auswahl) < 2:
            return False
        kennung = f"g{self._naechste_gruppennummer()}"
        kommandos = [
            WerteKommando(form, {"group": kennung})
            for form in self._auswahl
            if form.get("group") != kennung
        ]
        return self._sammeln(kommandos)

    def gruppierung_aufheben(self) -> bool:
        kommandos = [
            WerteKommando(form, {"group": ""})
            for form in self._auswahl
            if form.get("group")
        ]
        return self._sammeln(kommandos)

    def _naechste_gruppennummer(self) -> int:
        vergeben = {
            form.get("group")
            for form in self.formen
            if str(form.get("group", "")).strip()
        }
        nummer = 1
        while f"g{nummer}" in vergeben:
            nummer += 1
        return nummer

    def _sammeln(self, kommandos: list[Any]) -> bool:
        """Führt mehrere Änderungen als **einen** Undo-Schritt aus.
        Ausrichten ist für die Bedienerin eine Handlung, also soll auch
        ein einziges Strg+Z sie zurücknehmen."""
        if not kommandos:
            return False
        self.kommandos.ausfuehren(
            kommandos[0] if len(kommandos) == 1 else SammelKommando(kommandos)
        )
        self._nach_aenderung()
        self.zur_auswahl_rollen()
        return True

    # -- Zwischenablage --------------------------------------------------

    def kopieren(self) -> bool:
        """Legt die Auswahl als JSON-Text in die Zwischenablage.

        Text statt eigener MIME-Daten: `QClipboard.setMimeData()` lässt
        PySide6 beim Beenden des Programms abstürzen (in M9 reproduziert
        und dort dokumentiert). Der Text hat obendrein einen Vorteil –
        man kann ihn in einen Editor einfügen und nachsehen, was
        drinsteht.
        """
        if not self._auswahl:
            return False
        kennungen = {form.get("id") for form in self._auswahl}
        inhalt = {
            "natter_diagramm": 1,
            "typ": self.diagramm.typ,
            "shapes": copy.deepcopy(list(self._auswahl)),
            # Verbindungen kommen mit, wenn **beide** Enden mitkopiert
            # werden - eine Verbindung ins Nichts wäre beim Einfügen
            # wertlos.
            "connections": copy.deepcopy(
                [
                    verbindung
                    for verbindung in self.verbindungen
                    if verbindung.get("from") in kennungen
                    and verbindung.get("to") in kennungen
                ]
            ),
        }
        QApplication.clipboard().setText(
            json.dumps(inhalt, ensure_ascii=False, indent=1)
        )
        return True

    def ausschneiden(self) -> bool:
        if not self.kopieren():
            return False
        self.loeschen()
        return True

    def einfuegen(self) -> bool:
        """Fügt ein, was `kopieren()` abgelegt hat – versetzt um einen
        Rasterschritt, damit die Kopie nicht genau auf dem Original
        liegt und unsichtbar bleibt."""
        inhalt = self._zwischenablage_lesen()
        if inhalt is None:
            return False

        neue_kennungen: dict[str, str] = {}
        kommandos = []
        eingefuegt = []
        for form in inhalt.get("shapes", []):
            alt = form.get("id")
            form["id"] = self._neue_id()
            if alt:
                neue_kennungen[alt] = form["id"]
            form["x"] = form.get("x", 0) + RASTER
            form["y"] = form.get("y", 0) + RASTER
            # Gleich anhängen, damit die nächste `_neue_id()` diese hier
            # schon als vergeben sieht.
            self.formen.append(form)
            kommandos.append(EinfuegenKommando(self.formen, form))
            eingefuegt.append(form)
        for form in eingefuegt:
            self.formen.remove(form)

        neue_verbindungen: list[dict[str, Any]] = []
        for verbindung in inhalt.get("connections", []):
            verbindung["from"] = neue_kennungen.get(verbindung.get("from"))
            verbindung["to"] = neue_kennungen.get(verbindung.get("to"))
            if verbindung.get("from") and verbindung.get("to"):
                verbindung["id"] = self._neue_verbindungs_id()
                self.verbindungen.append(verbindung)
                neue_verbindungen.append(verbindung)
                kommandos.append(EinfuegenKommando(self.verbindungen, verbindung))
        for verbindung in neue_verbindungen:
            self.verbindungen.remove(verbindung)

        if not kommandos:
            return False
        self.kommandos.ausfuehren(SammelKommando(kommandos))
        # Das Eingefügte ist ausgewählt - wie nach dem Platzieren, damit
        # man es sofort weiterschieben kann.
        self._auswahl_setzen(eingefuegt)
        self._nach_aenderung()
        return True

    def _zwischenablage_lesen(self) -> dict[str, Any] | None:
        """Liest den Text der Zwischenablage, wenn er von Natter stammt.
        Fremder Text (aus einem Browser, aus Word) wird stillschweigend
        übergangen statt in einen Fehler zu laufen."""
        text = QApplication.clipboard().text()
        if not text or "natter_diagramm" not in text:
            return None
        try:
            inhalt = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(inhalt, dict) or not inhalt.get("natter_diagramm"):
            return None
        if inhalt.get("typ") != self.diagramm.typ:
            # Klassen in eine Entscheidungstabelle einzufügen ergäbe nichts
            return None
        return copy.deepcopy(inhalt)

    # -- Zeichnen -------------------------------------------------------

    def paintEvent(self, ereignis: QPaintEvent) -> None:
        stil = stil_zu_namen(self.diagramm.stil)
        maler = QPainter(self)
        maler.fillRect(self.rect(), QColor(stil.hintergrund))
        maler.scale(self.zoom, self.zoom)

        if self.seitenrand_sichtbar:
            self._seitenrand_zeichnen(maler, stil)
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

        fuehrend = self.ausgewaehlte_form
        for form in self.formen:
            form_zeichnen(
                maler,
                form,
                stil,
                ausgewaehlt=any(gewaehlt is form for gewaehlt in self._auswahl),
                mit_anfassern=form is fuehrend,
            )

        for verbindung in self.verbindungen:
            quelle = self.form_mit_id(verbindung.get("from"))
            ziel = self.form_mit_id(verbindung.get("to"))
            if quelle is not None and ziel is not None:
                verbindungsbeschriftungen_zeichnen(maler, verbindung, quelle, ziel, stil)

        # Knickpunkte nur an der ausgewählten Verbindung: an allen
        # gleichzeitig wäre das Diagramm mit Quadraten übersät.
        if self.ausgewaehlte_verbindung is not None:
            knickpunkte_zeichnen(maler, self.ausgewaehlte_verbindung, stil)

        self._hinweise_zeichnen(maler)
        self._hilfslinien_zeichnen(maler, stil.akzent)
        self._rahmen_zeichnen(maler, stil.akzent)

    def _rahmen_zeichnen(self, maler: QPainter, farbe: str) -> None:
        """Der aufgezogene Auswahlrahmen. Gestrichelt und ungefüllt –
        eine gefüllte Fläche würde die Formen darunter verdecken, und
        genau die will man beim Aufziehen sehen."""
        if self._rahmen is None:
            return
        von, bis = self._rahmen
        stift = QPen(QColor(farbe))
        stift.setStyle(Qt.PenStyle.DashLine)
        maler.setPen(stift)
        maler.setBrush(Qt.BrushStyle.NoBrush)
        maler.drawRect(
            QRectF(
                min(von.x(), bis.x()),
                min(von.y(), bis.y()),
                abs(bis.x() - von.x()),
                abs(bis.y() - von.y()),
            )
        )

    def _seitenrand_zeichnen(self, maler: QPainter, stil) -> None:
        """Blattgröße und bedruckbarer Bereich (Abschnitt 13.2). Ohne
        diese Linien wäre der Layout-Hinweis „liegt außerhalb des
        Seitenbereichs“ für Schülerinnen und Schüler nicht
        nachvollziehbar."""
        breite, hoehe = seitengroesse(self.diagramm.daten.get("page") or {})
        stift = QPen(QColor(stil.trennlinie))
        stift.setWidth(1)
        maler.setPen(stift)
        maler.drawRect(0, 0, int(breite), int(hoehe))

        links, oben, satz_breite, satz_hoehe = satzspiegel(
            self.diagramm.daten.get("page") or {}
        )
        stift.setStyle(Qt.PenStyle.DashLine)
        maler.setPen(stift)
        maler.drawRect(int(links), int(oben), int(satz_breite), int(satz_hoehe))

    def _hinweise_zeichnen(self, maler: QPainter) -> None:
        """Betroffene Formen bekommen einen gestrichelten Warnrahmen –
        wie die Wellenlinie des Design-Prüfers ein Hinweis, der nichts
        blockiert und sich abschalten lässt."""
        if not self.hinweise:
            return
        stift = QPen(QColor(HINWEIS_FARBE))
        stift.setWidth(2)
        stift.setStyle(Qt.PenStyle.DashLine)
        maler.setPen(stift)
        maler.setBrush(Qt.BrushStyle.NoBrush)
        betroffen = {kennung for hinweis in self.hinweise for kennung in hinweis.elemente}
        for kennung in betroffen:
            form = self.form_mit_id(kennung)
            if form is not None:
                maler.drawRect(form_rechteck(form).adjusted(-3, -3, 3, 3))

    def _sichtbare_breite(self) -> int:
        """Breite der Fläche in Diagrammkoordinaten – beim Zeichnen ist
        der Maler bereits skaliert, `self.width()` wäre also zu groß."""
        return int(self.width() / self.zoom) + RASTER

    def _sichtbare_hoehe(self) -> int:
        return int(self.height() / self.zoom) + RASTER

    def _raster_zeichnen(self, maler: QPainter, farbe: str) -> None:
        """Punktraster (Abschnitt 13.6) statt Gitternetzlinien – ruhiger
        und im dunklen Theme weniger aufdringlich."""
        maler.setPen(QColor(farbe))
        for x in range(0, self._sichtbare_breite(), RASTER):
            for y in range(0, self._sichtbare_hoehe(), RASTER):
                maler.drawPoint(x, y)

    def _hilfslinien_zeichnen(self, maler: QPainter, farbe: str) -> None:
        if not self._hilfslinien:
            return
        stift = QPen(QColor(farbe))
        stift.setStyle(Qt.PenStyle.DashLine)
        maler.setPen(stift)
        for richtung, wert in self._hilfslinien:
            if richtung == "x":
                maler.drawLine(int(wert), 0, int(wert), self._sichtbare_hoehe())
            else:
                maler.drawLine(0, int(wert), self._sichtbare_breite(), int(wert))
