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

→ **M8, Schritt 1: `.lfm`-Parser** – kleinteilig aufgeschlüsselt in
[`docs/arbeitspakete/M8.md`](arbeitspakete/M8.md) (wie M1–M7), aber mit
einer wichtigen Einschränkung: Exe-Export, portables ZIP, Starter/
Launcher und Signatur (Abschnitt 16, 17) brauchen zwingend einen echten
Windows-Rechner und werden hier nicht simuliert – bearbeitet wird der
`.lfm`-Parser und die Klassen-/Eigenschaftszuordnung nach `.pfm`, reine
Logik, testbar gegen die echten `referenz/lazarus/*.lfm`-Dateien. M1–M7
sind
funktional abgeschlossen (M3-Abnahme bestanden: Ampel vollständig über
Designer/Inspektor/Palette nachgebaut, siehe
[`docs/arbeitspakete/M3.md`](arbeitspakete/M3.md), Schritt 8; M4-Abnahme
bestanden: Fehlerkatalog-Beispiele, Ampel-Breakpoint mit Variablenanzeige,
Test-Explorer mit Soll-/Ist-Anzeige, siehe
[`docs/arbeitspakete/M4.md`](arbeitspakete/M4.md), Schritt 8; M5-Abnahme
bestanden: Kontoverwaltung mit echter SQLite-Persistenz, CSV-Auswertung
mit pandas in StringGrid und Chart, Würfelspiel-Highscore als HTML im
Browser, siehe [`docs/arbeitspakete/M5.md`](arbeitspakete/M5.md), Schritt
9 (MariaDB-Verbindungstest gegen eine echte Instanz bleibt
zurückgestellt); M6-Abnahme bestanden: `pcl.crt` mit ANSI-
Cursorsteuerung/-Farben, Tastatureingabe über `msvcrt`, Piepton über
`winsound`, siehe [`docs/arbeitspakete/M6.md`](arbeitspakete/M6.md),
Schritt 2; M7-Abnahme bestanden: Design-Prüfer (14 Regeln über
Geometrie/Lesbarkeit/Konsistenz/Bedienbarkeit/Namenskonvention,
Größenänderung/Skalierung zurückgestellt) und Paketverwaltung über `pip`,
siehe [`docs/arbeitspakete/M7.md`](arbeitspakete/M7.md), Schritt 4 – 532
Tests grün); die „Zurückgestellt“-Punkte aus M2–M7 werden bei Bedarf
zwischen M8-Schritten nachgeholt.

