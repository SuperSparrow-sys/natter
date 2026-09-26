# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **47**.

## Ein neuer Punkt

```markdown
## 47. Kurz, was nicht stimmt

**Gemeldet:** Datum, wo es auffiel (Fenster, Menü, Beispielprojekt),
Natter-Version.

**Beobachtet:** Was passiert ist und was stattdessen zu erwarten war.
Wörtlich übernommene Meldungen in Anführungszeichen.

**Ursache:** noch offen - oder nachgewiesen, mit Datei und Zeile.

**Zu tun:** Was geändert werden muss und woran das Erledigtsein zu
erkennen ist.
```

---

# Offen

## 4. Die Lizenzseite des Installers ist nie angesehen worden

**Beobachtet:** Die Textdateien `tools/lizenz_vorlagen/*.txt` sind
geprüft — Umlaute, Byte-Order-Mark, Inhalt. Wie sie im Installer
**aussehen**, ist nie jemand nachgegangen.

**Warum nicht:** Die Abnahme läuft über eine stille Installation
(`/VERYSILENT`), bei der keine Seite erscheint. Ein Bildschirmfoto des
Assistenten braucht eine angemeldete, interaktive Sitzung; die stand
bei den bisherigen Durchgängen nicht zur Verfügung.

**Noch zu prüfen:** Den Installer einmal von Hand durchklicken und
nachsehen, ob Lizenz- und Hinweisseite vollständig, mit richtigen
Umlauten und ohne abgeschnittene Zeilen erscheinen. **Das bleibt
offen** - dafür braucht es einen Menschen vor dem Bildschirm, und
eine stille Installation zeigt keine Seite.

**Was sich ohne das festhalten ließ** (zwei Tests in
`tests/test_textstil.py`):

- Beide Seiten sind in `tools/natter.iss` überhaupt eingebunden
  (`LicenseFile`, `InfoBeforeFile`). Eine Seite, die niemand
  einbindet, kann noch so schön sein.
- Keine Zeile ist länger als 80 Zeichen. Inno Setup zeigt beide
  Seiten in einem Feld fester Breite; was länger ist, bricht um und
  sieht nach einem Fehler aus. Gemessen liegt die längste Zeile bei
  74 Zeichen.

Umlaute und Byte-Order-Mark prüfen bereits
`test_der_installer_liest_seine_texte_als_utf8` und die
Umlaut-Tests.

