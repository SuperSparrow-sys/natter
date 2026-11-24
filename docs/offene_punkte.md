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

## 668. Eine `.pfm` hebt mit `_projektordner` die Bildpfad-Sperre des Designers wieder auf

**Gemeldet:** 24. November 2026, Prüfung A, Entwicklungsstand `42d5478`.

**Beobachtet:** Seit Punkt 334 lädt der Designer Bilder nur aus dem
Projektordner, damit das Öffnen einer fremden `.pfm` keine Verbindung
zu einem anderen Rechner aufbaut. Den Projektordner entnimmt er dem
Attribut `_projektordner` am Formular. Eine `.pfm` kann dieses
Attribut unter `properties` des Formulars selbst setzen, auf `null`
oder auf einen beliebigen Ordner. Danach lädt der Designer ein Bild
von jedem Pfad, auch einem Netzpfad. Wer eine Abgabe oder ein Projekt
aus fremder Hand im Designer öffnet, verbindet sich damit wieder mit
einem Rechner, den der Absender bestimmt, samt Anmeldeversuch mit dem
Windows-Konto und der Wartezeit aus Punkt 334. Nachgestellt mit einem
Bild in einem Nachbarordner des Projekts: ohne die Angabe bleibt die
Vorschau leer, mit `"_projektordner": null` oder mit dem Nachbarordner
erscheint das Bild. Dieselbe Lücke erlaubt jedes andere interne
Attribut mit Unterstrich, am Formular wie an jeder Komponente
(`_entwurfsansicht`, `_qwidget`, `_eltern` …); die Werte bleiben
Literale, aber der Designer arbeitet danach mit verbogenen Interna.

**Ursache:** nachgewiesen. `ide/codegen/design.py`, Zeilen 95-96
(`_eintrag_pruefen`) verlangt für Eigenschaftsnamen nur einen
Bezeichner, auch einen mit `_` am Anfang. `pcl/properties.py`, Zeile
576, nimmt jeden Namen mit `_` ohne Prüfung an. `ide/designer/laden.py`,
Zeile 227, setzt `_projektordner` an der Klasse; die Zuweisung aus der
`.pfm` im erzeugten `create_components` überdeckt es am Objekt.
`pcl/components/additional.py`, Zeilen 457-461 (`_bilddatei_finden`),
gibt bei `None` einen absoluten Pfad unverändert zurück. Nachweis:
`build/auswertung/pruefung_42d5478/A/668_projektordner_aus_pfm.py`.

**Zu tun:** Eigenschaftsnamen in einer `.pfm` auf die Eigenschaften
beschränken, die die jeweilige Komponente öffentlich anbietet (kein
`_` am Anfang, deklariert in `pcl`), und eine andere Angabe als
beschädigt melden. Erledigt, wenn ein Test eine `.pfm` mit
`_projektordner` am Formular als beschädigt ablehnt und ein Bild
außerhalb des Projektordners im Designer weiterhin nicht geladen wird.

## 669. Prüfungsmodus: Test-Explorer und Fäden zeigen Pythons Namensvorschlag „Did you mean“

**Gemeldet:** 24. November 2026, Prüfung A, Entwicklungsstand `42d5478`.

**Beobachtet:** Laut Handbuch, Abschnitt 4, gibt es im Prüfungsmodus
keinen Lösungsvorschlag, und der Fehlerkatalog entfernt dafür Pythons
eigenes „Did you mean …?“. Zwei Wege zeigen es trotzdem:

1. Lässt sich eine Testdatei nicht laden, weil die geprüfte Unit beim
   Import scheitert, steht im Test-Explorer der rohe Traceback. Bei
   einem Tippfehler auf oberster Ebene der Unit endet er mit
   „NameError: name 'pirnt' is not defined. Did you mean: 'print'?“.
   Das trifft gerade die Lage, in der eine Lehrkraft zur Klausur eine
   Testdatei austeilt.
2. Eine Ausnahme in einem Faden des Schülerprogramms geht an
   `sys.excepthook` vorbei und landet mit demselben Vorschlag roh auf
   der Fehlerausgabe, bei einem Programm mit Fenster also im Panel
   „Ausgabe“.

**Ursache:** nachgewiesen. `ide/testrunner/harness.py`, Zeile 284
(`addError` für `_FailedTest`) und Zeilen 348-360
(`ladefehler_meldung` hängt den Traceback unverändert an, auch im
Modus). `pcl/fehleranzeige.py`, Zeilen 88-95, hängt nur
`sys.excepthook` ein, nicht `threading.excepthook`. Nachweis:
`build/auswertung/pruefung_42d5478/A/669_testlauf_vorschlag.py`.

**Zu tun:** Im Ladefehler des Testlaufs Pythons Vorschläge wie im
Fehlerkatalog entfernen (`_vorschlaege_entfernen`), mindestens im
Prüfungsmodus, und für Fäden `threading.excepthook` auf dieselbe
Meldung wie `sys.excepthook` lenken. Erledigt, wenn ein Test mit
vorgetäuschtem Prüfungsmodus für eine Unit mit `pirnt` auf oberster
Ebene und für einen Faden mit demselben Fehler keinen Text „Did you
mean“ mehr findet.

## 670. NaN und Infinity aus einer `.pfm` landen als Name statt als Literal im erzeugten Quelltext

**Gemeldet:** 24. November 2026, Prüfung A, Entwicklungsstand `42d5478`.

**Beobachtet:** `json.loads` nimmt `NaN`, `Infinity` und `-Infinity`
an. Steht so ein Wert in einer `.pfm`, schreibt die Codeerzeugung
`self.b_ok.left = nan` bzw. `= inf` in den Quelltext, also einen Namen
und kein Literal. Beim Öffnen im Designer endet das mit `NameError`;
den fangen weder das Laden noch `oeffnen` ab, und statt „die Datei ist
beschädigt“ erscheint die Meldung für einen internen Fehler. Eine so
gespeicherte `u_*_design.py` bricht beim Programmstart ebenso ab.
Ausführbarer Code entsteht dabei nicht, weil `nan` und `inf` nirgends
definiert sind; es ist aber die einzige Stelle, an der ein Wert aus
der `.pfm` nicht als Literal im Quelltext steht.

**Ursache:** nachgewiesen. `ide/codegen/design.py`, Zeile 183
(`return repr(wert)` für Zahlen), `ide/schema.py`, Zeile 104
(`json.loads` ohne `parse_constant`). Abgefangen wird in
`ide/designer/laden.py`, Zeilen 241-251, und
`ide/shell/hauptfenster.py`, Zeile 8643, kein `NameError`. Nachweis:
`build/auswertung/pruefung_42d5478/A/670_nan_als_name.py`.

**Zu tun:** Nicht endliche Zahlen beim Lesen einer `.pfm` ablehnen
(`parse_constant` oder Prüfung in `pfm_pruefen`) und als beschädigt
melden. Erledigt, wenn ein Test eine `.pfm` mit `NaN` und eine mit
`Infinity` im Designer als beschädigt meldet und
`design_code_erzeugen` für sie keinen Quelltext liefert.

## 671. Die Integritätsprüfung beim Start läuft erst, nachdem die IDE geladen und das Hauptfenster gebaut ist

**Gemeldet:** 24. November 2026, Prüfung A, Entwicklungsstand `42d5478`.

**Beobachtet:** `starten()` baut zuerst Anwendung und Hauptfenster und
prüft danach die Installation. Bis dahin sind 157 Module aus `ide` und
`pcl` geladen und ausgeführt, darunter `ide.shell.hauptfenster`,
`pcl.pruefungsmodus` und `pcl.fehlerkatalog`, also genau die Dateien,
die die schnelle Prüfung ansehen soll. Eine veränderte Datei unter
ihnen läuft damit, bevor die Meldung „Natter wurde verändert“
erscheinen kann, und kann die Prüfung selbst ausschalten. Bei einer
Installation für alle Benutzer braucht eine solche Änderung
Verwaltungsrechte. Bei der Installation nur für das angemeldete Konto
kann jedes Programm dieses Kontos in den Programmordner schreiben;
dort ist die Meldung die einzige Rückmeldung über eine Veränderung.

