"""Modale Dialogfunktionen: `show_message`, `input_box`, `open_dialog`,
`ask_yes_no`, `save_dialog`, `color_dialog`, `input_number`.

Siehe README.md, Abschnitt 5.1, 5.2. Jeder Dialog ist ein einzelner
Funktionsaufruf und keine Komponente auf dem Formular: eine
unsichtbare Komponente, die nur zum Öffnen eines Dialogs dort liegt,
wäre für Lernende eher verwirrend als hilfreich.

Die neueren Dialoge laufen alle über `_zeigen`. Ein modaler Dialog
wartet auf einen Klick, der in einem Test nie kommt; ein Test ersetzt
`_zeigen` und bedient den fertig eingerichteten Dialog selbst.
"""

from __future__ import annotations

from PySide6.QtCore import QLocale
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QFileDialog,
    QInputDialog,
    QMessageBox,
)

from pcl.errors import NatterPropertyError
from pcl.properties import typ_beschreibung
from pcl.zahlen import text as _zahl_als_text

#: Vorgabefilter von `open_dialog` - Bilddateien.
#:
#: Bilder sind der Fall, für den der Dialog gebraucht wird
#: (Beispielprojekt `05_Bildergalerie`); wer etwas anderes öffnen will,
#: gibt einen eigenen Filter an.
BILDER_FILTER = "Bilder (*.png *.jpg *.jpeg *.bmp *.gif);;Alle Dateien (*.*)"

#: Vorgabefilter von `save_dialog` - Textdateien. Gespeichert wird im
#: Unterricht meist Text: eine Notiz, eine Liste, ein Spielstand.
TEXT_FILTER = "Textdateien (*.txt);;Alle Dateien (*.*)"

_DEUTSCH = QLocale(QLocale.Language.German, QLocale.Country.Germany)

#: Die größte Zahl, die `input_number` ohne eigene Grenzen annimmt -
#: die Grenze des Qt-Eingabefelds für ganze Zahlen.
_GROESSTE_ZAHL = 2_147_483_647


def _zeigen(dialog: QDialog) -> int:
    """Zeigt den Dialog modal und liefert, wie er geschlossen wurde
    (`QDialog.DialogCode`). Tests ersetzen diese Funktion."""
    return dialog.exec()


def _als_text(wert: object, wo: str) -> str:
    """Ein Text bleibt, wie er ist; eine Zahl wird mit Dezimalkomma
    geschrieben wie mit `pcl.text()`.

    ``show_message(ergebnis)`` mit einer Zahl liegt nahe, `print()`
    nimmt Zahlen ja auch. Qt lehnte sie mit einer langen englischen
    Meldung über „wrong argument types“ ab.
    """
    if isinstance(wert, str):
        return wert
    if isinstance(wert, (int, float)) and not isinstance(wert, bool):
        return _zahl_als_text(wert)
    raise NatterPropertyError(
        f"{wo} erwartet einen Text oder eine Zahl, "
        f"erhalten wurde {typ_beschreibung(type(wert))}."
    )


def _zahl_pruefen(wert: object, wo: str) -> None:
    if isinstance(wert, bool) or not isinstance(wert, (int, float)):
        raise NatterPropertyError(
            f"{wo} erwartet eine Zahl, erhalten wurde {typ_beschreibung(type(wert))}."
        )


def _angenommen(ergebnis: int) -> bool:
    return int(getattr(ergebnis, "value", ergebnis)) == QDialog.DialogCode.Accepted.value


def show_message(text: str | float) -> None:
    """Zeigt eine Meldung in einem kleinen Fenster (Abschnitt 5.1).

    Eine Zahl wird mit Dezimalkomma gezeigt: ``show_message(2.5)``
    zeigt „2,5“.
    """
    box = QMessageBox()
    box.setWindowTitle("Natter")
    box.setIcon(QMessageBox.Icon.Information)
    box.setText(_als_text(text, "show_message"))
    _zeigen(box)


def input_box(titel: str, frage: str, standard: str = "") -> str:
    """Fragt einen Text in einem kleinen Dialog ab (Abschnitt 5.1).
    Liefert bei Abbruch `standard` zurück."""
    titel = _als_text(titel, "input_box")
    frage = _als_text(frage, "input_box")
    standard = _als_text(standard, "input_box")
    text, bestaetigt = QInputDialog.getText(None, titel, frage, text=standard)
    return text if bestaetigt else standard


def open_dialog(titel: str = "Datei öffnen", filter: str = BILDER_FILTER) -> str:
    """Lässt eine vorhandene Datei auswählen und liefert ihren Pfad.

    Bei Abbruch kommt ein leerer Text zurück; das ist die Antwort, auf
    die ein Programm ohnehin prüfen muss, und erspart eine zweite
    Rückgabe neben dem Pfad.
    """
    titel = _als_text(titel, "open_dialog")
    filter = _als_text(filter, "open_dialog")
    pfad, _ = QFileDialog.getOpenFileName(None, titel, "", filter)
    return pfad


