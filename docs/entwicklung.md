# Natter entwickeln und ausliefern

Dieses Dokument richtet sich an alle, die an Natter **arbeiten** - nicht
an die, die damit unterrichten. Wie Natter benutzt wird und was es kann,
steht in der [README](../README.md).

Hier steht alles, was den Bau betrifft: wie die Auslieferung entsteht,
wie das Repository aufgebaut ist, wie getestet wird und woran die
Umsetzung entlanggegangen ist. Es stand früher im Konzeptdokument; dort
stiftete es Verwirrung, weil es zwischen der Beschreibung der Funktionen
stand (Nutzer-Hinweis September 2026).

Der Bau selbst ist in drei Befehlen beschrieben - siehe
[`tools/signieren/README.md`](../tools/signieren/README.md) und
[`docs/arbeitspakete/M13.md`](arbeitspakete/M13.md).

## 17. Verteilung: Installer mit eigener Python-Installation

> Dieser Abschnitt beschrieb bis M13 einen portablen ZIP-Ordner. Der
> Nutzer hat sich im September 2026 für einen richtigen Installer
> entschieden: „Programm als Exe nur zum Download auf z. B. einer
> Website, man installiert die Exe." Die Überlegung zur venv (17.3) und
> die Signatur (17.8) gelten unverändert; was sich geändert hat, steht
> hier und ausführlich in
> [`docs/arbeitspakete/M13.md`](arbeitspakete/M13.md).

### 17.1 Prinzip

Natter bringt alles mit, was es braucht — eine vollwertige,
verschiebbare CPython samt Qt und den Rechenbibliotheken. Auf dem
Zielrechner muss nichts weiter installiert sein, und eine dort bereits
vorhandene Python-Installation bleibt unberührt.

Ausgeliefert wird das als gewöhnlicher Windows-Installer
(`Natter-Setup.exe`, rund 340 MB) mit den klassischen Seiten:
Willkommen, anzunehmende Lizenz, Hinweis zum Platzbedarf, Zielordner,
Startmenü-Ordner, Zusatzaufgaben, Zusammenfassung.

### 17.2 Ordneraufbau

```
<Installationsordner>/
  Natter.exe              schlanker Starter (Symbol, Versionsangabe, signiert)
  python/                 CPython 3.13, relokierbar, mit pip
    python.exe            für Konsolenprogramme
    pythonw.exe           für die IDE und für GUI-Programme
    Lib/site-packages/    ide, pcl, PySide6, pandas, numpy, … + pip + PyInstaller
                          dazu templates/, docs/, design/, schemas/, beispielprojekte/
  Lizenzen/               LGPL-3.0 und die Lizenztexte aller Bibliotheken
  manifest.json           signierte Prüfsummen (17.8)
```

Projekte der Schüler liegen außerhalb des Programmordners (Standard:
`Dokumente/Natter`, frei wählbar). Das ist keine Kosmetik: in einen
Programmordner unter `Program Files` darf ohne Administratorrechte
niemand schreiben.

### 17.3 Warum keine venv

Eine venv speichert absolute Pfade (u. a. in `pyvenv.cfg` und in
Startskripten). Nach dem Verschieben an einen anderen Ort funktioniert
sie nicht mehr. Deshalb kommt Python als **relokierbare
Standalone-Distribution** (python-build-standalone, dieselbe Quelle, aus
der auch `uv python install` bedient wird).

Die Trennung, die sonst zwei venvs leisten würden, gibt es seit M13
nicht mehr: IDE und Schülerprogramme teilen sich eine Umgebung. Dafür
riegelt der Starter sie nach außen ab — er entfernt `PYTHONPATH`,
`PYTHONHOME`, `PYTHONUSERBASE` und `VIRTUAL_ENV` aus der Umgebung und
schaltet das Benutzer-Paketverzeichnis ab. Ohne das kann eine fremde
Python-Umgebung auf einem Schulrechner Natter umwerfen, ohne dass dort
jemand etwas an Natter geändert hätte.

