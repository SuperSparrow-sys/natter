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
| `Lizenzen\` | `dist/Natter/Lizenzen/` nach dem Bau |

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