def ask_yes_no(frage: str, titel: str = "Natter") -> bool:
    """Stellt eine Ja/Nein-Frage und liefert `True` für „Ja“.

    Wer das Fenster schließt, ohne zu antworten, hat nicht „Ja“
    gesagt: dann kommt `False` zurück, wie bei „Nein“::

        if ask_yes_no("Alle Einträge löschen?"):
            self.lb_liste.items.clear()
    """
    box = QMessageBox()
    box.setWindowTitle(_als_text(titel, "ask_yes_no"))
    box.setIcon(QMessageBox.Icon.Question)
    box.setText(_als_text(frage, "ask_yes_no"))
    ja = box.addButton("Ja", QMessageBox.ButtonRole.YesRole)
    nein = box.addButton("Nein", QMessageBox.ButtonRole.NoRole)
    box.setDefaultButton(ja)
    box.setEscapeButton(nein)
    _zeigen(box)
    return box.clickedButton() is ja


def save_dialog(
    titel: str = "Datei speichern",
    filter: str = TEXT_FILTER,
    dateiname: str = "",
) -> str:
    """Lässt einen Dateinamen zum Speichern wählen und liefert den Pfad.

    `dateiname` steht als Vorschlag im Feld. Gibt es die gewählte
    Datei schon, fragt der Dialog selbst, ob sie ersetzt werden soll.
    Bei Abbruch kommt ein leerer Text zurück, wie bei `open_dialog`::

        pfad = save_dialog(dateiname="notizen.txt")
        if pfad:
            self.m_text.lines.save_to_file(pfad)

    Hat der Filter eine Endung (`*.txt`) und fehlt sie am eingetippten
    Namen, wird sie angehängt.
    """
    titel = _als_text(titel, "save_dialog")
    filter = _als_text(filter, "save_dialog")
    dateiname = _als_text(dateiname, "save_dialog")
    dialog = QFileDialog(None, titel, dateiname, filter)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setFileMode(QFileDialog.FileMode.AnyFile)
    endung = _erste_endung(filter)
    if endung:
        dialog.setDefaultSuffix(endung)
    dialog.setLabelText(QFileDialog.DialogLabel.Accept, "Speichern")
    dialog.setLabelText(QFileDialog.DialogLabel.Reject, "Abbrechen")
    if not _angenommen(_zeigen(dialog)):
        return ""
    dateien = dialog.selectedFiles()
    return dateien[0] if dateien else ""


def _erste_endung(filter: str) -> str:
    """Die Endung aus dem ersten Muster des Filters, ohne Punkt: „txt“
    aus „Textdateien (*.txt)“. Leer, wenn das Muster keine hat."""
    anfang = filter.find("(*.")
    if anfang < 0:
        return ""
    rest = filter[anfang + 3 :]
    endung = rest.split(")")[0].split()[0].split(";")[0]
    return "" if endung in ("*", "") else endung


def color_dialog(farbe: str = "#ffffff", titel: str = "Farbe auswählen") -> str:
    """Lässt eine Farbe wählen und liefert sie als „#rrggbb“.

    `farbe` ist die Farbe, die beim Öffnen gewählt ist. Bei Abbruch
    kommt ein leerer Text zurück::

        neu = color_dialog(self.p_flaeche.color or "#ffffff")
        if neu:
            self.p_flaeche.color = neu
    """
    farbe = _als_text(farbe, "color_dialog")
    dialog = QColorDialog(QColor(farbe) if QColor.isValidColorName(farbe) else QColor())
    dialog.setWindowTitle(_als_text(titel, "color_dialog"))
    if not _angenommen(_zeigen(dialog)):
        return ""
    return dialog.selectedColor().name()


def input_number(
    titel: str,
    frage: str,
    standard: float = 0,
    minimum: float = -_GROESSTE_ZAHL,
    maximum: float = _GROESSTE_ZAHL,
    stellen: int = 0,
) -> int | float:
    """Fragt eine Zahl zwischen `minimum` und `maximum` ab.

    Mit `stellen = 0` (Vorgabe) ist es eine ganze Zahl (`int`), sonst
    eine Kommazahl (`float`) mit so vielen Nachkommastellen. Getippt
    wird mit Dezimalkomma. Eine Zahl außerhalb des Bereichs lässt das
    Feld gar nicht zu. Bei Abbruch kommt `standard` zurück::

        alter = input_number("Anmeldung", "Alter:", 16, 6, 99)
        preis = input_number("Kasse", "Preis in Euro:", 1.5, 0, 100, stellen=2)
    """
    for wert in (standard, minimum, maximum):
        _zahl_pruefen(wert, "input_number")
    if isinstance(stellen, bool) or not isinstance(stellen, int) or stellen < 0:
        raise NatterPropertyError(
            "input_number erwartet bei stellen eine ganze Zahl ab 0, "
            f"erhalten wurde {stellen!r}."
        )
    dialog = QInputDialog()
    dialog.setWindowTitle(_als_text(titel, "input_number"))
    dialog.setLabelText(_als_text(frage, "input_number"))
    dialog.setLocale(_DEUTSCH)
    dialog.setOkButtonText("OK")
    dialog.setCancelButtonText("Abbrechen")
    if stellen > 0:
        dialog.setInputMode(QInputDialog.InputMode.DoubleInput)
        dialog.setDoubleDecimals(stellen)
        dialog.setDoubleRange(float(minimum), float(maximum))
        dialog.setDoubleValue(float(standard))
    else:
        dialog.setInputMode(QInputDialog.InputMode.IntInput)
        dialog.setIntRange(int(minimum), int(maximum))
        dialog.setIntValue(int(standard))
    if not _angenommen(_zeigen(dialog)):
        return standard
    if stellen > 0:
        return round(dialog.doubleValue(), stellen)
    return dialog.intValue()
