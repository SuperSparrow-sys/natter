# Ablaufplan

Schritt-für-Schritt-Checkliste für die Umsetzung, damit nichts vergessen
wird. Konkretisiert konzept-natter.md, Abschnitt 20 (Umsetzungsphasen) und
23 (Voraussetzungen).

**Funktionsweise:** jeder Punkt ist einzeln abhakbar (`[ ]` → `[x]`).
Nahe Schritte (Rest von M0, ganz M1) sind kleinteilig. Spätere Phasen
(M2–M9) stehen hier vorerst nur als vollständige Stichwortliste aus
Abschnitt 20, damit nichts fehlt – sie werden jeweils kurz vor Beginn in
einer eigenen `docs/arbeitspakete/M<n>.md` so kleinteilig aufgeschlüsselt
wie M1 hier. Reihenfolge = Abhängigkeiten.

Aktueller Punkt, an dem wir stehen, steht immer ganz oben in diesem
Dokument (Abschnitt „Wo wir stehen“).

## Wo wir stehen

→ **M1, Schritt 4: `.pfm` → `u_*_design.py`-Generator** (siehe unten)

## Referenzmaterial

- [x] Lazarus-Übungsprojekte in `referenz/lazarus/` vorhanden (18 Projekte,
  mehr als die 8 MVP-Projekte aus Abschnitt 1) – nur Quelltext (`.pas`,
  `.lfm`, `.lpi`, `.lpr`) und Bilder committet; `lib/`, `backup/`, `*.exe`,
  `*.res`, `*.lps` sind über `.gitignore` ausgeschlossen (Kompilate/
  Sessiondaten, ungefiltert ca. 490 MB, nicht nötig)
- [ ] Zuordnungstabelle Projekt → benötigte `pcl`-Komponenten/Konzepte
  pflegen, siehe Tabelle unten (wird während M1 befüllt)
- [ ] optional, nicht blockierend: separate Excel-exportierte CSV-Beispiele,
  SQL-Dump einer Beispieldatenbank, Beispiel-Diagramme (DIA-Dateien oder
  Fotos von Struktogrammen) – erst relevant für M5 bzw. M9

### Referenzprojekte in `referenz/lazarus/`

| Ordner | Deckt ab (grob) |
|---|---|
| `a_GUI_Komponenten` | Grundkomponenten |
| `b_schneefigur` | Zeichnen (Shape/Canvas) |
| `c_rechenen`, `e_rechenen` | Eingabe/Berechnung, Edit |
| `d_Cookie_klicker` | Bilder, Timer/Klicks |
| `f_Pizza` | RadioGroup/CheckBox-artige Auswahl |
| `g_StringGrid` | StringGrid |
| `h_LinearesucheTabelle` | Such-/Tabellenalgorithmen |
| `i_KleinesEinmaleins` | Schleifen/Auswertung |
| `j_komplexeLeistung` | komplexere Logik |
| `k_Ampel` | Form, Button, Label, Shape – **Startprojekt für M1** |
| `l_Pet` | Bilder/Zustände (InfSys-Pet) |
| `m_Gaestebuch` | Textdatei-Ein-/Ausgabe |
| `n_abstrakte_Klasse` | abstrakte Klassen |
| `n_konto` | Kontoverwaltung, vermutlich Datenbank |
| `o_vererbung` | Vererbung |
| `p_Monster` | Klassen/Objekte |
| `q_Würfelspiel` | Zufallszahlen, Highscore-Datei |
| `r_Dateibearbeitung` | Dateiarbeit |

Wird während M1 verfeinert (genaue Komponentenliste je Projekt), sobald die
`.lfm`-Dateien systematisch ausgewertet werden.

## Zurückgestellt (nicht blockierend)

- [ ] `prototypes/s1`–`s7` (Machbarkeitsprüfungen, Abschnitt 23.3): Code
  liegt bereit (siehe `prototypes/README.md`), wird aber erst kurz vor dem
  jeweils betroffenen Meilenstein tatsächlich ausgeführt statt jetzt:
  S1/S4 vor M2, S2 vor M2, S3 vor M4, S5/S6 vor M8, S7 vor M9. Blockiert
  M1 nicht.
