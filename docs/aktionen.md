# Aktionsregister

Verbindliche Schnittstelle für das Aktionsregister der IDE (`ide/actions/`):
eine Aktion = ein Menüeintrag + ein Werkzeugleisten-Button + ein Tastenkürzel
+ ein Eintrag in der Befehlspalette, nur einmal implementiert. Siehe
konzept-natter.md, Abschnitt 7.2, 7.3, 7.9 und 23.2.

Status: leer. Wird ab M2 gefüllt, ausgehend von der Menüstruktur in
Abschnitt 7.2.

## Vorlage pro Aktion

| Feld | Beschreibung |
|---|---|
| ID | eindeutiger Bezeichner, z. B. `datei.neue_unit` |
| Name (Deutsch) | Anzeigetext im Menü/Tooltip |
| Menüposition | z. B. Datei → Neue Unit |
| Werkzeugleiste | Werkzeugleiste und Position, falls vorhanden |
| Tastenkürzel | z. B. Strg+N |
| Bereich | Editor / Designer / Diagramm-Editor / überall |
| Symbolname | Datei in `icons/` |
