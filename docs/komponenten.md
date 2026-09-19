# Komponenten-Referenz

Hier steht zu jeder Komponente, **was sie kann**: jede Eigenschaft mit
ihrem Typ, ihrem Standardwert und einem Satz dazu, und jedes Ereignis
mit seinem Auslöser. Dieselben Texte stehen als Kurzhinweis im
Objektinspektor, wenn man mit der Maus über einer Zeile stehen bleibt.

Die Eigenschaften setzt man im Designer (Objektinspektor) oder im Code
über `self.` und den Namen der Komponente, zum Beispiel
`self.b_start.caption = "Los"`.

Zum Nachschlagen genügt die Tabelle der jeweiligen Komponente; die
Angabe „Qt-Basis“ darunter ist für die Neugierigen und sagt, welches
Qt-Widget dahintersteckt.

Diese Seite ist zugleich die **verbindliche Schnittstelle** für `pcl`:
jede Komponente wird hier dokumentiert, bevor sie umgesetzt wird (siehe
README.md, Abschnitt 5 und 23.2).

Stand: `Form`, `Button`, `Label`, `Shape`, `Edit`, `CheckBox`,
`RadioButton`, `Memo`, `ListBox`, `ComboBox`, `StringGrid`, `Image`,
`ScrollBar` sind umgesetzt (M1, Schritt 2/3/6), `Chart` dazu aus M10.
Aus Schritt 6 kamen `SpinEdit`, `FloatSpinEdit`, `TrackBar`,
`ProgressBar`, `Timer`, `GroupBox`, `Panel` und `RadioGroup` dazu, aus
M15 `MainMenu` und `PopupMenu`. Rest folgt später – nur
deklariert/nicht genutzt oder in keinem Referenzprojekt vorhanden,
daher niedrigere Priorität: `MaskEdit`, `PaintBox`, `HtmlViewer`,
`DateEdit`, `TimeEdit`, `Calendar`, weitere Dialoge, `Sound`.

## Form

