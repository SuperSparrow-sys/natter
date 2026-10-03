# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **653**.

## Ein neuer Punkt

```markdown
## 653. Kurz, was nicht stimmt

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

## 637. Struktogramm-Code: eine Kommazahl in Bedingung oder Zuweisung ergibt ungültigen Code oder ein Tupel

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da.

**Beobachtet:**
- „x > 2,5“ als Bedingung einer Verzweigung wird `if x > 2,5:`, „solange x < 1,5“ wird `while x < 1,5:`, „wiederhole bis x >= 1,5“ wird `if x >= 1,5: break`, ein Fall „< 2,5“ der Fallauswahl `if note < 2,5:`. Jedes Mal `SyntaxError`, und `nicht_uebernommen` ist leer. „Quelltext → in Datei“ schreibt die Unit trotzdem in den Projektordner und meldet nur „Geschrieben: …“. Der Modul-Docstring verspricht „Der erzeugte Code ist dadurch immer gültiges Python“.
- „preis ← 2,5“ wird `preis = 2,5`; danach gibt „gesamt ← preis * 4“ das Tupel `(2, 5, 2, 5, 2, 5, 2, 5)` aus. „Ausgabe: 2,5 * x“ wird `print(2,5 * x)` und gibt „2 10“ aus. Ein Fall „2,5“ wird `case 2 | 5`, die Eingabe 5 landet dort.

Das Dezimalkomma ist im Unterricht die übliche Schreibweise; die Eingabe nimmt es seit 0.4.4 an, der Rest des Struktogramms nicht.

**Ursache:** nachgewiesen. `_bedingungstext` und `_als_ausdruck` (`ide/diagramm/struktogramm_code.py` Zeilen 1098 und 1131) prüfen mit `ast.parse(…, mode="eval")`, das „x > 2,5“ als Tupel annimmt; hinter `if`, `while`, `elif` ist ein Tupel ohne Klammern aber nicht erlaubt. Die Reparatur aus Punkt 604 (`_ist_grenze`) gilt nur für die Zählschleife. Zuweisung und Ausgabe (`_anweisung`, `_ein_ausgabe_als_python` Zeile 707) unterscheiden Dezimalkomma und Trennkomma nicht. Probe: Verzweigung „x > 2,5“ nach „Eingabe: x“ mit `als_python` übersetzt und ausgeführt, `SyntaxError: invalid syntax (line 3)`.

**Zu tun:** Eine Zahl der Form Ziffern-Komma-Ziffern in Köpfen, Fällen, Zuweisungen und Ausgaben als Kommazahl übersetzen (`2.5`), wo sie nicht eindeutig ein Trennzeichen ist (Funktionsaufruf, Liste); was sich so nicht entscheiden lässt, als Kommentar zählen. Kein Kopf darf Code ergeben, der nicht übersetzt. Erledigt, wenn ein Test die Fälle oben übersetzt, ausführt und 2,5 als Zahl findet.

## 638. Exe eines Konsolenprogramms mit matplotlib zeigt kein Diagramm mehr

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Rückschritt aus Punkt 629.

**Beobachtet:** Ein Konsolenprojekt mit `import matplotlib.pyplot as plt … plt.show()` öffnet in Natter ein Diagrammfenster. Mit „Als Exe exportieren“ (subprocess gemockt) steht im PyInstaller-Befehl `--exclude-module PySide6` und `--exclude-module shiboken6`; `tkinter` ist ohnehin ausgeschlossen, Tcl/Tk fehlt in der Auslieferung (`tools/ide_paketieren.py` Zeile 117). In einer Umgebung ohne PySide6 und tkinter wählt matplotlib das Backend „agg“, `plt.show()` gibt nur die englische Warnung „FigureCanvasAgg is non-interactive, and thus cannot be shown“ aus, und kein Fenster erscheint. Diagramme mit pyplot sind in Konsolenprogrammen im Unterricht verbreitet.

**Ursache:** nachgewiesen für den Ausschluss. Seit Punkt 629 kommen `PySide6` und `shiboken6` nur in die Exe, wenn im Projekt „pcl“ oder „PySide6“ vorkommt (`_OPTIONALE_PAKETE` in `ide/export/exporter.py` Zeilen 103-109). `_BRAUCHT["matplotlib"]` (Zeile 127) nennt nur `numpy` und `PIL`. Dass die Exe vor 629 ein Fenster zeigte, ist vermutet (PySide6 war nicht ausgeschlossen, der matplotlib-Hook von PyInstaller nimmt dann QtAgg).

**Zu tun:** Bei `matplotlib` auch `PySide6` und `shiboken6` mitnehmen, oder matplotlib in Konsolen-Exes auf ein mitgeliefertes Fenster-Backend festlegen. Erledigt, wenn ein Test (subprocess gemockt) für ein Konsolenprojekt mit `matplotlib.pyplot` keinen Ausschluss von PySide6 findet.

## 639. Formular mit doppeltem Menü-Kürzel aus einer älteren Fassung: der Designer öffnet es nicht, das Programm startet nicht

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Rückschritt aus Punkt 633.

**Beobachtet:** Eine `.pfm`, deren Hauptmenü zwei Einträge mit „Strg+N“ trägt, wie sie der Menü-Editor bis 0.4.3 ohne Einwand speicherte, lässt sich nicht mehr im Designer öffnen: `formular_fuer_designer_laden` endet mit `PfmBeschaedigt` „Das Tastenkürzel „Strg+N“ steht bei „Neu“ und bei „Neu2“ …“. Der Menü-Editor, in dem sich das Kürzel ändern ließe, ist damit nicht erreichbar; bleibt nur, die JSON-Datei von Hand zu bearbeiten. Auch das Programm selbst bricht beim Start ab, obwohl bis 0.4.3 nur das eine Kürzel wirkungslos war.

**Ursache:** nachgewiesen. `eintraege_pruefen` (`pcl/components/menus.py` Zeilen 272-275) löst bei einem doppelten Kürzel `NatterPropertyError` aus, einen `TypeError`; `formular_fuer_designer_laden` (`ide/designer/laden.py`) macht daraus „beschädigt“. Probe: `.pfm` mit zwei Einträgen „Strg+N“ in `%TEMP%`, geladen mit `formular_fuer_designer_laden`.

**Zu tun:** Ein doppeltes Kürzel im Designer zulassen und dort melden (Design-Prüfung oder Menü-Editor), statt das Öffnen zu verweigern; zur Laufzeit höchstens einen Hinweis geben und das zweite Kürzel nicht anmelden, statt den Start abzubrechen. Erledigt, wenn ein Test eine solche `.pfm` im Designer öffnet, das Kürzel im Menü-Editor ändert und das Programm danach startet.

## 640. Struktogramm-Code: „raise NichtGenugGeld“ und der zweite Name einer Tupel-Zuweisung werden still zum Kommentar

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Rückschritt aus Punkt 602.

**Beobachtet:**
- Ein Aussprung „raise NichtGenugGeld“ in der Verzweigung „betrag > stand?“ wird `# raise NichtGenugGeld` und `pass`. Die Abbuchung läuft danach weiter, der Stand wird negativ. Bis 2376f1d stand `raise NichtGenugGeld` im Code; Punkt 602 nennt `raise` ausdrücklich als übernommenen Aussprung, und das Beispielprojekt `06_Kontoverwaltung` hat eine solche eigene Ausnahme.
- „Vorname, Nachname = name.split()“ und danach „Ausgabe: Nachname“: `print(Nachname)` wird Kommentar, das Programm gibt nichts aus. Bis 2376f1d gab es „Lovelace“ aus.

