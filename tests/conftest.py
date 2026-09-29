"""Tests laufen headless (Abschnitt 19: pytest-qt headless), damit sie ohne
Bildschirm/CI-Runner funktionieren. Muss vor jedem PySide6-Import gesetzt
sein, daher hier auf Modulebene."""

import os
import re
import weakref

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

# -- Stufen der Suite (Punkt 223) ------------------------------------------
#
# Die Marker werden aus dem Inhalt der Testdatei abgeleitet, damit
# niemand sie von Hand pflegen muss und ein neuer Test von selbst in
# der richtigen Stufe landet. Die Stufen und ihre Befehle stehen in
# AGENTS.md, Abschnitt Tests.

_DEBUGGER = re.compile(r"DapClient|DebugSitzung|debugpy")
_PROZESS = re.compile(
    r"subprocess|Popen|sys\.executable|QProcess"
    r"|PyInstaller|pyinstaller|Authenticode|signtool"
)
_PROZESS_DATEINAME = re.compile(
    r"auslieferung|exe_export|exporter|signatur|installer"
    r"|beispiele_bedienen|beispiel_eingaben"
)
_HAUPTFENSTER_FIXTURES = {"hauptfenster", "hauptfenster_bauen"}

#: Tests, die mehr als die übliche Grenze brauchen dürfen, mit
#: Grenze in Sekunden. Gilt für die ganze Datei.
#:
#: Der Export als Exe lässt PyInstaller ein ganzes Programm bauen;
#: der Auslieferungsbau prüft echte Bauschritte. Beides dauert auf
#: einem langsamen Rechner mehrere Minuten, ohne dass etwas hängt.
_LANGE_DATEIEN = {
    "test_hauptfenster_exe_export.py": 600,
    "test_exporter.py": 600,
    "test_auslieferung_bauen.py": 600,
}


def pytest_collection_modifyitems(config, items) -> None:  # noqa: ANN001
    """Vergibt die Stufen-Marker `hauptfenster`, `debugger`, `prozess`
    und `rundlauf` und hebt die Zeitgrenze für die Dateien in
    `_LANGE_DATEIEN` an."""
    texte: dict[str, str] = {}
    for item in items:
        pfad = item.path
        schluessel = str(pfad)
        if schluessel not in texte:
            try:
                texte[schluessel] = pfad.read_text(encoding="utf-8")
            except OSError:
                texte[schluessel] = ""
        text = texte[schluessel]
        name = pfad.name

        if "HauptFenster(" in text or _HAUPTFENSTER_FIXTURES & set(item.fixturenames):
            item.add_marker(pytest.mark.hauptfenster)
        if _DEBUGGER.search(text):
            item.add_marker(pytest.mark.debugger)
        if _PROZESS.search(text) or _PROZESS_DATEINAME.search(name):
            item.add_marker(pytest.mark.prozess)
        if name == "test_eigenschaften_rundlauf.py":
            item.add_marker(pytest.mark.rundlauf)
        if name in _LANGE_DATEIEN and item.get_closest_marker("timeout") is None:
            item.add_marker(pytest.mark.timeout(_LANGE_DATEIEN[name]))


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


class _SpeicherAblage:
    """Steht in Tests für die Datei unter `%LOCALAPPDATA%` und die
    Stelle in `HKEY_CURRENT_USER`."""

    def __init__(self) -> None:
        self.text: str | None = None

    def lesen(self) -> str | None:
        return self.text

    def schreiben(self, text: str) -> None:
        self.text = text


@pytest.fixture(autouse=True)
def _pruefungsablagen_isoliert(monkeypatch):
    """Der Prüfungsmodus schreibt seinen Vermerk außer in die Ini auch
    in eine Datei unter `%LOCALAPPDATA%` und in die Registry (Punkt
    227). Im Test liegen beide im Speicher, sonst versetzte ein
    Testlauf den Rechner vier Stunden in den Modus."""
    import pcl.pruefungsmodus as modul

    datei = _SpeicherAblage()
    registry = _SpeicherAblage()
    monkeypatch.setattr(
        modul, "_weitere_ablagen", lambda: [datei, registry], raising=False
    )
    yield [datei, registry]


@pytest.fixture
def pruefung_beenden(_pruefungsablagen_isoliert):
    """Beendet den Prüfungsmodus im Test, indem alle Stellen geleert
    werden. Natter selbst kann das nicht (Punkt 227)."""
    import pcl.pruefungsmodus as modul

    datei, registry = _pruefungsablagen_isoliert

    def beenden(werte: QSettings | None = None) -> None:
        (werte or modul.einstellungen()).remove(modul.ENDE_SCHLUESSEL)
        datei.text = None
        registry.text = None

    return beenden


