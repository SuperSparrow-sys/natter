# Natter

Eine Lazarus-artige IDE für Python – für Schülerinnen und Schüler, die von
Pascal/Lazarus auf Python umsteigen. Zielplattform: Windows.

Das vollständige Konzept steht in [`konzept-natter.md`](konzept-natter.md):
Ziele und Abgrenzung, Technologie-Entscheidungen, Architektur,
Komponentenbibliothek `pcl`, IDE-Aufbau, Debugger, Diagramm-Editor,
Repository-Struktur, Teststrategie und Umsetzungsphasen (M0–M9).

## Status

M0, M1 und M2 sind funktional abgeschlossen (Repository, `pcl`-Laufzeit
mit 13 Komponenten, IDE-Grundgerüst mit Projekt öffnen/anlegen/starten),
M3 (Designer, Objektinspektor) läuft. Der vollständige, laufend
aktualisierte Ablaufplan mit Checkliste steht in
[`docs/PLAN.md`](docs/PLAN.md) – dort auch immer der aktuelle Punkt
unter „Wo wir stehen“.

## Die IDE starten

Auf einem Windows-Rechner mit Bildschirm (nicht headless):

```
uv sync --group dev
uv run python -m ide
```

Zum Ausprobieren: „Projekt → Projekt öffnen …“ und z. B.
`beispielprojekte/Ampel/ampel.natter` wählen, dann „Start → Starten ohne
Debugger“ (Strg+F5) – die Ampel öffnet sich als eigenes Fenster.

## Aufbau des Repositories

| Ordner | Inhalt |
|---|---|
| `pcl/` | Python Component Library – Laufzeit der Komponenten, läuft ohne IDE |
| `ide/` | die Entwicklungsumgebung selbst |
| `schemas/` | JSON-Schemas der Dateiformate (`.pfm`, `.natter`, `.pdiag`) |
| `design/` | Design-Tokens und Design-Referenz |
| `docs/` | Komponenten-Referenz, Aktionsregister, Fehlerkatalog, Arbeitspakete |
| `tests/` | Tests |

Die vollständige Zielstruktur steht in Abschnitt 18 des Konzepts; sie wird
schrittweise entlang der Arbeitspakete aufgebaut.

## Entwicklung

Voraussetzung: Python 3.13 und [uv](https://docs.astral.sh/uv/).

```
uv sync --group dev
uv run ruff check .
uv run pytest
```

## Lizenz

Privates Projekt, siehe [`LICENSE`](LICENSE): Nutzung erlaubt, Weitergabe
nicht erlaubt. Beitragsregeln stehen in [`AGENTS.md`](AGENTS.md).
