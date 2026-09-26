"""Tests für das signierte Prüfsummen-Manifest (ide/integritaet/).

Siehe docs/bericht.md, Abschnitt 7.5 und Arbeitspaket M8,
Schritt 4. Die Tests arbeiten mit einem Wegwerf-Schlüsselpaar und geben
den öffentlichen Teil beim Prüfen mit – der echte private Schlüssel
liegt bewusst nicht im Repository und darf deshalb auch in CI nicht
gebraucht werden.
"""

import json
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from ide.integritaet import (
    MANIFEST_DATEINAME,
    ManifestFehler,
    manifest_erstellen,
    manifest_pruefen,
    manifest_schreiben,
)
from ide.integritaet.start_pruefung import installation_pruefen, programmordner


@pytest.fixture
def schluesselpaar(tmp_path: Path) -> tuple[Path, str]:
    privat = Ed25519PrivateKey.generate()
    privat_pfad = tmp_path / "privat.pem"
    privat_pfad.write_bytes(
        privat.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    oeffentlich = (
        privat.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("ascii")
    )
    return privat_pfad, oeffentlich


#: Der Pfad, unter dem die Pakete der mitgelieferten Python liegen.
SP = "python/Lib/site-packages"


def _legen(ordner: Path, pfad: str, inhalt: bytes) -> Path:
    ziel = ordner / pfad
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_bytes(inhalt)
    return ziel


@pytest.fixture
def programm(tmp_path: Path) -> Path:
    """Ein Programmordner im Aufbau einer gebauten Installation.

    Seit M13 ist das kein eingefrorenes Bundle mehr, sondern
    `Natter.exe` neben einer gewöhnlichen Python-Installation - der
    Aufbau, den `tools/ide_paketieren.py` erzeugt.
    """
    ordner = tmp_path / "Natter"
    _legen(ordner, "Natter.exe", b"exe-inhalt")
    _legen(ordner, "python/pythonw.exe", b"pythonw")
    _legen(ordner, "python/Lib/os.py", b"stdlib")
    _legen(ordner, f"{SP}/ide/main.py", b"ide")
    _legen(ordner, f"{SP}/pcl/application.py", b"pcl")
    # Eine mitgelieferte Fremdbibliothek: sie darf sich ändern, ohne
    # dass Natter als verändert gilt.
    _legen(ordner, f"{SP}/numpy/__init__.py", b"numpy")
    _legen(ordner, "benutzer/mein_projekt.natter", b"{}")
    _legen(ordner, "pakete-zusatz/extra.py", b"x = 1")
    return ordner


def _pruefen(programm: Path, oeffentlich: str, **kwargs):
    return manifest_pruefen(programm, oeffentlicher_schluessel_pem=oeffentlich, **kwargs)


def test_manifest_erfasst_programmdateien_ohne_benutzerordner(programm: Path) -> None:
    """Abschnitt 17.8: „aller Programmdateien (ohne `benutzer/` und
    `pakete-zusatz/`)“ – dort ändert sich bestimmungsgemäß etwas."""
    dateien = manifest_erstellen(programm)["dateien"]

    assert set(dateien) == {
        "Natter.exe",
        "python/pythonw.exe",
        "python/Lib/os.py",
        f"{SP}/ide/main.py",
        f"{SP}/pcl/application.py",
    }


def test_unveraenderte_installation_ist_in_ordnung(programm, schluesselpaar) -> None:
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)

    ergebnis = _pruefen(programm, oeffentlich)

    assert ergebnis.in_ordnung
    assert ergebnis.als_meldung() == ""


def test_manifest_enthaelt_sich_nicht_selbst(programm, schluesselpaar) -> None:
    """Sonst könnte die Prüfung nie aufgehen: das Schreiben des
    Manifests verändert den Ordner, den es beschreibt."""
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)

    daten = json.loads((programm / MANIFEST_DATEINAME).read_text(encoding="utf-8"))

    assert MANIFEST_DATEINAME not in daten["manifest"]["dateien"]


def test_veraenderte_datei_wird_erkannt(programm, schluesselpaar) -> None:
    """Das M8-Abnahmekriterium: „veränderte Datei wird erkannt“."""
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    (programm / "python" / "Lib" / "os.py").write_bytes(b"manipuliert")

    ergebnis = _pruefen(programm, oeffentlich)

    assert not ergebnis.in_ordnung
    assert ergebnis.veraendert == ["python/Lib/os.py"]
    assert ergebnis.als_meldung().startswith("Natter wurde nach der Erstellung verändert:")
    assert "python/Lib/os.py (verändert)" in ergebnis.als_meldung()