**Ursache:** nachgewiesen. `ide/main.py`, Zeile 199 (`erstellen`)
vor Zeile 208 (`integritaet_bestaetigen`); `erstellen` importiert in
Zeile 138 das Hauptfenster und baut es in Zeile 142. Nachweis:
`build/auswertung/pruefung_42d5478/A/671_integritaet_nach_import.py`.

**Zu tun:** Die Prüfung vor dem Import des Hauptfensters ausführen,
nur mit dem, was dafür nötig ist (`ide.integritaet`, `cryptography`,
Qt für die Meldung), und die schon geladenen Module dabei mit
aufnehmen. Erledigt, wenn ein Test zeigt, dass beim Aufruf von
`installation_pruefen` während des Starts `ide.shell.hauptfenster`
noch nicht in `sys.modules` steht.

## 698. Designer ändert die Unit nur auf der Platte, der offene Editor bleibt beim alten Text; nach Löschen und Rückgängig startet das Programm nicht

**Gemeldet:** 24. November 2026, Prüfung B, Entwicklungsstand `42d5478`.

**Beobachtet:** Neues GUI-Projekt, Knopf `b_rechnen` platziert, Doppelklick: `b_rechnen_click` steht in `u_main.py`, der Editor dazu ist offen (so springt der Doppelklick hin). Danach den Knopf im Designer löschen: die leere Methode verschwindet aus der Datei, im Editor steht sie weiter, und der Reiter gilt als gespeichert. Strg+Z im Designer holt den Knopf und seine Verknüpfung zurück, die Methode auf der Platte aber nicht. Die Prüfung vor dem Start blockiert dann mit „Die Methode b_rechnen_click fehlt in der Klasse Form1 …“, während der Editor genau diese Methode zeigt. Der vorgeschlagene Doppelklick legt nichts an, weil die Verknüpfung schon besteht. Ebenso nach Doppelklick und sofortigem Strg+Z im Designer: Platte ohne, Editor mit Methode, Reiter unverändert. Erwartet wäre, dass Datei und Editor nach jedem Schritt übereinstimmen und Rückgängig beide zurückholt, wie es Punkt 537 als erledigt beschreibt.

**Ursache:** nachgewiesen. `_unit_tauschen` (`ide/designer/canvas.py`, Zeile 907) schreibt über `_unit_schreiben` (Zeile 2969) nur die Datei und führt bei offenen Editoren lediglich den Dateistand nach, nicht ihren Text. Beim Rückgängigmachen verlangt `_unit_tauschen`, dass Platte und alle Editoren den erwarteten Text haben; der Editor hat ihn nach dem ersten Schritt nicht mehr, also bleibt die Platte, wie sie ist. Weil der Dateistand nachgeführt ist, lädt auch die Rückkehr ins Fenster den Editor nicht neu. Nachweis: `build/auswertung/pruefung_42d5478/B/698_unit_editor_und_platte_auseinander.py`.

**Zu tun:** Das Entfernen und Wiederherstellen einer Methode durch den Designer (`_MethodeAnlegenKommando`, `_UnitTauschKommando`) auch im offenen Editor ausführen, als ein Schritt, wie es das Umbenennen schon tut (`editortext_ersetzen`). Erledigt, wenn ein Test mit offenem Editor nach Doppelklick, Löschen und Strg+Z Platte und Editor gleich findet und die Prüfung vor dem Start nichts meldet.

## 699. Mit F5 erscheint die Ausgabe von `print()` eines Programms mit Fenster nirgends

**Gemeldet:** 24. November 2026, Prüfung B, Entwicklungsstand `42d5478`.

**Beobachtet:** GUI-Projekt, in `u_main.py` ein `print("Zeile aus print")`. Mit Strg+F5 steht die Zeile im Panel „Ausgabe“, mit F5 („Starten“, unter dem Debugger) in keinem Panel und keinem Fenster; das Panel „Ausgabe“ bleibt ganz leer, auch ohne Zeile zu Start und Ende. `print()` zur Fehlersuche ist im Anfangsunterricht üblich, und F5 ist der Weg, den das Handbuch zuerst nennt.

**Ursache:** nachgewiesen. `debugpy_aufruf` (`ide/debugger/dap_client.py`, Zeilen 291 bis 295) startet ein Programm mit Fenster mit `ohne_konsole` und ohne Rohr für Standardausgabe und Fehlerausgabe; `output`-Ereignisse von debugpy wertet `DapClient` nicht aus. Punkt 87 hat das für Konsolenprogramme gelöst und Programme mit Fenster ausdrücklich gelassen. Nachweis: `build/auswertung/pruefung_42d5478/B/699_print_unter_dem_debugger.py`.

**Zu tun:** Die Ausgabe eines Programms mit Fenster auch unter dem Debugger ins Panel „Ausgabe“ bringen, etwa über ein Rohr mit `AusgabeLeser` wie bei Strg+F5 oder über die `output`-Ereignisse. Erledigt, wenn der Nachweis mit F5 die Zeile im Panel findet.

## 700. Ein Fehler beim Laden von `u_main.py` erscheint mit Strg+F5 als englischer Traceback, und die Schlusszeile verweist auf ein Fenster, das es nicht gab

**Gemeldet:** 24. November 2026, Prüfung B, Entwicklungsstand `42d5478`.

**Beobachtet:** GUI-Projekt, in der ersten Zeile von `u_main.py` ein `import` eines nicht installierten Moduls oder ein `open("punkte.txt")` einer fehlenden Datei. Strg+F5: das Panel „Ausgabe“ zeigt den englischen Traceback mit `ModuleNotFoundError: No module named …` bzw. `FileNotFoundError: [Errno 2] No such file or directory`, ohne Wo/Was/Zu prüfen, und darunter „Programm beendet (Code 1) … Die Fehlermeldung hat das Programm vor dem Beenden in einem eigenen Fenster gezeigt.“ Ein solches Fenster erscheint nicht. Die Prüfung vor dem Start findet beides nicht.

**Ursache:** nachgewiesen. Die deutsche Fehleranzeige hängt sich erst in `Application.run()` ein (`pcl/application.py`, Zeile 124, `einhaengen` in `pcl/fehleranzeige.py`). `main.py` aus der Vorlage importiert `u_main` vor `Application()`; ein Fehler beim Import läuft deshalb am Haken vorbei. `programmende_melden` (`ide/shell/hauptfenster.py`, ab Zeile 9521) nimmt bei jedem Programm mit Fenster an, die Meldung sei in einem Fenster erschienen. Nachweis: `build/auswertung/pruefung_42d5478/B/700_fehler_beim_import_der_unit.py`.

**Zu tun:** Die Fehleranzeige schon vor dem Import der Units wirken lassen, etwa durch Einhängen beim Import von `pcl` im gestarteten Programm oder in einer Starthülle wie bei Konsolenprogrammen, und die Schlusszeile danach richten, wo die Meldung tatsächlich steht. Erledigt, wenn der Nachweis eine deutsche Meldung mit Wo/Was/Zu prüfen findet und die Schlusszeile kein Fenster behauptet.

## 701. Löschen einer Komponente nimmt eine leere Methode mit, die ein Menüeintrag noch aufruft

**Gemeldet:** 24. November 2026, Prüfung B, Entwicklungsstand `42d5478`.

**Beobachtet:** Knopf `b_weiter` mit Doppelklick-Methode `b_weiter_click`, dazu ein Hauptmenü, dessen Eintrag „OK“ im Menü-Editor unter „Beim Anklicken“ dieselbe Methode nennt. Wird der Knopf gelöscht, nimmt der Designer `b_weiter_click` aus der Unit, obwohl die `.pfm` sie im Menüeintrag weiter nennt. Das Programm bricht danach beim Aufbau des Formulars ab: „Der Menüeintrag „OK“ soll beim Anklicken die Methode 'b_weiter_click' aufrufen, aber Form1 hat keine Methode mit diesem Namen.“ Die Prüfung vor dem Start meldet nichts (siehe Punkt 703).

