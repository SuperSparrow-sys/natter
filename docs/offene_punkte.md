# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **666**.

## Ein neuer Punkt

```markdown
## 666. Kurz, was nicht stimmt

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

## 662. Struktogramm-Code: Namen in eine Liste einlesen und alphabetisch sortieren bricht beim ersten Namen ab

**Gemeldet:** 4. Oktober 2026, Durchsicht vor 0.4.4, Stand 957c938. Rückschritt durch Punkt 659 (Commit 7ac58a8): bis b66b68a lief dasselbe Struktogramm richtig.

**Beobachtet:** Ein Bubblesort über eingegebene Namen: „namen ← []“, Zählschleife „für i von 1 bis 3“ mit „Eingabe: name“ und „namen.append(name)“, danach zwei Zählschleifen mit der Verzweigung „namen[j] > namen[j + 1]“ und dem Tausch über „hilf“. Erzeugt wird jetzt `name = zahl_lesen("name? ")`; mit der Eingabe „Cem“ bricht das Programm sofort mit „ValueError: could not convert string to float: 'Cem'“ ab. Ebenso der kleinste Name einer Liste („erster ← namen[0]“, Verzweigung „namen[i] < erster“). Mit dem Erzeuger aus b66b68a entstand `name = input("name? ")`, und das Programm gab „['Anna', 'Ben', 'Cem']“ bzw. „Anna“ aus. Punkt 659 verlangt ausdrücklich: „Listen aus Texten bleiben ausgenommen.“

**Ursache:** nachgewiesen. `_als_zahl_benutzt` in `ide/diagramm/struktogramm_code.py` (Zeile 1173 bis 1176) wertet jeden Namen neben `<` oder `>` als Zahl, also auch `namen` in „> namen[j + 1]“ und `erster` in „namen[i] < erster“; bis Punkt 659 blieb das ohne Folgen für die Eingabe. Seit Punkt 659 gibt `_zahlen_weitergeben` die Eigenschaft über ein Element (`element`, Zeile 1230, 1238 bis 1239) an die Liste und über `liste.append(name)` (Zeile 1241) an die Eingabe weiter. Nachweis: `als_python` und Ausführung mit untergeschobenem `input`, einmal mit dem Stand 957c938 und einmal mit `ide/` aus b66b68a (Skript `probe5.py` im Scratchpad der Durchsicht).

**Zu tun:** Ein Vergleich mit `<` oder `>` zwischen Elementen derselben Liste oder mit einem Namen, der selbst nur aus der Liste stammt, darf eine Liste nicht zur Zahlenliste machen; eine Liste zählt nur als Zahlenliste, wenn sie mit Zahlen angelegt wird oder ihre Elemente mit einer Zahl oder einem Zahlnamen verglichen oder verrechnet werden. Erledigt, wenn ein Test die beiden Struktogramme aus der Beobachtung mit „Cem“, „Anna“, „Ben“ ausführt und „['Anna', 'Ben', 'Cem']“ bzw. „Anna“ erhält, und die Beispiele aus Punkt 659 weiter 2, 10 und 22 ergeben.

## 663. Struktogramm-Code: das Maximum dreier eingegebener Zahlen bricht ab, wenn der Startwert mit „←“ zugewiesen wird

**Gemeldet:** 4. Oktober 2026, Durchsicht vor 0.4.4, Stand 957c938. Kein Rückschritt, mit b66b68a ebenso.

**Beobachtet:** Die übliche Aufgabe „Maximum dreier Zahlen“: „Eingabe: a“, „Eingabe: b“, „Eingabe: c“, „maximum ← a“, Verzweigungen „b > maximum“ und „c > maximum“ mit „maximum ← b“ bzw. „maximum ← c“, „Ausgabe: maximum“. Erzeugt wird `a = input("a? ")`, aber `b = zahl_lesen(…)` und `c = zahl_lesen(…)`; mit 3, 12, 9 bricht das Programm mit „TypeError: '>' not supported between instances of 'int' and 'str'“ ab. Mit „maximum = a“ statt „maximum ← a“ wird auch `a` mit `zahl_lesen` gelesen, und das Programm gibt 12 aus. Ebenso das Minimum zweier Zahlen mit „kleinste ← x“. Das Handbuch nennt „x ← 1“ als übliche Schreibweise der Zuweisung.

**Ursache:** nachgewiesen. In `_zahlen_weitergeben` (`ide/diagramm/struktogramm_code.py`, Zeile 1228) kennt `operator` die Zuweisung `=` (`=(?!=)`), aber nicht `←` und `:=`. „maximum ← a“ gibt die Eigenschaft deshalb nicht von `maximum` an `a` weiter; die Prüfung der Zuweisungen weiter unten (Zeile 1251 bis 1260) betrifft nur das Ziel einer Zuweisung und verlangt im Wert eines von `-*/%+`. Nachweis: `als_python` mit „maximum ← a“, „maximum := a“ und „maximum = a“ und Ausführung mit untergeschobenem `input` (Skript `probe9.py` im Scratchpad der Durchsicht).

**Zu tun:** Eine Zuweisung mit `←` oder `:=` wie eine mit `=` werten, in beide Richtungen: bekommt ein Zahlname den Wert eines anderen Namens, ist dieser ebenfalls eine Zahl. Erledigt, wenn ein Test das Maximum dreier Zahlen mit „maximum ← a“ für 3, 12, 9 und 10, 9, 2 ausführt und 12 bzw. 10 erhält.

## 664. Struktogramm-Code: `max`, `min`, `sum` und `sort` über eingelesene Zahlen rechnen mit Text

**Gemeldet:** 4. Oktober 2026, Durchsicht vor 0.4.4, Stand 957c938. Kein Rückschritt; Punkt 659 deckt nur Elemente wie `liste[i]` ab.

**Beobachtet:** „zahlen ← []“, Zählschleife mit „Eingabe: z“ und „zahlen.append(z)“, danach „Ausgabe: max(zahlen)“: mit 9, 10, 3 gibt das Programm 9 aus, ohne Meldung. „Ausgabe: sum(zahlen)“ und „mittel ← sum(noten) / len(noten)“ brechen mit „TypeError: unsupported operand type(s) for +: 'int' and 'str'“ ab, „zahlen.sort()“ ergibt „['10', '3', '9']“. Erzeugt wird in allen Fällen `z = input("z? ")`. Werden die Elemente dagegen in einer Schleife mit „summe ← summe + zahlen[i]“ verrechnet, liest der Code die Eingabe als Zahl. Das Handbuch sagt, eine Eingabe gelte als Zahl, wenn sie „mit `append` in eine Liste eingelesen wird, deren Elemente verrechnet oder verglichen werden“; das trifft auf `max`, `min`, `sum` und `sort` ebenso zu.

**Ursache:** nachgewiesen. `_als_zahl_benutzt` und `_zahlen_weitergeben` in `ide/diagramm/struktogramm_code.py` (Zeile 1139 bis 1262) werten eine Liste nur über Rechen- und Vergleichszeichen oder einen Anfangswert mit Zahlen als Zahlenliste; ein Aufruf wie `sum(zahlen)` oder `max(zahlen)` zählt nicht. Nachweis: Skripte `probe1.py` und `probe9.py` im Scratchpad der Durchsicht.

**Zu tun:** Eine Liste, die an `sum` übergeben oder deren Summe verrechnet wird, als Zahlenliste werten; bei `max`, `min`, `sorted` und `sort` nur, wenn das Ergebnis verrechnet oder mit einer Zahl verglichen wird, sonst bleibt eine Liste aus Texten Text (vgl. Punkt 662). Erledigt, wenn ein Test „sum(zahlen)“ und den Mittelwert mit 1, 2, 4 ausführt und 7 bzw. 2,33… erhält, und eine Namensliste weiter Text bleibt.

## 665. Struktogramm-Code: der Tausch „a, b ← b, a“ wird Kommentar, ein Bubblesort mit Merker läuft endlos (gering)

**Gemeldet:** 4. Oktober 2026, Durchsicht vor 0.4.4, Stand 957c938. Kein Rückschritt, mit b66b68a ebenso.

**Beobachtet:** Im Bubblesort steht der Tausch als „liste[j], liste[j + 1] ← liste[j + 1], liste[j]“. Im Code erscheint er als Kommentar `# liste[j], liste[j + 1] ← liste[j + 1], liste[j]`; mit „=“ statt „←“ wird dieselbe Zeile übernommen. Mit einer Schleife „solange getauscht“, in der „getauscht ← wahr“ nach dem Tausch steht, läuft das erzeugte Programm bei jeder unsortierten Eingabe endlos, weil nie getauscht wird. Ohne Merker bleibt die Liste unsortiert. Über dem Code steht zwar „1 Zeile konnte nicht übernommen werden“, aber die Zeile ist Python bis auf den Pfeil, den das Handbuch als Zuweisung nennt.

**Ursache:** nachgewiesen. `_ZUWEISUNG` in `ide/diagramm/struktogramm_code.py` (Zeile 85 bis 88) lässt als Ziel nur einen einzelnen Namen mit Index oder Attribut zu, keine durch Komma getrennte Liste von Zielen. Nachweis: `als_python` mit „a, b ← b, a“ und „a, b = b, a“ (Skript `probe2.py` im Scratchpad der Durchsicht).

**Zu tun:** Ein Ziel aus mehreren durch Komma getrennten Zielen vor `←` oder `:=` wie bei `=` übernehmen. Erledigt, wenn ein Test den Bubblesort mit Merker und Tausch „liste[j], liste[j + 1] ← liste[j + 1], liste[j]“ mit 10, 9, 100, 2 ausführt und [2, 9, 10, 100] erhält.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
