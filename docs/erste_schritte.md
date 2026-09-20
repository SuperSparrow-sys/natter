# Erste Schritte mit Natter

Diese Seite führt in zehn Minuten vom leeren Bildschirm zum laufenden
Programm.

## 1. Ein Projekt anlegen

**Projekt → Neues Projekt …**, oder auf dem Startbild „Neues Projekt …".

Im Projekt-Explorer links stehen genau zwei Dinge:

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

## 2. Das Formular bauen

Doppelklick auf **u_main** unter „Formulare" öffnet den Designer.

Links oben steht die **Komponentenpalette**. Eine Kachel anklicken und
dann ins Formular klicken – dort entsteht die Komponente. (Ein
Doppelklick auf die Kachel legt sie in die Mitte.)

Rechts steht der **Objektinspektor**. Dort wird eingestellt, was die
Komponente können soll:

* `caption` – die Beschriftung
* `left`, `top`, `width`, `height` – Lage und Größe
* Reiter **Ereignisse** – was bei einem Klick passieren soll

**Doppelklick auf den Knopf** im Formular: Natter legt die Methode
dafür in `u_main.py` an und verknüpft sie. (Dasselbe über die rechte
Maustaste: „Methode für „click“ anlegen“.) Der Reiter **Ereignisse**
im Objektinspektor zeigt danach, welche Methode an welchem Ereignis
hängt; dort lässt sich auch eine **schon vorhandene** Methode
auswählen.

Das Formular selbst lässt sich an den drei Anfassern rechts, unten und
in der Ecke größer ziehen. Der Punkteraster darauf zeigt, in welchen
Schritten eine Komponente einrastet.

## 3. Code schreiben

Weiter zu **u_main.py**. Dort steht jetzt die leere Methode; hinein
kommt, was passieren soll:

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
Eigenschaft wie jede andere. Im Unterricht braucht man das selten –
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

**F5** startet mit Debugger, **Strg+F5** ohne.

Vor dem Start prüft Natter den Quelltext. Findet es etwas, steht das
unten unter **Meldungen** – ein Doppelklick führt an die Stelle.

## 5. Wenn etwas schiefgeht

Natter zeigt keinen englischen Traceback, sondern eine Meldung in drei
Teilen:

* **Wo** – Datei, Zeile, Methode
* **Was** – was passiert ist
* **Prüfe** – woran es liegen könnte

Der letzte Teil ist Absicht: Natter nennt nicht die Lösung, sondern die
Stelle, an der sie zu suchen ist. Das Finden ist die eigentliche
Aufgabe.

Zum Suchen dient ein **Haltepunkt**: links neben die Zeilennummer
klicken. Mit F5 hält das Programm dort an, und unter **Variablen**
steht, was gerade in den Variablen liegt. Rechtsklick auf eine Liste
oder Tabelle: **Als Tabelle anzeigen**.

## 6. Diagramme

**Datei → Neues Diagramm …** bietet sieben Arten an: Klassendiagramm,
Struktogramm, Entscheidungstabelle, Use-Case-, Aktivitäts-, Zustands-
und Sequenzdiagramm.

Aus einem Klassendiagramm und aus einem Struktogramm erzeugt Natter
**Python-Quelltext** (Menü „Quelltext"). Das ist eine Vorlage zum
Weiterschreiben, kein fertiges Programm.

## Die wichtigsten Tasten

| Taste | Wofür |
|---|---|
| F5 | Starten mit Debugger |
| Strg+F5 | Starten ohne Debugger |
| Umschalt+F5 | Stopp |
| F11 / F10 | Einzelschritt / Prozedurschritt |
| Strg+S | Speichern |
| Strg+F | Suchen |
| Strg+Z | Rückgängig |
| Strg+G | Gehe zu Zeile … (im Diagramm-Editor: Gruppieren) |
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

Wer bei 03 hängt, kommt über 02 weiter — nicht über 09.

Beim Öffnen legt Natter eine **Kopie** im eigenen Dokumente-Ordner an.
Darin lässt sich alles ausprobieren, ohne etwas kaputtzumachen.
