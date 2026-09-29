# Das Paket für die Schule

Was eine Schule bekommt, ist nicht die `Natter-Setup.exe` allein.
Ohne das Zertifikat blockiert Windows den Start auf Rechnern mit Smart
App Control, und ohne Anleitung weiß niemand, warum.

Hier liegen die Dateien, die dafür von Hand geschrieben sind. Alles
andere im Paket entsteht beim Bau oder liegt schon im Repository.

Zu jedem `.ps1` gehört ein gleichnamiges `.cmd`. Ein PowerShell-Skript
lässt sich auf einem frisch aufgesetzten Rechner nicht per Doppelklick
starten: die Ausführungsrichtlinie steht dort auf `Restricted`, und
Dateien aus einem entpackten ZIP tragen zusätzlich die Markierung „aus
dem Internet". Das `.cmd` ruft dasselbe Skript mit
`-ExecutionPolicy Bypass` auf, und zwar nur für diesen einen Aufruf.

## Inhalt des Pakets

| Datei | Woher |
|---|---|
| `ZUERST-LESEN.txt` | aus diesem Ordner |
| `Zertifikat-eintragen.cmd` | aus diesem Ordner |
| `Zertifikat-eintragen.ps1` | aus diesem Ordner |
| `natter-codesign.cer` | `tools/signieren/` |
| `Natter-Setup.exe` | `dist/installer/` nach dem Bau |
| `Natter-pruefen.cmd` | aus diesem Ordner |
| `Natter-pruefen.ps1` | aus diesem Ordner |
| `Zertifikat-entfernen.cmd` | aus diesem Ordner |
| `Zertifikat-entfernen.ps1` | aus diesem Ordner |
| `Handbuch.md` | `docs/handbuch.md` |
| `Handbuch.html` | daraus erzeugt, zum Lesen im Browser |
| `Lizenzen\` | `dist/Natter/Lizenzen/` nach dem Bau |

## Wenn Natter auf einem Rechner nicht startet

`Natter-pruefen.ps1` startet die installierte Natter über ihre eigene
Python, fängt ab, woran sie scheitert, und legt einen Bericht auf den
Schreibtisch. Darin stehen Windows-Fassung, Signaturstatus, wo das
Zertifikat eingetragen ist, das Ergebnis der Integritätsprüfung und
der vollständige Traceback des Startversuchs.

Das Skript prüft beide Zertifikatspeicher, `LocalMachine` und
`CurrentUser`. Eine Prüfung, die nur den ersten kennt, meldet bei
einem Eintrag ohne Administratorrechte fälschlich „FEHLT" und schickt
auf eine falsche Fährte.

## Was niemals hineingehört

`natter-codesign.pfx` und die Passwortdatei daneben. Das ist der
private Schlüssel; wer ihn hat, kann im Namen von „Natter" signieren.
Im Paket steht ausschließlich die `.cer`, und die enthält nur den
öffentlichen Teil (`HasPrivateKey` ist `False`).

Vor dem Verschicken lohnt der Blick:

```powershell
$a = [System.IO.Compression.ZipFile]::OpenRead($zip)
$a.Entries | Where-Object { $_.Name -match '\.pfx$|passwort' }
```

Die Ausgabe muss leer sein.


## Smart App Control

Mit eingeschaltetem Smart App Control startet Natter nicht, und
daran ändert der Zertifikat-Eintrag nichts. Das war zunächst anders
eingeschätzt worden, und die Fehleinschätzung hat zwei Auslieferungen
gekostet.

Was gemessen wurde: mit dem Zertifikat in `LocalMachine\Root` und
`LocalMachine\TrustedPublisher` und eingeschaltetem Smart App Control
wurden frisch signierte Bibliotheken beim Laden abgewiesen. Im
Ereignisprotokoll stehen sie als `ValidatedSigningLevel=1`, also als
unsigniert, obwohl `Get-AuthenticodeSignature` sie als `Valid`
führt. Dieselbe Datei lief vor dem Nachsignieren und war danach
gesperrt - gleiches Zertifikat, gleicher Rechner. Entschieden wird
nach dem Ruf des einzelnen Dateihashs bei Microsoft, und für eine
frisch signierte Datei ist das ein Münzwurf.

Das Durchsignieren durch `tools/signieren/alles_signieren.ps1` bleibt
trotzdem: es gibt jeder Datei einen Herausgeber, und eine
nachträgliche Veränderung fällt auf. Nur der Zweck ist ein anderer
als gedacht.

Wer Natter auf einem solchen Rechner braucht, kommt um eines von
beidem nicht herum: die intelligente App-Steuerung ausschalten - was
Microsoft nur in eine Richtung zulässt - oder ein Zertifikat einer
öffentlichen Zertifizierungsstelle beschaffen.

Betroffen sind vor allem frisch aufgesetzte Einzelgeräte. Auf zentral
verwalteten Rechnern (Intune, Domäne) ist Smart App Control von Haus
aus abgeschaltet.
