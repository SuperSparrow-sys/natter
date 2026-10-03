# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **622**.

## Ein neuer Punkt

```markdown
## 622. Kurz, was nicht stimmt

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

## 593. Ein Hauptmenü oder Klappmenü auf einem Panel oder einer GroupBox: das Programm startet nicht

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:** Liegt ein `MainMenu` oder `PopupMenu` auf einem Behälter statt auf dem Formular, bricht das Programm beim Zuweisen der Einträge ab: „Der Menüeintrag „X“ soll beim Anklicken die Methode 'mi_x' aufrufen, aber Panel hat keine Methode mit diesem Namen.“ Die Methode steht im Formular, wo sie hingehört. Probe offscreen: Formular mit `self.p = Panel(self)`, `MainMenu(self.p)` (ebenso `PopupMenu(self.p)`) und `entries = [{"caption": "X", "on_click": "mi_x"}]`, `mi_x` als Methode des Formulars.

**Ursache:** nachgewiesen für die Laufzeit. `pcl/components/menus.py` Zeile 388 hält den unmittelbaren Elternteil für das Formular (`self._formular = parent`), `_handler_pruefen` (Zeilen 455-466) sucht die Methode dort. Im Designer nimmt `_behaelter_bei` (`ide/designer/canvas.py` ab Zeile 1741) jede abgelegte Komponente in den innersten Behälter auf, auch die Menüsymbole, und `ide/codegen/design.py` (Zeilen 404-407) erzeugt daraus `MainMenu(self.p_panel)`. Vermutet: Der Designer selbst prüft die Einträge ebenfalls gegen den Behälter.

**Zu tun:** Das Formular über die Elternkette bis zur `Form` bestimmen und im Designer Symbole mit `nur_im_designer` nie in einen Behälter legen (`_behaelter_bei`, `_behaelter_fuer`). Erledigt, wenn ein Test ein Menü auf einem Panel ablegt und das erzeugte Programm startet und die Methode aufruft.

## 594. Der Exe-Export prüft das Projekt nicht: ein Syntaxfehler in einer Unit ergibt eine Exe ohne diese Unit

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:** Steht in `u_main.py` ein Syntaxfehler, baut der Export weiter und meldet „Exe erstellt“. PyInstaller bricht nur bei einem Syntaxfehler im Startskript `main.py` ab; eine fehlerhafte Unit wird als `InvalidSourceModule` still weggelassen (Quelltext von PyInstaller 6.22.3: `depend/analysis.py` Zeilen 281-288, `lib/modulegraph/modulegraph.py` Zeilen 1958-1964, `compat.py` Zeilen 652-656). Vermutet, weil nicht gebaut wurde: die Exe endet beim Empfänger mit `ModuleNotFoundError: u_main`.

**Ursache:** nachgewiesen. `_als_exe_exportieren_aktion` (`ide/shell/hauptfenster.py` Zeilen 2715-2748) speichert nur alle Dateien und ruft die Prüfung vor dem Start (`projekt_pruefen`) nicht auf.

**Zu tun:** Vor dem Export `projekt_pruefen` laufen lassen und bei blockierenden Funden nicht exportieren, mit den Funden im Panel „Meldungen“. Erledigt, wenn ein Test den Export mit einem Syntaxfehler in einer Unit aufhält.

## 595. Haltepunkte stehen nach „Verwerfen“ auf der falschen Zeile oder sind weg

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d. Bezug: Punkt 419.

**Beobachtet:** Datei mit drei Zeilen, Haltepunkt auf Zeile 3. Darüber zwei Zeilen eingefügt, nicht gespeichert, Reiter geschlossen und „Verwerfen“ gewählt. Die Datei hat weiter drei Zeilen, der gemerkte Haltepunkt steht auf Zeile 5. Nach dem Wiederöffnen ist er fort (Probe mit Hauptfenster: im Editor `[5]`, nach dem Wiederöffnen `[]`). Liegt die gewanderte Zeile innerhalb der Datei, steht er auf einer fremden Anweisung.

**Ursache:** nachgewiesen. `_haltepunkte_merken` (`ide/shell/hauptfenster.py` ab Zeile 7599, aufgerufen in `_tab_schliessen` Zeile 7590) merkt die Zeilen aus dem Editor, auch wenn dessen Text verworfen wird; ebenso `_haltepunkte_ablegen` (ab Zeile 7632) beim Schließen von Projekt und Natter.

**Zu tun:** Beim Laden und Speichern den Stand der Haltepunkte festhalten, der zur Datei passt, und nach „Verwerfen“ diesen merken. Erledigt, wenn ein Test den Ablauf oben durchläuft und den Haltepunkt nach dem Wiederöffnen auf Zeile 3 findet.

## 596. Rückgängig führt Haltepunkte in drei Fällen nicht richtig zurück

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d. Bezug: Punkt 580.

**Beobachtet:** Proben mit `QuelltextEditor` offscreen:
- Haltepunkte auf 2 und 5, Funktion ab Zeile 4 zugeklappt, Strg+D. Nach Strg+Z bleibt nur `[2]`, nach Strg+Y nur `[5]`; erwartet war jeweils `[2, 5]`.
- Haltepunkt auf Zeile 3, Zeile 2 mit Alt+Pfeil runter verschoben, dann „Rückgängig“ aus dem Kontextmenü des Editors: der Text ist zurück, der Haltepunkt bleibt auf Zeile 2 und steht damit auf einer anderen Anweisung. Mit Strg+Z stimmt es.
- Eine Zeile mit Haltepunkt gelöscht und mit Strg+Z zurückgeholt: die Zeile ist wieder da, der Haltepunkt nicht.

**Ursache:** nachgewiesen. `undo`/`redo` (`ide/shell/quelltexteditor.py` Zeilen 573-590) wenden die gemerkte Zuordnung auf Haltepunkte an, die `_breakpoints_nachfuehren` (Zeilen 455-487) während `super().undo()` schon verschoben und teils verworfen hat. Das Kontextmenü kommt aus `createStandardContextMenu()` (Zeile 1679) und ruft Qts eigenes Rückgängig an diesen Methoden vorbei. Haltepunkte gelöschter Zeilen werden nirgends gemerkt.

**Zu tun:** Den Stand vor dem Rückgängigmachen sichern und die Zuordnung darauf anwenden, die Einträge Rückgängig und Wiederholen im Kontextmenü auf `self.undo`/`self.redo` legen und Haltepunkte gelöschter Zeilen je Schritt merken. Erledigt, wenn ein Test die drei Abläufe prüft.

## 597. `MainMenu.aktualisieren()` nach einem angehängten Eintrag endet mit `KeyError`

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:** `docs/komponenten.md` empfiehlt für Änderungen zur Laufzeit `eintrag()` und danach `aktualisieren()`. Nach `mm.eintrag("mi_datei")["children"].append({"name": "mi_neu", "caption": "Neu"})` und `mm.aktualisieren()` bricht das Programm mit `KeyError: 'separator'` ab, die Menüleiste ist dann schon geleert und nur halb neu aufgebaut. Ein über denselben Weg gesetztes Kürzel `"Strg+Bla"` wird still angenommen, steht im Menü und wirkt nie.

**Ursache:** nachgewiesen. `aktualisieren` (`pcl/components/menus.py` Zeilen 422-426) baut neu, ohne die Einträge mit `eintrag_vollstaendig` aufzufüllen oder mit `eintraege_pruefen` zu prüfen; Zeilen 470 und 473 greifen auf `eintrag["separator"]` und `eintrag["children"]` zu.

**Zu tun:** In `aktualisieren()` zuerst prüfen und die Einträge an Ort und Stelle auffüllen, damit Verweise aus `eintrag()` gültig bleiben. Erledigt, wenn ein Test einen knappen Eintrag anhängt, `aktualisieren()` aufruft und ihn im Menü findet, und ein ungültiges Kürzel mit deutscher Meldung abgelehnt wird.

## 598. `Chart`: häufige Eingabefehler enden englisch oder ergeben still ein falsches Diagramm

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d. Bezug: Punkt 592 (dort nur das leere Kreisdiagramm).

**Beobachtet:** Proben offscreen:
- `add_line_series` mit ungleich langen Listen: „ValueError: x and y must have same first dimension…“; ebenso `add_scatter_series` („x and y must be the same size“).
- `add_bar_series` mit `None` darin: `TypeError: unsupported operand…`.
- Kreisdiagramm mit einem negativen Stück: „Wedge sizes 'x' must be non negative values“; zu wenige Beschriftungen: „'labels' must be of length 'x'“; Werte als Text `["3", "1"]`: `UFuncTypeError` aus numpy.
- Histogramm mit `bins=0`: englischer `ValueError`.
- Werte als Text, wie sie aus `Edit.text` kommen: `add_line_series([1, 2, 3], ["10", "9", "100"])` zeichnet ohne Meldung eine Kategorienachse in der Reihenfolge 10, 9, 100.

**Ursache:** nachgewiesen. Die Methoden `add_*_series` (`pcl/components/chart.py` Zeilen 303-345) reichen die Werte ungeprüft an matplotlib weiter; nur geladene Daten laufen über `_als_zahlen`. Die Prüfung des Kreisdiagramms (Zeilen 309-322) fragt nur nach einem Wert über 0, und `_ist_positiv("3")` lässt Text durch.

**Zu tun:** Eine gemeinsame Vorprüfung in den `add_*`-Methoden: gleiche Länge, nur Zahlen (Text über `pcl.zahl` umwandeln oder deutsch melden), keine negativen Stücke, `bins` ab 1. Erledigt, wenn ein Test jeden Fall oben mit deutscher Meldung oder richtigem Diagramm prüft.

## 599. Ist `powershell.exe` gesperrt, meldet der Export „fehlgeschlagen“, obwohl die Exe gebaut ist

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:** `docs/handbuch.md` (Abschnitt AppLocker, Zeilen 209-210): „Ist `powershell.exe` für Schülerkonten gesperrt, entsteht beim Export trotzdem eine Exe, nur ohne Signatur.“ Probe mit einem Ersatz für `subprocess.run`, der wie eine gesperrte PowerShell `OSError` (WinError 1260) bzw. `FileNotFoundError` auslöst: die Ausnahme kommt aus `signieren_wenn_moeglich` heraus, das Hauptfenster meldet „Exe-Export fehlgeschlagen: [WinError 1260] …“ und öffnet den Ordner nicht, obwohl die Exe in `dist` liegt.

**Ursache:** nachgewiesen. `_powershell` (`ide/export/signatur.py` ab Zeile 131) fängt nur `subprocess.TimeoutExpired`; `exe_exportieren` (`ide/export/exporter.py` Zeile 604) fängt nichts.

**Zu tun:** Ein `OSError` beim Start von PowerShell wie eine misslungene Signatur behandeln („Exe erstellt, ohne Signatur“ mit Grund). Erledigt, wenn ein Test mit diesem Ersatz die Exe als erstellt und unsigniert gemeldet findet.

## 600. Der PDF-Export schneidet Formen links und oben ab und lässt Inhalt im Druckrand stehen

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d. Bezug: Punkt 568, der nur Inhalt rechts und unten jenseits der Seite einpasst.

**Beobachtet:**
- Ein Klick in den linken Seitenrand des Klassendiagramms (x = 20) legt die Klasse bei x = −72 an. `pdf_passt_auf_seite` sagt `True`, das PDF wird unverkleinert geschrieben, 72 der 184 Punkte Breite fehlen; die Statuszeile meldet „Exportiert nach …“.
- Formen zwischen Satzspiegel und Blattkante kommen unverkleinert ins PDF, bei y = 2 mit 0,4 mm Rand. Ein Struktogramm aus 37 Anweisungen gilt als passend und hat unten 4,9 mm Rand, obwohl `RAND_MM = 10` gilt.

**Ursache:** nachgewiesen. `pdf_passt_auf_seite` (`ide/diagramm/export.py` Zeilen 316-325) vergleicht nur rechte und untere Kante mit dem Blatt, nicht linke und obere Kante und nicht den Satzspiegel. `form_platzieren` (`ide/diagramm/canvas.py` Zeile 364) setzt die Mitte der Form auf den Klickpunkt, ohne einen Klick im Seitenrand zu korrigieren.

**Zu tun:** Gegen den Satzspiegel an allen vier Seiten prüfen und sonst einpassen, bei Struktogramm und Entscheidungstabelle die Ränder mitrechnen. Erledigt, wenn ein Test eine Form bei negativem x und eine im Druckrand exportiert und alles innerhalb des Satzspiegels findet.

## 601. Struktogramm-Code: eine Eingabe bleibt Text, wenn sie mit `!=`, `=`, in einer Fallauswahl oder mit `+` benutzt wird

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d. Bezug: Punkt 579, der nur Vergleiche mit `<`, `>`, `==` und Rechnungen mit `-`, `*`, `/`, `%` abdeckt.

**Beobachtet:** Proben mit `ide/diagramm/struktogramm_code.py`, der erzeugte Code ausgeführt:
- „Eingabe: z“ und „z != 0?“ ergeben `z = input("z? ")` und `if z != 0:`. Bei der Eingabe 0 kommt „nicht null“.
- „Eingabe: z“ und „z = 0?“ ergeben `if z == 0:`, das nie gilt.
- „Eingabe: note“ und eine Fallauswahl mit Kopf `note` und den Fällen 1, 2, sonst, genau das Beispiel aus `docs/handbuch.md` Abschnitt 3.4, ergeben `match note:` mit `case 1:`; bei der Eingabe 1 läuft der Sonst-Fall.
- „summe ← 0“, in einer Zählschleife „Eingabe: zahl“ und „summe ← summe + zahl“: `TypeError: unsupported operand type(s) for +: 'int' and 'str'`.
- „Eingabe: a“, „Eingabe: b“, „Ausgabe: a + b“ gibt bei 3 und 5 „35“ aus.

Keiner dieser Fälle erscheint als „nicht übernommen“.

**Ursache:** nachgewiesen. `_als_zahl_benutzt` (Zeilen 689-703) erkennt nur `<`, `>`, `<=`, `>=`, `-`, `*`, `/`, `%` und `==` vor einer Ziffer; `!=` fehlt, das einzelne `=` wird erst später in `_gleichheit` zu `==`, Fallbeschriftungen werden nicht angesehen, und `+` zählt absichtlich nicht.

**Zu tun:** Auch `!=`, ein einzelnes `=` vor einer Zahl, Zahlen als Fälle einer Fallauswahl über den Namen im Kopf und eine Summe mit einem Namen, der anderswo eine Zahl ist (oder mit 0 beginnt), als Zahlgebrauch werten. Erledigt, wenn ein Test jeden Fall oben ausführt und das erwartete Ergebnis erhält.

## 602. Struktogramm-Code: Pseudocode, der zufällig Python ist, landet unverändert im Code

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:**
- Ein neuer Anweisungsblock trägt „Anweisung“; daraus wird die Zeile `Anweisung`, beim Lauf `NameError`. Ebenso „Initialisierung“ oder „fertig ← falsch“ (`fertig = falsch`).
- Im Beispielprojekt `06_Kontoverwaltung` enthält `konto_abheben.pdiag` zweimal den Aussprung „Ende (Abbruch)“. Der erzeugte Code (Kopie in `%TEMP%`, geladen mit `Diagramm.laden`) enthält zweimal `Ende (Abbruch)`, also den Aufruf einer Funktion `Ende`; ausgeführt `NameError: name 'Ende' is not defined`.
- Eine Fallauswahl mit Kopf `farbe` und Fällen „rot“, „grün“ ergibt `if farbe == rot:`.

In allen Fällen meldet die Übersetzung „alles übernommen“ (`nicht_uebernommen` leer).

**Ursache:** nachgewiesen. `_anweisung` und `_aussprung` (`ide/diagramm/struktogramm_code.py` Zeilen 348-397) übernehmen alles, was `compile()` annimmt. Ein einzelner Name und ein Aufruf sind gültiges Python. Für Bedingungen gibt es mit `_unausgefuellt` eine Ausnahme für den Vorgabetext „Bedingung“, für „Anweisung“ und „Unterprogramm()“ nicht.

**Zu tun:** Eine Anweisung, die nur aus einem Namen besteht, sowie Namen und Aufrufe, die im Struktogramm nirgends einen Wert bekommen und keine eingebauten Namen sind, wie Pseudocode behandeln: Kommentar und Zählung. Einen Aussprung, der nicht `return …` ist und nicht in `AUSSPRUENGE` steht, als Aussprung mit Kommentar übersetzen. Den Vorgabetext „Anweisung“ wie „Bedingung“ als unausgefüllt werten. Erledigt, wenn ein Test die Fälle oben und das Beispiel `konto_abheben` ohne `NameError` beim Übersetzen findet und die Zeilen gezählt sind.

## 603. Struktogramm-Code: mehrzeilige Blöcke werden nicht übersetzt, „Eingabe:“ darin bleibt wirkungslos

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d. Bezug: Punkt 456 (gilt nur für einzeilige Blöcke) und Punkt 481.

**Beobachtet:** Ein Anweisungsblock mit den zwei Zeilen „Eingabe: a“ und „Eingabe: b“ ergibt wörtlich `Eingabe: a` und `Eingabe: b` im Code: zwei Annotationen ohne Wirkung, gezählt als übernommen. Ein Block mit „x ← 1“ und „y ← 2“ wird ganz zum Kommentar, ebenso „x = 1“ und „y ← 2“ zusammen, obwohl jede Zeile für sich übersetzt würde.

**Ursache:** nachgewiesen. `_anweisung` (`ide/diagramm/struktogramm_code.py` Zeilen 358-372) wendet Ein-/Ausgabe und Zuweisung nur an, wenn der Text keinen Zeilenumbruch hat; `_nur_annotation` (Zeile 706) erkennt nur einen Text aus genau einer Anweisung.

**Zu tun:** Mehrzeilige Blöcke Zeile für Zeile übersetzen und jede Annotation ohne Wert verwerfen. Erledigt, wenn ein Test die drei Blöcke oben in `a = input(…)`, `b = input(…)`, `x = 1`, `y = 2` übersetzt findet.

## 604. Struktogramm-Code: ein Komma in der Zählschleife ergibt einen falschen Bereich oder einen `TypeError`

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:**
- „für i von 1 bis 10, Schrittweite 2“ ergibt `range(1, (10,) + 1, 2)`, beim Lauf `TypeError`.
- „für i von 0,5 bis 2“ ergibt `range(0,5, 2 + 1)`: die Schleife läuft mit 0 und 3.
- „für i von 1 bis 2,5“ ergibt `range(1, (2,5) + 1)`, „i von 1 bis 10 schritt 0,5“ `range(1, 10 + 1, 0,5)`; beides `TypeError`.

Keine dieser Zeilen gilt als nicht übernommen.

**Ursache:** nachgewiesen. `_von_bis` (`ide/diagramm/struktogramm_code.py` Zeilen 884-911) prüft Anfang, Ende und Schrittweite mit `_ist_ausdruck`, das auch ein Tupel annimmt; das Dezimalkomma und ein Komma vor „Schrittweite“ werden so zu Tupeln oder zusätzlichen Argumenten.

**Zu tun:** Ein Komma vor „Schrittweite“ zulassen und Tupel als Grenze oder Schrittweite ablehnen (Kommentar und Zählung). Erledigt, wenn ein Test die vier Köpfe oben prüft.

## 605. Klassen-Code: mit Realisierung und Vererbung zugleich lässt sich die Klasse nicht anlegen

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d. Bezug: Punkt 149.

**Beobachtet:** `Vogel` mit dem Attribut `spannweite` realisiert das Interface `Fliegend` und erbt von `Tier` (Attribut `name`); die Realisierung ist zuerst gezogen. Erzeugt wird `class Vogel(Fliegend, Tier):` mit `def __init__(self, spannweite: float)` und `super().__init__()`. `Vogel("Tweety", 0.2)` scheitert an zu vielen Argumenten, `Vogel(0.2)` mit „Tier.__init__() missing 1 required positional argument: 'name'“. `ungueltige_namen` meldet nichts.

**Ursache:** nachgewiesen. `_basisform` (`ide/diagramm/klassen_code.py` ab Zeile 299) nimmt für den Konstruktor die erste Basisklasse aus `_basisklassen`, die Realisierungen mitzählt (`VERERBUNGSARTEN`, Zeile 35). Die Reihenfolge hängt davon ab, welche Verbindung zuerst gezogen wurde.

**Zu tun:** Für die Parameter des Konstruktors die erste Basisklasse nehmen, die kein Interface ist (Vererbung vor Realisierung), und Interfaces im Klassenkopf hinten anstellen. Erledigt, wenn ein Test das Beispiel oben in beiden Zeichenreihenfolgen mit `Vogel("Tweety", 0.2)` ausführt.

## 606. Klassen-Code: ein modellierter Konstruktor lässt Attribute mit Startwert weg

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:** `Konto` mit `-inhaber: str`, `-stand: float = 0` und der Operation `__init__(inhaber: str)` ergibt einen Konstruktor, der nur `self.__inhaber = inhaber` setzt. `vars(Konto("Anna"))` ist `{'_Konto__inhaber': 'Anna'}`; jede Methode, die `self.__stand` liest, bricht mit `AttributeError` ab. Das ist das übliche Muster: der Kontostand beginnt bei 0 und wird nicht übergeben.

**Ursache:** nachgewiesen. `_zuweisungen_fuer_init` (`ide/diagramm/klassen_code.py` ab Zeile 418) weist nur Attribute zu, die als Parameter vorkommen; ein Startwert ohne Parameter geht verloren.

**Zu tun:** Instanzattribute mit Startwert, die nicht Parameter sind, als `self.__stand = 0` in den modellierten Konstruktor schreiben. Erledigt, wenn ein Test das Beispiel oben erzeugt und `stand` am neuen Objekt findet.

## 607. Klassen-Code: eine Anfrage mit dem Namen eines öffentlichen Attributs verhindert das Anlegen

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:** `Person` mit dem öffentlichen Attribut `alter` und der Anfrage (Häkchen „Anfrage“) `alter(): int` ergibt `self.alter = alter` im Konstruktor und `@property def alter`. `Person(3)` scheitert mit „property 'alter' of 'Person' object has no setter“. `ungueltige_namen` meldet nichts.

**Ursache:** nachgewiesen. `_operation_zeilen` (`ide/diagramm/klassen_code.py` Zeile 524) macht eine Anfrage ohne Parameter zur Eigenschaft, ohne auf gleichnamige Attribute zu achten.

**Zu tun:** Den Namenskonflikt in `ungueltige_namen` melden oder in diesem Fall keine Eigenschaft erzeugen. Erledigt, wenn ein Test den Fall oben prüft.

## 608. Die Prüfung vor dem Start blockiert lauffähige Programme: Stern-Import, `try … except ImportError`, Dateien ohne UTF-8

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:** Proben mit `ide/run/pruefung.py` auf Kopien in `%TEMP%`:
- `from u_rechnen import *` in `u_main.py` blockiert den Start: „Aus der Unit u_rechnen wird * importiert, aber in u_rechnen.py gibt es keine Funktion, Klasse oder Variable dieses Namens“; aus `main.py` kommt dazu der Rat „Steht in u_main.py eine Zeile „def *():““.
- `try: from u_daten import extra` mit `except ImportError: extra = None` blockiert ebenso, und ein Name, der über `global` in einer beim Import aufgerufenen Funktion entsteht.
- Eine `u_main.py` in Windows-1252 blockiert mit der englischen Meldung „stream did not contain valid UTF-8“ (ruff `E902`), auch mit der Kopfzeile `# -*- coding: cp1252 -*-`, mit der Python die Datei ausführt. Im Editor lässt sich die Datei nicht öffnen, in Natter gibt es also keinen Weg, das zu beheben.

