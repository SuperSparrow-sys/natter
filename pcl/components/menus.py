"""Menü-Komponenten: `MainMenu` und `PopupMenu`.

Siehe README.md, Abschnitt 5.2 (Palette „Standard") und
Arbeitspaket M15, Schritt 1.

Bis M15 war ein Schülerprogramm mit Menüleiste in Natter nicht
baubar – die Lücke stand im Kopf von `pcl/components/standard.py`
seit M1 als bekannt vermerkt. Menüs brauchen zweierlei, was es bis
dahin nicht gab: eine Komponente, die auf dem Formular liegt, ohne
dort etwas anzuzeigen (das kam mit `Control.nur_im_designer` und dem
Zeitgeber in M14), und einen Editor für ihren Inhalt.

Die Einträge sind strukturierte Datensätze, keine Textzeilen. Das
ist dieselbe Entscheidung wie beim UML-Eigenschaften-Dialog im
Diagramm-Editor: ein Menüeintrag hat einen Bezeichner, eine
Beschriftung, ein Tastenkürzel und Untereinträge. Als freier Text
ließe sich das weder prüfen noch sinnvoll bearbeiten. Ein Eintrag ist
ein `dict` mit diesen Schlüsseln:

``name``
    Bezeichner im Quelltext, z. B. ``mi_datei_beenden``. Über ihn
    findet ein Programm den Eintrag wieder (`eintrag_suchen`).
``caption``
    Was dasteht. Ein ``&`` davor macht den folgenden Buchstaben zum
    Zugriffsbuchstaben (``&Datei`` → Alt+D).
``shortcut``
    Tastenkürzel in Qt-Schreibweise (``Strg+Q`` wird angenommen und
    umgesetzt, damit niemand ``Ctrl`` tippen muss).
``enabled``, ``visible``
    Wie bei jeder Komponente: ein abgeschalteter Eintrag steht grau
    da, ein unsichtbarer fehlt im Menü.
``checkable``, ``checked``
    ``checkable`` macht den Eintrag zu einem Umschalter wie „Raster
    anzeigen“, ``checked`` ist sein Zustand. Ein Klick schreibt den
    neuen Zustand zurück in den Eintrag, bevor ``on_click`` läuft.
    Ein Eintrag mit ``checked``, aber ohne ``checkable`` ist ebenfalls
    ankreuzbar; so blieben Menüs aus älteren Fassungen gleich.
``separator``
    Eine Trennlinie. Sie hat keine Beschriftung und kein Ereignis.
``on_click``
    Name der Methode auf dem Formular, nicht die Funktion selbst –
    die `.pfm` und der erzeugte Quelltext können nur Namen tragen.
    Geprüft wird er beim Zuweisen der Einträge, aufgelöst beim Aufbau
    des Menüs.
``children``
    Untereinträge. Zwei Ebenen reichen für den Unterricht; tiefer
    verschachtelte Menüs sind selbst für Erwachsene mühsam.

Was nicht gesetzt ist, fehlt im `dict` – so bleibt die `.pfm` klein
und lesbar, und `eintrag_vollstaendig()` füllt die Vorgaben auf.
"""

from __future__ import annotations

import re
import weakref
from typing import Any

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QAction, QColor, QKeySequence, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QMenu, QMenuBar, QWidget

from pcl.control import Control
from pcl.errors import NatterPropertyError, NatterUnbekannteEigenschaftError
from pcl.properties import Prop

#: Ein Eintrag mit allen Feldern auf ihrer Vorgabe. Die Reihenfolge ist
#: die, in der der Menü-Editor die Felder zeigt.
EINTRAG_VORGABE: dict[str, Any] = {
    "name": "",
    "caption": "",
    "shortcut": "",
    "enabled": True,
    "visible": True,
    "checkable": False,
    "checked": False,
    "separator": False,
    "on_click": "",
    "children": [],
}

#: Mindesthöhe der Menüleiste in Pixeln. Die tatsächliche Höhe misst
#: das Formular, sobald die Einträge in der Leiste stehen: unter
#: Windows 11 ist ein Eintrag 32 Pixel hoch, und in einer festen
#: 26-Pixel-Leiste schob Qt alle Einträge in den Knopf „···“ am
#: rechten Rand. Die Koordinaten aus der `.pfm` hängen davon nicht ab,
#: sie zählen ab dem Arbeitsbereich unter der Leiste.
MENUELEISTE_HOEHE = 26


