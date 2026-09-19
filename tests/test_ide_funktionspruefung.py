"""Funktionsprüfung der Haupt-IDE (M11, Abschnitt 3): **jede**
bedienbare Stelle wirklich auslösen, nicht den Code lesen.

Der Grund steht in `docs/arbeitspakete/M11.md`: In M9 haben
Bildschirmfotos und zurückgelesene PDFs sieben Fehler gefunden, die alle
Tests bestanden hatten, und die drei Fehlermeldungen des Nutzers
(Rollen, Menü-Abstürze, Zwischenablage) waren keine Testlücke, sondern
eine Lücke zwischen Test und echter Bedienung.

Das Muster stammt aus `tests/test_diagramm_menue_ausloesen.py`, wo es
eine ganze Fehlerklasse aufgedeckt hat: `QAction.triggered` schickt
immer ein `checked`-Flag mit, das in einem optionalen ersten Parameter
landet. Ein Test, der die Methode direkt aufruft, geht nie durch die
Signalverbindung und sieht davon nichts.

Die Liste der Stellen wird **nicht** von Hand gepflegt, sondern aus dem
Aktionsregister, der Menüleiste, der Werkzeugleiste und der
Komponentenpalette gelesen – sonst veraltet sie beim ersten neuen
Menüeintrag.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QFileDialog,
    QFontDialog,
    QInputDialog,
    QMenu,
    QMessageBox,
)

from ide.inspector.komponentenbaum import kind_komponenten
from ide.palette.palette import TYP_ROLLE
from ide.shell.hauptfenster import HauptFenster

#: Einträge, die das Fenster schließen oder wirklich ein Programm
#: starten. Sie werden einzeln mit stillgelegtem Starter geprüft, nicht
#: im Rundlauf: „Starten“ lässt sonst bei jedem Testlauf einen echten
#: Python-Prozess samt Debugger zurück, und der Lauf bleibt stehen.
AUSGENOMMEN = {
    "Beenden",
    "Schließen",
    "Drucken …",
    # Starten einen echten Prozess: ohne diese Ausnahme bleibt nach
    # jedem Testlauf ein Python-Programm samt Debugger zurück.
    "Starten",
    "Starten ohne Debugger",
    # „Alle Tests ausführen“ startet pytest. Innerhalb von pytest wäre
    # das eine Endlosschleife - der Lauf blieb real stehen, bis das
    # Zeitlimit ihn abbrach.
    "Alle Tests ausführen",
    # Baut wirklich eine Exe; das dauert Minuten und hat mit der Frage
    # „lässt sich der Eintrag auslösen“ nichts zu tun.
    "Als Exe exportieren …",
}


@pytest.fixture(autouse=True)
def _dialoge_stilllegen(monkeypatch: pytest.MonkeyPatch) -> None:
    """Jeder Dialog verhält sich, als hätte der Nutzer abgebrochen.

    Ohne das bliebe der ganze Testlauf an einem modalen `exec()`
    stehen – headless kommt es nie zurück. Das ist in diesem Projekt
    real passiert.
    """
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", "")))
    monkeypatch.setattr(QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", "")))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", staticmethod(lambda *a, **k: ""))
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("", False)))
    monkeypatch.setattr(QInputDialog, "getItem", staticmethod(lambda *a, **k: ("", False)))
    # „Gehe zu Zeile …“ benutzt `getInt` - ohne diese Stelle blieb der
    # ganze Lauf dort stehen.
    monkeypatch.setattr(QInputDialog, "getInt", staticmethod(lambda *a, **k: (1, False)))
    monkeypatch.setattr(QColorDialog, "getColor", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QFontDialog, "getFont", staticmethod(lambda *a, **k: (None, False)))
    monkeypatch.setattr(
        QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)
    )
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "critical", staticmethod(lambda *a, **k: None))
    # „Hilfe → Über Natter“ benutzt `about` - ohne diese Stelle blieb
    # der Lauf dort stehen, und zwar als allerletzter Eintrag.
    monkeypatch.setattr(QMessageBox, "about", staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Rejected.value)


@pytest.fixture
def fenster(qtbot, tmp_path: Path) -> HauptFenster:
    """Ein Fenster mit geöffnetem Projekt: ein leeres Fenster hat die
    halben Aktionen ausgegraut, und gerade die interessanten."""
    import shutil

    quelle = Path(__file__).resolve().parent.parent / "beispielprojekte" / "Garten"
    ziel = tmp_path / "Garten"
    shutil.copytree(quelle, ziel)
    for muell in ziel.rglob("__pycache__"):
        shutil.rmtree(muell, ignore_errors=True)

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(next(ziel.glob("*.natter")))
    return fenster


def _alle_aktionen(fenster: HauptFenster) -> list[tuple[str, object]]:
    """Jede bedienbare Aktion mit einem sprechenden Pfad.

    Gelesen aus der **Menüleiste**, nicht aus dem Aktionsregister
    allein: Dock-Umschalter, Design, Schriftart und die
    Einrückungslinien hängen dort direkt und stehen in keinem Register.
    """
    gefunden: list[tuple[str, object]] = []

    def einsammeln(menue: QMenu, pfad: str) -> None:
        for aktion in menue.actions():
            if aktion.isSeparator():
                continue
            name = f"{pfad}/{aktion.text()}".replace("&", "")
            if aktion.menu() is not None:
                einsammeln(aktion.menu(), name)
            else:
                gefunden.append((name, aktion))

    for menueaktion in fenster.menuBar().actions():
        if menueaktion.menu() is not None:
            einsammeln(menueaktion.menu(), menueaktion.text().replace("&", ""))
    return gefunden


# -- Die Liste selbst ----------------------------------------------------


def test_die_liste_der_bedienbaren_stellen_ist_vollstaendig(
    fenster: HauptFenster,
) -> None:
    """Sie wird aus der Oberfläche gelesen, nicht von Hand gepflegt –
    sonst veraltet sie beim ersten neuen Menüeintrag."""
    namen = [name for name, _ in _alle_aktionen(fenster)]

    assert len(namen) > 25, namen
    # Stichproben aus jedem Menü, damit ein leeres Menü auffällt
    for erwartet in (
        "Datei/Neue Unit",
        "Bearbeiten/Rückgängig",
        "Suchen/Suchen …",
        "Ansicht/Einrückungslinien",
        "Start/Starten",
        "Hilfe/Über Natter",
    ):
        assert erwartet in namen, f"{erwartet} fehlt in {namen}"


def test_jede_aktion_hat_einen_lesbaren_namen(fenster: HauptFenster) -> None:
    """Ein leerer oder englischer Eintrag wäre in einer deutschen
    Oberfläche für Schülerinnen und Schüler ein Fund."""
    for name, aktion in _alle_aktionen(fenster):
        beschriftung = aktion.text().replace("&", "").strip()
        assert beschriftung, f"{name} hat keine Beschriftung"


def test_kein_tastenkuerzel_ist_doppelt_vergeben(fenster: HauptFenster) -> None:
    """Zwei aktive Aktionen auf derselben Taste lösen in Qt gar nichts
    mehr aus. Im Diagramm-Editor ist das real passiert (Strg+G)."""
    vergeben: dict[str, str] = {}
    for name, aktion in _alle_aktionen(fenster):
        if not aktion.isEnabled():
            continue
        for kuerzel in aktion.shortcuts():
            text = kuerzel.toString()
            assert text not in vergeben, (
                f"„{text}“ ist an „{name}“ und an „{vergeben[text]}“ vergeben"
            )
            vergeben[text] = name


# -- Jede Stelle wirklich auslösen ---------------------------------------


def test_jeder_aktive_menueeintrag_laesst_sich_ausloesen(
    fenster: HauptFenster,
) -> None:
    """Der eigentliche Regressionstest: nichts darf beim Auslösen
    hochgehen. Nicht die Methode aufrufen, sondern den Weg gehen, den
    auch ein Klick nimmt."""
    fehler: list[str] = []
    for name, aktion in _alle_aktionen(fenster):
        if not aktion.isEnabled() or aktion.text().replace("&", "") in AUSGENOMMEN:
            continue
        try:
            aktion.trigger()
        except Exception as ausnahme:  # noqa: BLE001 - genau das wird gesucht
            fehler.append(f"{name}: {type(ausnahme).__name__}: {ausnahme}")

    assert not fehler, "\n".join(fehler)


def test_jeder_knopf_der_werkzeugleiste_laesst_sich_ausloesen(
    fenster: HauptFenster,
) -> None:
    fehler: list[str] = []
    for aktion in fenster.werkzeugleiste.actions():
        if (
            aktion.isSeparator()
            or not aktion.isEnabled()
            or aktion.text().replace("&", "") in AUSGENOMMEN
        ):
            continue
        try:
            aktion.trigger()
        except Exception as ausnahme:  # noqa: BLE001
            fehler.append(f"{aktion.text()}: {type(ausnahme).__name__}: {ausnahme}")

    assert not fehler, "\n".join(fehler)


def _alle_kontextmenues(fenster: HauptFenster) -> list[tuple[str, object]]:
    """Die Menüs hinter der rechten Maustaste, mit sprechendem Pfad.

    Bis M11 standen sie ausserhalb des Rundlaufs – dabei probieren die
    meisten dort zuerst. Jedes Menü wird von einer Methode gebaut, die
    es **zurückgibt** statt es zu öffnen; ein `QMenu.exec()` wartet auf
    einen Klick und bliebe im Test stehen.
    """
    gefunden: list[tuple[str, object]] = []

    explorer = fenster.explorer
    explorer.resize(260, 400)
    explorer.show()
    for gruppe in (explorer.formulare_gruppe, explorer.units_gruppe):
        for nummer in range(gruppe.childCount()):
            punkt = explorer.visualItemRect(gruppe.child(nummer)).center()
            menue = explorer.kontextmenue_fuer(punkt)
            if menue is None:
                continue
            for aktion in menue.actions():
                gefunden.append((f"Explorer/{gruppe.text(0)}/{aktion.text()}", aktion))

    from PySide6.QtWidgets import QTreeWidgetItem

    fenster.variablen_baum.addTopLevelItem(QTreeWidgetItem(["zahlen", "[1, 2]"]))
    fenster.variablen_baum.resize(220, 120)
    fenster.show()
    punkt = fenster.variablen_baum.visualItemRect(
        fenster.variablen_baum.topLevelItem(0)
    ).center()
    menue = fenster.variablen_kontextmenue_fuer(punkt)
    if menue is not None:
        for aktion in menue.actions():
            gefunden.append((f"Variablen/{aktion.text()}", aktion))

    # Der Designer öffnet sich nicht von selbst mit dem Projekt; ohne
    # dieses Öffnen bliebe sein Menü ausserhalb des Rundlaufs.
    for pfm in sorted(fenster.projekt.ordner.glob("*.pfm")):
        fenster.designer_oeffnen(pfm)
    for canvas in fenster._offene_canvases:
        kinder = [wert for _, wert in kind_komponenten(canvas.formular)]
        for komponente in (canvas.formular, *kinder):
            for aktion in canvas.kontextmenue_fuer(komponente).actions():
                if not aktion.isSeparator():
                    gefunden.append((f"Designer/{aktion.text()}", aktion))
    return gefunden


def test_die_kontextmenues_sind_im_rundlauf(fenster: HauptFenster) -> None:
    """Sie sollen überhaupt erst einmal gefunden werden – sonst prüfte
    der Test darunter nichts."""
    eintraege = _alle_kontextmenues(fenster)

    assert {pfad.split("/")[0] for pfad, _ in eintraege} == {
        "Explorer",
        "Variablen",
        "Designer",
    }


def test_jeder_kontextmenue_eintrag_laesst_sich_ausloesen(
    fenster: HauptFenster,
) -> None:
    """Derselbe Regressionstest wie für die Menüleiste, nur für die
    rechte Maustaste."""
    fehler: list[str] = []
    for name, aktion in _alle_kontextmenues(fenster):
        if not aktion.isEnabled():
            continue
        try:
            aktion.trigger()
        except Exception as ausnahme:  # noqa: BLE001 - genau das wird gesucht
            fehler.append(f"{name}: {type(ausnahme).__name__}: {ausnahme}")

    assert not fehler, "\n".join(fehler)


def test_jedes_dock_laesst_sich_schliessen_und_wieder_oeffnen(
    fenster: HauptFenster,
) -> None:
    """Nutzer-Feedback aus M7: ein geschlossenes Dock ließ sich nicht
    mehr zurückholen."""
    fenster.show()
    for dock in (
        fenster.explorer_dock,
        fenster.inspektor_dock,
        fenster.palette_dock,
        fenster.datenbank_dock,
        fenster.panels_dock,
    ):
        dock.close()
        assert dock.isVisible() is False, dock.windowTitle()
        dock.toggleViewAction().trigger()
        assert dock.isVisible() is True, dock.windowTitle()


# -- Die Palette ---------------------------------------------------------


def test_jede_komponente_der_palette_laesst_sich_platzieren(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Jede Kachel einmal anfassen: eine Komponente, die sich nicht
    ablegen lässt, fiele sonst erst der Schülerin auf."""
    from PySide6.QtWidgets import QListWidget

    projekt = fenster.projekt.ordner
    fenster.designer_oeffnen(projekt / "u_main.pfm")
    canvas = fenster._aktueller_canvas
    vorher = len(canvas.formular._qwidget.children())

    platziert = 0
    fehler: list[str] = []
    for seite in range(fenster.palette.count()):
        liste = fenster.palette.widget(seite)
        if not isinstance(liste, QListWidget):
            continue
        for zeile in range(liste.count()):
            typ = liste.item(zeile).data(TYP_ROLLE)
            if typ is None:
                continue
            try:
                canvas.komponente_platzieren(typ, 20 + 8 * platziert, 20)
                platziert += 1
            except Exception as ausnahme:  # noqa: BLE001
                fehler.append(f"{typ.__name__}: {type(ausnahme).__name__}: {ausnahme}")

    assert not fehler, "\n".join(fehler)
    assert platziert >= 12, f"nur {platziert} Komponenten in der Palette"
    assert len(canvas.formular._qwidget.children()) > vorher