**Ursache:** nachgewiesen. `_importe_pruefen` (`ide/run/pruefung.py` Zeilen 556-580) prüft jeden Namen aus `knoten.names`, auch `*`, und beachtet kein umschließendes `try`; `_oberste_namen` (Zeilen 444-468) sieht keine `global`-Namen. Für `E902` gibt es keine Übersetzung in `_UEBERSETZUNGEN` (Zeilen 184-187) und keine Ausnahme.

**Zu tun:** `*` überspringen, Importe in einem `try` mit `except ImportError` oder `ModuleNotFoundError` nicht prüfen, `global`-Namen mitzählen oder dann schweigen; für `E902` eine deutsche Meldung und bei gültiger Kodierungsangabe und erfolgreichem `compile()` nicht blockieren. Erledigt, wenn ein Test jeden Fall startet.

## 609. Eine exportierte Konsolen-Exe schließt ihr Fenster sofort, auch nach einem Fehler

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:** In Natter hält eine Hülle das Konsolenfenster offen („Programm beendet. Eingabetaste zum Schließen …“) und zeigt Fehler deutsch. Die exportierte Exe eines Konsolenprojekts baut `main.py` direkt: per Doppelklick gestartet verschwindet das Fenster mit der letzten Ausgabe, bei „01 Begrüßung“ also mit der Antwort, und ein Fehler erscheint als englischer Traceback, der ebenso sofort weg ist.

