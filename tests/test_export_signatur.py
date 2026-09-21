"""Die exportierte Exe wird signiert, wenn ein Zertifikat da ist.

Smart App Control prüft jede Datei, die geladen wird. Eine frisch
gebaute Exe ist unsigniert und hat keinen Ruf im Netz - das Programm
einer Schülerin wird auf einem solchen Rechner abgeschossen, bevor es
sein Fenster zeigt.

Die Grenze, die diese Tests bewachen: Natters privater Schlüssel
gehört nicht in die Auslieferung. Läge er dort, könnte jede
Installation beliebigen Code mit einem Zertifikat signieren, das auf
allen Schulrechnern als vertrauenswürdig eingetragen ist.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ide.export import signatur

WURZEL = Path(__file__).resolve().parent.parent


class _Antwort:
    """Was `subprocess.run` zurückgibt."""

    def __init__(self, stdout: str = "", stderr: str = "", returncode: int = 0) -> None:
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


# --------------------------------------- Die Grenze, die nicht fällt


def test_der_private_schluessel_liegt_nicht_in_der_auslieferung() -> None:
    """Der Kern der ganzen Abwägung: die `.pfx` darf weder im Paket
    noch im Repository landen. Wer sie hat, signiert im Namen von
    Natter - auf jedem Rechner, der das Zertifikat eingetragen hat,
    und ohne dass sich das widerrufen ließe."""
    verboten = []
    for muster in ("*.pfx", "*passwort*", "*.p12", "*.key"):
        for pfad in WURZEL.rglob(muster):
            if any(teil in pfad.parts for teil in (".venv", "build", "dist", ".git")):
                continue
            verboten.append(pfad.relative_to(WURZEL).as_posix())

    versehentlich = [p for p in verboten if not p.startswith("tools/signieren/")]
    assert not versehentlich, f"Schlüsselmaterial außerhalb tools/signieren/: {versehentlich}"


def test_die_pfx_ist_von_git_ausgeschlossen() -> None:
    gitignore = (WURZEL / ".gitignore").read_text(encoding="utf-8")

    assert "*.pfx" in gitignore
    assert "passwort" in gitignore


def test_das_modul_kennt_keinen_pfad_zu_einem_privaten_schluessel() -> None:
    """Es signiert über den Zertifikatspeicher. Ein Dateipfad im
    Quelltext wäre der erste Schritt dahin, den Schlüssel doch
    mitzuliefern."""
    quelle = (WURZEL / "ide" / "export" / "signatur.py").read_text(encoding="utf-8")

    assert ".pfx" not in quelle
    assert "-Password" not in quelle


# --------------------------------------- Was ohne Zertifikat geschieht


def test_ohne_zertifikat_wird_nicht_signiert(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(signatur, "vorhandenes_zertifikat", lambda: None)

    ergebnis = signatur.signieren_wenn_moeglich(Path("egal.exe"))

    assert ergebnis.signiert is False
    assert "Unbekannter Herausgeber" in ergebnis.grund


def test_ohne_zertifikat_wird_von_sich_aus_keines_angelegt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Einen Vertrauensanker einzurichten ist ein Eingriff in die
    Rechnereinstellungen. Der gehört gefragt, nicht nebenbei
    erledigt."""
    angelegt: list[bool] = []

    monkeypatch.setattr(signatur, "vorhandenes_zertifikat", lambda: None)
    monkeypatch.setattr(
        signatur, "zertifikat_anlegen", lambda: (angelegt.append(True), (None, ""))[1]
    )

    signatur.signieren_wenn_moeglich(Path("egal.exe"))

    assert not angelegt, "Natter hat ungefragt ein Zertifikat angelegt."


def test_mit_anlegen_wird_eines_erzeugt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(signatur, "vorhandenes_zertifikat", lambda: None)
    monkeypatch.setattr(signatur, "zertifikat_anlegen", lambda: ("ABC123", "angelegt"))
    monkeypatch.setattr(
        signatur,
        "exe_signieren",
        lambda exe, fp: signatur.SignaturErgebnis(True, f"mit {fp}"),
    )

    ergebnis = signatur.signieren_wenn_moeglich(Path("egal.exe"), anlegen=True)

    assert ergebnis.signiert is True
    assert "ABC123" in ergebnis.grund


# --------------------------------------- Wie signiert wird


def test_mit_zertifikat_wird_signiert(monkeypatch: pytest.MonkeyPatch) -> None:
    befehle: list[str] = []

    def _antwort(befehl, **_kwargs):  # noqa: ANN001, ANN202
        befehle.append(befehl[-1])
        return _Antwort(stdout="Valid\n")

    monkeypatch.setattr(subprocess, "run", _antwort)

    ergebnis = signatur.exe_signieren(Path("C:/tmp/Spiel.exe"), "ABC123")

    assert ergebnis.signiert is True
    assert "ABC123" in befehle[0]
    assert "Spiel.exe" in befehle[0]