- [ ] `design/referenz/` (freigegebene UI-Mockups): setzt erste
  Bildschirmentwürfe voraus, folgt mit M2/M3.

## M0 – Repository, CI, Schemas, Design-Tokens (Rest)

- [x] Repository, `pyproject.toml`, `AGENTS.md`, `LICENSE`, `.gitignore`
- [x] Schemas (`pfm`, `project`-Entwurf, `pdiag`) + Tests
- [x] `design/tokens.json` (Entwurf)
- [x] CI (Ruff + pytest)
- [x] Referenzmaterial eingespielt
- [ ] `schemas/project.schema.json` gegen `k_Ampel` grob abgleichen (Name,
  Typ, Hauptformular sinnvoll abgebildet?) – kleine Korrektur bei Bedarf

## M1 – pcl-Kern: Eigenschaften-System und erste Komponenten

Abnahmekriterium laut Konzept: Ampel, Würfelspiel, StringGrid-Übung laufen
mit `python main.py`. Hier in einzelne, unabhängig testbare Schritte
zerlegt, jeder Schritt für sich mit `pytest` abgesichert.

### 1. Eigenschaften-System (ohne Qt, reine Python-Logik) — erledigt

- [x] `pcl/properties.py`: `Prop`-Deskriptor (Typ, Standardwert, Kategorie,
  `doc`), `Event`-Deskriptor
- [x] Typprüfung beim Setzen, Fehlertext exakt wie im Fehlerkatalog
  (`docs/fehlerkatalog.yaml`, Eintrag `pcl_property_error`);
  `pcl/errors.py` mit `NatterPropertyError`/`NatterUnbekannteEigenschaftError`
- [x] unbekannte Eigenschaft (Tippfehler) löst Fehler aus statt still ein
  neues Attribut anzulegen (`Komponente.__setattr__`); eigene Attribute
  (`self.ampel = Ampel()`) bleiben über `neue_attribute_erlaubt = True`
  erlaubt (wird von `Form` in Schritt 2 gesetzt)
- [x] Tests (`tests/test_properties.py`, 14 Tests): Standardwert,
  Zuweisung/Lesen, Vererbung, Typprüfung (inkl. bool vs. int/float
  getrennt gehalten), Tippfehler-Erkennung, Event-Zuweisung, Sperre vs.
  `neue_attribute_erlaubt`, `eigenschaften()`/`ereignisse()`-Helfer für
  den späteren Objektinspektor

### 2. Anbindung an Qt — erledigt

- [x] `pcl/control.py`: `Control` als Basisklasse (Props `left`/`top`/
  `width`/`height`/`enabled`), verbindet `Prop`-Zugriff über den in Schritt
  1 ergänzten `_bei_prop_aenderung`-Hook mit dem zugehörigen `QWidget`
  (Setter ändert sofort das Widget)
- [x] `pcl/form.py`: `Form` (Props `caption`/`width`/`height`/`theme`,
  Event `on_create`), `create_components()`-Konvention wie im generierten
  Code (Abschnitt 4.3), `neue_attribute_erlaubt = True`
- [x] `pcl/application.py`: `Application.run(FormKlasse)`
- [x] Tests headless mit `QT_QPA_PLATFORM=offscreen`
  (`tests/test_control_form.py`, 9 Tests; `tests/conftest.py` mit
  session-weiter `QApplication`-Fixture)
- **Stolperstein festgehalten:** ein `QWidget` ganz ohne vorher erzeugte
  `QApplication` lässt den Prozess hart abstürzen (kein Python-Traceback,
  nur Exitcode). Deshalb erzeugt eine `autouse`-Fixture in
  `tests/conftest.py` immer zuerst eine `QApplication` für die gesamte
  Testsitzung.
- CI (`.github/workflows/ci.yml`) installiert dafür zusätzlich
  Qt-Systembibliotheken (`libegl1`, `libxkbcommon0` u. a.) auf dem
  Ubuntu-Runner

### 3. Erste Komponenten (reichen für `k_Ampel`) — erledigt

- [x] `pcl/components/standard.py`: `Button` (`caption`, Event `on_click`),
  `Label` (`caption`)
