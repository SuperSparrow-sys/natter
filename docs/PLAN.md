# Ablaufplan

Schritt-für-Schritt-Checkliste für die Umsetzung, damit nichts vergessen
wird. Konkretisiert docs/entwicklung.md, Abschnitt 20 (Umsetzungsphasen) und
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

**Stand 20. September 2026: M0 bis M15 sind abgeschlossen.** In
diesem Dokument und in allen Arbeitspaketen steht **kein einziges
offenes Kästchen** mehr. Was nicht gebaut wird, steht als getroffene
Entscheidung da und nicht als Haken, der nie kommt – ER-Diagramm,
Syntaxdiagramm, DIA-Import, mehrere Struktogramme je Seite,
Update-Mechanismus und CI-Release.

Zahlen zur Einordnung: rund 32 800 Zeilen Python in `ide/` und `pcl/`
(142 Module), 3421 Tests in 186 Dateien – alle grün, Ruff sauber. Dazu
ein Lehrgang aus neun aufeinander aufbauenden Beispielprojekten, die
alle wirklich starten, und eine gebaute, signierte `Natter.exe` mit
Installer, mitgelieferter Python-Installation und
`.natter`-Dateiverknüpfung.

Was M15 gebracht hat, in einem Satz je Block: Schülerprogramme haben
**Menüs**; `PaintBox` und `Canvas` können **zeichnen**, mit der Maus;
die **Datenbank ist kleiner geworden** statt größer (MySQL raus, eine
Abfrage ist eine Zeile); es gibt **sechs neue Komponenten** samt
Datums- und Uhrzeittyp; der Diagramm-Editor hat **Lineale,
Hilfslinien und eine Minimap**; und jede Zahl auf dem Bildschirm steht
**deutsch** da.

Die Drucker-Tests laufen bewusst nicht im Standardlauf mit
(`uv run pytest -m drucker` startet sie): die Windows-Druckerabfrage
kostet auf einem Rechner mit nicht erreichbarem Netzwerkdrucker knapp
eine Minute und ließ dabei die Zeitgrenzen der Debugger-Tests reißen.

### Was fertig ist

| Bereich | Stand |
|---|---|
| `pcl`-Komponentenbibliothek, Theme, Eigenschaften-System | fertig (M1) |
| IDE-Grundgerüst, Quelltexteditor, Projektverwaltung | fertig (M2) |
| Formular-Designer, Objektinspektor, Code-Erzeugung | fertig (M3) |
| Debugger, Fehlerkatalog, Testrunner | fertig (M4) |
| Datenbank, pandas, Charts | fertig (M5) |
| Konsolen-Feinschliff (CRT-Nachbau) | fertig (M6) |
| Design-Prüfer, Paketverwaltung | fertig (M7) |
| Lazarus-Import, Exe-Export, Signierung, Installer | fertig (M8) |
| Diagramm-Editor: sieben Diagrammtypen, Dialog, Quelltexterzeugung | fertig (M9) |
| Datenauswertung: Chart im Designer, Regression | fertig (M10) |
| Durchsicht der ganzen Oberfläche, Prüfungsmodus | fertig (M11) |
| Durchsicht für Lernende, Hilfe, Fehlerkatalog | fertig (M12) |
| Ausgelieferte Python-Installation | fertig (M13) |
| Aufräumen, Lehrgang, Timer, Exe als eine Datei | fertig (M14) |
| Menüs, Zeichnen, Maus, sechs Komponenten, Lineale/Minimap | fertig (M15) |

### Was noch zu tun ist

Am 19. September 2026 wurden alle 112 unabgehakten Punkte in diesem
Dokument und in `docs/arbeitspakete/` einzeln gegen den Quelltext
geprüft. Das Ergebnis: **86 davon waren längst erledigt und nur nie
abgehakt worden** – der ganze Eigenschaften-Dialog aus M9 Schritt 12,
beide Wege der Quelltexterzeugung (13 und 14), alle vier weiteren
Diagrammtypen, Zoom, Mehrfachauswahl, Knickpunkte, das Ziehen von
Struktogrammblöcken und ganz M10. Sie sind jetzt abgehakt. Vier
weitere waren gar keine Aufgaben, sondern getroffene Entscheidungen
(kein `StopIteration`-Eintrag, keine Screenshot-Sammlung im
Repository, zwei Daueraufgaben ohne Ende); sie stehen jetzt als solche
da. **Wirklich offen sind 22.**

Was wirklich bleibt, steht kleinteilig in
[`docs/arbeitspakete/M15.md`](arbeitspakete/M15.md) und in vier
Gruppen hier:

**1. Fehlende `pcl`-Komponenten** – die Lücke, die Lernende
unmittelbar trifft. `MainMenu` und `PopupMenu` sind seit M15 da; offen
bleiben `PaintBox` samt `Canvas` (Zeichnen kommt im Unterricht vor),
`MaskEdit`, `DateEdit`, `TimeEdit`, `Calendar`, `HtmlViewer` und
`Sound`.

**2. ~~Nicht sichtbare Komponenten im Designer~~ – erledigt, indem die
Datenbank kleiner wurde.** Hier stand, `DataSource`, `SQLQuery` und die
Verbindungen müssten als Symbole auf dem Formular liegen, wie in
Lazarus. Dabei wäre ein `.pfm`-gespeichertes MySQL-Passwort
herausgekommen, und dafür ein Schlüsselspeicher. Der Nutzer hat im
September 2026 stattdessen die Ursache gestrichen: MySQL/MariaDB und
PyMySQL sind entfallen, eine Abfrage ist
`db.query("SELECT ...", grenze=0)` mit Auto-Commit, `SQLTransaction`
ist weg – und die Data Controls brauchen keine `DataSource` mehr, womit
sie sich im Designer ablegen lassen und im Eigenschaften-Rundlauf
mitlaufen. Drei getrennt notierte Punkte (M5 zweimal, M11 einmal) sind
damit erledigt, zwei weitere hinfällig.

**3. Lineale, Hilfslinien und Minimap** im Diagramm-Editor – die drei
letzten ausgegrauten Einträge im Menü „Ansicht“ (M9, Teilschritt 2b).

**4. Kleinigkeiten:** ein Eintrag für `NatterDatenError` im
Fehlerkatalog, ein Abnahmetest für `plt.show()` aus Konsolenprogrammen,
und ein Durchgang über Abstände und Ausrichtung in Objektinspektor,
Explorer und Palette.

**Bewusst nicht in Arbeit** (steht so in den Paketen und bleibt dort):
ER-Diagramm, Syntaxdiagramm und DIA-Import (Konzept: „später
möglich“), mehrere Struktogramme auf einer Seite, ein echter
MariaDB-Verbindungstest (hinfällig – MySQL ist mit M15 entfallen), ein
Update-Mechanismus und die CI-Release-Automatisierung.

