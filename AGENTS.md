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
  docs/bericht.md, Abschnitt 6).
- Jedes Beispielprojekt muss auch ohne IDE mit `python main.py` laufen.
- Die Suite ist in drei Stufen geteilt. Die Marker `hauptfenster`,
  `prozess`, `debugger` und `rundlauf` vergibt `tests/conftest.py`
  aus dem Inhalt der Testdatei; von Hand gesetzt wird keiner.
  - schnell, beim Arbeiten:
    `uv run pytest -m "not drucker and not hauptfenster and not prozess and not debugger and not rundlauf"`
  - mittel, vor dem Push (dazu alle Tests mit Hauptfenster):
    `uv run pytest -m "not drucker and not prozess and not debugger and not rundlauf"`
  - voll, im CI (auf zwei Jobs verteilt) und vor dem Bau
    (`tools/auslieferung_bauen.py`, Schritt 4): `uv run pytest`
  - Jede Stufe läuft mit `-n 8 --dist loadfile` auf mehreren
    Prozessen (`pytest-xdist`) ein Mehrfaches schneller: die schnelle
    Stufe in rund 3 statt 11 Minuten. `loadfile` hält die Tests einer
    Datei in einem Prozess, damit Fixtures mit Modul-Geltung nur
    einmal entstehen.
- Jeder Test hat eine Zeitgrenze von 120 Sekunden (`pytest-timeout`,
  `timeout` in `pyproject.toml`). Wer länger braucht, bekommt eine
  begründete Ausnahme über `@pytest.mark.timeout(…)` oder, für ganze
  Dateien, in `_LANGE_DATEIEN` in `tests/conftest.py`.
- Neue Tests werden je Verhalten parametrisiert, nicht je Eigenschaft
  oder Komponente: ein Fall pro Eigenschaft vervielfacht die Laufzeit,
  ohne ein weiteres Verhalten zu prüfen.
- Kein ganzes Hauptfenster, wo ein Teil reicht: Editor, Dialog,
  Designer oder ein schlankes `QMainWindow` lassen sich allein bauen.
- Jedes Hauptfenster kommt aus der Fixture `hauptfenster` (oder
  `hauptfenster_bauen`, wenn vor dem Bau noch etwas vorbereitet wird
  oder ein zweites Fenster nötig ist). Die Fixture schließt es am Ende
  und beendet laufende Programme; ein nie geschlossenes Hauptfenster
  lässt Uhren und Kindprozesse im Testprozess zurück.
- `HauptFenster.designer_oeffnen()`/`DesignerCanvas(..., pfm_pfad=...)`
  schreiben bei jeder Änderung automatisch in die zugrunde liegende
  `.pfm` zurück. Tests, die etwas platzieren/verschieben/löschen/
  duplizieren, dürfen deshalb **nie** direkt gegen eine eingecheckte
  `beispielprojekte/…/*.pfm` laufen, sondern müssen zuerst in
  `tmp_path` kopiert werden – sonst verändert der Testlauf die
  Beispieldatei im Repository. Geschrieben wird 400 ms nach der
  letzten Änderung einer Folge; wer danach `.pfm`, `_design.py`,
  Komponentenbaum oder Prüfergebnisse liest, ruft vorher
  `canvas.jetzt_schreiben()` auf.
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

## Wissensgraph

