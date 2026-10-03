# Komponenten-Referenz

Hier steht zu jeder Komponente, was sie kann: jede Eigenschaft mit
ihrem Typ, ihrem Standardwert und einem Satz dazu, und jedes Ereignis
mit seinem Auslöser. Dieselben Texte stehen als Kurzhinweis im
Objektinspektor, wenn der Mauszeiger über einer Zeile stehen bleibt.

Eigenschaften lassen sich im Designer (Objektinspektor) setzen oder im
Code über `self.` und den Namen der Komponente, zum Beispiel
`self.b_start.caption = "Los"`.

Im Objektinspektor haben manche Zeilen einen eigenen Editor: Farben
einen Knopf „…“ mit Farbwähler, Eigenschaften mit fester Auswahl
(`Shape.shape`, `Chart.kind`, `Form.theme`) eine Auswahlliste,
`font_name` eine Schriftauswahl und `Image.picture` eine
Dateiauswahl. Ein ungültiger Wert wird abgelehnt; unter der Tabelle
steht dann, warum. Über der Tabelle schalten „A–Z“ und „Kategorie“
zwischen alphabetischer Liste und Gruppen nach Kategorie um.

F1 öffnet diese Seite an der Stelle der Komponente, die im Designer
gewählt ist oder deren Klasse im Quelltext unter dem Cursor steht.
Strg+F sucht in der Seite, F3 springt zum nächsten Treffer.

## Was jede Komponente hat

Diese Eigenschaften und Ereignisse hat jede Komponente, die auf einem
Formular liegt. Sie stehen deshalb nicht in jeder Tabelle weiter unten
noch einmal.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| left | int | 0 | Layout | Position von links in Pixeln |
| top | int | 0 | Layout | Position von oben in Pixeln |
| width | int | 75 | Layout | Breite in Pixeln (manche Komponenten bringen eine eigene Vorgabe mit) |
| height | int | 25 | Layout | Höhe in Pixeln (dito) |
| enabled | bool | True | Verhalten | Legt fest, ob die Komponente bedienbar ist |
| visible | bool | True | Verhalten | Legt fest, ob die Komponente im laufenden Programm zu sehen ist |
| hint | str | "" | Verhalten | Hinweistext, der erscheint, wenn die Maus eine Weile auf der Komponente ruht; leer = keiner |
| anchors_left, anchors_top, anchors_right, anchors_bottom | bool | True, True, False, False | Layout | An welchen Rändern die Komponente hängt, siehe „Mit dem Fenster wachsen“ |
| popup_menu | PopupMenu | – | Verhalten | Klappmenü auf die rechte Maustaste, siehe `PopupMenu` |
| font_name, font_size, font_bold, font_italic, font_color | str, int, bool, bool, str | "", 0, False, False, "" | Schrift | Schrift der Komponente, siehe „Schrift und Sammlungen“ |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_click | (self, sender) | Maustaste auf der Komponente gedrückt und losgelassen |
| on_double_click | (self, sender) | Doppelklick |
| on_mouse_down | (self, sender, x, y) | Maustaste gedrückt |
| on_mouse_move | (self, sender, x, y) | Maus bewegt |
| on_mouse_up | (self, sender, x, y) | Maustaste losgelassen |
| on_mouse_enter | (self, sender) | Maus kommt auf die Komponente |
| on_mouse_leave | (self, sender) | Maus verlässt die Komponente |
| on_key_press | (self, sender, taste) | Tastendruck, solange die Komponente den Fokus hat |

Genaueres steht unter „Die Maus“, „Die Tastatur“ und „Ein- und
ausblenden“ weiter unten.

Dazu drei Methoden: `nach_vorne_bringen()` holt die Komponente vor
alle anderen, die sie überlappen, `nach_hinten_schicken()` schickt sie
dahinter. So liegt etwa ein `Label` über einer `Shape`. `set_focus()`
setzt den Fokus auf die Komponente, in einem `Edit` also den Cursor:

```python
def b_neu_click(self, sender) -> None:
    self.e_tipp.text = ""
    self.e_tipp.set_focus()
```

### Mit dem Fenster wachsen

Wird das Fenster im laufenden Programm größer gezogen, bleiben die
Komponenten zunächst, wo sie sind. `anchors` legt fest, an welchen
Rändern eine Komponente hängt; den Abstand zu diesen Rändern behält
sie, wenn sich die Größe ändert:

| Häkchen | Wirkung |
|---|---|
| links und rechts | die Komponente wird mit dem Fenster breiter |
| nur rechts | die Komponente rückt mit dem rechten Rand mit |
| oben und unten | die Komponente wird mit dem Fenster höher |
| nur unten | die Komponente rückt mit dem unteren Rand mit |

Vorgabe ist links und oben. Ein Notizfeld, das das ganze Fenster
füllen soll, bekommt zusätzlich rechts und unten, ein Knopf in der
rechten unteren Ecke nur rechts und unten:

```python
self.m_text.anchors.right = True
self.m_text.anchors.bottom = True
```

Im Objektinspektor sind es die vier Häkchen `anchors_left`,
`anchors_top`, `anchors_right` und `anchors_bottom`. Liegt die
Komponente in einem `Panel` oder einer `GroupBox`, zählen deren
Ränder. Im Designer bleibt alles liegen, wenn das Formular größer
gezogen wird; die Anker wirken erst im laufenden Programm.

`Timer`, `MainMenu` und `PopupMenu` sind im laufenden Programm nicht zu
sehen. Sie haben deshalb weder `visible` noch `hint` noch `popup_menu`
noch die Maus- und Tastatur-Ereignisse.

## Form

Das Fenster selbst.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| caption | str | "Form1" | Darstellung | Fenstertitel |
| width | int | 480 | Layout | Fensterbreite in Pixeln |
| height | int | 360 | Layout | Fensterhöhe in Pixeln, ohne eine Menüleiste |
| theme | str | "system" | Darstellung | Farbschema: system, light oder dark |
| color | str | "" | Darstellung | Hintergrundfarbe als #RRGGBB, leer = Farbe des Farbschemas |
| position | str | "screen_center" | Layout | Wo das Fenster erscheint: screen_center (Bildschirmmitte) oder designed (an left und top) |
| left | int | 0 | Layout | Abstand des Fensters vom linken Bildschirmrand in Pixeln (bei position = designed) |
| top | int | 0 | Layout | Abstand des Fensters vom oberen Bildschirmrand in Pixeln (bei position = designed) |
| icon | str | "" | Darstellung | Bilddatei für das Fenstersymbol, z. B. assets/symbol.png |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_create | (self, sender) | unmittelbar vor der ersten Anzeige |
| on_close | (self, sender) | beim Schließen des Fensters; gibt der Handler `False` zurück, bleibt das Fenster offen |
| on_click | (self, sender) | Klick auf die freie Fläche |
| on_double_click | (self, sender) | Doppelklick auf die freie Fläche |
| on_mouse_down | (self, sender, x, y) | Maustaste auf der Fläche gedrückt |
| on_mouse_move | (self, sender, x, y) | Maus über der Fläche bewegt |
| on_mouse_up | (self, sender, x, y) | Maustaste auf der Fläche losgelassen |
| on_key_press | (self, sender, taste) | Tastendruck irgendwo im Fenster, siehe „Die Tastatur“ |

Die Maus-Ereignisse gelten für die freie Fläche: ein Klick auf einen
Knopf ist kein Klick auf das Formular. `x` und `y` zählen von der
linken oberen Ecke des Arbeitsbereichs – bei einem Formular mit
Menüleiste also unterhalb der Leiste, wie `left` und `top` einer
Komponente.

`on_mouse_move` kommt auch ohne gedrückte Taste. Wer nur beim Ziehen
zeichnen will, merkt sich in `on_mouse_down` ein eigenes Kennzeichen
und fragt es im Handler ab.

`width`, `height`, `left` und `top` geben im laufenden Programm das
Fenster wieder, wie es gerade ist: nach dem Größerziehen, Maximieren
oder Verschieben stehen dort die neuen Werte. Ein
`self.height = 500` ändert deshalb nur die Höhe und lässt eine
inzwischen geänderte Breite stehen.

`theme` wählt man im Objektinspektor aus einer Liste; ein anderer Wert
als `system`, `light` oder `dark` wird abgelehnt.

`on_close` kann das Schließen ablehnen. Gibt der Handler `False`
zurück, bleibt das Fenster offen, egal ob es über das Kreuz in der
Titelleiste oder über `close()` geschlossen werden sollte. Jede andere
Rückgabe, auch keine, lässt es zugehen:

```python
def form_close(self, sender):
    if not ask_yes_no("Wirklich beenden? Nicht gespeicherte "
                      "Einträge gehen verloren."):
        return False
```

