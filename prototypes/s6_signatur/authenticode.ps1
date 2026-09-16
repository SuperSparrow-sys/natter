# S6, Teil 1: Authenticode-Signatur mit selbst erstelltem Zertifikat.
# Siehe prototypes/s6_signatur/README.md.
#
# Verwendung:
#   .\authenticode.ps1 -Erstellen
#   .\authenticode.ps1 -Signieren -Datei .\S5Test.exe
#   .\authenticode.ps1 -Pruefen -Datei .\S5Test.exe

param(
    [switch]$Erstellen,
    [switch]$Signieren,
    [switch]$Pruefen,
    [string]$Datei
)

$zertName = "CN=Natter Codesignatur (privat, nicht öffentlich vertrauenswürdig)"
$zertSpeicherort = "Cert:\CurrentUser\My"

if ($Erstellen) {
    $zert = New-SelfSignedCertificate `
        -Subject $zertName `
        -Type CodeSigningCert `
        -KeyUsage DigitalSignature `
        -CertStoreLocation $zertSpeicherort `
        -NotAfter (Get-Date).AddYears(5)

    Write-Host "Zertifikat erstellt: $($zert.Thumbprint)"
    Write-Host "Sicherungskopie (mit Passwort) nicht vergessen, z. B.:"
    Write-Host "  `$pw = Read-Host -AsSecureString"
    Write-Host "  Export-PfxCertificate -Cert $zertSpeicherort\$($zert.Thumbprint) -FilePath natter-codesign.pfx -Password `$pw"
}

if ($Signieren) {
    if (-not $Datei) { throw "Bitte -Datei angeben." }
    $zert = Get-ChildItem $zertSpeicherort -CodeSigningCert | Where-Object { $_.Subject -eq $zertName } | Select-Object -First 1
    if (-not $zert) { throw "Kein passendes Zertifikat gefunden. Zuerst -Erstellen ausführen." }

    Set-AuthenticodeSignature -FilePath $Datei -Certificate $zert `
        -TimestampServer "http://timestamp.digicert.com" `
        -HashAlgorithm SHA256
}

if ($Pruefen) {
    if (-not $Datei) { throw "Bitte -Datei angeben." }
    Get-AuthenticodeSignature -FilePath $Datei | Format-List Status, StatusMessage, SignerCertificate
}
