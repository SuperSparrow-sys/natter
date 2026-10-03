# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **567**.

## Ein neuer Punkt

```markdown
## 567. Kurz, was nicht stimmt

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

## 540. Eine Ausnahme im Schülerprogramm unter dem Debugger lässt die IDE beliebige Module importieren

**Gemeldet:** 3. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand `241f38d`.

**Beobachtet:** Hält der Debugger an einer unbehandelten Ausnahme, importiert die IDE das Modul, das in der `exceptionId` der DAP-Antwort steht, in ihrem eigenen Prozess. Den Namen bestimmt das Schülerprogramm über `__qualname__` seiner Ausnahmeklasse. Eine Klasse namens `this.Fehler` ließ die IDE „The Zen of Python“ drucken; ein Modul, das beim Import `sys.exit` ruft (`jsonschema.__main__`), beendete die IDE ohne Meldung und ohne Frage nach ungespeicherten Änderungen.

**Ursache:** nachgewiesen. `_exception_klasse_aufloesen` (`pcl/fehlerkatalog.py`, um Zeile 1744) ruft `importlib.import_module` mit dem Namen aus der Antwort, aufgerufen über `fehlermeldung_aus_dap_erzeugen` aus `_debugger_exceptioninfo_bereit` im Hauptfaden.

**Zu tun:** Nichts importieren: nur eingebaute Ausnahmen und Klassen aus Modulen nachschlagen, die schon in `sys.modules` stehen. Erledigt, wenn ein Test mit einer `exceptionId` auf ein nicht geladenes Modul zeigt, dass es danach nicht in `sys.modules` steht.

## 541. Eine SVG-Datei im Projekt lässt die IDE Dateien außerhalb des Projekts und auf Netzpfaden lesen

**Gemeldet:** 3. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand `241f38d`.

**Beobachtet:** Bilder lädt der Designer nur aus dem Projektordner (Punkt 334). Eine SVG darin darf aber auf beliebige Pfade verweisen, auch `..`, absolute und UNC-Pfade, und Qt lädt sie. Eine `.pfm` mit `picture: assets/bild.svg`, deren SVG auf `\\localhost\c$\…\aussen.png` zeigte, zeigte nach dem Laden das Bild hinter dem Netzpfad. Schon das Öffnen eines fremden Formulars baut so eine SMB-Verbindung samt Anmeldung auf.

**Ursache:** nachgewiesen. `.svg` steht in `BILD_ENDUNGEN` (`ide/designer/bilder.py`); `_im_projektordner` (`pcl/components/additional.py`) prüft nur den Pfad der SVG selbst. Geladen wird über `QPixmap`/`QIcon`.

**Zu tun:** Eine SVG im IDE-Prozess nur ohne externe Verweise darstellen, Verweise vor dem Rendern entfernen. Erledigt, wenn ein Test eine SVG mit Verweis nach außen ohne dieses Bild darstellt und auf den Pfad nicht zugegriffen wird.

## 542. Der Port von debugpy nimmt Verbindungen ohne Kennung an

**Gemeldet:** 3. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand `241f38d`.

**Beobachtet:** debugpy wartet auf 127.0.0.1 an einem freien Port ohne Kennung; eine fremde Verbindung bekam auf `initialize` eine Antwort. Auf einem Rechner mit mehreren Sitzungen (Terminalserver) könnte ein anderes Konto sich verbinden, bevor die IDE es tut, und über den Debugger Code im Konto der Schülerin ausführen. Dieser Teil ist vermutet.

**Ursache:** nachgewiesen für den offenen Port: `ide/debugger/dap_client.py`, `_freien_port_finden` und `--listen <port> --wait-for-client`.

**Zu tun:** Die IDE lauscht, und debugpy verbindet sich zu ihr (`--connect`), oder die Verbindung wird an eine Kennung gebunden. Erledigt, wenn eine fremde Verbindung keine Sitzung bekommt.

## 543. Der Paketname aus „Pakete → Paket installieren …“ geht ungeprüft an pip

**Gemeldet:** 3. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand `241f38d`.

**Beobachtet:** Eine Eingabe, die mit `-` beginnt, liest pip als Schalter, etwa als Anforderungsdatei mit eigenem Paketverzeichnis über HTTP; Adressen und lokale Pfade gehen als Quelle durch.

**Ursache:** nachgewiesen. `ide/env/pakete.py` (Name als letztes Argument von `pip install`) und `_paket_installieren_aktion` in `ide/shell/hauptfenster.py` ohne Prüfung.

**Zu tun:** Nur Paketnamen nach PEP 508, wahlweise mit Version, annehmen, `--` vor den Namen setzen. Erledigt, wenn ein Test `-r…`, `--index-url=…`, `C:\…` und `https://…` deutsch ablehnt, ohne pip zu starten.

