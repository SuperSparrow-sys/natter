# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **411**.

## Ein neuer Punkt

```markdown
## 411. Kurz, was nicht stimmt

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

## 407. Der erste Start nach der Installation dauert 92 Sekunden

**Gemeldet:** 29. September 2026, Prüfung der installierten Fassung 0.4.0 (`build\auswertung\040\`).

**Beobachtet:** Vom Start von `Natter.exe` bis zum bedienbaren Hauptfenster vergingen beim ersten Mal nach dem Update 91,9 s; das Ladebild „Natter startet …“ stand ab 2,1 s. Der zweite Start brauchte 1,55 s. Bei 0.3.6 dauerte der erste Start 22,7 s (Punkt 48). Der erste Start des ObstSortierers dauerte 62,9 s, der zweite 4,0 s. In die Installation wurde keine `.pyc` geschrieben.

**Ursache:** nicht geklärt. Möglich sind die Prüfung frischer Dateien durch den Virenscanner (mit `starter\` sind 53 Dateien mehr dabei) oder Last durch eine zweite Sitzung, die während der Messung Fenster auf demselben Bildschirm öffnete.

**Zu tun:** Ursache messen (Prozessmonitor bzw. Zeitstempel je Import beim ersten Start, Vergleich mit einer frisch kopierten 0.3.6, ohne fremde Last). Liegt es an Natter, beheben; liegt es am Virenscanner, im Handbuch unter „Der erste Start dauert länger“ die gemessene Zeit nennen. Erledigt, wenn der erste Start ohne fremde Last gemessen und erklärt ist und nicht länger dauert als bei 0.3.6.

---

## 408. „Projekt öffnen …“ beginnt im Programmordner von Natter

**Gemeldet:** 29. September 2026, Prüfung der installierten Fassung 0.4.0 (Bild `09_dialog_projekt_oeffnen.png`).

**Beobachtet:** Der Dialog zeigt `…\AppData\Local\Programs\Natter` mit `Lizenzen`, `python` und `starter`. Eine Schülerin sucht ihre Projekte dort vergeblich und sieht Ordner, die sie nichts angehen.

**Ursache:** Der Startmenü-Eintrag setzt den Programmordner als Arbeitsordner, und `QFileDialog.getOpenFileName` wird in `_projekt_oeffnen_dialog` und `_datei_oeffnen_dialog` (`ide/shell/hauptfenster.py`) ohne Startordner aufgerufen.

**Zu tun:** Als Startordner den Ordner des offenen Projekts, sonst den zuletzt benutzten, sonst `Dokumente\Natter` nehmen. Erledigt, wenn ein Test den Startordner des Dialogs prüft.

---

## 409. Die Vorschlagsliste geht mitten in einem Kommentar auf

**Gemeldet:** 29. September 2026, Prüfung der installierten Fassung 0.4.0 (Bild `08_unit_geaendert_ungespeichert.png`).

**Beobachtet:** Beim Tippen der Kommentarzeile `# Sicherungsprobe 040 - bitte verwerfen` erschien die Vervollständigung mit `sorted(…)`, `abs(…)` usw. und fing die Eingabe ab.

**Ursache:** vermutet: Der Anstoß der Vervollständigung im Nebenfaden (Punkt 313) prüft nicht, ob der Cursor in einem Kommentar oder einer Zeichenkette steht.

**Zu tun:** In Kommentaren und Zeichenketten keine Vorschlagsliste von selbst öffnen (Strg+Leertaste darf weiter). Erledigt, wenn ein Test das Tippen in einem Kommentar und in einer Zeichenkette ohne Liste zeigt.

---

## 410. Doppelklick im Projekt-Explorer öffnet eine Unit nicht zuverlässig

**Gemeldet:** 29. September 2026, Prüfung der installierten Fassung 0.4.0, nicht sicher belegt.

**Beobachtet:** In drei Sitzungen blieben 12 Doppelklicks per UI Automation auf `u_main.py` bzw. `u_info.py` ohne Wirkung, einer um 09:09 öffnete die Unit; die Eingabetaste öffnete immer. Auf dem Bildschirm lagen dabei fremde Fenster einer anderen Sitzung, eine Störung der Automatisierung ist nicht ausgeschlossen. Dazu zwei Kleinigkeiten: Während der Ladeanzeige steht links schon „… gestartet (mit Debugger)“, und die Frage „Ungespeicherte Änderungen gefunden“ erscheint vor dem Hauptfenster allein auf dem Bildschirm.

**Zu tun:** Doppelklick im Explorer offscreen mit echten Mausereignissen (`QTest.mouseDClick`) und an der installierten Fassung von Hand nachprüfen; ist er belegt, beheben. Die Frage zur Sicherung erst zeigen, wenn das Hauptfenster steht. Erledigt, wenn der Doppelklick in einem Test eine Unit öffnet und die Frage ein Elternfenster hat.

---

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

## 46. Der Signaturtest läuft im CI nicht, und ein Debugger-Test wackelt dort ~~(zurückgestellt)~~

**Gemeldet:** 26. September 2026, GitHub-Actions-Läufe zu `250930c`
bis `18432cd`.

**Beobachtet:**

- `test_schritt_10_meldet_eine_signierte_vorlage` in
  `tests/test_auslieferung_bauen.py` braucht eine Datei, deren Kopie
  `Get-AuthenticodeSignature` als `Valid` meldet. Auf dem Runner
  (Windows Server) gilt keine der Kandidaten als gültig signiert,
  weder `notepad.exe` noch `pwsh.exe` noch `git.exe`. Der Test wird
  dort übersprungen („keine Datei mit eingebetteter Signatur
  gefunden“); lokal läuft er und ist grün. Die Prüfung von Schritt 10
  auf signierte Vorlagen wird damit im CI nicht getestet.
