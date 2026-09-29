"""Eine Aufgabe aus einem Tauschordner öffnen und als eigene Kopie
bearbeiten (Punkte 361, 362, 364, 390).

Der Ablauf hatte in einer Freigabe zehn Befunde. Zuletzt: im
beschreibbaren Tauschordner arbeitete die erste Schülerin im Original
der Lehrkraft (361), Zurücksetzen bei einer gesperrten Datei ließ die
Kopie ohne Projektdatei zurück (362), und über Laufwerksbuchstabe und
Netzpfad geöffnet, wurde die eigene Kopie nicht wiedererkannt (364).

Seit Punkt 390 geht jeder Projektordner, in dem Natter schreiben
darf, an seinem Ort auf; die Kopie kommt nur noch ohne Schreibrecht.
Ein Tauschordner ist hier deshalb eine Freigabe, auf der nur die
Lehrkraft schreiben darf, nachgestellt über die Schreibprobe
(`ordner_beschreibbar`). Mehrere Konten werden über einen eigenen
Dokumente-Ordner je Konto nachgestellt (`ide.pfade.dokumente_ordner`),
eine gesperrte Datei über
`CreateFile` ohne Freigabe wie bei Excel, ein verbundenes Laufwerk über
ein `Path.resolve`, das einen Ordner in einen anderen übersetzt. An
Windows selbst ändert keiner der Tests etwas.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox

import ide.pfade
import ide.shell.hauptfenster as hauptfenster_modul
from ide.shell import startbild
from ide.shell.hauptfenster import HauptFenster
from ide.shell.startbild import (
    QUELLDATEI,
    aufgabe_geaendert,
    aufgabe_kopieren,
    beispiel_kopieren,
    vorhandene_aufgabenkopie,
    zuletzt_merken,
)

_BEISPIELE = Path(__file__).resolve().parent.parent / "beispielprojekte"


def _aufgabe(ordner: Path, name: str = "Ampel") -> Path:
    ordner.mkdir(parents=True)
    (ordner / "main.py").write_text("import u_main\n", encoding="utf-8")
    (ordner / "u_main.py").write_text("x = 1\n", encoding="utf-8")
    datei = ordner / f"{name}.natter"
    datei.write_text(json.dumps({
        "format": "natter-project/1", "name": name,
        "type": "console", "main": "main.py",
    }), encoding="utf-8")
    return datei


_ECHTE_SCHREIBPROBE = hauptfenster_modul.ordner_beschreibbar

#: Die Frage nach einer geänderten Aufgabe, bevor `tests/conftest.py`
#: sie für jeden Test durch eine feste Antwort ersetzt.
_ECHTE_FRAGE = HauptFenster._geaenderte_aufgabe_fragen


def _schreibrecht_setzen(
    monkeypatch: pytest.MonkeyPatch, konto: str | None
) -> None:
    """In jeden Ordner, dessen Name mit „Tausch“ beginnt, darf nur die
    Lehrkraft schreiben, wie in eine Freigabe, auf der die Klasse nur
    lesen darf. Alles andere prüft die echte Schreibprobe. `konto` ist
    das angemeldete Konto."""

    def beschreibbar(ordner: Path | str) -> bool:
        if any(teil.startswith("Tausch") for teil in Path(ordner).parts):
            return konto == "lehrkraft"
        return _ECHTE_SCHREIBPROBE(ordner)

    monkeypatch.setattr(
        hauptfenster_modul, "ordner_beschreibbar", beschreibbar
    )


@pytest.fixture(autouse=True)
def _tausch_nur_zum_lesen(monkeypatch: pytest.MonkeyPatch) -> None:
    _schreibrecht_setzen(monkeypatch, None)


def _konto(monkeypatch: pytest.MonkeyPatch, wurzel: Path, name: str) -> Path:
    """Stellt das Konto `name` ein: ab jetzt ist sein Dokumente-Ordner
    der von Natter, und in den Tauschordner darf es nur schreiben,
    wenn es die Lehrkraft ist."""
    dokumente = wurzel / name / "Dokumente"
    monkeypatch.setattr(ide.pfade, "dokumente_ordner", lambda: dokumente)
    _schreibrecht_setzen(monkeypatch, name)
    return dokumente / "Natter"


def _fragen(fenster, antwort: bool) -> list[tuple[str, str, str]]:  # noqa: ANN001
    """Beantwortet das Kopierangebot dieses Fensters immer mit
    `antwort` und sammelt Titel, Text und zweiten Knopf."""
    gestellt: list[tuple[str, str, str]] = []

    def anbieten(titel, text, nein, **_kw):  # noqa: ANN001, ANN003, ANN202
        gestellt.append((titel, text, nein))
        return antwort

    fenster._kopie_anbieten = anbieten
    return gestellt


def _speichern(fenster, datei: Path, text: str) -> None:  # noqa: ANN001
    editor = fenster.datei_oeffnen(datei)
    editor.setPlainText(text)
    editor.document().setModified(True)
    assert fenster.alle_speichern()


def _lesen(datei: Path) -> str:
    return datei.read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "ort", ["heimatlaufwerk", "klassenordner", "downloads"]
)
def test_ein_kopierter_projektordner_geht_ohne_frage_an_seinem_ort_auf(
    ort: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster,  # noqa: ANN001
) -> None:
    """Punkte 390, 392 und 393: der Ordner gehört laut Windows einem
    anderen Konto, etwa nach einem Serverumzug mit `robocopy`, auf
    einem NAS oder nach dem Austeilen durch eine Schulsoftware, und
    Natter darf darin schreiben. Er geht bei jedem Öffnen ohne Frage
    an seinem Ort auf, auch unter „Downloads“, und unter
    `Dokumente\\Natter` entsteht keine Kopie. Bis 0.4.0 kam die Frage
    „Aufgabe öffnen“ mit vorgewählter Kopie."""
    heim = tmp_path / "H"
    downloads = tmp_path / "a" / "Downloads"
    wurzel = {
        "heimatlaufwerk": heim / "Informatik",
        "klassenordner": tmp_path / "Klasse7b",
        "downloads": downloads,
    }[ort]
    monkeypatch.setenv("HOMESHARE", str(heim))
    # Was bis 0.4.0 den Ausschlag gab: ein fremder Besitzer und der
    # Download-Ordner.
    monkeypatch.setattr(
        ide.pfade, "gehoert_dem_konto", lambda _pfad: False,
        raising=False,
    )
    monkeypatch.setattr(
        ide.pfade, "downloads_ordner", lambda: downloads, raising=False
    )
    natter = _konto(monkeypatch, tmp_path, "a")
    datei = _aufgabe(wurzel / "Ampel")
    gestellt = _fragen(hauptfenster, True)

    for _mal in range(2):
        projekt = hauptfenster.projekt_oeffnen_gemeldet(datei)
        assert projekt.ordner.resolve() == datei.parent.resolve()
        assert hauptfenster.projekt_schliessen()

    assert gestellt == []
    assert not natter.exists()


def test_beim_kopieren_zeigt_natter_wartezeiger_und_statusmeldung(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 398: eine große Aufgabe zu kopieren dauert Sekunden, und
    das Fenster stand dabei ohne Hinweis still. Beim Anlegen, beim
    Zurücksetzen und beim Ersetzen der Kopie steht jetzt, solange
    kopiert wird, der Wartezeiger, und die Statuszeile sagt, was
    geschieht. Danach ist der Wartezeiger wieder weg."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication

    datei = _aufgabe(tmp_path / "Tausch" / "Ampel")
    _konto(monkeypatch, tmp_path, "a")
    _fragen(hauptfenster, True)
    gesehen: list[tuple[str, object, str]] = []

    def beobachten(name: str) -> None:
        echt = getattr(hauptfenster_modul, name)

        def arbeit(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
            zeiger = QApplication.overrideCursor()
            gesehen.append((
                name, zeiger.shape() if zeiger is not None else None,
                hauptfenster.statusBar().currentMessage(),
            ))
            return echt(*args, **kwargs)

        monkeypatch.setattr(hauptfenster_modul, name, arbeit)

    beobachten("aufgabe_kopieren")
    beobachten("aufgabe_zuruecksetzen")

    hauptfenster.projekt_oeffnen_gemeldet(datei)
    assert hauptfenster.beispiel_zuruecksetzen_nachfragen(bestaetigt=True)
    zeit = (datei.parent / "u_main.py").stat().st_mtime + 60
    os.utime(datei.parent / "u_main.py", (zeit, zeit))
    hauptfenster._geaenderte_aufgabe_fragen = (
        lambda _kopie, _text="", _nein=None: "ersetzen"
    )
    hauptfenster.projekt_oeffnen_gemeldet(datei)

    assert [name for name, _zeiger, _meldung in gesehen] == [
        "aufgabe_kopieren", "aufgabe_zuruecksetzen", "aufgabe_zuruecksetzen",
    ]
    for _name, zeiger, meldung in gesehen:
        assert zeiger == Qt.CursorShape.WaitCursor
        assert meldung.startswith("„Ampel“ wird") and "kopiert" in meldung
    assert QApplication.overrideCursor() is None


def test_eine_aufgabe_im_tauschordner_nur_zum_lesen_wird_als_kopie_angeboten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster,  # noqa: ANN001
) -> None:
    """Die Lehrkraft verteilt die Aufgabe über einen Ordner, in dem die
    Klasse nur lesen darf. Nach „Eigene Kopie öffnen“ landet die Arbeit
    von A in ihrer Kopie. Das Original bleibt unverändert, und für B,
    die schon vorher kopiert hatte, gilt die Aufgabe nicht als
    geändert."""
    datei = _aufgabe(tmp_path / "Tausch6" / "Ampel")
    kopie_b = aufgabe_kopieren(
        datei, _konto(monkeypatch, tmp_path, "b")
    ).parent
    natter_a = _konto(monkeypatch, tmp_path, "a")
    gestellt = _fragen(hauptfenster, True)

    projekt = hauptfenster.projekt_oeffnen_gemeldet(datei)

    assert len(gestellt) == 1
    titel, text, nein = gestellt[0]
    assert titel == "Ordner ohne Schreibrecht" and nein == "Nur ansehen"
    assert str(natter_a) in text
    assert projekt.ordner.resolve() == (natter_a / "Ampel").resolve()
    _speichern(hauptfenster, natter_a / "Ampel" / "u_main.py", "x = 2\n")
    assert _lesen(natter_a / "Ampel" / "u_main.py") == "x = 2\n"
    assert _lesen(datei.parent / "u_main.py") == "x = 1\n"
    assert not aufgabe_geaendert(kopie_b)


@contextlib.contextmanager
def _wie_in_excel_offen(datei: Path) -> Iterator[None]:
    """Hält `datei` offen, ohne sie anderen freizugeben, so wie Excel
    eine CSV."""
    import _winapi

    griff = _winapi.CreateFile(
        str(datei), _winapi.GENERIC_READ, 0, 0, _winapi.OPEN_EXISTING, 0, 0,
    )
    try:
        yield
    finally:
        _winapi.CloseHandle(griff)


def _stand(ordner: Path) -> dict[str, bytes]:
    """Jede Datei der Kopie mit ihrem Inhalt, ohne die Sperrdatei."""
    return {
        datei.relative_to(ordner).as_posix(): datei.read_bytes()
        for datei in ordner.rglob("*")
        if datei.is_file() and datei.name != ".natter-sperre"
    }


@pytest.mark.parametrize(
    "weg", ["Aufgabe zurücksetzen", "Beispiel zurücksetzen", "Kopie ersetzen"]
)
def test_eine_gesperrte_datei_laesst_die_kopie_unveraendert(
    weg: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 362: `daten\\wetter.csv` der Kopie ist in Excel offen.
    Zurücksetzen und „Kopie ersetzen“ scheitern mit einer Meldung, die
    die Datei nennt, und die Kopie steht danach unverändert da, samt
    Projektdatei und `.natter-quelle`. Nach dem Schließen in Excel
    geht es."""
    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda _e, titel, text, *_a: meldungen.append(
            f"{titel}\n{text}"
        )),
    )
    tausch = tmp_path / "Tausch2" / "Wetter"
    shutil.copytree(_BEISPIELE / "07_CsvAuswertung", tausch)
    if weg == "Beispiel zurücksetzen":
        projektdatei = beispiel_kopieren(
            _BEISPIELE / "07_CsvAuswertung" / "07_CsvAuswertung.natter"
        )
    else:
        projektdatei = aufgabe_kopieren(
            tausch / "07_CsvAuswertung.natter", ide.pfade.natter_ordner()
        )
    kopie = projektdatei.parent
    hauptfenster.projekt_oeffnen(projektdatei)
    (kopie / "u_main.py").write_text("meine Arbeit\n", encoding="utf-8")
    vorher = _stand(kopie)

    def zuruecksetzen() -> object:
        if weg != "Kopie ersetzen":
            return hauptfenster.beispiel_zuruecksetzen_nachfragen(
                bestaetigt=True
            )
        hauptfenster._geaenderte_aufgabe_fragen = (
            lambda _kopie, _text="", _nein=None: "ersetzen"
        )
        _fragen(hauptfenster, True)
        return hauptfenster.projekt_oeffnen_gemeldet(
            tausch / "07_CsvAuswertung.natter"
        )

    if weg == "Kopie ersetzen":
        # Die Lehrkraft berichtigt die Aufgabe.
        zeit = (tausch / "u_main.py").stat().st_mtime + 60
        os.utime(tausch / "u_main.py", (zeit, zeit))

    with _wie_in_excel_offen(kopie / "daten" / "wetter.csv"):
        ergebnis = zuruecksetzen()

    assert not ergebnis
    assert _stand(kopie) == vorher
    assert any(kopie.glob("*.natter"))
    if weg != "Beispiel zurücksetzen":
        assert QUELLDATEI in vorher
    assert len(meldungen) == 1, meldungen
    assert str(Path("daten", "wetter.csv")) in meldungen[0]
    assert "anderen Programm" in meldungen[0]
    assert "Netzlaufwerk" not in meldungen[0]
    assert [p.name for p in kopie.parent.iterdir()] == [kopie.name]

    assert zuruecksetzen()
    assert _lesen(kopie / "u_main.py") != "meine Arbeit\n"
    assert hauptfenster.projekt.ordner.resolve() == kopie.resolve()


