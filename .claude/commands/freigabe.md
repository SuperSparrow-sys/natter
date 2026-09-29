---
description: Prüfen und Beheben im Wechsel über alle Qualitätsthemen, bis keine Punkte mehr offen sind; dann eine neue Fassung bauen, installieren und mit Bildschirmfotos prüfen
argument-hint: "[Versionsnummer, z. B. 0.4.0]"
---

# Freigabe: Prüfen, beheben, wiederholen - dann bauen

Ziel ist eine neue Fassung von Natter mit der Nummer `$1`. Gebaut wird
erst, wenn alle Qualitätsthemen hintereinander nichts Neues mehr finden
und in `docs/offene_punkte.md` unter „Offen“ nichts mehr steht. Danach
wird die Fassung gebaut, veröffentlicht, auf diesem Rechner installiert
und an der echten Oberfläche mit Bildschirmfotos geprüft.

Der Lauf dauert Stunden und läuft ohne Rückfragen durch. Alles, was
vom Nutzer zu entscheiden ist, wird am Anfang in einer einzigen Frage
geklärt.

## 0. Vorher: Stand und Fragen

- `git status`, `git log --oneline -5`: nicht eingecheckte Änderungen
  erst committen. Stand pushen.
- `uv run python -m tools.wache --aufraeumen` einmal laufen lassen und
  liegen gebliebene Probeordner `%TEMP%\natter_*` sowie fertige
  Arbeitsbäume unter `.claude/worktrees` entfernen.
- `docs/offene_punkte.md` lesen. Für jeden Punkt, der sich nicht ohne
  den Nutzer lösen lässt (braucht CI, echte Hardware, eine
  Entscheidung, Geld), in der einen Frage am Anfang klären: beheben
  oder unter „Zurückgestellt“ verschieben (mit Begründung im Punkt).
  Punkte unter „Zurückgestellt“ halten den Bau nicht auf.
- Versionsnummer `$1` bestätigen, falls leer: aus `git log` seit der
  letzten Fassung vorschlagen (siehe `.claude/commands/auslieferung.md`).

## 1. Themen und Reihenfolge

Die Themen laufen im Wechsel, immer in dieser Reihenfolge, jeweils mit
dem gleichnamigen Befehl unter `.claude/commands/`:

1. `durchsicht` - Logikfehler, Datenverlust, Unerreichbares, Widersprüche
2. `sicherheit` - Unterbau, Absturzsicherheit, Datenintegrität, Prüfungsmodus
3. `benutzbarkeit` - Anfängerinnen und Lehrkräfte an der Oberfläche
4. `leistung` - Startzeit, Reaktionszeit, Speicher, große Daten
5. `betrieb` - Installation, Aktualisierung, Konten, Verteilung

Barrierefreiheit ist keine Anforderung und wird nicht geprüft.

## 2. Eine Runde

Jede Runde nimmt das nächste Thema aus der Reihenfolge und läuft in
drei Schritten. Es arbeiten zu keinem Zeitpunkt mehr als drei Helfer
gleichzeitig.

### 2a. Prüfen

- Ein bis drei frische Helfer (`isolation: worktree`, ohne den Kontext
  dieser Sitzung) führen den Befehl des Themas aus. Bei zwei oder drei
  Helfern bekommt jeder eigene Bereiche des Themas und einen eigenen
  Nummernbereich (Helfer 1 ab der nächsten freien Nummer, Helfer 2 ab
  +30, Helfer 3 ab +60, Zähler nur Helfer 1). Faustregel: `sicherheit`
  zwei Helfer (Bereiche 1, 2, 5, 6, 7 und 3, 4, 8), `benutzbarkeit` und
  `betrieb` zwei, die übrigen einer.
