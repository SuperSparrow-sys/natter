"""Tests für das signierte Prüfsummen-Manifest (ide/integritaet/).

Siehe konzept-natter.md, Abschnitt 17.8 und docs/arbeitspakete/M8.md,
Schritt 4. Die Tests arbeiten mit einem Wegwerf-Schlüsselpaar und geben
den öffentlichen Teil beim Prüfen mit – der echte private Schlüssel
liegt bewusst nicht im Repository und darf deshalb auch in CI nicht
gebraucht werden.
"""

import json
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


@pytest.fixture
def programm(tmp_path: Path) -> Path:
    """Ein Programmordner im Aufbau einer gebauten Installation."""
    ordner = tmp_path / "Natter"
    (ordner / "_internal").mkdir(parents=True)
    (ordner / "benutzer").mkdir()
    (ordner / "pakete-zusatz").mkdir()
    (ordner / "Natter.exe").write_bytes(b"exe-inhalt")
    (ordner / "_internal" / "base_library.zip").write_bytes(b"stdlib")
    (ordner / "_internal" / "qt.dll").write_bytes(b"qt")
    (ordner / "benutzer" / "mein_projekt.natter").write_text("{}", encoding="utf-8")
    (ordner / "pakete-zusatz" / "extra.py").write_text("x = 1", encoding="utf-8")
    return ordner


def _pruefen(programm: Path, oeffentlich: str, **kwargs):
    return manifest_pruefen(programm, oeffentlicher_schluessel_pem=oeffentlich, **kwargs)


def test_manifest_erfasst_programmdateien_ohne_benutzerordner(programm: Path) -> None:
    """Abschnitt 17.8: „aller Programmdateien (ohne `benutzer/` und
    `pakete-zusatz/`)“ – dort ändert sich bestimmungsgemäß etwas."""
    dateien = manifest_erstellen(programm)["dateien"]

    assert set(dateien) == {"Natter.exe", "_internal/base_library.zip", "_internal/qt.dll"}


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
    (programm / "_internal" / "qt.dll").write_bytes(b"manipuliert")

    ergebnis = _pruefen(programm, oeffentlich)

    assert not ergebnis.in_ordnung
    assert ergebnis.veraendert == ["_internal/qt.dll"]
    assert ergebnis.als_meldung().startswith("Natter wurde nach der Erstellung verändert:")
    assert "_internal/qt.dll (verändert)" in ergebnis.als_meldung()


def test_fehlende_datei_wird_erkannt(programm, schluesselpaar) -> None:
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    (programm / "_internal" / "qt.dll").unlink()

    ergebnis = _pruefen(programm, oeffentlich)

    assert ergebnis.fehlend == ["_internal/qt.dll"]


def test_fremde_datei_wird_erkannt(programm, schluesselpaar) -> None:
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    (programm / "_internal" / "eingeschleust.dll").write_bytes(b"fremd")

    ergebnis = _pruefen(programm, oeffentlich)

    assert ergebnis.fremd == ["_internal/eingeschleust.dll"]


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
    (programm / "_internal" / "qt.dll").write_bytes(b"manipuliert")

    manifest_pfad = programm / MANIFEST_DATEINAME
    daten = json.loads(manifest_pfad.read_text(encoding="utf-8"))
    neue_summe = manifest_erstellen(programm)["dateien"]["_internal/qt.dll"]
    daten["manifest"]["dateien"]["_internal/qt.dll"] = neue_summe
    manifest_pfad.write_text(json.dumps(daten), encoding="utf-8")

    ergebnis = _pruefen(programm, oeffentlich)

    assert not ergebnis.signatur_gueltig
    assert "Signatur" in ergebnis.als_meldung()


def test_schnelle_pruefung_sieht_nur_die_kerndateien(programm, schluesselpaar) -> None:
    """Abschnitt 17.8: bei jedem Start schnell (Kerndateien), vollständig
    erst beim ersten Start bzw. über „Werkzeuge → Umgebung prüfen“."""
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    (programm / "_internal" / "qt.dll").write_bytes(b"manipuliert")

    assert _pruefen(programm, oeffentlich, nur_kern=True).in_ordnung
    assert not _pruefen(programm, oeffentlich, nur_kern=False).in_ordnung


def test_schnelle_pruefung_erkennt_eine_veraenderte_exe(programm, schluesselpaar) -> None:
    privat, oeffentlich = schluesselpaar
    manifest_schreiben(programm, privat)
    (programm / "Natter.exe").write_bytes(b"manipuliert")

    assert not _pruefen(programm, oeffentlich, nur_kern=True).in_ordnung


def test_fehlendes_manifest_meldet_einen_eigenen_fehler(programm) -> None:
    with pytest.raises(ManifestFehler):
        manifest_pruefen(programm)


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
        lambda *a, **k: PruefErgebnis(signatur_gueltig=True, veraendert=["_internal/qt.dll"]),
    )
    _app, fenster = ide_main.erstellen()

    assert ide_main.integritaet_bestaetigen(fenster) is False
    assert "Natter wurde nach der Erstellung verändert" in gezeigt["text"]


def test_werkzeuge_umgebung_pruefen_listet_betroffene_dateien(monkeypatch) -> None:
    from ide.integritaet import PruefErgebnis
    from ide.shell import hauptfenster as hauptfenster_modul
    from ide.shell.hauptfenster import HauptFenster

    monkeypatch.setattr(
        hauptfenster_modul,
        "installation_pruefen",
        lambda *a, **k: PruefErgebnis(
            signatur_gueltig=True, veraendert=["_internal/qt.dll"], fehlend=["Lizenzen/Qt.txt"]
        ),
    )
    fenster = HauptFenster()

    fenster.aktionen["werkzeuge.umgebung_pruefen"].qaction.trigger()

    eintraege = [
        fenster.meldungen_liste.item(i).text() for i in range(fenster.meldungen_liste.count())
    ]
    assert "[Umgebung] _internal/qt.dll" in eintraege
    assert "[Umgebung] Lizenzen/Qt.txt" in eintraege
