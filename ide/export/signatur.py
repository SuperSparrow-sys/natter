"""Eine exportierte Exe signieren, damit sie einen Herausgeber trägt.

Eine frisch gebaute Exe hat keinen. Windows nennt sie in jedem Dialog
„Unbekannter Herausgeber", und wer sie weitergibt, kann nicht zeigen,
woher sie stammt. Eine Signatur ändert das: sie nennt den Rechner, auf
dem das Programm entstanden ist, und sie fällt auf, wenn jemand die
Datei nachträglich verändert.

Was sie nicht leistet, gehört genauso hierher. Smart App Control lässt
sich mit einem selbst ausgestellten Zertifikat nicht zufriedenstellen.
Windows führt eine so signierte Datei im Ereignisprotokoll als
`ValidatedSigningLevel=1`, also als unsigniert, und entscheidet
stattdessen nach dem Ruf des einzelnen Dateihashs bei Microsoft. Beim
Ausprobieren lief dieselbe Bibliothek vor dem Nachsignieren und war
danach gesperrt - gleiches Zertifikat, gleicher Rechner. Auf einem
Rechner mit eingeschaltetem Smart App Control startet ein selbst
gebautes Programm deshalb nicht zuverlässig, signiert oder nicht.
Dafür bräuchte es ein Zertifikat einer öffentlichen
Zertifizierungsstelle, und das ist eine Entscheidung der Schule, nicht
die eines Programms.

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
  verlässt. Der Schlüssel ist nicht exportierbar, und eingetragen wird
  für das angemeldete Konto. Für alle Konten bräuchte es
  Administratorrechte, und die hätte Natter nur zu verlangen, wenn
  sich damit etwas erreichen ließe.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
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
#: weitergegeben wurden. Ist er nicht erreichbar, wird ohne ihn
#: signiert (siehe `exe_signieren`).
_ZEITSTEMPEL = "http://timestamp.digicert.com"

#: Wie lange ein Signieren mit Zeitstempel dauern darf. Der Dienst
#: antwortet sonst in ein, zwei Sekunden; dazu kommt der Start von
#: PowerShell. In einem Netz, das Verbindungen stumm verwirft, wartete
#: der Export ohne Grenze so lange, wie Windows es beim
#: Verbindungsaufbau aushält (Punkt 264).
_ZEITSTEMPEL_GEDULD_SEKUNDEN = 45

#: Wie lange das Signieren ohne Zeitstempel dauern darf. Es braucht
#: kein Netz; die Grenze fängt nur einen hängenden PowerShell-Aufruf
#: ab.
_SIGNIER_GEDULD_SEKUNDEN = 60

#: Wo Windows den Zustand von Smart App Control ablegt: 0 aus,
#: 1 eingeschaltet, 2 Prüfmodus. Lesen geht ohne besondere Rechte.
_SAC_SCHLUESSEL = "HKLM:\\SYSTEM\\CurrentControlSet\\Control\\CI\\Policy"
_SAC_WERT = "VerifiedAndReputablePolicyState"


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
    befehl: str,
    *,
    geduld: int | None = None,
    werte: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Führt `befehl` in PowerShell aus.

    `befehl` ist fester Text aus diesem Modul. Alles, was von außen
    kommt, etwa der Pfad der Exe, geht über `werte` als
    Umgebungsvariable hinein und wird im Befehl als `$env:NAME`
    gelesen (Punkt 229). In den Befehlstext eingesetzt, brach ein
    Apostroph im Pfad den Befehl, und ein Ordnername wie
    `a'+(…)+'b` führte den Ausdruck in der Klammer aus.
    """
    umgebung = None
    if werte:
        umgebung = {**os.environ, **werte}
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
                env=umgebung,
            ),
        )
    except subprocess.TimeoutExpired as abbruch:
        # Was PowerShell bis dahin geschrieben hat, bleibt erhalten:
        # `zertifikat_anlegen` braucht daraus den Fingerabdruck eines
        # schon angelegten Zertifikats, um es wieder zu entfernen
        # (Punkt 336).
        bisher = abbruch.stdout or ""
        if isinstance(bisher, bytes):
            bisher = bisher.decode("utf-8", errors="replace")
        return subprocess.CompletedProcess(
            args=[], returncode=1, stdout=bisher,
            stderr="Zeitüberschreitung",
        )


