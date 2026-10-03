"""Sicherung ungespeicherter Änderungen je Projekt (Punkt 344).

Beim Abmelden fragt Natter nach dem Speichern, und Windows bietet
nach wenigen Sekunden „Trotzdem abmelden“ an. Damit der Text dabei
nicht verloren geht, legt Natter vor der Frage, kurz nach jeder
Änderung und alle zwei Minuten eine Sicherung
`<Projektname>.natter-sicherung` in den Projektordner und bietet sie
beim nächsten Öffnen an.

`commitDataRequest` lässt sich nur mit einem echten
`QSessionManager` senden; die Tests rufen den Empfänger mit einer
Attrappe auf, wie `tests/test_sitzungsende.py`. Das Beenden durch
Windows bei offener Frage lässt sich im Testprozess nicht auslösen.
Nachgestellt wird es so: die Frage im ersten Fenster bleibt offen
(die Antwort ist „Abbrechen“, auf der Platte ändert sich nichts), das
erste Fenster gilt mit `_beendet` als nicht mehr offen, und ein
zweites Fenster öffnet das Projekt, wie es nach dem nächsten
Anmelden geschähe. Ohne `_beendet` gehörte die Sicherung zu einem
laufenden Fenster und würde nicht angeboten (Punkt 406)."""

from __future__ import annotations

import json
import time
import zipfile
from pathlib import Path

import jsonschema
import pytest
from PySide6.QtWidgets import QMessageBox

from ide.diagramm.neu import diagramm_erzeugen
from ide.project import Projekt, sicherung, sperre
from ide.shell.hauptfenster import (
    _SICHERUNG_TAKT_MS,
    HauptFenster,
    zip_schreiben,
)

_WURZEL = Path(__file__).resolve().parent.parent


class _Sitzung:
    """Steht für den `QSessionManager` beim Abmelden."""

    def __init__(self) -> None:
        self.abgebrochen = False

    def allowsInteraction(self) -> bool:  # noqa: N802
        return True

    def release(self) -> None:
        pass

    def cancel(self) -> None:
        self.abgebrochen = True


def _projekt_anlegen(ordner: Path) -> Path:
    (ordner / "main.py").write_text("a = 1\n", encoding="utf-8")
    natter = ordner / "t.natter"
    natter.write_text(json.dumps({
        "format": "natter-project/1", "name": "T", "type": "console",
        "main": "main.py",
    }), encoding="utf-8")
    return natter


@pytest.fixture
def natter(tmp_path: Path) -> Path:
    return _projekt_anlegen(tmp_path)


@pytest.fixture
def fenster(hauptfenster_bauen, natter: Path) -> HauptFenster:
    """Ein Fenster mit geändertem, ungespeichertem `main.py`."""
    fenster = hauptfenster_bauen()
    fenster.projekt_oeffnen(natter)
    editor = fenster.datei_oeffnen(natter.parent / "main.py")
    editor.selectAll()
    editor.insertPlainText("a = 42\n")
    assert editor.document().isModified()
    return fenster


def _gesichert(ordner: Path) -> dict[str, str]:
    """Pfad und Text jeder Datei in der Sicherung von Projekt „T“."""
    gelesen = sicherung.lesen(ordner / "T.natter-sicherung")
    return {e.pfad: e.text for e in gelesen.eintraege}


def _beendet(fenster: HauptFenster) -> None:
    """Lässt das Fenster als beendet gelten, wie nach „Trotzdem
    abmelden“, obwohl es im Testprozess weiter besteht."""
    sicherung.fenster_geschlossen(fenster._sicherung_herkunft)