**Sichtbar und bedienbar:** `uv run python -m ide` öffnet die IDE;
„Projekt öffnen …“ → `beispielprojekte/Ampel/ampel.natter` → Doppelklick
auf `u_main` im Explorer öffnet den echten Formular-Designer als Tab;
Klick auf ein Ampellicht/einen Button wählt es aus und füllt den
Objektinspektor rechts; Eigenschaften dort ändern wirkt sofort auf die
Anzeige. Im Designer selbst: Ziehen mit der Maus verschiebt, acht
Größenanfasser (Ecken + Kantenmitten, wie in Lazarus) an den Ecken/Kanten
der ausgewählten Komponente lassen sich mit der Maus zur Größenänderung
ziehen, Pfeiltasten/Alt+Pfeil/Umschalt+Pfeil bewegen bzw. skalieren
rasterweise, Entf löscht,
Strg+D dupliziert, Doppelklick auf der Palette platziert eine neue
Komponente mittig, Doppelklick auf einer Komponente oder dem
Formularhintergrund erzeugt (per `libcst`) ihre Standard-Ereignismethode
in der `.py`-Unit und verknüpft sie, Strg+Z/Strg+Umschalt+Z machen
rückgängig/wiederholen – jede Änderung wird automatisch in die `.pfm`
zurückgeschrieben. „Start → Starten ohne Debugger“ (Strg+F5) prüft das
Projekt zuerst mit Ruff (Syntaxfehler, unbekannte Namen, ungenutzte
Importe/Variablen); bei Funden erscheinen sie im Panel „Meldungen“ statt
zu starten, sonst startet das Programm als eigenes Fenster. „Start →
Starten“ (F5) startet stattdessen mit echtem Debugger: ein per
Rand-Klick im Editor gesetzter Breakpoint hält den laufenden Prozess an,
Panel „Aufrufstapel“ zeigt den Aufrufstapel und „Variablen“ die lokalen
Werte an der Haltestelle, Pause/Fortsetzen/Stopp/Einzelschritt/
Prozedurschritt/bis Rücksprung sind eigene Aktionen im Start-Menü. Eine
unbehandelte Ausnahme im laufenden Programm zeigt automatisch die
Wo/Was/Prüfe-Fehlerkatalog-Meldung im Panel „Meldungen“ und springt im
Editor zur Fehlerzeile. „Projekt → Alle Tests ausführen“ entdeckt
`test_*.py`-Dateien und zeigt sie im Panel „Tests“ als Baum mit
bestanden/fehlgeschlagen/Fehler-Status; Doppelklick auf einen einzelnen
Test, eine Klasse oder eine ganze Datei führt genau diesen Teil erneut
aus, fehlgeschlagene `assertEqual`-Vergleiche zeigen Soll/Ist als
Tooltip, „Testergebnisse als HTML exportieren“ schreibt ein Protokoll.
Programme können jetzt `SQLite3Connection`/`MySQLConnection`,
`SQLQuery`/`SQLTransaction`/`DataSource` sowie die daran gebundenen
`DBGrid`/`DBEdit`/`DBText`/`DBNavigator`/`DBComboBox` verwenden;
`StringGrid.load_dataframe()`/`.to_dataframe()` und `SQLQuery.to_dataframe()`
verbinden Tabellen mit `pandas`, `Chart` zeigt Balken-/Linien-/Kreis-/
Punktdiagramme über eingebettetes `matplotlib`. In der IDE öffnet ein
Doppelklick im Explorer `.csv`-Dateien als sortierbare/filterbare
Tabelle, Bilder als skalierte Vorschau mit Abmessungen und `.html`-
Dateien als automatisch aktualisierende Vorschau mit „Im Browser
öffnen“; das neue Dock „Datenbank“ verbindet sich mit SQLite/MySQL,
zeigt Tabellen/Spalten, führt SQL-Abfragen aus und importiert/exportiert
Tabellen als CSV bzw. SQL-Dump. „Werkzeuge → Design prüfen“ (und
automatisch nach jeder Designer-Änderung, abschaltbar) zeigt Hinweise/
Warnungen zu Geometrie, Lesbarkeit, Konsistenz, Bedienbarkeit und
Namenskonvention im Panel „Meldungen“; ein Klick auf einen Befund
markiert die betroffene Komponente im Designer. Das neue Menü „Pakete“
zeigt installierte Pakete, installiert ein neues per `pip` und
exportiert die Paketliste als `requirements.txt`.

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
  S1/S4 vor M2, S2 vor M2, S5/S6 vor M8, S7 vor M9. Blockiert M1 nicht.
  S3 (debugpy mit VS Code als DAP-Frontend) entfällt: der echte
  DAP-Client aus M4 wird gegen echtes `debugpy` automatisiert getestet
  (`docs/arbeitspakete/M4.md`, Schritt 3–5) – das prüft dieselbe Frage
  rigoroser und wiederholbar, ganz ohne VS Code.
- [ ] `design/referenz/` (freigegebene UI-Mockups): setzt erste
  Bildschirmentwürfe voraus, folgt mit M2/M3.
- [ ] **Visueller Feinschliff der IDE** (Nutzer-Feedback nach dem ersten
  echten Anschauen des Programms, September 2026): wirkt insgesamt noch
  zu farblos/grau. Sammelpunkt für alle folgenden Einzelschritte, jeweils
  eigene kleine Aufgabe statt einer großen:
  - [x] Fenster-/Taskleisten-Symbol (`ide/assets/icons/app.svg`)
  - [x] Werkzeugleiste mit Symbolen (Neu/Öffnen/Speichern/Projekt öffnen/
    Start), bisher nur diese fünf Aktionen
  - [x] Zeilennummern im Quelltexteditor (`ide/shell/quelltexteditor.py`)
  - [ ] Symbole (SVG) für Palette-Einträge und Komponentenbaum je
    Komponententyp (Button/Label/Edit/…, bisher nur Text)
  - [ ] Farbiges Theme/Akzentfarben über das ganze Programm konsequent
    angewendet (Docks, Reiter, Tabellen) statt nur im Designer-
    Auswahlrahmen; Referenz `design/tokens.json`
  - [ ] Syntax-Hervorhebung im Quelltexteditor (hängt an der Monaco-
    Entscheidung, siehe `prototypes/s2`)
  - [ ] Konsistentes Spacing/Ausrichtung in Objektinspektor, Explorer,
    Palette geprüft und ggf. nachgezogen
  - [ ] Icon für die spätere `.exe` und für `.natter`-Dateien im Windows-
    Explorer (Datei-Verknüpfung) – braucht den Packaging/Installer-
    Schritt aus M8, Icon-Quelle liegt schon als
    `ide/assets/icons/app.svg` bereit
