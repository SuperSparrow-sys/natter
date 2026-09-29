"""Die Kopie einer Aufgabe aus einem Ordner ohne Schreibrecht
(Punkte 333, 335, 340).

Punkt 321 bietet beim Öffnen aus einem solchen Ordner eine Kopie
unter „Dokumente\\Natter“ an. Die Kopie blieb schreibgeschützt, wenn
es die Dateien des Originals waren (333), eine Aufgabe aus der Wurzel
einer Freigabe landete samt allem dort in „ 2“ (335), und ein eigenes
Projekt gleichen Namens wurde statt der Aufgabe geöffnet (340).

Ohne Hauptfenster: geprüft werden `aufgabe_kopieren` und
`beispiel_kopieren` selbst. Den Weg über die Nachfrage deckt
`test_schreibschutz_beim_oeffnen.py` ab.
"""

from __future__ import annotations

import contextlib
import errno
import json
import os
import shutil
import stat
from collections.abc import Callable, Iterator
from pathlib import Path, PureWindowsPath

import pytest

from ide.atomar import atomar_schreiben
from ide.shell import startbild
from ide.shell.startbild import (
    DateiGesperrt,
    aufgabe_kopieren,
    beispiel_kopieren,
)


def _aufgabe(ordner: Path, name: str, inhalt: str) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text("import u_main\n", encoding="utf-8")
    (ordner / "u_main.py").write_text(inhalt, encoding="utf-8")
    datei = ordner / f"{name}.natter"
    datei.write_text(json.dumps({
        "format": "natter-project/1", "name": name,
        "type": "console", "main": "main.py",
    }), encoding="utf-8")
    return datei


@pytest.mark.parametrize(
    "kopieren", [aufgabe_kopieren, beispiel_kopieren],
    ids=["Aufgabe", "Beispiel"],
)
def test_die_kopie_schreibgeschuetzter_dateien_laesst_sich_speichern(
    kopieren: Callable[[Path, Path], Path], tmp_path: Path,
) -> None:
    """Punkt 333: Dateien von einer CD tragen das Attribut
    „Schreibgeschützt“ immer. In der Kopie darf es nicht mehr
    stehen."""
    datei = _aufgabe(tmp_path / "CD" / "Aufgabe", "Aufgabe", "x = 1\n")
    originale = sorted(datei.parent.iterdir())
    for pfad in originale:
        os.chmod(pfad, stat.S_IREAD)
    try:
        kopie = kopieren(datei, tmp_path / "Natter")

        atomar_schreiben(kopie.parent / "u_main.py", "x = 2\n")
        atomar_schreiben(kopie, kopie.read_text(encoding="utf-8"))
        assert (kopie.parent / "u_main.py").read_text(
            encoding="utf-8"
        ) == "x = 2\n"
        assert not os.access(datei.parent / "u_main.py", os.W_OK)
    finally:
        for pfad in originale:
            os.chmod(pfad, stat.S_IREAD | stat.S_IWRITE)


