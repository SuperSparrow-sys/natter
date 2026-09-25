# Natter – Bericht

Was Natter ist, wie es aufgebaut ist, wie es entstanden ist, wie eine
Auslieferung entsteht und was dabei gelernt wurde. Wie Natter bedient
wird, steht in der [README](../README.md) und im
[Handbuch](handbuch.md); was noch zu tun ist, in
[`offene_punkte.md`](offene_punkte.md).

Dieser Bericht ersetzt seit dem 25. September 2026 die früheren
Planungsunterlagen: `PLAN.md`, `entwicklung.md`, `umsetzungsplan.md`,
`pruefbericht.md`, `aktionen.md` und die fünfzehn Arbeitspakete
`arbeitspakete/M0.md` bis `M15.md`, zusammen rund 7000 Zeilen. Sie
stehen vollständig in der Git-Historie, zuletzt in Commit `8f35f2c`:

```
git show 8f35f2c:docs/arbeitspakete/M13.md
```

Wo im Quelltext „Abschnitt 17.8" oder „M13, Schritt 4" steht, ist eine
Stelle in diesen Unterlagen gemeint. Die Abschnitte 1 bis 16 beziehen
sich auf die README, 17 bis 23 auf das frühere `entwicklung.md`; der
Inhalt von 17 bis 23 steht jetzt in diesem Bericht.

## Was in `docs/` liegt

| Datei | Wofür | Wer sie liest |
|---|---|---|
| `bericht.md` | dieser Bericht | wer an Natter arbeitet |
| `offene_punkte.md` | Fehler und Aufgaben, die noch zu erledigen sind | wer an Natter arbeitet |
| `erledigte_punkte.md` | behobene Fehler mit Ursache und Änderung | wer einen ähnlichen Fehler sucht |
| `handbuch.md` | Einrichten, Prüfungsmodus, Tasten, Fehlersuche | Schulen; liegt als `Handbuch.html` in der ZIP |
| `erste_schritte.md` | Anleitung für den Einstieg | Natter selbst, „Hilfe → Erste Schritte" |
| `komponenten.md` | jede Komponente mit Eigenschaften und Ereignissen | Natter selbst, „Hilfe → Komponenten-Referenz" |
| `fehlerkatalog.yaml` | die Fehlermeldungen für Schüler, für Menschen lesbar | die Tests gleichen den Katalog im Code dagegen ab |

---

## 1. Stand im September 2026

| | |
|---|---|
| Fassung | 0.3.2, veröffentlicht als GitHub-Release |
| Quelltext | 36 100 Zeilen in `ide/` (120 Module) und `pcl/` (29 Module), dazu 3 200 Zeilen Werkzeuge in `tools/` |
| Tests | 4152 in 209 Dateien (42 400 Zeilen), alle grün; die CI läuft bei jedem Push auf Windows |
| Lehrgang | neun aufeinander aufbauende Beispielprojekte |
| Auslieferung | `Natter-Setup.exe` (278 MB) und `Natter-<Version>-Setup.zip` mit Zertifikat, Skripten und Handbuch |
| Installiert | rund 30 000 Dateien, 1,2 GB, unter `%LOCALAPPDATA%\Programs\Natter` |

Alle geplanten Meilensteine M0 bis M15 sind abgeschlossen. Was noch
offen ist, steht in [`offene_punkte.md`](offene_punkte.md).

---

## 2. Aufbau

### 2.1 Repository

```
natter/
  pcl/                 die Komponentenbibliothek, gegen die Schülerprogramme laufen
    components/        standard, additional, common, chart, system, medien, menus, graphics, data_access, data_controls
    theme/             Stylesheet für Schülerprogramme aus design/tokens.json
    properties.py      das Eigenschaften-System (Prop, Event)
    form.py, control.py, crt.py, dialogs.py, errors.py, fehlerkatalog.py, pruefungsmodus.py
  ide/                 die Entwicklungsumgebung
    shell/             Hauptfenster, Startbild, Quelltexteditor, Panels, Theme der IDE
    actions/           Aktionsregister: Menü, Werkzeugleiste, Tastenkürzel an einer Stelle
    palette/           Komponentenpalette mit Reitern
    designer/          Formular-Designer: Zeichenfläche, Auswahl, Anfasser, Rückgängig
    inspector/         Objektinspektor, Menü-Editor, Komponentenbaum
    codegen/           erzeugt u_*_design.py aus der .pfm, fügt Ereignismethoden mit libcst ein
    debugger/          DAP-Client gegen debugpy, Fehlerkatalog, Variablen-Tabellenansicht
    testrunner/        Test-Explorer für unittest
    viewers/           CSV-, Bild-, HTML-, Markdown- und Hilfeansicht
    database/          Datenbank-Panel (SQLite)
    diagramm/          Diagramm-Editor: sieben Diagrammarten, Export, Druck, Quelltexterzeugung
    lint/              Design-Prüfer
    env/               Paketverwaltung über pip
    export/            „Als Exe exportieren", Signatur der exportierten Exe, Quelltext als PDF
    import_lfm/        Import von .lfm-Formularen
    integritaet/       signiertes Prüfsummen-Manifest und Prüfung beim Start
    run/               Programmstart, Prüfung vor dem Start
    project/           Projektdatei, Vorlagen, Neu-Dialog
    pfade.py           Dokumente-Ordner, Ordner der Beispielkopien
  tools/               Werkzeuge für den Bau, nicht Teil der Auslieferung
    auslieferung_bauen.py   der ganze Bau in einem Befehl (Abschnitt 7)
    fortschritt.py          Fortschrittsbalken und Protokoll des Baus
    ide_paketieren.py       baut dist\Natter
    paket_bauen.py          stellt die ZIP zusammen
    veroeffentlichen.py     stellt Setup-Datei und ZIP als GitHub-Release bereit
    launcher.py             Quelltext von Natter.exe
    natter.iss              Inno Setup
    signieren/              Zertifikat, Signierskripte
    paket/                  ZUERST-LESEN.txt und die Skripte für die ZIP
  schemas/             pfm-, project- und pdiag-Schema mit Versionsnummer
  templates/           Projektvorlagen gui, console, gui_db
  beispielprojekte/    der Lehrgang, 01_Begruessung bis 09_ObstSortierer
  design/              tokens.json: Farben, Abstände, Schriften für hell und dunkel
  tests/               pytest, headless mit QT_QPA_PLATFORM=offscreen
```