**Nachgewiesen ohne Durchklicken (25. September 2026):** Die
Lizenzseite sagt „Die vollständige Lizenz steht nach der Installation
in der Datei LICENSE im Installationsordner." Dort liegt keine: der
Installationsordner enthält nur `Natter.exe`, `python\`, `Lizenzen\`
und `manifest.json`; Natters `LICENSE` steckt nur in
`python\Lib\site-packages\natter-<Version>.dist-info\licenses\`.
Entweder die Datei beim Paketieren nach `{app}\LICENSE` kopieren oder
den Satz ändern. Das lässt sich ohne Durchklicken beheben; das
Durchklicken selbst bleibt.

**Behoben ab 0.3.3:** `paketieren()` kopiert `LICENSE` in den
Programmordner, und die Rauchprobe (Schritt 6) bricht ab, wenn sie
fehlt. Offen bleibt nur das Durchklicken.


---

## 24. Die Auslieferung enthält GPL-Module, und Lizenztexte fehlen

**Gemeldet:** 25. September 2026, beim Zusammenfassen der
Planungsunterlagen in `docs/bericht.md`, Fassung 0.3.2.

**Beobachtet:** AGENTS.md und `docs/bericht.md`, Abschnitt 5, verlangen
nur Abhängigkeiten mit freizügiger Lizenz oder LGPL, kein PyQt und
keine GPL-only-Module von Qt wie Qt Charts. Geplant war dafür ein Test,
der die Pakete der Auslieferung mit ihrer Lizenz auflistet und bei GPL
fehlschlägt. Diesen Test gibt es nicht; kein Test im Repository nennt
„GPL".

**Ursache:** nachgewiesen - der Test stand nur im Plan (früher
`entwicklung.md`, Abschnitte 17.7 und 19) und wurde nie geschrieben.
`_lizenzen_sammeln()` in `tools/ide_paketieren.py` sammelt die
Lizenztexte und warnt bei fehlender Angabe, prüft aber nicht, welche
Lizenz es ist.

**Nachgemessen in `dist\Natter` (Fassung 0.3.2):**

- **Qt Charts, Qt Data Visualization und Qt Graphs werden
  ausgeliefert.** In `site-packages\PySide6` liegen `Qt6Charts.dll`,
  `Qt6ChartsQml.dll`, `Qt6DataVisualization.dll`,
  `Qt6DataVisualizationQml.dll`, `Qt6Graphs.dll`,
  `Qt6GraphsWidgets.dll` und die passenden `.pyd`/`.pyi`. Sie kommen
  mit `PySide6_Addons` und stehen nur unter GPL-3.0 oder einer
  kaufbaren Lizenz, nicht unter LGPL. Natter benutzt sie nicht; die
  frühere Planung sagte, sie würden aus dem Paket entfernt - das ist
  nie umgesetzt worden.
- **32 von rund 50 mitgelieferten Paketen haben keinen Lizenztext in
  `Lizenzen\`**, darunter PyInstaller, jedi, cryptography, Pillow,
  fontTools, contourpy, attrs, packaging und setuptools. MIT, BSD und
  Apache verlangen, dass der Lizenztext bei der Weitergabe dabei ist.
  Ursache: `_LAUFZEIT_PAKETE` in `tools/ide_paketieren.py` ist eine
  von Hand gepflegte Liste; laut ihrem Kommentar steckt PyInstaller
  „nicht in der gebauten Exe", was seit M13 nicht mehr stimmt.
- **PyInstaller steht unter GPL-2.0** mit einer Ausnahme für die
  erzeugten Programme. Natter braucht es für „Als Exe exportieren".
  Die Regel in AGENTS.md („nur freizügige Lizenzen oder LGPL") deckt
  das nicht ab; die Lizenzseite des Installers nennt es bereits.

**Zu tun:**

- Die Qt-Module Charts, DataVisualization und Graphs nach dem
  Auspacken entfernen, wie Tcl/Tk (`_tcl_tk_entfernen()`), und in der
  Rauchprobe (Schritt 6) prüfen, dass sie fehlen.
- Lizenztexte für **jedes** Paket der mitgelieferten Python sammeln,
  aus den Metadaten der installierten Pakete statt aus einer Liste.
- Ein Test, der für jedes Laufzeitpaket die Lizenz liest und bei GPL,
  AGPL oder unbekannter Lizenz fehlschlägt. Erlaubt: LGPL, die
  Doppellizenzen von PySide6/shiboken6 („LGPL-3.0 OR GPL"), und
  PyInstaller als ausdrücklich genannte Ausnahme - sofern das so
  entschieden wird.
- Erledigt, wenn die drei Module in `dist\Natter` fehlen, jedes Paket
  einen Lizenztext in `Lizenzen\` hat und der Test bei einem
  absichtlich eingetragenen GPL-Paket rot wird.

**Umgesetzt in Commit `9a83164`, nachgeprüft am Bau 0.3.3 (25. September
2026, Schülerweg Teil 1):** Der Bau meldet „35 Qt-Einträge unter GPL
entfernt", `Lizenzen\` hat 51 Einträge (0.3.2: 28), in einer frischen
Installation scheitert `import PySide6.QtCharts`. Der Test wird bei
einem eingetragenen GPL-Paket rot
(`tests/test_lizenzen_auslieferung.py`). Offen bleibt der Weg über
ein Update: wer 0.3.2 auf 0.3.3 aktualisiert, behält die Module
(Punkt 28). Bis Punkt 28 erledigt ist, bleibt dieser Punkt offen.

---

## 26. Ein Update erkennt die vorhandene Fassung nicht sichtbar

**Gemeldet:** 25. September 2026, vom Nutzer: „Wenn bereits ein
Natter-Programm installiert ist, soll die Exe das erkennen und sagen:
Update auf Version … Dabei sollen die veränderten Daten entweder
komplett gelöscht oder ersetzt werden."

**Stand heute (`tools/natter.iss`):** Die Grundlage ist da. Die feste
`AppId` lässt Inno Setup eine vorhandene Installation erkennen und
deren Ordner wieder vorschlagen, und `[InstallDelete]` leert vor dem
Kopieren die sieben Ordner, die Natter selbst in `site-packages`
mitbringt (`ide`, `pcl`, `docs` …). Es fehlt:

- Kein Hinweis auf das Update. Der Assistent sieht genauso aus wie
  bei einer Erstinstallation; die installierte Fassung wird nirgends
  genannt.
- Zielordner und Startmenü-Ordner werden bei einem Update erneut
  abgefragt (`DisableDirPage=no`, `DisableProgramGroupPage=no`).
- Kein Schutz gegen eine ältere Fassung über einer neueren.
- Die mitgelieferte Python wird nur überschrieben. Bringt eine neue
  Fassung etwa ein neueres numpy mit, bleiben Dateien der alten
  Paketversion liegen, die es in der neuen nicht mehr gibt - ein
  gemischter Stand, der erst beim Import auffällt. Dieselbe Sorte
  Befund wie beim Update auf 0.2.0 (`docs/bericht.md`, Abschnitt 8).

**Wie es in der Praxis gelöst wird** (Inno-Setup-Installer wie VS
Code, Git für Windows, Notepad++):

- Dieselbe `AppId` für alle Fassungen; Inno übernimmt dann Ordner,
  Startmenü und Zusatzaufgaben der vorhandenen Installation.
- `DisableDirPage=auto` und `DisableProgramGroupPage=auto`: bei einem
  Update entfallen die Seiten, bei einer Erstinstallation erscheinen
  sie.
- Die installierte Fassung aus der Registrierung lesen
  (`…\Uninstall\{AppId}_is1`, Wert `DisplayVersion`, unter HKCU oder
  HKLM) und im `[Code]`-Abschnitt auf der Willkommensseite nennen:
  „Natter 0.3.2 ist installiert und wird auf 0.3.3 aktualisiert. Die
  Projekte bleiben erhalten." Ist die installierte Fassung neuer,
  nachfragen oder abbrechen.
- Den Programmordner vollständig ersetzen, weil alles, was einem
  Benutzer gehört, woanders liegt: Projekte unter `Dokumente\Natter`,
  Einstellungen unter `%APPDATA%\Natter`. Zwei übliche Wege: den
  Anwendungsordner vor dem Kopieren leeren (`[InstallDelete]` mit
  `filesandordirs` für `{app}\python`), oder die alte Fassung vorher
  still über ihren eigenen Uninstaller entfernen. Der erste Weg ist
  der schlichtere und behält die Startmenü-Einträge.
- Eine laufende Natter vorher schließen (`CloseApplications`, Inno
  nutzt dafür den Neustart-Manager von Windows).

**Zu klären:** Über das Menü „Pakete" nachinstallierte Pakete liegen
in `{app}\python` und gingen beim vollständigen Ersetzen verloren. Die
Update-Meldung muss das sagen, oder die Liste der nachinstallierten
Pakete wird vorher gesichert und danach wieder eingespielt.

**Zu tun:** Hinweis auf der Willkommensseite mit alter und neuer
Nummer, Ordner-Seiten bei einem Update überspringen, Schutz gegen
eine ältere Fassung, `{app}\python` vor dem Kopieren vollständig
leeren, laufende Natter schließen. Erledigt, wenn ein Update von
0.3.2 auf die neue Fassung den Hinweis zeigt, danach keine Datei der
alten Fassung mehr im Programmordner liegt und Projekte und
Einstellungen unberührt sind.

**Nachgeprüft an 0.3.3 (25. September 2026, Schülerweg Teil 1,
Schritt 8):** Das Setup von 0.3.2 über einer installierten 0.3.0 und
das von 0.3.3 über 0.3.2 zeigen dieselben acht Seiten wie bei einer
Erstinstallation: Sprachauswahl, Willkommen („wird jetzt Natter
Version 0.3.3 … installieren"), Lizenz, Hinweis, Zielordner,
Startmenü, Zusatzaufgaben, Bereit. Die vorhandene Fassung wird
nirgends genannt; Zielordner und Startmenü sind aus der vorhandenen
Installation vorbelegt. Dass beim Update auch Dateien liegen bleiben,
steht als eigener Punkt 28. Belege: `docs/auswertung/schuelerweg_0.3.3.md`.

**Umgesetzt am 26. September 2026, Nachweis am nächsten Bau offen.** `tools/natter.iss` liest die installierte Fassung aus dem Deinstallationseintrag, nennt sie auf der Willkommensseite („Natter 0.3.3 ist installiert und wird auf 0.3.4 aktualisiert.“), überspringt bei einem Update Zielordner und Startmenü (`DisableDirPage=auto`, `DisableProgramGroupPage=auto`), lehnt eine ältere Fassung über einer neueren ab und schließt eine laufende Natter (`CloseApplications`). Nachgesehen an einem ohne Programmdateien übersetzten Setup (`/DOhneProgramm`) bis zur Seite „Bereit“: Hinweis und fünf statt acht Seiten; mit Nummer 0.3.2 über 0.3.3 die Ablehnung. Nachinstallierte Pakete: `tools/installer_pakete_merken.py` schreibt sie vor dem Kopieren mit der alten Python auf, nach dem Kopieren installiert das Setup sie per pip wieder; ohne Netz bleibt die Liste in `%APPDATA%\Natter\pakete_vor_update.txt`, und eine Meldung sagt, welche fehlen. Offen: ein echtes Update 0.3.2 → 0.3.4 mit einem nachinstallierten Paket, einmal mit und einmal ohne Netz.

---

## 28. Ein Update lässt Dateien der alten Fassung in `site-packages` liegen

**Gemeldet:** 25. September 2026, Schülerweg 0.3.3, Teil 1, Schritt 8.

**Beobachtet:** 0.3.2 installiert, 0.3.3 still darüber installiert.
Danach liegen 30 223 Dateien im Programmordner, bei einer frischen
0.3.3 sind es 30 075. Die 148 zusätzlichen Dateien:

- 141 Dateien der Qt-Module Charts, Data Visualization und Graphs
  (`Qt6Charts.dll`, `QtCharts.pyd`, `qml\QtCharts\…` und so weiter).
  `import PySide6.QtCharts` gelingt nach dem Update wieder. Genau diese
  Module entfernt der Bau seit 0.3.3, weil sie nur unter GPL stehen
  (Punkt 24); wer aktualisiert statt neu installiert, behält sie.
- 7 Dateien `natter-0.3.2.dist-info` neben `natter-0.3.3.dist-info`.
  `importlib.metadata.version("natter")` und `pip list` melden danach
  0.3.2. Natter selbst zeigt 0.3.3, weil es die Nummer aus
  `ide/main.py` liest.

Die vollständige Prüfung unter „Werkzeuge → Umgebung prüfen" meldet
trotzdem „alle Programmdateien unverändert".

**Ursache:** nachgewiesen. `[InstallDelete]` in `tools/natter.iss`
leert nur die sieben Ordner, die Natter selbst in `site-packages`
mitbringt, nicht die Fremdpakete und nicht die `dist-info` von Natter.
Das Manifest lässt Fremdpakete in `site-packages` bewusst aus, damit
pip dort nachinstallieren darf; Altdateien fallen deshalb nicht als
„fremd" auf.

**Zu tun:** Beim Update `{app}\python` vollständig ersetzen (siehe
Punkt 26, dort auch die Frage nach Paketen, die über „Pakete"
nachinstalliert wurden), mindestens aber die entfernten Qt-Module und
alte `natter-*.dist-info` per `[InstallDelete]` löschen. Erledigt,
wenn nach einem Update von 0.3.2 die Dateiliste der einer frischen
Installation entspricht (bis auf die Uninstaller-Dateien) und
`import PySide6.QtCharts` scheitert.

**Umgesetzt am 26. September 2026, Nachweis am nächsten Bau offen.** `[InstallDelete]` leert `{app}\python` vollständig (Pakete siehe Punkt 26). Test in `tests/test_installer_update.py`. Offen: nach einem echten Update von 0.3.2 die Dateiliste gegen die frische Installation vergleichen; `import PySide6.QtCharts` muss scheitern und `pip list` die neue Fassung melden.

---

## 34. Exportierte Exe lassen sich nicht signieren, weil der Bau die PyInstaller-Vorlagen signiert

**Gemeldet:** 26. September 2026, Schülerweg 0.3.3, Teil 2, Schritt 27.

**Beobachtet:** „Projekt → Als Exe exportieren …“ baut die Exe (GUI
55 s, 54,9 MB; Konsole 9,7 s, 8,0 MB), die Statuszeile endet aber mit
„Exe erstellt: … - Nicht signiert: UnknownError“.
`Get-AuthenticodeSignature` meldet `NotSigned`. Von Hand mit demselben
Zertifikat und Aufruf signiert: „%1 ist keine zulässige
Win32-Anwendung“. Eine Kopie von `Natter.exe` lässt sich dagegen
einwandfrei signieren. Die exportierte Exe trägt mitten in der Datei
eine Zertifikatstabelle (Offset 311 808, 7 160 Byte).

**Ursache:** nachgewiesen. Der Auslieferungsbau signiert jede
Binärdatei der Installation, auch
`python\Lib\site-packages\PyInstaller\bootloader\Windows-64bit-intel\run.exe`,
`runw.exe`, `run_d.exe`, `runw_d.exe` („Natter Codesignatur“, im
Entwicklungsbaum unsigniert). PyInstaller hängt beim Export das
Programmarchiv hinter diese Vorlage; die vorhandene Signatur steht
danach nicht mehr am Ende, und Windows lehnt die Datei beim Signieren
ab. Betroffen ist jede Fassung, seit der Bau alle Binärdateien
signiert (0.3.1).

**Zu tun:** Die Bootloader-Vorlagen von PyInstaller beim Signieren
auslassen (Ausnahmeliste in `tools/signieren/alles_signieren.ps1` und
`_signieren_mit_zwischenspeicher`, Schritt 10 entsprechend), oder
beim Export vor dem Signieren eine vorhandene Signatur entfernen. Die
Meldung „UnknownError“ durch einen deutschen Satz mit Grund ersetzen.
Ein Test in der Rauchprobe: aus der gebauten Python eine kleine Exe
exportieren und signieren. Erledigt, wenn eine in der installierten
Fassung exportierte Exe `Valid` signiert ist.

**Umgesetzt am 26. September 2026, Nachweis am nächsten Bau offen.** Die Vorlagen unter `PyInstaller\bootloader\` sind vom Signieren ausgenommen, an allen drei Stellen gleich (`ausgenommen_vom_signieren`/`NICHT_SIGNIERT` in `tools/ide_paketieren.py`, `$AUSGENOMMEN` in `tools/signieren/alles_signieren.ps1`, Schritt 10); Schritt 10 bricht jetzt umgekehrt ab, wenn eine Vorlage signiert ist (Test mit echtem PowerShell und einer von Microsoft signierten Datei). Nachgewiesen am Entwicklungsbaum: eine mit dem unsignierten Bootloader gebaute Exe lässt sich signieren (`Valid`). Die Statuszeile nennt statt „UnknownError“ einen deutschen Grund mit der Meldung von Windows. Offen: in der nächsten gebauten Installation eine Schüler-Exe exportieren; sie muss `Valid` signiert sein.

---

## 46. Der Signaturtest läuft im CI nicht, und ein Debugger-Test wackelt dort

**Gemeldet:** 26. September 2026, GitHub-Actions-Läufe zu `250930c`
bis `18432cd`.

**Beobachtet:**

- `test_schritt_10_meldet_eine_signierte_vorlage` in
  `tests/test_auslieferung_bauen.py` braucht eine Datei, deren Kopie
  `Get-AuthenticodeSignature` als `Valid` meldet. Auf dem Runner
  (Windows Server) gilt keine der Kandidaten als gültig signiert,
  weder `notepad.exe` noch `pwsh.exe` noch `git.exe`. Der Test wird
  dort übersprungen („keine Datei mit eingebetteter Signatur
  gefunden“); lokal läuft er und ist grün. Die Prüfung von Schritt 10
  auf signierte Vorlagen wird damit im CI nicht getestet.
- `test_variablen_panel_kommt_beim_halt_nach_vorne` in
  `tests/test_hauptfenster_debugger.py` lief in Lauf 18432cd in die
  Zeitgrenze von 45 Sekunden, bevor debugpy am Haltepunkt hielt. Der
  Code war derselbe wie im grünen Lauf davor; die Wiederholung des
  Jobs war grün.

**Ursache:** für den ersten Teil vermutlich die Zertifikatsprüfung auf
dem Runner (Katalogsignaturen, Sperrlisten ohne Netz), nicht
nachgewiesen. Für den zweiten noch offen; ein langsamer Runner liegt
nahe.

**Zu tun:** Für den Signaturtest eine Datei finden, die auch auf dem
Runner `Valid` ist, ohne dafür ein Zertifikat in einen Windows-Speicher
einzutragen. Beim Debugger-Test beobachten, ob er wieder ausfällt;
wenn ja, die Startzeit von debugpy auf dem Runner messen. Erledigt,
wenn der Signaturtest im CI läuft und der Debugger-Test in zehn
Läufen hintereinander grün ist.

---

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

## 7. Der Starter braucht die Hälfte der Startzeit ~~(zurückgestellt)~~

**Beobachtet:** Vom Doppelklick bis zum Fenster vergehen rund 1,65
Sekunden. Davon entfallen etwa 790 Millisekunden auf `Natter.exe`,
bevor überhaupt Python anläuft — der Starter entpackt sich und fährt
dann eine zweite Python hoch.

**Entschieden:** Der Starter bleibt, wie er ist. `Natter.exe` behält
sein eigenes Symbol, seine Versionsangabe und seine Signatur; die
Zeit wird dafür in Kauf genommen.

Hier nur festgehalten, damit die Frage nicht in einem halben Jahr noch
einmal von vorn aufgemacht wird. Gemessene Alternativen waren:
`--onedir` statt `--onefile` (spart 200 ms, kostet 15,8 MB und einen
Ordner neben der Exe) und die Verknüpfung direkt auf `pythonw.exe`
(spart 790 ms, kostet das eigene signierte `Natter.exe`).