Methoden: `show()` zeigt das Fenster, `close()` schließt es. Ein
gezeigtes Fenster bleibt offen, bis es geschlossen wird, auch wenn es
nur in einer einfachen Variablen stand (`spiel = FormSpiel()`,
`spiel.show()`). Mit `self.spiel = FormSpiel()` kann das Formular
später noch darauf zugreifen, etwa auf das, was darin eingetragen
wurde.
`show_modal()` zeigt es ebenfalls, wartet aber, bis es wieder
geschlossen ist; solange lassen sich die anderen Fenster des Programms
nicht bedienen. Die Zeile danach kann lesen, was im Fenster eingetragen
wurde:

```python
from u_einstellungen import FormEinstellungen

def b_einstellungen_click(self, sender) -> None:
    dialog = FormEinstellungen()
    dialog.show_modal()
    self.l_name.caption = dialog.e_name.text
```

Ein Fenster erscheint in der Mitte des Bildschirms. Mit `position =
"designed"` steht es stattdessen an `left` und `top`; eine Zuweisung an
`left` oder `top` verschiebt ein offenes Fenster sofort. `icon` ist
wie das Bild eines `Image` eine Datei relativ zum Projektordner; im
Objektinspektor wählt „…“ sie aus und kopiert sie nach `assets/`.
Ohne `icon` zeigen Titelleiste und Taskleiste das Symbol von Natter.

Eigene Attribute auf dem Formular sind erlaubt, etwa
`self.punkte = 0`. Bei einer Komponente führt ein unbekannter Name
dagegen zu einer Fehlermeldung, damit ein Tippfehler wie
`self.b_ok.captoin = "OK"` auffällt.

## Button

Ein Knopf.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| caption | str | "Button" | Darstellung | Beschriftung des Buttons |
| default | bool | False | Verhalten | Wenn wahr, löst die Eingabetaste diesen Knopf aus, gleich in welchem Feld sie gedrückt wird |

Ereignisse wie jede Komponente; das kennzeichnende ist `on_click`.

Ein Knopf mit `default = True` ist der Standardknopf des Formulars:
die Eingabetaste in einem `Edit` klickt ihn, man muss nicht erst zur
Maus greifen. Ausgenommen sind ein `Memo`, in dem die Eingabetaste
eine neue Zeile beginnt, und ein `StringGrid`. Hat ein anderer Knopf
den Fokus, klickt die Eingabetaste diesen.

## Label

Ein Text auf dem Formular.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| caption | str | "Label1" | Darstellung | Anzeigetext |
| color | str | "" | Darstellung | Hintergrundfarbe als #RRGGBB (nur bei transparent=False) |
| transparent | bool | True | Darstellung | Wenn wahr, kein eigener Hintergrund |
| word_wrap | bool | True | Darstellung | Wenn wahr, bricht zu langer Text um |
| alignment | str | "left" | Darstellung | Ausrichtung des Textes: left (links), center (mittig) oder right (rechts) |

`word_wrap` steht auf `True`: ohne Umbruch verschwände, was breiter
ist als das Label, ohne Meldung. Wer ein Label in einer Zeile halten
will, setzt es auf `False`.

## Edit

Ein einzeiliges Eingabefeld.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| text | str | "" | Darstellung | Eingegebener bzw. angezeigter Text |
| read_only | bool | False | Verhalten | Wenn wahr, nicht bearbeitbar |
| color | str | "" | Darstellung | Hintergrundfarbe als #RRGGBB, leer = Farbe des Farbschemas |
| alignment | str | "left" | Darstellung | Ausrichtung des Textes: left (links), center (mittig) oder right (rechts) |
| password | bool | False | Verhalten | Wenn wahr, erscheint statt jedes Zeichens ein Punkt |
| max_length | int | 0 | Verhalten | Höchstzahl der Zeichen, die sich eintippen lassen; 0 = keine Grenze |
| numbers_only | bool | False | Verhalten | Wenn wahr, lassen sich nur Ziffern, ein Minus am Anfang und ein Komma eintippen |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | jede Änderung des Textes (Tastatur oder Code) |

`text` ist immer ein Text, auch wenn eine Zahl darin steht. Zum
Rechnen wird er umgewandelt: `int(self.e_zahl.text)` für eine ganze
Zahl oder `zahl(self.e_preis.text)` für eine Kommazahl mit
Dezimalkomma (siehe „Zahlen mit Dezimalkomma“).

`numbers_only` hält beim Tippen alles fern, was keine Zahl werden
kann. Ein leeres Feld oder ein einzelnes „-“ bleibt trotzdem möglich;
`zahl()` meldet das beim Umwandeln.

## CheckBox

Ein Kästchen zum Ankreuzen.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| caption | str | "CheckBox1" | Darstellung | Beschriftung |
| checked | bool | False | Verhalten | Legt fest, ob das Kästchen angehakt ist |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | Umschalten (Klick oder Code) |

## RadioButton

Ein einzelnes Optionsfeld.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| caption | str | "RadioButton1" | Darstellung | Beschriftung |
| checked | bool | False | Verhalten | Legt fest, ob die Option ausgewählt ist |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | Umschalten (Klick oder Code) |

Optionsfelder im selben Behälter schließen einander aus: wird eines
gewählt, springt das vorher gewählte heraus. Für eine feste Liste von
Optionen ist `RadioGroup` bequemer.

## Memo

Ein mehrzeiliges Textfeld.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| lines | `Strings` | leer | Daten | Der Inhalt, eine Zeile je Eintrag, siehe „Schrift und Sammlungen“ |
| read_only | bool | False | Verhalten | Wenn wahr, nicht bearbeitbar |

Nur im Programm, nicht im Objektinspektor: `text` ist derselbe Inhalt
als ein einziger Text, die Zeilen durch Zeilenumbrüche getrennt.
`self.m_notiz.text = "Erste Zeile\nZweite Zeile"` setzt zwei Zeilen,
und `self.m_notiz.text` liefert den ganzen Inhalt zum Weiterverarbeiten.

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | jede Änderung des Textes (Tastatur oder Code) |

`lines` gilt in beide Richtungen: was das Programm zuweist, steht im
Memo, und was jemand ins Memo tippt, steht in `lines`. Damit speichert
`self.m_notiz.lines.save_to_file("notiz.txt")` den Text, der auf dem
Bildschirm steht.

## ListBox

Eine Liste zum Auswählen.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| items | `Strings` | leer | Daten | Die Einträge, siehe „Schrift und Sammlungen“ |
| item_index | int | -1 | Verhalten | Index des ausgewählten Eintrags, -1 = keine Auswahl |
| multi_select | bool | False | Verhalten | Wenn wahr, lassen sich mit Strg oder Umschalt mehrere Einträge wählen |
| sorted | bool | False | Verhalten | Wenn wahr, stehen die Einträge alphabetisch geordnet |
| selected | list\[int\] | \[\] | – | Die Nummern der gewählten Einträge (nur im Code) |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | ein anderer Eintrag wird ausgewählt |

Mit `multi_select` wählt ein Klick bei gedrückter Strg-Taste einen
weiteren Eintrag dazu, die Umschalttaste einen ganzen Bereich.
`selected` liefert die Nummern aller gewählten Einträge, aufsteigend;
eine Zuweisung wie `self.lb_sorten.selected = [0, 2]` wählt genau
diese.

```python
for nummer in self.lb_sorten.selected:
    self.m_bestellung.lines.add(self.lb_sorten.items[nummer])
```

Mit `sorted` ordnet die Liste auch später hinzugefügte Einträge
alphabetisch ein; Groß- und Kleinschreibung zählen dabei nicht.
`items` hat dann dieselbe Reihenfolge wie die Anzeige.

Ändert sich `items`, bleibt die Auswahl stehen: dieselbe Nummer, in
einer sortierten Liste derselbe Eintrag. Nur wenn es die gewählte
Nummer danach nicht mehr gibt, wird `item_index` zu -1, und
`on_change` meldet das. Eine Nummer, zu der es keinen Eintrag gibt
(`item_index = 5` bei zwei Einträgen), wählt nichts und ergibt
ebenfalls -1.

## ComboBox

Eine Auswahlliste zum Aufklappen.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| items | `Strings` | leer | Daten | Die Einträge, siehe „Schrift und Sammlungen“ |
| item_index | int | -1 | Verhalten | Index des ausgewählten Eintrags, -1 = keine Auswahl |
| text | str | "" | Darstellung | Angezeigter bzw. ausgewählter Text |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | ein anderer Eintrag wird ausgewählt |

`item_index` und `text` halten sich gegenseitig auf dem gleichen Stand.
Ein `text`, der nicht in `items` steht, lässt die Auswahl, wie sie
ist; `text` liefert danach den Eintrag, der tatsächlich zu sehen ist.
Wie bei der `ListBox` bleibt die Auswahl stehen, wenn sich `items`
ändert.

## StringGrid

