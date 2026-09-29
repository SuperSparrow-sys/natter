# Einmalige Einrichtung eines selbst erstellten Code-Signing-Zertifikats
# für Natter - die kostenlose Alternative zu einem gekauften
# Authenticode-Zertifikat. Was es leistet und was nicht, steht in
# docs/bericht.md, Abschnitt 7.5 und 7.6.
#
# Erzeugt das Zertifikat, installiert es auf DIESEM Rechner als
# vertrauenswürdig (Stammzertifizierungsstellen + Vertrauenswürdige
# Herausgeber - beides nötig, ein selbstsigniertes Zertifikat ist
# seine eigene Stammstelle) und exportiert zwei Dateien:
#   natter-codesign.cer - der öffentliche Teil. Nicht geheim, das ist
#     genau das, was auf jeden weiteren Rechner (z. B. Schulrechner
#     per GPO) verteilt wird, damit dort ebenfalls vertraut wird.
#   natter-codesign.pfx - der private Schlüssel, passwortgeschützt.
#     NIEMALS weitergeben oder committen (siehe .gitignore) - wer
#     diese Datei + Passwort hat, kann im Namen von "Natter" signieren.
#
# Verwendung:
#   .\zertifikat_einrichten.ps1
# (einmalig; ein erneuter Lauf verwendet ein vorhandenes Zertifikat
# weiter, statt ein neues zu erzeugen, siehe -Force zum Erneuern.)

param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$zertName = "CN=Natter Codesignatur"
$zertSpeicherort = "Cert:\CurrentUser\My"
$zielOrdner = $PSScriptRoot
$cerPfad = Join-Path $zielOrdner "natter-codesign.cer"
$pfxPfad = Join-Path $zielOrdner "natter-codesign.pfx"
$passwortPfad = Join-Path $zielOrdner "natter-codesign.pfx.passwort.txt"

$vorhanden = Get-ChildItem $zertSpeicherort -CodeSigningCert |
    Where-Object { $_.Subject -eq $zertName } | Select-Object -First 1

if ($vorhanden -and -not $Force) {
    Write-Host "Zertifikat existiert bereits: $($vorhanden.Thumbprint)"
    $zert = $vorhanden
} else {
    Write-Host "Erzeuge neues Code-Signing-Zertifikat ..."
    $zert = New-SelfSignedCertificate `
        -Subject $zertName `
        -Type CodeSigningCert `
        -KeyUsage DigitalSignature `
        -KeyExportPolicy Exportable `
        -CertStoreLocation $zertSpeicherort `
        -NotAfter (Get-Date).AddYears(5)
    Write-Host "Erzeugt: $($zert.Thumbprint)"
}

# Zufälliges Passwort für die .pfx-Sicherungskopie - lokal abgelegt
# (gitignored), nicht interaktiv abgefragt, damit dieses Skript auch
# automatisiert laufen kann.
Add-Type -AssemblyName System.Web -ErrorAction SilentlyContinue
$klartextPasswort = [System.Convert]::ToBase64String((1..24 | ForEach-Object { Get-Random -Maximum 256 }))
$securePasswort = ConvertTo-SecureString -String $klartextPasswort -AsPlainText -Force

Export-PfxCertificate -Cert "$zertSpeicherort\$($zert.Thumbprint)" -FilePath $pfxPfad -Password $securePasswort | Out-Null
Set-Content -Path $passwortPfad -Value $klartextPasswort -NoNewline
Export-Certificate -Cert "$zertSpeicherort\$($zert.Thumbprint)" -FilePath $cerPfad | Out-Null

Write-Host "Exportiert: $pfxPfad (privat, Passwort in $passwortPfad)"
Write-Host "Exportiert: $cerPfad (oeffentlich, zur Verteilung)"

# Auf DIESEM Rechner als vertrauenswuerdig eintragen, damit signierte
# Dateien hier sofort ohne Warnung/Block laufen. Fuer weitere Rechner
# (Schulrechner) muss natter-codesign.cer dort ebenso eingetragen
# werden - siehe tools/signieren/VERTEILUNG.md.
$oeffentlichesZert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2($cerPfad)

foreach ($speicher in @(
    @{Name="Root"; Store="Cert:\CurrentUser\Root"},
    @{Name="TrustedPublisher"; Store="Cert:\CurrentUser\TrustedPublisher"}
)) {
    $ziel = New-Object System.Security.Cryptography.X509Certificates.X509Store($speicher.Name, "CurrentUser")
    $ziel.Open("ReadWrite")
    $ziel.Add($oeffentlichesZert)
    $ziel.Close()
    Write-Host "In $($speicher.Store) eingetragen."
}

Write-Host ""
Write-Host "Fertig. Pruefen mit:"
Write-Host "  Get-ChildItem Cert:\CurrentUser\TrustedPublisher | Where-Object Subject -eq '$zertName'"
