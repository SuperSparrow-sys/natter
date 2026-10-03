# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **668**.

## Ein neuer Punkt

```markdown
## 668. Kurz, was nicht stimmt

**Gemeldet:** Datum, wo es auffiel (Fenster, Menü, Beispielprojekt),
Natter-Version.

**Beobachtet:** Was passiert ist und was stattdessen zu erwarten war.
Wörtlich übernommene Meldungen in Anführungszeichen.

**Ursache:** noch offen - oder nachgewiesen, mit Datei und Zeile.

**Zu tun:** Was geändert werden muss und woran das Erledigtsein zu
erkennen ist.
```

---

# Offen

## 666. Struktogramm-Code: eine eingetippte Ziffernfolge wird immer Zahl, PIN-Abfrage und Menü mit „"1"“ laufen endlos, Binärzahl und Quersumme brechen ab

**Gemeldet:** 4. Oktober 2026, Durchsicht vor 0.4.4, Stand 208c304. Rückschritt durch die Punkte 662 bis 665 (Commit 208c304): mit `ide/` aus 957c938 laufen alle Beispiele unten richtig.

**Beobachtet:** Jede „Eingabe:“ wird `eingabe_lesen(…)`, und das liefert für „1234“, „0815“, „1“ oder „1011“ eine Zahl, auch wo das Struktogramm sie als Text benutzt. Ohne jede Meldung falsch:

- PIN-Abfrage „geheim ← "1234"“, „Eingabe: pin“, Kopfschleife „solange pin != geheim“ mit „Eingabe: pin“: mit der Eingabe 1234 kommt immer wieder „falsch“, die Schleife endet nie. Ebenso „pin = "0815"“ in einer Verzweigung (immer „falsch“) und die Fußschleife „wiederhole bis eingabe = passwort oder versuche = 3“ mit „passwort ← "0000"“ (nach drei richtigen Eingaben „gesperrt“).
- Menü in einer Fußschleife „wiederhole bis wahl = "0"“ mit der Verzweigung „wahl = "1"“: weder „1“ noch „0“ wirkt, die Schleife endet nie. Eine Fallauswahl mit den Fällen „"1"“ und „"2"“ landet bei der Eingabe 1 immer bei „sonst“.
- „Eingabe: text“, „Eingabe: zeichen“ und „b = zeichen“ in „für jedes b in text“: für „Tel 0151 1234“ und „1“ kommt 0 statt 3 heraus.

Mit Abbruch:

- Binärzahl umrechnen, „für jedes ziffer in binaer“ mit „wert ← wert * 2 + int(ziffer)“: bei 1011 „TypeError: 'int' object is not iterable“; mit „für i von 0 bis len(binaer) - 1“ und „binaer[i] = "1"“: „TypeError: object of type 'int' has no len()“.
- Quersumme über die Ziffern („für jedes z in zahl“ oder „int(zahl[i])“) bei 4711, Palindromprüfung „wort = wort[::-1]“ bei 12321 („'int' object is not subscriptable“), „z in text“ bei „R2D2“ und „2“ („'in <string>' requires string as left operand, not int“).

Mit dem Erzeuger aus 957c938 entstand in allen diesen Fällen `input(…)`, und die Programme gaben „richtig“, „neu“, 3, 11, 13 und „Palindrom“ aus. Das Handbuch (`docs/handbuch.md`, Abschnitt 3.4) nennt nur die Postleitzahl als Ausnahme und sagt, ein eingelesener Name bleibe ein Name; dass eine PIN oder eine Menüwahl „1“ nicht mehr mit einem Text in Anführungszeichen übereinstimmt, steht nirgends.

