"""Öffnen, wenn Natter am Ziel nicht schreiben darf (Punkte 320, 321).

Ein Beispiel wird nach „Dokumente\\Natter\\Beispielprojekte“ kopiert.
Ist „Dokumente“ ein nicht verbundenes Netzlaufwerk oder fehlt das
Schreibrecht, endete der Menüeintrag in der Absturzmeldung, und die
Startseite meldete eine fehlende Projektdatei.

Eine Aufgabe auf einer Freigabe nur zum Lesen ging ohne Hinweis auf,
und gespeichert werden konnte sie nirgends.

Der Schreibschutz wird nachgestellt, ohne Rechte in Windows zu ändern:
für 320 über einen Dokumente-Ordner auf einem Laufwerk, das es nicht
gibt, und ein `copytree`, das `PermissionError` wirft; für 321 über
die Schreibprobe.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

import ide.pfade
from ide.shell.startbild import beispielprojekte


@pytest.fixture
def meldungen(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    gesehen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda _eltern, titel, text, *a: gesehen.append(
            f"{titel}\n{text}"
        )),
    )
    return gesehen


def _eintrag(fenster, name: str):  # noqa: ANN001, ANN202
    for aktion in fenster.menue("Datei").actions():
        if aktion.text() == "Beispielprojekte":
            for eintrag in aktion.menu().actions():
                if eintrag.text() == name:
                    return eintrag
    raise AssertionError(f"Kein Menüeintrag {name}")


def _verweigert(*_args, **_kwargs) -> None:  # noqa: ANN002, ANN003
    raise PermissionError(13, "Zugriff verweigert")


@pytest.mark.parametrize("grund", ["nicht verbunden", "kein Schreibrecht"])
def test_beispiel_ohne_beschreibbares_dokumente_meldet_den_zielordner(
    grund: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    meldungen: list[str], hauptfenster,  # noqa: ANN001
) -> None:
    if grund == "nicht verbunden":
        # Ein Laufwerksbuchstabe, den es auf diesem Rechner nicht gibt,
        # wie bei einem umgeleiteten, gerade nicht verbundenen
        # Netzlaufwerk.
        frei = next(
            (b for b in "QRSTUVWXYZ" if not Path(f"{b}:\\").exists()), None
        )
        if frei is None:
            pytest.skip("Kein freier Laufwerksbuchstabe.")
        dokumente = Path(f"{frei}:\\Dokumente")
    else:
        dokumente = tmp_path / "Dokumente"
        monkeypatch.setattr(shutil, "copytree", _verweigert)
    monkeypatch.setattr(ide.pfade, "dokumente_ordner", lambda: dokumente)
    original = next(
        p for p in beispielprojekte() if p.parent.name == "01_Begruessung"
    )
    ziel = str(dokumente / "Natter" / "Beispielprojekte")

    _eintrag(hauptfenster, "01_Begruessung").trigger()
    hauptfenster.startbild.projekt_gewaehlt.emit(original)

    assert hauptfenster.projekt is None
    assert len(meldungen) == 2, meldungen
    for text in meldungen:
        assert ziel in text
        assert "Netzlaufwerk" in text and "nicht schreiben" in text
        assert "nicht gefunden" not in text


def _aufgabe(ordner: Path) -> Path:
    ordner.mkdir(parents=True)
    (ordner / "main.py").write_text("import u_main\n", encoding="utf-8")
    (ordner / "u_main.py").write_text("x = 1\n", encoding="utf-8")
    datei = ordner / "Aufgabe3.natter"
    datei.write_text(json.dumps({
        "format": "natter-project/1", "name": "Aufgabe3",
        "type": "console", "main": "main.py",
    }), encoding="utf-8")
    return datei


def test_aufgabe_ohne_schreibrecht_wird_als_kopie_angeboten(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster,  # noqa: ANN001
) -> None:
    tausch = tmp_path / "Tausch" / "Aufgabe3"
    datei = _aufgabe(tausch)
    monkeypatch.setattr(
        "ide.shell.hauptfenster.ordner_beschreibbar",
        lambda ordner: Path(ordner).resolve() != tausch.resolve(),
    )
    fragen = _antworten(monkeypatch, [True])

    projekt = hauptfenster.projekt_oeffnen_gemeldet(datei)

    assert len(fragen) == 1
    assert str(tausch) in fragen[0][1] and "kopiert" in fragen[0][1]
    kopie = ide.pfade.natter_ordner() / "Aufgabe3"
    assert projekt.ordner.resolve() == kopie.resolve()
    editor = hauptfenster.datei_oeffnen(kopie / "u_main.py")
    editor.setPlainText("x = 2\n")
    editor.document().setModified(True)
    assert hauptfenster.alle_speichern()
    assert (kopie / "u_main.py").read_text(encoding="utf-8").strip() == "x = 2"
    assert (tausch / "u_main.py").read_text(encoding="utf-8") == "x = 1\n"


def _antworten(
    monkeypatch: pytest.MonkeyPatch, antworten: list[bool]
) -> list[tuple[str, str, str]]:
    """Gibt die Antworten auf das Kopierangebot der Reihe nach vor und
    sammelt Titel, Text und den zweiten Knopf jeder Frage."""
    from ide.shell.hauptfenster import HauptFenster

    fragen: list[tuple[str, str, str]] = []

    def anbieten(_self, titel, text, nein, **_kw):  # noqa: ANN001, ANN003, ANN202
        fragen.append((titel, text, nein))
        return antworten.pop(0)

    def frage(_eltern, titel, text, *_a):  # noqa: ANN001, ANN002, ANN202
        fragen.append((titel, text, ""))
        return (
            QMessageBox.StandardButton.Yes if antworten.pop(0)
            else QMessageBox.StandardButton.No
        )

    monkeypatch.setattr(
        HauptFenster, "_kopie_anbieten", anbieten, raising=False
    )
    # Kein Fenster darf im Test auf einen Klick warten.
    monkeypatch.setattr(QMessageBox, "question", staticmethod(frage))
    for art in ("information", "warning"):
        monkeypatch.setattr(
            QMessageBox, art, staticmethod(lambda *_a: None)
        )
    return fragen


def _nur_lesen(monkeypatch: pytest.MonkeyPatch, tausch: Path) -> None:
    """Schreibschutz für `tausch`: die Schreibprobe schlägt fehl, und
    Speichern dort wird verweigert."""
    import ide.shell.hauptfenster as hf

    echt = hf.atomar_schreiben

    def schreiben(pfad, *a, **kw):  # noqa: ANN001, ANN002, ANN003, ANN202
        if Path(pfad).resolve().is_relative_to(tausch.resolve()):
            raise PermissionError(13, "Zugriff verweigert")
        return echt(pfad, *a, **kw)

    monkeypatch.setattr(hf, "atomar_schreiben", schreiben)
    monkeypatch.setattr(
        hf, "ordner_beschreibbar",
        lambda ordner: Path(ordner).resolve() != tausch.resolve(),
    )


def _status(fenster) -> str:  # noqa: ANN001
    return fenster.statusBar().currentMessage()


@pytest.mark.parametrize("weg", ["beim Speichern", "beim zweiten Öffnen"])
def test_nach_nur_ansehen_kommt_die_arbeit_in_die_kopie(
    weg: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster, qtbot,  # noqa: ANN001
) -> None:
    """Punkt 341: erst „Nur ansehen“, dann eine Zeile geschrieben. Der
    Text landet in der Kopie, entweder über das Angebot in der Meldung
    zum gescheiterten Speichern oder über ein zweites Öffnen. Bricht
    der Wechsel ab, sagt die Statuszeile nichts von einer Kopie."""
    tausch = tmp_path / "Tausch" / "Ampel"
    datei = _aufgabe(tausch)
    _nur_lesen(monkeypatch, tausch)
    antworten = [False]
    fragen = _antworten(monkeypatch, antworten)

    projekt = hauptfenster.projekt_oeffnen_gemeldet(datei)
    assert projekt.ordner.resolve() == tausch.resolve()
    assert fragen[0][2] == "Nur ansehen"
    assert "nur zum Ansehen" in _status(hauptfenster)
    editor = hauptfenster.datei_oeffnen(tausch / "u_main.py")
    editor.setPlainText("x = 2\n")
    editor.document().setModified(True)
    kopie = ide.pfade.natter_ordner() / "Ampel"

    if weg == "beim Speichern":
        antworten.append(True)
        assert not hauptfenster._editor_speichern(editor)
        assert fragen[1][0] == "Nicht gespeichert"
        assert str(ide.pfade.natter_ordner()) in fragen[1][1]
        qtbot.waitUntil(
            lambda: hauptfenster.projekt.ordner.resolve() == kopie.resolve(),
            timeout=5000,
        )
    else:
        from ide.shell.hauptfenster import HauptFenster

        antworten.append(True)
        with monkeypatch.context() as m:
            m.setattr(
                HauptFenster, "_vorheriges_projekt_schliessen",
                lambda self, neuer_ordner=None: False,
            )
            hauptfenster.projekt_oeffnen_gemeldet(datei)
        assert hauptfenster.projekt.ordner.resolve() == tausch.resolve()
        assert "Kopie" not in _status(hauptfenster)
        assert "kopiert" not in _status(hauptfenster)
        antworten.append(True)
        hauptfenster.projekt_oeffnen_gemeldet(datei)
        assert hauptfenster.projekt.ordner.resolve() == kopie.resolve()

    assert (kopie / "u_main.py").read_text(encoding="utf-8") == "x = 2\n"
    assert (tausch / "u_main.py").read_text(encoding="utf-8") == "x = 1\n"
    assert "ungespeicherten Änderungen" in _status(hauptfenster)


@pytest.mark.parametrize("weg", ["beim Speichern", "beim zweiten Öffnen"])
def test_eine_vorhandene_kopie_behaelt_ihren_stand(
    weg: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster, qtbot,  # noqa: ANN001
) -> None:
    """Punkt 365: die eigene Kopie gibt es schon, mit der Arbeit vom
    Vortag. Wer im Original nur zum Ansehen etwas schreibt und dann in
    die Kopie wechselt, findet den Text aus dem Original als
    ungespeicherte Änderung im Editor; die Datei der Kopie bleibt, wie
    sie war, und ein Rückgängig holt ihren Stand zurück."""
    from ide.shell.startbild import aufgabe_kopieren

    tausch = tmp_path / "Tausch" / "Ampel"
    datei = _aufgabe(tausch)
    kopie = aufgabe_kopieren(datei, ide.pfade.natter_ordner()).parent
    gestern = "x = 5  # Arbeit von gestern\n"
    (kopie / "u_main.py").write_text(gestern, encoding="utf-8")
    _nur_lesen(monkeypatch, tausch)
    antworten = [False]
    fragen = _antworten(monkeypatch, antworten)

    hauptfenster.projekt_oeffnen_gemeldet(datei)
    assert fragen[0][2] == "Nur ansehen"
    editor = hauptfenster.datei_oeffnen(tausch / "u_main.py")
    editor.setPlainText("x = 1\ny = 2\n")
    editor.document().setModified(True)

    antworten.append(True)
    if weg == "beim Speichern":
        assert not hauptfenster._editor_speichern(editor)
        assert fragen[1][0] == "Nicht gespeichert"
        qtbot.waitUntil(
            lambda: hauptfenster.projekt.ordner.resolve() == kopie.resolve(),
            timeout=5000,
        )
    else:
        hauptfenster.projekt_oeffnen_gemeldet(datei)
        assert hauptfenster.projekt.ordner.resolve() == kopie.resolve()

    datei_kopie = kopie / "u_main.py"
    assert datei_kopie.read_text(encoding="utf-8") == gestern
    editor = hauptfenster.datei_oeffnen(datei_kopie)
    assert editor.toPlainText() == "x = 1\ny = 2\n"
    assert editor.document().isModified()
    assert "noch nicht gespeichert" in _status(hauptfenster)
    # Punkt 386: der Satz zu Rückgängig passt ganz in die Statuszeile
    # eines Fensters von 1280 Punkten Breite. Vorher stand der Pfad
    # der Kopie davor, und der Satz war rund 1570 Punkte breit.
    from PySide6.QtGui import QFont, QFontMetrics

    breite = QFontMetrics(QFont("Segoe UI", 9)).horizontalAdvance(
        _status(hauptfenster)
    )
    assert "Rückgängig" in _status(hauptfenster)
    assert breite < 1200, breite
    editor.undo()
    assert editor.toPlainText() == gestern
    assert not editor.document().isModified()
    assert "Dateien der Kopie bleiben" in fragen[1][1]


def test_eine_unlesbare_kopie_laesst_den_text_als_geaendert_stehen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 373: die Projektdatei der vorhandenen Kopie ist
    beschädigt. Der Wechsel scheitert mit einer Meldung, und der
    ungespeicherte Text aus dem Original gilt weiter als geändert,
    sodass die Nachfrage beim Schließen ihn nennt."""
    from ide.shell.hauptfenster import HauptFenster
    from ide.shell.startbild import aufgabe_kopieren

    tausch = tmp_path / "Tausch" / "Ampel"
    datei = _aufgabe(tausch)
    kopie = aufgabe_kopieren(datei, ide.pfade.natter_ordner())
    kopie.write_text("{ kaputt", encoding="utf-8")
    _nur_lesen(monkeypatch, tausch)
    _antworten(monkeypatch, [False, True])
    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda _e, titel, text, *_a: meldungen.append(
            f"{titel}: {text}"
        )),
    )
    hauptfenster.projekt_oeffnen_gemeldet(datei)
    editor = hauptfenster.datei_oeffnen(tausch / "u_main.py")
    editor.setPlainText("x = 1\ny = 2\n")
    editor.document().setModified(True)

    assert hauptfenster.projekt_oeffnen_gemeldet(datei) is None

    assert hauptfenster.projekt.ordner.resolve() == tausch.resolve()
    assert "beschädigt" in meldungen[-1]
    assert editor.document().isModified()
    gefragt: list[list[str]] = []

    def fragen(_self, namen):  # noqa: ANN001, ANN202
        gefragt.append(list(namen))
        return QMessageBox.StandardButton.Discard

    monkeypatch.setattr(HauptFenster, "_vor_dem_schliessen_fragen", fragen)
    assert hauptfenster.close()
    assert gefragt == [["u_main.py"]]