## 544. Prüfungsmodus: Datenbank-Panel und Testlauf geben weiter Lösungshinweise

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `241f38d`.

**Beobachtet:** Laut Handbuch, Abschnitt 4, sagen Meldungen im Modus nicht, woran es liegen könnte. Das Datenbank-Panel hängt bei SQL-Fehlern weiter „In SQL steht in einer Kommazahl ein Punkt …“ an, der Testlauf weiter Hinweise zu `main()` und `Application()`.

**Ursache:** nachgewiesen. `ide/database/panel.py` (`_kommazahl_hinweis`), `ide/testrunner/harness.py` (`_EINGABE_HINWEIS`), `ide/testrunner/ausfuehrung.py`; keine Abfrage von `pcl.pruefungsmodus.laeuft()`.

**Zu tun:** Die Hinweise im Modus weglassen. Erledigt, wenn ein SQL-Fehler mit `2.5` im Modus ohne Hinweis erscheint.

## 545. F12 öffnet die erzeugte `_design.py` zum Bearbeiten, Änderungen darin gehen verloren

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `241f38d`.

**Beobachtet:** In `u_main.py` steht der Cursor auf `self.e_zahl1`, F12 öffnet `u_main_design.py` in einem beschreibbaren Reiter. Eine dort gespeicherte Zeile ist nach der nächsten Änderung im Designer ohne Warnung weg.

**Ursache:** nachgewiesen. `_zur_definition_springen` (`ide/shell/hauptfenster.py`) übergibt jede Fundstelle an `datei_oeffnen`, das erzeugte Dateien nicht unterscheidet.

**Zu tun:** Führt eine Definition in eine `*_design.py`, den Designer öffnen und die Komponente auswählen. Erledigt, wenn F12 auf `self.e_zahl1` keinen Reiter mit `u_main_design.py` öffnet, sondern den Designer mit `e_zahl1` ausgewählt.

## 546. Der Diagramm-Editor überschreibt eine von außen geänderte `.pdiag` ohne Nachfrage

**Gemeldet:** 3. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand `241f38d`.

**Beobachtet:** Zwei Natter-Fenster öffnen dasselbe Diagramm. A ändert und speichert, danach speichert B: die Änderung aus A ist ohne Nachfrage verloren. Für Editor und Designer prüft Punkt 286 diesen Fall.

**Ursache:** nachgewiesen. `DiagrammFenster.speichern` (`ide/diagramm/fenster.py`) und `ide/diagramm/datei.py` schreiben ohne Vergleich mit `ide/dateistand.py`.

**Zu tun:** Dateistand beim Laden und Speichern merken, vor dem Schreiben bei einer Änderung von außen fragen. Erledigt, wenn die Probe mit zwei Fenstern nachfragt und bei „Nein“ die Änderung aus A bleibt.

## 547. `Strings.save_to_file` schreibt nicht atomar

**Gemeldet:** 3. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand `241f38d`.

**Beobachtet:** Ein Zeichen, das in der gewählten Kodierung fehlt, eine volle Platte oder ein abgezogener Stick mitten im Schreiben hinterlassen eine abgeschnittene Datei; die alte ist verloren. `10_Notizbuch` benutzt die Methode.

**Ursache:** nachgewiesen. `pcl/strings.py`, `save_to_file` öffnet die Zieldatei direkt mit `"w"`.

**Zu tun:** Zuerst vollständig kodieren, dann über eine Zwischendatei mit `os.replace` schreiben. Erledigt, wenn ein Kodierfehler die alte Datei unverändert lässt.

## 548. Tief verschachteltes JSON oder eine sehr lange Zahl in einer Projektdatei endet in der Absturzmeldung

**Gemeldet:** 3. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand `241f38d`.

**Beobachtet:** Eine `.natter`, `.pfm` oder `.pdiag` mit tief verschachteltem JSON wirft `RecursionError`, eine Zahl mit mehr als 4300 Ziffern `ValueError`, beides als Ausnahme statt „ist beschädigt“. Eine `.pfm` mit 300 ineinander liegenden Panels scheitert im Designer ebenso. Beim Start über die Dateiverknüpfung beendet sich Natter nach dem Fehlerdialog.

