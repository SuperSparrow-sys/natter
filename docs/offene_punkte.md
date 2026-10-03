# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **637**.

## Ein neuer Punkt

```markdown
## 637. Kurz, was nicht stimmt

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

## 622. Struktogramm-Code: Zahlenraten vergleicht die Eingabe als Text mit einer Zahl und endet nie

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d. Bezug:
Punkt 601, der nur den Vergleich mit einer Zahl im Text abdeckt.

**Beobachtet:** Das Struktogramm „geheim ← 42“, „Eingabe: tipp“,
„solange tipp != geheim“ ergibt `tipp = input("tipp? ")` und
`while tipp != geheim:`. Bei der Eingabe 42 läuft die Schleife weiter
und gibt „falsch“ aus, ohne Ende. Ebenso „geheim ← 7“, „Eingabe:
tipp“, Verzweigung „tipp == geheim?“: bei der Eingabe 7 erscheint
„falsch“. Nichts davon erscheint als „nicht übernommen“. Das
Zahlenraten ist eine der üblichsten Aufgaben zu Schleifen;
`docs/handbuch.md` (Abschnitt zum Struktogramm-Code) verspricht, dass
eine Eingabe dort zur Zahl wird, wo sie wie eine Zahl benutzt wird.

**Ursache:** nachgewiesen. `_als_zahl_benutzt`
(`ide/diagramm/struktogramm_code.py` Zeilen 884-910) wertet `==`,
`!=` und `=` nur als Zahlvergleich, wenn danach eine Ziffer steht
(`{vergleich}\s*-?\d`); ein Vergleich mit einem Namen, dem eine Zahl
zugewiesen ist, zählt nicht. Probe: `sg2.py` im Ordner der
Durchsicht, Fall „raten“.

**Zu tun:** Ein Name, der mit `==`, `!=` oder `=` mit einem Namen
verglichen wird, der als Zahl gilt (Zahl-Literal zugewiesen oder
selbst als Zahl erkannt), gilt ebenfalls als Zahl; das so lange
wiederholen, bis sich nichts mehr ändert. Erledigt, wenn ein Test
beide Fälle oben ausführt und bei der richtigen Eingabe „richtig“
erhält.

## 623. Gleiches Kürzel in zwei Klappmenüs löst das Menü der anderen Komponente aus

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d. Bezug:
Punkt 613, dessen Behebung dieses Verhalten erst herbeiführt.

**Beobachtet:** Zwei ListBoxen `lb_a` und `lb_b` mit je eigenem
Klappmenü `pm_a` und `pm_b`, beide mit einem Eintrag „Löschen“ auf
`Entf`, je mit eigener Methode. Der Fokus liegt in `lb_b`, Entf wird
gedrückt: aufgerufen wird die Methode von `pm_a`, gelöscht wird in
`lb_a`, und `popup_component` ist dabei `None`. Vor Punkt 613 tat die
Taste gar nichts; jetzt löscht sie in der falschen Liste.
`docs/komponenten.md` sagt nur, eine Taste löse „immer genau einen
Eintrag“ aus.

**Ursache:** nachgewiesen. `PopupMenu._menue_erneuern`
(`pcl/components/menus.py` Zeilen 657-671) überspringt ein Kürzel,
das schon ein anderes Klappmenü trägt (`_belegte_kuerzel`, Zeile
726), unabhängig davon, welche Komponente den Fokus hat; das zuerst
angemeldete gilt als `WindowShortcut` im ganzen Fenster. Probe:
`m1.py`, Ausgabe „Fokus lb_b, Entf -> [('a', None)]“.

**Zu tun:** Ein Kürzel, das mehrere Klappmenüs tragen, nur einmal
anmelden und beim Auslösen an das Klappmenü der Komponente mit dem
Fokus weitergeben; hat keine zugeordnete Komponente den Fokus, gilt
das Hauptmenü oder nichts. Erledigt, wenn ein Test mit Fokus in
`lb_b` die Methode von `pm_b` aufruft.

## 624. `popup_component` behält nach einem Tastenkürzel die Komponente des letzten Rechtsklicks

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d. Bezug:
Punkt 620.

**Beobachtet:** Das Klappmenü an `lb_a` wird einmal per Rechtsklick
geöffnet und geschlossen. Danach liegt der Fokus auf einem Button,
und Entf wird gedrückt. Das Beispiel aus `docs/komponenten.md`
(„gemeinsames Löschen“ für zwei Listen) löscht daraufhin den gewählten
Eintrag aus `lb_a`. Laut derselben Stelle gilt beim Kürzel die
Komponente mit dem Fokus, wenn ihr das Klappmenü zugeordnet ist; hier
ist das keine, zu erwarten wäre `None` und damit kein Löschen.

**Ursache:** nachgewiesen. `_kuerzel_ausloesen`
(`pcl/components/menus.py` Zeilen 673-676) setzt `_aufgeklappt_an`
nur, wenn `_komponente_mit_fokus()` etwas findet; sonst bleibt der
Wert vom letzten Aufklappen stehen. Probe: `m2.py`, Ausgabe „lb_a
nach Entf auf dem Knopf: ['y']“, vorher `['x', 'y']`.

**Zu tun:** Beim Kürzel `_aufgeklappt_an` immer auf das Ergebnis von
`_komponente_mit_fokus()` setzen, auch auf `None`. Erledigt, wenn ein
Test mit dem Fokus außerhalb der Listen `popup_component is None`
prüft.

## 625. Rückgängig nimmt Haltepunkte und Bedingungen zurück, die nach dem letzten Tippen gesetzt wurden

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d. Bezug:
Punkt 596, dessen Behebung den ganzen Stand der Haltepunkte je
Rückgängig-Schritt wiederherstellt.

**Beobachtet:** Probe mit `QuelltextEditor` offscreen:
- Ein Zeichen in Zeile 1 tippen, dann einen Haltepunkt auf Zeile 4
  setzen, dann Strg+Z: der Text ist zurück, der Haltepunkt ist weg.
- Umgekehrt kommt ein Haltepunkt, der nach dem Tippen entfernt wurde,
  mit Strg+Z wieder.
- Eine nach dem Tippen gesetzte Bedingung (`d > 3`) verschwindet mit
  Strg+Z.

Wer beim Debuggen einen Tippfehler zurücknimmt, verliert so die
gerade gesetzten Haltepunkte; während einer Sitzung geht der alte
Stand über `breakpoints_geaendert` sofort an debugpy.

**Ursache:** nachgewiesen. Der Stand der Haltepunkte wird nur bei
Textänderungen gemerkt (`_breakpoints_nachfuehren`,
`ide/shell/quelltexteditor.py` ab Zeile 538), und
`_schritt_mit_haltepunkten` (ab Zeile 655) setzt beim Rückgängig
diesen gemerkten Stand vollständig ein. `breakpoint_umschalten` (Zeile
488) und `bedingung_setzen` (Zeile 586) ändern die gemerkten Stände
nicht. Probe: `hp1.py`, Ausgaben „1 vor undo [4] / 1 nach undo []“,
„2 vor undo [] / 2 nach undo [4]“, „6 vor {4: 'd > 3'} / 6 undo {}“.

**Zu tun:** Beim Rückgängig nur die Zeilenwanderung des Textschritts
umkehren, oder Setzen, Entfernen und Bedingungen in alle gemerkten
Stände übertragen. Erledigt, wenn ein Test nach Tippen, Haltepunkt
setzen und Strg+Z den Haltepunkt noch findet und die Tests aus Punkt
596 grün bleiben.

## 626. Struktogramm-Code: eine Fallauswahl mit Fällen wie „< 0“ lässt die Eingabe Text, der Lauf bricht ab

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d. Bezug:
Punkt 601.

**Beobachtet:** „Eingabe: x“ und eine Fallauswahl mit dem Kopf „x“
und den Fällen „< 0“ und „sonst“ ergeben `x = input("x? ")` und
`if x < 0:`. Beim Lauf: „TypeError: '<' not supported between
instances of 'str' and 'int'“. Ein Fall „= 0“ wird zu `x == 0` und
gilt bei Text nie. Dieselbe Logik mit den Bedingungen im Fall („x <
0“, „x = 0“) läuft richtig.

**Ursache:** nachgewiesen. `_als_zahl_benutzt`
(`ide/diagramm/struktogramm_code.py` Zeilen 884-910) sucht Name und
Vergleich im selben Text; Kopf und Fallbeschriftung stehen aber in
verschiedenen Feldern. `_fallauswahl_mit_zahlen` (Zeilen 913-933)
erkennt nur Fälle, die reine Zahlen sind, obwohl die Codeerzeugung
Beschriftungen mit Vergleich ausdrücklich unterstützt. Probe:
`sg2.py`, Fall „fallauswahl vergleich“.

**Zu tun:** Ein Fall, der mit einem Vergleich gegen eine Zahl beginnt
(`<`, `>`, `<=`, `>=`, `=`, `==`, `!=`), macht den Namen im Kopf zur
Zahl. Erledigt, wenn ein Test mit der Eingabe „-3“ den Zweig „< 0“
ausführt.

## 627. Struktogramm-Code: „wiederhole bis betrag > 0“ macht die Eingabe zur ganzen Zahl, „2,5“ bricht ab

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d.

**Beobachtet:** Eine Fußschleife „wiederhole bis betrag > 0“ mit
„Eingabe: betrag“ im Rumpf ergibt `betrag = int(input(...))`. Die
Eingabe „2,5“ endet mit „ValueError: invalid literal for int()“.
Dieselbe Logik als Kopfschleife „solange betrag <= 0“ ergibt
`float(input(...).replace(",", "."))` und läuft. `docs/handbuch.md`
verspricht, dass eine Zahl „auch mit Komma eingetippt“ werden kann.

**Ursache:** nachgewiesen. `_als_ganzzahl_benutzt`
(`ide/diagramm/struktogramm_code.py` Zeilen 865-881) sucht mit
`\b(?:von|bis|schrittweite|range\()\s*{name}\b` in allen Texten des
Diagramms; das trifft auch das Wort „bis“ einer Fußschleife, nicht
nur die Grenze einer Zählschleife. Probe: `sg3.py`, Fall „bis-fuss
mit kommazahl“.

**Zu tun:** Ganzzahlige Namen nur aus den Köpfen von Zählschleifen und
aus `range(` sammeln. Erledigt, wenn ein Test die Fußschleife oben mit
„2,5“ ausführt.

## 628. `Chart.add_boxplot_series` prüft seine Werte nicht, die Referenz sagt es aber zu

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d. Bezug:
Punkt 598, der die Boxplot-Werte bewusst ungeprüft ließ.

**Beobachtet:** `add_boxplot_series(["1,5", "2", "3"])`, also Werte
aus einem Edit, endet mit einem englischen numpy-Fehler („the resolved
dtypes are not compatible with add.reduce“);
`add_boxplot_series([1, None, 3])` endet mit „TypeError: unsupported
operand type(s) for +: 'int' and 'NoneType'“. `docs/komponenten.md`
(Abschnitt Chart) zählt `add_boxplot_series` zu den Methoden, die
Text wie mit `zahl()` lesen und `None` mit einer Meldung ablehnen.

**Ursache:** nachgewiesen. `add_boxplot_series`
(`pcl/components/chart.py` ab Zeile 444) ruft `_zahlenliste` nicht
auf, die übrigen `add_*`-Methoden schon. Probe: `c1.py`, Zeilen
„boxplot text“ und „boxplot None“.

**Zu tun:** Die Werte durch `_zahlenliste` schicken wie bei den
anderen Reihen. Erledigt, wenn ein Test beide Fälle oben prüft.

## 629. Jede exportierte Konsolen-Exe enthält PySide6 und pcl

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d. Bezug:
Punkt 609, der den Konsolenhaken eingeführt hat.

**Beobachtet:** Der Export von „01 Begrüßung“ (nur `print` und
`input`, kein `pcl`) ergibt eine Exe von 27,4 MB; im Bauordner nennt
`PKG-00.toc` 32 Einträge für PySide6 (Qt6Core, Qt6Gui, Qt6Widgets,
Qt6Multimedia, Qt6Network), `PYZ-00.toc` die Module von `pcl`. Der
Bau dauert entsprechend länger, und die Exe packt als Einzeldatei
bei jedem Start alles aus. Der Kopf von `ide/export/exporter.py`
verspricht: „Mitgenommen wird nur, was das Projekt wirklich braucht“.

**Ursache:** nachgewiesen. `_KONSOLEN_HOOK` (`ide/export/exporter.py`
Zeile 201) enthält `from pcl.fehleranzeige import fehlertext`.
PyInstaller verfolgt die Importe von Laufzeithaken, und
`pcl/__init__.py` lädt `pcl.application` und damit PySide6. PySide6
steht nicht unter den optionalen Paketen, die
`_ueberfluessige_pakete` ausschließt.

**Zu tun:** Im Haken `pcl` nur nutzen, wenn das Programm es schon
geladen hat (`"pcl" in sys.modules`, dann über
`importlib.import_module`), sonst die vorhandene deutsche
Ersatzmeldung; oder die Meldung ohne `pcl` erzeugen. Erledigt, wenn
die Exe eines Konsolenprojekts ohne `pcl`-Import weder PySide6 noch
`pcl` enthält (prüfbar an `Analysis-00.toc`).

## 630. Klassendiagramm: eine „Anfrage“ ohne Parameter wird zur Eigenschaft, der Aufruf mit Klammern scheitert

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d.

**Beobachtet:** Die Operation `getStand(): float` mit dem Haken
„Anfrage“ (`ide/diagramm/klassendialog.py` Zeile 359) ergibt
`@property` über `def getStand(self)`. Das Diagramm zeigt
„+getStand(): float“, also mit Klammern, und so rufen Schülerinnen
sie auch auf: `k.getStand()` endet mit „TypeError: 'NoneType' object
is not callable“ (sobald der Rumpf geschrieben ist, mit „'float'
object is not callable“). Weder der Dialog noch `docs/handbuch.md`
sagen, dass eine Anfrage ohne Klammern benutzt wird.

**Ursache:** nachgewiesen. `ide/diagramm/klassen_code.py` Zeilen
563-568 („Anfrage ohne Parameter ist im Python-Sinn eine
Eigenschaft“).

**Zu tun:** Eine gewöhnliche Methode erzeugen, oder im Dialog (Tooltip
am Haken) und im Handbuch erklären, dass auf eine Anfrage ohne
Klammern zugegriffen wird. Erledigt, wenn Diagramm, Hilfe und
erzeugter Code dasselbe sagen.

## 631. „Ausführen bis Cursor“ auf einer Leer- oder Kommentarzeile hält eine Anweisung zu früh

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d. Bezug:
Punkte 611 und 621, die das für Haltepunkte behoben haben.

**Beobachtet:** In

```python
for i in range(3):
    a = i

    # rechnen
    b = a * 2
```

hält das Programm in Zeile 1, der Cursor steht auf der Leerzeile 3.
Nach „Ausführen bis Cursor“ hält es in Zeile 2, bevor `a = i` läuft;
erwartet war Zeile 5. Ist der Text während des Halts ungespeichert
geändert, geht außerdem die Zeilennummer des Editors statt der Zeile
der geladenen Datei an debugpy.

**Ursache:** nachgewiesen. `ide/shell/hauptfenster.py` Zeile 10024
nimmt `editor.textCursor().blockNumber() + 1` ohne `anweisungszeile()`
und ohne die Umrechnung aus `_haltepunkte_zur_datei` und gibt sie an
`debug_sitzung.bis_cursor` bzw. `_mit_debugger_starten(halten_bei=…)`
weiter. Probe: `dap3.py`, „angehalten in zeile 2“; debugpy antwortet
auf die angefragte Zeile 3 mit `'line': 2`.

**Zu tun:** Die Zielzeile wie bei Haltepunkten über
`anweisungszeile()` auf die nächste Anweisung legen und bei
geändertem Text auf die Zeile der Datei abbilden. Erledigt, wenn ein
Test mit dem Beispiel oben in Zeile 5 hält.

## 632. Debugger: „Als Tabelle anzeigen“ unter „Globale Variablen“ zeigt eine gleichnamige lokale Variable

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d. Bezug:
Punkt 612.

**Beobachtet:** Eine globale Liste `werte = [[1, 2], [3, 4]]` und
eine Funktion `def f(werte)`, angehalten in `f(5)`. „Als Tabelle
anzeigen“ an `werte` unter „Globale Variablen“ wertet den Parameter
aus (`5`) und meldet, der Wert lasse sich nicht als Tabelle anzeigen;
aufgeklappte Kinder wie `werte[0]` ebenso. Ein Parameter mit dem
Namen einer globalen Liste ist in Schulprogrammen häufig.

**Ursache:** nachgewiesen. debugpy liefert für Einträge der Gruppe
„Globals“ als `evaluateName` nur den Namen; `ide/shell/hauptfenster.py`
Zeile 9529 übernimmt ihn, und die Auswertung läuft im aktuellen Frame.
Probe: `dap2.py`, „Globals werte [[1, 2], [3, 4]] evaluateName= werte
/ evaluate -> 5“.

**Zu tun:** Einträge unter „Globale Variablen“ über den globalen
Namensraum auswerten, etwa `globals()['werte']`. Erledigt, wenn ein
Test mit überdecktem Namen die globale Liste als Tabelle zeigt.

## 633. Zwei Einträge im Hauptmenü mit demselben Kürzel: keiner wirkt, ohne Hinweis (gering)

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d. Bezug:
Punkt 613, der nur Hauptmenü gegen Klappmenü abdeckt.

**Beobachtet:** Zwei Einträge desselben `MainMenu` tragen „Strg+K“.
Beim Drücken wird keine der beiden Methoden aufgerufen; Qt hält das
Kürzel für mehrdeutig. Weder der Menü-Editor noch `eintraege_pruefen`
melden etwas. `docs/komponenten.md` verspricht, eine Taste löse
„immer genau einen Eintrag“ aus.

**Ursache:** nachgewiesen. `pcl/components/menus.py`: `_aktion_bauen`
setzt jedes Kürzel ohne Abgleich, `eintraege_pruefen` (ab Zeile 239)
sucht nicht nach doppelten Kürzeln; `ide/inspector/menue_editor.py`
zeigt nur `kuerzel_fehler` an. Probe: `m1.py`, „doppelt im
Hauptmenue: []“.

**Zu tun:** Doppelte Kürzel im selben Menü im Menü-Editor anzeigen und
beim Zuweisen deutsch ablehnen, oder nur das erste anmelden. Erledigt,
wenn ein Test den Fall oben prüft.

## 634. Chart: Jahreszahlen als Text bekommen Teilstriche wie „2019,75“ (gering)

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d. Bezug:
Punkt 598, seit dem Text in Zahlen umgewandelt wird.

**Beobachtet:** `add_line_series(["2020", "2021", "2022"], ["1,5",
"2", "3"])`, etwa aus einem StringGrid, beschriftet die x-Achse mit
„2019,75 2020,00 2020,25 …“. Bis 0.4.3 standen dort die drei Jahre.

**Ursache:** nachgewiesen. `_zahlen_wenn_moeglich`
(`pcl/components/chart.py` ab Zeile 171) macht aus den Texten Zahlen;
die Achse bekommt danach die üblichen Bruchteil-Teilstriche. Probe:
`c1.py`, Zeile „Jahre als Text“.

**Zu tun:** Sind alle x-Werte ganze Zahlen, nur ganzzahlige
Teilstriche zeigen (etwa `MaxNLocator(integer=True)`). Erledigt, wenn
ein Test bei den Jahren oben nur ganze Zahlen an der Achse findet.

## 635. `Chart.add_regression(x, y)` lehnt Text mit Dezimalkomma ab, den die Punktwolke annimmt (gering)

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d.

**Beobachtet:** `add_scatter_series(xs, ys)` mit `ys = ["1,5", "2,5",
"3,5"]` zeichnet. `add_regression(xs, ys)` mit denselben Listen
meldet „Die Werte für y müssen Zahlen sein. Gefunden wurde '1,5'.“
Ohne Argumente geht es, weil dann die schon umgewandelten Punkte der
Wolke dienen.

**Ursache:** nachgewiesen. `_regressionsdaten`
(`pcl/components/chart.py` ab Zeile 679) reicht übergebene `x` und `y`
ohne `_zahlenliste` an `pcl.analyse.regression` weiter. Probe:
`c1.py`, Zeile „regression text“.

**Zu tun:** `x` und `y` in `_regressionsdaten` durch `_zahlenliste`
schicken. Erledigt, wenn ein Test den Fall oben prüft.

## 636. Struktogramm-Code: ein Kommentar mit „#“ in einer Bedingung ergibt ungültigen Code ohne Meldung (gering)

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 1fbcb2d.

**Beobachtet:** Die Bedingung „x > 0 # positiv“ ergibt
`if x > 0 # positiv:`; der Doppelpunkt steht im Kommentar, Python
meldet „expected ':'“. Ebenso in Kopf- und Fußschleife und in einer
Fallbeschriftung („1 # eins“). `nicht_uebernommen` bleibt leer, das
Fenster meldet nichts, obwohl der Kopf des Moduls „immer gültiges
Python“ verspricht.

**Ursache:** nachgewiesen. `_ist_ausdruck`
(`ide/diagramm/struktogramm_code.py` ab Zeile 1041) prüft mit
`ast.parse(mode="eval")`, das den Kommentar übergeht; die Köpfe werden
als `f"... {kopf}:"` zusammengesetzt, und `uebersetzbar_machen` (ab
Zeile 222) korrigiert keine Kopfzeilen. Probe: `sg1.py`, vier Fälle
„kommentar in …“.

**Zu tun:** Köpfe vor dem Einsetzen über `ast.unparse` normalisieren
oder den Kommentar abtrennen und hinter den Doppelpunkt stellen.
Erledigt, wenn ein Test die vier Fälle übersetzt.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