def _fremde_sperre(ordner: Path, konto: str) -> None:
    import time

    from ide.project import sperre

    (ordner / sperre.SPERRDATEI).write_text(
        f"4711 1\nrechner=PC-R12\nkonto={konto}\n"
        f"erneuert={int(time.time())}\nordner={ordner.resolve()}\n",
        encoding="utf-8",
    )


def test_fremde_sperre_im_tauschordner_fuehrt_in_die_eigene_kopie(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 342: der Tauschordner ist beschreibbar, die Aufgabe an
    einem anderen Rechner offen. Nach „Eigene Kopie öffnen“ ist die
    Kopie unter „Dokumente\\Natter“ offen, und das zweite Öffnen bringt
    dieselbe Kopie."""
    tausch = tmp_path / "Tausch" / "Ampel"
    datei = _aufgabe(tausch)
    _fremde_sperre(tausch, "mueller.anna")
    fragen = _antworten(monkeypatch, [True, True])
    kopie = ide.pfade.natter_ordner() / "Ampel"

    projekt = hauptfenster.projekt_oeffnen_gemeldet(datei)
    assert projekt.ordner.resolve() == kopie.resolve()
    assert fragen[0][2] == "Trotzdem hier öffnen"

    assert hauptfenster.projekt_schliessen()
    projekt = hauptfenster.projekt_oeffnen_gemeldet(datei)
    assert projekt.ordner.resolve() == kopie.resolve()
    assert not (ide.pfade.natter_ordner() / "Ampel 2").exists()
    assert "Stand vom letzten Mal" in _status(hauptfenster)


def test_hinweis_zur_fremden_sperre_bietet_die_kopie_mit_ihrem_ordner_an(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 349: die Frage nennt „Dokumente\\Natter“ als Ziel und
    bietet die Kopie mit einem Knopf an. Nach „Trotzdem hier öffnen“
    kommt kein zweiter Hinweis hinterher."""
    tausch = tmp_path / "Tausch" / "Ampel"
    datei = _aufgabe(tausch)
    _fremde_sperre(tausch, "mueller.anna")
    fragen = _antworten(monkeypatch, [False, True])
    hinweise: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda _e, _t, text, *a: hinweise.append(text)),
    )

    projekt = hauptfenster.projekt_oeffnen_gemeldet(datei)
    assert projekt.ordner.resolve() == tausch.resolve()
    assert hinweise == []
    _titel, text, nein = fragen[0]
    assert "PC-R12" in text and "mueller.anna" in text
    assert str(ide.pfade.natter_ordner()) in text
    assert "„Eigene Kopie öffnen“" in text and nein in text
    assert "Ordner „Dokumente“" not in text

    projekt = hauptfenster.projekt_oeffnen_gemeldet(datei)
    assert projekt.ordner.resolve() == (
        ide.pfade.natter_ordner() / "Ampel"
    ).resolve()


