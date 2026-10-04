# Erste Schritte mit Natter

Diese Seite führt in zehn Minuten vom leeren Bildschirm zum laufenden
Programm.

## 1. Ein Projekt anlegen

**Projekt → Neues Projekt …**, oder auf der Startseite „Neues
Projekt …". Dort gibt es zwei Vorlagen:

* **GUI-Anwendung** – ein Fenster mit Knöpfen, Eingabefeldern und
  Beschriftungen. Darum geht es ab hier in den Abschnitten 1 bis 3.
* **Konsolenanwendung** – ein Programm im schwarzen Fenster mit
  `print()` und `input()`. Wie das geht, steht gleich unten unter
  „Ein Konsolenprogramm“.

Bei einer GUI-Anwendung stehen im Projekt-Explorer links genau zwei
Dinge:

| Eintrag | Wofür |
|---|---|
| **Formulare › u_main** | das **Formular**. Doppelklick öffnet den Designer |
| **Units › u_main.py** | der **eigene** Code: was passieren soll, wenn jemand klickt |

Im Ordner liegen noch zwei weitere Dateien, die Natter selbst schreibt
und die niemand von Hand bearbeitet – deshalb stehen sie auch nicht im
Baum: `u_main_design.py` (aus dem Formular erzeugt) und `main.py`
(startet das Programm). Wer trotzdem hineinsehen will: **Projekt → Startdatei
anzeigen**.

`u_main.pfm` hält fest, wie das Fenster aussieht; `u_main.py` hält
fest, was es tut. Deshalb zwei Dateien.

### Ein Konsolenprogramm

Bei einer Konsolenanwendung steht im Projekt-Explorer nur
**Units › u_main.py**. Ein Formular gibt es nicht, deshalb fehlen auch
Komponentenpalette und Objektinspektor. Das Programm steht in der
Funktion `main()` und läuft dort von oben nach unten:

```python
def main():
    name = input("Name: ")
    print("Hallo,", name)
```

`print(...)` schreibt eine Zeile ins schwarze Fenster, `input(...)`
wartet, bis etwas eingetippt und die Eingabetaste gedrückt ist. Jede
Zeile des Programms ist um eine Stufe eingerückt, damit sie zu `main()`
gehört. **F5** startet es (Abschnitt 4): das schwarze Fenster geht auf,
und am Ende wartet es auf die Eingabetaste, damit die Ausgabe lesbar
bleibt. Die Abschnitte 4 und 5 gelten für beide Vorlagen.

## 2. Das Formular bauen

Nach dem Anlegen ist der Designer schon offen, daneben als zweiter
Reiter `u_main.py`. Später öffnet ihn ein Doppelklick auf **u_main**
unter „Formulare".

Oben steht die **Komponentenpalette** mit den Reitern „Standard“,
„Zusätzlich“, „Eingabe“ und „Datenbank“. Die Kacheln zeigen nur ein
Symbol; ruht die Maus darauf, erscheinen Name und Zweck. Eine Kachel
anklicken und dann ins Formular klicken – dort entsteht die
Komponente. Ein Doppelklick auf die Kachel legt sie in die Mitte,
`Esc` bricht das Platzieren ab.

Rechts steht der **Objektinspektor**: oben alle Komponenten des
Formulars, darunter zwei Reiter.

* **Eigenschaften** – `name` (der Name im Code), `caption` (die
  Beschriftung), `left`, `top`, `width`, `height` (Lage und Größe)
  und alles Weitere
* **Ereignisse** – welche Methode bei einem Klick, einer Eingabe
  oder einem Takt läuft

Zum Mitmachen: einen **Button** und ein **Label** ins Formular
setzen. Beim Button im Objektinspektor `name` auf `b_start` und
`caption` auf `Start` stellen, beim Label `name` auf `l_ausgabe`.
Ohne neuen Namen hießen sie `button` und `label`.

Dann **Doppelklick auf den Knopf** im Formular. Natter legt in
`u_main.py` die Methode `b_start_click` an, verknüpft sie mit dem
Klick und setzt den Cursor hinein. Der Name der Methode besteht aus
dem Namen der Komponente und dem Ereignis. Welches Ereignis ein
Doppelklick nimmt, hängt von der Komponente ab:

| Doppelklick auf | legt an |
|---|---|
| Button, Label, Image, Panel | `…_click`: beim Anklicken |
| Edit, Memo, CheckBox, ComboBox, ListBox | `…_change`: bei jeder Änderung |
| Timer | `…_timer`: in jedem Takt |
| die freie Fläche des Formulars | `form_create`: einmal beim Start, bevor das Fenster erscheint |
| MainMenu, PopupMenu | keine Methode, sondern öffnet den Menü-Editor |

Gibt es die Methode schon, springt der Doppelklick nur hin. Dasselbe
liegt auf der rechten Maustaste: „Methode für „click“ anlegen“.
`Strg+Z` im Designer nimmt eine eben angelegte Methode wieder heraus,
solange noch nichts hineingeschrieben ist. Wird die Komponente später
umbenannt, heißt die Methode mit; Zeilen wie `self.button.caption`
im eigenen Code ändert Natter dabei nicht.

Für jedes andere Ereignis gibt es den Reiter **Ereignisse**. Ein
Doppelklick auf den Namen eines Ereignisses, etwa `on_mouse_down`,
legt dessen Methode an und springt hin. Die Auswahlliste daneben
bietet die **schon vorhandenen** Methoden an, die zu diesem Ereignis
passen; so können zwei Knöpfe dieselbe Methode benutzen. „(kein)“
löst die Verknüpfung wieder.

Das Formular selbst lässt sich an den drei Anfassern rechts, unten und
in der Ecke größer ziehen. Der Punkteraster darauf zeigt, in welchen
Schritten eine Komponente einrastet.

## 3. Code schreiben

In `u_main.py` steht jetzt die neue Methode:

```python
def b_start_click(self, sender):
    # Hier steht, was passieren soll.
    pass
```

Kommentar und `pass` werden durch das ersetzt, was passieren soll:

```python
def b_start_click(self, sender):
    self.l_ausgabe.caption = "Hallo!"
```

Jede Komponente ist über `self.` und ihren Namen erreichbar. Der Name
steht im Objektinspektor in der ersten Zeile
(`name`), und die Eigenschaften heißen dort genauso wie hier:

```python
self.l_titel.caption = "Hallo"
self.e_name.text = ""
self.b_ok.enabled = False
```

### „Wo steht eigentlich das `on_click`?“

In `u_main.py` stehen nur die **Methoden** – keine Zeile, die sie mit
dem Knopf verbindet. Das ist Absicht. Die Verbindung

```python
self.b_ok.on_click = self.b_ok_click
```

schreibt Natter beim Speichern des Formulars nach `u_main_design.py`,
zusammen mit allem anderen aus dem Designer. Diese Datei wird erzeugt
und nie von Hand geändert – deshalb taucht sie im Projekt-Explorer
nicht auf.

`on_click` lässt sich trotzdem selbst setzen: im Code ist es eine
Eigenschaft wie jede andere. Im Unterricht ist das selten nötig –
etwa, wenn zwei Knöpfe dieselbe Methode benutzen sollen. Dafür gibt es
aber auch den Reiter **Ereignisse** im Objektinspektor, und der
schreibt es ordentlich in die `.pfm` zurück.

`sender` ist die Komponente, die das Ereignis ausgelöst hat. Hängen
mehrere Knöpfe an derselben Methode, lässt sich daran erkennen, welcher
gedrückt wurde.

### Zwischen Formular und Code wechseln

**Umschalt+F12** springt vom Designer in die zugehörige `u_main.py`
und wieder zurück. (F12 selbst ist in Natter „Zur Definition
springen“.)

Zwei Hilfen im Editor: die **senkrechten Linien** zeigen die
Einrückungsebenen (bei Python ist die Einrückung die Syntax!), und die
**Rücktaste** löscht eine ganze Ebene auf einmal.

## 4. Starten

**F5** startet mit Debugger, **Strg+F5** ohne. Vorher speichert
Natter alle geänderten Dateien. Das Fenster des Programms geht auf,
und ein Klick auf „Start“ schreibt „Hallo!“ in das Label. Beendet
wird das Programm wie jedes Fenster oder mit **Umschalt+F5**.

Vor dem Start prüft Natter den Quelltext. Findet es etwas, steht das
unten unter **Meldungen** – ein Klick führt an die Stelle. Das
gilt auch, wenn in einer Unit etwas fehlt, das eine andere braucht:
`def main()` in einem Konsolenprogramm oder die Methode zu einem
Ereignis, die zum Beispiel mit Strg+Z verschwunden ist.