**Ursache:** nachgewiesen. `_leere_methoden_entfernen` (`ide/designer/canvas.py`, ab Zeile 2335) zählt als weiter benutzt nur die Ereignisse der verbleibenden Komponenten, nicht die `on_click` in den Einträgen der Menüs. `_handler_umhaengen` (Zeilen 3049 bis 3054) berücksichtigt die Menüeinträge beim Umbenennen bereits. Nachweis: `build/auswertung/pruefung_42d5478/B/701_loeschen_entfernt_menue_methode.py`.

**Zu tun:** Methoden, die ein Menüeintrag eines verbleibenden Menüs nennt, beim Löschen stehen lassen. Erledigt, wenn der Nachweis die Methode nach dem Löschen noch in der Unit findet und das Formular sich bauen lässt.

## 702. Ein Fehler in einer Ereignismethode lässt den Debugger in einem Programm mit Fenster nicht anhalten

**Gemeldet:** 24. November 2026, Prüfung B, Entwicklungsstand `42d5478`.

**Beobachtet:** GUI-Projekt mit F5 gestartet; eine Methode, die Qt aufruft (hier über einen Zeitgeber aus `form_create`), teilt durch 0. Die Fehlerzeile wird erreicht, aber nach 25 Sekunden ist das Panel „Meldungen“ leer, der Debugger hält nicht, und der Editor springt nicht zur Zeile. In einem Konsolenprojekt hält der Debugger an derselben Stelle und zeigt die Meldung aus dem Fehlerkatalog (`test_unbehandelte_ausnahme_zeigt_die_fehlerkatalog_meldung_und_springt_hin`). In Programmen mit Fenster stehen die Fehler aber meist in Ereignismethoden.

**Ursache:** Wirkung nachgewiesen, Mechanismus vermutet. Natter setzt nur den Filter `uncaught` (`ide/debugger/dap_client.py`, Zeile 515). Ein Fehler in einer von Qt aufgerufenen Methode gelangt nicht bis zum äußersten Rahmen, sondern an `sys.excepthook`, den `pcl.fehleranzeige` belegt; debugpy wertet ihn deshalb vermutlich nicht als unbehandelt. Nachweis: `build/auswertung/pruefung_42d5478/B/702_ereignisfehler_unter_f5.py`.

**Zu tun:** Unter dem Debugger auch Fehler in Ereignismethoden anhalten lassen, etwa mit dem Filter `userUnhandled` oder indem die Fehleranzeige des Programms unter dem Debugger den Fehler an debugpy weitergibt. Erledigt, wenn der Nachweis eine Meldung im Panel „Meldungen“ und den Halt an der Fehlerzeile findet.

## 703. Die Prüfung vor dem Start übersieht eine Menü-Methode, die in der Unit fehlt

**Gemeldet:** 24. November 2026, Prüfung B, Entwicklungsstand `42d5478`.

**Beobachtet:** Ein Menüeintrag nennt unter „Beim Anklicken“ eine Methode, die es in der Unit nicht gibt, etwa nach einem Tippfehler, nach Strg+Z im Editor oder nach Punkt 701. Die Prüfung vor dem Start meldet nichts; das Programm bricht erst beim Aufbau des Formulars ab. Für Ereignisse von Komponenten und Formular findet dieselbe Prüfung eine fehlende Methode seit Punkt 290 und sagt vorher, was fehlt.

**Ursache:** nachgewiesen. `_verknuepfungen` (`ide/run/pruefung.py`, ab Zeile 816) liest nur `events` und `children` der `.pfm`, nicht die `on_click` in `properties.entries` der Menüs. Nachweis: `build/auswertung/pruefung_42d5478/B/703_menue_methode_vorstart.py`.

**Zu tun:** Die Menüeinträge in `_verknuepfungen` mitnehmen, mit einer Meldung, die Menüeintrag und Methode nennt. Erledigt, wenn der Nachweis einen blockierenden Fund liefert.

## 704. Die leere Methode eines gelöschten Knopfs `b_ok` bleibt in der Unit stehen

**Gemeldet:** 24. November 2026, Prüfung B, Entwicklungsstand `42d5478`.

**Beobachtet:** Neues GUI-Projekt, Knopf in `b_ok` umbenannt, Doppelklick, Knopf gelöscht: `b_ok_click` bleibt leer in `u_main.py` stehen. Mit dem Namen `b_weiter` verschwindet die Methode wie in Punkt 537 vorgesehen. `b_ok` ist genau der Name, den der Kopfkommentar der Vorlage als Beispiel zeigt.

**Ursache:** nachgewiesen. `_leere_methoden_entfernen` (`ide/designer/canvas.py`, Zeile 2377) lässt eine Methode stehen, sobald ihr Name mehr als einmal im Quelltext vorkommt, auch in Kommentaren; der Kopfkommentar aus `templates/gui/u_main.py.template` (Zeilen 24 und 27) enthält `b_ok_click` zweimal. Nachweis: `build/auswertung/pruefung_42d5478/B/704_leere_methode_b_ok_bleibt.py`.

**Zu tun:** Nur Verwendungen im Code zählen, nicht in Kommentaren und Zeichenketten. Erledigt, wenn der Nachweis auch bei `b_ok` keine leere Methode mehr findet.

## 705. Häufige Anfängerfehler haben im Fehlerkatalog nur den allgemeinen Rückfall mit englischem Zitat

**Gemeldet:** 24. November 2026, Prüfung B, Entwicklungsstand `42d5478`.

**Beobachtet:** Echt ausgelöste Fehler und die Meldung von `fehlermeldung_erzeugen`:

- `for i in range(n / 2)`: „Die verwendeten Datentypen passen an dieser Stelle nicht zusammen. Python meldet dazu wörtlich: „'float' object cannot be interpreted as an integer““, dazu „Stimmt die Anzahl der Argumente?“, was hier in die Irre führt.
- `random.choice([])`: „Es wurde ein Platz angesprochen, den es in der Sammlung nicht gibt. Python meldet dazu wörtlich: „Cannot choose from an empty sequence““, und „Zu prüfen“ fragt nach einem Index, den es im Programm nicht gibt.
- `f"{eingabe:.2f}"` mit einem Text: „Der übergebene Wert passt nicht …“ mit dem englischen Zitat „Unknown format code 'f' for object of type 'str'“.
- Ein Wörterbuch, das in seiner eigenen Schleife wächst: `RuntimeError` ohne jeden Katalogeintrag, also die Meldung „Zu diesem Fehler gibt es noch keine deutsche Erklärung“ mit Traceback.

**Ursache:** nachgewiesen. Für diese Texte gibt es kein Muster in `_STANDARDMELDUNGEN` (`pcl/fehlerkatalog.py`, ab Zeile 257), es greift der Rückfall aus `_was_und_pruefe`; `docs/fehlerkatalog.yaml` hat keinen Eintrag für `RuntimeError`. Nachweis: `build/auswertung/pruefung_42d5478/B/705_fehlerkatalog_ohne_uebersetzung.py`.

**Zu tun:** Eigene Muster für diese vier Fälle, mit Leitfragen, die zum Fehler passen (Kommazahl statt ganzer Zahl als Grenze, leere Liste, Text statt Zahl beim Formatieren, Wörterbuch während der Schleife verändert). Erledigt, wenn der Nachweis für alle vier eine deutsche Meldung ohne „Python meldet dazu wörtlich“ findet.

## 706. `as_float` liest Feldwerte mit Tausenderpunkt anders als `zahl()`

**Gemeldet:** 24. November 2026, Prüfung B, Entwicklungsstand `42d5478`.

**Beobachtet:** Ein Textfeld der Datenbank mit „1.234,5“ ergibt über `field_by_name(…).as_float` „Der Wert '1.234,5' lässt sich nicht als Kommazahl lesen.“, `zahl("1.234,5")` ergibt 1234,5. „1.000“ ergibt über `as_float` 1,0, über `zahl()` 1000. Dieselbe Eingabe bedeutet damit in einem Programm je nach Weg etwas anderes.

