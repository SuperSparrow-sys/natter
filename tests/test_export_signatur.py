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

import re
import subprocess
import sys
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


@pytest.fixture(autouse=True)
def _eigenes_profil(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Der Vermerk nach einem „Nein" liegt unter LOCALAPPDATA. Ein
    Vermerk im echten Profil darf die Tests nicht beeinflussen, und
    die Tests dürfen dort keinen hinterlassen."""
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "profil"))


# --------------------------------------- Die Grenze, die nicht fällt


def test_der_private_schluessel_liegt_nicht_in_der_auslieferung() -> None:
    """Der Kern der ganzen Abwägung: die `.pfx` darf weder im Paket
    noch im Repository landen. Wer sie hat, signiert im Namen von
    Natter - auf jedem Rechner, der das Zertifikat eingetragen hat,
    und ohne dass sich das widerrufen ließe."""
    import fnmatch
    import os

    # Die ausgenommenen Ordner gar nicht erst betreten. `rglob` ging
    # sie ganz durch und siebte erst danach aus; mit Arbeitsbäumen
    # unter `.claude/worktrees`, jeder mit eigener `.venv`, dauerte
    # das länger als die Zeitgrenze eines Tests.
    auslassen = {".venv", "build", "dist", ".git", ".claude", "__pycache__"}
    verboten = []
    for ordner, unterordner, dateien in os.walk(WURZEL):
        unterordner[:] = [u for u in unterordner if u not in auslassen]
        for name in dateien:
            if any(
                fnmatch.fnmatch(name.lower(), muster)
                for muster in ("*.pfx", "*passwort*", "*.p12", "*.key")
            ):
                pfad = Path(ordner) / name
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


class _Zertifikatspeicher:
    """Die Speicher des Kontos, wie PowerShell sie sähe.

    Beantwortet die Befehle aus `signatur` so, wie Windows es täte,
    wenn die Rückfrage zum Stammzertifikat verneint wird: `Add` auf
    `Root` wirft, das Zertifikat bleibt in `My`, bis es jemand
    entfernt.
    """

    def __init__(self, ausgang: str = "nein") -> None:
        self.speicher: dict[str, set[str]] = {
            "My": set(), "Root": set(), "TrustedPublisher": set(),
        }
        #: Der Name im Zertifikat, sofern es nicht das eigene ist.
        self.subjekte: dict[str, str] = {}
        self.angelegt = 0
        self.ausgang = ausgang

    def __call__(self, befehl: str, *, geduld=None, werte=None):  # noqa: ANN001, ANN204
        if "New-SelfSignedCertificate" in befehl:
            self.angelegt += 1
            neu = f"NEU{self.angelegt}"
            self.speicher["My"].add(neu)
            if self.ausgang == "zeitgrenze":
                # So bricht `subprocess.run` ab, wenn die Rückfrage
                # hinter dem Fenster steht: die erste Zeile ist schon
                # geschrieben.
                raise subprocess.TimeoutExpired(
                    "powershell", geduld or 0, output=f"Angelegt|{neu}\n"
                )
            if self.ausgang == "fehler":
                return _Antwort(
                    stdout=f"Angelegt|{neu}\n",
                    stderr="Zugriff verweigert",
                    returncode=1,
                )
            return _Antwort(stdout=f"Angelegt|{neu}\nAbgelehnt|{neu}\n")
        if "Remove-Item" in befehl:
            fingerabdruck = (werte or {})["NATTER_ZERTIFIKAT"]
            self.speicher["My"].discard(fingerabdruck)
            self.speicher["TrustedPublisher"].discard(fingerabdruck)
            return _Antwort()
        if "'Root', 'TrustedPublisher'" in befehl:
            vertraut = self.speicher["Root"] | self.speicher["TrustedPublisher"]
            return _Antwort(stdout="\n".join(sorted(vertraut)))
        if "-CodeSigningCert" in befehl:
            # Wie PowerShell: ein `Where-Object` auf den Namen filtert,
            # und ausgegeben wird, was der Befehl verlangt.
            filter_ = re.search(
                r"Where-Object \{ \$_\.Subject -eq '([^']*)'", befehl
            )
            zeilen = []
            for fingerabdruck in sorted(self.speicher["My"]):
                subjekt = self.subjekte.get(
                    fingerabdruck, f"CN={signatur.ZERT_NAME}"
                )
                if filter_ and subjekt != filter_.group(1):
                    continue
                if "'|' + $_.Subject" in befehl:
                    zeilen.append(f"{fingerabdruck}|{subjekt}")
                else:
                    zeilen.append(fingerabdruck)
            return _Antwort(stdout="\n".join(zeilen))
        raise AssertionError(f"Unerwarteter Befehl: {befehl}")


def test_nach_einem_nein_bleibt_nichts_liegen_und_es_wird_nicht_neu_gefragt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Punkt 324: bis 0.3.6 blieb jedes abgelehnte Zertifikat in
    `CurrentUser\\My` liegen, und jeder weitere Export legte ein
    neues an und ließ Windows erneut fragen."""
    windows = _Zertifikatspeicher()
    monkeypatch.setattr(signatur, "_powershell", windows)

    erster = signatur.signieren_wenn_moeglich(Path("egal.exe"), anlegen=True)
    zweiter = signatur.signieren_wenn_moeglich(Path("egal.exe"), anlegen=True)

    assert erster.signiert is False and zweiter.signiert is False
    assert windows.speicher["My"] == set()
    assert windows.angelegt == 1
    # Der Grund nennt den Eintrag, der den Vermerk aufhebt, statt einer
    # Datei im ausgeblendeten Profilordner (Punkt 352).
    assert signatur.WIEDER_FRAGEN in zweiter.grund

    # Wer es sich anders überlegt, wird beim nächsten Export gefragt.
    signatur.rueckfrage_wieder_zulassen()
    signatur.signieren_wenn_moeglich(Path("egal.exe"), anlegen=True)
    assert windows.angelegt == 2


@pytest.mark.parametrize("ausgang", ["nein", "zeitgrenze", "fehler"])
def test_kein_ausgang_ausser_erfolg_laesst_ein_zertifikat_liegen(
    monkeypatch: pytest.MonkeyPatch, ausgang: str
) -> None:
    """Punkt 336: nach der Zeitgrenze blieb das Zertifikat in `My`
    liegen wie vor Punkt 324 nach einem „Nein“. Nachgebildet wird
    hier `subprocess.run`, damit auch `_powershell` mitgeprüft ist:
    es muss die Ausgabe bis zum Abbruch weitergeben."""
    windows = _Zertifikatspeicher(ausgang)

    def ausfuehren(argumente, **optionen):  # noqa: ANN001, ANN202
        umgebung = optionen.get("env") or {}
        return windows(
            argumente[-1],
            geduld=optionen.get("timeout"),
            werte={
                k: v for k, v in umgebung.items()
                if k.startswith("NATTER_")
            },
        )

    monkeypatch.setattr(signatur.subprocess, "run", ausfuehren)

    fingerabdruck, _grund = signatur.zertifikat_anlegen()

    assert fingerabdruck is None
    assert windows.angelegt == 1
    assert windows.speicher["My"] == set()


@pytest.mark.parametrize("eigenes", [False, True], ids=["nur_fremdes", "beide"])
def test_ein_fremdes_vertrautes_zertifikat_wird_nicht_genommen(
    monkeypatch: pytest.MonkeyPatch, eigenes: bool
) -> None:
    """Punkt 423: lag im Konto ein anderes Codesignatur-Zertifikat,
    dem der Rechner vertraut, etwa das der Schule, signierte der Export
    ohne Nachfrage damit. Signiert wird nur mit dem eigenen; fehlt
    es, gilt der Ablauf zum Anlegen mit der Ankündigung davor."""
    windows = _Zertifikatspeicher("nein")
    for speicher in ("My", "Root", "TrustedPublisher"):
        windows.speicher[speicher].add("SCHULE123")
    windows.subjekte["SCHULE123"] = "CN=Gymnasium Musterstadt"
    if eigenes:
        for speicher in ("My", "Root", "TrustedPublisher"):
            windows.speicher[speicher].add("EIGEN456")
    monkeypatch.setattr(signatur, "_powershell", windows)
    signiert_mit: list[str] = []
    monkeypatch.setattr(
        signatur,
        "exe_signieren",
        lambda exe, fp: (
            signiert_mit.append(fp),
            signatur.SignaturErgebnis(True, "signiert"),
        )[1],
    )
    angekuendigt: list[bool] = []

    ergebnis = signatur.signieren_wenn_moeglich(
        Path("egal.exe"),
        anlegen=True,
        vor_dem_anlegen=lambda: angekuendigt.append(True),
    )

    assert "SCHULE123" not in signiert_mit
    if eigenes:
        assert signiert_mit == ["EIGEN456"]
        assert not angekuendigt
    else:
        assert signiert_mit == []
        assert angekuendigt == [True]
        assert windows.angelegt == 1
        assert ergebnis.signiert is False
    # Das fremde Zertifikat bleibt, wo es ist.
    assert "SCHULE123" in windows.speicher["My"]


def test_nur_der_stammspeicher_steht_im_try() -> None:
    """Die Rückfrage kommt beim Eintrag in `Root`. Verneint, darf das
    Zertifikat auch nicht zu den vertrauenswürdigen Herausgebern."""
    import inspect

    quelle = inspect.getsource(signatur.zertifikat_anlegen)

    assert quelle.index("'Root'") < quelle.index("Abgelehnt|")
    assert quelle.index("Abgelehnt|") < quelle.index("'TrustedPublisher'")


# --------------------------------------- Wie signiert wird


def test_mit_zertifikat_wird_signiert(monkeypatch: pytest.MonkeyPatch) -> None:
    befehle: list[str] = []
    umgebungen: list[dict[str, str]] = []

    def _antwort(befehl, **kwargs):  # noqa: ANN001, ANN202
        befehle.append(befehl[-1])
        umgebungen.append(kwargs.get("env") or {})
        return _Antwort(stdout="Valid\n")

    monkeypatch.setattr(subprocess, "run", _antwort)

    ergebnis = signatur.exe_signieren(Path("C:/tmp/Spiel.exe"), "ABC123")

    assert ergebnis.signiert is True
    # Die Rückmeldung nennt den Herausgeber (Punkt 423).
    assert f"Herausgeber: „{signatur.ZERT_NAME}“" in ergebnis.grund
    # Pfad und Fingerabdruck stehen nicht im Befehlstext, sondern
    # kommen als Umgebungsvariablen an (Punkt 229).
    assert "ABC123" not in befehle[0]
    assert "Spiel.exe" not in befehle[0]
    assert umgebungen[0]["NATTER_SIGNIEREN_ZERTIFIKAT"] == "ABC123"
    assert umgebungen[0]["NATTER_SIGNIEREN_EXE"].endswith("Spiel.exe")


# Echte PowerShell, aber ohne Zertifikat: signiert wird dabei nichts,
# und am Zertifikatspeicher ändert sich nichts. Der Fingerabdruck
# gehört zu keinem Zertifikat; kommt die Meldung „liegt nicht im
# Zertifikatspeicher“, hat PowerShell die Exe unter ihrem Pfad
# gefunden. Mit dem Pfad im Befehlstext brach ein Apostroph den
# Befehl vorher ab (Punkt 229).
_KEIN_ZERTIFIKAT = "0" * 40

_NUR_WINDOWS = pytest.mark.skipif(
    sys.platform != "win32", reason="nur unter Windows"
)


@_NUR_WINDOWS
def test_ein_pfad_mit_apostroph_kommt_bei_powershell_an(
    tmp_path: Path,
) -> None:
    exe = tmp_path / "Jana's Spiel" / "Jana's Spiel.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"MZ")

    ergebnis = signatur.exe_signieren(exe, _KEIN_ZERTIFIKAT)

    assert ergebnis.signiert is False
    assert "nicht im Zertifikatspeicher" in ergebnis.grund
    fehlt = signatur.exe_signieren(
        exe.with_name("gibt's nicht.exe"), _KEIN_ZERTIFIKAT
    )
    assert "nicht gefunden" in fehlt.grund


@_NUR_WINDOWS
@pytest.mark.parametrize(
    "ordnername",
    [
        "a'$(New-Item -ItemType File -Path ausgefuehrt.txt)'b",
        "a'+(New-Item -ItemType File -Path ausgefuehrt.txt)+'b",
        "a[1]$(New-Item -ItemType File -Path ausgefuehrt.txt)",
    ],
)
def test_ein_ausdruck_im_pfad_wird_nicht_ausgefuehrt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ordnername: str
) -> None:
    monkeypatch.chdir(tmp_path)
    exe = tmp_path / ordnername / "p.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"MZ")

    ergebnis = signatur.exe_signieren(exe, _KEIN_ZERTIFIKAT)

    assert not (tmp_path / "ausgefuehrt.txt").exists()
    assert "nicht im Zertifikatspeicher" in ergebnis.grund


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


