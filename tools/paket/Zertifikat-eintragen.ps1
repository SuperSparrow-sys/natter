# Traegt das Natter-Zertifikat auf diesem Rechner als
# vertrauenswuerdig ein. Danach startet die signierte Natter.exe,
# ohne dass Smart App Control sie blockiert.
#
# Rechtsklick auf diese Datei -> "Mit PowerShell ausfuehren".
# Die Rueckfrage von Windows mit "Ja" beantworten: der Eintrag gilt
# fuer alle Benutzerkonten des Rechners und braucht dafuer
# Administratorrechte.

$ErrorActionPreference = "Stop"

$zertifikat = Join-Path $PSScriptRoot "natter-codesign.cer"

# Zweiter Ort fuer den Fall, dass diese Datei aus dem Quellbaum heraus
# aufgerufen wird: dort liegt das Zertifikat unter tools\signieren, und
# erst beim Paketieren wird es hierher kopiert. Ohne diesen Zweig
# bricht das Skript im Quellbaum mit der Meldung ab, das Paket sei
# unvollstaendig entpackt - was dann in die Irre fuehrt.
if (-not (Test-Path $zertifikat)) {
    $quellordner = Join-Path (Split-Path $PSScriptRoot -Parent) "signieren"
    $ausQuelle = Join-Path $quellordner "natter-codesign.cer"
    if (Test-Path $ausQuelle) {
        $zertifikat = $ausQuelle
    }
}

if (-not (Test-Path $zertifikat)) {
    Write-Host "natter-codesign.cer fehlt neben dieser Datei." -ForegroundColor Red
    Write-Host "Das Paket bitte vollstaendig entpacken, nicht einzelne Dateien."
    Read-Host "Mit der Eingabetaste schliessen"
    exit 1
}

# Ohne Administratorrechte laesst sich nur der eigene Benutzer
# eintragen - auf einem Schulrechner waere das fuer die naechste
# Klasse wirkungslos. Deshalb hier neu starten, statt es halb zu tun.
$identitaet = [Security.Principal.WindowsIdentity]::GetCurrent()
$rolle = New-Object Security.Principal.WindowsPrincipal($identitaet)
if (-not $rolle.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Administratorrechte werden gebraucht - Windows fragt gleich nach."
    Start-Process powershell.exe -Verb RunAs -ArgumentList @(
        "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`""
    )
    exit
}

$daten = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($zertifikat)
Write-Host ""
Write-Host "Zertifikat:    $($daten.Subject)"
Write-Host "Gueltig bis:   $($daten.NotAfter.ToString('dd.MM.yyyy'))"
Write-Host "Fingerabdruck: $($daten.Thumbprint)"
Write-Host ""

# Zwei Speicher, zwei Aufgaben: "Root" laesst Windows der Signatur
# glauben, "TrustedPublisher" laesst Smart App Control den Start zu.
# Einer allein genuegt nicht.
foreach ($speicher in "Root", "TrustedPublisher") {
    Import-Certificate -FilePath $zertifikat `
        -CertStoreLocation "Cert:\LocalMachine\$speicher" | Out-Null
    Write-Host "  eingetragen in $speicher" -ForegroundColor Green
}

Write-Host ""
Write-Host "Fertig. Natter-Setup.exe laesst sich jetzt installieren." -ForegroundColor Green
Write-Host ""
Read-Host "Mit der Eingabetaste schliessen"