**Ursache:** nachgewiesen. `_Feld.as_float` (`pcl/components/data_access.py`, ab Zeile 486) ersetzt nur das Komma durch einen Punkt und ruft `float()`, statt `pcl.zahlen.zahl` zu benutzen. Nachweis: `build/auswertung/pruefung_42d5478/B/706_as_float_gegen_zahl.py`.

**Zu tun:** Texte in `as_float` mit `zahl()` lesen. Erledigt, wenn der Nachweis für alle drei Werte dasselbe Ergebnis wie `zahl()` findet.

## 728. Eine `.pfm` mit falschem Grundaufbau öffnet sich mit der Absturzmeldung statt mit „beschädigt“

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** Eine `.pfm`, die nur `[]` oder `7` enthält, deren `properties` eine Zahl ist oder deren `children` keine Liste ist, wirft beim Öffnen über den Projekt-Explorer `AttributeError` („'list' object has no attribute 'get'“) bzw. `TypeError` („'float' object is not iterable“). Erwartet ist die Statuszeile „… lässt sich nicht öffnen, die Datei ist beschädigt“; in der installierten Fassung kommt die allgemeine Meldung „In Natter ist etwas schiefgegangen“.

**Ursache:** nachgewiesen. `formular_fuer_designer_laden` ruft `_zahlen_pruefen` (`ide/designer/laden.py:192-206`, Aufruf in Zeile 212) vor der Schema-Prüfung auf; die Funktion setzt ein Objekt mit `properties` als Objekt und `children` als Liste voraus. Die `except`-Liste in `HauptFenster.oeffnen` (`ide/shell/hauptfenster.py:8641-8644`) kennt weder `AttributeError` noch `TypeError`. Nachweis: `build/auswertung/pruefung_42d5478/C/728_pfm_grundaufbau.py` (4 Fälle).

**Zu tun:** Die Grundform prüfen, bevor `_zahlen_pruefen` läuft, oder das Schema zuerst anwenden. Erledigt, wenn alle vier Fälle des Nachweises „beschädigt“ melden.

## 729. Werte in einer `.pfm`, die das Schema zulässt, ergeben ungültigen Formular-Code

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** Vier Fälle enden beim Öffnen im Designer in der Absturzmeldung statt in „beschädigt“: `NaN` oder `Infinity` als Wert (Python liest beides als JSON) ergibt im erzeugten Code `nan` und `NameError`; ein Menüeintrag, der nur `children` hat, ergibt `{, "children": [` und `SyntaxError`; `children` eines Menüeintrags als Zahl ergibt `TypeError`; ein Eigenschaftswert mit 500 ineinander liegenden Listen ergibt `RecursionError`. Der letzte Fall ist die Lücke in Punkt 548: dort ist nur die Tiefe der Komponenten begrenzt.

**Ursache:** nachgewiesen. `_python_literal` (`ide/codegen/design.py:150-184`) schreibt Kommazahlen mit `repr` und steigt ohne Grenze in Listen und Objekte ab; `_eintrag_zeilen` (Zeile 241-247) setzt den Kopf eines Eintrags auch ohne Felder vor `"children"` zusammen und geht in Zeile 263 ungeprüft über `children`. `_tiefe_pruefen` (Zeile 109-120) zählt nur `children` der Komponenten. Nachweis: `build/auswertung/pruefung_42d5478/C/729_pfm_codeerzeugung.py`.

**Zu tun:** Nicht endliche Zahlen, Menüeinträge ohne Beschriftung, `children` ohne Liste und zu tiefe Werte in `pfm_pruefen` ablehnen. Erledigt, wenn alle vier Fälle des Nachweises „beschädigt“ melden.

## 730. Ein Diagramm mit einer Lage oder Größe über 2.147.483.647 öffnet sich mit der Absturzmeldung

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** Ein `.pdiag`, in dem bei einer Form `h` = `1e308` oder `w` bzw. `x` = `2147483648` steht, lässt sich nicht öffnen: `OverflowError` beim Bau des Diagrammfensters, weitere aus der Ereignisschleife beim Zeichnen. Erwartet ist „beschädigt“ wie bei einer `.pfm` mit zu großer Zahl (Punkt 444). Der Export als Bild scheitert an einer Form mit `y` unter -2.147.483.648 ebenso.

**Ursache:** nachgewiesen. Das Schema begrenzt die Zahlen nicht; `setMinimumSize` in `ide/diagramm/zoom.py:84` und `QSize` in `ide/diagramm/export.py:211` nehmen nur 32-Bit-Werte. `HauptFenster.oeffnen` (`ide/shell/hauptfenster.py:8641-8644`) fängt `OverflowError` nicht. Nachweis: `build/auswertung/pruefung_42d5478/C/730_pdiag_grosse_zahl.py`.

**Zu tun:** Lage und Größe beim Laden auf einen Bereich begrenzen oder die Datei als beschädigt melden. Erledigt, wenn die drei Fälle des Nachweises „beschädigt“ melden.

## 731. Ein unpassender Wert in der Einstellungsdatei verhindert den Start

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** Steht in `Natter-IDE.ini` `thema=dunkel` (statt `dark`), `layout=abc` oder `fuer_konsole_verborgen=@Rect(0 0 1 1)`, entsteht das Hauptfenster nicht: `NatterPropertyError` „theme erwartet 'system', 'light' oder 'dark' …“ bzw. `TypeError` aus `restoreState` und `set()`. Natter startet dann gar nicht, bis jemand die Datei von Hand berichtigt oder löscht; an einem Schulrechner kann das eine Schülerin nicht.

**Ursache:** nachgewiesen. `HauptFenster.__init__` übernimmt `design/thema` ungeprüft (`ide/shell/hauptfenster.py:1067`, geprüft erst in `pcl/theme/__init__.py:79` über `_stil_anwenden`), gibt `fenster/layout` ohne Typprüfung an `restoreState` (Zeile 1493-1495) und macht aus `fenster/fuer_konsole_verborgen` ohne Prüfung eine Menge (Zeile 1498-1503). Für `fenster/geometrie` gibt es diese Prüfung schon (Zeile 6629-6633). Nachweis: `build/auswertung/pruefung_42d5478/C/731_einstellungen_start.py` (3 Fälle).

**Zu tun:** Jeden gelesenen Wert auf Typ und erlaubte Werte prüfen und sonst den Standard nehmen. Erledigt, wenn das Hauptfenster in allen drei Fällen entsteht.

## 732. CSV-Import: ein Feld mit mehr als 4300 Ziffern endet in der Absturzmeldung

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** „CSV importieren …“ im Datenbank-Panel mit einer Datei, in der ein Feld aus 5000 Ziffern besteht, wirft `ValueError: Exceeds the limit (4300 digits) for integer string conversion` statt „Die CSV-Datei ließ sich nicht importieren“. Die übrigen 123 Abwandlungen der Probe (leer, BOM, ANSI, UTF-16, Binärmüll, 3000 Spalten, Felder von 2 MB) melden sich richtig.

**Ursache:** nachgewiesen. `_zahlenart` (`ide/database/panel.py:110`) ruft `int(wert)` für jede Ziffernfolge; `_csv_importieren_dialog` (Zeile 1267-1268) fängt `ValueError` nicht. Nachweis: `build/auswertung/pruefung_42d5478/C/732_csv_lange_zahl.py`.

**Zu tun:** Ziffernfolgen über 19 Stellen ohne Umwandlung als Text werten. Erledigt, wenn der Nachweis besteht und die Spalte als TEXT angelegt wird.

## 733. StringGrid: `row_count` und `col_count` ohne Obergrenze belegen beliebig viel Speicher

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** `row_count = 10**7` belegt im Schülerprogramm 1,2 GB und braucht 4 Sekunden; `row_count = 2**31` wuchs über 3 GB, bis die Probe den Prozess beendete. Ein Tippfehler in einer Eingabe, aus der die Zeilenzahl kommt, legt so einen Schulrechner lahm. Punkt 356 hat den Speicher je Zeile verkleinert, Punkt 449 die Untergrenze eingeführt; eine Obergrenze fehlt.

