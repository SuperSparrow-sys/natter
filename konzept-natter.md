# Natter – Konzept einer Lazarus-artigen IDE für Python

Name: **Natter**. Zielgruppe: Schülerinnen und Schüler, die von Pascal/Lazarus auf Python umsteigen. Zielplattform: Windows.

## 1. Ziele und Abgrenzung

**Ziele**

- Alles ist normales Python: Klassen, Variablen, Listen, Dateien, in Konsolenprogrammen `input()`/`print()` – ohne Spracherweiterung oder versteckte Umschreibung
- GUI-Programme wie in Lazarus: Ein- und Ausgabe ausschließlich über Komponenten (Edit, Memo, RadioGroup, ComboBox, StringGrid, Dialoge …), keine Konsole
- Klassische IDE-Bedienung wie Lazarus: Menüleiste, Werkzeugleisten und Komponentenpalette mit Reitern; alle Menüfunktionen (Datei → Neu, Öffnen, Speichern …) funktionieren vollständig
- Visuelle GUI-Entwicklung: Formular-Designer, Objektinspektor (Eigenschaften + Ereignisse), Doppelklick erzeugt Ereignis-Methode
- Eigenschaften im Objektinspektor und Attribute im Code sind dasselbe: `caption` im Inspektor ist `self.b_ok.caption` im Code
- Projekte aus mehreren Units (z. B. `u_pflanzen.py`, `u_garten.py`): Units anlegen, einbinden, nebeneinander und nacheinander in Tabs anzeigen
- Code-Editor und Gesamtoptik im VS-Code-Stil mit hellem und dunklem Design, Tastenkürzel wie in VS Code
- Ausführung in eigenen Fenstern: GUI-Programme im eigenen Programmfenster, Konsolenprogramme im eigenen Konsolenfenster
- Datenbankanbindung an MySQL/MariaDB und SQLite
- Debugger mit genauen, schülergerechten Fehlermeldungen, die keine Lösungen vorsagen
- Moderne Optik der IDE und der erstellten Programme, regelbasierter Design-Prüfer für Formulare
- Dateiarbeit wie im Unterricht: Text-, CSV- und HTML-Dateien schreiben/lesen, HTML im Browser öffnen, Bilder einbinden
- Datenauswertung von CSV/Excel-Dateien mit pandas, Anzeige in StringGrid und Diagrammen
- Testen mit Test-Explorer (Unit-/Klassentests, Soll-/Ist-Vergleich)
- Eigener Diagramm-Editor in einem separaten Fenster: UML-Diagramme, Struktogramme und Entscheidungstabellen von Hand zeichnen wie in DIA – ohne automatische Erzeugung
- Import vorhandener Lazarus-Formulare (`.lfm`)
- Export als Windows-Programm (`.exe`)
- Oberfläche, Hilfetexte und Meldungen vollständig auf Deutsch

**Abgrenzung**

- Keine Übersetzung von Pascal-Code nach Python (nur Formulare werden importiert)
- Nur Windows
- Nur Deutsch (keine Sprachumschaltung); Python-Bezeichner der Bibliothek (`caption`, `on_click`) bleiben englisch, weil sie Code sind
- Nur Python-Namensstil, keine Pascal-Aliasse
- Keine KI-Funktionen in der IDE. KI-Agenten werden ausschließlich bei der Entwicklung der IDE eingesetzt und sind nicht Teil des Programms.

**MVP-Kriterium:** Alle Übungsprojekte aus dem Kursmaterial (Cookie-Clicker, TAuto, Ampel, InfSys-Pet, Gästebuch, Kontoverwaltung, Würfelspiel mit Highscore, StringGrid-Übung) lassen sich vollständig in Natter umsetzen, debuggen und als `.exe` exportieren.

## 2. Technologie-Entscheidungen

| Bereich                                    | Entscheidung                                                                                                                                   | Begründung                                                                                    |
|--------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------|
| GUI-Toolkit (IDE + Programme)              | PySide6 (Qt 6, LGPL)                                                                                                                           | Umfangreiche Widgets, Tabellen-/Datenbank-Models, High-DPI, gut per QSS stylebar              |
| Code-Editor                                | Monaco (Editor von VS Code) in `QWebEngineView`                                                                                                | Original-VS-Code-Optik: Einrückungslinien, Klammerpaar-Farben, Minimap, Themes                |
| Autovervollständigung, Signaturen, Gehe-zu | Jedi (Python-Backend, per `QWebChannel` an Monaco)                                                                                             | Einfacher als ein vollständiger Language-Server                                               |
| Statische Prüfung                          | Ruff                                                                                                                                           | Schnell, Syntax- und Namensfehler vor dem Start                                               |
| Debugger                                   | debugpy über Debug Adapter Protocol (DAP)                                                                                                      | Standard von VS Code, Breakpoints/Step/Variablen                                              |
| Code-Änderungen durch die IDE              | libcst                                                                                                                                         | Einfügen/Umbenennen von Methoden ohne Formatierungsverlust                                    |
| Datenbanktreiber                           | `sqlite3` (Standardbibliothek), PyMySQL                                                                                                        | PyMySQL ist reines Python, MariaDB-kompatibel, einfach zu bündeln                             |
| Exe-Export                                 | PyInstaller                                                                                                                                    | Etabliert, unterstützt PySide6                                                                |
| Docking-Layout der IDE                     | `QDockWidget` (später ggf. PySide6-QtAds)                                                                                                      | VS-Code-artige Seitenleisten und Panels                                                       |
| Python                                     | Python 3.13 als relokierbare Standalone-Distribution im Programmordner, getrennte Paketordner für IDE und Schülerprojekte (siehe Abschnitt 17) | keine Installation nötig; funktioniert nach dem Verschieben des Ordners, anders als eine venv |
| Menüs, Werkzeugleisten, Tastenkürzel       | `QAction`-Register (eine Aktion = Menüeintrag + Werkzeugleisten-Button + Tastenkürzel + Befehlspalette)                                        | Jede Funktion ist überall gleich verfügbar und nur einmal implementiert                       |
| Diagramm-Editor                            | `QGraphicsView`/`QGraphicsScene` (PySide6) in eigenem Hauptfenster                                                                             | Formen, Verbindungen, Zoom, Druck und SVG/PDF-Export ohne Zusatzbibliothek                    |
| Symbole                                    | eigenes SVG-Symbolset, Basis Lucide (ISC-Lizenz) bzw. Codicons (CC BY 4.0), Komponenten-Symbole selbst gezeichnet                              | scharf bei jeder Skalierung, per `currentColor` automatisch hell/dunkel                       |
| Verteilung                                 | portabler Ordner als ZIP mit Starter `Natter.exe`                                                                                               | auspacken und starten, ohne Python-Installation und ohne Adminrechte                          |

## 3. Gesamtarchitektur

```
┌────────────────────────────── Natter IDE (PySide6, IDE-Pakete) ─────────────────────────┐
│ Menüleiste │ Werkzeugleisten │ Komponentenpalette                                         │
├────────────┴──────────┬──────┴──────────────────────────────┬────────────────────────────┤
│ Aktivitätsleiste      │ Editor-Tabs (Monaco / Designer)      │ Objektinspektor            │
│ Explorer / Projekt    │                                      │                            │
│ Suche / Debug / DB    ├──────────────────────────────────────┴────────────────────────────┤
│                       │ Panels: Meldungen │ Ausgabe │ Variablen │ Aufrufstapel              │
└───────┬───────────────┴──────────┬────────────────┬──────────────────────┬───────────────┘
        │                          │                │                      │
  Aktionsregister            Jedi + Ruff       DAP-Client ── debugpy ── Schülerprogramm
  (Menü/Leiste/Kürzel)                                                  (Prozess, Projekt-Pakete)
        │                                                                └── nutzt pcl
  Projekt/Units/Dateien ── Design-Prüfer (lokal, regelbasiert)
        │
  Diagramm-Editor (eigenes Fenster, .pdiag-Dateien)
```

Zwei getrennte Pakete:

- **`pcl`** (Python Component Library): Runtime der Komponenten. Wird von Schülerprogrammen und der exportierten `.exe` verwendet, läuft ohne IDE.
- **`ide`**: die Entwicklungsumgebung selbst. Der Designer rendert Formulare mit denselben `pcl`-Komponenten, dadurch sieht das Formular im Designer exakt wie im laufenden Programm aus.

## 4. Projektstruktur eines Schülerprojekts

### 4.0 Grundprinzip: alles ist normales Python

- Schülercode ist Standard-Python: `class`, `__init__`, `self`, Variablen, Listen, `dict`, `open()`, `import random`; `input()`/`print()` in Konsolenprogrammen
- Kein Präprozessor, keine eigene Syntax, keine Code-Umschreibung vor dem Start
- `pcl` ist eine gewöhnliche Bibliothek (`from pcl import Button`)
- Eigene Klassen (z. B. `Auto`, `Ampel`, `Konto`) sind normale Python-Klassen in eigenen Modulen, ohne Pflicht-Basisklasse
- Formulare werden als lesbarer Python-Code erzeugt, der zeigt, wie die Komponenten entstehen
- Jedes Projekt läuft auch ohne IDE mit `python main.py`

Beispiel Konsolenprogramm (keinerlei Natter-Besonderheiten):

``` python
name = input("Wie heißt du? ")
alter = int(input("Wie alt bist du? "))
print(f"Hallo {name}, in 10 Jahren bist du {alter + 10}.")
```

### 4.1 Dateien

```
Ampel/
  ampel.natter         Projektdatei (JSON): Name, Typ gui/console, Hauptformular, DB-Einstellungen, Export-Optionen
  main.py              Einstiegspunkt (entspricht .lpr)
  u_main.pfm           Formularbeschreibung für Designer, Inspektor und Design-Prüfer (entspricht .lfm)
  u_main_design.py     aus der .pfm erzeugter Python-Code, nicht bearbeiten
  u_main.py            eigener Code des Formulars
  u_ampel.py           eigene Klasse
  diagramme/           ampel_klassen.pdiag, ampel_zeichnen_struktogramm.pdiag …
  assets/              Bilder, Sounds
  build/               Export-Ausgabe
```

### 4.2 Formularbeschreibung `.pfm`

``` json
{
  "format": "pfm/1",
  "class": "Form1",
  "type": "Form",
  "properties": { "caption": "Ampel", "width": 480, "height": 360, "theme": "system" },
  "events": { "on_create": "form_create" },
  "children": [
    {
      "name": "b_ein", "type": "Button",
      "properties": { "caption": "Einschalten", "left": 24, "top": 24,
                      "width": 120, "height": 32, "variant": "primary" },
      "events": { "on_click": "b_ein_click" }
    },
    {
      "name": "s_rot", "type": "Shape",
      "properties": { "shape": "circle", "left": 200, "top": 24,
                      "width": 64, "height": 64, "brush_color": "#000000" }
    }
  ]
}
```

- Die `.pfm` ist die einzige Quelle für den Designer. Sie wird nie aus Python-Code zurückgelesen, dadurch kann eigener Code den Designer nicht beschädigen.
- Gespeichert werden nur Eigenschaften, die vom Standardwert abweichen (wie in `.lfm`).
- Zur Laufzeit und in der `.exe` wird die `.pfm` nicht benötigt.

### 4.3 Erzeugter Formular-Code und eigener Code

`u_main_design.py` (automatisch erzeugt bei jeder Änderung im Designer oder Inspektor):

``` python
# Automatisch erzeugt aus u_main.pfm - nicht bearbeiten
from pcl import Form, Button, Shape


class Form1Design(Form):
    b_ein: Button
    s_rot: Shape

    def create_components(self):
        self.caption = "Ampel"
        self.width = 480
        self.height = 360
        self.on_create = self.form_create

        self.b_ein = Button(self)
        self.b_ein.caption = "Einschalten"
        self.b_ein.left = 24
        self.b_ein.top = 24
        self.b_ein.width = 120
        self.b_ein.height = 32
        self.b_ein.variant = "primary"
        self.b_ein.on_click = self.b_ein_click

        self.s_rot = Shape(self)
        self.s_rot.shape = "circle"
        self.s_rot.left = 200
        self.s_rot.top = 24
        self.s_rot.width = 64
        self.s_rot.height = 64
        self.s_rot.brush.color = "#000000"
```

