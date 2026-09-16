# Komponenten-Referenz

Verbindliche Schnittstelle für `pcl`. Jede Komponente wird hier mit jeder
Eigenschaft (Name, Typ, Standardwert, Kategorie, deutscher Hilfetext) und
jedem Ereignis (Name, Signatur, Auslöser) dokumentiert, bevor sie in `pcl`
umgesetzt wird. Siehe konzept-natter.md, Abschnitt 5 und 23.2.

Status: `Form`, `Button`, `Label`, `Shape` sind umgesetzt (M1, Schritt 2/3).
Rest folgt in M1, Schritt 6.

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