**Ursache:** nachgewiesen. `row_count` und `col_count` (`pcl/components/additional.py:281-286`) haben nur `minimum=0`; `_bei_prop_aenderung` (Zeile 411-414) reicht jeden Wert an `setRowCount`/`setColumnCount` weiter. Nachweis: `build/auswertung/pruefung_42d5478/C/733_stringgrid_zeilenzahl.py`, Messreihe in `sg.log`.

**Zu tun:** Eine Höchstzahl festlegen und darüber mit `NatterPropertyError` und deutscher Meldung ablehnen, in `docs/komponenten.md` nennen. Erledigt, wenn der Nachweis besteht.

## 734. Zahlen außerhalb des Bereichs von Qt: rohes `OverflowError`, und der Wert bleibt in der Eigenschaft stehen

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** `self.lbl.left = 2**31` im Schülerprogramm endet in `OverflowError` ohne Text; danach liefert `lbl.left` den neuen Wert, das Widget steht am alten Platz. Dasselbe gilt für 470 Kombinationen aus Komponente und Eigenschaft (Lage und Größe aller Komponenten, `minimum`/`maximum`/`position`, `item_index`, `Timer.interval`, `Edit.max_length`, `FloatSpinEdit.decimals`). Andere unpassende Werte lehnt `Prop` mit deutscher Meldung ab, bevor etwas gespeichert ist. Zusätzlich: `FloatSpinEdit.minimum = float("nan")` löst `on_change` rund 250-mal aus und endet in `RecursionError`.

**Ursache:** nachgewiesen. `Prop.__set__` (`pcl/properties.py:216`) speichert den Wert, bevor `_bei_prop_aenderung` ihn an Qt gibt (etwa `pcl/control.py:651`, `setGeometry`). Bei `FloatSpinEdit` wechseln sich `_bei_wertaenderung` (`pcl/components/additional.py:763`) und das Zurücklesen ab Zeile 783 ab, weil `nan` nie gleich `nan` ist. Nachweis: `build/auswertung/pruefung_42d5478/C/734_zahl_ausserhalb_des_bereichs.py`, Gesamtliste in `rand.log` (`probe_randwerte.py`).

**Zu tun:** Ganze Zahlen über 2.147.483.647 und unter -2.147.483.648 sowie `nan` in `Prop` mit `NatterPropertyError` ablehnen, bevor gespeichert wird. Erledigt, wenn beide Fälle des Nachweises eine deutsche Meldung bekommen und der alte Wert stehen bleibt.

## 735. Designer: ein Menü, dessen Einträge Methoden aufrufen, lässt sich nicht kopieren oder duplizieren

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** In einer Kopie von `10_Notizbuch` endet Strg+C, Strg+V oder Strg+D auf dem Hauptmenü `mm_haupt` mit `NatterUnbekannteEigenschaftError` „Der Menüeintrag „Neu“ soll beim Anklicken die Methode 'mi_neu_click' aufrufen, aber _EinfuegenDesign hat keine Methode mit diesem Namen.“, in der installierten Fassung mit der allgemeinen Meldung. Aufgefallen in 15 von 50 Zufallsfolgen der Rückgängig-Probe; ohne diesen Handgriff ergaben alle 50 Folgen nach vollständigem Rückgängig und Wiederholen genau Anfang und Ende.

**Ursache:** nachgewiesen. `_ereignisse_entfernen` (`ide/designer/canvas.py:402-405`) nimmt nur `events` heraus, nicht das `on_click` in den Menüeinträgen; `_eintraege_bauen` (um Zeile 2061) baut die Kopie in einer Zwischenklasse ohne die Methoden des Formulars, und `MainMenu.entries` prüft die Methoden, weil die Zwischenklasse kein `_entwurfsansicht` trägt (`pcl/components/menus.py:577-589`). Nachweis: `build/auswertung/pruefung_42d5478/C/735_menue_kopieren.py`, Zufallsfolgen in `probe_undo_designer.py`.

**Zu tun:** Methodennamen in Menüeinträgen wie Ereignisse behandeln: vor dem Zwischenbau herausnehmen und danach verknüpfen, wenn es die Methode im Zielformular gibt. Erledigt, wenn beide Fälle des Nachweises ein Menü mit verknüpften Einträgen ergeben.

## 736. Formular-Import (.lfm): eine Fortsetzungszeile, die mit `+'…'` beginnt, wird weiter abgelehnt (Rückfall zu Punkt 549)

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** Punkt 549 nennt unter „Beobachtet“ eine Fortsetzungszeile mit `+'…'`. Eine Beschriftung, die über zwei Zeilen geht und deren zweite Zeile mit `+'weitergeht'` beginnt, ergibt weiter „Import fehlgeschlagen: Unerwartete Zeile in Objekt 'Label1' … Ist die gewählte Datei wirklich ein Formular im .lfm-Format?“. Lange Texte stehen im `.lfm`-Format in dieser Form; ein Formular mit einem solchen Text lässt sich nicht importieren.

**Ursache:** nachgewiesen. `_zeichenkette` (`ide/import_lfm/parser.py:85-127`) erkennt `+` nur am Ende einer Zeile (Zeile 122), `_zeichenkette_lesen` sieht danach nur in der nächsten Zeile nach. Der Test zu Punkt 549 (`test_zeichenketten_wie_lazarus_sie_schreibt` in `tests/test_lfm_parser.py`) prüft nur diese Form. Nachweis: `build/auswertung/pruefung_42d5478/C/736_lfm_plus_am_zeilenanfang.py`.

**Zu tun:** Auch eine Folgezeile annehmen, die mit `+` und einer Zeichenkette beginnt. Erledigt, wenn der Nachweis besteht und der vorhandene Test weiter grün ist.

## 758. Eine Klausur auf Grundlage eines Beispiels lässt sich im Prüfungsmodus nicht öffnen

**Gemeldet:** 24. November 2026, Prüfung D (Sicht der Lehrkraft),
Stand `42d5478`.

**Beobachtet:** Eine Lehrkraft baut eine Klausur aus
`06_Kontoverwaltung`: Ordner und Projektdatei heißen „Klausur“,
`u_main.py` trägt die Aufgabe, die Klasse `u_konto.py` und das
Klassendiagramm bleiben unverändert, weil sie erweitert werden sollen.
Die Klausur liegt in einem Tauschordner nur zum Lesen. Im
Prüfungsmodus öffnet eine Schülerin sie über „Projekt öffnen …“. Statt
der eigenen Kopie kommt „Beispielprojekt gesperrt“ mit dem Text
„„Klausur“ ist ein mitgeliefertes Beispielprojekt oder eine Kopie
davon. Während des Prüfungsmodus nicht verfügbar. Er läuft nach vier
Stunden von selbst aus.“ Das Projekt geht nicht auf, eine Kopie
entsteht nicht. Der Modus lässt sich vier Stunden lang nicht beenden,
die Klausur kann an diesem Tag also nicht in Natter geschrieben
werden. Die Meldung nennt nicht, welche Datei die Sperre auslöst, und
vorher prüfen kann die Lehrkraft das nur, indem sie den Modus im
eigenen Konto für vier Stunden einschaltet. Handbuch 4 beschreibt die
Erkennung am Inhalt, sagt aber nicht, dass eine Aufgabe mit einer
unveränderten Unit oder einem unveränderten Diagramm aus einem
Beispiel davon getroffen wird.

**Ursache:** nachgewiesen: `beispiel_nach_inhalt` in
`ide/shell/startbild.py:431` erkennt den Ordner an `u_konto.py`,
`_beispiel_projektordner` in `ide/shell/hauptfenster.py:644` sperrt ihn
deshalb. Nachweis:
`build\auswertung\pruefung_42d5478\D\758_klausur_aus_beispiel.py`.

**Zu tun:** Die Lehrkraft muss vor der Klausur erfahren, dass Natter
ihre Aufgabe im Prüfungsmodus sperren wird, und die Meldung im Modus
muss die auslösende Datei nennen. Handbuch 4 nennt den Fall bei den
Hinweisen für die Aufsicht. Erledigt, wenn die Probe entweder die
Klausur im Prüfungsmodus als eigene Kopie öffnet oder Natter beim
Öffnen der Aufgabe außerhalb des Modus darauf hinweist und die Meldung
im Modus `u_konto.py` nennt.