Jede Zeile im erzeugten Code entspricht genau einer Zeile im Objektinspektor. Genau diese Zuweisungen kann man im eigenen Code zur Laufzeit ebenfalls schreiben.

`u_ampel.py` (eigene Klasse, reines Python):

``` python
class Ampel:
    def __init__(self):
        self.__eingeschaltet = False
        self.__zustand = "rot"

    def einschalten(self):
        self.__eingeschaltet = True

    def get_zustand(self) -> str:
        return self.__zustand
```

`u_main.py` (eigener Formular-Code):

``` python
from u_main_design import Form1Design
from u_ampel import Ampel


class Form1(Form1Design):
    def form_create(self, sender):
        self.ampel = Ampel()

    def b_ein_click(self, sender):
        self.ampel.einschalten()
        self.ampel_zeichnen()

    def ampel_zeichnen(self):
        if self.ampel.get_zustand() == "rot":
            self.s_rot.brush.color = "#e53935"
```

`main.py`:

``` python
from pcl import Application
from u_main import Form1

app = Application()
app.run(Form1)
```

### 4.4 Synchronisation Designer ↔ Code

| Aktion                                                                | Wirkung                                                                                             |
|-----------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| Komponente hinzufügen / verschieben / Eigenschaft im Inspektor ändern | `.pfm` speichern, `u_main_design.py` neu erzeugen                                                   |
| Doppelklick auf Ereignis / Komponente                                 | Methode `def <name>_<ereignis>(self, sender):` in `u_main.py` einfügen (libcst), Editor springt hin |
| Ereignis im Inspektor per Auswahlliste zuordnen                       | vorhandene passende Methode aus `u_main.py` wird verknüpft                                          |
| Komponente umbenennen                                                 | Rückfrage, dann Umbenennung der Handler und aller `self.<name>`-Verwendungen                        |
| Komponente mit Handlern löschen                                       | Rückfrage, Handler bleiben erhalten und werden als verwaist gemeldet                                |

## 5. Komponentenbibliothek `pcl`

### 5.0 Eigenschaften-System: eine Quelle für Inspektor und Code

Jede Eigenschaft wird einmal in der Komponentenklasse definiert. Daraus ergeben sich automatisch das Python-Attribut, die Zeile im Objektinspektor, der passende Eingabe-Editor, der Standardwert und der Hilfetext.

``` python
class Button(Control):
    caption = Prop(str, "Button", category="Darstellung",
                   doc="Beschriftung des Buttons")
    enabled = Prop(bool, True, category="Verhalten",
                   doc="Legt fest, ob der Button angeklickt werden kann")
    align = Prop(Align, Align.NONE, category="Layout",
                 doc="Ausrichtung im übergeordneten Element")
    font = Prop(Font, category="Darstellung",
                doc="Schriftart, -größe, -farbe und -stil")
    on_click = Event(doc="Wird beim Klicken ausgelöst")
```

Verhalten:

- `self.b_ok.caption = "OK"` ändert sofort die Anzeige im laufenden Programm (Python-`property` mit Setter auf das Qt-Widget)
- Lesen liefert immer den aktuellen Wert, z. B. `self.e_name.text` nach einer Eingabe
- Falsche Typen werden mit verständlicher Meldung abgewiesen: `caption erwartet Text (str), erhalten wurde eine Zahl (int)`
- Unbekannte Eigenschaften lösen einen Fehler aus, statt stillschweigend ein neues Attribut anzulegen (Tippfehler `self.b_ok.captoin = ...` wird sofort gemeldet)
- Neue Komponenten erscheinen ohne Zusatzarbeit im Inspektor, weil der Inspektor die `Prop`-Definitionen der Klasse ausliest
- Eigene Attribute auf dem Formular (`self.ampel = Ampel()`) bleiben erlaubt; die Sperre gilt nur für Komponenten

Zuordnung Datentyp → Editor im Objektinspektor:

| Typ                                             | Editor                                                 |
|-------------------------------------------------|--------------------------------------------------------|
| `str`                                           | Textfeld                                               |
| `int`, `float`                                  | Zahlenfeld mit Pfeiltasten und Mausrad                 |
| `bool`                                          | Kontrollkästchen mit `True`/`False`                    |
| Aufzählung (`Align`, `BorderStyle`, `Cursor` …) | Auswahlliste                                           |
| Menge (`anchors`, `border_icons`)               | aufklappbar, ein Kontrollkästchen pro Wert             |
| `Color`                                         | Farbfeld + Farbwähler + benannte Farben + Theme-Farben |
| `Font`, `Constraints`, `Brush`, `Pen`           | aufklappbare Untereigenschaften + optionaler Dialog    |
| `Strings` (`items`, `lines`)                    | mehrzeiliger Listen-Editor                             |
| `Picture`, `Icon`                               | Datei wählen, Vorschau, Kopie nach `assets/`           |
| Verweis (`data_source`, `popup_menu`)           | Auswahlliste passender Komponenten auf dem Formular    |

### 5.1 Namensstil (Python)

Klassen ohne `T`-Präfix, Eigenschaften und Ereignisse in `snake_case`. Die Präfix-Namenskonvention aus dem Unterricht (`b_`, `e_`, `l_` …) wird vom Designer beim Anlegen vorgeschlagen und vom Design-Prüfer kontrolliert.

| Lazarus                           | Natter                                              |
|-----------------------------------|----------------------------------------------------|
| `l_name.Caption := 'Hallo';`      | `self.l_name.caption = "Hallo"`                    |
| `name := e_eingabe.Text;`         | `name = self.e_eingabe.text`                       |
| `m_ausgabe.Lines.Add('x');`       | `self.m_ausgabe.lines.add("x")`                    |
| `sg_tab.Cells[1,2] := 'x';`       | `self.sg_tab.cells[1, 2] = "x"`                    |
| `case rg_wahl.ItemIndex of`       | `match self.rg_wahl.item_index:`                   |
| `Form1.Color := clRed;`           | `self.color = Color.RED`                           |
| `s_lampe.Brush.Color := clGreen;` | `self.s_lampe.brush.color = Color.GREEN`           |
| `i_bild.Picture.LoadFromFile(p);` | `self.i_bild.picture.load_from_file(p)`            |
| `ShowMessage('x');`               | `show_message("x")`                                |
| `InputBox('T','F','');`           | `input_box("T", "F", "")`                          |
| `StrToInt(s)` / `IntToStr(i)`     | `int(s)` / `str(i)`                                |
| `Format('%.4d',[n])`              | `f"{n:04d}"`                                       |
| `FloatToStrF(x, ffFixed, 0, 2)`   | `f"{x:.2f}"`                                       |
| `OpenURL('website.html')`         | `open_url("website.html")`                         |
| `m_text.Lines.LoadFromFile(p)`    | `self.m_text.lines.load_from_file(p)`              |
| `sg_tab.LoadFromCSVFile(p, ';')`  | `self.sg_tab.load_from_csv_file(p, delimiter=";")` |

Eine vollständige Umstiegs-Referenz Pascal → Python (Datentypen, Strings, Arrays/Records, Dateien, Klassen, Vererbung) ist offline unter „Hilfe → Umstieg Pascal → Python“ verfügbar.

### 5.2 Komponenten (Umfang MVP)

| Palette         | Komponenten                                                                                                                            | Qt-Basis                                                           |
|-----------------|----------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| Standard        | Form, Label, Edit, Button, CheckBox, RadioButton, RadioGroup, Memo, ComboBox, ListBox, ScrollBar, GroupBox, Panel, MainMenu, PopupMenu | QWidget, QLabel, QLineEdit, QPushButton …                          |
| Additional      | StringGrid, Image, Shape, SpinEdit, FloatSpinEdit, MaskEdit, PaintBox, HtmlViewer                                                      | QTableWidget, QLabel+Pixmap/QMovie, eigenes Painting, QTextBrowser |
| Common Controls | TrackBar, ProgressBar, DateEdit, TimeEdit, Calendar                                                                                    | QSlider, QProgressBar, QDateEdit, QTimeEdit, QCalendarWidget       |
| Chart | Chart (Balken, Linie, Kreis, Punkte) | matplotlib eingebettet (`FigureCanvasQTAgg`), Stil aus den Design-Tokens |
| System          | Timer, Sound (WAV, MP3)                                                                                                                | QTimer, QMediaPlayer                                               |
| Dialoge         | show_message, input_box, message_dlg, OpenDialog, SaveDialog, SelectDirectoryDialog, ColorDialog, FontDialog                           | QMessageBox, QInputDialog, QFileDialog, QColorDialog, QFontDialog  |
| SQLdb           | SQLite3Connection, MySQLConnection, SQLTransaction, SQLQuery, DataSource                                                               | eigene Klassen auf DB-API                                          |
| Data Controls   | DBGrid, DBEdit, DBText, DBNavigator, DBComboBox                                                                                        | QTableView + eigenes Model                                         |

Später: PageControl, TreeView, StatusBar.

### 5.3 Layout

- Absolute Positionierung wie in Lazarus (`left`, `top`, `width`, `height`) mit 8-px-Raster
- `anchors` und `align` (`top`, `bottom`, `left`, `right`, `client`) für Größenänderungen des Fensters
- Optional Layout-Container (`FlowPanel`, `GridPanel`) für moderne, responsive Formulare
- High-DPI: alle Maße in logischen Pixeln, korrekte Darstellung bei 125 % / 150 % Windows-Skalierung

### 5.4 Ereignisse

| Ereignis                                                          | Komponenten                                                               | Handler-Signatur                      |
|-------------------------------------------------------------------|---------------------------------------------------------------------------|---------------------------------------|
| `on_click`, `on_double_click`                                     | alle sichtbaren                                                           | `(self, sender)`                      |
| `on_change`                                                       | Edit, Memo, ComboBox, CheckBox, TrackBar, ScrollBar, SpinEdit, DateEdit … | `(self, sender)`                      |
| `on_enter`, `on_exit`                                             | eingabefähige Komponenten (Fokus erhalten/verlieren)                      | `(self, sender)`                      |
| `on_key_down`, `on_key_up`                                        | Formular (`key_preview`), eingabefähige Komponenten                       | `(self, sender, key, shift)`          |
| `on_key_press`                                                    | wie oben                                                                  | `(self, sender, zeichen)`             |
| `on_mouse_down`, `on_mouse_up`, `on_mouse_move`, `on_mouse_wheel` | alle sichtbaren                                                           | `(self, sender, button, shift, x, y)` |
| `on_paint`                                                        | PaintBox, Form                                                            | `(self, sender)` mit `sender.canvas`  |
| `on_timer`                                                        | Timer                                                                     | `(self, sender)`                      |
| `on_select_cell`, `on_edit_cell`                                  | StringGrid                                                                | `(self, sender, spalte, zeile)`       |
| `on_create`, `on_show`, `on_resize`                               | Form                                                                      | `(self, sender)`                      |
| `on_close_query`                                                  | Form (Schließen abfragen/verhindern)                                      | `(self, sender) -> bool`              |
| `on_close`                                                        | Form                                                                      | `(self, sender)`                      |

Canvas der PaintBox: `line_to`, `move_to`, `rectangle`, `ellipse`, `text_out`, `pen`, `brush`, `font` (entspricht `TCanvas`).

### 5.5 Fehlerbehandlung in der Runtime

Qt verschluckt Ausnahmen in Ereignis-Handlern. `pcl` fängt sie ab, meldet sie an Debugger bzw. Fehlerdialog und verhindert stilles Weiterlaufen mit falschem Zustand.

