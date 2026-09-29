---
description: Unabhängige Durchsicht von Natter nach Fehlern, Logikfehlern und Lücken; Befunde in docs/offene_punkte.md eintragen
---

# Durchsicht: Was stimmt nicht, was fehlt?

Natter ist eine Python-Entwicklungsumgebung für den Informatikunterricht
(Quelltext unter `ide/`, Komponentenbibliothek `pcl/`, Hilfetexte unter
`docs/`, Beispielprojekte unter `beispielprojekte/`, Installer unter
`tools/`). Aufgabe ist eine unabhängige Durchsicht: finden, was falsch
ist, was sich widerspricht und was fehlt. Nichts reparieren.

## Ohne Vorwissen anfangen

Die Liste `docs/offene_punkte.md` und das Archiv
`docs/erledigte_punkte.md` erst am Ende lesen, beim Abgleich. Wer sie
vorher liest, sucht nur noch dort, wo schon gesucht wurde. Ebenso keine
Auswertungen unter `docs/auswertung/` vorab lesen.

Maßstab sind zwei Personen: eine Schülerin in den ersten Monaten
Programmieren, die mit Natter Oberflächen baut, Konsolenprogramme
schreibt, debuggt und Diagramme zeichnet; und eine Lehrkraft, die Natter
auf Schulrechnern installiert, Aufgaben stellt und Abgaben einsammelt.

## Wonach gesucht wird

1. Logikfehler: Code, der unter bestimmten Eingaben das Falsche tut -
   falsche Bedingungen, vertauschte Koordinaten, Rückgängig/Wiederholen,
   das nicht genau umkehrt, Zustand, der nach einem Abbruch
   stehenbleibt, Zählfehler, Randfälle (leer, ein Element, sehr groß).
2. Abstürze und Datenverlust: Ausnahmen ohne Behandlung, Speichern, das
   still scheitert, Dateien, die überschrieben werden, Arbeit, die beim
   Schließen verlorengeht.
3. Erreichbarkeit: Funktionen, die programmiert sind, aber in der
   Oberfläche nicht erreicht werden (kein Menü, keine Taste, kein
   Kontextmenü); Daten im Dateiformat (`schemas/`), die sich nicht
   bearbeiten lassen; Menüeinträge, die nichts tun.
4. Widersprüche: Hilfe, Handbuch, README oder Meldungen, die etwas
   anderes sagen als der Code tut; Tastenkürzel, die doppelt belegt
   oder falsch angegeben sind.
5. Fehlende Möglichkeiten: was für den Unterricht gebraucht wird und
   fehlt (Komponenten-Eigenschaften, Ereignisse, Dialoge, Editor- und
   Debugger-Funktionen, Designer-Handgriffe).
6. Auslieferung: was im Entwicklungsbaum geht, in der gebauten Fassung
   aber nicht (fehlende Dateien, Pfade, Rechte, Signaturen).

## Wie gearbeitet wird

- Jeden Befund am Code belegen: Datei und Zeile, dazu ein Nachweis -
  ein kurzer Aufruf mit `uv run python -c …` im Ordner `%TEMP%`, ein
  Test mit `QT_QPA_PLATFORM=offscreen` oder ein `grep`, der das Fehlen
  zeigt. Was sich nicht belegen lässt, als „vermutet“ kennzeichnen oder
  weglassen.
- Nichts im Repository ändern außer `docs/offene_punkte.md`. Keine
  eingecheckte `.pfm` oder Beispieldatei öffnen, die sich dabei
  verändern könnte; Proben laufen auf Kopien in einem temporären Ordner.
- Nichts bauen, nichts installieren, nichts an Windows ändern.
- Lange Läufe mit Zeitgrenze und Ausgabe in eine Datei.

## Abgleich und Eintragen

Erst jetzt `docs/offene_punkte.md` und `docs/erledigte_punkte.md`
lesen. Befunde, die dort schon stehen, weglassen; steht dort ein Punkt
als erledigt, der Fehler ist aber noch da, als neuen Punkt eintragen und
auf den alten verweisen.

Jeden verbleibenden Befund als eigenen Punkt in `docs/offene_punkte.md`
unter „Offen“ eintragen, vor „Zurückgestellt“, mit der Nummer, die oben
in der Datei als nächste genannt ist, und diese Nummer danach
hochzählen. Aufbau wie die Vorlage oben in der Datei:

```markdown
## 123. Kurz, was nicht stimmt

**Gemeldet:** Datum, Durchsicht, Entwicklungsstand (Commit).

**Beobachtet:** Was passiert und was stattdessen zu erwarten wäre.

**Ursache:** nachgewiesen, mit Datei und Zeile - oder vermutet.

**Zu tun:** Was geändert werden muss und woran das Erledigtsein zu
erkennen ist.
```

Reihenfolge nach Schwere: Datenverlust und Abstürze zuerst, dann
Logikfehler, dann Erreichbarkeit, Widersprüche und fehlende
Möglichkeiten.

Für die Texte gelten die Regeln aus `AGENTS.md`: niemanden mit „du“
oder „Sie“ ansprechen, keine bildhaften Schlusswendungen, keine
Fettschrift und keine Zuschreibungs-Etiketten in Kommentaren, keine
Vergleiche mit anderen Entwicklungsumgebungen. `uv run pytest -q
tests/test_textstil.py` muss danach grün sein.

## Abschluss

`docs/offene_punkte.md` committen (nur diese Datei, mit ausdrücklichem
Pfad) und pushen. Zum Schluss eine Tabelle ausgeben: Nummer, Titel,
Art (Logikfehler, Absturz, Datenverlust, Erreichbarkeit, Widerspruch,
fehlt), Schwere (hoch, mittel, gering), belegt oder vermutet.