## 5. Wenn etwas schiefgeht

Natter zeigt keinen englischen Traceback, sondern eine Meldung in drei
Teilen:

* **Wo** – Datei, Zeile, Methode
* **Was** – was passiert ist
* **Zu prüfen** – woran es liegen könnte

Der letzte Teil ist Absicht: Natter nennt nicht die Lösung, sondern die
Stelle, an der sie zu suchen ist. Das Finden ist die eigentliche
Aufgabe.

Zum Suchen dient ein **Haltepunkt**: links neben die Zeilennummer
klicken oder **F9** drücken. Mit F5 hält das Programm dort an, und
unter **Variablen** steht, was gerade in den Variablen liegt; ruht
die Maus im Editor auf einem Namen, zeigt ein Hinweis seinen Wert.
Doppelklick oder Rechtsklick auf eine Liste oder Tabelle:
**Als Tabelle anzeigen**. **F5** setzt das Programm fort.

Ohne Haltepunkt geht es auch: **F11** oder **F10**, bevor das
Programm läuft, startet es mit dem Debugger und hält in der ersten
Zeile von `u_main.py`, bei einem Konsolenprogramm in der ersten Zeile
von `main()`. Von dort führt F11 Zeile für Zeile weiter, F10 über
Aufrufe hinweg.

## 6. Diagramme

**Datei → Neues Diagramm …** bietet sieben Arten an: Klassendiagramm,
Struktogramm, Entscheidungstabelle, Use-Case-, Aktivitäts-, Zustands-
und Sequenzdiagramm.

Ein Doppelklick auf einen Block oder eine Form beschriftet sie, bei
einer Klasse öffnet er den Dialog für Attribute und Operationen.

Aus einem Klassendiagramm und aus einem Struktogramm erzeugt Natter
**Python-Quelltext**: **Quelltext → Erzeugen …** im Fenster des
Diagramms. Das ist eine Vorlage zum Weiterschreiben, kein fertiges
Programm.

## Die wichtigsten Tasten

| Taste | Wofür |
|---|---|
| F5 | Starten mit Debugger |
| Strg+F5 | Starten ohne Debugger |
| Umschalt+F5 | Stopp |
| F9 | Haltepunkt setzen oder entfernen |
| F11 / F10 | Einzelschritt / Prozedurschritt |
| Strg+S | Speichern |
| Strg+F | Suchen |
| Strg+Z | Rückgängig |
| Strg+G | Zu Zeile springen … (im Diagramm-Editor: Gruppieren) |
| Strg+Umschalt+E | Quelltext aus dem Diagramm erzeugen |
| Umschalt+F12 | Zwischen Formular und Code wechseln |

## Und wenn es nicht weitergeht?

Dann helfen die **Beispielprojekte** unter **Datei → Beispielprojekte**. Sie sind keine
Sammlung, sondern ein Weg von vorn nach hinten — jede Stufe bringt
genau eine neue Idee dazu, und oben in der Datei steht, welche:

| | Projekt | Neu auf dieser Stufe |
|---|---|---|
| 01 | Begrüßung | Ein- und Ausgabe, Variablen |
| 02 | Zahlenraten | Verzweigung, Schleife, Zufall |
| 03 | Taschenrechner | das erste Formular |
| 04 | Cookie-Klicker | Bilder, Zeitgeber, Spielstand |
| 05 | Bildergalerie | Dateien von der Festplatte holen |
| 06 | Kontoverwaltung | eigene Klassen, eine Datenbank |
| 07 | CSV-Auswertung | echte Daten einlesen und auswerten |
| 08 | Regression | aus Daten eine Regel ableiten |
| 09 | Obst-Sortierer | der Rechner lernt selbst eine Regel |
| 10 | Notizbuch | Menü, Textdatei, zweites Fenster |
| 11 | Malen | Zeichenfläche, Maus, Farben |

Wer bei 03 hängt, kommt über 02 weiter — nicht über 09.
10 und 11 setzen nur den Taschenrechner voraus.

Beim Öffnen legt Natter eine **Kopie** im eigenen Dokumente-Ordner an.
Darin lässt sich alles ausprobieren, ohne etwas kaputtzumachen.