**Ursache:** nachgewiesen. `exe_exportieren` (`ide/export/exporter.py` Zeile 536) übergibt `projekt.haupt_datei`; nur für GUI-Projekte gibt es einen eigenen Zweig (`--windowed`, Zeilen 530-531). Die Hülle `_KONSOLEN_HUELLE` (`ide/run/starter.py` Zeilen 34-110) gilt nur beim Start aus Natter.

**Zu tun:** Für Konsolenprojekte ein erzeugtes Startskript bauen, das `main.py` mit derselben Pause und derselben deutschen Fehlermeldung ausführt. Erledigt, wenn ein Test das Startskript eines Konsolenexports prüft.

## 610. Haltepunkte wandern falsch, wenn eine Änderung mitten in einer Zeile beginnt

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d. Bezug: Punkt 119.

**Beobachtet:** Proben mit `QuelltextEditor` offscreen:
- Haltepunkt auf `    b = 2`, die Schreibmarke hinter dem Einzug, Eingabetaste: der Haltepunkt bleibt auf der neuen, leeren Zeile, die Anweisung rutscht ohne ihn eine Zeile tiefer.
- Beim Neuladen einer von außen geänderten Datei (`_editor_neu_laden`, `ide/shell/hauptfenster.py` Zeile 5521) und beim Einfügen einer Ereignismethode beginnt der Unterschied oft mitten in einer Zeile; ein Haltepunkt auf `x = 1` stand danach auf `x = 0`, einer auf `c = 3` war nach dem Entfernen der Zeile davor weg.

