---
description: Aus dem aktuellen Stand eine neue, signierte Natter-Setup.exe bauen
argument-hint: "[neue Versionsnummer, z. B. 0.2.0]"
---

Baue aus dem jetzigen Stand des Arbeitsbaums eine neue, auslieferbare
`Natter-Setup.exe`. Gewünschte Versionsnummer (kann leer sein): `$1`

Die Arbeit macht `tools/auslieferung_bauen.py`. Deine Aufgabe ist das,
was ein Skript nicht kann: entscheiden, ob gebaut werden darf, einen
Fehlschlag deuten und den fertigen Stand festhalten.

Der Lauf dauert eine halbe Stunde. Was du vom Nutzer wissen musst,
fragst du deshalb **am Anfang und in einer einzigen Frage** – danach
läufst du ohne Rückfragen durch.

## 1. Vorher: darf gebaut werden?

Sieh dir `git status` und `git log --oneline -5` an.

- **Nicht eingecheckte Änderungen**: sie kommen in die Auslieferung
  hinein, aber der ausgelieferte Stand steht dann in keinem Commit und
  lässt sich später nicht wiederfinden. Committe sie vorher, statt
  darüber zu diskutieren; nenn in der Commit-Nachricht, was sie ändern.
- **Generierte Dateien von Hand geändert** (`u_*_design.py` und alles
  mit „Automatisch erzeugt … – nicht bearbeiten" in der Kopfzeile):
  das ist ein Abbruchgrund, siehe AGENTS.md. Melde es und baue nicht.

## 2. Versionsnummer

Ohne `$1` bleibt die Nummer, wie sie ist – für einen Probebau in
Ordnung, für ein Update an die Schulen nicht: Windows erkennt eine neue
Fassung an `AppVersion`, und bleibt die gleich, zeigt „Apps & Features"
nach dem Update weiter die alte Nummer.

Ist `$1` leer, lies an `git log` ab, was seit dem letzten Bau passiert
ist, und schlag eine Nummer vor: Patch für Fehlerbehebungen, Minor für
neue Komponenten oder Menüeinträge. Das ist die eine Frage am Anfang –
zusammen mit allem anderen, was noch offen ist.

## 3. Bauen

```
uv run python -m tools.auslieferung_bauen [--version <Nummer>]
```

Der Lauf dauert **zwanzig bis dreißig Minuten** – Tests, `pip`,
PyInstaller und die LZMA2-Kompression des Installers. Starte ihn im
Hintergrund und arbeite nicht daneben am selben Baum weiter; sonst baut
er einen Stand, den es nie gab.

Die zehn Schritte prüfen sich gegenseitig ab. Wichtig sind:

- **Schritt 4 (`pytest`)** – rot heißt: nicht bauen, Fehler beheben.
- **Schritt 6 (Rauchprobe in der gebauten Python)** – die Prüfung, die
  ein grünes Testprotokoll nicht ersetzt. Hier ist im September 2026
  aufgefallen, dass pandas in `dist` gar nicht lud, während im
  Entwicklungsbaum alles lief.
- **Schritt 7 (Manifest)** – schlägt an, wenn nach dem Signieren noch
  etwas an den Dateien geändert wurde. Beim Schüler gäbe das eine
  Manipulationswarnung beim ersten Start.

## 4. Wenn es abbricht

Rate nicht, sondern lies die Ausgabe des fehlgeschlagenen Schritts.
Behebe die Ursache und starte **den ganzen Lauf neu**, nicht nur den
einen Schritt – die Schritte bauen aufeinander auf.

`--nur-installer` ist ausschließlich dafür da, wenn nur an
`tools/natter.iss` etwas geändert wurde. `--ohne-tests` nie für eine
Auslieferung, die aus dem Haus geht.

## 5. Nachher: festhalten

- Schreib das Ergebnis in `docs/arbeitspakete/M13.md` (Abschnitt „Stand
  des Baus"): Datum, Version, Größe, Signaturstatus. Hat der Lauf etwas
  aufgedeckt, gehört der Befund dorthin – **mitsamt dem Irrweg**, falls
  einer dabei war. Ein festgehaltener Irrweg spart beim nächsten Mal
  einen halben Tag; siehe den Abschnitt zum Selbstsignieren.
- Committe die Versionsänderung und die Dokumentation und pushe.
  `dist/` gehört nicht ins Repository.
- Berichte am Ende in wenigen Zeilen: Version, Dateigröße, Ergebnis der
  Rauchprobe, Signaturstatus beider Dateien, Dauer. Nenn den Pfad
  `dist\installer\Natter-Setup.exe`, damit der Nutzer die Datei
  hochladen kann.

## Was du nicht tust

- Die fertige Exe irgendwohin hochladen oder veröffentlichen. Das macht
  der Nutzer.
- Einen roten Schritt übergehen, weil der Rest gut aussah.
- Ein grünes Testprotokoll als Beleg dafür nehmen, dass die
  Auslieferung funktioniert. Getestet wird der Entwicklungsbaum;
  ausgeliefert wird `dist\Natter`. Das ist nicht dasselbe, und genau
  dazwischen sind die letzten beiden Fehler entstanden.