GUI-Programme haben keine Konsole. Ruft Schülercode in einem GUI-Projekt `input()` auf, meldet `pcl` einen Fehler aus dem Fehlerkatalog statt zu hängen oder abzustürzen.

## 6. Design-System (IDE und Schülerprogramme)

**Design-Tokens** in einer zentralen `tokens.json`, daraus werden erzeugt: QSS für die IDE, QSS für `pcl`-Programme, Monaco-Themes.

| Token-Gruppe | Beispiele                                                                               |
|--------------|-----------------------------------------------------------------------------------------|
| Farben       | `bg`, `surface`, `border`, `text`, `text_muted`, `accent`, `danger`, `success`, `focus` |
| Abstände     | 4 / 8 / 12 / 16 / 24 px                                                                 |
| Radius       | 4 px (Eingaben), 6 px (Buttons), 8 px (Panels)                                          |
| Schrift      | Segoe UI Variable, Fallback Segoe UI; 10 / 12 / 14 / 20 pt                              |
| Zustände     | hover, pressed, focus (sichtbarer Fokusrahmen), disabled                                |

- **IDE:** helles und dunkles Theme angelehnt an VS Code „Light Modern“ / „Dark Modern“, umschaltbar, Option „wie Windows“
- **Diagramme:** eigene Stilvorlagen auf Basis der Tokens (siehe 13.6)
- **Schülerprogramme:** modernes, flaches Standard-Design (nicht Windows-95-Optik); Formular-Eigenschaft `theme` = `system` / `light` / `dark`; Akzentfarbe einstellbar; Buttons mit `variant` = `primary` / `secondary` / `danger` / `flat`
- Eigene Farben/Schriften pro Komponente bleiben möglich (Unterrichtsinhalt), der Design-Prüfer weist aber auf Kontrast- und Konsistenzprobleme hin

## 7. IDE-Aufbau

### 7.1 Hauptfenster

```
┌ ● garten – u_garten.py – Natter ────────────────────────────────────────────── ─  □  ✕ ┐
│ Datei  Bearbeiten  Suchen  Ansicht  Quelltext  Projekt  Start  Pakete  Werkzeuge  Fenster  Hilfe │
├───────────────────────────────────────┬──────────────────────────────────────────────────┤
│ [Unit][Formular] [Öffnen▾][Spei][Alle] │ Standard │ Zusätzlich │ Allgemein │ Dialoge │ …  │
│ [Units][Formulare] [▶▾][⏸][■] [↓][→][↑]│  ↖   ▭  ▤  Ok  Abc  [abc]  ☑  ◉  ≡  …        »   │
├──┬──────────────┬──────────────────────┴───────────────────────────┬──────────────────────┤
│E │ PROJEKT      │ u_main.py │ u_garten.py ● │ u_pflanzen.py │ Form1 │ Objektinspektor      │
│S │ ▾ Formulare  │                                                  │                      │
│D │   u_main     │   Monaco-Editor bzw. Formular-Designer           │                      │
│DB│ ▾ Units      │                                                  │                      │
│  │   u_garten   ├──────────────────────────────────────────────────┤                      │
│  │   u_pflanzen │ Meldungen │ Ausgabe │ Variablen │ Aufrufstapel     │                      │
├──┴──────────────┴──────────────────────────────────────────────────┴──────────────────────┤
│ garten │ Python 3.13 (portabel) │ Zeile 12, Spalte 8 │ bereit │ Dunkel                       │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

- Windows-Titelleiste mit hell/dunkel passend zum Theme; Titel: Projekt – aktive Datei – Programmname, `●` bei ungespeicherten Änderungen
- Menüleiste, Werkzeugleisten und Komponentenpalette oben wie in Lazarus, restliche Oberfläche im VS-Code-Stil
- Alle Bereiche ein-/ausblendbar und verschiebbar; „Fenster → Layout zurücksetzen“
- Aktivitätsleiste links (im Bild E, S, D, DB): Explorer/Projekt, Suche, Debug, Datenbank

### 7.2 Menüs

Jeder Eintrag hat Symbol, Tastenkürzel (rechts angezeigt) und ist deaktiviert, wenn er gerade nicht anwendbar ist. Alle Einträge sind auch über die Befehlspalette erreichbar.

| Menü           | Einträge                                                                                                                                                                                                                                                                                                                                                                                                     |
|----------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Datei**      | Neue Unit · Neues Formular · Neu … · Neues Projekt … · Öffnen … · Zuletzt geöffnet › · Wiederherstellen (letzten gespeicherten Stand laden) · Unit öffnen … · Speichern · Speichern unter … · Alles speichern · Als HTML exportieren · Im Browser öffnen (bei `.html`) · Seite schließen · Alle schließen · Verzeichnis säubern … (`__pycache__`, `build/`) · Drucken … · Einstellungen · Neustart · Beenden |
| **Bearbeiten** | Rückgängig · Wiederholen · Ausschneiden · Kopieren · Einfügen · Alles auswählen · Einrücken · Ausrücken · Zeile kommentieren · Zeile duplizieren · Zeile nach oben/unten · Cursor hinzufügen                                                                                                                                                                                                                 |
| **Suchen**     | Suchen … · Weitersuchen · Ersetzen … · In Dateien suchen … · Gehe zu Zeile … · Gehe zu Definition · Verwendungen finden · Gehe zu Symbol …                                                                                                                                                                                                                                                                   |
| **Ansicht**    | Objektinspektor · Projekt-Explorer · Komponentenpalette · Meldungen · Ausgabe · Debug-Fenster › (Variablen, Überwachte Ausdrücke, Aufrufstapel, Breakpoints) · Formular/Code umschalten · Units anzeigen … · Formulare anzeigen … · Tests · Minimap · Zoom › · Design › (Hell, Dunkel, wie Windows) · Befehlspalette                                                                                         |
| **Quelltext**  | Unit einbinden … · Importe ordnen · Dokument formatieren · Umbenennen … · Kommentar umschalten · Methodenrumpf erzeugen · Code-Vorlage einfügen …                                                                                                                                                                                                                                                            |
| **Projekt**    | Neues Projekt … · Projekt öffnen … · Zuletzt geöffnete Projekte › · Projekt speichern · Projekt schließen · Projekt-Inspektor · Datei zum Projekt hinzufügen … · Datei aus Projekt entfernen · Formulare … · Projektoptionen … (Hauptformular, Projekttyp, Symbol, Version)                                                                                                                                  |
| **Start**      | Starten mit Debugger · Starten ohne Debugger · Pause · Stopp · Neu starten · Einzelschritt · Prozedurschritt · Rücksprung · Ausführen bis Cursor · Breakpoint umschalten · Alle Breakpoints entfernen · Prüfen (ohne Start) · Tests ausführen · Exe erstellen …                                                                                                                                              |
| **Pakete**     | Paketverwaltung … (Projekt-Pakete anzeigen, Zusatzpakete installieren/entfernen) · Paket installieren … · Paketliste exportieren (`requirements.txt`)                                                                                                                                                                                                                                                        |
| **Werkzeuge**  | Diagramm-Editor öffnen · Design prüfen · Lazarus-Formular importieren … · Datenbank-Explorer · CSV in Datenbank importieren … · Tastenkürzel · Umgebung prüfen/reparieren · Einstellungen                                                                                                                                                                                                                    |
| **Fenster**    | Nächster Tab · Vorheriger Tab · Editor teilen › (rechts, unten) · Liste offener Dateien … · Layout zurücksetzen                                                                                                                                                                                                                                                                                              |
| **Hilfe**      | Kontexthilfe · Tastenkürzel-Übersicht · Komponenten-Referenz · Umstieg Pascal → Python · Fehlerkatalog · Erste Schritte · Über                                                                                                                                                                                                                                                                               |

### 7.3 Werkzeugleisten und Komponentenpalette

**Werkzeugleiste 1 (Datei):** Neue Unit · Neues Formular | Öffnen ▾ (mit zuletzt geöffneten Dateien) · Speichern · Alles speichern | Formular/Code umschalten · Formular anzeigen ▾

**Werkzeugleiste 2 (Projekt/Start):** Units anzeigen · Formulare anzeigen | Prüfen | Starten ▾ (mit/ohne Debugger, Exe erstellen) · Pause · Stopp | Einzelschritt · Prozedurschritt · Rücksprung

Symbole als SVG im einheitlichen Linienstil; farbige Akzente nur bei Start (grün), Stopp (rot) und Speichern, damit sie wie in Lazarus schnell erkennbar sind. Tooltip mit Name und Tastenkürzel.

**Komponentenpalette** mit Reitern:

| Reiter         | entspricht Lazarus  | Komponenten                                                                                                                      |
|----------------|---------------------|----------------------------------------------------------------------------------------------------------------------------------|
| Standard       | Standard            | MainMenu, PopupMenu, Button, Label, Edit, Memo, CheckBox, RadioButton, ListBox, ComboBox, ScrollBar, GroupBox, RadioGroup, Panel |
| Zusätzlich     | Additional          | StringGrid, Image, Shape, SpinEdit, FloatSpinEdit, MaskEdit, PaintBox, HtmlViewer                                                |
| Allgemein      | Common Controls     | TrackBar, ProgressBar, DateEdit, TimeEdit, Calendar (später PageControl, TreeView, StatusBar)                                    |
| Dialoge        | Dialogs             | OpenDialog, SaveDialog, SelectDirectoryDialog, ColorDialog, FontDialog                                                           |
| Datensteuerung | Data Controls       | DBGrid, DBEdit, DBText, DBNavigator, DBComboBox                                                                                  |
| Datenzugriff   | Data Access / SQLdb | DataSource, SQLite3Connection, MySQLConnection, SQLTransaction, SQLQuery                                                         |
| System         | System              | Timer, Sound                                                                                                                     |
| Diagramm       | Chart               | Chart                                                                                                                            |

- Auswahlpfeil ganz links; Klick auf Komponente, dann Klick ins Formular platziert sie; Doppelklick setzt sie mittig ins aktive Formular; Umschalt+Klick für mehrfaches Platzieren
- Tooltip mit deutschem Namen und Kurzbeschreibung („Button – Schaltfläche für Klick-Ereignisse“)
- `»` am rechten Rand für nicht sichtbare Komponenten bei schmalem Fenster
- Suchfeld zum Filtern der Komponenten
- Nicht-visuelle Komponenten (Timer, SQLQuery …) erscheinen im Designer als kleines Symbol

### 7.4 Units und Projekte aus mehreren Dateien

Beispiel mit mehreren Units:

`u_pflanzen.py`

``` python
class Pflanze:
    def __init__(self, name: str, wasserbedarf: int):
        self.name = name
        self.wasserbedarf = wasserbedarf
```

`u_garten.py`

``` python
from u_pflanzen import Pflanze


class Garten:
    def __init__(self):
        self.beete: list[Pflanze] = []

    def pflanzen(self, pflanze: Pflanze):
        self.beete.append(pflanze)