def test_fehlende_datei_wird_erkannt(programm, schluesselpaar) -> None:
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    (programm / "python" / "Lib" / "os.py").unlink()

    ergebnis = _pruefen(programm, oeffentlich)

    assert ergebnis.fehlend == ["python/Lib/os.py"]


def test_fremde_datei_wird_erkannt(programm, schluesselpaar) -> None:
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    (programm / "python" / "Lib" / "eingeschleust.py").write_bytes(b"fremd")

    ergebnis = _pruefen(programm, oeffentlich)

    assert ergebnis.fremd == ["python/Lib/eingeschleust.py"]


def test_datei_im_benutzerordner_loest_keinen_alarm_aus(programm, schluesselpaar) -> None:
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    (programm / "benutzer" / "neues_projekt.natter").write_text("{}", encoding="utf-8")

    assert _pruefen(programm, oeffentlich).in_ordnung


def test_manipuliertes_manifest_faellt_ueber_die_signatur_auf(programm, schluesselpaar) -> None:
    """Wer eine Datei austauscht, müsste auch ihre Prüfsumme im Manifest
    anpassen – das macht die Signatur ungültig."""
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    (programm / "python" / "Lib" / "os.py").write_bytes(b"manipuliert")

    manifest_pfad = programm / MANIFEST_DATEINAME
    daten = json.loads(manifest_pfad.read_text(encoding="utf-8"))
    neue_summe = manifest_erstellen(programm)["dateien"]["python/Lib/os.py"]
    daten["manifest"]["dateien"]["python/Lib/os.py"] = neue_summe
    manifest_pfad.write_text(json.dumps(daten), encoding="utf-8")

    ergebnis = _pruefen(programm, oeffentlich)

    assert not ergebnis.signatur_gueltig
    assert "Signatur" in ergebnis.als_meldung()


def test_schnelle_pruefung_sieht_nur_die_kerndateien(programm, schluesselpaar) -> None:
    """Abschnitt 17.8: bei jedem Start schnell (Kerndateien), vollständig
    erst beim ersten Start bzw. über „Werkzeuge → Umgebung prüfen“."""
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    (programm / "python" / "Lib" / "os.py").write_bytes(b"manipuliert")

    assert _pruefen(programm, oeffentlich, nur_kern=True).in_ordnung
    assert not _pruefen(programm, oeffentlich, nur_kern=False).in_ordnung


def test_schnelle_pruefung_erkennt_eine_veraenderte_exe(programm, schluesselpaar) -> None:
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    (programm / "Natter.exe").write_bytes(b"manipuliert")

    assert not _pruefen(programm, oeffentlich, nur_kern=True).in_ordnung


# -- Die mitgelieferte Python-Installation (M13) ---------------------------


def test_uebersetzte_module_zaehlen_nicht(programm, schluesselpaar) -> None:
    """Python legt neben jedem Modul eine `.pyc` ab, sobald es das erste
    Mal importiert wird. Seit M13 liegt eine echte Python-Installation
    bei - in der gebauten Auslieferung nachgemessen waren es über
    achtzig solcher Dateien, bevor überhaupt ein Fenster offen war.
    Zählten sie mit, wäre jede Installation nach dem ersten Start
    „verändert“."""
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    _legen(programm, f"{SP}/ide/__pycache__/main.cpython-313.pyc", b"uebersetzt")
    _legen(programm, "python/Lib/__pycache__/os.cpython-313.pyc", b"uebersetzt")

    assert _pruefen(programm, oeffentlich).in_ordnung


def test_selbst_nachinstalliertes_paket_loest_keinen_alarm_aus(
    programm, schluesselpaar
) -> None:
    """Das Menü „Pakete“ ist eine vorgesehene Funktion. Was ein Schüler
    darüber holt, landet seit M13 ganz normal in `site-packages`."""
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    _legen(programm, f"{SP}/requests/__init__.py", b"requests")

    assert _pruefen(programm, oeffentlich).in_ordnung


