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

## 459. Beispiel 03 leitet zum Ziehen aus der Palette an, das es nicht gibt

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Hilfe), Entwicklungsstand `1b08eac` (0.4.2).

**Beobachtet:** Der Kopfkommentar in `beispielprojekte/03_Taschenrechner/u_main.py`, dem ersten Programm mit Formular, beschreibt in den Zeilen 8 bis 11, wie eine neue Schaltfläche entsteht: „1. Doppelklick auf u_main.pfm öffnet den Designer. 2. Button aus der Palette aufs Formular ziehen. 3. Doppelklick auf den Button“. Beide ersten Schritte passen nicht zur Oberfläche. Im Projekt-Explorer steht unter „Formulare“ nur „u_main“, eine Datei `u_main.pfm` ist dort nicht zu sehen. Ziehen aus der Palette gibt es nicht: Probe offscreen mit der Komponentenpalette, `dragEnabled()` der Kachelliste ist `False`, und der Designer nimmt beim Ablegen nur Bilddateien an (`_bildpfade_aus_mime` liefert für die Daten einer Kachel eine leere Liste). Wer dem Kommentar folgt, zieht die Kachel aufs Formular, und beim Loslassen entsteht keine Komponente. `docs/handbuch.md`, Zeile 344, sagt ausdrücklich „Ziehen aus der Palette gibt es nicht“, `docs/erste_schritte.md` beschreibt Anklicken und dann ins Formular klicken. Punkt 181 hat denselben Widerspruch im Handbuch behoben; im Beispiel ist er stehen geblieben.

**Ursache:** nachgewiesen: Kommentar in `beispielprojekte/03_Taschenrechner/u_main.py`, Zeilen 9 und 10; `ide/palette/palette.py`, `_liste_erzeugen` (kein Ziehen), `ide/designer/canvas.py`, `eventFilter` (Ablegen nur für Bilder).

**Zu tun:** Den Kommentar an die Bedienung angleichen: Doppelklick auf „u_main“ unter „Formulare“, Kachel anklicken und dann ins Formular klicken. Erledigt, wenn ein Test die Anleitungen in den Kommentaren der Beispielprojekte gegen die Bedienung hält, wie es `tests/test_hilfeseiten_abgleich.py` für das Handbuch tut, und das Wort „ziehen“ für die Palette dort nicht mehr vorkommt.

## 460. Bei 125 % und 150 % zeigt der Objektinspektor auf kleinen Bildschirmen kaum eine Eigenschaft

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

## 461. Hilfeseiten lassen sich nicht durchsuchen, und F1 ist nicht belegt

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Hilfe, Auffindbarkeit), Entwicklungsstand `1b08eac` (0.4.2).

**Beobachtet:** Probe offscreen mit geöffnetem Beispiel 03. „Hilfe → Komponenten-Referenz“ öffnet eine Seite, die 32 031 Pixel hoch ist; sichtbar sind bei 1280 × 720 davon 368, also rund 87 Bildschirmseiten. Die Seite hat kein Inhaltsverzeichnis und keinen einzigen Verweis (`<a href` kommt im erzeugten HTML nicht vor), ebenso wenig `docs/handbuch.md` mit 37 Abschnitten. Wer wissen will, was ein `Timer` kann, muss rollen. „Suchen → Suchen …“ (Strg+F) im Reiter der Referenz meldet in der Statuszeile „Kein Quelltext-Reiter vorn. Zuerst links im Projekt-Explorer eine Quelltextdatei doppelklicken.“ Die Meldung schickt in den Projekt-Explorer, obwohl in der Hilfe gesucht werden sollte. Die Taste F1, unter Windows die übliche Hilfetaste, ist keiner Aktion und keinem `QShortcut` zugeordnet: weder mit einer markierten Komponente im Designer noch im Objektinspektor oder im Editor öffnet sie etwas.

**Ursache:** nachgewiesen: `HauptFenster._suchen_aktion` (`ide/shell/hauptfenster.py`, ab Zeile 5474) arbeitet nur mit `_aktueller_editor()`, und der liefert nur `QPlainTextEdit` (Zeile 5415), nicht die `HilfeAnsicht`. Im Aktionsregister hat keine Aktion das Kürzel F1.

