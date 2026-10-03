"""Datendateien im Explorer, Projektordner öffnen, Abgabe als ZIP
(Punkt 104)."""

from __future__ import annotations

import json
import os
import sys
import zipfile
from pathlib import Path

import pytest

from ide.project import Projekt
from ide.shell.explorer import PFAD_ROLLE


@pytest.fixture
def ordner(tmp_path: Path) -> Path:
    ordner = tmp_path / "Wetter"
    (ordner / "daten").mkdir(parents=True)
    (ordner / "__pycache__").mkdir()
    (ordner / "main.py").write_text("import u_main\n", encoding="utf-8")
    (ordner / "u_main.py").write_text("x = 1\n", encoding="utf-8")
    (ordner / "daten" / "wetter.csv").write_text("Ort;Grad\nHamburg;12\n", encoding="utf-8")
    (ordner / "notizen.txt").write_text("Hallo\n", encoding="utf-8")
    (ordner / "__pycache__" / "u_main.cpython-313.pyc").write_bytes(b"\x00")
    (ordner / "Wetter.natter").write_text(json.dumps({
        "format": "natter-project/1", "name": "Wetter", "type": "console", "main": "main.py",
    }), encoding="utf-8")
    return ordner


@pytest.fixture(autouse=True)
def anmeldename(monkeypatch: pytest.MonkeyPatch) -> str:
    """Ein fester Anmelde- und Rechnername; beide stehen im Namen der
    Abgabe."""
    import getpass

    monkeypatch.setattr(getpass, "getuser", lambda: "mueller.anna")
    monkeypatch.setenv("COMPUTERNAME", "PC-R12")
    return "mueller.anna"


@pytest.fixture
def mit_verknuepfungen(ordner: Path, tmp_path: Path) -> Path:
    """Die Anordnung aus Punkt 252: im Projekt eine Junction auf einen
    fremden Ordner und eine auf den Projektordner selbst. Beides geht
    ohne Verwaltungsrechte."""
    if sys.platform != "win32":
        pytest.skip("Junctions gibt es nur unter Windows.")
    import _winapi

    fremd = tmp_path / "fremd"
    fremd.mkdir()
    (fremd / "geheim.txt").write_text("fremd\n", encoding="utf-8")
    _winapi.CreateJunction(str(fremd), str(ordner / "daten" / "verweis"))
    _winapi.CreateJunction(str(ordner), str(ordner / "schleife"))
    return ordner


def test_weitere_dateien_betreten_keine_verknuepfung(
    mit_verknuepfungen: Path,
) -> None:
    projekt = Projekt.laden(mit_verknuepfungen)

    namen = [
        p.relative_to(mit_verknuepfungen).as_posix()
        for p in projekt.weitere_dateien()
    ]

    assert namen == ["daten/wetter.csv", "notizen.txt"]


def test_die_zip_nimmt_nichts_ueber_verknuepfungen_mit(
    qtbot, mit_verknuepfungen: Path, tmp_path: Path, hauptfenster
) -> None:  # noqa: ANN001
    hauptfenster.projekt_oeffnen(mit_verknuepfungen / "Wetter.natter")
    ziel = tmp_path / "abgabe.zip"

    anzahl = hauptfenster.projekt_als_zip(ziel)

    with zipfile.ZipFile(ziel) as archiv:
        namen = sorted(archiv.namelist())
    assert namen == [
        "Wetter - mueller.anna - PC-R12/Wetter.natter",
        "Wetter - mueller.anna - PC-R12/daten/wetter.csv",
        "Wetter - mueller.anna - PC-R12/main.py",
        "Wetter - mueller.anna - PC-R12/notizen.txt",
        "Wetter - mueller.anna - PC-R12/u_main.py",
    ]
    assert anzahl == len(namen)


def test_weitere_dateien(ordner: Path) -> None:
    projekt = Projekt.laden(ordner)

    namen = [p.relative_to(ordner).as_posix() for p in projekt.weitere_dateien()]

    assert namen == ["daten/wetter.csv", "notizen.txt"]