**Ursache:** nachgewiesen. `_pseudocode` (`ide/diagramm/struktogramm_code.py` Zeile 425) behandelt jeden großgeschriebenen Namen, der im Struktogramm keinen Wert bekommt (`_unbekannte_namen`, Zeile 812), als Pseudocode, auch den Namen einer Ausnahmeklasse hinter `raise`. `_zugewiesene_namen` (Zeile 750) erfasst bei einer Tupel-Zuweisung nur den ersten Namen. Probe: beide Struktogramme mit dem Erzeuger aus 2376f1d und aus 6c2a0da übersetzt und ausgeführt.

**Zu tun:** Den Namen hinter `raise` nicht als Pseudocode werten; alle Ziele einer Tupel-Zuweisung (auch in `for a, b in …`) als zugewiesen erfassen. Erledigt, wenn ein Test beide Fälle übersetzt findet und der Aussprung das Programm abbricht.

## 641. Struktogramm-Code: „wahr“ und „falsch“ werden nur zum Teil zu `True` und `False`

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Bezug: Punkt 602.

**Beobachtet:**
- Fallauswahl mit Kopf `fertig` und Fällen „wahr“ und „falsch“ nach „fertig ← wahr“: es entsteht `fertig = True` und `match fertig: case 'wahr': … case 'falsch':`. Kein Fall läuft, ohne Meldung. Bis 2376f1d endete das sichtbar mit `NameError`.
- Mehrfachauswahl mit dem Fall „fertig = wahr“: `if fertig == wahr:`, `NameError`.
- Fußschleife „wiederhole bis fertig = wahr“ mit „weiter“ im Rumpf: unten steht `if fertig == True`, vor dem `continue` aber `if fertig == wahr:`, `NameError` mitten im Lauf.