### 17.4 Größe

Die Installation belegt rund 1,4 GB, der Installer rund 340 MB. Die
größten Teile sind Qt (PySide6), pandas/matplotlib/scikit-learn und
PyInstaller.

### 17.5 Stolpersteine

| Problem | Ursache | Lösung |
|---|---|---|
| „Eine Anwendungssteuerungsrichtlinie hat diese Datei blockiert" | Smart App Control lehnt eine frisch gebaute, unsignierte Exe ab | Installer signieren (17.8) — gemessen: signiert läuft er durch |
| SmartScreen-Warnung | eine eigene Signatur ohne gekauftes Zertifikat hat keine Reputation | „Weitere Informationen" → „Trotzdem ausführen"; mit verteiltem Zertifikat entfällt sie |
| Installation bricht mit „Das System kann den angegebenen Pfad nicht finden" ab | ein sehr langer Zielordner reißt die Windows-Pfadgrenze | kurzen Zielordner wählen; die Vorgaben (`Program Files` bzw. `%LocalAppData%/Programs`) sind kurz genug |
| Nachinstallieren über „Pakete" schlägt fehl | systemweite Installation, kein Schreibrecht | entweder für den angemeldeten Benutzer installieren oder Natter als Administrator starten; die Meldung sagt das |

### 17.6 Exportierte Schülerprogramme

Siehe Abschnitt 16 der README: seit M14 kommt **eine einzige Exe**
heraus, in der auch die eigenen Unterordner des Projekts stecken. Das
ist die Gegenentscheidung zu 17.1: für Natter selbst ist der entpackte
Ordner richtig (1,4 GB entpacken sich nicht bei jedem Start), für ein
Schülerprogramm die eine Datei, die man verschicken kann.

### 17.7 Lizenz

**Natter** ist ein privates Projekt unter eigener Lizenz des Projektinhabers: Nutzung erlaubt, Weitergabe und Verbreitung nicht erlaubt.

Die enthaltenen Fremdkomponenten behalten ihre eigenen Lizenzen. Daraus folgen Regeln für die Auswahl:

| Regel | Umsetzung |
|---|---|
| Nur Komponenten mit freizügigen Lizenzen oder LGPL | PySide6/Qt (LGPLv3), Jedi, Ruff, libcst, debugpy, SQLAlchemy, openpyxl (MIT), pandas, numpy (BSD), matplotlib (PSF-basiert), Lucide (ISC), Codicons (CC BY 4.0) |
| Keine Qt-Module, die nur unter GPL stehen | **Qt Charts und Qt Data Visualization werden nicht verwendet** und aus dem Paket entfernt; die Chart-Komponente basiert auf matplotlib |
| Kein PyQt | PyQt steht unter GPL, PySide6 unter LGPL |
| LGPL-Pflichten für Qt/PySide6 | Qt-Bibliotheken bleiben austauschbare Dateien im Programmordner (kein statisches Einbinden), Lizenztexte und Quellenhinweise in `lizenzen/` und im Über-Dialog |
| Namensnennung | Codicons und weitere CC-BY-Inhalte im Über-Dialog nennen |
| Lizenzprüfung | ein Test listet alle Pakete im portablen Ordner mit Lizenz auf und schlägt bei GPL-Komponenten fehl |

Mit „Exe erstellen“ erzeugte Schülerprogramme sind davon unabhängig; der PyInstaller-Bootloader erlaubt jede Lizenz für das erzeugte Programm.

Hinweis: Diese Einordnung ist eine technische Planungsgrundlage und keine Rechtsberatung.

### 17.8 Signatur ohne gekauftes Zertifikat

Ziel: erkennen, ob Natter nach dem Build verändert wurde, und den Herausgeber anzeigen – ohne Kosten.

**Zwei Ebenen**