def test_explorer_zeigt_die_gruppe_dateien(
    qtbot, ordner: Path, hauptfenster
) -> None:  # noqa: ANN001
    hauptfenster.projekt_oeffnen(ordner / "Wetter.natter")
    gruppe = hauptfenster.explorer.dateien_gruppe

    eintraege = [gruppe.child(i).text(0) for i in range(gruppe.childCount())]

    assert not gruppe.isHidden()
    assert eintraege == ["daten/wetter.csv", "notizen.txt"]
    hauptfenster._bei_explorer_doppelklick(gruppe.child(1), 0)
    assert Path(gruppe.child(1).data(0, PFAD_ROLLE)).name == "notizen.txt"
    assert hauptfenster.editor_tabs.count() >= 1


def test_als_zip_speichern(
    qtbot, ordner: Path, tmp_path: Path, hauptfenster
) -> None:  # noqa: ANN001
    hauptfenster.projekt_oeffnen(ordner / "Wetter.natter")
    editor = hauptfenster.datei_oeffnen(ordner / "u_main.py")
    editor.setPlainText("x = 2\n")
    editor.document().setModified(True)
    ziel = tmp_path / "abgabe.zip"

    anzahl = hauptfenster.projekt_als_zip(ziel)

    with zipfile.ZipFile(ziel) as archiv:
        namen = sorted(archiv.namelist())
        inhalt = archiv.read("Wetter - mueller.anna - PC-R12/u_main.py").decode("utf-8")
        assert inhalt.replace("\r\n", "\n") == "x = 2\n"
    assert anzahl == len(namen)
    assert "Wetter - mueller.anna - PC-R12/daten/wetter.csv" in namen
    assert not any("__pycache__" in n for n in namen)


def test_keine_zip_wenn_eine_datei_nicht_gespeichert_wurde(
    qtbot, ordner: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster_bauen  # noqa: ANN001
) -> None:
    """Punkt 210: ließ sich eine geänderte Unit nicht schreiben, wäre
    in der ZIP der alte Stand gelandet."""
    import os
    import stat

    from PySide6.QtWidgets import QFileDialog, QMessageBox

    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda _eltern, _titel, text: meldungen.append(text)),
    )
    fenster = hauptfenster_bauen()
    # Seit Punkt 506 kommt die Meldung beim Speichern aus dem Editor als
    # Frage mit „Speichern unter …“; die Antwort ist „Abbrechen“.
    monkeypatch.setattr(
        type(fenster), "_speichern_unter_anbieten",
        lambda self, text: meldungen.append(text) or False,
    )
    fenster.projekt_oeffnen(ordner / "Wetter.natter")
    editor = fenster.datei_oeffnen(ordner / "u_main.py")
    editor.setPlainText("x = 2\n")
    editor.document().setModified(True)
    unit = ordner / "u_main.py"
    os.chmod(unit, stat.S_IREAD)
    ziel = tmp_path / "abgabe.zip"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *args, **kwargs: (str(ziel), "")),
    )
    try:
        assert fenster.projekt_als_zip(ziel) is None
        assert not ziel.exists()

        fenster._als_zip_aktion()
        assert not ziel.exists()
        assert "Keine ZIP" in fenster.statusBar().currentMessage()
    finally:
        os.chmod(unit, stat.S_IREAD | stat.S_IWRITE)
    assert meldungen
    assert editor.document().isModified()


