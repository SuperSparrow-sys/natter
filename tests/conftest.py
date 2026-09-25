"""Tests laufen headless (Abschnitt 19: pytest-qt headless), damit sie ohne
Bildschirm/CI-Runner funktionieren. Muss vor jedem PySide6-Import gesetzt
sein, daher hier auf Modulebene."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Ohne dies findet die "offscreen"-Plattform KEINE echten Windows-
# Systemschriften (auch nicht Consolas!) und weicht auf irgendeine
# zufällig verfügbare Ersatzschrift aus - Tests, die Schriftmetriken
# prüfen (z. B. "passt diese Beschriftung in den Button?"), maßen dann
# gegen eine andere Schrift als die echte App auf dem Bildschirm nutzt
# (real gefunden: Rückmeldung zur Editor-Schriftart, September
# 2026 - `QFontInfo` löste ohne dies fälschlich auf die mitgelieferte
# Cascadia-Code-Datei statt auf das eigentlich angeforderte Consolas
# auf, weil Consolas selbst gar nicht auffindbar war).
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

#: Zeitgrenze für alle Debugger-Tests, die auf einen echten
#: Unterprozess warten (debugpy-Handshake, Haltepunkt erreichen).
#:
#: Real gemessen: einzeln laufen diese Tests in gut einer Sekunde und
#: sind dreimal hintereinander grün. Am Ende der vollen Suite - nach über
#: tausend Qt-Tests im selben Prozess - reichten 15 Sekunden dagegen
#: nicht mehr zuverlässig: in vier Durchläufen fiel jedes Mal ein
#: *anderer* Debugger-Test um. Das war nie ein Fehler im Debugger,
#: sondern eine zu knappe Grenze unter Last.
DEBUG_ZEITGRENZE = 45000

import pytest  # noqa: E402
from PySide6.QtCore import QSettings  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _qt_anwendung():
    """Eine QWidget-Erzeugung ohne vorherige QApplication stürzt den
    Prozess fataler ab, ohne saubere Python-Ausnahme. Diese Fixture stellt
    sicher, dass für die gesamte Testsitzung immer genau eine
    QApplication existiert, bevor irgendein Test ein Widget erzeugt."""
    anwendung = QApplication.instance() or QApplication([])
    # Wie im echten Start (`ide/main.py`): Qts eigene Texte auf Deutsch.
    # Sonst prüften die Tests eine englische Oberfläche - genau das,
    # was M11 Abschnitt 4 abstellen sollte.
    from ide.deutsch import deutsch_einschalten

    deutsch_einschalten(anwendung)
    yield anwendung


@pytest.fixture(autouse=True)
def _qsettings_isoliert(tmp_path):
    """`HauptFenster` speichert die Design-Wahl (Hell/Dunkel/System) über
    `QSettings("Natter", "Natter-IDE")`. Ohne diese Umleitung würden
    Tests in die echte Windows-Registry des Nutzers schreiben und sich
    gegenseitig über den zuletzt gespeicherten Wert beeinflussen."""
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    yield


@pytest.fixture
def hintergrund_abwarten():
    """Wartet, bis der nebenher laufende Vorgang eines Fensters durch ist.

    Export, Testlauf und Paketinstallation laufen seit September 2026 in
    einem eigenen Faden, damit sich die IDE währenddessen bedienen
    lässt. Ein Test, der direkt nach dem Auslösen nachsieht, findet
    deshalb noch nichts.

    Gewartet wird über `QThread.wait()` und nicht über das Signal
    `finished`: der Faden kann schon fertig sein, bevor der Test sich
    auf das Signal legt, und dann wartete er auf etwas, das längst
    vorbei ist. Die Runde Ereignisse danach stellt die Signale
    `fertig`/`fehlgeschlagen` zu, denn erst die schreiben ins Fenster.
    """

    def warten(fenster, zeitlimit_ms: int = 20_000) -> None:
        from PySide6.QtWidgets import QApplication

        lauf = fenster._hintergrundarbeit
        assert lauf is not None, "Es wurde gar keine Hintergrundarbeit gestartet"
        assert lauf.wait(zeitlimit_ms), "Der Faden ist nicht fertig geworden"
        for _ in range(5):
            QApplication.processEvents()

    return warten


@pytest.fixture(autouse=True)
def _heimverzeichnis_isoliert(tmp_path_factory, monkeypatch):
    """Kein Test schreibt in das echte Heimverzeichnis.

    `beispiel_kopieren` legt die Arbeitskopie eines Beispiels im
    Ordner "Documents/Natter" des Nutzers an - auf einem Rechner,
    auf dem das Repository selbst dort liegt, also mitten in den
    Projektstamm. So standen nach einigen Testlaeufen 27 Ordner
    (`01_Begruessung`, `… 2`, `… 3` …) im Stamm und liessen
    `ruff check .` scheitern.

    Der Riegel gilt fuer alle Tests, nicht nur fuer den einen, der es
    ausgeloest hat: welcher Weg im naechsten Jahr dorthin fuehrt,
    weiss heute niemand.
    """
    from pathlib import Path

    # Ueber `tmp_path_factory` und nicht in `tmp_path`: mehrere Tests
    # pruefen, dass ihr `tmp_path` leer geblieben ist oder legen ihn
    # selbst an. Ein Heim-Ordner darin liess sechs davon scheitern -
    # ein Riegel, der die Tests kaputtmacht, die er schuetzen soll.
    heim = tmp_path_factory.mktemp("heim")
    monkeypatch.setattr(Path, "home", staticmethod(lambda: heim))

    # `Path.home()` allein genuegt seit September 2026 nicht mehr:
    # `ide.pfade.dokumente_ordner()` fragt Windows nach dem echten
    # Dokumente-Ordner (`SHGetKnownFolderPath`), und die API kennt
    # weder HOME noch USERPROFILE. Ein Testlauf legte dadurch eine
    # Arbeitskopie in "OneDrive\Dokumente\Natter" an - also genau
    # dort, wo die Arbeit des Nutzers liegt.
    import ide.pfade

    dokumente = heim / "Dokumente"
    monkeypatch.setattr(ide.pfade, "dokumente_ordner", lambda: dokumente)
    return heim


@pytest.fixture(autouse=True)
def _designvorgabe_isoliert():
    """Kein Test hinterlässt `NATTER_THEMA` in der Umgebung.

    Das Hauptfenster setzt die Variable beim Start und bei jedem
    Umschalten des Designs, damit gestartete Programme sie erben. Ein
    Test, der auf Dunkel schaltet, ließe sonst jeden folgenden Test
    „system" als dunkel auflösen - und welcher das ist, hinge von der
    Reihenfolge ab.

    Aufgeräumt wird nach dem Test und nicht über `monkeypatch.delenv`:
    das merkt sich eine fehlende Variable nicht und stellte deshalb
    nichts wieder her, was der Code erst während des Tests gesetzt hat.
    """
    vorher = os.environ.pop("NATTER_THEMA", None)
    yield
    os.environ.pop("NATTER_THEMA", None)
    if vorher is not None:
        os.environ["NATTER_THEMA"] = vorher