| Ebene | Umsetzung | Wirkung |
|---|---|---|
| Authenticode-Signatur mit eigenem Zertifikat | einmalig auf dem Laptop ein selbst erstelltes Zertifikat nur für den Verwendungszweck „Codesignatur“ anlegen (PowerShell `New-SelfSignedCertificate`); beim Build `Natter.exe` mit `Set-AuthenticodeSignature` signieren, mit kostenlosem Zeitstempeldienst | Windows zeigt unter Eigenschaften → Digitale Signaturen den Herausgeber; jede Veränderung der Exe macht die Signatur ungültig |
| Signiertes Prüfsummen-Manifest | beim Build SHA-256-Prüfsummen aller Programmdateien (ohne `benutzer/` und `pakete-zusatz/`) in `manifest.json`; das Manifest wird mit einem eigenen Ed25519-Schlüssel signiert, der öffentliche Schlüssel steckt im Starter | der Starter erkennt veränderte, fehlende oder fremde Dateien |

**Prüfungen beim Start**
- bei jedem Start: Signatur des Manifests und Prüfsummen der Kerndateien (Starter-Umfeld, Python, IDE-Code, `pcl`) – schnell
- beim ersten Start und über „Werkzeuge → Umgebung prüfen/reparieren“: alle Dateien
- bei Abweichung: verständliche Meldung („Natter wurde nach der Erstellung verändert: …“) mit Liste der betroffenen Dateien; Start nur nach Bestätigung

**Was die eigene Signatur nicht leistet**
- keine SmartScreen-Reputation; die Warnung wird durch „Zulassen“ vor dem Auspacken vermieden (17.5)
- auf fremden Rechnern erscheint der Herausgeber als nicht vertrauenswürdig, solange das eigene Zertifikat dort nicht importiert ist; auf eigenen Rechnern kann es im Benutzer-Zertifikatspeicher als vertrauenswürdig eingetragen werden

**Schlüsselschutz**
- privater Schlüssel des Zertifikats und Ed25519-Schlüssel nur auf dem Laptop, mit Passwort geschützt, niemals im Repository
- Sicherungskopie offline; bei Verlust neues Zertifikat und neuer Schlüssel

## 18. Repository-Struktur

```
natter/
  pcl/
    components/        standard.py, additional.py, common.py, chart.py, system.py, data_access.py, data_controls.py
    files.py           open_url, Pfad-/Arbeitsverzeichnis-Hilfen
    dataframe.py       StringGrid ↔ pandas, Chart-Datenübernahme
    theme/             tokens.json, Generatoren für QSS
    db/                Treiber-Adapter, Parameter-Übersetzung
    crt.py, dialogs.py, application.py, form_loader.py
  ide/
    shell/             Hauptfenster, Menüleiste, Werkzeugleisten, Aktivitätsleiste, Panels, Befehlspalette
    actions/           Aktionsregister (Menü, Werkzeugleiste, Tastenkürzel, Befehlspalette), Tastenkürzel-Editor
    palette/           Komponentenpalette mit Reitern
    designer/          Canvas, Auswahl, Anfasser, Raster, Undo
    inspector/         Objektinspektor, Eigenschaften-/Ereignis-Tabelle, Menü-Editor
    codegen/           design.py-Generator, libcst-Operationen
    debugger/          DAP-Client, Fehlerkatalog, Tabellenansicht für Variablen
    testrunner/        Test-Explorer (unittest)
    viewers/           CSV-Tabellenansicht, Bildvorschau, HTML-Vorschau, Markdown-Ansicht, Hilfeansicht
    database/          DB-Panel
    project/           Projektdatei, Vorlagen, Unit-Verwaltung, Sitzung
    lint/              Design-Prüfer
    diagramm/          Diagramm-Editor: Fenster, Formen, Verbindungen, Struktogramm-Blöcke, Entscheidungstabelle, Lineale, Minimap, Export
    env/               Paketordner, Paketverwaltung (pip), Umgebungsprüfung
    export/            PyInstaller-Pipeline für Schülerprojekte
    import_lfm/        .lfm-Parser und Zuordnung
    integritaet/       Prüfsummen-Manifest, Startprüfung
    run/               Programmstart, Prüfung vor dem Start
    assets/icons/      SVG-Symbole (Aktionen, Komponenten)
  tools/               Entwicklungswerkzeuge des Maintainers:
                       auslieferung_bauen.py (der ganze Weg zur Setup-Exe),
                       ide_paketieren.py, launcher.py (Natter.exe),
                       natter.iss (Inno Setup), signieren/, screenshot.py
  schemas/             pfm.schema.json, project.schema.json, pdiag.schema.json
  templates/           gui/, console/, gui_db/
  beispielprojekte/    die neun Projekte des Lehrgangs
  design/              tokens.json (Farben und Maße für IDE und Programme)
  tests/
```