### 2.2 Die ausgelieferte Installation

```
<Installationsordner>\
  Natter.exe              schlanker Starter (Symbol, Versionsangabe, signiert)
  python\                 CPython 3.13 (python-build-standalone), mit pip
    python.exe            für Konsolenprogramme
    pythonw.exe           für die IDE und für GUI-Programme
    Lib\site-packages\    ide, pcl, PySide6, pandas, numpy, … + pip + PyInstaller
                          dazu templates, docs (nur zwei Hilfeseiten), design, schemas, beispielprojekte
  Lizenzen\               LGPL-3.0 und die Lizenztexte aller Bibliotheken
  manifest.json           signierte Prüfsummen (Abschnitt 7.5)
```

Natter bringt eine vollständige Python-Installation mit. Auf einem
verwalteten Schulrechner ist keine vorhanden, und Schüler dürfen keine
installieren. Eine dort schon vorhandene Python bleibt unberührt.

**Warum keine venv.** Eine venv speichert absolute Pfade (in
`pyvenv.cfg` und in Startskripten) und funktioniert nach dem
Verschieben nicht mehr. Deshalb kommt Python als verschiebbare
Standalone-Distribution, dieselbe Quelle, aus der `uv python install`
bedient wird.

**IDE und Schülerprogramme teilen sich eine Umgebung.** Der Starter
riegelt sie dafür nach außen ab: er entfernt `PYTHONPATH`,
`PYTHONHOME`, `PYTHONUSERBASE` und `VIRTUAL_ENV` und schaltet das
Benutzer-Paketverzeichnis ab. Sonst kann eine fremde Python-Umgebung
auf einem Schulrechner Natter umwerfen, ohne dass jemand etwas an
Natter geändert hat.

**Wo die Daten liegen.** Projekte liegen unter `Dokumente\Natter`, die
Arbeitskopien der Beispiele eine Ebene tiefer unter
`Dokumente\Natter\Beispielprojekte`. „Dokumente" ist der Ordner, den
Windows dafür eingetragen hat, auch wenn er auf OneDrive umgeleitet
ist. Einstellungen und Fehlerprotokoll stehen unter `%APPDATA%\Natter`.

### 2.3 Die verbindlichen Schnittstellen

Diese Stellen verbinden die Teile von Natter miteinander. Wer sie
ändert, ändert mehrere Teile zugleich und prüft entsprechend sorgfältig.

| Schnittstelle | Was sie festlegt |
|---|---|
| `schemas/*.schema.json` | die Dateiformate `.pfm` (Formulare), `.natter` (Projekte), `.pdiag` (Diagramme), jeweils mit Versionsnummer wie `pfm/1` |
| `Prop`/`Event` in `pcl/properties.py` | jede Eigenschaft und jedes Ereignis einer Komponente mit Typ, Standardwert, Kategorie und deutschem Hilfetext. Objektinspektor, Codegenerator und Referenzseite lesen dieselbe Beschreibung |
| Aktionsregister in `ide/actions/` | eine Aktion ist Menüeintrag, Werkzeugleisten-Knopf, Tastenkürzel und Eintrag der Tastenübersicht zugleich und wird nur einmal beschrieben: ID, deutscher Name, Menüposition, Kürzel, Bereich, Symbol. Die Übersicht unter „Hilfe" wird daraus erzeugt |
| DAP | der Debugger spricht das Debug Adapter Protocol mit `debugpy` |
| `design/tokens.json` | Farben, Abstände, Radien und Schriften für hell und dunkel, für IDE und Schülerprogramme |
| `docs/fehlerkatalog.yaml` | Aufbau jeder Fehlermeldung: Wo, Was, Prüfe – mit Ort und Erklärung, nie mit dem korrigierten Code |

Erzeugte Dateien wie `u_*_design.py` tragen die Kopfzeile „Automatisch
erzeugt aus … – nicht bearbeiten" und werden nur über den Generator in
`ide/codegen/` geändert.

---

## 3. Entstehung: die Meilensteine

Natter ist in sechzehn Meilensteinen entstanden, M0 bis M15. Jeder
hatte ein Abnahmekriterium, das am laufenden Programm geprüft wurde und
nicht nur an Tests.

