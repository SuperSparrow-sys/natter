"""Eingabekomponenten mit Format: `MaskEdit`, `DateEdit`, `TimeEdit`,
`Calendar` (Abschnitt 5.2).

Alle vier sind ein dünner Mantel um ein Qt-Standardwidget, nach demselben
Muster wie `SpinEdit` und Geschwister in `additional.py`: ein `Prop` je
Lazarus-Eigenschaft, `_bei_prop_aenderung` reicht die Zuweisung an das
Widget weiter, und das Signal des Widgets schreibt den Wert zurück in den
`Prop`. Dadurch wirken Code und Bedienung in beide Richtungen, ohne dass
es eine zweite Quelle für den Wert gäbe.

Datum und Uhrzeit sind echte Python-Typen. `self.de_termin.date` ist
ein `datetime.date`, keine Zeichenkette - damit lässt sich rechnen, und
der Code, den eine Schülerin schreibt, bleibt gewöhnliches Python. In
der Oberfläche steht das Datum deutsch (`20.09.2026`), in der `.pfm` als
ISO-Zeichenkette; beides erledigt `pcl.properties` an einer Stelle
(`DATUM_FORMAT`, `pfm_wert`).
"""

from __future__ import annotations

from datetime import date, time
from typing import Any

from PySide6.QtCore import QDate, QLocale, QTime
from PySide6.QtWidgets import QCalendarWidget, QDateEdit, QLineEdit, QTimeEdit, QWidget

from pcl.components.additional import _prop_gleichziehen
from pcl.control import Control
from pcl.properties import DATUM_FORMAT, ZEIT_FORMAT, Event, Prop

#: Deutsche Monats- und Tagesnamen im `Calendar` und in den Aufklapp-
#: Kalendern von `DateEdit`. Qt nimmt sonst die Sprache des Systems -
#: auf einem englisch eingerichteten Schulrechner stünde dort „Monday".
_DEUTSCH = QLocale(QLocale.Language.German, QLocale.Country.Germany)

#: Qt schreibt Datumsformate anders als Python: `dd.MM.yyyy` statt
#: `%d.%m.%Y`. Beide sollen dasselbe zeigen, deshalb hier die
#: Übersetzung - und nur hier.
_QT_DATUM = DATUM_FORMAT.replace("%d", "dd").replace("%m", "MM").replace("%Y", "yyyy")
_QT_ZEIT = ZEIT_FORMAT.replace("%H", "HH").replace("%M", "mm")


def _als_qdate(wert: date) -> QDate:
    return QDate(wert.year, wert.month, wert.day)


def _als_date(wert: QDate) -> date:
    return date(wert.year(), wert.month(), wert.day())


def _als_qtime(wert: time) -> QTime:
    return QTime(wert.hour, wert.minute)


def _als_time(wert: QTime) -> time:
    return time(wert.hour(), wert.minute())