@pytest.fixture(autouse=True)
def _schliessen_ohne_nachfrage(monkeypatch):
    """Beim Schließen mit ungespeicherten Änderungen fragt das
    Hauptfenster nach (Punkt 84). Viele Tests schließen Fenster mit
    geändertem Text; ohne das hier stünde dort ein Dialog und wartete
    auf einen Klick, der nie kommt. Wer die Nachfrage selbst prüft,
    setzt die Antwort im Test neu.

    Dasselbe gilt für das Diagrammfenster (Punkt 111) und für das
    Löschen einer Komponente, die die Unit noch benutzt (Punkt 294):
    dort löscht der Designer im Test ohne Nachfrage."""
    from PySide6.QtWidgets import QMessageBox

    from ide.designer.canvas import DesignerCanvas
    from ide.diagramm.fenster import DiagrammFenster
    from ide.shell.hauptfenster import HauptFenster

    monkeypatch.setattr(
        HauptFenster,
        "_vor_dem_schliessen_fragen",
        lambda self, namen: QMessageBox.StandardButton.Discard,
    )
    monkeypatch.setattr(
        DiagrammFenster,
        "_vor_dem_schliessen_fragen",
        lambda self: QMessageBox.StandardButton.Discard,
    )
    monkeypatch.setattr(
        DesignerCanvas,
        "_loeschen_trotzdem_fragen",
        lambda self, name, zeile: True,
    )


@pytest.fixture(autouse=True)
def _aufgabe_an_ort_und_stelle(monkeypatch):
    """Die Frage nach einer eigenen Kopie kommt nur bei einem Ordner
    ohne Schreibrecht, bei der Sperre eines anderen Kontos und in
    einem vorläufig entpackten ZIP-Ordner (Punkt 390). Gerät ein Test
    doch einmal dorthin, wartete sie ohne das hier auf einen Klick. Die
    Antwort ist der Knopf, der nichts kopiert („Nur ansehen“,
    „Trotzdem hier öffnen“, bei geänderter Aufgabe „Eigene Kopie
    öffnen“); wer die Frage selbst prüft, setzt sie im Test neu."""
    from ide.shell.hauptfenster import HauptFenster

    monkeypatch.setattr(
        HauptFenster, "_kopie_anbieten",
        lambda self, titel, text, nein, **_kw: False,
    )
    monkeypatch.setattr(
        HauptFenster, "_geaenderte_aufgabe_fragen",
        lambda self, kopie, text="", nein=None: (
            "original" if nein else "behalten"
        ),
    )


@pytest.fixture(autouse=True)
def _im_hauptfaden_aufraeumen():
    """Nach jedem Test räumt der Hauptfaden die Zyklen selbst ab
    (Punkt 136). Sonst tat es gelegentlich ein Hintergrundfaden - etwa
    das Aufwärmen von jedi -, zerstörte dabei ein Fenster eines
    früheren Tests, und Qt brach mit „Fatal Python error: Aborted“ ab.

    Danach friert `gc.freeze()` alles ein, was überlebt hat - vor allem
    die importierten Bibliotheken. Ohne das ging jedes `collect()` alle
    Objekte seit Beginn des Laufs durch, nach den Chart-Tests (pandas,
    matplotlib) über 370 000, und wurde mit jedem Test teurer
    (Punkt 223). So sieht der nächste Test nur, was er selbst anlegt."""
    yield
    import gc

    gc.collect()
    gc.freeze()


#: Jeder pcl-Timer, der im Lauf entsteht (schwach gehalten). Der
#: Aufräumschritt nach jedem Test hält sie alle an.
_ALLE_TIMER: weakref.WeakSet = weakref.WeakSet()


def _timer_merken() -> None:
    from pcl.components.system import Timer

    ursprung = Timer.__init__

    def merken(self, *args, **kwargs):
        ursprung(self, *args, **kwargs)
        _ALLE_TIMER.add(self)

    Timer.__init__ = merken


_timer_merken()


