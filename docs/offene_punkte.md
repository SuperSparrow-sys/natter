# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **429**.

## Ein neuer Punkt

```markdown
## 429. Kurz, was nicht stimmt

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

## 423. Der Exe-Export signiert ohne Rückfrage mit jedem Codesignatur-Zertifikat, das im Konto liegt

**Gemeldet:** 29. September 2026, Sicherheitsprüfung, Entwicklungsstand `94200dc`.

**Beobachtet:** „Als Exe exportieren“ signiert die Exe mit dem ersten Zertifikat aus `Cert:\CurrentUser\My`, das zum Codesignieren taugt, einen privaten Schlüssel hat, noch gilt und dem das Konto vertraut. Das Natter-eigene Zertifikat „Natter Programme dieses Rechners“ wird nur vorgezogen; fehlt es, nimmt der Export jedes andere. Liegt im Konto einer Lehrkraft oder der Systembetreuung das Codesignatur-Zertifikat der Schule, etwa für Skripte oder für Regeln nach Herausgeber in AppLocker, bekommt ein exportiertes Schülerprogramm ohne Nachfrage diese Signatur und damit den Herausgeber der Schule. Die Rückmeldung lautet nur „Signiert - die Exe nennt jetzt einen Herausgeber.“ und nennt nicht, welcher. Das Handbuch (Abschnitt zum Exe-Export) beschreibt nur das eigene Zertifikat. Zu erwarten wäre, dass Natter ohne ausdrückliche Wahl nur mit dem eigenen Zertifikat signiert. Nachgestellt mit einem Ersatz für `_powershell`, der ein fremdes Zertifikat `SCHULE123` als vorhanden und vertraut meldet: `signieren_wenn_moeglich(..., anlegen=True)` signiert damit, `vor_dem_anlegen` wird nicht aufgerufen, Ergebnis `signiert=True`.

**Ursache:** nachgewiesen. `vorhandenes_zertifikat()` in `ide/export/signatur.py` (Zeile 191-220) sortiert mit `Sort-Object { $_.Subject -eq 'CN=Natter Programme dieses Rechners' }` nur um und gibt sonst das erste vertraute Zertifikat zurück. `signieren_wenn_moeglich()` (Zeile 535-553) signiert damit ohne Rückfrage; der Docstring von `ide/export/signatur.py` nennt „ein Zertifikat, das die Lehrkraft dort eingerichtet hat“ ausdrücklich als Quelle.

**Zu tun:** Ohne ausdrückliche Einstellung nur mit dem Zertifikat `CN=Natter Programme dieses Rechners` signieren. Soll ein anderes erlaubt sein, dann nur nach einer Wahl in den Einstellungen, und die Rückmeldung nach dem Export nennt den Herausgeber. Erledigt, wenn ein Test mit einem fremden, vertrauten Zertifikat im Konto keine Signatur mit diesem ergibt und das Handbuch das Verhalten beschreibt.

## 424. Ohne Netz meldet „Paket installieren …“ nach anderthalb Minuten auf Englisch, das Paket gebe es nicht

**Gemeldet:** 29. September 2026, Sicherheitsprüfung, Entwicklungsstand `94200dc`.

**Beobachtet:** Ist das Netz nicht erreichbar oder verwirft ein Proxy die Verbindung ohne Antwort, wiederholt `pip` den Abruf fünfmal mit je 15 Sekunden Wartezeit. Gemessen mit `pip install --dry-run` und einem Proxy auf der nicht erreichbaren Adresse `192.0.2.1`: 106 Sekunden. Danach steht in Statuszeile und Panel „Meldungen“ die Rohausgabe von `pip`, darunter „WARNING: Retrying (Retry(total=0 …)) after connection broken by 'ConnectTimeoutError …'“ und am Ende „ERROR: Could not find a version that satisfies the requirement … ERROR: No matching distribution found for …“. Die letzte Zeile liest sich so, als sei der Paketname falsch; dass keine Verbindung zustande kam, steht nur englisch in den Zeilen davor. Während der ganzen Zeit sind die anderen Vorgänge im Hintergrund gesperrt (`_hintergrund_frei`), also auch Testlauf, Exe-Export und „Als ZIP speichern“. Zu erwarten wäre eine deutsche Meldung, die fehlendes Netz von einem unbekannten Paketnamen unterscheidet, und eine kürzere Wartezeit.

**Ursache:** nachgewiesen. `paket_installieren()` in `ide/env/pakete.py` (Zeile 68-77) ruft `pip install` ohne `--timeout`, `--retries` oder eine eigene Zeitgrenze auf. `_mit_rechtehinweis()` (Zeile 80-91) ergänzt nur fehlende Schreibrechte; jede andere Ausgabe von `pip` geht unverändert über `_hintergrund_fehler()` in `ide/shell/hauptfenster.py` (Zeile 2860-2873) an die Oberfläche.

**Zu tun:** `pip` mit kürzerer Wartezeit und weniger Wiederholungen aufrufen und die Ausgabe auswerten: Verbindungsfehler als „Keine Verbindung zum Paketverzeichnis …“ melden, einen unbekannten Namen als solchen, jeweils auf Deutsch; die Rohausgabe höchstens im Panel „Meldungen“. Erledigt, wenn ein Test mit einem nicht erreichbaren Proxy die deutsche Meldung zur Verbindung ergibt und der Vorgang in weniger als 30 Sekunden endet.

## 425. Stürzt der Testprozess ab, meldet der Test-Explorer „0 Tests gelaufen, 0 nicht bestanden“

**Gemeldet:** 29. September 2026, Sicherheitsprüfung, Entwicklungsstand `94200dc`.

**Beobachtet:** Endet `harness.py` vorzeitig, fallen die Ergebnisse aller Testdateien weg, und die Statuszeile meldet „0 Tests gelaufen, 0 nicht bestanden“. Das sieht aus wie ein Lauf ohne Fehler. Probe in einem Ordner unter `%TEMP%` mit zwei Testdateien: `test_b.py` mit einem scheiternden `assertEqual(2, 3)`, `test_a.py` mit einem Test, der ein `Form()` aus `pcl` anlegt, ohne dass eine `QApplication` besteht. Qt bricht den Prozess dabei ab (Rückgabewert `0xC0000409`), und `tests_ausfuehren` liefert eine leere Liste; auch der scheiternde Test aus `test_b.py` erscheint nicht. Dasselbe gilt für jeden anderen harten Abbruch im geprüften Code, etwa `os._exit()`. Ein Formular im Test anzulegen liegt im Unterricht nahe, sobald die Logik eines Formulars geprüft werden soll.

**Ursache:** nachgewiesen: `ide/testrunner/ausfuehrung.py` wertet den Rückgabewert des Prozesses nicht aus. Nach `prozess.wait` (Zeile 91) wird nur die Ausgabe gelesen; fehlt die Marke und ist die Ausgabe leer, gibt Zeile 120 eine leere Liste zurück. `_tests_fertig` in `ide/shell/hauptfenster.py` zählt diese leere Liste als erfolgreichen Lauf. Eine Ausgabe ohne gültiges JSON hinter der Marke endet in Zeile 122 als `JSONDecodeError` und erscheint als englische Rohmeldung.

**Zu tun:** Fehlt die Ergebnismarke oder endet der Prozess mit einem Rückgabewert ungleich 0, ein Ergebnis mit Status „fehler“ liefern, das sagt, dass der Testlauf abgebrochen ist, und den Rückgabewert nennt; bei einem Abbruch durch Qt den Hinweis, dass ein Formular im Test eine `QApplication` braucht. Einen einzelnen Absturz nicht die Ergebnisse der übrigen Testdateien mitnehmen lassen, etwa indem jede Datei in eigenem Prozess läuft oder die bis dahin fertigen Ergebnisse vorher geschrieben werden. Erledigt, wenn ein Test mit den beiden Dateien oben den scheiternden Test aus `test_b.py` und einen Eintrag zum Abbruch findet.

## 426. `SQLQuery.to_dataframe()` leert den Puffer der Abfrage, an der DBGrid, DBText und DBNavigator hängen

**Gemeldet:** 29. September 2026, Sicherheitsprüfung, Entwicklungsstand `94200dc`.

**Beobachtet:** Hängen `DBGrid`, `DBText` und `DBNavigator` über eine `DataSource` an einer geöffneten `SQLQuery` und ruft das Programm danach `to_dataframe()` auf derselben Abfrage auf, etwa für ein Diagramm, zeigt das Gitter weiter alle Zeilen, aber keines der Steuerelemente reagiert mehr. Probe mit drei Zeilen (Anna, Ben, Cem), Qt offscreen: nach `to_dataframe()` ist `record_count` 0, „Vor“ im Navigator ändert nichts, `DBText` zeigt weiter „Anna“, und ein Klick auf die dritte Gitterzeile setzt den Datensatzzeiger nicht (`record_index` -1). Eine Meldung gibt es nicht; erst ein neues `open()` mit `aktualisieren()` bringt die Anzeige zurück.

**Ursache:** nachgewiesen: `pcl/components/data_access.py`, `SQLQuery.to_dataframe` (Zeile 576) führt `sql` neu aus und ruft am Ende `self.close()` (Zeile 586). Das leert `_zeilen` und setzt den Zeiger auf -1, benachrichtigt die `DataSource` aber nicht. `DBGrid._bei_zeilenwechsel` in `pcl/components/data_controls.py` verwirft danach jeden Klick, weil `zeile >= query.record_count` gilt.

**Zu tun:** `to_dataframe()` den Zustand der Abfrage nicht verändern lassen, also mit einem eigenen Cursor lesen und Puffer, Spalten und Zeiger stehen lassen; zumindest dürfen gebundene Steuerelemente nicht still aus dem Tritt geraten. Die Komponenten-Referenz nennt das Verhalten. Erledigt, wenn ein Test nach `to_dataframe()` mit dem Navigator auf den zweiten Datensatz kommt und `DBText` dessen Wert zeigt.

## 427. `SQLite3Connection` legt bei einem Tippfehler im Dateinamen still eine leere Datenbank an

**Gemeldet:** 29. September 2026, Sicherheitsprüfung, Entwicklungsstand `94200dc`.

**Beobachtet:** `SQLite3Connection("konton.sqlite")` statt `"konten.sqlite"` öffnet ohne Meldung eine neue, leere Datei im Projektordner. Die erste Abfrage scheitert mit „SQL-Fehler: eine Tabelle namens „konto“ gibt es in der Datenbank nicht“, obwohl die Tabelle in der richtigen Datei steht und im Datenbank-Panel zu sehen ist. Die Meldung nennt die Datei nicht, und der Hinweis unter „Zu prüfen“ lenkt auf Tabellen- und Spaltennamen. Die leere Datei `konton.sqlite` bleibt im Projektordner liegen. Probe unter `%TEMP%`: nach dem Aufruf liegen `konten.sqlite` und `konton.sqlite` nebeneinander. Das Datenbank-Panel fragt in diesem Fall seit Punkt 244 nach; im Schülerprogramm fehlt ein entsprechender Hinweis.

**Ursache:** nachgewiesen: `pcl/components/data_access.py`, `_verbindung_oeffnen` (Zeile 349) ruft `sqlite3.connect(ziel)` ohne Prüfung, ob die Datei vorher bestand. `sqlite3` legt eine fehlende Datei dabei an. `_datenbankmeldung_eindeutschen` in `pcl/fehlerkatalog.py` kennt den Dateinamen nicht.

**Zu tun:** Das Anlegen einer neuen Datei bleibt erlaubt, weil Programme ihre Datenbank so erzeugen. Scheitert aber eine Abfrage an einer fehlenden Tabelle, soll die Meldung den Dateinamen nennen und, wenn die Datei beim Verbinden neu angelegt wurde oder keine einzige Tabelle enthält, darauf hinweisen, dass wahrscheinlich eine andere Datei gemeint war. Erledigt, wenn ein Test mit falsch geschriebenem Dateinamen in der Meldung den Namen der Datei und diesen Hinweis findet.

## 428. Eine große Nachricht von debugpy, die stockend ankommt, lässt die Debug-Sitzung hängen

**Gemeldet:** 29. September 2026, Sicherheitsprüfung, Entwicklungsstand `94200dc`.

**Beobachtet:** Kommt eine Nachricht von debugpy mit mehr als 4 KB nicht in einem Stück an, gehen beim Lesen schon empfangene Bytes verloren. Der Datenstrom gerät aus dem Tritt und endet in einem `JSONDecodeError`. Mit einer Probe bestätigt, die eine Nachricht über 4 KB mit einer Pause mitten im Text schickt. Die Sitzung meldet danach nie „beendet“: Start und Stopp bleiben im Zustand des laufenden Debuggers stehen. Große Nachrichten entstehen vermutlich beim Aufklappen einer langen Liste in der Variablenansicht (nicht nachgemessen). Das ist selten, lässt sich dann aber nur durch einen Neustart von Natter beheben.

**Ursache:** nachgewiesen: `_naechste_nachricht` im DAP-Client liest mit einer Abfragezeitgrenze von 0,05 s und verwirft einen angefangenen Block, wenn die Zeitgrenze mitten in einer Nachricht abläuft. `DebugSitzung._worker` fängt nur `DapFehler`, nicht den `JSONDecodeError`, der daraus folgt.

**Zu tun:** Angefangene Nachrichten über die Zeitgrenze hinweg im Puffer behalten, und jede unerwartete Ausnahme im Lesefaden als Ende der Sitzung mit einer deutschen Meldung behandeln. Erledigt, wenn ein Test mit einer stockend gesendeten Nachricht über 4 KB sie vollständig liest und ein Test mit ungültigem JSON die Sitzung sauber beendet.

---

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
