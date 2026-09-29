# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **423**.

## Ein neuer Punkt

```markdown
## 423. Kurz, was nicht stimmt

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

## 416. Ein Knopf der Taskleiste zeigt noch das leere Fenstersymbol

**Gemeldet:** 29. September 2026, Prüfung der neu gebauten Fassung 0.4.2 (`build\auswertung\042b\`, Bilder `03_e_taskleiste_drittel2.png`, `03_i_taskleiste_aus_bildschirm_lupe.png`), nicht sicher belegt.

**Beobachtet:** Im ersten Programmlauf nach der Installation zeigte einer von zwei Knöpfen (vermutlich die IDE) das leere Fenstersymbol, der andere die Natter. In zwei Wiederholungen zeigten beide die Natter. Titelleiste und `WM_GETICON` liefern die Natter, das Symbol der Fensterklasse ist weiter leer. Beide Knöpfe heißen über UI Automation „Python – 1 aktives Fenster“.

**Ursache:** noch offen. Möglich: Die Taskleiste liest beim ersten Erscheinen das Symbol der Fensterklasse, bevor Qt das Fenstersymbol setzt; die Beschriftung kommt von `pythonw.exe`, weil weder IDE noch Programm eine eigene `AppUserModelID` setzen.

**Zu tun:** Am ersten Start nach einer Installation nachprüfen. Bestätigt es sich: ein eigenes `AppUserModelID` für IDE und Programme und das Symbol früh setzen. Erledigt, wenn ein Bildschirmfoto der Taskleiste beim ersten Programmlauf die Natter zeigt.

**Umgesetzt (29. September 2026), Nachweis steht aus.** IDE und Programme melden sich unter eigener Kennung bei Windows an, bevor ein Fenster entsteht: `anwendungs_kennung_setzen()` in `ide/main.py` setzt `Natter.IDE` als Erstes in `starten()`, `pcl.Application` setzt `Natter.Programm` (in einer exportierten Exe keine). Die Verknüpfungen im Startmenü und auf dem Schreibtisch tragen in `tools/natter.iss` dieselbe Kennung `Natter.IDE`. Darüber findet die Taskleiste Namen und Symbol der Verknüpfung, statt beides aus `pythonw.exe` zu nehmen. Außerdem setzt `anwendung_erzeugen()` das Symbol der Anwendung vor dem ersten Fenster; bis 0.4.2 setzte es nur das Hauptfenster für sich. Tests in `tests/test_taskleiste.py`. Im Entwicklungsbaum geprüft: `GetCurrentProcessExplicitAppUserModelID` liefert in beiden Prozessen die Kennung, der Knopf der IDE zeigt die Natter. Er heißt dort noch „Python“, weil es ohne Setup keine Verknüpfung mit der Kennung gibt. Offen ist nur das Bildschirmfoto am ersten Start nach einer Installation der nächsten Fassung.

## 417. Neue Unit, Test-Unit und Formular ohne Schreibrecht enden in „In Natter ist etwas schiefgegangen“

**Gemeldet:** 29. September 2026, Durchsicht (`/durchsicht`), Entwicklungsstand `d403e24`.

**Beobachtet:** Lässt sich im Projektordner nicht schreiben, etwa nach „Nur ansehen“ bei einer Aufgabe auf einer Freigabe ohne Schreibrecht oder bei abgezogenem USB-Stick, enden „Datei → Neue Unit“ (Strg+N), „Datei → Neue Test-Unit“ und „Datei → Neues Formular …“ mit einer unbehandelten `PermissionError`. In der installierten Fassung erscheint dafür die Absturzmeldung „In Natter ist etwas schiefgegangen: PermissionError“ mit dem Rat, der Lehrkraft Bescheid zu sagen. Zu erwarten wäre eine Meldung wie beim Speichern, die den Grund nennt und wie dort die eigene Kopie anbietet. Probe (Kopie von `03_Taschenrechner` in `%TEMP%`, Hauptfenster aus der Fixture, `atomar_schreiben` in `ide.shell.hauptfenster` wirft `PermissionError`): `_neue_unit_aktion`, `_neue_test_unit_aktion` und `_neues_formular_aktion` reichen die Ausnahme alle drei nach außen durch.

**Ursache:** nachgewiesen: `unit_erzeugen` (`ide/shell/hauptfenster.py`, Zeile 2169) schreibt mit `atomar_schreiben` ohne `try`; `_neue_unit_aktion` (Zeile 2977) und `_neue_test_unit_aktion` (Zeile 2332) rufen es ohne Fehlerbehandlung auf. `_neues_formular_aktion` (Zeile 2194) fängt in Zeile 2213 nur `ValueError` und `FileExistsError`, nicht `OSError`; `formular_erzeugen` (Zeile 2233) schreibt `.pfm` und Unit nacheinander, sodass bei einem Fehler in der zweiten Datei eine `.pfm` ohne Unit liegen bleiben kann. Designer (`DesignerCanvas.speichern`) und „Neues Diagramm …“ fangen denselben Fehler bereits ab.

**Zu tun:** Die drei Befehle fangen `OSError` ab, melden ihn wie das Speichern und lassen keine halb angelegten Dateien zurück. Erledigt, wenn ein Test mit einem `atomar_schreiben`, das `PermissionError` wirft, für alle drei Befehle eine Meldung statt einer Ausnahme findet und im Projektordner keine neue Datei liegt.

## 418. Beim Start mit Debugger nennt die Fehlermeldung eines AttributeError den Typ statt des fehlenden Namens

**Gemeldet:** 29. September 2026, Durchsicht (`/durchsicht`), Entwicklungsstand `d403e24`.

**Beobachtet:** F5 startet mit Debugger, und die Meldung zu einer unbehandelten Ausnahme kommt dann aus der `exceptionInfo`-Antwort von debugpy. Für `AttributeError` steht dort das erste Wort in Hochkommas der englischen Meldung statt des fehlenden Attributs:

- `'NoneType' object has no attribute 'caption'` wird zu „„NoneType“ existiert bei diesem Objekt nicht.“
- `'int' object has no attribute 'append'` wird zu „„int“ existiert bei diesem Objekt nicht.“
- `module 'random' has no attribute 'randInt'` wird zu „„random“ existiert bei diesem Objekt nicht.“
- `'Form1' object has no attribute 'l_ausgab'` wird zu „„Form1“ existiert bei diesem Objekt nicht.“

Mit Strg+F5 (ohne Debugger) nennt dieselbe Meldung richtig „caption“, „append“, „randInt“ und „l_ausgab“. Zwei weitere Abweichungen im Debugger-Weg: ein `KeyError` ergibt „Der Schlüssel "'a'" kommt in diesem Wörterbuch nicht vor.“ (ohne Debugger „Der Schlüssel 'a' …“), und ein `FileNotFoundError` bleibt beim englischen Zitat „Die angegebene Datei wurde nicht gefunden. Python meldet dazu wörtlich: „[Errno 2] No such file or directory: 'gibtsnicht.txt'““ statt „Die Datei „gibtsnicht.txt“ wurde nicht gefunden.“ Probe: dieselben Ausnahmen einmal über `fehlermeldung_erzeugen` und einmal als `exceptionInfo` (Meldung wie `str(exc)`) über `fehlermeldung_aus_dap_erzeugen`. Von 41 Fällen weichen sieben ab: alle fünf mit `AttributeError` (dazu `'abc'.upper.lower()` und ein Klassenattribut) sowie `KeyError` und `FileNotFoundError`; die übrigen stimmen überein.

**Ursache:** nachgewiesen: `_name_ermitteln` (`pcl/fehlerkatalog.py`, Zeile 97) nimmt ohne `exc.name` den ersten Treffer von `'([^']+)'` aus der Meldung. `_DapAusnahme` (Zeile 1481) setzt `name` und `filename` immer auf `None`, also greift im Debugger-Weg stets der reguläre Ausdruck, und bei `AttributeError` steht der Typ vor dem Namen. `_key_error` (Zeile 993) setzt `args[0]` mit `!r` ein; im Debugger-Weg ist das schon der Text `'a'` samt Hochkommas. `_file_not_found` (Zeile 1003) liest nur `exc.filename`. Die bestehenden Tests in `tests/test_fehlerkatalog_erste_schritte.py` decken nur die Sonderfälle ab, die `_ort_umlenken` umschreibt.