**Ursache:** nachgewiesen. `json_datei_lesen` (`ide/schema.py`) lässt beide Ausnahmen durch; `_oeffnen_fehler` und die `except`-Listen in `ide/shell/hauptfenster.py` kennen nur `json.JSONDecodeError`; `_projekt_aus_argv_oeffnen` in `ide/main.py` hat kein eigenes `try`.

**Zu tun:** Beide Ausnahmen als „beschädigt“ melden, eine Grenze für die Verschachtelung einer `.pfm`, und der Start mit so einer Datei lässt das Fenster offen. Erledigt, wenn die drei Proben für alle drei Dateiarten die Meldung zeigen.

## 549. Formular-Import (.lfm): Absturz bei ANSI-Dateien und offenem Listenende, `#13#10` und `+`-Fortsetzungen falsch

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `241f38d`.

**Beobachtet:** Eine `.lfm` in Windows-1252 endet in `UnicodeDecodeError`; `Lines.Strings = (` mit `)` hinter dem letzten Eintrag in `IndexError`; `'Zeile 1'#13#10'Zeile 2'` landet wörtlich in der Beschriftung; eine Fortsetzungszeile mit `+'…'` wird als unerwartete Zeile abgelehnt.

**Ursache:** nachgewiesen. Lesen nur mit `utf-8-sig` in `_formular_importieren_aktion` (`ide/shell/hauptfenster.py`); `_skalar_parsen`, `_wert_parsen` und `_objekt_parsen` in `ide/import_lfm/parser.py`.

**Zu tun:** Verkettete Texte aus Hochkommas und `#nn` sowie `+`-Zeilen lesen, `)` am Ende eines Eintrags annehmen, Dateiende ohne `)` als `LfmParserError` melden, bei einem Dekodierfehler auf cp1252 ausweichen. Erledigt, wenn alle vier Proben ohne Ausnahme durchlaufen und die Beschriftung „Zeile 1\nZeile 2“ lautet.

## 550. Python-eigene Ereignisfilter in Zyklen werden in Nebenfäden zerstört

**Gemeldet:** 3. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand `241f38d`.

**Beobachtet:** Nach Öffnen und Schließen von Designer, Editor, Diagrammen und CSV-Ansicht liegen `pcl.control._MausFilter`, `pcl.form._FensterFilter` und `_EscapeWache` als Python-eigene, gültige `QObject`s in Speicherzyklen. Eine Probe zeigte, dass die Speicherbereinigung einen `_MausFilter` in einem Nebenfaden zerstört. Dasselbe Muster wie Punkt 534, ohne Uhr; ein Absturz ist hier vermutet.

**Ursache:** nachgewiesen. `_MausFilter.__init__` (`pcl/control.py`), `_FensterFilter` (`pcl/form.py`) und `_EscapeWache.__init__` (`ide/designer/canvas.py`) rufen `super().__init__()` ohne Eltern.

**Zu tun:** Die Filter bekommen das gefilterte Widget bzw. den Designer als Eltern. Erledigt, wenn die Probe keine Python-eigenen, gültigen Filter mehr in Zyklen findet.

## 551. DBNavigator: „<<“ und „>>“ beenden das Programm, solange die Abfrage nicht geöffnet ist

**Gemeldet:** 3. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand `241f38d`.

**Beobachtet:** An einer nicht geöffneten oder geschlossenen `SQLQuery` werfen „<<“ und „>>“ `NatterDatenbankError`, das Schülerprogramm endet; „<“ und „>“ tun nichts.

**Ursache:** nachgewiesen. `_erster`/`_letzter` in `pcl/components/data_controls.py` prüfen nicht wie `_vor`/`_zurueck`.

**Zu tun:** Ohne geöffnete Abfrage nichts tun. Erledigt, wenn alle vier Knöpfe ohne Ausnahme bleiben.

## 552. Ein gescheiterter Versuch, eine Datei im Editor zu öffnen, lässt einen Editor im Speicher zurück

**Gemeldet:** 3. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand `241f38d`.

**Beobachtet:** `datei_oeffnen` auf eine Datei, die kein UTF-8 ist, meldet richtig „keine Textdatei“; der vorher gebaute `QuelltextEditor` lebt aber samt Uhr und Verbindungen weiter, auch nach `gc.collect()`.

