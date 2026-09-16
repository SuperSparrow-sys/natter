# Komponenten-Referenz

Verbindliche Schnittstelle für `pcl`. Jede Komponente wird hier mit jeder
Eigenschaft (Name, Typ, Standardwert, Kategorie, deutscher Hilfetext) und
jedem Ereignis (Name, Signatur, Auslöser) dokumentiert, bevor sie in `pcl`
umgesetzt wird. Siehe konzept-natter.md, Abschnitt 5 und 23.2.

Status: `Form`, `Button`, `Label`, `Shape`, `Edit`, `CheckBox`, `RadioButton`
sind umgesetzt (M1, Schritt 2/3/6). Rest folgt später in Schritt 6
(`RadioGroup`, `Memo`, `ComboBox`, `ListBox`, `ScrollBar`, `GroupBox`,
`Panel`, `MainMenu`, `PopupMenu`, `StringGrid`, `Image`, `SpinEdit`,
`FloatSpinEdit`, `MaskEdit`, `PaintBox`, `HtmlViewer`, `TrackBar`,
`ProgressBar`, `DateEdit`, `TimeEdit`, `Calendar`, Dialoge, `Timer`,
`Sound`).

## Form

Qt-Basis: `QWidget` (`pcl/form.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| caption | str | "Form1" | Darstellung | Fenstertitel |
| width | int | 480 | Layout | Fensterbreite in Pixeln |
| height | int | 360 | Layout | Fensterhöhe in Pixeln |
| theme | str | "system" | Darstellung | Farbschema: system, light oder dark |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_create | (self, sender) | unmittelbar vor der ersten Anzeige |

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

Keine eigenen Ereignisse.

## Shape

Qt-Basis: eigenes Painting (`QPainter` auf `QWidget`, `pcl/components/additional.py`)

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left, top, width, height, enabled | wie `Control` | – | – | geerbt von `Control` |
| shape | str | "rectangle" | Darstellung | Form der Zeichnung: rectangle oder circle |
| brush.color | str (Hex) | "#000000" | Darstellung | Füllfarbe; aufklappbare Untereigenschaft, kein eigenständiges `Prop` |

Keine eigenen Ereignisse. `shape` ist aktuell ein einfacher `str` ohne
Aufzählungs-Editor im Inspektor (Abschnitt 5.0 sieht dafür später einen
echten Enum-Typ vor, sobald `Align`/`BorderStyle` u. Ä. eingeführt werden).

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

**Bekannte Lücke:** `on_click`/`on_double_click` gelten laut Abschnitt 5.4
für „alle sichtbaren“ Komponenten. Bisher ist `on_click` nur bei `Button`
umgesetzt (dort über das native Qt-`clicked`-Signal). Ein komponenten-
übergreifendes `on_click` über `Control` (inkl. eigener Maus-Ereignis-
Behandlung für Komponenten ohne natives Klick-Signal wie `Label`/`Shape`)
ist noch offen und wird nachgezogen, sobald ein Referenzprojekt es
tatsächlich braucht (bisher nutzt keines der Übungsprojekte das).

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