**Ursache:** nachgewiesen. `_breakpoints_nachfuehren` (`ide/shell/quelltexteditor.py` Zeilen 455-487) zählt nur den Unterschied der Zeilenzahl und lässt die Zeile stehen, wenn die Änderung nicht am Zeilenanfang beginnt, auch wenn links davon nur Einzug steht. `editortext_ersetzen` (`ide/designer/canvas.py` Zeilen 544-583) ersetzt einen zeichengenauen Unterschied.

**Zu tun:** Eine Änderung, vor der in der Zeile nur Leerraum steht, wie eine am Zeilenanfang behandeln; beim Ersetzen von außen auf ganze Zeilen ausrichten (etwa zeilenweise mit `difflib`). Erledigt, wenn ein Test die Fälle oben prüft.

## 611. Ein Haltepunkt auf einer Leer- oder Kommentarzeile hält eine Anweisung zu früh

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:** Haltepunkte auf Zeile 3 (leer) und Zeile 4 (`# Kommentar`) einer Funktion; Zeile 5 ist `a = 1`. Mit echtem debugpy antwortet `setBreakpoints` mit `'line': 2` für beide, und das Programm hält in Zeile 2, bevor die vorige Anweisung gelaufen ist. Der rote Punkt im Editor bleibt auf Zeile 3 und 4.