def test_jede_palettenkachel_hat_ein_symbol(fenster: HauptFenster) -> None:
    """Eine Kachel ohne Bild ist im Unterricht nicht zu treffen – und
    ein Tippfehler im Dateinamen liefert nur ein leeres `QIcon`, keinen
    Fehler (in M8 real passiert)."""
    from PySide6.QtWidgets import QListWidget

    ohne: list[str] = []
    for seite in range(fenster.palette.count()):
        liste = fenster.palette.widget(seite)
        if not isinstance(liste, QListWidget):
            continue
        for zeile in range(liste.count()):
            eintrag = liste.item(zeile)
            typ = eintrag.data(TYP_ROLLE)
            if typ is not None and eintrag.icon().isNull():
                ohne.append(typ.__name__)

    assert not ohne, f"ohne Symbol: {ohne}"


def test_die_startbefehle_loesen_wirklich_den_starter_aus(
    fenster: HauptFenster, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Die Startbefehle sind aus dem Rundlauf ausgenommen, weil sie
    sonst bei jedem Testlauf einen echten Python-Prozess samt Debugger
    zurücklassen. Geprüft werden sie hier – mit stillgelegtem Starter,
    aber über denselben Weg, den ein Klick nimmt.

    Stillgelegt wird die Modulfunktion, nicht die Methode: die
    Rückrufe hängen seit dem Anlegen der Aktion als **gebundene**
    Methode am Signal, ein späteres Ersetzen am Objekt erreicht sie
    nicht mehr.
    """
    from ide.shell import hauptfenster as modul

    gestartet: list[str] = []
    monkeypatch.setattr(modul, "projekt_starten", lambda *a, **k: gestartet.append("ohne") or None)
    monkeypatch.setattr(
        modul.DebugSitzung, "starten", lambda self, *a, **k: gestartet.append("mit")
    )
    # Ruff-Prüfung überspringen: sie startet einen eigenen Prozess und
    # hat mit der Frage nichts zu tun.
    monkeypatch.setattr(modul, "projekt_pruefen", lambda *a, **k: [])

    for pfad, aktion in _alle_aktionen(fenster):
        if pfad in ("Start/Starten", "Start/Starten ohne Debugger"):
            aktion.trigger()

    assert set(gestartet) == {"ohne", "mit"}, gestartet


# -- Aufräumen beim Schließen --------------------------------------------


def test_beim_schliessen_wird_ein_laufendes_programm_beendet(
    fenster: HauptFenster,
) -> None:
    """Beim Aufräumen nach dieser Prüfung gefunden: auf dem Rechner
    warteten neunundvierzig `debugpy`-Prozesse aus früheren Sitzungen
    darauf, dass sich ein Debugger verbindet, der nie kommen würde.

    Schließt jemand Natter, während sein Programm läuft, bleibt es als
    Waise zurück – und der „Stopp“-Knopf, mit dem man es beenden
    könnte, ist mit der IDE verschwunden.
    """

    class _Prozess:
        def __init__(self) -> None:
            self.getoetet = False

        def poll(self) -> None:
            return None

        def kill(self) -> None:
            self.getoetet = True

    prozess = _Prozess()
    fenster.laufender_prozess = prozess

    fenster.close()

    assert prozess.getoetet is True
    assert fenster.laufender_prozess is None


def test_beim_schliessen_wird_die_debugger_sitzung_beendet(
    fenster: HauptFenster,
) -> None:
    class _Sitzung:
        def __init__(self) -> None:
            self.beendet = False

        def beenden(self) -> None:
            self.beendet = True

    sitzung = _Sitzung()
    fenster.debug_sitzung = sitzung

    fenster.close()

    assert sitzung.beendet is True
    assert fenster.debug_sitzung is None


def test_ohne_laufendes_programm_passiert_nichts(fenster: HauptFenster) -> None:
    assert fenster.kindprozesse_beenden() == 0


def test_ein_bereits_beendetes_programm_wird_nicht_noch_einmal_getoetet(
    fenster: HauptFenster,
) -> None:
    """`poll()` liefert den Rückgabewert, wenn das Programm von selbst
    fertig ist – dann gibt es nichts mehr zu beenden."""

    class _Fertig:
        def poll(self) -> int:
            return 0

        def kill(self) -> None:
            raise AssertionError("ein beendetes Programm wird nicht getötet")

    fenster.laufender_prozess = _Fertig()

    assert fenster.kindprozesse_beenden() == 0
