# AGENTS.md

Regeln für alle Beiträge zu Natter – verbindlich für Menschen und KI-Agenten,
die an der Entwicklung der IDE mitarbeiten. KI-Agenten werden ausschließlich
bei der Entwicklung von Natter eingesetzt, nicht in der fertigen IDE selbst
(siehe README.md, Abschnitt 1).

## Sprache

- Alle sichtbaren Texte der IDE und der `pcl`-Laufzeit (Menüs, Meldungen,
  Hilfetexte, Fehlermeldungen) sind Deutsch.
- Python-Bezeichner der Bibliothek (`caption`, `on_click`, Dateinamen,
  Commit-Nachrichten, Code-Kommentare) sind Englisch bzw. Projektsprache
  Deutsch für Dokumentation – Code selbst folgt üblichem Python-Namensstil,
  keine Pascal-Aliasse (siehe Abschnitt 5.1).

## Python

- Python 3.13, Typannotationen an öffentlichen Funktionen/Methoden und
  `Prop`/`Event`-Definitionen.
- Lint über Ruff (`ruff check`), Konfiguration in `pyproject.toml`. Das ist
  das verbindliche Tor, und es muss sauber durchlaufen.
- **`ruff format` wird bewusst nicht angewandt.** Der Quelltext ist von Hand
  auf rund 72 Zeichen umbrochen – eine Breite, die sich neben dem
  Objektinspektor noch lesen lässt und zu den ausführlichen deutschen
  Kommentaren passt, die in diesem Projekt begründen, warum etwas so ist.
  `ruff format` würde sie auf die konfigurierte `line-length = 100`
  zusammenziehen und dabei rund ein Drittel aller Dateien anfassen, ohne
  dass sich am Verhalten etwas ändert. Neuer Code folgt dem Umbruch des
  umgebenden Codes.
- Keine neue Syntax, kein Präprozessor: Schülercode und `pcl` sind normales
  Python (Abschnitt 4.0).

## Tests

- pytest. GUI-Tests (`pcl`, Designer, Diagramm-Editor) headless mit
  `QT_QPA_PLATFORM=offscreen` (pytest-qt), sobald PySide6-Code entsteht.
- Tests werden zuerst gegen virtuelle Abbildungen geschrieben (headless,
  In-Memory-SQLite …), erst zuletzt gegen echte Systeme (siehe
  docs/entwicklung.md, Abschnitt 19).
- Jedes Beispielprojekt muss auch ohne IDE mit `python main.py` laufen.
- `HauptFenster.designer_oeffnen()`/`DesignerCanvas(..., pfm_pfad=...)`
  schreiben bei jeder Änderung automatisch in die zugrunde liegende
  `.pfm` zurück. Tests, die etwas platzieren/verschieben/löschen/
  duplizieren, dürfen deshalb **nie** direkt gegen eine eingecheckte
  `beispielprojekte/…/*.pfm` laufen, sondern müssen zuerst in
  `tmp_path` kopiert werden – sonst verändert der Testlauf die
  Beispieldatei im Repository.
- `QT_QPA_PLATFORM=offscreen` findet unter Windows von sich aus keine
  Schriftarten (`QFontDatabase.families()` ist leer, Text erscheint als
  Kästchen/Tofu bzw. mit falschen Glyphen). Für alles, was tatsächlich
  gerendertes Pixelbild braucht (`widget.grab()`, Screenshots, künftige
  Bildvergleichstests), zusätzlich `QT_QPA_FONTDIR=C:\Windows\Fonts`
  setzen und eine konkrete Schriftart wie `QApplication.setFont(QFont(
  "Segoe UI", 9))` setzen – ohne Letzteres greift eine zufällige
  Ersatzschrift mit fehlerhaften Glyphen für einzelne Buchstaben. Siehe
  `tools/screenshot.py`.

## Sichtbare Texte und Kommentare

- Texte sprechen niemanden direkt an - weder mit „du" noch mit „Sie".
  Das gilt für Meldungen und Dialoge, für die Hilfeseiten, für die
  Projektvorlagen und für die Textseiten des Installers. Formuliert
  wird unpersönlich, wie in deutscher Software üblich: „Die Datei lässt
  sich nicht öffnen", „Zum Fortfahren die Bedingungen annehmen".
  Ausgenommen sind die Ausgaben der Beispielprogramme selbst: dort
  spricht das Programm einer Schülerin mit seinem Benutzer, und ein
  Begrüßungsprogramm darf „Wie heißt du?" fragen.