**Zu tun:** `fehlermeldung_aus_dap_erzeugen` holt Name, Schlüssel und Dateiname aus der Meldung nach demselben Muster, das Python für diese Ausnahmen benutzt (bei `AttributeError` das Wort nach „has no attribute“). Erledigt, wenn ein Test für jede der sechs Ausnahmen oben zeigt, dass beide Wege dasselbe „Was“ liefern.

## 419. Haltepunkte gehen beim Schließen des Reiters verloren

**Gemeldet:** 29. September 2026, Durchsicht (`/durchsicht`), Entwicklungsstand `d403e24`.

**Beobachtet:** In `u_main.py` wird ein Haltepunkt gesetzt, der Reiter geschlossen (etwa um aufzuräumen) und danach mit F5 gestartet. Das Programm hält nicht an. Wird die Datei wieder geöffnet, ist der Haltepunkt fort. Dasselbe nach dem Schließen des Projekts oder von Natter. Probe (Kopie von `01_Begruessung` in `%TEMP%`, Hauptfenster aus der Fixture): vor dem Schließen liefert `_offene_breakpoints()` `{…\u_main.py: [3]}`, danach `{}`, und der Editor der wieder geöffneten Datei hat `breakpoints == set()`. Einen Haltepunkt setzen und dann in einen anderen Reiter wechseln ist harmlos; erst das Schließen löscht ihn.