| | Inhalt | Abnahme |
|---|---|---|
| M0 | Repository, CI, Schemas, Design-Tokens | Schema-Tests grün |
| M1 | `pcl`: Eigenschaften-System, erste Komponenten, Theme, Generator `.pfm` → `u_*_design.py` | Ampel, Würfelspiel und StringGrid-Übung laufen mit `python main.py` |
| M2 | IDE-Grundgerüst: Hauptfenster, Aktionsregister, Projekte, Explorer, Editor, Units, Start als eigener Prozess | Projekt öffnen, Datei-Menü, Konsolenprogramm mit `input()` |
| M3 | Formular-Designer, Objektinspektor, Palette, Ereignis-Code mit libcst, Rückgängig | Ampel vollständig in der IDE gebaut, jede Eigenschaft über den Inspektor |
| M4 | Prüfung vor dem Start (Ruff), Debugger über DAP, Fehlerkatalog, Test-Explorer | Fehlerbeispiele, Haltepunkt mit Variablen, Soll/Ist im Test-Explorer |
| M5 | Datenbank, pandas, Chart, CSV-/Bild-/HTML-Ansicht, Datenbank-Panel | Kontoverwaltung mit SQLite, CSV-Auswertung, Highscore als HTML |
| M6 | Konsolen-Feinschliff, `pcl.crt` mit Cursor und Farben | Konsolen- und CRT-Übungen laufen |
| M7 | Design-Prüfer mit 14 Regeln, Paketverwaltung | jede Regel erkennt ihr Testformular, Paket über das Menü installierbar |
| M8 | `.lfm`-Import, Exe-Export, Installer, Signatur, Prüfsummen-Manifest | Pizza-Projekt importiert, fertiggestellt, als Exe gestartet; veränderte Datei wird erkannt |
| M9 | Diagramm-Editor: Klassendiagramm, Struktogramm, Entscheidungstabelle, danach Use-Case, Aktivität, Zustand, Sequenz; Export, Druck, Quelltexterzeugung | Ampel als Klassendiagramm, Struktogramm und Entscheidungstabelle, als PDF |
| M10 | `Chart` in der Palette, sechs Diagrammarten, Regression über numpy, scikit-learn | CSV einlesen, Regressionsgerade, Steigung und R² – im Designer zusammengeklickt |
| M11 | Schülertauglichkeit: jede Funktion durchgeprüft, Symbole, Vervollständigung, Startbild, Meldungen mit Lösungsvorschlag, Prüfungsmodus | Funktionsprüfung aller Menüs, Knöpfe, Docks und Paletteneinträge |
| M12 | Durchsicht aus Sicht von Lernenden: Hilfe, Fehlerkatalog ohne Debugger, gebaute Exe | vier Fehler in der gebauten Exe gefunden und behoben |
| M13 | eigene Python-Installation statt PyInstaller-Bundle, Installer mit allen üblichen Seiten, Bau in einem Befehl | pip, Export, Start und Prüfung arbeiten in der installierten Fassung |
| M14 | Aufräumen (490 MB Lazarus-Referenz auf 185 kB Prüfdaten), Lehrgang aus neun Projekten, `Timer` in der Palette, Exe als eine Datei | Lehrgang läuft vollständig |
| M15 | `MainMenu`/`PopupMenu` mit Menü-Editor, `PaintBox`/`Canvas`, Maus-Ereignisse, sechs weitere Komponenten, einfachere Datenbank, Lineale und Minimap | Zeichenprogramm mit der Maus, Menüleiste im Schülerprogramm |

Nach M15 kamen Fehlerbehebungen aus der Benutzung dazu. Sie stehen mit
Ursache in [`erledigte_punkte.md`](erledigte_punkte.md): Stylesheets,
die auf Dialoge durchschlugen, eine winzige Druckvorschau, der
Prüfungsmodus in der Fußzeile, Beispielkopien am falschen Ort, der
Designer, der beim Umschalten dunkel blieb, und weitere.

### Wie geprüft wurde

Nicht nur über die Testsuite. Jeder Schritt wurde auch im laufenden
Programm angesehen, mit Bildschirmfotos und zurückgelesenen PDFs. In
M9 hat das sieben Fehler gefunden, die alle Tests bestanden hatten:
abgeschnittene Texte, eine im Schwarz-Weiß-Druck unsichtbare
Kopfzeile, ein Struktogramm am Blattrand und eine Druckvorschau, die
das Fenster 48 Sekunden eingefroren hätte.

In M11 wurde jede bedienbare Stelle ausgelöst: 53 Menüeinträge, 8
Knöpfe der Werkzeugleiste, 5 Docks (schließen und wieder öffnen), 20
Kacheln der Palette, die Menüs aller sieben Diagrammarten und 48
Formen und Verbindungen. Die Liste wird aus der Oberfläche gelesen,
nicht von Hand gepflegt; ein neuer Menüeintrag ist damit vom nächsten
Testlauf an mitgeprüft (`tests/test_ide_funktionspruefung.py`). Vier
Einträge sind ausgenommen, weil sie wirklich etwas tun, das in einen
Testlauf nicht gehört, etwa ein Programm starten oder installieren.

---

## 4. Entscheidungen

