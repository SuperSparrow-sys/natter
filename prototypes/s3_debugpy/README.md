# S3 – debugpy: GUI-Prozess und Konsolenfenster

Prüft: Breakpoint hält an, Variablen lesbar, `input()` im eigenen
Konsolenfenster funktioniert (Abschnitt 7.8, 23.3).

Dieser Prototyp prüft nur, ob debugpy in beiden Ausführungsarten
grundsätzlich funktioniert – der eigentliche DAP-Client der IDE entsteht
erst in M4. Am einfachsten mit VS Code als DAP-Frontend.

## Voraussetzung

```
uv sync --group prototypes
```

## a) Konsolenprogramm im eigenen Konsolenfenster

In einer **eigenen** `cmd`- oder Windows-Terminal-Instanz (wichtig: eigenes
Fenster, nicht die IDE-Konsole):

```
start cmd /k uv run python -m debugpy --listen 5678 --wait-for-client prototypes\s3_debugpy\konsolenprogramm.py
```

Dann in VS Code: „Ausführen → Konfiguration hinzufügen → Python Debugger:
Remote Attach“, Host `localhost`, Port `5678`, Breakpoint in
`konsolenprogramm.py` auf die markierte Zeile setzen, attachen.

**Prüfen:** Breakpoint hält an, `summe`/`anzahl` sind im Variablen-Fenster
lesbar, nach „Fortsetzen“ funktioniert die nächste `input()`-Abfrage im
Konsolenfenster normal weiter.

## b) GUI-Programm als eigener Prozess

```
uv run python -m debugpy --listen 5678 --wait-for-client prototypes/s3_debugpy/gui_programm.py
```

Mit VS Code wie oben attachen, Breakpoint auf die markierte Zeile in
`gui_programm.py` setzen, im Fenster auf „Klicken“ klicken.

**Prüfen:** Breakpoint hält an, `self.klicks` ist lesbar, das Fenster bleibt
als eigenständiges Fenster mit eigenem Taskleisten-Eintrag erhalten.

## Erfolgskriterium

- Beide Fälle: Breakpoint hält zuverlässig an, Variablen lesbar.
- a) `input()` funktioniert im eigenen Konsolenfenster vor und nach dem
  Breakpoint.
- b) Programmfenster bleibt eigenständig, IDE (hier: das Terminal) bleibt
  bedienbar.

Ergebnis (bitte eintragen): **offen**
