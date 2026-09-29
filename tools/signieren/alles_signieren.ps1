# Signiert jede Binaerdatei im fertigen Programmordner, die noch keine
# gueltige Signatur hat.
#
# Warum das noetig ist: bis September 2026 signierte der Bau nur
# Natter.exe - von 820 Binaerdateien blieben 377 ohne Signatur,
# darunter die gesamte mitgelieferte Python samt numpy, scipy, pandas
# und sklearn. Eine Auslieferung, bei der neun von zehn Dateien keine
# Herkunft nennen, ist keine signierte Auslieferung.
#
# Was das nicht leistet: gegen eine eingeschaltete intelligente
# App-Steuerung hilft es nicht. Die entscheidet nach dem Ruf des
# einzelnen Dateihashs bei Microsoft und fuehrt eine mit einem selbst
# ausgestellten Zertifikat signierte Datei als unsigniert. Die
# Messung dazu steht in tools/signieren/README.md.
#
# Verwendung:
#   .\alles_signieren.ps1 -Ordner ..\..\dist\Natter
#   .\alles_signieren.ps1 -Ordner ..\..\dist\Natter -NurPruefen

param(
    [Parameter(Mandatory=$true)]
    [string]$Ordner,

    # Zaehlt nur, was fehlt, und aendert nichts.
    [switch]$NurPruefen
)

$ErrorActionPreference = "Stop"

#: Was Windows laedt und deshalb signiert sein muss. .cat und .sys
#: kommen in dieser Auslieferung nicht vor, stehen aber dabei, damit
#: eine kuenftige Abhaengigkeit nicht stillschweigend durchrutscht.
$ENDUNGEN = @("*.exe", "*.dll", "*.pyd", "*.sys", "*.cat", "*.ocx")

#: Vorlagen, aus denen PyInstaller bei "Als Exe exportieren" die
#: Schueler-Exe baut. Signiert laesst sich die fertige Exe nicht mehr
#: signieren (die Signatur der Vorlage steht dann mitten in der Datei).
#: Dieselbe Ausnahme steht in tools/ide_paketieren.py (NICHT_SIGNIERT)
#: und in Schritt 10 von tools/auslieferung_bauen.py.
$AUSGENOMMEN = "\PyInstaller\bootloader\"

$ZERT_NAME = "CN=Natter Codesignatur"
$ZEITSTEMPEL = "http://timestamp.digicert.com"

if (-not (Test-Path $Ordner)) {
    throw "Ordner nicht gefunden: $Ordner"
}

# Ueber den Zertifikatspeicher und nicht ueber die .pfx: ein Passwort
# auf der Kommandozeile steht in der Prozessliste, in der
# PowerShell-History und in jedem CI-Protokoll.
$zert = Get-ChildItem "Cert:\CurrentUser\My" -CodeSigningCert |
    Where-Object { $_.Subject -eq $ZERT_NAME } | Select-Object -First 1
if (-not $zert -and -not $NurPruefen) {
    throw "Kein Natter-Codesignatur-Zertifikat gefunden. Erst zertifikat_einrichten.ps1 ausfuehren."
}

Write-Host "Sehe $Ordner durch ..."
$alle = Get-ChildItem $Ordner -Recurse -File -Include $ENDUNGEN -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName.IndexOf($AUSGENOMMEN, [StringComparison]::OrdinalIgnoreCase) -lt 0 }

# Fremd signierte Dateien bleiben unangetastet. Qt und Microsoft haben
# ein Zertifikat einer oeffentlichen CA; ihre Signatur ist staerker als
# unsere, und sie zu ueberschreiben waere ein Rueckschritt.
$offen = @()
$fremd = 0
$eigen = 0
foreach ($datei in $alle) {
    $s = Get-AuthenticodeSignature $datei.FullName
    if ($s.Status -eq "Valid") {
        if ($s.SignerCertificate.Thumbprint -eq $zert.Thumbprint) { $eigen++ } else { $fremd++ }
    } else {
        $offen += $datei
    }
}

Write-Host ("  {0,5} Dateien gesamt" -f $alle.Count)
Write-Host ("  {0,5} bereits fremd signiert (Qt, Microsoft)" -f $fremd)
Write-Host ("  {0,5} bereits von Natter signiert" -f $eigen)
Write-Host ("  {0,5} ohne gueltige Signatur" -f $offen.Count)

if ($offen.Count -eq 0) {
    Write-Host "Nichts zu tun." -ForegroundColor Green
    exit 0
}

if ($NurPruefen) {
    Write-Host ""
    Write-Host "Diese Dateien haetten keine Signatur:" -ForegroundColor Yellow
    $offen | Select-Object -First 15 | ForEach-Object {
        "    " + $_.FullName.Substring($Ordner.Length).TrimStart('\')
    }
    if ($offen.Count -gt 15) { "    ... und {0} weitere" -f ($offen.Count - 15) }
    exit 1
}

Write-Host ""
Write-Host "Signiere $($offen.Count) Dateien ..."
$start = Get-Date
$fehlgeschlagen = @()
$zaehler = 0

foreach ($datei in $offen) {
    $zaehler++
    if ($zaehler % 10 -eq 0) {
        Write-Host ("  {0}/{1} ..." -f $zaehler, $offen.Count)
    }
    # Mit Zeitstempel: ohne ihn werden alle Signaturen ungueltig,
    # sobald das Zertifikat 2031 ablaeuft - auch auf Rechnern, auf
    # denen Natter laengst installiert ist.
    $ergebnis = Set-AuthenticodeSignature -FilePath $datei.FullName `
        -Certificate $zert -TimestampServer $ZEITSTEMPEL -HashAlgorithm SHA256
    if ($ergebnis.Status -ne "Valid") {
        $fehlgeschlagen += "$($datei.Name): $($ergebnis.Status) - $($ergebnis.StatusMessage)"
    }
}

$dauer = ((Get-Date) - $start).TotalSeconds
Write-Host ("Fertig in {0:N0} Sekunden." -f $dauer)

if ($fehlgeschlagen.Count -gt 0) {
    Write-Host ""
    Write-Host "Nicht signiert:" -ForegroundColor Red
    $fehlgeschlagen | Select-Object -First 10 | ForEach-Object { "    $_" }
    throw "$($fehlgeschlagen.Count) Datei(en) liessen sich nicht signieren."
}

Write-Host "Alle Dateien tragen jetzt eine gueltige Signatur." -ForegroundColor Green