Eine Tabelle mit Zellen aus Text.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| row_count | int | 5 | Daten | Anzahl der Zeilen, ab 0 |
| col_count | int | 5 | Daten | Anzahl der Spalten, ab 0 |
| cells\[spalte, zeile\] | str | "" | – | Inhalt einer Zelle |
| col_titles | `Strings` | leer | Daten | Die Spaltenköpfe, einer je Zeile; leer = Spaltennummern |
| default_col_width | int | 100 | Layout | Breite der Spalten in Pixeln, sofern col_widths nichts anderes sagt |
| col_widths\[spalte\] | int | – | – | Breite einer einzelnen Spalte (nur im Code) |
| col | int | -1 | – | Spalte der gewählten Zelle, -1 = keine Auswahl (nur im Code) |
| row | int | -1 | – | Zeile der gewählten Zelle, -1 = keine Auswahl (nur im Code) |
| read_only | bool | False | Verhalten | Wenn wahr, lassen sich die Zellen nicht bearbeiten; das Programm kann weiter hineinschreiben |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_select_cell | (self, sender, spalte, zeile) | eine andere Zelle wird ausgewählt |
| on_edit_cell | (self, sender, spalte, zeile, text) | eine Zelle wurde geändert |

`spalte` und `zeile` stehen in dieser Reihenfolge, wie bei
`cells[spalte, zeile]`.

`on_edit_cell` meint die Änderung durch den Benutzer. Was das Programm
selbst hineinschreibt (`cells[…] = …`, `load_dataframe`), löst es
nicht aus – sonst feuerte schon das Füllen der Tabelle hundert
Ereignisse.

`load_dataframe(df)` schreibt die Spaltennamen in Zeile 0 und die Werte
als Text darunter, Kommazahlen mit Dezimalkomma und so geschrieben
wie mit `text()`: „2,4“, „0,3“ statt „0,30000000000000004“ und
„0,00001“ statt „1e-05“.
`to_dataframe()` liest die Tabelle zurück. Eine Spalte, in der jede
Zelle leer oder eine Zahl ist („3“, „2,5“, „1.000“), kommt als Zahlen
zurück, sodass `df["Anzahl"].sum()` und `df["Note"].mean()` rechnen:
ganze Zahlen als `int`, sonst als Kommazahl, eine leere Zelle als
fehlender Wert. Alle anderen Spalten bleiben Text, auch eine, in der
ein Wert mit „0“ und einer weiteren Ziffer beginnt: „01067“ ist eine
Postleitzahl und behält ihre führende Null, wie beim CSV-Import im
Datenbank-Panel. Eine ganze Zahl kommt mit allen Stellen zurück, eine
Zelle wie „2,5 · 10^21“ als Kommazahl.

Auch große Datensätze passen hinein. `load_dataframe` legt die Werte
unverändert ab, zu Text werden sie erst, wenn eine Zelle zu sehen ist
oder abgefragt wird. 100.000 Zeilen mit vier Spalten sind so in
einer Zehntelsekunde geladen und belegen rund 20 MB, eine Million
Zeilen in etwa einer halben Sekunde rund 160 MB.

Ein Doppelklick im Designer legt `on_select_cell` an.

Die Spaltenköpfe stehen über der Tabelle und scrollen nicht mit weg:

```python
self.sg_punkte.col_titles = ["Name", "Punkte"]
self.sg_punkte.col_widths[0] = 160
self.sg_punkte.read_only = True
```

Eine Zelle außerhalb von `row_count` und `col_count` meldet sich mit
einem Fehler, der den gültigen Bereich nennt; gezählt wird ab 0.

`row` und `col` sagen, welche Zelle gewählt ist, etwa für einen Knopf
„Zeile löschen“. Zugewiesen wählen sie eine Zelle aus dem Programm und
lösen dabei `on_select_cell` aus. War noch nichts gewählt, gilt für
die andere Angabe 0. Mit -1 ist danach keine Zelle mehr gewählt.

```python
if self.sg_punkte.row >= 0:
    name = self.sg_punkte.cells[0, self.sg_punkte.row]
self.sg_punkte.row = 0
```

## Image

Ein Bild.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| picture | str | "" | Darstellung | Bilddatei, z. B. `assets/cookie.png`; im Objektinspektor über „…“ wählbar |
| stretch | bool | True | Darstellung | Bild auf die Größe der Komponente ziehen |
| proportional | bool | False | Darstellung | Beim Ziehen das Seitenverhältnis behalten |
| center | bool | False | Darstellung | Bild mittig setzen, wenn es kleiner ist als die Komponente |

Das Bild lässt sich auf drei Wegen setzen: eine Bilddatei aus dem
Explorer auf das Formular ziehen, im Objektinspektor in der Zeile
`picture` auf „…“ klicken, oder im Code:

```python
self.i_bild.picture.load_from_file("assets/cookie.png")
self.i_bild.picture.clear()          # Bild entfernen
```

Ein Bild von außerhalb des Projekts kopiert der Designer nach
`assets/`. Gespeichert wird der Pfad relativ zum Projektordner; das
Programm findet das Bild damit auch, wenn es aus einem anderen Ordner
gestartet wird.

`stretch` steht auf `True`, weil ein zu großes Bild ohne Skalierung
oben links abgeschnitten würde. Wer das Bild in Originalgröße will,
schreibt `self.i_bild.stretch = False`. Gerechnet wird immer vom
ungeskalierten Bild (`picture.original`); zweimal hintereinander
skaliert gäbe es sonst Treppen.

## Shape

Eine gezeichnete Form.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| shape | str | "rectangle" | Darstellung | Form der Zeichnung: rectangle, circle oder rounded_rectangle |
| brush_color | str | "#c0c0c0" | Darstellung | Füllfarbe als #RRGGBB; im Code `self.s_form.brush.color` |
| pen_color | str | "#000000" | Darstellung | Randfarbe als #RRGGBB, unabhängig von der Füllfarbe |
| transparent | bool | False | Darstellung | Wenn wahr, keine Füllung, nur der Rand |

`shape` wählt man im Objektinspektor aus einer Liste; im Code wird ein
Wert außerhalb dieser drei mit einer Fehlermeldung abgelehnt.

## ScrollBar

Ein waagrechter Rollbalken.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| minimum | int | 0 | Verhalten | Kleinster möglicher Wert |
| maximum | int | 100 | Verhalten | Größter möglicher Wert |
| position | int | 0 | Verhalten | Aktueller Wert |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | Änderung der Position (Ziehen oder Code) |

## SpinEdit

Ein Zahlenfeld mit zwei Pfeilknöpfen.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| minimum | int | 0 | Verhalten | Kleinster möglicher Wert |
| maximum | int | 100 | Verhalten | Größter möglicher Wert |
| value | int | 0 | Verhalten | Aktueller Wert |
| increment | int | 1 | Verhalten | Schrittweite der beiden Pfeilknöpfe |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | Änderung des Wertes (Pfeilknopf, Tastatur oder Code) |

Der Wert heißt hier `value`, bei `ScrollBar` und `TrackBar` dagegen
`position`: bei einem Schieber ist die Stellung gemeint, bei einem
Zahlenfeld die Zahl.

Ein Wert außerhalb von `minimum`..`maximum` wird auf die Grenze
gekappt; `value` trägt danach den gekappten Wert.

## FloatSpinEdit

Ein Zahlenfeld für Kommazahlen.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| minimum | float | 0,0 | Verhalten | Kleinster möglicher Wert |
| maximum | float | 100,0 | Verhalten | Größter möglicher Wert |
| value | float | 0,0 | Verhalten | Aktueller Wert |
| increment | float | 1,0 | Verhalten | Schrittweite der beiden Pfeilknöpfe |
| decimals | int | 2 | Darstellung | Anzahl der angezeigten Nachkommastellen |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | Änderung des Wertes (Pfeilknopf, Tastatur oder Code) |

Das Feld zeigt und nimmt immer ein Dezimalkomma an, auch auf einem
Rechner mit englischer Systemsprache.

Eine ganze Zahl darf ebenfalls zugewiesen werden; gelesen wird immer
eine Kommazahl. `decimals` rundet den Wert selbst, nicht nur die
Anzeige: nach `decimals = 1` ist aus 2,25 ein 2,3 geworden, und `value`
liefert danach ebenfalls 2,3.

## TrackBar

Ein Schieberegler.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| width | int | 150 | Layout | Breite in Pixeln |
| height | int | 30 | Layout | Höhe in Pixeln |
| minimum | int | 0 | Verhalten | Kleinster möglicher Wert |
| maximum | int | 10 | Verhalten | Größter möglicher Wert |
| position | int | 0 | Verhalten | Aktueller Wert |
| frequency | int | 1 | Darstellung | Abstand der Teilstriche unter dem Schieber; 0 = keine Teilstriche |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | Änderung der Position (Ziehen, Tastatur oder Code) |

`maximum` ist 10: bei 100 Schritten und `frequency = 1` verschmölzen
die Teilstriche zu einem Balken.

## ProgressBar