Das Handbuch (Abschnitt Diagramme) sagt: „wahr“ und „falsch“ werden zu `True` und `False`.

**Ursache:** nachgewiesen. `_fall_als_text` (`ide/diagramm/struktogramm_code.py` Zeile 573) macht jeden Namen ohne Wert zum Text, auch „wahr“; `_wahrheitswerte` läuft nur in `bedingung()` und `_anweisung`, nicht für die Vorabprüfung der Fußschleife und nicht in `_vergleich` (Zeile 647).

**Zu tun:** `_wahrheitswerte` auf jeden erzeugten Ausdruck anwenden, auch auf Fälle und die Vorabprüfung. Erledigt, wenn ein Test die drei Fälle oben übersetzt, ausführt und den richtigen Zweig findet.

## 642. Struktogramm-Code: ein Fall „J“ oder „N“ endet mit `NameError`

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Bezug: Punkt 602.

**Beobachtet:** „Eingabe: antwort“ und eine Fallauswahl mit den Fällen „J“, „N“, „sonst“ ergibt `if antwort == J:` und beim Lauf `NameError: name 'J' is not defined`. Klein geschriebene Fälle wie „rot“ werden seit Punkt 602 richtig `'rot'`. Ja/Nein-Abfragen mit J und N und Notenstufen A bis F sind im Unterricht häufig.

**Ursache:** nachgewiesen. `_fall_als_text` (`ide/diagramm/struktogramm_code.py` Zeile 586) lässt einen Namen mit `etikett.isupper()` als Konstante stehen, auch einen einzelnen Großbuchstaben, der im Struktogramm nirgends einen Wert bekommt.

**Zu tun:** Großgeschriebene Fälle nur dann als Name übernehmen, wenn sie im Struktogramm einen Wert bekommen; sonst als Text. Erledigt, wenn ein Test „J“/„N“ übersetzt und die Eingabe „J“ den richtigen Zweig nimmt.

## 643. Struktogramm-Code: jede eingegebene Zahl wird `float`, ein Listenindex endet mit `TypeError`

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Bezug: Punkte 601 und 622.

**Beobachtet:** „Eingabe: i“, „i < 3?“, „Ausgabe: liste[i]“ endet mit `TypeError: list indices must be integers or slices, not float`. „Eingabe: a“, „Eingabe: b“, „Ausgabe: a + b“ mit 3 und 5 gibt „8.0“ aus, ein Countdown „solange n > 0“ „3.0“, „2.0“, „1.0“, jeweils mit Dezimalpunkt.

**Ursache:** nachgewiesen. Eine als Zahl benutzte Eingabe wird `float(input(…).replace(",", "."))` (`ide/diagramm/struktogramm_code.py` um Zeile 728); als `int` gilt nur ein Name im Kopf einer Zählschleife oder in `range`. Seit 601/622 erfassen `_als_zahl_benutzt` und `_zahlen_weitergeben` deutlich mehr Namen.