**Ursache:** nachgewiesen. `datei_oeffnen` (`ide/shell/hauptfenster.py`) baut und verbindet den Editor, bevor feststeht, ob die Datei lesbar ist, und gibt ihn im Fehlerfall nicht frei.

**Zu tun:** Erst lesen, dann bauen, oder im Fehlerfall `deleteLater()`. Erledigt, wenn kein verworfener Editor mehr lebt.

## 553. Die Prüfung vor dem Start ruft ruff ohne Zeitgrenze

**Gemeldet:** 3. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand `241f38d`.

**Beobachtet:** Vermutet: Bei einem Projekt auf einem nicht mehr erreichbaren Netzlaufwerk steht Natter, bis ruff zurückkehrt; nicht nachgestellt.

**Ursache:** nachgewiesen für die fehlende Grenze: `_ruff_pruefen` (`ide/run/pruefung.py`), `subprocess.run` ohne `timeout`.

**Zu tun:** Eine Zeitgrenze; danach ohne Prüfung starten und das in der Statuszeile sagen. Erledigt, wenn eine Attrappe, die nicht zurückkehrt, den Start nach der Grenze nicht mehr aufhält.

## 554. Die Integritätsprüfung beim Start entfällt ohne Meldung, wenn `Natter.exe` fehlt

**Gemeldet:** 3. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand `241f38d`.

**Beobachtet:** Ob geprüft wird, hängt allein an `Natter.exe` neben dem Ordner `python`. `python\pythonw.exe -m ide` startet die IDE auch ohne sie, dann werden weder Manifest noch Signatur geprüft. Der Docstring behauptet, ohne den Starter lasse sich Natter nicht starten.

**Ursache:** nachgewiesen am Code. `programmordner` und `installation_pruefen` in `ide/integritaet/start_pruefung.py`.

**Zu tun:** Die Installation an einem Merkmal erkennen, das ohne Starter bleibt (etwa `manifest.json`), eine fehlende `Natter.exe` als Befund melden, Docstring berichtigen. Erledigt, wenn ein Test mit nachgebautem Aufbau ohne `Natter.exe` einen Befund erhält.

## 555. Testlauf: gescheiterte `subTest`-Fälle, übersprungene und `expectedFailure`-Tests verschwinden

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `241f38d`.

**Beobachtet:** Eine Testdatei mit `test_sub` (zwei gescheiterte Subtests), einem `@unittest.skip`-Test, einem bestandenen `@unittest.expectedFailure`-Test und `test_ok` ergibt nur „1 Test gelaufen, 0 nicht bestanden“, ebenso im HTML-Protokoll. `python -m unittest` meldet zwei Fehlschläge und einen unerwarteten Erfolg.

**Ursache:** nachgewiesen. `_StrukturiertesErgebnis` (`ide/testrunner/harness.py`) überschreibt nur `addSuccess`, `addFailure` und `addError`.

**Zu tun:** `addSubTest`, `addSkip`, `addExpectedFailure` und `addUnexpectedSuccess` melden, gescheiterte Subtests mit ihren Parametern. Erledigt, wenn die Probe `test_sub` als nicht bestanden zeigt und keiner der vier Tests fehlt.

## 556. Testlauf: ein Fehler in `setUpClass` ergibt eine zerlegte Test-ID und eine Meldung über eine fehlende Datei

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `241f38d`.

