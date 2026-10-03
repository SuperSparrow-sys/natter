# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **662**.

## Ein neuer Punkt

```markdown
## 662. Kurz, was nicht stimmt

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

## 658. Struktogramm-Code: „nicht“, „und“, „oder“ mit einem Namen ohne Wert ergeben Code, der mit `NameError` abbricht

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand b66b68a. Rückschritt durch Punkt 655 (Commit 53d66e4): vorher wurden diese Texte als Kommentar mit Platzhalter übernommen und über dem Code gezählt.

**Beobachtet:** Eine Fallauswahl „status“ mit den Fällen „bestanden“, „nicht bestanden“ und „sonst“ nach „Eingabe: status“ ergibt `if status == 'bestanden':` und `elif not bestanden:`. Über dem Code steht, dass alles übernommen wurde. Mit der Eingabe „nicht bestanden“ bricht das Programm mit „NameError: name 'bestanden' is not defined“ ab. Ebenso wird die Verzweigung „nicht fertig“ ohne Zuweisung an `fertig` zu `if not fertig:` und „x > 0 und gerade“ zu `if x > 0 and gerade:`, beide enden mit `NameError`. Vor Punkt 655 standen alle drei als Kommentar mit `if False:` im Code, und die Meldung über dem Code nannte sie. Das Handbuch sagt: „Ein Fall wie „J“ oder „rot“, der im Struktogramm keinen Wert bekommt, ist ein Text“ und „Was kein Python ist, steht als Kommentar im Code“.

**Ursache:** nachgewiesen. `_logikwoerter` in `ide/diagramm/struktogramm_code.py` (Zeile 730 bis 758) wird aus `_einzeilig` auf jeden Kopf und jeden Fall angewandt. Danach ist „nicht bestanden“ der gültige Ausdruck `not bestanden`; `_fall_als_text` (Zeile 600) macht nur einzelne Bezeichner zum Text, und `_vergleich` (Zeile 681) übernimmt `not bestanden` als Bedingung (`_ist_bedingung`). Ob die Namen im Struktogramm einen Wert bekommen (`self.zugewiesen`), prüft für Bedingungen niemand. Nachweis: `als_python` mit den drei Beispielen, einmal unverändert und einmal mit `_logikwoerter` als Identität (Skript `stg_probe3b.py`/`stg_probe4.py` im Scratchpad der Durchsicht).

**Zu tun:** „und“, „oder“, „nicht“ nur übersetzen, wenn jeder übrige Name der Bedingung im Struktogramm einen Wert bekommt oder eingebaut ist; sonst wie vorher als Kommentar mit Platzhalter übernehmen und zählen. Ein Fall einer Fallauswahl aus mehreren Wörtern ohne Wert ist ein Text. Erledigt, wenn ein Test das Beispiel mit „nicht bestanden“ mit beiden Eingaben ohne Ausnahme ausführt und „nicht fertig“ ohne Zuweisung als nicht übernommen gezählt wird.

## 659. Struktogramm-Code: eine Eingabe, die mit Elementen einer Zahlenliste verglichen oder in eine Liste eingelesen wird, bleibt Text

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand b66b68a. Kein Rückschritt; Punkt 656 deckt nur den Namen als Index ab.

**Beobachtet:** Drei übliche Unterrichtsaufgaben ergeben falsche Ergebnisse ohne Meldung:
- Lineare Suche: „liste ← [3, 7, 5]“, „Eingabe: gesucht“, Schleife mit „liste[i] = gesucht“. Erzeugt wird `gesucht = input("gesucht? ")`; mit der Eingabe 5 gibt das Programm „nicht gefunden“ aus. Ebenso „x in zahlen“.
- Zahlen in eine Liste einlesen und das Maximum bestimmen: „Eingabe: z“, „liste.append(z)“, dann „liste[i] > maximum“. Mit 9, 10, 3 gibt das Programm 9 aus, weil Texte verglichen werden.
- Dieselbe Liste summieren: „summe ← summe + liste[i]“ bricht mit „TypeError: unsupported operand type(s) for +: 'int' and 'str'“ ab.

**Ursache:** nachgewiesen. `_als_zahl_benutzt` und `_zahlen_weitergeben` in `ide/diagramm/struktogramm_code.py` (Zeile 1076 bis 1185) werten einen Namen nur als Zahl, wenn er neben einem Rechen- oder Vergleichszeichen mit einer Zahl oder einem Zahlnamen steht. Ein Element `liste[i]` einer Liste aus Zahlen zählt nicht als Zahl, `x in zahlen` nicht als Vergleich, und ein Name, der mit `append` in eine Liste kommt, deren Elemente verrechnet werden, bleibt Text. Nachweis: `als_python` und Ausführung mit untergeschobenem `input` (Skripte `stg_probe.py` und `stg_probe2.py` im Scratchpad der Durchsicht).

**Zu tun:** Eine Liste, die mit Zahlen angelegt wird oder deren Elemente verrechnet oder mit `<`/`>` verglichen werden, als Zahlenliste werten; ein Name, der mit einem Element einer Zahlenliste verglichen, mit `in` in ihr gesucht oder mit `append` in sie eingefügt wird, ist dann eine Zahl. Listen aus Texten bleiben ausgenommen. Erledigt, wenn ein Test die drei Beispiele ausführt und „gefunden an Stelle 2“, 10 und 22 erhält.

## 660. Test-Explorer: die Statuszeile verspricht, dass ein Klick den Grund zeigt, ein Klick tut aber nichts

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand b66b68a. Kein Rückschritt.

**Beobachtet:** Nach „Projekt → Alle Tests ausführen“ steht in der Statuszeile „Ein Klick auf einen Eintrag im Test-Explorer zeigt, woran es lag.“ Ein Klick auf einen fehlgeschlagenen Test zeigt nichts, ein Doppelklick startet ihn nur neu. Der Grund steht allein als Tooltip über der Spalte „Status“; über dem Testnamen erscheint nichts. Bei `assertEqual(2, 3, "Größe stimmt nicht")` zeigt der Tooltip nur „Soll: 2 · Ist: 3“, der Text der Lehrkraft fehlt. Das Handbuch (Abschnitt 3.7) sagt: „Ist ein `assert` nicht erfüllt, steht die Zeile im Panel.“

**Ursache:** nachgewiesen. In `ide/shell/hauptfenster.py` ist am Baum nur `itemActivated` mit dem Neustart verbunden (Zeile 1199); die Meldung steht in `_tests_fertig` (Zeile 2692 bis 2693). `_test_eintrag_aktualisieren` (Zeile 3315 bis 3328) setzt den Tooltip nur für Spalte 1 und bei vorhandenem Soll/Ist ohne `nachricht`. Nachweis: Tooltips der Spalten 0 bis 2 nach einem Lauf sind `['', 'Soll: 2 · Ist: 3', '']`.

**Zu tun:** Den Grund eines nicht bestandenen Tests sichtbar machen, wo die Meldung es sagt, etwa bei einem Klick in einer Zeile unter dem Baum oder in der Ausgabe, mit Soll, Ist und eigenem Text; sonst die Meldung und das Handbuch an das tatsächliche Verhalten anpassen. Erledigt, wenn ein Test nach einem Klick auf einen fehlgeschlagenen Eintrag Soll, Ist und den Text aus `assertEqual` sichtbar findet.

## 661. Test-Explorer: eine Ausnahme im Test nennt weder Fehlerart noch Zeile und bleibt englisch (gering)

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand b66b68a. Kein Rückschritt.

**Beobachtet:** Wirft die geprüfte Funktion eine Ausnahme, steht als Grund nur „'NoneType' object has no attribute 'foo'“. Fehlerart (`AttributeError`), Datei und Zeile fehlen, und der Text ist nicht übersetzt. Bei einem nicht erfüllten `assert` steht dagegen die Zeile da. Mit dieser Meldung lässt sich die Stelle im eigenen Code nicht finden.

**Ursache:** nachgewiesen. `addError` in `ide/testrunner/harness.py` (Zeile 271 bis 294) übernimmt nur `str(err[1])`, ohne Typ, letzte Zeile des Tracebacks aus dem Projekt und ohne `meldung_eindeutschen` oder Fehlerkatalog.

**Zu tun:** Fehlerart, Datei und Zeile der letzten Stelle im Projekt und den deutschen Text aus dem Fehlerkatalog in die Meldung übernehmen. Erledigt, wenn ein Test mit einer Ausnahme in der geprüften Funktion Fehlerart, Dateiname und Zeile in der Meldung findet.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