#: Deutsche Tastennamen -> die, die Qt versteht. Verglichen wird je
#: ganzem Teil zwischen „+“ und ohne Rücksicht auf Groß- und
#: Kleinschreibung; das Ersetzen von Teilzeichenketten machte aus
#: „Delete“ einmal „Entfete“ (Punkt 561).
_TASTENNAMEN = {
    "strg": "Ctrl",
    "umschalt": "Shift",
    "entf": "Del",
    "einfg": "Ins",
    "pos1": "Home",
    "ende": "End",
    "bild auf": "PgUp",
    "bild ab": "PgDown",
    "rück": "Backspace",
    "rücktaste": "Backspace",
    "eingabe": "Return",
    "leertaste": "Space",
    "pfeil links": "Left",
    "pfeil rechts": "Right",
    "pfeil hoch": "Up",
    "pfeil runter": "Down",
    "druck": "Print",
}

#: Qts Tastennamen -> die deutsche Anzeige im Menü.
_ANZEIGENAMEN = {
    "ctrl": "Strg",
    "shift": "Umschalt",
    "del": "Entf",
    "delete": "Entf",
    "ins": "Einfg",
    "insert": "Einfg",
    "home": "Pos1",
    "end": "Ende",
    "pgup": "Bild auf",
    "pgdown": "Bild ab",
    "backspace": "Rück",
    "return": "Eingabe",
    "enter": "Eingabe",
    "space": "Leertaste",
    "left": "Pfeil links",
    "right": "Pfeil rechts",
    "up": "Pfeil hoch",
    "down": "Pfeil runter",
    "print": "Druck",
}


def _teile_umsetzen(kuerzel: str, namen: dict[str, str]) -> str:
    """Setzt jeden Teil eines Kürzels über `namen` um. Ein „+“ am
    Ende (`Strg++`) ist die Plustaste, kein Trenner."""
    akkorde = []
    for akkord in re.split(r"(?<!\+),", kuerzel):
        akkord = akkord.strip()
        teile = re.split(r"\+(?=.)", akkord)
        akkorde.append(
            "+".join(namen.get(teil.strip().lower(), teil.strip()) for teil in teile)
        )
    return ", ".join(akkorde)


def _deutsche_kuerzel_umsetzen(kuerzel: str) -> str:
    """Macht aus „Strg+Q" das, was Qt versteht (`Ctrl+Q`).

    Wer die Oberfläche auf Deutsch bedient, tippt „Strg" – und `Qt`
    würde daraus stillschweigend gar kein Kürzel machen, ohne sich zu
    beschweren. Genau so eine stumme Nicht-Wirkung soll es in Natter
    nicht geben; was sich trotzdem nicht umsetzen lässt, meldet
    `eintraege_pruefen`.
    """
    return _teile_umsetzen(kuerzel, _TASTENNAMEN)


def kuerzel_fehler(kuerzel: str) -> str | None:
    """Was gegen `kuerzel` spricht, oder `None`, wenn Qt es versteht."""
    if not kuerzel.strip():
        return None
    folge = QKeySequence(_deutsche_kuerzel_umsetzen(kuerzel))
    # Jeder Teil einer Folge muss eine Taste sein: aus „Strg+S, Bla“
    # machte Qt eine Folge mit einer unbekannten zweiten Taste, und das
    # Kürzel wirkte nie (Punkt 621).
    if folge.toString() and all(
        folge[i].key() != Qt.Key.Key_unknown for i in range(folge.count())
    ):
        return None
    return (
        f"Das Tastenkürzel „{kuerzel}“ lässt sich nicht umsetzen. Gemeint "
        "sind Angaben wie „Strg+S“, „Umschalt+F5“, „Strg+Ende“, "
        "„Strg+Bild auf“ oder „Alt+Pfeil links“."
    )


def kuerzel_anzeige(kuerzel: str) -> str:
    """Die deutsche Schreibweise für die Anzeige im Menü.

    Nötig, weil Qt die Tastennamen selbst schreibt und dafür
    Übersetzungsdateien bräuchte, die PySide6 nicht mitliefert: im
    Menü stand „Ctrl+N", obwohl im Editor „Strg+N" eingetragen war und
    die ganze Oberfläche sonst deutsch ist. Aufgefallen beim ersten
    echten Probelauf des Notizblock-Programms, nicht in den Tests -
    die prüften die Tastenfolge, nicht ihre Beschriftung.

    Der Weg darum herum ist Qts eigener: steht im Text einer Aktion
    ein Tabulator, zeigt Qt alles dahinter rechtsbündig als
    Kürzelspalte und schreibt nichts Eigenes hin.
    """
    return _teile_umsetzen(_deutsche_kuerzel_umsetzen(kuerzel), _ANZEIGENAMEN)


def eintrag_vollstaendig(eintrag: dict[str, Any]) -> dict[str, Any]:
    """Ein Eintrag mit allen Feldern – fehlende auf ihrer Vorgabe.

    Untereinträge werden mit aufgefüllt, damit niemand die Rekursion
    selbst schreiben muss.
    """
    voll = dict(EINTRAG_VORGABE)
    voll.update(eintrag)
    voll["children"] = [eintrag_vollstaendig(kind) for kind in eintrag.get("children", [])]
    return voll