**Beobachtet:** `setUpClass` mit `RuntimeError` liefert die ID `setUpClass (test_b.T)`, der Baum zeigt ein Modul „setUpClass (test_b“ mit dem Eintrag „T)“, ein Doppelklick meldet „Die Testdatei setUpClass (test_b.py lässt sich nicht laden“. Die Dauer erscheint als „-0,000“.

**Ursache:** nachgewiesen. `_tests_baum_befuellen` (`ide/shell/hauptfenster.py`) trennt jede ID an Punkten; `ide/testrunner/harness.py` übernimmt `_ErrorHolder.id()`; `_dauer` liest `time.perf_counter()` zu früh.

**Zu tun:** `_ErrorHolder` erkennen und Klasse bzw. Modul als ID melden, mit deutschem Text wie „Vorbereitung der Klasse T gescheitert“; Dauer nie negativ. Erledigt, wenn die Probe einen Eintrag unter `test_b → T` zeigt.

## 557. Panel „Tests“ und HTML-Protokoll zeigen nach einem Projektwechsel das alte Projekt, Einzelläufe fehlen im Protokoll

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `241f38d`.

**Beobachtet:** Nach einem Testlauf in einem Projekt und dem Öffnen eines anderen zeigt „Tests“ weiter die alten Ergebnisse, der HTML-Export schreibt sie unter dem neuen Titel, ein Doppelklick führt die alte Test-ID im neuen Ordner aus. Ein Test, der nach einer Korrektur per Doppelklick besteht, steht im Protokoll weiter als nicht bestanden.

**Ursache:** nachgewiesen. `_letzte_testergebnisse` setzt nur `_tests_fertig`, `tests_baum.clear()` steht nur in `_tests_baum_befuellen`, `_einzeltest_fertig` ändert nur den Baum (`ide/shell/hauptfenster.py`).

**Zu tun:** Beim Öffnen und Schließen eines Projekts beides leeren, Einzelläufe in die gemerkten Ergebnisse übernehmen. Erledigt, wenn nach einem Projektwechsel das Panel leer ist und der Export einen Einzellauf enthält.

## 558. „Unit öffnen …“ (Strg+P) öffnet ein Formular als JSON-Text im Editor

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `241f38d`.

**Beobachtet:** Die Liste enthält `u_main.pfm`; die Wahl öffnet die `.pfm` als beschreibbaren Text, auch wenn der Designer sie offen hat. Der Docstring von `oeffnen` nennt genau das als behobenen Fehler.

**Ursache:** nachgewiesen. `_unit_oeffnen_dialog` (`ide/shell/hauptfenster.py`) ruft `datei_oeffnen` statt `oeffnen`.

**Zu tun:** Über `oeffnen` gehen. Erledigt, wenn die Wahl von `u_main.pfm` den Designer zeigt.

## 559. Menüeinträge: „Angekreuzt“ lässt sich im Programm nur abwählen, und der Zustand kommt nicht im Eintrag an

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `241f38d`.

**Beobachtet:** Ein Eintrag ohne `checked` ist nicht ankreuzbar; einer mit `checked: True` verliert beim Klick das Häkchen, aber `eintrag(...)["checked"]` bleibt `True`, auch im Handler, und nach `aktualisieren()` ist das Häkchen wieder da. Ein Umschalter wie „Raster anzeigen“ lässt sich so nicht bauen.

**Ursache:** nachgewiesen. `pcl/components/menus.py`: `setCheckable(True)` nur bei `checked`, kein Rückweg vom Klick in den Eintrag.

**Zu tun:** Ankreuzbarkeit vom Anfangszustand trennen (eigenes Feld `checkable` samt Schema, Menü-Editor und Doku), den Zustand nach einem Klick in den Eintrag schreiben. Erledigt, wenn ein anfangs leerer Eintrag sich ankreuzen lässt und der Handler den neuen Zustand liest.

## 560. Projekt-Explorer: Datenbank, PDF und andere Nicht-Textdateien unter „Dateien“ enden in „keine Textdatei“

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `241f38d`.

**Beobachtet:** Ein Doppelklick auf `konten.sqlite` meldet „„konten.sqlite“ ist keine Textdatei …“, ebenso für ein Aufgabenblatt als `.pdf` oder `.docx`. Punkt 104 (erledigt) verspricht einen passenden Betrachter.

**Ursache:** nachgewiesen. `oeffnen` (`ide/shell/hauptfenster.py`) kennt nur CSV, Bilder, HTML und Markdown.

**Zu tun:** `.sqlite`/`.db` im Datenbank-Panel verbinden, PDF und Office-Dateien mit dem zuständigen Windows-Programm öffnen. Erledigt, wenn ein Doppelklick auf `konten.sqlite` das Panel mit dieser Datei verbindet.

## 561. Menü-Tastenkürzel mit deutschen Tastennamen wie „Strg+Ende“ wirken nicht, „Delete“ wird zu „Entfete“

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `241f38d`.

**Beobachtet:** `Strg+Ende`, `Strg+Pos1` und `Strg+Bild auf` ergeben kein Kürzel, im Menü steht es trotzdem. `Ctrl+Delete` erscheint als „Strg+Entfete“, `Ctrl+Insert` als „Strg+Einfgert“.

**Ursache:** nachgewiesen. `_TASTENNAMEN` und `kuerzel_anzeige` in `pcl/components/menus.py` ersetzen Teilzeichenketten und kennen nur Strg, Umschalt, Entf und Einfg.

**Zu tun:** Tastennamen als ganze Teile zwischen `+` umsetzen, Pos1, Ende, Bild auf, Bild ab, Rück ergänzen, ein Kürzel ohne Wirkung melden. Erledigt, wenn `Strg+Ende` wirkt und `Ctrl+Delete` als „Strg+Entf“ erscheint.

## 562. Lesereihenfolge (Tab-Reihenfolge, Design-Prüfung) teilt Zeilen an festen 24-Pixel-Grenzen

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `241f38d`.

**Beobachtet:** „rechts“ (200, 46) und „links“ (10, 50) ergeben „rechts“ vor „links“, (200, 40) und (10, 47) dagegen „links“ zuerst. Der Kommentar verspricht, was weniger als 24 px auseinander liegt, gelte als nebeneinander.

**Ursache:** nachgewiesen. `lesereihenfolge` (`ide/lint/regeln.py`), Schlüssel `top // _ZEILENHOEHE`.

**Zu tun:** Zeilen nach Abstand zum Zeilenanfang bilden. Erledigt, wenn beide Proben „links“ vor „rechts“ liefern.

## 563. HTML-Vorschau: nach einem Verweis lädt das Speichern die falsche Seite

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `241f38d`.

**Beobachtet:** Nach einem Klick auf `seite2.html` beobachtet die Vorschau weiter nur `index.html`: Änderungen an `seite2.html` erscheinen nicht, und Speichern von `index.html` springt auf die erste Seite zurück.

**Ursache:** nachgewiesen. `_neu_laden` in `ide/viewers/html_vorschau.py` zeigt immer `self._pfad` und beobachtet nur diese Datei.

**Zu tun:** Die gerade gezeigte Seite beobachten und neu laden. Erledigt, wenn eine Änderung an `seite2.html` bei offener Seite 2 sofort erscheint.

## 564. Markdown: der Reiter zeigt den Dateinamen statt der Überschrift, wenn die Datei mit BOM gespeichert ist

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `241f38d`.

**Beobachtet:** `README.md` mit UTF-8-BOM und `# Obstsortierer` ergibt den Reiter „README.md“.

**Ursache:** nachgewiesen. `_markdown_titel` (`ide/shell/hauptfenster.py`) liest mit `utf-8` statt `utf-8-sig`.

**Zu tun:** Mit `utf-8-sig` lesen. Erledigt, wenn der Reiter „Obstsortierer“ heißt.

## 565. „Unit umbenennen“ lehnt eine reine Änderung der Groß- und Kleinschreibung ab

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `241f38d`.

**Beobachtet:** `u_konto.py` in `U_Konto.py` umzubenennen meldet „gibt es schon“; beim Formular ist dieser Fall eigens erlaubt.

**Ursache:** nachgewiesen. `_unit_umbenennen` (`ide/shell/hauptfenster.py`): `if ziel.exists()` ohne Ausnahme für die eigene Datei.

**Zu tun:** Die eigene Datei ausnehmen wie in `_formular_umbenennen`. Erledigt, wenn `u_konto` → `U_Konto` gelingt.

## 566. Häufige SQLite-Fehler kommen englisch an, ein CSV-Import mit `sqlite_` im Namen scheitert englisch

**Gemeldet:** 3. Oktober 2026, Sicherheitsprüfung, Entwicklungsstand `241f38d`.

**Beobachtet:** Unübersetzt bleiben unter anderem `unrecognized token: "'Meier"` (offenes Anführungszeichen), `misuse of aggregate function sum()`, `sub-select returns 2 columns - expected 1`, `database or disk is full`, `too many columns on …`. Der Import von `sqlite_daten.csv` meldet „object name reserved for internal use: sqlite_daten_natter_import“.

**Ursache:** nachgewiesen. `_datenbankmeldung_eindeutschen` (`pcl/fehlerkatalog.py`) kennt diese Meldungen nicht; `ide/database/panel.py` bildet den Hilfsnamen aus dem Dateinamen, auch mit `sqlite_`.

**Zu tun:** Die Meldungen deutsch fassen, beim Import einen Namen mit `sqlite_` umbenennen. Erledigt, wenn jede genannte Meldung deutsch erscheint und der Import von `sqlite_daten.csv` gelingt.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
