"""Control: Basisklasse aller platzierbaren pcl-Komponenten mit Qt-Anbindung.

Siehe README.md, Abschnitt 5. Verbindet den Prop-Zugriff aus
`pcl.properties` mit einem echten QWidget: eine Zuweisung wie
``self.b_ok.caption = "OK"`` ändert sofort die Anzeige (live).

Die Maus gehört jeder sichtbaren Komponente (Abschnitt 5.4). Bis M15
war `on_click` nur am `Button` verdrahtet, weil nur er ein eigenes
Qt-Klicksignal hat; `Label` und `Image` hatten dafür je eine eigene
QLabel-Unterklasse, die `mousePressEvent` abfing. Drei Nachbauten
derselben Sache, und für `Shape`, `Panel` oder die frische `PaintBox`
gab es sie gar nicht - ausgerechnet eine Zeichenfläche konnte also
nicht das, wofür man sie im Unterricht benutzt: mit der Maus malen.

Jetzt hängt ein Ereignisfilter am Widget, und alle fünf Ereignisse
stehen an einer Stelle. `Button` behält sein natives Klicksignal
(`_klick_kommt_vom_widget`), damit sein `on_click` nicht doppelt
auslöst.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtWidgets import QWidget

from pcl.font import Font
from pcl.properties import MAUS_EREIGNISSE, Event, Komponente, Prop

#: Weitergereicht, damit `from pcl.control import MAUS_EREIGNISSE`
#: dort steht, wo die Ereignisse auch deklariert sind.
__all__ = ["Control", "EREIGNIS_PARAMETER", "MAUS_EREIGNISSE"]

#: Was eine Ereignis-Methode über `sender` hinaus bekommt.
#:
#: `on_click` und `on_double_click` bleiben bei `(self, sender)`: mehr
#: braucht ein Klick nicht. Wer weiß, wo geklickt wurde, nimmt
#: `on_mouse_down`; dort stehen die Koordinaten dabei, gezählt von der
#: linken oberen Ecke der Komponente. Der Ereignis-Generator
#: (`ide/codegen/ereignis.py`) legt die Methode danach mit der richtigen
#: Parameterliste an.
EREIGNIS_PARAMETER: dict[str, tuple[str, ...]] = {
    "on_mouse_down": ("x", "y"),
    "on_mouse_move": ("x", "y"),
    "on_mouse_up": ("x", "y"),
    # `StringGrid`: welche Zelle. Ohne Spalte und Zeile müsste der
    # Schüler im Handler erst `sender` nach der Auswahl fragen - eine
    # Umständlichkeit, die zwei Parameter erledigen.
    "on_select_cell": ("spalte", "zeile"),
    "on_edit_cell": ("spalte", "zeile", "text"),
}


class _MausFilter(QObject):
    """Reicht die Mausereignisse des Widgets an seine Komponente weiter.

    Ein Ereignisfilter statt einer QWidget-Unterklasse je Komponente:
    sonst bräuchte jede der zwanzig Komponenten eine eigene Klasse, nur
    um `mousePressEvent` zu überschreiben - und die, die ihr Widget von
    Qt fertig bekommen (`QPushButton`, `QComboBox`), könnten es gar
    nicht.

    Gibt immer `False` zurück: das Ereignis läuft danach ganz normal
    weiter. Ohne das könnte man in ein `Edit` nicht mehr hineinklicken.
    """

    def __init__(self, control: Control) -> None:
        super().__init__()
        self._control = control
        self._gedrueckt = False

    def eventFilter(self, objekt: QObject, ereignis: QEvent) -> bool:  # noqa: N802
        art = ereignis.type()
        if art == QEvent.Type.MouseButtonPress:
            self._gedrueckt = True
            self._control._maus_melden("on_mouse_down", ereignis)
        elif art == QEvent.Type.MouseMove:
            self._control._maus_melden("on_mouse_move", ereignis)
        elif art == QEvent.Type.MouseButtonRelease:
            self._control._maus_melden("on_mouse_up", ereignis)
            # `on_click` erst beim Loslassen, und nur wenn auf derselben
            # Komponente gedrückt wurde - wer danebenzieht, hat es sich
            # anders überlegt. Genauso verhält sich ein echter Knopf.
            if self._gedrueckt and not self._control._klick_kommt_vom_widget:
                self._control._ereignis_ausloesen("on_click")
            self._gedrueckt = False
        elif art == QEvent.Type.MouseButtonDblClick:
            self._control._ereignis_ausloesen("on_double_click")
        return False


class Control(Komponente):
    """Gemeinsame Basis aller auf einem Formular platzierten Komponenten."""

    #: Ob die Komponente nur im Designer zu sehen ist.
    #:
    #: Manche Komponenten haben nichts anzuzeigen - ein Zeitgeber etwa
    #: tickt nur. Im Designer braucht man sie trotzdem: man muss sie
    #: anklicken können, um im Objektinspektor ihr Intervall
    #: einzustellen. Dafür steht ein kleines Symbol auf dem Formular, das
    #: im laufenden Programm verschwindet; genau das macht diese Angabe.
    #:
    #: Der Rest der IDE braucht dafür keine Sonderfälle: solche
    #: Komponenten sind gewöhnliche `Control`s und tauchen damit von
    #: selbst im Komponentenbaum, im Objektinspektor und in der `.pfm`
    #: auf.
    nur_im_designer = False

    #: Welches Ereignis ein Doppelklick im Designer anlegt.
    #:
    #: Nur nötig, wenn eine Komponente mehrere eigene Ereignisse
    #: hat und trotzdem eines davon das kennzeichnende ist - beim
    #: `StringGrid` die Auswahl einer Zelle, nicht deren Änderung. Bei
    #: einer Komponente mit genau einem Ereignis findet der Designer es
    #: von selbst, und wo jede Wahl geraten wäre (`DBNavigator`), bleibt
    #: die Angabe bewusst leer.
    standard_ereignis: str | None = None

    #: Ob andere Komponenten in dieser hier liegen dürfen.
    #:
    #: Im Code ging das immer schon - `RadioButton(self.g_zahlung)`
    #: hängt den Knopf an die `GroupBox`, das erledigt `__init__` von
    #: selbst. Der Designer legte bis dahin trotzdem jede
    #: abgelegte Komponente ans Formular; ein Panel war dort eine
    #: Fläche, auf der nichts liegen konnte. Diese Angabe sagt ihm,
    #: wohin er eine Ablage geben darf.
    ist_behaelter = False

    #: Ob die Komponente ihr `on_click` selbst auslöst. Nur der
    #: `Button` tut das - er hat ein natives Qt-Klicksignal, und ohne
    #: diese Angabe feuerte sein `on_click` zweimal.
    _klick_kommt_vom_widget = False

    on_click = Event(doc="Wird beim Klicken ausgelöst")
    on_double_click = Event(doc="Wird beim Doppelklick ausgelöst")
    on_mouse_down = Event(
        doc="Wird beim Drücken der Maustaste ausgelöst; bekommt x und y dazu"
    )
    on_mouse_move = Event(
        doc="Wird beim Bewegen der Maus über der Komponente ausgelöst; bekommt x und y dazu"
    )
    on_mouse_up = Event(
        doc="Wird beim Loslassen der Maustaste ausgelöst; bekommt x und y dazu"
    )

    left = Prop(int, 0, kategorie="Layout", doc="Position von links in Pixeln")
    top = Prop(int, 0, kategorie="Layout", doc="Position von oben in Pixeln")
    width = Prop(int, 75, kategorie="Layout", doc="Breite in Pixeln")
    height = Prop(int, 25, kategorie="Layout", doc="Höhe in Pixeln")
    enabled = Prop(
        bool, True, kategorie="Verhalten", doc="Legt fest, ob die Komponente bedienbar ist"
    )

    def __init__(self, parent: Komponente | None = None) -> None:
        # `parent=None` für eine Komponente, die im Code erzeugt wird
        # und auf keinem Formular liegt (ein Zeitgeber etwa). Das Widget
        # entsteht trotzdem - so braucht der Rest der Klasse keine
        # Sonderfälle -, es bleibt nur elternlos und ungezeigt.
        eltern_widget: QWidget | None = parent._qwidget if parent is not None else None
        # Die Komponente merkt sich, woran sie hängt. Qt weiß es zwar
        # auch (`_qwidget.parentWidget()`), aber nicht als `pcl`-Objekt
        # - und der Designer, der Komponentenbaum und das Speichern in
        # die `.pfm` brauchen genau das: zu welcher Komponente ein
        # Kind gehört, nicht zu welchem Widget.
        self._eltern = parent
        self._font = Font(self)
        self._popup_menu: Any = None
        self._qwidget: QWidget = self._qwidget_erzeugen(eltern_widget)
        self._geometrie_anwenden()
        self._qwidget.setEnabled(self.enabled)
        if type(self).nur_im_designer:
            # `hide()` ausdrücklich: ein Kind-Widget erscheint sonst
            # von selbst, sobald das Fenster geöffnet wird - der
            # Zeitgeber stünde dann als kleine Uhr im fertigen
            # Schülerprogramm.
            self._qwidget.hide()
        else:
            # Der Filter muss am Objekt hängen bleiben: ein QObject ohne
            # Eltern und ohne Referenz wird eingesammelt, und die
            # Ereignisse kämen nie an.
            self._maus_filter = _MausFilter(self)
            self._qwidget.installEventFilter(self._maus_filter)
            if parent is not None:
                self._qwidget.show()

    @property
    def eltern(self) -> Komponente | None:
        """Die Komponente, in der diese hier liegt – das Formular oder
        ein Behälter (`Panel`, `GroupBox`). `None` bei einer Komponente,
        die im Code ohne Eltern erzeugt wurde."""
        return self._eltern

    @property
    def popup_menu(self) -> Any:
        """Das Klappmenü, das auf die rechte Maustaste erscheint, oder
        `None`.

        Zugewiesen wird eine `PopupMenu`-Komponente vom Formular:
        ``self.sg_tabelle.popup_menu = self.pm_tabelle``. Die Zuordnung
        steht hier und nicht im Menü, weil dasselbe Klappmenü an
        mehreren Komponenten hängen darf.
        """
        return self._popup_menu

    @popup_menu.setter
    def popup_menu(self, menue: Any) -> None:
        self._popup_menu = menue
        if menue is None:
            self._qwidget.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
            return
        # `CustomContextMenu` statt `ActionsContextMenu`: das Menü wird
        # bei jedem Aufklappen neu gebaut, damit eine zur Laufzeit
        # geänderte Beschriftung auch wirklich erscheint.
        self._qwidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._qwidget.customContextMenuRequested.connect(self._klappmenue_zeigen)

    def _klappmenue_zeigen(self, punkt) -> None:
        if self._popup_menu is not None:
            self._popup_menu.aufklappen(self, punkt.x(), punkt.y())

    @property
    def font(self) -> Font:
        """Schriftart der Komponente, z. B.
        ``self.m_zettel.font.size = 12``."""
        return self._font

    def _eigenes_qss_anwenden(self) -> None:
        """Setzt das komponenteneigene Stylesheet aus allen Beiträgen neu.

        Bündelt Schrift (`font`) und Hintergrundfarbe (`Label.color`,
        `Edit.color`) an einer Stelle: beide schreiben auf dasselbe
        `setStyleSheet` der Komponente und hätten sich sonst gegenseitig
        gelöscht."""
        self._qwidget.setStyleSheet(" ".join(self._qss_teile()))

    def _qss_teile(self) -> list[str]:
        """QSS-Anweisungen dieser Komponente. Unterklassen mit eigener
        Darstellung (z. B. `Label.color`) hängen ihre Anweisungen an."""
        return self._font.qss_teile()

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        """Erzeugt das zugehörige QWidget. Von konkreten Komponenten
        überschrieben (z. B. `Button` erzeugt ein `QPushButton`)."""
        raise NotImplementedError("Konkrete Komponenten erzeugen ihr eigenes QWidget")

    def _geometrie_anwenden(self) -> None:
        self._qwidget.setGeometry(self.left, self.top, self.width, self.height)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        if name in ("left", "top", "width", "height"):
            self._geometrie_anwenden()
        elif name == "enabled":
            self._qwidget.setEnabled(wert)

    def nach_vorne_bringen(self) -> None:
        """Holt die Komponente vor alle überlappenden Geschwister-
        Komponenten (Z-Ebene) - z. B. ein
        `Label`, das über einer `Shape` liegen soll."""
        self._qwidget.raise_()

    def nach_hinten_schicken(self) -> None:
        """Schickt die Komponente hinter alle überlappenden Geschwister-
        Komponenten (Z-Ebene)."""
        self._qwidget.lower()