def test_die_abgabe_traegt_den_anmeldenamen(
    qtbot, ordner: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster, hintergrund_abwarten,
) -> None:  # noqa: ANN001
    """Punkt 323: hießen alle Abgaben einer Klasse `Wetter.zip` und
    entpackten sich nach `Wetter/`, ersetzte eine die andere.
    Seit Punkt 396 steht auch der Rechner im Namen."""
    from PySide6.QtWidgets import QFileDialog

    vorschlaege: list[str] = []
    ziel = tmp_path / "abgabe.zip"

    def speichern_unter(_eltern, _titel, vorschlag, _filter):  # noqa: ANN001, ANN202
        vorschlaege.append(vorschlag)
        return str(ziel), ""

    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(speichern_unter)
    )
    hauptfenster.projekt_oeffnen(ordner / "Wetter.natter")

    hauptfenster._als_zip_aktion()
    hintergrund_abwarten(hauptfenster)

    assert Path(vorschlaege[0]).name == "Wetter - mueller.anna - PC-R12.zip"
    with zipfile.ZipFile(ziel) as archiv:
        ordner_in_der_zip = {n.split("/")[0] for n in archiv.namelist()}
    assert ordner_in_der_zip == {"Wetter - mueller.anna - PC-R12"}


def test_eine_gesperrte_datei_hinterlaesst_keine_zip(
    qtbot, ordner: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster, hintergrund_abwarten,
) -> None:  # noqa: ANN001
    """Punkt 343: eine CSV, die Excel offen hält, brach die ZIP mitten
    im Schreiben ab. Am Ziel blieb eine leere ZIP liegen, die wie eine
    Abgabe aussah, und gemeldet wurde der englische Text von Windows
    in der Statuszeile."""
    if sys.platform != "win32":
        pytest.skip("Die Sperre ohne Freigabe gibt es nur unter Windows.")
    import _winapi

    from PySide6.QtWidgets import QFileDialog, QMessageBox

    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda _eltern, _titel, text: meldungen.append(text)),
    )
    abgabe = tmp_path / "Abgabe"
    abgabe.mkdir()
    ziel = abgabe / "Wetter - mueller.anna - PC-R12.zip"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *args, **kwargs: (str(ziel), "")),
    )
    hauptfenster.projekt_oeffnen(ordner / "Wetter.natter")

    # So hält Excel eine geöffnete CSV: ohne Freigabe für andere.
    griff = _winapi.CreateFile(
        str(ordner / "daten" / "wetter.csv"), _winapi.GENERIC_READ, 0,
        0, _winapi.OPEN_EXISTING, 0, 0,
    )
    try:
        hauptfenster._als_zip_aktion()
        hintergrund_abwarten(hauptfenster)
    finally:
        _winapi.CloseHandle(griff)

    assert list(abgabe.iterdir()) == []
    assert len(meldungen) == 1
    assert str(Path("daten", "wetter.csv")) in meldungen[0]
    assert "anderen Programm" in meldungen[0]
    assert "Errno" not in meldungen[0]


def test_abgabe_in_einen_ordner_nur_zum_anlegen(
    qtbot, ordner: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster, hintergrund_abwarten,
) -> None:  # noqa: ANN001
    """Punkt 363: in einem Einsammelordner, in dem nur Anlegen erlaubt
    ist, ließ sich die Zwischendatei neben dem Ziel nicht umbenennen.
    Die Abgabe scheiterte, und die Zwischendatei blieb sichtbar liegen.
    Nachgestellt mit den Rechten, die Schulen für solche Ordner
    vergeben: lesen und anlegen, aber nicht löschen."""
    if sys.platform != "win32":
        pytest.skip("Die Rechte werden mit icacls gesetzt.")
    import os
    import subprocess

    from PySide6.QtWidgets import QFileDialog, QMessageBox

    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda _eltern, _titel, text: meldungen.append(text)),
    )
    abgabe = tmp_path / "Abgabe"
    abgabe.mkdir()
    ziel = abgabe / "Wetter - mueller.anna - PC-R12.zip"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *args, **kwargs: (str(ziel), "")),
    )
    hauptfenster.projekt_oeffnen(ordner / "Wetter.natter")

    konto = os.environ["USERDOMAIN"] + "\\" + os.environ["USERNAME"]

    def icacls(*argumente: str) -> None:
        subprocess.run(
            ["icacls", str(abgabe), *argumente],
            check=True, capture_output=True, timeout=30,
        )

    icacls("/inheritance:r", "/grant:r", f"{konto}:(OI)(CI)(RX,W)")
    try:
        # Die Probe selbst: umbenennen muss hier verboten sein. Ein
        # Konto mit Verwaltungsrechten (etwa auf dem CI-Rechner)
        # darf es trotzdem; dann lässt sich der Einsammelordner hier
        # nicht nachstellen.
        probe = abgabe / "probe.txt"
        probe.write_text("x", encoding="utf-8")
        try:
            probe.rename(abgabe / "probe2.txt")
        except PermissionError:
            pass
        else:
            pytest.skip("Das Konto darf trotz der Rechte umbenennen.")

        hauptfenster._als_zip_aktion()
        hintergrund_abwarten(hauptfenster)
    finally:
        icacls("/grant:r", f"{konto}:(OI)(CI)F")
        icacls("/reset", "/T")

    assert meldungen == []
    assert sorted(p.name for p in abgabe.iterdir()) == [
        "Wetter - mueller.anna - PC-R12.zip", "probe.txt",
    ]
    with zipfile.ZipFile(ziel) as archiv:
        assert "Wetter - mueller.anna - PC-R12/main.py" in archiv.namelist()


