"""Abnahmetest für das Beispielprojekt Würfelspiel (M1, Schritt 8).

Treibt die Logik headless über echte Qt-Klicks; der Zufall wird für
reproduzierbare Ergebnisse über `random.randint` kontrolliert, der
`input_box`-Dialog beim Verlieren über `QTimer.singleShot` automatisch
bedient (wie in tests/test_dialogs.py). Siehe tests/test_beispiel_ampel.py
für die Begründung, warum nicht `python main.py` direkt läuft.
"""

import importlib
import shutil
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

_PROJEKT_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "Wuerfelspiel"
_PROJEKT_MODULE = ("main", "u_main", "u_main_design")


@pytest.fixture
def form1_klasse():
    sys.path.insert(0, str(_PROJEKT_ORDNER))
    for name in _PROJEKT_MODULE:
        sys.modules.pop(name, None)
    try:
        modul = importlib.import_module("u_main")
        yield modul.Form1
    finally:
        sys.path.remove(str(_PROJEKT_ORDNER))
        for name in _PROJEKT_MODULE:
            sys.modules.pop(name, None)


@pytest.fixture
def form1_klasse_isoliert(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Wie `form1_klasse`, aber aus einer Kopie in `tmp_path` mit dorthin
    verändertem Arbeitsverzeichnis - nötig für Tests, die (wie der
    HTML-Export, M5 Schritt 9) tatsächlich eine Datei schreiben, siehe
    AGENTS.md und tests/test_beispiel_kontoverwaltung.py."""
    projekt_kopie = tmp_path / "Wuerfelspiel"
    shutil.copytree(_PROJEKT_ORDNER, projekt_kopie)
    monkeypatch.chdir(projekt_kopie)
    sys.path.insert(0, str(projekt_kopie))
    for name in _PROJEKT_MODULE:
        sys.modules.pop(name, None)
    try:
        modul = importlib.import_module("u_main")
        yield modul.Form1
    finally:
        sys.path.remove(str(projekt_kopie))
        for name in _PROJEKT_MODULE:
            sys.modules.pop(name, None)


def _wuerfeln_mit(monkeypatch: pytest.MonkeyPatch, werte: list[int]) -> None:
    folge = iter(werte)
    monkeypatch.setattr("random.randint", lambda a, b: next(folge))


def test_start_zustand(form1_klasse) -> None:
    formular = form1_klasse()
    assert formular.l_zahl.caption == "Gewürfelte Zahl: 0"
    assert formular.l_punkte.caption == "Punkte: 0"
    assert formular.l_leben.caption == "Leben: 3"
    assert (formular.sg_tabelle.cells[0, 0], formular.sg_tabelle.cells[1, 0]) == (
        "Name",
        "Punkte",
    )


def test_normaler_wurf_erhoeht_punkte(form1_klasse, monkeypatch: pytest.MonkeyPatch) -> None:
    formular = form1_klasse()
    _wuerfeln_mit(monkeypatch, [4])

    formular.b_wuerfeln._qwidget.click()

    assert formular.l_zahl.caption == "Gewürfelte Zahl: 4"
    assert formular.l_punkte.caption == "Punkte: 4"
    assert formular.l_leben.caption == "Leben: 3"


def test_sechs_kostet_ein_leben_ohne_punkte(form1_klasse, monkeypatch: pytest.MonkeyPatch) -> None:
    formular = form1_klasse()
    _wuerfeln_mit(monkeypatch, [6])

    formular.b_wuerfeln._qwidget.click()

    assert formular.l_punkte.caption == "Punkte: 0"
    assert formular.l_leben.caption == "Leben: 2"


def test_drei_sechsen_fragen_namen_ab_und_tragen_ergebnis_ein(
    form1_klasse, monkeypatch: pytest.MonkeyPatch
) -> None:
    formular = form1_klasse()
    _wuerfeln_mit(monkeypatch, [3, 6, 6, 6])

    def namen_eingeben() -> None:
        dialog = QApplication.activeModalWidget()
        dialog.setTextValue("Max")
        dialog.accept()

    formular.b_wuerfeln._qwidget.click()  # 3 Punkte
    formular.b_wuerfeln._qwidget.click()  # Leben 3 -> 2
    formular.b_wuerfeln._qwidget.click()  # Leben 2 -> 1

    QTimer.singleShot(0, namen_eingeben)
    formular.b_wuerfeln._qwidget.click()  # Leben 1 -> 0, Namensabfrage

    assert formular.sg_tabelle.row_count == 2
    assert (formular.sg_tabelle.cells[0, 1], formular.sg_tabelle.cells[1, 1]) == ("Max", "3")

    # nach dem Verlust wird zurückgesetzt
    assert formular.l_punkte.caption == "Punkte: 0"
    assert formular.l_leben.caption == "Leben: 3"
    assert formular.b_wuerfeln.enabled is True


def test_highscore_als_html_exportieren_schreibt_datei_und_oeffnet_sie(
    form1_klasse_isoliert, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M5, Schritt 9 (Abnahme): Würfelspiel-Highscore als HTML im
    Browser."""
    formular = form1_klasse_isoliert()
    _wuerfeln_mit(monkeypatch, [3, 6, 6, 6])

    def namen_eingeben() -> None:
        dialog = QApplication.activeModalWidget()
        dialog.setTextValue("Max")
        dialog.accept()

    formular.b_wuerfeln._qwidget.click()
    formular.b_wuerfeln._qwidget.click()
    formular.b_wuerfeln._qwidget.click()
    QTimer.singleShot(0, namen_eingeben)
    formular.b_wuerfeln._qwidget.click()

    aufgerufen = []
    monkeypatch.setattr("u_main.open_url", lambda ziel: aufgerufen.append(ziel))

    formular.b_html_exportieren._qwidget.click()

    datei = Path("highscore.html")
    assert datei.exists()
    inhalt = datei.read_text(encoding="utf-8")
    assert "<h1>Highscore</h1>" in inhalt
    assert "<td>Max</td>" in inhalt
    assert "<td>3</td>" in inhalt
    assert aufgerufen == ["highscore.html"]
