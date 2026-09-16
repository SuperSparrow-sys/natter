# Prototypen S1–S7 (Phase M0)

Wegwerf-Prototypen für die technischen Machbarkeitsprüfungen aus
konzept-natter.md, Abschnitt 23.3. Jeder Ordner ist eigenständig, klein und
nicht Teil von `pcl`/`ide` – Code hier wird nicht weiterverwendet, nur das
Ergebnis (bestanden/durchgefallen, ggf. Anpassung der Technologie-Entscheidung
in `konzept-natter.md`).

Reihenfolge nach Risiko: **S2, S7** zuerst (könnten die Konzept-Entscheidung
kippen), dann S1, S3, S4, S5, zuletzt S6 (erst für M8 relevant). Siehe
`docs/PLAN.md`.

Voraussetzung für S2–S4 und S7 (im normalen Entwicklungs-venv, reicht für
diese vier): `uv sync --group prototypes`. S1 und S5 brauchen zusätzlich eine
portable Python-Distribution bzw. einen PyInstaller-Build außerhalb dieses
venv – siehe die jeweiligen `README.md`.

| Nr. | Ordner | Prüft |
|---|---|---|
| S1 | `s1_portables_python/` | portables Python 3.13 + PySide6/WebEngine aus verschiebbarem Ordner |
| S2 | `s2_monaco_jedi/` | Monaco in `QWebEngineView` + Jedi-Vervollständigung, offline |
| S3 | `s3_debugpy/` | debugpy für GUI-Prozess und Konsolenfenster |
| S4 | `s4_getrennte_paketordner/` | getrennte Paketordner statt venv |
| S5 | `s5_pyinstaller/` | PyInstaller-Export aus dem portablen Python |
| S6 | `s6_signatur/` | Authenticode-Signatur + signiertes Prüfsummen-Manifest |
| S7 | `s7_qgraphicsview/` | andockende, rechtwinklige Verbindungen in `QGraphicsView` |