- Jeder Auftrag an einen Helfer enthält: zuerst `git merge --ff-only
  main`; nur `docs/offene_punkte.md` committen, nicht pushen;
  Probeordner eindeutig unter `%TEMP%\natter_…` und am Ende löschen;
  jede Warteschleife und jeder Hintergrundlauf mit eigener Zeitgrenze;
  gestartete Prozesse selbst beenden; `tools/signieren/` weder öffnen
  noch durchsuchen; kein `git stash`; keine volle Testsuite; nichts
  bauen oder installieren; nur Befunde, die im Unterricht spürbar sind
  und sich belegen lassen.
- Nach dem Prüfen: Zweige zusammenführen, Nummern lückenlos neu
  vergeben (auch Verweise „Punkt N“ im Text), `tests/test_textstil.py`,
  committen, pushen.

### 2b. Beheben

- Die neuen Punkte in höchstens drei Stränge aufteilen, getrennt nach
  Dateien, damit sie sich nicht in die Quere kommen. Jeder Strang ist
  ein Helfer mit `isolation: worktree`, bekommt die Regeln aus
  `AGENTS.md`, einen Test je Punkt, der ohne die Änderung scheitert
  (Gegenprobe über Patch-Datei oder Kopie), die Stufe „schnell“ und die
  betroffenen Testdateien, und schreibt Archivtexte nach
  `build/auswertung/punkte_<erste Nummer>ff.json`.
- Entscheidungen, die nur der Nutzer treffen kann und die am Anfang
  nicht geklärt wurden: den Punkt unter „Zurückgestellt“ verschieben,
  mit Begründung, und am Ende berichten. Nicht raten.

### 2c. Zusammenführen und sichern

- Zweige nacheinander zusammenführen, Konflikte auflösen (meist nur
  Importe), `uv run ruff check .`.
- Volle Suite parallel: `uv run pytest -q -p no:cacheprovider -n 8
  --dist loadfile --max-worker-restart=0`, mit `timeout 1800` und
  Ausgabe in eine Datei. Rot heißt: beheben, bevor es weitergeht.
- Archivtexte zusammenführen und mit
  `build/auswertung/punkte_verschieben.py` ins Archiv verschieben,
  committen, pushen.
- Nach dem Push den CI-Lauf auf GitHub abwarten (`gh run watch`, in
  Git Bash mit vollem Pfad `/c/Program Files/GitHub CLI/gh.exe`, mit
  Zeitgrenze); rot wird wie ein neuer Punkt behandelt.
- `uv run python -m tools.wache --aufraeumen`, fertige Arbeitsbäume
  und ihre Zweige entfernen.

## 3. Die Wache (alle 10 Minuten)

Zu Beginn eine Überwachung starten, die für die ganze Dauer läuft und
nach Ablauf neu gestartet wird:

```
Monitor(timeout_ms=1800000, command:
  while true; do sleep 600; uv run python -m tools.wache --still 20 2>&1 | head -30; done)
```

Jede Meldung „WACHE AUFFAELLIG“ wird sofort bearbeitet:

- verwaist oder hängend (Prozesse): gehören sie zu keinem laufenden
  Helfer, mit `uv run python -m tools.wache --aufraeumen` beenden;
  gehören sie zu einem laufenden Helfer, erst nachsehen, ob er noch
  arbeitet.
- still (Arbeitsbaum seit 20 Minuten unverändert): hat der zugehörige
  Helfer seit mehr als 30 Minuten nichts gemeldet und läuft bei ihm
  kein Test, gilt er als hängend: mit `TaskStop` beenden, seinen
  Arbeitsbaum ansehen (Brauchbares übernehmen) und die Aufgabe einmal
  neu vergeben. Hängt sie ein zweites Mal, die betroffenen Punkte unter
  „Zurückgestellt“ verschieben und am Ende berichten.
- liegen geblieben (Probeordner): löschen, wenn kein Helfer mehr läuft.
- Speicher knapp: keine neuen Helfer starten, bis wieder genug frei ist.

Ein vorübergehender Fehler der Werkzeugprüfung oder des Kontos („no
verdict“, „organization has disabled …“) ist kein Hänger: einmal
wiederholen, sonst warten und den Nutzer benachrichtigen.