**Ursache:** nachgewiesen: Die Haltepunkte stehen nur im Editor-Objekt (`QuelltextEditor.breakpoints`, `ide/shell/quelltexteditor.py`, Zeile 386). `_offene_breakpoints` (`ide/shell/hauptfenster.py`, Zeile 8375) sammelt sie beim Start nur aus den offenen Reitern, und `_tab_schliessen` (Zeile 6817) gibt den Editor samt Haltepunkten auf. Ein neu geöffneter Editor beginnt immer leer.

**Zu tun:** Haltepunkte und ihre Bedingungen je Datei im Hauptfenster aufbewahren, solange das Projekt offen ist, beim Öffnen einer Datei wieder in den Editor setzen und beim Start auch für geschlossene Dateien an debugpy geben. Ob sie außerdem das Schließen des Projekts überstehen, ist eine eigene Entscheidung. Erledigt, wenn ein Test Haltepunkt setzen, Reiter schließen und mit Debugger starten durchläuft und das Programm an der Zeile hält.

## 420. Der Test-Explorer zeigt bei Listen und Tupeln „Lists differ:“ als Teil des Ist-Werts

**Gemeldet:** 29. September 2026, Durchsicht (`/durchsicht`), Entwicklungsstand `d403e24`.

**Beobachtet:** Ein Test mit `self.assertEqual(sorted([3, 1, 2]), [1, 2, 4])` schlägt fehl. Der Tooltip im Panel „Tests“ und die Spalte „Ist“ im HTML-Protokoll zeigen „Ist: Lists differ: [1, 2, 3]“, bei Tupeln „Tuples differ: (1, 2)“. Soll ist richtig „[1, 2, 4]“. Der englische Vorsatz gehört nicht zum Wert und ist im Protokoll für die Lehrkraft mitten in der Wertespalte zu sehen. Probe: eine Testdatei mit vier Fällen in `%TEMP%` über `tests_ausfuehren`; Liste und Tupel liefern den Vorsatz im Ist-Wert, Text und Zahl nicht.

**Ursache:** nachgewiesen: `_SOLL_IST_MUSTER` in `ide/testrunner/harness.py` (Zeile 26) ist `^(?P<ist>.+?) != (?P<soll>.+)$` und wird auf die erste Zeile der Meldung angewandt (`_soll_ist_extrahieren`, Zeile 34). `unittest` schreibt bei Listen, Tupeln und Folgen „Lists differ: … != …“, „Tuples differ: …“ und „Sequences differ: …“ davor.