### Wie der Stand geprüft wurde

Nicht nur über die Testsuite: jeder Schritt wurde zusätzlich im
laufenden Programm angesehen (Bildschirmfotos, exportierte PDFs mit
`QPdfDocument` zurückgelesen und gerendert). Das hat in M9 sieben
Fehler zutage gefördert, die alle Tests bestanden hatten – unter
anderem abgeschnittene Texte, eine im Schwarz-Weiß-Druck unsichtbare
Tabellenkopfzeile, ein am Blattrand klebendes Struktogramm und eine
Druckvorschau, die das Fenster 48 Sekunden eingefroren hätte.

**M8 ist abgeschlossen** (September 2026): Abnahme bestanden mit
`beispielprojekte/Pizza` – aus `tests/daten/lazarus/f_Pizza` über
„Werkzeuge → Lazarus-Formular importieren …“ übernommen, im Designer
fertiggestellt, als ZIP gebaut und aus einem frischen Ordner gestartet
– sowie dem signierten Prüfsummen-Manifest, das eine manipulierte
`Natter.exe`-Installation beim Start erkennt (Details in
[`docs/arbeitspakete/M8.md`](arbeitspakete/M8.md), Schritt 4 und 6).
Dafür waren zwei Lücken in der `.pfm`-Pipeline zu schließen
(Strings-Sammlungen `items`/`lines` und eine echte
`font`-Untereigenschaft); dabei kamen vier Fehler ans Licht, die alle
erst beim tatsächlichen Ausführen sichtbar wurden – Objektinspektor und
Rückgängig schrieben nie in die `.pfm` zurück, der Lazarus-Import
erzeugte eine beim Öffnen abstürzende `.pfm` und ließ
`u_main_design.py` auf dem leeren Vorlagenstand, und Kästchen/
Optionsfelder/Bildlaufleisten hatten im `pcl`-Theme keine QSS-Regeln,
sodass in **jedem** Schülerprogramm der Markierungszustand fehlte.
790 Tests grün.

Der bisherige Verlauf von M8, kleinteilig aufgeschlüsselt in
[`docs/arbeitspakete/M8.md`](arbeitspakete/M8.md) (wie M1–M7): Schritt 1
(`.lfm`-Parser), Schritt 2 (Klassen-/Eigenschaftszuordnung nach `.pfm`),
Schritt 3 (IDE-Verdrahtung „Werkzeuge → Lazarus-Formular importieren …“,
per Screenshot gegen das echte `k_Ampel`-`.lfm` geprüft; Pascal-Rumpf-
Übernahme und Bild-Extraktion daraus zurückgestellt) und der Kern von
Schritt 4 (PyInstaller-Export über „Projekt → Als Exe exportieren …“,
mit einem **echten** PyInstaller-Bau des Ampel-Beispielprojekts geprüft
– dabei einen echten Absturz gefunden und behoben: `pcl.theme` fand
`design/tokens.json` in der gebauten Exe nicht, betraf jedes
`pcl`-Programm, siehe M8.md) sind erledigt – 675 Tests grün zu dem
Zeitpunkt, gegen alle 19 echten `tests/daten/lazarus/*.lfm`-Dateien
geprüft. Offen bleibt aus M8 nur noch ein optionales, gekauftes (statt
selbst erstelltes) Authenticode-Zertifikat für Verteilung an unbekannte
Rechner außerhalb der Schule. Seither ein
weiterer Visueller-Feinschliff-Durchgang (Nutzer-Feedback September
2026): Designer-Eigenschaften mit Lazarus abgeglichen (Shape
`pen_color`/`transparent`/Z-Ebene, Label `color`/`transparent`),
Dunkelmodus-Tabellenzellen (StringGrid, komplett schwarz statt
themagerecht) behoben, ein kritischer Fund dabei – `u_..._design.py`
wurde nach der ersten Projekterzeugung nie wieder aktualisiert, jede
Designer-Änderung wirkte nur optisch im Designer, nie im echten
generierten Code – behoben; alle Beispielprojekte durchgetestet
(mehrere abgeschnittene Button-/Label-Beschriftungen durch
Qt/Lazarus-Schriftmetrik-Unterschiede gefunden und behoben), erstes
portiertes Lazarus-Referenzprojekt (`GuiKomponenten`) sowie ein neues
Konsolenrechner-Beispielprojekt (Projekttyp „console“ end-to-end
geprüft, inkl. echtem Exe-Export und Probestart); Projekt-Explorer
bereinigt (keine Rahmen/Hover-Schattierungen, kein versehentliches
Qt-Umbenennen mehr, solider Auswahlbalken statt Baum-Artefakt);
Editor-Schriftart jetzt mit echter Schriftdatei mitgeliefert
(Cascadia Code) und über „Ansicht → Schriftart“ wählbar
(Consolas/Cascadia Code/Courier New), dabei einen echten Fund
gemacht – das IDE-weite Stylesheet überschrieb `setFont()` auf dem
Editor komplett, eine spezifischere QSS-Regel behebt es. Danach
weitere echte Funde und Nutzerwünsche: `pip` fehlte im `uv`-venv
(Absturz bei „Pakete anzeigen“, jetzt als Abhängigkeit ergänzt plus
saubere Fehlerbehandlung), Kontoverwaltung-Beispielprojekt „+“/„-“
im `DBNavigator` waren nie verknüpft (jetzt Konto anlegen/löschen
möglich), Designer-Klick-Platzierung (Palette-Klick → Fadenkreuz →
Klick aufs Formular platziert dort, wie in Lazarus, zusätzlich zum
bisherigen Doppelklick) und eine „name“-Zeile im Objektinspektor
(Bezeichner im Code getrennt von `caption`, frei umbenennbar). Dann
M8 Schritt 4 vollständig abgeschlossen (siehe M8.md, Schritt 4/5):
Natter selbst (nicht nur Schülerprojekte) lässt sich jetzt als
eigenständige, signierte Exe samt Windows-Installationsassistenten
bauen (`tools/ide_paketieren.py`, `tools/natter.iss`) mit echter
`.natter`-Dateizuordnung; kostenloses selbstsigniertes Code-Signing-
Zertifikat gegen Windows Smart App Control eingerichtet und am
echten, wieder aktivierten Smart App Control verifiziert
(`tools/signieren/`). 746 Tests grün. M1–M7 sind
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
„Projekt öffnen …“ → `beispielprojekte/03_Taschenrechner/
03_Taschenrechner.natter` → Doppelklick auf `u_main` im Explorer öffnet
den echten Formular-Designer als Tab; Klick auf einen Knopf oder ein
Textfeld wählt ihn aus und füllt den Objektinspektor rechts; Eigenschaften dort ändern wirkt sofort auf die
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

