# Traegt das Natter-Zertifikat auf diesem Rechner als
# vertrauenswuerdig ein. Danach nennt Windows beim Installieren
# keinen unbekannten Herausgeber mehr.
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
    # Wird die Rueckfrage abgelehnt oder fehlen die Rechte ganz, wirft
    # Start-Process. Ohne dieses try/catch schliesst sich das Fenster
    # dann wortlos, und es sieht aus, als sei alles in Ordnung
    # gewesen - dabei ist nichts eingetragen worden.
    try {
        Start-Process powershell.exe -Verb RunAs -ArgumentList @(
            "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`""
        )
    } catch {
        Write-Host ""
        Write-Host "Nichts eingetragen." -ForegroundColor Red
        Write-Host "Die Rueckfrage nach Administratorrechten wurde abgelehnt,"
        Write-Host "oder dieses Konto hat keine. Ohne sie laesst sich das"
        Write-Host "Zertifikat nicht fuer den Rechner eintragen - dann ist die"
        Write-Host "Systembetreuung der richtige Weg."
        Write-Host ""
        Read-Host "Mit der Eingabetaste schliessen"
    }
    exit
}

$daten = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($zertifikat)
Write-Host ""
Write-Host "Zertifikat:    $($daten.Subject)"
Write-Host "Gueltig bis:   $($daten.NotAfter.ToString('dd.MM.yyyy'))"
Write-Host "Fingerabdruck: $($daten.Thumbprint)"
Write-Host ""

# Der Fingerabdruck steht hier fest drin, derselbe wie in
# ZUERST-LESEN.txt. Bis 0.3.3 zeigte das Skript ihn nur an und trug
# im selben Zug ein - der verlangte Vergleich war erst moeglich, als
# es schon zu spaet war (Punkt 29). Eine untergeschobene andere .cer
# wird jetzt gar nicht erst eingetragen.
$ERWARTET = "DFE4686FB0E8442FD5CAC3C8A76D58A8EB27A8E8"
if ($daten.Thumbprint -ne $ERWARTET) {
    Write-Host "Nichts eingetragen." -ForegroundColor Red
    Write-Host "Der Fingerabdruck stimmt nicht mit dem von Natter ueberein:"
    Write-Host "  erwartet: $ERWARTET"
    Write-Host "  gefunden: $($daten.Thumbprint)"
    Write-Host "Diese natter-codesign.cer stammt nicht aus dem Natter-Paket."
    Write-Host ""
    Read-Host "Mit der Eingabetaste schliessen"
    exit 1
}

# Zwei Speicher, zwei Aufgaben: "Root" laesst Windows der Signatur
# glauben, "TrustedPublisher" laesst sie beim Ausfuehren durchgehen,
# ohne nachzufragen. Einer allein genuegt nicht.
# Nachsehen statt melden: Import-Certificate gibt keinen Fehler,
# wenn eine Gruppenrichtlinie den Speicher festhaelt. Gemeldet wurde
# dann "eingetragen", und im Speicher stand nichts.
$fehlt = @()
foreach ($speicher in "Root", "TrustedPublisher") {
    try {
        Import-Certificate -FilePath $zertifikat `
            -CertStoreLocation "Cert:\LocalMachine\$speicher" -ErrorAction Stop | Out-Null
    } catch {
        Write-Host "  $speicher : $($_.Exception.Message)" -ForegroundColor Red
    }

    $drin = Get-ChildItem "Cert:\LocalMachine\$speicher" -ErrorAction SilentlyContinue |
        Where-Object { $_.Thumbprint -eq $daten.Thumbprint }
    if ($drin) {
        Write-Host "  eingetragen in $speicher" -ForegroundColor Green
    } else {
        Write-Host "  NICHT eingetragen in $speicher" -ForegroundColor Red
        $fehlt += $speicher
    }
}

Write-Host ""
if ($fehlt.Count -gt 0) {
    Write-Host "Der Eintrag ist unvollstaendig." -ForegroundColor Red
    Write-Host "Windows meldet beim Installieren weiterhin einen unbekannten"
    Write-Host "Herausgeber. Haelt eine Gruppenrichtlinie die Speicher fest,"
    Write-Host "fuehrt nur der Weg ueber die Systembetreuung weiter."
} else {
    Write-Host "Fertig. Natter-Setup.exe laesst sich jetzt installieren." -ForegroundColor Green
}
Write-Host ""
Read-Host "Mit der Eingabetaste schliessen"