> **Stand September 2026.** Der Baum oben ist der wirkliche, nicht der
> geplante. Drei Abweichungen gegenüber der ursprünglichen Planung sind
> Entscheidungen, keine Lücken: es gibt **kein `web/monaco/`** (der
> Editor ist ein `QPlainTextEdit` mit eigener Hervorhebung, siehe
> unten), **kein `launcher/`** und **kein `build/`** als Pakete – beides
> liegt in `tools/`, weil es Werkzeuge des Maintainers sind und nicht
> Teil des ausgelieferten `ide`-Pakets.

## 19. Teststrategie

Erst gegen virtuelle Abbildungen, zuletzt gegen echte Systeme.

| Ebene                | Vorgehen                                                                                                                                                                                                                                                                                    |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Runtime `pcl`        | pytest + pytest-qt headless (`QT_QPA_PLATFORM=offscreen`), jede Komponente: Eigenschaften lesen/schreiben, Live-Wirkung auf das Widget, Typprüfung, Tippfehler-Erkennung, Ereignisse                                                                                                        |
| Eigenschaften-System | für jede `Prop`: Standardwert, Editor-Zuordnung, Hilfetext vorhanden; Inspektor-Änderung = gleiche Wirkung wie Zuweisung im Code                                                                                                                                                            |
| Reines Python        | jedes Beispielprojekt läuft mit `python main.py` ohne IDE                                                                                                                                                                                                                                   |
| Optik                | Referenz-Screenshots aller Komponenten hell/dunkel, Pixelvergleich                                                                                                                                                                                                                          |
| Formate              | `.pfm` → `u_*_design.py` → Formular ergibt dieselben Eigenschaftswerte wie die `.pfm`; Schema-Validierung                                                                                                                                                                                   |
| Designer             | Command-/Undo-Tests ohne Fenster                                                                                                                                                                                                                                                            |
| Codegenerierung      | libcst-Einfügen/Umbenennen gegen Beispieldateien, Formatierung bleibt erhalten                                                                                                                                                                                                              |
| Debugger             | skriptgesteuerte DAP-Sitzungen gegen Beispielprogramme mit jedem Fehlertyp                                                                                                                                                                                                                  |
| Fehlermeldungen      | Katalogtests: jede Meldung enthält Ort + Erklärung, keine Codezeilen mit Lösungen                                                                                                                                                                                                           |
| Datenbank            | SQLite in-memory (MariaDB entfiel mit M15, Abschnitt 3)                                                                                                                                                                                                                     |
| Dateiarbeit          | Text-/CSV-/HTML-Dateien mit Umlauten schreiben und lesen; Arbeitsverzeichnis in IDE und Exe; `open_url` mit gemocktem Browser; Excel-CSV (Windows-1252, Semikolon, Dezimalkomma)                                                                                                            |
| Bilder               | alle Formate laden, `stretch`/`proportional`/`center`, Kopie nach `assets/`, Drag & Drop, Export enthält Bilder                                                                                                                                                                             |
| pandas/Chart         | `load_dataframe`/`to_dataframe` verlustfrei, Chart-Serien aus Listen und Serien, Referenz-Screenshots hell/dunkel                                                                                                                                                                           |
| Test-Explorer        | Beispiel-Testdateien mit bestandenen/fehlgeschlagenen Tests, Soll-/Ist-Anzeige                                                                                                                                                                                                              |
| Kann-Liste           | Tabelle aus Abschnitt 12 als Checkliste: je Zeile ein Beispielprojekt, das in der IDE läuft                                                                                                                                                                                                 |
| Design-Prüfer        | absichtlich fehlerhafte Formulare je Regel; Befunde nie als Fehler eingestuft                                                                                                                                                                                                               |
| Diagramm-Editor      | Formen/Verbindungen per Command-Tests ohne Fenster; Verbindungen folgen verschobenen Formen; Struktogramm-Blockbaum bleibt nach Einfügen/Löschen/Verschieben geschlossen; `.pdiag` speichern/laden verlustfrei; Referenz-Screenshots aller Formen in allen Stilvorlagen; SVG/PDF/PNG-Export |
| Aktionen und Menüs   | jede Aktion registriert, in einem Menü erreichbar, Kürzel ohne Konflikt; Datei-Aktionen (Neu, Öffnen, Speichern, Speichern unter, Wiederherstellen, Schließen) gegen temporäre Projektordner                                                                                                |
| Units                | Unit anlegen/einbinden/umbenennen passt Importe korrekt an; Kreisbezug wird erkannt; Beispielprojekt `u_pflanzen`/`u_garten` läuft                                                                                                                                                          |
| Umgebung             | Zusatzpaket installieren, Reparatur stellt Zustand wieder her; IDE-Pakete sind aus Schülerprogrammen nicht importierbar                                                                                                                                                                     |
| Portabilität         | ZIP auf frischem Windows ohne Python entpacken (Desktop, USB-Stick, Pfad mit Leer- und Sonderzeichen, langer Pfad), starten, Projekt anlegen, ausführen, Exe erstellen; Ordner verschieben und erneut starten                                                                               |
| Signatur | `Get-AuthenticodeSignature` meldet gültige Signatur; eine veränderte Datei im Paket wird vom Starter erkannt; manipuliertes Manifest wird abgelehnt |
| Lizenzen | alle Pakete im portablen Ordner mit Lizenz auflisten; Build schlägt bei GPL-Komponenten (z. B. Qt Charts) fehl |
| Lazarus-Import       | echte `.lfm`-Dateien der Übungsprojekte als Testfälle                                                                                                                                                                                                                                       |
| Ausführung           | Start GUI/Konsole als eigener Prozess; Konsolenprojekt mit per Pipe eingespeister `input()`-Eingabe; Stopp beendet Prozessbaum                                                                                                                                                              |
| Export | Build auf dem Windows-Laptop mit automatischem Probestart |
| Abnahme              | alle Übungsprojekte aus dem Kursmaterial auf einem echten Windows-Rechner                                                                                                                                                                                                                   |

