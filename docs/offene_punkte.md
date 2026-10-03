# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **593**.

## Ein neuer Punkt

```markdown
## 593. Kurz, was nicht stimmt

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

## 567. Die Design-Prüfung bricht bei Farben wie „red“ oder „#abc“ ab

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** Der Objektinspektor nimmt für `color` jeden Farbnamen an, den Qt kennt („red“, „#abc“, „#80ff0000“). Nach der nächsten Änderung im Designer läuft die automatische Design-Prüfung und endet mit `ValueError: invalid literal for int() with base 16: 're'`; es erscheint die allgemeine Fehlermeldung, und die übrigen Beobachter von `jetzt_schreiben` laufen nicht mehr. „#80ff0000“ wird nicht abgelehnt, sondern als RGB `80ff00` gelesen. Probe offscreen mit `HauptFenster`, `color = "red"` über `eigenschaft_uebernehmen` und `jetzt_schreiben`: der Traceback führt über `_design_pruefen_automatisch` nach `ide/lint/regeln.py`.

**Ursache:** nachgewiesen. `_relative_luminanz` in `ide/lint/regeln.py` (Zeile 413) setzt sechsstelliges Hex voraus; aufgerufen wird die Prüfung ohne Schutz aus `ide/shell/hauptfenster.py` (um Zeile 7762, automatisch über 7163/7753, standardmäßig an).

**Zu tun:** Die Farbe über `QColor` auswerten (auch Namen, drei- und achtstelliges Hex). Erledigt, wenn ein Test mit „red“, „#abc“ und „#80ff0000“ eine Prüfung ohne Ausnahme und mit richtigem Kontrast bekommt.

## 568. Der PDF-Export eines Diagramms schneidet alles jenseits der Seite ohne Hinweis ab

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** Ein Struktogramm mit 61 Anweisungen ist 592 × 1770 Punkte groß, eine A4-Hochformatseite 794 × 1123. Das PDF hat eine Seite, das Bild reicht bis an die Unterkante, und etwa ab der 38. Anweisung fehlt alles. Eine Entscheidungstabelle mit 40 Regeln (2272 Punkte breit) wird auf A4 quer ebenso abgeschnitten. Der Druck desselben Diagramms verkleinert dagegen auf die Seite. Handbuch Abschnitt 3.4 nennt das PDF als Form für Arbeitsblatt und Abgabe.

**Ursache:** nachgewiesen. `als_pdf` in `ide/diagramm/export.py` (Zeilen 298–320) verschiebt nur um den Seitenrand und zeichnet in Originalgröße auf genau eine Seite; `auf_seite_zeichnen` (ab Zeile 323) für den Druck skaliert.

**Zu tun:** Wie beim Druck auf die Seite einpassen (oder auf mehrere Seiten verteilen) und das in der Statuszeile sagen. Erledigt, wenn ein Test mit einem überlangen Struktogramm ein PDF bekommt, in dem der letzte Block zu sehen ist.

## 569. Diagramm-Export und „Speichern unter …“ im Codefenster: Erfolg gemeldet, obwohl nichts geschrieben wurde, oder allgemeine Fehlermeldung

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** Export in einen Ordner, in den nicht geschrieben werden kann oder den es nicht gibt: bei SVG und PDF steht „Exportiert nach x.svg“ bzw. „x.pdf“ in der Statuszeile, die Datei existiert nicht. Bei PNG fliegt `OSError: PNG konnte nicht geschrieben werden` bis zur allgemeinen Meldung „In Natter ist etwas schiefgegangen“. Dasselbe gilt für „Quelltext → Erzeugen … → In eine Datei schreiben“ und „Speichern unter …“ im Codefenster mit einem Ziel ohne Schreibrecht (`PermissionError [WinError 5]`). Der Exportdialog schlägt den Ordner der `.pdiag` vor; in einem schreibgeschützten Austauschordner tritt der Fall also ohne Umweg ein.

**Ursache:** nachgewiesen. `ide/diagramm/fenster.py`, Export (Zeilen 1527–1533): `QPainter` auf `QSvgGenerator`/`QPdfWriter` (`export.py` Zeilen 268, 315) scheitert ohne Ausnahme, `isActive()` wird nicht geprüft, und der `OSError` aus `als_png` (`export.py` Zeile 201) wird nicht gefangen; `ide/diagramm/codefenster.py` Zeile 219 und `fenster.py` Zeile 1128 fangen den Schreibfehler ebenfalls nicht.

**Zu tun:** Schreiben prüfen (Painter aktiv, Datei danach vorhanden) und einen Schreibfehler wie beim Speichern der `.pdiag` als verständliche Meldung zeigen. Erledigt, wenn Tests für alle drei Exportformate und das Codefenster mit einem nicht beschreibbaren Ziel eine Meldung statt Erfolg oder Ausnahme bekommen.

## 570. Der Formular-Import überschreibt Bilder in `assets/` ohne Nachfrage

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** Zwei importierte `.lfm`-Formulare mit je einer Komponente `Image1` (der übliche Standardname) schreiben beide nach `assets/Image1.png`. Danach enthält die Datei nur noch das Bild des zweiten Formulars, und beide `.pfm` zeigen darauf. Ein vorhandenes eigenes `assets/Image1.png` wird ebenso ersetzt. Die Warnungen melden jeweils nur „geschrieben“.

**Ursache:** nachgewiesen. `_import_bilder_schreiben` in `ide/shell/hauptfenster.py` (um Zeile 8017) bildet den Dateinamen allein aus dem Komponentennamen und schreibt mit `write_bytes` ohne Prüfung.

**Zu tun:** Einen freien Namen wählen (etwa mit dem Formularnamen davor) und vorhandene Dateien nie überschreiben. Erledigt, wenn ein Test mit zwei Importen beide Bilder unverändert behält.

## 571. Löschen, Überschreiben und `pop` über `item_index` treffen ohne Auswahl still den letzten Eintrag

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563. Bezug: Punkt 475, der nur das Lesen abdeckt.

**Beobachtet:** ListBox mit „a“, „b“, „c“, nichts ausgewählt (`item_index` = -1). `items[item_index]` meldet richtig den Fehler aus Punkt 475, aber `del self.lb.items[self.lb.item_index]` löscht „c“, `items[item_index] = "X"` überschreibt den letzten Eintrag, und `items.pop(item_index)` entfernt ihn. Der übliche Knopf „Eintrag löschen“ verliert so ohne Auswahl Daten. `del items[10]` meldet englisch „IndexError list assignment index out of range“.

**Ursache:** nachgewiesen. `pcl/strings.py`: die Prüfung auf `auswahlliste` steht nur in `__getitem__` (Zeile 228), nicht in `__setitem__` (Zeile 255), `__delitem__` (Zeile 268) und `pop` (Zeile 118).

**Zu tun:** Dieselbe Prüfung und Meldung für Schreiben, Löschen und `pop`, dazu eine deutsche Meldung für einen Index außerhalb der Liste. Erledigt, wenn ein Test alle drei Wege ohne Auswahl ablehnt.

## 572. `Chart.load_csv` und `HtmlViewer.load_from_file` scheitern an Dateien in der Windows-Codepage

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** Eine CSV-Datei, die eine deutsche Tabellenkalkulation als „CSV (Trennzeichen-getrennt)“ speichert, ist in cp1252 geschrieben. `load_csv` endet damit in `UnicodeDecodeError: 'utf-8' codec can't decode byte 0xfc`, ebenso `HtmlViewer.load_from_file` mit einer Seite, die „Größe“ in cp1252 enthält. `Strings.load_from_file` weicht in diesem Fall auf cp1252 aus (`docs/komponenten.md`, Abschnitt items / lines).