**Zu tun:** Strg+F auch in Hilfeseiten suchen lassen (die `HilfeAnsicht` ist ein `QTextBrowser` und kann `find`), den langen Seiten ein Inhaltsverzeichnis mit Sprungzielen geben und F1 belegen, am besten mit der Referenz an der Stelle der gewählten Komponente. Erledigt, wenn Strg+F in der Referenz „Timer“ findet und F1 bei markiertem Button die Referenz beim Abschnitt „Button“ öffnet.

## 462. Die Menüs lassen sich nicht mit Alt und Buchstabe öffnen

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Einheitlichkeit), Entwicklungsstand `1b08eac` (0.4.2).

**Beobachtet:** Keiner der elf Menütitel des Hauptfensters hat eine Zugriffstaste; die Titel lauten „Datei“, „Bearbeiten“ … ohne `&`, und im Menü ist kein Buchstabe unterstrichen. Probe offscreen: Editor mit `u_main.py` im Fokus, Alt+D gedrückt, danach ist kein Menü offen (`menuBar().activeAction()` ist `None`). Dasselbe gilt für den Diagramm-Editor. Unter Windows öffnet Alt+D in fast jedem Programm das Menü „Datei“; eine Lehrkraft, die vorne mit der Tastatur arbeitet, kommt so nur über Alt allein und die Pfeiltasten in die Menüs. Die Knöpfe in einigen Dialogen haben Zugriffstasten („&Kopieren“, „&Speichern unter …“ in `ide/diagramm/codefenster.py`), die Menüs nicht.

**Ursache:** nachgewiesen: `ide/shell/hauptfenster.py`, Zeile 934, `self.menuBar().addMenu(titel)` mit Titeln ohne `&`; ebenso `ide/diagramm/fenster.py`, Zeile 667.

**Zu tun:** Den Menütiteln Zugriffstasten geben, ohne Doppelungen innerhalb einer Menüleiste (etwa „&Datei“, „&Bearbeiten“, „&Suchen“, „&Ansicht“, „&Quelltext“, „&Projekt“, „S&tart“, „Pa&kete“, „&Werkzeuge“, „&Fenster“, „&Hilfe“). Erledigt, wenn ein Test Alt+D im Hauptfenster das Menü „Datei“ öffnen sieht und für jede Menüleiste eindeutige Zugriffstasten findet.

## 463. Das Kontextmenü im Editor sagt „Wiederherstellen“, das Menü „Wiederholen“

**Gemeldet:** 29. September 2026, Benutzbarkeitsprüfung (Einheitlichkeit), Entwicklungsstand `1b08eac` (0.4.2).

**Beobachtet:** Probe offscreen, `QuelltextEditor.kontextmenue()` mit geladener deutscher Qt-Übersetzung. Die rechte Maustaste im Editor zeigt „Rückgängig Strg+Z“ und „Wiederherstellen Strg+Y“. Dieselbe Aktion heißt im Menü „Bearbeiten“, in der Werkzeugleiste, in der Tastenkürzel-Übersicht und im Diagramm-Editor „Wiederholen“. Die Rechtsklickmenüs der Eingabefelder (Suchen, Objektinspektor) zeigen ebenfalls „Wiederherstellen“. Im selben Kontextmenü steht „Zeile nach oben Alt+Pfeil oben“, die Tastenkürzel-Übersicht schreibt dieselbe Taste „Alt+Pfeil hoch/runter“, und „Zeile duplizieren“ heißt dort „Zeile darunter noch einmal einfügen“. Einschätzung: Wer im Menü „Wiederholen“ gelernt hat, erkennt „Wiederherstellen“ nicht sicher als denselben Befehl.

**Ursache:** nachgewiesen: `QuelltextEditor.kontextmenue` (`ide/shell/quelltexteditor.py`, Zeile 1505) baut auf `createStandardContextMenu()`, dessen Beschriftungen aus Qts eigener Übersetzung kommen; die eigenen Einträge darunter (Zeilen 1510 bis 1514) und `EDITORTASTEN` in `ide/shell/tastenkuerzel.py` sind unabhängig voneinander geschrieben.

**Zu tun:** Im Kontextmenü des Editors „Wiederherstellen“ in „Wiederholen“ umbenennen und die Beschriftungen der Editortasten in Kontextmenü und Übersicht aus einer Quelle nehmen. Erledigt, wenn ein Test im Kontextmenü des Editors „Wiederholen“ findet und jede Taste dort so geschrieben ist wie in der Tastenkürzel-Übersicht.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
