"""Menü-Komponenten: `MainMenu` und `PopupMenu`.

Siehe README.md, Abschnitt 5.2 (Palette „Standard") und
`docs/arbeitspakete/M15.md`, Schritt 1. Vorbild sind `TMainMenu` und
`TPopupMenu` aus Lazarus.

Bis M15 war ein Schülerprogramm mit Menüleiste in Natter **nicht
baubar** – die Lücke stand im Kopf von `pcl/components/standard.py`
seit M1 als bekannt vermerkt. Menüs brauchen zweierlei, was es bis
dahin nicht gab: eine Komponente, die auf dem Formular liegt, ohne
dort etwas anzuzeigen (das kam mit `Control.nur_im_designer` und dem
Zeitgeber in M14), und einen Editor für ihren Inhalt.

**Die Einträge sind strukturierte Datensätze, keine Textzeilen.** Das
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
    Zugriffsbuchstaben, genau wie in Lazarus (``&Datei`` → Alt+D).
``shortcut``
    Tastenkürzel in Qt-Schreibweise (``Strg+Q`` wird angenommen und
    umgesetzt, damit niemand ``Ctrl`` tippen muss).
``enabled``, ``checked``
    Wie bei jeder Komponente; ``checked`` macht den Eintrag
    ankreuzbar.
``separator``
    Eine Trennlinie. Sie hat keine Beschriftung und kein Ereignis.
``on_click``
    **Name** der Methode auf dem Formular, nicht die Funktion selbst –
    die `.pfm` und der erzeugte Quelltext können nur Namen tragen.
    Aufgelöst wird er erst beim Aufbau des Menüs.
``children``
    Untereinträge. Zwei Ebenen reichen für den Unterricht; tiefer
    verschachtelte Menüs sind selbst für Erwachsene mühsam.

Was nicht gesetzt ist, fehlt im `dict` – so bleibt die `.pfm` klein
und lesbar, und `eintrag_vollstaendig()` füllt die Vorgaben auf.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QPoint, QPointF, QRectF, Qt
from PySide6.QtGui import QAction, QColor, QKeySequence, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import QMenu, QMenuBar, QWidget

from pcl.control import Control
from pcl.errors import NatterPropertyError
from pcl.properties import Prop

#: Ein Eintrag mit allen Feldern auf ihrer Vorgabe. Die Reihenfolge ist
#: die, in der der Menü-Editor die Felder zeigt.
EINTRAG_VORGABE: dict[str, Any] = {
    "name": "",
    "caption": "",
    "shortcut": "",
    "enabled": True,
    "checked": False,
    "separator": False,
    "on_click": "",
    "children": [],
}

#: Höhe der Menüleiste in Pixeln. Fest statt gemessen: die `.pfm` hält
#: Koordinaten, die auf jedem Rechner dasselbe bedeuten sollen, und
#: eine gemessene Höhe fiele je nach Windows-Schriftgröße anders aus.
MENUELEISTE_HOEHE = 26


#: Deutsche Schreibweise -> die, die Qt versteht.
_TASTENNAMEN = {"Strg": "Ctrl", "Umschalt": "Shift", "Entf": "Del", "Einfg": "Ins"}


def _deutsche_kuerzel_umsetzen(kuerzel: str) -> str:
    """Macht aus „Strg+Q" das, was Qt versteht (`Ctrl+Q`).

    Wer die Oberfläche auf Deutsch bedient, tippt „Strg" – und `Qt`
    würde daraus stillschweigend gar kein Kürzel machen, ohne sich zu
    beschweren. Genau so eine stumme Nicht-Wirkung soll es in Natter
    nicht geben.
    """
    for deutsch, englisch in _TASTENNAMEN.items():
        kuerzel = kuerzel.replace(deutsch, englisch)
    return kuerzel


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
    for deutsch, englisch in _TASTENNAMEN.items():
        kuerzel = kuerzel.replace(englisch, deutsch)
    return kuerzel


def eintrag_vollstaendig(eintrag: dict[str, Any]) -> dict[str, Any]:
    """Ein Eintrag mit allen Feldern – fehlende auf ihrer Vorgabe.

    Untereinträge werden mit aufgefüllt, damit niemand die Rekursion
    selbst schreiben muss.
    """
    voll = dict(EINTRAG_VORGABE)
    voll.update(eintrag)
    voll["children"] = [eintrag_vollstaendig(kind) for kind in eintrag.get("children", [])]
    return voll


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
        eintraege_pruefen(eintrag.get("children", []), _tiefe + 1)


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
    die Symbole „filigraner, wie in Lazarus, und ein wenig bunter"
    festgelegt. Ein erster Entwurf mit `seite / 16` sah auf dem
    Formular aus wie ein Balkendiagramm.
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
    Laufzeit Qt-Menüs; sie unterscheiden sich nur darin, **wo** das
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
        self._formular = parent
        super().__init__(parent)

    #: Das Entwurfszeit-Symbol dieser Menüart, von den Unterklassen
    #: gesetzt.
    SYMBOL: type[_MenueSymbol] = _MenueSymbol

    def _qwidget_erzeugen(self, eltern_widget: QWidget | None) -> QWidget:
        return type(self).SYMBOL(eltern_widget)

    @property
    def entries(self) -> list[dict[str, Any]]:
        """Die Einträge des Menüs als Liste strukturierter Datensätze.

        Gelesen wird eine **Kopie**: wer ``menue.entries[0]["caption"]``
        ändert, soll nicht aus Versehen am Original schrauben, ohne
        dass das Menü davon erfährt. Zum Ändern gibt es die Zuweisung
        und `eintrag()`.
        """
        return [eintrag_vollstaendig(eintrag) for eintrag in self._eintraege]

    @entries.setter
    def entries(self, eintraege: list[dict[str, Any]]) -> None:
        eintraege_pruefen(eintraege)
        self._eintraege = [eintrag_vollstaendig(eintrag) for eintrag in eintraege]
        self._menue_erneuern()

    def eintrag(self, name: str) -> dict[str, Any] | None:
        """Der Eintrag mit diesem Bezeichner – zum Lesen **und**
        Ändern, denn hier kommt das Original zurück. Nach einer
        Änderung ``menue.aktualisieren()`` aufrufen."""
        return eintrag_suchen(self._eintraege, name)

    def aktualisieren(self) -> None:
        """Baut das Menü neu auf – nötig, nachdem ein über `eintrag()`
        geholter Datensatz von Hand geändert wurde."""
        self._menue_erneuern()

    # -- Aufbau ----------------------------------------------------------

    def _handler_suchen(self, name: str):
        """Die Methode des Formulars, die zu diesem Namen gehört.

        Ein leerer Name heißt „kein Ereignis". Ein Name, zu dem es
        keine Methode gibt, ist dagegen ein Fehler, den jemand sehen
        soll – nur passiert er beim Aufbau des Fensters, wo eine
        Ausnahme das ganze Programm mitnähme. Deshalb bleibt der
        Eintrag stattdessen wirkungslos und meldet sich über die
        gewöhnliche Fehleranzeige, sobald jemand ihn anklickt.
        """
        if not name or self._formular is None:
            return None
        return getattr(self._formular, name, None)

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
            self._qt_objekte.append(untermenue)
            return untermenue

        beschriftung = eintrag["caption"]
        if eintrag["shortcut"]:
            # Der Tabulator ist Absicht, siehe `kuerzel_anzeige`.
            beschriftung += "\t" + kuerzel_anzeige(eintrag["shortcut"])
        aktion = QAction(beschriftung, eltern)
        aktion.setEnabled(eintrag["enabled"])
        if eintrag["checked"]:
            aktion.setCheckable(True)
            aktion.setChecked(True)
        if eintrag["shortcut"]:
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
    """Menüleiste am oberen Rand des Fensters, wie `TMainMenu` in
    Lazarus.

    Auf dem Formular liegt nur ein kleines Symbol; die Leiste selbst
    erscheint erst im laufenden Programm. Das ist dieselbe Regel wie
    beim Zeitgeber: was im fertigen Programm keine Fläche einnimmt,
    nimmt im Designer auch keine weg.

    Die Leiste sitzt **über** dem Inhalt des Formulars: das Fenster
    wächst um ihre Höhe, die Komponenten behalten ihre Koordinaten.
    Genau so verhält sich Lazarus auch – dort ist ``Top = 0`` der
    obere Rand des Arbeitsbereichs, nicht des Fensters.
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
        leiste.clear()
        self._qt_objekte.clear()
        for eintrag in self._eintraege:
            self._aktion_bauen(eintrag, leiste)


class PopupMenu(_Menue):
    """Klappmenü auf die rechte Maustaste, wie `TPopupMenu` in Lazarus.

    Zugeordnet wird es über die Eigenschaft ``popup_menu`` einer
    sichtbaren Komponente: ``self.sg_tabelle.popup_menu =
    self.pm_tabelle``. Ohne Zuordnung passiert nichts – ein Klappmenü
    ohne Ort, an dem es aufklappt, ist kein Fehler, sondern nur noch
    nicht fertig.
    """

    SYMBOL = _KlappmenueSymbol

    def menue(self, eltern: QWidget | None = None) -> QMenu:
        """Das fertige `QMenu`. Baut es bei jedem Aufruf neu auf,
        damit Änderungen an den Einträgen sofort sichtbar sind."""
        menue = QMenu(eltern)
        self._qt_objekte = [menue]
        for eintrag in self._eintraege:
            self._aktion_bauen(eintrag, menue)
        return menue

    def aufklappen(self, komponente: Control, x: int, y: int) -> None:
        """Klappt das Menü an dieser Stelle der Komponente auf."""
        widget = komponente._qwidget
        punkt = widget.mapToGlobal(widget.rect().topLeft()) + QPoint(x, y)
        self.menue(widget).exec(punkt)
