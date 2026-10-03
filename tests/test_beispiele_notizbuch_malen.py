"""Die Beispiele „Notizbuch“ und „Malen“ (Punkt 107).

Gearbeitet wird auf Kopien in `tmp_path`: das Notizbuch schreibt
Dateien, und eingecheckte Beispiele dürfen im Test nicht verändert
werden (AGENTS.md).
"""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from ide.shell.startbild import beispielprojekte
from pcl import dialogs

BEISPIELE = Path(__file__).resolve().parent.parent / "beispielprojekte"
_AM_LEBEN: list[object] = []


def _module_vergessen() -> None:
    for name in [n for n in sys.modules if n.startswith("u_")]:
        sys.modules.pop(name, None)


@pytest.fixture
def laden(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    def laden(projekt: str):
        ordner = tmp_path / projekt
        shutil.copytree(
            BEISPIELE / projekt, ordner, ignore=shutil.ignore_patterns("__pycache__")
        )
        monkeypatch.syspath_prepend(str(ordner))
        monkeypatch.chdir(ordner)
        _module_vergessen()
        formular = importlib.import_module("u_main").Form1()
        _AM_LEBEN.append(formular)
        return formular, ordner

    yield laden
    _module_vergessen()


def test_beide_stehen_bei_den_beispielen() -> None:
    namen = {pfad.parent.name for pfad in beispielprojekte()}
    assert {"10_Notizbuch", "11_Malen"} <= namen


# -- Notizbuch --------------------------------------------------------------


def test_notizbuch_speichert_und_laedt_eine_textdatei(laden, monkeypatch, tmp_path) -> None:
    formular, _ = laden("10_Notizbuch")
    formular.show()
    ziel = tmp_path / "einkauf.txt"
    monkeypatch.setattr("u_main.save_dialog", lambda *args: str(ziel))
    monkeypatch.setattr("u_main.open_dialog", lambda *args: str(ziel))

    formular.m_text.lines = ["Milch", "Brot"]
    assert formular.geaendert
    assert formular.l_status.caption.startswith("Neue Notiz *")

    formular.mi_speichern_click(formular)
    assert ziel.read_text(encoding="utf-8") == "Milch\nBrot\n"
    assert formular.l_status.caption == "einkauf.txt - 2 Zeilen"

    formular.mi_neu_click(formular)
    assert list(formular.m_text.lines) == []

    formular.mi_oeffnen_click(formular)
    assert list(formular.m_text.lines) == ["Milch", "Brot"]
    assert not formular.geaendert


def test_notizbuch_fragt_vor_neu_nach_dem_speichern(laden, monkeypatch) -> None:
    formular, _ = laden("10_Notizbuch")
    gefragt: list[str] = []

    def fragen(frage: str, *args) -> bool:
        gefragt.append(frage)
        return False

    monkeypatch.setattr("u_main.ask_yes_no", fragen)
    formular.m_text.lines = ["wichtig"]
    formular.mi_neu_click(formular)

    assert gefragt == ["Die Notiz ist nicht gespeichert. Jetzt speichern?"]
    assert list(formular.m_text.lines) == []


def test_notizbuch_behaelt_die_notiz_wenn_die_datei_sich_nicht_schreiben_laesst(
    laden, monkeypatch, tmp_path
) -> None:
    """Ein Ordner ohne Schreibrecht beendete bis 0.4.3 das Programm,
    und die Notiz war weg. Jetzt kommt eine Meldung, und sie bleibt
    ungespeichert stehen."""
    formular, _ = laden("10_Notizbuch")
    gemeldet: list[str] = []
    monkeypatch.setattr("u_main.show_message", gemeldet.append)
    monkeypatch.setattr("u_main.save_dialog", lambda *args: str(tmp_path))
    formular.m_text.lines = ["wichtig"]

    assert formular.speichern() is False

    assert "lässt sich dort nicht speichern" in gemeldet[0]
    assert formular.geaendert
    assert formular.dateiname == ""
    assert list(formular.m_text.lines) == ["wichtig"]


def test_notizbuch_bleibt_offen_wenn_das_speichern_abgebrochen_wird(
    laden, monkeypatch
) -> None:
    # Punkt 209: „Ja“ auf die Rückfrage, dann „Abbrechen“ im
    # Speicherdialog - das Fenster bleibt offen, die Notiz auch.
    formular, _ = laden("10_Notizbuch")
    formular.show()
    monkeypatch.setattr("u_main.ask_yes_no", lambda *args: True)
    monkeypatch.setattr("u_main.save_dialog", lambda *args: "")
    formular.m_text.lines = ["wichtig"]

    formular.mi_beenden_click(formular)
    QApplication.processEvents()

    assert formular._qwidget.isVisible()
    assert list(formular.m_text.lines) == ["wichtig"]

    # Wird die Frage verneint, geht es zu.
    monkeypatch.setattr("u_main.ask_yes_no", lambda *args: False)
    formular.close()
    QApplication.processEvents()
    assert not formular._qwidget.isVisible()


def test_notizbuch_hat_ein_menue_und_ein_mitwachsendes_textfeld(laden, qtbot) -> None:
    formular, _ = laden("10_Notizbuch")
    formular.show()
    qtbot.waitExposed(formular._qwidget)

    titel = [aktion.text() for aktion in formular._menueleiste.actions()]
    assert titel == ["&Datei", "&Hilfe"]

    breite = formular.m_text.width
    formular._qwidget.resize(formular._qwidget.width() + 100, formular._qwidget.height())
    qtbot.waitUntil(lambda: formular.m_text.width == breite + 100, timeout=2000)


def test_notizbuch_oeffnet_das_info_fenster_modal(laden) -> None:
    formular, _ = laden("10_Notizbuch")
    formular.show()
    gesehen: list[str] = []

    def schliessen() -> None:
        fenster = QApplication.activeModalWidget() or next(
            w for w in QApplication.topLevelWidgets()
            if w.isVisible() and w.windowTitle() == "Über das Notizbuch"
        )
        gesehen.append(fenster.windowTitle())
        fenster.close()

    QTimer.singleShot(0, schliessen)
    formular.mi_info_click(formular)

    assert gesehen == ["Über das Notizbuch"]


# -- Malen ----------------------------------------------------------------


def test_malen_zeichnet_mit_der_gewaehlten_farbe(laden) -> None:
    formular, _ = laden("11_Malen")
    formular.show()

    formular.farbe_click(formular.p_rot)
    formular.pb_flaeche_mouse_down(formular.pb_flaeche, 10, 20)
    formular.pb_flaeche_mouse_move(formular.pb_flaeche, 60, 20)
    formular.pb_flaeche_mouse_up(formular.pb_flaeche, 60, 20)

    assert formular.pb_flaeche.canvas.pixels[35, 20] == "#e53935"


def test_malen_malt_nur_mit_gedrueckter_taste(laden) -> None:
    formular, _ = laden("11_Malen")
    formular.show()
    formular.pb_flaeche_mouse_move(formular.pb_flaeche, 30, 30)
    formular.pb_flaeche_mouse_move(formular.pb_flaeche, 80, 80)
    assert formular.pb_flaeche.canvas.pixels[55, 55] == "#ffffff"


def test_malen_farbe_aus_dem_dialog(laden, monkeypatch) -> None:
    formular, _ = laden("11_Malen")
    monkeypatch.setattr("u_main.color_dialog", lambda alt: "#123456")
    formular.b_farbe_click(formular.b_farbe)
    assert formular.farbe == "#123456"

    monkeypatch.setattr("u_main.color_dialog", lambda alt: "")
    formular.b_farbe_click(formular.b_farbe)
    assert formular.farbe == "#123456"


def test_malen_dicke_und_leeren(laden) -> None:
    formular, _ = laden("11_Malen")
    formular.tb_dicke.position = 9
    assert formular.l_dicke.caption == "Dicke: 9"

    formular.pb_flaeche_mouse_down(formular.pb_flaeche, 10, 10)
    formular.pb_flaeche_mouse_move(formular.pb_flaeche, 50, 10)
    formular.b_leeren_click(formular.b_leeren)
    assert formular.pb_flaeche.canvas.pixels[30, 10] == "#ffffff"


# -- Beide laufen ohne IDE --------------------------------------------------


@pytest.mark.parametrize("projekt", ["10_Notizbuch", "11_Malen"])
def test_laeuft_mit_python_main_py(projekt: str, tmp_path: Path) -> None:
    """`python main.py` startet das Fenster und läuft, bis es jemand
    schließt. Hier genügt, dass es nach drei Sekunden noch läuft und
    nichts auf die Fehlerausgabe geschrieben hat."""
    ordner = tmp_path / projekt
    shutil.copytree(BEISPIELE / projekt, ordner, ignore=shutil.ignore_patterns("__pycache__"))
    fehler = tmp_path / "fehler.txt"
    umgebung = {**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"}
    wurzel = str(BEISPIELE.parent)
    umgebung["PYTHONPATH"] = wurzel + os.pathsep + umgebung.get("PYTHONPATH", "")
    with open(fehler, "w", encoding="utf-8") as ausgabe:
        prozess = subprocess.Popen(
            [sys.executable, "main.py"], cwd=ordner, stdout=ausgabe, stderr=ausgabe
        )
        try:
            time.sleep(3)
            assert prozess.poll() is None, fehler.read_text(encoding="utf-8")
        finally:
            prozess.kill()
            prozess.wait(timeout=30)
    assert "Traceback" not in fehler.read_text(encoding="utf-8")


def test_dialoge_im_beispiel_kommen_aus_pcl() -> None:
    """Die Beispiele nehmen die Dialoge aus Punkt 90 und bauen keine
    eigenen."""
    quelle = (BEISPIELE / "10_Notizbuch" / "u_main.py").read_text(encoding="utf-8")
    for name in ("ask_yes_no", "open_dialog", "save_dialog"):
        assert name in quelle
        assert hasattr(dialogs, name)


def test_lange_menueeintraege_brechen_im_erzeugten_code_um() -> None:
    """Ein Menüeintrag mit Kürzel und Methode ergab eine Zeile über
    hundert Zeichen; `ruff check` hielt die erzeugte Datei des
    Notizbuchs deshalb an."""
    from ide.codegen.design import design_code_erzeugen

    eintrag = {
        "name": "mi_speichern_unter",
        "caption": "Speichern &unter …",
        "shortcut": "Strg+Umschalt+S",
        "on_click": "mi_speichern_unter_click",
    }
    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {},
        "children": [
            {
                "name": "mm_haupt",
                "type": "MainMenu",
                "properties": {
                    "entries": [{"caption": "&Datei", "children": [eintrag]}]
                },
            }
        ],
    }
    code = design_code_erzeugen(pfm, "u_main.pfm")
    assert max(len(zeile) for zeile in code.splitlines()) <= 100
    namensraum: dict = {}
    exec(compile(code, "u_main_design.py", "exec"), namensraum)