**Zu tun:** Eine Eingabe, die als Index oder in ganzzahligen Rechnungen benutzt wird, als ganze Zahl lesen, oder allgemein ganzzahlige Eingaben als `int` und nur Kommazahlen als `float` liefern (wie `pcl.zahl`). Erledigt, wenn ein Test den Listenindex ohne Fehler ausführt und „8“ statt „8.0“ ausgibt.

## 644. Haltepunkt auf `else:`, `finally:` oder einer Docstring-Zeile hält an der falschen Stelle

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Bezug: Punkte 611 und 631.

**Beobachtet:** Mit echtem debugpy gemessen:
- `if n > 3: a = 'gross'` / `else: a = 'klein'` mit n = 5, Haltepunkt auf `else:`: das Programm hält im `if`-Zweig, obwohl der `else`-Zweig nie läuft.
- `for … else:` mit Haltepunkt auf `else:`: Halt bei jedem Schleifendurchlauf.
- `try`/`finally` mit Haltepunkt auf `finally:`: Halt im `try`-Block, bevor er läuft.
- Haltepunkt auf der Docstring-Zeile einer Funktion: Halt einmal an der `def`-Zeile beim Laden des Moduls, nie beim Aufruf.

Dasselbe gilt für „Ausführen bis Cursor“ auf diesen Zeilen.

**Ursache:** nachgewiesen. `anweisungszeile` (`ide/shell/quelltexteditor.py` Zeile 492) überspringt nur Leer- und Kommentarzeilen. Zeilen ohne eigenen Bytecode bleiben stehen, und debugpy legt den Haltepunkt auf eine Anweisung davor.

**Zu tun:** Die nächste ausführbare Zeile aus der Zeilentabelle des übersetzten Codes bestimmen (`co_lines`), mindestens `else:`, `finally:`, `try:` und Docstrings überspringen. Erledigt, wenn ein Test mit debugpy für die vier Fälle oben Editor und Halt übereinstimmend findet.

## 645. Nach Strg+S während einer Debug-Sitzung bekommt debugpy falsche Haltepunkt-Zeilen

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Bezug: Punkt 621.

**Beobachtet:** Im Halt eine Zeile oben einfügen und einen Haltepunkt setzen: debugpy bekommt richtig die Zeile der geladenen Datei. Nach Strg+S und einem weiteren Haltepunkt gehen die Zeilen des Editors unverändert an debugpy, das laufende Programm kennt die Anweisungen aber noch eine Zeile höher. „Ausführen bis Cursor“ schickt ebenso eine Zeile zu viel. Das Programm hält an der falschen Anweisung, ein Haltepunkt fällt still weg.

**Ursache:** nachgewiesen. `_zeilen_zur_datei` (`ide/shell/hauptfenster.py` Zeile 7678) vergleicht den Editor mit der Datei auf der Platte, nicht mit dem Stand, den das Programm beim Start geladen hat; nach dem Speichern sind beide gleich, und die Umrechnung entfällt. Probe mit `HauptFenster` und nachgebildeter Sitzung: nach dem Speichern `('probe.py', [4, 5])` statt `[3, 4]`.

**Zu tun:** Beim Start der Sitzung den Text jeder Datei festhalten und bis zum Ende der Sitzung gegen diesen umrechnen. Erledigt, wenn ein Test nach Einfügen, Speichern und neuem Haltepunkt die Zeilen der geladenen Datei an debugpy gehen sieht.

## 646. Eine Testdatei der Lehrkraft verhindert Start und Exe-Export, solange die Funktion noch fehlt

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Beim Export Rückschritt aus Punkt 594.

**Beobachtet:** Nach Handbuch Abschnitt 3.7 teilt eine Lehrkraft eine `test_….py` aus, die zeigt, welche Anforderungen schon erfüllt sind. Importiert sie eine Funktion, die die Schülerin noch nicht geschrieben hat (`from u_main import verdoppeln`), meldet die Prüfung vor dem Start einen blockierenden Fund `natter-import` in der Testdatei: das Programm startet nicht. Seit Punkt 594 entsteht auch keine Exe, obwohl Testdateien nicht in die Exe gehören. Gerade solange die Aufgabe nicht fertig ist, soll sich das Programm aber starten lassen.

