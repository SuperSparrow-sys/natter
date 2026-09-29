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

from PySide6.QtCore import QEvent, QObject, QPointF, Qt
from PySide6.QtWidgets import QApplication, QScrollBar, QWidget

from pcl.errors import NatterPropertyError
from pcl.font import Font
from pcl.properties import (
    ALLGEMEINE_EREIGNISSE,
    MAUS_EREIGNISSE,
    Event,
    Komponente,
    Prop,
    typ_beschreibung,
)

#: Weitergereicht, damit `from pcl.control import MAUS_EREIGNISSE`
#: dort steht, wo die Ereignisse auch deklariert sind.
__all__ = [
    "ALLGEMEINE_EREIGNISSE",
    "Control",
    "EREIGNIS_PARAMETER",
    "MAUS_EREIGNISSE",
    "tastenname",
]

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
    # Welche Taste, als deutscher Name (siehe `tastenname`).
    "on_key_press": ("taste",),
}

#: Tasten ohne Schriftzeichen und ihr Name, wie er auf einer deutschen
#: Tastatur steht. Buchstaben, Ziffern und die übrigen Zeichen
#: ergeben sich aus dem Tastendruck selbst.
_TASTENNAMEN: dict[int, str] = {
    Qt.Key.Key_Return.value: "Eingabe",
    Qt.Key.Key_Enter.value: "Eingabe",
    Qt.Key.Key_Space.value: "Leertaste",
    Qt.Key.Key_Left.value: "Links",
    Qt.Key.Key_Right.value: "Rechts",
    Qt.Key.Key_Up.value: "Oben",
    Qt.Key.Key_Down.value: "Unten",
    Qt.Key.Key_Escape.value: "Esc",
    Qt.Key.Key_Tab.value: "Tab",
    Qt.Key.Key_Backtab.value: "Tab",
    Qt.Key.Key_Backspace.value: "Rücktaste",
    Qt.Key.Key_Delete.value: "Entf",
    Qt.Key.Key_Home.value: "Pos1",
    Qt.Key.Key_End.value: "Ende",
    Qt.Key.Key_PageUp.value: "Bild auf",
    Qt.Key.Key_PageDown.value: "Bild ab",
    Qt.Key.Key_Insert.value: "Einfg",
    **{
        getattr(Qt.Key, f"Key_F{nummer}").value: f"F{nummer}"
        for nummer in range(1, 13)
    },
}


def tastenname(taste: int, text: str = "") -> str | None:
    """Der deutsche Name einer Taste, wie ihn `on_key_press` bekommt.

    Buchstaben kommen immer groß („A“, auch ohne Umschalttaste),
    Ziffern als „0“ bis „9“, auch vom Ziffernblock. Die Tasten ohne
    Schriftzeichen tragen ihren Namen von der deutschen Tastatur
    („Links“, „Eingabe“, „Leertaste“, „Entf“). Jedes andere Zeichen
    kommt als das Zeichen selbst („+“, „ß“, „#“), Umlaute groß.

    `None` für Tasten, die allein nichts bedeuten: Umschalt, Strg,
    Alt und ähnliche. Ein Programm, das auf „A“ wartet, soll nicht
    schon beim Drücken der Umschalttaste davor etwas bekommen.
    """
    taste = int(getattr(taste, "value", taste))
    if taste in _TASTENNAMEN:
        return _TASTENNAMEN[taste]
    if Qt.Key.Key_A.value <= taste <= Qt.Key.Key_Z.value:
        return chr(taste)
    if Qt.Key.Key_0.value <= taste <= Qt.Key.Key_9.value:
        return chr(taste)
    if len(text) == 1 and text.isprintable():
        gross = text.upper()
        # „ß“.upper() ergibt „SS“ - zwei Zeichen für eine Taste.
        return gross if len(gross) == 1 else text
    return None


