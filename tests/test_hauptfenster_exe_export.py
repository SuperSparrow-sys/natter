"""Tests für „Projekt → Als Exe exportieren …“ (Abschnitt 16, 17;
M8 Schritt 4). Nutzt ein Double für `exe_exportieren`, damit der Test
nicht 15-40 Sekunden auf einen echten PyInstaller-Bau wartet (siehe
`tests/test_exporter.py` für die Export-Logik selbst und
Arbeitspaket M8 für die einmalige echte Abnahme).

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


def test_ohne_offenes_projekt_zeigt_hinweis(hauptfenster) -> None:
    hauptfenster._als_exe_exportieren_aktion()
    meldung = hauptfenster.statusBar().currentMessage()
    assert meldung.startswith("Kein Projekt offen.")
    assert "Projekt → Projekt öffnen …" in meldung


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
        lambda projekt, **_: ExportErgebnis(True, ausgabe, "Signiert."),
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
        return ExportErgebnis(True, ausgabe, "Signiert.")

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
        return ExportErgebnis(True, ausgabe, "Signiert.")

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
        return ExportErgebnis(True, ausgabe, "Signiert.")

    monkeypatch.setattr("ide.shell.hauptfenster.exe_exportieren", gefaelschter_export)
    monkeypatch.setattr("ide.shell.hauptfenster.sys.platform", "nicht-win32")

    staende: list[int] = []
    fenster._als_exe_exportieren_aktion()
    fenster._hintergrundarbeit.fortschritt.connect(lambda p, _t: staende.append(p))
    _abwarten(fenster, qtbot)

    # Danach verschwindet er wieder: ein dauerhaft sichtbarer Balken in
    # der Statuszeile sieht nach einem hängenden Programm aus.
    assert fenster._fortschritt_balken.isHidden()


# Der Grund aus `zertifikat_anlegen` nach einem „Nein“, so lang, wie
# er im Export tatsächlich ankommt.
def _grund_ohne_signatur() -> str:
    from ide.export import signatur

    return (
        "Ohne Signatur: das Zertifikat wurde nicht als vertrauenswürdig "
        "eingetragen, die Rückfrage von Windows wurde verneint, nicht "
        "beantwortet oder ist nicht erlaubt. Natter hat es wieder "
        "entfernt und fragt in diesem Konto nicht erneut. "
        f"{signatur._NEUER_VERSUCH}"
    )


def _meldungen(fenster: HauptFenster) -> list[str]:
    liste = fenster.meldungen_liste
    return [liste.item(i).text() for i in range(liste.count())]


def test_vor_dem_anlegen_des_zertifikats_kommt_eine_ankuendigung(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot, hauptfenster,
) -> None:
    """Punkt 350: die Sicherheitswarnung von Windows kam mitten im
    Export, ohne dass Natter sie angekündigt hätte. Ohne Zertifikat
    und ohne Vermerk erscheint die Ankündigung jetzt, bevor
    `zertifikat_anlegen` läuft, und der Export wartet auf sie."""
    from PySide6.QtWidgets import QMessageBox

    from ide.export import signatur

    hauptfenster.projekt_oeffnen(
        _projekt_kopie(tmp_path) / "04_CookieKlicker.natter"
    )
    exe = tmp_path / "dist" / "04_CookieKlicker.exe"
    exe.parent.mkdir(parents=True)
    exe.write_bytes(b"MZ")
    ablauf: list[str] = []

    monkeypatch.setattr(signatur, "vorhandenes_zertifikat", lambda: None)
    monkeypatch.setattr(
        signatur, "abgelehnt_vermerk", lambda: tmp_path / "vermerk.txt"
    )
    monkeypatch.setattr(
        signatur, "zertifikat_anlegen",
        lambda: ablauf.append("angelegt") or (None, _grund_ohne_signatur()),
    )
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda _eltern, _titel, text: ablauf.append(text)),
    )

    def export(projekt, *, vor_dem_anlegen=None, **_):  # noqa: ANN001, ANN202
        ergebnis = signatur.signieren_wenn_moeglich(
            exe, anlegen=True, vor_dem_anlegen=vor_dem_anlegen
        )
        return ExportErgebnis(True, exe, ergebnis.grund)

    monkeypatch.setattr("ide.shell.hauptfenster.exe_exportieren", export)
    monkeypatch.setattr("ide.shell.hauptfenster.sys.platform", "nicht-win32")

    hauptfenster._als_exe_exportieren_aktion()
    # Nicht über `lauf.wait()`: der Faden wartet auf die Ankündigung,
    # und die kommt nur, solange die Oberfläche Ereignisse verarbeitet.
    lauf = hauptfenster._hintergrundarbeit
    qtbot.waitUntil(lauf.isFinished, timeout=10_000)

    assert len(ablauf) == 2
    ankuendigung, angelegt = ablauf
    assert angelegt == "angelegt"
    assert "Sicherheitswarnung" in ankuendigung
    assert signatur.ZERT_NAME in ankuendigung
    assert "„Nein“" in ankuendigung


def test_der_grund_ohne_signatur_steht_ganz_im_panel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot, hauptfenster,
) -> None:
    """Punkt 351: der Grund endete in der Statuszeile am Fensterrand
    und stand im Panel „Meldungen“ als eine Zeile, deren Rest nur über
    die waagrechte Bildlaufleiste zu erreichen war, hinter englischen
    Zeilen von PyInstaller."""
    monkeypatch.setattr("ide.shell.hauptfenster.sys.platform", "nicht-win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    hauptfenster.resize(1280, 800)
    hauptfenster.show()
    exe = (
        tmp_path / "Dokumente" / "Natter" / "Ampel" / "dist" / "Ampel.exe"
    )
    grund = _grund_ohne_signatur()
    protokoll = (
        "12345 INFO: Building EXE from EXE-00.toc completed successfully.\n"
        f"{grund}\n"
    )

    hauptfenster._export_fertig(ExportErgebnis(True, exe, protokoll))
    qtbot.wait(50)

    texte = _meldungen(hauptfenster)
    liste = hauptfenster.meldungen_liste
    assert " ".join(grund.split()) in " ".join(" ".join(texte).split())
    assert not any("INFO" in t for t in texte)
    assert liste.horizontalScrollBar().maximum() == 0
    status = hauptfenster.statusBar().currentMessage()
    assert "ohne Signatur" in status and "Meldungen" in status
    assert grund not in status


def test_die_rueckfrage_laesst_sich_im_panel_wieder_zulassen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot, hauptfenster,
) -> None:
    """Punkt 352: nach einem „Nein“ ging ein neuer Versuch nur über
    das Löschen einer Datei im ausgeblendeten Ordner `AppData`. Jetzt
    steht nach dem Export ein Eintrag im Panel „Meldungen“, und ein
    Klick darauf hebt den Vermerk auf."""
    from PySide6.QtCore import Qt

    from ide.export import signatur

    monkeypatch.setattr("ide.shell.hauptfenster.sys.platform", "nicht-win32")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    vermerk = signatur.abgelehnt_vermerk()
    vermerk.parent.mkdir(parents=True)
    vermerk.write_text("verneint\n", encoding="utf-8")
    hauptfenster.resize(1280, 800)
    hauptfenster.show()
    exe = tmp_path / "dist" / "Ampel.exe"

    hauptfenster._export_fertig(
        ExportErgebnis(True, exe, _grund_ohne_signatur())
    )
    liste = hauptfenster.meldungen_liste
    eintraege = liste.findItems(
        signatur.WIEDER_FRAGEN, Qt.MatchFlag.MatchExactly
    )
    assert len(eintraege) == 1
    liste.scrollToItem(eintraege[0])
    qtbot.mouseClick(
        liste.viewport(), Qt.MouseButton.LeftButton,
        pos=liste.visualItemRect(eintraege[0]).center(),
    )

    assert not vermerk.exists()
    assert signatur.WIEDER_FRAGEN not in _meldungen(hauptfenster)
    assert "wieder" in hauptfenster.statusBar().currentMessage()