**Ursache:** nachgewiesen. Die verlegte Zeile aus der Antwort gibt `ide/debugger/dap_client.py` (Zeilen 711-737) zurück, `ide/shell/hauptfenster.py` (Zeilen 9313-9321) verwirft sie.

**Zu tun:** Die Zeile aus der Antwort übernehmen und den Punkt im Editor dorthin setzen, oder Haltepunkte auf Leer- und Kommentarzeilen gleich auf die nächste Anweisung legen. Erledigt, wenn ein Test einen Haltepunkt auf einer Leerzeile setzt und Editor und Halt übereinstimmen.

## 612. „Als Tabelle anzeigen“ an einer aufgeklappten Variablen zeigt fremde Daten oder nichts

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:** Mit echtem debugpy: das Kind `werte` eines Objekts `p` wird als globale Variable `werte` ausgewertet (dort ein Text, Meldung „lässt sich nicht als Tabelle anzeigen“); die erste Zeile `0` einer Matrix ergibt dieselbe Meldung; ein Kind mit dem Anzeigenamen `[0]` zeigt die Liste `[0]`. Tabellen verschachtelter Daten, etwa eine Zeile einer Matrix oder eine Liste in einem Objekt, sind so nicht zu erreichen.

**Ursache:** nachgewiesen. `variable_als_tabelle_zeigen(eintrag.text(0))` (`ide/shell/hauptfenster.py` Zeilen 1128 und 9820) wertet den angezeigten Namen aus; `evaluateName` aus der Antwort von debugpy (`p.werte`, `matrix[0]`) wird nicht gespeichert (`grep evaluateName ide/shell/hauptfenster.py` findet nichts).

