# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **454**.

## Ein neuer Punkt

```markdown
## 454. Kurz, was nicht stimmt

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

## 441. Nach einem gescheiterten INSERT mit zu großer Zahl schreibt `SQLite3Connection` nichts mehr fest, und alles Weitere geht beim Programmende verloren

**Gemeldet:** 2. Oktober 2026, Sicherheitsprüfung (Bereiche 3, 4 und 8), Entwicklungsstand `1445802` (Fassung 0.4.2 mit späteren Fehlerbehebungen).

**Beobachtet:** In ein Programm mit einer Dateidatenbank wird eine ganze Zahl über 64 Bit geschrieben, etwa eine Fakultät, eine lange Ziffernfolge mit `int()` oder ein immer weiter wachsender Spielstand: `db.execute("INSERT INTO konto VALUES (:w, :s)", w="gross", s=2**70)`. Das scheitert mit `OverflowError`. Ein Programm mit Fenster läuft nach der Fehlermeldung weiter. Danach ist die Transaktion offen (`in_transaction == True`), und jedes weitere `execute()` gilt als Teil einer ausdrücklich begonnenen Transaktion und wird nicht festgeschrieben. Eine zweite Verbindung (Datenbank-Panel oder ein zweites Programm) bekommt „database is locked“. Beim Beenden verwirft `_abschliessen` alles. Probe: Zeile „vorher“, dann der Überlauf, dann `INSERT 'danach'`, Verbindung geschlossen. In der Datei steht nur „vorher“. Auf das Verlorene weist nur der Hinweis auf `stderr` beim Schließen hin. Erwartet wäre, dass der gescheiterte Befehl nichts offen lässt, wie bei einem SQL-Fehler seit Punkt 238.

**Ursache:** nachgewiesen. `pcl/components/data_access.py`, `SQLite3Connection._ausfuehren` (ab Zeile 324) fängt nur `sqlite3.Error` (Zeile 330). Python öffnet vor dem INSERT selbst eine Transaktion. Der `OverflowError` entsteht erst beim Binden des Platzhalters und ist keine `sqlite3.Error`, deshalb läuft das Zurückrollen bei `not war_offen and verbindung.in_transaction` nicht. Ab dann sieht `_festschreiben_falls_eigen` (Zeile 292) `war_offen == True` und schreibt nie fest. Dasselbe gilt für `SQLQuery.open()`, `exec_sql()` und `to_dataframe()`, die über `_ausfuehren` laufen. Die Meldung an das Programm ist zudem nur der englische Satz „Python int too large to convert to SQLite INTEGER“ im Rückfall „Die Rechnung ließ sich nicht ausführen“.

**Zu tun:** In `_ausfuehren` jede Ausnahme beim Ausführen behandeln, nicht nur `sqlite3.Error`, und eine Transaktion zurückrollen, die erst dieser Befehl geöffnet hat. Einen Überlauf als `NatterDatenbankError` mit deutschem Satz melden, etwa: die Zahl ist zu groß für eine Datenbankspalte, höchstens 9.223.372.036.854.775.807, größere Zahlen als Text speichern. Erledigt, wenn ein Test nach dem Überlauf `in_transaction == False` findet, ein folgendes INSERT nach dem Schließen in der Datei steht und eine zweite Verbindung sofort schreiben kann.

## 442. CSV-Import und `StringGrid.to_dataframe()` machen aus „1.250“ in einer Spalte mit Dezimalpunkt 1250

**Gemeldet:** 2. Oktober 2026, Sicherheitsprüfung (Bereiche 3, 4 und 8), Entwicklungsstand `1445802`.

**Beobachtet:** Eine CSV-Datei mit Dezimalpunkt, wie sie aus offenen Datenquellen, englischem Excel oder `pandas.to_csv` kommt, wird im Datenbank-Panel importiert: `nr;laenge;breite;preis` mit den Zeilen `1;0.125;52.520;1.299`, `2;1.250;13.405;2.49`, `3;2.375;8.5;0.99`. Die Spalten werden richtig als REAL angelegt, die Werte aber so gespeichert: `laenge` 0.125, 1250.0, 2375.0; `breite` 52520.0, 13405.0, 8.5; `preis` 1299.0, 2.49, 0.99. Jeder Wert mit genau drei Nachkommastellen und ohne führende 0 wird zur Tausenderzahl, alle anderen bleiben Dezimalzahlen, in derselben Spalte. Es kommt keine Meldung. `sum()`, `avg()` und `ORDER BY` liefern danach falsche Ergebnisse, die nicht als Fehler auffallen. `StringGrid.to_dataframe()` liefert für dieselben Zellen ebenfalls `0.125, 1250.0, 2375.0` und `1299.00, 2.49, 0.99`.

**Ursache:** nachgewiesen. Beide Wege lesen jede Zelle für sich mit `pcl.zahlen.zahl`, das einen Punkt vor genau drei Ziffern als Tausendertrennung liest (`_TAUSENDERPUNKTE`, `pcl/zahlen.py` Zeile 26, so festgelegt in Punkt 136 der erledigten Punkte, Abschnitt zu „1.000“). Das passt für eine einzelne Eingabe, nicht aber für eine Spalte, in der andere Werte den Punkt erkennbar als Dezimalzeichen benutzen. Betroffen: `ide/database/panel.py`, `_zahlenart` (ab Zeile 100) und `_umwandler` (Zeile 143); `pcl/dataframe.py`, `_spalte_lesen` mit `_ganzzahlig` und `_zelle_lesen` (Zeilen 118 bis 153). Ergänzt Punkt 288, der die Typerkennung einführte.

**Zu tun:** Das Dezimalzeichen je Spalte festlegen statt je Zelle. Kommt in einer Spalte ein Punkt vor, der keine Tausendertrennung sein kann (etwa „2.49“, „8.5“, „0.125“), und kein Komma, dann gilt der Punkt in der ganzen Spalte als Dezimalzeichen. Ist das nicht eindeutig, bleibt die Spalte Text. Erledigt, wenn die Probe oben nach dem Import 1.25, 2.375, 13.405 und 1.299 ergibt, `to_dataframe()` dasselbe liefert und eine Spalte nur mit „1.000“ und „2.500“ weiter als 1000 und 2500 gelesen wird.

## 443. Methode anlegen bei ungespeicherter Unit mit Syntaxfehler endet in „In Natter ist etwas schiefgegangen“

**Gemeldet:** 2. Oktober 2026, Sicherheitsprüfung (Bereiche 3, 4 und 8), Entwicklungsstand `1445802`.

**Beobachtet:** `u_main.py` ist im Editor offen und enthält ungespeichert eine angefangene Zeile (`self.x = `). Ein Doppelklick auf einen Knopf im Designer legt die Methode an. Das kommt beim Arbeiten ständig vor. Dabei fliegt `libcst.ParserSyntaxError` („Syntax Error @ 48:1“) bis nach oben durch. In der installierten Fassung erscheint die allgemeine Absturzmeldung. Danach steht `button_click` in der Datei auf der Platte und in der `.pfm`, im Editor aber nicht. Wer den Tippfehler behebt und speichert, überschreibt die Datei ohne die Methode. Nachgestellt mit dem Hauptfenster aus `tests/conftest.py`. Erwartet wäre wie in Punkt 141 eine Meldung mit der Zeile des Syntaxfehlers, bevor etwas geschrieben wird.

**Ursache:** nachgewiesen. `ide/designer/canvas.py`, `ereignis_handler_erzeugen` prüft vor dem Schreiben nur den Text auf der Platte (`_syntaxfehler_melden([quelltext], …)`, Zeilen 2597 und 2598), nicht die offenen Editoren. Das Umbenennen prüft beide über `_unit_quelltexte()` (Zeile 2455). Danach ruft `HauptFenster._zur_methode_springen` (`ide/shell/hauptfenster.py`, Zeilen 6823 und 6824) für einen geänderten Editor `handler_methode_einfuegen` ohne `try` auf. Der zweite Aufruf in Zeile 6848 fängt `ParserSyntaxError`. Denselben Weg nimmt „Methode anlegen“ im Menü-Editor (`ide/inspector/menue_editor.py`, Zeile 116).

**Zu tun:** Vor dem Anlegen alle Fassungen der Unit prüfen (`_unit_quelltexte()`), im Designer wie im Menü-Editor, und bei einem Syntaxfehler im Editor dieselbe Meldung zeigen, ohne die Datei zu ändern. `_zur_methode_springen` fängt den Fehler zusätzlich ab. Erledigt, wenn ein Test mit ungespeicherter, fehlerhafter Unit nach dem Doppelklick eine Meldung findet, keine Ausnahme, und Datei, Editor und `.pfm` unverändert bleiben.

## 444. Eine `.pfm` mit unbekannter Eigenschaft oder falschem Werttyp öffnet sich mit der Absturzmeldung statt mit „beschädigt“

**Gemeldet:** 2. Oktober 2026, Sicherheitsprüfung (Bereiche 3, 4 und 8), Entwicklungsstand `1445802`.

**Beobachtet:** Eine `.pfm` hat einen falschen Werttyp, etwa von Hand bearbeitet („width“: 400.5 oder „caption“: 5), oder eine Eigenschaft, die diese Fassung nicht kennt, etwa geschrieben von einer neueren Fassung auf dem Rechner zu Hause. Sie geht im Explorer oder über „Öffnen“ nicht mit der Meldung „lässt sich nicht öffnen, die Datei ist beschädigt“ auf, wie sie für ungültiges JSON kommt. Stattdessen fliegt die Ausnahme durch: `NatterPropertyError` („Form1.width erwartet eine Zahl (int), erhalten wurde eine Kommazahl (float).“), `NatterUnbekannteEigenschaftError` („Label besitzt keine Eigenschaft 'foo'.“) oder bei 10^30 ein `OverflowError` ohne Text. In der installierten Fassung ist das die allgemeine Absturzmeldung „In Natter ist etwas schiefgegangen“. Nachgestellt mit dem Hauptfenster (`HauptFenster.oeffnen`) und mit `formular_fuer_designer_laden` für acht Fälle.

**Ursache:** nachgewiesen. `ide/shell/hauptfenster.py`, `oeffnen` (Zeilen 7912 bis 7920) fängt nur `JSONDecodeError`, `UnicodeDecodeError`, `schema_fehler()`, `KeyError` und `PfmBeschaedigt`. Das Schema lässt unter `properties` jedes Objekt zu (`schemas/pfm.schema.json`), und `pfm_pruefen` (`ide/codegen/design.py`) prüft nur die Namen. Werte und Bekanntheit prüft erst das Ausführen des erzeugten Codes in `formular_fuer_designer_laden` (`ide/designer/laden.py`). Derselbe Aufruf steht ungeschützt in `_projekt_startdateien_oeffnen` (Zeile 2217).

**Zu tun:** Beim Laden für den Designer `NatterPropertyError`, `NatterUnbekannteEigenschaftError`, `TypeError`, `ValueError` und `OverflowError` als beschädigte Datei melden, mit Komponente, Eigenschaft und erwartetem Typ. Eine unbekannte Eigenschaft benennen, damit eine Datei aus einer neueren Fassung als solche erkennbar ist. Erledigt, wenn ein Test mit „width“: 400.5 und mit einer unbekannten Eigenschaft eine Meldung in der Statuszeile findet und keine Ausnahme.

## 445. Debugger und Exe-Export scheitern an einer Projektdatei wie `random.py` oder `queue.py`

**Gemeldet:** 2. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand 1445802 (0.4.2 mit Fehlerbehebungen).

**Beobachtet:** Liegt im Projektordner eine Datei, die so heißt wie ein Modul der Standardbibliothek, laden der Debugger und der Exe-Export diese Datei statt des Moduls und führen sie aus. Im Unterricht sind solche Namen häufig: `random.py` für eine Übung mit Zufallszahlen, `queue.py` für eine Warteschlange, `string.py`, `copy.py`, `json.py`, `datetime.py`, `code.py`. Das Programm selbst muss das Modul gar nicht benutzen. Ein Projekt mit `main.py` (nur `print('hallo')`) und einer zweiten Übungsdatei `string.py` läuft ohne Debugger einwandfrei. Mit Debugger endet `DapClient.starten` nach 93,3 Sekunden mit „Der Debugger ließ sich nach 3 Versuchen nicht starten: Konnte nicht mit debugpy auf Port … verbinden.“ Was die Ursache ist, sagt die Meldung nicht. Beim Exe-Export läuft die Datei im Prozess von PyInstaller, und der Export bricht mit ihrem Fehler ab. Probe mit 50 typischen Dateinamen, jeweils `python -m PyInstaller --version` und `python -m debugpy --version` mit dem Projektordner als Arbeitsordner: Den Debugger brechen unter anderem `random`, `string`, `code`, `queue`, `json`, `copy`, `datetime`, `socket`, `inspect`, `enum`, `shutil`, `pickle` und `heapq`. Den Export brechen unter anderem `random`, `string`, `json`, `copy`, `datetime`, `logging`, `hashlib`, `uuid` und `zipfile`. Erwartet wäre, dass Debugger und Export so laufen wie der Start ohne Debugger oder dass die Meldung die störende Datei nennt.

**Ursache:** nachgewiesen. `ide/debugger/dap_client.py`, `debugpy_aufruf` (ab Zeile 131): `python -m debugpy` mit `cwd=arbeitsordner`. `ide/export/exporter.py`, Zeile 425 ff. und 479: `python -m PyInstaller` mit `cwd=projekt.ordner`. Mit `-m` setzt Python den Arbeitsordner an die erste Stelle von `sys.path`, noch vor die Standardbibliothek; die Werkzeuge importieren deshalb die Dateien der Schülerin. Dazu kommt `DapClient._verbinden` (Zeile 279): Die Schleife merkt nicht, dass der debugpy-Prozess schon beendet ist, und wartet bei jedem der drei Versuche die vollen 30 Sekunden.

**Zu tun:** Debugger und Exe-Export so starten, dass der Projektordner nicht vor der Standardbibliothek im Suchpfad steht, solange das Werkzeug selbst lädt (etwa `-P`). Das Schülerprogramm findet seine eigenen Units trotzdem: Den Ordner des Programms trägt erst die Hülle bzw. der Laufzeit-Hook ein. Der Verbindungsaufbau zum Debugger bricht ab, sobald der Prozess beendet ist, und meldet dann dessen Fehlerausgabe. Erledigt, wenn ein Test mit einem Projekt aus `main.py` und `random.py` (bzw. `string.py`) mit Debugger an einem Haltepunkt in `main.py` hält und der Exe-Export eine lauffähige Exe liefert.

## 446. Prüfungsmodus: die Prüfung vor dem Start nennt den richtigen Namen

**Gemeldet:** 2. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand 1445802 (0.4.2 mit Fehlerbehebungen).

**Beobachtet:** Das Handbuch, Abschnitt 4, sagt: Im Prüfungsmodus sagen Fehlermeldungen nur noch, was falsch ist, „kein Lösungsvorschlag“. Der Fehlerkatalog entfernt dafür auch Pythons eigenes „Did you mean …?“. Die Prüfung vor dem Start nennt im Prüfungsmodus dagegen weiter die richtige Schreibweise. Probe: `main.py` mit `from u_rechner import berechne`, in `u_rechner.py` steht `def Berechne()`, `pruefungsmodus_laeuft` gibt `True` zurück. Meldung im Panel und im Tooltip: „In u_rechner.py gibt es keine Funktion oder Klasse berechne. main.py ruft sie beim Start auf. Hier heißt sie Berechne, und Groß- und Kleinschreibung zählen.“ Der Teil „Zu prüfen“ fehlt dabei richtig; der Vorschlag steckt im Teil „Was“.

**Ursache:** nachgewiesen. `ide/run/pruefung.py`, `_import_fund` (Zeile 474 ff.): Der Hinweis auf die ähnlich geschriebene Definition wird an `meldung` angehängt (Zeile 513 bis 517). Für die Regel `natter-import` gibt `RuffFund.was` die `meldung` unverändert aus. Gesperrt wird im Prüfungsmodus nur `pruefe` (Zeile 222 ff.).

**Zu tun:** Den Satz „Hier heißt sie …“ in den Teil verschieben, der im Prüfungsmodus entfällt, oder ihn im Prüfungsmodus weglassen. Bei den übrigen eigenen Regeln der Prüfung vor dem Start nachsehen, ob „Was“ eine Korrektur enthält. Erledigt, wenn ein Test im Prüfungsmodus für den Fall oben weder in `was` noch in `str(fund)` den Namen `Berechne` findet und ihn außerhalb des Modus weiter findet.

## 447. Ein nachinstalliertes Paket mit `.pth`-Datei meldet bei jedem Start „Natter wurde verändert“

**Gemeldet:** 2. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand 1445802 (0.4.2 mit Fehlerbehebungen).

**Beobachtet:** Manche Pakete legen beim Installieren eine `.pth`-Datei unmittelbar in `site-packages`. Bekanntes Beispiel ist `pywin32` (`pywin32.pth`), das unter Windows unter anderem mit `pyttsx3` und `jupyter` mitkommt. Installiert jemand ein solches Paket über „Pakete → Paket installieren …“, fragt Natter danach bei jedem Start: „Natter wurde nach der Erstellung verändert: python/Lib/site-packages/pywin32.pth (zusätzlich). … Natter neu installieren …“ und „Trotzdem starten?“, voreingestellt „Nein“. Nachgestellt mit einer Wegwerf-Installation und eigenem Schlüssel: Vor dem Ablegen der `.pth` ist die schnelle Prüfung `in_ordnung`, danach nicht mehr, und gemeldet wird genau diese Datei. Der empfohlene Weg hilft nicht. Das Setup merkt sich nachinstallierte Pakete (`tools/installer_pakete_merken.py`) und installiert sie nach dem Kopieren wieder (`tools/natter.iss`, `CurStepChanged`). Damit liegt die `.pth` wieder da, und die Meldung kommt weiter. Erwartet wäre, dass ein über das Menü „Pakete“ installiertes Paket keinen Integritätsalarm auslöst, so wie es seit Punkt 40 für `python/Scripts` und für den Rest von `site-packages` gilt.

**Ursache:** nachgewiesen. `ide/integritaet/manifest.py`, `ist_startdatei` (Zeile 175 ff.) und `_erfasst` (Zeile 140 ff.): Jede `.pth` unmittelbar in `site-packages` gilt seit Punkt 230 als Startdatei, steht unter Aufsicht und gehört zur schnellen Prüfung bei jedem Start (`ist_kerndatei`, `_kandidaten`). Eine Datei, die nicht im Manifest steht, wird zum Befund `fremd`, auch wenn `pip` sie bestimmungsgemäß angelegt hat. Probe: `_erfasst("python/Lib/site-packages/pywin32.pth")` und `ist_kerndatei(…)` liefern beide `True`.

**Zu tun:** Eine `.pth`, die zu einem über `pip` installierten Paket gehört, von einer unterschobenen unterscheiden. Ein Anhaltspunkt: Sie steht in der `RECORD`-Datei eines `*.dist-info` in `site-packages`, das nicht zu Natter gehört. Die Startprüfung soll sie dann nicht als Veränderung von Natter melden, höchstens als Hinweis wie bei den Bibliotheken. Was der Schutz aus Punkt 230 dabei verliert, in `docs/bericht.md`, Abschnitt 7.5, festhalten. Erledigt, wenn ein Test eine `.pth` samt passendem `dist-info` ohne Befund durchlässt und eine `.pth` ohne zugehöriges Paket weiter als `zusätzlich` meldet.

## 448. Alt+Pfeil und Strg+D auf einer zugeklappten Funktion zerreißen den Code

**Gemeldet:** 2. Oktober 2026, Durchsicht, Entwicklungsstand 0.4.2 plus Fehlerbehebungen (Commit 1445802).

**Beobachtet:** Probe offscreen mit `QuelltextEditor`: Eine Klasse mit den Methoden `a` (Zeilen 2–5) und `b` wird geladen, `falten(2)` klappt `a` zu, und die Schreibmarke steht in Zeile 2. Alt+Pfeil runter (`zeile_verschieben(True)`) tauscht nur die sichtbare Kopfzeile mit der ersten versteckten Rumpfzeile. Danach steht `        x = 1` vor `    def a(self):`, die Datei hat einen Einrückungsfehler, und die Faltung ist aufgehoben. Strg+D (`zeile_duplizieren`) auf derselben Kopfzeile ergibt zweimal `def a(self):` direkt untereinander, der erste Kopf hat keinen Rumpf. Erwartet wäre, dass beide Befehle die ganze zugeklappte Funktion bewegen bzw. verdoppeln, so wie sie zu sehen ist.

Dazu kommt: Wer eine Zeile außerhalb der Faltung verschiebt (Zeile 1 „import os“ bei zugeklappter Funktion in Zeile 4), bekommt den Rumpf der Funktion wieder sichtbar. `_gefaltet` meldet aber weiter `{4}`, Rand und Text widersprechen sich also.

**Ursache:** nachgewiesen. `zeile_verschieben` (`ide/shell/quelltexteditor.py`, ab Zeile 1256) tauscht zwei Einträge in `toPlainText().split("\n")` und setzt das ganze Dokument neu. Versteckte Blöcke zählen dabei als gewöhnliche Zeilen, und das Neusetzen macht alle Blöcke sichtbar, ohne `_gefaltet` zu leeren. `zeile_duplizieren` (Zeile 1248) kopiert nur `cursor.block().text()`. Faltungen sind über den Rand, „Alles zuklappen“ und das Kontextmenü erreichbar, die Tasten stehen im Handbuch (Tabelle bei Zeile 918).

**Zu tun:** Steht die Schreibmarke auf einer zugeklappten Kopfzeile, wirken beide Befehle auf Kopf und Rumpf zusammen. Die Nachbarzeile, mit der getauscht wird, ist die nächste sichtbare Zeile bzw. ein ganzer zugeklappter Block. Andere Faltungen bleiben zu, und `_gefaltet` stimmt mit dem Bild überein. Erledigt, wenn ein Test die Probe oben mit unverändert gültigem Python (`ast.parse`) und weiter zugeklappter Funktion beendet.

## 449. Negative Werte bei `Timer.interval`, `StringGrid.row_count` und `col_count` werden still angenommen und wirken falsch

**Gemeldet:** 2. Oktober 2026, Durchsicht, Entwicklungsstand 0.4.2 plus Fehlerbehebungen (Commit 1445802).

**Beobachtet:** Probe offscreen:
- Nach `t.interval = -100` liefert `t.interval` den Wert -100, der `QTimer` läuft aber mit 1 ms. Nach `t.interval = 0` feuert `on_timer` ohne Pause. In Spielen wird das Intervall oft schrittweise verkleinert (`self.t_takt.interval -= 100`). Unter null rast das Spiel dann los, ohne jede Meldung.
- Bei einem `StringGrid` mit drei Zeilen ergibt `row_count = -1` das Ergebnis `row_count == -1`, die Tabelle zeigt aber weiter zwei Zeilen. `cells[0, 0]` meldet dann „Zeile 0 gibt es nicht, die Tabelle hat -1 Zeilen (0 bis -2).“
- Nach `col_count = -1` meldet das Modell -1 Spalten.

Im Objektinspektor gehen dieselben Werte ebenso durch. Erwartet wäre eine deutsche Meldung, wie sie `Canvas.pen.width` schon bringt („erwartet eine Breite ab 1“).

**Ursache:** nachgewiesen. `Timer._bei_prop_aenderung` (`pcl/components/system.py`) gibt den Wert ungeprüft an `QTimer.setInterval`; Qt macht aus negativen Werten 1 ms. `StringGrid._bei_prop_aenderung` (`pcl/components/additional.py`) ruft `setRowCount`/`setColumnCount`, und `TabellenModell.zeilenzahl_setzen`/`spaltenzahl_setzen` (`pcl/components/tabelle.py`) löscht bei -1 mit `del self._zeilen[-1:]` nur die letzte Zeile bzw. setzt `_spalten = -1`. `EigenschaftenTabelle.wert_pruefen` (`ide/inspector/eigenschaften_tabelle.py`, ab Zeile 402) prüft nur Farben und Bilder.

**Zu tun:** `interval` unter 1 sowie `row_count` und `col_count` unter 0 mit `NatterPropertyError` und deutschem Satz ablehnen, im Programm wie im Objektinspektor. `docs/komponenten.md` nennt die Untergrenzen. Erledigt, wenn ein Test für alle drei Eigenschaften die Meldung bekommt und der alte Wert samt Anzeige bleibt.

## 450. Haltepunkt bleibt beim Verschieben einer Zeile mit Alt+Pfeil an der alten Zeilennummer

**Gemeldet:** 2. Oktober 2026, Durchsicht, Entwicklungsstand 0.4.2 plus Fehlerbehebungen (Commit 1445802).

**Beobachtet:** Probe offscreen mit dem Text „a = 1 / b = 2 / c = 3“. Haltepunkt in Zeile 1, dann Alt+Pfeil runter auf Zeile 1. Der Text lautet danach „b = 2 / a = 1 / c = 3“, der Haltepunkt steht weiter bei `{1}`, also jetzt auf `b = 2`. Beim nächsten Start mit Debugger hält das Programm an der falschen Anweisung. Erwartet wäre, dass der Haltepunkt mit `a = 1` nach Zeile 2 wandert. Beim Einfügen und Löschen von Zeilen tut er das seit Punkt 119.

**Ursache:** nachgewiesen. `zeile_verschieben` (`ide/shell/quelltexteditor.py`, ab Zeile 1256) ersetzt das ganze Dokument, ohne dass sich die Zeilenzahl ändert. `_breakpoints_nachfuehren` (ab Zeile 444) reagiert nur auf einen Unterschied in der Zeilenzahl (`if not unterschied …: return`).

**Zu tun:** `zeile_verschieben` tauscht Haltepunkte und Bedingungen der beiden Zeilen mit und meldet `breakpoints_geaendert`. Erledigt, wenn ein Test den Haltepunkt samt Bedingung nach Alt+Pfeil hoch und runter auf derselben Anweisung findet.

## 451. Sortierte ListBox und CSV-Ansicht ordnen Umlaute hinter „Z“, die CSV-Ansicht auch Kleinbuchstaben

**Gemeldet:** 2. Oktober 2026, Durchsicht, Entwicklungsstand 0.4.2 plus Fehlerbehebungen (Commit 1445802).

**Beobachtet:** Probe mit den Namen „Zimmer, Özdemir, anna, Bauer, Ärger, ulla“:
- `ListBox` mit `sorted = True` ergibt „anna, Bauer, ulla, Zimmer, Ärger, Özdemir“.
- Die CSV-Ansicht, aufsteigend nach der Spalte sortiert, ergibt „Bauer, Zimmer, anna, ulla, Ärger, Özdemir“.

Eine nach Namen sortierte Klassenliste hat damit alle Namen mit Umlaut am Ende, und in der CSV-Ansicht stehen klein geschriebene Einträge hinter allen großen. Erwartet wäre die Reihenfolge eines deutschen Wörterbuchs: „anna, Ärger, Bauer, Özdemir, ulla, Zimmer“.

**Ursache:** nachgewiesen. `ListBox._items_geaendert` (`pcl/components/standard.py`, Zeile 513) sortiert mit `key=str.casefold`, und das ordnet nach Codepunkten. `_sortierschluessel` (`ide/viewers/csv_ansicht.py`, ab Zeile 277) legt für Textzellen den unveränderten Zelltext als Schlüssel ab, `_Tabellendaten.sortieren` vergleicht ihn direkt.

**Zu tun:** Ein gemeinsamer Sortierschlüssel für deutschen Text, z. B. `QCollator` mit deutscher Locale oder eine eigene Umschreibung von ä/ö/ü/ß mit `casefold`. ListBox und CSV-Ansicht verwenden ihn beide. Erledigt, wenn ein Test die Namen oben in beiden Fällen in Wörterbuchreihenfolge findet.

## 452. Design-Prüfung übergeht alles in Panels und GroupBoxen und meldet einen Timer als Überlappung

**Gemeldet:** 2. Oktober 2026, Durchsicht, Entwicklungsstand 0.4.2 plus Fehlerbehebungen (Commit 1445802).

**Beobachtet:** Probe mit `ide.lint.regeln.pruefen` auf einem Formular mit einem Panel. Darin überlappen sich zwei Knöpfe, ein dritter ragt rechts über das Panel hinaus (left 180 + 75 > 200). Daneben liegt ein `Timer`, dessen Symbol einen Knopf auf dem Formular berührt. Gemeldet wird nur „b_start überlappt mit t_takt. Eine der beiden verschieben oder schmaler machen, damit beide anklickbar bleiben.“ Der Timer ist im laufenden Programm aber unsichtbar. Die beiden Fehler im Panel bleiben ohne Meldung. RadioButtons in einer GroupBox oder Knöpfe in einem Panel sind im Unterricht häufig, gerade dort bleiben Überlappung, fehlende Beschriftung, Kontrast und Klickfläche ungeprüft.

**Ursache:** nachgewiesen. `_geometrie_pruefen`, `_lesbarkeit_pruefen`, `_beschriftung_pruefen`, `_konsistenz_pruefen` und `_bedienbarkeit_pruefen` in `ide/lint/regeln.py` (Zeilen 232, 370, 413, 437, 504) lesen nur `pfm.get("children")`. Nur die Namensprüfung steigt über `_alle_komponenten` in Behälter ab. Komponenten mit `nur_im_designer` (Timer, MainMenu, PopupMenu) werden nirgends ausgenommen.

**Zu tun:** Die Regeln prüfen jede Ebene: Geschwister untereinander und gegen die Fläche ihres Behälters. Komponenten mit `nur_im_designer` fallen aus Überlappung, Abständen und Kanten heraus. Erledigt, wenn ein Test die Probe oben mit zwei Funden im Panel und ohne Fund zum Timer beendet.

## 453. Struktogramm: „für jedes x in liste“ wird zu einer Schleife, die nie läuft

**Gemeldet:** 2. Oktober 2026, Durchsicht, Entwicklungsstand 0.4.2 plus Fehlerbehebungen (Commit 1445802).

**Beobachtet:** Probe mit `als_python`: Eine Zählschleife mit dem Kopf „für jedes x in liste“ ergibt `# für jedes x in liste` und `for _ in range(0):`. Der Rumpf läuft nie, und `x` ist darin unbekannt. „for x in liste“ und „für x in liste“ werden dagegen übernommen. „für jedes …“ bzw. „für jeden …“ ist die übliche Schreibweise für das Durchlaufen einer Liste.

**Ursache:** nachgewiesen. `_zaehlkopf` (`ide/diagramm/struktogramm_code.py`, ab Zeile 687) schneidet über `_FUER` nur „für/fuer/for“ ab. „jedes x in liste“ ist kein Python, `_von_bis` passt nicht, und der Kopf fällt auf den Platzhalter zurück.

**Zu tun:** Nach „für“ auch „jedes/jede/jeden“ abschneiden, sofern danach „Name in Ausdruck“ steht. Erledigt, wenn ein Test „für jedes x in liste“ zu `for x in liste:` übersetzt und ausführt.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
