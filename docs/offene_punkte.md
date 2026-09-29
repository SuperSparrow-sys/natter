# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **441**.

## Ein neuer Punkt

```markdown
## 441. Kurz, was nicht stimmt

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

## 429. F5 startet das Programm ein zweites Mal, wenn es schon mit Strg+F5 läuft

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Fehlertoleranz), Entwicklungsbaum auf Commit `1b08eac`, offscreen mit dem Hauptfenster geprüft.

**Beobachtet:** Neues GUI-Projekt, mit „Starten ohne Debugger“ (Strg+F5) gestartet. Nachdem das Programm geladen hatte, „Starten“ (F5) gewählt. Die Statusleiste meldet „Z1 gestartet (mit Debugger)“, der erste Prozess läuft weiter, und es gibt eine Debugger-Sitzung dazu: zwei Fenster desselben Programms. Umgekehrt ebenso: „Starten ohne Debugger“ lehnt einen zweiten Start nur ab, wenn schon ein Programm über Strg+F5 läuft, nicht bei einer laufenden Debugger-Sitzung. Im Unterricht wechseln Schülerinnen zwischen F5 und Strg+F5, ohne den Unterschied zu kennen; liegt das erste Programmfenster hinter Natter, arbeiten sie danach im falschen Fenster weiter oder schreiben zweimal in dieselbe Datenbank. Zweimal dieselbe Taste zu drücken wird dagegen abgefangen („… läuft bereits - zuerst über „Start → Stopp“ beenden.“).

**Ursache:** nachgewiesen. `_mit_debugger_starten` in `ide/shell/hauptfenster.py` prüft nur `self.debug_sitzung`, `_projekt_starten_aktion` nur `self.laufender_prozess`. Keiner der beiden Wege sieht nach, ob über den anderen schon ein Programm läuft. Der Docstring von `_projekt_starten_aktion` verspricht „nur eine laufende Instanz pro Projekt“.

**Zu tun:** Beide Startwege lehnen einen Start ab, solange über den jeweils anderen ein Programm läuft, mit derselben Meldung wie beim zweiten Druck auf dieselbe Taste. Erledigt, wenn ein Test Strg+F5 und danach F5 auslöst (und umgekehrt) und danach nur ein Programm läuft.

## 430. Ein leeres Feld im Datenbank-Panel verbindet still mit einer Datenbank, die nur im Arbeitsspeicher liegt

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Aufgabe „Datenbanktabelle anlegen und im Formular anzeigen“), Entwicklungsbaum auf Commit `1b08eac`, `DatenbankPanel` offscreen geprüft.

**Beobachtet:** Im Datenbank-Panel ohne Eintrag im Feld „Datenbankdatei oder :memory:“ auf „Verbinden“ geklickt. Das Panel zeigt „Verbunden“. `CREATE TABLE schueler (…)` läuft durch, die Tabelle erscheint im Baum. Nach „Trennen“ und erneutem „Verbinden“ ist sie weg, und im Projektordner liegt keine Datei. Auch ein Formular mit `SQLite3Connection` sieht die Tabelle nie. Eine Schülerin, die zum ersten Mal eine Tabelle anlegt, hat keinen Anhaltspunkt, dass sie in einer Datenbank ohne Datei gearbeitet hat; die Arbeit der Stunde ist beim Trennen oder Schließen von Natter ohne Nachfrage verloren. Der Platzhalter „:memory:“ erklärt das nicht, er ist ein Fachbegriff von SQLite.

**Ursache:** nachgewiesen. `DatenbankPanel._verbinden` in `ide/database/panel.py` setzt ein leeres Feld mit `or ":memory:"` gleich einer Datenbank im Arbeitsspeicher und meldet danach dasselbe „Verbunden“ wie bei einer Datei. `trennen()` fragt bei einer solchen Datenbank nicht nach.

**Zu tun:** Ein leeres Feld verbindet nicht, sondern bittet darum, eine Datei zu wählen oder einen Namen einzutragen, und schlägt eine Datei im Projektordner vor. Wer ausdrücklich `:memory:` einträgt, sieht in der Statuszeile, dass die Daten beim Trennen verloren gehen. Erledigt, wenn ein Klick auf „Verbinden“ bei leerem Feld keine Verbindung herstellt und ein Test das belegt.

## 431. Vergessenes `self.` vor einem Komponentennamen: die Meldung nennt die naheliegende Ursache nicht

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Aufgabe „Fehler absichtlich einbauen“), Entwicklungsbaum auf Commit `1b08eac`, Prüfung vor dem Start und Fehlerkatalog an einer Kopie eines neuen GUI-Projekts geprüft.

**Beobachtet:** Formular mit den Komponenten `button`, `edit` und `label`. In der Ereignismethode steht `edit.text = 'x'` statt `self.edit.text = 'x'`, der häufigste Fehler in den ersten Fensterprogrammen. Die Prüfung vor dem Start verhindert den Start mit „u_main.py, Zeile 6: Der Name edit ist an dieser Stelle nicht bekannt. Ist er richtig geschrieben? Wurde er vorher zugewiesen oder importiert?“. Die Schreibweise stimmt aber, zugewiesen oder importiert wird eine Komponente nie. Läuft das Programm ohne Natter, heißt es im Fehlerkatalog „Ist die Schreibweise korrekt? Wurde die Variable vorher zugewiesen? Ist die Unit eingebunden?“. Beide Leitfragen führen weg von der Ursache. Beim Tippfehler im Komponentennamen (`self.lable`) fragt der Katalog dagegen gezielt nach der Komponente auf dem Formular.

**Ursache:** nachgewiesen. Die Vorlage zu F821 in `ide/run/pruefung.py` und `_name_error` in `pcl/fehlerkatalog.py` haben je eine feste Leitfrage und schauen nicht nach, ob der unbekannte Name eine Komponente des Formulars der Unit ist.

**Zu tun:** Ist der unbekannte Name eine Komponente im Formular dieser Unit (oder ein Attribut der Klasse), lautet die Leitfrage sinngemäß „Auf dem Formular gibt es eine Komponente edit. Fehlt davor self.?“, als Frage und ohne den fertigen Code, wie es `docs/fehlerkatalog.yaml` verlangt. Erledigt, wenn ein Test für `edit.text` in einer Ereignismethode diese Leitfrage in der Prüfung vor dem Start und im Fehlerkatalog findet.

## 432. Neues Projekt mit einem schon vorhandenen Namen: der Dialog ist zu, die Meldung steht nur in der Statusleiste

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (erster Kontakt, „Neues Projekt …“), Entwicklungsbaum auf Commit `1b08eac`, offscreen mit dem Hauptfenster geprüft.

**Beobachtet:** Zweimal hintereinander „Projekt → Neues Projekt …“ mit dem Namen „Ampel“ im vorgegebenen Ordner. Beim zweiten Mal schließt sich der Dialog, es entsteht kein Projekt, und in der Statusleiste steht: „Projekt konnte nicht angelegt werden: C:\Users\…\Ampel ist nicht leer.. Einen anderen Namen oder einen Ordner wählen, in dem Schreibrechte bestehen.“ Der Satz hat zwei Punkte hintereinander, nennt den ganzen Pfad statt des Namens und rät zu einem Ordner mit Schreibrechten, obwohl es nur um den Namen geht. Vorlage, Name und Ordner müssen danach noch einmal eingegeben werden. Im Unterricht kommt das oft vor: Aufgabennamen wie „Aufgabe1“ wiederholen sich, und wer in der nächsten Stunde das Projekt neu anlegt statt es zu öffnen, landet hier. Einen leeren oder ungültigen Namen meldet der Dialog dagegen in sich selbst, rot unter dem Feld.

**Ursache:** nachgewiesen. `NeuesProjektDialog.accept` in `ide/project/neu_dialog.py` prüft Name und Ordner, aber nicht, ob `ordner/name` schon besteht und nicht leer ist. Das stellt erst `projekt_erzeugen` in `ide/project/neu.py` fest (`FileExistsError(f"{zielordner} ist nicht leer.")`), nachdem der Dialog zu ist. `_neues_projekt_dialog` in `ide/shell/hauptfenster.py` hängt an diesen Text ohne Prüfung einen Punkt und den Rat zu den Schreibrechten an.

**Zu tun:** Der Dialog prüft vor dem Schließen, ob es den Projektordner schon gibt, und zeigt den Hinweis wie bei einem ungültigen Namen im Dialog, etwa „Ein Projekt „Ampel“ gibt es in diesem Ordner schon. Einen anderen Namen wählen oder das vorhandene über „Projekt öffnen …“ laden.“ Erledigt, wenn ein Test den Dialog bei vorhandenem Ordner offen findet und den Hinweis darin liest.

## 433. Natter schließen beendet ein laufendes Programm ohne Nachfrage

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Fehlertoleranz, falsches Fenster geschlossen), Entwicklungsbaum auf Commit `1b08eac`, offscreen mit dem Hauptfenster geprüft.

**Beobachtet:** GUI-Projekt mit Strg+F5 gestartet, alle Dateien gespeichert, dann das Hauptfenster von Natter geschlossen. Es kommt keine Nachfrage, das Programm wird sofort mit beendet. Wer das Kreuz des falschen Fensters erwischt, etwa weil Natter und das Programm übereinander liegen, verliert damit auch, was im Programm gerade eingegeben war, und muss Natter neu starten und das Projekt wieder öffnen. Nachgefragt wird nur bei ungespeicherten Dateien und bei einer offenen Transaktion im Datenbank-Panel.

**Ursache:** nachgewiesen. `HauptFenster.closeEvent` in `ide/shell/hauptfenster.py` fragt über `_vor_dem_schliessen_klaeren` nur nach `_ungespeicherte_namen()` und der Transaktion; `_beim_beenden_aufraeumen` beendet laufende Programme danach ohne weiteres.

**Zu tun:** Läuft beim Schließen ein Programm oder eine Debugger-Sitzung, fragt Natter nach („Das Programm „…“ läuft noch und wird mit Natter beendet.“ mit „Beenden“ und „Abbrechen“). Beim Abmelden von Windows bleibt es beim Beenden ohne Frage. Erledigt, wenn ein Test beim Schließen mit laufendem Programm die Nachfrage findet und nach „Abbrechen“ beides weiterläuft.

## 434. Nach jeder Änderung im Designer steht „Design-Prüfung: 0 Funde. Jeder Eintrag unten …“ in der Statusleiste

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Verständlichkeit), Entwicklungsbaum auf Commit `1b08eac`, offscreen mit dem Hauptfenster geprüft.

**Beobachtet:** Neues GUI-Projekt, Knopf platziert und umbenannt. Die Statusleiste zeigt danach „Design-Prüfung: 0 Funde. Jeder Eintrag unten im Panel „Meldungen“ sagt, was sich ändern lässt; ein Klick markiert die Komponente.“ Bei null Funden verweist der Satz auf Einträge, die es nicht gibt. Weil die automatische Design-Prüfung von Anfang an eingeschaltet ist, erscheint er nach jedem Platzieren, Verschieben, Umbenennen und Rückgängigmachen und ersetzt dabei, was vorher in der Statusleiste stand.

**Ursache:** nachgewiesen. `_design_pruefen` in `ide/shell/hauptfenster.py` setzt die Statuszeile ohne Unterscheidung nach der Zahl der Befunde und auch dann, wenn die Prüfung automatisch lief.

**Zu tun:** Ohne Befunde schreibt die automatische Prüfung nichts in die Statuszeile; die von Hand ausgelöste meldet „Design-Prüfung: keine Funde.“ Der Satz über die Einträge steht nur, wenn es welche gibt. Erledigt, wenn ein Test nach dem Platzieren eines Knopfs ohne Befund die Statuszeile unverändert findet.

## 435. Die Leitfrage zu einem Einrückungsfehler verweist auf „begin/end“

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Verständlichkeit), Entwicklungsbaum auf Commit `1b08eac`, Konsolen-Hülle aus `ide/run/starter.py` mit einer Probe geprüft.

**Beobachtet:** Ein Konsolenprogramm mit `if x == 1:` und nicht eingerückter Zeile darunter endet, wenn es ohne die Prüfung vor dem Start läuft (etwa mit `python main.py`), mit „Zu prüfen: Ist die Zeile darunter eingerückt? Python nutzt die Einrückung anstelle von begin/end.“ Für eine Schülerin, die mit Python anfängt, bedeutet „begin/end“ nichts; es verweist auf eine andere Programmiersprache, auf die Natter sich nicht beziehen soll.

**Ursache:** nachgewiesen. Zwei Leitfragen in `pcl/fehlerkatalog.py` (die Einträge zu `IndentationError`, Zeilen 529 und 559) enthalten den Satz.

**Zu tun:** Den Satzteil durch eine Erklärung aus Python heraus ersetzen, etwa „Was zu einem if, for, while oder def gehört, steht darunter weiter eingerückt.“ Erledigt, wenn „begin/end“ in keiner sichtbaren Meldung mehr vorkommt.

## 436. Beispiel 03 leitet zum Ziehen aus der Palette an, das es nicht gibt

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Hilfe), Entwicklungsstand `1b08eac` (0.4.2).

**Beobachtet:** Der Kopfkommentar in `beispielprojekte/03_Taschenrechner/u_main.py`, dem ersten Programm mit Formular, beschreibt in den Zeilen 8 bis 11, wie eine neue Schaltfläche entsteht: „1. Doppelklick auf u_main.pfm öffnet den Designer. 2. Button aus der Palette aufs Formular ziehen. 3. Doppelklick auf den Button“. Beide ersten Schritte passen nicht zur Oberfläche. Im Projekt-Explorer steht unter „Formulare“ nur „u_main“, eine Datei `u_main.pfm` ist dort nicht zu sehen. Ziehen aus der Palette gibt es nicht: Probe offscreen mit der Komponentenpalette, `dragEnabled()` der Kachelliste ist `False`, und der Designer nimmt beim Ablegen nur Bilddateien an (`_bildpfade_aus_mime` liefert für die Daten einer Kachel eine leere Liste). Wer dem Kommentar folgt, zieht die Kachel aufs Formular, und beim Loslassen entsteht keine Komponente. `docs/handbuch.md`, Zeile 344, sagt ausdrücklich „Ziehen aus der Palette gibt es nicht“, `docs/erste_schritte.md` beschreibt Anklicken und dann ins Formular klicken. Punkt 181 hat denselben Widerspruch im Handbuch behoben; im Beispiel ist er stehen geblieben.

**Ursache:** nachgewiesen: Kommentar in `beispielprojekte/03_Taschenrechner/u_main.py`, Zeilen 9 und 10; `ide/palette/palette.py`, `_liste_erzeugen` (kein Ziehen), `ide/designer/canvas.py`, `eventFilter` (Ablegen nur für Bilder).

**Zu tun:** Den Kommentar an die Bedienung angleichen: Doppelklick auf „u_main“ unter „Formulare“, Kachel anklicken und dann ins Formular klicken. Erledigt, wenn ein Test die Anleitungen in den Kommentaren der Beispielprojekte gegen die Bedienung hält, wie es `tests/test_hilfeseiten_abgleich.py` für das Handbuch tut, und das Wort „ziehen“ für die Palette dort nicht mehr vorkommt.

## 437. Bei 125 % und 150 % zeigt der Objektinspektor auf kleinen Bildschirmen kaum eine Eigenschaft

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Darstellung), Entwicklungsstand `1b08eac` (0.4.2).

**Beobachtet:** Probe offscreen mit einem Bildschirm in logischen Pixeln, abzüglich Taskleiste und Titelleiste, frischen Einstellungen und `fensterlage_herstellen()` wie beim Start (maximiert). Geöffnet ist eine Kopie von Beispiel 03, das Formular im Designer. Gemessen wurden die Sichtfläche der Eigenschaftentabelle, des Komponentenbaums und der Mitte:

| Bildschirm | Eigenschaften | Komponentenbaum | Designer |
|---|---|---|---|
| 1366 × 768, 100 % | 244 × 162 (5 Zeilen) | 246 × 123 | 816 × 423 |
| 1366 × 768, 125 % | 244 × 66 (2 Zeilen) | 246 × 76 | 543 × 280 |
| 1280 × 800, 125 % | 244 × 84 (2 Zeilen) | 246 × 84 | 474 × 306 |
| 1280 × 800, 150 % | 244 × 6 (keine Zeile) | 246 × 60 | 303 × 204 |

Bei 1280 × 800 und 150 % steht unter „Eigenschaft | Wert“ keine einzige Zeile; `caption`, `name` oder `text` lassen sich erst ändern, nachdem Docks von Hand verkleinert oder geschlossen wurden. Bei 125 % sind es zwei Zeilen, jede weitere Eigenschaft braucht die Bildlaufleiste, und vom Taschenrechner-Formular (340 Pixel hoch) ist die Zeile „Ergebnis“ im Designer abgeschnitten. Die Komponentenpalette belegt dabei in jeder Größe einen Streifen von 89 Pixeln über die volle Fensterbreite für eine einzige Reihe von 14 Kacheln, und der Objektinspektor teilt seine Höhe im Verhältnis 1 : 2 zwischen Komponentenbaum und Reitern auf. Punkt 348 hat das nur für Konsolenprojekte gelöst, wo beide Docks ausgeblendet werden; in einem Formularprojekt braucht es beide.

**Ursache:** nachgewiesen für die Aufteilung: `ide/palette/palette.py`, Zeile 232 (feste Höhe der Kachelliste), `ide/shell/hauptfenster.py`, Zeile 1286 (`resizeDocks` auf 88 Pixel für die Palette), `ide/inspector/objektinspektor.py`, Zeilen 91 und 92 (Streckfaktoren 1 und 2 für Baum und Reiter). Eine Anpassung an wenig Höhe gibt es nicht.

**Zu tun:** Bei wenig Höhe den Platz zugunsten der Eigenschaftentabelle verteilen, etwa den Komponentenbaum im Objektinspektor einklappbar oder deutlich niedriger machen und die Palette nicht über die volle Breite legen. Erledigt, wenn ein Test bei 853 × 470 logischen Pixeln (1280 × 800 bei 150 %) mit geöffnetem Formular mindestens fünf Zeilen der Eigenschaftentabelle sichtbar findet.

## 438. Hilfeseiten lassen sich nicht durchsuchen, und F1 ist nicht belegt

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Hilfe, Auffindbarkeit), Entwicklungsstand `1b08eac` (0.4.2).

**Beobachtet:** Probe offscreen mit geöffnetem Beispiel 03. „Hilfe → Komponenten-Referenz“ öffnet eine Seite, die 32 031 Pixel hoch ist; sichtbar sind bei 1280 × 720 davon 368, also rund 87 Bildschirmseiten. Die Seite hat kein Inhaltsverzeichnis und keinen einzigen Verweis (`<a href` kommt im erzeugten HTML nicht vor), ebenso wenig `docs/handbuch.md` mit 37 Abschnitten. Wer wissen will, was ein `Timer` kann, muss rollen. „Suchen → Suchen …“ (Strg+F) im Reiter der Referenz meldet in der Statuszeile „Kein Quelltext-Reiter vorn. Zuerst links im Projekt-Explorer eine Quelltextdatei doppelklicken.“ Die Meldung schickt in den Projekt-Explorer, obwohl in der Hilfe gesucht werden sollte. Die Taste F1, unter Windows die übliche Hilfetaste, ist keiner Aktion und keinem `QShortcut` zugeordnet: weder mit einer markierten Komponente im Designer noch im Objektinspektor oder im Editor öffnet sie etwas.

**Ursache:** nachgewiesen: `HauptFenster._suchen_aktion` (`ide/shell/hauptfenster.py`, ab Zeile 5474) arbeitet nur mit `_aktueller_editor()`, und der liefert nur `QPlainTextEdit` (Zeile 5415), nicht die `HilfeAnsicht`. Im Aktionsregister hat keine Aktion das Kürzel F1.

**Zu tun:** Strg+F auch in Hilfeseiten suchen lassen (die `HilfeAnsicht` ist ein `QTextBrowser` und kann `find`), den langen Seiten ein Inhaltsverzeichnis mit Sprungzielen geben und F1 belegen, am besten mit der Referenz an der Stelle der gewählten Komponente. Erledigt, wenn Strg+F in der Referenz „Timer“ findet und F1 bei markiertem Button die Referenz beim Abschnitt „Button“ öffnet.

## 439. Die Menüs lassen sich nicht mit Alt und Buchstabe öffnen

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Einheitlichkeit), Entwicklungsstand `1b08eac` (0.4.2).

**Beobachtet:** Keiner der elf Menütitel des Hauptfensters hat eine Zugriffstaste; die Titel lauten „Datei“, „Bearbeiten“ … ohne `&`, und im Menü ist kein Buchstabe unterstrichen. Probe offscreen: Editor mit `u_main.py` im Fokus, Alt+D gedrückt, danach ist kein Menü offen (`menuBar().activeAction()` ist `None`). Dasselbe gilt für den Diagramm-Editor. Unter Windows öffnet Alt+D in fast jedem Programm das Menü „Datei“; eine Lehrkraft, die vorne mit der Tastatur arbeitet, kommt so nur über Alt allein und die Pfeiltasten in die Menüs. Die Knöpfe in einigen Dialogen haben Zugriffstasten („&Kopieren“, „&Speichern unter …“ in `ide/diagramm/codefenster.py`), die Menüs nicht.

**Ursache:** nachgewiesen: `ide/shell/hauptfenster.py`, Zeile 934, `self.menuBar().addMenu(titel)` mit Titeln ohne `&`; ebenso `ide/diagramm/fenster.py`, Zeile 667.

**Zu tun:** Den Menütiteln Zugriffstasten geben, ohne Doppelungen innerhalb einer Menüleiste (etwa „&Datei“, „&Bearbeiten“, „&Suchen“, „&Ansicht“, „&Quelltext“, „&Projekt“, „S&tart“, „Pa&kete“, „&Werkzeuge“, „&Fenster“, „&Hilfe“). Erledigt, wenn ein Test Alt+D im Hauptfenster das Menü „Datei“ öffnen sieht und für jede Menüleiste eindeutige Zugriffstasten findet.

## 440. Das Kontextmenü im Editor sagt „Wiederherstellen“, das Menü „Wiederholen“

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Einheitlichkeit), Entwicklungsstand `1b08eac` (0.4.2).

**Beobachtet:** Probe offscreen, `QuelltextEditor.kontextmenue()` mit geladener deutscher Qt-Übersetzung. Die rechte Maustaste im Editor zeigt „Rückgängig Strg+Z“ und „Wiederherstellen Strg+Y“. Dieselbe Aktion heißt im Menü „Bearbeiten“, in der Werkzeugleiste, in der Tastenkürzel-Übersicht und im Diagramm-Editor „Wiederholen“. Die Rechtsklickmenüs der Eingabefelder (Suchen, Objektinspektor) zeigen ebenfalls „Wiederherstellen“. Im selben Kontextmenü steht „Zeile nach oben Alt+Pfeil oben“, die Tastenkürzel-Übersicht schreibt dieselbe Taste „Alt+Pfeil hoch/runter“, und „Zeile duplizieren“ heißt dort „Zeile darunter noch einmal einfügen“. Einschätzung: Wer im Menü „Wiederholen“ gelernt hat, erkennt „Wiederherstellen“ nicht sicher als denselben Befehl.

**Ursache:** nachgewiesen: `QuelltextEditor.kontextmenue` (`ide/shell/quelltexteditor.py`, Zeile 1505) baut auf `createStandardContextMenu()`, dessen Beschriftungen aus Qts eigener Übersetzung kommen; die eigenen Einträge darunter (Zeilen 1510 bis 1514) und `EDITORTASTEN` in `ide/shell/tastenkuerzel.py` sind unabhängig voneinander geschrieben.

**Zu tun:** Im Kontextmenü des Editors „Wiederherstellen“ in „Wiederholen“ umbenennen und die Beschriftungen der Editortasten in Kontextmenü und Übersicht aus einer Quelle nehmen. Erledigt, wenn ein Test im Kontextmenü des Editors „Wiederholen“ findet und jede Taste dort so geschrieben ist wie in der Tastenkürzel-Übersicht.

---

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