def _auffuellen(eintraege: list[dict[str, Any]]) -> None:
    """Füllt fehlende Felder an Ort und Stelle auf. Anders als
    `eintrag_vollstaendig` bleiben die Datensätze dieselben, also auch
    jeder Verweis, den `eintrag()` geliefert hat."""
    for eintrag in eintraege:
        for feld, vorgabe in EINTRAG_VORGABE.items():
            if feld not in eintrag:
                eintrag[feld] = list(vorgabe) if isinstance(vorgabe, list) else vorgabe
        _auffuellen(eintrag["children"])


def eintrag_knapp(eintrag: dict[str, Any]) -> dict[str, Any]:
    """Gegenstück zu `eintrag_vollstaendig`: alles weglassen, was auf
    seiner Vorgabe steht. So steht in der `.pfm` nur, was jemand
    wirklich eingestellt hat."""
    knapp: dict[str, Any] = {}
    for feld, vorgabe in EINTRAG_VORGABE.items():
        if feld == "children":
            continue
        wert = eintrag.get(feld, vorgabe)
        if wert != vorgabe:
            knapp[feld] = wert
    kinder = [eintrag_knapp(kind) for kind in eintrag.get("children", [])]
    if kinder:
        knapp["children"] = kinder
    return knapp


def eintraege_pruefen(eintraege: Any, _tiefe: int = 0) -> None:
    """Wirft `NatterPropertyError`, wenn die Einträge nicht die
    beschriebene Gestalt haben.

    Lieber hier laut als später stumm: ein Tippfehler im Feldnamen
    („childs" statt „children") würde sonst einen ganzen Teilbaum
    verschwinden lassen, ohne dass irgendwo etwas passiert.
    """
    if not isinstance(eintraege, list):
        raise NatterPropertyError(
            f"Menüeinträge müssen eine Liste sein, erhalten wurde {type(eintraege).__name__}."
        )
    if _tiefe > 2:
        raise NatterPropertyError(
            "Menüs gehen bis zur zweiten Ebene; tiefer verschachtelt findet sich "
            "niemand mehr zurecht."
        )
    for eintrag in eintraege:
        if not isinstance(eintrag, dict):
            raise NatterPropertyError(
                f"Ein Menüeintrag muss ein dict sein, erhalten wurde {type(eintrag).__name__}."
            )
        unbekannt = set(eintrag) - set(EINTRAG_VORGABE)
        if unbekannt:
            erlaubt = ", ".join(sorted(EINTRAG_VORGABE))
            raise NatterPropertyError(
                f"Unbekanntes Feld {sorted(unbekannt)[0]!r} in einem Menüeintrag. "
                f"Erlaubt sind: {erlaubt}."
            )
        fehler = kuerzel_fehler(str(eintrag.get("shortcut", "")))
        if fehler is not None:
            raise NatterPropertyError(fehler)
        eintraege_pruefen(eintrag.get("children", []), _tiefe + 1)
    # Ein doppeltes Kürzel macht die Einträge nicht ungültig. Der
    # Menü-Editor lehnt es beim Anwenden ab; zur Laufzeit wirkt nur
    # das erste (`_kuerzel_gewinner`). Bis zu Punkt 639 lehnte schon
    # das Zuweisen ab, und eine `.pfm` aus 0.4.3 mit zwei gleichen
    # Kürzeln ließ sich weder im Designer öffnen noch starten.


def doppeltes_kuerzel(eintraege: list[dict[str, Any]]) -> str | None:
    """Eine Meldung, wenn zwei Einträge desselben Menüs dasselbe
    Tastenkürzel tragen, sonst `None`.

    Qt hält ein solches Kürzel für mehrdeutig und löst gar keinen der
    beiden Einträge aus, ohne etwas zu melden (Punkt 633)."""
    gesehen: dict[str, str] = {}
    for eintrag in _blaetter_roh(eintraege):
        kuerzel = str(eintrag.get("shortcut", "") or "").strip()
        if not kuerzel or eintrag.get("separator") or kuerzel_fehler(kuerzel):
            continue
        schluessel = _kuerzel_schluessel(kuerzel)
        beschriftung = str(eintrag.get("caption", "")).replace("&", "") or "ohne Beschriftung"
        if schluessel in gesehen:
            return (
                f"Das Tastenkürzel „{kuerzel}“ steht bei „{gesehen[schluessel]}“ "
                f"und bei „{beschriftung}“. Eine Taste kann nur einen Eintrag "
                "auslösen; einer der beiden braucht ein anderes Kürzel."
            )
        gesehen[schluessel] = beschriftung
    return None


