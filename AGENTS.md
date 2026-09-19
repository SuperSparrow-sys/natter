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

## Lizenzen von Abhängigkeiten

Nur Abhängigkeiten mit freizügigen Lizenzen oder LGPL, kein PyQt, keine
GPL-only-Qt-Module (z. B. Qt Charts). Siehe docs/entwicklung.md, Abschnitt 17.7.
