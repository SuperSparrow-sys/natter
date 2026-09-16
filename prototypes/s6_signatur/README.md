# S6 – Signatur ohne gekauftes Zertifikat

Prüft: erkennt blockierte Dateien, OneDrive-Pfad, zu lange Pfade und
veränderte Dateien; Exe mit eigenem Zertifikat signiert; kein Alarm des
Windows-Virenscanners (Abschnitt 17.8, 23.3). Relevant erst für den Export
(M8) – zeitlich zuletzt.

Zwei unabhängige Teile: Authenticode-Signatur der `.exe` (PowerShell,
nativ) und signiertes Prüfsummen-Manifest (Python, `cryptography`,
Ed25519).

## Teil 1 – Authenticode-Signatur

```powershell
.\authenticode.ps1 -Erstellen
.\authenticode.ps1 -Signieren -Datei .\pfad\zu\einer.exe
.\authenticode.ps1 -Pruefen -Datei .\pfad\zu\einer.exe
```

(z. B. die `S5Test.exe` aus dem S5-Prototyp verwenden.)

**Prüfen:** `Get-AuthenticodeSignature` meldet `Status: Valid`; Datei danach
mit einem Hex-Editor oder Texteditor ein Byte ändern → erneut prüfen →
`Status` ist nicht mehr `Valid`. Windows-Explorer → Eigenschaften →
Digitale Signaturen zeigt den Herausgeber.

**Privater Schlüssel bleibt nur auf dem Laptop** (Zertifikatspeicher bzw.
`.pfx`-Sicherungskopie mit Passwort), niemals im Repository.

## Teil 2 – signiertes Prüfsummen-Manifest

```
uv run --with cryptography python manifest.py schluessel
uv run --with cryptography python manifest.py erstellen <programmordner>
uv run --with cryptography python manifest.py pruefen <programmordner>
```

`schluessel` erzeugt `privat.pem`/`oeffentlich.pem` (nicht committen –
stehen in `.gitignore`), `erstellen` berechnet SHA-256 je Datei im
angegebenen Ordner und signiert das Manifest, `pruefen` prüft Signatur und
Prüfsummen erneut.

**Prüfen:** nach `erstellen` meldet `pruefen` „alle Dateien stimmen
überein“. Danach eine Datei im Programmordner ändern, hinzufügen oder
löschen und erneut `pruefen` – die betroffene Datei muss in „Veränderte
Dateien“/„Fremde/zusätzliche Dateien“/„Fehlende Dateien“ erscheinen.

## Erfolgskriterium

- Teil 1: gültige Signatur erkennbar, Veränderung macht sie ungültig.
- Teil 2: Manipulation (verändert/fehlend/fremd) wird zuverlässig erkannt,
  gültiger Zustand wird nicht fälschlich als manipuliert gemeldet.
- Kein Alarm des Windows-Virenscanners beim Signieren/Prüfen selbst (separat
  bei S5 für die erzeugte `.exe` zu beobachten).

Ergebnis (bitte eintragen): **offen**