## 4. Ende der Schleife

Die Schleife endet, wenn beides gilt:

- die letzten fünf Runden (alle Themen je einmal) haben keinen neuen
  Punkt gefunden, und
- unter „Offen“ in `docs/offene_punkte.md` steht nichts mehr.

Findet eine Runde etwas, beginnt die Zählung neu. Es wird so lange im
Kreis geprüft und behoben, bis die Helfer nichts mehr finden, höchstens
aber 15 Runden. Nach jeweils fünf Runden geht eine kurze Nachricht an
den Nutzer (Befunde je Runde, was wiederholt auftaucht). Ist nach 15
Runden noch nicht Schluss, wird angehalten, nicht gebaut, und berichtet
- dann entscheidet der Nutzer. Taucht derselbe Fehler
nach dem Beheben zum dritten Mal auf, wird er gründlicher angegangen
(Ursache statt Symptom, eigener Strang), nicht zurückgestellt.

## 5. Bauen, veröffentlichen, installieren

Erst jetzt, nach `.claude/commands/auslieferung.md`:

1. `uv run python -m tools.auslieferung_bauen --version $1` im
   Hintergrund, Ausgabe in eine Datei, eine Wache auf Schritte, Fehler
   und Stille über 5 Minuten. Bricht er ab: Ursache lesen, beheben,
   Tests zu `tools/` laufen lassen, ganz neu starten.
2. Der Bau veröffentlicht selbst auf GitHub (Schritt 12). Die
   Release-Beschreibung nennt die neuen Funktionen und behobenen Fehler
   seit der letzten Fassung in wenigen Sätzen.
3. Installation auf diesem Rechner, still über die vorhandene Fassung:
   `Natter-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
   /CURRENTUSER /LOG=…`, Zeitgrenze 10 Minuten, Rückgabe 0; danach
   prüfen, dass Windows `$1` führt und `ide/main.py` in der
   Installation `VERSION = "$1"` hat.

## 6. Prüfen an der installierten Fassung

Mit einem Skript nach dem Muster von `build/auswertung/036/ui_036.py`
(UI Automation, echte Tasten und Klicks, Bildschirmfotos), abgelegt
unter `build/auswertung/<version>/`:

- erster Start nach der Installation: Zeit messen (Ziel unter 10 s),
  Bild der Startseite;
- ein Beispiel mit Fenster (Notizbuch): Start mit und ohne Debugger,
  Stopp, F5 und sofort Stopp, Ladeanzeige in der Statusleiste sichtbar;
- ein Beispiel mit scikit-learn (ObstSortierer): erster Start in Sekunden;
- Malen mit gezogenem Strich; Konsolenprogramm mit Umlauteingabe;
- Rechtsklick auf ein zweites Formular im Explorer;
- Datenbank-Panel: Verbinden, `BEGIN`, Programmstart mit Nachfrage;
- nach jedem Schritt und nach dem Beenden: `tools.wache` ohne
  verwaiste Prozesse.

Jedes Bild ansehen, nicht nur speichern. Was nicht stimmt, ist ein
neuer Punkt: beheben, und der Ablauf beginnt bei 2c mit einer
Patch-Fassung (dritte Stelle der Nummer +1).

## 7. Abschluss

- Eintrag in `docs/bericht.md`, Abschnitt 8: Datum, Fassung, Größe,
  Signaturen, Dauer, Runden und Befunde je Thema, Messwerte (erster
  Start, Programmstart), was beim Bau oder der Installation schiefging
  - mitsamt Irrweg.
- Committen, pushen, CI abwarten.
- `tools.wache --aufraeumen`, Arbeitsbäume, Zweige und Probeordner
  entfernen.
- Dem Nutzer die Bildschirmfotos schicken und in wenigen Zeilen
  berichten: Version, Adresse des Releases, Größe, Signaturstatus,
  Runden je Thema mit Zahl der Befunde, Messwerte, zurückgestellte
  Punkte mit Grund.