**Ursache:** nachgewiesen. `pcl/components/chart.py` Zeile 354: `pd.read_csv` ohne Kodierung, gefangen werden nur `EmptyDataError` und `ParserError`; `pcl/components/medien.py` Zeile 69: `read_text(encoding="utf-8")`.

**Zu tun:** Wie `Strings.load_from_file` auf cp1252 ausweichen, sonst eine deutsche Meldung. Erledigt, wenn Tests mit cp1252-Dateien beide Methoden durchlaufen lassen.

## 573. Der Exe-Export lässt benutzte Bibliotheken weg, wenn ein Ordner über dem Projekt „build“, „dist“ oder „diagramme“ heißt

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** Ein Projekt mit `import pandas` und `from pcl import Chart` unter `D:\build\Statistik\`: `_ueberfluessige_pakete` schließt pandas, matplotlib und numpy aus (Probe: an gewöhnlichem Ort „False False False“, unter `build`, `dist` und `diagramme` jeweils „True True True“). Die Exe bricht beim Empfänger ab.

**Ursache:** nachgewiesen. `ide/export/exporter.py` Zeile 346 prüft `teil in _NICHT_MITNEHMEN for teil in datei.parts` auf dem absoluten Pfad statt relativ zum Projektordner.

**Zu tun:** Nur die Teile relativ zum Projektordner prüfen. Erledigt, wenn ein Test mit einem Projekt unter einem Ordner `build` dieselben Pakete behält wie an anderem Ort.

## 574. „Als Tabelle anzeigen“ im Debugger lässt bei großen Werten Zeilen aus der Mitte weg

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** Probe mit `DapClient` und echtem debugpy: eine Liste von 200 Dictionaries mit je zwei Texten zu 250 Zeichen. Die Antwort auf `evaluate` ist auf 65 540 Zeichen gekürzt; debugpy kürzt dabei in der Mitte. Der Rest ist zufällig weiter gültiges JSON: die Tabelle hat 127 Zeilen, nach Nummer 83 folgt 157, und Zeile 84 ist aus zwei Datensätzen zusammengesetzt. Das Fenster sagt „angezeigt werden die ersten 127“. Mit 20 Datensätzen stimmt alles.

**Ursache:** nachgewiesen. `tabellen_ausdruck` in `ide/debugger/tabellenansicht.py` liefert das ganze Ergebnis als einen Text über `evaluate` mit `context: "watch"` (`DapClient.auswerten`); `MAX_ZEILEN` (200) und `MAX_ZELLENTEXT` (300) begrenzen ihn nicht unter die Kürzungsgrenze von debugpy. Die Meldung steht in `ide/viewers/tabellen_ansicht.py` Zeile 89.

**Zu tun:** Das Ergebnis unter der Grenze halten (Zeilenzahl nach Textlänge begrenzen) oder einen Kontext ohne Kürzung verwenden, und eine gekürzte Antwort erkennen, statt sie zu lesen. Erledigt, wenn ein Test mit großen Werten nur zusammenhängende erste Zeilen und eine stimmende Meldung bekommt.

## 575. Eine `.py` in einem Unterordner verhindert den Start

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** Eine alte Fassung in `alt/versuch1.py` oder eine Hilfsdatei in `daten/hilfe.py` mit einem Syntaxfehler blockiert den Start, obwohl das Programm sie nicht benutzt und der Projekt-Explorer sie nicht zeigt. Die Meldung nennt nur „versuch1.py, Zeile 1: …“ ohne Unterordner; die Datei ist so nicht zu finden. Ein frisches Konsolenprojekt hat keine Funde, mit den beiden Dateien zwei blockierende.

**Ursache:** nachgewiesen. `ide/run/pruefung.py` Zeile 334 übergibt ruff `str(projekt.ordner)`, das rekursiv prüft; `Projekt.units()` sieht nur die oberste Ebene.

**Zu tun:** Nur die Dateien prüfen, aus denen das Programm besteht, oder Funde außerhalb davon nicht blockieren lassen; die Meldung nennt den Pfad relativ zum Projekt. Erledigt, wenn ein Test mit einer fehlerhaften Datei in einem Unterordner startet.

## 576. `Chart.load_csv` lässt eine x-Spalte mit Dezimalkomma als Text stehen

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** CSV `zeit;weg` mit Werten wie `0,5;1,2` bis `10,0;20,5`, `kind = "scatter"`: die x-Achse zeigt „0,5“, „1,0“, „1,5“, „2,0“, „10,0“ als Kategorien in gleichem Abstand, und `add_regression()` meldet „Die Werte für x müssen Zahlen sein. Gefunden wurde '0,5'“. Dieselben Daten über `load_grid` ergeben `y = 2,50·x - 1,92`. `docs/komponenten.md` (Chart) sagt, Dezimalkomma werde ohne Angabe erkannt. Ein Weg-Zeit-Versuch im Physik- oder Mathematikunterricht ist genau dieser Fall.

**Ursache:** nachgewiesen. `pcl/components/chart.py` Zeile 460: nur die y-Spalte läuft durch `_als_zahlen`, die x-Spalte bleibt roh.

**Zu tun:** Die x-Spalte wie die y-Spalte umwandeln, wenn sie aus Zahlen besteht. Erledigt, wenn ein Test mit Komma-Werten in x eine Regression bekommt.

## 577. Alt+Pfeil links verschiebt im Designer nicht, sondern springt „Zurück zur vorigen Stelle“

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** Probe offscreen mit `HauptFenster`, Kopie von 03_Taschenrechner, ein Button ausgewählt, `QTest.keyClick` mit Alt: Alt+Rechts verschiebt von (24, 160) auf (25, 160), Alt+Hoch auf (25, 159), Alt+Links ändert nichts; die Statuszeile meldet „Es gibt keine vorige Stelle, zu der es zurückginge.“ Handbuch Abschnitt 5 und die Tastenkürzel-Übersicht (`ide/shell/tastenkuerzel.py` Zeile 98) nennen „Alt+Pfeil: um genau einen Bildpunkt verschieben“ und zugleich Alt+Links für „Zurück“.

**Ursache:** nachgewiesen. Die Aktion `suchen.zurueck` mit `Alt+Left` (`ide/shell/hauptfenster.py` um Zeile 1617) ist ein Fensterkürzel und greift vor dem `KeyPress`, den `DesignerCanvas._tastatur_verarbeiten` (`ide/designer/canvas.py`, Alt-Zweig bei Zeile 1678) auswertet. Die Tests prüfen nur Alt+Rechts.

**Zu tun:** Im Designer die Pfeiltasten mit Alt vorrangig behandeln (`ShortcutOverride` annehmen) oder das Kürzel für „Zurück“ dort nicht wirken lassen. Erledigt, wenn ein Test alle vier Alt+Pfeile im Designer bei geöffnetem Hauptfenster prüft.

## 578. Die Menüleiste eines Schülerprogramms wächst nicht mit, wenn das Fenster größer gezogen wird

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563. Bezug: Punkt 39, dessen Behebung sagt, die Leiste wachse bei einer Größenänderung zur Laufzeit mit; das gilt nur für `self.width = …` im Code.

**Beobachtet:** Formular 400 breit mit `MainMenu`, gezeigt. Nach `resize(800, 500)` wie beim Ziehen am Rand ist das Fenster 800 breit, die Leiste weiter 400; maximiert ebenso. Im Beispiel 10_Notizbuch, dessen Memo mit `anchors` das Fenster füllt, endet die Menüleiste nach dem Maximieren mitten im Fenster, und weitere Einträge rutschen in den Überlaufknopf.

**Ursache:** nachgewiesen. `pcl/form.py`: nur `_groesse_anwenden` (Zeile 279) passt die Leiste an; `_fensterlage_uebernehmen` (Zeile 284), das nach einer Größenänderung durch den Benutzer läuft, übernimmt nur die Werte.

**Zu tun:** Die Breite der Leiste bei jeder Größenänderung des Fensters nachführen. Erledigt, wenn ein Test nach `resize` und nach dem Maximieren eine Leiste in Fensterbreite findet.

## 579. Aus „Eingabe: zahl“ im Struktogramm entsteht Code, der beim ersten Vergleich abbricht

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563. Bezug: Punkt 456.

**Beobachtet:** „Eingabe: zahl“ und danach die Verzweigung „zahl > 0?“ ergeben `zahl = input("zahl? ")` und `if zahl > 0:`. Ausgeführt: `TypeError: '>' not supported between instances of 'str' and 'int'`. Das ist das übliche Muster im Anfangsunterricht.

**Ursache:** nachgewiesen. `_ein_ausgabe_als_python` in `ide/diagramm/struktogramm_code.py` (Zeilen 589–592) erzeugt immer `input(...)` ohne Umwandlung.

**Zu tun:** Entscheiden, ob eine Umwandlung erzeugt wird (etwa `zahl(input(...))` aus `pcl` oder je nach Verwendung) oder ein Kommentar darauf hinweist. Erledigt, wenn das Beispiel oben lauffähigen Code oder einen sichtbaren Hinweis ergibt.

## 580. Nach Strg+Z auf Alt+Pfeil steht der Haltepunkt auf einer anderen Zeile

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** Probe offscreen mit `QuelltextEditor`: „a = 1“, „b = 2“, „c = 3“, Haltepunkt auf Zeile 1. Alt+Pfeil runter ergibt „b, a, c“ mit Haltepunkt auf Zeile 2 (richtig, auf „a = 1“). Strg+Z stellt „a, b, c“ wieder her, der Haltepunkt bleibt auf Zeile 2 und steht jetzt auf „b = 2“.

**Ursache:** nachgewiesen. `_ganzen_text_ersetzen` (`ide/shell/quelltexteditor.py` ab Zeile 1361) ordnet Haltepunkte nur beim Ausführen um. Rückgängig ersetzt den ganzen Text mit gleicher Zeilenzahl, und `_breakpoints_nachfuehren` (Zeile 448) tut bei Unterschied 0 nichts.

**Zu tun:** Haltepunkte (und Faltungen) beim Rückgängigmachen und Wiederholen mit zurückführen. Erledigt, wenn ein Test nach Alt+Pfeil, Strg+Z und Strg+Y den Haltepunkt jeweils auf derselben Anweisung findet.

## 581. Struktogramm-Code: Randfälle bei Zählschleife und Auswahl ergeben falschen Code

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** Proben mit `ide/diagramm/struktogramm_code.py`:
- „für i von 10 bis 1 schrittweite (-1)“ ergibt `range(10, 1 + 1, (-1))`, ausgeführt 10 bis 3; 2 und 1 fehlen.
- „Eingabe: n“ und „für i von 1 bis n“ ergeben `for _ in range(0):`, die Zeile gilt als nicht übernommen, obwohl die Beschriftung vollständig ist.
- Mehrfachauswahl mit Kopf `x` und Fällen „< 0“, „= 0“, „> 0“ ergibt `if x < 0` / `# = 0` / `elif False:` / `elif x > 0`; der Fall x == 0 geht verloren.
- Fälle „1“, „sonst“, „2“ ergeben `elif x == sonst:` (NameError beim Lauf, nicht als „nicht übernommen“ gezählt); ein letzter Fall „else“ ergibt `elif False:`.

