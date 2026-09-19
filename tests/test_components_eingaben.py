"""`MaskEdit`, `DateEdit`, `TimeEdit`, `Calendar` (M15, Abschnitt 4).

Der Kern dieser vier ist nicht das Widget, sondern der **Typ**: seit M15
kennt `Prop` auch `datetime.date` und `datetime.time`. Damit ist
``self.de_termin.date`` ein echtes Datum, mit dem sich rechnen lässt -
und nicht eine Zeichenkette, die erst jemand zerlegen müsste.

Geprüft wird deshalb beides: dass die Komponente tut, was sie soll, und
dass der Wert unterwegs ein Datum bleibt - im Objektinspektor deutsch
angezeigt, in der `.pfm` als ISO-Zeichenkette, im erzeugten Quelltext
als `date(2026, 11, 23)`.
"""

from __future__ import annotations

from datetime import date, time

import pytest

from pcl import Calendar, DateEdit, Form, MaskEdit, TimeEdit
from pcl.errors import NatterPropertyError
from pcl.properties import pfm_wert, text_aus_wert, wert_aus_pfm, wert_aus_text

_AM_LEBEN: list[object] = []


@pytest.fixture
def formular():
    f = Form()
    _AM_LEBEN.append(f)
    return f


def _bauen(formular, typ):
    k = typ(formular)
    _AM_LEBEN.append(k)
    return k


# -- MaskEdit -----------------------------------------------------------


def test_die_maske_landet_am_widget(formular) -> None:
    feld = _bauen(formular, MaskEdit)

    feld.mask = "00000"

    assert feld._qwidget.inputMask() == "00000"


def test_was_nicht_in_die_maske_passt_kommt_nicht_hinein(formular) -> None:
    """Der ganze Zweck: eine Postleitzahl aus Buchstaben gibt es nicht,
    und das Feld nimmt sie gar nicht erst an."""
    feld = _bauen(formular, MaskEdit)
    feld.mask = "00000"

    feld.text = "abcde"

    assert feld.text == ""


def test_was_in_die_maske_passt_bleibt_stehen(formular) -> None:
    feld = _bauen(formular, MaskEdit)
    feld.mask = "00000"

    feld.text = "20095"

    assert feld.text == "20095"
    assert feld._qwidget.text() == "20095"


def test_die_maske_loescht_einen_schon_gesetzten_text_nicht(formular) -> None:
    """`setInputMask` leert das Feld. Wer erst den Text und dann die
    Maske setzt, hätte den Text sonst verloren."""
    feld = _bauen(formular, MaskEdit)
    feld.text = "20095"

    feld.mask = "00000"

    assert feld.text == "20095"


def test_ohne_maske_ist_es_ein_gewoehnliches_textfeld(formular) -> None:
    feld = _bauen(formular, MaskEdit)

    feld.text = "was auch immer"

    assert feld.text == "was auch immer"


def test_on_change_meldet_jede_aenderung(formular) -> None:
    feld = _bauen(formular, MaskEdit)
    gesehen: list[str] = []
    feld.on_change = lambda sender: gesehen.append(sender.text)

    feld._qwidget.setText("abc")

    assert gesehen == ["abc"]


# -- DateEdit -----------------------------------------------------------


def test_das_datum_ist_ein_echtes_date(formular) -> None:
    feld = _bauen(formular, DateEdit)

    feld.date = date(2026, 11, 23)

    assert feld.date == date(2026, 11, 23)
    assert isinstance(feld.date, date)


def test_mit_dem_datum_laesst_sich_rechnen(formular) -> None:
    """Der Grund für den echten Typ: ``(bis - von).days`` geht nur mit
    einem `date`, nicht mit `"23.11.2026"`."""
    von = _bauen(formular, DateEdit)
    bis = _bauen(formular, DateEdit)
    von.date = date(2026, 11, 23)
    bis.date = date(2026, 12, 24)

    assert (bis.date - von.date).days == 31


def test_das_datum_steht_deutsch_im_feld(formular) -> None:
    feld = _bauen(formular, DateEdit)

    feld.date = date(2026, 11, 23)

    assert feld._qwidget.text() == "23.11.2026"


def test_ein_klick_im_widget_schreibt_zurueck_in_die_prop(formular) -> None:
    from PySide6.QtCore import QDate

    feld = _bauen(formular, DateEdit)
    gesehen: list[date] = []
    feld.on_change = lambda sender: gesehen.append(sender.date)

    feld._qwidget.setDate(QDate(2027, 3, 1))

    assert feld.date == date(2027, 3, 1)
    assert gesehen == [date(2027, 3, 1)]


def test_ein_text_statt_eines_datums_wird_abgelehnt(formular) -> None:
    feld = _bauen(formular, DateEdit)

    with pytest.raises(NatterPropertyError, match="Datum"):
        feld.date = "23.11.2026"


