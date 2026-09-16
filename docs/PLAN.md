# Umsetzungsplan

Konkretisiert konzept-natter.md, Abschnitt 20 (Umsetzungsphasen) und 23
(Voraussetzungen) zu einer Schritt-für-Schritt-Reihenfolge. Wird laufend
aktualisiert; der aktuelle Stand steht immer auch in
`docs/arbeitspakete/M0.md`.

## Warum echte Lazarus-Projekte, keine Screenshots

Für Abschnitt 23.1 werden die **echten Projektdateien** gebraucht
(`.lfm` + `.pas` + `assets/`), keine Screenshots:

- Der `.lfm`-Importer (Abschnitt 15) parst den Text der `.lfm`-Datei
  (`object … end`-Format). Ohne echte `.lfm`-Dateien lässt sich der Parser
  nicht schreiben oder testen.
- Die `.pas`-Dateien liefern die Pascal-Rümpfe, die beim Import als
  Kommentar in die neuen Python-Methoden übernommen werden (Umstiegshilfe).
- Die MVP-Abnahme („Alle Übungsprojekte … lassen sich vollständig in Natter
  umsetzen, debuggen und als `.exe` exportieren“) braucht die Originale als
  Vergleichsbasis.

Screenshots sind trotzdem nützlich, aber zusätzlich: als visuelle Referenz
dafür, wie die Formulare aussehen sollen (für den Design-Prüfer und den
Vergleich „sieht im Designer genauso aus wie zur Laufzeit“). Sie ersetzen
die Quelldateien nicht.

**Bitte kopieren, wenn verfügbar:**

```
referenz/
  lazarus/
    ampel/            Ampel.lpi, u_main.pas, u_main.lfm, u_ampel.pas, assets …
    wuerfelspiel/      … (inkl. Highscore-Datei/-Format, falls vorhanden)
    stringgrid_uebung/
    cookie_clicker/
    tauto/
    infsys_pet/
    gaestebuch/
    kontoverwaltung/   inkl. SQL-Dump der Beispieldatenbank, falls vorhanden
```

Reicht auch unvollständig / nach und nach – wir fangen mit **Ampel** an,
weil es das durchgängige Beispiel im Konzept ist (Abschnitt 4–5) und die
kleinste sinnvolle Menge an Komponenten abdeckt (Form, Button, Shape).
Zusätzlich hilfreich, aber nicht blockierend: Beispiel-CSV-Dateien (auch aus
Excel exportiert) und Beispiel-Diagramme (DIA-Dateien oder Fotos von
Struktogrammen auf Papier).

## Reihenfolge

### Schritt 1 – M0 abschließen (läuft parallel zu Schritt 2)

| Wer | Aufgabe |
|---|---|
| Ich | `prototypes/`-Ordner mit den sieben Wegwerf-Prototypen S1–S7 (Abschnitt 23.3) anlegen: je ein möglichst kleines, eigenständiges Skript pro Prüfung, mit `README.md` je Prüfung (Ausführung, Erfolgskriterium) |
| Du | Prototypen auf dem Windows-Laptop ausführen, Ergebnis (bestanden/durchgefallen) zurückmelden |
| Beide | bei Durchfallen: betroffene Technologie-Entscheidung in `konzept-natter.md` anpassen, bevor M1 beginnt |

Reihenfolge der Prototypen nach Risiko: **S2 (Monaco/Jedi)** und
**S7 (QGraphicsView-Verbindungen)** zuerst, da sie die Konzept-Entscheidung
am ehesten kippen könnten; danach S1, S3, S4, S5; S6 (Signatur) zuletzt, da
er erst für den Export (M8) relevant wird.

### Schritt 2 – Material sammeln

| Wer | Aufgabe |
|---|---|
| Du | Ampel-Projekt aus Lazarus in `referenz/lazarus/ampel/` kopieren (mindestens dieses eine, den Rest nach und nach) |
| Ich | sobald `ampel/` da ist: `.lfm` als erstes Testbeispiel für `schemas/pfm.schema.json` und späteren Importer verwenden |

### Schritt 3 – M1 starten, sobald Ampel vorliegt

Reihenfolge innerhalb M1, jede Teilaufgabe einzeln testbar:

1. `pcl` Eigenschaften-System: `Prop`, `Event`, Typprüfung, Fehler bei
   unbekannter Eigenschaft (Abschnitt 5.0) – ohne Qt, reine Python-Logik,
   zuerst testbar
2. `pcl.Control`/`pcl.Form` als dünne Hülle um `QWidget` mit dem
   Eigenschaften-System verbunden (headless testbar mit
   `QT_QPA_PLATFORM=offscreen`)
3. Erste Komponenten: `Form`, `Button`, `Label`, `Shape` – genug für Ampel
4. `.pfm` → `u_main_design.py`-Generator (Abschnitt 4.3), gegen
   `schemas/pfm.schema.json` und das echte Ampel-`.pfm` getestet
5. Ampel von Hand als Natter-Projekt nachbauen (`main.py`, `u_main.py`,
   `u_ampel.py`) und mit `python main.py` laufen lassen – Abnahmekriterium
   von M1 für dieses eine Projekt
6. Rest von M1: übrige Standard-/Additional-/Common-Komponenten, Theme
   hell/dunkel, Dialoge, Timer, Sound, bis Würfelspiel und
   StringGrid-Übung ebenfalls mit `python main.py` laufen

### Danach

M2–M9 wie im Konzept (Abschnitt 20) beschrieben; wird jeweils vor Beginn in
`docs/arbeitspakete/M<n>.md` konkretisiert, wenn M1 abgeschlossen ist.

## Nächste konkrete Schritte

1. Du: Ampel-Projekt (und wenn einfach möglich, gleich die übrigen sieben)
   nach `referenz/lazarus/` kopieren.
2. Ich: `prototypes/` für S1–S7 anlegen und pushen.
3. Du: Prototypen auf dem Windows-Laptop durchgehen, Ergebnisse melden.
4. Ich: `pcl`-Eigenschaften-System (`Prop`/`Event`) beginnen, sobald Ampel
   vorliegt.
