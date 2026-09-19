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

**Stand September 2026: alle neun Meilensteine sind abgenommen.**
M0–M8 sind abgeschlossen, und in M9 ist das Abnahmekriterium aus dem
Konzept erfüllt – UML-Klassendiagramm, Struktogramm und
Entscheidungstabelle der Ampel von Hand erstellt und als PDF
exportiert. Natter ist damit **fachlich vollständig** für das, was im
Unterricht gebraucht wird; was noch offen ist, ist Ausbau und
Feinschliff, kein fehlendes Fundament.

Zahlen zur Einordnung: rund 16 500 Zeilen Python in `ide/` und `pcl/`,
1129 Tests in 125 Dateien – im committeten Stand alle grün, Ruff
sauber. Dazu zehn Beispielprojekte, die alle wirklich starten, und eine
gebaute, signierte `Natter.exe` mit Installer und
`.natter`-Dateiverknüpfung.

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
| Diagramm-Editor: Klasse, Struktogramm, Tabelle | fertig (M9, abgenommen) |

### Was noch zu tun ist

Fünf Gruppen, absteigend nach Nutzen für den Unterricht:

**1. M9 zu Ende bringen** (die Teilschritte, die beim Zeichnen
tatsächlich fehlen):

- **UML-Klassen über einen Eigenschaften-Dialog bearbeiten statt
  direkt auf der Zeichenfläche** (Schritt 12, Nutzer-Entscheidung
  September 2026 nach dem Vorbild von Dia). Das ist der größte
  verbliebene Brocken: Attribute und Operationen werden von freien
  Textzeilen zu strukturierten Datensätzen mit Sichtbarkeit, Typ und
  Parameterliste, das Schema wächst entsprechend, und die vorhandenen
  `.pdiag` müssen beim Laden umgesetzt werden
- **Quelltext aus den Diagrammen erzeugen** (Schritte 13 und 14,
  Nutzer-Wunsch September 2026, Vorbilder Dia und Structorizer):
  aus der modellierten Klasse die Python-Klasse, aus dem Struktogramm
  den Algorithmus – wahlweise ganz oder nur der ausgewählte Block, und
  wahlweise in ein Fenster zum Kopieren oder in eine eigene Datei.
  Schritt 13 setzt Schritt 12 voraus, weil sich nur aus strukturierten
  Attributen und Operationen sinnvoll Code erzeugen lässt; Schritt 14
  geht unabhängig davon
- Mehrfachauswahl, Ausrichten/Verteilen, Kopieren/Einfügen (3b) –
  das ist der spürbarste Mangel: wer zehn Klassen gesetzt hat, kann
  sie derzeit nur einzeln anfassen
- Knickpunkte in Verbindungen und verschiebbare Beschriftungen (4b)
- Blöcke im Struktogramm mit der Maus verschieben (der Baum kann es
  schon, nur das Ziehen fehlt)
- Zoom auch für Struktogramm und Entscheidungstabelle; Lineale und
  Minimap (Rest von 2b)

**2. Die vier weiteren Diagrammtypen** (Abschnitt 13.4 „Später“):
Use-Case, Aktivität, Zustand, Sequenz. Sie bauen auf der fertigen
Formen-und-Verbindungen-Infrastruktur auf – nötig sind je nur neue
Formen- und Verbindungsarten, kein neues Grundgerüst.

**3. Liegengebliebenes aus früheren Meilensteinen** (je Paket
dokumentiert, nichts davon blockiert den Unterricht):

- M3 (2 Punkte): Komponente per Klick+Klick an einer gewählten Stelle
  platzieren statt nur mittig
- M5 (7 Punkte): Designzeit-Aktivierung von Datenbankkomponenten,
  Zugangsdaten im Windows Credential Store, „Als Tabelle anzeigen“ im
  Variablen-Panel, Bild per Drag & Drop ins Formular
- M8 (4 Punkte): Pascal-Rümpfe beim Lazarus-Import als Kommentar
  übernehmen, Bilder aus `Picture.Data` extrahieren, sowie
  Update-Mechanismus und CI-Release-Automatisierung (beide bewusst
  zurückgestellt)

**4. Neu aufgenommen: M10 – Datenauswertung** (Nutzer-Wunsch
September 2026). Diagramme im Designer nutzbar machen und Regression
mit scikit-learn auf CSV- oder Datenbankdaten. Die `Chart`-Komponente
existiert seit M5, ist aber im Designer gar nicht erreichbar – sie
fehlt in der Palette und hat kein Symbol. Einzelheiten in
[`docs/arbeitspakete/M10.md`](arbeitspakete/M10.md).

**5. Offene Frage an den Nutzer:** in
`beispielprojekte/CrtDemo/main.py` steht ein nicht committetes
`input()`. Es hält das Konsolenfenster offen, bricht aber drei Tests.
Die saubere Lösung gehört in den Starter (`ide/run/`), nicht in jedes
Beispiel – das ist noch zu entscheiden.

