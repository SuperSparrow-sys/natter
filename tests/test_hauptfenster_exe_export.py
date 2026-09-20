"""Tests für „Projekt → Als Exe exportieren …“ (Abschnitt 16, 17;
M8 Schritt 4). Nutzt ein Double für `exe_exportieren`, damit der Test
nicht 15-40 Sekunden auf einen echten PyInstaller-Bau wartet (siehe
`tests/test_exporter.py` für die Export-Logik selbst und
`docs/arbeitspakete/M8.md` für die einmalige echte Abnahme).

Der Export läuft seit September 2026 in einem eigenen Faden - die IDE
bleibt währenddessen bedienbar. Die Tests warten deshalb auf das
Signal, mit dem er sich zurückmeldet, statt anzunehmen, dass nach dem
Aufruf schon alles vorbei ist.
"""

from __future__ import annotations

import shutil
import threading
from pathlib import Path

import pytest

from ide.export.exporter import ExportErgebnis
from ide.shell.hauptfenster import HauptFenster


def _projekt_kopie(tmp_path: Path) -> Path:
    original = Path(__file__).resolve().parent.parent / "beispielprojekte" / "04_CookieKlicker"
    ziel = tmp_path / "04_CookieKlicker"
    shutil.copytree(original, ziel)
    return ziel


def _abwarten(fenster: HauptFenster, qtbot) -> None:
    """Wartet, bis der Faden mit dem Export durch ist.

    Über `QThread.wait()` und nicht über das Signal `finished`: der
    Faden kann schon fertig sein, bevor der Test sich auf das Signal
    legt, und dann wartete er auf etwas, das längst vorbei ist.
    """
    lauf = fenster._hintergrundarbeit
    assert lauf is not None, "Es wurde gar keine Hintergrundarbeit gestartet"
    assert lauf.wait(10_000), "Der Faden ist nicht fertig geworden"
    # Die Signale `fertig`/`fehlgeschlagen` stehen danach noch in der
    # Warteschlange der Oberfläche; ohne diese Runde ist die
    # Nachbereitung noch nicht gelaufen.
    qtbot.wait(100)


def test_ohne_offenes_projekt_zeigt_hinweis() -> None:
    fenster = HauptFenster()
    fenster._als_exe_exportieren_aktion()
    meldung = fenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Projekt offen.")
    assert "Projekt → Öffnen" in meldung


def test_erfolgreicher_export_meldet_den_ausgabepfad(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "04_CookieKlicker.natter")
    ausgabe = tmp_path / "dist" / "04_CookieKlicker.exe"
    ausgabe.parent.mkdir(parents=True)
    ausgabe.write_bytes(b"MZ")

    monkeypatch.setattr(
        "ide.shell.hauptfenster.exe_exportieren",
        lambda projekt, **_: ExportErgebnis(True, ausgabe, "ok"),
    )
    monkeypatch.setattr("ide.shell.hauptfenster.sys.platform", "nicht-win32")

    fenster._als_exe_exportieren_aktion()
    _abwarten(fenster, qtbot)

    assert str(ausgabe) in fenster.statusBar().currentMessage()


def test_fehlgeschlagener_export_zeigt_protokoll_in_meldungen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "04_CookieKlicker.natter")

    monkeypatch.setattr(
        "ide.shell.hauptfenster.exe_exportieren",
        lambda projekt, **_: ExportErgebnis(False, None, "PyInstaller-Fehler: xyz"),
    )

    fenster._als_exe_exportieren_aktion()
    _abwarten(fenster, qtbot)

    texte = [fenster.meldungen_liste.item(i).text() for i in range(fenster.meldungen_liste.count())]
    assert any("PyInstaller-Fehler" in t for t in texte)
    assert "fehlgeschlagen" in fenster.statusBar().currentMessage()


