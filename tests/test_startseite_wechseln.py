"""Der Weg von einem offenen Projekt zurück zur Startseite.

Bis September 2026 gab es ihn nicht. Das Startbild erschien nur,
solange kein einziger Reiter offen war - wer ein anderes Projekt öffnen
wollte, musste erst jede Datei schließen oder den Weg über
„Projekt → Öffnen …“ kennen und auf die Liste der zuletzt geöffneten
verzichten. Gefragt hat danach der Nutzer: „wie komme ich außerdem von
einem geöffneten Projekt zu der Startseite, wenn ich wechseln möchte?“

Die Antwort ist „Ansicht → Startseite“, und zurück geht es über den
ersten Knopf dort. Die Reiter bleiben dabei offen; das Startbild legt
sich nur davor.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ide.shell.hauptfenster import HauptFenster


def _projekt_kopie(tmp_path: Path) -> Path:
    original = Path(__file__).resolve().parent.parent / "beispielprojekte" / "03_Taschenrechner"
    ziel = tmp_path / "03_Taschenrechner"
    shutil.copytree(original, ziel)
    return ziel / "03_Taschenrechner.natter"


def _mit_projekt(tmp_path: Path, qtbot) -> HauptFenster:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    projektdatei = _projekt_kopie(tmp_path)
    fenster.projekt_oeffnen(projektdatei)
    fenster.datei_oeffnen(projektdatei.parent / "u_main.py")
    return fenster


def test_die_startseite_steht_im_menue_ansicht(qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    eintraege = [a.text() for a in fenster.menue("Ansicht").actions() if a.text()]

    assert "Startseite" in eintraege


def test_bei_offenem_projekt_fuehrt_der_eintrag_zur_startseite(tmp_path: Path, qtbot) -> None:
    fenster = _mit_projekt(tmp_path, qtbot)
    assert fenster.mitte.currentWidget() is fenster.editor_tabs

    fenster._startseite_aktion()

    assert fenster.mitte.currentWidget() is fenster.startbild


def test_die_geoeffneten_dateien_bleiben_offen(tmp_path: Path, qtbot) -> None:
    """Die Startseite legt sich davor, sie schließt nichts.

    Sonst wäre der Weg zur Startseite ein Weg, den niemand zweimal
    geht: einmal hin heißt, die Arbeit von vorn zu suchen.
    """
    fenster = _mit_projekt(tmp_path, qtbot)
    vorher = fenster.editor_tabs.count()

    fenster._startseite_aktion()

    assert fenster.editor_tabs.count() == vorher
    assert fenster.projekt is not None


def test_ein_knopf_fuehrt_zurueck_zur_arbeit(tmp_path: Path, qtbot) -> None:
    fenster = _mit_projekt(tmp_path, qtbot)
    fenster._startseite_aktion()

    assert "zurueck" in fenster.startbild.knoepfe
    knopf = fenster.startbild.knoepfe["zurueck"]
    assert "03_Taschenrechner" in knopf.text()

    knopf.click()

    assert fenster.mitte.currentWidget() is fenster.editor_tabs


def test_ohne_offenes_projekt_gibt_es_keinen_rueckweg_knopf(qtbot) -> None:
    """Ein Knopf „Zurück zu …“ ohne Ziel wäre eine Sackgasse."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster._startseite_aktion()

    assert "zurueck" not in fenster.startbild.knoepfe


def test_derselbe_eintrag_fuehrt_wieder_zurueck(tmp_path: Path, qtbot) -> None:
    """Wer den Weg hin kennt, kennt damit auch den Weg zurück."""
    fenster = _mit_projekt(tmp_path, qtbot)

    fenster._startseite_aktion()
    assert fenster.mitte.currentWidget() is fenster.startbild

    fenster._startseite_aktion()
    assert fenster.mitte.currentWidget() is fenster.editor_tabs


def test_die_startseite_zeigt_das_zuletzt_geoeffnete_projekt(tmp_path: Path, qtbot) -> None:
    """Sie wird beim Aufrufen neu aufgebaut - sonst stünde dort der
    Stand vom Programmstart."""
    fenster = _mit_projekt(tmp_path, qtbot)

    fenster._startseite_aktion()

    beschriftungen = [k.text() for k in fenster.startbild.knoepfe.values()]
    assert any("03_Taschenrechner" in text for text in beschriftungen)


# ------------------------------------------------- Der Ladekreis am Zeiger


def test_beim_start_traegt_der_zeiger_einen_ladekreis(monkeypatch, qtbot) -> None:
    """Vorgabe: „füge noch den Ladekreis für die Maus hinzu in der Zeit,
    bis offen ist“.

    Windows zeigt ihn von sich aus nur die ersten Augenblicke nach dem
    Doppelklick und nimmt ihn dann wieder weg - ausgerechnet in der
    Zeit, in der noch nichts zu sehen ist. Geprüft wird, dass `main()`
    ihn setzt und am Ende auch wieder zurücknimmt: ein Zeiger, der
    dauerhaft als „beschäftigt“ stehen bleibt, wäre schlimmer als
    keiner.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    import ide.main as hauptmodul

    gesetzt: list[Qt.CursorShape] = []
    zurueckgenommen: list[bool] = []

    monkeypatch.setattr(
        QApplication, "setOverrideCursor", staticmethod(lambda c: gesetzt.append(c.shape()))
    )
    monkeypatch.setattr(
        QApplication, "restoreOverrideCursor", staticmethod(lambda: zurueckgenommen.append(True))
    )
    monkeypatch.setattr(hauptmodul, "fehlerhaken_einrichten", lambda: None)
    monkeypatch.setattr(hauptmodul, "integritaet_bestaetigen", lambda _f: True)
    monkeypatch.setattr(QApplication, "exec", lambda self: 0)
    monkeypatch.setattr(hauptmodul.sys, "argv", ["natter"])

    assert hauptmodul.main() == 0

    assert Qt.CursorShape.BusyCursor in gesetzt, "Kein Ladekreis am Zeiger"
    assert zurueckgenommen, "Der Ladekreis bleibt nach dem Start stehen"