def _bekommt_taste(widget: QWidget) -> bool:
    """Ob `widget` den Tastendruck als Erstes bekommt und nicht nur
    weitergereicht von einem Kind.

    Das ist das Widget mit dem Fokus. Hat im ganzen Programm keines
    den Fokus - ein Formular nur mit Beschriftungen etwa -, schickt Qt
    die Taste an das Fenster selbst.
    """
    if widget.hasFocus():
        return True
    return widget.isWindow() and QApplication.focusWidget() is None


def _kennung(ereignis: QEvent) -> tuple[Any, ...]:
    """Was ein Ereignis auf seinem Weg durch die Eltern-Widgets
    wiedererkennbar macht.

    Qt reicht ein Maus-Ereignis, das ein Widget nicht annimmt, als
    neues Objekt an die Eltern weiter; Art, Zeitstempel und Stelle auf
    dem Bildschirm bleiben dabei gleich.
    """
    art = ereignis.type()
    if art == QEvent.Type.KeyPress:
        return (art, ereignis.timestamp(), ereignis.key(), ereignis.text())
    stelle = ereignis.globalPosition()
    return (art, ereignis.timestamp(), stelle.x(), stelle.y(), ereignis.button())


class _MausFilter(QObject):
    """Reicht die Mausereignisse des Widgets an seine Komponente weiter.

    Ein Ereignisfilter statt einer QWidget-Unterklasse je Komponente:
    sonst bräuchte jede der zwanzig Komponenten eine eigene Klasse, nur
    um `mousePressEvent` zu überschreiben - und die, die ihr Widget von
    Qt fertig bekommen (`QPushButton`, `QComboBox`), könnten es gar
    nicht.

    Gibt immer `False` zurück: das Ereignis läuft danach ganz normal
    weiter. Ohne das könnte man in ein `Edit` nicht mehr hineinklicken.

    Tastendrücke laufen durch denselben Filter. Gemeldet wird nur,
    was das Widget mit dem Fokus bekommt: eine Taste, die ein Kind
    nicht haben will, reicht Qt an die Eltern weiter, und ohne diese
    Prüfung meldete ein `Panel` die Tasten des Knopfs, der darin
    liegt.

    Derselbe Filter hängt auch an den inneren Widgets einer
    Komponente (`Control._filter_anhaengen`). Bei einer `ListBox`
    kommt die Maus am inneren Anzeigebereich an, bei einem `SpinEdit`
    am Eingabefeld darin, bei einer `RadioGroup` an der Option. Nimmt
    das innere Widget ein Ereignis nicht an, reicht Qt es an das
    äußere weiter; `_schon_gemeldet` sorgt dafür, dass es dann nicht
    ein zweites Mal gemeldet wird.
    """

    def __init__(self, control: Control) -> None:
        super().__init__()
        self._control = control
        self._gedrueckt = False
        self._zuletzt: tuple[tuple[Any, ...], QObject] | None = None

    def _schon_gemeldet(self, objekt: QObject, ereignis: QEvent) -> bool:
        """Ob dasselbe Ereignis eben an einem inneren Widget derselben
        Komponente gemeldet wurde und jetzt nur weitergereicht ist."""
        kennung = _kennung(ereignis)
        vorher = self._zuletzt
        self._zuletzt = (kennung, objekt)
        if vorher is None or vorher[0] != kennung:
            return False
        # Dasselbe Widget zweimal hintereinander ist ein zweiter
        # Tastendruck, nicht ein weitergereichter erster: zweimal
        # „Unten“ muss die Figur zweimal bewegen. `isAncestorOf`
        # zählt ein Widget als seinen eigenen Vorfahren.
        if vorher[1] is objekt:
            return False
        try:
            return isinstance(objekt, QWidget) and objekt.isAncestorOf(vorher[1])
        except RuntimeError:
            # Das innere Widget ist inzwischen gelöscht.
            return False

    def _stelle(self, objekt: QObject, ereignis: QEvent) -> QPointF:
        """Die Stelle des Zeigers, gezählt ab der linken oberen Ecke
        der Komponente, auch wenn ein inneres Widget das Ereignis
        bekommen hat."""
        stelle = ereignis.position()
        aussen = self._control._qwidget
        if objekt is aussen or not isinstance(objekt, QWidget):
            return stelle
        try:
            return QPointF(objekt.mapTo(aussen, stelle.toPoint()))
        except RuntimeError:
            return stelle

    def eventFilter(self, objekt: QObject, ereignis: QEvent) -> bool:  # noqa: N802
        art = ereignis.type()
        if art in _MAUS_ARTEN:
            if self._schon_gemeldet(objekt, ereignis):
                return False
            stelle = self._stelle(objekt, ereignis)
            if art == QEvent.Type.MouseButtonPress:
                self._gedrueckt = ereignis.button() == Qt.MouseButton.LeftButton
                self._control._maus_melden("on_mouse_down", stelle)
            elif art == QEvent.Type.MouseMove:
                self._control._maus_melden("on_mouse_move", stelle)
            elif art == QEvent.Type.MouseButtonRelease:
                self._control._maus_melden("on_mouse_up", stelle)
                # `on_click` erst beim Loslassen, nur für die linke
                # Taste und nur, wenn auf der Komponente gedrückt und
                # auf ihr losgelassen wurde - wer danebenzieht, hat es
                # sich anders überlegt. Genauso verhält sich ein echter
                # Knopf. Qt schickt das Loslassen immer an das Widget,
                # auf dem gedrückt wurde, deshalb die Prüfung der
                # Stelle. Die rechte Taste gehört dem Klappmenü.
                if (
                    self._gedrueckt
                    and ereignis.button() == Qt.MouseButton.LeftButton
                    and self._control._qwidget.rect().contains(stelle.toPoint())
                    and not self._control._klick_kommt_vom_widget
                ):
                    self._control._ereignis_ausloesen("on_click")
                self._gedrueckt = False
            elif ereignis.button() == Qt.MouseButton.LeftButton:
                self._control._ereignis_ausloesen("on_double_click")
        elif art == QEvent.Type.KeyPress and _bekommt_taste(objekt):
            if self._schon_gemeldet(objekt, ereignis):
                return False
            name = tastenname(ereignis.key(), ereignis.text())
            if name is not None:
                self._control._taste_melden(name)
            if name == "Eingabe":
                self._control._eingabetaste()
        return False