**Ursache:** nachgewiesen. `_importe_pruefen` (`ide/run/pruefung.py` Zeilen 626-665) läuft über `projekt.alle_python_dateien()` und behandelt Testdateien wie Programmcode; der Export ruft dieselbe Prüfung (`_vorstart_pruefung_blockiert(fuer_export=True)`, `ide/shell/hauptfenster.py` Zeile 2777). Probe: Projekt mit `test_aufgabe.py` wie oben, Ergebnis „1 Funde, blockiert=True“.

**Zu tun:** Testdateien bei der Prüfung vor Start und Export nicht blockieren lassen (höchstens Hinweis), sie gehören zum Test-Explorer. Erledigt, wenn ein Test ein solches Projekt startet und exportiert (subprocess gemockt).

## 647. Rückgängig nach weiterem Tippen verliert gesetzte Haltepunkte oder holt entfernte zurück

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Bezug: Punkt 625.

**Beobachtet:** Eingabetaste, dann Haltepunkt auf `d = 4`, dann noch einmal Eingabetaste, dann zweimal Strg+Z: nach dem zweiten ist der Haltepunkt weg. Umgekehrt: Haltepunkt vorhanden, Eingabetaste, Haltepunkt entfernen, Eingabetaste, zweimal Strg+Z: der entfernte Haltepunkt ist wieder da. Direkt nach dem Setzen oder Entfernen rückgängig gemacht stimmt es.

**Ursache:** nachgewiesen. `_schritt_mit_haltepunkten` (`ide/shell/quelltexteditor.py` Zeile 704) belegt `_vor_eigenen` beim ersten Rückgängig unter dem neuen Stand, liest es beim nächsten Schritt aber unter dem alten; eine eigene Änderung an einem früheren Stand wird nicht weitergetragen.

**Zu tun:** Von Hand gesetzte und entfernte Haltepunkte über alle folgenden Rückgängig-Schritte erhalten. Erledigt, wenn ein Test die beiden Abläufe oben durchspielt und die Haltepunkte so findet, wie sie zuletzt von Hand gesetzt waren.

## 648. Kürzel eines Klappmenüs wirken bei unsichtbaren und abgeschalteten Einträgen und fehlen bei abgeschaltetem Hauptmenü-Eintrag

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Bezug: Punkte 613, 621 und 623.

**Beobachtet:**
- Ein Klappmenü-Eintrag „Löschen“ mit „Entf“ und `visible: False` fehlt im Menü, Entf in der zugeordneten Liste ruft aber seine Methode auf. Ebenso ein Eintrag in einem Untermenü mit `enabled: False`. Im Hauptmenü wirken beide nicht, wie in der Komponenten-Referenz beschrieben.
- Trägt das Hauptmenü „Datensatz löschen“ mit „Entf“ und `enabled: False`, und das Klappmenü der Liste „Eintrag löschen“ mit „Entf“, tut Entf in der Liste gar nichts.

**Ursache:** nachgewiesen. `PopupMenu._menue_erneuern` (`pcl/components/menus.py` Zeilen 678-714) meldet jedes Blatt aus `_blaetter` an und übernimmt nur dessen eigenes `enabled`, weder `visible` noch den Zustand des Untermenüs. `_hauptmenue_kuerzel` (Zeile 767) zählt auch abgeschaltete und unsichtbare Einträge des Hauptmenüs als belegt. Probe: Formular mit ListBox und PopupMenu offscreen, Tasten über `QTest.keyClick`.

**Zu tun:** Kürzel unsichtbarer Einträge und von Einträgen unter abgeschalteten oder unsichtbaren Untermenüs nicht auslösen; als belegt nur bedienbare, sichtbare Hauptmenü-Einträge zählen und bei deren Änderung neu abgleichen. Erledigt, wenn ein Test die drei Fälle oben prüft.

## 649. Klassen-Code: gerichtete Assoziation „0..1“ wird ein Pflichtparameter

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Bezug: Punkt 619.