**Ursache:** nachgewiesen. Zeile 796 (`abwaerts = schritt.startswith("-")` erkennt `(-1)` nicht), Zeile 764 (Grenze aus einer Variablen), Zeile 46 (`_VERGLEICHSANFAENGE` ohne einzelnes `=`), Zeilen 563–572 und 721–725 (Sonst-Fall nur als letzter und nur als „sonst“, `bloecke.py` Zeile 28).

**Zu tun:** Die vier Fälle richtig übersetzen oder als nicht übernommen melden. Erledigt, wenn je ein Test die Fälle oben ausführt und das erwartete Verhalten prüft.

## 582. Klassen-Code: ein Kommentar mit `"""` am Ende und ein Vererbungskreis ergeben ungültigen Code ohne Meldung

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** `_docstring('Sagt """', 1)` ergibt `"""Sagt \"\"\\""""` und damit `SyntaxError: unterminated string literal`. Zwei Klassen, die voneinander erben, ergeben `class B(A)` vor `class A`; der Code endet mit `NameError`, und `ungueltige_namen` meldet nichts. Zwei Klassen gleichen Namens überschreiben sich still.

**Ursache:** nachgewiesen. `ide/diagramm/klassen_code.py` Zeilen 105–108: die Prüfung `endswith('"')` greift nach dem Maskieren und verdoppelt den Rückstrich. Kreise und doppelte Namen prüft `ungueltige_namen` nicht; `canvas.py` Zeile 427 lehnt nur die Selbstvererbung ab.

