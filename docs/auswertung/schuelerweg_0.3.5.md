# Schülerweg 0.3.5 – Auswertung

Der Weg eines Schülers auf einem Schulrechner, geprüft an der
veröffentlichten Fassung 0.3.5 (Release `v0.3.5`), nicht am
Entwicklungsbaum. Teil 1: Vorbereitung, Release, Installation, Update,
erster Start. Teil 2: Schülerweg bis Exe-Export, Deinstallation,
Aufräumen. Beide Teile liefen am 27.09.2026 in einer Sitzung.

Belege (Bildschirmfotos, Protokolle, Dateilisten) liegen unter
`build\auswertung\035\` und sind nicht eingecheckt; die Verweise unten
sind relativ zu dieser Datei. Die Belege von 0.3.3 unter
`build\auswertung\` bleiben unberührt.

## 1. Ausgangszustand

| | |
|---|---|
| Fassung | 0.3.5, Release `v0.3.5` (Tag auf `39fdfdf`), nicht neu gebaut |
| Datum | 27.09.2026 |
| Rechner | LAPTOPJONATHAN, zugleich der Baurechner |
| Windows | Windows 11 Pro 25H2, Build 26200.9457 |
| Smart App Control | aus (`VerifiedAndReputablePolicyState` = 0) |
| Adminrechte | Konto `jonat` in der Gruppe Administratoren, Prozess nicht erhöht, `ConsentPromptBehaviorAdmin` = 5; ein Standardkonto stand nicht zur Verfügung |
| Fremde Python im PATH | nur die Platzhalter des Microsoft Store (`WindowsApps\python.exe`, `python3.exe`, `pythonw.exe`) |
| PYTHON*-Variablen | Benutzer und System: keine; im Prozess der Testsitzung `PYTHONIOENCODING=utf-8:surrogateescape` |
| Natter-Zertifikat | eingetragen (Baurechner), Vorher-Stand aller sechs Speicher in `zertifikate_vorher.txt` (144 Einträge) |
| Vorhandene Installation | Natter 0.3.5 vom 26.09. (mit dem für den Update-Test nachinstallierten `cowsay`), 30 100 Dateien, 1 211 MB |
| Registry-Reste | `HKCU\Software\Natter` mit `Diagramm\ansicht` und leerem `Natter-IDE` (aus älteren Fassungen) |
| Virenscanner | Microsoft Defender, Echtzeitschutz an |

Beleg: [02_ausgangszustand.json](../../build/auswertung/035/ergebnisse/02_ausgangszustand.json).

Abweichungen von einem frischen Schulrechner wie bei 0.3.3: Zertifikat
eingetragen, Konto Administrator (nicht erhöht), App-Steuerung aus.

### Sicherung und Rückweg

Gesichert nach `build\auswertung\035\sicherung\`: `%APPDATA%\Natter`
(1 Datei), `Dokumente\Natter` als ZIP (20 Dateien), die Registry-Einträge
(Deinstallation 0.3.5, `.natter`, `NatterProjekt`, `HKCU\Software\Natter`)
als `.reg`, dazu `hashes_vorher.txt` (SHA-256 aller 21 Nutzerdateien).
Rückweg: 0.3.5 frisch installieren, ZIP nach `Dokumente\Natter`, INI nach
`%APPDATA%\Natter`.

## 2. Schritte Teil 1

„Gegenprobe“: an einem Stand nachgesehen, an dem die Prüfung
anschlagen muss; jede liegt als eigene Datei vor. Reihenfolge wie bei
0.3.3: erster Start (9–13) an der frischen Installation, Update (8)
danach.

| Nr | Schritt | Erwartet | Beobachtet | Ergebnis | Beleg | Punkt | geprüft per |
|---|---|---|---|---|---|---|---|
| 1 | Sicherung | Einstellungen, Projekte, Registry gesichert | 1 + 20 Dateien, 4 `.reg`, Hashes aller 21 Dateien | OK | [sicherung](../../build/auswertung/035/sicherung/) | – | Skript |
| 2 | Ausgangszustand | erfasst | siehe Abschnitt 1; Konto Administrator (nicht erhöht), Zertifikat eingetragen – Grenzen des Testrechners, kein Fehler von Natter | OK | [02_ausgangszustand.json](../../build/auswertung/035/ergebnisse/02_ausgangszustand.json) | – | Skript |
| 3 | Fassung bereitstellen | Release = geprüfter Bau | `gh release download v0.3.5`: Setup (289 910 912 Byte) und ZIP (290 119 819 Byte) SHA-256-gleich mit `dist` vom 26.09.; Bau: 4250 Tests, Rauchprobe bestanden, „35 Qt-Einträge unter GPL entfernt“, 48,9 min, beide Signaturen `Valid` | OK | [03_release_vergleich.json](../../build/auswertung/035/ergebnisse/03_release_vergleich.json), [auslieferung_035.log](../../build/auswertung/035/auslieferung_035.log) | – | Skript |
| 4 | Vorhandene 0.3.5 still deinstallieren | alles weg | 42,8 s; Programmordner samt `python\` und `cowsay` weg, Startmenü, Desktop, `.natter`, Uninstall-Eintrag weg, dazu `HKCU\Software\Natter` (Reste älterer Fassungen, neu seit 0.3.4) | OK | [deinstallieren_035.json](../../build/auswertung/035/ergebnisse/deinstallieren_035.json), [bestand_vor_deinstallation_035.json](../../build/auswertung/035/ergebnisse/bestand_vor_deinstallation_035.json) | 21, 45 | Skript |
| 5 | ZIP wie eine Lehrkraft | Inhalt wie beschrieben | 12 Einträge wie in `ZUERST-LESEN.txt` und Bericht 7.7, `Lizenzen\` 51 Einträge (79 Dateien); Setup gleich Release, `Valid`, DigiCert-Zeitstempel; `.cer` ohne privaten Schlüssel, Fingerabdruck wie im Text; Version 0.3.5 eingesetzt, kein „Stick“, keine Anrede | OK | [05_zip.json](../../build/auswertung/035/ergebnisse/05_zip.json) | 33 | Skript |
| 5a | `Natter-pruefen.cmd` ohne Installation | verständliche Meldung | „Natter ist fuer dieses Konto nicht installiert. Zum Installieren Natter-Setup.exe aus diesem Paket ausfuehren.“ | OK | [Bericht](../../build/auswertung/035/Natter-Pruefbericht_ohne_installation.txt) | 31 | Skript |
| 5b | `Zertifikat-eintragen` lesen | Vergleich vor dem Eintragen | `$ERWARTET` = `DFE4686F…A8E8`, Vergleich vor `Import-Certificate`, bei Abweichung „Nichts eingetragen“. Gegenprobe am Vergleich: mitgelieferte `.cer` angenommen, fremde (Logitech-Stamm) abgelehnt | OK | [05_zip.json](../../build/auswertung/035/ergebnisse/05_zip.json) | 29 | von Hand (gelesen) + Skript |
| 6 | Installation wie ein Schüler | Ordner, ~30 000 Dateien, 1,2 GB, Verknüpfungen, kein `.ruff_cache` | 278,0 s, 30 075 Dateien, 1 193 MB; `LICENSE`, `Lizenzen\`, `Natter.exe`, `manifest.json`, `python\`; Startmenü, Desktop, `.natter` → `Natter.exe "%1"`; kein `.ruff_cache`; `HKCU\Software\Natter` nicht angelegt | OK | [bestand_nach_installation_035_frisch.json](../../build/auswertung/035/ergebnisse/bestand_nach_installation_035_frisch.json) | – | Skript |
| 6a | Mitgelieferte Python | QtCharts scheitert, Versionen wie `uv.lock` | `No module named 'PySide6.QtCharts'`; zehn Pakete ohne Abweichung; Python 3.13.15 in Auslieferung und Entwicklung. Gegenprobe: im Entwicklungsbaum ist QtCharts importierbar | OK | [python_035_frisch.json](../../build/auswertung/035/ergebnisse/python_035_frisch.json) | 33 | Skript |
| 7 | Signaturen | alle gültig, Vorlagen unsigniert | 808 Binärdateien: 804 `Valid` (413 Qt, 375 Natter Codesignatur, 16 Microsoft), 4 `NotSigned` = `PyInstaller\bootloader\…\run*.exe`, gewollt unsigniert (Punkt 34). Gegenprobe: unsignierte `.pyd` → `NotSigned`, Natter.exe mit einem geänderten Byte → `HashMismatch`, Kopie → `Valid` | OK | [signaturen_035_frisch.json](../../build/auswertung/035/ergebnisse/signaturen_035_frisch.json), [07_signatur_gegenprobe.json](../../build/auswertung/035/ergebnisse/07_signatur_gegenprobe.json) | 34 | Skript |
| 8 | Update 0.3.4 → 0.3.5 | alte Fassung erkannt, alte Dateien weg, Pakete bleiben | 0.3.4 aus dem Release still installiert, `cowsay` über „Pakete → Paket installieren …“ (25,4 s). Setup 0.3.5 sichtbar: 5 Seiten, keine Sprachauswahl, „Natter 0.3.4 ist installiert und wird auf 0.3.5 aktualisiert.“ Still: 427,4 s. Danach 30 100 Dateien = frisch + 25 von `cowsay`, keine fehlt, nur `natter-0.3.5.dist-info`, Merkliste gelöscht, Manifest in Ordnung, QtCharts fehlt. Die Aufgabenseite zeigt „Registriere Natter mit der .natter-Dateierweiterung“ | OK / Auffällig | [08_update_vergleich.json](../../build/auswertung/035/ergebnisse/08_update_vergleich.json), [setup_seiten_v035_ueber_v034.json](../../build/auswertung/035/ergebnisse/setup_seiten_v035_ueber_v034.json), [Seite 1](../../build/auswertung/035/bilder/08_v035_ueber_v034_seite1.png) | 26, 28, 49 | UIA (win32) + Skript |
| 9 | Start mit verschmutzter Umgebung | startet normal, echtes `pcl` | Hauptfenster erscheint; `pythonw.exe -m ide` und Jedi-Prozess ohne `PYTHONPATH`, `PYTHONHOME`, `PYTHONUSERBASE`, `VIRTUAL_ENV`, mit `PYTHONNOUSERSITE=1`; Falle nicht ausgelöst. Gegenprobe ohne Starter: `PYTHONPATH` → falsches `pcl` gewinnt, falsches `PYTHONHOME` → Python startet nicht. Dieser erste Start nach der Installation dauerte 15,15 s | OK / Auffällig | [09_umgebung.json](../../build/auswertung/035/ergebnisse/09_umgebung.json), [Bild](../../build/auswertung/035/bilder/09_verschmutzte_umgebung.png) | 48 | UIA |
| 9a | Erster Start wiederholt, Gegenversuch 0.3.3 | Ursache der 15 s eingrenzen | nach erneuter Installation 18,49 / 2,56 / 2,42 s; 0.3.3 (Setup vom 25.09.) heute frisch: 15,36 / 2,32 / 2,30 s – der lange erste Start liegt am Rechner, nicht an 0.3.5 | Auffällig | [09b](../../build/auswertung/035/ergebnisse/09b_erster_start_wiederholt.json), [09c](../../build/auswertung/035/ergebnisse/09c_gegenversuch_033_erster_start.json) | 48 | UIA |
| 10 | Startzeit | bedienbar in wenigen Sekunden | 2,49 / 2,54 / 2,60 s bis zum Hauptfenster | OK | [10_startzeit.json](../../build/auswertung/035/ergebnisse/10_startzeit.json) | – | UIA |
| 11 | Werkzeuge → Umgebung prüfen | „unverändert“, Oberfläche bedienbar | „Umgebung geprüft: alle Programmdateien unverändert.“ nach 8,24 s ab Menüklick; währenddessen antwortet die Oberfläche in höchstens 0,05 s | OK | [11_umgebung_pruefen.json](../../build/auswertung/035/ergebnisse/11_umgebung_pruefen.json), [Bild](../../build/auswertung/035/bilder/11_umgebung_pruefen.png) | 33 | UIA |
| 11a | Kerndatei verändert | deutsche Warnung | „Natter wurde nach der Erstellung verändert: python/Lib/site-packages/pcl/crt.py (verändert) … Trotzdem starten?“ | OK | [Bild](../../build/auswertung/035/bilder/11_manipulation_kern.png) | – | UIA |
| 11b | `manifest.json` entfernt / unlesbar | Warnung | „… manifest.json fehlt in C:\…\Natter“ bzw. „… manifest.json ist unlesbar.“, jeweils mit „Trotzdem starten?“. Nach dem Zurücklegen: Manifest in Ordnung | OK | [weg](../../build/auswertung/035/ergebnisse/11_manipulation_manifest_weg.json), [kaputt](../../build/auswertung/035/ergebnisse/11_manipulation_manifest_kaputt.json), [danach](../../build/auswertung/035/ergebnisse/manifest_035_nach_manipulation.json) | 27 | UIA + Skript |
| 12 | Bildschirmfotos | Ladebild, Startbild, hell, dunkel | Startbild, hell, dunkel vorhanden. Ladebild beim Start über das Startmenü: „Natter / Version 0.3.5 / Fenster wird aufgebaut …“, kein „Projekt wird geöffnet“. Ohne offenes Projekt zeigt der Explorer leere Überschriften „Formulare“, „Units“, „Diagramme“ | OK / Auffällig | [Ladebild](../../build/auswertung/035/bilder/12_ladebild_startmenue_1.png), [Startbild](../../build/auswertung/035/bilder/12_startbild.png), [hell](../../build/auswertung/035/bilder/12_hauptfenster_hell.png), [dunkel](../../build/auswertung/035/bilder/12_hauptfenster_dunkel.png) | 33, 52 | UIA; Ladebild per Startmenü |
| 13 | Sichtbare Texte | deutsch, Dezimalkomma, keine Anrede, kein Verweis auf andere IDEs | 307 Texte (Hauptfenster 75, Warnungen, Statuszeile, Prüfbericht, `ZUERST-LESEN.txt`): keine Anrede, kein Verweis, kein Dezimalpunkt; einziger englischer Text ist die zitierte Windows-Meldung. Gegenprobe: dieselbe Suche findet im Installer 0.3.2 10 Texte mit Anrede. Installer 0.3.5: alle Seiten unpersönlich bis auf „Registriere Natter …“ (Schritt 8) | OK / Auffällig | [13_texte.json](../../build/auswertung/035/ergebnisse/13_texte.json), [13_texte_gegenprobe.json](../../build/auswertung/035/ergebnisse/13_texte_gegenprobe.json) | 30, 49 | Skript |
| 13a | Lizenz- und Hinweisseite ganz (Punkt 4) | vollständig, Umlaute, nichts abgeschnitten | Setup sichtbar, beide Seiten bis ans Ende geblättert (7 und 3 Bilder), danach abgebrochen: Text zeilengleich mit `INSTALLER_LIZENZ.txt` (54 Zeilen) und `INSTALLER_HINWEIS.txt` (23 Zeilen), Umlaute richtig, keine Zeile abgeschnitten | OK | [04_setup_texte.json](../../build/auswertung/035/ergebnisse/04_setup_texte.json), [Lizenz 4](../../build/auswertung/035/bilder/04_lizenz_4.png), [Hinweis 2](../../build/auswertung/035/bilder/04_hinweis_2.png) | 4 | UIA (win32) |

Zum Ladebild: gestartet aus einem Hintergrundprozess liegt es hinter dem
aktiven Fenster. Ein Bildschirmausschnitt zeigt dann das fremde Fenster
darüber, `PrintWindow` lieferte diesmal auch nach 20 Versuchen nur
Schwarz, und ein kurz nach vorn gelegtes Fenster war noch leer
(`12_ladebild_*.png`). Über das Startmenü gestartet, wie ein Schüler es
tut, erscheint es richtig gezeichnet. Das ist eine Grenze des
Testaufbaus.

## 3. Messwerte Teil 1

| Messung | Wert |
|---|---|
| Bau 0.3.5 (26.09.) | 48,9 min, pytest 22:51 (4250 Tests), `dist\Natter` 12:45, Installer 10:29 |
| Setup-Datei / ZIP | 289 910 912 / 290 119 819 Byte |
| Installation frisch, still | 278,0 s; weitere: 250,8 / 271,5 / 275,0 s |
| Installation 0.3.4, still | 263,6 s |
| Update 0.3.4 → 0.3.5, still | 427,4 s |
| Gegenversuch 0.3.3 installiert | 265,0 s (am 25.09.: 148,9 s) |
| Deinstallation | 42,8 / 13,4 / 19,6 / 11,7 / 13,5 / 21,1 s |
| Dateien und Größe frisch | 30 075 Dateien, 1 193 MB, 861 `__pycache__`-Ordner |
| Binärdateien | 808: 804 gültig signiert, 4 Vorlagen gewollt unsigniert |
| Erster Start nach Installation | 15,15 s; wiederholt 18,49 s; 0.3.3 heute 15,36 s |
| Start bis Hauptfenster | 2,49 / 2,54 / 2,60 s |
| Umgebung prüfen | 8,24 s ab Menüklick, Oberfläche ≤ 0,05 s |

---

# Teil 2: Schülerweg in der installierten Natter

27.09.2026, derselbe Rechner, Natter 0.3.5 frisch installiert.

## Wie bedient wurde

Wie bei 0.3.3 über UIA (pywinauto 0.6.9) mit Bildschirmfotos. Die
Grenzen des Testaufbaus aus der Auswertung 0.3.3 gelten weiter
(Doppelklick als Fensternachricht, längerer Code über die
Zwischenablage, modale Menüaktionen und Auswahllisten mit der Maus,
Konsolen über `TermControl`). Neu:

- Die Palettenkacheln tragen seit 0.3.4 Namen (Punkt 44). Die
  Hilfsfunktionen der Testskripte suchten namenlose Kacheln und
  verwechselten benannte mit Meldungen; sie wurden angepasst, danach
  wurden Kacheln über ihren Namen gewählt.
- Mehrere Skripte klickten auf Bildschirmpositionen, die am Foto von
  0.3.3 abgelesen waren (Diagramm-Editor, Designer). Wo das ins Leere
  ging, wurde nach dem Foto dieses Laufs neu gemessen und wiederholt.
- Ein Klick im ersten Lauf von G kam zu früh nach dem Reiterwechsel und
  verknüpfte am Formular; eine gezielte Nachstellung zeigte das
  richtige Verhalten (Zeile 21a).

Eingriffe per Skript statt über die Oberfläche:

- **B:** die durch Punkt 47 verdoppelten Anführungszeichen in der Unit
  korrigiert, damit Start, Menü und Neuöffnen prüfbar waren.
- **G:** die SQL-Platzhalter des Testcodes auf `:name`, wie bei 0.3.3.
- **J:** der Attributname „stand: float“ in Name und Typ getrennt, um
  die Vererbung im erzeugten Code zu prüfen.
- **M:** `u_main.py` beider Projekte vor dem Export auf den Stand aus B
  und C zurückgesetzt.
- **O:** die Nutzerdaten per Skript verschoben und zurückgespielt.

## 6. Schritte Teil 2

| Nr | Schritt | Erwartet | Beobachtet | Ergebnis | Beleg | Punkt | geprüft per |
|---|---|---|---|---|---|---|---|
| 14 | A Lehrgang 01–09 | öffnen, starten, Kernfunktion | 01: „Freut mich, Jörg!“, „In 10 Jahren bist du 25.“; 02: Hinweis und „keine Zahl“; 03: 12 + 4 = 16, „Durch null kann man nicht teilen.“; 04: „3 Kekse“; 05: Bild über den Dateidialog → „testbild_natter.png - 43,9 kB“; 06: „Björn Größe“, 12,50; 07: Koeln → „Mittelwert 10,7 °C“; 08: polynomial, 165 cm → 38,2; 09: → „Banane“ | OK | [teil2_A.json](../../build/auswertung/035/ergebnisse/teil2_A.json), Bilder `A_*` | – | UIA; Menü und Listen mit der Maus |
| 14a | A Auf Original zurücksetzen | Rückfrage, Original | „„03_Taschenrechner“ auf den Auslieferungszustand zurücksetzen? …“ → Ja → „steht wieder im Auslieferungszustand“ | OK | [Bild](../../build/auswertung/035/bilder/A_zuruecksetzen_rueckfrage.png) | – | UIA |
| 14b | A Beispielkommentar 01 | keine Anrede | Original in der Installation: „# Gestartet wird das Programm mit F5.“ Die Arbeitskopie zeigte noch „Drücke F5 …“: Natter hatte eine ältere Kopie aus `Dokumente\Natter\01_Begruessung` nach `Beispielprojekte` umgezogen (gewollt, die Arbeit der Schülerin bleibt) | OK | `site-packages\beispielprojekte\01_Begruessung\u_main.py` | 45 | Skript (Dateiinhalt; die Aussage betrifft die Datei in der Installation, die kein Fenster zeigt) |
| 14c | A Laufzeit 09 | Fenster in einigen Sekunden | erster Lauf aus Natter: kein Fenster in 40 s; zweiter Lauf 40,7 s einschließlich Öffnen; ohne Natter 68,4 s, dann 3,3 s. Import von scikit-learn, pandas, PySide6 selbst 1,3 s | Auffällig | [14c](../../build/auswertung/035/ergebnisse/14c_09_ohne_natter.json), [22a](../../build/auswertung/035/ergebnisse/22a_import_zeiten.txt), [erster Lauf](../../build/auswertung/035/ergebnisse/teil2_A_erster_lauf.json) | 48 | UIA + Skript |
| 15 | B Projekt, Palette, Objektinspektor | platzieren, verschieben, Eigenschaft, Rückgängig | „Projekt → Neues Projekt …“; Kacheln per UIA mit Namen; Label, Edit, Button platziert, Button um 120/40 px verschoben, „Verdoppeln“ gesetzt; zweimal Rückgängig → Ausgangslage, zweimal Wiederholen → wieder da | OK | [teil2_B_035.json](../../build/auswertung/035/ergebnisse/teil2_B_035.json), [Bild](../../build/auswertung/035/bilder/B_2_caption.png) | 44 | UIA + Maus |
| 15a | B Komponentenbaum, Design-Prüfung | sofort aktuell, keine Fehlalarme | Baum nach jedem Platzieren aktuell; neues Projekt: „Design-Prüfung: 6 Funde“; nach „Verdoppeln“: „Die Beschriftung „Verdoppeln“ ist breiter als die Komponente (75 Pixel) …“. Das Panel zeigte nur zwei Einträge; die Prüfung der `.pfm` am Ende von B ergibt 9 Funde aus vier Regeln (Tab-Reihenfolge, abgeschnittener Text, Präfix, Standardname), keinen zur Geometrie | OK | [Bild](../../build/auswertung/035/bilder/B_1_platziert.png), [15a_design_pruefung_umrechner.json](../../build/auswertung/035/ergebnisse/15a_design_pruefung_umrechner.json) | 36, 45 | UIA + Skript (alle Funde) |
| 15b | B Menü-Editor über das Symbol | Symbol per UIA, F2 | Symbol „MainMenu“ per UIA gefunden und angeklickt, F2 öffnet „Menü bearbeiten“; „Datei → Beenden“, `entries` „(1 Eintrag)“ | OK | [Bild](../../build/auswertung/035/bilder/B_3_menue_editor.png) | 44, 45 | UIA |
| 15c | B Doppelklick auf Button | Methode anlegen und hinspringen | Reiter `u_main.py` vorn, Cursor in `button_click`, `pass` markiert, kein `pass` mehr in der Klasse darüber; Statuszeile „Methode button_click in u_main.py.“ | OK | [Bild](../../build/auswertung/035/bilder/B_4_methode.png) | 37 | UIA + Nachricht |
| 15d | B Code tippen | Zeilen wie getippt | Aus `self.label.caption = f"{wert * 2:.2f}".replace(".", ",")` wird `…replace(".", ",")"""")""""""")`; Start verweigert („2 Funde vor dem Start“) | Fehler | [Bild](../../build/auswertung/035/bilder/B_5_code_getippt.png), [teil2_B_035.json](../../build/auswertung/035/ergebnisse/teil2_B_035.json) | 47 | UIA, Code getippt |
| 16 | B starten, bedienen, neu öffnen, ohne Natter | Zahl mit Komma → Ergebnis | nach dem Eingriff: „2,5“ → „5,00“; Natter geschlossen, neu geöffnet: „3,25“ → „6,50“; ohne Natter `python.exe main.py`: Fenster nach 1,5 s, „1,5“ → „3,00“ | OK | [teil2_B_035_fortsetzung.json](../../build/auswertung/035/ergebnisse/teil2_B_035_fortsetzung.json), [Bild](../../build/auswertung/035/bilder/B_lauf2_programm.png) | – | UIA |
| 16a | B Menü im Programm | „Datei“ in der Menüleiste | „Datei“ links oben (0/0 im Fenster), kein Knopf „···“, klappt „Beenden“ auf – in allen drei Läufen | OK | [Bild](../../build/auswertung/035/bilder/B_lauf1_menue.png) | 39 | UIA + Maus |
| 17 | C Konsolenprojekt | eigenes Fenster, Eingabe, Umlaute | „Natter – Gruss“; „Jürgen Weiß“ → „Grüße, Jürgen Weiß! Äpfel, Öl, Übung, Maß: 3,5 €“ | OK | [Bild](../../build/auswertung/035/bilder/C_konsole.png) | – | UIA (TermControl) |
| 18 | D Name falsch / Doppelpunkt / Einrückung | nicht starten, Zeile, Wo/Was/Prüfe | alle drei nicht gestartet, richtige Zeile, deutsch, ohne Anrede. Einrückung: „Nach dem Doppelpunkt in der Zeile darüber fehlt ein eingerückter Block. Die Zeile um eine Ebene einrücken (Tab-Taste, vier Leerzeichen).“ – eigene Meldung, aber „Prüfe“ als Anweisung | OK / Auffällig | [teil2_D.json](../../build/auswertung/035/ergebnisse/teil2_D.json), [Bild](../../build/auswertung/035/bilder/D_einrueckung_ide.png) | 45, 51 | UIA |
| 18a | D `int("3,5")`, Division durch 0 | Wo/Was/Prüfe | „Der Text „3,5“ lässt sich nicht als ganze Zahl lesen.“ / „Es wurde durch 0 geteilt.“, jeweils Zeile und Leitfrage | OK | [Bild](../../build/auswertung/035/bilder/D_int_komma_konsole.png) | – | UIA (TermControl) |
| 18b | D Endlosschleife | anhalten | „Start → Stopp“ beendet sie nach 1,5 s | OK | [teil2_D.json](../../build/auswertung/035/ergebnisse/teil2_D.json) | – | UIA |
| 18c | D `input()` im GUI-Programm | deutsche Erklärung, Fehler-Code | „Keine Eingabe für input() (EOFError) … ein Programm mit Fenster hat keine Konsole …“; Programm endet, Panel „Programm beendet (Code 1) … in einem eigenen Fenster gezeigt.“ | OK | [Bild](../../build/auswertung/035/bilder/D_input_gui_0.png) | 41 | UIA |
| 18d | D Komponente fehlt | Wo/Was/Prüfe, Fehler-Code | „„ergebnis“ existiert bei diesem Objekt nicht.“, Zeile 6; Panel „Programm beendet (Code 1) …“ | OK | [Bild](../../build/auswertung/035/bilder/D_komponente_fehlt_ide.png) | 41 | UIA |
| 19 | E Vervollständigung | Liste, Typen, Erklärung | „pri“ → `print(*values: object, …) -> None – gibt Werte aus`; „konto_ab“ → `konto_abheben(konto: int, betrag: float) -> float – Hebt einen Betrag ab …` | OK | [Bild](../../build/auswertung/035/bilder/E_konto_ab.png) | – | UIA |
| 19a | E Parameterhilfe, Klammern | nach Übernahme; Umschalt schließt | nach Übernahme mit Eingabetaste sichtbar (`konto_abheben(konto: int, …) → float`); Umschalt+8 nach `print` → `print()` mit Hilfe; Umschalt+2 `a` Umschalt+2 → `x = "a"""` | OK / Fehler | [Hilfe](../../build/auswertung/035/bilder/E_parameterhilfe.png), [Umschalt+8](../../build/auswertung/035/bilder/E_umschalt8.png), [Umschalt+2](../../build/auswertung/035/bilder/E_umschalt2_anfuehrungszeichen.png) | 43, 47 | UIA + Tasten |
| 19b | E Tastenkürzel, hell/dunkel, Minimap | vorhanden | Tastenkürzel als Reiter; hell/dunkel Schritt 12; Minimap nur im Diagramm-Editor (Schritt 24) | OK | [Bild](../../build/auswertung/035/bilder/E_editor_minimap.png) | – | UIA |
| 20 | F Debugger | Haltepunkt, Einzelschritt, Variablen | „Angehalten: nach einem Einzelschritt“, `i` 1 → 2, `summe` 0 → 1; Tabelle ohne „special variables“, beide Zeilen sichtbar | OK | [Bild](../../build/auswertung/035/bilder/F_einzelschritt.png) | 45 | UIA + Maus |
| 20a | F Test-Explorer | grün und rot | „2 Tests gelaufen, 1 nicht bestanden. …“ | OK | [Bild](../../build/auswertung/035/bilder/F_tests.png) | – | UIA |
| 21 | G Datenbank | Tabelle, Grid, ändern, neu laden | GUI-Projekt mit StringGrid und `SQLite3Connection` (eine Vorlage gui_db nennt der Bericht nicht mehr); 2 Namen gespeichert, einer geändert, nach Neustart „1 Anna Groß-Weber“, „2 Bernd Müller“ | OK | [teil2_G3.json](../../build/auswertung/035/ergebnisse/teil2_G3.json), [Bild](../../build/auswertung/035/bilder/G_neustart.png) | 45 | UIA; Code per Zwischenablage |
| 21a | G Ereignisse verknüpfen | vorhandene Methode wählbar | Liste zeigt „(kein)“, `button2_click`, `button_click`, `form_create`; gewählt → `.pfm` `button2: on_click = button2_click` | OK | [21a_probe_ereignis.json](../../build/auswertung/035/ergebnisse/21a_probe_ereignis.json), [Liste](../../build/auswertung/035/bilder/G_probe_3_liste.png) | 38 | UIA + Maus |
| 21b | G Datenbank-Panel | im Fenster | „Ansicht → Datenbank“: eingedockt unten rechts, „Nicht verbunden“ bis eine Datei gewählt ist | OK | [Bild](../../build/auswertung/035/bilder/G_db_panel.png) | 45 | UIA |
| 21c | G Beschriftung „Speichern“ | Fund, wenn abgeschnitten | im 75-Pixel-Knopf sichtbar abgeschnitten, ohne Fund (Schätzung genau 75) | Auffällig | [Bild](../../build/auswertung/035/bilder/G_designer.png) | 52 | UIA |
| 22 | H CSV, pandas, Chart, Bild, HTML | alles sichtbar | Grid „2,4“, „2,8“ mit Dezimalkomma, Balkendiagramm, Bild, „Mittelwert Hamburg: 9,7 °C“; `bericht.html` als Reiter in Natter | OK | [Bild](../../build/auswertung/035/bilder/H_programm.png), [HTML](../../build/auswertung/035/bilder/H_html_in_natter.png) | 42 | UIA |
| 22a | H Platzieren auf ein StringGrid | Komponente entsteht | Klick mit gewählter Kachel „Chart“ in das StringGrid legt nichts an, Platzierungsmodus bleibt still aktiv; nachgestellt mit der installierten Python | Fehler | [Designer](../../build/auswertung/035/bilder/H_designer.png) | 50 | UIA + Skript |
| 23 | I Paketverwaltung | installieren, importieren | `cowsay` in 16,8 s, Oberfläche ≤ 0,07 s, Import und Ausgabe „Hallo aus Natter“ | OK | [teil2_I.json](../../build/auswertung/035/ergebnisse/teil2_I.json) | – | UIA |
| 23a | I Umgebung prüfen danach | keine Warnung | „Umgebung geprüft: alle Programmdateien unverändert.“ | OK | [Bild](../../build/auswertung/035/bilder/I_umgebung.png) | 40 | UIA |
| 24 | J Klassendiagramm | zeichnen, speichern, öffnen, exportieren | zwei Klassen, Attribut über F2, gespeichert, geöffnet; Vererbung per zwei Klicks (`inheritance` s2 → s1); PNG 3 601 Byte, PDF 12 302 Byte A4 quer; Minimap, Lineale; Ansicht in der INI unter `[diagramm]`, kein `HKCU\Software\Natter` | OK | [teil2_J3.json](../../build/auswertung/035/ergebnisse/teil2_J3.json), [teil2_J_pdf.json](../../build/auswertung/035/ergebnisse/teil2_J_pdf.json), [Bild](../../build/auswertung/035/bilder/J_klassendiagramm_vererbung.png) | 45 | UIA + Maus |
| 24a | J Quelltext aus Klassendiagramm | Vererbung, Namensprüfung | mit „stand: float“: „Kein Quelltext erzeugt. Konto: Das Attribut „stand: float“ ist kein gültiger Python-Name. …“; nach dem Eingriff: `class Sparkonto(Konto):` hinter `class Konto` | OK | [Meldung](../../build/auswertung/035/bilder/J_k2_quelltext_folge.png), [teil2_J3_vererbung.json](../../build/auswertung/035/ergebnisse/teil2_J3_vererbung.json) | 35 | UIA |
| 24b | J Struktogramm | Blöcke, Export, Quelltext | Anweisung und Verzweigung eingefügt, PDF 12 492 Byte, Quelltext `def Ablauf(): … if False: pass`; beim zweiten Erzeugen Rückfrage „„u_ablauf.py“ gibt es bereits. Überschreiben?“ | OK | [Bild](../../build/auswertung/035/bilder/J_struktogramm_bloecke.png) | – | UIA + Maus |
| 24c | J Diagramm nach Änderung von außen | – | erneutes Öffnen einer außerhalb geänderten `.pdiag` zeigt im offenen Fenster den alten Stand | Auffällig | [Meldung](../../build/auswertung/035/bilder/J_k2_quelltext_folge.png) | 52 | UIA |
| 25 | K `.lfm`-Import | im Designer, im Explorer | `f_Pizza`: „unit1.lfm importiert: 31 Hinweise im Importbericht …“, `pizza.pfm/.py/_design.py`, Designer offen, „pizza“ sofort im Explorer des Konsolenprojekts | OK | [teil2_K.json](../../build/auswertung/035/ergebnisse/teil2_K.json), [Bild](../../build/auswertung/035/bilder/K_import.png) | 45 | UIA + Dateidialog |
| 26 | L Prüfungsmodus | Einschränkungen, Neustart | Rückfrage nennt 4 h; „Prüfungsmodus – noch 3:59 h“; keine Vorschlagsliste, Meldung ohne „Prüfe“, „Quelltext → Erzeugen …“ gesperrt; übersteht Neustart; beendet per INI wie vereinbart. Handbuch: „Er lässt sich in Natter nicht vorzeitig beenden.“ | OK | [teil2_L.json](../../build/auswertung/035/ergebnisse/teil2_L.json), [Bild](../../build/auswertung/035/bilder/L_an_editor.png) | 45 | UIA; Ende per INI |
| 27 | M Quelltext als PDF | A4 | 1 Seite, MediaBox 595 × 842, 22 293 Byte | OK | [teil2_M.json](../../build/auswertung/035/ergebnisse/teil2_M.json) | – | UIA + Dateidialog |
| 27a | M Exe-Export | Dauer, Größe, Signatur | GUI 66,6 s / 54,9 MB, Konsole 12,9 s / 8,0 MB; beide `Valid`, „CN=Natter Codesignatur“, DigiCert-Zeitstempel; kein neues Zertifikat | OK | [teil2_M.json](../../build/auswertung/035/ergebnisse/teil2_M.json), [Bild](../../build/auswertung/035/bilder/M_gui_ide.png) | 34 | UIA + Skript |
| 27b | M Exe im fremden Ordner | läuft ohne Natter | `%TEMP%\fremd`, ohne Python im PATH: GUI in 3,5 s ohne Konsole, „1,5“ → „3,00“; Konsole nach 1,4 s, „Zoë Brück“ → Umlaute und € richtig | OK | [Bild](../../build/auswertung/035/bilder/M_fremd_gui.png), [teil2_M.json](../../build/auswertung/035/ergebnisse/teil2_M.json) | – | UIA |
| 28 | N Deinstallation | alles weg | 21,1 s; Programmordner, Startmenü, Desktop, `.natter`, `NatterProjekt`, Uninstall-Eintrag, `HKCU\Software\Natter` weg; bleiben `%APPDATA%\Natter\Natter-IDE.ini` und die Projekte in `Dokumente\Natter` (gewollt: Nutzerdaten) | OK | [teil2_N.json](../../build/auswertung/035/ergebnisse/teil2_N.json) | 21, 45 | Skript (stille Deinstallation hat keine Oberfläche) |
| 28a | N Exe nach Deinstallation | eigenständig | GUI 3,8 s, „3,00“; Konsole 1,5 s, Umlaute richtig | OK | [Bild](../../build/auswertung/035/bilder/N_fremd_gui.png), [teil2_N.json](../../build/auswertung/035/ergebnisse/teil2_N.json) | – | UIA |
| 29 | O Aufräumen | Ausgangszustand | Testprojekte nach `035\teil2_projekte\`, `%TEMP%\fremd` nach `035\fremd_nach_test\` verschoben (die zwei Exe von 0.3.3 vorher nach `sicherung\fremd_vorher\`); Sicherung zurückgespielt; 0.3.5 frisch installiert (275,0 s, Manifest in Ordnung); 21 von 21 Nutzerdateien SHA-256-gleich mit der Sicherung; Zertifikate 144 = 144; kein Testprozess; Start normal, „Umgebung geprüft: alle Programmdateien unverändert.“; INI danach erneut zurückgespielt | OK | [29_endstand_start.json](../../build/auswertung/035/ergebnisse/29_endstand_start.json), [manifest_035_endstand.json](../../build/auswertung/035/ergebnisse/manifest_035_endstand.json) | – | Skript (Dateien zurückspielen) + UIA |

## 7. Messwerte Teil 2

| Messung | Wert |
|---|---|
| Lehrgangsbeispiel öffnen bis Programm bedient | 11,1–15,3 s (01–06, 08), 07: 24,8 s, 09: 40,7 s |
| Paketinstallation `cowsay` | 16,8 s, Oberfläche ≤ 0,07 s |
| Exe-Export GUI / Konsole | 66,6 s / 12,9 s |
| Exe-Größe GUI / Konsole | 54,9 MB / 8,0 MB |
| Exe im fremden Ordner GUI / Konsole | 3,5 s / 1,4 s (nach Deinstallation 3,8 s / 1,5 s) |
| Endlosschleife stoppen | 1,5 s |
| Quelltext als PDF | 1 Seite A4, 22 293 Byte |
| Diagramm PNG / PDF / Struktogramm-PDF | 3 601 / 12 302 / 12 492 Byte |
| Deinstallation nach Benutzung | 21,1 s, 0 Reste |
| Endstand installiert | 275,0 s, 30 075 Dateien |

## 4. Nur von Hand prüfbar

Checkliste für Jonathan.

- [ ] SmartScreen beim Start von `Natter-Setup.exe` auf einem Rechner ohne eingetragenes Zertifikat, Datei frisch aus dem Internet
- [ ] Smart App Control eingeschaltet: Setup, `Natter.exe`, exportierte Schüler-Exe; Eintrag in `CodeIntegrity/Operational`
- [ ] Druck auf A4: Quelltext, Klassendiagramm, Struktogramm auf einem echten Drucker (geprüft wurde nur das Seitenformat der PDFs)
- [ ] Echter Schulrechner mit Standardkonto (nicht Administrator) und Proxy: Installation, Start, Paketverwaltung über pip, Update mit nachinstalliertem Paket
- [ ] Update ohne Netz: Meldung mit der gesicherten Paketliste
- [ ] `Zertifikat-eintragen.cmd` ausführen, die UAC-Rückfrage einmal ablehnen und einmal annehmen
- [ ] Verteilung über eine Softwareverteilung mit `/VERYSILENT`: landet Natter im Profil des Verteilkontos?
- [ ] Doppelklick und Tippen mit echter Maus und deutscher Tastatur: Anführungszeichen (Punkt 47), Klammern, Parameterhilfe
- [ ] Erster Start nach der Installation auf einem Schulrechner messen (Punkt 48)
- [ ] Exe-Export auf einem Rechner ohne Bauzertifikat (Zertifikat „Natter Programme dieses Rechners“)
- [x] Installer-Seiten Lizenz und Hinweise (Punkt 4): erledigt in Schritt 13a

## 5. Zusammenfassung

**Ergebnis gesamt.** Der Schülerweg läuft in 0.3.5 von der
Installation bis zur eigenständigen Exe, und fast alle Befunde aus
0.3.3 sind am Rechner bestätigt behoben: Update mit Hinweis und
vollständig ersetztem `python\` samt wieder installiertem Paket,
Integritätsprüfung ohne stille Lücke und ohne Fehlalarm nach „Pakete“,
signierte Schüler-Exe, Vererbung und Namensprüfung im erzeugten Code,
Sprung zur Methode, Ereignisse aus der Unit, Menü im Programm,
deutsche Meldung zu `input()` mit Fehler-Code, Dezimalkomma im Grid,
benannte Palettenkacheln, Datenbank-Panel im Fenster. Ein Fehler ist
durch die Korrekturen erst sichtbar geworden und trifft jede
Schülerin.

**Die fünf wichtigsten Befunde, nach Schwere:**

1. **Getippte Anführungszeichen werden verdoppelt (Punkt 47).** Seit
   Klammern auch mit Umschalt geschlossen werden, ergibt `"a"` getippt
   `"a"""`; eigener Code mit Text startet dann nicht.
2. **Platzieren per Klick in ein StringGrid legt nichts an (Punkt 50)**,
   und der Platzierungsmodus bleibt ohne Hinweis aktiv.
3. **Der erste Start nach der Installation dauert 15–18 s (Punkt 48)**,
   ein Beispiel mit scikit-learn beim ersten Mal über 60 s; liegt am
   Rechner (Gegenversuch 0.3.3), betrifft aber jeden frisch
   eingerichteten Schulrechner.
4. **Der Hinweis zu Einrückungsfehlern gibt eine Lösung vor (Punkt 51)**,
   statt eine Leitfrage zu stellen.
5. **Installer: „Registriere Natter mit der .natter-Dateierweiterung“
   (Punkt 49)**, die einzige Stelle mit Befehlsform.

**Neu angelegte Punkte in `offene_punkte.md`:**

| Nr | Titel |
|---|---|
| 47 | Getippte Anführungszeichen werden verdoppelt |
| 48 | Der erste Start nach der Installation dauert 15 bis 18 Sekunden |
| 49 | Der Installer schreibt „Registriere Natter mit der .natter-Dateierweiterung“ |
| 50 | Ein Klick zum Platzieren in ein StringGrid legt nichts an |
| 51 | Der Hinweis zu Einrückungsfehlern gibt eine Anweisung statt einer Frage |
| 52 | Kleinere Befunde aus dem Schülerweg 0.3.5 |

**Bekannte offene Punkte:**

- **4** (Lizenzseite nie angesehen): bestätigt behoben, in Schritt 13a
  vollständig geprüft; am Punkt vermerkt, kann nach
  `erledigte_punkte.md`.
- **7** (Starter braucht die halbe Startzeit, zurückgestellt): nicht
  Gegenstand; Startzeit 2,5 s gemessen, der Anteil des Starters nicht.
- **46** (Signaturtest und Debugger-Test im CI): am Rechner nicht
  prüfbar, betrifft den CI-Runner.

**Bereits erledigte Punkte, am Rechner bestätigt:** 21 (4, 28), 26 und
28 (8), 27 (11b), 29 (5b), 30 (13, bis auf 49), 31 (5a), 33 (6a, 11, 12),
34 (7, 27a), 35 (24a), 36 und 37 (15a, 15c), 38 (21a), 39 (16a), 40
(23a), 41 (18c, 18d), 42 (22), 43 (19a, bis auf 47), 44 (15, 15b),
45 (15a, 15b, 18, 20, 21b, 24, 25, 26, 28).

---

## Kontrolle der Vollständigkeit (27.09.2026)

Nachgeprüft am Rechner, im Repository und an den Belegen, nach
denselben Prüfpunkten wie die Kontrolle von 0.3.3. Testbeginn:
Commit `6637c8d` (lokal, nicht gepusht; er enthält die Kontrolle von
0.3.3).

| Prüfpunkt | Ergebnis | Beleg |
|---|---|---|
| 1.1 Kopf vollständig | erledigt | Abschnitt 1 |
| 1.2 Jeder Schritt 1–13 und A–O hat eine Zeile mit allen Spalten | erledigt: 62 Zeilen, Nummern 1–29 lückenlos, keine doppelt, keine leere Zelle | Auszählung per Skript |
| 1.3 „OK“ mit konkretem Wert | erledigt: jede „OK“-Zeile nennt eine Zahl, einen wörtlichen Meldungstext oder ein Bild | ebenso |
| 1.4 Jeder verlinkte Beleg existiert | erledigt: 98 von 98 | Linkprüfung per Skript |
| 1.5 Belege passen inhaltlich | erledigt: Werte aus den JSON-Dateien übernommen; Stichproben geprüft (Signaturen 804/4, Hauptfenster 75 Texte, Paket 0.3.4 25,4 s, Design-Prüfung). Eine Aussage aus dem Panel („keiner zur Geometrie“) war nur für zwei von sechs Einträgen belegt und ist mit einer Prüfung der `.pfm` ergänzt | `15a_design_pruefung_umrechner.json` |
| 1.6 Zeilen per Skript statt UIA begründet | erledigt: 14b, 28, 29 in der Spalte „geprüft per“ begründet, Eingriffe unter „Wie bedient wurde“ | Tabelle Teil 2 |
| 1.7 Messwerte, Zusammenfassung, Checkliste | erledigt: Checkliste mit SmartScreen, Smart App Control, A4, Standardkonto und Proxy; Punkt 4 erledigt (13a) | Abschnitte 3, 4, 5, 7 |
| 1.8 Gegenproben Teil 1 als Datei | erledigt: Signatur, GPL-Import, verschmutzte Umgebung, Manifest, Texte, Fingerabdruck | `07_signatur_gegenprobe.json`, `python_035_frisch.json`, `09_umgebung.json`, `11_*`, `13_texte_gegenprobe.json`, `05_zip.json` |
| 2.1 Jede Zeile „Auffällig“/„Fehler“ nennt einen Punkt | erledigt | Tabelle |
| 2.2 Punkte mit Gemeldet, Beobachtet, Ursache, Zu tun | erledigt: 47–52 vollständig | `docs/offene_punkte.md` |
| 2.3 Keine Nummer doppelt oder neu vergeben | erledigt: vor dem Test „nächster Punkt 47“, danach „53“ | `git diff 6637c8d -- docs/offene_punkte.md` |
| 2.4 Jeder neue Punkt in einer Schrittzeile | erledigt: 47–52 | Tabelle |
| 2.5 Bekannte Punkte 4, 7, 46 bewertet | erledigt | Abschnitt 5 |
| 3.1 Kein Push, Tag, Release seit Testbeginn | erledigt: Tags `v0.3.2`, `v0.3.4`, `v0.3.5` und die drei Releases wie vorher, `origin/main` unverändert | `git tag`, `gh release list`, `git log origin/main..HEAD` |
| 3.2 Nur Auswertung und `offene_punkte.md` geändert | erledigt: keine Änderung in `ide/`, `pcl/`, `tools/`, `tests/` | `git diff --stat 6637c8d -- ide pcl tools tests` |
| 3.3 `tools/signieren/` unverändert, nichts Geheimes versioniert | erledigt: Schlüsseldateien vom 17.09., ignoriert | `git status --ignored tools/signieren` |
| 3.4 Keine Belege committet | erledigt: nichts unter `build/` versioniert | `git ls-files build` |
| 4.1 Endstand installiert | erledigt: 0.3.5 frisch (vereinbarter Endstand), Manifest in Ordnung | `manifest_035_endstand.json` |
| 4.2 Python ohne Testwerkzeuge und ohne Paket aus I | erledigt: frisch installiert, kein `cowsay` | `bestand_nach_installation_035_endstand.json` |
| 4.3 Umgebung prüfen grün, Start normal, Prüfungsmodus aus | erledigt | `29_endstand_start.json` |
| 4.4 `%APPDATA%\Natter` und `Dokumente\Natter` wie Sicherung | erledigt: 21 von 21 Dateien SHA-256-gleich, INI nach dem Startcheck erneut zurückgespielt und bytegleich | `sicherung\hashes_vorher.txt` |
| 4.5 Zertifikate (sechs Speicher) | erledigt: 144 = 144, nichts dazu, nichts weg | `zertifikate_vorher.txt` |
| 4.6 Keine Testprozesse, keine Reste in `%TEMP%\fremd` | erledigt: keine Prozesse, `%TEMP%\fremd` leer (Inhalt nach `035\fremd_nach_test\`), kein Prüfbericht auf dem Schreibtisch | `Get-Process`, `Test-Path` |
| 4.7 Sicherung vorhanden | erledigt: `build\auswertung\035\sicherung\` | – |

### Lücken

Keine im Sinne der Prüfpunkte. Nur als Text belegt, ohne Bild:
die Konsolenausgabe der exportierten Exe im fremden Ordner (27b, 28a);
das Fenster war beim Foto schon geschlossen.

### Abweichungen am Rechner

| Abweichung | Herkunft | Befehl |
|---|---|---|
| `HKCU\Software\Natter` (Reste älterer Fassungen) fehlt | gewollt: der Uninstaller von 0.3.5 räumt ihn (Punkt 45); gesichert in `sicherung\hkcu_software_natter.reg` | `Test-Path HKCU:\Software\Natter` |
| `cowsay` nicht mehr in der installierten Python | vor dem Test aus dem Update-Test vom 26.09. vorhanden; Endstand ist eine frische 0.3.5 | `& "$env:LOCALAPPDATA\Programs\Natter\python\python.exe" -m pip list` |
| `%TEMP%\fremd` leer statt mit den zwei Exe von 0.3.3 | verschoben nach `035\sicherung\fremd_vorher\` | `Get-ChildItem $env:TEMP\fremd` |

**Urteil:** Ja, vollständig: alle Schritte 1–13 und A–O sind mit
vorhandenen, passenden Belegen dokumentiert, jeder Befund steht als
Punkt in `offene_punkte.md`, und der Rechner entspricht bis auf die
drei begründeten Abweichungen der Sicherung.