# -- TimeEdit -----------------------------------------------------------


def test_die_uhrzeit_ist_eine_echte_time(formular) -> None:
    feld = _bauen(formular, TimeEdit)

    feld.time = time(17, 45)

    assert feld.time == time(17, 45)
    assert isinstance(feld.time, time)


def test_die_uhrzeit_steht_als_hh_mm_im_feld(formular) -> None:
    feld = _bauen(formular, TimeEdit)

    feld.time = time(7, 5)

    assert feld._qwidget.text() == "07:05"


def test_eine_geaenderte_uhrzeit_kommt_in_der_prop_an(formular) -> None:
    from PySide6.QtCore import QTime

    feld = _bauen(formular, TimeEdit)

    feld._qwidget.setTime(QTime(22, 30))

    assert feld.time == time(22, 30)


# -- Calendar -----------------------------------------------------------


def test_der_kalender_zeigt_deutsche_monatsnamen(formular) -> None:
    """Qt nimmt sonst die Sprache des Systems - auf einem englisch
    eingerichteten Schulrechner stünde dort „November" als „November",
    aber „Montag" als „Monday"."""
    kalender = _bauen(formular, Calendar)

    sprache = kalender._qwidget.locale()

    assert sprache.monthName(11) == "November"
    assert sprache.dayName(1) == "Montag"


def test_der_gewaehlte_tag_ist_ein_date(formular) -> None:
    kalender = _bauen(formular, Calendar)

    kalender.date = date(2026, 11, 23)

    assert kalender.date == date(2026, 11, 23)


def test_eine_auswahl_im_kalender_meldet_sich(formular) -> None:
    from PySide6.QtCore import QDate

    kalender = _bauen(formular, Calendar)
    gesehen: list[date] = []
    kalender.on_change = lambda sender: gesehen.append(sender.date)

    kalender._qwidget.setSelectedDate(QDate(2026, 12, 24))

    assert kalender.date == date(2026, 12, 24)
    assert gesehen == [date(2026, 12, 24)]


# -- Der Typ unterwegs: Anzeige, .pfm, Quelltext ------------------------


def test_im_objektinspektor_steht_das_datum_deutsch() -> None:
    assert text_aus_wert(date(2026, 11, 23)) == "23.11.2026"
    assert text_aus_wert(time(7, 5)) == "07:05"


def test_getippt_wird_ebenfalls_deutsch() -> None:
    assert wert_aus_text(date, "23.11.2026") == date(2026, 11, 23)
    assert wert_aus_text(time, "07:05") == time(7, 5)


def test_ein_unsinniges_datum_faellt_auf() -> None:
    with pytest.raises(ValueError):
        wert_aus_text(date, "32.13.2026")
    with pytest.raises(ValueError):
        wert_aus_text(date, "morgen")


def test_in_der_pfm_steht_iso() -> None:
    """Eine Datei, die Maschinen lesen: ISO sortiert sich richtig und
    ist unabhängig davon, in welchem Land sie geöffnet wird."""
    assert pfm_wert(date(2026, 11, 23)) == "2026-11-23"
    assert pfm_wert(time(7, 5)) == "07:05"
    assert pfm_wert("ein Text") == "ein Text"
    assert pfm_wert(42) == 42


def test_aus_der_pfm_kommt_wieder_ein_datum() -> None:
    assert wert_aus_pfm(date, "2026-11-23") == date(2026, 11, 23)
    assert wert_aus_pfm(time, "07:05") == time(7, 5)
    assert wert_aus_pfm(str, "2026-11-23") == "2026-11-23"


def test_der_erzeugte_quelltext_traegt_ein_echtes_datum() -> None:
    """Im `u_*_design.py` muss `date(2026, 11, 23)` stehen - eine
    Zeichenkette würde die Prop ablehnen, und das Programm startete
    nicht."""
    from ide.codegen.design import design_code_erzeugen

    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {},
        "children": [
            {
                "name": "de_termin",
                "type": "DateEdit",
                "properties": {"date": "2026-11-23"},
            },
            {
                "name": "te_beginn",
                "type": "TimeEdit",
                "properties": {"time": "17:45"},
            },
        ],
    }

    quelltext = design_code_erzeugen(pfm, "u_main.pfm")

    assert "from datetime import date, time" in quelltext
    assert "self.de_termin.date = date(2026, 11, 23)" in quelltext
    assert "self.te_beginn.time = time(17, 45)" in quelltext


def test_ohne_datum_steht_kein_datetime_import_im_erzeugten_code() -> None:
    """Sonst stünde in jeder erzeugten Datei ein Import, den niemand
    braucht."""
    from ide.codegen.design import design_code_erzeugen

    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {},
        "children": [
            {"name": "b_ok", "type": "Button", "properties": {"caption": "OK"}}
        ],
    }

    assert "datetime" not in design_code_erzeugen(pfm, "u_main.pfm")