#: Was `Set-AuthenticodeSignature` meldet, wenn der Zeitstempeldienst
#: nicht erreichbar ist (in einer Probe mit einem nur im Speicher
#: erzeugten Zertifikat so beobachtet, Punkt 264).
_KEIN_NETZ = "UnknownError|Unknown error (0x80072efd)\n"


def _ohne_zeitstempeldienst(
    befehle: list[str], geduld: list[object]
):  # noqa: ANN202
    """Ein `subprocess.run`, hinter dem der Zeitstempeldienst nicht
    erreichbar ist: mit `-TimestampServer` scheitert das Signieren,
    ohne gelingt es."""

    def _antwort(befehl, **kwargs):  # noqa: ANN001, ANN202
        befehle.append(befehl[-1])
        geduld.append(kwargs.get("timeout"))
        if "Set-AuthenticodeSignature" not in befehl[-1]:
            return _Antwort(stdout="")  # Smart App Control: aus
        if "TimestampServer" in befehl[-1]:
            return _Antwort(stdout=_KEIN_NETZ)
        return _Antwort(stdout="Valid|Signatur überprüft.\n")

    return _antwort


def test_ohne_zeitstempeldienst_wird_ohne_zeitstempel_signiert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Auf einem Rechner ohne Netz oder hinter einem Proxy blieb jede
    Exe unsigniert, obwohl ein Zertifikat da war, und das Protokoll
    gab der Datei die Schuld (Punkt 264)."""
    befehle: list[str] = []
    geduld: list[object] = []
    monkeypatch.setattr(signatur, "_ZEITSTEMPEL", "http://127.0.0.1:9")
    monkeypatch.setattr(
        subprocess, "run", _ohne_zeitstempeldienst(befehle, geduld)
    )

    ergebnis = signatur.exe_signieren(Path("C:/tmp/Spiel.exe"), "ABC123")

    assert ergebnis.signiert is True
    assert ergebnis.grund.startswith(
        "Signiert, ohne Zeitstempel: keine Verbindung zum "
        "Zeitstempeldienst"
    )
    assert "Ablauf des Zertifikats" in ergebnis.grund
    signierbefehle = [b for b in befehle if "Set-AuthenticodeSignature" in b]
    assert len(signierbefehle) == 2
    assert "http://127.0.0.1:9" in signierbefehle[0]
    assert "TimestampServer" not in signierbefehle[1]
    assert "SHA256" in signierbefehle[1]


def test_jeder_signierversuch_hat_eine_zeitgrenze(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In einem Netz, das Verbindungen stumm verwirft, wartete der
    Export ohne Grenze auf Windows (Punkt 264)."""
    befehle: list[str] = []
    geduld: list[object] = []
    monkeypatch.setattr(
        subprocess, "run", _ohne_zeitstempeldienst(befehle, geduld)
    )

    signatur.exe_signieren(Path("C:/tmp/Spiel.exe"), "ABC123")

    grenzen = [
        g for b, g in zip(befehle, geduld, strict=True)
        if "Set-AuthenticodeSignature" in b
    ]
    assert grenzen and all(
        isinstance(g, (int, float)) and 0 < g <= 120 for g in grenzen
    )


