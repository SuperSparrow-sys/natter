# S7 – QGraphicsView: andockende, rechtwinklige Verbindung

Prüft: Zwei Formen (Rechtecke) mit einer rechtwinkligen Verbindungslinie, die
beim Verschieben einer Form ohne Flackern folgt. Grundlage für den
Diagramm-Editor (Abschnitt 13).

## Ausführen

```
uv sync --group prototypes
uv run python prototypes/s7_qgraphicsview/app.py
```

## Bedienung

Beide Rechtecke sind per Maus verschiebbar (`ItemIsMovable`). Die Linie
verbindet die rechte Kante des linken und die linke Kante des rechten
Rechtecks rechtwinklig (erst horizontal zur Mitte, dann vertikal, dann
horizontal zum Ziel) und muss beim Ziehen sofort und ohne sichtbares
Flackern folgen.

## Erfolgskriterium

- Verbindung folgt beim Verschieben beider Formen ohne Flackern und ohne
  spürbare Verzögerung.
- Kein manuelles Neuzeichnen nötig (kein Blinken beim Loslassen).

Ergebnis (bitte eintragen): **offen**