def test_laufwerk_und_netzpfad_ergeben_dieselbe_kopie(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Punkt 364: `K:` ist mit `\\\\server\\tausch` verbunden, und
    `resolve()` macht aus dem einen den anderen. Nachgestellt mit zwei
    gleichen Ordnern `K` und `Server\\tausch` und einem `resolve`, das
    `K` in `Server\\tausch` übersetzt. Die über `K` angelegte Kopie wird
    für den Eintrag in „Zuletzt geöffnet“ wiedergefunden, und es
    entsteht keine „Ampel 2“."""
    server = tmp_path / "Server" / "tausch"
    _aufgabe(server / "Ampel")
    laufwerk = tmp_path / "K"
    shutil.copytree(server, laufwerk)
    echt = Path.resolve
    ziel_k, ziel_server = echt(laufwerk), echt(server)

    def resolve(self: Path, strict: bool = False) -> Path:
        pfad = echt(self, strict)
        if pfad.is_relative_to(ziel_k):
            return ziel_server / pfad.relative_to(ziel_k)
        return pfad

    monkeypatch.setattr(Path, "resolve", resolve)
    natter = ide.pfade.natter_ordner()
    ueber_k = laufwerk / "Ampel" / "Ampel.natter"
    einstellungen = QSettings(
        str(tmp_path / "einstellungen.ini"), QSettings.Format.IniFormat
    )

    eintrag = zuletzt_merken(einstellungen, ueber_k)[0]
    kopie = aufgabe_kopieren(ueber_k, natter)

    assert vorhandene_aufgabenkopie(eintrag, natter) == kopie
    assert aufgabe_kopieren(eintrag, natter) == kopie
    assert aufgabe_kopieren(ueber_k, natter) == kopie
    assert sorted(p.name for p in natter.iterdir()) == ["Ampel"]
    assert startbild.aufgabe_original(kopie.parent) is not None


def test_eine_klasse_arbeitet_an_derselben_aufgabe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster_bauen,  # noqa: ANN001
) -> None:
    """Der ganze Ablauf: die Lehrkraft bearbeitet ihre Aufgabe im
    Tauschordner, in dem nur sie schreiben darf, ohne Frage, drei
    Schülerinnen öffnen sie
    nacheinander, zwei davon gleichzeitig. Jede bekommt eine eigene
    Kopie mit dem Stand der Lehrkraft, keine sieht die Arbeit einer
    anderen, und in der nächsten Stunde geht die eigene Kopie wieder
    auf. Eine berichtigte Aufgabe wird angekündigt und auf Wunsch
    nicht übernommen."""
    datei = _aufgabe(tmp_path / "Tausch" / "Ampel")
    unit = datei.parent / "u_main.py"

    _konto(monkeypatch, tmp_path, "lehrkraft")
    lehrkraft = hauptfenster_bauen()
    gestellt = _fragen(lehrkraft, False)
    projekt = lehrkraft.projekt_oeffnen_gemeldet(datei)
    assert gestellt == []
    assert projekt.ordner.resolve() == datei.parent.resolve()
    _speichern(lehrkraft, unit, "x = 1\n# Aufgabe: Ampel\n")
    assert lehrkraft.projekt_schliessen()

    kopien: dict[str, Path] = {}
    fenster = {}
    for name in ("a", "b", "c"):
        natter = _konto(monkeypatch, tmp_path, name)
        fenster[name] = hauptfenster_bauen()
        _fragen(fenster[name], True)
        projekt = fenster[name].projekt_oeffnen_gemeldet(datei)
        kopien[name] = natter / "Ampel"
        assert projekt.ordner.resolve() == kopien[name].resolve()
        assert "# Aufgabe: Ampel" in _lesen(kopien[name] / "u_main.py")
        if name == "a":
            # A schreibt, während B und C noch öffnen.
            _speichern(
                fenster["a"], kopien["a"] / "u_main.py",
                "x = 1\n# Aufgabe: Ampel\nlicht = 'rot'\n",
            )
        if name == "b":
            assert fenster["b"].projekt_schliessen()

    assert "licht" not in _lesen(unit)
    for name in ("b", "c"):
        assert "licht" not in _lesen(kopien[name] / "u_main.py")
        assert not aufgabe_geaendert(kopien[name])

    # Nächste Stunde: A öffnet wieder über den Tauschordner.
    _konto(monkeypatch, tmp_path, "a")
    assert fenster["a"].projekt_schliessen()
    gestellt = _fragen(fenster["a"], True)
    fenster["a"].projekt_oeffnen_gemeldet(datei)
    assert gestellt[0][0] == "Eigene Kopie vorhanden"
    assert "licht" in _lesen(kopien["a"] / "u_main.py")
    assert not (kopien["a"].parent / "Ampel 2").exists()

    # Die Lehrkraft berichtigt die Aufgabe; A behält ihren Stand.
    zeit = unit.stat().st_mtime + 60
    os.utime(unit, (zeit, zeit))
    gefragt: list[Path] = []
    fenster["a"]._geaenderte_aufgabe_fragen = (
        lambda kopie, _text="", _nein=None: (
            gefragt.append(kopie) or "behalten"
        )
    )
    fenster["a"].projekt_oeffnen_gemeldet(datei)
    assert gefragt == [kopien["a"]]
    assert "licht" in _lesen(kopien["a"] / "u_main.py")


class _NeuesProjekt:
    """Steht für den Dialog „Neues Projekt“ und gibt Vorlage, Ordner
    und Namen vor."""

    def __init__(self, ordner: Path, name: str) -> None:
        self._werte = ("console", ordner, name)

    def exec(self) -> int:
        from PySide6.QtWidgets import QDialog

        return QDialog.DialogCode.Accepted

    def werte(self) -> tuple[str, Path, str]:
        return self._werte


def test_ein_eigenes_projekt_auf_dem_heimatlaufwerk_geht_ohne_frage_auf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 379: ein mit „Neues Projekt“ auf dem Heimatlaufwerk
    angelegtes Projekt geht auch an einem anderen Rechner, also mit
    leeren Einstellungen, ohne Frage an seinem Ort auf. Die Aufgabe
    der Lehrkraft im Tauschordner nur zum Lesen fragt dagegen bei
    jedem Öffnen; eine Antwort merkt sich Natter nicht (Punkt 361)."""
    _konto(monkeypatch, tmp_path, "a")
    gestellt = _fragen(hauptfenster, False)
    heimat = tmp_path / "H" / "Informatik" / "Ampel"
    monkeypatch.setattr(
        "ide.shell.hauptfenster.NeuesProjektDialog",
        lambda parent=None: _NeuesProjekt(heimat, "Ampel"),
    )
    hauptfenster._neues_projekt_dialog()
    assert hauptfenster.projekt_schliessen()
    # Stunde 2 an einem anderen Rechner: die Einstellungen sind leer.
    hauptfenster._design_einstellungen.clear()
    aufgabe = _aufgabe(tmp_path / "Tausch" / "Blinker", "Blinker")

    hauptfenster.projekt_oeffnen_gemeldet(aufgabe)
    projekt = hauptfenster.projekt_oeffnen_gemeldet(heimat / "Ampel.natter")
    assert projekt.ordner.resolve() == heimat.resolve()
    hauptfenster.projekt_oeffnen_gemeldet(aufgabe)

    assert [titel for titel, _text, _nein in gestellt] == [
        "Ordner ohne Schreibrecht", "Ordner ohne Schreibrecht",
    ]
    assert hauptfenster.projekt.ordner.resolve() == aufgabe.parent.resolve()
    assert not (ide.pfade.natter_ordner() / "Ampel").exists()


def test_eine_entpackte_abgabe_oeffnet_die_lehrkraft_an_ihrem_ort(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster_bauen,  # noqa: ANN001
) -> None:
    """Punkt 381: eine Schülerin gibt mit „Als ZIP speichern …“ ab, die
    Lehrkraft entpackt die Abgabe unter „Downloads“ und öffnet sie.
    Die entpackten Dateien gehören ihr; es kommt keine Frage, keine
    Kopie, und von einer verteilten Aufgabe ist nirgends die Rede."""
    import zipfile

    natter_anna = _konto(monkeypatch, tmp_path, "anna")
    _aufgabe(natter_anna / "Aufgabe3", "Aufgabe3")
    anna = hauptfenster_bauen()
    anna.projekt_oeffnen(natter_anna / "Aufgabe3" / "Aufgabe3.natter")
    abgabe = tmp_path / "Abgaben" / "Aufgabe3 - anna.zip"
    abgabe.parent.mkdir()
    assert anna.projekt_als_zip(abgabe)

    natter_lehrkraft = _konto(monkeypatch, tmp_path, "lehrkraft")
    downloads = tmp_path / "lehrkraft" / "Downloads" / "Aufgabe3 - anna"
    with zipfile.ZipFile(abgabe) as zip_datei:
        zip_datei.extractall(downloads)
    projektdatei = next(downloads.rglob("*.natter"))
    lehrkraft = hauptfenster_bauen()
    gestellt = _fragen(lehrkraft, True)
    texte: list[str] = []
    for art in ("information", "warning", "question"):
        monkeypatch.setattr(
            QMessageBox, art,
            staticmethod(lambda _e, _titel, text, *_a, **_k: (
                texte.append(text) or QMessageBox.StandardButton.Ok
            )),
        )

    projekt = lehrkraft.projekt_oeffnen_gemeldet(projektdatei)

    assert gestellt == []
    assert projekt.ordner.resolve() == projektdatei.parent.resolve()
    assert not natter_lehrkraft.exists()
    assert not any("verteilte Aufgabe" in text for text in texte)


def test_nach_berichtigter_aufgabe_kommt_eine_frage_und_nichts_geht_verloren(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 380: nach einer berichtigten Aufgabe kommt beim Öffnen
    genau eine Frage, vorgewählt ist „Eigene Kopie öffnen“. Nach dieser
    Wahl fragt Natter zu demselben Stand nicht wieder nach der
    Änderung. Ändert die Lehrkraft die Aufgabe noch einmal und wird
    die Kopie ersetzt, liegt die Arbeit danach in „Ampel (vorher)“."""
    datei = _aufgabe(tmp_path / "Tausch" / "Ampel")
    natter = _konto(monkeypatch, tmp_path, "a")
    kopie = natter / "Ampel"
    gestellt = _fragen(hauptfenster, True)
    geaendert: list[str] = []
    antworten: list[str] = []

    def fragen(_kopie, text="", nein=None) -> str:  # noqa: ANN001
        geaendert.append(text)
        return antworten.pop(0)

    hauptfenster._geaenderte_aufgabe_fragen = fragen
    hauptfenster.projekt_oeffnen_gemeldet(datei)
    _speichern(hauptfenster, kopie / "u_main.py", "meine Arbeit\n")

    def berichtigen(text: str) -> None:
        (datei.parent / "u_main.py").write_text(text, encoding="utf-8")
        zeit = (datei.parent / "u_main.py").stat().st_mtime + 60
        os.utime(datei.parent / "u_main.py", (zeit, zeit))

    berichtigen("x = 2\n")
    gestellt.clear()
    antworten.append("behalten")
    hauptfenster.projekt_oeffnen_gemeldet(datei)
    assert len(gestellt) + len(geaendert) == 1
    assert _lesen(kopie / "u_main.py") == "meine Arbeit\n"

    gestellt.clear()
    geaendert.clear()
    hauptfenster.projekt_oeffnen_gemeldet(datei)
    assert geaendert == []
    assert [titel for titel, _text, _nein in gestellt] == [
        "Eigene Kopie vorhanden"
    ]

    berichtigen("x = 3\n")
    antworten.append("ersetzen")
    hauptfenster.projekt_oeffnen_gemeldet(datei)
    vorher = natter / "Ampel (vorher)"
    assert _lesen(kopie / "u_main.py") == "x = 3\n"
    assert _lesen(vorher / "u_main.py") == "meine Arbeit\n"
    assert not (vorher / QUELLDATEI).exists()
    assert "Ampel (vorher)" in hauptfenster.statusBar().currentMessage()

    # Das Fenster selbst: der sichere Knopf ist vorgewählt, und der
    # Ordner für den bisherigen Stand steht in der Frage.
    gezeigt: list[tuple[str, str]] = []

    def zeigen(fenster: QMessageBox) -> int:
        gezeigt.append((fenster.text(), fenster.defaultButton().text()))
        return 0

    monkeypatch.setattr(QMessageBox, "exec", zeigen)
    wahl = _ECHTE_FRAGE(hauptfenster, kopie, "", "Original öffnen")
    assert wahl == "behalten"
    assert gezeigt[0][1] == "Eigene Kopie öffnen"
    assert "Ampel (vorher 2)" in gezeigt[0][0]


def test_im_pruefungsmodus_laesst_sich_die_kopie_einer_aufgabe_zuruecksetzen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 371: in einer Klausur wird die Aufgabe über einen
    Tauschordner verteilt. Der Eintrag zum Zurücksetzen hing im Menü
    der Beispiele, das im Prüfungsmodus als Ganzes gesperrt ist. Er
    steht jetzt unter „Projekt“ und in der Befehlspalette, geht bei
    der Kopie einer Aufgabe und bleibt bei einem Beispiel gesperrt."""
    import pcl.pruefungsmodus as modul
    from ide.shell.befehlspalette import Befehlspalette

    ini = QSettings(str(tmp_path / "pruefung.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr(modul, "einstellungen", lambda: ini)
    monkeypatch.setattr(
        QMessageBox, "question",
        staticmethod(lambda *_a: QMessageBox.StandardButton.Yes),
    )
    datei = _aufgabe(tmp_path / "Klausur" / "Ampel")
    kopie = aufgabe_kopieren(datei, ide.pfade.natter_ordner())
    modul.starten(ini)
    hauptfenster._pruefungsmodus_nachfuehren()
    hauptfenster.projekt_oeffnen(kopie)
    (kopie.parent / "u_main.py").write_text("kaputt\n", encoding="utf-8")

    palette = Befehlspalette(hauptfenster.aktionen)
    palette._filtern("original")
    assert palette.gefilterte_zeilen() == [
        "Projekt → Auf Original zurücksetzen …"
    ]
    hauptfenster.aktionen["projekt.auf_original_zuruecksetzen"].qaction.trigger()
    assert _lesen(kopie.parent / "u_main.py") == "x = 1\n"

    beispiel = beispiel_kopieren(
        _BEISPIELE / "01_Begruessung" / "01_Begruessung.natter"
    )
    hauptfenster.projekt_oeffnen(beispiel)
    assert not hauptfenster._beispiel_zuruecksetzen_eintrag.isEnabled()
    assert not hauptfenster.beispiel_zuruecksetzen_nachfragen(bestaetigt=True)


def test_zuruecksetzen_schliesst_die_diagrammfenster_der_kopie(
    tmp_path: Path, hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 374: ein geändertes Diagrammfenster der Kopie blieb nach
    dem Zurücksetzen offen, und sein Speichern schrieb den alten Stand
    in die eben zurückgesetzte Kopie."""
    tausch = tmp_path / "Tausch" / "Konto"
    shutil.copytree(_BEISPIELE / "06_Kontoverwaltung", tausch)
    kopie = aufgabe_kopieren(
        tausch / "06_Kontoverwaltung.natter", ide.pfade.natter_ordner()
    ).parent
    hauptfenster.projekt_oeffnen(next(kopie.glob("*.natter")))
    pdiag = kopie / "diagramme" / "konto_klassen.pdiag"
    fenster = hauptfenster.diagramm_oeffnen(pdiag)
    fenster.diagramm.daten["name"] = "alter Stand"
    fenster._geaendert = True

    assert hauptfenster.beispiel_zuruecksetzen_nachfragen(bestaetigt=True)

    assert not [
        schluessel for schluessel in hauptfenster._offene_diagramme
        if Path(schluessel).resolve().is_relative_to(kopie.resolve())
    ]
    assert "konto_klassen.pdiag" not in hauptfenster._ungespeicherte_namen()
    assert pdiag.read_bytes() == (
        tausch / "diagramme" / "konto_klassen.pdiag"
    ).read_bytes()


def test_scheitert_der_rueckweg_bleiben_die_alten_dateien_erhalten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 375: `u_1.py` ist gesperrt, und beim Zurückschieben der
    schon verschobenen `u_0.py` prüft sie gerade ein Virenscanner. Das
    Aufräumen löschte danach den Zwischenordner samt `u_0.py`. Jetzt
    bleibt er stehen, und die Meldung nennt ihn."""
    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda _e, titel, text, *_a: meldungen.append(
            f"{titel}\n{text}"
        )),
    )
    datei = _aufgabe(tmp_path / "Tausch" / "Ampel")
    kopie = aufgabe_kopieren(datei, ide.pfade.natter_ordner()).parent
    for nummer in range(3):
        (kopie / f"u_{nummer}.py").write_text(
            f"meine Arbeit {nummer}\n", encoding="utf-8"
        )
    hauptfenster.projekt_oeffnen(next(kopie.glob("*.natter")))
    echt = os.rename

    def umbenennen(von, nach) -> None:  # noqa: ANN001
        von = Path(von)
        in_kopie = von.parent.resolve() == kopie.resolve()
        if (von.name == "u_1.py" and in_kopie) or (
            von.name == "u_0.py" and not in_kopie
        ):
            raise PermissionError(13, "Zugriff verweigert")
        echt(von, nach)

    monkeypatch.setattr(os, "rename", umbenennen)
    assert not hauptfenster.beispiel_zuruecksetzen_nachfragen(
        bestaetigt=True
    )
    monkeypatch.setattr(os, "rename", echt)

    orte = [kopie / "u_0.py", *kopie.parent.glob(".natter-neu-*/alt/u_0.py")]
    gefunden = [ort for ort in orte if ort.is_file()]
    assert gefunden, "u_0.py ist verloren"
    assert _lesen(gefunden[0]) == "meine Arbeit 0\n"
    assert _lesen(kopie / "u_1.py") == "meine Arbeit 1\n"
    assert len(meldungen) == 1, meldungen
    if gefunden[0].parent != kopie:
        assert str(gefunden[0].parent) in meldungen[0]


def _viele_dateien(ordner: Path, anzahl: int = 300) -> None:
    """Legt den Unterordner `daten` mit `anzahl` kleinen Dateien an."""
    (ordner / "daten").mkdir()
    for nummer in range(anzahl):
        (ordner / "daten" / f"d{nummer:04}.txt").write_text(
            f"{nummer}\n", encoding="utf-8"
        )


def test_eine_geaenderte_aufgabe_wird_beim_oeffnen_einmal_durchgesehen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 387: beim Öffnen einer geänderten Aufgabe mit vorhandener
    Kopie bildete Natter den Fingerabdruck dreimal und fragte dabei
    jede Datei einzeln ab. Jetzt einmal, mit Größe und Zeit aus den
    Verzeichniseinträgen; der Wert ist derselbe wie vorher, damit
    vorhandene Kopien ihre Aufgabe nicht für geändert halten."""
    datei = _aufgabe(tmp_path / "Tausch" / "Ampel")
    _viele_dateien(datei.parent)
    natter = _konto(monkeypatch, tmp_path, "a")
    _fragen(hauptfenster, True)
    hauptfenster.projekt_oeffnen_gemeldet(datei)
    assert hauptfenster.projekt_schliessen()
    zeit = (datei.parent / "u_main.py").stat().st_mtime + 60
    os.utime(datei.parent / "u_main.py", (zeit, zeit))
    hauptfenster._geaenderte_aufgabe_fragen = (
        lambda _kopie, _text="", _nein=None: "behalten"
    )

    gebildet: list[Path] = []
    abgefragt: list[str] = []
    echt_fingerabdruck, echt_stat = startbild._fingerabdruck, os.stat

    def fingerabdruck(quelle: Path) -> str:
        gebildet.append(Path(quelle))
        return echt_fingerabdruck(quelle)

    def stat(pfad, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003, ANN202
        # `QUELLDATEI` hält den Pfad in Kleinbuchstaben fest.
        teile = {teil.lower() for teil in Path(pfad).parts}
        if {"tausch", "daten"} <= teile:
            abgefragt.append(str(pfad))
        return echt_stat(pfad, *args, **kwargs)

    monkeypatch.setattr(startbild, "_fingerabdruck", fingerabdruck)
    monkeypatch.setattr(os, "stat", stat)
    projekt = hauptfenster.projekt_oeffnen_gemeldet(datei)
    monkeypatch.setattr(os, "stat", echt_stat)

    assert projekt.ordner.resolve() == (natter / "Ampel").resolve()
    assert len(gebildet) == 1
    assert abgefragt == []
    assert not aufgabe_geaendert(natter / "Ampel")
    bisher = sorted(
        f"{pfad.relative_to(datei.parent).as_posix()}\t"
        f"{pfad.stat().st_size}\t{pfad.stat().st_mtime_ns}"
        for pfad in startbild._projekt_dateien(datei.parent)
    )
    assert echt_fingerabdruck(datei.parent) == hashlib.sha256(
        "\n".join(bisher).encode()
    ).hexdigest()


def test_zuruecksetzen_verschiebt_einen_ordner_als_ganzes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Punkt 389: Zurücksetzen verschob jede Datei der Kopie einzeln,
    bei 300 Dateien in `daten` 600 Umbenennungen hin und her. Jetzt
    wandert `daten` als Ganzes, und der bisherige Stand liegt
    vollständig in „Ampel (vorher)“."""
    datei = _aufgabe(tmp_path / "Tausch" / "Ampel")
    _viele_dateien(datei.parent)
    kopie = aufgabe_kopieren(datei, tmp_path / "Natter").parent
    (kopie / "daten" / "d0000.txt").write_text(
        "meine Arbeit\n", encoding="utf-8"
    )
    umbenannt: list[Path] = []
    echt = os.rename

    def umbenennen(von, nach) -> None:  # noqa: ANN001
        umbenannt.append(Path(von))
        echt(von, nach)

    monkeypatch.setattr(os, "rename", umbenennen)
    projektdatei, vorher = startbild.aufgabe_zuruecksetzen(kopie)
    monkeypatch.setattr(os, "rename", echt)

    assert len(umbenannt) < 20, len(umbenannt)
    assert projektdatei == kopie / "Ampel.natter"
    assert vorher == kopie.parent / "Ampel (vorher)"
    assert _lesen(kopie / "daten" / "d0000.txt") == "0\n"
    assert _lesen(vorher / "daten" / "d0000.txt") == "meine Arbeit\n"
    assert len(list((vorher / "daten").iterdir())) == 300
    assert len(list((kopie / "daten").iterdir())) == 300
    assert [p.name for p in kopie.parent.iterdir()] == [
        "Ampel", "Ampel (vorher)"
    ]


def _meldungen(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Sammelt Titel und Text jeder Warnung, statt sie zu zeigen."""
    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda _e, titel, text, *_a: meldungen.append(
            f"{titel}\n{text}"
        )),
    )
    return meldungen


def test_ein_projekt_aus_einem_vorlaeufig_entpackten_zip_wird_kopiert(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 391: eine Aufgabe aus einer ZIP-Datei, vom Explorer
    vorläufig in `%TEMP%\\Temp1_Ampel.zip` abgelegt. Der Ordner gehört
    dem eigenen Konto und ist beschreibbar, trotzdem kommt das Angebot
    der Kopie mit dem Grund, und die Kopie liegt danach unter
    `Dokumente\\Natter`. Fehlen neben der Projektdatei `main.py` und
    die Unit, kommt stattdessen der Hinweis zum Entpacken, und nichts
    wird geöffnet oder kopiert."""
    natter = _konto(monkeypatch, tmp_path, "a")
    temp = tmp_path / "a" / "Temp"
    monkeypatch.setattr(ide.pfade, "temp_ordner", lambda: temp)
    datei = _aufgabe(temp / "Temp1_Ampel.zip" / "Ampel")
    gestellt = _fragen(hauptfenster, True)
    meldungen = _meldungen(monkeypatch)

    projekt = hauptfenster.projekt_oeffnen_gemeldet(datei)

    assert len(gestellt) == 1
    _titel, text, nein = gestellt[0]
    assert nein == "Hier öffnen" and "beim Abmelden" in text
    assert projekt.ordner.resolve() == (natter / "Ampel").resolve()
    assert meldungen == []

    assert hauptfenster.projekt_schliessen()
    gestellt.clear()
    nur_datei = _aufgabe(temp / "Temp2_Blinker.zip" / "Blinker", "Blinker")
    for name in ("main.py", "u_main.py"):
        (nur_datei.parent / name).unlink()

    assert hauptfenster.projekt_oeffnen_gemeldet(nur_datei) is None

    assert gestellt == []
    assert len(meldungen) == 1
    assert meldungen[0].startswith("ZIP-Datei nicht entpackt")
    assert "„main.py“ und „u_main.py“" in meldungen[0]
    assert hauptfenster.projekt is None
    assert [p.name for p in nur_datei.parent.iterdir()] == ["Blinker.natter"]
    assert not (natter / "Blinker").exists()


def test_eine_gesperrte_datei_der_aufgabe_wird_beim_kopieren_genannt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 395: eine CSV der Aufgabe ist in Excel offen. „Eigene
    Kopie öffnen“ scheitert mit einer Meldung, die die Datei nennt,
    und unter `Dokumente\\Natter` bleibt kein angefangener Ordner."""
    datei = _aufgabe(tmp_path / "Tausch" / "Ampel")
    (datei.parent / "zz_daten.csv").write_text("1;2\n", encoding="utf-8")
    natter = _konto(monkeypatch, tmp_path, "a")
    _fragen(hauptfenster, True)
    meldungen = _meldungen(monkeypatch)

    with _wie_in_excel_offen(datei.parent / "zz_daten.csv"):
        assert hauptfenster.projekt_oeffnen_gemeldet(datei) is None

    assert len(meldungen) == 1
    assert "„zz_daten.csv“" in meldungen[0]
    assert "keine Kopie entstanden" in meldungen[0]
    assert list(natter.iterdir()) == []


@pytest.mark.parametrize(
    "ordner", ["7zO4A1B2C3D", "Rar$DIa12345.6789"],
    ids=["7-Zip", "WinRAR"],
)
def test_nur_die_projektdatei_aus_einem_packprogramm_bringt_den_hinweis(
    ordner: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 402: 7-Zip und WinRAR holen beim Doppelklick nur die
    `.natter` nach `%TEMP%\\7zO…` bzw. `%TEMP%\\Rar$DI…` und löschen
    den Ordner beim Schließen des Archivs. Erkannt wurde nur der
    Ordner des Explorers, und das Projekt ging ohne Hinweis auf."""
    natter = _konto(monkeypatch, tmp_path, "a")
    temp = tmp_path / "a" / "Temp"
    monkeypatch.setattr(ide.pfade, "temp_ordner", lambda: temp)
    datei = _aufgabe(temp / ordner)
    for name in ("main.py", "u_main.py"):
        (datei.parent / name).unlink()
    gestellt = _fragen(hauptfenster, True)
    meldungen = _meldungen(monkeypatch)

    assert hauptfenster.projekt_oeffnen_gemeldet(datei) is None

    assert gestellt == []
    assert len(meldungen) == 1
    assert meldungen[0].startswith("ZIP-Datei nicht entpackt")
    assert hauptfenster.projekt is None
    assert not natter.exists()


def test_eine_alte_kopie_der_aufgabe_nennt_die_statuszeile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 401: bis 0.3.6 legte Natter auch von einer Aufgabe in
    einem beschreibbaren Klassenordner eine eigene Kopie an. Seit 0.4.0
    geht die Aufgabe dort ohne Frage am Ort auf (Punkt 390), und die
    Kopie mit der Arbeit der letzten Stunden sah niemand mehr. Jetzt
    nennt die Statuszeile sie, ohne eine Frage zu stellen."""
    natter = _konto(monkeypatch, tmp_path, "a")
    datei = _aufgabe(tmp_path / "Klasse7b" / "Ampel")
    kopie = aufgabe_kopieren(datei, natter)
    (kopie.parent / "u_main.py").write_text("x = 2\n", encoding="utf-8")
    gestellt = _fragen(hauptfenster, True)

    projekt = hauptfenster.projekt_oeffnen_gemeldet(datei)

    assert projekt.ordner.resolve() == datei.parent.resolve()
    assert gestellt == []
    meldung = hauptfenster.statusBar().currentMessage()
    assert str(kopie.parent) in meldung, meldung


def _pruefungsmodus_starten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fenster,  # noqa: ANN001
) -> None:
    import pcl.pruefungsmodus as modul

    ini = QSettings(str(tmp_path / "pruefung.ini"), QSettings.Format.IniFormat)
    monkeypatch.setattr(modul, "einstellungen", lambda: ini)
    modul.starten(ini)
    fenster._pruefungsmodus_nachfuehren()


def test_im_pruefungsmodus_holt_eine_eigene_quelldatei_kein_beispiel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 403: `.natter-quelle` ist Text im eigenen Projekt. Zeigte
    sie auf ein Beispiel, holte „Auf Original zurücksetzen …“ im
    Prüfungsmodus dessen Lösung in das eigene Projekt. Die Projektdatei
    in anderer Schreibweise, `04_cookieklicker.natter`, galt dabei nicht
    als Kopie des Beispiels, obwohl Windows sie im Original findet."""
    beispiel = _BEISPIELE / "04_CookieKlicker"
    mein = tmp_path / "Mein"
    mein.mkdir()
    (mein / "04_cookieklicker.natter").write_bytes(
        (beispiel / "04_CookieKlicker.natter").read_bytes()
    )
    (mein / "u_main.py").write_text("# meine Arbeit\n", encoding="utf-8")
    (mein / QUELLDATEI).write_text(
        f"{str(beispiel.resolve()).upper()}\n", encoding="utf-8"
    )
    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda _e, titel, *_a: meldungen.append(titel)),
    )
    _pruefungsmodus_starten(tmp_path, monkeypatch, hauptfenster)

    hauptfenster.projekt_oeffnen(mein / "04_cookieklicker.natter")
    assert not hauptfenster.beispiel_zuruecksetzen_nachfragen(
        bestaetigt=True
    )
    assert _lesen(mein / "u_main.py") == "# meine Arbeit\n"
    assert not hauptfenster._beispiel_zuruecksetzen_eintrag.isEnabled()
    with pytest.raises(ValueError, match="Beispiel"):
        startbild.aufgabe_zuruecksetzen(mein)
    assert _lesen(mein / "u_main.py") == "# meine Arbeit\n"
    assert startbild.beispiel_original(mein) == beispiel


def _geaendert_offen(fenster, datei: Path, text: str):  # noqa: ANN001, ANN202
    editor = fenster.datei_oeffnen(datei)
    editor.setPlainText(text)
    editor.document().setModified(True)
    return editor


@pytest.mark.parametrize("antwort", ["Save", "Cancel"])
def test_ein_gescheitertes_zuruecksetzen_behaelt_den_ungespeicherten_text(
    antwort: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 405: die Reiter der Kopie gingen vor dem Zurücksetzen ohne
    Frage zu. Scheiterte das Kopieren danach an einer gesperrten
    Datei, war der ungespeicherte Text weg, samt Sicherung. Jetzt
    kommt vorher die Frage wie beim Schließen. Nach „Speichern“ steht
    der Text in der Datei und im wieder geöffneten Reiter, nach
    „Abbrechen“ bleibt er ungespeichert im Editor."""
    datei = _aufgabe(tmp_path / "Tausch" / "Ampel")
    kopie = aufgabe_kopieren(datei, ide.pfade.natter_ordner())
    hauptfenster.projekt_oeffnen(kopie)
    _geaendert_offen(hauptfenster, kopie.parent / "u_main.py", "x = 2\n")
    gefragt: list[list[str]] = []

    def fragen(_self, namen):  # noqa: ANN001, ANN202
        gefragt.append(namen)
        return getattr(QMessageBox.StandardButton, antwort)

    monkeypatch.setattr(HauptFenster, "_vor_dem_schliessen_fragen", fragen)

    def gesperrt(ordner: Path):  # noqa: ANN202
        raise startbild.DateiGesperrt(Path(ordner) / "daten.csv")

    monkeypatch.setattr(hauptfenster_modul, "aufgabe_zuruecksetzen", gesperrt)
    _meldungen(monkeypatch)

    assert not hauptfenster.beispiel_zuruecksetzen_nachfragen(
        bestaetigt=True
    )

    assert gefragt == [["u_main.py"]]
    unit = (kopie.parent / "u_main.py").resolve()
    assert unit in hauptfenster._reiter_im_ordner(kopie.parent)
    editor = hauptfenster.datei_oeffnen(unit)
    assert editor.toPlainText() == "x = 2\n"
    gespeichert = antwort == "Save"
    assert editor.document().isModified() is not gespeichert
    assert (_lesen(kopie.parent / "u_main.py") == "x = 2\n") is gespeichert


def test_nach_speichern_liegt_der_text_im_ordner_mit_dem_bisherigen_stand(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 405: die Rückfrage verspricht, dass der bisherige Stand
    der Kopie in „Ampel (vorher)“ kommt. Dort lag bis dahin nur, was
    auf der Platte stand, nicht der Text im Editor."""
    datei = _aufgabe(tmp_path / "Tausch" / "Ampel")
    kopie = aufgabe_kopieren(datei, ide.pfade.natter_ordner())
    hauptfenster.projekt_oeffnen(kopie)
    _geaendert_offen(hauptfenster, kopie.parent / "u_main.py", "x = 3\n")
    monkeypatch.setattr(
        HauptFenster, "_vor_dem_schliessen_fragen",
        lambda _self, _namen: QMessageBox.StandardButton.Save,
    )

    assert hauptfenster.beispiel_zuruecksetzen_nachfragen(bestaetigt=True)

    vorher = kopie.parent.parent / "Ampel (vorher)"
    assert _lesen(vorher / "u_main.py") == "x = 3\n"
    assert _lesen(kopie.parent / "u_main.py") == "x = 1\n"
