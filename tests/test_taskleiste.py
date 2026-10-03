"""Wie Windows IDE und Programme in der Taskleiste führt (Punkt 416).

Ohne eigene Kennung ordnete die Taskleiste beide der `pythonw.exe`
zu: die Knöpfe hießen „Python“, und beim ersten Start nach der
Installation zeigte einer das leere Fenstersymbol. Jetzt melden sich
IDE und Programm unter eigener Kennung an, bevor ein Fenster
entsteht, und die Verknüpfungen des Setups tragen die der IDE.
"""

from __future__ import annotations

import ctypes
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtGui import QIcon

import ide.main
import pcl.application

ISS = Path(__file__).resolve().parent.parent / "tools" / "natter.iss"


@pytest.fixture
def kennungen(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Fängt den Aufruf an Windows ab, statt die Kennung des
    Testprozesses zu ändern."""
    gesetzt: list[str] = []
    shell32 = SimpleNamespace(
        SetCurrentProcessExplicitAppUserModelID=gesetzt.append
    )
    monkeypatch.setattr(ctypes, "windll", SimpleNamespace(shell32=shell32),
                        raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    return gesetzt


@pytest.mark.parametrize(
    ("setzen", "kennung"),
    [
        (ide.main.anwendungs_kennung_setzen, "Natter.IDE"),
        (pcl.application._anwendungs_kennung_setzen, "Natter.Programm"),
    ],
    ids=["ide", "programm"],
)
def test_ide_und_programm_melden_sich_unter_eigener_kennung_an(
    kennungen: list[str], setzen, kennung: str,  # noqa: ANN001
) -> None:
    setzen()
    assert kennungen == [kennung]


def test_eine_exportierte_exe_bleibt_ohne_natter_kennung(
    kennungen: list[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    pcl.application._anwendungs_kennung_setzen()
    assert kennungen == []


def test_die_kennung_steht_vor_der_anwendung(
    kennungen: list[str], monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows nimmt die Kennung nur an, bevor das erste Fenster
    entsteht; `starten()` setzt sie deshalb vor allem anderen."""
    reihenfolge: list[str] = []
    monkeypatch.setattr(
        ide.main, "anwendungs_kennung_setzen",
        lambda: reihenfolge.append("kennung"),
    )

    def _anwendung() -> None:
        reihenfolge.append("anwendung")
        raise RuntimeError("abgebrochen")

    monkeypatch.setattr(ide.main, "anwendung_erzeugen", _anwendung)
    with pytest.raises(RuntimeError):
        ide.main.starten()
    assert reihenfolge == ["kennung", "anwendung"]


def test_die_verknuepfungen_tragen_die_kennung_der_ide() -> None:
    text = ISS.read_text(encoding="utf-8")
    definiert = re.search(r'#define MyAppUserModelID "([^"]+)"', text)
    assert definiert and definiert.group(1) == ide.main.ANWENDUNGS_KENNUNG

    verknuepfungen = [
        zeile for zeile in text.splitlines()
        if zeile.startswith("Name:")
        and 'Filename: "{app}\\{#MyAppExeName}"' in zeile
    ]
    assert len(verknuepfungen) == 2
    for zeile in verknuepfungen:
        assert 'AppUserModelID: "{#MyAppUserModelID}"' in zeile


def test_die_ide_setzt_ihr_symbol_vor_dem_ersten_fenster(qapp) -> None:  # noqa: ANN001
    vorher = qapp.windowIcon()
    qapp.setWindowIcon(QIcon())
    try:
        app = ide.main.anwendung_erzeugen()
        assert not app.windowIcon().isNull()
    finally:
        qapp.setWindowIcon(vorher)


def test_ein_formular_wird_vor_dem_zeigen_benannt(
    qapp, monkeypatch: pytest.MonkeyPatch,  # noqa: ANN001
) -> None:
    """Punkt 469: der Knopf eines Programms hieß „Python“. Windows
    nimmt Namen, Symbol und Befehl vom Fenster, wenn der Knopf
    entsteht; `Form.show` setzt sie deshalb, solange das Fenster noch
    nicht zu sehen ist, und nur beim ersten Zeigen. Dass Windows den
    Namen übernimmt, zeigt nur die echte Taskleiste; offscreen gibt es
    kein echtes Fenster."""
    from pcl import Form, taskleiste

    monkeypatch.setattr(taskleiste, "kennung_gesetzt", True)
    benannt: list[tuple[int, bool]] = []
    monkeypatch.setattr(
        taskleiste, "fenster_benennen",
        lambda hwnd: benannt.append(
            (hwnd, formular._qwidget.isVisible())
        ) or True,
    )
    formular = Form()
    try:
        formular.show()
        formular.show()
        assert benannt == [(int(formular._qwidget.winId()), False)]
    finally:
        formular._qwidget.hide()
        formular._qwidget.deleteLater()


def test_ohne_eigene_kennung_bleibt_das_fenster_unberuehrt(
    qapp, monkeypatch: pytest.MonkeyPatch,  # noqa: ANN001
) -> None:
    """In der IDE und in einer exportierten Exe gibt es keine eigene
    Kennung; Name und Symbol gälten sonst für die Gruppe „Python“."""
    from pcl import taskleiste

    monkeypatch.setattr(taskleiste, "kennung_gesetzt", False)
    assert taskleiste.fenster_benennen(1) is False