def vertrauenswuerdige_fingerabdruecke() -> set[str]:
    """Wem dieser Rechner beim Ausführen von Code vertraut.

    Beides zusammen zählt: die Wurzel, damit die Kette überhaupt
    validiert, und der Herausgeber, damit Windows die Signatur beim
    Ausführen nicht beanstandet. Geprüft werden Konto und Rechner - wer
    ohne Administratorrechte einträgt, landet im Konto, und das gilt
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


def smart_app_control_an() -> bool:
    """Ob Smart App Control auf diesem Rechner scharf geschaltet ist.

    Gebraucht wird das für die Rückmeldung nach dem Export, nicht für
    eine Entscheidung im Ablauf. Ist es eingeschaltet, startet ein
    selbst gebautes Programm auf diesem Rechner nicht zuverlässig, und
    daran ändert die Signatur nichts. Das gehört in den Satz, den
    jemand nach dem Exportieren liest - sonst sucht er den Fehler in
    seinem Programm.
    """
    befehl = (
        f"(Get-ItemProperty -Path '{_SAC_SCHLUESSEL}' "
        f"-Name '{_SAC_WERT}' -ErrorAction SilentlyContinue)"
        f".{_SAC_WERT}"
    )
    ergebnis = _powershell(befehl)
    zeilen = [z.strip() for z in (ergebnis.stdout or "").splitlines() if z.strip()]
    return bool(zeilen) and zeilen[-1] == "1"


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


#: Der Eintrag im Panel „Meldungen“, der den Vermerk aufhebt
#: (`rueckfrage_wieder_zulassen`). Er steht hier, weil die Gründe
#: unten auf ihn verweisen.
WIEDER_FRAGEN = "Beim nächsten Export wieder nach dem Zertifikat fragen"

#: Der Satz, mit dem jeder Grund nach einem „Nein“ endet. Bis 0.3.x
#: nannte er eine Datei im ausgeblendeten Ordner `AppData`, die für
#: einen neuen Versuch zu löschen war (Punkt 352).
_NEUER_VERSUCH = (
    f"Einen neuen Versuch erlaubt der Eintrag „{WIEDER_FRAGEN}“ im "
    "Panel „Meldungen“."
)


def abgelehnt_vermerk() -> Path:
    """Die Datei, die festhält, dass die Rückfrage verneint wurde.

    Bis 0.3.6 legte jeder Export nach einem „Nein" ein weiteres
    Zertifikat an, und Windows fragte jedes Mal wieder (Punkt 324).
    Wer einmal abgelehnt hat, wird nicht bei jedem Export erneut
    gefragt; wer es sich anders überlegt, nimmt den Eintrag
    `WIEDER_FRAGEN` nach dem Export oder löscht die Datei. Sie liegt
    im Profil wie das Zertifikat selbst: wird das Profil
    zurückgesetzt, sind beide weg, und die nächste Rückfrage ist
    wieder die erste.
    """
    basis = os.environ.get("LOCALAPPDATA") or str(
        Path.home() / "AppData" / "Local"
    )
    return Path(basis) / "Natter" / "zertifikat_abgelehnt.txt"


def _ablehnung_vermerken() -> None:
    pfad = abgelehnt_vermerk()
    try:
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(
            "Die Rückfrage von Windows zum Zertifikat "
            f"„{ZERT_NAME}“ wurde verneint. Solange diese Datei "
            "besteht, legt „Als Exe exportieren“ kein neues an.\n",
            encoding="utf-8",
        )
    except OSError:
        # Ohne Vermerk fragt der nächste Export wieder; das ist
        # lästig, aber kein Grund, den Export scheitern zu lassen.
        pass


def rueckfrage_wieder_zulassen() -> None:
    """Hebt den Vermerk auf: der nächste Export fragt wieder."""
    try:
        abgelehnt_vermerk().unlink(missing_ok=True)
    except OSError:
        pass


def _zertifikat_entfernen(fingerabdruck: str) -> None:
    """Nimmt ein nicht eingetragenes Zertifikat wieder heraus.

    Aus dem persönlichen Speicher samt Schlüssel und aus den
    vertrauenswürdigen Herausgebern. Den Stammspeicher lässt der
    Befehl aus: dort steht es nicht, sonst wäre es eingetragen, und
    jeder Zugriff darauf zöge eine weitere Rückfrage von Windows
    nach sich.
    """
    befehl = (
        "$f = $env:NATTER_ZERTIFIKAT; "
        "Remove-Item -LiteralPath ('Cert:\\CurrentUser\\My\\' + $f) "
        "-DeleteKey -ErrorAction SilentlyContinue; "
        "$speicher = New-Object System.Security.Cryptography."
        "X509Certificates.X509Store('TrustedPublisher', 'CurrentUser'); "
        "$speicher.Open('ReadWrite'); "
        "@($speicher.Certificates | Where-Object { $_.Thumbprint -eq $f }) | "
        "ForEach-Object { $speicher.Remove($_) }; $speicher.Close()"
    )
    _powershell(
        befehl, geduld=_SIGNIER_GEDULD_SEKUNDEN,
        werte={"NATTER_ZERTIFIKAT": fingerabdruck},
    )


def zertifikat_anlegen() -> tuple[str | None, str]:
    """Legt ein Zertifikat an, das diesen Rechner nie verlässt.

    Der Schlüssel ist nicht exportierbar: er lässt sich auch von einem
    Programm nicht als Datei herausholen, das später einmal auf diesem
    Rechner läuft. Eingetragen wird für das angemeldete Konto, nicht
    für den Rechner - dafür bräuchte es Administratorrechte, und ein
    Vertrauensanker für alle Konten ist mehr, als der Zweck hergibt.

    Zuerst in den Stammspeicher, weil Windows nur dort nachfragt.
    Verneint jemand die Rückfrage, wirft `Add` eine Ausnahme; dann
    kommt es auch nicht zu den vertrauenswürdigen Herausgebern.

    Den Fingerabdruck meldet der Befehl gleich nach dem Anlegen. Jeder
    Ausgang außer dem Erfolg entfernt das Zertifikat wieder über
    denselben `finally`-Zweig: ein „Nein“, eine Rückfrage, die in die
    Zeitgrenze läuft, und jeder andere Fehler. Bis 0.3.6 blieb es nach
    einem „Nein“ liegen, eines je Export (Punkt 324), und nach der
    Zeitgrenze auch danach noch (Punkt 336).
    """
    befehl = (
        "$z = New-SelfSignedCertificate "
        f"-Subject 'CN={ZERT_NAME}' "
        "-Type CodeSigningCert -KeyUsage DigitalSignature "
        "-KeyExportPolicy NonExportable "
        f"-NotAfter (Get-Date).AddYears({_JAHRE}) "
        "-CertStoreLocation Cert:\\CurrentUser\\My; "
        "Write-Output ('Angelegt|' + $z.Thumbprint); "
        "try { "
        "  $speicher = New-Object System.Security.Cryptography."
        "X509Certificates.X509Store('Root', 'CurrentUser'); "
        "  $speicher.Open('ReadWrite'); $speicher.Add($z); $speicher.Close() "
        "} catch { Write-Output ('Abgelehnt|' + $z.Thumbprint); exit 0 }; "
        "$speicher = New-Object System.Security.Cryptography."
        "X509Certificates.X509Store('TrustedPublisher', 'CurrentUser'); "
        "$speicher.Open('ReadWrite'); $speicher.Add($z); $speicher.Close(); "
        "Write-Output ('Eingetragen|' + $z.Thumbprint)"
    )
    ergebnis = _powershell(befehl, geduld=_GEDULD_SEKUNDEN)
    meldungen: dict[str, str] = {}
    for zeile in (ergebnis.stdout or "").splitlines():
        art, trenner, wert = zeile.strip().partition("|")
        if trenner and wert:
            meldungen[art] = wert
    neuer = meldungen.get("Angelegt", "")
    abgelehnt = "Abgelehnt" in meldungen
    eingetragen = "Eingetragen" in meldungen and ergebnis.returncode == 0
    zeitgrenze = ergebnis.stderr == "Zeitüberschreitung"
    erfolg = False
    try:
        if not (abgelehnt or eingetragen or zeitgrenze):
            meldung = (
                (ergebnis.stderr or ergebnis.stdout or "")
                .strip().splitlines()
            )
            grund = meldung[-1] if meldung else "kein Grund gemeldet"
            return None, f"Das Zertifikat ließ sich nicht anlegen: {grund}"

        # Nachsehen statt annehmen, auch ohne Ausnahme: ein Zertifikat
        # im persönlichen Speicher, dem niemand vertraut, setzt zwar
        # eine Signatur, aber die Exe startete trotzdem nicht.
        if eingetragen and neuer in vertrauenswuerdige_fingerabdruecke():
            erfolg = True
            return neuer, "Zertifikat für dieses Benutzerkonto angelegt."

        _ablehnung_vermerken()
        return None, (
            "Ohne Signatur: das Zertifikat wurde nicht als vertrauenswürdig "
            "eingetragen, die Rückfrage von Windows wurde verneint, nicht "
            "beantwortet oder ist nicht erlaubt. Natter hat es wieder "
            f"entfernt und fragt in diesem Konto nicht erneut. {_NEUER_VERSUCH}"
        )
    finally:
        if neuer and not erfolg:
            _zertifikat_entfernen(neuer)


#: Was hinter den Statuswerten von `Set-AuthenticodeSignature` steht.
#: Bis 0.3.3 stand der englische Wert allein in der Statuszeile, etwa
#: „Nicht signiert: UnknownError“ - damit weiß niemand, was los ist.
_SIGNATUR_GRUENDE = {
    "UnknownError": "Windows hat die Datei zum Signieren abgelehnt",
    "NotTrusted": "dem Zertifikat vertraut dieser Rechner nicht",
    "HashMismatch": "die Datei wurde nach dem Signieren verändert",
    "NotSigned": "Windows hat keine Signatur angebracht",
    "NotSupportedFileFormat": "diese Art Datei lässt sich nicht signieren",
    "Incompatible": "das Zertifikat passt nicht zu dieser Datei",
    "DateiFehlt": "die Exe wurde nicht gefunden",
    "ZertifikatFehlt": "das Zertifikat liegt nicht im Zertifikatspeicher",
}


def signatur_grund(status: str, meldung: str = "") -> str:
    """Deutscher Grund zu einem Statuswert, mit der Meldung von Windows
    dahinter, sofern es eine gibt (sie ist auf einem deutschen Windows
    schon deutsch)."""
    grund = _SIGNATUR_GRUENDE.get(status, status or "kein Grund gemeldet")
    meldung = meldung.strip()
    return f"{grund} ({meldung})" if meldung else grund


def _signierbefehl(*, mit_zeitstempel: bool) -> str:
    """Der PowerShell-Befehl zum Signieren, mit oder ohne Zeitstempel.

    Pfad und Fingerabdruck kommen als Umgebungsvariablen an, nicht im
    Befehlstext (Punkt 229). `-LiteralPath` nimmt den Pfad wörtlich;
    eckige Klammern im Namen gelten sonst als Platzhalter.
    """
    zeitstempel = f"-TimestampServer '{_ZEITSTEMPEL}' " if mit_zeitstempel else ""
    return (
        "$exe = $env:NATTER_SIGNIEREN_EXE; "
        "if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) "
        "{ Write-Output 'DateiFehlt|'; exit 0 }; "
        "$z = Get-ChildItem Cert:\\CurrentUser\\My | "
        "Where-Object { $_.Thumbprint -eq $env:NATTER_SIGNIEREN_ZERTIFIKAT } | "
        "Select-Object -First 1; "
        "if ($null -eq $z) { Write-Output 'ZertifikatFehlt|'; exit 0 }; "
        "$e = Set-AuthenticodeSignature -LiteralPath $exe -Certificate $z "
        f"{zeitstempel}-HashAlgorithm SHA256; "
        "Write-Output ([string]$e.Status + '|' + $e.StatusMessage)"
    )


def _signieren_lassen(
    exe: Path, fingerabdruck: str, *, mit_zeitstempel: bool
) -> tuple[str, str]:
    """Ein Signierversuch. Liefert Statuswert und Meldung von Windows;
    bei einer Zeitüberschreitung ist der Statuswert leer."""
    ergebnis = _powershell(
        _signierbefehl(mit_zeitstempel=mit_zeitstempel),
        geduld=(
            _ZEITSTEMPEL_GEDULD_SEKUNDEN
            if mit_zeitstempel
            else _SIGNIER_GEDULD_SEKUNDEN
        ),
        werte={
            "NATTER_SIGNIEREN_EXE": str(exe),
            "NATTER_SIGNIEREN_ZERTIFIKAT": fingerabdruck,
        },
    )
    status = (ergebnis.stdout or "").strip().splitlines()
    letzter, _, meldung = (status[-1] if status else "").partition("|")
    if not letzter:
        meldung = (ergebnis.stderr or "").strip()
    return letzter, meldung


#: Was nach einem Fehlschlag mit Zeitstempel einen zweiten Versuch
#: ohne ihn lohnt. `UnknownError` meldet Windows, wenn der Dienst
#: nicht erreichbar ist (0x80072efd, 0x80072ee2), und ein leerer
#: Status steht für eine Zeitüberschreitung. Fehlt die Datei oder das
#: Zertifikat, ändert ein zweiter Versuch nichts.
_OHNE_ZEITSTEMPEL_WIEDERHOLEN = ("UnknownError", "")

#: Die Protokollzeile für eine Signatur ohne Zeitstempel.
OHNE_ZEITSTEMPEL = (
    "Signiert, ohne Zeitstempel: keine Verbindung zum "
    "Zeitstempeldienst. Die Signatur gilt bis zum Ablauf des "
    "Zertifikats."
)


def exe_signieren(exe: Path, fingerabdruck: str) -> SignaturErgebnis:
    """Signiert `exe` mit dem Zertifikat zu `fingerabdruck`.

    Zuerst mit Zeitstempel. Scheitert das am Zeitstempeldienst, etwa
    auf einem Rechner ohne Netz oder in einem Schulnetz, das nur über
    einen Proxy nach außen geht, wird ohne ihn noch einmal signiert.
    Bis 0.3.6 blieb die Exe dann unsigniert, und das Protokoll
    schrieb die Ablehnung der Datei zu statt dem Netz (Punkt 264).
    Eine Signatur ohne Zeitstempel gilt bis zum Ablauf des
    Zertifikats; das ist weniger als mit, aber mehr als keine.

    Schlägt auch der zweite Versuch fehl, lag es nicht am Netz, und
    gemeldet wird sein Grund.
    """
    status, meldung = _signieren_lassen(exe, fingerabdruck, mit_zeitstempel=True)
    ohne_zeitstempel = False
    if status in _OHNE_ZEITSTEMPEL_WIEDERHOLEN:
        status, meldung = _signieren_lassen(
            exe, fingerabdruck, mit_zeitstempel=False
        )
        ohne_zeitstempel = True
    if status == "Valid":
        grund = (
            OHNE_ZEITSTEMPEL
            if ohne_zeitstempel
            else "Signiert - die Exe nennt jetzt einen Herausgeber."
        )
        if smart_app_control_an():
            grund = (
                f"{grund} Auf diesem Rechner ist Smart App Control "
                "eingeschaltet; damit startet ein selbst gebautes Programm "
                "nicht zuverlässig, auch signiert nicht."
            )
        return SignaturErgebnis(True, grund)
    return SignaturErgebnis(False, f"Nicht signiert: {signatur_grund(status, meldung)}")


def signieren_wenn_moeglich(
    exe: Path,
    *,
    anlegen: bool = False,
    vor_dem_anlegen: Callable[[], None] | None = None,
) -> SignaturErgebnis:
    """Signiert `exe`, sofern ein Zertifikat da ist.

    Mit `anlegen=True` legt Natter eines an, falls keines gefunden
    wird. Der Standard ist `False`, weil ein Vertrauensanker ein
    Eingriff in die Einstellungen des Kontos ist. Der Export als Exe
    übergibt `True` (`ide/export/exporter.py`): sonst käme aus jedem
    Export ein Programm ohne erkennbare Herkunft. Gefragt wird dabei
    trotzdem: den Eintrag in den Stammspeicher lässt Windows nur nach
    einer eigenen Rückfrage zu, und wer sie verneint, bekommt eine
    unsignierte Exe und den Grund dazu. Das Zertifikat gilt nur für
    das angemeldete Konto, und sein Schlüssel ist nicht exportierbar.

    Ohne Zertifikat bleibt die Exe unsigniert. Sie läuft trotzdem
    überall dort, wo Smart App Control ausgeschaltet ist - auf einem
    verwalteten Schulrechner also ohne Weiteres. Windows nennt sie dann
    nur in jedem Dialog „Unbekannter Herausgeber“.

    Wurde die Rückfrage in diesem Konto schon einmal verneint, legt
    `anlegen=True` kein neues an (`abgelehnt_vermerk`).

    `vor_dem_anlegen` läuft unmittelbar bevor Natter ein Zertifikat
    anlegt und Windows daraufhin fragt. Die Oberfläche kündigt die
    Sicherheitswarnung damit an (Punkt 350): ohne Ankündigung hält
    eine Schülerin sie eher für einen Angriff und antwortet mit
    „Nein“.
    """
    fingerabdruck = vorhandenes_zertifikat()
    if fingerabdruck is None and anlegen:
        if abgelehnt_vermerk().exists():
            return SignaturErgebnis(
                False,
                "Ohne Signatur: die Rückfrage von Windows zum Zertifikat "
                f"wurde in diesem Konto verneint. {_NEUER_VERSUCH}",
            )
        if vor_dem_anlegen is not None:
            vor_dem_anlegen()
        fingerabdruck, grund = zertifikat_anlegen()
        if fingerabdruck is None:
            return SignaturErgebnis(False, grund)
    if fingerabdruck is None:
        return SignaturErgebnis(
            False,
            "Ohne Signatur - Windows nennt die Exe „Unbekannter Herausgeber“.",
        )
    return exe_signieren(exe, fingerabdruck)
