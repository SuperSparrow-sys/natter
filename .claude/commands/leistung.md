---
description: Unabhängige Prüfung der Leistung von Natter (Startzeit, Reaktionszeit, Speicher, große Daten); Befunde mit Messwerten in docs/offene_punkte.md eintragen
---

# Leistung: Bleibt Natter auf einem Schulrechner flüssig?

Natter ist eine Python-Entwicklungsumgebung für den Informatikunterricht
(Quelltext unter `ide/`, Komponentenbibliothek `pcl/`, Starter und Bau
unter `tools/`). Aufgabe ist eine unabhängige Messung der Leistung:
Wo wartet jemand spürbar, wo wächst der Speicher, wo steht die
Oberfläche? Nichts reparieren.

## Ohne Vorwissen anfangen

`docs/offene_punkte.md`, `docs/erledigte_punkte.md` und `docs/bericht.md`
erst am Ende lesen, beim Abgleich.

Maßstab ist ein typischer Schulrechner: vier Kerne, 8 GB Speicher,
SSD oder langsame Festplatte, Virenscanner aktiv, Projekte auf einem
Netzlaufwerk, 30 Rechner starten gleichzeitig. Spürbar ist, was länger
dauert als:

- 1 Sekunde für eine Reaktion auf Klick oder Taste,
- 3 Sekunden für das Öffnen eines Projekts oder Designers,
- 5 Sekunden für den Start eines kleinen Programms,
- 10 Sekunden für den Start von Natter selbst.

## Was gemessen wird

1. Start von Natter: kalt (erster Start nach Neustart bzw. nach
   Installation) und warm; Anteil von Python-Start, Importen, Qt,
   Integritätsprüfung, Aufwärmen der Vervollständigung. Werkzeug: `-X
   importtime`, Zeitstempel im Code nur in einer Kopie.
2. Start eines Schülerprogramms: Konsole, Fenster, Fenster mit pandas,
   matplotlib oder scikit-learn; mit und ohne Debugger; erster und
   zweiter Start.
3. Reaktionszeit der Oberfläche: Tippen in einer Unit mit 50, 500 und
   5 000 Zeilen, Vervollständigung, Wellenlinien der Prüfung, Suchen
   und Ersetzen, Designer mit 5, 50 und 200 Komponenten, Objektinspektor,
   Diagramme mit vielen Formen, Rückgängig über viele Schritte.
4. Große Daten: CSV und Datenbank mit 10 000 und 1 000 000 Zeilen im
   Datenbank-Panel, in `DBGrid`, `StringGrid`, Chart; viel Ausgabe im
   Panel „Ausgabe“; große Bilder in `Image`.
5. Speicher über die Zeit: eine Doppelstunde nachstellen (Projekte
   öffnen und schließen, 50-mal starten und stoppen, Designer und
   Diagramme öffnen und schließen) und den Speicher von Natter vorher
   und nachher messen; übrig gebliebene Prozesse zählen.
6. Hintergrundarbeit: Stellen, an denen der Hauptfaden wartet
   (Dateizugriffe, Unterprozesse, Netzwerk), gefunden per Code und
   bestätigt per Messung (ein Timer im Hauptfenster, dessen Aussetzer
   gemessen werden).
7. Netzlaufwerk: Öffnen, Speichern und Starten eines Projekts auf einem
   langsamen Pfad (nachstellen über einen Ordner mit künstlicher
   Verzögerung oder einen UNC-Pfad auf `\\localhost\…`, falls
   vorhanden).

## Wie gearbeitet wird

- Messen, nicht schätzen: jede Messung mindestens dreimal, Median
  angeben, Rechner und Bedingungen (kalt/warm, andere Last) nennen.
  Für die gebaute Fassung `dist\Natter` nur lesen, Messungen an einer
  Kopie in einem eigenen Ordner unter `%TEMP%`.
- Jeden Befund belegen: Messwert, Grenze aus dem Maßstab, Ursache mit
  Datei und Zeile, wenn gefunden, sonst „Ursache vermutet“.
- Nichts im Repository ändern außer `docs/offene_punkte.md`. Nichts
  bauen, nichts installieren, nichts an Windows ändern. Keine volle
  Testsuite. Jede Warteschleife und jeder Hintergrundlauf bekommt eine
  Zeitgrenze; gestartete Prozesse selbst beenden; Temp-Ordner am Ende
  löschen.

## Abgleich und Eintragen

Erst jetzt `docs/offene_punkte.md` und `docs/erledigte_punkte.md`
lesen, Bekanntes weglassen. Jeden Befund als eigenen Punkt unter
„Offen“ vor „Zurückgestellt“, mit der nächsten freien Nummer, Aufbau
wie die Vorlage oben in der Datei (Gemeldet: Datum, Leistungsprüfung,
Commit), im Punkt die Messwerte und im „Zu tun“ eine messbare Grenze.

Reihenfolge: stehende Oberfläche zuerst, dann lange Wartezeiten beim
Starten, dann wachsender Speicher, dann Übriges. Für die Texte gelten
die Regeln aus `AGENTS.md`; `uv run pytest -q tests/test_textstil.py`
muss danach grün sein.

## Abschluss

`docs/offene_punkte.md` committen (nur diese Datei, mit ausdrücklichem
Pfad) und pushen. Tabelle: Nummer, Titel, Art (Start, Reaktion, große
Daten, Speicher, Hauptfaden, Netzlaufwerk), gemessener Wert, Grenze,
Schwere. Dazu eine kurze Tabelle aller Messungen, auch der unauffälligen.
Findet sich nichts, keinen Commit anlegen und das ausdrücklich sagen.
