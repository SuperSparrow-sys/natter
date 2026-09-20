# Erste Schritte mit Natter

Diese Seite führt in zehn Minuten vom leeren Bildschirm zum laufenden
Programm. Wenn du Lazarus kennst, wird dir fast alles bekannt vorkommen –
nur die Sprache ist Python statt Pascal.

## 1. Ein Projekt anlegen

**Projekt → Neues Projekt …**, oder auf dem Startbild „Neues Projekt …".

Im Projekt-Explorer links siehst du genau zwei Dinge:

| Eintrag | Wofür |
|---|---|
| **Formulare › u_main** | das **Formular**. Doppelklick öffnet den Designer |
| **Units › u_main.py** | **dein** Code: was passieren soll, wenn jemand klickt |

Im Ordner liegen noch zwei weitere Dateien, die Natter selbst schreibt
und die du nicht bearbeitest – deshalb stehen sie auch nicht im Baum:
`u_main_design.py` (aus dem Formular erzeugt) und `main.py` (startet das
Programm). Genau so hält es Lazarus mit der Projektdatei `.lpr`. Wenn du
trotzdem hineinsehen willst: **Projekt → Startdatei anzeigen**.

Die Trennung von `u_main.pfm` und `u_main.py` ist derselbe Gedanke wie
`.lfm` und `.pas` in Lazarus.

## 2. Das Formular bauen

Doppelklick auf **u_main** unter „Formulare" öffnet den Designer.

Links oben steht die **Komponentenpalette**. Klick eine Kachel an und
dann in das Formular – dort entsteht die Komponente. (Ein Doppelklick
auf die Kachel legt sie in die Mitte.)

Rechts steht der **Objektinspektor**. Dort änderst du, was die
Komponente können soll:

* `caption` – die Beschriftung
* `left`, `top`, `width`, `height` – Lage und Größe
* Reiter **Ereignisse** – was bei einem Klick passieren soll

**Doppelklick auf den Knopf** im Formular – Natter legt dir die
Methode dafür in `u_main.py` an und verknüpft sie. (Dasselbe über die
rechte Maustaste: „Methode für „click“ anlegen“.) Der Reiter
**Ereignisse** im Objektinspektor zeigt danach, welche Methode an
welchem Ereignis hängt; dort lässt sich auch eine **schon vorhandene**
Methode auswählen.

## 3. Code schreiben

Wechsle zu **u_main.py**. Dort steht jetzt deine leere Methode – trag
hinein, was passieren soll:

```python
def b_start_click(self, sender):
    self.l_ausgabe.caption = "Hallo!"
```

Jede Komponente erreichst du über `self.` und ihren Namen – genauso wie
in Lazarus. Der Name steht im Objektinspektor in der ersten Zeile
(`name`), und die Eigenschaften heißen dort genauso wie hier:

```python
self.l_titel.caption = "Hallo"
self.e_name.text = ""
self.b_ok.enabled = False
```

### „Wo steht eigentlich das `on_click`?“

In `u_main.py` findest du nur die **Methoden** – keine Zeile, die sie
mit dem Knopf verbindet. Das ist Absicht. Die Verbindung

```python
self.b_ok.on_click = self.b_ok_click
```

schreibt Natter beim Speichern des Formulars nach `u_main_design.py`,
zusammen mit allem anderen, was du im Designer eingestellt hast. Diese
Datei wird erzeugt und nie von Hand geändert – deshalb siehst du sie
auch nicht im Projekt-Explorer. Genau so macht es Lazarus mit der
`.lfm`.

Du kannst `on_click` trotzdem selbst setzen, wenn du willst: im Code
ist es eine Eigenschaft wie jede andere. Im Unterricht braucht man das
nur selten – etwa wenn zwei Knöpfe dieselbe Methode benutzen sollen.
Dafür gibt es aber auch den Reiter **Ereignisse** im Objektinspektor,
und der schreibt es ordentlich in die `.pfm` zurück.

`sender` ist übrigens die Komponente, die das Ereignis ausgelöst hat.
Wenn mehrere Knöpfe an derselben Methode hängen, erkennst du daran,
welcher gedrückt wurde.

### Zwischen Formular und Code wechseln

**Umschalt+F12** springt vom Designer in die zugehörige `u_main.py`
und wieder zurück – wie F12 in Lazarus. (F12 selbst ist in Natter
„Zur Definition springen“, wie in VS Code.)

Zwei Hilfen im Editor: die **senkrechten Linien** zeigen dir die
Einrückungsebenen (bei Python ist die Einrückung die Syntax!), und die
**Rücktaste** löscht eine ganze Ebene auf einmal.

## 4. Starten

**F5** startet mit Debugger, **Strg+F5** ohne.

Vor dem Start prüft Natter deinen Code. Findet es etwas, steht es unten
unter **Meldungen** – ein Doppelklick bringt dich an die Stelle.

## 5. Wenn etwas schiefgeht

Natter zeigt keinen englischen Traceback, sondern eine Meldung in drei
Teilen:

* **Wo** – Datei, Zeile, Methode
* **Was** – was passiert ist
* **Prüfe** – woran es liegen könnte

Der letzte Teil ist Absicht: Natter sagt dir nicht die Lösung, sondern
wo du suchen sollst. Das Finden ist die eigentliche Aufgabe.

Zum Suchen setzt du einen **Haltepunkt**: Klick links neben die
Zeilennummer. Mit F5 hält das Programm dort an, und unter **Variablen**
siehst du, was gerade in deinen Variablen steht. Rechtsklick auf eine
Liste oder Tabelle: **Als Tabelle anzeigen**.

## 6. Diagramme

**Datei → Neues Diagramm …** gibt dir sieben Arten: Klassendiagramm,
Struktogramm, Entscheidungstabelle, Use-Case-, Aktivitäts-, Zustands-
und Sequenzdiagramm.

Aus einem Klassendiagramm und aus einem Struktogramm kann Natter
**Python-Quelltext erzeugen** (Menü „Quelltext"). Das ist eine Vorlage
zum Abschreiben, kein fertiges Programm.

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

## Und wenn ich nicht weiterkomme?

Probier die **Beispielprojekte** vom Startbild. Sie sind keine
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

Wenn du bei 03 hängst, hilft 02 weiter — nicht 09.

Beim Öffnen legt Natter eine **Kopie** in deinem Dokumente-Ordner an.
Du kannst darin also alles ausprobieren, ohne etwas kaputtzumachen.