- [x] **Eigenschaften-Abgleich mit Lazarus** (Nutzer-Frage „Habe ich die
  Attribute genau wie in Lazarus?“, September 2026): systematischer
  Abgleich aller `pcl`-`Prop`/`Event`-Namen gegen jede tatsächlich in
  `referenz/lazarus/*/unit1.lfm` verwendete Eigenschaft. Ergebnis: alle
  in den Referenzprojekten genutzten Komponententypen haben eine
  `pcl`-Entsprechung; vier echte Eigenschaftslücken gefunden und behoben:
  `Label.on_click` (Lazarus `TLabel.OnClick`, für Cookie-Klicker-artige
  Übungen), `Form.color`/`Edit.color` (Lazarus `Color`, z. B.
  `clSilver`/`clYellow` in `a_GUI_Komponenten`), `Edit.read_only`
  (Lazarus `ReadOnly`, `f_Pizza`), `Shape.shape = "rounded_rectangle"`
  (Lazarus `stRoundSquare`, `b_schneefigur`). Kleinere, unkritische Lücken
  zurückgestellt: `ScrollBar.page_size`, `StringGrid.fixed_cols`/
  `col_widths`, `Image.stretch`, `ListBox.item_height` – keine davon
  verhindert, dass ein Referenzprojekt läuft

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

### 4. `.pfm` → `u_*_design.py` — erledigt

- [x] `ide/codegen/design.py`: liest `.pfm` (Abschnitt 4.2), erzeugt
  `u_*_design.py` im Format aus Abschnitt 4.3 (Kopfzeile „nicht
  bearbeiten“, Typ-Annotationen der Kinder, sortierte `from pcl import
  ...`-Zeile)
- [x] validiert gegen `schemas/pfm.schema.json` (`jsonschema.validate`,
  jetzt Laufzeit-Abhängigkeit statt nur `dev`-Gruppe)
- [x] Test (`tests/test_design_codegen.py`, 7 Tests): ungültige `.pfm`
  abgelehnt, generierter Code importierbar, Formular liefert dieselben
  Eigenschaftswerte wie die `.pfm`, `on_create`/`on_click` korrekt
  verknüpft (echter Qt-Klick löst den generierten Handler-Aufruf aus)

### 5. Ampel nachbauen (erstes Abnahmeprojekt) — erledigt

- [x] `.pfm` von Hand aus `referenz/lazarus/k_Ampel/u_main.lfm` abgeleitet
  (Buttons `b_einschalten`/`b_wechseln`/`b_auschalten`, Label, Gehäuse-
  und drei Ampellicht-`Shape`s) → `beispielprojekte/Ampel/u_main.pfm`
- [x] `u_main_design.py` mit dem Generator erzeugt (nicht von Hand)
- [x] `u_ampel.py`: `Ampel`-Klasse, reines Python, Zustandsautomat 1↔2↔3↔4
  originalgetreu aus `referenz/lazarus/k_Ampel/u_tampel.pas` übernommen
- [x] `u_main.py` (Event-Handler, Farblogik aus `u_main.pas`
  originalgetreu übernommen) + `main.py`
- [x] Abnahme (`tests/test_beispiel_ampel.py`, 4 Tests): Startzustand
  Grün, `Wechseln` durchläuft Grün→Gelb→Rot→Gelb→Grün, `Auschalten`
  löscht alle Lichter, `Einschalten` zeigt die aktuelle Phase wieder –
  über echte Qt-Klicks, headless, **nicht** durch tatsächliches
  Ausführen von `python main.py` mit sichtbarem Fenster (das bleibt der
  Gesamtabnahme auf einem echten Windows-Rechner vorbehalten, siehe
  Abschnitt 19, letzte Zeile)

### 6. Restliche Standard-/Additional-/Common-Komponenten (läuft)

