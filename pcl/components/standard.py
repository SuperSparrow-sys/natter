"""Standard-Komponenten: Button, Label, Edit, CheckBox, RadioButton, Memo,
ListBox, ComboBox, ScrollBar, GroupBox, Panel, RadioGroup.

Siehe README.md, Abschnitt 5.2 (Palette „Standard“).

`GroupBox` und `Panel` sind Behälter: `Control.__init__` hängt jede
Komponente an das `_qwidget` ihres `parent`, ``Button(self.p_feld)``
funktioniert also ohne weiteres Zutun. Im Designer lässt sich das noch
nicht ablegen (dort wird jede Komponente ein Kind des Formulars) - was
dafür fehlt, steht in `docs/komponenten.md` unter „Offene Punkte“.
`RadioGroup` braucht das nicht: sie erzeugt ihre Optionsfelder wie
`TRadioGroup` selbst aus `items`.

`MainMenu` und `PopupMenu` fehlen weiterhin; sie brauchen einen eigenen
Menü-Editor im Designer.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QScrollBar,
    QVBoxLayout,
    QWidget,
)

from pcl.control import Control
from pcl.properties import Event, Prop
from pcl.strings import Strings

#: Innenabstand (links, oben, rechts, unten) der Optionsliste einer
#: `RadioGroup`. Oben mehr, weil dort die Beschriftung der QGroupBox
#: sitzt.
_RADIOGROUP_RAENDER = (10, 8, 8, 6)
#: Abstand zwischen zwei Optionsfeldern einer `RadioGroup` in Pixeln.
_RADIOGROUP_ABSTAND = 2

#: Objektname des `QFrame` hinter einem `Panel`, damit `Panel.color` als
#: `QFrame#...`-Regel genau dieses Widget trifft (siehe `Panel._qss_teile`).
_PANEL_OBJEKTNAME = "pcl_panel"


class Button(Control):
    """Schaltfläche für Klick-Ereignisse. Qt-Basis: `QPushButton`."""

    caption = Prop(str, "Button", kategorie="Darstellung", doc="Beschriftung des Buttons")
    on_click = Event(doc="Wird beim Klicken ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QPushButton(eltern_widget)
        widget.setText(self.caption)
        widget.clicked.connect(self._bei_klick)
        return widget

    def _bei_klick(self) -> None:
        if self.on_click is not None:
            self.on_click(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "caption":
            self._qwidget.setText(wert)


class _KlickbaresLabel(QLabel):
    """`QLabel`, das Mausklicks an das besitzende `Label` weiterreicht
    (Abschnitt 5.1: `on_click` – z. B. für Cookie-Klicker-artige
    Übungen, in denen ein Label statt eines Buttons angeklickt wird)."""

    def __init__(self, eltern_widget: QWidget, label: Label) -> None:
        super().__init__(eltern_widget)
        self._label = label

    def mousePressEvent(self, event: Any) -> None:
        super().mousePressEvent(event)
        self._label._bei_klick()


class Label(Control):
    """Textanzeige, per `on_click` auch anklickbar. Qt-Basis: `QLabel`.

    `color`/`transparent` wie Lazarus' `TLabel` (Nutzer-Feedback
    September 2026): ein Label kann eine eigene Hintergrundfarbe zeigen
    - nützlich, um es sichtbar über einer `Shape` zu platzieren."""

    caption = Prop(str, "Label1", kategorie="Darstellung", doc="Anzeigetext")
    color = Prop(
        str,
        "",
        kategorie="Darstellung",
        doc="Hintergrundfarbe als #RRGGBB (nur bei transparent=False)",
    )
    transparent = Prop(
        bool, True, kategorie="Darstellung", doc="Wenn wahr (Standard), kein eigener Hintergrund"
    )
    on_click = Event(doc="Wird beim Klicken ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = _KlickbaresLabel(eltern_widget, self)
        widget.setText(self.caption)
        return widget

    def _bei_klick(self) -> None:
        if self.on_click is not None:
            self.on_click(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "caption":
            self._qwidget.setText(wert)
        elif name in ("color", "transparent"):
            self._eigenes_qss_anwenden()

    def _qss_teile(self) -> list[str]:
        teile = super()._qss_teile()
        if not self.transparent and self.color:
            teile.append(f"background-color: {self.color};")
        return teile


class Edit(Control):
    """Einzeiliges Eingabefeld. Qt-Basis: `QLineEdit`."""

    text = Prop(str, "", kategorie="Darstellung", doc="Eingegebener bzw. angezeigter Text")
    read_only = Prop(bool, False, kategorie="Verhalten", doc="Wenn wahr, nicht bearbeitbar")
    color = Prop(
        str, "", kategorie="Darstellung", doc="Hintergrundfarbe als #RRGGBB, leer = Theme-Standard"
    )
    on_change = Event(doc="Wird bei jeder Änderung des Textes ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QLineEdit(eltern_widget)
        widget.setText(self.text)
        widget.setReadOnly(self.read_only)
        widget.textChanged.connect(self._bei_textaenderung)
        return widget

    def _bei_textaenderung(self, neuer_text: str) -> None:
        # QLineEdit.setText ändert die Anzeige nicht erneut, wenn der Text
        # bereits übereinstimmt, daher keine Endlosschleife über Prop.__set__.
        self.text = neuer_text
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "text":
            self._qwidget.setText(wert)
        elif name == "read_only":
            self._qwidget.setReadOnly(wert)
        elif name == "color":
            self._eigenes_qss_anwenden()

    def _qss_teile(self) -> list[str]:
        teile = super()._qss_teile()
        if self.color:
            teile.append(f"background-color: {self.color};")
        return teile


class CheckBox(Control):
    """Kontrollkästchen. Qt-Basis: `QCheckBox`."""

    caption = Prop(str, "CheckBox1", kategorie="Darstellung", doc="Beschriftung")
    checked = Prop(
        bool, False, kategorie="Verhalten", doc="Legt fest, ob das Kästchen angehakt ist"
    )
    on_change = Event(doc="Wird beim Umschalten ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QCheckBox(eltern_widget)
        widget.setText(self.caption)
        widget.setChecked(self.checked)
        widget.toggled.connect(self._bei_umschalten)
        return widget

    def _bei_umschalten(self, wert: bool) -> None:
        self.checked = wert
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "caption":
            self._qwidget.setText(wert)
        elif name == "checked":
            self._qwidget.setChecked(wert)


class Memo(Control):
    """Mehrzeiliges Textfeld. Qt-Basis: `QPlainTextEdit`.

    `lines` ist eine aufklappbare `Strings`-Untereigenschaft (Abschnitt
    5.0, 11.2), kein eigenständiges `Prop` – wie `Shape.brush`.
    """

    read_only = Prop(bool, False, kategorie="Verhalten", doc="Wenn wahr, nicht bearbeitbar")

    def __init__(self, parent: Control) -> None:
        self._lines = Strings(self._lines_geaendert)
        super().__init__(parent)

    @property
    def lines(self) -> Strings:
        return self._lines

    @lines.setter
    def lines(self, werte: list[str]) -> None:
        self._lines.zuweisen(werte)

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QPlainTextEdit(eltern_widget)
        widget.setReadOnly(self.read_only)
        return widget

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "read_only":
            self._qwidget.setReadOnly(wert)

    def _lines_geaendert(self) -> None:
        self._qwidget.setPlainText("\n".join(self._lines))


class ListBox(Control):
    """Einfache Auswahlliste. Qt-Basis: `QListWidget`."""

    item_index = Prop(
        int, -1, kategorie="Verhalten", doc="Index des ausgewählten Eintrags, -1 = keine Auswahl"
    )
    on_change = Event(doc="Wird ausgelöst, wenn ein anderer Eintrag ausgewählt wird")

    def __init__(self, parent: Control) -> None:
        self._items = Strings(self._items_geaendert)
        super().__init__(parent)

    @property
    def items(self) -> Strings:
        return self._items

    @items.setter
    def items(self, werte: list[str]) -> None:
        self._items.zuweisen(werte)

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QListWidget(eltern_widget)
        widget.currentRowChanged.connect(self._bei_zeilenwechsel)
        return widget

    def _items_geaendert(self) -> None:
        self._qwidget.clear()
        self._qwidget.addItems(list(self._items))

    def _bei_zeilenwechsel(self, zeile: int) -> None:
        self.item_index = zeile
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "item_index":
            self._qwidget.setCurrentRow(wert)


class ComboBox(Control):
    """Dropdown-Auswahl. Qt-Basis: `QComboBox`."""

    item_index = Prop(
        int, -1, kategorie="Verhalten", doc="Index des ausgewählten Eintrags, -1 = keine Auswahl"
    )
    text = Prop(str, "", kategorie="Darstellung", doc="Angezeigter bzw. ausgewählter Text")
    on_change = Event(doc="Wird ausgelöst, wenn ein anderer Eintrag ausgewählt wird")

    def __init__(self, parent: Control) -> None:
        self._items = Strings(self._items_geaendert)
        super().__init__(parent)

    @property
    def items(self) -> Strings:
        return self._items

    @items.setter
    def items(self, werte: list[str]) -> None:
        self._items.zuweisen(werte)

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QComboBox(eltern_widget)
        widget.currentIndexChanged.connect(self._bei_index_wechsel)
        widget.currentTextChanged.connect(self._bei_text_wechsel)
        return widget

    def _items_geaendert(self) -> None:
        self._qwidget.clear()
        self._qwidget.addItems(list(self._items))

    def _bei_index_wechsel(self, index: int) -> None:
        self.item_index = index
        if self.on_change is not None:
            self.on_change(self)

    def _bei_text_wechsel(self, text: str) -> None:
        self.text = text

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "item_index":
            self._qwidget.setCurrentIndex(wert)
        elif name == "text":
            self._qwidget.setCurrentText(wert)


class RadioButton(Control):
    """Optionsfeld, typischerweise in einer Gruppe mit anderen
    `RadioButton`-Komponenten. Qt-Basis: `QRadioButton`."""

    caption = Prop(str, "RadioButton1", kategorie="Darstellung", doc="Beschriftung")
    checked = Prop(
        bool, False, kategorie="Verhalten", doc="Legt fest, ob die Option ausgewählt ist"
    )
    on_change = Event(doc="Wird beim Umschalten ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QRadioButton(eltern_widget)
        widget.setText(self.caption)
        widget.setChecked(self.checked)
        widget.toggled.connect(self._bei_umschalten)
        return widget

    def _bei_umschalten(self, wert: bool) -> None:
        self.checked = wert
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "caption":
            self._qwidget.setText(wert)
        elif name == "checked":
            self._qwidget.setChecked(wert)


class ScrollBar(Control):
    """Bildlaufleiste, im Unterricht oft zur Eingabe eines Zahlenwerts
    genutzt. Qt-Basis: `QScrollBar` (horizontal)."""

    minimum = Prop(int, 0, kategorie="Verhalten", doc="Kleinster möglicher Wert")
    maximum = Prop(int, 100, kategorie="Verhalten", doc="Größter möglicher Wert")
    position = Prop(int, 0, kategorie="Verhalten", doc="Aktueller Wert")
    on_change = Event(doc="Wird bei Änderung der Position ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QScrollBar(Qt.Orientation.Horizontal, eltern_widget)
        widget.setMinimum(self.minimum)
        widget.setMaximum(self.maximum)
        widget.setValue(self.position)
        widget.valueChanged.connect(self._bei_wertaenderung)
        return widget

    def _bei_wertaenderung(self, wert: int) -> None:
        self.position = wert
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "minimum":
            self._qwidget.setMinimum(wert)
        elif name == "maximum":
            self._qwidget.setMaximum(wert)
        elif name == "position":
            self._qwidget.setValue(wert)


class GroupBox(Control):
    """Beschrifteter Rahmen, der andere Komponenten zusammenfasst.
    Qt-Basis: `QGroupBox`. Entspricht `TGroupBox` in Lazarus.

    Als Behälter braucht sie keinen eigenen Code: `Control.__init__`
    hängt jede Komponente an das `_qwidget` ihres `parent`, also genügt
    ``RadioButton(self.g_zahlung)``. `left`/`top` der Kind-Komponente
    zählen dann ab der linken oberen Ecke der GroupBox, und
    ``self.g_zahlung.enabled = False`` sperrt den ganzen Inhalt auf
    einmal (das erledigt Qt).

    Im Designer geht diese Verschachtelung noch nicht - siehe
    `docs/komponenten.md`, „Offene Punkte“.
    """

    # Standardgröße als Prop-Standard (wie bei `Chart`): in 75x25 hätte
    # der Rahmen nicht einmal für die eigene Beschriftung Platz.
    width = Prop(int, 185, kategorie="Layout", doc="Breite in Pixeln")
    height = Prop(int, 105, kategorie="Layout", doc="Höhe in Pixeln")

    caption = Prop(str, "GroupBox1", kategorie="Darstellung", doc="Beschriftung über dem Rahmen")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QGroupBox(eltern_widget)
        widget.setTitle(self.caption)
        return widget

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "caption":
            self._qwidget.setTitle(wert)


class _PanelQWidget(QFrame):
    """`QFrame`, der seine Beschriftung selbst mittig zeichnet.

    Ein Kind-`QLabel` wäre der kürzere Weg, läge aber über den
    Komponenten, die später auf dem Panel entstehen, und finge deren
    Mausklicks ab. Gezeichnet wird mit der Schrift und der Textfarbe des
    Widgets, damit `font`-Eigenschaft und Theme (hell/dunkel) wirken.
    """

    def __init__(self, eltern_widget: QWidget, panel: Panel) -> None:
        super().__init__(eltern_widget)
        self._panel = panel
        # Fester Objektname, damit `Panel.color` als `QFrame#...`-Regel
        # genau dieses Widget treffen kann und nicht jede Komponente
        # darauf, die zufällig auch ein QFrame ist (QLabel, QTableWidget
        # und QPlainTextEdit sind welche).
        self.setObjectName(_PANEL_OBJEKTNAME)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setFrameShadow(QFrame.Shadow.Raised)

    def paintEvent(self, event: Any) -> None:  # noqa: N802 (Qt-Konvention)
        super().paintEvent(event)
        if not self._panel.caption:
            return
        maler = QPainter(self)
        maler.setPen(self.palette().color(QPalette.ColorRole.WindowText))
        maler.setFont(self.font())
        maler.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._panel.caption)


class Panel(Control):
    """Fläche, die andere Komponenten zusammenfasst. Qt-Basis: `QFrame`
    mit selbst gezeichneter Beschriftung. Entspricht `TPanel` in Lazarus.

    Behälter wie `GroupBox` - siehe dort.
    """

    # Standardgröße als Prop-Standard (wie bei `Chart`).
    width = Prop(int, 185, kategorie="Layout", doc="Breite in Pixeln")
    height = Prop(int, 105, kategorie="Layout", doc="Höhe in Pixeln")

    caption = Prop(str, "Panel1", kategorie="Darstellung", doc="Beschriftung mittig auf der Fläche")
    color = Prop(
        str, "", kategorie="Darstellung", doc="Hintergrundfarbe als #RRGGBB, leer = Theme-Standard"
    )

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        return _PanelQWidget(eltern_widget, self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "caption":
            self._qwidget.update()
        elif name == "color":
            self._eigenes_qss_anwenden()

    def _qss_teile(self) -> list[str]:
        teile = super()._qss_teile()
        if self.color:
            # Als eigene Regel auf genau dieses Widget, nicht als nackte
            # Anweisung: ein Stylesheet kaskadiert in Qt auf die Kinder
            # (Abschnitt 6), die Fläche soll aber nur das Panel selbst
            # bekommen und nicht die Komponenten darauf - von denen sind
            # einige (Label, StringGrid, Memo) ebenfalls ein QFrame.
            teile.append(f"QFrame#{_PANEL_OBJEKTNAME} {{ background-color: {self.color}; }}")
        return teile


class RadioGroup(Control):
    """Rahmen mit mehreren Optionsfeldern, von denen immer genau eines
    gewählt ist. Qt-Basis: `QGroupBox` mit je einem `QRadioButton` pro
    Eintrag. Entspricht `TRadioGroup` in Lazarus.

    Anders als `GroupBox`/`Panel` ist dies **kein** offener Behälter: die
    Optionsfelder entstehen aus `items`, genau wie `TRadioGroup.Items` in
    Lazarus. Deshalb ist die Komponente auch im Designer vollständig
    benutzbar, ohne dass er Verschachtelung beherrschen müsste.
    """

    # Standardgröße als Prop-Standard (wie bei `Chart`): Platz für
    # Beschriftung und drei bis vier Optionen.
    width = Prop(int, 185, kategorie="Layout", doc="Breite in Pixeln")
    height = Prop(int, 105, kategorie="Layout", doc="Höhe in Pixeln")

    caption = Prop(str, "RadioGroup1", kategorie="Darstellung", doc="Beschriftung über dem Rahmen")
    item_index = Prop(
        int, -1, kategorie="Verhalten", doc="Index der gewählten Option, -1 = keine Auswahl"
    )
    on_change = Event(doc="Wird beim Wechsel der Auswahl ausgelöst")

    def __init__(self, parent: Control) -> None:
        self._items = Strings(self._items_geaendert)
        self._optionen: list[QRadioButton] = []
        # Während `_optionen_neu_aufbauen()` löst jedes erzeugte und jedes
        # gelöschte Optionsfeld ein `toggled` aus. Ohne diese Sperre
        # überschriebe das den gerade gesetzten `item_index`.
        self._baut_auf = False
        super().__init__(parent)

    @property
    def items(self) -> Strings:
        return self._items

    @items.setter
    def items(self, werte: list[str]) -> None:
        self._items.zuweisen(werte)

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QGroupBox(eltern_widget)
        widget.setTitle(self.caption)
        anordnung = QVBoxLayout(widget)
        anordnung.setContentsMargins(*_RADIOGROUP_RAENDER)
        anordnung.setSpacing(_RADIOGROUP_ABSTAND)
        anordnung.addStretch(1)
        return widget

    def _items_geaendert(self) -> None:
        self._optionen_neu_aufbauen()

    def _optionen_neu_aufbauen(self) -> None:
        self._baut_auf = True
        try:
            for option in self._optionen:
                option.setParent(None)
                option.deleteLater()
            self._optionen = []
            anordnung = self._qwidget.layout()
            for nummer, text in enumerate(self._items):
                option = QRadioButton(text, self._qwidget)
                option.toggled.connect(
                    lambda gewaehlt, index=nummer: self._bei_umschalten(gewaehlt, index)
                )
                # Vor den Dehnungsplatz am Ende, damit die Optionen oben
                # stehen und nicht über die Höhe verteilt werden.
                anordnung.insertWidget(anordnung.count() - 1, option)
                option.show()
                self._optionen.append(option)
            # Ein Index, der auf einen weggefallenen Eintrag zeigte, wäre
            # sonst eine Auswahl, die es nicht mehr gibt.
            if not 0 <= self.item_index < len(self._optionen):
                self.__dict__["_prop_item_index"] = -1
            else:
                self._optionen[self.item_index].setChecked(True)
        finally:
            self._baut_auf = False

    def _bei_umschalten(self, gewaehlt: bool, index: int) -> None:
        if self._baut_auf or not gewaehlt:
            return
        self.item_index = index
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "caption":
            self._qwidget.setTitle(wert)
        elif name == "item_index":
            self._auswahl_anwenden(wert)

    def _auswahl_anwenden(self, index: int) -> None:
        self._baut_auf = True
        try:
            for nummer, option in enumerate(self._optionen):
                soll = nummer == index
                if option.isChecked() == soll:
                    continue
                # `setChecked(False)` prallt an einem Optionsfeld ab, das
                # in einer Gruppe steht: Qt lässt genau die Schaltfläche,
                # die gerade gewählt ist, nicht abwählen, weil in einer
                # Gruppe immer eine gewählt sein soll. Ohne dieses
                # kurzzeitige Aufheben blieb `item_index = -1` ohne
                # Wirkung - die alte Auswahl stand weiter da.
                option.setAutoExclusive(False)
                option.setChecked(soll)
                option.setAutoExclusive(True)
        finally:
            self._baut_auf = False
        if index != -1 and not 0 <= index < len(self._optionen):
            # Ein Index ohne Option wäre eine Auswahl, die niemand sieht:
            # `item_index` stünde auf 2, angehakt wäre nichts. Dieselbe
            # Regel wie beim Wegfallen eines Eintrags - zurück auf -1.
            self.__dict__["_prop_item_index"] = -1