@pytest.mark.parametrize("abbrueche", [1, 2])
def test_eine_gescheiterte_zweite_abgabe_laesst_die_erste_stehen(
    qtbot, ordner: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster, hintergrund_abwarten, abbrueche: int,
) -> None:  # noqa: ANN001
    """Punkt 372: wurde eine vorhandene ZIP noch einmal gespeichert und
    brach das Schreiben am Ziel ab (Kontingent voll, USB-Stick
    abgezogen), lag danach eine abgeschnittene Datei dort, und die
    vollständige frühere Abgabe war verloren. Nachgebildet wird ein
    Abbruch nach 100.000 Byte beim ersten Schreiben ans Ziel. Bricht
    auch das Zurückschreiben der alten ZIP ab, muss die Meldung sagen,
    dass sie nicht mehr vollständig ist."""
    import errno
    import shutil

    from PySide6.QtWidgets import QFileDialog, QMessageBox

    meldungen: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        staticmethod(lambda _eltern, _titel, text: meldungen.append(text)),
    )
    ziel = tmp_path / "Wetter - mueller.anna - PC-R12.zip"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *args, **kwargs: (str(ziel), "")),
    )
    # Groß genug, dass der Abbruch mitten in der ZIP liegt.
    (ordner / "daten" / "gross.bin").write_bytes(os.urandom(300_000))
    hauptfenster.projekt_oeffnen(ordner / "Wetter.natter")
    hauptfenster.projekt_als_zip(ziel)
    vorher = ziel.read_bytes()
    (ordner / "notizen.txt").write_text("Korrigiert\n", encoding="utf-8")

    echt = shutil.copyfileobj
    abgebrochen: list[bool] = []

    def copyfileobj(quelle, aus, *args, **kwargs) -> None:  # noqa: ANN001
        if (
            Path(getattr(aus, "name", "")) == ziel
            and len(abgebrochen) < abbrueche
        ):
            abgebrochen.append(True)
            aus.write(quelle.read(100_000))
            raise OSError(errno.ENOSPC, "Nicht genügend Speicher")
        echt(quelle, aus, *args, **kwargs)

    monkeypatch.setattr(shutil, "copyfileobj", copyfileobj)

    hauptfenster._als_zip_aktion()
    hintergrund_abwarten(hauptfenster)

    assert len(abgebrochen) == abbrueche
    assert len(meldungen) == 1
    if abbrueche == 2:
        assert "nicht mehr vollständig" in meldungen[0]
        return
    assert "nicht mehr vollständig" not in meldungen[0]
    assert ziel.read_bytes() == vorher
    with zipfile.ZipFile(ziel) as archiv:
        assert archiv.read(
            "Wetter - mueller.anna - PC-R12/notizen.txt"
        ).replace(b"\r\n", b"\n") == b"Hallo\n"


