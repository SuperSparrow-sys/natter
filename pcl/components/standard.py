"""Standard-Komponenten: Button, Label, Edit, CheckBox, RadioButton, Memo,
ListBox, ComboBox, ScrollBar, GroupBox, Panel, RadioGroup.

Siehe README.md, Abschnitt 5.2 (Palette „Standard“).

`GroupBox` und `Panel` sind Behälter: `Control.__init__` hängt jede
Komponente an das `_qwidget` ihres `parent`, ``Button(self.p_feld)``
funktioniert also ohne weiteres Zutun, im Designer ebenso.
`RadioGroup` braucht das nicht: sie erzeugt ihre Optionsfelder selbst
aus `items`.

`MainMenu` und `PopupMenu` stehen in `pcl/components/menus.py`.
"""

from __future__ import annotations

import builtins
from typing import Any

from PySide6.QtCore import QRegularExpression, Qt
from PySide6.QtGui import QPainter, QPalette, QRegularExpressionValidator
from PySide6.QtWidgets import (
    QAbstractItemView,
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
from pcl.errors import NatterPropertyError, NatterZellenError
from pcl.properties import ART_FARBE, Event, Prop, typ_beschreibung
from pcl.strings import Strings

#: Innenabstand (links, oben, rechts, unten) der Optionsliste einer
#: `RadioGroup`. Oben mehr, weil dort die Beschriftung der QGroupBox
#: sitzt.
_RADIOGROUP_RAENDER = (10, 8, 8, 6)
#: Abstand zwischen zwei Optionsfeldern einer `RadioGroup` in Pixeln.
_RADIOGROUP_ABSTAND = 2

#: Die Werte von `alignment` und die waagerechte Qt-Ausrichtung dazu.
#: Senkrecht steht der Text immer in der Mitte.
AUSRICHTUNGEN = ("left", "center", "right")
_QT_AUSRICHTUNG = {
    "left": Qt.AlignmentFlag.AlignLeft,
    "center": Qt.AlignmentFlag.AlignHCenter,
    "right": Qt.AlignmentFlag.AlignRight,
}


def _ausrichtung(wert: str) -> Qt.AlignmentFlag:
    return _QT_AUSRICHTUNG[wert] | Qt.AlignmentFlag.AlignVCenter


def _ausrichtung_prop(standard: str) -> Prop:
    return Prop(
        str,
        standard,
        kategorie="Darstellung",
        doc="Ausrichtung des Textes: left (links), center (mittig) oder right (rechts)",
        werte=AUSRICHTUNGEN,
    )


def _zeilen_der_texte(eintraege: list[str], texte: list[str]) -> list[int]:
    """Die Nummern, unter denen `texte` in `eintraege` stehen. Ein
    Text, der zweimal gewählt war, findet auch zwei Zeilen."""
    zeilen: list[int] = []
    for text in texte:
        for zeile, eintrag in enumerate(eintraege):
            if eintrag == text and zeile not in zeilen:
                zeilen.append(zeile)
                break
    return zeilen


#: Was ein `Edit` mit `numbers_only` annimmt: ein Minus am Anfang,
#: Ziffern und höchstens ein Komma oder Punkt. Auch ein halb getipptes
#: „-“ oder „3,“ muss durchgehen, sonst ließe es sich nicht eintippen.
_NUR_ZAHLEN = QRegularExpression(r"-?[0-9]*([.,][0-9]*)?")

#: `QLineEdit.maxLength` ohne Grenze - der Qt-Standardwert.
_KEINE_GRENZE = 32767

#: Objektname des `QFrame` hinter einem `Panel`, damit `Panel.color` als
#: `QFrame#...`-Regel genau dieses Widget trifft (siehe `Panel._qss_teile`).
_PANEL_OBJEKTNAME = "pcl_panel"


class Button(Control):
    """Schaltfläche für Klick-Ereignisse. Qt-Basis: `QPushButton`.

    `on_click` kommt hier aus Qt selbst (`clicked`) und nicht aus dem
    Maus-Filter in `Control`: ein Knopf reagiert auch auf die
    Leertaste, und das ist ein Klick, den kein Mausereignis meldet.
    """

    caption = Prop(str, "Button", kategorie="Darstellung", doc="Beschriftung des Buttons")
    default = Prop(
        bool,
        False,
        kategorie="Verhalten",
        doc="Wenn wahr, löst die Eingabetaste diesen Knopf aus, "
        "gleich in welchem Feld sie gedrückt wird",
    )

    _klick_kommt_vom_widget = True

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QPushButton(eltern_widget)
        widget.setText(self.caption)
        widget.clicked.connect(self._bei_klick)
        return widget

    def _bei_klick(self) -> None:
        if self.on_click is not None:
            self.on_click(self)

    def _eingabetaste(self) -> None:
        """Die Eingabetaste auf einem Knopf mit Fokus klickt ihn
        selbst, nicht den Standardknopf."""
        if self._qwidget.isEnabled():
            self._qwidget.click()

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "caption":
            self._qwidget.setText(wert)
        elif name == "default":
            # Nur für den Rahmen, an dem man den Standardknopf erkennt.
            # Ausgelöst wird er über `Form._standardknopf_druecken`.
            self._qwidget.setDefault(wert)


class Label(Control):
    """Textanzeige, per `on_click` auch anklickbar. Qt-Basis: `QLabel`.

    Über `color`/`transparent` kann ein Label eine eigene
    Hintergrundfarbe zeigen - nützlich, um es sichtbar über einer
    `Shape` zu platzieren.

    `word_wrap` steht auf `True`, und das aus einem handfesten Grund:
    ein `QLabel` bricht von sich aus nicht um, und was breiter ist als
    das Label, verschwindet ohne Meldung. Im Beispielprojekt
    `09_ObstSortierer` endete die Erklärung dadurch mitten im Satz.
    Betroffen ist jeder, der einen längeren Text in ein Label schreibt
    - also genau das, was jemand tut, der sein Programm erklären will.
    Im Designer fällt es nicht auf, solange die Beschriftung dort kurz
    ist.

    Abschaltbar bleibt es trotzdem: ein Label, das in einer Zeile
    stehen soll, wächst sonst in die Höhe und verschiebt, was
    darunter liegt."""

    caption = Prop(str, "Label1", kategorie="Darstellung", doc="Anzeigetext")
    color = Prop(
        str,
        "",
        kategorie="Darstellung",
        doc="Hintergrundfarbe als #RRGGBB (nur bei transparent=False)",
        art=ART_FARBE,
    )
    transparent = Prop(
        bool, True, kategorie="Darstellung", doc="Wenn wahr (Standard), kein eigener Hintergrund"
    )
    word_wrap = Prop(
        bool,
        True,
        kategorie="Darstellung",
        doc="Wenn wahr (Standard), bricht zu langer Text um statt abgeschnitten zu werden",
    )
    alignment = _ausrichtung_prop("left")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QLabel(eltern_widget)
        widget.setText(self.caption)
        widget.setWordWrap(self.word_wrap)
        widget.setAlignment(_ausrichtung(self.alignment))
        return widget

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "caption":
            self._qwidget.setText(wert)
        elif name == "alignment":
            self._qwidget.setAlignment(_ausrichtung(wert))
        elif name == "word_wrap":
            self._qwidget.setWordWrap(wert)
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
        str,
        "",
        kategorie="Darstellung",
        doc="Hintergrundfarbe als #RRGGBB, leer = Theme-Standard",
        art=ART_FARBE,
    )
    alignment = _ausrichtung_prop("left")
    password = Prop(
        bool,
        False,
        kategorie="Verhalten",
        doc="Wenn wahr, erscheint statt jedes Zeichens ein Punkt",
    )
    max_length = Prop(
        int,
        0,
        kategorie="Verhalten",
        doc="Höchstzahl der Zeichen, die sich eintippen lassen; 0 = keine Grenze",
    )
    numbers_only = Prop(
        bool,
        False,
        kategorie="Verhalten",
        doc="Wenn wahr, lassen sich nur Ziffern, ein Minus am Anfang und "
        "ein Komma eintippen",
    )
    on_change = Event(doc="Wird bei jeder Änderung des Textes ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QLineEdit(eltern_widget)
        widget.setText(self.text)
        widget.setReadOnly(self.read_only)
        widget.setAlignment(_ausrichtung(self.alignment))
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
        elif name == "alignment":
            self._qwidget.setAlignment(_ausrichtung(wert))
        elif name == "color":
            self._eigenes_qss_anwenden()
        elif name == "password":
            self._qwidget.setEchoMode(
                QLineEdit.EchoMode.Password if wert else QLineEdit.EchoMode.Normal
            )
        elif name == "max_length":
            self._qwidget.setMaxLength(wert if wert > 0 else _KEINE_GRENZE)
        elif name == "numbers_only":
            self._qwidget.setValidator(
                QRegularExpressionValidator(_NUR_ZAHLEN, self._qwidget) if wert else None
            )

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
    on_change = Event(doc="Wird bei jeder Änderung des Textes ausgelöst")

    _eingabe_loest_standardknopf_aus = False

    def __init__(self, parent: Control) -> None:
        self._lines = Strings(self._lines_geaendert, self._zeile_angehaengt)
        #: Solange das Programm den Text ins Widget schreibt, meldet
        #: Qt diese Änderung als `textChanged` zurück. Sie darf dann
        #: nicht noch einmal in `lines` landen.
        self._schreibt_ins_widget = False
        super().__init__(parent)

    @property
    def lines(self) -> Strings:
        return self._lines

    @lines.setter
    def lines(self, werte: list[str]) -> None:
        self._lines.zuweisen(werte)

    @property
    def text(self) -> str:
        """Der ganze Inhalt als ein Text, die Zeilen durch einen
        Zeilenumbruch getrennt. Dieselben Daten wie `lines`."""
        return "\n".join(self._lines)

    @text.setter
    def text(self, wert: str) -> None:
        if not isinstance(wert, str):
            raise NatterPropertyError(
                f"Memo.text erwartet {typ_beschreibung(str, akkusativ=True)}, "
                f"erhalten wurde {typ_beschreibung(type(wert))}."
            )
        self._lines.zuweisen(wert)

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QPlainTextEdit(eltern_widget)
        widget.setReadOnly(self.read_only)
        widget.textChanged.connect(self._bei_textaenderung)
        return widget

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "read_only":
            self._qwidget.setReadOnly(wert)

    def _lines_geaendert(self) -> None:
        self._schreibt_ins_widget = True
        try:
            self._qwidget.setPlainText("\n".join(self._lines))
        finally:
            self._schreibt_ins_widget = False
        self._ereignis_ausloesen("on_change")

    def _zeile_angehaengt(self, zeile: str) -> None:
        """`lines.add`: nur die neue Zeile ins Widget, nicht den ganzen
        Text noch einmal. Ein leeres Feld hat noch keine Zeile, an die
        sich anhängen ließe; dort wird der Text gesetzt."""
        if self._qwidget.document().isEmpty():
            self._lines_geaendert()
            return
        self._schreibt_ins_widget = True
        try:
            self._qwidget.appendPlainText(zeile)
        finally:
            self._schreibt_ins_widget = False
        self._ereignis_ausloesen("on_change")

    def _bei_textaenderung(self) -> None:
        """Was im Memo getippt wird, landet in `lines`.

        Bis Punkt 55 lief es nur in eine Richtung: `lines` ins Widget.
        `lines.save_to_file` speicherte deshalb den Stand, den das
        Programm zuletzt hineingeschrieben hatte, und nicht das, was
        auf dem Bildschirm stand.
        """
        if self._schreibt_ins_widget:
            return
        text = self._qwidget.toPlainText()
        self._lines.still_uebernehmen(text.split("\n") if text else [])
        self._ereignis_ausloesen("on_change")


class ListBox(Control):
    """Einfache Auswahlliste. Qt-Basis: `QListWidget`.

    Mit `multi_select` lassen sich mehrere Einträge wählen, wie unter
    Windows üblich mit gedrückter Strg- oder Umschalttaste. Welche es
    sind, sagt `selected`, eine Liste der Nummern.

    Mit `sorted` ordnet die Liste ihre Einträge selbst alphabetisch,
    auch die, die später mit `items.add()` dazukommen. `items` enthält
    dann dieselbe Reihenfolge, die zu sehen ist, und `item_index` zählt
    in ihr.
    """

    item_index = Prop(
        int, -1, kategorie="Verhalten", doc="Index des ausgewählten Eintrags, -1 = keine Auswahl"
    )
    multi_select = Prop(
        bool,
        False,
        kategorie="Verhalten",
        doc="Wenn wahr, lassen sich mit Strg oder Umschalt mehrere Einträge wählen",
    )
    sorted = Prop(
        bool,
        False,
        kategorie="Verhalten",
        doc="Wenn wahr, stehen die Einträge alphabetisch geordnet",
    )
    on_change = Event(doc="Wird ausgelöst, wenn ein anderer Eintrag ausgewählt wird")

    def __init__(self, parent: Control) -> None:
        self._items = Strings(self._items_geaendert, self._eintrag_angehaengt)
        super().__init__(parent)

    @property
    def items(self) -> Strings:
        return self._items

    @items.setter
    def items(self, werte: list[str]) -> None:
        self._items.zuweisen(werte)

    @property
    def selected(self) -> list[int]:
        """Die Nummern der gewählten Einträge, aufsteigend; leer, wenn
        nichts gewählt ist. Ohne `multi_select` höchstens eine.

        Zuweisen wählt genau diese Einträge:
        ``self.lb_sorten.selected = [0, 2]``.
        """
        widget = self._qwidget
        return sorted(
            zeile for zeile in range(widget.count()) if widget.item(zeile).isSelected()
        )

    @selected.setter
    def selected(self, nummern: list[int]) -> None:
        widget = self._qwidget
        gewuenscht = set()
        for nummer in nummern:
            if isinstance(nummer, bool) or not isinstance(nummer, int):
                raise NatterPropertyError(
                    f"ListBox.selected erwartet Nummern ({typ_beschreibung(int)}), "
                    f"erhalten wurde {typ_beschreibung(type(nummer))}."
                )
            if not 0 <= nummer < widget.count():
                raise NatterZellenError(
                    f"Eintrag {nummer} gibt es nicht, die Liste hat "
                    f"{widget.count()} Einträge."
                )
            gewuenscht.add(nummer)
        if not self.multi_select and len(gewuenscht) > 1:
            raise NatterPropertyError(
                "ListBox.selected: ohne multi_select lässt sich nur ein Eintrag wählen."
            )
        for zeile in range(widget.count()):
            widget.item(zeile).setSelected(zeile in gewuenscht)

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QListWidget(eltern_widget)
        widget.currentRowChanged.connect(self._bei_zeilenwechsel)
        return widget

    def _items_geaendert(self) -> None:
        """Baut die Liste neu auf und behält dabei die Auswahl.

        Die Liste wird geleert und neu gefüllt. Dabei meldete Qt den
        Verlust der Auswahl, und ein `items.add()` hinterließ eine
        Liste ohne Auswahl und ein `on_change`, das niemand ausgelöst
        hatte. Jetzt schweigt das Widget während des Aufbaus; gewählt
        bleibt dieselbe Nummer, in einer sortierten Liste derselbe
        Eintrag. `on_change` kommt nur, wenn es die Nummer nicht mehr
        gibt und die Auswahl deshalb wegfällt.

        Für `multi_select` gilt dasselbe: in einer sortierten Liste
        werden die gewählten Texte wiedergefunden. Über die alten
        Nummern war nach `items.add("a")` vor „b, c“ plötzlich „b“
        statt „c“ gewählt.
        """
        widget = self._qwidget
        vorher = self.item_index
        vorher_gewaehlt = self.selected
        vorher_text = widget.item(vorher).text() if 0 <= vorher < widget.count() else None
        gewaehlte_texte = [widget.item(zeile).text() for zeile in vorher_gewaehlt]
        if self.sorted:
            # Still, sonst meldete das Umordnen sich selbst als
            # Änderung und landete wieder hier.
            self._items.still_uebernehmen(builtins.sorted(self._items, key=str.casefold))
        eintraege = list(self._items)
        widget.blockSignals(True)
        try:
            widget.clear()
            widget.addItems(eintraege)
            neu = vorher if 0 <= vorher < len(eintraege) else -1
            if self.sorted and vorher_text in eintraege:
                neu = eintraege.index(vorher_text)
            widget.setCurrentRow(neu)
            if self.multi_select:
                if self.sorted:
                    vorher_gewaehlt = _zeilen_der_texte(
                        eintraege, gewaehlte_texte
                    )
                for zeile in vorher_gewaehlt:
                    if zeile < widget.count():
                        widget.item(zeile).setSelected(True)
        finally:
            widget.blockSignals(False)
        if neu != vorher:
            self.__dict__["_prop_item_index"] = neu
            self._ereignis_ausloesen("on_change")

    def _eintrag_angehaengt(self, text: str) -> None:
        """`items.add`: nur den neuen Eintrag ans Widget geben. In
        einer sortierten Liste muss er an seinen Platz, dort wird neu
        aufgebaut."""
        if self.sorted:
            self._items_geaendert()
        else:
            self._qwidget.addItem(text)

    def _bei_zeilenwechsel(self, zeile: int) -> None:
        self.item_index = zeile
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "item_index":
            self._qwidget.setCurrentRow(wert)
            # Eine Nummer, die es nicht gibt, wählt nichts. Sie darf
            # dann auch nicht in `item_index` stehen bleiben, sonst
            # endet ein späteres ``items[self.lb.item_index]`` mit
            # einem IndexError.
            if self._qwidget.currentRow() != wert:
                self.__dict__["_prop_item_index"] = self._qwidget.currentRow()
        elif name == "multi_select":
            self._qwidget.setSelectionMode(
                QAbstractItemView.SelectionMode.ExtendedSelection
                if wert
                else QAbstractItemView.SelectionMode.SingleSelection
            )
        elif name == "sorted" and wert:
            self._items_geaendert()


class ComboBox(Control):
    """Dropdown-Auswahl. Qt-Basis: `QComboBox`."""

    item_index = Prop(
        int, -1, kategorie="Verhalten", doc="Index des ausgewählten Eintrags, -1 = keine Auswahl"
    )
    text = Prop(str, "", kategorie="Darstellung", doc="Angezeigter bzw. ausgewählter Text")
    on_change = Event(doc="Wird ausgelöst, wenn ein anderer Eintrag ausgewählt wird")

    def __init__(self, parent: Control) -> None:
        self._items = Strings(self._items_geaendert, self._eintrag_angehaengt)
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
        """Füllt die Liste neu und behält dabei die Auswahl.

        Wie bei der `ListBox`: ohne das stand nach `items.add()` der
        erste Eintrag da statt des gewählten, und `on_change` kam
        zweimal. Ohne vorherige Auswahl wählt Qt beim Füllen den
        ersten Eintrag; das bleibt so und meldet sich als Wechsel.
        """
        widget = self._qwidget
        vorher = self.item_index
        widget.blockSignals(True)
        try:
            widget.clear()
            widget.addItems(list(self._items))
            if 0 <= vorher < widget.count():
                widget.setCurrentIndex(vorher)
        finally:
            widget.blockSignals(False)
        neu = widget.currentIndex()
        self.__dict__["_prop_text"] = widget.currentText()
        if neu != vorher:
            self.__dict__["_prop_item_index"] = neu
            self._ereignis_ausloesen("on_change")

    def _eintrag_angehaengt(self, text: str) -> None:
        """`items.add`: nur den neuen Eintrag ans Widget geben."""
        self._qwidget.addItem(text)

    def _bei_index_wechsel(self, index: int) -> None:
        self.item_index = index
        # `text` vor `on_change` nachziehen. Qt meldet einen Wechsel
        # in zwei Schritten: erst `currentIndexChanged`, dann
        # `currentTextChanged`. Wurde `on_change` schon im ersten
        # ausgelöst, las jede Ereignis-Methode, die `self.cb_x.text`
        # abfragt, noch den vorherigen Text - die Anzeige hinkte der
        # Auswahl dauerhaft einen Schritt hinterher. Gefunden im
        # Beispielprojekt `08_Regression`: ein Klick auf „polynomial"
        # zeigte die lineare Formel, ein Klick auf „exponentiell" die
        # polynomiale.
        self.text = self._qwidget.currentText()
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
            # Einen Text, der nicht in der Liste steht, übergeht Qt.
            # `text` gibt dann wieder, was tatsächlich angezeigt wird.
            if self._qwidget.currentText() != wert:
                self.__dict__["_prop_text"] = self._qwidget.currentText()


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
        if name in ("minimum", "maximum", "position"):
            # Qt schiebt bei einem Minimum über dem Maximum das Maximum
            # mit und kappt die Position. Die Eigenschaften lesen das
            # zurück, damit Programm und Objektinspektor dasselbe sehen
            # wie das Widget.
            for prop_name, gelesen in (
                ("minimum", self._qwidget.minimum()),
                ("maximum", self._qwidget.maximum()),
                ("position", self._qwidget.value()),
            ):
                self.__dict__[f"_prop_{prop_name}"] = gelesen


class GroupBox(Control):
    """Beschrifteter Rahmen, der andere Komponenten zusammenfasst.
 Qt-Basis: `QGroupBox`.

 Als Behälter braucht sie keinen eigenen Code: `Control.__init__`
 hängt jede Komponente an das `_qwidget` ihres `parent`, also genügt
 ``RadioButton(self.g_zahlung)``. `left`/`top` der Kind-Komponente
 zählen dann ab der linken oberen Ecke der GroupBox, und
 ``self.g_zahlung.enabled = False`` sperrt den ganzen Inhalt auf
 einmal (das erledigt Qt).

 Das geht auch im Designer: eine Komponente, die über der GroupBox
 abgelegt wird, landet darin statt daneben auf dem Formular. Dafür
 steht `ist_behaelter`.
 """

    ist_behaelter = True

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
    """`QFrame`, der seine Beschriftung selbst zeichnet, ausgerichtet
    nach `Panel.alignment`.

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
        # Ein paar Pixel Rand, damit links oder rechts ausgerichteter
        # Text nicht am Rahmen klebt.
        flaeche = self.rect().adjusted(4, 0, -4, 0)
        maler.drawText(flaeche, _ausrichtung(self._panel.alignment), self._panel.caption)


class Panel(Control):
    """Fläche, die andere Komponenten zusammenfasst. Qt-Basis: `QFrame`
    mit selbst gezeichneter Beschriftung.

    Behälter wie `GroupBox` - siehe dort.
    """

    ist_behaelter = True

    # Standardgröße als Prop-Standard (wie bei `Chart`).
    width = Prop(int, 185, kategorie="Layout", doc="Breite in Pixeln")
    height = Prop(int, 105, kategorie="Layout", doc="Höhe in Pixeln")

    caption = Prop(str, "Panel1", kategorie="Darstellung", doc="Beschriftung auf der Fläche")
    alignment = _ausrichtung_prop("center")
    color = Prop(
        str,
        "",
        kategorie="Darstellung",
        doc="Hintergrundfarbe als #RRGGBB, leer = Theme-Standard",
        art=ART_FARBE,
    )

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        return _PanelQWidget(eltern_widget, self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name in ("caption", "alignment"):
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
    Eintrag.

    Anders als `GroupBox`/`Panel` ist dies kein offener Behälter: die
    Optionsfelder entstehen aus `items`. Deshalb ist die Komponente auch
    im Designer vollständig
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
                # Nach einem Klick auf eine Option hat sie den Fokus.
                # Ohne den Filter kamen danach weder Tasten beim
                # Formular noch Klicks bei der RadioGroup an.
                if getattr(self, "_maus_filter", None) is not None:
                    self._filter_anhaengen(option)
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