**Zu tun:** Den Vorsatz „… differ: “ vor dem Vergleich abschneiden. Erledigt, wenn ein Test mit Liste und Tupel „[1, 2, 3]“ und „(1, 2)“ als Ist-Wert findet.

## 421. „In ein Text lässt sich kein einzelner Platz überschreiben.“

**Gemeldet:** 29. September 2026, Durchsicht (`/durchsicht`), Entwicklungsstand `d403e24`.

**Beobachtet:** `wort[0] = "H"` ist im Anfangsunterricht ein häufiger Fehler. Die Meldung dazu lautet „In ein Text lässt sich kein einzelner Platz überschreiben.“; richtig wäre „In einen Text …“. Dasselbe Muster „Über {typ} lässt sich nicht Stück für Stück laufen.“ ergibt bei einem Wahrheitswert „Über ein Wahrheitswert …“. Probe: `exec("'abc'[1] = 'x'")` und `fehlermeldung_erzeugen`.

**Ursache:** nachgewiesen: `pcl/fehlerkatalog.py`, Zeilen 296 und 342 setzen `{typ}` nach „In“ und „Über“ ein, wo der Akkusativ steht. `_TYPNAMEN` (Zeile 128) führt nur den Nominativ („ein Text“, „ein Wahrheitswert“, „ein Zahlenbereich“). Für die Meldungen der Komponenten wurde derselbe Fehler in Punkt 297 mit einer Akkusativform in `pcl/properties.py` behoben, der Fehlerkatalog blieb beim Nominativ.

**Zu tun:** Für diese beiden Muster die Akkusativform einsetzen. Erledigt, wenn ein Test für `'abc'[1] = 'x'` „In einen Text“ findet.

## 422. Häufige Laufzeitfehler bleiben englisch oder verlieren den Typ des Objekts

**Gemeldet:** 29. September 2026, Durchsicht (`/durchsicht`), Entwicklungsstand `d403e24`.

**Beobachtet:** Drei Fälle, die im Unterricht regelmäßig vorkommen:

- `random.randint(5, 1)`, etwa wenn beim Zahlenraten die untere Grenze über die obere wandert: „Der übergebene Wert passt nicht zu dem, was hier erwartet wird. Python meldet dazu wörtlich: „empty range in randrange(5, 2)““. Dass die erste Zahl größer als die zweite ist, steht nur im englischen Zitat, und die „2“ darin ist nicht die Zahl aus dem Programm.
- `min([])` und `max([])` bei einer leeren Liste: „Python meldet dazu wörtlich: „min() iterable argument is empty““.
- `ergebnis.upper()`, wenn eine Funktion ohne `return` `None` geliefert hat: „„upper“ existiert bei diesem Objekt nicht.“ Python nennt den Typ (`'NoneType' object has no attribute 'upper'`), die deutsche Meldung lässt ihn weg. Gerade `None` ist aber der Hinweis auf das vergessene `return`; bei `x.append(3)` mit einer Zahl fehlt entsprechend „ganze Zahl“.

Probe: 38 typische Fehler über `fehlermeldung_erzeugen`; die drei oben sind die häufigsten, die ohne eigene Übersetzung oder ohne Typ ankommen.

**Ursache:** nachgewiesen: `_STANDARDMELDUNGEN` in `pcl/fehlerkatalog.py` hat kein Muster für „empty range in randrange“ und „iterable argument is empty“/„arg is an empty sequence“, es greift der Rückfall mit Zitat. `_attribute_error` (Zeile 885) baut „Was“ nur aus dem Namen; `exc.obj` (seit Python 3.10) bzw. der Typ aus der Meldung wird nicht benutzt.

**Zu tun:** Muster für die beiden Meldungen ergänzen; bei `randint` nennt die Meldung, dass der erste Wert nicht größer als der zweite sein darf. Die Meldung zum `AttributeError` nennt den Typ über `_typname`, bei `None` mit dem Hinweis, dass eine Funktion ohne `return` `None` liefert. Erledigt, wenn Tests für die drei Fälle eine deutsche Meldung ohne englisches Zitat und bei `None` das Wort „None“ finden.

---

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