**Visueller Feinschliff (Nutzer-Feedback, September 2026):** die
Komponentenpalette ist jetzt wie in Lazarus eine horizontale Leiste aus
reinen Symbol-Kacheln (Name als Tooltip); der Quelltexteditor nutzt eine
echte Programmierschriftart (Cascadia Code, mit Konsolas/Courier New als
Ersatz) und eine VS-Code-artige Python-Syntaxhervorhebung
(`PythonHervorhebung`). Die gesamte IDE-Hülle (Menüleiste, Symbolleiste,
Docks, Tabs, Explorer, Panels) hat jetzt ein einheitliches, modernes
Theme (`ide_qss_erzeugen`) statt Standard-Qt-Grau. Das Menü „Ansicht“
bietet Ein-/Ausblenden für alle fünf Docks (auch Wiederherstellen nach
Schließen) über `toggleViewAction()`. Die Menüs Bearbeiten/Suchen/
Quelltext/Fenster/Hilfe, die zwar vorhanden aber wirkungslos waren, sind
jetzt vollständig verdrahtet: Rückgängig/Wiederholen/Ausschneiden/
Kopieren/Einfügen/Alles auswählen, ein nicht-modaler Suchen-und-Ersetzen-
Dialog samt Gehe-zu-Zeile, Kommentar umschalten (Strg+#), Tab-Navigation
und Layout zurücksetzen, sowie Komponenten-Referenz/Über Natter. Ein
Editor-Tab schließen (das „×“ auf dem Tab) war dabei ebenfalls
verdrahtet, aber tot – jetzt fragt es bei ungespeicherten Änderungen
nach. Units im Projekt-Explorer lassen sich über einen „⋮“-Knopf
umbenennen und löschen (inkl. Synchronisierung eines offenen
Editor-Tabs). „Projekt → Als Exe exportieren …“ baut das Projekt mit
PyInstaller (`ide/export`) zu einem eigenständigen, portablen Ordner
oder ZIP – mit einem echten Bau und Probestart des Ampel-
Beispielprojekts geprüft (siehe `docs/arbeitspakete/M8.md`, Schritt 4).
„Ansicht → Design“ schaltet zwischen Hell/Dunkel/System um (per
QSettings gemerkt) – der Quelltexteditor (Syntax-Hervorhebung,
Zeilennummernrand, aktuelle Zeile) folgt sofort mit echten
VS-Code-Dark+/Light+-Farben statt einer bloßen Annäherung, gegen ein
echtes VS-Code-Referenzbild geprüft. Dabei auch einen Fehler gefunden
und behoben: eine Raute innerhalb einer Zeichenkette (z. B.
`"#000000"`) wurde fälschlich als Kommentarbeginn eingefärbt. Ein
gezieltes Durchspielen aller Menüs/Funktionen (Nutzer-Feedback: „schaue
ob jede Funktion auch funktioniert“) deckte auf, dass der Editor bei
einem normalen Debugger-Halt (Breakpoint/Einzelschritt/Pause) nicht zur
aktuellen Zeile sprang, nur bei einer unbehandelten Ausnahme – jetzt
behoben, zusätzlich lässt sich jeder Aufrufstapel-Eintrag anklicken, um
dorthin zu springen.

## Referenzmaterial

- [x] Lazarus-Übungsprojekte als Prüfdaten in `tests/daten/lazarus/`
  vorhanden (20 Projekte,
  mehr als die 8 MVP-Projekte aus Abschnitt 1) – nur Quelltext (`.pas`,
  `.lfm`, `.lpi`, `.lpr`) und Bilder committet; `lib/`, `backup/`, `*.exe`,
  `*.res`, `*.lps` sind ausgeschlossen (Kompilate/Sessiondaten,
  ungefiltert ca. 490 MB, nicht nötig). **Seit M14** liegen nur noch
  die 47 Dateien im Repository, die Tests wirklich lesen – aus
  `referenz/` wurde `tests/daten/lazarus/`, aus 490 MB wurden 185 kB
- [x] Zuordnungstabelle Projekt → benötigte `pcl`-Komponenten/Konzepte:
  überholt und abgelöst. `docs/komponenten.md` führt die Komponenten
  vollständig, und der Lehrgang in `beispielprojekte/` ordnet sie
  Stufe für Stufe zu – das ist dieselbe Auskunft in nützlicherer Form
- [x] Excel-exportierte CSV-Beispiele, SQL-Dump, Beispiel-Diagramme:
  vorhanden, nur an anderer Stelle als gedacht – `07_CsvAuswertung`
  bringt eine deutsche CSV mit Dezimalkomma mit, `06_Kontoverwaltung`
  eine SQLite-Datenbank samt drei `.pdiag`-Diagrammen

### Referenzprojekte in `tests/daten/lazarus/`

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

- [x] `prototypes/s1`–`s7` (Machbarkeitsprüfungen, Abschnitt 23.3):
  **erledigt, weil überholt.** Jede Frage, die ein Prototyp klären
  sollte, ist inzwischen am fertigen Programm beantwortet – portables
  Python (S1) trägt seit M13 die ausgelieferte Installation,
  getrennte Paketordner (S4) und der Editor (S2) stecken in der
  laufenden IDE, `QGraphicsView` (S7) hat sich im Diagramm-Editor als
  unnötig erwiesen, weil eigenes Zeichnen auf `QWidget` dort genauer
  steuerbar war. Der Prototyp-Code bleibt als Beleg liegen.
  S6 ist erledigt und vollständig produktiv gemacht: Teil 1
  (Authenticode mit selbst erstelltem Zertifikat) in `tools/signieren/`,
  Teil 2 (signiertes Prüfsummen-Manifest) in `ide/integritaet/`.
  S3 (debugpy mit VS Code als DAP-Frontend) entfällt: der echte
  DAP-Client aus M4 wird gegen echtes `debugpy` automatisiert getestet
  (`docs/arbeitspakete/M4.md`, Schritt 3–5) – das prüft dieselbe Frage
  rigoroser und wiederholbar, ganz ohne VS Code. S5 (PyInstaller aus
  portablem Python) ist durch den echten Export in M8 Schritt 4 überholt
  – dort direkt mit dem echten Ampel-Beispielprojekt statt dem
  Prototyp-Testprogramm geprüft, siehe `docs/arbeitspakete/M8.md`.
- [x] `design/referenz/` (freigegebene UI-Mockups): **erledigt, weil
  überholt.** Gegen Entwürfe zu prüfen war gedacht, solange es die
  Oberfläche noch nicht gab; seit M2/M3 wird stattdessen am laufenden
  Programm geprüft, und `design/tokens.json` hält die verbindlichen
  Farben und Maße.
- [x] **Visueller Feinschliff der IDE** (Nutzer-Feedback nach dem ersten
  echten Anschauen des Programms, September 2026): wirkte insgesamt zu
  farblos/grau. Sammelpunkt für die folgenden Einzelschritte – seit
  M15, Abschnitt 6 sind alle abgehakt:
  - [x] Fenster-/Taskleisten-Symbol (`ide/assets/icons/app.png` – seit
    September 2026 das von Hand gezeichnete Natter-Maskottchen statt
    des ursprünglichen Vektor-Platzhalters)
  - [x] Werkzeugleiste mit Symbolen (Neu/Öffnen/Speichern/Projekt öffnen/
    Start), bisher nur diese fünf Aktionen
  - [x] Zeilennummern im Quelltexteditor (`ide/shell/quelltexteditor.py`)
  - [x] Symbole (SVG) für Palette-Einträge je Komponententyp (Button/
    Label/Edit/…): `ide/assets/icons/komponente_*.svg`, Palette jetzt ein
    einzeiliger horizontaler Symbolstreifen wie in Lazarus statt einer
    vertikalen Textliste (Nutzer-Feedback, September 2026, mit
    Lazarus-Screenshot belegt) – Komponentenbaum-Symbole (Objektinspektor)
    noch offen
  - [x] Farbiges Theme/Akzentfarben über das ganze Programm konsequent
    angewendet (Docks, Reiter, Tabellen) statt nur im Designer-
    Auswahlrahmen; Referenz `design/tokens.json` (`ide_qss_erzeugen`,
    inkl. Dunkelmodus-Fix für Tabellenzellen)
  - [x] Syntax-Hervorhebung im Quelltexteditor
    (`ide/shell/python_hervorhebung.py`, Nutzer-Feedback September 2026:
    Schriftart/Farben sollen zu VS Code passen) – regelbasiert, an VS
    Codes Light+-Farben angelehnt (Schlüsselwörter/Zeichenketten/
    Kommentare/Zahlen/eingebaute Funktionen wie `print` unterscheidbar);
    echte Monaco-Integration mit vollständiger Grammatik bleibt trotzdem
    ein eigener, späterer Schritt (`prototypes/s2`). Editor-Schriftart
    jetzt `Cascadia Code`/`Consolas`/`Courier New` (wie
    `design/tokens.json`, `family_mono`) statt der UI-Schriftart
  - [x] Knöpfe für Rückgängig/Wiederholen in der Werkzeugleiste
    (`ide/assets/icons/rueckgaengig.svg`/`wiederholen.svg`,
    Nutzer-Feedback September 2026: „Ich sehe die Buttons nicht zum
    rückgängig machen“) – beide Aktionen waren vorhanden und verdrahtet,
    hatten aber kein `symbol` und erschienen deshalb nur im Menü
  - [x] Konsistentes Spacing/Ausrichtung in Objektinspektor, Explorer,
    Palette – mit M15, Abschnitt 6 durchgegangen. Drei Funde: die
    beiden Bäume rückten verschieden tief ein (20 gegen 14 px), die
    Eigenschaften-Tabelle zeigte eine Zeilennummern-Spalte, und ihre
    Wert-Spalte endete mitten im Dock, während der Wert darin
    abgeschnitten war
  - [x] Icon für die `.exe` und für `.natter`-Dateien im Windows-
    Explorer (Datei-Verknüpfung) – über `tools/natter.iss`
    (`SetupIconFile`, Registry-`DefaultIcon`), Icon-Quelle jetzt
    `ide/assets/icons/app.ico` (aus dem Natter-Maskottchen erzeugt,
    siehe unten)
- [x] **Eigenschaften-Abgleich mit Lazarus** (Nutzer-Frage „Habe ich die
  Attribute genau wie in Lazarus?“, September 2026): systematischer
  Abgleich aller `pcl`-`Prop`/`Event`-Namen gegen jede tatsächlich in
  `tests/daten/lazarus/*/unit1.lfm` verwendete Eigenschaft. Ergebnis: alle
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
- [x] `schemas/project.schema.json` gegen `k_Ampel` abgeglichen –
  überholt durch die Praxis: das Schema trägt inzwischen jedes der neun
  Lehrgangsprojekte und jedes neu angelegte Projekt, und der
  Lazarus-Import erzeugt gültige Projektdateien aus echten `.lpi`

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

- [x] `.pfm` von Hand aus `tests/daten/lazarus/k_Ampel/u_main.lfm` abgeleitet
  (Buttons `b_einschalten`/`b_wechseln`/`b_auschalten`, Label, Gehäuse-
  und drei Ampellicht-`Shape`s) → `beispielprojekte/Ampel/u_main.pfm`
  (das Ampel-Projekt ist mit dem Lehrgang in M14 aufgegangen)
- [x] `u_main_design.py` mit dem Generator erzeugt (nicht von Hand)
- [x] `u_ampel.py`: `Ampel`-Klasse, reines Python, Zustandsautomat 1↔2↔3↔4
  originalgetreu aus `tests/daten/lazarus/k_Ampel/u_tampel.pas` übernommen
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
- [x] `RadioGroup`, `GroupBox`, `Panel` – nachgezogen und im Reiter
  „Standard“ der Palette, dort am Ende wie in Lazarus
- [x] `MainMenu`, `PopupMenu` – nachgezogen in M15: beide liegen als
  Symbol auf dem Formular (`Control.nur_im_designer`) und werden über
  einen Menü-Editor gefüllt, wie in Lazarus
- **Bekannte Lücke, bewusst zurückgestellt:** `on_click`/`on_double_click`
  sollten laut Abschnitt 5.4 für „alle sichtbaren“ Komponenten gelten,
  sind bisher aber nur bei `Button` verdrahtet (natives Qt-Signal). Ein
  komponentenübergreifendes `on_click` über `Control` bräuchte eigene
  Maus-Ereignis-Behandlung für Komponenten ohne natives Klick-Signal
  (`Label`, `Shape`); kein Referenzprojekt braucht es bisher (siehe
  `docs/komponenten.md`).
- [x] `SpinEdit`, `FloatSpinEdit` – umgesetzt und in der Palette
- [x] `PaintBox` samt `Canvas` (`line_to`, `rectangle`, `ellipse`,
  `text_out` …) – seit M15, Abschnitt 2 da
- [x] `MaskEdit` und `HtmlViewer` – seit M15, Abschnitt 4 da.
  `HtmlViewer` auf `QTextBrowser`: `QWebEngineView` wöge über 100 MB
  in der gebauten Exe
- [x] `TrackBar`, `ProgressBar` – umgesetzt und in der Palette
- [x] `DateEdit`, `TimeEdit`, `Calendar` – seit M15, Abschnitt 4 da,
  im eigenen Palettenreiter „Eingabe". Dafür kennt `Prop` jetzt
  `date` und `time`: `self.de_termin.date` ist ein echtes
  `datetime.date`, mit dem sich rechnen lässt
- [x] Dialoge: `pcl/dialogs.py` mit `show_message`, `input_box` –
  `tests/test_dialogs.py`, 3 Tests (modale Dialoge headless über
  `QTimer.singleShot` + `QApplication.activeModalWidget()` bedient),
  gegen echte Nutzung in `g_StringGrid`/`j_komplexeLeistung`/`l_Pet`/
  `m_Gaestebuch` (`show_message`) und `q_Würfelspiel` (`input_box`)
  geprüft; `message_dlg`, `OpenDialog`, `SaveDialog`,
  `SelectDirectoryDialog`, `ColorDialog`, `FontDialog` ungenutzt,
  zurückgestellt
- [x] `Timer` – umgesetzt und in der Palette (Nutzer-Hinweis September
  2026: „der Timer muss als Komponente auch mit rein, der ist wichtig“);
  auf dem Formular steht sein Symbol, im laufenden Programm ist er
  unsichtbar
- [x] `Sound` – seit M15, Abschnitt 4 da. Spielt `.wav` über
  `QSoundEffect`, `Sound.beep()` gibt einen Ton ohne Datei. Keine
  `Control`: sie liegt nicht auf dem Formular, sondern wird im Code
  erzeugt wie eine Datenbankverbindung
- [x] Datei-Methoden für Listen-Komponenten (`Strings.load_from_file`/
  `.save_to_file`, siehe oben); `open_url` ist inzwischen in
  `pcl/files.py` umgesetzt – das Würfelspiel schreibt damit seine
  Highscore-Liste als HTML und öffnet sie im Browser

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

- [x] Würfelspiel mit Highscore (`tests/daten/lazarus/q_Würfelspiel` als
  Vorlage) → `beispielprojekte/Wuerfelspiel/`; alle benötigten
  Komponenten (`Button`, `Label`, `StringGrid`, `input_box`) waren bereits
  aus Schritt 6 vorhanden. Abnahme: `tests/test_beispiel_wuerfelspiel.py`,
  4 Tests über echte Qt-Klicks, Zufall kontrolliert über
  `monkeypatch("random.randint", ...)`, Namensabfrage beim Verlieren über
  `QTimer.singleShot` bedient wie in `tests/test_dialogs.py`
- [x] StringGrid-Übung (`tests/daten/lazarus/g_StringGrid` als Vorlage) →
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

- [x] Abnahme: Kontoverwaltung (`tests/daten/lazarus/n_konto`) mit SQLite,
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

- [x] `.lfm`-Import (Parser, Zuordnungstabelle, Abschnitt 15) – mit
  echten `.lfm`-Dateien aus `tests/daten/lazarus/` getestet
- [x] Exe-Export (PyInstaller-Pipeline) – sowohl für Schülerprojekte
  (`ide/export/exporter.py`) als auch für Natter selbst
  (`tools/ide_paketieren.py`), Icon `ide/assets/icons/app.ico` für die
  `.exe` und die `.natter`-Dateizuordnung im Windows-Explorer
  verwendet (`tools/natter.iss`)
- [x] portables ZIP-Paket mit Starter (S5 aus `prototypes/`
  eingesetzt), Signatur mit kostenlosem selbst erstelltem Zertifikat
  gegen Windows Smart App Control (S6, Teil 1, `tools/signieren/`)
- [x] signiertes Prüfsummen-Manifest (S6, Teil 2, Abschnitt 17.8):
  `ide/integritaet/` erzeugt beim Paketieren ein Ed25519-signiertes
  `manifest.json` und prüft es beim Start; „Werkzeuge → Umgebung
  prüfen“ prüft alle Dateien. Ein gekauftes, öffentlich vertrautes
  Zertifikat für Verteilung außerhalb bekannter Rechner bleibt
  optional und zurückgestellt
- [x] Abnahme: ein Lazarus-Übungsprojekt importieren, fertigstellen, als
  Exe starten; ZIP auf Rechner ohne Python entpacken und vollständig
  nutzen; veränderte Datei wird erkannt – erfüllt mit
  `beispielprojekte/Pizza` (aus `tests/daten/lazarus/f_Pizza` importiert,
  im Designer fertiggestellt, als ZIP gebaut und aus einem frischen
  Ordner gestartet) und der Manipulationsprüfung an der echten
  gebauten `Natter.exe`, siehe M8.md, Schritt 4 und 6

## M9 – Diagramm-Editor

Kleinteilig aufgeschlüsselt in
[`docs/arbeitspakete/M9.md`](arbeitspakete/M9.md) (wie M1–M8).
Reihenfolge (Nutzer-Feedback September 2026): erst die MVP-Dreiergruppe
aus dem Abnahmekriterium (Klassendiagramm, Struktogramm,
Entscheidungstabelle, jeweils inkl. PNG/SVG/PDF-Export und Drucken von
Anfang an), danach Use-Case-, Aktivitäts-, Zustands- und
Sequenzdiagramm. Eigenes Top-Level-Fenster mit eigenem
Taskleisten-Eintrag statt Dock/Tab in der IDE (Abschnitt 13.1).

- [x] Fenster, Palette, Klassendiagramm, Struktogramm, Entscheidungstabelle
- [x] Stilvorlagen, Layout-Hinweise, Export (PNG/SVG/PDF), Druck
- [x] Abnahme: UML-Klassendiagramm `TAmpel`, Struktogramm
  `ampel_zeichnen` und Entscheidungstabelle der Ampel von Hand erstellt
  und als PDF exportiert
- [x] Zoom und Ansicht verschieben (2b), Mehrfachauswahl/Anordnen (3b),
  Knickpunkte und verschiebbare Beschriftungen (4b) – **Lineale,
  Hilfslinien und Minimap** sind als Einzige aus 2b offen geblieben
- [x] Use-Case, Aktivität, Zustand, Sequenz – alle vier umgesetzt und je
  an einem von Hand nachgebauten Beispiel angesehen
- [x] UML-Klassen über den Eigenschaften-Dialog mit fünf Reitern statt
  direkt auf der Zeichenfläche (Schritt 12, Vorbild Dia)
- [x] Quelltext aus Klassendiagramm und Struktogramm erzeugen
  (Schritte 13 und 14), wahlweise ins Fenster oder in eine Datei

## M10 – Datenauswertung: Diagramme und Regression

Kleinteilig aufgeschlüsselt in
[`docs/arbeitspakete/M10.md`](arbeitspakete/M10.md). Neu aufgenommen
auf Nutzer-Wunsch September 2026; geht über Abschnitt 11.6 des
Konzepts hinaus.

Ausgangslage war: die `Chart`-Komponente gab es seit M5 (Säulen, Linie,
Kreis, Punkte über matplotlib), sie stand aber **nicht** in der
Komponentenpalette und hatte kein Symbol – im Designer ließ sich kein
Diagramm auf ein Formular ziehen. `scikit-learn` fehlte ganz.

- [x] `Chart` in die Palette, mit eigenem SVG-Symbol
- [x] Diagrammart und Beschriftungen als Eigenschaften im
  Objektinspektor, mit Beispieldaten im Designer
- [x] Daten aus CSV, Datenbank oder `StringGrid` in ein Diagramm
- [x] `scikit-learn` aufgenommen – die geforderte Messung der
  Exe-Größe steht in `docs/arbeitspakete/M10.md`
- [x] Lineare, polynomiale, exponentielle und logarithmische
  Regression hinter einer einzigen deutschen Schnittstelle
- [x] Beispielprojekt – aus dem Lehrgang wurde daraus
  `beispielprojekte/08_Regression/`, dazu `09_ObstSortierer`
  (Random Forest)
- [x] Abnahme: CSV einlesen, Punkte anzeigen, Regressionsgerade
  darüberlegen, Steigung/Achsenabschnitt/R² ausgeben – im Designer
  zusammengeklickt
- [x] geblieben war ein einziger Punkt: ein eigener Eintrag für
  `NatterDatenError` in `docs/fehlerkatalog.yaml`. Mit M15,
  Abschnitt 6 erledigt – vorher griff der `ValueError`-Eintrag und
  fragte nach „Leerzeichen, Einheit oder Dezimalkomma", was bei einem
  Datenfehler fast immer die falsche Fährte ist

## Umsetzungsreihenfolge (autonomer Lauf ab September 2026)

Der Nutzer hat entschieden: **alles aus diesem Plan, der Reihe nach.**
Vorab geklärt wurde alles Folgende, damit der Lauf nicht unterbrochen
werden muss:

| Frage | Entscheidung |
|---|---|
| Struktogramm und Entscheidungstabelle | bleiben **in der Fläche** bedienbar, kein Dialog |
| Notiz und Paket im Klassendiagramm | bleiben ebenfalls direkt bearbeitbar (nur ein Textfeld) |
| Fehlende Struktogramm-Blocktypen | **alle drei** (Endlosschleife, Parallelabschnitt, Try-Block) |
| Regression | **numpy rechnet**, scikit-learn liegt zusätzlich bei |
| Datenquellen fürs Diagramm | **alle drei**: CSV über pandas, SQL, und `StringGrid` |
| Histogramm und Boxplot | kommen dazu, aber zur **Auswahl**, nicht als Vorgabe |
| Umfang von M11 | **Abschnitte 1 bis 4 vollständig**, nicht nur eine Auswahl |
| Startbild | **wird gebraucht**, kein „nice to have“ |
| Meldungen | **jede** Meldung bekommt einen Lösungsvorschlag |
| Prüfungsmodus | neu: vier Stunden ohne Lösungen und ohne Quelltexterzeugung |
| Vervollständigung | **`jedi`** – MIT-Lizenz geprüft, nichts zu kaufen, keine sichtbare Spur in der Oberfläche |
| Bildschirmfotos | **nicht ins Repository** – Arbeitsmaterial, wird danach gelöscht |
| Symbolstil | **filigraner, näher an Lazarus, etwas bunter** |

### Arbeitsweise in diesem Lauf

Ausdrücklicher Wunsch des Nutzers, gilt für jeden Schritt:

1. **Zwischendurch immer wieder testen** – nicht erst am Ende
2. **Regelmäßig committen und pushen**, nicht alles in einem Schwung
3. **Laufend mit Bildschirmfotos prüfen, ob die Gestaltung stimmt.**
   Was nicht passt, wird **sofort korrigiert**, nicht nur vermerkt.
   Das hat sich schon bewährt: in M9 fanden Bildschirmfotos und
   zurückgelesene PDFs sieben Fehler, die alle Tests bestanden hatten
4. Keine Rückfragen mehr – offene Einzelfälle werden mit einer
   begründeten Entscheidung im Commit festgehalten

### Reihenfolge

- [x] **0.** `input()` in `beispielprojekte/CrtDemo/main.py` prüfen,
  gegebenenfalls korrigieren und committen (bricht derzeit drei Tests)
- [x] **1.** M9 Schritt 12 – Eigenschaften-Dialog für UML-Klassen
  (Datenmodell, fünf Reiter, Darstellung, Migration der vorhandenen
  `.pdiag`)
- [x] **2.** M9 Schritt 13 – Klasse als Python-Quelltext ausgeben
- [x] **3.** M9 Schritt 14 – Struktogramm als Quelltext ausgeben,
  **einschließlich** der drei neuen Blocktypen
- [x] **4.** M9 Teilschritt 3b – Mehrfachauswahl, Ausrichten/Verteilen,
  Kopieren/Einfügen, Gruppieren, Zeichenreihenfolge
- [x] **5.** M9 Teilschritt 4b – Knickpunkte, verschiebbare
  Beschriftungen
- [x] **6.** M9 Rest von 2b – Zoom für Struktogramm und Tabelle.
  Lineale und Minimap stehen noch aus
- [x] **7.** M9 Struktogramm – Blöcke mit der Maus verschieben,
  Kopfzeile mit dem Namen
- [x] **8.** M10 vollständig – `Chart` in der Palette, sechs
  Diagrammarten, Datenquellen (CSV/SQL/StringGrid), Regression über
  numpy, Beispielprojekt `beispielprojekte/Regression/`. Gemessen und
  im Paket festgehalten: scikit-learn kostet die Exe 108 MB
- [x] **9.** M9 „Danach“ – Use-Case-, Aktivitäts-, Zustands- und
  Sequenzdiagramm samt Abnahme
- [x] **10.** Reste aus früheren Paketen – M3, M5 und M8. Offen bleibt
  nur die Designzeit-Aktivierung der SQLdb-Komponenten: sie braucht
  eine Designer-Integration für nicht-visuelle Komponenten, die es
  bisher gar nicht gibt (in M5 seit langem so begründet)
- [x] **11.** Restliche `pcl`-Komponenten: `SpinEdit`, `FloatSpinEdit`,
  `TrackBar`, `ProgressBar`, `Timer`, `GroupBox`, `Panel`,
  `RadioGroup`. Offen bleiben `DateEdit`/`TimeEdit`/`Calendar` (`Prop`
  kennt keinen Datumstyp – eine Schnittstellenentscheidung, die kein
  Referenzprojekt absichert), `MaskEdit`, `PaintBox`, `HtmlViewer`,
  `Sound` sowie `MainMenu`/`PopupMenu` (brauchen einen Menü-Editor im
  Designer). Alle Gründe stehen in `docs/komponenten.md`
- [x] **12.** M11 – Schülertauglichkeit: Funktionsprüfung mit
  Bildschirmfotos, Einrückungslinien, Symbole, Vervollständigung,
  Startbild, Meldungen mit Lösungsvorschlag, Nutzerfreundlichkeit.
  Abschnitte 1 bis 6 sind abgearbeitet; was bewusst offenbleibt, steht
  in `docs/arbeitspakete/M11.md` mit Begründung
- [x] **13.** M11 Abschnitt 6 – **Prüfungsmodus**: vier Stunden ohne
  Lösungsvorschläge und ohne Quelltexterzeugung aus Klassendiagramm
  und Struktogramm. Übersteht einen Neustart, läuft von selbst aus

- [x] **14.** M12 – Oberfläche und Programmierung für Lernende
  (`docs/arbeitspakete/M12.md`), auf Nutzer-Wunsch nach M11: nicht mehr
  „tät es, was es verspricht“, sondern „stolpert jemand darüber, der
  gerade erst anfängt“. Gefunden wurden unter anderem ein Knopf, der mal
  ging und mal nicht; eine Startdatei, die Schüler gar nicht sehen
  sollten; eine Anleitung mit falschen Tasten; sechs Alltagsfehler ohne
  deutsche Meldung; ein ungenutzter Import, der den Start verhinderte;
  und der Fehlerkatalog, der die Schüler nur über F5 erreichte

- [x] **15.** M13 – **Vollwertige Installation und Installer**
  (`docs/arbeitspakete/M13.md`), auf Nutzer-Wunsch nach M12: „der
  Installer soll alles beinhalten, um das System vollumfänglich zu
  installieren … beachte, dass in der Exe alle Dinge komplett machbar
  sind, also auch pip und den Rest“. Statt eines eingefrorenen
  PyInstaller-Bundles liefert Natter jetzt eine vollwertige,
  verschiebbare CPython mit `pip` aus; damit arbeiten Paketverwaltung,
  Exe-Export, Debugger und Vorstart-Prüfung in der installierten
  Fassung wieder. Der Installer bringt die klassischen Seiten mit,
  einschließlich anzunehmender Lizenz und Zielordner-Auswahl. Vier
  Fehler waren am Quellbaum nicht zu sehen und kamen erst in der
  fertigen Installation heraus – darunter eine Auslieferung, der ein
  Dutzend Pakete fehlte, obwohl der Bau fehlerfrei durchlief, und eine
  Integritätsprüfung, die still gar nicht mehr lief

- [x] **16.** M14 – **Aufräumen, Lehrgang, Timer, Exe als eine Datei**
  (`docs/arbeitspakete/M14.md`): Serena und die 490 MB Lazarus-Referenz
  entfernt (die vier Import-Tests behalten ihre Vorlagen als 185 kB
  Prüfdaten), aus elf losen Beispielen ein Lehrgang von neun
  aufeinander aufbauenden Projekten gemacht – zwei Konsolenprojekte,
  dann Oberfläche, Bilder, SQL, CSV, Regression und zum Schluss ein
  Random Forest. Dabei fiel auf, was dem Lehrgang fehlte: der Zeitgeber
  gehört in die Palette (`Control.nur_im_designer`), ein Bild braucht
  `on_click`, ein Dateidialog fehlte ganz, und eine Auswahl in einer
  Liste konnte nichts auslösen. Das Löschen einer Unit räumt jetzt auch
  die Hintergrunddateien weg, der Exe-Export liefert **eine** Datei mit
  Ladebalken, und README und Konzept sind getrennt

> **Hinweis zu den Pfaden in diesem Dokument (Stand M14):** Den Ordner
> `referenz/` gibt es nicht mehr — 490 MB Lazarus-Projekte samt
> gebauten Exen. Die 47 Dateien, gegen die der Lazarus-Import geprüft
> wird, liegen jetzt als Prüfdaten in `tests/daten/lazarus/`. Die
> Pfadangaben in diesem Dokument sind am 19. September 2026 darauf
> umgestellt worden; wo im Fließtext noch von „der Referenz" die Rede
> ist, ist dieser Ordner gemeint.

- [x] **17.** M15 – **was nach der Bestandsaufnahme übrig blieb**
  (`docs/arbeitspakete/M15.md`). Am 19. September 2026 wurden auf
  Nutzer-Wunsch („prüfe als erstes was noch offen ist. viel wurde
  schon behoben und comittet") alle 112 unabgehakten Punkte einzeln
  gegen den Quelltext geprüft; 96 waren längst erledigt. Was bleibt:
  `MainMenu`/`PopupMenu` mit Menü-Editor, `PaintBox`/`Canvas`, die
  Datenbankkomponenten als Symbole im Designer, die letzten sechs
  fehlenden Komponenten, Lineale/Hilfslinien/Minimap und vier
  Kleinigkeiten

Zurückgestellt bleiben bewusst: Update-Mechanismus und
CI/Release-Automatisierung (M8), ER-Diagramm, Syntaxdiagramm und
`.dia`-Import (M9) – alle vier sind im jeweiligen Paket als
zurückgestellt begründet.


## M11 – Schülertauglichkeit und Prüfungsmodus

Kleinteilig aufgeschlüsselt in
[`docs/arbeitspakete/M11.md`](arbeitspakete/M11.md). Neu aufgenommen
auf Nutzer-Wunsch September 2026.

Bis M10 ging es darum, dass Natter **alles kann**, was der Unterricht
braucht. Hier geht es darum, dass es sich für Schülerinnen und Schüler
auch **gut anfühlt** – und dass jede einzelne Funktion nachweislich
tut, was sie verspricht.

- [x] Symbole neu gestalten: einheitliches Raster, `currentColor` statt
  fest eingetragener Farbe, Symbole für den Diagramm-Editor (der hatte
  bisher gar keine)
- [x] Quelltexteditor: Einrückung sichtbar machen, Vervollständigung
  nach den ersten Buchstaben, Fehler direkt im Text unterringeln
- [x] Funktionsprüfung **jeder** bedienbaren Stelle – Menüeinträge,
  Knöpfe, Dialoge, Kontextmenüs und jede Komponente samt **jeder**
  ihrer Eigenschaften, bis in das gestartete Programm hinein. Die
  Bildschirmfotos waren dabei Arbeitsmaterial und sind es geblieben:
  gefunden haben sie unter anderem, dass der Auswahlrahmen des
  Designers die Komponenten selbst verschob
- [x] Nutzerfreundlichkeit: Startbild, deutsche Meldungen mit
  Lösungsvorschlag, Tastenkürzel-Übersicht, Kurzhinweise überall,
  Bedienung allein mit der Tastatur, Papierkorb statt endgültigem
  Löschen und die Prüfung auf einem 1366×768-Schulrechner
- [x] **Prüfungsmodus:** vier Stunden lang keine Lösungsvorschläge
  und keine Quelltexterzeugung aus Klassendiagramm und
  Struktogramm. Übersteht einen Neustart von Natter und läuft von
  selbst aus
- [x] Aufräumen, was dabei auffiel: der leere Reiter „Ausgabe“, ein
  „Stopp“, das nur den Debugger beendete, zwei verschiedene Wege zum
  Öffnen, ausgegraute Menüeinträge, die inzwischen etwas können, und
  jede Stelle, an der ein Traceback statt einer Meldung kam

## M12 – Durchsicht für Lernende

Kleinteilig in [`docs/arbeitspakete/M12.md`](arbeitspakete/M12.md).
Dieselbe Übung wie M11, aber aus der anderen Richtung: nicht „tut die
IDE, was sie soll", sondern „kommt eine Schülerin damit zurecht".

- [x] Oberfläche und Programmierung für Lernende durchgesehen
- [x] Umstieg Pascal → Python als eigene Hilfeseite
  (`docs/umstieg_pascal_python.md`), Code-Stellen in der Hilfe lesbar
- [x] Der Fehlerkatalog erreicht die Schüler auch ohne Debugger
- [x] Komponenten-Referenz für Lernende geöffnet
- [x] Die gebaute Exe war an vier Stellen kaputt – gefunden, weil sie
  wirklich gebaut und benutzt wurde, nicht nur getestet
- **Entschieden, nicht offen:** `StopIteration` bekommt keinen
  Katalogeintrag; sie kommt im Unterricht kaum vor

## M13 – Eine echte Python-Installation ausliefern

Kleinteilig in [`docs/arbeitspakete/M13.md`](arbeitspakete/M13.md).

- [x] Natter liefert eine vollständige Python-Installation mit, statt
  eine vorhandene zu suchen – auf einem verwalteten Schulrechner ist
  keine da, und Lernende dürfen keine installieren
- [x] Stolperstein dabei: tiefe Installationspfade reißen die
  Windows-Pfadlängengrenze; beim Prüfen kurze, realistische
  Zielordner verwenden

## M14 – Aufräumen, Lehrgang, Timer, Exe als eine Datei

Kleinteilig in [`docs/arbeitspakete/M14.md`](arbeitspakete/M14.md).

- [x] Ballast raus: Serena entfernt, die 490 MB Lazarus-Referenz auf
  185 kB Prüfdaten in `tests/daten/lazarus/` eingedampft – ohne einen
  einzigen Test zu verlieren
- [x] Aus elf lose gesammelten Beispielen wurde ein **Lehrgang** aus
  neun aufeinander aufbauenden Projekten, von der Konsolenausgabe bis
  zum Random Forest
- [x] `Timer` als Komponente in der Palette (Nutzer-Hinweis: „der
  Timer muss als Komponente auch mit rein, der ist wichtig")
- [x] Die gebaute Exe ist jetzt eine einzige Datei

## M15 – Was nach der Bestandsaufnahme übrig blieb

Kleinteilig in [`docs/arbeitspakete/M15.md`](arbeitspakete/M15.md).
Entstanden aus der Prüfung aller 112 unabgehakten Punkte am
19. September 2026 (96 davon waren längst erledigt).

- [x] `MainMenu` und `PopupMenu` mit Menü-Editor als Dialog – ein
  Schülerprogramm mit Menüleiste war bis dahin nicht baubar. Dafür
  verdrahtet die Komponentenpalette jetzt **alle** Reiter statt zwei
  namentlich genannter; ein dritter wäre vorher stumm geblieben
- [x] `PaintBox` und `Canvas` (freies Zeichnen mit Koordinaten) –
  `pen`/`brush`/`pixels`, `move_to`/`line_to`/`line`, `rectangle`,
  `ellipse`, `fill_rect`, `text_out`, `clear`, `on_paint`. Ohne
  Kantenglättung, damit `pixels[x, y]` die Farbe zurückgibt, die im
  Stift stand. Maus-Ereignisse zum Malen kommen mit dem nächsten Punkt
- [x] Die Datenbank wird **einfacher statt größer**. Geplant waren
  hier die fünf Datenbankkomponenten als Symbole auf dem Formular samt
  Designzeit-Verbindung; auf den Hinweis, dass ein `.pfm`-gespeichertes
  MySQL-Passwort einen Schlüsselspeicher nach sich zöge, kam vom Nutzer
  die Gegenrichtung („nimm das passwort raus und mache die datenbank
  abfrage einfacher"). Ergebnis: MySQL/MariaDB und PyMySQL entfallen,
  eine Abfrage ist `db.query("SELECT ...", grenze=0)` mit Auto-Commit,
  `SQLTransaction` entfällt, und die Data Controls kommen ohne
  `DataSource` aus – womit sie im Designer platzierbar und vom
  Eigenschaften-Rundlauf prüfbar sind (der offene Punkt aus M11)
- [x] `MaskEdit`, `DateEdit`, `TimeEdit`, `Calendar`, `HtmlViewer`,
  `Sound` – dazu kennt `Prop` jetzt `date` und `time`
- [x] Maus-Ereignisse für **alle** sichtbaren Komponenten in `Control`:
  `on_click`, `on_double_click`, `on_mouse_down`/`_move`/`_up`. Damit
  kann die `PaintBox` das, wofür man eine Zeichenfläche im Unterricht
  benutzt – mit der Maus malen
- [x] Lineale, Hilfslinien und Minimap im Diagramm-Editor
- [x] Kleinigkeiten: `NatterDatenError` im Fehlerkatalog,
  `plt.show()`-Abnahmetest, ein Durchgang über Abstände und
  Ausrichtung. Der Credential Store entfiel – ohne MySQL gibt es keine
  Zugangsdaten mehr abzulegen

## Nächster konkreter Schritt

**M15, Schritt 2: `PaintBox` und `Canvas`.** Schritt 1
(`MainMenu`/`PopupMenu` samt Menü-Editor) ist erledigt, und mit ihm das
Hindernis, das auch die Schritte 3 und 4 blockierte: die
Komponentenpalette verdrahtet jetzt alle Reiter statt zwei namentlich
genannter.

Als Nächstes fehlt das freie Zeichnen. `Shape` liefert fertige Formen,
aber Zeichnen mit Koordinaten – wie im Lazarus-Referenzprojekt
`b_schneefigur` – geht nicht. Wichtig dabei: gezeichnet wird in ein
`QPixmap`, sonst wäre alles beim ersten Neuzeichnen des Fensters weg,
und das macht Lernende ratlos, weil ihr Code richtig aussieht.