**Zu tun:** `evaluateName` am Eintrag ablegen und auswerten; ohne ihn den Eintrag nicht anbieten. Erledigt, wenn ein Test eine Matrixzeile und ein Attribut als Tabelle öffnet.

## 613. Gleiches Tastenkürzel in Hauptmenü und Klappmenü: die Taste tut nichts mehr

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d. Bezug: Punkt 591, seit dem die Kürzel eines Klappmenüs im ganzen Fenster gelten.

**Beobachtet:** „Bearbeiten → Löschen“ mit `Entf` im `MainMenu` und „Löschen“ mit `Entf` in einem `PopupMenu` desselben Formulars, ein übliches Muster. Ein Druck auf Entf löst keine der beiden Methoden aus (Probe: Aufrufe `[]`); ohne das Klappmenü ruft er die des Hauptmenüs (`['haupt']`). Ebenso bei zwei Klappmenüs mit demselben Kürzel. `docs/komponenten.md` (Zeile 754) verspricht, das Kürzel wirke „wie bei MainMenu im ganzen Fenster“.

**Ursache:** nachgewiesen. `PopupMenu._menue_erneuern` (`pcl/components/menus.py` Zeilen 585-594) meldet seine Kürzel als Fensterkürzel an, ohne die des Hauptmenüs zu kennen; Qt hält ein doppeltes Kürzel für mehrdeutig und löst nichts aus.

**Zu tun:** Doppelte Kürzel innerhalb eines Formulars beim Zuweisen mit deutscher Meldung ablehnen oder nur einmal anmelden. Erledigt, wenn ein Test den Fall oben prüft.

## 614. `Chart`: jedes `clear()` und jede neue Reihe zeichnet sofort neu, ein Diagramm per Zeitgeber wird zäh

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:** Offscreen gemessen: `draw()` allein 34 ms, `clear()` 63 ms, `clear()` mit `add_line_series` aus 10 Punkten 227 ms, hundertmal hintereinander 35,8 s. Mehr als vier bis fünf Aktualisierungen in der Sekunde schafft ein Diagramm mit Zeitgeber nicht, jede weitere Reihe kostet einen vollen Durchgang. Ein Balkendiagramm mit 2000 Kategorien als Text hält die Oberfläche 29,8 s an.

**Ursache:** nachgewiesen. `_neu_zeichnen` (`pcl/components/chart.py` Zeilen 717-731) ruft `draw()` direkt, aufgerufen aus `clear()` (Zeile 628) und nach jeder Reihe (Zeile 840).

**Zu tun:** Das Neuzeichnen bündeln, etwa mit `QTimer.singleShot(0, …)` und einer Prüfung, ob das Widget noch besteht. Erledigt, wenn ein Test `clear()` mit einer Reihe in einem Bruchteil der heutigen Zeit misst.

## 615. Debugger-Tabellenansicht: Zahlen werden als Text sortiert, eine sehr breite Tabelle scheitert unverständlich

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d. Bezug: Punkt 574.

