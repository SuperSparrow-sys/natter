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

## 453. Stürzt der Testprozess ab, meldet der Test-Explorer „0 Tests gelaufen, 0 nicht bestanden“

**Gemeldet:** 29. September 2026, Sicherheitsprüfung, Entwicklungsstand `94200dc`.

**Beobachtet:** Endet `harness.py` vorzeitig, fallen die Ergebnisse aller Testdateien weg, und die Statuszeile meldet „0 Tests gelaufen, 0 nicht bestanden“. Das sieht aus wie ein Lauf ohne Fehler. Probe in einem Ordner unter `%TEMP%` mit zwei Testdateien: `test_b.py` mit einem scheiternden `assertEqual(2, 3)`, `test_a.py` mit einem Test, der ein `Form()` aus `pcl` anlegt, ohne dass eine `QApplication` besteht. Qt bricht den Prozess dabei ab (Rückgabewert `0xC0000409`), und `tests_ausfuehren` liefert eine leere Liste; auch der scheiternde Test aus `test_b.py` erscheint nicht. Dasselbe gilt für jeden anderen harten Abbruch im geprüften Code, etwa `os._exit()`. Ein Formular im Test anzulegen liegt im Unterricht nahe, sobald die Logik eines Formulars geprüft werden soll.

**Ursache:** nachgewiesen: `ide/testrunner/ausfuehrung.py` wertet den Rückgabewert des Prozesses nicht aus. Nach `prozess.wait` (Zeile 91) wird nur die Ausgabe gelesen; fehlt die Marke und ist die Ausgabe leer, gibt Zeile 120 eine leere Liste zurück. `_tests_fertig` in `ide/shell/hauptfenster.py` zählt diese leere Liste als erfolgreichen Lauf. Eine Ausgabe ohne gültiges JSON hinter der Marke endet in Zeile 122 als `JSONDecodeError` und erscheint als englische Rohmeldung.

**Zu tun:** Fehlt die Ergebnismarke oder endet der Prozess mit einem Rückgabewert ungleich 0, ein Ergebnis mit Status „fehler“ liefern, das sagt, dass der Testlauf abgebrochen ist, und den Rückgabewert nennt; bei einem Abbruch durch Qt den Hinweis, dass ein Formular im Test eine `QApplication` braucht. Einen einzelnen Absturz nicht die Ergebnisse der übrigen Testdateien mitnehmen lassen, etwa indem jede Datei in eigenem Prozess läuft oder die bis dahin fertigen Ergebnisse vorher geschrieben werden. Erledigt, wenn ein Test mit den beiden Dateien oben den scheiternden Test aus `test_b.py` und einen Eintrag zum Abbruch findet.

## 454. `SQLQuery.to_dataframe()` leert den Puffer der Abfrage, an der DBGrid, DBText und DBNavigator hängen

**Gemeldet:** 29. September 2026, Sicherheitsprüfung, Entwicklungsstand `94200dc`.

**Beobachtet:** Hängen `DBGrid`, `DBText` und `DBNavigator` über eine `DataSource` an einer geöffneten `SQLQuery` und ruft das Programm danach `to_dataframe()` auf derselben Abfrage auf, etwa für ein Diagramm, zeigt das Gitter weiter alle Zeilen, aber keines der Steuerelemente reagiert mehr. Probe mit drei Zeilen (Anna, Ben, Cem), Qt offscreen: nach `to_dataframe()` ist `record_count` 0, „Vor“ im Navigator ändert nichts, `DBText` zeigt weiter „Anna“, und ein Klick auf die dritte Gitterzeile setzt den Datensatzzeiger nicht (`record_index` -1). Eine Meldung gibt es nicht; erst ein neues `open()` mit `aktualisieren()` bringt die Anzeige zurück.

**Ursache:** nachgewiesen: `pcl/components/data_access.py`, `SQLQuery.to_dataframe` (Zeile 576) führt `sql` neu aus und ruft am Ende `self.close()` (Zeile 586). Das leert `_zeilen` und setzt den Zeiger auf -1, benachrichtigt die `DataSource` aber nicht. `DBGrid._bei_zeilenwechsel` in `pcl/components/data_controls.py` verwirft danach jeden Klick, weil `zeile >= query.record_count` gilt.

**Zu tun:** `to_dataframe()` den Zustand der Abfrage nicht verändern lassen, also mit einem eigenen Cursor lesen und Puffer, Spalten und Zeiger stehen lassen; zumindest dürfen gebundene Steuerelemente nicht still aus dem Tritt geraten. Die Komponenten-Referenz nennt das Verhalten. Erledigt, wenn ein Test nach `to_dataframe()` mit dem Navigator auf den zweiten Datensatz kommt und `DBText` dessen Wert zeigt.

## 455. `SQLite3Connection` legt bei einem Tippfehler im Dateinamen still eine leere Datenbank an

**Gemeldet:** 29. September 2026, Sicherheitsprüfung, Entwicklungsstand `94200dc`.

**Beobachtet:** `SQLite3Connection("konton.sqlite")` statt `"konten.sqlite"` öffnet ohne Meldung eine neue, leere Datei im Projektordner. Die erste Abfrage scheitert mit „SQL-Fehler: eine Tabelle namens „konto“ gibt es in der Datenbank nicht“, obwohl die Tabelle in der richtigen Datei steht und im Datenbank-Panel zu sehen ist. Die Meldung nennt die Datei nicht, und der Hinweis unter „Zu prüfen“ lenkt auf Tabellen- und Spaltennamen. Die leere Datei `konton.sqlite` bleibt im Projektordner liegen. Probe unter `%TEMP%`: nach dem Aufruf liegen `konten.sqlite` und `konton.sqlite` nebeneinander. Das Datenbank-Panel fragt in diesem Fall seit Punkt 244 nach; im Schülerprogramm fehlt ein entsprechender Hinweis.

**Ursache:** nachgewiesen: `pcl/components/data_access.py`, `_verbindung_oeffnen` (Zeile 349) ruft `sqlite3.connect(ziel)` ohne Prüfung, ob die Datei vorher bestand. `sqlite3` legt eine fehlende Datei dabei an. `_datenbankmeldung_eindeutschen` in `pcl/fehlerkatalog.py` kennt den Dateinamen nicht.

**Zu tun:** Das Anlegen einer neuen Datei bleibt erlaubt, weil Programme ihre Datenbank so erzeugen. Scheitert aber eine Abfrage an einer fehlenden Tabelle, soll die Meldung den Dateinamen nennen und, wenn die Datei beim Verbinden neu angelegt wurde oder keine einzige Tabelle enthält, darauf hinweisen, dass wahrscheinlich eine andere Datei gemeint war. Erledigt, wenn ein Test mit falsch geschriebenem Dateinamen in der Meldung den Namen der Datei und diesen Hinweis findet.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
