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

---

# Teil 2: Schülerweg in der installierten Natter

26.09.2026, 00:00–01:30, derselbe Rechner, Natter 0.3.3 frisch
installiert (siehe „Stand für Teil 2“). Vorab geklärt: Prüfungsmodus
wird durch Löschen von `pruefung/ende` aus der INI beendet; der
Exe-Export darf das vorhandene Bauzertifikat benutzen, es wird kein
Zertifikat angelegt oder verändert; Endstand ist 0.3.3 aus diesem Bau.

## Wie bedient wurde

Natter wurde als echtes Fenster über UIA bedient (pywinauto 0.6.9),
belegt mit Bildschirmfotos. Vier Grenzen des Testaufbaus, die keine
Fehler von Natter sind, aber die Spalte „geprüft per“ erklären:

- **Doppelklick.** Über die Eingabewarteschlange erzeugte Doppelklicks
  (pywinauto, `SendInput`) kamen in Natter nicht als Doppelklick an,
  einfache Klicks schon. Direkt geschickte `WM_LBUTTONDBLCLK` wirken.
  Doppelklicks sind deshalb „UIA + Nachricht“. Mit echter Maus steht
  der Doppelklick auf der Liste „Nur von Hand prüfbar“.
- **Tastatur.** pywinauto schickt Zeichen standardmäßig als
  Unicode-Pakete ohne Umschalttaste; mit `vk_packet=False` bildet es
  das deutsche Layout falsch ab („=“ wird „+“). Kurzer Code wurde
  getippt (Schritt 16), längerer über die Zwischenablage eingefügt.
- **Modale Menüaktionen und Auswahllisten.** UIA-Invoke auf einen
  Menüeintrag, der einen modalen Dialog öffnet, kehrt nicht zurück;
  UIA-Select wechselt den Eintrag einer Auswahlliste nicht. Beides
  wurde mit der Maus bedient.
- **Konsolenfenster.** Konsolenprogramme öffnen sich in Windows
  Terminal. Der Text wurde über das UIA-Element `TermControl` gelesen.

## 6. Schritte Teil 2

