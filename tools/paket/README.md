# Das Paket für die Schule

Was eine Lehrkraft bekommt, ist nicht die `Natter-Setup.exe` allein.
Ohne das Zertifikat blockiert Windows den Start auf Rechnern mit Smart
App Control, und ohne Anleitung weiß niemand, warum.

Hier liegen die beiden Dateien, die dafür von Hand geschrieben sind.
Alles andere im Paket entsteht beim Bau oder liegt schon im
Repository.

## Inhalt des Pakets

| Datei | Woher |
|---|---|
| `ZUERST-LESEN.txt` | aus diesem Ordner |
| `Zertifikat-eintragen.ps1` | aus diesem Ordner |
| `natter-codesign.cer` | `tools/signieren/` |
| `Natter-Setup.exe` | `dist/installer/` nach dem Bau |
| `Handbuch.md` | `docs/fuer_lehrkraefte.md` |
| `Handbuch.html` | daraus erzeugt, zum Lesen im Browser |
| `Natter-pruefen.ps1` | aus diesem Ordner |
| `Zertifikat-entfernen.ps1` | aus diesem Ordner |
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

Der Grund, warum der Zertifikat-Eintrag überhaupt nötig ist. Smart
App Control blockiert unsignierte Programme vollständig - nicht mit
einer Warnung, sondern mit einem Abbruch beim Start.

Im September 2026 fiel dabei auf, dass der Eintrag allein nicht
genügte: der Bau signierte nur `Natter.exe`, und von 820
Binärdateien blieben 377 ohne Signatur. Blockiert wurde
`python\DLLs\_socket.pyd`, und die Blockade wäre auf dem nächsten
Rechner an einer anderen Datei hängen geblieben - was durchkam,
entschied bis dahin die Cloud-Reputation von Microsoft.

Auf einem Testrechner nachgewiesen: eine einzige signierte Datei
reichte, damit Natter startete. Smart App Control akzeptiert also ein
selbst ausgestelltes Zertifikat, sofern es in `LocalMachine\Root` und
`LocalMachine\TrustedPublisher` liegt. Microsofts eigene
Dokumentation ist an dieser Stelle zu eng formuliert; sie spricht nur
von Zertifizierungsstellen im Trusted Root Program.

Seitdem signiert `tools/signieren/alles_signieren.ps1` jede
Binärdatei ohne gültige Signatur, und Schritt 10 des Baus bricht ab,
wenn auch nur eine übrig bleibt.

Betroffen sind vor allem frisch aufgesetzte Einzelgeräte. Auf zentral
verwalteten Rechnern (Intune, Domäne) ist Smart App Control von Haus
aus abgeschaltet.