def test_die_startdatei_eines_nachinstallierten_pakets_loest_keinen_alarm_aus(
    programm, schluesselpaar
) -> None:
    """pip legt zu einem Paket eine Startdatei in `python/Scripts` ab.
    Nach `cowsay` meldete „Umgebung prüfen“ in 0.3.3 „Natter wurde nach
    der Erstellung verändert: python/Scripts/cowsay.exe (zusätzlich)“
    (Punkt 40)."""
    privat, oeffentlich = schluesselpaar
    _legen(programm, "python/Scripts/pip.exe", b"pip")
    manifest_schreiben(programm, privat)
    _legen(programm, "python/Scripts/cowsay.exe", b"cowsay")
    _legen(programm, "python/Scripts/pip.exe", b"pip, angehoben")

    assert _pruefen(programm, oeffentlich).in_ordnung


def test_eine_neue_datei_in_der_python_selbst_faellt_weiter_auf(
    programm, schluesselpaar
) -> None:
    """Die Gegenprobe zu `python/Scripts`: daneben bleibt alles unter
    Aufsicht."""
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    _legen(programm, "python/fremd.dll", b"fremd")

    ergebnis = _pruefen(programm, oeffentlich)

    assert not ergebnis.in_ordnung
    assert "python/fremd.dll" in ergebnis.fremd


def test_eine_angehobene_bibliothek_loest_keinen_alarm_aus(programm, schluesselpaar) -> None:
    """`pip` löst beim Nachinstallieren Abhängigkeiten mit auf und hebt
    dabei ohne Rückfrage etwa numpy an. Stünde das unter Aufsicht,
    forderte Natter danach bei jedem Start zur Neuinstallation auf."""
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    _legen(programm, f"{SP}/numpy/__init__.py", b"neuere fassung")

    assert _pruefen(programm, oeffentlich).in_ordnung


def test_eingeschleuster_code_in_natters_eigenen_paketen_faellt_auf(
    programm, schluesselpaar
) -> None:
    """Die Gegenprobe zu den drei Tests darüber: in `ide` und `pcl`
    steht Natters eigener Code, und dort hat nichts Neues zu suchen."""
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    _legen(programm, f"{SP}/ide/eingeschleust.py", b"boeser code")

    ergebnis = _pruefen(programm, oeffentlich)

    assert ergebnis.fremd == [f"{SP}/ide/eingeschleust.py"]


def test_die_schnelle_pruefung_sieht_natters_eigenen_code(programm, schluesselpaar) -> None:
    """Abschnitt 17.8 zählt „IDE-Code, `pcl`“ ausdrücklich zur schnellen
    Prüfung. Seit M13 liegen beide in `site-packages` statt neben der
    Exe - ohne eigene Regel fielen sie aus der Prüfung bei jedem Start
    heraus."""
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    _legen(programm, f"{SP}/pcl/application.py", b"manipuliert")

    ergebnis = _pruefen(programm, oeffentlich, nur_kern=True)

    # Ausdrücklich „verändert“ und nicht bloß „nicht in Ordnung“: fiele
    # `pcl` aus den Kerndateien heraus, stünde dieselbe Datei als
    # „zusätzlich“ da - auch ein Alarm, aber der falsche.
    assert ergebnis.veraendert == [f"{SP}/pcl/application.py"]
    assert ergebnis.fremd == []


def test_die_schnelle_pruefung_liest_die_standardbibliothek_nicht(
    programm, schluesselpaar, monkeypatch
) -> None:
    """Sie läuft bei jedem Start. Die mitgelieferte Python bringt gut
    dreißigtausend Dateien mit; würden die alle gelesen, dauerte jeder
    Start Sekunden länger (in der Auslieferung gemessen: 2,7 s gegen
    0,07 s)."""
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)

    gelesen: list[str] = []
    echtes_lesen = Path.read_bytes

    def _mitschreiben(self: Path) -> bytes:
        gelesen.append(self.as_posix())
        return echtes_lesen(self)

    monkeypatch.setattr(Path, "read_bytes", _mitschreiben)
    _pruefen(programm, oeffentlich, nur_kern=True)

    assert not [pfad for pfad in gelesen if pfad.endswith("python/Lib/os.py")]


def test_fehlendes_manifest_meldet_einen_eigenen_fehler(programm) -> None:
    with pytest.raises(ManifestFehler):
        manifest_pruefen(programm)