| Nr | Schritt | Erwartet | Beobachtet | Ergebnis | Beleg | Punkt | geprüft per |
|---|---|---|---|---|---|---|---|
| 14 | A Lehrgang 01–09 | öffnen, starten, Kernfunktion | Alle neun öffnen sich als Arbeitskopie unter `Dokumente\Natter\Beispielprojekte` und laufen. 01: „Jörg“, 15 → „Freut mich, Jörg!“, „In 10 Jahren bist du 25.“; 02: „Zu groß.“ und „keine Zahl“; 03: 12+4=16, Division durch 0 abgefangen; 04: 3 Klicks → „3 Kekse“; 05: Bild über den Dateidialog → „testbild_natter.png - 43,9 kB“; 06: Konto „Björn Größe“, 12,50 eingezahlt; 07: Ort Köln → neue Kennzahlen; 08: polynomial → neue Formel, 165 cm → 38,2; 09: 120 g/190 mm/35 mm → „Banane“ | OK | [teil2_A.json](../../build/auswertung/ergebnisse/teil2_A.json), Bilder `A_*` | – | UIA; Menü und Auswahllisten mit der Maus |
| 14a | A Auf Original zurücksetzen | Rückfrage, Original | „„03_Taschenrechner“ auf den Auslieferungszustand zurücksetzen? Alle Änderungen an diesem Beispiel gehen dabei verloren.“ Ja → Datei gleich dem Original | OK | [Bild](../../build/auswertung/bilder/A_zuruecksetzen_rueckfrage.png) | – | UIA |
| 14b | A Beispielkommentare | keine Anrede | `01_Begruessung/u_main.py`: „# Drücke F5, um das Programm zu starten.“ | Auffällig | – | 45 | Skript |
| 15 | B Projekt, Palette, Objektinspektor | platzieren, verschieben, Eigenschaft, Rückgängig | „Projekt → Neues Projekt …“ (ein „Datei → Neu“ gibt es nicht). Label, Edit, Button platziert, Button um 120/40 px verschoben, Beschriftung „Verdoppeln“ im Objektinspektor; zweimal Rückgängig stellt Ausgangslage her, zweimal Wiederholen wieder her | OK | [teil2_B2.json](../../build/auswertung/ergebnisse/teil2_B2.json) | – | UIA + Maus |
| 15a | B Design-Prüfung | keine Fehlalarme | Direkt nach dem Platzieren „9 Funde“, darunter „label liegt teilweise außerhalb des Formulars“, obwohl alles bei 32/32 bis 224/192 in 480 × 360 liegt: `_geometrie_pruefen` liest die Formulargröße mit 0 als Ersatz, ein neues Projekt speichert keine Größe | Fehler | [Bild](../../build/auswertung/bilder/B_1_platziert.png) | 36 | UIA + Code |
| 15b | B Komponentenbaum | zeigt neue Komponenten | nach dem Platzieren nur „Form1: Form“; erst nach Neuöffnen alle (auch in Schritt G) | Auffällig | [Bild](../../build/auswertung/bilder/B_1_platziert.png) | 45 | UIA |
| 15c | B Menü-Editor | über drei Wege | Doppelklick auf das Symbol und Doppelklick auf `entries` öffnen „Menü bearbeiten“; „Datei → Beenden“ angelegt, `entries` „(1 Eintrag)“. F2 nach dem Anklicken des Symbols öffnet nichts (Tastaturfokus bleibt außerhalb der Zeichenfläche) | OK / Auffällig | [Bild](../../build/auswertung/bilder/B_3_menue_editor.png) | 45 | UIA + Nachricht |
| 15d | B Doppelklick auf Button | Methode anlegen und hinspringen | Methode `button_click` wird angelegt und verknüpft, die Unit öffnet sich aber nicht und der Cursor springt nicht hin – Handbuch und Tastenübersicht versprechen „anlegen und hinspringen“ | Fehler | [Bild](../../build/auswertung/bilder/B_3_editor.png) | 37 | Nachricht + Code |
| 16 | B Code, starten, bedienen | Zahl mit Komma → Ergebnis | Zwei Zeilen im Editor getippt, gespeichert. Programm: „2,5“ → „5,00“, nach Neuöffnen „3,25“ → „6,50“, ohne Natter mit `python.exe main.py` ebenso (Fenster nach 1,6 s) | OK | [Bild](../../build/auswertung/bilder/B_4_programm.png) | – | UIA, Code getippt |
| 16a | B Menü im Programm | „Datei“ in der Menüleiste | Menüleiste leer, „Datei“ nur über den Knopf „···“ oben rechts erreichbar; der Button-Text „Verdoppeln“ ist abgeschnitten („erdoppel“), ohne Hinweis der Design-Prüfung | Fehler / Auffällig | [Bild](../../build/auswertung/bilder/B_5_punkte_geklickt.png) | 39, 45 | UIA + Maus |
| 17 | C Konsolenprojekt | eigenes Fenster, Eingabe, Umlaute | Fenster „Natter – Gruss“; „Jürgen Weiß“ → „Grüße, Jürgen Weiß! Äpfel, Öl, Übung, Maß: 3,5 €“ | OK | [Bild](../../build/auswertung/bilder/C_konsole.png) | – | UIA (TermControl) |
| 17a | C Klammern automatisch schließen | wie beschrieben | Nur ohne Zusatztaste aktiv (`not event.modifiers()`); mit Umschalttaste (deutsche Tastatur: `(`, `"`) bleibt `print("` offen | Auffällig | [teil2_C_klammern.json](../../build/auswertung/ergebnisse/teil2_C_klammern.json) | 43 | Tasten + Code |
| 18 | D Name falsch / Doppelpunkt / Einrückung | nicht starten, Zeile, Wo/Was/Prüfe | alle drei nicht gestartet, richtige Zeile, deutsch, kein Code. Beim Einrückungsfehler fragt der Hinweis nach Doppelpunkt, Klammer oder Anführungszeichen, nicht nach der Einrückung | OK / Auffällig | [teil2_D.json](../../build/auswertung/ergebnisse/teil2_D.json) | 45 | UIA |
| 18a | D `int("3,5")`, Division durch 0 | Wo/Was/Prüfe im Programmfenster | „Laufzeitfehler: Ungültiger Wert (ValueError) / Wo: u_main.py, Zeile 2 / Was: Der Text „3,5“ lässt sich nicht als ganze Zahl lesen. / Prüfe: …“; ebenso Division durch 0 | OK | [Bild](../../build/auswertung/bilder/D_int_komma_konsole.png) | – | UIA (TermControl) |
| 18b | D Endlosschleife | anhalten | „Start → Stopp“ beendet sie nach 1,5 s | OK | [teil2_D.json](../../build/auswertung/ergebnisse/teil2_D.json) | – | UIA |
| 18c | D Komponente fehlt | Wo/Was/Prüfe | Fehlerfenster deutsch mit Zeile 6; im Panel danach „Programm beendet (Code 0)“ | OK / Auffällig | [Bild](../../build/auswertung/bilder/D_komponente_fehlt_0.png) | 41 | UIA |
| 18d | D `input()` im GUI-Programm | deutsche Erklärung | „Zu diesem Fehler gibt es noch keine deutsche Erklärung“, darunter englischer Traceback `EOFError: EOF when reading a line`; im Panel „Programm beendet (Code 0)“ | Fehler | [Bild](../../build/auswertung/bilder/D_input_gui_0.png) | 41 | UIA |
| 19 | E Vervollständigung | Liste, Typen, Erklärung | „pri“ → `print(*values: object, …) -> None – gibt Werte aus`; „konto_ab“ → `konto_abheben(konto: int, betrag: float) -> float – Hebt einen Betrag ab …`; Eingabe fügt `konto_abheben()` ein | OK | [Bild](../../build/auswertung/bilder/E_konto_ab.png) | – | UIA |
| 19a | E Parameterhilfe | nach `(` und nach Übernahme | erscheint nach `print` + Umschalt+8 und nach `input(`, mit Typen; nach Übernahme aus der Liste ist sie nicht zu sehen | OK / Auffällig | [Bild](../../build/auswertung/bilder/E_parameterhilfe.png) | 43 | UIA + Tasten |
| 19b | E Tastenkürzel, hell/dunkel, Minimap | vorhanden | Tastenkürzel als Reiter; hell/dunkel siehe Schritt 12; eine Minimap gibt es nur im Diagramm-Editor (Schritt 23), nicht im Quelltexteditor | OK | [Bild](../../build/auswertung/bilder/E_editor_minimap.png) | – | UIA |
| 20 | F Debugger | Haltepunkt, Einzelschritt, Variablen | Klick in den Rand setzt Haltepunkt; F5 „Angehalten: an einem Haltepunkt“, F11 „nach einem Einzelschritt“, `i` wechselt 1 → 2; Stopp beendet. Erste Zeile der Tabelle „special variables“ (englisch); das Panel zeigt in der Grundaufteilung nur eine Zeile | OK / Auffällig | [Bild](../../build/auswertung/bilder/F_angehalten.png) | 45 | UIA + Maus |
| 20a | F Test-Explorer | grün und rot | „Datei → Neue Test-Unit“ legt `test_neu1.py` ohne Namensfrage an; „2 Tests gelaufen, 1 nicht bestanden“ | OK | [Bild](../../build/auswertung/bilder/F_tests.png) | – | UIA |
| 21 | G Datenbank | Vorlage gui_db, Tabelle, Grid, ändern, neu laden | Eine Vorlage gui_db gibt es nicht (`templates/` hat nur `gui` und `console`; `bericht.md` nennt sie trotzdem). Mit GUI-Projekt, StringGrid und `SQLite3Connection`: 2 Namen gespeichert, einer geändert, nach Neustart beide geladen | OK / Auffällig | [Bild](../../build/auswertung/bilder/G_neustart.png) | 45 | UIA; Code per Zwischenablage |
| 21a | G Ereignisse verknüpfen | vorhandene Methode wählbar | Die Auswahlliste im Reiter „Ereignisse“ zeigt nur „(kein)“, obwohl `button_click` im Code steht; Doppelklick auf die Komponente verknüpft die gleichnamige Methode | Fehler | [Bild](../../build/auswertung/bilder/G_ereignisse.png) | 38 | UIA + Code |
| 21b | G Datenbank-Panel | Tabelle sichtbar | schwebendes Fenster, links abgeschnitten, „Nicht verbunden“ | Auffällig | [Bild](../../build/auswertung/bilder/G_db_panel.png) | 45 | UIA |
| 22 | H CSV, pandas, Chart, Bild, HTML | alles sichtbar | Grid, Balkendiagramm „Hamburg“, Bild, „Mittelwert Hamburg: 9,7 °C“; `bericht.html` in Natter als Reiter mit „Im Browser öffnen“. Im Grid aus `load_dataframe` stehen die Temperaturen mit Punkt: „2.4“, „2.8“ | OK / Fehler | [Bild](../../build/auswertung/bilder/H_programm.png) | 42 | UIA |
| 23 | I Paketverwaltung | installieren, importieren | `cowsay` in 18 s installiert, Oberfläche dabei bedienbar (Antwort ≤ 0,09 s), Import funktioniert | OK | [teil2_I.json](../../build/auswertung/ergebnisse/teil2_I.json) | – | UIA |
| 23a | I Umgebung prüfen danach | keine Warnung | „Natter wurde nach der Erstellung verändert: python/Scripts/cowsay.exe (zusätzlich) … Natter neu installieren“ | Fehler | [Bild](../../build/auswertung/bilder/I_umgebung.png) | 40 | UIA |
| 24 | J Klassendiagramm | zeichnen, speichern, öffnen, exportieren | zwei Klassen mit Namen und Attribut über F2 → „Eigenschaften: UML – Klasse“, Vererbung per zwei Klicks, gespeichert, wieder geöffnet; PNG (Auflösung wählbar) und PDF exportiert; Minimap und Lineale | OK | [Export](../../build/auswertung/bilder/J_export_Bank.png), [Minimap](../../build/auswertung/bilder/J_minimap.png) | – | UIA + Maus |
| 24a | J Quelltext aus Klassendiagramm | Vererbung im Code | `class Sparkonto:` statt `class Sparkonto(Konto):`. Ein Attribut mit „stand: float“ im Namensfeld ergibt `self.__stand: float = stand: float` (Syntaxfehler), das danach jeden Start des Projekts blockiert | Fehler | [teil2_J3.json](../../build/auswertung/ergebnisse/teil2_J3.json) | 35 | UIA |
| 24b | J Struktogramm | Blöcke, Export, Quelltext | Block über Palette + Klick auf den Kopf eingefügt, PDF 12 KB, Quelltext `def Ablauf(): …` | OK | [Bild](../../build/auswertung/bilder/J_struktogramm_bloecke.png) | – | UIA + Maus |
| 25 | K `.lfm`-Import | im Designer | `f_Pizza`: „31 Hinweise im Importbericht“, Formular im Designer, `pizza.pfm/.py/_design.py` angelegt. Im Konsolenprojekt erscheint das Formular nicht im Projekt-Explorer | OK / Auffällig | [Bild](../../build/auswertung/bilder/K_import.png) | 45 | UIA + Dateidialog |
| 26 | L Prüfungsmodus | Einschränkungen, Neustart | Rückfrage nennt 4 h und „lässt sich bis dahin nicht abschalten“; Fußzeile „Prüfungsmodus – noch 3:59 h“; keine Vorschlagsliste, keine Parameterhilfe, Meldungen ohne „Prüfe“, „Quelltext → Erzeugen …“ gesperrt; übersteht Neustart. Beendet über die INI wie vereinbart; in der Oberfläche gibt es keinen Weg | OK / Auffällig | [Bild](../../build/auswertung/bilder/L_an_editor.png) | 45 | UIA; Ende per INI |
| 27 | M Quelltext als PDF | A4 | eine Seite 595 × 842 pt, 16 KB | OK | `build\auswertung\M_Umrechner_Quelltext.pdf` | – | UIA + Dateidialog |
| 27a | M Exe-Export | Dauer, Größe, Signatur | GUI 55 s / 54,9 MB, Konsole 9,7 s / 8,0 MB; beide „Nicht signiert: UnknownError“, kein Zertifikat angelegt. Ursache: der Bau hat die Bootloader-Vorlagen von PyInstaller in der Installation signiert; eine daraus gebaute Exe lässt sich nicht mehr signieren („%1 ist keine zulässige Win32-Anwendung“) | Fehler | [teil2_M.json](../../build/auswertung/ergebnisse/teil2_M.json) | 34 | UIA + Skript |
| 27b | M Exe im fremden Ordner | läuft ohne Natter | `%TEMP%\fremd`, ohne Python im PATH: GUI in 3,8 s ohne Konsole, „1,5“ → „3,00“; Konsole in 1,4 s, „Zoë Brück“ → Umlaute und € richtig | OK | [GUI](../../build/auswertung/bilder/M_fremd_gui.png), [Konsole](../../build/auswertung/bilder/M_fremd_konsole.png) | – | UIA |
| 28 | N Deinstallation | alles weg | 12,9 s; Programmordner vollständig weg, auch `python\` mit `cowsay`; kein `.ruff_cache` entstanden (Punkt 21 erledigt); Startmenü, Desktop, `.natter`, Uninstall-Eintrag weg. Es bleiben `%APPDATA%\Natter\Natter-IDE.ini` und `Dokumente\Natter` (gewollt: Nutzerdaten) sowie `HKCU\Software\Natter\Diagramm` (Minimap/Lineale) und ein leerer Schlüssel `…\Natter-IDE` | OK / Auffällig | [deinstallieren_033_teil2.json](../../build/auswertung/ergebnisse/deinstallieren_033_teil2.json) | 21, 45 | Skript |
| 28a | N Exe nach Deinstallation | eigenständig | beide wie in 27b | OK | [teil2_N_exe.json](../../build/auswertung/ergebnisse/teil2_N_exe.json) | – | UIA |
| 29 | O Aufräumen | Ausgangszustand | Testprojekte nach `build\auswertung\teil2_projekte\` verschoben (nicht gelöscht), Sicherung zurückgespielt (13 Dateien, INI byte-gleich), 0.3.3 still installiert, das dabei neu angelegte Desktopsymbol entfernt. Zertifikate: 0 Unterschiede zum Anfang, nichts zu entfernen | OK | – | – | Skript |

Eingriffe per Skript statt über die Oberfläche: in Schritt 21 die
SQL-Platzhalter meines Testcodes (`:name` statt `?`), in Schritt 27
das Zurücksetzen von `u_main.py` in beiden Projekten nach den
Fehlerfällen aus Schritt 18.

## 7. Messwerte Teil 2

| Messung | Wert |
|---|---|
| Start eines Lehrgangsbeispiels bis Programmfenster | 10–16 s je Beispiel einschließlich Öffnen |
| Paketinstallation `cowsay` | 18 s, Oberfläche reagiert in ≤ 0,09 s |
| Exe-Export GUI / Konsole | 55 s / 9,7 s |
| Exe-Größe GUI / Konsole | 54,9 MB / 8,0 MB |
| Start der Exe im fremden Ordner GUI / Konsole | 3,8 s / 1,4 s bis zur ersten Ausgabe |
| Endlosschleife stoppen | 1,5 s |
| Quelltext als PDF | 1 Seite A4, 16 KB |
| Diagramm-Export PNG / PDF | 3,7 KB / 12 KB |
| Deinstallation nach Benutzung | 12,9 s, 0 Reste im Programmordner |
| Neuinstallation Endstand | 149,4 s, 30 075 Dateien |

## 4. Nur von Hand prüfbar

Checkliste für Jonathan. Was hier steht, ließ sich auf diesem Rechner
nicht oder nicht aussagekräftig prüfen.

- [ ] Installer interaktiv durchklicken: Lizenz- und Hinweisseite vollständig, Umlaute, keine abgeschnittenen Zeilen (Punkt 4). Die Seiten liegen als Bild unter `bilder\08_v032_ueber_v030_seite2.png` und `…seite3.png`; geprüft wurde nur ihr Text
- [ ] SmartScreen beim Start von `Natter-Setup.exe` auf einem Rechner ohne eingetragenes Zertifikat, Datei frisch aus dem Internet
- [ ] Smart App Control eingeschaltet: Verhalten von Setup, `Natter.exe` und einer exportierten Schüler-Exe; Eintrag im Ereignisprotokoll `CodeIntegrity/Operational`
- [ ] Druck auf A4: Quelltext, Klassendiagramm, Struktogramm auf einem echten Drucker (geprüft wurde nur das Seitenformat der PDFs)
- [ ] Echter Schulrechner mit Standardkonto (nicht Administrator) und Proxy: Installation, Start, Paketverwaltung über pip
- [ ] `Zertifikat-eintragen.cmd` ausführen, die UAC-Rückfrage einmal ablehnen und einmal annehmen
- [ ] Verteilung „für viele Rechner" wie in `ZUERST-LESEN.txt` (`/VERYSILENT`) über eine Softwareverteilung: landet Natter dann im Profil des Verteilkontos statt beim Schüler?
- [ ] Doppelklick mit echter Maus: Projekt-Explorer, Palettenkachel, Komponente im Designer, Klasse im Diagramm (Testaufbau siehe „Wie bedient wurde“)
- [ ] Exe-Export auf einem Rechner ohne Bauzertifikat: legt Natter „Natter Programme dieses Rechners“ an, fragt Windows nach dem Stammzertifikat, und scheitert die Signatur dort genauso (Punkt 34)?
- [ ] Tippen mit deutscher Tastatur: Klammern und Anführungszeichen im Editor, Parameterhilfe nach `(`

## 5. Zusammenfassung

**Ergebnis gesamt.** Der Weg eines Schülers funktioniert von der
Installation bis zur eigenständigen Exe: alle neun Lehrgangsprojekte,
ein eigenes GUI- und Konsolenprojekt, Fehlermeldungen, Debugger,
Tests, Datenbank, pandas, Diagramme, Import, Prüfungsmodus, Export und
Deinstallation laufen, und die Meldungen für Schüler sind deutsch, mit
Ort und Zeile, ohne Lösungscode und ohne Anrede. Die Befunde liegen
dort, wo Natter etwas zusagt, das es nicht hält – Signatur beim
Export, Vererbung im erzeugten Code, Sprung zur Methode, Update und
Integritätsprüfung – und bei Fehlalarmen, die Schüler in die Irre
schicken.

**Die fünf wichtigsten Befunde, nach Schwere:**

1. **Exe-Export ohne Signatur (Punkt 34).** Der Bau signiert die
   Bootloader-Vorlagen von PyInstaller; jede Schüler-Exe ist dadurch
   unsignierbar, die Statuszeile sagt nur „UnknownError“.
2. **Integritätsprüfung lässt sich still abschalten (Punkt 27)** und
   **meldet nach Natters eigener Paketinstallation eine Veränderung
   (Punkt 40)** – einmal schweigt sie, wo sie warnen sollte, einmal
   warnt sie mit dem Rat zur Neuinstallation, wo alles in Ordnung ist.
3. **Update lässt Altdateien liegen (Punkt 28)**, darunter die
   Qt-Module unter GPL; danach meldet pip natter 0.3.2.
4. **Quelltext aus dem Klassendiagramm (Punkt 35):** Vererbung fehlt,
   ungültige Namen ergeben Code, der jeden Start blockiert.
5. **Design-Prüfung mit Fehlalarm in jedem neuen Projekt (Punkt 36)**,
   zusammen mit dem fehlenden Sprung zur Methode (Punkt 37) und der
   nicht wählbaren eigenen Methode im Reiter „Ereignisse“ (Punkt 38)
   die Stellen, an denen ein Schüler im ersten eigenen Projekt hängen
   bleibt.

**Neu angelegte Punkte in `offene_punkte.md`:**

| Nr | Titel |
|---|---|
| 27 | Die Integritätsprüfung entfällt still, wenn `manifest.json` fehlt oder unlesbar ist |
| 28 | Ein Update lässt Dateien der alten Fassung in `site-packages` liegen |
| 29 | `Zertifikat-eintragen` lässt den verlangten Vergleich des Fingerabdrucks nicht zu |
| 30 | Der Installer spricht mit „Sie" an |
| 31 | `Natter-pruefen` meldet eine fehlende Installation als „unvollständig" |
| 32 | Der Auslieferungsbau prüft mit ruff auch nicht eingecheckte Ordner |
| 33 | Kleinere Befunde aus dem Schülerweg 0.3.3, Teil 1 |
| 34 | Exportierte Exe lassen sich nicht signieren, weil der Bau die PyInstaller-Vorlagen signiert |
| 35 | Der Quelltext aus dem Klassendiagramm übernimmt keine Vererbung und prüft keine Namen |
| 36 | Die Design-Prüfung meldet in neuen Projekten jede Komponente als außerhalb des Formulars |
| 37 | Doppelklick auf eine Komponente springt nicht zur Methode |
| 38 | Der Reiter „Ereignisse" bietet selbst geschriebene Methoden nicht an |
| 39 | Das Hauptmenü eines Schülerprogramms ist nur über „···" erreichbar |
| 40 | „Umgebung prüfen" meldet nach einer Paketinstallation über Natter eine Veränderung |
| 41 | `input()` im GUI-Programm endet mit englischem Traceback |
| 42 | `StringGrid.load_dataframe` zeigt Zahlen mit Dezimalpunkt |
| 43 | Klammern schließen und Parameterhilfe hängen an der Tastatur |
| 44 | Palettenkacheln und Menüsymbol sind für UIA namenlos |
| 45 | Kleinere Befunde aus dem Schülerweg 0.3.3, Teil 2 |

Punkt 21 (Rest nach dem Deinstallieren) ist mit Schritt 28
nachgewiesen und kann nach `erledigte_punkte.md`; Punkt 26 ist mit
Schritt 8 belegt.