## 20. Umsetzungsphasen

Jede Phase hat festgelegte Schnittstellen (Schemas, `Prop`-API, Aktionsregister, DAP) und eigene Tests, damit Arbeitspakete unabhängig voneinander umgesetzt werden können.

| Phase | Inhalt                                                                                                                                                                                                                                                                          | Abnahmekriterium                                                                                                                                                                  |
|-------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| M0 | Technische Machbarkeitsprüfungen (siehe 23.3), Repository, CI, Schemas, Design-Tokens, Design-Referenz | alle Prüfungen laufen auf einem Windows-Rechner ohne installiertes Python; Schema-Tests grün; Design-Referenz freigegeben |
| M1    | Eigenschaften-System (`Prop`/`Event`), Ereignisse, `pcl` Standard-, Additional- und Common-Controls-Komponenten inkl. Image/PaintBox/HtmlViewer, Datei-Methoden der Komponenten, `open_url`, Generator `.pfm` → `design.py`, Theme hell/dunkel, Dialoge, Timer, Sound           | Ampel, Würfelspiel, StringGrid-Übung laufen mit `python main.py`                                                                                                                  |
| M2    | IDE-Grundgerüst, Aktionsregister, alle Menüs und Werkzeugleisten, SVG-Symbole, Quelltexteditor, Themes, Explorer, Neu-Dialog, Units (Tabs, geteilte Ansicht, Einbinden), portable Laufzeit mit getrennten Paketordnern, Ausführung in eigenen Fenstern (GUI + Konsole), Tastenkürzel-Tab | Projekt aus M1 in der IDE öffnen, alle Datei-Menüfunktionen funktionieren, Projekt `u_pflanzen`/`u_garten` anlegen und starten, Konsolenprogramm mit `input()` im eigenen Fenster |
| M3    | Designer, Objektinspektor mit allen Editoren und Reitern, Komponentenpalette mit Reitern, Ereignis-Codegenerierung, Undo                                                                                                                                                        | Ampel komplett in der IDE erstellen, alle Eigenschaften nur über den Inspektor gesetzt                                                                                            |
| M4    | Ruff-Prüfung, Debugger inkl. Tabellenansicht, Fehlerkatalog (Wo/Was/Prüfe), Test-Explorer                                                                                                                                                                                       | Fehlerbeispiele liefern korrekte Meldungen, Breakpoints/Step funktionieren, Tests mit Soll/Ist-Anzeige                                                                            |
| M5    | SQLdb- und Data-Control-Komponenten, DB-Panel mit CSV-Import/-Export, pandas-Anbindung, Chart, CSV-/Bild-/HTML-Ansichten in der IDE                                                                                                                                             | Kontoverwaltung mit SQLite; CSV-Auswertung mit pandas in StringGrid und Chart; Würfelspiel-Highscore als HTML im Browser                                              |
| M6    | Konsolen-Feinschliff, `pcl.crt`                                                                                                                                                                                                                                                 | Konsolen- und CRT-Übungen aus dem Kursmaterial laufen                                                                                                                             |
| M7    | Design-Prüfer, Paketverwaltung                                                                                                                                                                                                                                                  | alle Prüfregeln erkennen ihre Testformulare; Paket über das Menü installierbar                                                                                                    |
| M8 | `.lfm`-Import, Exe-Export, portables ZIP-Paket mit Starter, Prüfsummen-Manifest und Signatur | Lazarus-Übungsprojekt importieren, fertigstellen, als Exe starten; ZIP auf einem Rechner ohne Python entpacken und vollständig nutzen; veränderte Datei wird erkannt |
| M9    | Diagramm-Editor: Fenster, Palette, Klassendiagramm, Struktogramm, Entscheidungstabelle; danach Use-Case, Aktivität, Zustand, Sequenz; Stilvorlagen, Export, Druck                                                                                                               | UML-Klassendiagramm TAmpel, Struktogramm `ampel_zeichnen` und Entscheidungstabelle der Ampel von Hand erstellen und als PDF exportieren                                           |