| Entscheidung | Begründung |
|---|---|
| PySide6 statt PyQt | PySide6 steht unter LGPL, PyQt unter GPL |
| Eigener Editor (`QPlainTextEdit`) statt Monaco | Monaco hätte QtWebEngine gebraucht, rund 100 MB. Die eigene Hervorhebung in den Farben von VS Code reicht für den Unterricht; Jedi liefert die Vervollständigung |
| Formulare als erzeugter Python-Code | `.pfm` beschreibt das Formular, daraus entsteht `u_*_design.py`. Jedes Schülerprogramm läuft damit auch ohne Natter mit `python main.py` |
| Eigene Python-Installation statt PyInstaller-Bundle (M13) | in einem eingefrorenen Python gibt es kein `pip`, und PyInstaller braucht für „Als Exe exportieren" eine vollständige Installation |
| Kein Tcl/Tk | Natter baut jede Oberfläche mit Qt; Tcl/Tk kostete 10,5 MB. Mit `tkinter` fällt `turtle` weg; gezeichnet wird mit `PaintBox` und `Canvas` |
| Nur SQLite, keine Passwörter (M15) | MySQL hätte ein gespeichertes Passwort in der `.pfm` und dafür einen Schlüsselspeicher nach sich gezogen. Stattdessen ist die Datenbank einfacher geworden: eine Abfrage ist `db.query("SELECT …")` |
| Exe-Export als eine Datei (M14) | für Natter selbst ist der entpackte Ordner richtig (1,2 GB entpacken sich nicht bei jedem Start), für ein Schülerprogramm die eine Datei, die sich verschicken lässt |
| Diagramm-Editor in eigenem Fenster | mit eigenem Taskleisten-Eintrag, nur zum Zeichnen von Hand; UML-Inhalte werden über einen Eigenschaften-Dialog bearbeitet |
| Prüfungsmodus | vier Stunden ohne Lösungsvorschläge, ohne Vervollständigung und ohne Quelltexterzeugung aus Diagrammen; übersteht einen Neustart und läuft von selbst aus |
| Keine KI in der IDE, nur Deutsch, keine Aliasse für Python-Namen | Natter soll Python unterrichten, wie es ist |
| Beispiele als Arbeitskopien | ein Beispiel wird nach `Dokumente\Natter\Beispielprojekte` kopiert und dort weiterbenutzt; „Auf Original zurücksetzen …" holt den Ausgangszustand zurück |
| Zurückgestellt | Update-Mechanismus (auf Schulrechnern verteilt die Systembetreuung), ER-Diagramm, Syntaxdiagramm, DIA-Import, mehrere Struktogramme auf einer Seite |

---

## 5. Lizenz

Natter ist ein privates Projekt unter eigener Lizenz des
Projektinhabers: Nutzung erlaubt, Weitergabe und Verbreitung nicht
erlaubt. Die mitgelieferten Bibliotheken behalten ihre eigenen
Lizenzen. Daraus folgen Regeln für die Auswahl:

