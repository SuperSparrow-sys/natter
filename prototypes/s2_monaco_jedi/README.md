# S2 – Monaco in QWebEngineView mit Jedi, offline

Prüft: Vervollständigung, Fehlermarkierung und Theme-Wechsel funktionieren
ohne Internetverbindung (Abschnitt 23.3). Dies ist der riskanteste
Prototyp – fällt er durch, wird QScintilla als Ausweichlösung geprüft
(Abschnitt 21).

## 1. Monaco besorgen (einmalig, danach offline nutzbar)

Monaco selbst ist nicht Teil dieses Repositorys (zu groß, per Lizenz separat
gebündelt, siehe Abschnitt 17.7). Einmalig herunterladen und den Ordner
`vs` hierher kopieren:

```
npm pack monaco-editor
tar -xf monaco-editor-*.tgz package/min/vs -O   # oder Archiv normal entpacken
```

Ergebnis: `prototypes/s2_monaco_jedi/monaco/vs/loader.js` muss existieren.
(`monaco/` ist in `.gitignore` und wird nicht committet.)

## 2. Ausführen

```
uv sync --group prototypes
uv run python prototypes/s2_monaco_jedi/app.py
```

Es öffnet sich ein Fenster mit Monaco. **WLAN/Kabel dabei ausstecken**, um
„offline“ wirklich zu prüfen.

## Prüfen

- Vervollständigung: im Editor eine neue Zeile `gru` tippen und
  Strg+Leertaste drücken – Vorschlag `gruss` (von Jedi über die
  QWebChannel-Brücke) muss erscheinen, auch ohne Internet.
- Theme-Wechsel: Knöpfe „Hell“/„Dunkel“ oben rechts wechseln das Editor-Theme
  sofort.
- Fehlermarkierung ist in diesem Prototyp nur als Brücke (`fehler_markieren`
  in `bridge.py`) vorbereitet, aber noch nicht ins Editor-Markierungs-API
  verdrahtet – für S2 reicht der Nachweis, dass Jedi-Daten offline über
  `QWebChannel` beim JavaScript ankommen.

## Erfolgskriterium

- Vervollständigung und Theme-Wechsel funktionieren ohne Internetverbindung.
- Keine Netzwerkfehler/leere Seite in der Konsolenausgabe von
  `QWebEngineView`.

Ergebnis (bitte eintragen): **offen**
