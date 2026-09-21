"""Eine exportierte Exe signieren, damit Windows sie starten lässt.

Smart App Control prüft jede Datei, die geladen wird, und lässt nur
durch, was signiert ist oder einen Ruf im Netz hat. Eine frisch
gebaute Exe hat weder das eine noch das andere: das Programm einer
Schülerin wird auf einem solchen Rechner abgeschossen, bevor es sein
Fenster zeigt. Dasselbe ist Natter selbst passiert, bevor die
Auslieferung durchsigniert wurde.

Der private Schlüssel von Natter liegt ausdrücklich nicht in der
Auslieferung. Läge er dort, könnte jede Natter-Installation beliebigen
Code mit einem Zertifikat signieren, das auf allen Schulrechnern als
vertrauenswürdig eingetragen ist - eine Hintertür ins Schulnetz, die
sich nicht widerrufen lässt. Die mitgelieferte `natter-codesign.cer`
enthält nur den öffentlichen Teil; damit lässt sich prüfen, nicht
signieren.

Signiert wird deshalb mit dem, was auf dem Rechner schon liegt:

* einem Zertifikat, das die Lehrkraft dort eingerichtet hat, oder
* einem, das Natter auf diesem Rechner anlegt und das ihn nie
  verlässt. Der Schlüssel ist nicht exportierbar, das Zertifikat gilt
  nur für das angemeldete Konto.

Was damit signiert wurde, läuft auf diesem Rechner. Auf einem fremden
Rechner mit Smart App Control läuft es weiterhin nicht - dafür
bräuchte es ein Zertifikat einer öffentlichen Zertifizierungsstelle,
und das ist eine Entscheidung der Schule, nicht die eines Programms.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from ide.prozess import ohne_konsole

#: Der Name, unter dem Natter ein eigenes Zertifikat anlegt. Getrennt
#: vom Zertifikat, mit dem Natter selbst signiert ist („Natter
#: Codesignatur"): die beiden haben nichts miteinander zu tun, und ein
#: gleicher Name würde in der Zertifikatsverwaltung zwei ganz
#: verschiedene Dinge nebeneinanderstellen.
ZERT_NAME = "Natter Programme dieses Rechners"

#: Fünf Jahre, wie beim Zertifikat der Auslieferung. Länger wäre bei
#: einem Schlüssel ohne Sperrmöglichkeit nicht zu verantworten.
_JAHRE = 5

#: Der Zeitstempeldienst. Ohne ihn werden alle Signaturen ungültig,
#: sobald das Zertifikat abläuft - auch bei Programmen, die längst
#: weitergegeben wurden.
_ZEITSTEMPEL = "http://timestamp.digicert.com"


@dataclass(frozen=True)
class SignaturErgebnis:
    """Was beim Signieren herauskam.

    `grund` steht auch im Erfolgsfall: die Oberfläche sagt damit, ob
    signiert wurde und womit - eine Exe, die stillschweigend ohne
    Signatur herauskommt, fällt erst auf dem fremden Rechner auf.
    """

    signiert: bool
    grund: str


#: Wie lange auf PowerShell gewartet wird. Das Eintragen in den
#: Stammspeicher zeigt einen Sicherheitsdialog von Windows, und der
#: wartet auf eine Antwort - ohne Grenze stünde der Export still,
#: wenn niemand hinsieht.
_GEDULD_SEKUNDEN = 180


def _powershell(
    befehl: str, *, geduld: int | None = None
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            [
                "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                "-Command", befehl,
            ],
            **ohne_konsole(
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=geduld,
            ),
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="Zeitüberschreitung"
        )


def vertrauenswuerdige_fingerabdruecke() -> set[str]:
    """Wem dieser Rechner beim Ausführen von Code vertraut.

    Beides zusammen zählt: die Wurzel, damit die Kette überhaupt
    validiert, und der Herausgeber, damit Smart App Control den Start
    zulässt. Geprüft werden Konto und Rechner - wer ohne
    Administratorrechte einträgt, landet im Konto, und das gilt
    trotzdem.
    """
    befehl = (
        "foreach ($s in 'Root', 'TrustedPublisher') { "
        "  foreach ($e in 'CurrentUser', 'LocalMachine') { "
        "    Get-ChildItem \"Cert:\\$e\\$s\" -ErrorAction SilentlyContinue | "
        "      ForEach-Object { Write-Output $_.Thumbprint } } }"
    )
    ergebnis = _powershell(befehl)
    return {z.strip() for z in (ergebnis.stdout or "").splitlines() if z.strip()}


def vorhandenes_zertifikat() -> str | None:
    """Der Fingerabdruck eines brauchbaren Zertifikats, oder `None`.

    Brauchbar heißt dreierlei: privater Schlüssel vorhanden, noch
    gültig, und dieser Rechner vertraut ihm auch. Der dritte Teil ist
    der wichtigste und fehlte zuerst. Ein Zertifikat, das nur im
    persönlichen Speicher liegt, setzt zwar eine Signatur, aber
    Windows lehnt sie ab: die Exe wäre signiert und startete trotzdem
    nicht. Das ist der schlechteste aller Zustände, weil nichts darauf
    hindeutet - beim Ausprobieren genau so aufgetreten.

    Ein eigenes von Natter hat Vorrang vor einem fremden: es ist auf
    diesen Zweck zugeschnitten.
    """
    vertraut = vertrauenswuerdige_fingerabdruecke()
    if not vertraut:
        return None

    befehl = (
        "Get-ChildItem Cert:\\CurrentUser\\My -CodeSigningCert | "
        "Where-Object { $_.HasPrivateKey -and $_.NotAfter -gt (Get-Date) } | "
        f"Sort-Object {{ $_.Subject -eq 'CN={ZERT_NAME}' }} -Descending | "
        "ForEach-Object { Write-Output $_.Thumbprint }"
    )
    ergebnis = _powershell(befehl)
    for zeile in (ergebnis.stdout or "").splitlines():
        fingerabdruck = zeile.strip()
        if fingerabdruck in vertraut:
            return fingerabdruck
    return None


def zertifikat_anlegen() -> tuple[str | None, str]:
    """Legt ein Zertifikat an, das diesen Rechner nie verlässt.

    Der Schlüssel ist nicht exportierbar: er lässt sich auch von einem
    Programm nicht als Datei herausholen, das später einmal auf diesem
    Rechner läuft. Eingetragen wird für das angemeldete Konto, nicht
    für den Rechner - dafür bräuchte es Administratorrechte, und ein
    Vertrauensanker für alle Konten ist mehr, als der Zweck hergibt.
    """
    befehl = (
        "$z = New-SelfSignedCertificate "
        f"-Subject 'CN={ZERT_NAME}' "
        "-Type CodeSigningCert -KeyUsage DigitalSignature "
        "-KeyExportPolicy NonExportable "
        f"-NotAfter (Get-Date).AddYears({_JAHRE}) "
        "-CertStoreLocation Cert:\\CurrentUser\\My; "
        "foreach ($s in 'Root', 'TrustedPublisher') { "
        "  $speicher = New-Object System.Security.Cryptography."
        "X509Certificates.X509Store($s, 'CurrentUser'); "
        "  $speicher.Open('ReadWrite'); $speicher.Add($z); $speicher.Close() }; "
        "Write-Output $z.Thumbprint"
    )
    ergebnis = _powershell(befehl, geduld=_GEDULD_SEKUNDEN)
    fingerabdruck = (ergebnis.stdout or "").strip().splitlines()
    if ergebnis.returncode != 0 or not fingerabdruck:
        meldung = (ergebnis.stderr or ergebnis.stdout or "").strip().splitlines()
        grund = meldung[-1] if meldung else "kein Grund gemeldet"
        return None, f"Das Zertifikat ließ sich nicht anlegen: {grund}"

    # Nachsehen statt annehmen: den Eintrag in den Stammspeicher lässt
    # Windows nur nach einer Rückfrage zu. Wer dort „Nein" wählt, hat
    # ein Zertifikat im persönlichen Speicher, dem niemand vertraut -
    # damit signiert, wäre die Exe signiert und startete trotzdem
    # nicht.
    neuer = fingerabdruck[-1].strip()
    if neuer not in vertrauenswuerdige_fingerabdruecke():
        return None, (
            "Das Zertifikat wurde angelegt, aber nicht als vertrauenswürdig "
            "eingetragen - ohne das lässt Windows das fertige Programm nicht "
            "starten. Die Rückfrage von Windows dazu muss bejaht werden."
        )
    return neuer, "Zertifikat für diesen Rechner angelegt."


def exe_signieren(exe: Path, fingerabdruck: str) -> SignaturErgebnis:
    """Signiert `exe` mit dem Zertifikat zu `fingerabdruck`."""
    befehl = (
        f"$z = Get-ChildItem Cert:\\CurrentUser\\My | "
        f"Where-Object {{ $_.Thumbprint -eq '{fingerabdruck}' }}; "
        f"$e = Set-AuthenticodeSignature -FilePath '{exe}' -Certificate $z "
        f"-TimestampServer '{_ZEITSTEMPEL}' -HashAlgorithm SHA256; "
        "Write-Output $e.Status"
    )
    ergebnis = _powershell(befehl)
    status = (ergebnis.stdout or "").strip().splitlines()
    letzter = status[-1] if status else ""
    if letzter == "Valid":
        return SignaturErgebnis(True, "Signiert - startet auch mit Smart App Control.")
    grund = letzter or (ergebnis.stderr or "").strip() or "kein Grund gemeldet"
    return SignaturErgebnis(False, f"Nicht signiert: {grund}")


def signieren_wenn_moeglich(exe: Path, *, anlegen: bool = False) -> SignaturErgebnis:
    """Signiert `exe`, sofern ein Zertifikat da ist.

    Mit `anlegen=True` legt Natter eines an, falls keines gefunden
    wird. Das ist ausdrücklich nicht der Standard: einen
    Vertrauensanker einzurichten ist ein Eingriff in die
    Rechnereinstellungen, und der gehört gefragt und nicht nebenbei
    erledigt.

    Ohne Zertifikat bleibt die Exe unsigniert. Sie läuft dann überall
    dort, wo Smart App Control ausgeschaltet ist - auf einem
    verwalteten Schulrechner also ohne Weiteres.
    """
    fingerabdruck = vorhandenes_zertifikat()
    if fingerabdruck is None and anlegen:
        fingerabdruck, grund = zertifikat_anlegen()
        if fingerabdruck is None:
            return SignaturErgebnis(False, grund)
    if fingerabdruck is None:
        return SignaturErgebnis(
            False,
            "Ohne Signatur - auf einem Rechner mit Smart App Control "
            "startet die Exe nicht.",
        )
    return exe_signieren(exe, fingerabdruck)