**Ursache:** nachgewiesen. `EINGABE_LESEN` in `ide/diagramm/struktogramm_code.py` (Zeile 129 bis 140) entscheidet allein nach dem eingetippten Text, und `_ein_ausgabe_als_python` (Zeile 876) erzeugt für jede Eingabe `eingabe_lesen(…)`. Was das Struktogramm über den Namen sagt (Vergleich mit einem Text in Anführungszeichen, Fälle in Anführungszeichen, `für jedes … in name`, `len(name)`, `name[i]`, `name[::-1]`, `… in name`), spielt seit 208c304 keine Rolle mehr. Nachweis: Skripte `faelle2.py`, `faelle3.py` und `faelle4.py` im Scratchpad der Durchsicht übersetzen dieselben Struktogramme mit `ide/` aus 957c938 und aus 208c304 und führen den Code mit Eingaben über die Standardeingabe aus. Nebenbei steht in `_Schreiber.__init__` (Zeile 246 bis 247) noch der Kommentar zum entfernten Attribut `zahlnamen` über `eingabe_lesen`.

**Zu tun:** Eine Eingabe, die das Struktogramm erkennbar als Text benutzt, als Text lesen (`input(…)`), auch wenn Ziffern getippt werden: verglichen oder zugewiesen mit einem Text in Anführungszeichen, unter einer Fallauswahl mit Fällen in Anführungszeichen, durchlaufen mit „für jedes … in“, mit `len`, Index, Ausschnitt oder als rechte Seite von `in`. Alles andere bleibt bei `eingabe_lesen`, damit die Punkte 662 bis 664 erledigt bleiben. Das Handbuch nennt die Regel. Den verwaisten Kommentar entfernen. Erledigt, wenn Tests die PIN-Abfrage mit 1111 und 1234 („falsch“, „richtig“), das Menü mit „"1"“ und „"0"“, die Binärzahl 1011 (11), die Quersumme über Ziffern von 4711 (13) und das Palindrom 12321 ausführen und die Tests aus den Punkten 662 bis 665 grün bleiben.

## 667. Struktogramm-Code: eine Fallauswahl über ein Rechenzeichen („+“, „-“, „*“, „:“) wird zu `if False`, der Taschenrechner rechnet nie

**Gemeldet:** 4. Oktober 2026, Durchsicht vor 0.4.4, Stand 208c304. Kein Rückschritt, mit 957c938 ebenso.

**Beobachtet:** Der übliche Taschenrechner als Struktogramm: „Eingabe: a“, „Eingabe: op“, „Eingabe: b“, Fallauswahl mit dem Kopf „op“ und den Fällen „+“, „-“, „*“, „:“ und „sonst“, darin „Ausgabe: a + b“ usw. Erzeugt wird für jeden Fall `# +` und `if False:` bzw. `elif False:`; mit 3, „-“, 5 gibt das Programm „?“ aus statt -2. Über dem Code steht „4 Zeilen konnten nicht übernommen werden“, obwohl jeder Fall ein einzelnes Zeichen ist, das nur als Text gemeint sein kann. Ein Fall „rot“ oder „J“ wird dagegen schon als Text `"rot"` übernommen (Punkte 602, 642).

**Ursache:** nachgewiesen. `_fall_als_text` in `ide/diagramm/struktogramm_code.py` (Zeile 640 bis 656) macht nur Bezeichner zu Text, `_ist_einfacher_wert` (Zeile 1367) lässt „+“ nicht als Muster zu, und `_wenn_kette` (ab Zeile 679) setzt für eine Beschriftung, die kein Python ist, den Platzhalter `False`. Nachweis: Skript `r.py` im Scratchpad der Durchsicht gibt den erzeugten Code aus; `faelle2.py` führt ihn aus.

**Zu tun:** Ein Fall, der nur aus Satz- oder Rechenzeichen besteht („+“, „-“, „*“, „/“, „:“, „?“), unter einem Kopf, der ein Name ist, als Text übernehmen. Erledigt, wenn ein Test den Taschenrechner mit 3, „-“, 5 und 3, „+“, 5 ausführt und -2 bzw. 8 erhält und die Meldung über nicht übernommene Zeilen dabei entfällt.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