## 21. Risiken

| Risiko                                                  | Gegenmaßnahme                                                                                    |
|---------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| ~~Monaco-Integration in Qt aufwendig~~ **eingetreten**  | Statt Monaco ein `QPlainTextEdit` mit eigener, regelbasierter Python-Hervorhebung in den Farben von VS Code. Kostet keine 100 MB QtWebEngine und reicht für den Unterricht; Jedi liefert die Vervollständigung unabhängig davon |
| Designer-Komplexität (Undo, Mehrfachauswahl, Anker)     | Command-Pattern von Anfang an, Designer rendert echte `pcl`-Komponenten                          |
| Ausnahmen in Qt-Handlern gehen verloren                 | zentrale Ausnahmebehandlung in `pcl` ab M1                                                       |
| Eigener Code im erzeugten `design.py` geht verloren     | Datei klar gekennzeichnet, Editor zeigt sie schreibgeschützt an                                  |
| Schülerpakete beschädigen die Umgebung                  | getrennte Paketordner, Reparaturfunktion                                                         |
| Portabler Ordner sehr groß                              | Größe nach erstem Build messen, doppelte Teile vermeiden                                         |
| Tastenkürzel kollidieren untereinander                  | Aktionsregister leitet Kürzel zentral, Konfliktprüfung im Test                                   |
| Virenscanner blockieren Exes                            | Ordner-Export als Standard                                                                       |
| Installationsgröße                                      | akzeptiert; WebEngine nur einmal gebündelt                                                       |
| Diagramm-Editor: Linienführung und Andocken aufwendig   | zuerst gerade und rechtwinklige Linien mit manuellen Knickpunkten, keine automatische Wegfindung |
| Umfang wächst unkontrolliert                            | MVP strikt an den Übungsprojekten ausrichten                                                     |

