# Nimmt das Natter-Zertifikat aus den Vertrauensspeichern wieder
# heraus.
#
# Wer Vertrauen vergibt, muss es zuruecknehmen koennen: nach dem
# Schuljahr, beim Ausmustern eines Geraets, oder wenn der Verdacht
# besteht, dass der private Schluessel des Entwicklers abhandengekommen
# ist. Ein selbst ausgestelltes Zertifikat laesst sich nicht
# widerrufen - es gibt keine Sperrliste, die Windows abfragen koennte.
# Der Eintrag von Hand zurueckgenommen ist die einzige Moeglichkeit.
#
# Rechtsklick auf diese Datei -> "Mit PowerShell ausfuehren".
#
# Danach meldet Windows beim Installieren wieder einen unbekannten
# Herausgeber. Die Installation selbst bleibt unberuehrt; sie laesst
# sich ueber "Apps & Features" entfernen.

param([switch]$Still)

$ErrorActionPreference = "Stop"

$FINGERABDRUCK = "DFE4686FB0E8442FD5CAC3C8A76D58A8EB27A8E8"

$identitaet = [Security.Principal.WindowsIdentity]::GetCurrent()
$rolle = New-Object Security.Principal.WindowsPrincipal($identitaet)
$admin = $rolle.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $admin) {
    Write-Host "Administratorrechte werden gebraucht - Windows fragt gleich nach."
    Start-Process powershell.exe -Verb RunAs -ArgumentList @(
        "-ExecutionPolicy", "Bypass", "-File", "`"$PSCommandPath`""
    )
    exit
}

Write-Host ""
Write-Host "Suche $FINGERABDRUCK ..."
$gefunden = 0

# Ueber die Store-API und nicht ueber Remove-Item: den
# Benutzer-Stammspeicher laesst der PowerShell-Anbieter nicht
# beschreiben ("Der Vorgang ist fuer den Benutzerstammspeicher nicht
# zulaessig"), die API schon.
foreach ($ebene in "LocalMachine", "CurrentUser") {
    foreach ($name in "Root", "TrustedPublisher") {
        try {
            $speicher = New-Object System.Security.Cryptography.X509Certificates.X509Store($name, $ebene)
            $speicher.Open("ReadWrite")
            $treffer = $speicher.Certificates | Where-Object { $_.Thumbprint -eq $FINGERABDRUCK }
            foreach ($zert in $treffer) {
                $speicher.Remove($zert)
                Write-Host "  entfernt aus $ebene\$name" -ForegroundColor Green
                $gefunden++
            }
            $speicher.Close()
        } catch {
            Write-Host "  $ebene\$name : $($_.Exception.Message)" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
if ($gefunden -eq 0) {
    Write-Host "Nichts gefunden - das Zertifikat war nicht eingetragen."
} else {
    Write-Host "$gefunden Eintrag/Eintraege entfernt." -ForegroundColor Green
    Write-Host "Windows meldet beim Installieren wieder einen unbekannten"
    Write-Host "Herausgeber. Die Installation selbst bleibt unberuehrt."
}
Write-Host ""

if (-not $Still) {
    Read-Host "Mit der Eingabetaste schliessen"
}