### Wie der Stand geprüft wurde

Nicht nur über die Testsuite: jeder Schritt wurde zusätzlich im
laufenden Programm angesehen (Bildschirmfotos, exportierte PDFs mit
`QPdfDocument` zurückgelesen und gerendert). Das hat in M9 sieben
Fehler zutage gefördert, die alle Tests bestanden hatten – unter
anderem abgeschnittene Texte, eine im Schwarz-Weiß-Druck unsichtbare
Tabellenkopfzeile, ein am Blattrand klebendes Struktogramm und eine
Druckvorschau, die das Fenster 48 Sekunden eingefroren hätte.

**M8 ist abgeschlossen** (September 2026): Abnahme bestanden mit
`beispielprojekte/Pizza` – aus `referenz/lazarus/f_Pizza` über
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
Zeitpunkt, gegen alle 19 echten `referenz/lazarus/*.lfm`-Dateien
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
  S1/S4 vor M2, S2 vor M2, S7 vor M9. Blockiert M1 nicht.
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
- [ ] `design/referenz/` (freigegebene UI-Mockups): setzt erste
  Bildschirmentwürfe voraus, folgt mit M2/M3.
- [ ] **Visueller Feinschliff der IDE** (Nutzer-Feedback nach dem ersten
  echten Anschauen des Programms, September 2026): wirkt insgesamt noch
  zu farblos/grau. Sammelpunkt für alle folgenden Einzelschritte, jeweils
  eigene kleine Aufgabe statt einer großen:
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
  - [ ] Konsistentes Spacing/Ausrichtung in Objektinspektor, Explorer,
    Palette geprüft und ggf. nachgezogen
  - [x] Icon für die `.exe` und für `.natter`-Dateien im Windows-
    Explorer (Datei-Verknüpfung) – über `tools/natter.iss`
    (`SetupIconFile`, Registry-`DefaultIcon`), Icon-Quelle jetzt
    `ide/assets/icons/app.ico` (aus dem Natter-Maskottchen erzeugt,
    siehe unten)
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

- [x] `.lfm`-Import (Parser, Zuordnungstabelle, Abschnitt 15) – mit
  echten `.lfm`-Dateien aus `referenz/lazarus/` getestet
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
  `beispielprojekte/Pizza` (aus `referenz/lazarus/f_Pizza` importiert,
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
- [ ] Zoom/Lineale/Minimap, Mehrfachauswahl/Anordnen, Knickpunkte
  (Teilschritte 2b, 3b, 4b)
- [ ] danach Use-Case, Aktivität, Zustand, Sequenz

## M10 – Datenauswertung: Diagramme und Regression

Kleinteilig aufgeschlüsselt in
[`docs/arbeitspakete/M10.md`](arbeitspakete/M10.md). Neu aufgenommen
auf Nutzer-Wunsch September 2026; geht über Abschnitt 11.6 des
Konzepts hinaus.

Ausgangslage: die `Chart`-Komponente gibt es seit M5 bereits (Säulen,
Linie, Kreis, Punkte über matplotlib), sie steht aber **nicht** in der
Komponentenpalette und hat kein Symbol – im Designer lässt sich bis
heute kein Diagramm auf ein Formular ziehen. `scikit-learn` ist noch
gar nicht dabei.

- [ ] `Chart` in die Palette, mit eigenem SVG-Symbol
- [ ] Diagrammart und Beschriftungen als Eigenschaften im
  Objektinspektor, mit Beispieldaten im Designer
- [ ] Daten aus CSV, Datenbank oder `StringGrid` in ein Diagramm
- [ ] `scikit-learn` aufnehmen – **vorher** die Auswirkung auf die
  Größe der gebauten `Natter.exe` messen und die Entscheidung
  festhalten; Alternative ist `numpy.polyfit`
- [ ] Lineare, polynomiale, exponentielle und logarithmische
  Regression hinter einer einzigen deutschen Schnittstelle
- [ ] Beispielprojekt `beispielprojekte/Regression/`
- [ ] Abnahme: CSV einlesen, Punkte anzeigen, Regressionsgerade
  darüberlegen, Steigung/Achsenabschnitt/R² ausgeben – im Designer
  zusammengeklickt

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

## Nächster konkreter Schritt

Siehe „Umsetzungsreihenfolge“ oben – der Lauf arbeitet die vierzehn
Punkte der Reihe nach ab. Die Punkte 0 bis 3 sind erledigt, aus
Punkt 8 sind M10 Punkt 1 und 2 vorgezogen und fertig. **Punkt 12**
(M11, Schülertauglichkeit) und **Punkt 13** (Prüfungsmodus) sind
abgearbeitet; was in M11 bewusst offenbleibt, steht dort mit
Begründung.