**Zu tun:** Das Maskieren berichtigen und Kreise sowie doppelte Klassennamen vor dem Erzeugen melden. Erledigt, wenn Tests für alle drei Fälle übersetzbaren Code oder eine Meldung bekommen.

## 583. `RadioGroup.item_index` aus dem Code löst kein `on_change` aus

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** `rg.item_index = 1` ruft `on_change` nicht auf, ebenso wenig, wenn kürzere `items` den Index auf -1 setzen. `docs/komponenten.md` (RadioGroup, Zeile 809) nennt „Wechsel der Auswahl (Klick oder Code)“. CheckBox `checked`, ScrollBar `position` und ListBox `item_index` lösen im selben Fall aus.

**Ursache:** nachgewiesen. `pcl/components/standard.py` Zeilen 962–990: `_auswahl_anwenden` setzt `_baut_auf = True`, und `_bei_prop_aenderung` ruft `on_change` nie auf.

**Zu tun:** Bei einer Änderung aus dem Code wie bei den übrigen Komponenten `on_change` auslösen. Erledigt, wenn ein Test beide Wege prüft.

## 584. ComboBox: nach dem Kürzen von `items` steht die Auswahl auf dem ersten Eintrag statt auf -1

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** `cb.item_index = 2`, dann `cb.items = ["a"]` ergibt `item_index` 0 mit Text „a“ und einem `on_change`. Die ListBox steht im gleichen Fall auf -1, und `docs/komponenten.md` (ComboBox) sagt „Wie bei der ListBox bleibt die Auswahl stehen“.

