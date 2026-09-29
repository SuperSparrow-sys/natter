# Signiert eine Datei (Exe oder Installer) mit dem Natter-Code-Signing-
# Zertifikat aus zertifikat_einrichten.ps1. Siehe tools/ide_paketieren.py,
# das dieses Skript nach dem PyInstaller-Bau aufruft.
#
# Verwendung:
#   .\datei_signieren.ps1 -Datei ..\..\dist\Natter\Natter.exe

param(
    [Parameter(Mandatory=$true)]
    [string]$Datei
)

$ErrorActionPreference = "Stop"

$zertName = "CN=Natter Codesignatur"
$zertSpeicherort = "Cert:\CurrentUser\My"

$zert = Get-ChildItem $zertSpeicherort -CodeSigningCert |
    Where-Object { $_.Subject -eq $zertName } | Select-Object -First 1
if (-not $zert) {
    throw "Kein Natter-Codesignatur-Zertifikat gefunden. Erst zertifikat_einrichten.ps1 ausfuehren."
}

if (-not (Test-Path $Datei)) {
    throw "Datei nicht gefunden: $Datei"
}

$ergebnis = Set-AuthenticodeSignature -FilePath $Datei -Certificate $zert `
    -TimestampServer "http://timestamp.digicert.com" `
    -HashAlgorithm SHA256

if ($ergebnis.Status -ne "Valid") {
    throw "Signieren fehlgeschlagen: $($ergebnis.Status) - $($ergebnis.StatusMessage)"
}

Write-Host "Signiert: $Datei (Status: $($ergebnis.Status))"