def test_es_wird_mit_zeitstempel_signiert(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ohne Zeitstempel werden alle Signaturen ungültig, sobald das
    Zertifikat abläuft - auch bei Programmen, die längst
    weitergegeben wurden."""
    befehle: list[str] = []

    def _antwort(befehl, **_kwargs):  # noqa: ANN001, ANN202
        befehle.append(befehl[-1])
        return _Antwort(stdout="Valid\n")

    monkeypatch.setattr(subprocess, "run", _antwort)

    signatur.exe_signieren(Path("C:/tmp/Spiel.exe"), "ABC123")

    assert "TimestampServer" in befehle[0]
    assert "SHA256" in befehle[0]


def test_ein_fehlschlag_wird_gemeldet_und_nicht_verschwiegen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess, "run", lambda *a, **k: _Antwort(stdout="UnknownError\n")
    )

    ergebnis = signatur.exe_signieren(Path("C:/tmp/Spiel.exe"), "ABC123")

    assert ergebnis.signiert is False
    assert "UnknownError" in ergebnis.grund


def test_ein_angelegtes_zertifikat_ist_nicht_exportierbar() -> None:
    """Der Schlüssel soll den Rechner nicht verlassen können - auch
    nicht durch ein Programm, das später einmal darauf läuft."""
    quelle = (WURZEL / "ide" / "export" / "signatur.py").read_text(encoding="utf-8")

    assert "-KeyExportPolicy NonExportable" in quelle


def test_es_wird_nur_fuer_das_eigene_konto_eingetragen() -> None:
    """Der Eintrag fuer alle Konten braucht Administratorrechte, und er
    bringt nichts: Smart App Control erkennt ein selbst ausgestelltes
    Zertifikat auch dann nicht an. Beim Ausprobieren stand die
    signierte Datei im Ereignisprotokoll als
    `ValidatedSigningLevel=1`, also als unsigniert. Wer dafuer nach
    Administratorrechten fragt, verlangt etwas fuer nichts.

    Geprueft wird der Anlege-Befehl und nicht die ganze Datei:
    `vertrauenswuerdige_fingerabdruecke()` liest auch den Speicher des
    Rechners, und das muss es auch - ein dort eingetragenes Zertifikat
    gilt ja.
    """
    import inspect

    quelle = inspect.getsource(signatur.zertifikat_anlegen)

    assert "'CurrentUser'" in quelle
    assert "LocalMachine" not in quelle
    assert "RunAs" not in quelle


def test_smart_app_control_wird_aus_der_registrierung_gelesen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(signatur, "_powershell", lambda *a, **k: _Antwort("1\n"))
    assert signatur.smart_app_control_an() is True

    monkeypatch.setattr(signatur, "_powershell", lambda *a, **k: _Antwort("0\n"))
    assert signatur.smart_app_control_an() is False

    # Pruefmodus meldet 2 und blockiert nichts.
    monkeypatch.setattr(signatur, "_powershell", lambda *a, **k: _Antwort("2\n"))
    assert signatur.smart_app_control_an() is False

    # Aeltere Windows-Fassungen kennen den Wert gar nicht.
    monkeypatch.setattr(signatur, "_powershell", lambda *a, **k: _Antwort(""))
    assert signatur.smart_app_control_an() is False


def test_bei_eingeschaltetem_schutz_wird_nichts_versprochen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Eine Signatur laesst eine selbst gebaute Exe unter Smart App
    Control nicht starten. Wer das Gegenteil liest, sucht den Fehler
    danach im eigenen Programm."""
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: _Antwort(stdout="Valid\n"))
    monkeypatch.setattr(signatur, "smart_app_control_an", lambda: True)

    ergebnis = signatur.exe_signieren(Path("C:/tmp/Spiel.exe"), "ABC123")

    assert ergebnis.signiert is True
    assert "nicht zuverlässig" in ergebnis.grund


# --------------------------------------- Der Weg durch den Export


def test_der_export_signiert_und_schreibt_es_ins_protokoll() -> None:
    quelle = (WURZEL / "ide" / "export" / "exporter.py").read_text(encoding="utf-8")

    assert "signieren_wenn_moeglich(exe_pfad, anlegen=True)" in quelle
    assert "signatur.grund" in quelle


def test_der_export_legt_bei_bedarf_ein_zertifikat_an() -> None:
    """Ohne das bliebe die Exe auf einem Rechner ohne Zertifikat
    unsigniert, und Smart App Control liesse sie nicht starten - ein
    Export, dessen Ergebnis sich nicht öffnen lässt, ist keiner."""
    quelle = (WURZEL / "ide" / "export" / "exporter.py").read_text(encoding="utf-8")

    assert "anlegen=True" in quelle


def test_die_oberflaeche_sagt_es_wenn_nicht_signiert_wurde() -> None:
    """Sonst gibt jemand ein Programm weiter und wundert sich beim
    Freund, warum nichts passiert."""
    quelle = (WURZEL / "ide" / "shell" / "hauptfenster.py").read_text(encoding="utf-8")

    assert "Signiert" in quelle
    assert "signaturzeile" in quelle