**Ursache:** nachgewiesen. `pcl/components/standard.py` Zeile 633 setzt den alten Index nur, wenn es ihn noch gibt; sonst wählt Qt nach `addItems` selbst Eintrag 0.

**Zu tun:** Eine nicht mehr vorhandene Auswahl auf -1 setzen. Erledigt, wenn ein Test ComboBox und ListBox gleich behandelt.

## 585. `sys.exit("Text")` verschluckt im Konsolenprojekt die Meldung

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** `python main.py` mit `sys.exit("Ungültige Eingabe - Abbruch")` gibt den Text aus und endet mit 1. In Natter erscheint der Text nicht, das Programm endet mit 0, und das Fenster zeigt nur „Programm beendet …“.

**Ursache:** nachgewiesen. `_KONSOLEN_HUELLE` in `ide/run/starter.py` (Zeile 74) macht aus einem Nicht-Zahl-Code still 0.

**Zu tun:** Wie Python selbst den Text auf die Fehlerausgabe schreiben und mit 1 enden. Erledigt, wenn ein Test Ausgabe und Rückgabewert mit und ohne Hülle vergleicht.

## 586. Das Quelltext-PDF wandert mit dem nächsten Exe-Export in die Exe

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** „Projekt → Quelltext als PDF …“ schlägt `<Projektordner>/<Name> Quelltext.pdf` vor. Der nächste Exe-Export nimmt die Datei als Programmdaten mit (`_daten_dateien_des_projekts` liefert `['Statistik Quelltext.pdf']`), und die Exe legt sie beim ersten Start neben sich ab, beim Empfänger also den ganzen Quelltext.

