# Komponenten-Referenz

Verbindliche Schnittstelle für `pcl`. Jede Komponente wird hier mit jeder
Eigenschaft (Name, Typ, Standardwert, Kategorie, deutscher Hilfetext) und
jedem Ereignis (Name, Signatur, Auslöser) dokumentiert, bevor sie in `pcl`
umgesetzt wird. Siehe konzept-natter.md, Abschnitt 5 und 23.2.

Status: `Form`, `Button`, `Label`, `Shape`, `Edit`, `CheckBox`,
`RadioButton`, `Memo`, `ListBox`, `ComboBox`, `StringGrid`, `Image`,
`ScrollBar` sind umgesetzt (M1, Schritt 2/3/6). Rest folgt später in
Schritt 6 – nur deklariert/nicht genutzt oder in keinem Referenzprojekt
vorhanden, daher niedrigere Priorität: `RadioGroup`, `GroupBox`, `Panel`,
`MainMenu`, `PopupMenu`, `SpinEdit`, `FloatSpinEdit`, `MaskEdit`,
`PaintBox`, `HtmlViewer`, `TrackBar`, `ProgressBar`, `DateEdit`, `TimeEdit`,
`Calendar`, Dialoge, `Timer`, `Sound`.

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
| lines | `Strings` | leer | – | mehrzeiliger Text; aufklappbare Untereigenschaft wie `Shape.brush`, kein eigenständiges `Prop` |

Keine eigenen Ereignisse. `lines` synchronisiert bisher nur in eine
Richtung (Zuweisung/`add`/`clear` → Anzeige); von Benutzern eingetippter
Text wird nicht in `lines` zurückgeschrieben (kein Referenzprojekt braucht
das bisher, siehe `referenz/lazarus/*` – nur `.Lines.Add`/`.Clear`).

## ListBox

Qt-Basis: `QListWidget` (`pcl/components/standard.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| items | `Strings` | leer | – | Einträge; aufklappbare Untereigenschaft, kein eigenständiges `Prop` |
| item_index | int | -1 | Verhalten | Index des ausgewählten Eintrags, -1 = keine Auswahl |

Keine eigenen Ereignisse (kein Referenzprojekt braucht bisher eines,
`item_index` wird bei Bedarf ausgelesen statt auf Änderung zu reagieren).

## ComboBox

Qt-Basis: `QComboBox` (`pcl/components/standard.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| items | `Strings` | leer | – | Einträge; aufklappbare Untereigenschaft, kein eigenständiges `Prop` |
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