- [x] `pcl/components/additional.py`: `Shape` (`shape` = rectangle/circle,
  `brush.color` als aufklappbare Untereigenschaft, eigenes `QPainter`-
  Painting)
- [x] `Form`-Event `on_create` bereits in Schritt 2 umgesetzt,
  `Button`-Event `on_click` jetzt dazu
- [x] `pcl/__init__.py` exportiert `Application`, `Button`, `Control`,
  `Event`, `Form`, `Label`, `Prop`, `Shape` (Abschnitt 4.3:
  `from pcl import Form, Button, Shape`)
- [x] Tests (`tests/test_components.py`, 10 Tests, headless): Standardwerte,
  Live-Wirkung, echter Klick löst `on_click` mit `sender` aus, Typprüfung
  von `brush.color`, Tippfehlerschutz
- [x] `docs/komponenten.md` für `Form`, `Button`, `Label`, `Shape` ausgefüllt

### 4. `.pfm` → `u_*_design.py`

- [ ] Generator: liest `.pfm` (Abschnitt 4.2), erzeugt
  `u_*_design.py` im Format aus Abschnitt 4.3 (Kopfzeile „nicht
  bearbeiten“)
- [ ] gegen `schemas/pfm.schema.json` validiert
- [ ] Test: `.pfm` → generierter Code → Formular liefert dieselben
  Eigenschaftswerte wie die `.pfm`

### 5. Ampel nachbauen (erstes Abnahmeprojekt)

- [ ] `.pfm` von Hand aus `referenz/lazarus/k_Ampel/u_main.lfm` ableiten
  (Buttons `b_einschalten`/`b_wechseln`/`b_Auschalten`, Label, drei
  `Shape`-Ampellichter)
- [ ] `u_main_design.py` generieren
- [ ] `u_ampel.py` (eigene Klasse, reines Python, siehe
  `referenz/lazarus/k_Ampel/u_tampel.pas` als fachliche Vorlage)
- [ ] `u_main.py` (Event-Handler) + `main.py`
- [ ] läuft mit `python main.py`, Ampel schaltet sichtbar um

### 6. Restliche Standard-/Additional-/Common-Komponenten

- [ ] `Edit`, `CheckBox`, `RadioButton`, `RadioGroup`, `Memo`, `ComboBox`,
  `ListBox`, `ScrollBar`, `GroupBox`, `Panel`, `MainMenu`, `PopupMenu`
- [ ] `StringGrid`, `Image`, `SpinEdit`, `FloatSpinEdit`, `MaskEdit`,
  `PaintBox` (inkl. Canvas: `line_to`, `rectangle`, `ellipse`, `text_out`),
  `HtmlViewer`
- [ ] `TrackBar`, `ProgressBar`, `DateEdit`, `TimeEdit`, `Calendar`
- [ ] Dialoge: `show_message`, `input_box`, `message_dlg`, `OpenDialog`,
  `SaveDialog`, `SelectDirectoryDialog`, `ColorDialog`, `FontDialog`
- [ ] `Timer`, `Sound`
- [ ] Datei-Methoden der Komponenten (`lines.load_from_file` usw.,
  Abschnitt 11.2), `open_url`

### 7. Theme

- [ ] `design/tokens.json` → QSS-Generator für `pcl`-Programme, hell/dunkel,
  `theme`-Eigenschaft des Formulars (`system`/`light`/`dark`)

### 8. Zweites/drittes Abnahmeprojekt

- [ ] Würfelspiel mit Highscore (`referenz/lazarus/q_Würfelspiel` als
  Vorlage) läuft mit `python main.py`
- [ ] StringGrid-Übung (`referenz/lazarus/g_StringGrid` als Vorlage) läuft
  mit `python main.py`

### 9. Dokumentation nachziehen

- [ ] `docs/komponenten.md` für jede in M1 entstandene Komponente ausfüllen
  (Pflicht laut `AGENTS.md`, Definition of Done)

## M2 – IDE-Grundgerüst (Stichworte aus Abschnitt 20, Details folgen in `docs/arbeitspakete/M2.md`)