**Ursache:** nachgewiesen. `_KEINE_DATEN` in `ide/export/exporter.py` (Zeile 197) schließt `.pdf` und `.zip` nicht aus; Vorschlag in `ide/shell/hauptfenster.py` um Zeile 2682.

**Zu tun:** Abgabe-Unterlagen (Quelltext-PDF, Abgabe-ZIP) beim Export auslassen oder sie nicht im Projektordner vorschlagen. Erledigt, wenn ein Test nach „Quelltext als PDF“ am vorgeschlagenen Ort keine PDF unter den Exportdaten findet.

## 587. `modul_verdeckt` meldet Datenordner von Natter als Python-Module und kann ein Modul ausführen

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563. Bezug: Punkt 536.

**Beobachtet:** Eine Unit `design.py` oder `docs.py` bekommt den Hinweis, sie heiße wie ein Python-Modul, und Umbenennen dorthin wird abgelehnt; `find_spec` findet im Prozess der IDE `design`, `templates`, `schemas`, `beispielprojekte`, `docs`, `ide` und `tools` als Namespace-Pakete (belegt im Entwicklungsbaum). Ein Dateiname mit Punkt wie `this.x.py` lässt `find_spec("this.x")` das Elternmodul importieren und ausführen: die Probe druckt den „Zen of Python“. Für die gebaute Fassung vermutet dasselbe, weil der Installationsordner im Suchpfad steht.

**Ursache:** nachgewiesen. `ide/run/pruefung.py` Zeilen 459–472 fragt `importlib.util.find_spec` im eigenen Prozess.

**Zu tun:** Nur gegen die Standardbibliothek und installierte Pakete prüfen, ohne zu importieren und ohne die Ordner der IDE. Erledigt, wenn Tests für `design.py` keinen Hinweis und für `this.x.py` keine Ausführung zeigen.

## 588. Im Menü-Editor lässt sich „Ankreuzbar“ bei einem angekreuzten Eintrag nicht abwählen

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** Eintrag „Raster“ mit `checkable` und `checked`. „Ankreuzbar“ abwählen, einen anderen Eintrag wählen und zurück: „Ankreuzbar“ ist wieder angehakt. Nach „Anwenden“ ist der Eintrag im Programm weiter ankreuzbar. „Angekreuzt“ bleibt bedienbar, auch wenn „Ankreuzbar“ aus ist.