Ein Fortschrittsbalken.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| width | int | 150 | Layout | Breite in Pixeln |
| height | int | 22 | Layout | Höhe in Pixeln |
| minimum | int | 0 | Verhalten | Kleinster möglicher Wert |
| maximum | int | 100 | Verhalten | Größter möglicher Wert |
| position | int | 0 | Verhalten | Aktueller Wert (Füllstand) |
| show_text | bool | True | Darstellung | Prozentzahl im Balken anzeigen |

Ein `position` außerhalb von `minimum`..`maximum` wird auf die Grenze
gekappt.

## PaintBox

Eine freie Zeichenfläche. `Shape` legt fertige Formen hin, `PaintBox`
zeichnet mit Koordinaten: der Ursprung liegt links oben, `x` läuft nach
rechts, `y` nach unten.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| border_color | str | "#90a4ae" | Darstellung | Farbe des Rahmens um die Zeichenfläche als #RRGGBB |
| canvas | Canvas | – | – | die Zeichenfläche selbst |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_paint | (self, sender) | die Fläche ist neu entstanden: beim ersten Anzeigen und nach jeder Größenänderung |

| Methode | Bedeutung |
|---|---|
| `clear()` | löscht die Fläche (Kurzform für `canvas.clear()`) |
| `repaint()` | löst `on_paint` von Hand aus |

### Canvas

| Methode | Bedeutung |
|---|---|
| `move_to(x, y)` | setzt den Stift, ohne zu zeichnen |
| `line_to(x, y)` | zieht eine Linie dorthin und setzt den Stift nach |
| `line(x1, y1, x2, y2)` | Kurzform aus `move_to` und `line_to` |
| `rectangle(x1, y1, x2, y2)` | Rechteck: Rand in `pen`, Fläche in `brush`; beide Ecken gehören dazu |
| `ellipse(x1, y1, x2, y2)` | Ellipse im angegebenen Rechteck; ein Quadrat ergibt einen Kreis |
| `fill_rect(x1, y1, x2, y2)` | füllt ein Rechteck ohne Rand; beide Ecken gehören dazu, dieselben Zahlen ergeben dieselbe Fläche wie bei `rectangle` |
| `text_out(x, y, text)` | schreibt Text; `(x, y)` ist die linke obere Ecke |
| `clear()` | löscht die ganze Fläche |
| `pixels[x, y]` | einzelner Bildpunkt – lesen liefert `#RRGGBB`, zuweisen setzt ihn. Eine Stelle außerhalb der Fläche ergibt beim Lesen einen `IndexError` |
| `width` / `height` | Größe der Fläche in Pixeln |

`pen` hat `color` und `width`, `brush` hat `color` und `style`.
`style = "clear"` zeichnet nur den Umriss, `"solid"` füllt.

```python
stift = self.pb_bild.canvas
stift.brush.color = "#e3f2fd"
stift.rectangle(20, 20, 436, 240)

stift.pen.color = "#8d6e63"
stift.pen.width = 3
stift.line(190, 130, 140, 100)

stift.text_out(30, 30, "Mit Koordinaten gezeichnet")
```

Das Gezeichnete bleibt stehen: gemalt wird in ein Bild im Speicher.
Ein Fenster, das darüberfährt, löscht nichts, und beim Größerziehen
bleibt erhalten, was schon da war. Das gilt auch für das, was beim
Verkleinern kurz außerhalb der Fläche lag: nach dem Zurückvergrößern
ist es wieder zu sehen. `width` und `height` geben die sichtbare
Größe an. Gezeichnet wird ohne
Kantenglättung, damit `pixels[x, y]` genau die Farbe liefert, mit der
gezeichnet wurde.

## Timer

Ein Zeitgeber. Im Designer liegt er als kleine Uhr auf dem Formular,
im laufenden Programm ist er nicht zu sehen.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| enabled | bool | True | Verhalten | Legt fest, ob der Zeitgeber läuft |
| interval | int | 1000 | Verhalten | Abstand zwischen zwei Auslösungen in Millisekunden, ab 1 |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_timer | (self, sender) | nach jeweils `interval` Millisekunden, solange `enabled` wahr ist |

Ein Doppelklick auf die Uhr legt die Methode für `on_timer` an. Ein
frisch erzeugter Zeitgeber läuft sofort los; `enabled = False` hält
ihn an. Im Code geht es auch:

```python
self.t_ampel = Timer(self)
self.t_ampel.interval = 2000
self.t_ampel.on_timer = self.t_ampel_timer
```

Wird das Formular geschlossen, halten seine Zeitgeber an: ein
Countdown in einem geschlossenen Spielfenster meldet sich nicht mehr.
Beim nächsten `show()` laufen die wieder, bei denen `enabled` wahr ist.

## MainMenu

Die Menüleiste am oberen Rand des Fensters. Auf dem Formular liegt nur
ein kleines Symbol; die Leiste erscheint im laufenden Programm.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| width | int | 32 | Layout | Breite des Symbols |
| height | int | 32 | Layout | Höhe des Symbols |
| entries | Liste | [] | Allgemein | Die Einträge des Menüs (Doppelklick öffnet den Menü-Editor) |

Das Menü selbst hat keine Ereignisse; jeder Eintrag hat sein eigenes.

Die Leiste sitzt über dem Inhalt: das Fenster wächst um ihre Höhe, und
`top = 0` bleibt der obere Rand des Arbeitsbereichs. Ein Knopf ganz
oben steht auch im laufenden Programm ganz oben und nicht hinter dem
Menü.

### Die Einträge

Ein Eintrag hat diese Felder:

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

Ausgefüllt wird das im Menü-Editor: Doppelklick auf das Symbol, F2,
oder die Zeile `entries` im Objektinspektor. Links steht der Baum der
Einträge, rechts die Felder des ausgewählten. Der Knopf „Methode
anlegen“ neben „Beim Anklicken“ schreibt die Methode in den Quelltext
des Formulars und springt dorthin; steht im Feld noch kein Name, wird
er aus dem Bezeichner des Eintrags gebildet (`mi_beenden` →
`mi_beenden_click`). Ein Durchgang durch den Dialog ist ein Schritt
für „Rückgängig“.

Gibt es die Methode zu einem Eintrag nicht, etwa nach einem
Tippfehler, bricht das Programm beim Start mit einer Meldung ab, die
den Eintrag und den gesuchten Namen nennt.

Menüs gehen bis zur zweiten Ebene („Datei → Zuletzt geöffnet“).

Im Code geht es auch:

```python
self.mm_haupt.entries = [
    {"caption": "&Datei", "children": [
        {"caption": "&Neu", "shortcut": "Strg+N", "on_click": "mi_neu_click"},
        {"separator": True},
        {"caption": "B&eenden", "on_click": "mi_ende_click"},
    ]},
]
```

Ein einzelner Eintrag lässt sich über seinen Bezeichner finden und zur
Laufzeit ändern; danach `aktualisieren()` aufrufen:

```python
self.mm_haupt.eintrag("mi_speichern")["enabled"] = False
self.mm_haupt.aktualisieren()
```

## PopupMenu

Ein Klappmenü auf die rechte Maustaste. Auf dem Formular liegt nur ein
kleines Symbol.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| width | int | 32 | Layout | Breite des Symbols |
| height | int | 32 | Layout | Höhe des Symbols |
| entries | Liste | [] | Allgemein | Die Einträge des Menüs, aufgebaut wie bei `MainMenu` |

Zugeordnet wird es über die Eigenschaft `popup_menu` einer sichtbaren
Komponente. Im Objektinspektor steht dafür in der Zeile `popup_menu`
eine Auswahl mit allen Klappmenüs des Formulars; im Code geht es so:

```python
self.sg_tabelle.popup_menu = self.pm_tabelle
```

`None` im Code oder „(kein)“ im Objektinspektor nimmt die Zuordnung
wieder weg. Dasselbe Klappmenü darf an mehreren Komponenten hängen.

## GroupBox

Ein Rahmen mit Überschrift, der andere Komponenten aufnimmt.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| width | int | 185 | Layout | Breite in Pixeln |
| height | int | 105 | Layout | Höhe in Pixeln |
| caption | str | "GroupBox1" | Darstellung | Beschriftung über dem Rahmen |

## Panel

Eine Fläche, die andere Komponenten aufnimmt.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| width | int | 185 | Layout | Breite in Pixeln |
| height | int | 105 | Layout | Höhe in Pixeln |
| caption | str | "Panel1" | Darstellung | Beschriftung auf der Fläche; leer = keine |
| color | str | "" | Darstellung | Hintergrundfarbe als #RRGGBB, leer = Farbe des Farbschemas |
| alignment | str | "center" | Darstellung | Ausrichtung des Textes: left (links), center (mittig) oder right (rechts) |

## Behälter

`GroupBox` und `Panel` nehmen andere Komponenten auf. Im Designer
landet eine Komponente, die auf einem Behälter abgelegt wird, in
diesem Behälter. `left` und `top` zählen dann ab dessen linker oberer
Ecke, und `enabled = False` oder `visible = False` am Behälter gilt für
alles, was darin liegt.

Im Code wird der Behälter statt des Formulars als Eltern angegeben:

```python
self.g_zahlung = GroupBox(self)
self.rb_bar = RadioButton(self.g_zahlung)
```

Die Namen bleiben dabei flach: ein Knopf im Panel heißt weiter
`self.b_ok`.

## RadioGroup

Eine Gruppe von Optionsfeldern mit Rahmen. Die Optionsfelder entstehen
aus `items`.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| width | int | 185 | Layout | Breite in Pixeln |
| height | int | 105 | Layout | Höhe in Pixeln |
| caption | str | "RadioGroup1" | Darstellung | Beschriftung über dem Rahmen |
| items | `Strings` | leer | Daten | Die Optionen, siehe „Schrift und Sammlungen“ |
| item_index | int | -1 | Verhalten | Index der gewählten Option, -1 = keine Auswahl |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | Wechsel der Auswahl (Klick oder Code) |

`item_index` ist die eine Stelle, an der die Auswahl steht. Ein Index
außerhalb von `0..len(items)-1` fällt auf `-1` zurück, beim Zuweisen
wie auch dann, wenn `items` kürzer wird. `item_index = -1` hebt die
Auswahl auf.

## Chart

Ein Diagramm.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| width | int | 320 | Layout | Breite in Pixeln |
| height | int | 240 | Layout | Höhe in Pixeln |
| kind | str | "bar" | Darstellung | Diagrammart: bar, line, pie, scatter, histogram, boxplot |
| title | str | "" | Darstellung | Überschrift über dem Diagramm |
| x_label | str | "" | Darstellung | Beschriftung der x-Achse |
| y_label | str | "" | Darstellung | Beschriftung der y-Achse |
| legend | bool | False | Darstellung | Legende mit den Serientiteln anzeigen |
| grid | bool | False | Darstellung | Gitternetzlinien anzeigen |

Methoden zum Zeichnen: `add_bar_series(kategorien, werte, *, title="")`,
`add_line_series(x, y, *, title="")`,
`add_pie_series(labels, werte, *, title="")`,
`add_scatter_series(x, y, *, title="")`,
`add_histogram_series(werte, *, bins=10, title="")`,
`add_boxplot_series(werte, *, title="")`, `clear()`. Alle nehmen Listen
und pandas-Serien entgegen.

Methoden zum Laden von Daten:

| Methode | Woher |
|---|---|
| `load_csv(pfad, x, y, *, sep=None, decimal=None)` | CSV-Datei; `x`/`y` als Spaltenname oder Spaltennummer. Trennzeichen und Dezimalkomma werden ohne Angabe selbst erkannt |
| `load_query(verbindung, sql, *, x=None, y=None)` | Datenbankabfrage über eine `SQLite3Connection` |
| `load_grid(stringgrid, *, x=None, y=None)` | `StringGrid` desselben Formulars |

Alle drei enden in einem `pandas.DataFrame`, abrufbar über
`Chart.dataframe`. Ohne `x`/`y` nehmen `load_query` und `load_grid` die
ersten beiden Spalten.

Regression: `add_regression(x=None, y=None, art="linear", *, grad=2)`
legt die Gerade bzw. Kurve über die vorhandenen Punkte, schreibt die
Formel in die Legende und gibt das Ergebnis zurück (siehe
`pcl.analyse` unten). Ohne `x` und `y` rechnet sie mit den Punkten
der zuletzt gezeichneten Punkte- oder Linienserie, sonst mit den
zuletzt geladenen Daten.

Die Zahlen an den Achsen stehen mit Dezimalkomma, wie die Formel in
der Legende.

Ein Kreisdiagramm bekommt keine Legende, auch wenn `legend` gesetzt
ist: seine Stücke tragen ihre Beschriftung schon selbst. Ein zu langer
`title` wird umgebrochen.

Solange keine Daten da sind, zeichnet das Diagramm eine kleine
Beispielreihe in der gewählten Art; so steht schon im Designer ein
erkennbares Diagramm. Der erste `add_*_series`-Aufruf wirft die
Vorschau weg. `kind` wählt man im Objektinspektor aus einer Liste; ein
unbekannter Wert wird mit einer Fehlermeldung abgelehnt, die die
möglichen Arten nennt.

## MaskEdit

Ein Textfeld mit Eingabemaske. Was nicht in die Maske passt, nimmt das
Feld gar nicht erst an.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| width | int | 120 | Layout | Breite in Pixeln |
| text | str | "" | Darstellung | Inhalt des Feldes |
| mask | str | "" | Verhalten | Eingabemaske, z. B. 00.00.0000 für ein Datum (leer = keine) |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | jede Änderung des Textes |

In der Maske steht `0` für eine Ziffer (Pflicht), `9` für eine Ziffer
(freiwillig), `A` für einen Buchstaben (Pflicht) und `N` für einen
Buchstaben oder eine Ziffer. Alles andere steht fest da.

```python
self.me_plz.mask = "00000"            # 12345
self.me_datum.mask = "00.00.0000"     # 20.09.2026
```

## DateEdit

Ein Datumsfeld mit Aufklapp-Kalender.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| width | int | 130 | Layout | Breite in Pixeln |
| date | date | 01.01.2026 | Verhalten | Das eingestellte Datum |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | ein anderes Datum wird eingestellt |

`date` ist ein echtes `datetime.date`, keine Zeichenkette; damit lässt
sich rechnen:

```python
von = self.de_start.date
bis = self.de_ende.date
self.l_dauer.caption = f"{(bis - von).days} Tage"
```

Angezeigt wird deutsch (`23.11.2026`), im Quelltext steht
`date(2026, 11, 23)`.

## TimeEdit

Ein Uhrzeitfeld.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| width | int | 90 | Layout | Breite in Pixeln |
| time | time | 08:00 | Verhalten | Die eingestellte Uhrzeit |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | eine andere Uhrzeit wird eingestellt |

`time` ist ein `datetime.time`, angezeigt als `hh:mm`.

## Calendar

Ein Monatskalender zum Anklicken, mit deutschen Monats- und
Tagesnamen.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| width | int | 320 | Layout | Breite in Pixeln |
| height | int | 220 | Layout | Höhe in Pixeln |
| date | date | 01.01.2026 | Verhalten | Der gewählte Tag |

| Ereignis | Signatur | Auslöser |
|---|---|---|
| on_change | (self, sender) | ein anderer Tag wird gewählt |

## HtmlViewer

Zeigt HTML an, ohne den Browser zu öffnen.

| Eigenschaft | Typ | Standardwert | Kategorie | Hilfetext |
|---|---|---|---|---|
| width | int | 320 | Layout | Breite in Pixeln |
| height | int | 220 | Layout | Höhe in Pixeln |
| html | str | "" | Darstellung | Der angezeigte HTML-Text |

| Methode | Bedeutung |
|---|---|
| `load_from_file(pfad)` | lädt eine `.html`-Datei |
| `clear()` | leert die Anzeige |

```python
self.hv_seite.html = "<h2>Bericht</h2><p>Ein <b>fetter</b> Text</p>"
self.hv_seite.load_from_file("auswertung.html")
```

Überschriften, Absätze, Listen, Tabellen, Fett- und Kursivschrift,
Bilder und Links werden angezeigt. JavaScript und alles, was eine
Seite erst im Browser zusammenbaut, nicht.

## Die Maus

Jede sichtbare Komponente hat diese fünf Ereignisse – der Knopf
genauso wie das Bild, das Formular oder die Zeichenfläche. Sie
kommen auch dort an, wo die Komponente innen aus mehreren Teilen
besteht: auf den Einträgen einer `ListBox`, im Eingabefeld eines
`SpinEdit`, auf den Tagen eines `Calendar` oder den Optionen einer
`RadioGroup`.

| Ereignis | Wann | Bekommt |
|---|---|---|
| on_click | linke Maustaste gedrückt und losgelassen, beides auf der Komponente | `sender` |
| on_double_click | Doppelklick | `sender` |
| on_mouse_down | Maustaste gedrückt | `sender`, `x`, `y` |
| on_mouse_move | Maus bewegt | `sender`, `x`, `y` |
| on_mouse_up | Maustaste losgelassen | `sender`, `x`, `y` |
| on_mouse_enter | Maus kommt auf die Komponente | `sender` |
| on_mouse_leave | Maus verlässt die Komponente | `sender` |

`x` und `y` zählen ab der linken oberen Ecke der Komponente, nicht ab
der des Fensters. Wer nur wissen will, dass geklickt wurde, nimmt
`on_click`; wer wissen will, wo, nimmt `on_mouse_down`.

Die rechte Maustaste löst kein `on_click` aus, sie gehört dem
Klappmenü (`popup_menu`). `on_mouse_down` und `on_mouse_up` kommen
bei jeder Taste. Wer auf der Komponente drückt und die Maus
daneben loslässt, hat nicht geklickt.

`on_mouse_enter` und `on_mouse_leave` kommen genau einmal, wenn die
Maus auf die Komponente kommt und wenn sie sie wieder verlässt. Damit
lässt sich etwas hervorheben, solange die Maus darüber steht:

```python
def l_hilfe_mouse_enter(self, sender):
    self.l_hilfe.font.bold = True

def l_hilfe_mouse_leave(self, sender):
    self.l_hilfe.font.bold = False
```

Damit lässt sich malen:

```python
def pb_bild_mouse_down(self, sender, x, y):
    self.malt = True
    self.pb_bild.canvas.pen.color = "#c42b1c"
    self.pb_bild.canvas.move_to(x, y)

def pb_bild_mouse_move(self, sender, x, y):
    if self.malt:
        self.pb_bild.canvas.line_to(x, y)

def pb_bild_mouse_up(self, sender, x, y):
    self.malt = False
```

Ein Doppelklick auf eine Zeile im Reiter „Ereignisse“ des
Objektinspektors legt die Methode an; die Koordinaten stehen dann
schon in der Parameterliste.

## Die Tastatur

Jede sichtbare Komponente und das Formular haben `on_key_press`. Die
Methode bekommt neben `sender` den Namen der Taste:

| Taste | `taste` |
|---|---|
| Buchstaben | `"A"` bis `"Z"`, immer groß |
| Ziffern | `"0"` bis `"9"`, auch vom Ziffernblock |
| Eingabetaste | `"Eingabe"` |
| Leertaste | `"Leertaste"` |
| Pfeiltasten | `"Links"`, `"Rechts"`, `"Oben"`, `"Unten"` |
| Esc, Tab, Rücktaste, Entf | `"Esc"`, `"Tab"`, `"Rücktaste"`, `"Entf"` |
| Pos1, Ende, Bild auf, Bild ab, Einfg | `"Pos1"`, `"Ende"`, `"Bild auf"`, `"Bild ab"`, `"Einfg"` |
| Funktionstasten | `"F1"` bis `"F12"` |
| jedes andere Zeichen | das Zeichen selbst, z. B. `"+"` oder `"Ä"` |

Umschalt, Strg und Alt allein lösen nichts aus.

Wer eine Taste bekommt:

- Das Formular bekommt jeden Tastendruck in seinem Fenster, auch wenn
  gerade ein Eingabefeld oder ein Knopf den Fokus hat.
- Eine Komponente bekommt nur die Tasten, die sie selbst mit dem Fokus
  bekommt.
- Hat eine Komponente den Fokus, melden sich beide: zuerst das
  Formular, dann die Komponente.

Ein Spiel mit Pfeiltasten gehört deshalb an das Formular:

```python
def form_key_press(self, sender, taste):
    if taste == "Links":
        self.s_figur.left -= 10
    elif taste == "Rechts":
        self.s_figur.left += 10
    elif taste == "Oben":
        self.s_figur.top -= 10
    elif taste == "Unten":
        self.s_figur.top += 10
```

„Eingabe bestätigt“ gehört an das Eingabefeld:

```python
def e_name_key_press(self, sender, taste):
    if taste == "Eingabe":
        self.l_gruss.caption = "Hallo " + self.e_name.text
```

Wie bei der Maus legt ein Doppelklick auf die Zeile `on_key_press` im
Reiter „Ereignisse“ die Methode mit dem Parameter `taste` an.

## Ein- und ausblenden

`visible` hat jede sichtbare Komponente. `False` blendet sie im
laufenden Programm aus, `True` wieder ein:

```python
self.l_hinweis.visible = False
```

Im Designer bleibt eine ausgeblendete Komponente zu sehen, damit sie
sich weiter anklicken und bearbeiten lässt. Liegen in einem `Panel`
oder einer `GroupBox` weitere Komponenten, verschwinden sie mit ihrem
Behälter.

## Schrift und Sammlungen

### font

Jede Komponente hat eine Schrift mit Name, Größe und Stil:

| Untereigenschaft | Typ | Standardwert | Hilfetext |
|---|---|---|---|
| font.name | str | "" | Schriftart; leer = Schriftart des Formulars |
| font.size | int | 0 | Schriftgröße in Punkt; 0 = Größe des Formulars |
| font.bold | bool | False | Fettschrift |
| font.italic | bool | False | Kursivschrift |
| font.color | str | "" | Schriftfarbe als #RRGGBB; leer = Farbe des Farbschemas |

Im Code: `self.l_titel.font.size = 14`, bei einer falschen Antwort
etwa `self.l_antwort.font.color = "#e53935"` für rote Schrift. Im
Objektinspektor heißen sie `font_name`, `font_size`, `font_bold`,
`font_italic` und `font_color`; `font_name` hat dort eine
Schriftauswahl, `font_color` einen Farbwähler. Eine Farbe, die keine
ist („rot“), wird mit einer Fehlermeldung abgelehnt.

### items / lines

`ListBox.items`, `ComboBox.items`, `RadioGroup.items` und
`Memo.lines` sind Sammlungen von Textzeilen. Sie kennen `add(text)`,
`clear()`, `load_from_file(pfad)`, `save_to_file(pfad)`, `len(…)`,
Zugriff über den Index (`self.lb_sorten.items[0]`), `del` und
Schleifen (`for sorte in self.lb_sorten.items:`). Dazu kommen die
übrigen Listenbefehle:

| Befehl | Bedeutung |
|---|---|
| `append(text)` | dasselbe wie `add(text)` |
| `extend(texte)` | hängt mehrere Zeilen ans Ende, ebenso `items += ["a", "b"]` |
| `insert(index, text)` | fügt eine Zeile an dieser Stelle ein |
| `remove(text)` | entfernt die erste Zeile mit diesem Text |
| `index(text)` | Nummer der ersten Zeile mit diesem Text, ab 0 |
| `count(text)` | wie oft der Text als Zeile vorkommt |
| `pop()`, `pop(index)` | entfernt die letzte bzw. diese Zeile und gibt sie zurück |
| `sort()`, `sort(reverse=True)` | ordnet die Zeilen, auch mit `key=` |
| `reverse()` | kehrt die Reihenfolge um |

Jede Zeile ist ein Text; eine Zahl wird abgelehnt, auch bei
`items[0] = 5` und `insert(0, 5)`. Der ganze Inhalt lässt
sich auf einmal zuweisen:

```python
self.lb_sorten.items = ["Hawaii", "Napoli"]
```

Im Objektinspektor öffnet ein Doppelklick auf die Zeile einen
Zeileneditor.

`load_from_file` liest UTF-8, auch mit der Markierung am Anfang, die
Excel beim Speichern als „CSV UTF-8“ voranstellt. Eine Datei, die
kein UTF-8 ist, wird in der Windows-Kodierung (cp1252) gelesen, in
der ältere Programme Umlaute speichern. Mit
`load_from_file(pfad, encoding="…")` gilt genau die angegebene
Kodierung.

`add` hängt nur die neue Zeile an. Tausende Zeilen in einer Schleife
sind deshalb schnell geschrieben, etwa alle Primzahlen bis 10 000 in
ein `Memo`.

## Dialogfunktionen

Keine Komponenten, sondern Funktionen aus `pcl`, die ein kleines
Fenster zeigen und warten, bis es geschlossen wird.

| Funktion | Bedeutung |
|---|---|
| `show_message(text)` | zeigt eine Meldung mit einem OK-Knopf; eine Zahl erscheint mit Dezimalkomma (`show_message(2.5)` zeigt „2,5“) |
| `input_box(titel, frage, standard="")` | fragt einen Text ab; bei Abbruch kommt `standard` zurück |
| `open_dialog(titel="Datei öffnen", filter=…)` | lässt eine vorhandene Datei auswählen und liefert ihren Pfad; bei Abbruch einen leeren Text. Ohne `filter` werden Bilddateien angeboten |
| `ask_yes_no(frage, titel="Natter")` | stellt eine Frage mit den Knöpfen „Ja“ und „Nein“; `True` bei „Ja“, sonst `False` |
| `save_dialog(titel="Datei speichern", filter=…, dateiname="")` | lässt einen Dateinamen zum Speichern wählen und liefert den Pfad; bei Abbruch einen leeren Text. Ohne `filter` werden Textdateien angeboten, die Endung `.txt` wird angehängt, wenn sie fehlt |
| `color_dialog(farbe="#ffffff", titel="Farbe auswählen")` | lässt eine Farbe wählen und liefert sie als `#rrggbb`; bei Abbruch einen leeren Text |
| `input_number(titel, frage, standard=0, minimum=…, maximum=…, stellen=0)` | fragt eine Zahl zwischen `minimum` und `maximum` ab; mit `stellen=0` eine ganze Zahl, sonst eine Kommazahl mit so vielen Nachkommastellen. Getippt wird mit Dezimalkomma. Bei Abbruch kommt `standard` zurück |
| `open_url(pfad_oder_adresse)` | öffnet eine Internetadresse oder eine Datei im Standardbrowser; ein relativer Pfad gilt ab dem Arbeitsordner. Eine Adresse ohne `https://` wie `www.schule.de` wird als Webadresse erkannt, solange es keine Datei dieses Namens gibt. Ein so geöffneter Browser gehört nicht zum Programm und bleibt offen, wenn das Programm mit „Stopp“ endet |

