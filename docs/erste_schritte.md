# Erste Schritte mit Natter

Diese Seite führt in zehn Minuten vom leeren Bildschirm zum laufenden
Programm. Wenn du Lazarus kennst, wird dir fast alles bekannt vorkommen –
nur die Sprache ist Python statt Pascal.

## 1. Ein Projekt anlegen

**Projekt → Neues Projekt …**, oder auf dem Startbild „Neues Projekt …".

Natter legt dir einen Ordner mit vier Dateien an:

| Datei | Wofür |
|---|---|
| `main.py` | startet das Programm – hier änderst du nichts |
| `u_main.pfm` | das **Formular**: wo welche Komponente liegt. Entsteht im Designer, nicht von Hand |
| `u_main_design.py` | wird aus der `.pfm` erzeugt. **Nicht bearbeiten** – deine Änderungen wären beim nächsten Speichern weg |
| `u_main.py` | **dein** Code: was passieren soll, wenn jemand klickt |

Die Trennung der letzten beiden ist derselbe Gedanke wie `.lfm` und
`.pas` in Lazarus.

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

Trag bei `on_click` eines Knopfes einen Namen ein, etwa
`b_start_click`. Natter legt dir die passende Methode in `u_main.py`
an.

## 3. Code schreiben

Wechsle zu **u_main.py**. Dort steht jetzt deine leere Methode:

```python
def b_start_click(self, sender) -> None:
    self.l_ausgabe.caption = "Hallo!"
```

Jede Komponente erreichst du über `self.` und ihren Namen – genauso wie
in Lazarus.

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
| F7 / F8 | Einzelschritt / Prozedurschritt |
| Strg+S | Speichern |
| Strg+F | Suchen |
| Strg+Z | Rückgängig |
| Strg+G | Gruppieren (im Diagramm-Editor) |
| Strg+Umschalt+E | Quelltext aus dem Diagramm erzeugen |

## Und wenn ich nicht weiterkomme?

Probier eines der **Beispielprojekte** vom Startbild. Sie sind alle
lauffähig und zeigen je eine Sache: die Ampel die Klassen, der Garten
die Listen, das Würfelspiel den Zufall, die CSV-Auswertung das Einlesen
von Daten.