def test_der_uninstaller_loest_keinen_alarm_aus(programm, schluesselpaar) -> None:
    """Inno Setup legt `unins000.exe` und `unins000.dat` neben
    `Natter.exe` - erst *während* der Installation, also lange nachdem
    das Manifest beim Bau geschrieben wurde. Ohne Ausnahme begrüßte
    jede frisch installierte Natter den Schüler mit „Natter wurde nach
    der Erstellung verändert" und der Aufforderung, neu zu
    installieren; die neue Installation legte den Uninstaller prompt
    wieder an (M13, an einer echten Installation aufgefallen)."""
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    _legen(programm, "unins000.exe", b"uninstaller")
    _legen(programm, "unins000.dat", b"eintraege")

    assert _pruefen(programm, oeffentlich, nur_kern=True).in_ordnung
    assert _pruefen(programm, oeffentlich).in_ordnung


def test_die_ausgelieferte_installation_wird_erkannt(programm, schluesselpaar, monkeypatch):
    """Seit M13 läuft Natter als gewöhnliches `pythonw.exe -m ide`.
    `sys.frozen` gibt es dort nicht mehr - würde weiter danach gefragt,
    fiele die Prüfung in der ausgelieferten Fassung stillschweigend ganz
    aus, und bemerkt hätte das niemand: sie meldet sich ja nur, wenn
    etwas nicht stimmt."""
    privat, _ = schluesselpaar
    manifest_schreiben(programm, privat)
    monkeypatch.setattr(sys, "executable", str(programm / "python" / "pythonw.exe"))

    assert programmordner() == programm


def test_ohne_natter_exe_daneben_gilt_es_nicht_als_installation(
    programm, monkeypatch
) -> None:
    """Die Gegenprobe: im Entwicklungsbaum zeigt derselbe Weg auf
    `.venv`, und dort liegt keine `Natter.exe`."""
    (programm / "Natter.exe").unlink()
    monkeypatch.setattr(sys, "executable", str(programm / "python" / "pythonw.exe"))

    assert programmordner() is None


def test_eine_installation_wird_auch_ohne_manifest_erkannt(programm, monkeypatch) -> None:
    """Bis 0.3.3 galt ein Ordner ohne `manifest.json` als
    Entwicklungsbaum - wer das Manifest löschte, schaltete die Prüfung
    ab (Punkt 27)."""
    monkeypatch.setattr(sys, "executable", str(programm / "python" / "pythonw.exe"))

    assert programmordner() == programm


def test_ein_fehlendes_manifest_ist_ein_befund(programm, monkeypatch) -> None:
    monkeypatch.setattr(sys, "executable", str(programm / "python" / "pythonw.exe"))

    ergebnis = installation_pruefen()

    assert ergebnis is not None
    assert not ergebnis.in_ordnung
    assert "manifest.json fehlt" in ergebnis.als_meldung()
    assert ergebnis.als_meldung().startswith("Natter wurde nach der Erstellung verändert")


def test_ein_unlesbares_manifest_ist_ein_befund(programm, monkeypatch) -> None:
    _legen(programm, "manifest.json", b"{ kein json")
    monkeypatch.setattr(sys, "executable", str(programm / "python" / "pythonw.exe"))

    ergebnis = installation_pruefen(vollstaendig=True)

    assert ergebnis is not None
    assert not ergebnis.in_ordnung
    assert "manifest.json ist unlesbar." in ergebnis.als_meldung()


def test_manifest_loeschen_verbirgt_keine_veraenderung(
    programm, schluesselpaar, monkeypatch
) -> None:
    """Der Weg aus der Auswertung zu 0.3.3: Kerndatei verändern und das
    Manifest löschen - bis dahin startete Natter ohne jede Meldung."""
    privat, _ = schluesselpaar
    manifest_schreiben(programm, privat)
    _legen(programm, f"{SP}/pcl/application.py", b"veraendert")
    (programm / "manifest.json").unlink()
    monkeypatch.setattr(sys, "executable", str(programm / "python" / "pythonw.exe"))

    assert not installation_pruefen().in_ordnung
    assert not installation_pruefen(vollstaendig=True).in_ordnung


def test_im_entwicklungsbaum_wird_nicht_geprueft() -> None:
    """`python -m ide` läuft nicht aus einer gebauten Installation –
    dort gibt es kein Manifest und soll auch keine Warnung geben."""
    assert programmordner() is None
    assert installation_pruefen() is None


# -- Verdrahtung in der IDE ------------------------------------------------


