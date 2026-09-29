"""Sammlungen, Auswahl, Dialoge und Fenstergröße in pcl (Punkte 143,
144, 164, 165, 166, 167, 174 und 175). Headless."""

from __future__ import annotations

import time

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from pcl import ComboBox, Form, ListBox, Memo, dialogs, show_message
from pcl.errors import NatterPropertyError
from pcl.strings import Strings

#: Alle Komponenten hier bleiben am Leben, solange das Modul lebt -
#: siehe die Begründung in `tests/test_beispiele_bedienen.py`.
_AM_LEBEN: list[object] = []


@pytest.fixture
def formular():
    f = Form()
    _AM_LEBEN.append(f)
    return f


def _neu(typ, formular):
    k = typ(formular)
    _AM_LEBEN.append(k)
    return k


# -- Punkt 143: Strings[i] = wert prüft den Typ --------------------------


def test_zuweisen_an_eine_zeile_lehnt_eine_zahl_ab(formular) -> None:
    memo = _neu(Memo, formular)
    memo.lines = ["a", "b"]
    with pytest.raises(NatterPropertyError, match="erhalten wurde"):
        memo.lines[0] = 5
    assert memo.lines == ["a", "b"]
    memo.lines[0] = "c"
    assert memo._qwidget.toPlainText() == "c\nb"


def test_zuweisen_an_einen_ausschnitt_prueft_jedes_element() -> None:
    zeilen = Strings()
    zeilen.zuweisen(["a", "b", "c"])
    with pytest.raises(NatterPropertyError):
        zeilen[0:2] = ["x", 5]
    assert list(zeilen) == ["a", "b", "c"]
    zeilen[0:2] = ["x", "y"]
    assert list(zeilen) == ["x", "y", "c"]


def test_listbox_lehnt_eine_zahl_als_eintrag_ab(formular) -> None:
    lb = _neu(ListBox, formular)
    lb.items = ["a"]
    with pytest.raises(NatterPropertyError):
        lb.items[0] = 5
    assert lb.items == ["a"]


# -- Punkt 144: show_message mit einer Zahl -----------------------------


def _gezeigt(monkeypatch) -> list[str]:
    """Ersetzt das Zeigen der Meldung; ein modaler Dialog wartete im
    Test auf einen Klick, der nie kommt."""
    texte: list[str] = []

    def zeigen(dialog) -> int:
        texte.append(dialog.text())
        return 0

    monkeypatch.setattr(QMessageBox, "exec", zeigen)
    return texte


def test_show_message_zeigt_eine_zahl_mit_komma(monkeypatch) -> None:
    texte = _gezeigt(monkeypatch)
    show_message(2.5)
    show_message(42)
    assert texte == ["2,5", "42"]


def test_show_message_lehnt_anderes_deutsch_ab(monkeypatch) -> None:
    _gezeigt(monkeypatch)
    with pytest.raises(NatterPropertyError, match="Text oder eine Zahl"):
        show_message(["a"])


def test_ask_yes_no_nimmt_eine_zahl_als_frage(monkeypatch) -> None:
    texte = _gezeigt(monkeypatch)
    dialogs.ask_yes_no(3.5)
    assert texte == ["3,5"]


def test_input_number_lehnt_einen_text_als_grenze_ab(monkeypatch) -> None:
    monkeypatch.setattr(dialogs, "_zeigen", lambda dialog: 0)
    with pytest.raises(NatterPropertyError, match="erwartet eine Zahl"):
        dialogs.input_number("Titel", "Frage", 0, "1", 10)


# -- Punkt 164: Größe und Lage des Fensters ------------------------------


def test_width_und_height_folgen_dem_fenster(formular) -> None:
    formular.width, formular.height = 480, 360
    formular._qwidget.show()
    QApplication.processEvents()
    formular._qwidget.resize(800, 600)
    QApplication.processEvents()
    assert (formular.width, formular.height) == (800, 600)
    formular.height = 500
    QApplication.processEvents()
    assert formular._qwidget.width() == 800
    assert formular._qwidget.height() == 500
    formular._qwidget.move(123, 77)
    QApplication.processEvents()
    assert (formular.left, formular.top) == (
        formular._qwidget.x(),
        formular._qwidget.y(),
    )
    formular._qwidget.hide()


# -- Punkt 165: items.add behält die Auswahl -----------------------------


def test_combobox_behaelt_die_auswahl_bei_add(formular) -> None:
    cb = _neu(ComboBox, formular)
    cb.items = ["rot", "gruen"]
    cb.item_index = 1
    meldungen: list[tuple[int, str]] = []
    cb.on_change = lambda s: meldungen.append((s.item_index, s.text))
    cb.items.add("gelb")
    del cb.items[2]
    cb.items[0] = "blau"
    assert (cb.item_index, cb.text) == (1, "gruen")
    assert cb._qwidget.currentText() == "gruen"
    assert meldungen == []