@pytest.mark.parametrize(
    ("antwort", "bleibt"),
    [
        (QMessageBox.StandardButton.Cancel, True),
        (QMessageBox.StandardButton.Save, False),
        (QMessageBox.StandardButton.Discard, False),
    ],
    ids=["frage_offen", "speichern", "verwerfen"],
)
def test_abmelden_sichert_vor_der_frage(
    fenster: HauptFenster, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    antwort: QMessageBox.StandardButton, bleibt: bool,
) -> None:
    """Während die Frage offen ist, steht der Text schon in der
    Sicherung. Nach „Speichern“ oder „Verwerfen“ ist sie weg; nach
    „Abbrechen“ arbeitet Natter weiter, und sie bleibt."""
    waehrend_der_frage = []

    def fragen(self, namen):  # noqa: ANN001, ANN202
        waehrend_der_frage.append(_gesichert(tmp_path))
        return antwort

    monkeypatch.setattr(HauptFenster, "_vor_dem_schliessen_fragen", fragen)

    fenster._sitzungsende_klaeren(_Sitzung())
    # Beim Schließen am Ende des Tests wird verworfen.
    monkeypatch.setattr(
        HauptFenster, "_vor_dem_schliessen_fragen",
        lambda self, namen: QMessageBox.StandardButton.Discard,
    )

    assert waehrend_der_frage == [{"main.py": "a = 42\n"}]
    assert (tmp_path / "T.natter-sicherung").exists() is bleibt


@pytest.mark.parametrize(
    "wiederherstellen", [True, False], ids=["wiederherstellen", "verwerfen"]
)
def test_naechstes_oeffnen_bietet_die_sicherung_an(
    fenster: HauptFenster, hauptfenster_bauen, natter: Path,
    monkeypatch: pytest.MonkeyPatch, wiederherstellen: bool,
) -> None:
    """Das Kriterium aus Punkt 344: `commitDataRequest` mit geändertem
    Editor, die Frage bleibt unbeantwortet, und beim nächsten Öffnen
    des Projekts kommt der Text wieder."""
    ordner = natter.parent
    monkeypatch.setattr(
        HauptFenster, "_vor_dem_schliessen_fragen",
        lambda self, namen: QMessageBox.StandardButton.Cancel,
    )
    fenster._sitzungsende_klaeren(_Sitzung())
    _beendet(fenster)
    gefragt = []
    monkeypatch.setattr(
        HauptFenster, "_sicherung_wiederherstellen_fragen",
        lambda self, text: gefragt.append(text) or wiederherstellen,
    )

    danach = hauptfenster_bauen()
    danach.projekt_oeffnen(natter)

    assert len(gefragt) == 1
    assert "„T“" in gefragt[0] and "  main.py" in gefragt[0]
    assert "Uhr" in gefragt[0]
    # Auf die Platte kommt dabei nichts.
    assert (ordner / "main.py").read_text(encoding="utf-8") == "a = 1\n"
    if not wiederherstellen:
        assert not (ordner / "T.natter-sicherung").exists()
        assert danach._ungespeicherte_editoren() == []
        return
    editor = danach._aktueller_editor()
    assert editor.toPlainText() == "a = 42\n"
    assert editor.document().isModified()
    # Der Cursor steht an der ersten geretteten Stelle (Punkt 474).
    assert editor.textCursor().position() == len("a = ")
    assert danach.editor_tabs.tabText(danach.editor_tabs.currentIndex()) == (
        "main.py ●"
    )
    # Ein Bearbeitungsschritt: Strg+Z holt den Stand der Datei zurück,
    # und dann ist nichts mehr ungespeichert.
    editor.undo()
    assert editor.toPlainText() == "a = 1\n"
    assert not editor.document().isModified()
    assert not (ordner / "T.natter-sicherung").exists()