**Ursache:** nachgewiesen. `ide/inspector/menue_editor.py` Zeilen 451–453 zeigen `checkable or checked`; `pcl/components/menus.py` Zeile 489 macht jeden Eintrag mit `checked` ankreuzbar.

**Zu tun:** Beim Abwählen von „Ankreuzbar“ auch „Angekreuzt“ zurücksetzen und ausgrauen. Erledigt, wenn ein Test den Weg oben durchgeht und einen nicht ankreuzbaren Eintrag bekommt.

## 589. `HtmlViewer.load_from_file`: Bilder mit relativem Pfad gelten ab dem Arbeitsordner, nicht ab der Seite

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** `bericht/seite.html` mit `<img src="b.png">`, das Bild liegt daneben. Aus einem anderen Arbeitsordner geladen fehlt das Bild, im Ordner der Seite erscheint es.

**Ursache:** nachgewiesen. `pcl/components/medien.py` Zeile 69 ruft `setHtml` ohne Suchpfad oder Basisadresse.

**Zu tun:** Den Ordner der Datei als Bezug setzen. Erledigt, wenn ein Test das Bild unabhängig vom Arbeitsordner findet.

## 590. Rückgängig nach einem Stilwechsel im Diagramm-Editor lässt das Häkchen auf dem neuen Stil

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** Stil auf „black-white“ wechseln, dann Strg+Z: der Stil ist wieder „modern-light“, angehakt bleibt „black-white“.

**Ursache:** nachgewiesen. `ide/diagramm/fenster.py` Zeilen 1191–1201: nur das Ausführen setzt `stil_aktionen[...].setChecked`.

**Zu tun:** Das Häkchen nach Rückgängig und Wiederholen aus dem Stand des Diagramms setzen. Erledigt, wenn ein Test es nach Strg+Z prüft.

## 591. Tastenkürzel in einem PopupMenu wirken nie

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:** Ein Eintrag eines `PopupMenu` mit `shortcut` „Entf“ zeigt das Kürzel im aufgeklappten Menü, die Taste löst aber nichts aus, solange das Menü nicht offen ist. `docs/komponenten.md` beschreibt die Einträge „aufgebaut wie bei MainMenu“, wo das Kürzel im ganzen Fenster wirkt.

**Ursache:** nachgewiesen. `PopupMenu.menue()` (`pcl/components/menus.py` Zeilen 560–567) baut die `QAction`s erst beim Aufklappen in `aufklappen`; vorher gibt es keine Aktion, die das Kürzel trägt.

**Zu tun:** Entscheiden: die Kürzel an der zugeordneten Komponente anmelden oder in Menü-Editor und Referenz sagen, dass sie im Klappmenü nur angezeigt werden. Erledigt, wenn Verhalten und Referenz übereinstimmen und ein Test es festhält.

## 592. Kleinere Abweichungen in `pcl`: MaskEdit, leeres Kreisdiagramm, Tausenderpunkte, Achsenabschnitt

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand c3d9563.

**Beobachtet:**
- `MaskEdit` mit Maske `00.00.0000` liefert leer `text == ".."` statt `""` (Standardwert laut Referenz); `if self.me_datum.text == ""` greift nie.
- `Chart.add_pie_series([], [])` endet englisch mit „ValueError: All wedge sizes are zero“.
- `Chart.load_csv` mit `1.200,50` meldet „enthält nicht nur Zahlen“.
- `docs/komponenten.md` (Zeile 1492) beschreibt `achsenabschnitt` als Wert bei x = 0; bei logarithmischer Regression ist es der Wert bei x = 1.

**Ursache:** nachgewiesen. `_text_gleichziehen` in `pcl/components/eingaben.py`; `pcl/components/chart.py` Zeile 277 und `_als_zahlen` (ab Zeile 110, ersetzt nur das Komma); `_logarithmisch` in `pcl/analyse.py`.

**Zu tun:** Leeres MaskEdit als `""` liefern, leeres Kreisdiagramm mit deutscher Meldung, Tausenderpunkte wie `pcl.zahlen.zahl` lesen, die Referenz zum Achsenabschnitt berichtigen. Erledigt, wenn je ein Test die Fälle festhält.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