- [x] `Edit` (`text`, `on_change`), `CheckBox` (`caption`/`checked`,
  `on_change`), `RadioButton` (`caption`/`checked`, `on_change`) –
  `tests/test_components_eingabe.py`, 9 Tests, u. a. Eingabe über das
  echte `QWidget` aktualisiert die Prop und feuert `on_change`
- [x] `pcl/strings.py`: `Strings`-Sammlung (`add`, `clear`,
  `load_from_file`/`save_to_file`, Indizierung, Iteration) –
  `tests/test_strings.py`, 7 Tests
- [x] `Memo` (`lines`), `ListBox` (`items`, `item_index`), `ComboBox`
  (`items`, `item_index`, `text`, beidseitig synchron) –
  `tests/test_components_listen.py`, 9 Tests, gegen echte Nutzung in
  `f_Pizza`/`m_Gaestebuch`/`n_abstrakte_Klasse` u. a. geprüft
  (`.Lines.Add`, `.items.add`, `.itemindex`, `.Text`)
- [x] `StringGrid` (`row_count`/`col_count`, `cells[spalte, zeile]`),
  `Image` (`picture.load_from_file`/`.clear()`) –
  `tests/test_components_additional.py`, 8 Tests, gegen echte Nutzung in
  `g_StringGrid`/`d_Cookie_klicker`/`l_Pet` geprüft
- [x] `ScrollBar` (`minimum`/`maximum`/`position`, `on_change`) – einzige
  der restlichen Komponenten mit tatsächlicher funktionaler Nutzung
  (`f_Pizza`: `sb_behinderung.position` steuert eine Schriftgröße) –
  3 weitere Tests in `tests/test_components_eingabe.py`
- [ ] `RadioGroup`, `GroupBox`, `Panel`, `MainMenu`, `PopupMenu` – in
  keinem Referenzprojekt funktional genutzt (`RadioGroup1` in `f_Pizza`
  nur deklariert), daher niedrigste Priorität; werden nachgezogen, wenn
  M2 (Menüs/Komponentenpalette) sie ohnehin braucht
- **Bekannte Lücke, bewusst zurückgestellt:** `on_click`/`on_double_click`
  sollten laut Abschnitt 5.4 für „alle sichtbaren“ Komponenten gelten,
  sind bisher aber nur bei `Button` verdrahtet (natives Qt-Signal). Ein
  komponentenübergreifendes `on_click` über `Control` bräuchte eigene
  Maus-Ereignis-Behandlung für Komponenten ohne natives Klick-Signal
  (`Label`, `Shape`); kein Referenzprojekt braucht es bisher (siehe
  `docs/komponenten.md`).
- [ ] `SpinEdit`, `FloatSpinEdit`, `MaskEdit`, `PaintBox` (inkl. Canvas:
  `line_to`, `rectangle`, `ellipse`, `text_out`), `HtmlViewer` – keine
  Nutzung in `referenz/lazarus/`
- [ ] `TrackBar`, `ProgressBar`, `DateEdit`, `TimeEdit`, `Calendar` – keine
  Nutzung in `referenz/lazarus/`
- [x] Dialoge: `pcl/dialogs.py` mit `show_message`, `input_box` –
  `tests/test_dialogs.py`, 3 Tests (modale Dialoge headless über
  `QTimer.singleShot` + `QApplication.activeModalWidget()` bedient),
  gegen echte Nutzung in `g_StringGrid`/`j_komplexeLeistung`/`l_Pet`/
  `m_Gaestebuch` (`show_message`) und `q_Würfelspiel` (`input_box`)
  geprüft; `message_dlg`, `OpenDialog`, `SaveDialog`,
  `SelectDirectoryDialog`, `ColorDialog`, `FontDialog` ungenutzt,
  zurückgestellt
- [ ] `Timer`, `Sound` – keine Nutzung in `referenz/lazarus/`
- [x] Datei-Methoden für Listen-Komponenten (`Strings.load_from_file`/
  `.save_to_file`, siehe oben); `open_url` noch offen (keine Nutzung in
  `referenz/lazarus/` bisher, `.html`-Ausgabe kommt erst in M5/M6-nahen
  Übungen vor)

### 7. Theme — erledigt

- [x] `pcl/theme/__init__.py`: `design/tokens.json` → QSS-Generator für
  `pcl`-Programme, hell/dunkel; `theme_aufloesen` löst `system` über
  `QStyleHints.colorScheme()` auf (Ausweich-Standard `light`, falls
  unbekannt/keine `QApplication`)