def _wirksame_blaetter(eintraege: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Die Einträge ohne Untereinträge, die sich bedienen lassen: selbst
    sichtbar und bedienbar, und jedes Untermenü darüber ebenso. Nur
    deren Kürzel wirken (Punkt 648)."""
    ergebnis = []
    for eintrag in eintraege:
        if eintrag.get("separator") or not eintrag.get("visible", True):
            continue
        if not eintrag.get("enabled", True):
            continue
        kinder = eintrag.get("children") or []
        if kinder:
            ergebnis.extend(_wirksame_blaetter(kinder))
        else:
            ergebnis.append(eintrag)
    return ergebnis


def _kuerzel_gewinner(
    eintraege: list[dict[str, Any]], belegt: set[str] | None = None
) -> set[int]:
    """Die Einträge (als `id`), deren Kürzel angemeldet werden: je
    Taste der erste bedienbare Eintrag, und keiner, dessen Taste in
    `belegt` schon vergeben ist. Qt hielte zwei gleiche Kürzel für
    mehrdeutig und löste keines aus (Punkte 633, 639)."""
    vergeben = set(belegt or ())
    gewinner: set[int] = set()
    for eintrag in _wirksame_blaetter(eintraege):
        kuerzel = str(eintrag.get("shortcut", "") or "").strip()
        if not kuerzel or kuerzel_fehler(kuerzel):
            continue
        schluessel = _kuerzel_schluessel(kuerzel)
        if schluessel in vergeben:
            continue
        vergeben.add(schluessel)
        gewinner.add(id(eintrag))
    return gewinner


def _blaetter_roh(eintraege: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Wie `_blaetter`, aber für Einträge, die noch nicht aufgefüllt
    sind."""
    ergebnis = []
    for eintrag in eintraege:
        kinder = eintrag.get("children") or []
        if kinder:
            ergebnis.extend(_blaetter_roh(kinder))
        else:
            ergebnis.append(eintrag)
    return ergebnis


def eintrag_suchen(eintraege: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    """Sucht einen Eintrag über seinen Bezeichner, auch in den
    Untereinträgen. Damit ein Programm ``menue.eintrag("mi_speichern")``
    schreiben kann, statt sich durch Listenindizes zu hangeln."""
    for eintrag in eintraege:
        if eintrag.get("name") == name:
            return eintrag
        treffer = eintrag_suchen(eintrag.get("children", []), name)
        if treffer is not None:
            return treffer
    return None


class _MenueSymbol(QWidget):
    """Grundlage der beiden Entwurfszeit-Symbole.

    Gezeichnet statt als Bilddatei beigelegt – wie beim Zeitgeber. So
    gibt es nichts, was beim Paketieren vergessen werden kann, und die
    Linienstärke passt sich der Größe an.

    Die Striche sind bewusst dünn (`seite / 26`): der Nutzer hat für
    die Symbole „filigraner und ein wenig bunter" festgelegt. Ein
    erster Entwurf mit `seite / 16` sah auf dem Formular aus wie ein
    Balkendiagramm.
    """

    RAHMEN = QColor("#37474f")
    LEISTE = QColor("#0067c0")
    GRUND = QColor("#f7f9fa")
    ZEILE = QColor("#7b8f9a")
    ZEIGER = QColor("#f2b134")

    def _maler(self) -> tuple[QPainter, QRectF, float]:
        maler = QPainter(self)
        maler.setRenderHint(QPainter.RenderHint.Antialiasing)
        flaeche = QRectF(self.rect()).adjusted(2.0, 2.0, -2.0, -2.0)
        strich = max(1.0, min(flaeche.width(), flaeche.height()) / 26)
        return maler, flaeche, strich

    def _zeilen(self, maler: QPainter, kasten: QRectF, strich: float) -> None:
        """Die angedeuteten Menüeinträge: drei Striche, der letzte kurz –
        so sieht auch bei 32 px eine Liste aus und kein Gitter."""
        maler.setPen(QPen(self.ZEILE, strich * 1.4))
        for nummer, anteil in enumerate((0.72, 0.72, 0.46)):
            hoehe = kasten.top() + kasten.height() * (0.28 + nummer * 0.24)
            links = kasten.left() + kasten.width() * 0.16
            maler.drawLine(links, hoehe, links + kasten.width() * anteil, hoehe)


class _HauptmenueSymbol(_MenueSymbol):
    """Fenster mit blauer Menüleiste und einem aufgeklappten Menü –
    dasselbe Motiv wie `komponente_mainmenu.svg` in der Palette, damit
    Kachel und Symbol auf dem Formular zusammengehören."""

    def paintEvent(self, event: Any) -> None:  # noqa: N802 (Qt-Konvention)
        maler, flaeche, strich = self._maler()

        maler.setPen(QPen(self.RAHMEN, strich))
        maler.setBrush(self.GRUND)
        maler.drawRect(flaeche)

        leiste = QRectF(flaeche.left(), flaeche.top(), flaeche.width(), flaeche.height() * 0.22)
        maler.setPen(Qt.PenStyle.NoPen)
        maler.setBrush(self.LEISTE)
        maler.drawRect(leiste.adjusted(strich, strich, -strich, 0))

        kasten = QRectF(
            flaeche.left() + flaeche.width() * 0.12,
            leiste.bottom() + flaeche.height() * 0.08,
            flaeche.width() * 0.6,
            flaeche.height() * 0.58,
        )
        maler.setPen(QPen(self.RAHMEN, strich))
        maler.setBrush(self.GRUND)
        maler.drawRect(kasten)
        self._zeilen(maler, kasten, strich)
        maler.end()


class _KlappmenueSymbol(_MenueSymbol):
    """Freischwebendes Klappmenü mit dem Mauszeiger davor – ohne
    Fensterrahmen und ohne blaue Leiste. Genau daran ist es auf dem
    Formular vom Hauptmenü zu unterscheiden; zwei gleich aussehende
    Symbole wären schlimmer als gar keines."""

    def paintEvent(self, event: Any) -> None:  # noqa: N802 (Qt-Konvention)
        maler, flaeche, strich = self._maler()

        kasten = QRectF(
            flaeche.left() + flaeche.width() * 0.32,
            flaeche.top() + flaeche.height() * 0.08,
            flaeche.width() * 0.64,
            flaeche.height() * 0.78,
        )
        maler.setPen(QPen(self.RAHMEN, strich))
        maler.setBrush(self.GRUND)
        maler.drawRect(kasten)
        self._zeilen(maler, kasten, strich)

        # Der Mauszeiger als Streckenzug in Anteilen der Fläche - so
        # behält er seine Gestalt, egal wie groß das Symbol gerät.
        def punkt(x_anteil: float, y_anteil: float) -> QPointF:
            return QPointF(
                flaeche.left() + flaeche.width() * x_anteil,
                flaeche.top() + flaeche.height() * y_anteil,
            )

        zeiger = QPolygonF(
            [
                punkt(0.0, 0.06),
                punkt(0.30, 0.40),
                punkt(0.13, 0.42),
                punkt(0.20, 0.62),
                punkt(0.12, 0.66),
                punkt(0.05, 0.46),
            ]
        )
        maler.setPen(QPen(self.RAHMEN, strich))
        maler.setBrush(self.ZEIGER)
        maler.drawPolygon(zeiger)
        maler.end()


class _Menue(Control):
    """Gemeinsamer Kern von `MainMenu` und `PopupMenu`.

    Beide halten denselben Baum aus Einträgen und bauen daraus zur
    Laufzeit Qt-Menüs; sie unterscheiden sich nur darin, wo das
    Menü erscheint.
    """

    nur_im_designer = True

    #: Auf dem Formular ist nur das Symbol zu sehen, und das ist immer
    #: gleich groß - eine Menüleiste zieht man nicht auf.
    width = Prop(int, 32, kategorie="Layout", doc="Breite des Symbols")
    height = Prop(int, 32, kategorie="Layout", doc="Höhe des Symbols")

    def __init__(self, parent: Any = None) -> None:
        self._eintraege: list[dict[str, Any]] = []
        #: Die aufgebauten Qt-Objekte, damit sie nicht vom
        #: Müllsammler geholt werden, solange das Menü lebt.
        self._qt_objekte: list[Any] = []
        # Das Formular über die Elternkette: ein Menü kann im Designer
        # auf einem Panel gelandet sein, und die Methoden stehen im
        # Formular, nicht im Panel (Punkt 593).
        formular = parent
        while isinstance(formular, Control):
            formular = formular._eltern
        self._formular = formular if formular is not None else parent
        super().__init__(parent)

    #: Das Entwurfszeit-Symbol dieser Menüart, von den Unterklassen
    #: gesetzt.
    SYMBOL: type[_MenueSymbol] = _MenueSymbol

    def _qwidget_erzeugen(self, eltern_widget: QWidget | None) -> QWidget:
        return type(self).SYMBOL(eltern_widget)

    @property
    def entries(self) -> list[dict[str, Any]]:
        """Die Einträge des Menüs als Liste strukturierter Datensätze.

        Gelesen wird eine Kopie: wer ``menue.entries[0]["caption"]``
        ändert, soll nicht aus Versehen am Original schrauben, ohne
        dass das Menü davon erfährt. Zum Ändern gibt es die Zuweisung
        und `eintrag()`.
        """
        return [eintrag_vollstaendig(eintrag) for eintrag in self._eintraege]

    @entries.setter
    def entries(self, eintraege: list[dict[str, Any]]) -> None:
        eintraege_pruefen(eintraege)
        self._handler_pruefen(eintraege)
        self._eintraege = [eintrag_vollstaendig(eintrag) for eintrag in eintraege]
        self._menue_erneuern()

    def eintrag(self, name: str) -> dict[str, Any] | None:
        """Der Eintrag mit diesem Bezeichner – zum Lesen und
        Ändern, denn hier kommt das Original zurück. Nach einer
        Änderung ``menue.aktualisieren()`` aufrufen."""
        return eintrag_suchen(self._eintraege, name)

    def aktualisieren(self) -> None:
        """Baut das Menü neu auf – nötig, nachdem ein über `eintrag()`
        geholter Datensatz von Hand geändert wurde.

        Geprüft und aufgefüllt wird zuerst, wie beim Zuweisen: ein
        angehängter knapper Eintrag endete sonst mit `KeyError`, und die
        Leiste war schon halb abgebaut (Punkt 597)."""
        eintraege_pruefen(self._eintraege)
        self._handler_pruefen(self._eintraege)
        _auffuellen(self._eintraege)
        self._menue_erneuern()

    # -- Aufbau ----------------------------------------------------------

    def _handler_suchen(self, name: str):
        """Die Methode des Formulars, die zu diesem Namen gehört.

        Ein leerer Name heißt „kein Ereignis“. Ein Name, zu dem es
        keine Methode gibt, meldet `_handler_pruefen` schon beim
        Zuweisen der Einträge; hier bleibt ein solcher Eintrag nur
        noch wirkungslos.
        """
        if not name or self._formular is None:
            return None
        return getattr(self._formular, name, None)

    def _handler_pruefen(self, eintraege: list[dict[str, Any]]) -> None:
        """Meldet einen Menüeintrag, dessen Methode es nicht gibt.

        Bis Punkt 75 blieb ein Tippfehler im Namen ohne jede Meldung:
        der Eintrag stand im Menü, ein Klick darauf tat nichts. Jetzt
        bricht der Start mit einer deutschen Meldung über die
        gewöhnliche Fehleranzeige ab - so wie bei jedem anderen
        Tippfehler in `create_components()` auch.

        Nicht im Designer: dort ist ein Menüeintrag, dessen Methode
        noch nicht geschrieben ist, der Normalfall, und das Formular
        muss sich trotzdem öffnen lassen.
        """
        formular = self._formular
        if formular is None or getattr(formular, "_entwurfsansicht", False):
            return
        for eintrag in eintraege:
            name = eintrag.get("on_click", "")
            if name and not callable(getattr(formular, name, None)):
                beschriftung = eintrag.get("caption", "").replace("&", "")
                raise NatterUnbekannteEigenschaftError(
                    f"Der Menüeintrag „{beschriftung}“ soll beim Anklicken "
                    f"die Methode {name!r} aufrufen, aber {type(formular).__name__} "
                    f"hat keine Methode mit diesem Namen."
                )
            self._handler_pruefen(eintrag.get("children", []))

    def _aktion_bauen(self, eintrag: dict[str, Any], eltern: QMenu | QMenuBar):
        if eintrag["separator"]:
            return eltern.addSeparator()

        kinder = eintrag["children"]
        if kinder:
            untermenue = QMenu(eintrag["caption"], eltern)
            untermenue.setEnabled(eintrag["enabled"])
            for kind in kinder:
                self._aktion_bauen(kind, untermenue)
            eltern.addMenu(untermenue)
            untermenue.menuAction().setVisible(eintrag["visible"])
            self._qt_objekte.append(untermenue)
            return untermenue

        beschriftung = eintrag["caption"]
        if eintrag["shortcut"]:
            # Der Tabulator ist Absicht, siehe `kuerzel_anzeige`.
            beschriftung += "\t" + kuerzel_anzeige(eintrag["shortcut"])
        aktion = QAction(beschriftung, eltern)
        aktion.setEnabled(eintrag["enabled"])
        aktion.setVisible(eintrag["visible"])
        if eintrag["checkable"] or eintrag["checked"]:
            aktion.setCheckable(True)
            aktion.setChecked(eintrag["checked"])
            # Vor triggered verbunden, also vor dem Handler: der liest
            # schon den neuen Zustand (Punkt 559).
            aktion.toggled.connect(
                lambda an, e=eintrag: e.__setitem__("checked", an)
            )
        if eintrag["shortcut"] and id(eintrag) in getattr(self, "_gewinner", ()):
            aktion.setShortcut(QKeySequence(_deutsche_kuerzel_umsetzen(eintrag["shortcut"])))
        handler = self._handler_suchen(eintrag["on_click"])
        if handler is not None:
            aktion.triggered.connect(lambda _geprueft=False, h=handler: h(self))
        eltern.addAction(aktion)
        self._qt_objekte.append(aktion)
        return aktion

    def _menue_erneuern(self) -> None:
        """Von den Unterklassen überschrieben: `MainMenu` baut eine
        Leiste, `PopupMenu` ein Klappmenü."""


class MainMenu(_Menue):
    """Menüleiste am oberen Rand des Fensters.

    Auf dem Formular liegt nur ein kleines Symbol; die Leiste selbst
    erscheint erst im laufenden Programm. Das ist dieselbe Regel wie
    beim Zeitgeber: was im fertigen Programm keine Fläche einnimmt,
    nimmt im Designer auch keine weg.

    Die Leiste sitzt über dem Inhalt des Formulars: das Fenster
    wächst um ihre Höhe, die Komponenten behalten ihre Koordinaten:
    ``Top = 0`` ist der obere Rand des Arbeitsbereichs, nicht des
    Fensters.
    """

    SYMBOL = _HauptmenueSymbol

    def __init__(self, parent: Any = None) -> None:
        self._leiste: QMenuBar | None = None
        super().__init__(parent)

    def in_leiste_aufbauen(self, leiste: QMenuBar) -> None:
        """Baut die Einträge in diese Menüleiste. Ruft das Formular
        beim Anzeigen auf; danach merkt sich das Menü die Leiste und
        baut sich bei jeder Änderung von selbst neu auf."""
        self._leiste = leiste
        self._menue_erneuern()

    def _menue_erneuern(self) -> None:
        leiste = self._leiste
        if leiste is None:
            return
        # Die Untermenüs hängen als Kinder an der Leiste; `clear()`
        # nimmt nur ihre Einträge weg. Jedes `aktualisieren()` ließ
        # sonst ein Untermenü mehr zurück (Punkt 621).
        for objekt in self._qt_objekte:
            if isinstance(objekt, QMenu):
                objekt.deleteLater()
        leiste.clear()
        self._qt_objekte.clear()
        self._gewinner = _kuerzel_gewinner(self._eintraege)
        for eintrag in self._eintraege:
            self._aktion_bauen(eintrag, leiste)
        _klappmenue_kuerzel_erneuern(self._formular)


class PopupMenu(_Menue):
    """Klappmenü auf die rechte Maustaste.

    Zugeordnet wird es über die Eigenschaft ``popup_menu`` einer
    sichtbaren Komponente: ``self.sg_tabelle.popup_menu =
    self.pm_tabelle``. Ohne Zuordnung passiert nichts – ein Klappmenü
    ohne Ort, an dem es aufklappt, ist kein Fehler, sondern nur noch
    nicht fertig.
    """

    SYMBOL = _KlappmenueSymbol

    def __init__(self, parent: Any = None) -> None:
        self._aufgeklappt_an: Control | None = None
        super().__init__(parent)

    @property
    def popup_component(self) -> Control | None:
        """Die Komponente, an der das Klappmenü zuletzt aufging, oder
        `None`. Hängt dasselbe Klappmenü an zwei Listen, sagt sie der
        Methode, welche gemeint ist (Punkt 620). Bei einem Tastenkürzel
        ist es die Komponente, an der es ausgelöst wurde; Kürzel eines
        Klappmenüs wirken nur, solange eine seiner Komponenten den
        Fokus hat (Punkte 623, 624)."""
        return self._aufgeklappt_an

    def menue(self, eltern: QWidget | None = None) -> QMenu:
        """Das fertige `QMenu`. Baut es bei jedem Aufruf neu auf,
        damit Änderungen an den Einträgen sofort sichtbar sind; das
        vorige wird freigegeben, sonst blieb bei jedem Rechtsklick ein
        Menü mehr am Widget hängen (Punkt 621)."""
        for objekt in self._qt_objekte:
            if isinstance(objekt, QMenu) and not objekt.isVisible():
                objekt.deleteLater()
        menue = QMenu(eltern)
        self._qt_objekte = [menue]
        self._gewinner = _kuerzel_gewinner(self._eintraege)
        for eintrag in self._eintraege:
            self._aktion_bauen(eintrag, menue)
        return menue

    def _menue_erneuern(self) -> None:
        """Meldet die Tastenkürzel der Einträge an den Komponenten an,
        denen das Klappmenü zugeordnet ist.

        Die Aktionen des Klappmenüs entstehen erst beim Aufklappen. Ein
        Kürzel wie „Entf“ stand deshalb im Menü, wirkte aber nie
        (Punkt 591). Es gilt dort, wo das Klappmenü aufgeht: solange
        eine seiner Komponenten den Fokus hat. Bis dahin galt es im
        ganzen Fenster, und mit zwei Listen, deren Klappmenüs beide
        „Entf“ trugen, löschte die Taste in der Liste ohne Fokus
        (Punkt 623). Ein Kürzel, das schon das Hauptmenü trägt, wird
        nicht angemeldet: Qt hielte es für mehrdeutig und löste gar
        nichts aus (Punkt 613). Im Designer wird nichts angemeldet."""
        for aktion in getattr(self, "_kuerzel_aktionen", []):
            # Sofort abschalten und abnehmen: `deleteLater` allein ließ
            # das Kürzel bis zum nächsten Ereignisdurchlauf wirken.
            aktion.setEnabled(False)
            besitzer = aktion.parent()
            if isinstance(besitzer, QWidget):
                besitzer.removeAction(aktion)
            aktion.deleteLater()
        self._kuerzel_aktionen: list[QAction] = []
        formular = self._formular
        if formular is None or getattr(formular, "_entwurfsansicht", False):
            return
        gewinner = _kuerzel_gewinner(self._eintraege, _hauptmenue_kuerzel(formular))
        for komponente in self._komponenten():
            for eintrag in _blaetter(self._eintraege):
                if id(eintrag) not in gewinner:
                    continue
                aktion = QAction(komponente._qwidget)
                aktion.setShortcut(
                    QKeySequence(_deutsche_kuerzel_umsetzen(eintrag["shortcut"]))
                )
                aktion.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
                aktion.setEnabled(eintrag["enabled"])
                aktion.triggered.connect(
                    lambda _an=False, e=eintrag, k=komponente: self._kuerzel_ausloesen(e, k)
                )
                komponente._qwidget.addAction(aktion)
                self._kuerzel_aktionen.append(aktion)

    def _kuerzel_ausloesen(self, eintrag: dict[str, Any], komponente: Control) -> None:
        # Bei jedem Kürzel neu gesetzt; vorher blieb nach einem Kürzel
        # die Komponente des letzten Rechtsklicks stehen (Punkt 624).
        self._aufgeklappt_an = komponente
        if eintrag["checkable"] or eintrag["checked"]:
            eintrag["checked"] = not eintrag["checked"]
        handler = self._handler_suchen(eintrag["on_click"])
        if handler is not None:
            handler(self)

    def _zuordnen(self, komponente: Control) -> None:
        """Merkt sich eine Komponente, der dieses Klappmenü zugeordnet
        wurde. Aufgerufen vom Setter `popup_menu`. Schwach gehalten:
        das Klappmenü soll eine Komponente nicht am Leben halten."""
        refs = self.__dict__.setdefault("_zugeordnet", [])
        if not any(r() is komponente for r in refs):
            refs.append(weakref.ref(komponente))

    def _komponenten(self) -> list[Control]:
        """Die Komponenten, denen dieses Klappmenü zugeordnet ist.

        Über die Zuordnung selbst bestimmt, nicht über die Attribute des
        Formulars: Knöpfe, die ein Programm in einer Liste hält, fehlten
        dort, und ihr Kürzel wirkte nicht (Punkt 653)."""
        gefunden: list[Control] = []
        lebend = []
        for ref in self.__dict__.get("_zugeordnet", []):
            komponente = ref()
            if komponente is None:
                continue
            lebend.append(ref)
            if getattr(komponente, "_popup_menu", None) is self:
                gefunden.append(komponente)
        self.__dict__["_zugeordnet"] = lebend
        return gefunden

    def aufklappen(self, komponente: Control, x: int, y: int) -> None:
        """Klappt das Menü an dieser Stelle der Komponente auf."""
        self._aufgeklappt_an = komponente
        widget = komponente._qwidget
        punkt = widget.mapToGlobal(widget.rect().topLeft()) + QPoint(x, y)
        menue = self.menue(widget)
        menue.exec(punkt)
        menue.deleteLater()


def _blaetter(eintraege: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Alle Einträge ohne Untereinträge, auch in den Untermenüs."""
    ergebnis = []
    for eintrag in eintraege:
        if eintrag["children"]:
            ergebnis.extend(_blaetter(eintrag["children"]))
        else:
            ergebnis.append(eintrag)
    return ergebnis


def _kuerzel_schluessel(kuerzel: str) -> str:
    """Ein Kürzel in einer Form, in der gleiche Tasten gleich sind."""
    return QKeySequence(_deutsche_kuerzel_umsetzen(kuerzel)).toString()


def _hauptmenue_kuerzel(formular: Any) -> set[str]:
    """Die Kürzel, die auf `formular` schon das Hauptmenü trägt. Nur
    sichtbare, bedienbare Einträge belegen eine Taste; ein
    abgeschalteter „Datensatz löschen“ mit Entf ließ sonst Entf im
    Klappmenü einer Liste wirkungslos (Punkt 648)."""
    belegt: set[str] = set()
    for wert in vars(formular).values():
        if isinstance(wert, MainMenu):
            belegt.update(
                _kuerzel_schluessel(e["shortcut"])
                for e in _wirksame_blaetter(wert._eintraege)
                if e.get("shortcut") and not kuerzel_fehler(str(e["shortcut"]))
            )
    return belegt


def _klappmenue_kuerzel_erneuern(formular: Any) -> None:
    """Gleicht die Kürzel aller Klappmenüs neu ab, wenn sich das
    Hauptmenü geändert hat."""
    if formular is None:
        return
    for wert in list(vars(formular).values()):
        if isinstance(wert, PopupMenu):
            wert._menue_erneuern()
