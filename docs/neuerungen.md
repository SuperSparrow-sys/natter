# Neuerungen

Was jede Fassung von Natter Neues bringt, aus Sicht des Unterrichts.
Der Abschnitt einer Fassung erscheint beim Veröffentlichen als Text
unter dem GitHub-Release (`tools/veroeffentlichen.py`); der Bau bricht
ab, wenn er fehlt. Kurz halten: nur, was im Unterricht auffällt, keine
Punktnummern und keine Einzelkorrekturen.

## 0.4.4

- Struktogramme werden zuverlässiger in Python übersetzt, auch ≠, ≤, ≥,
  mod, div, und/oder/nicht und Eingaben, die Zahl oder Text sein
  können. Typische Aufgaben wie Zahlenraten oder Maximum laufen ohne
  Nacharbeit.
- Debugger: F9 setzt Haltepunkte, F5 setzt fort, die aktuelle Zeile ist
  gelb hinterlegt. Haltepunkte bleiben beim Bearbeiten an ihrer Stelle.
- Tests als einfache Funktionen mit `assert` laufen im Test-Explorer,
  mit deutschen Meldungen samt Zeile.
- Neu: „Datei → Speichern unter …“, etwa für ausgeteilte Dateien in
  schreibgeschützten Ordnern.
- Neue Ereignisse `on_mouse_enter` und `on_mouse_leave`.
- Handbuch und „Erste Schritte“ überarbeitet: Schritt für Schritt zum
  ersten Knopf, und welcher Doppelklick welche Methode anlegt.
- Hilfeseiten zeigen Code farbig und in der Schrift des Editors; die
  Schriftgröße lässt sich mit Strg+Mausrad einstellen.
- Fehler behoben, die Daten kosten oder Programme abbrechen konnten.

## 0.4.3

- F1 öffnet die passende Hilfeseite, die Hilfe ist durchsuchbar, Menüs
  öffnen sich mit Alt und Buchstabe.
- Das Datenbank-Panel führt SQL-Skripte mit mehreren Anweisungen aus.
- Häufige Laufzeitfehler werden auf Deutsch erklärt, ein vergessenes
  `self.` wird als Ursache genannt.
- Haltepunkte bleiben über Projektwechsel und Neustart erhalten.

## 0.4.2

- Gestartete Programme haben in Fenster und Taskleiste ein eigenes
  Symbol.

## 0.4.1

- „Projekt öffnen …“ beginnt im Ordner der eigenen Projekte.
- Doppelklick im Projekt-Explorer öffnet eine Unit zuverlässig.

## 0.4.0

Erste veröffentlichte Fassung. Natter ist eine Entwicklungsumgebung für
Python im Informatikunterricht, vollständig auf Deutsch: Oberflächen
entstehen im Formular-Designer, dazu kommen Debugger, Diagramm-Editor
für UML, Struktogramme und Entscheidungstabellen mit Code-Erzeugung,
Test-Explorer, SQLite-Datenbanken, Prüfungsmodus, Austeilen und
Einsammeln von Aufgaben sowie der Export als Windows-Programm.