| Regel | Umsetzung |
|---|---|
| Nur freizügige Lizenzen oder LGPL | PySide6/Qt (LGPLv3), Jedi, Ruff, libcst, debugpy, SQLAlchemy, openpyxl (MIT), pandas, numpy, scikit-learn, scipy (BSD), matplotlib (PSF-basiert) |
| Keine Qt-Module, die nur unter GPL stehen | Qt Charts und Qt Data Visualization werden nicht verwendet; `Chart` baut auf matplotlib auf |
| Kein PyQt | PyQt steht unter GPL |
| LGPL-Pflichten für Qt | die Qt-Bibliotheken bleiben austauschbare Dateien im Programmordner, die Lizenztexte liegen in `Lizenzen\` |
| Lizenztexte | der Bau sammelt sie für jedes Laufzeitpaket in `Lizenzen\` und warnt bei Paketen ohne Lizenzangabe. Eine automatische Prüfung auf GPL-Komponenten war geplant und fehlt noch (Punkt 24 in `offene_punkte.md`) |

Mit „Als Exe exportieren" erzeugte Schülerprogramme sind davon
unabhängig; der PyInstaller-Bootloader erlaubt jede Lizenz für das
erzeugte Programm. Diese Einordnung ist eine technische
Planungsgrundlage und keine Rechtsberatung.

---

## 6. Tests

`uv run pytest` läuft headless (`QT_QPA_PLATFORM=offscreen`). Die
Drucker-Tests sind im Standardlauf abgewählt (`uv run pytest -m
drucker` startet sie): die Druckerabfrage von Windows kostet mit einem
nicht erreichbaren Netzwerkdrucker knapp eine Minute und ließ dabei
Zeitgrenzen anderer Tests reißen.

Vorgehen: erst gegen nachgebildete Systeme (headless, SQLite im
Speicher, nachgebildetes `git` und `gh`), zuletzt gegen echte.

| Bereich | Wie |
|---|---|
| `pcl` | jede Komponente: Eigenschaften lesen und schreiben, Wirkung auf das Widget, Typprüfung, Ereignisse |
| Eigenschaften-Rundlauf | eine Änderung im Objektinspektor wirkt wie dieselbe Zuweisung im Code |
| Beispielprojekte | jedes läuft mit `python main.py` ohne IDE |
| Formate | `.pfm` → `u_*_design.py` → Formular ergibt dieselben Werte; Schema-Prüfung |
| Designer, Diagramm-Editor | Kommandos und Rückgängig ohne Fenster |
| Codegenerierung | libcst-Einfügen und -Umbenennen, Formatierung bleibt erhalten |
| Debugger | echte DAP-Sitzungen gegen `debugpy` |
| Fehlermeldungen | jede Meldung hat Ort und Erklärung und keinen Lösungscode |
| Oberfläche | jede bedienbare Stelle wird ausgelöst (Abschnitt 3) |
| Texte | `tests/test_textstil.py`: niemand wird mit „du" oder „Sie" angesprochen, keine Markdown-Hervorhebung und keine Zuschreibungs-Etiketten in Kommentaren, kein Verweis auf Lazarus außerhalb von `ide/import_lfm/` |
| Auslieferung | Rauchprobe in der gebauten Python, Manifest, Signaturen (Abschnitt 7) |

Tests, die etwas an Dateien ändern, arbeiten auf Kopien in `tmp_path`.
Das gilt auch für alles, was der Designer automatisch in eine `.pfm`
zurückschreibt. Eine Absicherung in `tests/conftest.py` lenkt
Heimverzeichnis, Dokumente-Ordner, Einstellungen und die
Designvorgabe für jeden Test auf Wegwerf-Ordner um.

Die **CI** läuft bei jedem Push auf `windows-latest`
(`.github/workflows/ci.yml`): Ruff und alle Tests, rund neun Minuten.
Bis zum 25. September lief sie auf Linux und scheiterte dort 200 Mal
hintereinander schon beim Einsammeln der Tests, weil
`PySide6.QtMultimedia` unter Linux `libpulse` erwartet.

---

## 7. Auslieferung

### 7.1 Der Bau in einem Befehl

```powershell
uv run python -m tools.auslieferung_bauen --version 0.3.3
```

Das Skript führt zwölf Schritte aus und prüft nach jedem, ob das
Ergebnis stimmt. Es bricht ab, statt eine kaputte Auslieferung
fertigzubauen.

| Schritt | Wofür |
|---|---|
| 1 Arbeitsbaum | meldet nicht Eingechecktes; prüft, ob sich veröffentlichen ließe (`gh` angemeldet, nichts außer den Versionsdateien offen) |
| 2 Versionen | `pyproject.toml`, `tools/natter.iss` und `ide/main.py` tragen dieselbe Nummer; `--version` setzt alle drei |
| 3 `ruff check` | das verbindliche Tor aus AGENTS.md |
| 4 `pytest` | rot heißt: nicht bauen. Entfällt, wenn derselbe eingecheckte Stand mit denselben Paketen schon grün war; `--alle-tests` erzwingt ihn |
| 5 `dist\Natter` | Python bereitstellen, Pakete aus `uv.lock` installieren, Starter bauen, Lizenzen sammeln, signieren, Manifest schreiben |
| 6 Rauchprobe | Importe und eine Rechnung in der **gebauten** Python, nicht im Entwicklungsbaum |
| 7 Manifest | dieselbe Prüfung, die beim Schüler bei jedem Start läuft |
| 8 Installer | Inno Setup, Kompression auf acht Kernen |
| 9 Signieren | die Setup-Datei |
| 10 Signaturen | Windows selbst fragen, ob jede Binärdatei gültig signiert ist |
| 11 Paket | `Natter-<Version>-Setup.zip` mit Setup-Datei, Zertifikat, Skripten, Handbuch, Lizenzen |
| 12 Veröffentlichen | Version einchecken, Tag `v<Version>`, Push, GitHub-Release mit Setup-Datei und ZIP |

Schritt 6 ist die wichtigste Prüfung. Getestet wird der
Entwicklungsbaum, ausgeliefert wird `dist\Natter`, und genau dazwischen
sind mehrere Auslieferungsfehler entstanden (Abschnitt 9).

Schalter: `--nicht-veroeffentlichen` für Probebauten,
`--nur-installer` baut aus einem vorhandenen `dist\Natter` nur die
Setup-Datei neu, `--ohne-tests` überspringt Schritt 4 und
veröffentlicht nicht. Den Ablauf drumherum – wann gebaut werden darf,
welche Nummer die nächste ist, was danach festgehalten wird – beschreibt
`.claude/commands/auslieferung.md`.

### 7.2 Fortschritt und Protokoll

In einer Konsole zeigt der Bau drei Zeilen am unteren Rand: einen
Balken für den ganzen Bau mit Restzeit, einen für den laufenden Schritt
und darunter, woran gerade gearbeitet wird. Grün heißt gezählt (Tests,
Pakete, Dateien), gelb mit „≈" heißt geschätzt nach der Dauer des
letzten Laufs (`build\bau-cache\bauzeiten.json`). In eine Datei
umgeleitet gibt es Zeilen statt Balken. Jede Zeile aller beteiligten
Programme steht in `dist\auslieferung.log`; bei einem Fehler zeigt die
Meldung Schritt, Ende der Ausgabe und den Pfad zum Protokoll.

### 7.3 Was den Bau schneller macht, ohne am Ergebnis etwas zu ändern

| Maßnahme | Wirkung |
|---|---|
| Inno Setup auf acht Kernen (`LZMANumBlockThreads=8`) | getrennt gemessen 185 statt 691 Sekunden, im Bau 492; die Setup-Datei wird 0,7 % größer |
| Signaturen unveränderter Dateien wiederverwenden | abgelegt unter der Prüfsumme der unsignierten Datei, je Zertifikat getrennt, in `build\bau-cache\signaturen`; Schritt 10 prüft trotzdem jede |
| Tests nicht zweimal für denselben Stand | nur bei eingechecktem Baum und denselben Paketversionen |
| Setup-Datei im ZIP nur ablegen | sie ist schon mit LZMA gepackt |

Die nächste große Ersparnis wäre, die Paketinstallation (6 Minuten) zu
überspringen, wenn sich `uv.lock` nicht geändert hat. Sie ist nicht
gebaut: an genau so einer Stelle ist schon einmal ein alter Stand in
die Auslieferung geraten.

### 7.4 Der Installer

Inno Setup mit den üblichen Seiten: Willkommen, Lizenz zum Annehmen,
Zielordner, Startmenü, Zusatzaufgaben (Desktopsymbol,
`.natter`-Verknüpfung), Zusammenfassung, Fertigstellen mit „Natter
starten". Deinstallation über „Apps & Features".

Voreinstellung ist die Installation nur für den angemeldeten Benutzer
unter `%LOCALAPPDATA%\Programs\Natter`. Auf einem Schulrechner ohne
Administratorrechte ist das der einzige Weg, und nur dort kann `pip`
später auch schreiben.

`[InstallDelete]` leert bei einem Update die sieben Ordner, die Natter
selbst mitbringt. Inno Setup überschreibt sonst nur und löscht nichts,
was in der neuen Fassung fehlt; ein entferntes Modul bliebe
importierbar und könnte das neue verdecken.

### 7.5 Signatur und Prüfsummen-Manifest

Zwei Ebenen, beide ohne Kosten:

| Ebene | Umsetzung | Wirkung |
|---|---|---|
| Authenticode | selbst ausgestelltes Zertifikat „Natter Codesignatur" (`New-SelfSignedCertificate`), jede Binärdatei ohne fremde Signatur wird signiert, mit Zeitstempel von DigiCert | Windows zeigt den Herausgeber; jede Veränderung macht die Signatur ungültig |
| Prüfsummen-Manifest | SHA-256 der Programmdateien in `manifest.json`, mit einem eigenen Ed25519-Schlüssel signiert; der öffentliche Schlüssel steckt im Starter | Natter erkennt beim Start veränderte, fehlende oder fremde Dateien |

Bei jedem Start werden die Kerndateien geprüft (0,07 s), über
„Werkzeuge → Umgebung prüfen" alle (2,6 s). Nicht geprüft werden
übersetzte Module und die Fremdbibliotheken in `site-packages`: dort
legt Python beim ersten Import `.pyc` an, und `pip` darf dort Pakete
nachinstallieren.

Beide privaten Schlüssel liegen nur auf dem Baurechner
(`tools/signieren/`, von Git ausgeschlossen) und nie in der
Auslieferung. Läge der Codesignatur-Schlüssel dort, könnte jede
Installation beliebigen Code mit einem Zertifikat signieren, dem alle
Rechner mit eingetragenem Zertifikat vertrauen, und widerrufen ließe
sich das nicht. Die exportierte Exe einer Schülerin wird deshalb mit
einem Zertifikat signiert, das Natter auf ihrem Rechner anlegt und
dessen Schlüssel nicht exportierbar ist (`ide/export/signatur.py`).

### 7.6 Smart App Control

Die intelligente App-Steuerung von Windows 11 lässt sich mit einem
selbst ausgestellten Zertifikat nicht zufriedenstellen. Das wurde
zunächst anders eingeschätzt und hat zwei Fassungen gekostet.

Gemessen am 21. September: mit dem Zertifikat in `LocalMachine\Root`
und `LocalMachine\TrustedPublisher` wies Windows frisch signierte
Bibliotheken beim Laden ab. Im Ereignisprotokoll
(`Microsoft-Windows-CodeIntegrity/Operational`) standen sie als
`ValidatedSigningLevel=1`, also als unsigniert, während
`Get-AuthenticodeSignature` sie als `Valid` meldete. Dieselbe Datei lief
vor dem Nachsignieren und war danach gesperrt. Entschieden wird nach
dem Ruf des einzelnen Dateihashs bei Microsoft; für eine frisch
signierte Datei ist das Zufall, und ein Programm aus 800 Binärdateien
braucht 800 Treffer.

Eine frühere Messung schien das Gegenteil zu zeigen: eine einzige
signierte Datei ließ Natter auf einem Testrechner starten. Die übrigen
Dateien waren dort aber über ihren Ruf durchgekommen; das Zertifikat
hatte damit nichts zu tun.

Was daraus folgt:

- Auf Rechnern mit eingeschalteter App-Steuerung startet Natter nicht.
  Abhilfe ist, sie auszuschalten (Einstellungen → Datenschutz und
  Sicherheit → Windows-Sicherheit → App- und Browsersteuerung). Das
  lässt Windows nur in eine Richtung zu: einmal aus, bleibt sie aus,
  bis Windows neu aufgesetzt wird. Oder ein Zertifikat einer
  öffentlichen Zertifizierungsstelle, etwa 200 bis 400 Euro im Jahr.
- Verwaltete Schulrechner (Intune, Domäne) haben die App-Steuerung
  normalerweise aus; betroffen sind frisch aufgesetzte Einzelgeräte.
- Das Zertifikat bleibt trotzdem nützlich: es nennt den Herausgeber,
  erspart auf Rechnern mit eingetragenem Zertifikat die
  SmartScreen-Warnung und macht Veränderungen erkennbar.
- `ZUERST-LESEN.txt` stellt die Frage nach der App-Steuerung an den
  Anfang, weil davon alles Weitere abhängt.

### 7.7 Die ZIP und die Veröffentlichung

`Natter-<Version>-Setup.zip` enthält:

| Datei | Wofür |
|---|---|
| `ZUERST-LESEN.txt` | Reihenfolge und Voraussetzungen, Versionsnummer wird beim Bau eingesetzt |
| `Natter-Setup.exe` | das Installationsprogramm |
| `natter-codesign.cer` | nur der öffentliche Teil des Zertifikats |
| `Zertifikat-eintragen.cmd`/`.ps1` | trägt es für alle Konten ein, mit Rückfrage nach Administratorrechten; prüft danach, ob der Eintrag wirklich im Speicher steht |
| `Zertifikat-entfernen.cmd`/`.ps1` | nimmt es wieder heraus |
| `Natter-pruefen.cmd`/`.ps1` | startet die installierte Fassung und legt einen Bericht auf den Schreibtisch |
| `Handbuch.html`/`.md` | das Handbuch |
| `Lizenzen\` | die Lizenztexte |

Zu jedem `.ps1` gibt es ein `.cmd` zum Doppelklicken: auf einem frisch
aufgesetzten Rechner verweigert Windows PowerShell-Skripte per
Doppelklick, und Dateien aus einem entpackten ZIP gelten als „aus dem
Internet". Das `.cmd` ruft das Skript mit `-ExecutionPolicy Bypass` auf,
nur für diesen einen Aufruf.

Die Setup-Datei und die ZIP liegen als Anhänge an einem GitHub-Release
im öffentlichen Repository, nicht in der Git-Historie: GitHub nimmt
dort keine Datei über 100 MB an. Der Link „Herunterladen" in der
README zeigt auf die neueste Fassung. Vor dem Entpacken die ZIP unter
*Eigenschaften* „zulassen", sonst fragt Windows bei jeder Datei nach.

### 7.8 Stolpersteine bei der Installation

| Problem | Ursache | Abhilfe |
|---|---|---|
| „Eine Anwendungssteuerungsrichtlinie hat diese Datei blockiert" | intelligente App-Steuerung (7.6) | ausschalten oder öffentliches Zertifikat |
| SmartScreen-Warnung beim Installieren | keine Reputation für ein eigenes Zertifikat | Zertifikat eintragen, oder „Weitere Informationen" → „Trotzdem ausführen" |
| „Das System kann den angegebenen Pfad nicht finden" | ein sehr langer Zielordner reißt die Windows-Pfadgrenze | kurzen Zielordner wählen; die Vorgabe ist kurz genug |
| Nachinstallieren über „Pakete" schlägt fehl | systemweite Installation ohne Schreibrecht | für den angemeldeten Benutzer installieren |
| Nach dem Deinstallieren bleibt ein Ordner | `.ruff_cache` aus der Prüfung vor dem Start | offen, Punkt 21 in `offene_punkte.md` |

---

## 8. Protokoll der Auslieferungen

Nach jedem Bau kommt hier ein Eintrag dazu: Datum, Fassung, Größe,
Signaturen, Dauer, und was der Lauf aufgedeckt hat, samt Irrweg.

### 0.3.2 – 25. September 2026

`Natter-Setup.exe`, 277,9 MB. `Natter.exe` und `Natter-Setup.exe`
`Valid`, keine Binärdatei ohne gültige Signatur. Die ZIP (278 MB)
enthält elf Dateien und 28 Lizenztexte. Veröffentlicht als Release
`v0.3.2`, das Tag zeigt auf `268de88`, den Stand, aus dem gebaut wurde.
Neu: Beispielkopien im eigenen Unterordner und „Auf Original
zurücksetzen …", Designer und Programm folgen dem Design von Natter.

Erster Bau mit Fortschrittsanzeige, 36,7 Minuten:

| Schritt | 0.3.1 | 0.3.2 |
|---|---|---|
| 4 pytest | 13:32 (4089 Tests) | 15:17 (4142 Tests) |
| 5 `dist\Natter` | – | 12:16, davon Pakete 6:03, Signieren 4:41 |
| 8 Installer | etwa 11:30 | 8:12 |
| gesamt | 42,2 min | 36,7 min |

Das Signieren dauerte länger als sonst, weil der Zwischenspeicher zum
ersten Mal gefüllt wurde (375 Einträge). Die Mehrkern-Kompression war im
Bau langsamer als getrennt gemessen; möglich ist, dass der Virenscanner
die frisch geschriebenen Dateien beim ersten Lesen prüft, nachgewiesen
ist es nicht. Der erste Versuch brach in Schritt 4 ab: ein älterer Test
fing die pip-Aufrufe noch auf dem alten Weg ab. Vor dem Start waren
nur die Bau-Tests gelaufen, nicht die ganze Suite.

### 0.3.1 – 21. September 2026

`Natter-Setup.exe`, 276 MB, 42,2 Minuten, elf Schritte. Erstmals jede
Binärdatei signiert (377, 0,28 s je Datei). Der erste Bauversuch
scheiterte an der Rauchprobe: auf dem Baurechner war die App-Steuerung
an, und sie wies die frisch signierten Dateien ab. Daraus ist die
Messung in Abschnitt 7.6 entstanden. Auf dem Baurechner ist die
App-Steuerung seitdem aus. Schritt 10 meldete im ersten Lauf 29 341
Dateien ohne Signatur: zusammen mit `-LiteralPath` ignoriert PowerShell
den Schalter `-Include` ohne Meldung und liefert jede Datei.

### 0.3.0 – 20. September 2026

275,3 MB, beide Signaturen `Valid`, 29,4 Minuten, davon 15,6 für 4054
Tests. Vollständig entfernt und neu installiert: 30 161 Dateien,
1 202 MB. Nachgesehen in der Installation: Integritätsprüfung sauber,
Fenster nach 2,6 s, „Quelltext als PDF" schreibt ein PDF.

Aufgedeckt: die Versionsnummer stand an drei Stellen, geprüft wurden
zwei. Windows zeigte 0.3.0, das Ladebild 0.2.1. Beim Beheben schrieb
ein Testlauf `1.0.0` in die eingecheckte `ide/main.py`, weil das Skript
die dritte Datei schon kannte und die Testabsicherung noch nicht; eine
Warnung im Docstring hatte das nicht aufgehalten. Seitdem lenkt eine
autouse-Fixture die Pfade um.

### 0.2.0 – 20. September 2026

275,4 MB, rund neun Minuten, davon dreieinhalb für 3690 Tests. Still
installiert ohne Administratorrechte, „Apps & Features" zeigt die
Fassung, Startmenü und `.natter`-Verknüpfung stehen.

Aufgedeckt: eine Prüfung suchte in `{app}\ide`, obwohl Natter unter
`python\Lib\site-packages` liegt – und zwei Kontrollen auf verbotene
Inhalte meldeten „bestanden", weil der Ordner gar nicht existierte. Die
Paketbeschreibung in `pyproject.toml` stand noch auf Lazarus. Die
Auslieferung nahm den ganzen `docs/`-Ordner mit statt der zwei
Hilfeseiten. Und ein Update ließ entfernte Dateien liegen, woraus
`[InstallDelete]` entstand (7.4).

### 0.1.0 – 20. September 2026

275,5 MB, Setup-Datei und `Natter.exe` signiert, Aussteller
`CN=Natter Codesignatur`.

---

## 9. Irrwege und was daraus folgt

Die Befunde, die beim nächsten Mal am meisten Zeit sparen. Ausführlich
stehen sie in den früheren Arbeitspaketen (Git-Historie) und in
[`erledigte_punkte.md`](erledigte_punkte.md).

**Ein grünes Testprotokoll belegt nicht, dass die Auslieferung
funktioniert.** Getestet wird der Entwicklungsbaum, ausgeliefert wird
`dist\Natter`. Beispiele: pip löste die Abhängigkeiten frisch gegen
PyPI auf, und in der Auslieferung lag pandas 3.0.6, getestet war 3.0.5.
Deshalb kommen die Versionen jetzt aus `uv.lock`, und Schritt 6 prüft
in der gebauten Python.

**Die Umgebung des Baurechners sickert in den Bau.** `PYTHONUSERBASE`
der Windows-Store-Python ließ die frisch ausgepackte Python die Pakete
des Baurechners als ihre eigenen sehen. pip meldete „Requirement
already satisfied" und gab 0 zurück; in der Auslieferung fehlten ein
Dutzend Pakete. Aufgefallen ist es erst beim Nachzählen.

**Eine Prüfung, die nicht fehlschlagen kann, prüft nichts.** Die
Integritätsprüfung erkannte eine Installation an `sys.frozen` und lief
nach M13 still gar nicht mehr. Kontrollen auf verbotene Inhalte zeigten
auf Ordner, die es nicht gab, und meldeten „bestanden".

**Was nicht verglichen wird, kann auseinanderlaufen.** Die
Versionsnummer an drei Stellen, die Liste der Endungen im Signierskript
und in Schritt 10, die Dateien der ZIP und ihre Beschreibung: überall
hält jetzt ein Test die beiden Seiten zusammen.

**Selbst signieren und die App-Steuerung** – siehe 7.6. Eine Messung
mit einer einzigen Datei reicht nicht; das Ereignisprotokoll
(`ValidatedSigningLevel`) sagt, ob Windows eine Signatur wirklich
anerkennt.

**Tests schreiben wirklich.** Der Designer schreibt jede Änderung in
die `.pfm` zurück, `_version_setzen()` in die Versionsdateien, der Bau
in `build\` und `dist\`. Wer so etwas testet, lenkt die Pfade vorher
um; die Absicherungen in `tests/conftest.py` und den Bau-Tests tun das
von sich aus.

**Ein Prozessbaum hängt an seinen Rohren.** Eine mit PyInstaller
gebaute Einzeldatei startet sich als Kindprozess nach. Das Kind erbt die
Ausgabe-Rohre, und `subprocess.run(…, timeout=…)` wartet nach dem
Abbruch endlos darauf, dass sie zugehen. Ausgabe in Dateien, beenden
mit `taskkill /PID <pid> /T /F`.

**Inno Setup löscht beim Update nichts.** Was in einer neuen Fassung
fehlt, bleibt liegen, bis `[InstallDelete]` es ausdrücklich entfernt.
Dasselbe gilt für Dateien, die erst nach der Installation entstehen
(Uninstaller, `.ruff_cache`): sie gehören nicht ins Manifest und werden
beim Deinstallieren nicht entfernt.

**PowerShell verschluckt Schalter.** `Get-ChildItem -LiteralPath …
-Include …` ignoriert `-Include` ohne Meldung. In Inno-Signierbefehlen
ist `$q` das Anführungszeichen; ein echtes `"` kommt wörtlich durch.