def test_start_laeuft_ohne_manifest_einfach_durch() -> None:
    from ide.main import erstellen, integritaet_bestaetigen

    _app, fenster = erstellen()

    assert integritaet_bestaetigen(fenster) is True


def test_veraenderte_installation_fragt_vor_dem_start_nach(monkeypatch) -> None:
    """Abschnitt 17.8: „Start nur nach Bestätigung“."""
    from PySide6.QtWidgets import QMessageBox

    from ide import main as ide_main
    from ide.integritaet import PruefErgebnis

    gezeigt = {}

    def _warnung(eltern, titel, text, *args, **kwargs):
        gezeigt["titel"] = titel
        gezeigt["text"] = text
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "warning", staticmethod(_warnung))
    monkeypatch.setattr(
        ide_main,
        "installation_pruefen",
        lambda *a, **k: PruefErgebnis(signatur_gueltig=True, veraendert=["python/Lib/os.py"]),
    )
    _app, fenster = ide_main.erstellen()

    assert ide_main.integritaet_bestaetigen(fenster) is False
    assert "Natter wurde nach der Erstellung verändert" in gezeigt["text"]


def test_werkzeuge_umgebung_pruefen_listet_betroffene_dateien(monkeypatch, qtbot) -> None:
    from ide.integritaet import PruefErgebnis
    from ide.shell import hauptfenster as hauptfenster_modul
    from ide.shell.hauptfenster import HauptFenster

    monkeypatch.setattr(hauptfenster_modul, "programmordner", lambda: Path("C:/Natter"))
    monkeypatch.setattr(
        hauptfenster_modul,
        "installation_pruefen",
        lambda *a, **k: PruefErgebnis(
            signatur_gueltig=True, veraendert=["python/Lib/os.py"], fehlend=["Lizenzen/Qt.txt"]
        ),
    )
    fenster = HauptFenster()

    fenster.aktionen["werkzeuge.umgebung_pruefen"].qaction.trigger()
    qtbot.waitUntil(lambda: fenster.meldungen_liste.count() >= 2, timeout=5000)

    eintraege = [
        fenster.meldungen_liste.item(i).text() for i in range(fenster.meldungen_liste.count())
    ]
    assert "[Umgebung] python/Lib/os.py" in eintraege
    assert "[Umgebung] Lizenzen/Qt.txt" in eintraege


def test_umgebung_pruefen_haelt_die_oberflaeche_nicht_an(monkeypatch, qtbot) -> None:
    """Punkt 33: die vollständige Prüfung dauert in einer Installation
    2,4 s; bis 0.3.3 lief sie im Faden der Oberfläche."""
    import time

    from ide.integritaet import PruefErgebnis
    from ide.shell import hauptfenster as hauptfenster_modul
    from ide.shell.hauptfenster import HauptFenster

    def langsam(*_a, **_k):
        time.sleep(1.0)
        return PruefErgebnis(signatur_gueltig=True)

    monkeypatch.setattr(hauptfenster_modul, "programmordner", lambda: Path("C:/Natter"))
    monkeypatch.setattr(hauptfenster_modul, "installation_pruefen", langsam)
    fenster = HauptFenster()

    start = time.perf_counter()
    fenster.aktionen["werkzeuge.umgebung_pruefen"].qaction.trigger()
    dauer = time.perf_counter() - start

    assert dauer < 0.5
    qtbot.waitUntil(
        lambda: "unverändert" in fenster.statusBar().currentMessage(), timeout=5000
    )


def test_ein_fehlendes_manifest_steht_im_panel(monkeypatch, qtbot) -> None:
    from ide.integritaet import PruefErgebnis
    from ide.shell import hauptfenster as hauptfenster_modul
    from ide.shell.hauptfenster import HauptFenster

    monkeypatch.setattr(hauptfenster_modul, "programmordner", lambda: Path("C:/Natter"))
    monkeypatch.setattr(
        hauptfenster_modul,
        "installation_pruefen",
        lambda *a, **k: PruefErgebnis(
            signatur_gueltig=False, manifest_fehler="manifest.json fehlt in C:\\Natter."
        ),
    )
    fenster = HauptFenster()

    fenster.aktionen["werkzeuge.umgebung_pruefen"].qaction.trigger()
    qtbot.waitUntil(lambda: fenster.meldungen_liste.count() >= 1, timeout=5000)

    assert fenster.meldungen_liste.item(0).text() == "[Umgebung] manifest.json fehlt in C:\\Natter."