## 22. Offene Fragen

Entschieden: Name „Natter“, Monaco als Editor, Ausführung in eigenen Fenstern, reines Python, Formulare als erzeugter Python-Code, Menüs/Werkzeugleisten/Palette wie Lazarus mit SVG-Symbolen, Units mit Tabs und geteilter Ansicht, Tastenkürzel wie VS Code mit Übersichts-Tab, Python 3.13 portabel ohne Installation (ZIP auspacken und starten), Namenskonvention nur als Hinweis, nur Deutsch, keine KI in der IDE, Diagramm-Editor in eigenem Fenster nur zum manuellen Zeichnen, Fehlermeldungen immer mit Wo/Was/Prüfe ohne abgestufte Hilfen, private Lizenz (Nutzung ja, Weitergabe nein), Repository und Build auf dem Windows-Laptop durch den Projektinhaber, Signatur mit eigenem Zertifikat und signiertem Prüfsummen-Manifest ohne Kosten, Schulrechner unkritisch.

**Noch offen:** keine.

## 23. Voraussetzungen für den Entwicklungsstart

### 23.1 Material, das vorliegen muss

| Material | Zweck |
|---|---|
| Lazarus-Projekte der Übungsaufgaben (`.lfm`, `.pas`, Bilder, Sounds) | Testfälle für `.lfm`-Import und Abnahme (Ampel, Würfelspiel, Kontoverwaltung …) |
| Beispiel-CSV-Dateien, auch aus Excel exportiert | Tests für CSV-Ansicht, Zeichensatz- und Trennzeichen-Erkennung, pandas |
| Beispiel-Datenbank (SQL-Dump aus dem Unterricht) | Tests für SQLdb-Komponenten und Datenbank-Panel |
| Beispiel-Diagramme (DIA-Dateien, Struktogramme als Bild) | Referenz für Formen und Darstellung im Diagramm-Editor |

### 23.2 Festlegungen, die vor dem Code geschrieben werden

Diese Dokumente sind die verbindlichen Schnittstellen zwischen den Arbeitspaketen. Ohne sie bauen parallel arbeitende Agenten nicht zueinander passende Teile.