@pytest.mark.parametrize("konto", ["eigenes", "fremdes"])
def test_sperre_eines_anderen_rechners_im_eigenen_konto_raet_zu_keiner_kopie(
    konto: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 345: im eigenen Konto ist die Sperre fast immer ein nicht
    beendetes Natter am anderen Rechner. Kein Kopierangebot und kein
    Rat zur Kopie; bei einem fremden Konto bleibt der Hinweis auf die
    andere Sitzung."""
    from ide.project import sperre

    ordner = ide.pfade.natter_ordner() / "Ampel"
    datei = _aufgabe(ordner)
    _fremde_sperre(
        ordner, sperre.kontoname() if konto == "eigenes" else "mueller.anna"
    )
    fragen = _antworten(monkeypatch, [])
    hinweise: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "information",
        staticmethod(lambda _e, _t, text, *a: hinweise.append(text)),
    )

    if konto == "eigenes":
        projekt = hauptfenster.projekt_oeffnen_gemeldet(datei)
        assert fragen == []
    else:
        projekt = hauptfenster.projekt_oeffnen(datei)
    assert projekt.ordner.resolve() == ordner.resolve()
    assert len(hinweise) == 1
    if konto == "eigenes":
        assert "im selben Konto" in hinweise[0]
        assert "nicht beendet" in hinweise[0]
        assert "Kopie" not in hinweise[0]
    else:
        assert "Beide Sitzungen" in hinweise[0]
        assert "Ordner „Dokumente“" not in hinweise[0]


def test_kopie_einer_aufgabe_laesst_sich_zuruecksetzen_und_erneuern(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 346: „Auf Original zurücksetzen …“ gilt auch für die Kopie
    einer Aufgabe, und nach einer Berichtigung der Aufgabe fragt das
    erneute Öffnen, ob die Kopie ersetzt werden soll."""
    import os

    from ide.shell.hauptfenster import HauptFenster

    tausch = tmp_path / "Tausch" / "Ampel"
    datei = _aufgabe(tausch)
    _nur_lesen(monkeypatch, tausch)
    _antworten(monkeypatch, [True, True, True])
    ersetzen: list[bool] = []
    monkeypatch.setattr(
        HauptFenster, "_geaenderte_aufgabe_fragen",
        lambda self, kopie, text="", nein=None: (
            "ersetzen" if ersetzen.pop(0) else "behalten"
        ),
    )
    kopie = ide.pfade.natter_ordner() / "Ampel"
    unit = kopie / "u_main.py"

    hauptfenster.projekt_oeffnen_gemeldet(datei)
    assert hauptfenster._beispiel_zuruecksetzen_eintrag.isEnabled()
    unit.write_text("kaputt\n", encoding="utf-8")
    assert hauptfenster.beispiel_zuruecksetzen_nachfragen(bestaetigt=True)
    assert unit.read_text(encoding="utf-8") == "x = 1\n"
    assert hauptfenster.projekt.ordner.resolve() == kopie.resolve()

    # Die Lehrkraft berichtigt die Aufgabe.
    unit.write_text("x = 5\n", encoding="utf-8")
    (tausch / "u_main.py").write_text("x = 3\n", encoding="utf-8")
    zeit = (tausch / "u_main.py").stat().st_mtime + 60
    os.utime(tausch / "u_main.py", (zeit, zeit))
    ersetzen.append(False)
    hauptfenster.projekt_oeffnen_gemeldet(datei)
    assert ersetzen == []
    assert unit.read_text(encoding="utf-8") == "x = 5\n"
    assert "kopiert" not in _status(hauptfenster)

    # Nach „behalten“ fragt Natter zu diesem Stand nicht wieder
    # (Punkt 380), erst nach der nächsten Berichtigung.
    hauptfenster.projekt_oeffnen_gemeldet(datei)
    assert unit.read_text(encoding="utf-8") == "x = 5\n"
    os.utime(tausch / "u_main.py", (zeit + 60, zeit + 60))
    ersetzen.append(True)
    hauptfenster.projekt_oeffnen_gemeldet(datei)
    assert ersetzen == []
    assert unit.read_text(encoding="utf-8") == "x = 3\n"
    assert "neu" in _status(hauptfenster)
    assert not (ide.pfade.natter_ordner() / "Ampel 2").exists()


def test_kopie_nach_speicherfehler_meldet_eine_beschaedigte_kopie(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster,  # noqa: ANN001
) -> None:
    """Punkt 378: Derselbe Fall wie in Punkt 373, aber über „Eigene
    Kopie öffnen“ in der Meldung zum gescheiterten Speichern. Dort kam
    die beschädigte Projektdatei der Kopie als Traceback heraus statt
    als Meldung."""
    from ide.shell.startbild import aufgabe_kopieren

    tausch = tmp_path / "Tausch" / "Ampel"
    datei = _aufgabe(tausch)
    kopie = aufgabe_kopieren(datei, ide.pfade.natter_ordner())
    kopie.write_text("{ kaputt", encoding="utf-8")
    _nur_lesen(monkeypatch, tausch)
    _antworten(monkeypatch, [False])
    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda _e, titel, text, *_a: meldungen.append(
            f"{titel}: {text}"
        )),
    )
    hauptfenster.projekt_oeffnen_gemeldet(datei)
    editor = hauptfenster.datei_oeffnen(tausch / "u_main.py")
    editor.setPlainText("x = 1\ny = 2\n")
    editor.document().setModified(True)
    monkeypatch.setattr(
        hauptfenster, "_kopie_holen", lambda _d: (kopie, "vorhanden"),
    )

    hauptfenster._kopie_nach_speicherfehler()

    assert "beschädigt" in meldungen[-1]
    assert hauptfenster.projekt.ordner.resolve() == tausch.resolve()
    assert editor.document().isModified()


def test_projektdatei_ohne_leserecht_meldet_den_grund_auf_deutsch(
    monkeypatch: pytest.MonkeyPatch, hauptfenster,  # noqa: ANN001
    meldungen: list[str],
) -> None:
    """Punkt 385: eine Projektdatei, die dieses Konto nicht lesen darf.
    Vorher stand in der Meldung „[Errno 13] Permission denied“ mit dem
    Pfad in doppelten Backslashes."""
    from ide.project import Projekt

    ordner = ide.pfade.natter_ordner() / "Ampel"
    datei = _aufgabe(ordner)

    def laden(_cls, pfad):  # noqa: ANN001, ANN202
        raise PermissionError(13, "Permission denied", str(pfad))

    monkeypatch.setattr(Projekt, "laden", classmethod(laden))

    assert hauptfenster.projekt_oeffnen_gemeldet(datei) is None

    assert len(meldungen) == 1
    text = meldungen[0]
    assert "Leserecht" in text and str(ordner) in text
    for fremd in ("Errno", "Permission", "denied", "\\\\"):
        assert fremd not in text, fremd