- [x] `Form.theme` wendet das QSS beim Erzeugen und bei jeder Änderung
  sofort auf `self._qwidget` an (Qt-Stylesheet-Vererbung erreicht alle
  Kind-Komponenten automatisch)
- [x] Tests (`tests/test_theme.py`, 6 Tests)
- (Reihenfolge zu Schritt 8 bewusst getauscht: Abnahmeprojekte zuerst,
  da Theme rein optisch ist und die funktionale M1-Abnahme nicht
  blockiert)

**M1 ist damit vollständig abgeschlossen** (alle neun Schritte erledigt,
106 Tests grün). Weiter mit M2.

### 8. Zweites/drittes Abnahmeprojekt — erledigt

- [x] Würfelspiel mit Highscore (`referenz/lazarus/q_Würfelspiel` als
  Vorlage) → `beispielprojekte/Wuerfelspiel/`; alle benötigten
  Komponenten (`Button`, `Label`, `StringGrid`, `input_box`) waren bereits
  aus Schritt 6 vorhanden. Abnahme: `tests/test_beispiel_wuerfelspiel.py`,
  4 Tests über echte Qt-Klicks, Zufall kontrolliert über
  `monkeypatch("random.randint", ...)`, Namensabfrage beim Verlieren über
  `QTimer.singleShot` bedient wie in `tests/test_dialogs.py`
- [x] StringGrid-Übung (`referenz/lazarus/g_StringGrid` als Vorlage) →
  `beispielprojekte/StringGridUebung/`; dafür `Form.close()` ergänzt
  (entspricht `Close` aus der LCL, für `b_schliessen`). Abnahme:
  `tests/test_beispiel_stringgriduebung.py`, 5 Tests, inkl. der
  originalgetreu nachgebildeten Eigenart des Originals (zu lange Eingabe
  wird abgelehnt, aber `row_count` wächst trotzdem schon vorher, sodass
  die nächste gültige Eingabe die freigebliebene Zeile überschreibt)

**M1-Abnahmekriterium aus dem Konzept damit funktional erfüllt:** Ampel,
Würfelspiel und StringGrid-Übung laufen (headless nachgewiesen über echte
Qt-Interaktionen, siehe Begründung in `tests/test_beispiel_ampel.py`).
Offen bis M1 vollständig abgeschlossen ist: Schritt 7 (Theme) nachholen,
Schritt 9 (Dokumentation) ist durchgehend parallel mitgelaufen statt erst
am Ende.

### 9. Dokumentation nachziehen — läuft durchgehend mit

- [x] `docs/komponenten.md` wird nach jeder Komponente sofort ausgefüllt
  statt erst am Ende (Pflicht laut `AGENTS.md`, Definition of Done) –
  aktueller Stand: alle bisher gebauten Komponenten dokumentiert

## M2 – IDE-Grundgerüst

Kleinteilig aufgeschlüsselt in
[`docs/arbeitspakete/M2.md`](arbeitspakete/M2.md) (wie M1 oben).
Schritte 1–10 erledigt: Hauptfenster-Grundgerüst, Aktionsregister,
Projektmodell, „Neues Projekt …“/„Projekt öffnen …“/„Öffnen …“,
Explorer, Platzhalter-Editor (inkl. Speichern), „Unit öffnen …“, „Neue
Unit“ + `u_pflanzen`/`u_garten`-Beispielprojekt, Ausführung als eigener
Prozess ohne Debugger. 164 Tests grün.

- [x] Abnahme: Projekt aus M1 in der IDE öffnen, alle (bisher
  umgesetzten) Datei-Menüfunktionen, `u_pflanzen`/`u_garten`-Projekt
  anlegen und starten – funktional erfüllt; ob das Konsolenfenster für
  `input()` tatsächlich sichtbar erscheint, ist nur auf dem
  Windows-Laptop zu verifizieren (headless nicht möglich)

Zurückgestellt innerhalb M2 (Details und Begründung in
`docs/arbeitspakete/M2.md`): Monaco, vollständige Menüs/Werkzeugleisten,
Units-Feinschliff (Einbinden-Dialog, Umbenennen, Kreisbezug, geteilte
Ansicht), Sitzung, portable Laufzeit, Start-Vorlauf (Speichern/Ruff),
Pause/Stopp/Neustart, Tastenkürzel-Tab/Befehlspalette.

