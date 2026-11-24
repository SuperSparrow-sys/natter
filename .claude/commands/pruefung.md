---
description: Drei spezialisierte Sessions prüfen Natter gleichzeitig auf Sicherheit, Funktionstüchtigkeit und Fehler; Befunde in docs/offene_punkte.md, nichts wird behoben
---

# Prüfung in drei Sessions: Sicherheit, Funktion, Fehler

Natter ist eine Python-Entwicklungsumgebung für den
Informatikunterricht: `ide/` (Editor, Designer, Inspektor, Debugger,
Diagramm-Editor, Projektverwaltung), `pcl/` (Komponenten der
Schülerprogramme, läuft ohne IDE), `tools/` (Starter, Bau),
`beispielprojekte/`, `schemas/`, `docs/`. Regeln stehen in `AGENTS.md`.

Ziel ist ein belastbares Urteil über drei Fragen, jede von einer
eigenen Session bearbeitet:

| Session | Frage | Kürzel |
|---|---|---|
| A | Lässt sich Natter missbrauchen oder aushebeln? | `sicherheit` |
| B | Funktionieren die Kernabläufe von Anfang bis Ende? | `funktion` |
| C | Welche Fehler zeigen sich, wenn man gezielt Eingaben erzeugt und zusieht, was bricht? | `fehler` |

Geprüft wird nur. Nichts wird behoben, nichts gebaut, nichts
installiert. Ergebnis sind neue Punkte in `docs/offene_punkte.md` und
ein kurzer Bericht. Beheben geht danach mit `/freigabe` oder „arbeite
die Liste ab“.

Diese Sitzung ist die Leitsession: sie bereitet vor, startet die drei
Sessions, führt die Ergebnisse zusammen und berichtet. Sie prüft
nicht selbst mit.

## 0. Vorbereitung (Leitsession)

1. `git status` muss sauber sein, sonst erst committen. `git pull
   --ff-only`, Commit-Hash als `<stand>` (7 Zeichen) merken.
2. In `docs/offene_punkte.md` die nächste freie Nummer `N` lesen.
   Nummernbereiche: A ab `N`, B ab `N+30`, C ab `N+60`.
3. `uv run python -m tools.wache --aufraeumen`, liegen gebliebene
   Ordner `%TEMP%\natter_*` löschen.
4. Ausgangslage messen, einmal für alle drei Sessions:
   `uv run pytest -m "not drucker and not prozess and not debugger and not rundlauf" -n 8 --dist loadfile -q -p no:cacheprovider`
   mit `timeout 1800`, Ausgabe nach
   `build/auswertung/pruefung_<stand>/ausgangslage.log`. Rote oder
   übersprungene Tests notieren; sie gehen als Ausgangslage an
   Session B.
