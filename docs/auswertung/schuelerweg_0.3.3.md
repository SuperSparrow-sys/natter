# Schülerweg 0.3.3 – Auswertung

Der Weg eines Schülers auf einem Schulrechner, geprüft an der
ausgelieferten Fassung 0.3.3 (gebaut mit `--nicht-veroeffentlichen`),
nicht am Entwicklungsbaum. Teil 1: Vorbereitung, Bau, Installation,
erster Start. Teil 2 (Schülerweg bis Exe-Export, Deinstallation) folgt
in einer eigenen Sitzung und schreibt in diese Datei.

Belege (Bildschirmfotos, Protokolle, Dateilisten) liegen unter
`build\auswertung\` und sind nicht eingecheckt. Die Verweise unten
sind relativ zu dieser Datei.

## 1. Ausgangszustand

| | |
|---|---|
| Fassung | 0.3.3, lokaler Commit (nicht gepusht), Bau ohne Veröffentlichung |
| Datum | 25.09.2026 |
| Rechner | LAPTOPJONATHAN, zugleich der Baurechner |
| Windows | Windows 11 Pro 25H2, Build 26200.9457 |
| Smart App Control | aus (`VerifiedAndReputablePolicyState` = 0), auf diesem Rechner nicht mehr einschaltbar |
| Adminrechte | Konto `jonat` ist in der Gruppe Administratoren; alle Schritte laufen ohne Erhöhung (UAC fragt nach, `ConsentPromptBehaviorAdmin` = 5). Ein echtes Standardkonto stand nicht zur Verfügung |
| Fremde Python im PATH | nur die Platzhalter des Microsoft Store: `%LOCALAPPDATA%\Microsoft\WindowsApps\python.exe`, `python3.exe`, `pythonw.exe` |
| PYTHON*-Variablen | Benutzer und System: keine. Im Prozess der Testsitzung `PYTHONIOENCODING=utf-8:surrogateescape` |
| Natter-Zertifikat | bereits eingetragen in `LocalMachine\Root`, `LocalMachine\TrustedPublisher`, `CurrentUser\TrustedPublisher`, mit privatem Schlüssel in `CurrentUser\My` (Baurechner) |
| Vorhandene Installation | Natter 0.3.0, nur für dieses Konto, `%LOCALAPPDATA%\Programs\Natter`, 30 168 Dateien, 1 202 MB, installiert am 21.09.2026 |
| Virenscanner | Microsoft Defender, Echtzeitschutz an |

Abweichungen von einem frischen Schulrechner: das Zertifikat ist
schon eingetragen, das Konto ist Administrator (nur nicht erhöht), und
die App-Steuerung ist aus. Ergebnisse zu SmartScreen, zur
Zertifikatsabfrage und zur App-Steuerung gelten deshalb nicht für
einen frischen Rechner; sie stehen unter „Nur von Hand prüfbar".

### Sicherung und Rückweg

Gesichert nach `build\auswertung\sicherung\`:

| Was | Wohin |
|---|---|
| `%APPDATA%\Natter` (1 Datei, `Natter-IDE.ini`) | `sicherung\APPDATA_Natter\` |
| `C:\Users\jonat\OneDrive\Dokumente\Natter` (13 Dateien) | `sicherung\Dokumente_Natter.zip` (als ZIP, siehe Schritt 3) |
| Deinstallationseintrag `HKCU\…\Uninstall\{961DA420-CA63-4436-9023-9CA411B620DA}_is1` | `sicherung\uninstall_eintrag_0.3.0.reg` |
| `HKCU\Software\Classes\.natter`, `…\NatterProjekt` | `sicherung\natter_endung.reg`, `sicherung\natter_projekt.reg` |
| Dateiliste der Installation 0.3.0 | `dateiliste_0.3.0_vorher.txt` |

Rückweg: Natter über „Apps & Features" entfernen,
`sicherung\APPDATA_Natter\` nach `%APPDATA%\Natter` zurückkopieren und
`sicherung\Dokumente_Natter.zip` nach `Dokumente\Natter` entpacken. Die
`.reg`-Dateien sind nur Beleg; nach einer Neuinstallation legt das
Setup die Einträge selbst an. Als GitHub-Release gibt es nur `v0.3.2`
(nachgesehen mit `gh release list`); zurückgegangen wird deshalb auf
0.3.2 oder eine neuere Fassung, nicht auf 0.3.0.

## 2. Schritte

Belege liegen unter `build\auswertung\`, von hier aus erreichbar als
`../../build/auswertung/…`. „Gegenprobe" heißt: an einem Stand
nachgesehen, an dem die Prüfung anschlagen muss.

Die Reihenfolge weicht an einer Stelle vom Auftrag ab: der erste
Start (9 bis 13) wurde an der frischen Installation aus Schritt 6
geprüft und das Update (8) danach, weil Schritt 8 die frische
Installation wieder entfernt.

| Nr | Schritt | Erwartet | Beobachtet | Ergebnis | Beleg | Punkt | geprüft per |
|---|---|---|---|---|---|---|---|
| 1 | Sicherung | Einstellungen, Projekte, Registry gesichert | 1 + 13 Dateien, 3 `.reg`; vorhanden war 0.3.0 (AppId `{961DA420-…}_is1`, HKCU) | OK | [sicherung](../../build/auswertung/sicherung/) | – | Skript |
| 2 | Ausgangszustand | erfasst | siehe Abschnitt 1; Konto ist Administrator (nicht erhöht), Zertifikat schon eingetragen | Auffällig | Abschnitt 1 | – | Skript |
| 3 | Bau `--nicht-veroeffentlichen` | 12 Schritte grün | 1. Versuch: Abbruch in Schritt 3, weil `ruff check .` die Sicherungskopie der Schülerprojekte unter `build\auswertung\` mitprüfte. 2. Versuch nach Packen der Sicherung als ZIP: grün, 41,7 min, nichts veröffentlicht | Auffällig | [bau_konsole_versuch1.log](../../build/auswertung/bau_konsole_versuch1.log), [bau_konsole.log](../../build/auswertung/bau_konsole.log) | 32 | Skript |
| 3a | Neue Lizenzprüfungen im Bau | GPL-Module entfernt, Lizenzen für jedes Paket, `LICENSE` | „35 Qt-Einträge unter GPL entfernt", 51 Einträge in `Lizenzen\` (0.3.2: 28), `LICENSE` in `dist\Natter`, Rauchprobe bestanden. Gegenprobe: dieselbe Rauchprobe an 0.3.2 meldet QtCharts und die übrigen drei Module sowie die fehlende `LICENSE` | OK | `dist\auslieferung.log` | – | Skript |
| 4 | 0.3.0 still deinstallieren | alles weg | Startmenü, `.natter`-Zuordnung, Registry weg; Programmordner bleibt mit `.ruff_cache` (5 Dateien). Das ist der alte Stand von Punkt 21, der Uninstaller von 0.3.0 kennt die neue Regel nicht. Projekte und Einstellungen unberührt. Rest danach von Hand entfernt, damit Schritt 6 einem frischen Rechner entspricht | Auffällig (erwartet) | [deinstallieren_030.json](../../build/auswertung/ergebnisse/deinstallieren_030.json) | 21 | Skript |
| 5 | ZIP wie eine Lehrkraft | Inhalt wie beschrieben | 11 Dateien + `Lizenzen\` (51), wie in `ZUERST-LESEN.txt` und Bericht 7.7. Setup-Datei gleich der aus `dist\installer` (SHA-256), `Valid`, Zeitstempel DigiCert. `.cer` ohne privaten Schlüssel, Fingerabdruck wie im Text. Version 0.3.3 eingesetzt | OK | [zip](../../build/auswertung/zip/) | – | Skript |
| 5a | `Natter-pruefen.cmd` ohne Installation | verständliche Meldung | „Die Installation ist unvollstaendig - python\python.exe fehlt. Natter neu installieren." obwohl gar keine Installation da ist. Sucht nur unter `%LOCALAPPDATA%\Programs\Natter` | Auffällig | [Bericht](../../build/auswertung/Natter-Pruefbericht_ohne_installation.txt) | 31 | Skript |
| 5b | `Zertifikat-eintragen` lesen und bewerten | Vergleich des Fingerabdrucks vor dem Eintragen möglich | Das Skript zeigt den Fingerabdruck und trägt im selben Zug ein, ohne anzuhalten. `ZUERST-LESEN.txt` verlangt den Vergleich vorher. Sonst sorgfältig: prüft den Speicher nach dem Eintragen, meldet eine abgelehnte Rückfrage | Auffällig | `zip\Zertifikat-eintragen.ps1` | 29 | von Hand (gelesen) |
| 5c | Texte in `ZUERST-LESEN.txt` | stimmen | „Natter-Setup.exe (275 MB)" steht fest im Text (tatsächlich 276,4 MB); „die Datei kommt von einem Stick", obwohl sie über GitHub verteilt wird | Auffällig | `zip\ZUERST-LESEN.txt` | 33 | von Hand |
| 6 | Installation wie ein Schüler | Ordner, ~30 000 Dateien, 1,2 GB, Verknüpfungen, kein `.ruff_cache` | 148,9 s, 30 075 Dateien, 1 193 MB; `Natter.exe`, `python\`, `Lizenzen\`, `LICENSE`, `manifest.json`; Startmenü, Desktop, `.natter` → `Natter.exe "%1"`; kein `.ruff_cache` | OK | [bestand_nach_installation_033_frisch.json](../../build/auswertung/ergebnisse/bestand_nach_installation_033_frisch.json) | – | Skript |
| 6a | Mitgelieferte Python | QtCharts scheitert, Versionen wie `uv.lock` | `No module named 'PySide6.QtCharts'`; pandas, numpy, jedi, debugpy, PyInstaller, PySide6, ruff, matplotlib, scipy, scikit-learn ohne Abweichung. Gegenprobe: im Entwicklungsbaum ist QtCharts importierbar. Python selbst: ausgeliefert 3.13.15, getestet 3.13.14 | OK | [python_033_frisch.json](../../build/auswertung/ergebnisse/python_033_frisch.json) | 33 | Skript |
| 7 | Signaturen | alle gültig | 808 von 808 `Valid`: 413 Qt, 379 Natter Codesignatur, 16 Microsoft. Gegenprobe: unsignierte `.pyd` → `NotSigned`, Natter.exe mit einem geänderten Byte → `HashMismatch` | OK | [signaturen_033_frisch.json](../../build/auswertung/ergebnisse/signaturen_033_frisch.json) | – | Skript |
| 8 | Update 0.3.2 → 0.3.3 | alte Fassung erkannt, alte Dateien weg | Assistent zeigt alle 8 Seiten wie bei einer Erstinstallation, keine Rede von 0.3.2 (ebenso 0.3.2 über 0.3.0). Nach dem Update 148 Dateien mehr als frisch: 141 der Qt-Module unter GPL (`import PySide6.QtCharts` gelingt wieder) und `natter-0.3.2.dist-info` neben `natter-0.3.3.dist-info`; `pip list` und `importlib.metadata` melden danach natter 0.3.2. Die vollständige Manifestprüfung meldet trotzdem „in Ordnung", weil sie `site-packages` außerhalb von Natter nicht ansieht | Fehler | [setup_seiten_v033_ueber_v032.json](../../build/auswertung/ergebnisse/setup_seiten_v033_ueber_v032.json), [rest_nach_update.txt](../../build/auswertung/rest_nach_update.txt), Bilder `08_*` | 26, 28 | UIA (win32) + Skript |
| 9 | Start mit verschmutzter Umgebung | startet normal, echtes `pcl` | Hauptfenster nach 2,4 s; `pythonw.exe -m ide` und der Jedi-Hilfsprozess ohne `PYTHONPATH`, `PYTHONHOME`, `PYTHONUSERBASE`, `VIRTUAL_ENV`, mit `PYTHONNOUSERSITE=1`; die Falle im falschen `pcl` löst nicht aus. Gegenprobe ohne Starter: mit `PYTHONPATH` gewinnt das falsche `pcl`, mit falschem `PYTHONHOME` startet Python gar nicht | OK | [09_umgebung.json](../../build/auswertung/ergebnisse/09_umgebung.json), [Bild](../../build/auswertung/bilder/09_verschmutzte_umgebung.png) | – | UIA |
| 10 | Startzeit | bedienbar in wenigen Sekunden | 2,21 / 2,29 / 2,25 s bis zum Hauptfenster mit ansprechbarer Menüleiste. Das Ladebild erscheint nach 0,9 s | OK | [10_startzeit.json](../../build/auswertung/ergebnisse/10_startzeit.json) | – | UIA |
| 11 | Werkzeuge → Umgebung prüfen | „unverändert" | Statuszeile „Umgebung geprüft: alle Programmdateien unverändert." Die Prüfung dauert 2,4 s und läuft im GUI-Thread; das Fenster reagiert so lange nicht | OK / Auffällig | [11_umgebung_pruefen.json](../../build/auswertung/ergebnisse/11_umgebung_pruefen.json), [Bild](../../build/auswertung/bilder/11_umgebung_pruefen.png) | 33 | UIA |
| 11a | Kerndatei verändert (`pcl\crt.py`) | deutsche Warnung | „Natter wurde verändert": nennt die Datei, sagt, dass Projekte nicht betroffen sind und was zu tun ist, „Trotzdem starten?" Ja/Nein. Nach dem Zurücklegen wieder in Ordnung | OK | [Bild](../../build/auswertung/bilder/11_manipulation_kern.png) | – | UIA |
| 11b | `manifest.json` entfernt oder unlesbar | Warnung | Natter startet ohne jede Meldung. Mit veränderter Kerndatei und entferntem Manifest liefern Schnell- und Vollprüfung `None`; „Umgebung prüfen" meldet dann laut Code „Natter läuft nicht aus einer gebauten Installation" | Fehler | [11_manipulation_manifest_weg.json](../../build/auswertung/ergebnisse/11_manipulation_manifest_weg.json), [11_manipulation_manifest_kaputt.json](../../build/auswertung/ergebnisse/11_manipulation_manifest_kaputt.json) | 27 | UIA + Skript |
| 12 | Bildschirmfotos | Ladebild, Startbild, hell, dunkel | alle vier vorhanden; Umschalten über Ansicht → Design wirkt sofort. Das Ladebild zeigt „Version 0.3.3" und bei jedem Start „Projekt wird geöffnet …", auch ohne Projekt | OK / Auffällig | [Ladebild](../../build/auswertung/bilder/12_ladebild.png), [Startbild](../../build/auswertung/bilder/12_startbild.png), [hell](../../build/auswertung/bilder/12_hauptfenster_hell.png), [dunkel](../../build/auswertung/bilder/12_hauptfenster_dunkel.png) | 33 | UIA; Ladebild per Win32 `PrintWindow` |
| 13 | Sichtbare Texte | deutsch, Dezimalkomma, keine Anrede, kein Verweis auf andere IDEs | Natter selbst (Hauptfenster 60 Texte, Warnung, Statuszeile, Ladebild), `ZUERST-LESEN.txt`, Prüfskript, Handbuch: ohne Fund. Installer: 19 Stellen mit „Sie"/„Ihr" aus den Standardtexten von Inno Setup, dazu die Sprachauswahl; Zahlen dort mit Komma („1,17 GB") | Auffällig | [setup_seiten_v032_ueber_v030.json](../../build/auswertung/ergebnisse/setup_seiten_v032_ueber_v030.json) | 30 | UIA + Skript |

Das Ladebild ist ein Werkzeugfenster mit dem Titel „Natter" und liegt
nach einem Start aus einem Hintergrundprozess hinter dem aktiven
Fenster, weil Windows einen solchen Prozess nicht nach vorn lässt.
Nach einem Doppelklick durch einen Schüler tritt das nicht auf. Das
Foto entstand deshalb über `PrintWindow` statt als
Bildschirmausschnitt.

## 3. Messwerte

### Bau (2. Versuch, 25.09.2026, 21:49–22:31)

| Schritt | Dauer |
|---|---|
| 1–3 Arbeitsbaum, Versionen, ruff | 0:00 |
| 4 pytest (4187 Tests) | 22:19 |
| 5 `dist\Natter` | 10:29 |
| 5.1 Python bereitstellen | 0:27 |
| 5.2 Pakete installieren, Qt-GPL-Module entfernen | 5:51 |
| 5.3 Starter bauen | 0:15 |
| 5.4 Lizenzen sammeln und prüfen | 0:07 |
| 5.5 Signieren | 3:13 |
| 5.6 Prüfsummen | 0:36 |
| 6 Rauchprobe | 0:03 |
| 7 Manifest | 0:09 |
| 8 Installer | 7:56 |
| 9 Installer signieren | 0:02 |
| 10 Signaturen prüfen | 0:36 |
| 11 Paket | 0:04 |
| 12 Veröffentlichen | übersprungen |
| gesamt | 41,7 min |

Der Test-Stempel griff nicht, weil `build\` und `docs\auswertung\`
uneingecheckt im Baum lagen; pytest lief deshalb im Bau erneut, wie
schon im Lauf davor (22:51).

### Installation und Start

| Messung | Wert |
|---|---|
| Setup-Datei | 276,4 MB (289 821 792 Byte) |
| ZIP | 277 MB (290 029 719 Byte) |
| Installation frisch, still | 148,9 s; zweiter Lauf 160,7 s |
| Installation 0.3.2, still | 160,6 s |
| Update 0.3.2 → 0.3.3, still | 211,1 s |
| Deinstallation 0.3.0 / 0.3.3 frisch / 0.3.3 nach Update | 35,0 / 9,8 / 13,0 s |
| Dateien und Größe frisch | 30 075 Dateien, 1 193 MB, davon 861 `__pycache__`-Ordner |
| Dateien nach Update | 30 223 (148 Altdateien) |
| Binärdateien | 808, alle gültig signiert |
| Start bis Hauptfenster | 2,21 / 2,29 / 2,25 s |
| Ladebild sichtbar nach | 0,89 s |
| Umgebung prüfen (vollständig) | 2,4 s |

## 4. Nur von Hand prüfbar

Checkliste für Jonathan. Was hier steht, ließ sich auf diesem Rechner
nicht oder nicht aussagekräftig prüfen.

- [ ] Installer interaktiv durchklicken: Lizenz- und Hinweisseite vollständig, Umlaute, keine abgeschnittenen Zeilen (Punkt 4). Die Seiten liegen als Bild unter `bilder\08_v032_ueber_v030_seite2.png` und `…seite3.png`; geprüft wurde nur ihr Text
- [ ] SmartScreen beim Start von `Natter-Setup.exe` auf einem Rechner ohne eingetragenes Zertifikat, Datei frisch aus dem Internet
- [ ] Smart App Control eingeschaltet: Verhalten von Setup und `Natter.exe`, Eintrag im Ereignisprotokoll `CodeIntegrity/Operational`
- [ ] Echter Schulrechner mit Standardkonto (nicht Administrator) und Proxy: Installation, Start, Paketverwaltung über pip
- [ ] `Zertifikat-eintragen.cmd` ausführen, die UAC-Rückfrage einmal ablehnen und einmal annehmen
- [ ] Verteilung „für viele Rechner" wie in `ZUERST-LESEN.txt` (`/VERYSILENT`) über eine Softwareverteilung: landet Natter dann im Profil des Verteilkontos statt beim Schüler?
- [ ] Druck auf A4 (Teil 2)

## Stand für Teil 2

| | |
|---|---|
| Installiert | Natter 0.3.3 aus diesem Bau, frisch installiert (nicht die aktualisierte Installation aus Schritt 8), nur für dieses Konto unter `%LOCALAPPDATA%\Programs\Natter`, 30 075 Dateien, Desktopsymbol und `.natter`-Zuordnung gesetzt |
| Setup-Datei | `build\auswertung\zip\Natter-Setup.exe`, gleich `dist\installer\Natter-Setup.exe` |
| Sicherung | `build\auswertung\sicherung\`: Einstellungen als Ordner, Projekte als ZIP, `.reg`-Dateien |
| Einstellungen | `%APPDATA%\Natter\Natter-IDE.ini` wurde von den Starts in Teil 1 benutzt; das Design steht wie vorher auf „Hell". Kein Prüfungsmodus gesetzt |
| Projekte | `Dokumente\Natter` unverändert (13 Dateien) |
| Zertifikate | unverändert; Vergleich mit dem Stand vom Anfang (`zertifikate_vorher.txt`, 144 Einträge): 0 Unterschiede |
| Repository | Commit `9a83164` lokal, nicht gepusht. Der Bau hat die Versionsnummer in `pyproject.toml`, `tools/natter.iss`, `ide/main.py` und `uv.lock` auf 0.3.3 gesetzt; diese Änderungen sind nicht eingecheckt |
| Testgerüst | `build\auswertung\venv` (pywinauto 0.6.9, Pillow, psutil), Skripte `erster_start.py`, `installation.py`, `setup_seiten.py`, `ladebild.py` |
| Auftrag Teil 2 | `build\auswertung\auftrag_teil2.md`, mit den vorab geklärten Antworten |

## 5. Zusammenfassung

Folgt am Ende von Teil 2.