_MAUS_ARTEN = (
    QEvent.Type.MouseButtonPress,
    QEvent.Type.MouseMove,
    QEvent.Type.MouseButtonRelease,
    QEvent.Type.MouseButtonDblClick,
)


class Anchors:
    """Die Ränder, an denen eine Komponente hängt, z. B.
    ``self.m_text.anchors.right = True``.

    Wird das Fenster (oder der Behälter, in dem die Komponente liegt)
    größer oder kleiner, behält die Komponente ihren Abstand zu jedem
    Rand, an dem sie hängt. Hängt sie an links und rechts, wächst sie
    in der Breite mit; nur an rechts, rückt sie mit dem rechten Rand
    mit. Oben und unten ebenso. Vorgabe ist links und oben: die
    Komponente bleibt, wo sie ist.

    Wie `font` kein eigenständiges `Prop`, sondern eine Untereigenschaft
    an einem festen Attributnamen; im Objektinspektor und in der `.pfm`
    stehen die vier Häkchen flach als `anchors_left`, `anchors_top`,
    `anchors_right` und `anchors_bottom`.
    """

    def __init__(self, besitzer: Control) -> None:
        self._besitzer = besitzer
        self._werte = {"left": True, "top": True, "right": False, "bottom": False}

    def _lesen(self, seite: str) -> bool:
        return self._werte[seite]

    def _setzen(self, seite: str, wert: bool) -> None:
        if not isinstance(wert, bool):
            raise NatterPropertyError(
                f"{type(self._besitzer).__name__}.anchors.{seite} erwartet "
                f"{typ_beschreibung(bool, akkusativ=True)}, "
                f"erhalten wurde {typ_beschreibung(type(wert))}."
            )
        self._werte[seite] = wert
        self._besitzer._anker_geaendert()

    @property
    def left(self) -> bool:
        return self._lesen("left")

    @left.setter
    def left(self, wert: bool) -> None:
        self._setzen("left", wert)

    @property
    def top(self) -> bool:
        return self._lesen("top")

    @top.setter
    def top(self, wert: bool) -> None:
        self._setzen("top", wert)

    @property
    def right(self) -> bool:
        return self._lesen("right")

    @right.setter
    def right(self, wert: bool) -> None:
        self._setzen("right", wert)

    @property
    def bottom(self) -> bool:
        return self._lesen("bottom")

    @bottom.setter
    def bottom(self, wert: bool) -> None:
        self._setzen("bottom", wert)

    def ist_vorgabe(self) -> bool:
        """Ob nur links und oben gesetzt sind - dann folgt die
        Komponente keiner Größenänderung."""
        return self._werte == {"left": True, "top": True, "right": False, "bottom": False}


