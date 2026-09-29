"""Listen, Kommazahlen im Grid, Webadressen, deutsche Qt-Texte und
das Ablehnen des Schließens (offene Punkte 199-202, 207, 208)."""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pandas as pd
import pytest

from pcl import Form, ListBox, Memo, StringGrid, open_url
from pcl.errors import NatterPropertyError

_WURZEL = Path(__file__).resolve().parents[1]
_OFFEN: list[Form] = []


class _Fenster(Form):
    def create_components(self) -> None:
        self.lb_liste = ListBox(self)
        self.m_notiz = Memo(self)
        self.sg_tabelle = StringGrid(self)


def _fenster() -> _Fenster:
    fenster = _Fenster()
    _OFFEN.append(fenster)
    return fenster


# -- 199: sortierte Mehrfachauswahl --------------------------------------


def test_sortierte_mehrfachauswahl_behaelt_die_gewaehlten_texte() -> None:
    liste = _fenster().lb_liste
    liste.sorted = True
    liste.multi_select = True
    liste.items = ["b", "c"]
    liste.selected = [1]

    liste.items.add("a")

    assert list(liste.items) == ["a", "b", "c"]
    assert [liste.items[i] for i in liste.selected] == ["c"]


# -- 200: Kommazahlen im StringGrid --------------------------------------


def test_load_dataframe_schreibt_kommazahlen_wie_text() -> None:
    tabelle = _fenster().sg_tabelle
    df = pd.DataFrame({"wert": [0.1 + 0.2, 1e-05, 1.5e16]})

    tabelle.load_dataframe(df)

    zellen = [tabelle.cells[0, zeile] for zeile in (1, 2, 3)]
    assert zellen == ["0,3", "0,00001", "15000000000000000"]


# -- 201: Webadresse ohne https:// ---------------------------------------


@pytest.mark.parametrize(
    ("eingabe", "erwartet"),
    [
        ("www.schule.de", "https://www.schule.de"),
        ("schule.de/stundenplan", "https://schule.de/stundenplan"),
    ],
)
def test_open_url_erkennt_eine_webadresse_ohne_schema(
    eingabe: str,
    erwartet: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    aufgerufen: list[str] = []
    monkeypatch.setattr("pcl.files._oeffnen", aufgerufen.append)

    open_url(eingabe)

    assert aufgerufen == [erwartet]


def test_open_url_laesst_einen_dateinamen_eine_datei(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    aufgerufen: list[str] = []
    monkeypatch.setattr("pcl.files._oeffnen", aufgerufen.append)

    open_url("bericht.html")

    assert aufgerufen == [(tmp_path / "bericht.html").resolve().as_uri()]


# -- 202: Qts eigene Texte auf Deutsch -----------------------------------

#: Läuft in einem eigenen Prozess: im Testprozess hat womöglich schon
#: die IDE die Übersetzung geladen, und der Test bestünde auch ohne
#: `Application`.
_DEUTSCH_PROBE = textwrap.dedent(
    """
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QInputDialog, QLineEdit

    from pcl import Application, input_box

    Application()
    feld = QLineEdit()
    menue = feld.createStandardContextMenu()
    print("MENUE", "|".join(a.text() for a in menue.actions()))

    def knoepfe_lesen():
        for fenster in QApplication.topLevelWidgets():
            if isinstance(fenster, QInputDialog) and fenster.isVisible():
                from PySide6.QtWidgets import QPushButton
                texte = [k.text() for k in fenster.findChildren(QPushButton)]
                print("KNOEPFE", "|".join(texte))
                fenster.reject()
                return
        QTimer.singleShot(20, knoepfe_lesen)

    QTimer.singleShot(0, knoepfe_lesen)
    input_box("Titel", "Frage")
    """
)


def test_ein_pcl_programm_zeigt_qts_texte_auf_deutsch(tmp_path: Path) -> None:
    skript = tmp_path / "probe.py"
    skript.write_text(_DEUTSCH_PROBE, encoding="utf-8")
    umgebung = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    umgebung["PYTHONPATH"] = str(_WURZEL)
    umgebung["PYTHONIOENCODING"] = "utf-8"
    lauf = subprocess.run(
        [sys.executable, str(skript)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=umgebung,
        timeout=60,
        cwd=tmp_path,
    )
    assert lauf.returncode == 0, lauf.stderr
    zeilen = dict(
        zeile.split(" ", 1) for zeile in lauf.stdout.splitlines() if " " in zeile
    )
    assert "Rückgängig" in zeilen["MENUE"].replace("&", "")
    assert "Abbrechen" in zeilen["KNOEPFE"].replace("&", "")


# -- 207: append, extend, reverse, Memo.text ------------------------------


def test_append_haengt_an_listbox_und_memo_an() -> None:
    fenster = _fenster()
    fenster.lb_liste.items.append("x")
    fenster.m_notiz.lines.append("Zeile")

    assert list(fenster.lb_liste.items) == ["x"]
    assert fenster.lb_liste._qwidget.item(0).text() == "x"
    assert fenster.m_notiz._qwidget.toPlainText() == "Zeile"


def test_extend_reverse_und_plus_gleich() -> None:
    liste = _fenster().lb_liste
    liste.items.extend(["a", "b"])
    liste.items += ["c"]
    liste.items.reverse()

    assert list(liste.items) == ["c", "b", "a"]
    angezeigt = [liste._qwidget.item(i).text() for i in range(3)]
    assert angezeigt == ["c", "b", "a"]
    with pytest.raises(NatterPropertyError):
        liste.items.extend([1])


def test_memo_text_liest_und_schreibt_den_ganzen_inhalt() -> None:
    memo = _fenster().m_notiz
    memo.text = "Erste\nZweite"

    assert list(memo.lines) == ["Erste", "Zweite"]
    assert memo._qwidget.toPlainText() == "Erste\nZweite"

    memo.lines.add("Dritte")
    assert memo.text == "Erste\nZweite\nDritte"
    with pytest.raises(NatterPropertyError, match="Memo.text"):
        memo.text = 5


# -- 208: on_close lehnt das Schließen ab --------------------------------


def test_on_close_mit_false_laesst_das_fenster_offen() -> None:
    class Rueckfrage(Form):
        def create_components(self) -> None:
            self.darf_zu = False
            self.on_close = self.form_close

        def form_close(self, sender) -> bool:
            return self.darf_zu

    formular = Rueckfrage()
    _OFFEN.append(formular)
    formular.show()

    formular.close()
    assert formular._qwidget.isVisible()

    formular.darf_zu = True
    formular.close()
    assert not formular._qwidget.isVisible()


def test_on_close_ohne_rueckgabe_schliesst() -> None:
    formular = Form()
    _OFFEN.append(formular)
    formular.on_close = lambda sender: None
    formular.show()

    formular.close()

    assert not formular._qwidget.isVisible()