def test_eine_aufgabe_aus_der_wurzel_einer_freigabe_bekommt_ihren_namen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Punkt 335: `\\\\server\\klausur\\Klausur.natter` hat keinen
    Projektordner mit Namen. Eine echte Freigabe gibt es im Test
    nicht; der Ordner `freigabe` gilt hier als ihre Wurzel."""
    assert startbild._ist_wurzel(PureWindowsPath("\\\\server\\klausur\\"))
    assert startbild._ist_wurzel(PureWindowsPath("K:\\"))
    assert not startbild._ist_wurzel(PureWindowsPath("K:\\Klausur"))

    freigabe = tmp_path / "freigabe"
    datei = _aufgabe(freigabe, "Klausur", "x = 1\n")
    (freigabe / "Andere Klasse").mkdir()
    (freigabe / "Andere Klasse" / "noten.csv").write_text(
        "1;2\n", encoding="utf-8"
    )
    (freigabe / "diagramme").mkdir()
    (freigabe / "diagramme" / "klassen.pdiag").write_text(
        "{}", encoding="utf-8"
    )
    monkeypatch.setattr(
        startbild, "_ist_wurzel", lambda ordner: Path(ordner) == freigabe
    )

    kopie = aufgabe_kopieren(datei, tmp_path / "Natter")

    assert kopie == tmp_path / "Natter" / "Klausur" / "Klausur.natter"
    assert (kopie.parent / "u_main.py").is_file()
    assert (kopie.parent / "diagramme" / "klassen.pdiag").is_file()
    assert [p.name for p in kopie.parent.iterdir() if p.is_dir()] == [
        "diagramme"
    ]


def test_ein_eigenes_projekt_gleichen_namens_ist_keine_kopie(
    tmp_path: Path,
) -> None:
    """Punkt 340: Unter „Dokumente\\Natter“ liegen auch eigene
    Projekte. Weiterbenutzt wird nur eine Kopie derselben Aufgabe."""
    natter = tmp_path / "Natter"
    _aufgabe(natter / "Ampel", "Ampel", "eigenes Projekt\n")
    aufgabe = _aufgabe(
        tmp_path / "Tausch" / "Woche1" / "Ampel", "Ampel",
        "Aufgabe der Lehrkraft\n",
    )

    erste = aufgabe_kopieren(aufgabe, natter)
    (erste.parent / "u_main.py").write_text(
        "Arbeit der Stunde\n", encoding="utf-8"
    )
    zweite = aufgabe_kopieren(aufgabe, natter)
    andere = aufgabe_kopieren(
        _aufgabe(
            tmp_path / "Tausch" / "Woche3" / "Ampel", "Ampel",
            "andere Aufgabe\n",
        ),
        natter,
    )

    assert erste == natter / "Ampel 2" / "Ampel.natter"
    assert zweite == erste
    assert (zweite.parent / "u_main.py").read_text(
        encoding="utf-8"
    ) == "Arbeit der Stunde\n"
    assert andere == natter / "Ampel 3" / "Ampel.natter"
    assert (natter / "Ampel" / "u_main.py").read_text(
        encoding="utf-8"
    ) == "eigenes Projekt\n"


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


@pytest.mark.parametrize(
    "art", ["Aufgabe mit gesperrter Datei", "Beispiel bei vollem Laufwerk"]
)
def test_eine_gescheiterte_kopie_hinterlaesst_keinen_ordner(
    art: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Punkt 395: scheitert das Kopieren mittendrin, bleibt unter
    `Dokumente\\Natter` nichts liegen, und der nächste Versuch legt
    eine vollständige Kopie unter dem ursprünglichen Namen an. Bei
    einer gesperrten Datei nennt der Fehler sie."""
    datei = _aufgabe(tmp_path / "Tausch" / "Ampel", "Ampel", "x = 1\n")
    (datei.parent / "zz_daten.csv").write_text("1;2\n", encoding="utf-8")
    natter = tmp_path / "Natter"
    natter.mkdir()

    if art.startswith("Aufgabe"):
        kopieren = aufgabe_kopieren
        with _wie_in_excel_offen(datei.parent / "zz_daten.csv"):
            for _ in range(2):
                with pytest.raises(DateiGesperrt) as fehler:
                    kopieren(datei, natter)
                assert fehler.value.pfad.name == "zz_daten.csv"
    else:
        kopieren = beispiel_kopieren
        echt = startbild._beschreibbar_kopieren

        def voll(quelle: str, ziel: str) -> str:
            if Path(quelle).name == "u_main.py":
                raise OSError(errno.ENOSPC, "Kein Speicherplatz")
            return echt(quelle, ziel)

        with monkeypatch.context() as geaendert:
            geaendert.setattr(startbild, "_beschreibbar_kopieren", voll)
            with pytest.raises(OSError):
                kopieren(datei, natter)
    assert list(natter.iterdir()) == []

    kopie = kopieren(datei, natter)

    assert kopie == natter / "Ampel" / "Ampel.natter"
    assert (kopie.parent / "u_main.py").is_file()
    assert (kopie.parent / "zz_daten.csv").is_file()
    assert [p.name for p in natter.iterdir()] == ["Ampel"]
    if kopieren is aufgabe_kopieren:
        assert (kopie.parent / startbild.QUELLDATEI).is_file()


@pytest.mark.parametrize("bearbeitet", [False, True])
def test_eine_halbe_beispielkopie_wird_vervollstaendigt(
    bearbeitet: bool, tmp_path: Path,
) -> None:
    """Punkt 395: eine Kopie eines Beispiels, die vor der Änderung
    mittendrin abbrach, hat nur Projektdatei und `main.py`. Sie wird
    als unvollständig erkannt und neu angelegt, statt ohne Unit
    weiterbenutzt zu werden. Wurde in ihr schon etwas geändert, liegt
    der alte Stand danach im Ordner daneben."""
    datei = _aufgabe(tmp_path / "Beispiele" / "Ampel", "Ampel", "x = 1\n")
    natter = tmp_path / "Natter"
    halb = natter / "Ampel"
    halb.mkdir(parents=True)
    for name in ("Ampel.natter", "main.py"):
        shutil.copy2(datei.parent / name, halb / name)
    if bearbeitet:
        (halb / "main.py").write_text("print(1)\n", encoding="utf-8")

    kopie = beispiel_kopieren(datei, natter)

    assert kopie == halb / "Ampel.natter"
    assert (halb / "u_main.py").read_text(encoding="utf-8") == "x = 1\n"
    assert (halb / "main.py").read_text(
        encoding="utf-8"
    ) == "import u_main\n"
    vorher = natter / "Ampel (vorher)"
    assert vorher.exists() == bearbeitet
    if bearbeitet:
        assert (vorher / "main.py").read_text(
            encoding="utf-8"
        ) == "print(1)\n"


def test_zuruecksetzen_legt_keinen_ordner_nur_fuer_das_eigene_konto_an(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Punkt 397: `tempfile.mkdtemp` gibt einem Ordner unter Windows
    Rechte nur für das eigene Konto, und die Dateien, die daraus in
    die Kopie verschoben wurden, behielten sie. Nach dem Zurücksetzen
    konnte etwa die Lehrkraft die Kopie nicht mehr lesen."""
    import tempfile

    datei = _aufgabe(tmp_path / "Tausch" / "Ampel", "Ampel", "x = 1\n")
    kopie = aufgabe_kopieren(datei, tmp_path / "Natter")
    (kopie.parent / "u_main.py").write_text("x = 2\n", encoding="utf-8")

    def verboten(*_a, **_k):  # noqa: ANN002, ANN003, ANN202
        raise AssertionError("mkdtemp beim Zurücksetzen")

    monkeypatch.setattr(tempfile, "mkdtemp", verboten)
    startbild.aufgabe_zuruecksetzen(kopie.parent)

    assert (kopie.parent / "u_main.py").read_text(encoding="utf-8") == "x = 1\n"