def test_nach_einer_zeitueberschreitung_wird_ohne_zeitstempel_signiert(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    befehle: list[str] = []

    def _antwort(befehl, **kwargs):  # noqa: ANN001, ANN202
        befehle.append(befehl[-1])
        if "TimestampServer" in befehl[-1]:
            raise subprocess.TimeoutExpired(befehl, kwargs.get("timeout"))
        return _Antwort(stdout="Valid|\n")

    monkeypatch.setattr(subprocess, "run", _antwort)
    monkeypatch.setattr(signatur, "smart_app_control_an", lambda: False)

    ergebnis = signatur.exe_signieren(Path("C:/tmp/Spiel.exe"), "ABC123")

    assert ergebnis.signiert is True
    assert "ohne Zeitstempel" in ergebnis.grund


def test_ohne_zertifikat_im_speicher_gibt_es_keinen_zweiten_versuch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ein zweiter Versuch hilft nur gegen das Netz. Fehlt das
    Zertifikat, bliebe es beim zweiten Mal genauso."""
    befehle: list[str] = []

    def _antwort(befehl, **_kwargs):  # noqa: ANN001, ANN202
        befehle.append(befehl[-1])
        return _Antwort(stdout="ZertifikatFehlt|\n")

    monkeypatch.setattr(subprocess, "run", _antwort)

    ergebnis = signatur.exe_signieren(Path("C:/tmp/Spiel.exe"), "ABC123")

    assert ergebnis.signiert is False
    assert len(befehle) == 1


def test_ein_fehlschlag_wird_gemeldet_und_nicht_verschwiegen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *a, **k: _Antwort(
            stdout="UnknownError|%1 ist keine zulässige Win32-Anwendung.\n"
        ),
    )

    ergebnis = signatur.exe_signieren(Path("C:/tmp/Spiel.exe"), "ABC123")

    assert ergebnis.signiert is False
    # Deutsch statt des englischen Statuswerts, mit der Meldung von
    # Windows dahinter (Schülerweg 0.3.3, Punkt 34).
    assert "UnknownError" not in ergebnis.grund
    assert "abgelehnt" in ergebnis.grund
    assert "keine zulässige Win32-Anwendung" in ergebnis.grund


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

    assert re.search(
        r"signieren_wenn_moeglich\(\s*exe_pfad, anlegen=True", quelle
    )
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


@pytest.mark.parametrize(
    "fehler",
    [OSError(22, "Die Anwendung wurde durch eine Richtlinie blockiert"),
     FileNotFoundError("powershell")],
)
def test_eine_gesperrte_powershell_ergibt_eine_unsignierte_exe(
    monkeypatch: pytest.MonkeyPatch, fehler: OSError
) -> None:
    """Punkt 599: der Fehler beim Start von PowerShell kam aus dem
    Export heraus, und der meldete „fehlgeschlagen“."""
    def gesperrt(*_a, **_k):  # noqa: ANN002, ANN003, ANN202
        raise fehler

    monkeypatch.setattr(signatur.subprocess, "run", gesperrt)

    ergebnis = signatur.signieren_wenn_moeglich(Path("egal.exe"), anlegen=True)

    assert ergebnis.signiert is False
    assert "PowerShell" in ergebnis.grund