def test_schon_gepackte_dateien_kommen_unveraendert_in_die_zip(
    qtbot, ordner: Path, tmp_path: Path, hauptfenster,
) -> None:  # noqa: ANN001
    """Punkt 388: Fotos, Musik und Archive wurden noch einmal gepackt.
    Kleiner wurden sie dabei kaum, bei 100 MB Fotos stand Natter aber
    über zehn Sekunden still. Quelltext und Daten werden weiter
    gepackt."""
    for name in ("foto.JPG", "bild.png", "lied.mp3", "alt.zip", "text.pdf"):
        (ordner / "daten" / name).write_bytes(os.urandom(2000))
    hauptfenster.projekt_oeffnen(ordner / "Wetter.natter")
    ziel = tmp_path / "abgabe.zip"

    hauptfenster.projekt_als_zip(ziel)

    with zipfile.ZipFile(ziel) as archiv:
        arten = {
            i.filename.split("/", 1)[1]: i.compress_type
            for i in archiv.infolist()
        }
    ungepackt = {n for n, art in arten.items() if art == zipfile.ZIP_STORED}
    assert ungepackt == {
        "daten/foto.JPG", "daten/bild.png", "daten/lied.mp3",
        "daten/alt.zip", "daten/text.pdf",
    }
    assert arten["main.py"] == zipfile.ZIP_DEFLATED
    assert arten["daten/wetter.csv"] == zipfile.ZIP_DEFLATED


def test_als_zip_speichern_haelt_natter_nicht_an(
    qtbot, ordner: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster, hintergrund_abwarten,
) -> None:  # noqa: ANN001
    """Punkt 388: ein Projekt mit 100 Fotos zu 1 MB über eine
    vorhandene ZIP speichern. Bis 0.3.x lief das im Faden der
    Oberfläche, und eine Uhr im Fenster setzte 13 Sekunden aus.
    Zufallsdaten lassen sich so wenig packen wie Fotos."""
    import time

    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QFileDialog

    (ordner / "bilder").mkdir()
    for i in range(100):
        (ordner / "bilder" / f"foto{i:03}.jpg").write_bytes(
            os.urandom(1_000_000)
        )
    ziel = tmp_path / "Wetter - mueller.anna - PC-R12.zip"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *args, **kwargs: (str(ziel), "")),
    )
    hauptfenster.projekt_oeffnen(ordner / "Wetter.natter")
    hauptfenster.projekt_als_zip(ziel)
    (ordner / "notizen.txt").write_text("Korrigiert\n", encoding="utf-8")
    takte: list[float] = []
    uhr = QTimer()
    uhr.setInterval(20)
    uhr.timeout.connect(lambda: takte.append(time.perf_counter()))
    uhr.start()
    qtbot.wait(100)

    hauptfenster._als_zip_aktion()
    lauf = hauptfenster._hintergrundarbeit
    if lauf is not None:
        qtbot.waitUntil(lauf.isFinished, timeout=60_000)
    qtbot.wait(100)
    uhr.stop()

    pausen = [b - a for a, b in zip(takte, takte[1:], strict=False)]
    assert max(pausen) < 1.0
    hintergrund_abwarten(hauptfenster)
    with zipfile.ZipFile(ziel) as archiv:
        assert len(archiv.namelist()) == 105
        assert archiv.read(
            "Wetter - mueller.anna - PC-R12/notizen.txt"
        ).replace(b"\r\n", b"\n") == b"Korrigiert\n"
    assert hauptfenster.statusBar().currentMessage() == (
        f"105 Dateien in {ziel.name} gespeichert."
    )