**Beobachtet:**
- Sortieren nach einer Zahlenspalte ergibt 10, 100, 2.25, 3.5, 9; selbst die Spalte „#“ steht als 0, 1, 10, 11, 2. Kommazahlen erscheinen mit Punkt („3.5“), anders als in jeder anderen Anzeige von Natter. Die CSV-Ansicht sortiert dagegen nach Zahlwert.
- Eine Liste von Listen mit 8000 Spalten überschreitet die Antwortgrenze von debugpy; die Meldung rät zu „Start → Stopp … neu starten“, was nicht hilft, und hängt die ganze Rohantwort an: rund 65 700 Zeichen in der Statuszeile.

**Ursache:** nachgewiesen. `ide/viewers/tabellen_ansicht.py` Zeilen 37-43 legt jede Zelle als `QTableWidgetItem(str(zelle))` an, `ide/debugger/tabellenansicht.py` Zeilen 57-66 macht jeden Wert mit `str` zu Text. Die Grenze in `fertig` (Zeilen 68-87) zählt nur Zeilen, nicht Spalten, und übernimmt die erste Zeile immer.

**Zu tun:** Zahlen mit Typ übertragen, nach Zahlwert sortieren (`pcl.sortieren.sortierschluessel`) und mit Dezimalkomma zeigen; auch die Spaltenzahl begrenzen und die Rohantwort in der Meldung kürzen. Erledigt, wenn ein Test beides prüft.

## 616. Exe-Export: vorige Exe gelöscht, Semikolon im Namen, fremde Dateien in der Exe

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:**
- Scheitert ein Export oder wird er abgebrochen (Natter während des Exports geschlossen), ist `dist\<Name>.exe` danach weg, auch wenn sie vom letzten erfolgreichen Export stammt (`ide/export/exporter.py` Zeilen 569-578: `exe_pfad.unlink(missing_ok=True)` bei Rückgabe ungleich 0).
- Ein Semikolon in einem Datei- oder Ordnernamen, unter Windows erlaubt (`Noten; 7a.csv`, Ordner `Info;Kurs`), lässt PyInstaller mit „Wrong syntax, should be --add-data=SOURCE:DEST“ abbrechen: `--add-data` wird mit `os.pathsep` zusammengesetzt (Zeilen 512, 518, 521). Nachweis: `SourceDestAction` von PyInstaller direkt aufgerufen.
- Alles im Projektordner außer Quelltext geht als Daten in die Exe und wird bei jedem Start neben sie kopiert, auch `Testergebnisse.html` aus dem HTML-Export der Tests und `Thumbs.db`/`desktop.ini` (`_daten_dateien_des_projekts`, Zeilen 262-278). Bleiben `_pyinstaller_build` oder `_pyinstaller_spec` liegen, weil `rmtree(…, ignore_errors=True)` (Zeilen 565-566) still scheitert, erscheinen sie unter den weiteren Dateien des Projekts und kommen in die Abgabe-ZIP (Probe: `weitere_dateien` mit `_pyinstaller_build\Projekt\base_library.zip`).

**Ursache:** jeweils an der genannten Stelle nachgewiesen.

**Zu tun:** Nur eine in diesem Lauf geschriebene Exe löschen, die Daten über eine erzeugte `.spec` mit `datas` statt über die Befehlszeile übergeben, Testberichte, `Thumbs.db` und `desktop.ini` ausschließen und die Zwischenordner nach `%TEMP%` legen oder ausschließen. Erledigt, wenn ein Test zu jedem Fall besteht.

## 617. Struktogramm: die Zahl der nicht übernommenen Zeilen erscheint nirgends

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:** Der Modulkommentar von `ide/diagramm/struktogramm_code.py` verspricht, dass „sofort zu sehen ist, was von Hand nachzuziehen ist“, und `Ergebnis.meldung()` liefert den Satz „2 Zeilen konnten nicht übernommen werden.“ für den Kopf des Ausgabefensters. Weder das Fenster „Quelltext“ noch das Schreiben in eine Datei zeigt diesen Satz; die Kommentare im Code sind der einzige Hinweis.

**Ursache:** nachgewiesen. `DiagrammFenster.quelltext_code` (`ide/diagramm/fenster.py` Zeile 1080) gibt nur `.text` weiter; `grep -rn "meldung()" ide` findet keinen Aufruf von `Ergebnis.meldung`, nur Tests in `tests/test_struktogramm_code.py`.

**Zu tun:** Die Meldung im Codefenster über dem Text und beim Schreiben in die Datei in der Statuszeile zeigen. Erledigt, wenn ein Test das Codefenster für ein Struktogramm mit Pseudocode öffnet und den Satz findet.

## 618. MaskEdit: die Referenz nennt nur einen Teil der Maskenzeichen, fester Text wird zerstückelt

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d. Bezug: Punkt 592.

**Beobachtet:** `docs/komponenten.md` (Zeilen 891-893) sagt nach der Liste der Platzhalter „Alles andere steht fest da“. Qt liest aber auch `a n X x D d H h B b # > < ! \ ;` als Steuerzeichen. Die Maske „Datum: 00.00.0000“ zeigt `'  tum:   .  .    '`, „KD-0000“ zeigt `'K -    '`.