Für die Arbeit an Natter liegt in `graphify-out/` ein Wissensgraph des
Codes: Module, Klassen, Funktionen und wer wen aufruft, gewonnen mit
[graphify](https://github.com/safishamsi/graphify) aus der Syntax des
Quelltexts, ohne Sprachmodell und ohne Netz. Er ist ein Werkzeug der
Entwicklung, kein Teil der IDE, und wird nicht eingecheckt.

- Wer verstehen will, wie Teile zusammenhängen, fragt zuerst den
  Graphen, statt Dateien der Reihe nach zu lesen:
  `graphify query "<Frage>"`, `graphify path "<A>" "<B>"`,
  `graphify explain "<Name>"`, `graphify affected "<Name>"` (wer
  von einer Änderung betroffen ist). Die Antworten sind ein kleiner
  Ausschnitt statt ganzer Dateien. `graphify-out/GRAPH_REPORT.md`
  nur für den Überblick über die ganze Architektur.
- Zum Ändern einer bestimmten Stelle wird die Datei weiterhin selbst
  gelesen - der Graph sagt, wo etwas steht, nicht, was genau dort
  steht.
- Aktuell hält ihn `tools/graph_aktualisieren.sh`, ohne dass jemand
  daran denken muss: am Ende jeder Antwort von Claude Code (Hook
  `Stop` in `.claude/settings.json`) und nach jedem Commit, Checkout
  und Merge (Git-Hooks), also auch nach dem Bau, dessen Schritt 12
  die Versionsnummer committet. Das Skript vergleicht einen
  Fingerabdruck aller Python-Dateien und kehrt ohne Änderung nach
  rund 0,3 Sekunden zurück; nur bei einer Änderung rechnet graphify
  im Hintergrund neu (gut 10 Sekunden, nie zwei Läufe zugleich). Das
  Protokoll des letzten Laufs steht in `graphify-out/letzter_lauf.log`.
- Einrichten auf einem neuen Rechner:
  `uv tool install graphifyy`, `graphify update .` und
  `bash tools/graph_aktualisieren.sh --einrichten` für die Git-Hooks.
  Fehlt graphify oder `graphify-out/`, etwa in den Arbeitsbäumen unter
  `.claude/worktrees`, tun die Hooks nichts.
- Der Graph enthält nur Code und ohne `tests/` (`.graphifyignore`):
  die Tests sind zwei Drittel aller Python-Dateien und verdrängten in
  jeder Antwort den Code, nach dem gefragt war. Dokumente, Hilfeseiten,
  `.pfm`-Dateien und Tests werden wie bisher durchsucht.

## Schnittstellen zuerst

- `schemas/*.schema.json`, das `Prop`/`Event`-System, das Aktionsregister und
  DAP-Schnittstellen sind die verbindlichen Schnittstellen zwischen den
  Teilen von Natter (siehe `docs/bericht.md`, Abschnitt 2.3). Änderungen
  daran betreffen mehrere Teile zugleich und werden entsprechend
  sorgfältig geprüft.
- Neue oder geänderte Dateiformate erhalten eine Versionsnummer im Format
  (`pfm/1`, `pdiag/1`, `natter-project/1`) und ein aktualisiertes Schema.

## Definition of Done

Ein Punkt aus `docs/offene_punkte.md` gilt als erledigt, wenn:

1. das unter „Zu tun" genannte Kriterium erfüllt ist,
2. zugehörige Tests grün sind (`ruff check`, `pytest`),
3. betroffene Schemas/Dokumente (`docs/komponenten.md`, `docs/bericht.md`,
   `docs/fehlerkatalog.yaml`, `schemas/*.json`) aktualisiert sind,
4. keine erzeugten Dateien von Hand geändert wurden,
5. alle sichtbaren Texte Deutsch sind.

## Auslieferung

Eine neue `Natter-Setup.exe` entsteht in einem Befehl, nicht in fünf:

```powershell
uv run python -m tools.auslieferung_bauen --version 0.3.6
```

Das Skript prüft nach jedem der zwölf Schritte, ob das Ergebnis stimmt,
und bricht ab, statt eine kaputte Auslieferung fertigzubauen. Die
Begründung steht in `docs/bericht.md`, Abschnitt 7.1; den Ablauf
drumherum (wann gebaut werden darf, welche
Versionsnummer die nächste ist, was hinterher dokumentiert wird)
beschreibt `.claude/commands/auslieferung.md`.

Zwei Dinge gelten dabei unabhängig vom Werkzeug:

- **Ein grünes Testprotokoll belegt nicht, dass die Auslieferung
  funktioniert.** Getestet wird der Entwicklungsbaum, ausgeliefert wird
  `dist\Natter`. Die beiden letzten Auslieferungsfehler sind genau
  dazwischen entstanden – deshalb die Rauchprobe in Schritt 6.
- **Die Versionsnummer gehört zum Update dazu.** Sie steht an drei
  Stellen: in `pyproject.toml`, in `tools/natter.iss` (`AppVersion`,
  daran erkennt Windows eine neue Fassung) und als `VERSION` in
  `ide/main.py` (Startbild). Mit `--version` setzt das Skript alle drei
  selbst; ohne prüft es in Schritt 2, dass sie übereinstimmen. Die
  Zahl im Beispiel oben ist die nächste nach 0.3.5.

## Lizenzen von Abhängigkeiten

Nur Abhängigkeiten mit freizügigen Lizenzen oder LGPL, kein PyQt, keine
GPL-only-Qt-Module (z. B. Qt Charts). Einzige ausdrückliche Ausnahme
ist PyInstaller (GPL-2.0 mit Ausnahme für erzeugte Programme), das für
„Als Exe exportieren" mitgeliefert wird. Der Bau prüft das und bricht
bei jedem anderen GPL-Paket ab (`LIZENZ_AUSNAHMEN` in
`tools/ide_paketieren.py`). Siehe docs/bericht.md, Abschnitt 5.