def test_ein_gemeinsames_konto_gibt_an_zwei_rechnern_nebeneinander_ab(
    ordner: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Punkt 396: mit einem Konto für alle, etwa „schueler“, schlug
    Natter an jedem Rechner denselben Namen vor, und im gemeinsamen
    Einsammelordner ersetzte jede Abgabe die vorige."""
    import getpass

    from ide.shell.hauptfenster import abgabe_name, zip_schreiben

    monkeypatch.setattr(getpass, "getuser", lambda: "schueler")
    einsammeln = tmp_path / "Einsammeln"
    einsammeln.mkdir()
    for rechner in ("PC-R01", "PC-R02"):
        monkeypatch.setenv("COMPUTERNAME", rechner)
        name = abgabe_name(ordner.name)
        zip_schreiben(ordner, name, einsammeln / f"{name}.zip")

    assert sorted(p.name for p in einsammeln.iterdir()) == [
        "Wetter - schueler - PC-R01.zip",
        "Wetter - schueler - PC-R02.zip",
    ]


@pytest.mark.parametrize("fall", ["gelungen", "gesperrt", "zu_langsam"])
def test_beim_schliessen_waehrend_der_zip_kommt_das_ergebnis(
    qtbot, ordner: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    hauptfenster, fall: str,
) -> None:  # noqa: ANN001
    """Punkt 394: wurde Natter geschlossen, während die Abgabe-ZIP
    noch entstand, lösten sich die Signale, und weder eine gelungene
    noch eine gescheiterte Abgabe wurde gemeldet. Die ZIP wird hier
    künstlich verlangsamt, damit sie beim Schließen sicher noch läuft.
    Bei „zu_langsam“ reißt die Zeitgrenze beim Schließen, und am Ziel
    darf nichts liegen."""
    import time

    from PySide6.QtWidgets import QFileDialog, QMessageBox

    import ide.shell.hauptfenster as modul

    if fall == "gesperrt" and sys.platform != "win32":
        pytest.skip("Die Sperre ohne Freigabe gibt es nur unter Windows.")
    meldungen: list[tuple[str, str]] = []
    for art in ("warning", "information"):
        monkeypatch.setattr(
            QMessageBox, art,
            staticmethod(
                lambda _eltern, titel, text: meldungen.append((titel, text))
            ),
        )
    echt = modul.zip_schreiben

    def langsam(ordner, oben, ziel, melden):  # noqa: ANN001, ANN202
        def zaeh(prozent: int, text: str) -> None:
            time.sleep(0.4)
            melden(prozent, text)

        return echt(ordner, oben, ziel, zaeh)

    monkeypatch.setattr(modul, "zip_schreiben", langsam)
    if fall == "zu_langsam":
        monkeypatch.setattr(
            modul.HauptFenster, "_ZIP_GEDULD", 0.2, raising=False
        )
    abgabe = tmp_path / "Abgabe"
    abgabe.mkdir()
    ziel = abgabe / "Wetter - mueller.anna - PC-R12.zip"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *args, **kwargs: (str(ziel), "")),
    )
    hauptfenster.projekt_oeffnen(ordner / "Wetter.natter")
    griff = None
    if fall == "gesperrt":
        import _winapi

        griff = _winapi.CreateFile(
            str(ordner / "daten" / "wetter.csv"), _winapi.GENERIC_READ,
            0, 0, _winapi.OPEN_EXISTING, 0, 0,
        )
    try:
        hauptfenster._als_zip_aktion()
        lauf = hauptfenster._hintergrundarbeit
        assert lauf.isRunning()
        hauptfenster.close()
    finally:
        if griff is not None:
            _winapi.CloseHandle(griff)

    assert not lauf.isRunning()
    assert not hauptfenster.isVisible()
    assert len(meldungen) == 1
    titel, text = meldungen[0]
    if fall == "gelungen":
        assert titel == "ZIP gespeichert"
        with zipfile.ZipFile(ziel) as archiv:
            assert len(archiv.namelist()) == 5
    else:
        assert titel == "Keine ZIP gespeichert"
        assert list(abgabe.iterdir()) == []
        erwartet = {
            "gesperrt": "anderen Programm",
            "zu_langsam": "noch nicht fertig",
        }[fall]
        assert erwartet in text
