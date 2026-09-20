# Natter signieren ("Weg A": kostenloses, selbst erstelltes Zertifikat)

Nutzer-Feedback (September 2026): Windows Smart App Control blockierte
den Start der unsignierten `Natter.exe` komplett (nicht nur eine
Warnung) - bestätigt über das Ereignisprotokoll
(`Microsoft-Windows-CodeIntegrity/Operational`, "did not meet the
Enterprise signing level requirements"). Ein gekauftes Authenticode-
Zertifikat (ca. 100-400 $/Jahr) löst das für **jeden** Rechner sofort,
kostet aber Geld. Die hier eingerichtete, kostenlose Alternative
funktioniert genauso gut, aber nur auf Rechnern, auf denen das
Zertifikat vorher als vertrauenswürdig eingetragen wurde (z. B. per
Gruppenrichtlinie auf allen Schulrechnern) - siehe Abschnitt
"Verteilung auf weitere Rechner" unten.

## Einmalige Einrichtung (pro Rechner, der signierte Builds erzeugt)

```powershell
powershell -ExecutionPolicy Bypass -File tools\signieren\zertifikat_einrichten.ps1
```

Erzeugt ein 5 Jahre gültiges Code-Signing-Zertifikat, trägt es auf
**diesem** Rechner als vertrauenswürdig ein (Stammzertifizierungs-
stellen + Vertrauenswürdige Herausgeber) und legt zwei Dateien in
diesem Ordner ab:

- `natter-codesign.cer` - öffentlicher Teil, **nicht geheim**. Das ist
  genau die Datei, die auf jedem weiteren Rechner verteilt wird.
- `natter-codesign.pfx` + `natter-codesign.pfx.passwort.txt` -
  **privater Schlüssel**. Niemals weitergeben, niemals committen
  (beide Dateiendungen stehen in `.gitignore`). Wer diese Datei plus
  Passwort hat, kann im Namen von "Natter" signieren. Sicherungskopie
  an einem sicheren Ort außerhalb des Repositorys aufbewahren - ohne
  sie muss bei einem Rechnerwechsel ein neues Zertifikat erzeugt
  werden (und dann auf allen Schulrechnern neu verteilt werden).

## Kompletter Bau (Exe + Installer, signiert)

```powershell
uv run python -m tools.auslieferung_bauen --version 0.2.0
```

Das ist der Normalweg. Ein Skript führt die drei Befehle unten in
der richtigen Reihenfolge aus, prüft nach jedem Schritt das
Ergebnis und bricht ab, statt eine kaputte Auslieferung
fertigzubauen – siehe `tools/auslieferung_bauen.py`. `--version`
ist weglassbar; dann bleibt die Nummer, wie sie ist (für einen
Probebau in Ordnung, für ein Update an die Schulen nicht, weil
Windows eine neue Fassung an `AppVersion` erkennt).

Von Hand, wenn ein einzelner Schritt wiederholt werden soll:

```powershell
uv run python -m tools.ide_paketieren
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" tools\natter.iss
powershell -ExecutionPolicy Bypass -File tools\signieren\datei_signieren.ps1 -Datei dist\installer\Natter-Setup.exe
```

Der erste Befehl lädt beim allerersten Mal die mitgelieferte CPython
herunter (rund 21 MB, danach zwischengespeichert) und installiert
Natter samt aller Bibliotheken hinein - seit M13 ist die Auslieferung
eine vollwertige Python-Installation und entsprechend groß
(`dist\Natter` rund 1,2 GB, der fertige Installer rund 340 MB).
Rechnen Sie für die ersten beiden Befehle zusammen mit einigen
Minuten.

`ide_paketieren.py` signiert `Natter.exe` automatisch (Schritt 1),
sofern ein Zertifikat vorhanden ist - sonst nur eine Warnung, kein
Abbruch. Der Installer selbst (`Natter-Setup.exe`) muss danach separat
signiert werden (dritter Befehl oben), weil Inno Setup ihn erst nach
`ide_paketieren.py` erzeugt.

**Prüfen:**

```powershell
Get-AuthenticodeSignature dist\Natter\Natter.exe
Get-AuthenticodeSignature dist\installer\Natter-Setup.exe
```

Beide sollten `Status: Valid` zeigen. Windows-Explorer → Rechtsklick
auf die Datei → Eigenschaften → Reiter "Digitale Signaturen" zeigt
denselben Status mit Herausgeber "Natter Codesignatur".

## Verteilung auf weitere Rechner (z. B. alle Schulrechner)

Eine signierte Exe allein reicht nicht - jeder Rechner muss dem
Zertifikat erst vertrauen. Dafür wird **nur** `natter-codesign.cer`
gebraucht (nicht die `.pfx`, kein Passwort nötig):

**Einzelner Rechner, manuell:**

```powershell
Import-Certificate -FilePath natter-codesign.cer -CertStoreLocation Cert:\LocalMachine\Root
Import-Certificate -FilePath natter-codesign.cer -CertStoreLocation Cert:\LocalMachine\TrustedPublisher
```
(Admin-PowerShell nötig, `LocalMachine` statt `CurrentUser`, damit es
für alle Konten auf dem Rechner gilt.)

**Viele Schulrechner per Gruppenrichtlinie (empfohlen):**

1. Gruppenrichtlinienverwaltung → Computerkonfiguration → Richtlinien
   → Windows-Einstellungen → Sicherheitseinstellungen →
   Richtlinien für öffentliche Schlüssel.
2. Rechtsklick auf "Vertrauenswürdige Stammzertifizierungsstellen" →
   Importieren → `natter-codesign.cer` auswählen.
3. Denselben Import wiederholen unter "Vertrauenswürdige Herausgeber".
4. GPO verknüpfen/aktualisieren - nach dem nächsten `gpupdate`
   (oder automatisch beim nächsten Anmeldezyklus) ist das Zertifikat
   auf allen erfassten Rechnern eingetragen, signierte Natter-Builds
   starten dort ohne Smart-App-Control-Blockade.

## Wenn das nicht reicht: echtes Zertifikat kaufen

Reicht "Weg A" nicht (z. B. weil Natter auch außerhalb der Schule,
an unbekannte Rechner verteilt werden soll), braucht es ein
öffentlich vertrautes Authenticode-Zertifikat (Sectigo, SSL.com,
DigiCert, …). Der Signierschritt selbst (`Set-AuthenticodeSignature`
bzw. `signtool sign`) bleibt gleich - nur das Zertifikat in
`zertifikat_einrichten.ps1` wird gegen das gekaufte ausgetauscht,
keine weiteren Codeänderungen nötig.