## 759. Lösung und Notizen der Lehrkraft im Aufgabenordner landen in jeder Schülerkopie

**Gemeldet:** 24. November 2026, Prüfung D (Sicht der Lehrkraft),
Stand `42d5478`.

**Beobachtet:** Im Aufgabenordner „Ampel“ eines Tauschordners nur zum
Lesen liegen neben der Aufgabe `loesung.py`, ein versteckter Ordner
`.lehrkraft` mit einer Notiz zur Bewertung, ein Unterordner `loesung`
mit einer fertigen `u_main.py` und der Ordner `dist` mit einer Exe aus
„Als Exe exportieren“. „Eigene Kopie öffnen“ kopiert alles davon nach
`Dokumente\Natter\Ampel`. Der Projekt-Explorer der Schülerin zeigt
`loesung.py` unter „Units“, die übrigen Dateien liegen im Ordner und
sind im Windows-Explorer zu sehen. Die Abgabe-ZIP lässt versteckte
Einträge, `build` und `dist` weg, die Kopie der Aufgabe nicht.
Handbuch 3.6 sagt nicht, dass Lösung und Notizen nicht in den
Aufgabenordner gehören.

**Ursache:** nachgewiesen: `_NICHT_MITKOPIEREN` in
`ide/shell/startbild.py:187` nimmt nur `__pycache__`, `*.pyc`,
Sperrdatei, Quelldatei und Sicherung aus; `zip_schreiben` in
`ide/shell/hauptfenster.py:771` lässt zusätzlich versteckte Einträge,
`build` und `dist` weg. `Projekt.units` in `ide/project/projekt.py:232`
zeigt jede `.py` im Projektordner. Nachweis:
`build\auswertung\pruefung_42d5478\D\759_loesung_in_kopie.py`.

**Zu tun:** Beim Kopieren einer Aufgabe dieselben Einträge weglassen
wie in der Abgabe-ZIP und in Handbuch 3.6 festhalten, dass alles
Übrige im Aufgabenordner zu jeder Schülerin kopiert wird. Erledigt,
wenn die Probe in der Kopie weder `.lehrkraft` noch `dist` findet und
das Handbuch den Satz enthält.

## 760. Druckt die Lehrkraft eingesammelte Abgaben als Quelltext-PDF, steht ihr eigener Name darauf

**Gemeldet:** 24. November 2026, Prüfung D (Sicht der Lehrkraft),
Stand `42d5478`.

**Beobachtet:** Die Lehrkraft entpackt zwei Abgaben
(`Ampel - schueler01 - PC-R01.zip`, `Ampel - schueler02 - PC-R02.zip`),
öffnet sie nacheinander und wählt „Projekt → Quelltext als PDF …“. Die
Kopfzeile beider PDFs lautet „Ampel – u_main.py – <Name der Lehrkraft>
– 24.11.2026“: der Name kommt aus der Anmeldung am Rechner der
Lehrkraft, der Projektname ist bei der ganzen Klasse gleich, und der
Ordnername der Abgabe mit dem Konto der Schülerin steht nirgends.
Beim Entpacken in einen gemeinsamen Ordner schlägt Natter für beide
Abgaben denselben Dateinamen `Ampel Quelltext.pdf` vor. Handbuch 3.6
begründet die Kopfzeile damit, dass bei zwanzig eingesammelten
Abgaben sonst nicht zu erkennen ist, welche zu wem gehört; das gilt
nur, wenn die Schülerinnen das PDF selbst erzeugen.

**Ursache:** nachgewiesen: `quelltext_als_pdf` in
`ide/export/quelltext_pdf.py:344` nimmt `anmeldename()` des
angemeldeten Kontos, `seitenkoepfe` (Zeile 289) den Projektnamen aus
der `.natter`; `_quelltext_als_pdf_aktion` in
`ide/shell/hauptfenster.py:2752` schlägt `<Projektname> Quelltext.pdf`
vor. Nachweis:
`build\auswertung\pruefung_42d5478\D\760_pdf_kopfzeile.py`.

**Zu tun:** Bei einer entpackten Abgabe muss Kopfzeile und
vorgeschlagener Dateiname die Abgabe erkennen lassen, etwa über den
Namen ihres Ordners. Erledigt, wenn die Probe für die beiden Abgaben
verschiedene Dateinamen vorgeschlagen bekommt und in jeder Kopfzeile
das Konto der Schülerin steht.

## 761. Am Beamer mit 1280 × 800 bei 125 % ist im Designer schon das Formular eines neuen Projekts abgeschnitten

**Gemeldet:** 24. November 2026, Prüfung D (Sicht der Lehrkraft),
Stand `42d5478`.

**Beobachtet:** Hauptfenster mit dem Beispiel 03_Taschenrechner im
Designer, logische Fenstergröße abzüglich Taskleiste und Titelleiste.
Sichtbare Fläche des Designers:

| Beamer 1280 × 800 | Fenster | Designer sichtbar |
|---|---|---|
| 100 % | 1280 × 720 | 872 × 424 |
| 125 % | 1024 × 576 | 604 × 280 |
| 150 % | 853 × 480 | 433 × 172 |
| 125 %, Oberfläche 14 pt | 1024 × 576 | 604 × 239 |

Ein neues GUI-Projekt hat ein Formular von 480 × 360, der
Taschenrechner 520 × 340, die Beispiele 04 bis 09 sind 560 bis 640
hoch. Bei 125 % fehlen dem leeren Formular 80 Pixel Höhe, beim
Taschenrechner liegen die Rechenknöpfe bei 150 % unter dem Rand
(`beamer_125_designer.png`, `beamer_150_designer.png`). Die
Vergrößerung der Oberfläche, die Handbuch 6 („Schrift am Beamer zu
klein“) empfiehlt, nimmt dem Designer weitere 41 Pixel. Komponentenpalette
und Panels belegen zusammen rund 200 Pixel Höhe. Punkt 348 hat das nur
für Konsolenprojekte gelöst.

**Ursache:** nachgewiesen: Aufteilung der Docks in
`ide/shell/hauptfenster.py`, geprüft wird sie nur für 1366 × 768
(`tests/test_schulrechner_layout.py`). Nachweis:
`build\auswertung\pruefung_42d5478\D\761_beamer_designer.py` mit den
Bildschirmfotos `beamer_*.png` daneben.

**Zu tun:** Dem Designer bei kleiner logischer Fenstergröße mehr Höhe
lassen. Erledigt, wenn die Probe bei 1024 × 576 eine sichtbare
Designerfläche von mindestens 480 × 360 misst, ohne dass ein Dock von
Hand geschlossen wurde.

## 762. „Datei → Zuletzt geöffnet“ zeigt eingesammelte Abgaben alle unter demselben Namen

**Gemeldet:** 24. November 2026, Prüfung D (Sicht der Lehrkraft),
Stand `42d5478`.

**Beobachtet:** Die Lehrkraft öffnet vier entpackte Abgaben
nacheinander. Die Startseite listet sie als
„Ampel - schueler04 - PC-R04“ bis „Ampel - schueler01 - PC-R01“, das
Menü „Datei → Zuletzt geöffnet“ viermal als „Ampel“. Welcher Eintrag zu
wem gehört, steht nur in der Statuszeile beim Überfahren.

**Ursache:** nachgewiesen: `_zuletzt_menue_aufbauen` in
`ide/shell/hauptfenster.py:6301` beschriftet mit `pfad.stem`, dem Namen
der Projektdatei; die Startseite nimmt `eindeutige_namen` aus
`ide/shell/startbild.py:156` mit dem Ordnernamen. Nachweis:
`build\auswertung\pruefung_42d5478\D\762_zuletzt_menue.py`.

**Zu tun:** Das Menü so beschriften wie die Startseite. Erledigt, wenn
die Probe vier verschiedene Einträge findet.

## 763. Gleichnamige Aufgaben aus verschiedenen Wochen bekommen je nach Reihenfolge „Aufgabe“ oder „Aufgabe 2“

**Gemeldet:** 24. November 2026, Prüfung D (Sicht der Lehrkraft),
Stand `42d5478`.

