# Natter

**Eine Entwicklungsumgebung für Python** — für Schülerinnen und
Schüler im Informatikunterricht. Oberfläche, Hilfetexte und Meldungen
sind vollständig auf Deutsch. Zielplattform: Windows.

Alles Gewohnte liegt an seinem Platz: Menüleiste, Werkzeugleisten,
Komponentenpalette, Formular-Designer, Objektinspektor,
Projekt-Explorer. Wer Python kennt, findet gewöhnliches Python vor — kein
Dialekt, keine versteckte Umschreibung.

Dieses Dokument beschreibt, **was es gibt**. Wie Natter gebaut und
ausgeliefert wird, steht in [`docs/entwicklung.md`](docs/entwicklung.md).

## Herunterladen

**[Neueste Fassung für Windows herunterladen](https://github.com/SuperSparrow-sys/natter/releases/latest)**

Dort liegen zwei Dateien:

| Datei | Wofür |
|---|---|
| `Natter-<Version>-fuer-Lehrkraefte.zip` | das vollständige Paket für die Schule: Installationsprogramm, Zertifikat, Hilfsskripte und Handbuch |
| `Natter-Setup.exe` | nur das Installationsprogramm, für einen Rechner, auf dem das Zertifikat schon eingetragen ist |

Mit der ZIP geht es unter Windows so weiter:

1. Die ZIP herunterladen.
2. **Vor dem Entpacken** Rechtsklick auf die ZIP → *Eigenschaften* →
   unten *Zulassen* anhaken → *OK*. Windows markiert heruntergeladene
   Dateien als „aus dem Internet" und fragt sonst bei jeder
   entpackten Datei einzeln nach. Fehlt der Haken, ist die Datei
   schon zugelassen.
3. Rechtsklick → *Alle extrahieren …*, danach `ZUERST-LESEN.txt`
   öffnen. Dort steht, ob der Rechner die Voraussetzungen erfüllt und
   in welcher Reihenfolge es weitergeht.

Unter jeder Fassung stehen die SHA-256-Prüfsummen beider Dateien. Mit
`Get-FileHash <Datei>` in der PowerShell lässt sich nachsehen, ob der
Download unverändert angekommen ist.

---

## 1. Ziele und Abgrenzung

**Was Natter leistet**

- Alles ist normales Python: Klassen, Variablen, Listen, Dateien, in
  Konsolenprogrammen `input()`/`print()` — ohne Spracherweiterung
- GUI-Programme: Ein- und Ausgabe ausschließlich über
  Komponenten (Edit, Memo, RadioGroup, ComboBox, StringGrid, Dialoge …)
- Visuelle Oberflächenentwicklung: Formular-Designer, Objektinspektor
  für Eigenschaften und Ereignisse, Doppelklick erzeugt die Methode
- Eigenschaft im Inspektor und Attribut im Code sind dasselbe: `caption`
  im Inspektor ist `self.b_ok.caption` im Code
- Projekte aus mehreren Units, nebeneinander in Reitern
- Code-Editor im VS-Code-Stil mit hellem und dunklem Design
- Ausführung in eigenen Fenstern: GUI-Programme als eigenes Fenster,
  Konsolenprogramme in einem eigenen Konsolenfenster
- Datenbanken: SQLite — eine Datei neben dem Programm
- Debugger mit schülergerechten Fehlermeldungen, die keine Lösung
  vorsagen
- Diagramm-Editor für UML, Struktogramme und Entscheidungstabellen
- Import vorhandener `.lfm`-Formulare
- Export des eigenen Programms als Windows-Programm (`.exe`)

**Was Natter bewusst nicht tut**

- Fremden Quelltext nach Python übersetzen (nur Formulare werden
  importiert)
- Andere Betriebssysteme als Windows, andere Sprachen als Deutsch
- Deutsche oder anderssprachige Aliasse für Python-Namen
- KI-Funktionen in der IDE

## 1a. Für Lehrkräfte

[`docs/fuer_lehrkraefte.md`](docs/fuer_lehrkraefte.md) beschreibt das
Einrichten auf einem einzelnen Rechner und im Computerraum, die
Warnung von Windows beim ersten Start, wo Programm und Schülerdaten
liegen, den Prüfungsmodus und sämtliche Tastenkürzel. Ohne
Programmierkenntnisse lesbar.

## 1b. Was noch offen ist

[`docs/offene_punkte.md`](docs/offene_punkte.md) sammelt gefundene
Fehler und ungeklärte Fragen, die noch nicht behoben sind — jeweils
mit dem, was nachgewiesen ist, und dem, was noch zu prüfen bleibt.
[`docs/umsetzungsplan.md`](docs/umsetzungsplan.md) sagt je Punkt, wie
er umgesetzt und womit er geprüft wird.

## 2. Worauf Natter aufbaut

| Bereich | Technik |
|---|---|
| Oberfläche (IDE und Schülerprogramme) | PySide6 (Qt 6) |
| Code-Editor | Qt (`QPlainTextEdit`) mit eigener Python-Hervorhebung |
| Vervollständigung, Signaturen, Gehe-zu | Jedi |
| Prüfung vor dem Start | Ruff |
| Debugger | debugpy über das Debug Adapter Protocol |
| Code-Änderungen durch die IDE | libcst |
| Datenbanken | `sqlite3` |
| Exe-Export | PyInstaller |
| Diagramm-Editor | `QGraphicsView`/`QGraphicsScene` |
| Symbole | eigenes SVG-Set, per `currentColor` hell/dunkel |

## 3. Aufbau

Natter besteht aus zwei Teilen, die getrennt bleiben:

- **`pcl`** — die Python Component Library. Sie enthält die Komponenten,
  aus denen Schülerprogramme bestehen, und läuft **ohne** die IDE. Ein
  exportiertes Programm braucht nur `pcl`.
- **`ide`** — die Entwicklungsumgebung: Editor, Designer, Inspektor,
  Debugger, Diagramm-Editor, Projektverwaltung.

`pcl` kennt `ide` nicht. Diese Richtung ist Absicht: sie sorgt dafür,
dass ein Schülerprogramm nie von der Entwicklungsumgebung abhängt.

## 4. Ein Schülerprojekt

Ein Projekt ist ein Ordner mit einer `.natter`-Datei:

```
MeinProjekt/
  MeinProjekt.natter     Projektdatei (Name, Art, Startdatei)
  main.py                Startdatei — erzeugt und ausgeblendet
  u_main.pfm             das Formular, im Designer bearbeitet
  u_main.py              der eigene Code
  u_main_design.py       aus dem Formular erzeugt und ausgeblendet
```

**Sichtbar ist, was bearbeitet wird.** `main.py` und `u_main_design.py`
erzeugt Natter selbst und führt sie selbst nach — im Projekt-Explorer
tauchen sie nicht auf. Wird
eine Unit gelöscht, verschwinden ihr Formular und ihre erzeugte Datei
mit ihr.

**Was sichtbar ist, hat ein festes Gerüst.** Eine neue Unit ist nie eine
leere Datei, sondern kommt mit den nötigen Importen und einem
Klassenrumpf.

### 4.1 Konsolenprojekte

Ein Konsolenprojekt läuft von oben nach unten, mit `print()` und
`input()` in einem eigenen Konsolenfenster. Der Aufbau ist derselbe wie
bei einem GUI-Projekt, nur ohne Formular:

```
MeinProjekt/
  MeinProjekt.natter
  main.py                startet das Programm — erzeugt und ausgeblendet
  u_main.py              der eigene Code
```

**Auch hier gilt: `main.py` startet nur.** Alles, was programmiert
wird, steht in `u_main.py`. Es gibt keinen Projekttyp, bei dem eine
Schülerin in die Startdatei schauen müsste.

## 5. Die Komponentenbibliothek `pcl`

### 5.1 Standard

`Button`, `Label`, `Edit`, `CheckBox`, `Memo`, `ListBox`, `ComboBox`,
`RadioButton`, `RadioGroup`, `ScrollBar`, `GroupBox`, `Panel`,
`MainMenu`, `PopupMenu`

`MainMenu` ist die Menüleiste am oberen Rand des Fensters, `PopupMenu`
das Klappmenü auf die rechte Maustaste. Ihre Einträge werden im
Menü-Editor gefüllt: Doppelklick auf das Symbol, F2 oder die Zeile
`entries` im Objektinspektor.

### 5.2 Zusätzlich

`StringGrid`, `Image`, `Shape`, `PaintBox`, `HtmlViewer`, `Chart`,
`SpinEdit`, `FloatSpinEdit`, `TrackBar`, `ProgressBar`, `Timer`

`PaintBox` ist die freie Zeichenfläche: `Shape` legt fertige Formen hin,
`PaintBox` zeichnet mit Koordinaten.

```python
stift = self.pb_bild.canvas
stift.pen.color = "#c42b1c"
stift.line(10, 10, 120, 80)
stift.brush.color = "#f2b134"
stift.ellipse(30, 30, 90, 90)
stift.text_out(10, 110, "Hallo")
```

Das Gezeichnete bleibt stehen, auch wenn ein Fenster darüberfährt.
Gemalt wird mit der Maus über `on_mouse_down`/`on_mouse_move` – die
Koordinaten stehen in der Ereignis-Methode.

`Timer`, `MainMenu` und `PopupMenu` zeigen im laufenden Programm
nichts an. Im Designer liegen sie als kleines Symbol auf dem Formular,
damit man sie anklicken und einstellen kann.

### 5.2a Eingabe

`MaskEdit`, `DateEdit`, `TimeEdit`, `Calendar`

Eingaben mit festem Format. `MaskEdit` lässt nur hinein, was in die
Maske passt (`00000` für eine Postleitzahl). `DateEdit`, `TimeEdit` und
`Calendar` arbeiten mit **echten Python-Typen**:

```python
von = self.de_start.date          # ein datetime.date
bis = self.de_ende.date
self.l_dauer.caption = f"{(bis - von).days} Tage"
```

Angezeigt wird deutsch (`23.11.2026`, `17:45`, „November", „Montag"),
gespeichert wird in der `.pfm` als ISO-Datum.

### 5.3 Datenbank

`SQLite3Connection`, `SQLQuery`, `DataSource`, `DBGrid`, `DBText`,
`DBEdit`, `DBComboBox`, `DBNavigator`

### 5.4 Dialoge und Werkzeuge

`show_message`, `input_box`, `open_dialog`, `open_url`, `regression`,
`Sound` (spielt `.wav` ab, `Sound.beep()` für einen kurzen Ton),
`analyse`

Die Eigenschaften heißen in Python-Schreibweise: `caption`,
`on_click`, `read_only`.

## 6. Design

Ein Satz Design-Tokens (`design/tokens.json`) färbt sowohl die IDE als
auch die Schülerprogramme, in einem hellen und einem dunklen Thema. Ein
Programm sieht damit von Anfang an ordentlich aus, ohne dass jemand
Farben von Hand setzt.

## 7. Die Entwicklungsumgebung

| Bereich | Inhalt |
|---|---|
| Menü und Werkzeugleisten | jede Funktion als Aktion — Menüeintrag, Knopf, Tastenkürzel und Befehlspalette aus einer Quelle |
| Projekt-Explorer | Units, Formulare, Diagramme; umbenennen und löschen über „⋮" |
| Formular-Designer | echte `pcl`-Komponenten, Ziehen mit Maus und Tastatur, acht Größenanfasser, Rückgängig |
| Komponentenpalette | zwei Reiter, „Standard" und „Zusätzlich" |
| Objektinspektor | Eigenschaften und Ereignisse; Doppelklick auf ein Ereignis legt die Methode an |
| Quelltexteditor | Zeilennummern, Syntax-Hervorhebung in den Farben von VS Code, Einrückungslinien, Vervollständigung, Fehler direkt unterringelt |
| Betrachter | CSV als sortierbare Tabelle, Bilder, HTML — und Markdown gesetzt statt als Rohtext |
| Ausgabe-Panel | Programmausgabe, Fehler und Prüfmeldungen |
| Test-Explorer | Unit- und Klassentests mit Soll-/Ist-Vergleich |
| Startbild | zuletzt geöffnete Projekte, neues Projekt, die Beispielprojekte |

## 8. Debugger und Fehlermeldungen

Haltepunkte, Einzelschritt, Variablenanzeige — über debugpy, also
dieselbe Technik wie in VS Code.

Wichtiger als der Debugger ist der **Fehlerkatalog**: Natter übersetzt
die häufigsten Python-Fehlermeldungen in verständliches Deutsch und
sagt, wo man nachsehen sollte — ohne die Lösung zu verraten. Er greift
bei jedem Programmstart, nicht nur unter dem Debugger.

Vor jedem Start läuft zusätzlich eine schnelle Prüfung mit Ruff.
Syntaxfehler halten das Programm an, bevor es startet; Kleinigkeiten wie
ein ungenutzter Import sind nur ein Hinweis und blockieren nichts.

## 9. Konsolenprogramme

Laufen in einem eigenen Konsolenfenster, das nach dem Ende offen bleibt
(„Programm beendet. Eingabetaste zum Schließen …"), damit die Ausgabe
lesbar bleibt.

## 10. Datenbanken

Natter kennt **eine** Datenbank: SQLite, eine Datei neben dem
Programm. Kein Server, kein Netz, keine Zugangsdaten — und damit auch
kein Passwort, das irgendwo gespeichert werden müsste.

### 10.1 Im Code

Öffnen ist eine Zeile, abfragen auch:

```python
self.db = SQLite3Connection("konten.sqlite")

for zeile in self.db.query("SELECT inhaber, stand FROM konto"):
    print(zeile["inhaber"], zeile["stand"])
```

Jede Zeile ist ein gewöhnliches `dict`. `query_one(...)` liefert die
erste Zeile oder `None`, `execute(...)` führt INSERT/UPDATE/DELETE aus
und schreibt sofort fest.

Werte gehören nie in den SQL-Text, sondern als `:name`-Platzhalter
hinein und als Schlüsselwortargument hinterher — das verhindert
SQL-Injection:

```python
self.db.execute("INSERT INTO konto (inhaber) VALUES (:wer)", wer=name)
```

### 10.2 Auf dem Formular

`DBGrid`, `DBEdit`, `DBText` und `DBNavigator` zeigen eine Abfrage
unmittelbar an. Am kürzesten über `show_rows`:

```python
self.g_konten.show_rows(self.db.query("SELECT * FROM konto"))
```

## 11. Dateien, Bilder und Datenauswertung

- Text-, CSV- und HTML-Dateien schreiben und lesen
- HTML im Browser öffnen
- Bilder einbinden: per Drag & Drop in den Designer oder zur Laufzeit
  über `picture.load_from_file(…)`
- CSV- und Excel-Dateien mit pandas auswerten, Ergebnis im `StringGrid`
  oder als Diagramm
- Diagramme: Balken, Linie, Kreis, Punktwolke, Histogramm, Boxplot
- Ausgleichskurven: linear, polynomial, exponentiell, logarithmisch,
  mit Bestimmtheitsmaß und Vorhersage

## 12. Der Lehrgang: neun Beispielprojekte

Die mitgelieferten Beispiele sind keine Sammlung, sondern eine
Reihenfolge. Jede Stufe bringt genau eine neue Idee dazu:

| | Projekt | Art | Neu |
|---|---|---|---|
| 01 | Begrüßung | Konsole | Ein- und Ausgabe, Variablen |
| 02 | Zahlenraten | Konsole | Verzweigung, Schleife, Zufall |
| 03 | Taschenrechner | GUI | Formular, Knopf, Ereignis |
| 04 | Cookie-Klicker | GUI | Bilder, Zeitgeber, Spielstand |
| 05 | Bildergalerie | GUI | Dateien von der Festplatte holen |
| 06 | Kontoverwaltung | GUI | eigene Klassen, SQL-Datenbank |
| 07 | CSV-Auswertung | GUI | CSV lesen und schreiben, auswerten |
| 08 | Regression | GUI | aus Daten eine Regel ableiten |
| 09 | Obst-Sortierer | GUI | Random Forest mit scikit-learn |

Ein Beispiel wird beim Öffnen **kopiert**, nicht an Ort und Stelle
geöffnet — die Arbeit landet im eigenen Dokumente-Ordner und ist am
nächsten Tag noch da.

## 13. Diagramm-Editor

Ein eigenes Fenster für Klassendiagramme, Struktogramme und
Entscheidungstabellen. Gezeichnet wird von Hand, wie in DIA — Natter
erzeugt keine Diagramme aus dem Code und keinen Code aus Diagrammen,
weil beides dem Verständnis eher im Weg steht.

Export als PDF, PNG und SVG; drucken geht direkt.

## 14. Design-Prüfer

Regelbasierte Hinweise auf Formulare, die unordentlich aussehen würden:
überlappende Komponenten, Text, der aus seinem Feld läuft, uneinheitliche
Abstände.

## 15. Formular-Import

Vorhandene `.lfm`-Formulare lassen sich einlesen; eingebettete Bilder
landen als Dateien im Projekt, und der zugehörige Pascal-Code aus der
`.pas` wird als Kommentar übernommen, damit man ihn beim Übersetzen
danebenlegen kann.

## 16. Exe-Export

„Projekt → Als Exe exportieren" baut aus dem eigenen Projekt **eine
einzige Exe-Datei**, die auf einem Rechner ohne Python läuft. Alles, was
dazugehört — auch eigene Unterordner wie `bilder/` oder `daten/` —,
steckt darin; es gibt keinen Ordner zum Mitschicken und nichts zum
Entpacken. Während des Baus läuft in der untersten Zeile ein
Ladebalken mit.

## 17. Quelltext als PDF

„Projekt → Quelltext als PDF …" schreibt den Quelltext des ganzen
Projekts zum Abgeben: eine Datei je Seite, mit Zeilennummern und
derselben Einfärbung wie im Editor, auf A4 mit Rand zum Anstreichen.
In der Kopfzeile stehen Projektname, Dateiname und Datum — bei zwanzig
eingesammelten Abgaben ist sonst nicht zu erkennen, welche zu wem
gehört. Ausgegeben wird nur, was jemand selbst geschrieben hat.

## 18. Prüfungsmodus

Vier Stunden ohne Lösungsvorschläge und ohne Quelltexterzeugung aus
Diagrammen. Übersteht einen Neustart und läuft von selbst wieder aus.
Solange er läuft, steht das rot in der Fußzeile.

---

## Installation

`Natter-Setup.exe` herunterladen und starten. Der Installer bringt alles
mit; auf dem Rechner muss kein Python installiert sein, und eine bereits
vorhandene Python-Installation bleibt unberührt.

Vorgabe ist die Installation **nur für den angemeldeten Benutzer** — auf
einem Schulrechner ohne Administratorrechte der Weg, der immer
funktioniert. Der Zielordner lässt sich frei wählen.

## Mitwirken

Wie Natter gebaut, getestet und ausgeliefert wird, steht in
[`docs/entwicklung.md`](docs/entwicklung.md); die Regeln für Beiträge in
[`AGENTS.md`](AGENTS.md).

## Lizenz

Privates Projekt, siehe [`LICENSE`](LICENSE): Nutzung erlaubt,
Weitergabe nicht erlaubt. Die Lizenztexte der mitgelieferten
Bibliotheken liegen nach der Installation im Ordner `Lizenzen`.