**Ursache:** nachgewiesen. `pcl/components/eingaben.py` reicht die Maske an `QLineEdit.setInputMask` weiter; Referenz, Docstring (Zeilen 71-73) und Hilfetext der Eigenschaft (Zeile 95) nennen die übrigen Zeichen und das Maskieren mit `\` nicht.

**Zu tun:** Alle Sonderzeichen und `\` in der Referenz nennen, mit einem Beispiel mit festem Text. Erledigt, wenn die Referenz das beschreibt und ein Test die Maske `Datum: 00.00.0000` in der dort gezeigten Schreibweise prüft.

## 619. Klassen-Code: eine gerichtete Assoziation wird kein Attribut

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d. Bezug: Punkt 182.

**Beobachtet:** `Auto` → `Motor` als „Gerichtete Assoziation“ aus der Palette, am Ziel die Beschriftung „-motor 1“. Der erzeugte Code enthält zwei leere Klassen. Mit Aggregation oder Komposition entsteht `self.motor = motor`. Im Unterricht ist die gerichtete Assoziation mit Rollenname die übliche Form für „kennt ein“, und genau sie wird im Code zu einem Attribut.

**Ursache:** nachgewiesen. `TEILEARTEN` (`ide/diagramm/klassen_code.py` Zeile 42) enthält nur `aggregation` und `composition`; `directed_association` aus `ide/diagramm/formen.py` (Zeile 123) kommt in `klassen_code.py` nicht vor.

**Zu tun:** Eine gerichtete Assoziation an der Quelle wie ein Teil behandeln (Name aus dem Rollennamen am Ziel, Liste bei Vielfachheit) oder in Handbuch und Codefenster sagen, dass sie nicht übersetzt wird. Erledigt, wenn ein Test das Beispiel oben prüft.

## 620. Klappmenü: die Methode erfährt nicht, an welcher Komponente das Menü aufging

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:** `docs/komponenten.md` (Zeile 752) erlaubt dasselbe Klappmenü an mehreren Komponenten. Ein gemeinsames „Löschen“ für zwei ListBoxen lässt sich trotzdem nicht schreiben: `sender` ist immer das Klappmenü, und welche ListBox angeklickt wurde, steht nirgends.

**Ursache:** nachgewiesen. `pcl/components/menus.py` Zeile 501 ruft die Methode mit dem Menü als Absender; `aufklappen` (Zeilen 603-607) merkt sich die Komponente nicht.

**Zu tun:** Die Komponente beim Aufklappen als Eigenschaft des Klappmenüs ablegen und in der Referenz beschreiben. Erledigt, wenn ein Test das Menü an zwei Komponenten aufklappt und jeweils die richtige findet.

## 621. Kleinere Abweichungen in Menüs, Chart, Auswahllisten und Editor

**Gemeldet:** 3. Oktober 2026, Durchsicht, Stand 2376f1d.

**Beobachtet:**
- `kuerzel_fehler` nimmt „Strg+S, Bla“ an; Qt macht daraus eine Folge mit `Key_unknown`, das Kürzel wirkt nie (`pcl/components/menus.py` Zeilen 151-156). Pfeiltasten und „Druck“ fehlen in `_TASTENNAMEN`.
- Jeder Rechtsklick auf eine Komponente mit Klappmenü legt ein neues `QMenu` an, das nie freigegeben wird (nach 30 Klicks 30 Kinder, Zeilen 563-564); jedes `MainMenu.aktualisieren()` lässt die alten Untermenüs an der Leiste hängen (nach 50 Aufrufen 55, Zeilen 475 und 542-543).
- Menüeinträge kennen weder `visible` noch eine Gruppe, in der genau ein Eintrag angekreuzt ist (`EINTRAG_VORGABE`, Zeilen 67-77).
- `Chart`: eine Linienreihe aus einem Punkt ist unsichtbar (kein Marker, `chart.py` Zeile 305); der `title` einer Reihe wird zur Überschrift des ganzen Diagramms (zwei Reihen „Jungen“ und „Mädchen“ ergeben die Überschrift „Mädchen“, Zeilen 836-839); `kind` wirkt nicht auf Reihen aus `add_*_series`; Achsenbereiche lassen sich nicht festlegen.
- `ComboBox` wählt beim Füllen von `items` Eintrag 0, die Referenz (`docs/komponenten.md` Zeile 349) nennt -1 als Vorgabe; `RadioGroup` meldet kein `on_change`, wenn sich der Text der gewählten Option durch `items.insert(0, …)` ändert, die ComboBox schon (`pcl/components/standard.py` Zeilen 953-961 und 646).
- `MaskEdit` meldet `on_change` bei abgelehnten Zeichen und bei der Rücktaste über leere Stellen, und beim Wechsel der Maske mit dem Text samt festen Zeichen (`pcl/components/eingaben.py` Zeilen 105-129).
- Umschalt+Tab rückt eine Zeile mit Tabulator-Einzug nicht aus (`ide/shell/quelltexteditor.py` Zeile 1307 zählt mit `lstrip(" ")` nur Leerzeichen).
- `docs/handbuch.md` (Zeile 1006) und `ide/shell/tastenkuerzel.py` (Zeile 83) nennen „Klick rechts im Zeilenrand“ für das Zuklappen; ein Rechtsklick in den Rand öffnet aber das Menü für Haltepunkte und Bedingungen, das in keiner Übersicht steht.
- Vermutet, nur am Code: Wer während eines Halts eine Zeile oberhalb eines Haltepunkts einfügt, schickt die neue Zeilennummer sofort an debugpy (`hauptfenster.py` Zeilen 9313-9321), das laufende Programm hat aber den alten Stand geladen und hält an einer anderen Anweisung.

**Ursache:** jeweils an der genannten Stelle nachgewiesen, außer dem letzten Punkt.

**Zu tun:** Jede Abweichung beheben oder in der Referenz beschreiben. Erledigt, wenn zu jedem Punkt ein Test oder ein Satz in der Referenz besteht.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