```python
from pcl import (
    ask_yes_no,
    color_dialog,
    input_box,
    input_number,
    open_dialog,
    open_url,
    save_dialog,
    show_message,
)

name = input_box("Anmeldung", "Name:")
show_message(f"Hallo {name}!")

pfad = open_dialog("Bild öffnen")
if pfad:
    self.i_bild.picture.load_from_file(pfad)

open_url("https://www.example.org")
open_url("auswertung.html")

if ask_yes_no("Alle Einträge löschen?"):
    self.lb_liste.items.clear()

ziel = save_dialog(dateiname="notizen.txt")
if ziel:
    self.m_text.lines.save_to_file(ziel)

farbe = color_dialog()
if farbe:
    self.p_flaeche.color = farbe

alter = input_number("Anmeldung", "Alter:", 16, 6, 99)
```

## Zahlen mit Dezimalkomma

Was in einem Eingabefeld steht, ist Text, und Python rechnet nur mit
dem Dezimalpunkt. Zwei Funktionen aus `pcl` übernehmen das Umwandeln:

| Funktion | Bedeutung |
|---|---|
| `zahl(text)` | liest eine Zahl aus einem Text, mit Komma oder Punkt („2,5“ ergibt 2.5, „1.234,5“ ergibt 1234.5). Punkte zwischen Dreiergruppen sind Tausendertrennung: „1.000“ ergibt 1000, „1.234.567“ ergibt 1234567. Sonst ist der Punkt ein Dezimalpunkt: „2.5“ ergibt 2.5, „0.500“ ergibt 0.5. Ist der Text keine Zahl, kommt ein `ValueError` mit deutscher Meldung |
| `text(zahl, stellen=None)` | schreibt eine Zahl mit Komma; ohne `stellen` so kurz wie möglich („3“, „0,3“), mit `stellen` genau so viele Nachkommastellen („2,50“). Gerundet wird wie in der Schule, bei einer 5 aufwärts: `text(2.5, 0)` ergibt „3“, `text(0.125, 2)` „0,13“. Ohne `stellen` erscheint kein „e“: `text(0.00001)` ergibt „0,00001“; erst ab 10^21 und unter 10^-10 steht eine Zehnerpotenz da („2,5 · 10^21“) |

```python
from pcl import text, zahl

try:
    preis = zahl(self.e_preis.text)
except ValueError:
    self.l_summe.caption = "Bitte einen Preis eintragen."
    return
self.l_summe.caption = f"Summe: {text(preis * 3, 2)} Euro"
```

## Datenbank

Natter kennt eine Datenbank: SQLite, eine Datei neben dem Programm.
Ohne Server, ohne Netz und ohne Zugangsdaten.

### SQLite3Connection

| Aufruf | Bedeutung |
|---|---|
| `SQLite3Connection(datei)` | öffnet die Datei sofort; gibt es sie nicht, legt SQLite sie an. `":memory:"` für eine Datenbank, die nur im Arbeitsspeicher lebt |
| `query(sql, **parameter)` | SELECT; liefert alle Zeilen als Liste von `dict`s. Eine schreibende Anweisung schreibt `query` wie `execute` fest |
| `query_one(sql, **parameter)` | wie `query`, aber nur die erste Zeile – oder `None` |
| `execute(sql, **parameter)` | INSERT/UPDATE/DELETE/CREATE; schreibt sofort fest und liefert die Anzahl betroffener Zeilen. Scheitert die Anweisung, wird sie zurückgerollt, und die Datei bleibt für andere Programme beschreibbar. Innerhalb einer Transaktion schreibt es nichts fest |
| `transaction()` | für einen `with`-Block: alle Anweisungen darin sind eine Transaktion. Endet der Block ohne Fehler, wird alles festgeschrieben, endet er mit irgendeiner Ausnahme, wird alles zurückgenommen |
| `commit()` / `rollback()` | schließen eine mit `execute("BEGIN")` begonnene Transaktion: `commit()` schreibt alles seitdem fest, `rollback()` nimmt alles seitdem zurück |
| `database_name` | der Dateipfad |
| `connected` | `True` öffnet, `False` schließt. Ist beim Schließen oder am Programmende noch eine Transaktion offen, wird sie zurückgenommen, und ein Hinweis sagt das |

```python
self.db = SQLite3Connection("konten.sqlite")

self.db.execute("""
    CREATE TABLE IF NOT EXISTS konto (
        nummer  INTEGER PRIMARY KEY AUTOINCREMENT,
        inhaber TEXT    NOT NULL,
        stand   REAL    NOT NULL DEFAULT 0
    )
""")

self.db.execute("INSERT INTO konto (inhaber) VALUES (:wer)", wer="Anna")

for zeile in self.db.query("SELECT inhaber, stand FROM konto"):
    print(zeile["inhaber"], zeile["stand"])
```

Werte gehören nie in den SQL-Text. Sie kommen als `:name`-Platzhalter
hinein und als Schlüsselwortargument hinterher. Wer den Wert in den
Text klebt, öffnet die bekannteste Sicherheitslücke überhaupt: eine
Eingabe wie `0 OR 1=1; DROP TABLE konto` löscht dann die Tabelle.

Gehören mehrere Anweisungen zusammen, etwa Abbuchung und Gutschrift
bei einer Überweisung, fasst `with self.db.transaction():` sie zu
einer Transaktion zusammen. Erst am Ende des Blocks wird
festgeschrieben. Scheitert im Block irgendetwas, eine SQL-Anweisung
ebenso wie ein gewöhnlicher Python-Fehler, nimmt er alle Anweisungen
darin zurück:

```python
betrag = int(self.e_betrag.text)
with self.db.transaction():
    self.db.execute(
        "UPDATE konto SET stand = stand - :b WHERE nummer = 1", b=betrag
    )
    self.db.execute(
        "UPDATE konto SET stand = stand + :b WHERE nummer = 2", b=betrag
    )
```

Dasselbe geht auch von Hand mit `execute("BEGIN")`, `commit()` und
`rollback()`. Dann muss aber jeder Weg aus der Methode, auch ein
`ValueError`, bei `commit()` oder `rollback()` ankommen; sonst bleibt
die Transaktion offen, jedes weitere `BEGIN` scheitert, und die Datei
bleibt für andere Programme gesperrt.

Jeder Fehler der Datenbank kommt als `NatterDatenbankError` an, auch
einer, den SQLite erst beim Lesen einer späteren Zeile bemerkt (etwa
ungültiges JSON), und einer beim Schreiben in eine schreibgeschützte
Datei.

Weil SQLite eine fehlende Datei beim Verbinden anlegt, landet ein
Tippfehler im Dateinamen (`"konton.sqlite"` statt `"konten.sqlite"`)
in einer neuen, leeren Datenbank. Scheitert eine Abfrage an einer
Tabelle, die es nicht gibt, nennt die Meldung deshalb die Datei. War
die Datei beim Verbinden neu oder enthält sie keine einzige Tabelle,
steht dazu der Hinweis, dass wahrscheinlich eine andere Datei gemeint
war. Die leere Datei bleibt im Ordner liegen und lässt sich löschen.

### SQLQuery und DataSource

Eine Abfrage mit Datensatzzeiger, für `DBNavigator` und die anderen
Data Controls:

```python
self.abfrage = SQLQuery(self.db)
self.abfrage.sql = "SELECT * FROM konto"
self.abfrage.open()
self.ds_konten = DataSource(self.abfrage)
self.g_konten.data_source = self.ds_konten
```

| Aufruf | Bedeutung |
|---|---|
| `sql` | die SQL-Anweisung mit `:name`-Platzhaltern |
| `params` | die Werte für die Platzhalter, z. B. `self.abfrage.params["wer"] = "Anna"` |
| `open()` / `close()` | führt ein SELECT aus bzw. gibt das Ergebnis frei. Steht in `sql` doch eine schreibende Anweisung, schreibt `open()` sie fest wie `exec_sql()` |
| `exec_sql()` | führt eine schreibende Anweisung aus und schreibt sie fest, außer nach einem `execute("BEGIN")` |
| `first()`, `next()`, `prior()`, `last()` | bewegen den Datensatzzeiger |
| `eof` | `True`, wenn der Zeiger hinter dem letzten Datensatz steht |
| `record_count`, `record_index` | Anzahl der Datensätze, Stelle des Zeigers |
| `field_by_name(name)` | ein Feld des aktuellen Datensatzes, siehe unten |
| `set_field(name, wert)` | ändert ein Feld des aktuellen Datensatzes |
| `to_dataframe()` | führt `sql` erneut aus und liefert das Ergebnis als pandas-`DataFrame`; schreibt wie `open()` fest. Gepufferte Zeilen und Datensatzzeiger bleiben unverändert, gebundene Data Controls arbeiten danach weiter |

