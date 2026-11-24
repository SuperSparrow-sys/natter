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


# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