```

`u_main.py`

``` python
from u_main_design import Form1Design
from u_garten import Garten
from u_pflanzen import Pflanze
```

| Funktion                     | Verhalten                                                                                                                                                               |
|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Neue Unit                    | legt `u_neu1.py` an, fragt beim ersten Speichern nach dem Namen, fügt die Datei dem Projekt hinzu                                                                       |
| Neues Formular               | legt `u_form2.py`, `u_form2.pfm` und `u_form2_design.py` an und öffnet den Designer                                                                                     |
| Unit einbinden …             | Dialog mit allen Projekt-Units und ihren Klassen/Funktionen; bereits eingebundene sind ausgegraut; fügt `from u_garten import Garten` im Importblock oben ein, sortiert |
| Autovervollständigung        | schlägt Klassen aus anderen Units vor und ergänzt auf Wunsch den Import                                                                                                 |
| Unit öffnen …                | Schnellauswahl aller Projektdateien mit Suche                                                                                                                           |
| Tabs                         | jede Unit in eigenem Tab, `●` bei Änderungen, Strg+Tab wechselt, Tabs anheften und per Drag & Drop sortieren                                                            |
| Nacheinander / nebeneinander | Editor teilen rechts oder unten, bis zu 3 Bereiche; z. B. `u_pflanzen.py` links, `u_garten.py` rechts                                                                   |
| Gehe zu Definition           | Strg+Klick auf `Pflanze` öffnet `u_pflanzen.py` an der Klasse                                                                                                           |
| Debugger                     | Einzelschritt in eine andere Unit öffnet diese automatisch                                                                                                              |
| Projekt-Explorer             | Gruppen Formulare, Units, Assets; Formular-Units als ein Eintrag, `.pfm` und `_design.py` darunter eingeklappt (optional ausblendbar)                                   |
| Unit umbenennen              | Rückfrage, dann werden alle Importe in anderen Units angepasst                                                                                                          |
| Kreisbezüge                  | Warnung im Panel „Meldungen“, wenn sich zwei Units gegenseitig einbinden                                                                                                |
| Sitzung                      | offene Tabs, Cursorpositionen, geteilte Ansicht und Breakpoints werden pro Projekt gespeichert (`.natter-session`, entspricht `.lps`)                                    |

Weitere Formulare werden im Code wie normale Python-Objekte erzeugt:

``` python
from u_form2 import Form2

def b_details_click(self, sender):
    self.form2 = Form2()
    self.form2.show()          # oder self.form2.show_modal()
```

Der Projektordner ist Import-Wurzel. Unterordner sind möglich und werden als Python-Pakete behandelt.

### 7.5 Neu-Dialog und Vorlagen

„Datei → Neu …“ öffnet einen Dialog mit Vorschau und Beschreibung:

| Kategorie | Vorlagen                                                                                                                                       |
|-----------|------------------------------------------------------------------------------------------------------------------------------------------------|
| Projekt   | GUI-Anwendung, Konsolenanwendung, GUI-Anwendung mit Datenbank                                                                                  |
| Datei     | Unit (leer), Klassen-Unit, Formular, Datenbank-Formular, Textdatei                                                                             |
| Diagramm  | Klassendiagramm, Use-Case-Diagramm, Aktivitätsdiagramm, Zustandsdiagramm, Sequenzdiagramm, Struktogramm, Entscheidungstabelle, leeres Diagramm |

Klassen-Unit:

``` python
class NeueKlasse:
    def __init__(self):
        pass
```

### 7.6 Objektinspektor

Aufbau und Bedienung wie in Lazarus, Optik im VS-Code-Stil:

```
┌ Komponentenbaum ─────────────────────────┐
│ ▾ Form1: Form                            │
│     b_ein: Button                        │
│     s_rot: Shape                         │
├──────────────────────────────────────────┤
│ [Filter …                            ] ⨯ │
│ Eigenschaften │ Ereignisse │ Favoriten │ Geändert │
├───────────────┬──────────────────────────┤
│   align       │ NONE                   ▾ │
│ › anchors     │ {TOP, LEFT}              │
│   caption     │ Einschalten              │  ← geänderter Wert hervorgehoben
│   color       │ ■ DEFAULT              ▾ │
│   enabled     │ ☑ True                   │
│ › font        │ (Font)                   │
│   height      │ 32                       │
├───────────────┴──────────────────────────┤
│ Beschriftung des Buttons                 │
│ Button.caption: str                      │
└──────────────────────────────────────────┘
```

| Funktion              | Beschreibung                                                                                      |
|-----------------------|---------------------------------------------------------------------------------------------------|
| Komponentenbaum       | alle Komponenten mit Verschachtelung; Auswahl synchron mit dem Designer                           |
| Filter                | Eigenschaften nach Namen filtern                                                                  |
| Reiter Eigenschaften  | alphabetisch oder nach Kategorie gruppiert (umschaltbar)                                          |
| Reiter Ereignisse     | Doppelklick erzeugt Methode; Auswahlliste mit passenden vorhandenen Methoden; „Zum Code springen“ |
| Reiter Favoriten      | selbst angeheftete Eigenschaften pro Komponententyp                                               |
| Reiter Geändert       | nur Eigenschaften, die vom Standardwert abweichen (ersetzt „Bedingte Eigenschaften“ aus Lazarus)  |
| Hervorhebung          | abweichende Werte fett in Akzentfarbe; Rechtsklick „Auf Standardwert zurücksetzen“                |
| Untereigenschaften    | aufklappbar (`font.size`, `anchors`, `constraints.min_width`)                                     |
| Hilfebereich          | Beschreibung und Python-Signatur der gewählten Eigenschaft, z. B. `Button.caption: str`           |
| Spaltentrenner        | verschiebbar, Namen werden nicht abgeschnitten (Tooltip bei schmaler Spalte)                      |
| Mehrfachauswahl       | gemeinsame Eigenschaften mehrerer Komponenten gleichzeitig ändern                                 |
| Tastatur              | Pfeiltasten, Enter übernimmt, Esc verwirft, Tab zum nächsten Feld                                 |
| Live-Wirkung          | jede Änderung sofort im Designer sichtbar und Rückgängig-fähig                                    |
| Während des Debuggens | Variablen-Panel zeigt Komponenten mit denselben Eigenschaftsnamen                                 |

### 7.7 Designer

Platzieren per Klick oder Drag & Drop, Verschieben, Größenanfasser, Mehrfachauswahl (Rahmen, Strg+Klick), Hilfslinien und Einrasten, Ausrichten/Verteilen, Tab-Reihenfolge, Z-Reihenfolge, Kopieren/Einfügen, Rückgängig/Wiederholen (Command-Pattern), Vorschau hell/dunkel und in mehreren Fenstergrößen. Der Designer rendert echte `pcl`-Komponenten.

Tastatur im Designer: Pfeiltasten verschieben um einen Rasterschritt, Alt+Pfeil um 1 px, Umschalt+Pfeil ändert die Größe, Entf löscht, Strg+D dupliziert.

### 7.8 Programmausführung in eigenen Fenstern

Ablauf beim Start (F5 mit Debugger, Strg+F5 ohne Debugger): alle Dateien speichern → `u_*_design.py` aktualisieren → Ruff-Prüfung → Start als eigener Prozess mit dem mitgelieferten Python und den Projekt-Paketen.

| Projekttyp | Ausführung                                                                                                                                                         |
|------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| GUI        | nur das Programmfenster als eigenes Fenster mit eigenem Taskleisten-Eintrag, keine Konsole; Ein- und Ausgabe ausschließlich über Komponenten; IDE bleibt bedienbar |
| Konsole    | eigenes Windows-Konsolenfenster (Windows Terminal, falls vorhanden, sonst Eingabeaufforderung); `input()` und `print()` funktionieren direkt                       |

- Nach Programmende bleibt das Konsolenfenster offen („Programm beendet (Code 0). Taste drücken zum Schließen.“), damit Ausgaben lesbar bleiben
- Stopp-Button beendet das Programm samt Unterprozessen
- Beim Anhalten an einem Breakpoint kommt die IDE in den Vordergrund und springt zur Zeile
- Exitcode und Laufzeit werden im Panel „Ausgabe“ angezeigt
- Standardmäßig nur eine laufende Instanz pro Projekt; erneuter Start fragt nach

### 7.9 Tastenkürzel

Standardbelegung wie VS Code (deutsche Tastatur). Übersicht und Anpassung in einem eigenen Tab (Hilfe → Tastenkürzel-Übersicht, `Strg+K Strg+S`):

- durchsuchbare Tabelle mit Befehl, Tastenkürzel, Bereich (Editor, Designer, überall) und Quelle (Standard/eigene)
- Doppelklick auf eine Zeile nimmt ein neues Kürzel auf; Konflikte werden angezeigt
- Suche nach Tastenkombination per Aufnahme
- Zurücksetzen einzelner oder aller Kürzel
- Übersicht als HTML exportieren und drucken

| Aktion                                        | Kürzel                            |
|-----------------------------------------------|-----------------------------------|
| Befehlspalette                                | Strg+Umschalt+P                   |
| Unit öffnen (Schnellauswahl)                  | Strg+P                            |
| Neue Unit                                     | Strg+N                            |
| Öffnen                                        | Strg+O                            |
| Speichern / Speichern unter                   | Strg+S / Strg+Umschalt+S          |
| Alles speichern                               | Strg+K S                          |
| Seite schließen                               | Strg+W                            |
| Nächster Tab                                  | Strg+Tab                          |
| Suchen / Ersetzen / In Dateien suchen         | Strg+F / Strg+H / Strg+Umschalt+F |
| Gehe zu Zeile                                 | Strg+G                            |
| Gehe zu Definition / Verwendungen             | F12 / Umschalt+F12                |
| Umbenennen                                    | F2                                |
| Zeile kommentieren                            | Strg+#                            |
| Dokument formatieren                          | Umschalt+Alt+F                    |
| Starten mit / ohne Debugger                   | F5 / Strg+F5                      |
| Stopp / Neu starten                           | Umschalt+F5 / Strg+Umschalt+F5    |
| Breakpoint umschalten                         | F9                                |
| Prozedurschritt / Einzelschritt / Rücksprung  | F10 / F11 / Umschalt+F11          |
| Seitenleiste / Panel ein-aus                  | Strg+B / Strg+J                   |
| Formular/Code umschalten *(Natter-spezifisch)* | Strg+Alt+F12                      |
| Objektinspektor anzeigen *(Natter-spezifisch)* | Strg+Alt+I                        |
| Unit einbinden *(Natter-spezifisch)*           | Strg+Alt+U                        |
| Diagramm-Editor öffnen *(Natter-spezifisch)*   | Strg+Alt+D                        |
| Alle Tests ausführen                          | Strg+; A                          |
| Kontexthilfe zu Komponente/Eigenschaft/Befehl | Strg+F1                           |
| Tastenkürzel-Übersicht                        | Strg+K Strg+S                     |

## 8. Debugger und Fehlermeldungen

### 8.1 Funktionen

- Breakpoints (Klick in den Rand), später bedingte Breakpoints
- Start, Pause, Fortsetzen, Einzelschritt, Prozedurschritt, Ausführen bis Rücksprung, Ausführen bis Cursor
- Variablen: lokale Variablen, `self` mit Komponenten (nur relevante Eigenschaften wie `text`, `caption`, `checked`, `item_index`), eigene Objekte aufklappbar
- Überwachte Ausdrücke
- Aufrufstapel nur mit eigenem Code (`justMyCode`), `pcl`- und Qt-Interna ausgeblendet
- Anhalten bei unbehandelten Ausnahmen, auch in Ereignis-Handlern

### 8.2 Prüfung vor dem Start

Ruff prüft vor jedem Start auf Syntaxfehler, unbekannte Namen, fehlende Importe und nicht verwendete Variablen. Fehler erscheinen im Panel „Meldungen“ und als Markierung im Editor.

### 8.3 Aufbau einer Fehlermeldung

Jede Meldung besteht aus drei Teilen:

```
Laufzeitfehler: Division durch 0 (ZeroDivisionError)

Wo:   u_main.py, Zeile 42, in b_berechnen_click
          ergebnis = summe / anzahl
                             ^^^^^^