- `test_ein_durchgang_mit_zwei_haltepunkten` in
  `tests/test_hauptfenster_debugger.py` lief in Lauf 18432cd in die
  Zeitgrenze von 45 Sekunden, bevor debugpy am Haltepunkt hielt. Der
  Code war derselbe wie im grünen Lauf davor; die Wiederholung des
  Jobs war grün.

**Ursache:** für den ersten Teil vermutlich die Zertifikatsprüfung auf
dem Runner (Katalogsignaturen, Sperrlisten ohne Netz), nicht
nachgewiesen. Für den zweiten noch offen; ein langsamer Runner liegt
nahe.

**Nachtrag 27. September 2026:** Im Lauf zu `4054bbf` (26.09.,
Nr. 36239269490) lief ein anderer Debugger-Test in dieselbe Grenze:
`test_breakpoint_in_ereignis_handler_haelt_an_und_zeigt_self` in
`tests/test_m4_abnahme.py`, 45 s ohne Halt. Beim Aufräumen des Jobs
beendete der Runner zwei noch laufende `python`-Prozesse; das
Schülerprogramm war also gestartet, hielt aber nicht am Haltepunkt.
Der Signaturtest nennt beim Überspringen jetzt für jeden Kandidaten
Status und Meldung von `Get-AuthenticodeSignature`, und die
Kandidatenliste ist um `dotnet.exe`, `msedge.exe`, `chrome.exe` und
die Python aus `C:\hostedtoolcache` erweitert. Der nächste CI-Lauf
zeigt damit, warum der Runner keine der Dateien als gültig
anerkennt.

**Befund aus dem Lauf zu `fd1f1cf` (27.09., Nr. 36317070410, grün):**
Für alle zwölf Kandidaten gab `Get-AuthenticodeSignature` weder
Status noch Meldung aus (`notepad.exe: |`, `msedge.exe: |`, …). Damit
liegt es nicht an den Dateien: der Aufruf selbst liefert auf dem
Runner nichts. Vermutet, nicht nachgewiesen: `powershell.exe` erbt
dort `PSModulePath` aus PowerShell 7 und lädt ein unpassendes Modul
`Microsoft.PowerShell.Security`. Nächster Schritt: bei leerer Ausgabe
auch `stderr` ins Protokoll schreiben und den Aufruf mit bereinigtem
`PSModulePath` wiederholen.

**Umgesetzt (27. September 2026):** `powershell_umgebung()` in `tools/auslieferung_bauen.py` startet `powershell.exe` ohne `PSModulePath`, im Bau (Schritt 10 und Signaturprüfung) wie im Test; der Test schreibt bei einem Fehlschlag auch die Fehlerausgabe in die Begründung. Nachweis steht aus: der nächste CI-Lauf muss den Signaturtest ausführen statt ihn zu überspringen. Lokal nicht nachstellbar, weil PowerShell 7 hier nicht installiert ist.

**Nachgewiesen für den Signaturtest (27. September 2026):** CI-Lauf 36351997791 zu `8dc76cd`: 4672 bestanden, kein Test übersprungen; der Signaturtest lief also auf dem Runner. Die Ursache war der geerbte `PSModulePath`. Offen bleibt nur der zweite Teil: der Debugger-Test muss in zehn Läufen hintereinander grün sein.

**Zu tun:** Für den Signaturtest eine Datei finden, die auch auf dem
Runner `Valid` ist, ohne dafür ein Zertifikat in einen Windows-Speicher
einzutragen. Beim Debugger-Test beobachten, ob er wieder ausfällt;
wenn ja, die Startzeit von debugpy auf dem Runner messen. Erledigt,
wenn der Signaturtest im CI läuft und der Debugger-Test in zehn
Läufen hintereinander grün ist.

**Nachtrag:** 28. September 2026, `tests/test_debugger_schritt_vor_dem_start.py` (Punkt 295) blieb im CI-Job „Prozesse, Debugger, Rundlauf“ einmal nach 45 s ohne Halt stehen; der erneute Lauf desselben Stands war grün, lokal ist er durchgehend grün. Gleiche Art wie oben.

**Zurückgestellt:** 28. September 2026 auf Wunsch des Nutzers. Der Nachweis braucht zehn grüne CI-Läufe hintereinander und hält die Fassung 0.4.0 nicht auf.

---

## 7. Der Starter braucht die Hälfte der Startzeit ~~(zurückgestellt)~~

**Beobachtet:** Vom Doppelklick bis zum Fenster vergehen rund 1,65
Sekunden. Davon entfallen etwa 790 Millisekunden auf `Natter.exe`,
bevor überhaupt Python anläuft — der Starter entpackt sich und fährt
dann eine zweite Python hoch.

**Entschieden:** Der Starter bleibt, wie er ist. `Natter.exe` behält
sein eigenes Symbol, seine Versionsangabe und seine Signatur; die
Zeit wird dafür in Kauf genommen.

Hier nur festgehalten, damit die Frage nicht in einem halben Jahr noch
einmal von vorn aufgemacht wird. Gemessene Alternativen waren:
`--onedir` statt `--onefile` (spart 200 ms, kostet 15,8 MB und einen
Ordner neben der Exe) und die Verknüpfung direkt auf `pythonw.exe`
(spart 790 ms, kostet das eigene signierte `Natter.exe`).