- [ ] Aktionsregister, alle Menüs/Werkzeugleisten, SVG-Symbole
- [ ] Monaco-Einbindung, Themes
- [ ] Explorer, Neu-Dialog
- [ ] Units (Tabs, geteilte Ansicht, Einbinden)
- [ ] portable Laufzeit mit getrennten Paketordnern
- [ ] Ausführung in eigenen Fenstern (GUI + Konsole)
- [ ] Tastenkürzel-Tab
- [ ] Abnahme: Projekt aus M1 in der IDE öffnen, alle Datei-Menüfunktionen,
  `u_pflanzen`/`u_garten`-Projekt anlegen und starten, Konsolenprogramm mit
  `input()` im eigenen Fenster

## M3 – Designer, Objektinspektor

- [ ] Designer (Canvas, Auswahl, Anfasser, Raster, Undo)
- [ ] Objektinspektor mit allen Editoren/Reitern
- [ ] Komponentenpalette mit Reitern
- [ ] Ereignis-Codegenerierung (Doppelklick → Methode, libcst)
- [ ] Abnahme: Ampel komplett in der IDE erstellen, alle Eigenschaften nur
  über den Inspektor gesetzt

## M4 – Debugger, Fehlerkatalog, Tests

- [ ] Ruff-Prüfung vor Start
- [ ] Debugger (DAP-Client auf debugpy) inkl. Tabellenansicht für Variablen
- [ ] Fehlerkatalog vollständig verdrahtet (Wo/Was/Prüfe)
- [ ] Test-Explorer
- [ ] Abnahme: Fehlerbeispiele liefern korrekte Meldungen,
  Breakpoints/Step funktionieren, Tests mit Soll/Ist-Anzeige

## M5 – Datenbank, pandas, Charts

- [ ] SQLdb- und Data-Control-Komponenten
- [ ] DB-Panel mit CSV-Import/-Export
- [ ] pandas-Anbindung, Chart-Komponente (matplotlib)
- [ ] CSV-/Bild-/HTML-Ansichten in der IDE
- [ ] Abnahme: Kontoverwaltung (`referenz/lazarus/n_konto`) mit
  MariaDB/SQLite, CSV-Auswertung mit pandas in StringGrid und Chart,
  Würfelspiel-Highscore als HTML im Browser

## M6 – Konsolen-Feinschliff

- [ ] `pcl.crt` (optionales Hilfsmodul für den Umstieg aus CRT-Unterricht)
- [ ] Abnahme: Konsolen-/CRT-Übungen laufen

## M7 – Design-Prüfer, Paketverwaltung

- [ ] Design-Prüfer (regelbasiert, Abschnitt 14)
- [ ] Paketverwaltung (pip über die IDE)
- [ ] Abnahme: alle Prüfregeln erkennen ihre Testformulare, Paket über das
  Menü installierbar

## M8 – Lazarus-Import, Exe-Export, Verteilung

- [ ] `.lfm`-Import (Parser, Zuordnungstabelle, Abschnitt 15) – jetzt mit
  echten `.lfm`-Dateien aus `referenz/lazarus/` testbar
- [ ] Exe-Export (PyInstaller-Pipeline)
- [ ] portables ZIP-Paket mit Starter, Prüfsummen-Manifest, Signatur
  (S5/S6 aus `prototypes/` hier tatsächlich einsetzen)
- [ ] Abnahme: ein Lazarus-Übungsprojekt importieren, fertigstellen, als
  Exe starten; ZIP auf Rechner ohne Python entpacken und vollständig
  nutzen; veränderte Datei wird erkannt

## M9 – Diagramm-Editor

- [ ] Fenster, Palette, Klassendiagramm, Struktogramm, Entscheidungstabelle
- [ ] danach Use-Case, Aktivität, Zustand, Sequenz
- [ ] Stilvorlagen, Export, Druck
- [ ] Abnahme: UML-Klassendiagramm `TAmpel`, Struktogramm
  `ampel_zeichnen` und Entscheidungstabelle der Ampel von Hand erstellen
  und als PDF exportieren

## Nächster konkreter Schritt

**M1, Schritt 1:** `pcl/properties.py` mit `Prop`/`Event`-Kern anlegen,
reine Python-Logik ohne Qt, mit pytest abgesichert (siehe oben).