**Beobachtet:** Die Lehrkraft legt jede Woche einen Ordner an,
`Tausch\8b\Woche1\Aufgabe` und `Tausch\8b\Woche2\Aufgabe`. Ben öffnet
beide, Anna fehlte in Woche 1 und öffnet nur Woche 2. Bens Kopie von
Woche 2 heißt `Aufgabe 2`, Annas `Aufgabe`. Die Abgaben zu Woche 2
heißen damit „Aufgabe 2 - ben - PC-R01“ und „Aufgabe - anna - PC-R01“;
Annas trägt denselben Namensanfang wie Bens Abgabe aus Woche 1. Aus dem
Namen einer Abgabe lässt sich nicht ablesen, zu welcher Woche sie
gehört.

**Ursache:** nachgewiesen: `aufgabe_kopieren` in
`ide/shell/startbild.py:760` benennt die Kopie nach dem Ordner der
Aufgabe und zählt bei einem belegten Namen hoch; `abgabe_name` in
`ide/shell/hauptfenster.py:680` übernimmt den Ordnernamen der Kopie.
Nachweis:
`build\auswertung\pruefung_42d5478\D\763_gleichnamige_aufgaben.py`.

**Zu tun:** Die Kopie einer Aufgabe so benennen, dass gleichnamige
Aufgaben aus verschiedenen Ordnern unterscheidbar bleiben, oder in
Handbuch 3.6 eindeutige Ordnernamen für Aufgaben verlangen. Erledigt,
wenn die Probe für Woche 2 bei beiden Konten denselben Namensanfang
findet oder das Handbuch den Satz enthält.

## 788. Ein Formular, das nicht in die Datei kam, geht beim Schließen von Natter ohne Nachfrage verloren

**Gemeldet:** 24. November 2026, Prüfung E (Schülersicht, Sicherung und Gleichzeitigkeit), Stand `42d5478`.

**Beobachtet:** Zwei Wege führen dahin. Erstens zwei Natter auf demselben Projekt, etwa weil die `.natter` zweimal doppelgeklickt wurde: In B ist der Designer offen, A setzt einen Knopf und schreibt die `.pfm`. B lädt das Formular nicht nach. Setzt B danach ein Label, fragt der Designer „… Mit der Änderung aus dem Designer überschreiben? …“ mit vorgewähltem „Nein“; danach steht das Label nur im Designer, der Reiter heißt „u_main (Designer) ●“. Zweitens lässt sich die `.pfm` nicht schreiben (USB-Stick gezogen, Netzlaufwerk weg, Datei gesperrt). Nach dem Platzieren eines Knopfs kommt einmal die Meldung „„u_main.pfm“ konnte nicht gespeichert werden …“, der Reiter heißt „u_main (Designer) ●“. Wird danach das Fenster von Natter geschlossen, kommt keine Frage: Natter geht zu, die Änderung ist weg, die `.pfm` ist auf dem alten Stand. Beim Schließen des einzelnen Reiters wird dagegen gefragt (Punkt 235). Bei **Projekt → Projekt schließen** kommt nur die Frage des Reiters; „Abbrechen“ darin schließt das Projekt trotzdem, und der Designer-Reiter mit „●“ bleibt ohne Projekt stehen. In die Sicherung `<Projekt>.natter-sicherung` kommt die Formularänderung nie, auch nach einem Absturz ist sie verloren. Im ersten Weg schließt B ebenso ohne Frage, und das Label ist weg.

**Ursache:** nachgewiesen (`build/auswertung/pruefung_42d5478/E/788_formular_schliessen.py`, mit zwei echten Natter-Prozessen `788_designer_zwei_prozesse.py`). `_ungespeicherte_namen` in `ide/shell/hauptfenster.py:6729` zählt nur Editoren und Diagramme, nicht Designer mit `ungespeichert`; `closeEvent` (Zeile 6688) fragt nur danach. `_vorheriges_projekt_schliessen` fragt ebenso nicht nach Designern und überlässt sie `_reiter_schliessen_wenn` (Zeile 4774), das die Antwort „Abbrechen“ von `_tab_schliessen` nicht auswertet. `_sicherung_eintraege` (Zeile 6868) kennt nur Editoren und Diagramme. Der Designer bemerkt eine von außen geänderte `.pfm` erst beim nächsten eigenen Schreiben (`DesignerCanvas.speichern`, `ide/designer/canvas.py:3154`), anders als ein Editor beim Wechsel ins Fenster (`_von_aussen_geaenderte_neu_laden`).

**Zu tun:** Designer mit nicht geschriebener Änderung gehören in die gemeinsame Nachfrage beim Schließen des Fensters, beim Schließen und beim Wechsel des Projekts; „Abbrechen“ lässt das Projekt offen. Ihr Formular kommt als eigener Eintrag in die Sicherung. Ein Designer ohne eigene ungeschriebene Änderung lädt eine von außen geänderte `.pfm` beim Wechsel ins Fenster neu. Erledigt, wenn beide Nachweise die Frage beim Schließen finden, nach „Abbrechen“ Projekt und Reiter offen bleiben und die Sicherung die `.pfm` enthält.

---

## 789. „Speichern unter …“ an einen Ort außerhalb des Projekts lässt den Reiter still dort weiterarbeiten

**Gemeldet:** 24. November 2026, Prüfung E (Schülersicht, Datei wiederfinden), Stand `42d5478`.

**Beobachtet:** `u_main.py` geändert und mit **Datei → Speichern unter …** versehentlich auf den Desktop gelegt. Der Reiter heißt weiter „u_main.py“ und schreibt ab jetzt auf den Desktop. Die Unit im Projektordner bleibt auf dem alten Stand; das Programm startet diesen Stand, und die Abgabe-ZIP enthält ihn. Was danach getippt wird, kommt nicht mehr in die Sicherung des Projekts. Ein Doppelklick auf `u_main.py` im Projekt-Explorer öffnet einen zweiten Reiter mit demselben Namen und dem alten Text. Die Statusleiste nennt nur „Gespeichert als C:\…\Desktop\u_main.py.“; ein Hinweis, dass die Datei jetzt nicht mehr zum Projekt gehört, fehlt.

**Ursache:** nachgewiesen (`build/auswertung/pruefung_42d5478/E/789_speichern_unter_desktop.py`). `editor_speichern_unter` in `ide/shell/hauptfenster.py:5527` setzt den Pfad des Reiters ohne Prüfung auf das neue Ziel; `_sicherung_eintraege` (Zeile 6868) lässt Dateien außerhalb des Projektordners aus.

**Zu tun:** Liegt das Ziel außerhalb des offenen Projekts, vorher darauf hinweisen, dass das Programm weiter die Unit im Projekt benutzt, und den Reiter so beschriften, dass er sich von der Unit des Projekts unterscheidet (etwa mit dem Ordner). Erledigt, wenn der Nachweis die Nachfrage findet und zwei Reiter verschiedener Dateien nicht mehr gleich heißen.

---

## 790. Speichern auf einem abgezogenen USB-Stick oder vollen Datenträger meldet englischen Rohtext mit dem Namen der Zwischendatei

**Gemeldet:** 24. November 2026, Prüfung E (Schülersicht, Störungen beim Speichern), Stand `42d5478`.

**Beobachtet:** Projektordner während der Arbeit entfernt (USB-Stick gezogen), dann Strg+S: „„u_main.py“ konnte nicht gespeichert werden: [Errno 2] No such file or directory: 'C:\…\.u_main.py.25268.tmp'“. Bei vollem Datenträger: „[Errno 28] No space left on device“. Die Zwischendatei kennt niemand, der Text ist englisch, und unter „Häufige Gründe“ fehlt der volle Datenträger. Anders als bei verweigertem Schreibrecht wird kein „Speichern unter …“ angeboten, obwohl das hier der einzige Weg ist, den Text zu retten. Die alte Datei bleibt erhalten, der Text steht weiter im Editor, eine Zwischendatei bleibt nicht liegen. Dieselbe Rohmeldung zeigt der Designer, wenn er die `.pfm` nicht schreiben kann. Eine Datei, die ein anderes Programm offen hält, wird dagegen verständlich gemeldet und bietet „Speichern unter …“ an.

