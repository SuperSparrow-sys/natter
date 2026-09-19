"""Tests für pcl/components/standard.py: Memo, ListBox, ComboBox. Headless.
Siehe docs/PLAN.md, M1 Schritt 6.
"""

from pcl import ComboBox, Form, ListBox, Memo


class _Formular(Form):
    def create_components(self) -> None:
        self.m_ausgabe = Memo(self)
        self.lb_kurzwahl = ListBox(self)
        self.cb_mws = ComboBox(self)


def test_memo_lines_add_zeigt_text_im_qwidget() -> None:
    formular = _Formular()
    formular.m_ausgabe.lines.add("Username: max")
    formular.m_ausgabe.lines.add("Kommentar: hallo")
    assert formular.m_ausgabe._qwidget.toPlainText() == "Username: max\nKommentar: hallo"


def test_memo_lines_clear_leert_qwidget() -> None:
    formular = _Formular()
    formular.m_ausgabe.lines.add("x")
    formular.m_ausgabe.lines.clear()
    assert formular.m_ausgabe._qwidget.toPlainText() == ""


def test_listbox_items_add_fuellt_qwidget() -> None:
    formular = _Formular()
    formular.lb_kurzwahl.items.add("Margherita (5.5 EUR)")
    formular.lb_kurzwahl.items.add("Salami (6.5 EUR)")
    assert formular.lb_kurzwahl._qwidget.count() == 2
    assert formular.lb_kurzwahl._qwidget.item(0).text() == "Margherita (5.5 EUR)"


def test_listbox_item_index_standard_ist_minus_eins() -> None:
    formular = _Formular()
    assert formular.lb_kurzwahl.item_index == -1


def test_listbox_auswahl_ueber_qwidget_aktualisiert_item_index() -> None:
    formular = _Formular()
    formular.lb_kurzwahl.items.add("a")
    formular.lb_kurzwahl.items.add("b")
    formular.lb_kurzwahl._qwidget.setCurrentRow(1)
    assert formular.lb_kurzwahl.item_index == 1


def test_listbox_item_index_zuweisung_wirkt_sofort() -> None:
    formular = _Formular()
    formular.lb_kurzwahl.items.add("a")
    formular.lb_kurzwahl.items.add("b")
    formular.lb_kurzwahl.item_index = 0
    assert formular.lb_kurzwahl._qwidget.currentRow() == 0


def test_combobox_items_und_text() -> None:
    formular = _Formular()
    formular.cb_mws.items.add("Hund")
    formular.cb_mws.items.add("Katze")
    assert formular.cb_mws._qwidget.count() == 2
    assert formular.cb_mws.text == "Hund"  # erster Eintrag automatisch ausgewählt
    assert formular.cb_mws.item_index == 0


def test_combobox_item_index_zuweisung_aktualisiert_text() -> None:
    formular = _Formular()
    formular.cb_mws.items.add("Hund")
    formular.cb_mws.items.add("Katze")
    formular.cb_mws.item_index = 1
    assert formular.cb_mws.text == "Katze"


def test_combobox_auswahl_ueber_qwidget_aktualisiert_props() -> None:
    formular = _Formular()
    formular.cb_mws.items.add("Hund")
    formular.cb_mws.items.add("Katze")
    formular.cb_mws._qwidget.setCurrentIndex(1)
    assert formular.cb_mws.item_index == 1
    assert formular.cb_mws.text == "Katze"


# -- on_change sieht den neuen Text, nicht den alten --------------------
#
# Gefunden im Beispielprojekt `08_Regression` (September 2026): ein Klick
# auf "polynomial" zeigte die *lineare* Formel, ein Klick auf
# "exponentiell" die polynomiale - die Anzeige hinkte der Auswahl
# dauerhaft einen Schritt hinterher. Qt meldet einen Wechsel in zwei
# Schritten (`currentIndexChanged`, dann `currentTextChanged`), und
# `on_change` feuerte schon im ersten. Jede Ereignis-Methode, die
# `self.cb_x.text` abfragt, las damit den vorherigen Text.


def test_combobox_on_change_sieht_den_neuen_text() -> None:
    formular = _Formular()
    formular.cb_mws.items = ["linear", "polynomial", "exponentiell"]
    gesehen: list[str] = []
    formular.cb_mws.on_change = lambda sender: gesehen.append(sender.text)

    formular.cb_mws._qwidget.setCurrentIndex(1)
    formular.cb_mws._qwidget.setCurrentIndex(2)

    assert gesehen == ["polynomial", "exponentiell"]


def test_combobox_on_change_sieht_auch_den_neuen_index() -> None:
    formular = _Formular()
    formular.cb_mws.items = ["a", "b", "c"]
    gesehen: list[int] = []
    formular.cb_mws.on_change = lambda sender: gesehen.append(sender.item_index)

    formular.cb_mws._qwidget.setCurrentIndex(2)

    assert gesehen == [2]


def test_combobox_on_change_feuert_genau_einmal_je_wechsel() -> None:
    """Das Nachziehen von `text` darf keinen zweiten Durchlauf
    auslösen - sonst rechnete jedes Programm alles doppelt."""
    formular = _Formular()
    formular.cb_mws.items = ["a", "b", "c"]
    rufe: list[str] = []
    formular.cb_mws.on_change = lambda sender: rufe.append(sender.text)

    formular.cb_mws._qwidget.setCurrentIndex(1)

    assert rufe == ["b"]


def test_combobox_on_change_wirkt_auch_bei_zuweisung_im_code() -> None:
    formular = _Formular()
    formular.cb_mws.items = ["a", "b", "c"]
    gesehen: list[str] = []
    formular.cb_mws.on_change = lambda sender: gesehen.append(sender.text)

    formular.cb_mws.item_index = 2

    assert gesehen == ["c"]