Qt-Basis: `QWidget` (`pcl/form.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| caption | str | "Form1" | Darstellung | Fenstertitel |
| width | int | 480 | Layout | Fensterbreite in Pixeln |
| height | int | 360 | Layout | Fensterhöhe in Pixeln |
| theme | str | "system" | Darstellung | Farbschema: system, light oder dark; wendet das QSS aus `pcl/theme/` (Quelle: `design/tokens.json`) sofort auf das Formular an |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_create | (self, sender) | unmittelbar vor der ersten Anzeige |

Methoden: `show()`, `close()` (entspricht `Close` aus der LCL).

Besonderheit: einziger Komponententyp mit `neue_attribute_erlaubt = True`
(Abschnitt 5.0) – eigene Attribute wie `self.ampel = Ampel()` bleiben
erlaubt.

## Button

Qt-Basis: `QPushButton` (`pcl/components/standard.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height | int | 0, 0, 75, 25 | Layout | Position/Größe in Pixeln (geerbt von `Control`) |
| enabled | bool | True | Verhalten | Legt fest, ob die Komponente bedienbar ist (geerbt von `Control`) |
| caption | str | "Button" | Darstellung | Beschriftung des Buttons |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_click | (self, sender) | Klick auf den Button |

## Label

Qt-Basis: `QLabel` (`pcl/components/standard.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| caption | str | "Label1" | Darstellung | Anzeigetext |
| color | str (Hex) | "" | Darstellung | Hintergrundfarbe (nur bei transparent=False), wie Lazarus `TLabel.Color` |
| transparent | bool | True | Darstellung | Wenn wahr (Standard), kein eigener Hintergrund, wie Lazarus `TLabel.Transparent` |

Keine eigenen Ereignisse.

## Shape

Qt-Basis: eigenes Painting (`QPainter` auf `QWidget`, `pcl/components/additional.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| shape | str | "rectangle" | Darstellung | Form der Zeichnung: rectangle oder circle |
| brush.color | str (Hex) | "#c0c0c0" | Darstellung | Füllfarbe; aufklappbare Untereigenschaft, kein eigenständiges `Prop` |
| pen_color | str (Hex) | "#000000" | Darstellung | Randfarbe, unabhängig von `brush.color` (wie Lazarus `Pen.Color`) |
| transparent | bool | False | Darstellung | Wenn wahr, keine Füllung - nur der Rand (wie Lazarus `Brush.Style=bsClear`) |

Keine eigenen Ereignisse. `shape` ist aktuell ein einfacher `str` ohne
Aufzählungs-Editor im Inspektor (Abschnitt 5.0 sieht dafür später einen
echten Enum-Typ vor, sobald `Align`/`BorderStyle` u. Ä. eingeführt werden).

`Control` (alle Komponenten) hat außerdem `nach_vorne_bringen()`/
`nach_hinten_schicken()` (Z-Ebene, wie Lazarus `BringToFront`/
`SendToBack`) - keine Inspektor-Zeile, da eine Aktion statt einer
Eigenschaft (Nutzer-Feedback September 2026: „Z-Ebene“).

## Edit

Qt-Basis: `QLineEdit` (`pcl/components/standard.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| text | str | "" | Darstellung | Eingegebener bzw. angezeigter Text |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | jede Änderung des Textes (Tastatur oder Code) |

## CheckBox

Qt-Basis: `QCheckBox` (`pcl/components/standard.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| caption | str | "CheckBox1" | Darstellung | Beschriftung |
| checked | bool | False | Verhalten | Legt fest, ob das Kästchen angehakt ist |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | Umschalten (Klick oder Code) |

## RadioButton

Qt-Basis: `QRadioButton` (`pcl/components/standard.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| caption | str | "RadioButton1" | Darstellung | Beschriftung |
| checked | bool | False | Verhalten | Legt fest, ob die Option ausgewählt ist |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | Umschalten (Klick oder Code) |

Hinweis: gruppiert sich aktuell nur visuell durch gemeinsame Platzierung;
eine echte `RadioGroup`-Komponente mit automatischer gegenseitiger
Exklusivität folgt später in Schritt 6.

## Memo

Qt-Basis: `QPlainTextEdit` (`pcl/components/standard.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| lines | `Strings` | leer | Daten | mehrzeiliger Text; Sammlungs-Eigenschaft (siehe „Schrift und Sammlungen“ unten) |
| read_only | bool | False | Verhalten | Wenn wahr, nicht bearbeitbar (wie Lazarus `TMemo.ReadOnly`) |

Keine eigenen Ereignisse. `lines` synchronisiert bisher nur in eine
Richtung (Zuweisung/`add`/`clear` → Anzeige); von Benutzern eingetippter
Text wird nicht in `lines` zurückgeschrieben (kein Referenzprojekt braucht
das bisher, siehe `tests/daten/lazarus/*` – nur `.Lines.Add`/`.Clear`).

## ListBox

Qt-Basis: `QListWidget` (`pcl/components/standard.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| items | `Strings` | leer | Daten | Einträge; Sammlungs-Eigenschaft (siehe „Schrift und Sammlungen“ unten) |
| item_index | int | -1 | Verhalten | Index des ausgewählten Eintrags, -1 = keine Auswahl |

Keine eigenen Ereignisse (kein Referenzprojekt braucht bisher eines,
`item_index` wird bei Bedarf ausgelesen statt auf Änderung zu reagieren).

## ComboBox

Qt-Basis: `QComboBox` (`pcl/components/standard.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| items | `Strings` | leer | Daten | Einträge; Sammlungs-Eigenschaft (siehe „Schrift und Sammlungen“ unten) |
| item_index | int | -1 | Verhalten | Index des ausgewählten Eintrags, -1 = keine Auswahl |
| text | str | "" | Darstellung | Angezeigter bzw. ausgewählter Text, folgt `item_index` |

Keine eigenen Ereignisse. `item_index` und `text` halten sich in beide
Richtungen synchron (Zuweisung ↔ Auswahl über das Widget).

## StringGrid

Qt-Basis: `QTableWidget` (`pcl/components/additional.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| row_count | int | 5 | Daten | Anzahl der Zeilen |
| col_count | int | 5 | Daten | Anzahl der Spalten |
| cells\[spalte, zeile\] | str | "" | – | Zellinhalt; aufklappbare Untereigenschaft, kein eigenständiges `Prop` |

Keine eigenen Ereignisse (`on_select_cell`/`on_edit_cell` aus Abschnitt
5.4 sind noch offen, kein Referenzprojekt braucht sie bisher).

## Image

Qt-Basis: `QLabel` mit `QPixmap` (`pcl/components/additional.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| picture.load_from_file(pfad) / picture.clear() | Methoden | – | – | aufklappbare Untereigenschaft, kein eigenständiges `Prop` |

Keine eigenen Ereignisse. `stretch`/`proportional`/`center` aus Abschnitt
11.4 sind noch offen (kein Referenzprojekt braucht sie bisher; alle drei
Bild-Projekte zeigen ein Bild einfach in Originalgröße an).

**Bekannte Lücke:** `on_click`/`on_double_click` gelten laut Abschnitt 5.4
für „alle sichtbaren“ Komponenten. Bisher ist `on_click` nur bei `Button`
umgesetzt (dort über das native Qt-`clicked`-Signal). Ein komponenten-
übergreifendes `on_click` über `Control` (inkl. eigener Maus-Ereignis-
Behandlung für Komponenten ohne natives Klick-Signal wie `Label`/`Shape`)
ist noch offen und wird nachgezogen, sobald ein Referenzprojekt es
tatsächlich braucht (bisher nutzt keines der Übungsprojekte das).

## ScrollBar

Qt-Basis: `QScrollBar`, horizontal (`pcl/components/standard.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| minimum | int | 0 | Verhalten | Kleinster möglicher Wert |
| maximum | int | 100 | Verhalten | Größter möglicher Wert |
| position | int | 0 | Verhalten | Aktueller Wert |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | Änderung der Position (Ziehen oder Code) |

Gegen die echte Nutzung in `f_Pizza` geprüft (`sb_behinderung.position`
steuert dort die Schriftgröße eines Memos, Min=5/Max=50).

## SpinEdit

Qt-Basis: `QSpinBox` (`pcl/components/additional.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| minimum | int | 0 | Verhalten | Kleinster möglicher Wert |
| maximum | int | 100 | Verhalten | Größter möglicher Wert |
| value | int | 0 | Verhalten | Aktueller Wert |
| increment | int | 1 | Verhalten | Schrittweite der beiden Pfeilknöpfe |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | Änderung des Wertes (Pfeilknopf, Tastatur oder Code) |

`value` heißt wie Lazarus' `TSpinEdit.Value` – anders als bei
`ScrollBar`/`TrackBar`, wo der Wert in der LCL `Position` heißt. Die
`pcl`-Namen folgen hier bewusst der jeweiligen Lazarus-Komponente, damit
ein aus dem Unterricht bekanntes Programm ohne Umdenken übertragbar
bleibt.

Ein Wert außerhalb von `minimum`..`maximum` wird von Qt auf die Grenze
gekappt; `value` trägt danach den gekappten Wert, nicht den zugewiesenen.

## FloatSpinEdit

Qt-Basis: `QDoubleSpinBox` (`pcl/components/additional.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| minimum | float | 0.0 | Verhalten | Kleinster möglicher Wert |
| maximum | float | 100.0 | Verhalten | Größter möglicher Wert |
| value | float | 0.0 | Verhalten | Aktueller Wert |
| increment | float | 1.0 | Verhalten | Schrittweite der beiden Pfeilknöpfe |
| decimals | int | 2 | Darstellung | Anzahl der angezeigten Nachkommastellen |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | Änderung des Wertes (Pfeilknopf, Tastatur oder Code) |

Wie bei jeder `float`-Eigenschaft darf auch eine ganze Zahl zugewiesen
werden (`pcl.properties.Prop._passt_typ`); gelesen wird immer ein
`float`. `decimals` rundet den Wert wie in Qt auch tatsächlich, nicht
nur die Anzeige: nach `decimals = 1` ist aus `2.25` ein `2.3` geworden,
und `value` liefert danach ebenfalls `2.3`.

## TrackBar

Qt-Basis: `QSlider`, horizontal (`pcl/components/additional.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, enabled | wie `Control` | – | – | geerbt von `Control` |
| width | int | 150 | Layout | Breite in Pixeln |
| height | int | 30 | Layout | Höhe in Pixeln |
| minimum | int | 0 | Verhalten | Kleinster möglicher Wert |
| maximum | int | 10 | Verhalten | Größter möglicher Wert |
| position | int | 0 | Verhalten | Aktueller Wert |
| frequency | int | 1 | Darstellung | Abstand der Teilstriche unter dem Schieber; 0 = keine Teilstriche |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | Änderung der Position (Ziehen, Tastatur oder Code) |

`maximum` ist 10 und nicht 100, `frequency` ist 1 – beides wie
`TTrackBar` in Lazarus. Mit `maximum = 100` und `frequency = 1` würden
die Teilstriche bei 150 Pixeln Breite zu einem durchgehenden Balken
verschmelzen.

Die Standardgröße steht als `Prop`-Standard an der Komponente (wie bei
`Chart`) und nicht in der Tabelle des Designers, damit erzeugter Code und
eine von Hand geschriebene Komponente dieselbe Größe bekommen.

## ProgressBar

Qt-Basis: `QProgressBar` (`pcl/components/additional.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, enabled | wie `Control` | – | – | geerbt von `Control` |
| width | int | 150 | Layout | Breite in Pixeln |
| height | int | 22 | Layout | Höhe in Pixeln |
| minimum | int | 0 | Verhalten | Kleinster möglicher Wert |
| maximum | int | 100 | Verhalten | Größter möglicher Wert |
| position | int | 0 | Verhalten | Aktueller Wert (Füllstand) |
| show_text | bool | True | Darstellung | Prozentzahl im Balken anzeigen |

Keine Ereignisse (auch `TProgressBar` in Lazarus hat keine).

`show_text` ist neu gegenüber Lazarus, wo der Balken nie eine Zahl
trägt. Qt zeigt sie von sich aus an, und im Unterricht ist genau das
hilfreich; `show_text = False` liefert die Lazarus-Optik.

Ein `position` außerhalb von `minimum`..`maximum` wird auf die Grenze
gekappt, wie bei `SpinEdit` und `TrackBar` auch. Das musste die
Komponente selbst tun: `QProgressBar.setValue()` **ignoriert** einen zu
großen Wert stillschweigend, statt ihn zu kappen – `position = 300` ließ
den Balken kommentarlos auf 0 stehen.

## Timer

Qt-Basis: `QTimer` (`pcl/components/system.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| enabled | bool | True | Verhalten | Legt fest, ob der Zeitgeber läuft |
| interval | int | 1000 | Verhalten | Abstand zwischen zwei Auslösungen in Millisekunden |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_timer | (self, sender) | nach jeweils `interval` Millisekunden, solange `enabled` wahr ist |

**Die einzige Komponente, die im laufenden Programm nichts anzeigt.**
Im Designer liegt sie als kleine Uhr auf dem Formular — anklickbar,
verschiebbar, im Objektinspektor einstellbar —, im fertigen Programm
ist sie unsichtbar. Genau so hält Lazarus es mit `TTimer`.

Du ziehst den Zeitgeber also wie jede andere Komponente aus der Palette
„Zusätzlich" auf das Formular und stellst `interval` und `enabled` im
Objektinspektor ein. Ein Doppelklick auf die Uhr legt die Methode für
`on_timer` an.

Im Quelltext geht es weiterhin auch:

```python
self.t_ampel = Timer(self)
self.t_ampel.interval = 2000
self.t_ampel.on_timer = self.t_ampel_timer
```

Technisch ist sie eine gewöhnliche `Control` mit
`nur_im_designer = True` (`pcl/control.py`). Dadurch brauchen
Komponentenbaum, Objektinspektor, `.pfm`-Schreiber und Codeerzeugung
keinen einzigen Sonderfall (M14).

`enabled` ist wie in Lazarus standardmäßig **wahr**: ein frisch
erzeugter `Timer` läuft sofort los. `interval = 0` stoppt ihn nicht,
sondern lässt Qt so oft auslösen, wie die Ereignisschleife es zulässt –
wie in der LCL. `stop()`/`start()` gibt es bewusst nicht; `enabled`
ist der eine Schalter, wie in Lazarus.

## MainMenu

Qt-Basis: `QMenuBar` (`pcl/components/menus.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, enabled | wie `Control` | – | – | geerbt von `Control` |
| width | int | 32 | Layout | Breite des Symbols |
| height | int | 32 | Layout | Höhe des Symbols |
| entries | Liste | [] | Allgemein | Die Einträge des Menüs (Doppelklick öffnet den Menü-Editor) |

Keine eigenen Ereignisse – **jeder Eintrag** hat sein eigenes.

Die Menüleiste am oberen Rand des Fensters, wie `TMainMenu` in
Lazarus. Auf dem Formular liegt nur ein kleines Symbol; die Leiste
selbst erscheint erst im laufenden Programm. Dieselbe Regel wie beim
`Timer`: was im fertigen Programm keine Fläche einnimmt, nimmt im
Designer auch keine weg.

Die Leiste sitzt **über** dem Inhalt: das Fenster wächst um ihre Höhe,
die Komponenten behalten ihre Koordinaten. Genau so verhält sich
Lazarus auch – dort ist `Top = 0` der obere Rand des Arbeitsbereichs,
nicht des Fensters. Ein Knopf, den du ganz nach oben setzt, steht im
laufenden Programm auch ganz oben und nicht hinter dem Menü.

### Die Einträge

Ein Eintrag ist kein Text, sondern ein Datensatz mit diesen Feldern:

| Feld | Bedeutung |
|---|---|
| `name` | Bezeichner im Quelltext, z. B. `mi_datei_beenden` |
| `caption` | Was dasteht. Ein `&` macht den nächsten Buchstaben zum Zugriffsbuchstaben (`&Datei` → Alt+D) |
| `shortcut` | Tastenkürzel, deutsch geschrieben: `Strg+Q`, `Strg+Umschalt+S` |
| `enabled` | Ob der Eintrag anklickbar ist |
| `checked` | Macht den Eintrag ankreuzbar und kreuzt ihn an |
| `separator` | Eine Trennlinie – ohne Beschriftung und ohne Ereignis |
| `on_click` | Name der Methode, die beim Anklicken läuft |
| `children` | Untereinträge (zweite Ebene) |

Ausgefüllt wird das im **Menü-Editor**: Doppelklick auf das Symbol,
F2, oder die Zeile `entries` im Objektinspektor. Links steht der Baum
der Einträge, rechts die Felder des ausgewählten. Ein Durchgang durch
den Dialog ist ein Schritt für „Rückgängig", egal wie viel du darin
geändert hast.

Menüs gehen bis zur **zweiten Ebene** („Datei → Zuletzt geöffnet"),
tiefer nicht – dort findet sich niemand mehr zurecht.

Im Quelltext geht es auch:

```python
self.mm_haupt.entries = [
    {"caption": "&Datei", "children": [
        {"caption": "&Neu", "shortcut": "Strg+N", "on_click": "mi_neu_klick"},
        {"separator": True},
        {"caption": "B&eenden", "on_click": "mi_ende_klick"},
    ]},
]
```

Einen einzelnen Eintrag findest du über seinen Bezeichner und änderst
ihn zur Laufzeit; danach `aktualisieren()` aufrufen:

```python
self.mm_haupt.eintrag("mi_speichern")["enabled"] = False
self.mm_haupt.aktualisieren()
```

## PopupMenu

Qt-Basis: `QMenu` (`pcl/components/menus.py`)

Eigenschaften und Einträge wie bei `MainMenu`.

Das Klappmenü auf die rechte Maustaste, wie `TPopupMenu` in Lazarus.
Zugeordnet wird es über die Eigenschaft `popup_menu` einer sichtbaren
Komponente:

```python
self.sg_tabelle.popup_menu = self.pm_tabelle
```

Die Zuordnung steht bei der Komponente und nicht beim Menü, weil
dasselbe Klappmenü an mehreren Komponenten hängen darf. Ohne
Zuordnung passiert nichts – ein Klappmenü ohne Ort, an dem es
aufklappt, ist kein Fehler, sondern nur noch nicht fertig.

## GroupBox

Qt-Basis: `QGroupBox` (`pcl/components/standard.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, enabled | wie `Control` | – | – | geerbt von `Control` |
| width | int | 185 | Layout | Breite in Pixeln |
| height | int | 105 | Layout | Höhe in Pixeln |
| caption | str | "GroupBox1" | Darstellung | Beschriftung über dem Rahmen |

Keine eigenen Ereignisse.

## Panel

Qt-Basis: `QFrame` mit eigener Beschriftung (`pcl/components/standard.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, enabled | wie `Control` | – | – | geerbt von `Control` |
| width | int | 185 | Layout | Breite in Pixeln |
| height | int | 105 | Layout | Höhe in Pixeln |
| caption | str | "Panel1" | Darstellung | Beschriftung, mittig auf der Fläche; leer = keine |
| color | str (Hex) | "" | Darstellung | Hintergrundfarbe als #RRGGBB, leer = Farbe des Themes |

Keine eigenen Ereignisse.

Die Beschriftung wird selbst gezeichnet statt über ein Kind-`QLabel`
gelegt: ein Kind-Widget läge sonst über den Komponenten, die später auf
dem Panel entstehen, und finge deren Mausklicks ab.

## Behälter: was `GroupBox`, `Panel` und `RadioGroup` schon können

`Control` nimmt seit jeher ein beliebiges `parent` entgegen und hängt
sich an dessen `_qwidget`. Ein `GroupBox` oder `Panel` als `parent`
funktioniert damit zur **Laufzeit** vollständig: die Kind-Komponente
wird auf den Behälter geklebt, `left`/`top` zählen ab dessen linker
oberer Ecke, und `enabled = False` am Behälter sperrt den ganzen Inhalt
auf einmal (das erledigt Qt).

```python
self.g_zahlung = GroupBox(self)
self.rb_bar = RadioButton(self.g_zahlung)   # links/oben relativ zur GroupBox
```

Im **Designer** geht das noch nicht: dort landet jede abgelegte
Komponente am Formular. Optisch ist das Ergebnis dasselbe (die
Komponente liegt über dem Behälter), die `.pfm` beschreibt sie aber als
Kind des Formulars. Was dafür fehlt, steht unter „Offene Punkte“.

`RadioGroup` braucht das alles **nicht**: sie erzeugt ihre Optionsfelder
wie `TRadioGroup` in Lazarus selbst aus `items` und ist damit auch im
Designer vollständig benutzbar.

## RadioGroup

Qt-Basis: `QGroupBox` mit je einem `QRadioButton` pro Eintrag
(`pcl/components/standard.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, enabled | wie `Control` | – | – | geerbt von `Control` |
| width | int | 185 | Layout | Breite in Pixeln |
| height | int | 105 | Layout | Höhe in Pixeln |
| caption | str | "RadioGroup1" | Darstellung | Beschriftung über dem Rahmen |
| items | `Strings` | leer | Daten | Die Optionen; Sammlungs-Eigenschaft (siehe „Schrift und Sammlungen“) |
| item_index | int | -1 | Verhalten | Index der gewählten Option, -1 = keine Auswahl |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | Wechsel der Auswahl (Klick oder Code) |

Gegen `RadioGroup1` aus `tests/daten/lazarus/f_Pizza` geprüft – dort zwar
nur deklariert, aber mit denselben Eigenschaftsnamen wie `TRadioGroup`
(`Items`, `ItemIndex`, `Caption`).

Anders als bei einzelnen `RadioButton`-Komponenten ist die gegenseitige
Ausschließlichkeit hier echt: Qt setzt sie innerhalb der `QGroupBox`
automatisch durch, und `item_index` ist die eine Stelle, an der die
Auswahl steht.

`item_index` zeigt nie auf eine Option, die es nicht gibt: ein Index
außerhalb von `0..len(items)-1` fällt auf `-1` zurück – sowohl beim
Zuweisen als auch, wenn `items` kürzer wird. `item_index = -1` hebt die
Auswahl wirklich auf. Das musste eigens gelöst werden: ein Optionsfeld
in einer Gruppe lässt sich mit `setChecked(False)` nicht abwählen, weil
Qt in einer Gruppe immer eine gewählte Schaltfläche haben will – die
Komponente hebt `autoExclusive` dafür kurz auf.

## Chart

Qt-Basis: `FigureCanvasQTAgg` aus matplotlib (`pcl/components/chart.py`)

Die einzige Komponente, die nicht auf einem Qt-Standardwidget sitzt.
Sie deckt Abschnitt 11.6 ab und ist die Grundlage der Auswertungen in
M10 (Regression mit scikit-learn).

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, enabled | wie `Control` | – | – | geerbt von `Control` |
| width | int | 320 | Layout | Breite in Pixeln |
| height | int | 240 | Layout | Höhe in Pixeln |
| kind | str | "bar" | Darstellung | Diagrammart: bar, line, pie, scatter, histogram, boxplot |
| title | str | "" | Darstellung | Überschrift über dem Diagramm |
| x_label | str | "" | Darstellung | Beschriftung der x-Achse |
| y_label | str | "" | Darstellung | Beschriftung der y-Achse |
| legend | bool | False | Darstellung | Legende mit den Serientiteln anzeigen |
| grid | bool | False | Darstellung | Gitternetzlinien anzeigen |

Keine Ereignisse.

Methoden zum Zeichnen: `add_bar_series(kategorien, werte, *, title="")`,
`add_line_series(x, y, *, title="")`,
`add_pie_series(labels, werte, *, title="")`,
`add_scatter_series(x, y, *, title="")`,
`add_histogram_series(werte, *, bins=10, title="")`,
`add_boxplot_series(werte, *, title="")`, `clear()`. Alle nehmen Listen
**und** pandas-Serien entgegen – matplotlib versteht beide Formen
direkt.

Methoden zum Laden von Daten (M10):

| Methode | Woher |
|---|---|
| `load_csv(pfad, x, y, *, sep=None, decimal=None)` | CSV-Datei; `x`/`y` als Spaltenname **oder** Spaltennummer. Trennzeichen und Dezimalkomma werden ohne Angabe selbst erkannt |
| `load_query(verbindung, sql, *, x=None, y=None)` | Datenbankabfrage über eine `SQLite3Connection`/`MySQLConnection` aus M5 |
| `load_grid(stringgrid, *, x=None, y=None)` | `StringGrid` desselben Formulars – der häufigste Weg im Unterricht: Daten erst als Tabelle zeigen, dann als Diagramm |

Alle drei enden in **einem** `pandas.DataFrame`, abrufbar über
`Chart.dataframe`. So gibt es intern nur einen Datenweg, und Diagramm
wie Regression müssen nichts über die Herkunft wissen. Ohne `x`/`y`
nehmen `load_query` und `load_grid` die ersten beiden Spalten.

Regression: `add_regression(x=None, y=None, art="linear", *, grad=2)`
legt die Gerade bzw. Kurve über die vorhandenen Punkte, schreibt die
Formel in die Legende und **gibt das Ergebnis zurück** (siehe
`pcl.analyse` unten). Ohne `x` und `y` rechnet sie mit den zuletzt
geladenen Daten.

Ein Kreisdiagramm bekommt **keine** Legende, auch wenn `legend` gesetzt
ist: seine Stücke tragen ihre Beschriftung schon selbst, und ein
Legendenkasten deckte in der Sichtprüfung ein Stück samt Beschriftung
zu. Ein zu langer `title` wird umgebrochen statt abgeschnitten –
matplotlib kürzt einen Titel nicht von sich aus.

Das Standardformat ist mit 320x240 größer als bei allen anderen
Komponenten; mit den 75x25 aus `Control` wäre nach dem Ablegen aus der
Palette nur der Figurenrahmen zu sehen.

`kind` legt fest, was **ohne** eigenen `add_*_series`-Aufruf zu sehen
ist: solange keine echten Daten da sind, zeichnet die Komponente eine
kleine Beispielreihe in der gewählten Art. Im Designer steht damit ein
erkennbares Diagramm statt eines leeren Rechtecks. Der erste
`add_*_series`-Aufruf wirft die Vorschau weg, `clear()` lässt bewusst
leer. Ein unbekannter Wert fällt wie bei `Shape.shape` auf `bar`
zurück, statt die Anzeige mit einem Fehler abzubrechen.

Die Serienfarben kommen aus `design/tokens.json`, Eintrag
`color.<theme>.chart` – sechs Farben, die sich bei mehr Serien
wiederholen. Sie beginnen mit der Akzentfarbe, damit das übliche
Diagramm mit einer Serie so aussieht wie gewohnt. Ein Diagramm färbt
sich beim Erzeugen einmalig nach dem aktuellen Theme ein; ein späterer
Theme-Wechsel zur Laufzeit wirkt (wie bei allen `pcl`-Komponenten)
nicht rückwirkend.

## Auswertung: `pcl.analyse`

`pcl/analyse.py`. Keine Komponente, sondern eine Funktion auf
Modulebene – das Gegenstück zu `pcl.dialogs` für die Datenauswertung
aus M10.

```python
ergebnis = pcl.analyse.regression(groessen, schuhgroessen, art="linear")
self.l_steigung.caption = f"Steigung: {ergebnis.steigung:.2f}"
```

| Funktion | Signatur |
|---|---|
| regression | `(x, y, art="linear", *, grad=2) -> Regressionsergebnis` |

`art` ist `linear`, `polynomial` (mit `grad=2` oder `3`),
`exponentiell` oder `logarithmisch`. Gerechnet wird über
`numpy.polyfit`, **nicht** über scikit-learn: numpy ist klein, immer da
und für diese vier Arten völlig ausreichend. scikit-learn liegt dem
Programm trotzdem bei, damit Fortgeschrittene damit arbeiten können –
Natter selbst hängt aber nicht davon ab.

`Regressionsergebnis` ist bewusst ein kleines, lesbares Objekt statt
der scikit-learn-API:

| Feld | Bedeutung |
|---|---|
| steigung | linear: `m` aus `y = m·x + b`; polynomial: Koeffizient des Glieds `·x`; exponentiell: Wachstumsrate im Exponenten; logarithmisch: Faktor vor `ln(x)` |
| achsenabschnitt | Wert bei `x = 0` |
| bestimmtheitsmass | R², immer auf der **Originalskala** gerechnet – auch bei exponentiell und logarithmisch, sonst gehörte die Zahl zu einer anderen Kurve als der gezeichneten |
| formel | lesbarer Text, z. B. `y = 2,31·x + 4,07` |
| koeffizienten | alle Koeffizienten, höchste Potenz zuerst |
| vorhersage(x) | y-Wert zu einem x oder zu einer Reihe von x-Werten |

Rechenrauschen wird geglättet: `numpy.polyfit` liefert für die
Normalparabel `1,0·x² - 1,21e-14·x + 2,37e-14`. Koeffizienten unter dem
1e-10-fachen des größten werden auf glatt 0 gesetzt, damit in der
Legende `y = 1,00·x²` steht.

## Dialogfunktionen

`pcl/dialogs.py`. Keine Komponenten, sondern modale Funktionen auf
Modulebene (Abschnitt 5.1, 5.2), analog `ShowMessage`/`InputBox` in der
LCL. `message_dlg`, `OpenDialog`, `SaveDialog`, `SelectDirectoryDialog`,
`ColorDialog`, `FontDialog` sind in keinem Referenzprojekt genutzt und
daher zurückgestellt.

| Funktion | Signatur | Entspricht |
|---|---|---|
| show_message | (text: str) -> None | `ShowMessage` |
| input_box | (titel: str, frage: str, standard: str = "") -> str | `InputBox`, liefert bei Abbruch `standard` |

Gegen die echte Nutzung in `g_StringGrid`/`j_komplexeLeistung`/`l_Pet`/
`m_Gaestebuch` (`show_message`) und `q_Würfelspiel` (`input_box`) geprüft.

## Schrift und Sammlungen

Zwei Eigenschaftsarten gelten quer über die Komponenten hinweg und
tauchen deshalb nicht in jeder Tabelle oben einzeln auf.

### font (jede `Control`-Komponente)

Entspricht `TFont` in Lazarus (`pcl/font.py`), aufklappbare
Untereigenschaft wie `Shape.brush`:

| Untereigenschaft | Typ | Standardwert | Hilfetext |
|---|---|---|---|
| font.name | str | "" | Schriftart; leer = Schriftart des Themes |
| font.size | int | 0 | Schriftgröße in Punkt; 0 = Größe des Themes |
| font.bold | bool | False | Fettschrift (Lazarus `Font.Style = [fsBold]`) |
| font.italic | bool | False | Kursivschrift (Lazarus `fsItalic`) |

In der `.pfm`, im erzeugten Code und im Objektinspektor erscheinen sie
flach als `font_name`, `font_size`, `font_bold`, `font_italic`
(`pcl.properties.VERSCHACHTELTE_EIGENSCHAFTEN`). Sie wirken über ein
komponenteneigenes Stylesheet, nicht über `QWidget.setFont()`: das Theme
setzt `font-family`/`font-size` per QSS, und ein Stylesheet schlägt in Qt
immer `setFont()`.

### items / lines (`ListBox`, `ComboBox`, `Memo`)

Zeilenweise `Strings`-Sammlungen (`pcl/strings.py`). Neben `add`,
`clear`, `load_from_file`, `save_to_file`, Indizierung und Iteration
lässt sich der ganze Inhalt auf einmal zuweisen:

    self.lb_sorten.items = ["Hawaii", "Napoli"]

In der `.pfm` stehen sie als Liste von Zeichenketten; im
Objektinspektor öffnet ein Doppelklick auf die Zeile einen Zeileneditor
(wie der „…“-Knopf in Lazarus). Der Codegenerator schreibt sie **vor**
allen anderen Eigenschaften, weil das Füllen der Sammlung die Auswahl im
Qt-Widget zurücksetzt und eine im Designer gesetzte `item_index`-
Vorauswahl sonst wieder verloren ginge.

## Offene Punkte

Was den Komponenten aus Schritt 6 noch fehlt und **außerhalb von `pcl`**
gelöst werden muss – festgehalten, damit es nicht in Modulen versickert,
die niemand mehr liest:

1. **Behälter im Designer.** Eine im Designer abgelegte Komponente wird
   immer ein Kind des Formulars (`ide/designer/canvas.py`,
   `_PlatzierenKommando`: `typ(canvas.formular)`). Damit ein `Panel` oder
   eine `GroupBox` dort wirklich etwas aufnimmt, müssten vier Stellen
   zusammenspielen: der Designer müsste beim Ablegen den Behälter unter
   dem Mauszeiger als `parent` wählen und die Koordinaten umrechnen,
   `ide/inspector/komponentenbaum.py` die Kinder am Behälter statt am
   Formular suchen (`kind_komponenten` liest heute `vars(objekt)`, ein
   Kind des Panels steht aber als Attribut des Formulars da),
   `ide/designer/pfm_schreiben.py` sie in das bereits vorhandene
   `children`-Feld des Behälters schreiben (`schemas/pfm.schema.json`
   kann Verschachtelung schon) und `ide/codegen/design.py` daraus
   `Button(self.p_feld)` statt `Button(self)` erzeugen.
2. **Die Datenbank-Komponenten im Designer.** Für den `Timer` ist das
   in M14 gelöst: `Control.nur_im_designer` gibt ihm ein Symbol auf dem
   Formular, das im laufenden Programm verschwindet. Bei
   `SQLite3Connection`, `SQLQuery` und `DataSource` fehlt dafür noch
   ein Stück, das der Timer nicht brauchte: ihre Konstruktoren
   verlangen eine andere Komponente (`SQLQuery(verbindung)`), der
   Designer erzeugt aber für jede Komponente `Typ(self)`. Es bräuchte
   also eine Eigenschaft, die auf eine andere Komponente zeigt — in der
   `.pfm`, im Objektinspektor und in der Codeerzeugung.
3. **Standardgrößen beim Ablegen.** `_STANDARDGROESSEN` in
   `ide/designer/canvas.py` kennt die meisten neuen Komponenten nicht
   (die beiden Menüs stehen seit M15 drin, weil ein Symbol quadratisch
   sein muss). Sie
   bringen ihre Größe deshalb als `Prop`-Standard selbst mit (wie
   `Chart`) – das wirkt überall gleich und ist die bessere Lösung, aber
   der Eintrag dort bleibt der Vollständigkeit halber offen.
4. **`SpinEdit` verliert im Designer seine Pfeilspitzen.**
   `ide/shell/theme.py` führt `QSpinBox` in derselben Regel wie
   `QLineEdit`/`QComboBox` (Zeile ~254). Sobald eine Komponente auch nur
   eine QSS-Regel abbekommt, zeichnet Qt sie vollständig aus dem
   Stylesheet – und die beiden Pfeilspitzen fallen ersatzlos weg
   (Bildvergleich, Schritt 6; `pcl/theme/__init__.py` nimmt `QSpinBox`
   deshalb bewusst aus). Das Stylesheet des Hauptfensters kaskadiert in
   das eingebettete Designer-Formular hinein, deshalb betrifft es dort
   auch `SpinEdit`; ebenso die `QSpinBox`-Felder der IDE selbst
   (`ide/diagramm/eigenschaften.py`, `ide/diagramm/klassendialog.py`).
   `QDoubleSpinBox` steht nicht in der Regel und ist darum in Ordnung –
   `FloatSpinEdit` sieht im Designer richtig aus. Die Korrektur ist ein
   Wort: `, QSpinBox` aus diesem einen Selektor streichen. Außerhalb von
   `pcl/` und deshalb hier nur festgehalten.
5. **`DateEdit`, `TimeEdit`, `Calendar`: erst die Frage klären, wie ein
   Datum aussieht.** Die Komponenten selbst wären wieder dünne Mäntel
   (`QDateEdit`, `QTimeEdit`, `QCalendarWidget`), aber `Prop` kennt
   bisher nur `str`, `int`, `float`, `bool` – die vier Typen, die der
   Objektinspektor anzeigen, die `.pfm` als JSON speichern und
   `pcl/errors.py` in einer deutschen Meldung benennen kann. Ein Datum
   braucht eine Entscheidung, die alle drei Stellen betrifft, und die
   sollte nicht nebenbei fallen:
   * als `str` in ISO-Form (`"2026-12-24"`) – serialisierbar ohne
     Änderung am Format, aber der Schüler rechnet mit Text statt mit
     `datetime.date`;
   * als `str` in deutscher Schreibweise (`"24.12.2026"`) – passt zur
     Oberfläche, ist aber zum Rechnen noch unhandlicher;
   * als echter `date`-Typ im `Prop`-System – am saubersten, verlangt
     aber einen neuen Typ in `_TYPNAMEN`, im Objektinspektor und in der
     `.pfm` (Formatversion!).

   Dazu kommt der Standardwert: `TDateEdit` zeigt in Lazarus *heute* an,
   ein `Prop`-Standard muss aber konstant sein, sonst stünde in jeder
   frisch gespeicherten `.pfm` das Datum des Tages, an dem sie entstand.
   Kein Referenzprojekt in `tests/daten/lazarus/` benutzt eine dieser drei
   Komponenten, es gibt also auch keine echte Nutzung, an der sich die
   Wahl prüfen ließe (Abschnitt 21: „MVP strikt an den Übungsprojekten
   ausrichten“). Deshalb bewusst offen gelassen statt geraten.
6. **Noch nicht umgesetzt:** `MaskEdit`, `PaintBox`, `HtmlViewer`,
   `Sound` und die restlichen Dialoge aus Abschnitt 5.2.
   `MainMenu` und `PopupMenu` standen hier bis M15; sie sind jetzt da,
   samt Menü-Editor im Designer.

## Vorlage pro Komponente

```
## <Komponente>

Qt-Basis: <...>

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| ... | ... | ... |
```