class _AnkerFilter(QObject):
    """Meldet der Komponente, wenn sich die Fläche, auf der sie liegt,
    in der Größe ändert."""

    def __init__(self, control: Control) -> None:
        super().__init__()
        self._control = control

    def eventFilter(self, objekt: QObject, ereignis: QEvent) -> bool:  # noqa: N802
        if ereignis.type() == QEvent.Type.Resize:
            anwenden = getattr(self._control, "_anker_anwenden", None)
            if anwenden is not None and "_anchors" in self._control.__dict__:
                anwenden()
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

    #: Ob die Eingabetaste hier den Standardknopf des Formulars
    #: auslöst (`Button.default`). Nicht in einem `Memo`, dort beginnt
    #: sie eine neue Zeile, und nicht in einem `StringGrid`, dort
    #: schließt sie die Bearbeitung einer Zelle ab.
    _eingabe_loest_standardknopf_aus = True

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
    on_key_press = Event(
        doc="Wird bei einem Tastendruck ausgelöst, solange die Komponente "
        "den Fokus hat; bekommt den Namen der Taste dazu"
    )

    left = Prop(int, 0, kategorie="Layout", doc="Position von links in Pixeln")
    top = Prop(int, 0, kategorie="Layout", doc="Position von oben in Pixeln")
    width = Prop(int, 75, kategorie="Layout", doc="Breite in Pixeln")
    height = Prop(int, 25, kategorie="Layout", doc="Höhe in Pixeln")
    enabled = Prop(
        bool, True, kategorie="Verhalten", doc="Legt fest, ob die Komponente bedienbar ist"
    )
    visible = Prop(
        bool,
        True,
        kategorie="Verhalten",
        doc="Legt fest, ob die Komponente im laufenden Programm zu sehen ist",
    )
    hint = Prop(
        str,
        "",
        kategorie="Verhalten",
        doc="Hinweistext, der erscheint, wenn die Maus eine Weile auf der "
        "Komponente ruht; leer = keiner",
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
        self._anchors = Anchors(self)
        #: Abstand zum rechten und unteren Rand der Fläche, auf der die
        #: Komponente liegt - das, was `anchors` beim Vergrößern hält.
        self._anker_abstand = (0, 0)
        self._anker_filter: _AnkerFilter | None = None
        self._anker_laeuft = False
        self._popup_menu: Any = None
        self._klappmenue_verbunden = False
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
            self._filter_anhaengen(self._qwidget)
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
        if menue is not None and not callable(getattr(menue, "aufklappen", None)):
            raise NatterPropertyError(
                f"{type(self).__name__}.popup_menu erwartet ein PopupMenu, "
                f"erhalten wurde {typ_beschreibung(type(menue))}."
            )
        self._popup_menu = menue
        if menue is None:
            self._qwidget.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)
            return
        # `CustomContextMenu` statt `ActionsContextMenu`: das Menü wird
        # bei jedem Aufklappen neu gebaut, damit eine zur Laufzeit
        # geänderte Beschriftung auch wirklich erscheint.
        self._qwidget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        # Nur einmal verbinden. Qt hängt bei jedem `connect` eine
        # weitere Verbindung an, und nach der zweiten Zuweisung klappte
        # das Menü zweimal hintereinander auf.
        if not self._klappmenue_verbunden:
            self._qwidget.customContextMenuRequested.connect(self._klappmenue_zeigen)
            self._klappmenue_verbunden = True

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

    def _filter_anhaengen(self, widget: QWidget) -> None:
        """Hängt den Ereignisfilter an `widget` und an die Widgets
        darin, die zur Komponente selbst gehören.

        Bei Listen, Textfeldern und Tabellen kommt die Maus nicht am
        äußeren Widget an, sondern am Anzeigebereich darin
        (`viewport()`), bei Spinboxen und Datumsfeldern am
        Eingabefeld, beim Kalender an der Monatstabelle. Diese
        Widgets nehmen den Klick selbst an; ein Filter nur am äußeren
        Widget hörte ihn nie.

        Aufgerufen wird das, bevor Komponenten in diese hier gelegt
        werden; ein `Panel` bekommt so nicht die Filter der Knöpfe
        darin. Ausgelassen sind Bildlaufleisten und alles, was in
        einem eigenen Fenster aufklappt, etwa die Liste einer
        `ComboBox`: ein Zug am Rollbalken ist kein Klick auf die Liste.
        """
        fenster = widget.window()
        for inneres in [widget, *widget.findChildren(QWidget)]:
            if inneres is not widget and (
                inneres.window() is not fenster
                or isinstance(inneres, QScrollBar)
                or isinstance(inneres.parent(), QScrollBar)
            ):
                continue
            inneres.installEventFilter(self._maus_filter)

    @property
    def anchors(self) -> Anchors:
        """Die Ränder, an denen die Komponente hängt, z. B.
        ``self.m_text.anchors.right = True``."""
        return self._anchors

    def _versatz_oben(self) -> int:
        """Wie weit der Arbeitsbereich der Fläche unter ihrer Oberkante
        beginnt: bei einem Formular mit Menüleiste deren Höhe, sonst 0.
        `top = 0` meint den oberen Rand unter der Leiste."""
        hoehe = getattr(self._eltern, "_leistenhoehe", None)
        return hoehe() if hoehe is not None else 0

    def _flaeche(self) -> tuple[int, int] | None:
        """Breite und Höhe des Arbeitsbereichs, auf dem die Komponente
        liegt; `None` ohne Eltern."""
        if self._eltern is None:
            return None
        widget = self._eltern._qwidget
        return widget.width(), widget.height() - self._versatz_oben()

    def _geometrie_anwenden(self) -> None:
        self._qwidget.setGeometry(
            self.left, self.top + self._versatz_oben(), self.width, self.height
        )
        if not self._anker_laeuft:
            self._anker_abstand_merken()

    def _anker_abstand_merken(self) -> None:
        flaeche = self._flaeche()
        if flaeche is None:
            return
        breite, hoehe = flaeche
        self._anker_abstand = (
            breite - self.left - self.width,
            hoehe - self.top - self.height,
        )

    def _anker_geaendert(self) -> None:
        """Nach einer Änderung an `anchors`: den Abstand zu den Rändern
        merken und die Fläche beobachten, falls noch nicht geschehen."""
        self._anker_abstand_merken()
        # Ein Zeitgeber oder Menü ist im Programm nicht zu sehen und
        # hat nichts, das mitwachsen könnte.
        if type(self).nur_im_designer:
            return
        if self._anker_filter is None and self._eltern is not None:
            if not self._anchors.ist_vorgabe():
                self._anker_filter = _AnkerFilter(self)
                self._eltern._qwidget.installEventFilter(self._anker_filter)

    def _anker_anwenden(self) -> None:
        """Rückt oder dehnt die Komponente nach einer Größenänderung
        der Fläche so, dass die Abstände zu den angehängten Rändern
        bleiben.

        Im Designer nicht: dort bleibt jede Komponente, wo sie
        abgelegt wurde, auch wenn das Formular größer gezogen wird.
        """
        # `Control._formular` ausdrücklich: die Menüs führen unter
        # diesem Namen das Formular selbst als Attribut.
        if getattr(Control._formular(self), "_entwurfsansicht", False):
            return
        flaeche = self._flaeche()
        if flaeche is None or self._anchors.ist_vorgabe():
            return
        breite, hoehe = flaeche
        rechts, unten = self._anker_abstand
        anker = self._anchors
        self._anker_laeuft = True
        try:
            if anker.right:
                if anker.left:
                    self.width = max(0, breite - self.left - rechts)
                else:
                    self.left = breite - self.width - rechts
            if anker.bottom:
                if anker.top:
                    self.height = max(0, hoehe - self.top - unten)
                else:
                    self.top = hoehe - self.height - unten
        finally:
            self._anker_laeuft = False

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        if name in ("left", "top", "width", "height"):
            self._geometrie_anwenden()
        elif name == "enabled":
            self._qwidget.setEnabled(wert)
        elif name == "visible":
            self._sichtbarkeit_anwenden()
        elif name == "hint":
            self._qwidget.setToolTip(wert)

    def _formular(self) -> Komponente | None:
        """Das Formular, auf dem die Komponente liegt, über die
        Elternkette - auch durch Behälter hindurch."""
        objekt: Any = self._eltern
        while isinstance(objekt, Control):
            objekt = objekt._eltern
        return objekt

    def _sichtbarkeit_anwenden(self) -> None:
        """Blendet das Widget ein oder aus.

        Drei Fälle bleiben unberührt: eine Komponente, die nur im
        Designer zu sehen ist (ein Zeitgeber hat nichts zu zeigen),
        eine Komponente ohne Eltern (`show()` machte aus ihr ein
        eigenes Fenster) und der Designer selbst. Dort muss eine
        ausgeblendete Komponente anklickbar bleiben, sonst ließe sie
        sich nie wieder einblenden.
        """
        if type(self).nur_im_designer or self._eltern is None:
            return
        if getattr(self._formular(), "_entwurfsansicht", False):
            return
        self._qwidget.setVisible(self.visible)

    def _taste_melden(self, name: str) -> None:
        """Meldet einen Tastendruck erst dem Formular, dann der
        Komponente.

        Das Formular hört jede Taste in seinem Fenster, gleich welche
        Komponente gerade den Fokus hat. Ein Spiel mit Pfeiltasten
        braucht das: sonst käme „Links“ nur an, solange niemand in ein
        Eingabefeld geklickt hat.
        """
        formular = self._formular()
        if formular is not None:
            formular._ereignis_ausloesen("on_key_press", name)
        self._ereignis_ausloesen("on_key_press", name)

    def _eingabetaste(self) -> None:
        """Die Eingabetaste, während die Komponente den Fokus hat:
        der Standardknopf des Formulars, falls es einen gibt."""
        if not type(self)._eingabe_loest_standardknopf_aus:
            return
        formular = self._formular()
        druecken = getattr(formular, "_standardknopf_druecken", None)
        if druecken is not None:
            druecken()

    def set_focus(self) -> None:
        """Setzt den Fokus auf die Komponente: in ein `Edit` etwa den
        Cursor, sodass sofort getippt werden kann.

        Gebraucht wird das nach einem Knopfdruck, der das Eingabefeld
        geleert hat, etwa „Neu raten“: ohne diesen Aufruf müsste erst
        wieder hineingeklickt werden.
        """
        self._qwidget.setFocus(Qt.FocusReason.OtherFocusReason)

    def nach_vorne_bringen(self) -> None:
        """Holt die Komponente vor alle überlappenden Geschwister-
        Komponenten (Z-Ebene) - z. B. ein
        `Label`, das über einer `Shape` liegen soll."""
        self._qwidget.raise_()

    def nach_hinten_schicken(self) -> None:
        """Schickt die Komponente hinter alle überlappenden Geschwister-
        Komponenten (Z-Ebene)."""
        self._qwidget.lower()