Was:  Es wurde durch 0 geteilt. Der markierte Wert war zu diesem Zeitpunkt 0.
Prüfe: Welche Werte kann der Teiler annehmen? Wird der Fall 0 vorher behandelt?
```

- **Wo:** Datei, Zeile, Methode, genaue Stelle im Ausdruck (Spaltenmarkierung ab Python 3.11)
- **Was:** Fehlerart in verständlichem Deutsch, ggf. mit tatsächlichen Werten zum Fehlerzeitpunkt
- **Prüfe:** allgemeine Leitfragen zur Fehlersuche

### 8.4 Regeln gegen Lösungsvorgaben

Die Meldungen stammen aus einem **festen, von Hand gepflegten Katalog** (deterministisch, keine KI). Dadurch ist genau kontrollierbar, was angezeigt wird.

Jede Meldung hat **immer** genau die drei Teile **Wo**, **Was** und **Prüfe** (siehe 8.3). Es gibt keine abgestuften Hilfen und keine Einstellung dafür.

Erlaubt: Fehlerart, Ort, Werte von Variablen zum Fehlerzeitpunkt, allgemeine Leitfragen.

Nicht erlaubt: korrigierter Code, konkrete Ersatzzeilen, vollständige Anweisungen, „Füge X ein“, Namensvorschläge („Meintest du …?“), Verweise auf Musterlösungen. Die Vorschläge, die Python selbst seit Version 3.12 an manche Fehlermeldungen anhängt („Did you mean …?“), werden entfernt.

### 8.5 Katalog (Auszug, MVP)

| Fehler | Typischer Auslöser im Unterricht | Inhalt von „Was“ und „Prüfe“ |
|----------------------------------------|--------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| SyntaxError, IndentationError          | fehlender Doppelpunkt, falsche Einrückung                                                              | Stelle markiert, Hinweis auf Blockstruktur statt `begin … end`           |
| NameError                              | Tippfehler, Variable vor Zuweisung benutzt, Unit nicht eingebunden                                     | Leitfrage Schreibweise / Zuweisung / Import                              |
| UnboundLocalError                      | globale Variable in Funktion verändert                                                                 | Erklärung lokal/global                                                   |
| AttributeError                         | falsche Komponenten-Eigenschaft, `__attribut` von außen                                                | bei `__attribut`: Erklärung Kapselung und Namensumbildung                |
| TypeError                              | `str + int`, falsche Parameteranzahl, Instanz einer abstrakten Klasse                                  | bei abstrakter Klasse: welche Methoden noch nicht überschrieben sind     |
| ValueError                             | `int("abc")`, `float("3,5")`                                                                           | bei Komma: Hinweis Dezimalpunkt vs. Dezimalkomma                         |
| ZeroDivisionError                      | Division durch 0                                                                                       | Wert des Teilers                                                         |
| IndexError                             | Listenindex, `cells[spalte, zeile]` außerhalb                                                          | gültiger Bereich und verwendeter Index                                   |
| KeyError                               | dict-Schlüssel, pandas-Spaltenname                                                                     | vorhandene Schlüssel bzw. Spaltennamen der Datei                         |
| FileNotFoundError                      | Dateipfad falsch                                                                                       | gesuchter Pfad und aktuelles Arbeitsverzeichnis                          |
| PermissionError                        | Datei noch in Excel geöffnet                                                                           | Hinweis auf geöffnete Datei / Schreibrechte                              |
| UnicodeDecodeError                     | Excel-CSV in Windows-1252                                                                              | Hinweis auf Zeichensatz der Datei                                        |
| pandas `ParserError`, `EmptyDataError` | falsches Trennzeichen, leere Datei                                                                     | erkannte Spaltenanzahl, Hinweis Trennzeichen                             |
| `input()` in GUI-Projekt               | Konsolenbefehl in Formular-Code                                                                        | „In GUI-Programmen erfolgen Eingaben über Komponenten auf dem Formular.“ |
| `pcl`-Fehler                           | unbekannte Eigenschaft, falscher Eigenschaftstyp, Datenbankverbindung, SQL-Fehler, Bild nicht gefunden | Komponente, Eigenschaft, erwarteter Typ                                  |

### 8.6 Test-Explorer

Deckt die Teststufen der Kann-Liste ab (Unit-/Klassen-/Integrationstest, Normal-/Grenz-/Fehlerfall).

- Tests in Dateien `test_*.py` mit `unittest` (Standardbibliothek, reines Python); Vorlage „Test-Unit“ im Neu-Dialog
- Panel „Tests“: Baum aus Dateien, Klassen und Testmethoden mit Status (bestanden/fehlgeschlagen/Fehler) und Laufzeit
- Einzelnen Test, eine Datei oder alle Tests ausführen; Test mit Debugger starten
- Bei fehlgeschlagenen Vergleichen Soll-/Ist-Anzeige: `Soll: 50 · Ist: 45` (aus `assertEqual`), Sprung zur Zeile
- Testergebnisse als HTML exportieren (Testprotokoll)

## 9. Konsolenprojekte

- Vorlage mit `main.py` in reinem Python (`input()`, `print()`, eigene Klassen, Module)
- Ausführung im eigenen Konsolenfenster wie in 7.8 beschrieben; Debugger verbindet sich automatisch
- Farben und Cursorsteuerung über ANSI-Codes funktionieren in Windows Terminal und der Eingabeaufforderung
- Optionales Hilfsmodul `pcl.crt` für den Umstieg aus dem CRT-Unterricht: `clr_scr()`, `goto_xy()`, `text_color()`, `text_background()`, `read_key()`, `key_pressed()`, `delay()`, `beep()`. Es ist selbst reines Python und keine Voraussetzung.

## 10. Datenbankanbindung

### 10.1 Komponenten und Ablauf (wie im Kursmaterial)

``` python
self.query.sql = "SELECT * FROM kunden WHERE ort = :ort"
self.query.params["ort"] = self.e_ort.text
self.query.open()

while not self.query.eof:
    self.m_ausgabe.lines.add(self.query.field_by_name("name").as_string)
    self.query.next()

self.query.close()
```

- `open()` für SELECT, `exec_sql()` für INSERT/UPDATE/DELETE, `transaction.commit()` / `rollback()`
- Parameter immer im Stil `:name`; `pcl` übersetzt intern in den Treiberstil (PyMySQL: `%(name)s`), dadurch ist SQL-Injection-sicheres Arbeiten der Standard
- Designzeit-Aktivierung: `active = True` im Inspektor zeigt echte Daten im DBGrid des Designers
- `DBNavigator` mit Erster/Zurück/Vor/Letzter/Einfügen/Löschen/Speichern/Abbrechen

### 10.2 Datenbank-Panel in der IDE

Verbindung testen, Tabellen und Spalten anzeigen, SQL-Abfragen ausführen, Ergebnis als Tabelle. Zugangsdaten werden nicht im Klartext in der `.pfm` gespeichert, sondern verschlüsselt pro Benutzer (Windows Credential Store); für den Export wählbar.

## 11. Dateien, Bilder, HTML und Datenauswertung

### 11.1 Grundregeln

- **Arbeitsverzeichnis:** beim Start aus der IDE der Projektordner, in der `.exe` der Programmordner. `open("highscore.txt")` funktioniert dadurch wie in Lazarus ohne absolute Pfade.
- **Zeichensatz:** UTF-8 überall (Python-UTF-8-Modus, Konsole auf UTF-8). Umlaute funktionieren in Dateien, Komponenten und Konsole; die Ersatzschreibweise ue/ae/oe ist nicht nötig.
- **Explorer:** aktualisiert sich automatisch, wenn das Programm Dateien anlegt oder ändert.
- **Projektvorlagen** enthalten einen Ordner `daten/`; beim Exe-Export wählbar, ob er mitkopiert wird.

### 11.2 Textdateien

Reines Python, keine Hilfsbibliothek nötig:

| Lazarus                                                   | Python                                                                       |
|-----------------------------------------------------------|------------------------------------------------------------------------------|
| `assignFile` + `reset` + `readLn` bis `EOF` + `closeFile` | `with open("datei.txt", encoding="utf-8") as datei:` + `for zeile in datei:` |
| `rewrite`                                                 | `open("datei.txt", "w", encoding="utf-8")`                                   |
| `append`                                                  | `open("datei.txt", "a", encoding="utf-8")`                                   |
| `writeLn(datei, text)`                                    | `datei.write(text + "\n")`                                                   |
| Trennzeichen mit `Pos`/`Copy`                             | `name, punkte = zeile.strip().split(";")`                                    |

Komponenten mit Datei-Methoden (wie in der LCL):

- `lines.load_from_file(pfad)` / `lines.save_to_file(pfad)` für Memo, ListBox, ComboBox (`items`)
- `load_from_csv_file(pfad, delimiter=";")` / `save_to_csv_file(...)` für StringGrid

### 11.3 HTML-Dateien

- HTML wird wie jede Textdatei mit `open(..., "w")` geschrieben
- Öffnen im Standardbrowser mit `webbrowser.open(...)` (Standardbibliothek) oder `open_url(...)` aus `pcl` (entspricht `OpenURL` aus `LCLIntf`, löst relative Pfade zum Arbeitsverzeichnis auf, funktioniert auch mit `https://`-Adressen)

``` python
from pcl import open_url

with open("website.html", "w", encoding="utf-8") as datei:
    datei.write("<!DOCTYPE html>\n<html><body>\n")
    datei.write("<h1>Highscore</h1>\n")
    datei.write("</body></html>\n")

open_url("website.html")
```

- Komponente **HtmlViewer** zeigt HTML direkt im Formular an (`self.hv_seite.load_from_file("website.html")` oder `.html = "..."`)
- IDE: `.html`-Dateien mit Syntaxhervorhebung, „Im Browser öffnen“ per Rechtsklick/Menü, Vorschau-Tab mit automatischer Aktualisierung beim Speichern

### 11.4 Bilder

- **Image** mit Eigenschaft `picture`: Editor im Objektinspektor mit Datei-Auswahl, Vorschau und automatischer Kopie nach `assets/` (Rückfrage bei gleichem Dateinamen)
- Formate: PNG, JPG, GIF (auch animiert), BMP, ICO, SVG, WEBP
- Eigenschaften wie `TImage`: `stretch`, `proportional`, `center`, `transparent`
- Im Code: `self.i_bild.picture.load_from_file("assets/cookie_boese.png")`, `self.i_bild.picture.clear()`
- Drag & Drop einer Bilddatei aus dem Projekt-Explorer oder Windows-Explorer ins Formular erzeugt eine Image-Komponente mit diesem Bild
- Weitere Bild-Eigenschaften: `icon` des Formulars, `glyph` bei Buttons (Symbol neben dem Text, entspricht BitBtn/SpeedButton)
- Design-Prüfer warnt bei Bildern außerhalb des Projektordners (würden beim Export fehlen)
- IDE: Bilddateien öffnen sich in einem Vorschau-Tab mit Größe und Abmessungen
- Export: `assets/` wird immer mitkopiert

### 11.5 CSV-Dateien

Zwei Wege, beide reines Python:

1.  **Standardbibliothek** `csv` bzw. `split` – entspricht dem Unterrichtsstoff „Datensätze prüfen/zerlegen“
2.  **pandas** – für Auswertungen (11.6)

``` python
import csv

with open("schueler.csv", encoding="utf-8", newline="") as datei:
    for name, vorname, geburtsdatum in csv.reader(datei, delimiter=";"):
        ...
```

- IDE: `.csv` öffnet sich in einer Tabellenansicht mit automatisch erkanntem Trennzeichen und Zeichensatz; umschaltbar zwischen Tabelle und Text; Sortieren/Filtern nur in der Ansicht, Datei bleibt unverändert
- Excel-CSV (Semikolon, Windows-1252, Dezimalkomma) wird erkannt und in der Tabellenansicht angezeigt; Hinweise im Fehlerkatalog, falls das Programm die Datei anders liest

### 11.6 Datenauswertung mit pandas

In den Projekt-Paketen vorinstalliert (offline nutzbar): **pandas, numpy, openpyxl** (Excel-Dateien), **matplotlib**, **SQLAlchemy** (für pandas mit MySQL).

``` python
import pandas as pd

df = pd.read_csv("verkauf.csv", sep=";", decimal=",")
umsatz = df.groupby("region")["umsatz"].sum()

self.sg_auswertung.load_dataframe(umsatz.reset_index())
self.ch_umsatz.add_bar_series(umsatz.index, umsatz.values, title="Umsatz je Region")
```