def test_listbox_behaelt_die_auswahl_bei_add(formular) -> None:
    lb = _neu(ListBox, formular)
    lb.items = ["rot", "gruen"]
    lb.item_index = 1
    meldungen: list[int] = []
    lb.on_change = lambda s: meldungen.append(s.item_index)
    lb.items.add("gelb")
    lb.items[0] = "blau"
    del lb.items[2]
    assert lb.item_index == 1
    assert lb._qwidget.currentRow() == 1
    assert meldungen == []


def test_listbox_meldet_eine_weggefallene_auswahl(formular) -> None:
    lb = _neu(ListBox, formular)
    lb.items = ["rot", "gruen"]
    lb.item_index = 1
    meldungen: list[int] = []
    lb.on_change = lambda s: meldungen.append(s.item_index)
    del lb.items[1]
    assert lb.item_index == -1
    assert meldungen == [-1]


def test_sortierte_listbox_behaelt_den_gewaehlten_eintrag(formular) -> None:
    lb = _neu(ListBox, formular)
    lb.sorted = True
    lb.items = ["birne", "kiwi"]
    lb.item_index = 1
    lb.items.add("apfel")
    assert lb.items == ["apfel", "birne", "kiwi"]
    assert lb.items[lb.item_index] == "kiwi"
    assert lb._qwidget.currentRow() == lb.item_index


# -- Punkt 166: item_index ohne passenden Eintrag ----------------------


def test_listbox_item_index_ueber_das_ende_ergibt_minus_eins(formular) -> None:
    lb = _neu(ListBox, formular)
    lb.items = ["a", "b"]
    lb.item_index = 5
    assert lb.item_index == -1


def test_listbox_item_index_vor_den_items_ergibt_minus_eins(formular) -> None:
    lb = _neu(ListBox, formular)
    lb.item_index = 1
    lb.items = ["a", "b"]
    assert lb.item_index == -1


# -- Punkt 167: add in einer Schleife ------------------------------------


@pytest.mark.parametrize("typ", [Memo, ListBox, ComboBox], ids=lambda t: t.__name__)
def test_viertausend_mal_add_bleibt_schnell(formular, typ) -> None:
    k = _neu(typ, formular)
    sammlung = k.lines if typ is Memo else k.items
    anfang = time.perf_counter()
    for nummer in range(4000):
        sammlung.add(f"Zeile {nummer}")
    dauer = time.perf_counter() - anfang
    assert len(sammlung) == 4000
    # Vorher quadratisch: 30 s für 4 000 Zeilen. Die Grenze lässt Luft
    # für einen Rechner, auf dem die Tests parallel laufen; einzeln
    # dauert es rund eine halbe Sekunde.
    assert dauer < 3.0, f"{dauer:.2f} s"


def test_memo_add_ergibt_denselben_text(formular) -> None:
    memo = _neu(Memo, formular)
    memo.lines.add("eins")
    memo.lines.add("zwei")
    assert memo._qwidget.toPlainText() == "eins\nzwei"
    memo.lines = [""]
    memo.lines.add("drei")
    assert memo._qwidget.toPlainText() == "\ndrei"
    assert memo.lines == ["", "drei"]


def test_listbox_add_zeigt_den_neuen_eintrag(formular) -> None:
    lb = _neu(ListBox, formular)
    lb.items.add("eins")
    lb.items.add("zwei")
    eintraege = [lb._qwidget.item(i).text() for i in range(lb._qwidget.count())]
    assert eintraege == ["eins", "zwei"]


# -- Punkt 174: Kodierung beim Laden ------------------------------------


def test_load_from_file_ueberspringt_die_bom(tmp_path) -> None:
    datei = tmp_path / "liste.csv"
    datei.write_bytes("Name;Punkte\nJörg;3\n".encode("utf-8-sig"))
    zeilen = Strings()
    zeilen.load_from_file(datei)
    assert zeilen[0] == "Name;Punkte"
    assert zeilen[1] == "Jörg;3"


def test_load_from_file_liest_eine_ansi_datei(tmp_path) -> None:
    datei = tmp_path / "alt.txt"
    datei.write_bytes("Größe\nÄpfel\n".encode("cp1252"))
    zeilen = Strings()
    zeilen.load_from_file(datei)
    assert list(zeilen) == ["Größe", "Äpfel"]


# -- Punkt 175: ComboBox.text ohne passenden Eintrag -------------------


def test_combobox_text_ausserhalb_der_liste(formular) -> None:
    cb = _neu(ComboBox, formular)
    cb.items = ["rot", "gruen"]
    cb.text = "blau"
    assert cb.text == cb._qwidget.currentText() == "rot"
    assert cb.item_index == 0
    cb.text = "gruen"
    assert (cb.text, cb.item_index) == ("gruen", 1)