**Beobachtet:** Eine Klasse `Knoten` mit einer gerichteten Assoziation auf sich selbst, beschriftet „naechster 0..1“, ergibt `def __init__(self, inhalt: int, naechster: Knoten)`. `Knoten(5)` endet mit `TypeError … missing … 'naechster'`; der erste Knoten einer verketteten Liste lässt sich nur mit `None` von Hand anlegen. Die Vielfachheit 0..1 bedeutet „optional“.

**Ursache:** nachgewiesen. `ide/diagramm/klassen_code.py` (Zeile 55 `ATTRIBUTARTEN`, Erzeugung um Zeile 249) macht jede gerichtete Assoziation zu einem Pflichtparameter, ohne die Vielfachheit zu beachten.

**Zu tun:** Bei der Vielfachheit 0..1 (und 0..*/\*) einen Parameter mit Vorgabe `None` bzw. eine leere Liste erzeugen. Erledigt, wenn ein Test `Knoten(5)` aus dem erzeugten Code ohne Fehler anlegt.

## 650. Fehlermeldung einer Konsolen-Exe ist englisch und zeigt auf die Bibliothek

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Rückschritt aus Punkt 629 gegenüber Punkt 609.

**Beobachtet:** Der Konsolenhaken soll laut Kommentar einen Fehler „wie in Natter“ melden. Ohne `pcl` in der Exe steht dort „Was: ValueError: invalid literal for int() with base 10: 'abc'“ ohne „Zu prüfen“; Natter selbst meldet „Der Text „abc“ lässt sich nicht als ganze Zahl lesen“. Bei `random.choice([])` heißt es „Wo: random.py, Zeile 351“ statt der Zeile im Programm der Schülerin.

**Ursache:** nachgewiesen. `_KONSOLEN_HOOK` (`ide/export/exporter.py` ab Zeile 202) greift ohne `pcl` auf eine eigene Meldung zurück, die nichts übersetzt und die letzte Stelle des Tracebacks nimmt (`stellen[-1]`, Zeile 227). Probe: Haken mit normalem Python vor einem kleinen Konsolenprogramm ausgeführt.

**Zu tun:** Die Übersetzung der häufigen Fehler ohne Qt verfügbar machen (etwa ein Modul ohne PySide6-Import, das Haken und `pcl.fehleranzeige` teilen) und als Stelle die letzte im Projektordner nehmen. Erledigt, wenn ein Test den Haken mit `int("abc")` und `random.choice([])` laufen lässt und die deutsche Meldung mit der Zeile im Projekt findet.

## 651. Klick in den Zeilenrand einer Leerzeile entfernt den Haltepunkt der Zeile darunter

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Bezug: Punkt 611.

**Beobachtet:** Bei `a = 1`, Leerzeile, `b = 2` mit Haltepunkt auf `b = 2` löscht ein Klick links neben der Leerzeile (oder F9 dort) den Haltepunkt auf `b = 2`. An der angeklickten Zeile ist nichts zu sehen. Das Handbuch nennt für den Klick „Haltepunkt setzen oder entfernen“.

**Ursache:** nachgewiesen. `breakpoint_umschalten` (`ide/shell/quelltexteditor.py` Zeile 531) legt die Leerzeile auf die nächste Anweisung um und schaltet dort um.

**Zu tun:** Auf einer Leer- oder Kommentarzeile nur setzen, nie entfernen. Erledigt, wenn ein Test den Klick auf die Leerzeile macht und der Haltepunkt darunter bleibt.

## 652. Hinweis im Codefenster des Struktogramms: „1 Zeile … Sie stehen als Kommentar im Code“

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand 6c2a0da. Bezug: Punkt 617.

**Beobachtet:** Bei einer nicht übernommenen Zeile steht „1 Zeile konnte nicht übernommen werden. Sie stehen als Kommentar im Code.“ Die Mehrzahl passt nicht, und das großgeschriebene „Sie“ am Satzanfang liest sich wie eine Anrede.

**Ursache:** nachgewiesen. `ide/diagramm/fenster.py` Zeile 1095 hängt immer denselben Satz an.

**Zu tun:** Den Satz in die Meldung selbst nehmen und nach Anzahl formulieren, ohne „Sie“ („steht als Kommentar im Code“ / „stehen als Kommentar im Code“). Erledigt, wenn ein Test den Text für eine und für zwei Zeilen prüft.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