| Bereich                  | Umsetzung                                                                                                                                                         |
|--------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Einlesen                 | `pd.read_csv`, `pd.read_excel`, `pd.read_sql` (mit Verbindung aus `SQLite3Connection`/`MySQLConnection` über `.engine`)                                           |
| Anzeige im Formular      | `StringGrid.load_dataframe(df)` und `StringGrid.to_dataframe()`                                                                                                   |
| Diagramme im Formular    | Komponente **Chart**: `add_bar_series`, `add_line_series`, `add_pie_series`, `add_scatter_series`, `clear`; nimmt Listen oder pandas-Serien; Farben aus dem Theme |
| Diagramme mit matplotlib | in Konsolenprogrammen und GUI-Programmen per `plt.show()` in eigenem Fenster                                                                                      |
| Speichern                | `df.to_csv(..., sep=";", index=False)`, `df.to_excel(...)`, `df.to_html(...)` + `open_url(...)`                                                                   |
| Debugger                 | DataFrames, Listen, dicts und Listen von Objekten im Variablen-Panel per „Als Tabelle anzeigen“ in einem eigenen Tab (sortier- und filterbar)                     |
| Datenbank                | „Werkzeuge → CSV in Datenbank importieren …“ in eine Import-/Rohtabelle (SQLite oder MySQL), Export einer Tabelle als CSV und SQL-Dump im Datenbank-Panel         |
| Export                   | PyInstaller bindet pandas/matplotlib nur ein, wenn das Projekt sie importiert (ca. +60–100 MB)                                                                    |

## 12. Abgleich mit Kursmaterial und Kann-Liste

| Thema (Kursmaterial / Kann-Liste)                                 | Lazarus                                            | Umsetzung                                                                            | Abschnitt         |
|-------------------------------------------------------------------|----------------------------------------------------|--------------------------------------------------------------------------------------|-------------------|
| Konsolen-Ein-/Ausgabe                                             | `writeln`, `readln`                                | `print`, `input` im eigenen Konsolenfenster                                          | 7.8, 9            |
| Zufallszahlen                                                     | `randomize`, `random`                              | `random` (Standardbibliothek)                                                        | –                 |
| CRT, Sound, Verzögerung                                           | `crt`                                              | `pcl.crt` (optional)                                                                 | 9                 |
| Zeichencodierung, Umlaute                                         | `ord`, `chr`, Codepage 437/ANSI                    | `ord`, `chr`, UTF-8 überall                                                          | 11.1              |
| Datentypen inkl. Datum/Zeit                                       | Integer, Double, Boolean, Char, String, TDateTime  | `int`, `float`, `bool`, `str`, `datetime`; DateEdit, TimeEdit, Calendar              | 5.2               |
| Strings und Konvertierung                                         | `Copy`, `Pos`, `Length`, `StrToInt`, `FloatToStrF` | Slicing, `find`, `len`, `int()`, f-Strings; Katalog-Hinweis Dezimalkomma             | 5.1, 8.5          |
| Eingaben validieren                                               | MaskEdit, eigene Prüfung                           | MaskEdit (`edit_mask`), eigene Prüfung                                               | 5.2               |
| Arrays, Records, dynamische Arrays, Listen                        | `array`, `record`, `SetLength`                     | `list`, `dataclass`, `list`                                                          | Umstiegs-Referenz |
| Tabellenalgorithmen, Suche, Sortierung                            | eigene Implementierung                             | eigene Implementierung; Debugger-Tabellenansicht für Listen                          | 11.6              |
| Prozeduren/Funktionen, lokal/global                               | `procedure`, `function`, `result`                  | `def`, `return`, `global`; Katalog UnboundLocalError                                 | 8.5               |
| Units                                                             | `uses`, interface/implementation                   | Module, Unit einbinden                                                               | 7.4               |
| GUI-Komponenten und Ereignisse                                    | LCL                                                | `pcl`-Komponenten, Ereignisliste                                                     | 5.2, 5.4          |
| Bilder einfügen                                                   | TImage, `Picture.LoadFromFile`                     | Image, `picture.load_from_file`                                                      | 11.4              |
| Zeichnen                                                          | TShape, TCanvas                                    | Shape, PaintBox mit Canvas                                                           | 5.2, 5.4          |
| Dialoge                                                           | `ShowMessage`, `InputBox`, `MessageDlg`            | `show_message`, `input_box`, `message_dlg`                                           | 5.2               |
| Mehrere Formulare                                                 | `Form2.Show`                                       | `Form2().show()`                                                                     | 7.4               |
| Klassen, Sichtbarkeit, Getter/Setter                              | `class`, private/protected/public                  | `class`, `_`/`__`, `@property`; Katalog-Hinweis Kapselung                            | 8.5               |
| Vererbung, abstrakte Klassen, Polymorphie                         | `virtual`, `abstract`, `override`, `inherited`     | Vererbung, `abc.ABC`, `@abstractmethod`, `super()`; Katalog-Hinweis abstrakte Klasse | 8.5               |
| Beziehungen, 1:n                                                  | Referenzen, dynamische Arrays                      | Referenzen, Listen von Objekten                                                      | –                 |
| Textdateien, Trennzeichen                                         | `assignFile`, `readLn`, `writeLn`                  | `open`, `with`, `split`                                                              | 11.2              |
| CSV-Dateien                                                       | Textdatei + Trennzeichen                           | `csv`, pandas, StringGrid-CSV-Methoden                                               | 11.5, 11.6        |
| HTML-Dateien                                                      | `writeLn` + `OpenURL`                              | `write` + `open_url`/`webbrowser`                                                    | 11.3              |
| Testen, Grenzfälle, Soll/Ist                                      | manuell                                            | Test-Explorer mit `unittest`                                                         | 8.6               |
| Syntax-, Laufzeit-, Logikfehler beheben                           | Nachrichtenzeile, Debugger                         | Ruff-Prüfung, Debugger, Fehlerkatalog                                                | 8                 |
| Datenbankanbindung                                                | SQLdb-Komponenten                                  | SQLdb-Komponenten, pandas `read_sql`                                                 | 10, 11.6          |
| Daten übernehmen (CSV → Importtabelle)                            | phpMyAdmin                                         | Datenbank-Panel: CSV-Import, CSV-/SQL-Export                                         | 11.6              |
| Programm weitergeben                                              | Kompilat                                           | Exe-Export                                                                           | 16                |
| Struktogramm, Entscheidungstabelle                                | Papier / DIA                                       | Diagramm-Editor, manuell                                                             | 13                |
| UML: Klassen-, Use-Case-, Aktivitäts-, Zustands-, Sequenzdiagramm | DIA                                                | Diagramm-Editor, manuell                                                             | 13                |

## 13. Diagramm-Editor (UML, Struktogramme, Entscheidungstabellen)

### 13.1 Grundsätze

- **Eigenes Fenster** mit eigenem Taskleisten-Eintrag, unabhängig vom Hauptfenster verschiebbar (z. B. auf einen zweiten Bildschirm)
- **Nur manuelles Zeichnen** wie in DIA: Formen aus einer Palette auf die Zeichenfläche ziehen, beschriften, verbinden, anordnen
- **Keine automatische Erzeugung** aus Code, keine automatische Umwandlung zwischen Diagramm und Code, keine inhaltliche Prüfung der Notation
- Diagramme sind normale Projektdateien (`.pdiag`) im Ordner `diagramme/` und erscheinen im Projekt-Explorer; Doppelklick öffnet sie im Diagramm-Editor
- Gleiches Theme, gleiche Symbole und gleiches Tastenkürzel-System wie die IDE

### 13.2 Fensteraufbau

```
┌ ampel_klassen.pdiag – Diagramm-Editor – Natter ───────────────────────────── ─  □  ✕ ┐
│ Datei  Bearbeiten  Ansicht  Anordnen  Format  Hilfe                                    │
├────────────────────────────────────────────────────────────────────────────────────────┤
│ [Neu][Öffnen][Speichern] │ [↶][↷] │ [Auswahl][Hand] │ [Ausrichten▾][Verteilen▾] │ 100 % ▾ │
├───────────────┬──────────────────────────────────────────────────┬─────────────────────┤
│ FORMEN        │ ampel_klassen.pdiag │ ampel_zeichnen.pdiag        │ EIGENSCHAFTEN       │
│ [Suche …]     │  ┌ Lineal ─────────────────────────────────────┐ │ Form: Klasse        │
│ ▾ Klassen     │  │ · · · · · · · · · · · · · · · · · · · · · · │ │ Name   TAmpel       │
│   ▭ Klasse    │  │ ·   ┌───────────────┐        ┌──────────┐   │ │ Abstrakt ☐          │
│   ▭ Abstrakt  │  │ ·   │    TAmpel     │ 1    * │  TLampe  │   │ │ › Attribute (2)     │
│   ▭ Interface │  │ ·   ├───────────────┤◆───────├──────────┤   │ │ › Methoden (4)      │
│   ─▷ Vererbung│  │ ·   │ -an: bool     │        │ -farbe   │   │ │ Füllung  ■ Standard │
│   ─◆ Kompos.  │  │ ·   │ -zustand: str │        └──────────┘   │ │ Linie    ■ Standard │
│   ─◇ Aggreg.  │  │ ·   ├───────────────┤                       │ │ Schrift  Segoe UI 10│
│   ── Assoz.   │  │ ·   │ +einschalten()│                       │ │                     │
│ › Use-Case    │  │ ·   └───────────────┘                       │ │                     │
│ › Aktivität   │  └────────────────────────────────────────────┘ │                     │
│ › Zustand     │  Minimap ▫                                       │                     │
│ › Sequenz     │                                                  │                     │
│ › Struktogramm│                                                  │                     │
│ › Entsch.-Tab.│                                                  │                     │
├───────────────┴──────────────────────────────────────────────────┴─────────────────────┤
│ 3 Formen, 1 Verbindung │ Raster 8 px │ Einrasten ein │ A4 quer │ Stil: Modern hell       │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

| Bereich                | Inhalt                                                                                                                                                                                                                                                                                                                                                                                                                              |
|------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Menüs                  | Datei (Neu, Öffnen, Speichern, Speichern unter, Exportieren ›, Drucken, Schließen), Bearbeiten (Rückgängig, Wiederholen, Ausschneiden, Kopieren, Einfügen, Duplizieren, Löschen, Alles auswählen), Ansicht (Zoom, Raster, Lineale, Hilfslinien, Minimap, Seitenränder), Anordnen (Ausrichten, Verteilen, Gleiche Größe, Vordergrund/Hintergrund, Gruppieren), Format (Stilvorlage, Füllung, Linie, Schrift, Stil übertragen), Hilfe |
| Formen-Palette (links) | Reiter/Gruppen je Diagrammtyp, Suche, Tooltip mit Name und Kurzbeschreibung                                                                                                                                                                                                                                                                                                                                                         |
| Zeichenfläche (Mitte)  | Tabs für mehrere offene Diagramme, Raster, Lineale, Seitenansicht (A4/A3, hoch/quer), Minimap                                                                                                                                                                                                                                                                                                                                       |
| Eigenschaften (rechts) | wie Objektinspektor: Text-Felder der Form, Füllung, Linie, Schrift, Größe/Position, Verbindungs-Beschriftungen                                                                                                                                                                                                                                                                                                                      |
| Statusleiste           | Auswahl, Raster, Einrasten, Seitenformat, Stilvorlage                                                                                                                                                                                                                                                                                                                                                                               |

### 13.3 Bedienung

| Funktion                   | Verhalten                                                                                                                      |
|----------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| Form einfügen              | aus der Palette ziehen, oder anklicken und auf die Fläche klicken; Doppelklick fügt in der Mitte ein                           |
| Beschriften                | Doppelklick auf Text bearbeitet direkt in der Form; Tab springt zum nächsten Textfeld (z. B. Name → Attribute → Methoden)      |
| Verschieben / Größe        | Ziehen, Anfasser; Einrasten am Raster und an Kanten/Mitten anderer Formen mit Hilfslinien und Abstandsanzeige                  |
| Verbinden                  | Verbindung aus der Palette wählen, von Form zu Form ziehen; Enden docken an Andockpunkten an und folgen beim Verschieben       |
| Linienführung              | gerade, rechtwinklig oder mit frei setzbaren Knickpunkten; Knickpunkte per Doppelklick hinzufügen/entfernen                    |
| Verbindungs-Beschriftungen | Multiplizitäten, Rollen, Bedingungen `[guard]`, Ereignisse; frei verschiebbar, bleiben an der Linie                            |
| Mehrfachauswahl            | Rahmen ziehen, Strg+Klick; Ausrichten, Verteilen, gleiche Größe                                                                |
| Gruppieren                 | Strg+G / Strg+Umschalt+G                                                                                                       |
| Stil übertragen            | Format einer Form auf andere übernehmen                                                                                        |
| Zoom / Verschieben         | Strg+Mausrad, Leertaste+Ziehen, Strg+0 (alles anzeigen), Strg+1 (100 %)                                                        |
| Rückgängig                 | unbegrenzt innerhalb der Sitzung                                                                                               |
| Export                     | PNG (wählbare Auflösung, transparenter oder weißer Hintergrund), SVG, PDF; Kopieren in die Zwischenablage zum Einfügen in Word |
| Drucken                    | mit Seitenvorschau, Anpassen an Seite                                                                                          |

### 13.4 Diagrammtypen und Formen

| Diagrammtyp                          | Formen                                                                                                                                           | Verbindungen                                                                                                                           |
|--------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------|
| **Klassendiagramm**                  | Klasse (Name, Attribute, Methoden als getrennte Bereiche), abstrakte Klasse (`{abstract}`, kursiv), Interface, Notiz, Paket                      | Assoziation, gerichtete Assoziation, Aggregation ◇, Komposition ◆, Vererbung ▷, Abhängigkeit, Realisierung; Multiplizitäten und Rollen |
| **Use-Case-Diagramm**                | Akteur, Anwendungsfall, Systemgrenze, Notiz                                                                                                      | Assoziation, `<<include>>`, `<<extend>>`, Generalisierung                                                                              |
| **Aktivitätsdiagramm**               | Startknoten, Endknoten, Ablaufende, Aktion, Entscheidung/Zusammenführung, Gabelung/Vereinigung, Swimlane, Objektknoten, Notiz                    | Kontrollfluss mit Bedingung, Objektfluss                                                                                               |
| **Zustandsdiagramm**                 | Startzustand, Endzustand, Zustand (mit entry/do/exit-Bereich), zusammengesetzter Zustand, Entscheidung, Notiz                                    | Übergang mit `Ereignis [Bedingung] / Aktion`                                                                                           |
| **Sequenzdiagramm**                  | Akteur, Lebenslinie (Objekt), Aktivierungsbalken, Zerstörung ✕, kombiniertes Fragment (`alt`, `opt`, `loop`), Notiz                              | synchrone Nachricht, asynchrone Nachricht, Antwort, Erzeugung                                                                          |
| **Struktogramm** (Nassi-Shneiderman) | Anweisung, Verzweigung (ja/nein), Mehrfachauswahl, Zählschleife, kopfgesteuerte Schleife, fußgesteuerte Schleife, Unterprogrammaufruf, Aussprung | – (Blöcke werden verschachtelt statt verbunden)                                                                                        |
| **Entscheidungstabelle**             | Tabelle mit Bedingungsteil und Aktionsteil, Regeln als Spalten                                                                                   | –                                                                                                                                      |

Klassendiagramm-Formen bieten Kurzeingaben beim Beschriften: eine Zeile pro Attribut/Methode, Sichtbarkeit mit `+`, `-`, `#`; Zeilen per Enter hinzufügen, per Strg+Pfeil umsortieren. Der Text wird nicht auf Richtigkeit geprüft.