| Dokument | Inhalt |
|---|---|
| `AGENTS.md` | Regeln für alle Beiträge: Python 3.13, Typannotationen, Ruff-Formatierung, pytest, Tests zuerst headless, alle sichtbaren Texte deutsch, keine Änderung erzeugter Dateien, Definition of Done je Arbeitspaket |
| `schemas/pfm.schema.json`, `project.schema.json`, `pdiag.schema.json` | Dateiformate mit Versionsnummer |
| `docs/komponenten.md` | alle Komponenten mit jeder Eigenschaft (Name, Typ, Standardwert, Kategorie, deutscher Hilfetext) und jedem Ereignis inkl. Signatur |
| `docs/aktionen.md` | alle Aktionen mit ID, deutschem Namen, Menüposition, Werkzeugleiste, Tastenkürzel, Bereich, Symbolname |
| `design/tokens.json` | Farben, Abstände, Radien, Schriften für hell/dunkel und die Diagramm-Stilvorlagen |
| `design/referenz/` | freigegebene Design-Referenz: Hauptfenster hell/dunkel, Objektinspektor, Designer mit Formular, Komponentenpalette, aufgeklapptes Menü, angehaltener Debugger, Fehlermeldung, Diagramm-Editor, Beispiel-Schülerprogramm; Vergleichsbasis für Screenshot-Tests |
| `design/icons.md` | alle benötigten Symbole (Aktionen, Komponenten, Diagrammformen) mit Stilregeln |
| `docs/fehlerkatalog.yaml` | Format und erste Einträge des Fehlerkatalogs mit den Texten für „Was“ und „Prüfe“ |
| `docs/arbeitspakete/` | je Phase die Arbeitspakete mit Abhängigkeiten, Schnittstellen und Abnahmetests |

### 23.3 Technische Machbarkeitsprüfungen (Phase M0)

Die riskantesten Teile werden vor M1 als kleine Wegwerf-Prototypen auf Windows geprüft:

| Nr. | Prüfung | Erfolgskriterium |
|---|---|---|
| S1 | Portables Python 3.13 (Standalone-Distribution) + PySide6 inkl. WebEngine aus einem Ordner auf dem Desktop | Fenster mit WebEngine startet; Ordner verschieben und erneut starten funktioniert |
| S2 | Monaco in `QWebEngineView` mit `QWebChannel` und Jedi-Vervollständigung, offline | Vervollständigung, Fehlermarkierung und Theme-Wechsel ohne Internet |
| S3 | debugpy: GUI-Programm als eigener Prozess und Konsolenprogramm im eigenen Konsolenfenster | Breakpoint hält an, Variablen lesbar, `input()` im Konsolenfenster funktioniert |
| S4 | Getrennte Paketordner statt venv | Schülerprogramm kann IDE-Pakete nicht importieren; Zusatzpaket per pip landet in `pakete-zusatz` |
| S5 | PyInstaller aus dem portablen Python mit PySide6 und pandas | erzeugte Exe läuft auf einem Rechner ohne Python |
| S6 | Starter `Natter.exe` mit Signatur und Manifest | erkennt blockierte Dateien, OneDrive-Pfad, zu lange Pfade und veränderte Dateien; Exe mit eigenem Zertifikat signiert; kein Alarm des Windows-Virenscanners |
| S7 | `QGraphicsView`: zwei Formen mit andockender, rechtwinkliger Verbindung | Verbindung folgt beim Verschieben ohne Flackern |

Fällt eine Prüfung durch, wird die betroffene Entscheidung im Konzept angepasst (z. B. QScintilla statt Monaco), bevor M1 beginnt.

### 23.4 Entwicklungsumgebung

| Punkt | Festlegung |
|---|---|
| Plattform der Agenten | Linux reicht für den Großteil (Qt headless, Tests); Windows ist zwingend für Starter, Konsolenfenster, Exe-Export, Portabilität und Referenz-Screenshots |
| Versionen | beim Start aktuelle stabile Versionen von Python 3.13, PySide6, Monaco, debugpy und PyInstaller festlegen und in einer Sperrdatei fixieren |
| Build und Windows-Tests | auf dem Windows-Laptop (vom Projektinhaber eingerichtet); Ruff und pytest headless zusätzlich unter Linux möglich |
| Arbeitsweise | kleine Arbeitspakete mit eigenen Tests; Merge nur mit grünen Tests und passender Design-Referenz |
