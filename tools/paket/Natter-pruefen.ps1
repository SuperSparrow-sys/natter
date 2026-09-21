# Sieht nach, warum Natter nicht startet.
#
# Startet die installierte Natter ueber ihre eigene Python und faengt
# ab, woran sie scheitert. Das Ergebnis landet als Textdatei auf dem
# Schreibtisch und laesst sich weitergeben.
#
# Rechtsklick auf diese Datei -> "Mit PowerShell ausfuehren".
# Administratorrechte werden nicht gebraucht.
#
# Mit -Still wartet das Skript am Ende nicht auf die Eingabetaste -
# fuer einen Lauf ueber mehrere Rechner hinweg.

param([switch]$Still)

$ErrorActionPreference = "Continue"

$programm = Join-Path $env:LOCALAPPDATA "Programs\Natter"
$python = Join-Path $programm "python\python.exe"
$bericht = Join-Path ([Environment]::GetFolderPath("Desktop")) "Natter-Pruefbericht.txt"

$zeilen = New-Object System.Collections.Generic.List[string]
function Merken($text) { $zeilen.Add($text); Write-Host $text }

Merken "Natter-Pruefbericht vom $(Get-Date -Format 'dd.MM.yyyy HH:mm')"
Merken ("=" * 60)
Merken ""

# --- Wo liegt was -----------------------------------------------------
Merken "Rechner und System"
Merken "  Windows:      $([Environment]::OSVersion.VersionString)"
Merken "  Benutzer:     $env:USERNAME"
Merken "  Programmordner vorhanden: $(Test-Path $programm)"
Merken "  Python vorhanden:         $(Test-Path $python)"
Merken ""

if (-not (Test-Path $python)) {
    Merken "Die Installation ist unvollstaendig - python\python.exe fehlt."
    Merken "Natter neu installieren."
    $zeilen | Out-File -FilePath $bericht -Encoding utf8
    if (-not $Still) {
        Read-Host "Bericht liegt auf dem Schreibtisch. Eingabetaste zum Schliessen"
    }
    exit 1
}

# --- Was Windows von der Exe haelt ------------------------------------
$exe = Join-Path $programm "Natter.exe"
if (Test-Path $exe) {
    $signatur = Get-AuthenticodeSignature $exe
    Merken "Signatur der Natter.exe"
    Merken "  Status:    $($signatur.Status)"
    if ($signatur.SignerCertificate) {
        Merken "  Aussteller: $($signatur.SignerCertificate.Subject)"
        Merken "  Fingerabdruck: $($signatur.SignerCertificate.Thumbprint)"
    }
    Merken ""
}

# --- Ist das Zertifikat eingetragen -----------------------------------
# Beide Orte, nicht nur LocalMachine: wer das Zertifikat ohne
# Administratorrechte eintraegt, landet in CurrentUser. Das wirkt fuer
# das eigene Konto und ist damit kein Fehler - eine Pruefung, die nur
# LocalMachine kennt, meldete faelschlich "FEHLT" und schickte auf
# eine falsche Faehrte.
$fingerabdruck = "DFE4686FB0E8442FD5CAC3C8A76D58A8EB27A8E8"
Merken "Zertifikat im Speicher"
$fuer_alle = $true
foreach ($speicher in "Root", "TrustedPublisher") {
    $orte = @()
    foreach ($ebene in "LocalMachine", "CurrentUser") {
        $treffer = Get-ChildItem "Cert:\$ebene\$speicher" -ErrorAction SilentlyContinue |
            Where-Object { $_.Thumbprint -eq $fingerabdruck }
        if ($treffer) { $orte += $ebene }
    }
    if ($orte.Count -eq 0) {
        Merken "  $speicher : FEHLT"
        $fuer_alle = $false
    } else {
        Merken "  $speicher : eingetragen ($($orte -join ', '))"
        if ($orte -notcontains "LocalMachine") { $fuer_alle = $false }
    }
}
if (-not $fuer_alle) {
    Merken "  Hinweis: fuer alle Konten des Rechners gilt nur der"
    Merken "           Eintrag unter LocalMachine."
}
Merken ""

# --- Der eigentliche Start --------------------------------------------
# Hier faellt auf, was beim Aufbau des Fensters schiefgeht: ein Modul,
# das der Virenscanner entfernt hat, eine fehlende Systembibliothek,
# eine Einstellung, die sich nicht schreiben laesst.
Merken "Startversuch"
Merken ("-" * 60)

$skript = @'
import sys, traceback, platform
print("Python:", sys.version.split()[0], platform.machine())
try:
    from ide.main import VERSION
    print("Natter-Version:", VERSION)
except Exception:
    print("Schon der erste Import scheitert:")
    traceback.print_exc(file=sys.stdout)
    sys.exit(2)

try:
    from ide.integritaet.start_pruefung import installation_pruefen
    ergebnis = installation_pruefen()
    if ergebnis is None:
        print("Integritaetspruefung: kein Manifest (Entwicklungsbaum)")
    elif ergebnis.in_ordnung:
        print("Integritaetspruefung: in Ordnung")
    else:
        print("Integritaetspruefung: ABWEICHUNG")
        for datei in ergebnis.betroffene_dateien[:10]:
            print("   ", datei)
except Exception:
    print("Integritaetspruefung scheitert:")
    traceback.print_exc(file=sys.stdout)

try:
    from ide.main import starten
    app, fenster = starten()
    print("Fenster aufgebaut:", fenster is not None)
    if fenster is not None:
        print("Fenster sichtbar:", fenster.isVisible())
        print()
        print("ERGEBNIS: Natter startet.")
    else:
        print()
        print("ERGEBNIS: Die Pruefung der Installation hat den Start abgelehnt.")
except Exception:
    print()
    print("ERGEBNIS: Der Start scheitert hier:")
    traceback.print_exc(file=sys.stdout)
    sys.exit(3)
'@

$tmp = Join-Path $env:TEMP "natter-startversuch.py"
$skript | Out-File -FilePath $tmp -Encoding utf8

Push-Location $programm
$ausgabe = & $python $tmp 2>&1
$code = $LASTEXITCODE
Pop-Location
Remove-Item $tmp -ErrorAction SilentlyContinue

foreach ($zeile in $ausgabe) { Merken "  $zeile" }
Merken ("-" * 60)
Merken ""
Merken "Rueckgabewert: $code"

# --- Was Natter selbst mitgeschrieben hat -----------------------------
$log = Join-Path $env:APPDATA "Natter\natter-fehler.log"
Merken ""
if (Test-Path $log) {
    Merken "Protokolldatei $log"
    Merken ("-" * 60)
    Get-Content $log -Tail 40 | ForEach-Object { Merken "  $_" }
} else {
    Merken "Keine Protokolldatei unter $log"
}

$zeilen | Out-File -FilePath $bericht -Encoding utf8
Write-Host ""
Write-Host "Der Bericht liegt auf dem Schreibtisch:" -ForegroundColor Green
Write-Host "  $bericht"
Write-Host ""
if (-not $Still) {
    Read-Host "Mit der Eingabetaste schliessen"
}