Später möglich: ER-Diagramm (modifizierte Chen-Notation), Syntaxdiagramm, Import von DIA-Dateien (`.dia`).

### 13.5 Struktogramm- und Tabellen-Editor

Struktogramme sind Blöcke, keine frei verbundenen Formen. Das Zeichnen bleibt manuell, der Editor hält nur die Blockstruktur zusammen:

- Block aus der Palette auf eine Einfügelinie ziehen (zwischen zwei Blöcken, in einen leeren Zweig oder Schleifenkörper); die Einfügestelle wird hervorgehoben
- Breiten und Höhen passen sich beim Einfügen an, damit der Rahmen geschlossen bleibt; Verzweigungen bekommen die Beschriftungen „ja“/„nein“ (änderbar)
- Mehrfachauswahl: Fälle über Plus/Minus am Block hinzufügen/entfernen
- Blöcke mit ihrem Inhalt verschieben, kopieren, löschen
- Kopfzeile mit Name des Struktogramms bzw. Unterprogramms; mehrere Struktogramme auf einer Seite möglich
- Tastatur: Enter fügt eine Anweisung darunter ein, Entf löscht den Block

Entscheidungstabelle:

- Zeilen für Bedingungen und Aktionen, Spalten für Regeln hinzufügen/entfernen/verschieben
- Zellen im Bedingungsteil per Klick durchschalten: `J` → `N` → `*` → leer; im Aktionsteil `X` → leer
- Keine automatische Zusammenfassung oder Vollständigkeitsprüfung von Regeln

### 13.6 Design der Diagramme

Moderne, ruhige Darstellung statt DIA-Optik, aber normgerechte Notation:

| Element       | Gestaltung                                                                                                                |
|---------------|---------------------------------------------------------------------------------------------------------------------------|
| Linien        | 1,5 px, gleichmäßige Pfeilspitzen in UML-Form (offenes Dreieck, Raute gefüllt/leer), Kantenglättung                       |
| Formen        | UML-Formen nach Norm (Klassen eckig, Aktionen/Zustände abgerundet), dezente Füllung, keine Schatten- oder Verlaufseffekte |
| Schrift       | Segoe UI für Namen/Beschriftungen, Cascadia Code für Attribute und Methoden; Klassennamen fett, abstrakte kursiv          |
| Abstände      | einheitliche Innenabstände auf 8-px-Raster, automatische Mindestgröße, damit Text nie abgeschnitten wird                  |
| Auswahl       | Akzentfarbe, runde Anfasser, Andockpunkte erscheinen erst beim Überfahren                                                 |
| Zeichenfläche | Punktraster, im dunklen Theme dunkel; Seitenbereich als helle Fläche sichtbar                                             |

Stilvorlagen (für ganze Diagramme umschaltbar):

| Vorlage       | Einsatz                                                                |
|---------------|------------------------------------------------------------------------|
| Modern hell   | Standard, farbige Akzente je Formtyp in gedeckten Tönen                |
| Modern dunkel | Arbeit im dunklen Theme                                                |
| Schwarz-Weiß  | Druck, Abgabe, Prüfungsunterlagen; Export immer mit weißem Hintergrund |

Der Export verwendet unabhängig vom IDE-Theme die im Diagramm gewählte Stilvorlage.

Layout-Hinweise (keine Inhaltsprüfung, nur Darstellung, abschaltbar): überlappende Formen, abgeschnittene Texte, lose Verbindungsenden, Formen außerhalb des Seitenbereichs.

### 13.7 Dateiformat `.pdiag`

``` json
{
  "format": "pdiag/1",
  "type": "class",
  "page": { "size": "A4", "orientation": "landscape" },
  "style": "modern-light",
  "shapes": [
    { "id": "s1", "kind": "class", "x": 96, "y": 64, "w": 184, "h": 136,
      "text": { "name": "TAmpel", "attributes": ["-an: bool", "-zustand: str"],
                "methods": ["+einschalten()", "+get_zustand(): str"] },
      "abstract": false }
  ],
  "connectors": [
    { "id": "c1", "kind": "composition", "from": "s1", "to": "s2",
      "waypoints": [[320, 132]], "labels": { "from": "1", "to": "3" } }
  ]
}
```

JSON mit Schema und Versionsnummer, lesbar und versionierbar; Struktogramme speichern einen Blockbaum statt Koordinaten.

## 14. Design-Prüfer

Regelbasierte Prüfung von Formularen, lokal und ohne KI. Aufruf über „Werkzeuge → Design prüfen“ oder automatisch beim Speichern eines Formulars (abschaltbar). Befunde erscheinen im Panel „Meldungen“; ein Klick markiert die betroffene Komponente im Designer.

Befunde sind **Hinweise und Warnungen, keine Fehler**. Sie verhindern weder Start noch Export.

| Kategorie        | Prüfungen                                                                                                                 |
|------------------|---------------------------------------------------------------------------------------------------------------------------|
| Geometrie        | Überlappungen, Komponenten außerhalb des Formulars, nicht am Raster, uneinheitliche Abstände, nicht bündige Kanten        |
| Größenänderung   | Formular in Mindestgröße, Standardgröße und maximiert prüfen: abgeschnittene oder verschobene Komponenten, fehlende Anker |
| Skalierung       | 100 %, 125 %, 150 %: abgeschnittene Texte                                                                                 |
| Lesbarkeit       | Kontrast nach WCAG AA in hellem **und** dunklem Theme, Mindestschriftgröße, zu viele Schriftarten/-farben                 |
| Konsistenz       | einheitliche Button-Größen und -Varianten, einheitliche Label-Ausrichtung zu Eingabefeldern                               |
| Bedienbarkeit    | Tab-Reihenfolge logisch (oben links → unten rechts), Eingabefeld ohne Beschriftung, zu kleine Klickflächen                |
| Namenskonvention | fehlendes Präfix (`b_`, `e_`, `l_` …), Standardnamen wie `button1`, Standardtexte wie „Button1“ – nur Hinweis             |

Einzelne Regeln lassen sich in den Einstellungen abschalten. Für Diagramme gelten nur die Layout-Hinweise aus 13.6.

## 15. Lazarus-Import (`.lfm`)

- Parser für das Text-`.lfm`-Format (`object … end`)
- Zuordnungstabelle Klassen und Eigenschaften: `TButton → Button`, `Caption → caption`, `Left/Top/Width/Height`, `Font.*`, `Anchors`, `Align`, `Items`, `ColCount/RowCount`
- Farben: `clRed`, `clBtnFace`, `$00FF8000` → Hex-Werte bzw. Theme-Tokens
- Ereignisse: `OnClick = b_startClick` → `on_click: b_start_click`, Methodenrümpfe in `u_main.py` werden angelegt
- Aus der zugehörigen `.pas` wird der Pascal-Rumpf jedes Handlers als Kommentar in die neue Methode übernommen (Umstiegshilfe, eigener Code)
- Bilder aus `Picture.Data` werden nach `assets/` extrahiert
- Nicht unterstützte Komponenten werden als Platzhalter angelegt und im Importbericht aufgeführt
- Anschließend läuft der Design-Prüfer und zeigt Verbesserungsmöglichkeiten für das importierte Formular

## 16. Exe-Export

- Dialog: Programmname, Version, Symbol, Zielordner, Einzeldatei oder Ordner
- GUI-Projekte ohne Konsolenfenster, Konsolenprojekte mit Konsole
- Automatisch eingebunden: eigener Code inkl. `u_*_design.py`, `assets/`, benötigte `pcl`-Module, Datenbanktreiber, importierte Pakete wie pandas (die `.pfm` wird nicht benötigt)
- Wählbar: Ordner `daten/` und weitere Dateien (z. B. `highscore.txt`, CSV-Dateien) mitkopieren
- Standard: Ordner-Variante als ZIP (Einzeldatei-Exes werden in Schulnetzen häufiger von Virenscannern blockiert)
- Nach dem Build automatischer Probestart mit Fehlerbericht