**Ursache:** nachgewiesen (`build/auswertung/pruefung_42d5478/E/790_speicherfehler_meldung.py`). `datei_schreiben_gemeldet` in `ide/shell/hauptfenster.py:5911` setzt im Zweig für `OSError` den Text des Fehlers unverändert ein und reicht `unter` nicht weiter; ebenso `DesignerCanvas.speichern` in `ide/designer/canvas.py:3176`. Punkt 321 hatte das nur für `PermissionError` geändert.

**Zu tun:** Für fehlenden Ordner, Laufwerk oder Netzpfad und für vollen Datenträger einen deutschen Satz ohne die Zwischendatei, dazu „Speichern unter …“ wie beim verweigerten Schreiben. Erledigt, wenn der Nachweis kein „Errno“ und kein „.tmp“ mehr findet und das Angebot erscheint.

---

## 791. Eine Änderung nur an einem Diagramm kommt erst nach bis zu zwei Minuten in die Sicherung

**Gemeldet:** 24. November 2026, Prüfung E (Schülersicht, Sicherung), Stand `42d5478`.

**Beobachtet:** Struktogramm oder Klassendiagramm geändert, keine Unit angefasst, Natter sieben Sekunden später hart beendet (`taskkill /F`, wie Task-Manager oder Stromausfall). Im Projektordner liegt keine Sicherung, beim nächsten Öffnen kommt keine Frage, die Änderung ist verloren. Mit einer gleichzeitig geänderten Unit kommt das Diagramm mit in die Sicherung und wird vollständig wiederhergestellt. Punkt 473 hat den Zwei-Minuten-Takt für Diagramme bewusst gelassen; wer eine Stunde lang nur ein Struktogramm zeichnet, verliert bei einem Absturz aber bis zu zwei Minuten Arbeit.

**Ursache:** nachgewiesen (`build/auswertung/pruefung_42d5478/E/791_diagramm_sicherung.py`, echter harter Abbruch in `probe_hart_beenden.py` im selben Ordner). Nur `contentsChanged` der Editoren startet `_sicherung_bald` (`ide/shell/hauptfenster.py:5447`); `DiagrammFenster._bei_aenderung` (`ide/diagramm/fenster.py:678`) meldet dem Hauptfenster nichts.

**Zu tun:** Jede Änderung in einem Diagrammfenster startet `_sicherung_bald` wie eine Änderung im Editor. Handbuch Abschnitt 6 entsprechend anpassen. Erledigt, wenn der Nachweis nach einer Diagrammänderung die laufende Uhr findet und der harte Abbruch das Diagramm anbietet.

---

## 792. „Projekt schließen“ beendet ein laufendes Programm ohne Nachfrage, ein Projektwechsel lässt es weiterlaufen

**Gemeldet:** 24. November 2026, Prüfung E (Schülersicht, Fehlgriffe), Stand `42d5478`.

**Beobachtet:** Programm läuft, dann **Projekt → Projekt schließen**: das Programm wird ohne Frage beendet, was darin eingegeben war, ist weg. Beim Schließen des Fensters fragt Natter seit Punkt 433 („Das Programm läuft noch. Beenden und Natter schließen?“). Beim Öffnen eines anderen Projekts wird weder gefragt noch beendet; das Programm des alten Projekts läuft neben dem neuen weiter.

**Ursache:** nachgewiesen (`build/auswertung/pruefung_42d5478/E/792_projekt_schliessen_programm.py`). `projekt_schliessen` in `ide/shell/hauptfenster.py:4334` ruft `kindprozesse_beenden` ohne `_laufendes_programm_fragen`; `projekt_oeffnen` (Zeile 4259) tut keins von beiden.

**Zu tun:** Schließen und Wechseln des Projekts fragen bei laufendem Programm wie das Schließen des Fensters; nach „Beenden“ endet das Programm in beiden Fällen, nach „Abbrechen“ bleibt alles, wie es war. Erledigt, wenn der Nachweis in beiden Fällen die Frage findet.

---

## 793. Beim Löschen einer Unit geht ihr ungespeicherter Text verloren, obwohl die Nachfrage den Papierkorb verspricht

**Gemeldet:** 24. November 2026, Prüfung E (Schülersicht, Fehlgriffe), Stand `42d5478`.

**Beobachtet:** Unit `u_rechnen.py` geöffnet, Zeilen getippt, nicht gespeichert, dann im Projekt-Explorer **⋮ → Löschen …**. Die Nachfrage lautet „„u_rechnen.py“ wirklich löschen? Die Dateien landen im Papierkorb und lassen sich von dort zurückholen.“ Im Papierkorb liegt der Stand der Platte; der getippte Text ist weder dort noch in der Sicherung. Wer die falsche Unit erwischt, bekommt aus dem Papierkorb nur einen älteren Stand zurück, und die Nachfrage sagt nichts davon.

**Ursache:** nachgewiesen (`build/auswertung/pruefung_42d5478/E/793_unit_loeschen_ungespeichert.py`). `_unit_loeschen` in `ide/shell/hauptfenster.py:3886` schließt den Reiter über `_reiter_schliessen_wenn`, das den Editor vorher als unverändert setzt; die Nachfrage (Zeile 3875) prüft nicht, ob die Unit ungespeichert offen ist.

**Zu tun:** Ist die Unit mit ungespeicherten Änderungen offen, steht das in der Nachfrage, und in den Papierkorb kommt der Text aus dem Editor. Erledigt, wenn der Nachweis den getippten Text im Papierkorb und den Hinweis in der Nachfrage findet.

---

## 794. Schließt das erste von zwei Natter auf einem Projekt, gilt das Projekt als nicht mehr offen

**Gemeldet:** 24. November 2026, Prüfung E (Schülersicht, Gleichzeitigkeit), Stand `42d5478`.

**Beobachtet:** Projekt in Natter A offen, dann in einem zweiten Natter B (echter zweiter Prozess). B bekommt richtig den Hinweis, dass A das Projekt offen hat. Wird A geschlossen, verschwindet `.natter-sperre`, obwohl B weiterarbeitet, und auch die Erneuerung alle fünf Minuten legt sie nicht wieder an. Ein drittes Natter, an diesem oder einem anderen Rechner, bekommt keinen Hinweis mehr. Das trifft auch die Sicherung: Arbeitet die Partnerin aus einem anderen Konto an Rechner R1 noch mit ungespeichertem Text, während die Sperrdatei fehlt, bietet Natter an Rechner R2 diesen Text als „Sicherung ungespeicherter Änderungen … Natter wurde damals beendet …“ an, setzt ihn nach „Wiederherstellen“ in den eigenen Editor und entfernt den Anteil der Partnerin aus der Sicherung. Laut Handbuch Abschnitt 6 bleibt die Sicherung eines anderen Kontos liegen, solange dessen Rechner das Projekt offen hat.

**Ursache:** nachgewiesen (`build/auswertung/pruefung_42d5478/E/794_sperre_geht_verloren.py`, zwei echte Natter-Prozesse und ein vorgetäuschter zweiter Rechner). `projekt_oeffnen` in `ide/shell/hauptfenster.py:4288` legt bei einem anderen Besitzer keine eigene Sperre an; `sperre.freigeben` (`ide/project/sperre.py:254`) entfernt beim Schließen von A die Datei, und `sperre.erneuern` (Zeile 247) erneuert nur eine Sperre, die schon dem eigenen Prozess gehört. `sicherung.laeuft` (`ide/project/sicherung.py:184`) entscheidet für ein fremdes Konto an einem anderen Rechner allein über `sperre.anderer_besitzer`.

**Zu tun:** Ein Natter, das ein Projekt ohne eigene Sperre offen hat, trägt sich ein, sobald die Sperrdatei fehlt oder abgelaufen ist (spätestens beim nächsten Erneuern), und `freigeben` entfernt nur den eigenen Eintrag. Erledigt, wenn der Nachweis nach dem Schließen von A die Sperre von B findet und R2 den Anteil der Partnerin nicht anbietet.


# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