@pytest.fixture(autouse=True)
def _fenster_des_tests_aufraeumen(request):
    """Schließt nach jedem Test die Fenster, die er geöffnet hat, und
    lässt Qt sie löschen (Punkt 223).

    Viele Tests zeigen ein Formular oder bauen einen Dialog und lassen
    ihn am Ende einfach stehen. pcl hält ein gezeigtes Formular fest,
    bis es geschlossen ist (Punkt 214), und Qt behält jedes Fenster
    ohne Eltern. Gemessen lebten nach 500 Tests über 200 Fenster, die
    Zahl der Python-Objekte hatte sich verdreifacht, und das
    `gc.collect()` nach jedem Test wurde mit der Laufzeit immer
    teurer. In einem Prozess brauchte die Suite dadurch ein Mehrfaches
    der Zeit ihrer einzelnen Dateien.

    Fenster einer Fixture, die länger als ein Test lebt, bleiben
    stehen: ein solcher Test räumt nur die pcl-Formulare ab."""
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    vorher = set(map(id, app.topLevelWidgets())) if app else set()
    yield
    app = QApplication.instance()
    if app is None:
        return
    import sys

    # Erst die Timer anhalten: ihr QTimer hat keine Eltern, überlebt
    # das Löschen der Fenster und schrieb dann in Beschriftungen, die
    # es nicht mehr gab - auch bei einem Formular, das nie gezeigt
    # wurde oder schon beim Import einer Testdatei entstand.
    for zeitgeber in list(_ALLE_TIMER):
        try:
            zeitgeber._qtimer.stop()
        except (AttributeError, RuntimeError):
            pass
    form = sys.modules.get("pcl.form")
    if form is not None:
        form._offene_formulare.clear()
    lange_fixtures = any(
        definition.scope in ("module", "class", "package")
        for name in request.fixturenames
        if name not in ("qapp", "qapp_args", "qapp_cls")
        for definition in request._fixturemanager.getfixturedefs(
            name, request.node
        )
        or ()
    )
    if lange_fixtures:
        return
    from PySide6.QtCore import QCoreApplication, QEvent

    for fenster in app.topLevelWidgets():
        if id(fenster) in vorher:
            continue
        # Nicht `close()`: das löst `closeEvent` aus, und manches
        # Fenster fragt darin modal nach dem Speichern - der Lauf
        # stand dann, bis die Zeitgrenze ihn abbrach.
        try:
            fenster.hide()
            fenster.deleteLater()
        except RuntimeError:
            pass
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


@pytest.fixture(autouse=True)
def _zwischenablage_leeren():
    """Nach jedem Test die Zwischenablage leeren.

    Liegt beim Beenden des Prozesses noch ein selbst gesetztes
    `QMimeData` in der Zwischenablage, stürzt Python auf der Plattform
    `offscreen` beim Aufräumen ab (Code 139), obwohl alle Tests
    bestanden haben. Unter Windows selbst passiert das nicht - geprüft
    mit einem Skript ohne Natter -, betroffen sind also nur Testläufe,
    im CI aber jeder, der mit dem Kopieren im Designer endet."""
    yield
    from PySide6.QtWidgets import QApplication

    if QApplication.instance() is not None:
        QApplication.clipboard().clear()


@pytest.fixture(autouse=True)
def _konsole_nicht_offen_halten(monkeypatch):
    """Ein Konsolenprogramm unter dem Debugger wartet am Ende auf die
    Eingabetaste (Punkt 87). In Tests drückt sie niemand; ohne das hier
    endete das Programm nie."""
    from ide.debugger.dap_client import KONSOLE_NICHT_OFFEN_HALTEN

    monkeypatch.setenv(KONSOLE_NICHT_OFFEN_HALTEN, "1")


def hauptfenster_aufraeumen(fenster) -> None:
    """Beendet Programm und Debugger eines Hauptfensters und schließt es.

    `kindprozesse_beenden` steht vor dem Schließen und nicht nur im
    `closeEvent`: ein Test, der die Frage nach ungespeicherten
    Änderungen mit „Abbrechen" beantworten lässt, hält das Fenster
    offen, und dann liefe `closeEvent` nicht bis zum Ende durch.
    """
    import shiboken6

    if not shiboken6.isValid(fenster):
        return
    fenster.kindprozesse_beenden()
    fenster.close()


@pytest.fixture
def hauptfenster_bauen(qtbot):
    """Baut Hauptfenster, die am Ende des Tests sicher geschlossen werden.

    Für Tests, die vor dem Bau noch etwas vorbereiten (Einstellungen,
    ein Projekt, ein ersetztes Verhalten der Klasse) oder die ein
    zweites Fenster für einen „Neustart" brauchen.

    Punkt 223: 39 Dateien bauten ein Hauptfenster, ohne es zu
    registrieren. Geschlossen wurde es nie, `closeEvent` und damit
    `kindprozesse_beenden` liefen nicht, und Fenster samt laufender
    Uhren sammelten sich im Testprozess an. Einzeln brauchten alle
    Dateien 28 Minuten, in einem Prozess über 90 oder die Suite hing.
    """
    from ide.shell.hauptfenster import HauptFenster

    gebaut: list[HauptFenster] = []

    def bauen() -> HauptFenster:
        fenster = HauptFenster()
        qtbot.addWidget(fenster)
        gebaut.append(fenster)
        return fenster

    yield bauen
    for fenster in gebaut:
        hauptfenster_aufraeumen(fenster)


@pytest.fixture
def hauptfenster(hauptfenster_bauen):
    """Ein frisches Hauptfenster ohne Projekt, das nach dem Test
    geschlossen wird. Jeder Test, der ein ganzes Hauptfenster braucht,
    holt es sich hier oder über `hauptfenster_bauen`."""
    return hauptfenster_bauen()


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