## 17. Verteilung: portabler Ordner ohne Installation

### 17.1 Prinzip

Die IDE wird als **ZIP-Datei** verteilt. Auspacken (z. B. auf dem Desktop), `Natter.exe` starten, fertig:

- keine Python-Installation nötig, keine Adminrechte, kein Installer, keine Registry-Einträge
- alles liegt im entpackten Ordner: Python 3.13, alle Pakete, Monaco, Hilfe, Einstellungen
- Ordner kann verschoben, auf USB-Stick kopiert oder einfach gelöscht werden (= Deinstallation)
- mehrere Versionen können nebeneinander liegen
- vollständig offline nutzbar

### 17.2 Ordneraufbau

```
Natter/
  Natter.exe               kleiner Starter (setzt Pfade, startet die IDE, zeigt Startfehler verständlich an)
  runtime/
    python/                Python 3.13, relokierbare Standalone-Distribution (vollständige Standardbibliothek)
    pakete-ide/            PySide6 inkl. WebEngine, Jedi, Ruff, libcst, IDE-Code
    pakete-projekt/        PySide6 (Multimedia), pcl,         debugpy, PyMySQL, SQLAlchemy,
                           pandas, numpy, openpyxl, matplotlib, PyInstaller
    pakete-zusatz/         vom Benutzer über „Pakete“ installierte Pakete
  monaco/                  Code-Editor
  hilfe/                   Komponenten-Referenz, Umstiegs-Referenz, Fehlerkatalog
  vorlagen/                Projekt- und Dateivorlagen
  benutzer/                Einstellungen, Tastenkürzel, zuletzt geöffnete Projekte, Sitzungen
  lizenzen/                Lizenztexte aller enthaltenen Komponenten
```

Projekte der Schüler liegen außerhalb des Programmordners (Standard: `Dokumente\Natter-Projekte`, frei wählbar).

### 17.3 Warum keine venv

Eine venv speichert absolute Pfade (u. a. in `pyvenv.cfg` und in Startskripten). Nach dem Verschieben oder Auspacken an einem anderen Ort funktioniert sie nicht mehr. Deshalb:

- Python kommt als **relokierbare Standalone-Distribution** (z. B. python-build-standalone, wie sie auch `uv` verwendet); sie funktioniert an jedem Ort
- Die Trennung, die sonst die venvs leisten, übernehmen **getrennte Paketordner**: Der Starter setzt beim Start der IDE nur `pakete-ide` in den Suchpfad, beim Start eines Schülerprogramms nur `pakete-projekt` und `pakete-zusatz` (isolierter Modus `-I`, keine Benutzer-Site-Packages, keine Umgebungsvariablen von außen)
- Ergebnis wie bei zwei venvs: installierte Zusatzpakete können die IDE nicht beschädigen
- „Werkzeuge → Umgebung prüfen/reparieren“ leert `pakete-zusatz` bzw. prüft die Paketordner gegen das signierte Prüfsummen-Manifest (17.8)

### 17.4 Größe und Aufbau des ZIP

- Entpackt grob 1–1,5 GB, als ZIP etwa die Hälfte (Qt WebEngine, pandas/matplotlib und PyInstaller sind die größten Teile; genaue Werte nach dem ersten Build messen)
- Gemeinsam genutzte Teile (Python selbst, PySide6-Grundmodule) werden nur einmal abgelegt
- `__pycache__` wird beim Build vorab erzeugt, damit der erste Start schnell ist
- Alle Pfade im Paket kurz halten, damit auch tief liegende Dateien unter der Windows-Grenze von 260 Zeichen bleiben

### 17.5 Stolpersteine beim Auspacken und Starten

| Problem                                                          | Ursache                                                                                | Lösung                                                                                                              |
|------------------------------------------------------------------|----------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| Windows blockiert Dateien nach dem Auspacken                     | ZIP aus dem Internet trägt die „Mark of the Web“                                       | vor dem Auspacken ZIP → Eigenschaften → „Zulassen“; der Starter erkennt blockierte Dateien und erklärt den Schritt  |
| SmartScreen-Warnung „Der Computer wurde durch Windows geschützt“ | ZIP aus dem Internet trägt die „Mark of the Web“; eigene Signatur ohne gekauftes Zertifikat hat keine SmartScreen-Reputation | vor dem Auspacken ZIP → Eigenschaften → „Zulassen“; dann erscheint keine Warnung |
| Virenscanner meldet `Natter.exe` | kleine Exe unbekannter Herkunft | Starter klein und ohne gepackten Inhalt halten (kein PyInstaller-Onefile), eigene Signatur (17.8) |
| Desktop wird mit OneDrive synchronisiert                         | Tausende Dateien werden hochgeladen, „Nur online verfügbar“ macht Dateien unzugänglich | Starter erkennt OneDrive-Pfad und empfiehlt einen nicht synchronisierten Ort (z. B. `C:\Users\<Name>\Natter`)        |
| Auspacken dauert lange                                           | sehr viele kleine Dateien                                                              | alternativ 7-Zip-Archiv oder selbstentpackendes Archiv anbieten; Inhalt unverändert                                 |
| Pfad zu lang                                                     | tiefes Entpackziel                                                                     | Starter prüft die Pfadlänge und warnt                                                                               |

### 17.6 Exportierte Schülerprogramme

Unverändert nach Abschnitt 16: Auch die mit „Exe erstellen“ erzeugten Programme sind portable Ordner (bzw. ZIP), die ohne Python auf jedem Windows-Rechner laufen.

### 17.7 Lizenz

**Natter** ist ein privates Projekt unter eigener Lizenz des Projektinhabers: Nutzung erlaubt, Weitergabe und Verbreitung nicht erlaubt.

Die enthaltenen Fremdkomponenten behalten ihre eigenen Lizenzen. Daraus folgen Regeln für die Auswahl:

| Regel | Umsetzung |
|---|---|
| Nur Komponenten mit freizügigen Lizenzen oder LGPL | PySide6/Qt (LGPLv3), Monaco, Jedi, Ruff, libcst, debugpy, PyMySQL, SQLAlchemy, openpyxl (MIT), pandas, numpy (BSD), matplotlib (PSF-basiert), Lucide (ISC), Codicons (CC BY 4.0) |
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
    editor/            Monaco-Brücke (QWebChannel), Jedi, Ruff
    designer/          Canvas, Auswahl, Anfasser, Raster, Undo
    inspector/         Eigenschaften-/Ereignis-Editoren
    codegen/           design.py-Generator, libcst-Operationen
    debugger/          DAP-Client, Fehlerkatalog, Tabellenansicht für Variablen
    testing/           Test-Explorer (unittest)
    viewers/           CSV-Tabellenansicht, Bildvorschau, HTML-Vorschau
    help/              Kontexthilfe, Komponenten- und Umstiegs-Referenz
    database/          DB-Panel
    project/units/     Unit-Verwaltung, Import-Einfügen, Kreisbezug-Erkennung, Sitzung
    lint/              Design-Prüfer
    diagram/           Diagramm-Editor: Fenster, Szene, Formen, Verbindungen, Struktogramm-Blöcke, Entscheidungstabelle, Export
    env/               Paketordner, Paketverwaltung (pip), Umgebungsprüfung
  launcher/            Starter Natter.exe (Pfade, Startprüfungen: Mark of the Web, OneDrive, Pfadlänge, Manifest-Signatur)
  build/               Build-Skripte: portables Paket, Manifest, Signatur
    importer/          .lfm-Parser und Zuordnung
    export/            PyInstaller-Pipeline
    project/           Projektdatei, Vorlagen
  icons/               SVG-Symbole (Aktionen, Komponenten)
  web/monaco/          gebündeltes Monaco
  schemas/             pfm.schema.json, project.schema.json, pdiag.schema.json
  templates/           gui/, console/, gui_db/
  tests/
  installer/
```

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
| Datenbank            | SQLite in-memory; danach MariaDB im Docker-Container auf dem Homeserver                                                                                                                                                                                                                     |
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
| M2    | IDE-Grundgerüst, Aktionsregister, alle Menüs und Werkzeugleisten, SVG-Symbole, Monaco, Themes, Explorer, Neu-Dialog, Units (Tabs, geteilte Ansicht, Einbinden), portable Laufzeit mit getrennten Paketordnern, Ausführung in eigenen Fenstern (GUI + Konsole), Tastenkürzel-Tab | Projekt aus M1 in der IDE öffnen, alle Datei-Menüfunktionen funktionieren, Projekt `u_pflanzen`/`u_garten` anlegen und starten, Konsolenprogramm mit `input()` im eigenen Fenster |
| M3    | Designer, Objektinspektor mit allen Editoren und Reitern, Komponentenpalette mit Reitern, Ereignis-Codegenerierung, Undo                                                                                                                                                        | Ampel komplett in der IDE erstellen, alle Eigenschaften nur über den Inspektor gesetzt                                                                                            |
| M4    | Ruff-Prüfung, Debugger inkl. Tabellenansicht, Fehlerkatalog (Wo/Was/Prüfe), Test-Explorer                                                                                                                                                                                       | Fehlerbeispiele liefern korrekte Meldungen, Breakpoints/Step funktionieren, Tests mit Soll/Ist-Anzeige                                                                            |
| M5    | SQLdb- und Data-Control-Komponenten, DB-Panel mit CSV-Import/-Export, pandas-Anbindung, Chart, CSV-/Bild-/HTML-Ansichten in der IDE                                                                                                                                             | Kontoverwaltung mit MariaDB und SQLite; CSV-Auswertung mit pandas in StringGrid und Chart; Würfelspiel-Highscore als HTML im Browser                                              |
| M6    | Konsolen-Feinschliff, `pcl.crt`                                                                                                                                                                                                                                                 | Konsolen- und CRT-Übungen aus dem Kursmaterial laufen                                                                                                                             |
| M7    | Design-Prüfer, Paketverwaltung                                                                                                                                                                                                                                                  | alle Prüfregeln erkennen ihre Testformulare; Paket über das Menü installierbar                                                                                                    |
| M8 | `.lfm`-Import, Exe-Export, portables ZIP-Paket mit Starter, Prüfsummen-Manifest und Signatur | Lazarus-Übungsprojekt importieren, fertigstellen, als Exe starten; ZIP auf einem Rechner ohne Python entpacken und vollständig nutzen; veränderte Datei wird erkannt |
| M9    | Diagramm-Editor: Fenster, Palette, Klassendiagramm, Struktogramm, Entscheidungstabelle; danach Use-Case, Aktivität, Zustand, Sequenz; Stilvorlagen, Export, Druck                                                                                                               | UML-Klassendiagramm TAmpel, Struktogramm `ampel_zeichnen` und Entscheidungstabelle der Ampel von Hand erstellen und als PDF exportieren                                           |

## 21. Risiken

| Risiko                                                  | Gegenmaßnahme                                                                                    |
|---------------------------------------------------------|--------------------------------------------------------------------------------------------------|
| Monaco-Integration in Qt aufwendig                      | früher Prototyp in M2; Ausweichlösung QScintilla                                                 |
| Designer-Komplexität (Undo, Mehrfachauswahl, Anker)     | Command-Pattern von Anfang an, Designer rendert echte `pcl`-Komponenten                          |
| Ausnahmen in Qt-Handlern gehen verloren                 | zentrale Ausnahmebehandlung in `pcl` ab M1                                                       |
| Eigener Code im erzeugten `design.py` geht verloren     | Datei klar gekennzeichnet, Editor zeigt sie schreibgeschützt an                                  |
| Schülerpakete beschädigen die Umgebung                  | getrennte Paketordner, Reparaturfunktion                                                         |
| Portabler Ordner sehr groß                              | Größe nach erstem Build messen, doppelte Teile vermeiden                                         |
| Tastenkürzel kollidieren mit Monaco-internen Kürzeln    | Aktionsregister leitet Kürzel zentral, Konfliktprüfung im Test                                   |
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