def test_beim_start_kommt_die_frage_ueber_dem_sichtbaren_fenster(
    fenster: HauptFenster, natter: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Punkt 410: mit dem Projekt auf der Befehlszeile stand die Frage
    vor dem Hauptfenster allein auf dem Bildschirm. Sie gehört über
    das Fenster, und das muss da schon zu sehen sein."""
    import sys

    import ide.main as modul
    from tests.conftest import hauptfenster_aufraeumen

    fenster._sicherung_uhr.timeout.emit()
    _beendet(fenster)
    # Sonst fragte der Start erst, ob das Projekt in einem anderen
    # Fenster weiterbearbeitet werden soll.
    sperre.freigeben(natter.parent)

    class _Anzeige:
        def __init__(self, version: str) -> None:
            pass

        def show(self) -> None:
            pass

        def melden(self, text: str) -> None:
            pass

        def finish(self, fenster: object) -> None:
            pass

        def close(self) -> None:
            pass

    gefragt: list[tuple[bool, bool]] = []

    def exec_(frage: QMessageBox) -> int:
        eltern = frage.parentWidget()
        gefragt.append((
            isinstance(eltern, HauptFenster) and eltern is not fenster,
            eltern is not None and eltern.isVisible(),
        ))
        return 0

    monkeypatch.setattr(modul, "Ladeanzeige", _Anzeige)
    monkeypatch.setattr(modul, "integritaet_bestaetigen", lambda f: True)
    monkeypatch.setattr(modul, "fehlerhaken_einrichten", lambda: None)
    monkeypatch.setattr(sys, "argv", ["Natter.exe", str(natter)])
    monkeypatch.setattr(QMessageBox, "exec", exec_)

    _app, gestartet = modul.starten()
    try:
        assert gefragt == [(True, True)], (
            "Die Frage kam ohne sichtbares Hauptfenster dahinter."
        )
    finally:
        hauptfenster_aufraeumen(gestartet)


def test_seither_geaenderte_datei_wird_genannt_und_nicht_ueberschrieben(
    fenster: HauptFenster, hauptfenster_bauen, natter: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wurde die Datei nach der Sicherung auf der Platte geändert, sagt
    die Frage das, und „Speichern“ fragt vor dem Überschreiben."""
    ordner = natter.parent
    monkeypatch.setattr(
        HauptFenster, "_vor_dem_schliessen_fragen",
        lambda self, namen: QMessageBox.StandardButton.Cancel,
    )
    fenster._sitzungsende_klaeren(_Sitzung())
    _beendet(fenster)
    (ordner / "main.py").write_text("a = 7  # anderswo\n", encoding="utf-8")
    gefragt = []
    monkeypatch.setattr(
        HauptFenster, "_sicherung_wiederherstellen_fragen",
        lambda self, text: gefragt.append(text) or True,
    )
    ueberschreiben = []
    monkeypatch.setattr(
        HauptFenster, "_von_aussen_geaendert_fragen",
        lambda self, name: ueberschreiben.append(name) or "abbrechen",
    )

    danach = hauptfenster_bauen()
    danach.projekt_oeffnen(natter)
    danach._editor_speichern(danach._aktueller_editor())

    assert "main.py (seit der Sicherung auf der Platte geändert)" in (
        gefragt[0]
    )
    assert ueberschreiben == ["main.py"]
    assert (ordner / "main.py").read_text(encoding="utf-8") == (
        "a = 7  # anderswo\n"
    )


@pytest.mark.parametrize(
    ("taste", "erwartet"),
    [("Escape", True), ("Return", True), ("Verwerfen", False)],
)
def test_frage_waehlt_wiederherstellen_vor(
    hauptfenster: HauptFenster, taste: str, erwartet: bool,
) -> None:
    """Vorgewählt ist „Wiederherstellen“; auch Escape verliert
    nichts."""
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    def antworten() -> None:
        frage = QApplication.activeModalWidget()
        assert isinstance(frage, QMessageBox)
        assert frage.defaultButton().text() == "Wiederherstellen"
        if taste == "Verwerfen":
            next(
                k for k in frage.buttons() if k.text() == "Verwerfen"
            ).click()
            return
        QTest.keyClick(frage, getattr(Qt.Key, f"Key_{taste}"))

    QTimer.singleShot(0, antworten)

    assert hauptfenster._sicherung_wiederherstellen_fragen("Text") is (
        erwartet
    )


def test_uhr_sichert_und_speichern_raeumt_auf(
    fenster: HauptFenster, tmp_path: Path,
) -> None:
    uhr = fenster._sicherung_uhr
    assert uhr.isActive() and uhr.interval() == _SICHERUNG_TAKT_MS == 120_000

    uhr.timeout.emit()

    assert _gesichert(tmp_path) == {"main.py": "a = 42\n"}
    assert fenster._editor_speichern(fenster._aktueller_editor())
    assert not (tmp_path / "T.natter-sicherung").exists()


def test_eine_pause_nach_dem_tippen_sichert(
    fenster: HauptFenster, tmp_path: Path,
) -> None:
    """Punkt 473: die Sicherung kommt wenige Sekunden nach der letzten
    Änderung, nicht erst mit dem nächsten Takt der Uhr. An der
    installierten 0.4.3 fehlte sie nach einem Beenden über den
    Task-Manager 15 Sekunden nach dem Tippen ganz."""
    bald = fenster._sicherung_bald
    assert bald.isActive() and bald.interval() == 5000

    bald.timeout.emit()

    assert _gesichert(tmp_path) == {"main.py": "a = 42\n"}


def test_projekt_schliessen_mit_verwerfen_raeumt_auf(
    fenster: HauptFenster, tmp_path: Path,
) -> None:
    """Die Antwort beim Schließen gibt `conftest.py` vor: Verwerfen."""
    fenster._sicherung_uhr.timeout.emit()
    assert (tmp_path / "T.natter-sicherung").exists()

    assert fenster.projekt_schliessen()

    assert not (tmp_path / "T.natter-sicherung").exists()
    assert (tmp_path / "main.py").read_text(encoding="utf-8") == "a = 1\n"


def test_diagramm_kommt_mit_zurueck(
    hauptfenster_bauen, natter: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    ordner = natter.parent
    (ordner / "diagramme").mkdir()
    pdiag = ordner / "diagramme" / "klassen.pdiag"
    diagramm_erzeugen("class", pdiag)
    vorher = pdiag.read_text(encoding="utf-8")
    zuerst = hauptfenster_bauen()
    zuerst.projekt_oeffnen(natter)
    fenster = zuerst.diagramm_oeffnen(pdiag)
    fenster.diagramm.daten["name"] = "Geändert"
    fenster._geaendert = True
    monkeypatch.setattr(
        HauptFenster, "_vor_dem_schliessen_fragen",
        lambda self, namen: QMessageBox.StandardButton.Cancel,
    )
    zuerst._sitzungsende_klaeren(_Sitzung())
    _beendet(zuerst)
    monkeypatch.setattr(
        HauptFenster, "_sicherung_wiederherstellen_fragen",
        lambda self, text: True,
    )

    danach = hauptfenster_bauen()
    danach.projekt_oeffnen(natter)

    wieder = danach._offene_diagramme[str(pdiag)]
    assert wieder is not fenster
    assert wieder.diagramm.daten["name"] == "Geändert"
    assert wieder.geaendert
    assert pdiag.read_text(encoding="utf-8") == vorher


@pytest.mark.parametrize(
    "inhalt",
    [
        "{ kaputt",
        json.dumps({"format": "natter-sicherung/9", "saved": "x",
                    "files": []}),
        json.dumps({
            "format": "natter-sicherung/1",
            "saved": "2026-09-29T14:05:00+02:00",
            "files": [{"path": "../fremd.py", "kind": "text",
                       "text": "x", "disk": None}],
        }),
    ],
    ids=["kein_json", "falsches_format", "pfad_nach_draussen"],
)
def test_unlesbare_sicherung_fuehrt_zu_einem_hinweis(
    hauptfenster: HauptFenster, natter: Path,
    monkeypatch: pytest.MonkeyPatch, inhalt: str,
) -> None:
    datei = natter.parent / "T.natter-sicherung"
    datei.write_text(inhalt, encoding="utf-8")
    hinweise = []
    monkeypatch.setattr(
        HauptFenster, "_sicherung_unlesbar_melden",
        lambda self, pfad, grund: hinweise.append((pfad, grund)),
    )
    monkeypatch.setattr(
        HauptFenster, "_sicherung_wiederherstellen_fragen",
        lambda self, text: pytest.fail("Gefragt trotz kaputter Sicherung"),
    )

    assert hauptfenster.projekt_oeffnen(natter) is not None

    assert len(hinweise) == 1 and hinweise[0][0] == datei
    assert hinweise[0][1].endswith(".")
    assert datei.read_text(encoding="utf-8") == inhalt
    assert hauptfenster._ungespeicherte_editoren() == []


def _aendern(fenster: HauptFenster, datei: Path, text: str) -> None:
    editor = fenster.datei_oeffnen(datei)
    editor.selectAll()
    editor.insertPlainText(text)


def test_zwei_fenster_behalten_jedes_seinen_anteil(
    hauptfenster_bauen, natter: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Punkt 406: zwei Fenster am selben Projekt. Keines ersetzt oder
    löscht, was das andere gesichert hat, und ein drittes bietet den
    Text eines noch offenen Fensters nicht an."""
    ordner = natter.parent
    (ordner / "zwei.py").write_text("b = 1\n", encoding="utf-8")
    a = hauptfenster_bauen()
    a.projekt_oeffnen(natter)
    b = hauptfenster_bauen()
    b.projekt_oeffnen(natter)
    _aendern(a, ordner / "main.py", "a = 42\n")
    _aendern(b, ordner / "zwei.py", "b = 2\n")
    beide = {"main.py": "a = 42\n", "zwei.py": "b = 2\n"}

    a._sicherung_uhr.timeout.emit()
    b._sicherung_uhr.timeout.emit()
    a._sicherung_uhr.timeout.emit()
    assert _gesichert(ordner) == beide

    monkeypatch.setattr(
        HauptFenster, "_vor_dem_schliessen_fragen",
        lambda self, namen: QMessageBox.StandardButton.Cancel,
    )
    a._sitzungsende_klaeren(_Sitzung())
    b._sitzungsende_klaeren(_Sitzung())
    assert _gesichert(ordner) == beide

    assert b._editor_speichern(b._aktueller_editor())
    assert _gesichert(ordner) == {"main.py": "a = 42\n"}

    monkeypatch.setattr(
        HauptFenster, "_sicherung_wiederherstellen_fragen",
        lambda self, text: pytest.fail("Text eines offenen Fensters"),
    )
    hauptfenster_bauen().projekt_oeffnen(natter)
    assert _gesichert(ordner) == {"main.py": "a = 42\n"}


@pytest.mark.parametrize(
    "eigenes_konto", [True, False], ids=["eigenes_konto", "fremdes_konto"]
)
def test_sperre_eines_anderen_rechners_und_vorhandene_sicherung(
    hauptfenster: HauptFenster, natter: Path,
    monkeypatch: pytest.MonkeyPatch, eigenes_konto: bool,
) -> None:
    """Punkt 400: am Rechner PC-ANDERER ging Natter vor fünf Minuten
    aus, Sperrdatei und Sicherung liegen noch im Projektordner.

    Im eigenen Konto wird die Sicherung angeboten. Stammt die Sperre
    aus einem fremden Konto, arbeitet dort vermutlich noch jemand; die
    Sicherung wird nicht angeboten, bleibt aber nach dem nächsten
    Uhrschlag dieses Fensters erhalten. Die Sicherung liegt im alten
    Format `natter-sicherung/1` vor, das keine Herkunft kennt."""
    ordner = natter.parent
    datei = ordner / "T.natter-sicherung"
    datei.write_text(json.dumps({
        "format": "natter-sicherung/1",
        "saved": "2026-09-29T14:05:00+02:00",
        "files": [{"path": "main.py", "kind": "text",
                   "text": "gesichert = 1\n", "disk": None}],
    }), encoding="utf-8")
    konto = sperre.kontoname() if eigenes_konto else "jemand.anders"
    (ordner / sperre.SPERRDATEI).write_text(
        f"4712 0\nrechner=PC-ANDERER\nkonto={konto}\n"
        f"erneuert={int(time.time()) - 300}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        HauptFenster, "_projekt_schon_offen_melden",
        lambda self, name, besitzer=None: None,
    )
    monkeypatch.setattr(
        HauptFenster, "_sicherung_unlesbar_melden",
        lambda self, pfad, grund: pytest.fail(grund),
    )
    gefragt = []
    monkeypatch.setattr(
        HauptFenster, "_sicherung_wiederherstellen_fragen",
        lambda self, text: gefragt.append(text) or True,
    )

    hauptfenster.projekt_oeffnen(natter)

    if eigenes_konto:
        assert len(gefragt) == 1
        editor = hauptfenster._aktueller_editor()
        assert editor.toPlainText() == "gesichert = 1\n"
        assert editor.document().isModified()
        return
    assert gefragt == []
    (ordner / "zwei.py").write_text("b = 1\n", encoding="utf-8")
    _aendern(hauptfenster, ordner / "zwei.py", "neu = 2\n")
    hauptfenster._sicherung_uhr.timeout.emit()
    assert sorted(
        e.text for e in sicherung.lesen(datei).eintraege
    ) == ["gesichert = 1\n", "neu = 2\n"]


def test_sicherung_bleibt_aus_explorer_abgabe_export_und_kopie(
    qtbot, natter: Path, tmp_path: Path,
) -> None:
    from ide.export.exporter import _daten_dateien_des_projekts
    from ide.shell.explorer import PFAD_ROLLE, ProjektExplorer
    from ide.shell.startbild import _NICHT_MITKOPIEREN

    ordner = natter.parent
    datei = ordner / "T.natter-sicherung"
    datei.write_text("{}", encoding="utf-8")
    (ordner / "noten.csv").write_text("a;b\n", encoding="utf-8")
    projekt = Projekt.laden(natter)

    explorer = ProjektExplorer()
    qtbot.addWidget(explorer)
    explorer.projekt_anzeigen(projekt)
    gezeigt = [
        explorer.dateien_gruppe.child(i).data(0, PFAD_ROLLE)
        for i in range(explorer.dateien_gruppe.childCount())
    ]
    assert gezeigt == [str(ordner / "noten.csv")]

    abgabe = tmp_path / "abgabe.zip"
    zip_schreiben(ordner, "T", abgabe)
    with zipfile.ZipFile(abgabe) as archiv:
        namen = archiv.namelist()
    abgabe.unlink()
    assert "T/noten.csv" in namen
    assert "T/T.natter-sicherung" not in namen

    assert _daten_dateien_des_projekts(projekt) == [ordner / "noten.csv"]

    assert _NICHT_MITKOPIEREN(str(ordner), ["T.natter-sicherung", "a.py"]) == {
        "T.natter-sicherung"
    }


def test_geschriebene_sicherung_passt_zum_schema(tmp_path: Path) -> None:
    schema = json.loads(
        (_WURZEL / "schemas" / "natter-sicherung.schema.json").read_text(
            encoding="utf-8"
        )
    )
    jsonschema.Draft202012Validator.check_schema(schema)
    ziel = sicherung.pfad_fuer(tmp_path, "Ampel")
    eintraege = [
        sicherung.Eintrag("u_main.py", "text", "a = 1\n", "123:6"),
        sicherung.Eintrag("diagramme/k.pdiag", "diagram", "{}\n", ""),
    ]

    herkunft = sicherung.Herkunft("PC-R12", "anna", 4712, 99, "a1")

    sicherung.schreiben(ziel, eintraege, herkunft)

    assert ziel.name == "Ampel.natter-sicherung"
    daten = json.loads(ziel.read_text(encoding="utf-8"))
    jsonschema.validate(daten, schema)
    assert daten["format"] == "natter-sicherung/2"
    teil = daten["parts"][0]
    assert teil["window"] == {
        "computer": "PC-R12", "account": "anna", "pid": 4712,
        "start": 99, "id": "a1",
    }
    assert teil["files"][0]["disk"] == {"mtime_ns": 123, "size": 6}
    assert teil["files"][1]["disk"] is None
    gelesen = sicherung.lesen(ziel)
    assert list(gelesen.eintraege) == eintraege
    assert gelesen.anteile[0].herkunft == herkunft
    # Das alte Format passt weiter zum Schema und wird gelesen.
    alt = {
        "format": "natter-sicherung/1",
        "saved": "2026-09-29T14:05:00+02:00",
        "files": teil["files"],
    }
    jsonschema.validate(alt, schema)
    ziel.write_text(json.dumps(alt), encoding="utf-8")
    gelesen = sicherung.lesen(ziel)
    assert list(gelesen.eintraege) == eintraege
    assert gelesen.anteile[0].herkunft is None
