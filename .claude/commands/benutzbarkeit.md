---
description: Unabhängige Prüfung der Benutzbarkeit von Natter aus Sicht von Anfängerinnen und Lehrkräften; Befunde in docs/offene_punkte.md eintragen
---

# Benutzbarkeit: Kommt eine Anfängerin allein zurecht?

Natter ist eine Python-Entwicklungsumgebung für den Informatikunterricht
(Quelltext unter `ide/`, Komponentenbibliothek `pcl/`, Hilfeseiten unter
`docs/`, Beispielprojekte unter `beispielprojekte/`, Vorlagen unter
`templates/`). Aufgabe ist eine unabhängige Prüfung der Benutzbarkeit:
Wo bleibt jemand hängen, wird in die Irre geführt, verliert Zeit oder
gibt auf? Nichts reparieren.

## Ohne Vorwissen anfangen

`docs/offene_punkte.md`, `docs/erledigte_punkte.md` und `docs/bericht.md`
erst am Ende lesen, beim Abgleich.

Maßstab sind drei Personen, die Natter zum ersten Mal sehen:

- Eine Schülerin der 7. oder 8. Klasse ohne Programmiererfahrung. Sie
  liest ungern, klickt viel, tippt Tippfehler, versteht keine
  englischen Fachwörter und weiß nicht, was ein Traceback ist.
- Eine Schülerin der Oberstufe, die schon etwas Python kann und
  schnell ein Fensterprogramm mit Datenbank bauen will.
- Eine Lehrkraft, die in 20 Minuten Pause eine Aufgabe vorbereiten und
  in der Stunde vorne vorführen will, auf einem Beamer mit 1280 × 800.

## Wonach gesucht wird

1. Erster Kontakt: Startseite, erstes Projekt, erstes Programm starten.
   Wie viele Schritte, wo ist unklar, was als Nächstes kommt?
2. Aufgaben aus dem Unterricht durchspielen, jeweils mit echten
   Klicks und Tasten an einer Kopie eines Beispiels oder einem neuen
   Projekt:
   - ein Konsolenprogramm mit `input()` und `print()` schreiben;
   - ein Fenster mit Knopf, Eingabefeld und Beschriftung bauen, die
     Ereignismethode anlegen, das Programm starten;
   - einen Fehler absichtlich einbauen (Tippfehler im Namen, falsche
     Einrückung, fehlende Klammer, Division durch null, Text statt
     Zahl) und prüfen, ob die Meldung verständlich ist und zur
     richtigen Stelle führt;
   - mit dem Debugger eine Schleife Schritt für Schritt verfolgen;
   - ein Struktogramm und ein Klassendiagramm zeichnen und Code
     daraus erzeugen;
   - eine Datenbanktabelle anlegen und im Formular anzeigen;
   - ein Projekt speichern, schließen, wieder öffnen, als ZIP abgeben.
3. Verständlichkeit: Menübeschriftungen, Tooltips, Meldungen,
   Fachbegriffe, englische Reste, unklare Symbole, Meldungen ohne
   Hinweis, was zu tun ist.
4. Fehlertoleranz: Was passiert bei typischen Fehlgriffen (falsches
   Fenster geschlossen, Datei außerhalb gespeichert, Komponente
   gelöscht, Strg+Z zu oft, Programm zweimal gestartet)? Lässt sich
   alles rückgängig machen oder wird gewarnt?
5. Auffindbarkeit: Funktionen, die es gibt, die aber niemand findet
   (tief versteckt, nur per Tastenkürzel, falsches Menü).
6. Einheitlichkeit: gleiche Dinge heißen und verhalten sich überall
   gleich (Begriffe, Tastenkürzel, Knopfreihenfolge in Dialogen,
   Nachfragen beim Schließen).
7. Hilfe: Passen Handbuch, „Erste Schritte“ und Beispiele zu dem, was
   die Oberfläche zeigt? Findet eine Schülerin dort die Antwort auf
   ihre Frage?
8. Darstellung: kleine Bildschirme (1366 × 768, 1280 × 800),
   Windows-Skalierung 125 % und 150 %, helles und dunkles Design,
   Beamer. Abgeschnittene Texte, überlappende Elemente, zu kleine
   Schrift.

## Wie gearbeitet wird

- An der Oberfläche prüfen, nicht nur am Code: offscreen mit
  `QT_QPA_PLATFORM=offscreen` und `QT_QPA_FONTDIR=C:\Windows\Fonts`,
  Bildschirmfotos über `widget.grab()` (siehe `tools/screenshot.py`),
  für Proben mit dem Hauptfenster
  `uv run pytest -p tests.conftest <datei> --rootdir=.`.
- Jeden Befund belegen: Ablauf in Schritten, was erwartet war, was
  geschah, dazu ein Bildschirmfoto oder die genaue Meldung. Wo es um
  Einschätzung geht (etwa „unverständlich“), die Begründung nennen und
  als Einschätzung kennzeichnen.
- Gewichten nach Häufigkeit im Unterricht: was jede Schülerin in der
  ersten Stunde trifft, wiegt schwerer als ein seltener Weg.
- Nichts im Repository ändern außer `docs/offene_punkte.md`; Proben
  auf Kopien in einem eigenen Ordner unter `%TEMP%`, am Ende löschen.
  Nichts bauen, nichts installieren. Jede Warteschleife und jeder
  Hintergrundlauf bekommt eine Zeitgrenze.

## Abgleich und Eintragen

Erst jetzt `docs/offene_punkte.md` und `docs/erledigte_punkte.md`
lesen, Bekanntes weglassen, einen wieder aufgetauchten erledigten
Fehler als neuen Punkt mit Verweis eintragen. Jeden Befund als eigenen
Punkt unter „Offen“ vor „Zurückgestellt“, mit der nächsten freien
Nummer, Aufbau wie die Vorlage oben in der Datei (Gemeldet: Datum,
Benutzbarkeitsprüfung, Commit).

Reihenfolge: was die erste Stunde verhindert, zuerst; dann was Zeit
kostet; dann Unschönes. Für die Texte gelten die Regeln aus
`AGENTS.md`; `uv run pytest -q tests/test_textstil.py` muss danach
grün sein.

## Abschluss

`docs/offene_punkte.md` committen (nur diese Datei, mit ausdrücklichem
Pfad) und pushen. Tabelle: Nummer, Titel, Art (Einstieg, Verständnis,
Fehlertoleranz, Auffindbarkeit, Einheitlichkeit, Hilfe, Darstellung),
Schwere (hoch, mittel, gering), belegt oder eingeschätzt. Findet sich
nichts, keinen Commit anlegen und das ausdrücklich sagen.