- Kommentare und Docstrings tragen keine Markdown-Hervorhebung
  (`**so**`) und keine Zuschreibungs-Etiketten der Form
  „Nutzer-Feedback September 2026:". Die Begründung selbst ist wertvoll
  und gehört in den Kommentar; das Etikett davor nicht.
- Geprüft wird beides in `tests/test_textstil.py`.
- Natter erklärt sich aus sich heraus. Kein Text, kein Kommentar und
  keine Hilfeseite verweist auf Lazarus, Delphi oder die LCL - ein
  Vergleich wie „wie Lazarus `TLabel.Color`“ sagt jemandem, der Lazarus
  nie benutzt hat, nichts. Die Eigenschaft wird stattdessen aus sich
  heraus beschrieben. Einzige Ausnahme ist `ide/import_lfm/`: dort ist
  das fremde Dateiformat der Gegenstand des Codes.

## Generierte Dateien

- Dateien, die als automatisch erzeugt gekennzeichnet sind (z. B.
  `u_*_design.py`, Kopfzeile „Automatisch erzeugt aus … – nicht bearbeiten“)
  werden nie von Hand geändert. Änderungen erfolgen ausschließlich über den
  Generator (`ide/codegen/`).

## Schnittstellen zuerst

- `schemas/*.schema.json`, das `Prop`/`Event`-System, das Aktionsregister und
  DAP-Schnittstellen sind die verbindlichen Schnittstellen zwischen
  Arbeitspaketen (siehe Abschnitt 23.2). Änderungen daran betreffen mehrere
  Arbeitspakete und werden entsprechend sorgfältig geprüft.
- Neue oder geänderte Dateiformate erhalten eine Versionsnummer im Format
  (`pfm/1`, `pdiag/1`, `natter-project/1`) und ein aktualisiertes Schema.

## Definition of Done je Arbeitspaket

Ein Arbeitspaket (siehe `docs/arbeitspakete/`) gilt als abgeschlossen, wenn:

1. das im Arbeitspaket genannte Abnahmekriterium erfüllt ist,
2. zugehörige Tests grün sind (`ruff check`, `pytest`),
3. betroffene Schemas/Dokumente (`docs/komponenten.md`, `docs/aktionen.md`,
   `docs/fehlerkatalog.yaml`, `schemas/*.json`) aktualisiert sind,
4. keine erzeugten Dateien von Hand geändert wurden,
5. alle sichtbaren Texte Deutsch sind.

## Auslieferung

Eine neue `Natter-Setup.exe` entsteht in einem Befehl, nicht in fünf:

```powershell
uv run python -m tools.auslieferung_bauen --version 0.2.0
```

Das Skript prüft nach jedem der zehn Schritte, ob das Ergebnis stimmt,
und bricht ab, statt eine kaputte Auslieferung fertigzubauen. Die
Begründung steht in `docs/arbeitspakete/M13.md`, Abschnitt „Der Bau in
einem Befehl"; den Ablauf drumherum (wann gebaut werden darf, welche
Versionsnummer die nächste ist, was hinterher dokumentiert wird)
beschreibt `.claude/commands/auslieferung.md`.

Zwei Dinge gelten dabei unabhängig vom Werkzeug:

- **Ein grünes Testprotokoll belegt nicht, dass die Auslieferung
  funktioniert.** Getestet wird der Entwicklungsbaum, ausgeliefert wird
  `dist\Natter`. Die beiden letzten Auslieferungsfehler sind genau
  dazwischen entstanden – deshalb die Rauchprobe in Schritt 6.
- **Die Versionsnummer gehört zum Update dazu.** Sie steht in
  `pyproject.toml` und in `tools/natter.iss` und muss in beiden gleich
  sein; Windows erkennt eine neue Fassung an `AppVersion`.

## Lizenzen von Abhängigkeiten

Nur Abhängigkeiten mit freizügigen Lizenzen oder LGPL, kein PyQt, keine
GPL-only-Qt-Module (z. B. Qt Charts). Siehe docs/entwicklung.md, Abschnitt 17.7.