---

## 10. Risiken

| Risiko | Gegenmaßnahme |
|---|---|
| Rechner mit eingeschalteter App-Steuerung | in `ZUERST-LESEN.txt` und im Handbuch an erster Stelle; dauerhaft nur mit öffentlichem Zertifikat lösbar |
| Eigener Code in `u_*_design.py` geht verloren | die Datei ist als erzeugt gekennzeichnet und erscheint nicht im Projekt-Explorer; bearbeitet werden die `.pfm` im Designer und die Unit daneben |
| Schüler installieren Pakete, die die Umgebung stören | „Werkzeuge → Umgebung prüfen", das Manifest überwacht Natters eigene Dateien |
| Ausnahmen in Qt-Ereignissen gehen verloren | zentrale Ausnahmebehandlung in `pcl`, Fehlerfenster mit Protokoll unter `%APPDATA%\Natter` |
| Tastenkürzel kollidieren | das Aktionsregister vergibt sie zentral, ein Test prüft auf Doppelungen |
| Installationsgröße (1,2 GB) | Tcl/Tk entfernt, nur zwei Hilfeseiten ausgeliefert; Qt und die Rechenbibliotheken machen den Rest aus |
| Umfang wächst | neue Wünsche als Punkt in `offene_punkte.md`, nicht nebenbei |