## M3 – Designer, Objektinspektor

Kleinteilig aufgeschlüsselt in
[`docs/arbeitspakete/M3.md`](arbeitspakete/M3.md). Reihenfolge:
Objektinspektor zuerst (baut direkt auf `pcl.properties` auf), dann
Designer-Canvas (Anzeige/Auswahl, dann Platzieren/Verschieben/Größe),
Undo, Komponentenpalette, Ereignis-Codegenerierung (libcst), zuletzt
Ampel vollständig in der IDE nachbauen als Abnahme.

- [x] Abnahme: Ampel komplett in der IDE erstellen, alle Eigenschaften nur
  über den Inspektor gesetzt

## M4 – Debugger, Fehlerkatalog, Tests

Kleinteilig aufgeschlüsselt in
[`docs/arbeitspakete/M4.md`](arbeitspakete/M4.md). Reihenfolge:
Ruff-Prüfung vor Start (trivial, eigenständig), Fehlerkatalog (braucht
keinen Debugger), dann der DAP-Client selbst (Grundgerüst, Breakpoints/
Ausführungssteuerung, Variablen/Aufrufstapel, jeweils gegen echtes
`debugpy` getestet statt manuell mit VS Code wie ursprünglich in S3
vorgesehen), IDE-Verdrahtung, Test-Explorer, zuletzt die Abnahme.

- [x] Abnahme: Fehlerbeispiele liefern korrekte Meldungen,
  Breakpoints/Step funktionieren, Tests mit Soll/Ist-Anzeige

## M5 – Datenbank, pandas, Charts

Kleinteilig aufgeschlüsselt in
[`docs/arbeitspakete/M5.md`](arbeitspakete/M5.md). Reihenfolge: SQLdb-
Kern gegen SQLite zuerst (reine Python-Logik, keine Qt-Abhängigkeit),
dann MySQL/MariaDB-Unterstützung (echter Verbindungstest gegen eine
laufende MariaDB-Instanz zurückgestellt, siehe M5.md), pandas-Anbindung
und Chart-Komponente (beide unabhängig von der Datenbank), `open_url`,
Data Controls, IDE-Betrachter (CSV/Bild/HTML), Datenbank-Panel, zuletzt
die Abnahme.

- [x] Abnahme: Kontoverwaltung (`referenz/lazarus/n_konto`) mit SQLite,
  CSV-Auswertung mit pandas in StringGrid und Chart, Würfelspiel-
  Highscore als HTML im Browser – MariaDB-Teil zurückgestellt (siehe
  M5.md, „Stolperstein MariaDB“)

## M6 – Konsolen-Feinschliff

Kleinteilig aufgeschlüsselt in
[`docs/arbeitspakete/M6.md`](arbeitspakete/M6.md).

- [x] Abnahme: Konsolen-/CRT-Übungen laufen (`beispielprojekte/CrtDemo/`)

## M7 – Design-Prüfer, Paketverwaltung

Kleinteilig aufgeschlüsselt in
[`docs/arbeitspakete/M7.md`](arbeitspakete/M7.md). Größenänderung/
Skalierung (brauchen ein Anker-System bzw. eine DPI-Simulation, die
`pcl` noch nicht hat) und Teile von Lesbarkeit (Schriftgröße/-art gibt
es als Prop noch nicht) bewusst zurückgestellt, siehe M7.md.

- [x] Design-Prüfer (regelbasiert, Abschnitt 14)
- [x] Paketverwaltung (pip über die IDE)
- [x] Abnahme: alle Prüfregeln erkennen ihre Testformulare, Paket über das
  Menü installierbar

## M8 – Lazarus-Import, Exe-Export, Verteilung

Kleinteilig aufgeschlüsselt in
[`docs/arbeitspakete/M8.md`](arbeitspakete/M8.md). Exe-Export/
Verteilung brauchen einen echten Windows-Rechner, siehe M8.md.

- [ ] `.lfm`-Import (Parser, Zuordnungstabelle, Abschnitt 15) – jetzt mit
  echten `.lfm`-Dateien aus `referenz/lazarus/` testbar
- [ ] Exe-Export (PyInstaller-Pipeline), Icon `ide/assets/icons/app.svg`
  (als `.ico` konvertiert) für die `.exe` und die `.natter`-Dateizuordnung
  im Windows-Explorer verwenden (siehe „Zurückgestellt“ oben)
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