Ein Feld aus `field_by_name` gibt seinen Wert auf vier Arten her:

| Eigenschaft | Liefert |
|---|---|
| `value` | den Wert, wie er in der Datenbank steht |
| `as_string` | als Text, wie ihn die Data Controls zeigen; ein leeres Feld als `""`, eine Kommazahl mit Dezimalkomma (`"1,5"`) |
| `as_integer` | als ganze Zahl; ein leeres Feld als `0` |
| `as_float` | als Kommazahl; ein leeres Feld als `0.0`. Ein Text mit Dezimalkomma wie `"2,5"` wird verstanden |

Lässt sich ein Feld nicht als Zahl lesen, etwa ein Name, bricht
`as_integer` bzw. `as_float` mit einer Meldung ab, die den Wert nennt.

```python
while not self.abfrage.eof:
    summe += self.abfrage.field_by_name("stand").as_float
    self.abfrage.next()
```

### Die Data Controls

`DBGrid`, `DBText`, `DBEdit`, `DBComboBox` und `DBNavigator` zeigen
Daten an, ohne dass jede Zelle einzeln gefüllt werden muss. Am
kürzesten:

```python
self.g_konten.show_rows(self.db.query("SELECT * FROM konto"))
```

Alle fünf stehen in der Palette im Reiter „Datenbank“. Die
Datenquelle wird im Code zugewiesen, etwa in `form_create`:

```python
self.abfrage = SQLQuery(self.db)
self.abfrage.sql = "SELECT * FROM konto"
self.abfrage.open()
self.dbg_konten.data_source = DataSource(self.abfrage)
```

Ohne zugeordnete Datenquelle zeigen alle fünf eine leere Anzeige.

Ein leeres Feld (`NULL`) erscheint leer, eine Kommazahl mit
Dezimalkomma und Binärdaten als Hinweis wie „(Binärdaten, 4 Bytes)“.
Steht in einem Feld eine Zahl, liest `DBEdit` die Eingabe als Zahl,
mit Komma wie mit Punkt.

## DBGrid

Tabelle mit den Zeilen einer Abfrage. Eigene Eigenschaften hat sie
keine; was sie zeigt, bestimmt `data_source`. `show_rows(zeilen)`
zeigt eine Liste von Wörterbüchern ohne Datenquelle.

Ein Klick auf eine Zeile macht sie zum aktuellen Datensatz; `DBText`
und `DBEdit` an derselben Datenquelle zeigen danach deren Werte. Die
Zellen selbst lassen sich nicht bearbeiten, geändert wird über ein
`DBEdit`.

`aktualisieren()` an der Datenquelle füllt die Tabelle nur dann neu,
wenn sich die Daten der Abfrage geändert haben (`open()`,
`set_field()`, `close()`). Wandert nur der Datensatzzeiger, setzt sie
bloß die Auswahl; so bleibt auch eine Tabelle mit 20.000 Zeilen beim
Blättern flüssig. Dasselbe gilt für die Einträge einer `DBComboBox`.

Die Tabelle behält die Zeilen der Abfrage, wie sie sind, und macht nur
aus den sichtbaren Zellen Text. Eine Abfrage mit 100.000 Zeilen ist
deshalb sofort zu sehen und kostet kaum zusätzlichen Speicher.

## DBText

Beschriftung, die ein Feld des aktuellen Datensatzes zeigt.

| Eigenschaft | Bedeutung |
|---|---|
| field | Name des angezeigten Feldes |

## DBEdit

Eingabefeld für ein Feld des aktuellen Datensatzes.

| Eigenschaft | Bedeutung |
|---|---|
| field | Name des gebundenen Feldes |

## DBComboBox

Auswahlliste mit den Werten einer Spalte.

| Eigenschaft | Bedeutung |
|---|---|
| list_field | Anzuzeigende Spalte der Datenquelle in `list_source` |

## DBNavigator

Knöpfe zum Blättern durch die Datensätze und zum Bearbeiten.

| Ereignis | Bedeutung |
|---|---|
| on_insert | Klick auf „Einfügen“ |
| on_delete | Klick auf „Löschen“ |
| on_save | Klick auf „Speichern“ |
| on_cancel | Klick auf „Abbrechen“ |

## Sound

Spielt einen Klang ab. Keine Komponente für das Formular, sondern im
Code erzeugt, wie eine Datenbankverbindung.

| Aufruf | Bedeutung |
|---|---|
| `Sound(datei)` / `load_from_file(datei)` | lädt eine `.wav` |
| `play()` / `stop()` | abspielen, abbrechen |
| `volume` | Lautstärke zwischen 0,0 und 1,0 |
| `file_name` | die geladene Datei, oder `None` |
| `Sound.beep()` | ein kurzer Ton ohne Datei, auch `Sound.beep(440, 500)` |

```python
self.klang = Sound()
self.klang.load_from_file("treffer.wav")
self.klang.play()
```

Nur `.wav`: eine MP3 bräuchte Codecs, die auf einem verwalteten
Schulrechner nicht sicher vorhanden sind. Eine MP3 lässt sich mit
einem Audioprogramm umwandeln; die Meldung sagt das auch.

## Auswertung: `pcl.analyse`

Eine Funktion für die Datenauswertung.

```python
ergebnis = pcl.analyse.regression(groessen, schuhgroessen, art="linear")
self.l_steigung.caption = f"Steigung: {ergebnis.steigung:.2f}"
```

| Funktion | Signatur |
|---|---|
| regression | `(x, y, art="linear", *, grad=2) -> Regressionsergebnis` |

`art` ist `linear`, `polynomial` (mit `grad=2` oder `3`),
`exponentiell` oder `logarithmisch`.

| Feld | Bedeutung |
|---|---|
| steigung | linear: `m` aus `y = m·x + b`; polynomial: Koeffizient des Glieds `·x`; exponentiell: Wachstumsrate im Exponenten; logarithmisch: Faktor vor `ln(x)` |
| achsenabschnitt | Wert bei `x = 0` |
| bestimmtheitsmass | R², immer auf der Originalskala gerechnet |
| formel | lesbarer Text, z. B. `y = 2,31·x + 4,07` |
| koeffizienten | alle Koeffizienten, höchste Potenz zuerst |
| vorhersage(x) | y-Wert zu einem x oder zu einer Reihe von x-Werten |

Koeffizienten unter dem 1e-10-fachen des größten werden auf 0 gesetzt,
damit in der Legende `y = 1,00·x²` steht und kein Rechenrauschen.

## Konsolenprogramme: `pcl.crt`

Für Programme ohne Fenster, die mit `print()` und `input()` arbeiten,
gibt es Farben, Cursorsprünge und Tastenabfragen im Konsolenfenster.
Das Modul wird eigens eingebunden:

```python
from pcl import crt

crt.clr_scr()
crt.goto_xy(10, 5)
crt.text_color("yellow")
crt.text_background("blue")
print("Hallo")
crt.text_color("light_gray")
crt.text_background("black")
```

| Funktion | Bedeutung |
|---|---|
| `clr_scr()` | löscht das Fenster, der Cursor steht danach links oben |
| `goto_xy(x, y)` | setzt den Cursor auf Spalte `x`, Zeile `y`; gezählt wird ab 1 |
| `text_color(farbe)` | Farbe der Schrift für alles, was danach ausgegeben wird |
| `text_background(farbe)` | Farbe des Hintergrunds hinter der Schrift |
| `read_key()` | wartet auf eine Taste und liefert sie, ohne Eingabetaste und ohne sie anzuzeigen. Ein Zeichen kommt als das Zeichen selbst, Sondertasten mit denselben Namen wie bei `on_key_press`: „Oben“, „Unten“, „Links“, „Rechts“, „Pos1“, „Ende“, „Bild auf“, „Bild ab“, „Einfg“, „Entf“, „F1“ bis „F12“; eine andere Sondertaste ergibt einen leeren Text |
| `key_pressed()` | `True`, wenn eine Taste gedrückt wurde, die noch nicht gelesen ist; wartet nicht |
| `delay(millisekunden)` | wartet so viele Millisekunden |
| `beep(frequenz=800, dauer_ms=200)` | ein Piepton |

Die Farben heißen `black`, `blue`, `green`, `cyan`, `red`, `magenta`,
`brown`, `light_gray`, `dark_gray`, `light_blue`, `light_green`,
`light_cyan`, `light_red`, `light_magenta`, `yellow` und `white`;
statt des Namens geht auch die Nummer 0 bis 15 in dieser Reihenfolge.
Ein unbekannter Name oder eine Zahl außerhalb von 0 bis 15 bricht mit
einer Meldung ab.

Farben und Cursorsprünge wirken im Konsolenfenster, das Natter beim
Start eines Konsolenprogramms öffnet, und in Windows Terminal. Im
Ausgabefenster der IDE und in einer umgeleiteten Ausgabe stehen sie
als Steuerzeichen im Text.