5. Nachweisordner anlegen:
   `C:\Users\jonat\Documents\natter\build\auswertung\pruefung_<stand>\`
   mit Unterordnern `A`, `B`, `C`. `/build/` ist nicht eingecheckt.

## 1. Sessions starten

Alle drei gleichzeitig, jede `fresh`, mit eigenem Arbeitsbaum
(`use_worktree: true`). Ist das Starten von Sessions nicht verfügbar,
stattdessen drei Helfer mit `isolation: worktree`. Mehr als drei
laufen nie gleichzeitig.

Jeder Auftrag besteht aus den gemeinsamen Regeln (Abschnitt 2) und
dem Teil seiner Session (Abschnitt 3, 4 oder 5), dazu `<stand>`, sein
Nummernbereich und sein Nachweisordner. Session B bekommt zusätzlich
die Ausgangslage aus Schritt 0.4.

Während die Sessions laufen, alle 10 Minuten
`uv run python -m tools.wache --still 20` (Monitor mit Zeitgrenze).
Meldet sie einen verwaisten Prozess, der zu keiner laufenden Session
gehört, aufräumen. Hat eine Session 30 Minuten nichts gemeldet und
läuft bei ihr kein Test, nachfragen; hängt sie weiter, beenden, ihren
Arbeitsbaum sichten und den Auftrag einmal neu vergeben.

## 2. Gemeinsame Regeln (in jeden Auftrag)

Arbeitsweise:

- Zuerst `git merge --ff-only main`. Danach Stand `<stand>` prüfen.
- `docs/offene_punkte.md`, `docs/erledigte_punkte.md`,
  `docs/bericht.md` und `docs/auswertung/` erst am Ende lesen, beim
  Abgleich. Ausnahme ist Session C, Abschnitt 5.6.
- Jeder Befund wird belegt: Datei und Zeile, dazu ein Nachweis, der
  sich wiederholen lässt. Das ist ein kurzes Skript oder ein
  pytest-Test, abgelegt im Nachweisordner der Session als
  `<nummer>_<stichwort>.py`, mit einer Zeile Aufruf darüber. Was sich
  nicht belegen lässt, heißt „vermutet“ oder entfällt.
- Nur Befunde, die im Unterricht oder an einem Schulrechner spürbar
  sind. Stilfragen, Geschmack und Mikro-Optimierungen nicht.

Was nicht angefasst wird:

- Im Repository wird nur `docs/offene_punkte.md` geändert, committet
  mit ausdrücklichem Pfad, nicht gepusht. Kein `git add -A`, kein
  `git stash`.
- Eingecheckte `.pfm`, `.pdiag`, `.natter` und Beispieldateien nie
  direkt öffnen, wenn sie sich dabei ändern können: Designer und
  Diagramm-Editor schreiben automatisch zurück. Proben laufen auf
  Kopien unter `%TEMP%\natter_<kürzel>_<zufall>\`, die am Ende
  gelöscht werden.
- Kein „Als Exe exportieren“, kein `exe_exportieren`, kein
  `signieren_wenn_moeglich`, keine PowerShell-Zertifikatsbefehle,
  kein PyInstaller, kein `tools.auslieferung_bauen`. Export und
  Signatur nur mit Attrappen (`monkeypatch`) prüfen.
  `tools/signieren/` weder öffnen noch durchsuchen.
- Nichts an Windows ändern: keine Registry-Schreibzugriffe, keine
  Zertifikate, keine Dateizuordnungen. Der Prüfungsmodus schreibt in
  Registry, INI und Datei (`pcl/pruefungsmodus.py`, `RegistryAblage`,
  `IniAblage`, `DateiAblage`); diese Ablagen werden für jede Probe
  auf einen Ordner unter `%TEMP%` umgebogen.
- Skripte außerhalb von pytest, die `HauptFenster` bauen, leiten vor
  dem Import von `ide.shell.hauptfenster` die Einstellungen um:
  `QSettings.setDefaultFormat(QSettings.Format.IniFormat)` und
  `QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())`.
  Zum Warten eine `QEventLoop` mit `QTimer.singleShot`, nicht
  `QTest.qWait`. Proben mit Hauptfenster als pytest:
  `uv run pytest -p tests.conftest <datei> --rootdir=.` mit der
  Fixture `hauptfenster`.
- Keine neue Abhängigkeit. Zufallseingaben mit `random` und festem
  Startwert, nicht mit `hypothesis`.
- Keine volle Testsuite. Einzelne Testdateien sind erlaubt.

Läufe:

- Jeder Unterprozess und jede Warteschleife hat eine Zeitgrenze,
  Ausgabe in eine Datei statt in ein Rohr. Prozessbäume mit
  `taskkill /PID <pid> /T /F` beenden.
- GUI-Proben headless mit `QT_QPA_PLATFORM=offscreen`. Wo Schrift
  oder Pixel zählen, `QT_QPA_FONTDIR=C:\Windows\Fonts` und
  `QApplication.setFont(QFont("Segoe UI", 9))`, bei Schriftfragen
  `QT_QPA_PLATFORM=windows`.
- Am Ende selbst gestartete Prozesse beenden,
  `uv run python -m tools.wache --aufraeumen`, Probeordner löschen.

Abgleich und Eintragen:

- Erst jetzt `docs/offene_punkte.md` und `docs/erledigte_punkte.md`
  lesen. Was dort offen steht, weglassen. Steht ein Punkt als
  erledigt, der Fehler ist aber wieder da, als neuen Punkt eintragen
  und auf den alten verweisen.
- Jeder Befund wird ein eigener Punkt unter „Offen“, vor
  „Zurückgestellt“, im eigenen Nummernbereich, nach der Vorlage oben
  in der Datei. Unter **Gemeldet:** Datum, Session (`Prüfung A`,
  `Prüfung B` oder `Prüfung C`), `<stand>`. Unter **Ursache:** der
  Pfad zum Nachweis. Den Zähler „Der nächste Punkt bekommt …“ nicht
  ändern, das macht die Leitsession.
- Texte nach `AGENTS.md`: niemanden mit „du“ oder „Sie“ ansprechen,
  keine bildhaften Schlusswendungen, keine Vergleiche mit anderen
  Entwicklungsumgebungen. Missbrauchswege so beschreiben, dass sie
  sich beheben lassen, ohne Anleitung zum Ausnutzen.
  `uv run pytest -q tests/test_textstil.py` muss grün sein.
- Rückmeldung an die Leitsession: Name des Zweigs, Tabelle mit
  Nummer, Titel, Art, Schwere (hoch, mittel, gering), belegt oder
  vermutet, dazu eine Zeile, was aus Zeitgründen nicht geprüft wurde.
  Findet sich nichts, keinen Commit anlegen und das sagen.

## 3. Session A: Sicherheit

Grundlage ist `.claude/commands/sicherheit.md` mit ihrem Maßstab
(neugierige Schülerin, Schülerin im Prüfungsmodus, eingeschränkter
Schulrechner) und ihrer Gewichtung. Schwerpunkte aus dem Aufbau von
Natter, in dieser Reihenfolge:

1. Dateien, aus denen Code wird. `ide/designer/laden.py:216` führt
   den aus einer `.pfm` erzeugten Quelltext mit `exec` aus,
   `ide/designer/canvas.py:2059` ebenso beim Einfügen aus der
   Zwischenablage. Geschützt wird das durch `pfm_pruefen`
   (`ide/codegen/design.py:123`) und `_zahlen_pruefen`. Zu klären:
   Gibt es einen Wert in einer `.pfm` (Beschriftung, Listeneinträge,
   Menütexte, Bildpfad, Schriftname, Farbe, Zahl, verschachtelte
   Eigenschaft), der nicht als Literal, sondern als Code im erzeugten
   Quelltext landet? Läuft jeder Weg dorthin über die Prüfung,
   einschließlich Zwischenablage, `.lfm`-Import (`ide/import_lfm/`),
   Codeerzeugung aus Diagrammen (`ide/diagramm/`, `als_python`) und
   Methodeneinfügen über libcst (`ide/codegen/ereignis.py`)? Ein
   Nachweis lädt eine präparierte Datei und zeigt, ob eine
   harmlose Markierung (eine Datei im Probeordner anlegen) entsteht.
2. Prozesse und Suchpfad. `ide/run/starter.py`,
   `ide/run/interpreter.py`, `ide/debugger/dap_client.py` (`runpy`),
   `ide/testrunner/harness.py`, `ide/env/pakete.py` (Paketnamen an
   `pip`), `_sicher_fuer_befehlszeile` in `ide/export/exporter.py`:
   Gehen Projektnamen, Pfade oder Paketnamen ungeprüft in
   Befehlszeilen ein? Kann eine Datei im Projektordner (etwa
   `ruff.py`, `pcl.py`, `debugpy.py`, `sitecustomize.py`) Module der
   IDE oder des Debuggers verdecken? `modul_verdeckt` in
   `ide/run/pruefung.py` als Ausgangspunkt.
3. Prüfungsmodus (`pcl/pruefungsmodus.py`). Alle Wege zu
   Lösungsvorschlägen und Codeerzeugung, während er läuft: Menüs,
   Tastenkürzel, Befehlspalette, Kontextmenüs, Diagrammfenster,
   Hinweise in der Fehleranzeige laufender Schülerprogramme
   (`pcl/fehleranzeige.py`, `pcl/fehlerkatalog.py`). Ablagen und
   Prüfwert: Lässt sich der Modus durch Löschen oder Bearbeiten einer
   Ablage, durch ein anderes Konto oder durch Verstellen der Uhr
   vorzeitig beenden? Stimmt das Verhalten mit `docs/handbuch.md`
   überein?
4. Integrität beim Start (`ide/integritaet/`): Wird vor der Prüfung
   schon Code aus den zu prüfenden Dateien importiert? Was passiert
   bei fehlendem, vertauschtem oder verändertem Manifest und bei einer
   veränderten Datei außerhalb der Kernliste? Nur gegen eine Kopie
   eines Ordners mit Manifest, nie gegen eine Installation.
5. Dateisystem. Projektsperre (`ide/project/sperre.py`),
   Verknüpfungen (`ist_verknuepfung`, `enthaelt_verknuepfung` in
   `ide/project/projekt.py`), Pfade mit `..`, Laufwerk, UNC,
   reservierten Namen und Überlänge in `.natter`, `.pfm` und
   `.pdiag`, atomares Schreiben (`ide/atomar.py`) bei vollem oder
   schreibgeschütztem Ziel, Papierkorb (`ide/papierkorb.py`).
6. Datenbank: Abschnitt 8 aus `sicherheit.md`, Schwerpunkt SQL aus
   Tabellen- und Spaltennamen, `ATTACH` und gesperrt bleibende
   Dateien.

Art für die Tabelle: Codeausführung, Prüfungsmodus, Dateisystem,
Integrität, Prozess, Datenbank, Netz.

## 4. Session B: Funktionstüchtigkeit

Grundlage ist `.claude/commands/durchsicht.md` mit ihrem Maßstab
(Schülerin in den ersten Monaten, Lehrkraft im Computerraum). Hier
wird jeder Kernablauf einmal im Code verfolgt und einmal echt
durchgespielt, mit pytest-qt und der Fixture `hauptfenster`, nicht
nur gelesen. Ein Ablauf gilt als funktionstüchtig, wenn er von Anfang
bis Ende das Erwartete tut und danach kein Zustand, Prozess oder
Dateirest übrig bleibt.

1. Projekt: neu aus jeder Vorlage (`ide/project/neu.py`,
   `templates/`), öffnen über Menü, zuletzt geöffnet und
   Kommandozeile (`_projekt_aus_argv_oeffnen` in `ide/main.py`),
   speichern, alle speichern, beenden mit ungespeicherten Änderungen,
   Sicherung (`ide/project/sicherung.py`), Datei von außen geändert
   (`ide/dateistand.py`).
2. Designer-Kette: Komponente platzieren, `.pfm` (nach 400 ms, vorher
   `canvas.jetzt_schreiben()`), `_design.py`, Doppelklick legt die
   Methode an, Komponente und Methode umbenennen, löschen,
   duplizieren, Rückgängig und Wiederholen. Eigenschaft im Inspektor
   und Attribut im laufenden Programm müssen übereinstimmen.
3. Starten und Stoppen: Vorstartprüfung (`ide/run/pruefung.py`) auf
   falsche Treffer, die einen korrekten Start verhindern, und auf
   übersehene Fehler; GUI- und Konsolenprogramm; Ausgabe im Panel
   (lange Zeilen, viele Zeilen, ohne Zeilenende, Umlaute); F5 und
   sofort Stopp; zweimal hintereinander starten; Programm, das
   Kindprozesse startet; nach dem Ende keine Prozesse übrig
   (`ide/prozess.py`, `prozessbaum_beenden`).
4. Debugger (`ide/debugger/`): Haltepunkt setzen, nach Bearbeiten und
   Schließen des Reiters erhalten, Einzelschritt, Variablen und
   Tabellenansicht, Ausnahme im Schülerprogramm, `input()` beim
   Debuggen, Abbruch mitten im Schritt.
5. Weitere Abläufe: Testrunner (`ide/testrunner/`), Datenbank-Panel
   mit Transaktion und Programmstart, Diagramm zu Code (UML und
   Struktogramm), Fehlermeldungen: passt die deutsche Meldung aus
   `docs/fehlerkatalog.yaml` zur tatsächlich ausgelösten Ausnahme?
   Deutsches Zahlenformat (`pcl/zahlen.py`) in Anzeige und Eingabe.
6. Dokumentation gegen Code: Tastenkürzel in `docs/handbuch.md`
   gegen `ide/shell/tastenkuerzel.py` und das Aktionsregister,
   Eigenschaften in `docs/komponenten.md` gegen `pcl/components/`.
   Menüeinträge, die nichts tun; Funktionen ohne Weg in der
   Oberfläche.
7. Ausgangslage: Jeder rote Test aus Schritt 0.4 wird einzeln
   nachgestellt. Rot aus eigenem Fehler ist ein Befund, rot aus der
   Umgebung (Schrift, Zeit, Parallelität) ebenfalls, dann als
   wackelnder Test.

Art für die Tabelle: Logikfehler, Absturz, Datenverlust,
Prozessrest, Erreichbarkeit, Widerspruch, wackelnder Test.

## 5. Session C: Fehlersuche durch Testen

Diese Session liest wenig und probiert viel. Sie erzeugt Eingaben,
führt sie aus und hält fest, was bricht. Alle Probe-Tests liegen im
Nachweisordner, nicht unter `tests/`. Jede Probe hat einen festen
Startwert und eine Zeitgrenze und meldet die Fälle, die scheitern,
in verkleinerter Form (der kürzeste Fall, der den Fehler noch zeigt).

1. Rundläufe. Für jede `.pfm`, `.pdiag` und `.natter` aus
   `beispielprojekte/` und `templates/` (Kopien): laden, speichern,
   wieder laden, Inhalt gleich. Für `.pfm` zusätzlich: erzeugter
   Code (`design_code_erzeugen`) kompiliert und besteht `ruff check
   --isolated`. Für die `.lfm` aus `tests/daten/` und selbst
   abgewandelte Fassungen davon: Import, dann derselbe Rundlauf.
2. Beschädigte Dateien. Je Format einige hundert Abwandlungen der
   Rundlauf-Dateien: Felder entfernt, Typen vertauscht, riesige und
   negative Zahlen, tiefe Verschachtelung, leere Datei, BOM,
   ANSI-Kodierung, Binärmüll, sehr lange Namen. Erwartet ist eine
   deutsche Meldung über die vorgesehene Ausnahme
   (`PfmBeschaedigt`, `ProjektdateiUngueltig` und ihre Gegenstücke),
   nie eine rohe Ausnahme, kein Hänger über 5 Sekunden, kein
   Speicherwachstum über 500 MB. Gleiches für CSV im Datenbank-Panel
   und für die Einstellungsdatei.
3. Komponenten mit Randwerten. Über das `Prop`/`Event`-System alle
   Komponenten aus `pcl/components/` erzeugen und jede Eigenschaft
   mit Randwerten setzen und wieder lesen: leer, `None`, 0, negativ,
   sehr groß, Unicode mit Emoji und RTL, Dezimalkomma, falscher Typ.
   Erwartet: Wert kommt so zurück oder es gibt eine deutsche Meldung.
   Parametrisiert je Verhalten, nicht je Eigenschaft.
4. Beispielprojekte. Jedes unter `beispielprojekte/` als Kopie mit
   `python main.py` starten (offscreen, Zeitgrenze 30 Sekunden,
   Fenster per Timer schließen). Läuft es an, endet es sauber, bleibt
   ein Prozess übrig?
5. Rückgängig und Wiederholen. Im Designer, im Diagramm-Editor (UML,
   Struktogramm, Entscheidungstabelle) und im Editor je 50 zufällige
   Folgen aus 5 bis 30 Handgriffen: alles rückgängig ergibt genau den
   Anfang, alles wiederholen genau das Ende, die Datei auf der Platte
   passt jeweils zum Zustand.
6. Rückfälle. Abweichend von Abschnitt 2 hier zuerst
   `docs/erledigte_punkte.md` lesen und aus den letzten 150 Punkten
   30 auswählen, bevorzugt Datenverlust, Absturz, Hänger und
   Prozessreste. Für jeden den beschriebenen Fehler nachstellen. Ist
   er wieder da, ist das ein Befund mit Verweis auf den alten Punkt.
   Gibt es zu einem Punkt keinen Test unter `tests/`, der ihn
   abdeckt, in der Rückmeldung als Testlücke nennen, nicht als Punkt.

Art für die Tabelle: Rundlauf, beschädigte Datei, Randwert,
Beispielprojekt, Rückgängig, Rückfall.

## 6. Zusammenführen (Leitsession)

Erst wenn alle drei Sessions zurückgemeldet haben:

1. Die drei Zweige nacheinander in `main` zusammenführen. Konflikte
   treten nur in `docs/offene_punkte.md` auf.
2. Dubletten zwischen den Sessions zu einem Punkt zusammenlegen, die
   Nachweise beider nennen.
3. Nummern lückenlos ab `N` neu vergeben, Verweise „Punkt …“ im Text
   mitziehen, den Zähler „Der nächste Punkt bekommt …“ setzen.
   Reihenfolge: Codeausführung und Prüfungsmodus, dann Datenverlust
   und Abstürze, dann Logikfehler, dann der Rest.
4. `uv run pytest -q tests/test_textstil.py`, dann
   `git add docs/offene_punkte.md`, committen, pushen.
5. Nachkontrolle: `%LOCALAPPDATA%\Natter\`, `%APPDATA%\Natter\`,
   `HKCU:\Software\Natter` und `Cert:\CurrentUser\*` auf Einträge, die
   während der Prüfung entstanden sind. Gefundenes melden, nicht
   still löschen.
6. `uv run python -m tools.wache --aufraeumen`, Probeordner löschen,
   Sessions archivieren. Zweige und Arbeitsbäume bleiben stehen.

## 7. Bericht

Kurz und auf Deutsch:

- je Frage ein Urteil in zwei bis drei Sätzen: Sicherheit,
  Funktionstüchtigkeit, Fehlerlage, jeweils mit dem schwersten Befund;
- Tabelle aller neuen Punkte: Nummer, Titel, Session, Art, Schwere,
  belegt oder vermutet;
- Ausgangslage der Tests (grün, rot, wackelnd);
- was nicht geprüft wurde und warum, dazu die Testlücken aus 5.6;
- Pfad zum Nachweisordner.

Dauer: Vorbereitung rund 10 Minuten, die drei Sessions je ein bis
zwei Stunden gleichzeitig, Zusammenführen rund 15 Minuten.