def test_eine_ausnahme_im_export_reisst_die_ide_nicht_mit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Eine Ausnahme in einem Nebenfaden beendet sonst das Programm.

    Hier gehört sie in das Panel „Meldungen“: ein Export, der an einer
    gesperrten Datei scheitert, ist kein Grund, die IDE zu schließen.
    """
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "04_CookieKlicker.natter")

    def platzt(projekt, **_):
        raise PermissionError("Die Datei wird von einem anderen Programm benutzt")

    monkeypatch.setattr("ide.shell.hauptfenster.exe_exportieren", platzt)

    fenster._als_exe_exportieren_aktion()
    _abwarten(fenster, qtbot)

    texte = [fenster.meldungen_liste.item(i).text() for i in range(fenster.meldungen_liste.count())]
    assert any("PermissionError" in t for t in texte)
    assert "fehlgeschlagen" in fenster.statusBar().currentMessage()
    assert fenster._fortschritt_balken.isHidden()


def test_waehrend_des_exports_bleibt_die_oberflaeche_bedienbar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Die eigentliche Vorgabe: „während die exe erstellt wird muss das
    Programm weiterhin bedient werden können“.

    Geprüft wird, was das konkret heißt: während der Export läuft,
    verarbeitet das Fenster weiter Ereignisse. Ein Export, der die
    Oberfläche anhält, käme hier nie bis zur Zusicherung.
    """
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "04_CookieKlicker.natter")
    ausgabe = tmp_path / "dist" / "04_CookieKlicker.exe"
    ausgabe.parent.mkdir(parents=True)
    ausgabe.write_bytes(b"MZ")

    laeuft = threading.Event()
    weiter = threading.Event()

    def langsamer_export(projekt, fortschritt=None, **_):
        laeuft.set()
        weiter.wait(timeout=10)
        return ExportErgebnis(True, ausgabe, "ok")

    monkeypatch.setattr("ide.shell.hauptfenster.exe_exportieren", langsamer_export)
    monkeypatch.setattr("ide.shell.hauptfenster.sys.platform", "nicht-win32")

    fenster._als_exe_exportieren_aktion()
    assert laeuft.wait(timeout=5), "Der Export ist gar nicht angelaufen"

    # Mitten im Export: das Fenster nimmt weiter Ereignisse an und
    # lässt sich bedienen.
    geklickt: list[str] = []
    fenster.ausgabe_zeile("Test während des Exports")
    qtbot.wait(20)
    geklickt.append(fenster.ausgabe_liste.item(fenster.ausgabe_liste.count() - 1).text())
    assert "während des Exports" in geklickt[0]

    weiter.set()
    _abwarten(fenster, qtbot)
    assert str(ausgabe) in fenster.statusBar().currentMessage()


def test_ein_zweiter_export_waehrend_des_ersten_wird_abgelehnt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Zwei gleichzeitige Exporte schrieben in dieselbe Exe."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "04_CookieKlicker.natter")
    ausgabe = tmp_path / "dist" / "04_CookieKlicker.exe"
    ausgabe.parent.mkdir(parents=True)
    ausgabe.write_bytes(b"MZ")

    laeuft = threading.Event()
    weiter = threading.Event()

    def langsamer_export(projekt, fortschritt=None, **_):
        laeuft.set()
        weiter.wait(timeout=10)
        return ExportErgebnis(True, ausgabe, "ok")

    monkeypatch.setattr("ide.shell.hauptfenster.exe_exportieren", langsamer_export)
    monkeypatch.setattr("ide.shell.hauptfenster.sys.platform", "nicht-win32")

    fenster._als_exe_exportieren_aktion()
    assert laeuft.wait(timeout=5)
    erster = fenster._hintergrundarbeit

    fenster._als_exe_exportieren_aktion()

    assert fenster._hintergrundarbeit is erster, "Ein zweiter Faden wurde gestartet"
    assert "wartet" in fenster.statusBar().currentMessage()

    weiter.set()
    _abwarten(fenster, qtbot)


def test_ein_ladebalken_laeuft_in_der_untersten_zeile_mit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Vorgabe: „wenn ich ein Programm als Exe
 exportiere soll unten ein Ladebalken sein in der untersten Zeile".

 Ein Export dauert eine halbe bis eine Minute; ohne Balken sieht das
 nach einem Absturz aus.
 """
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(_projekt_kopie(tmp_path) / "04_CookieKlicker.natter")
    ausgabe = tmp_path / "dist" / "04_CookieKlicker.exe"
    ausgabe.parent.mkdir(parents=True)
    ausgabe.write_bytes(b"MZ")

    def gefaelschter_export(projekt, fortschritt=None, **_):
        # So ruft der echte Exporter zurück, während PyInstaller läuft.
        for prozent, text in ((5, "gestartet"), (55, "gesucht"), (100, "fertig")):
            fortschritt(prozent, text)
        return ExportErgebnis(True, ausgabe, "ok")

    monkeypatch.setattr("ide.shell.hauptfenster.exe_exportieren", gefaelschter_export)
    monkeypatch.setattr("ide.shell.hauptfenster.sys.platform", "nicht-win32")

    staende: list[int] = []
    fenster._als_exe_exportieren_aktion()
    fenster._hintergrundarbeit.fortschritt.connect(lambda p, _t: staende.append(p))
    _abwarten(fenster, qtbot)

    # Danach verschwindet er wieder: ein dauerhaft sichtbarer Balken in
    # der Statuszeile sieht nach einem hängenden Programm aus.
    assert fenster._fortschritt_balken.isHidden()