class MaskEdit(Control):
    """Textfeld mit Eingabemaske (entspricht ``TMaskEdit`` in Lazarus).
    Qt-Basis: `QLineEdit` mit `setInputMask`.

    Die Maske sagt, was an welcher Stelle stehen darf - alles andere
    nimmt das Feld gar nicht erst an. Das erspart die halbe Prüfung im
    Code::

        self.me_datum.mask = "00.00.0000"      # 20.09.2026
        self.me_plz.mask = "00000"             # 12345
        self.me_telefon.mask = "00000-000000"

    Die Zeichen der Maske sind die von Qt und Lazarus: `0` eine Ziffer
    (Pflicht), `9` eine Ziffer (freiwillig), `A` ein Buchstabe
    (Pflicht), `N` Buchstabe oder Ziffer. Alles andere steht fest da.

    Was nicht hineinpasst, nimmt das Feld gar nicht erst an: wer
    bei der Maske `00000` Buchstaben tippt, sieht nichts erscheinen.
    Ob schon genug drinsteht, sagt die Länge::

        if len(self.me_plz.text) < 5:
            self.l_hinweis.caption = "Die Postleitzahl ist zu kurz."

    (Hier stand zwischenzeitlich ein `is_complete`, das Qts
    `hasAcceptableInput()` weiterreichte. Nachgemessen meldete das auch
    bei halb gefülltem Feld „fertig" - eine Eigenschaft, die lügt, ist
    schlimmer als keine.)
    """

    width = Prop(int, 120, kategorie="Layout", doc="Breite in Pixeln")

    text = Prop(str, "", kategorie="Darstellung", doc="Inhalt des Feldes")
    mask = Prop(
        str,
        "",
        kategorie="Verhalten",
        doc="Eingabemaske, z. B. 00.00.0000 für ein Datum (leer = keine)",
    )

    on_change = Event(doc="Wird bei jeder Änderung des Textes ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QLineEdit(eltern_widget)
        widget.textChanged.connect(self._bei_textaenderung)
        return widget

    def _bei_textaenderung(self, text: str) -> None:
        _prop_gleichziehen(self, "text", text)
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "mask":
            # Die Maske vor dem Text: `setInputMask` leert das Feld,
            # ein vorher gesetzter Text wäre sonst weg.
            self._qwidget.setInputMask(wert)
            self._qwidget.setText(self.text)
            self._text_gleichziehen()
        elif name == "text":
            self._qwidget.setText(wert)
            self._text_gleichziehen()

    def _text_gleichziehen(self) -> None:
        """Holt zurück, was wirklich im Feld steht.

        Das Widget weist zurück, was nicht in die Maske passt - bei der
        Maske `00000` bleibt von ``feld.text = "abcde"`` nichts übrig.
        Ohne diesen Abgleich stünde in der Prop weiter `"abcde"`,
        während das Feld leer ist: `text` behauptete etwas, das man
        nirgends sieht. Über `textChanged` allein kommt es nicht
        zurück - war das Feld vorher schon leer, meldet Qt gar keine
        Änderung."""
        _prop_gleichziehen(self, "text", self._qwidget.text())


class DateEdit(Control):
    """Datumsfeld mit Aufklapp-Kalender (entspricht ``TDateEdit``).
    Qt-Basis: `QDateEdit`.

    ``self.de_termin.date`` ist ein gewöhnliches `datetime.date`::

        von = self.de_start.date
        bis = self.de_ende.date
        self.l_dauer.caption = f"{(bis - von).days} Tage"
    """

    width = Prop(int, 130, kategorie="Layout", doc="Breite in Pixeln")

    date = Prop(
        date,
        date(2026, 1, 1),
        kategorie="Verhalten",
        doc="Das eingestellte Datum (TT.MM.JJJJ)",
    )
    on_change = Event(doc="Wird bei jeder Änderung des Datums ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QDateEdit(eltern_widget)
        widget.setLocale(_DEUTSCH)
        widget.setDisplayFormat(_QT_DATUM)
        widget.setCalendarPopup(True)
        widget.calendarWidget().setLocale(_DEUTSCH)
        widget.setDate(_als_qdate(self.date))
        widget.dateChanged.connect(self._bei_datumsaenderung)
        return widget

    def _bei_datumsaenderung(self, wert: QDate) -> None:
        _prop_gleichziehen(self, "date", _als_date(wert))
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "date":
            self._qwidget.setDate(_als_qdate(wert))


class TimeEdit(Control):
    """Uhrzeitfeld (entspricht ``TTimeEdit``). Qt-Basis: `QTimeEdit`.

    ``self.te_beginn.time`` ist ein gewöhnliches `datetime.time`.
    """

    width = Prop(int, 90, kategorie="Layout", doc="Breite in Pixeln")

    time = Prop(
        time, time(8, 0), kategorie="Verhalten", doc="Die eingestellte Uhrzeit (hh:mm)"
    )
    on_change = Event(doc="Wird bei jeder Änderung der Uhrzeit ausgelöst")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QTimeEdit(eltern_widget)
        widget.setLocale(_DEUTSCH)
        widget.setDisplayFormat(_QT_ZEIT)
        widget.setTime(_als_qtime(self.time))
        widget.timeChanged.connect(self._bei_zeitaenderung)
        return widget

    def _bei_zeitaenderung(self, wert: QTime) -> None:
        _prop_gleichziehen(self, "time", _als_time(wert))
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "time":
            self._qwidget.setTime(_als_qtime(wert))


class Calendar(Control):
    """Monatskalender zum Anklicken (entspricht ``TCalendar``).
    Qt-Basis: `QCalendarWidget`, mit deutschen Monats- und Tagesnamen.
    """

    # Ein Kalender braucht Platz - als Prop-Standard, damit er überall
    # gleich groß erscheint (wie bei `Chart` und `RadioGroup`).
    width = Prop(int, 320, kategorie="Layout", doc="Breite in Pixeln")
    height = Prop(int, 220, kategorie="Layout", doc="Höhe in Pixeln")

    date = Prop(
        date, date(2026, 1, 1), kategorie="Verhalten", doc="Der gewählte Tag"
    )
    on_change = Event(doc="Wird ausgelöst, wenn ein anderer Tag gewählt wird")

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        widget = QCalendarWidget(eltern_widget)
        widget.setLocale(_DEUTSCH)
        widget.setGridVisible(True)
        widget.setSelectedDate(_als_qdate(self.date))
        widget.selectionChanged.connect(self._bei_auswahl)
        return widget

    def _bei_auswahl(self) -> None:
        _prop_gleichziehen(self, "date", _als_date(self._qwidget.selectedDate()))
        if self.on_change is not None:
            self.on_change(self)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        super()._bei_prop_aenderung(name, wert)
        if name == "date":
            self._qwidget.setSelectedDate(_als_qdate(wert))
