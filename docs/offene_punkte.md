# Offene Punkte

Gefundene Fehler und ungeklärte Fragen, die noch nicht behoben sind.
Jeder Eintrag nennt, was beobachtet wurde, was davon nachgewiesen ist
und was noch zu prüfen bleibt.

Erledigte Punkte werden hier gestrichen, nicht abgehakt — was drinsteht,
ist offen.

---

## 1. Stylesheets kaskadieren auf Kinder — auch auf Dialoge

**Beobachtet:** Im Diagramm-Editor öffnet das Feld „Füllung" den
Farbauswahl-Dialog. Dort hat jede Beschriftung und jeder Knopf einen
grauen Rahmen, die Texte wirken ausgegraut, und der Dialog sieht aus,
als wäre er abgeschaltet. Beim Feld „Linie" genauso — es ist dieselbe
Klasse.

**Ursache — nachgewiesen und nachgestellt.**
`ide/diagramm/eigenschaften.py`, Zeile 56:

```python
gewaehlt = QColorDialog.getColor(QColor(self.farbe or "#ffffff"), self)
```

Als Elternteil wird `self` übergeben, also der Farbknopf. Auf dem steht
vier Zeilen darüber:

```python
self.setStyleSheet(f"background-color: {farbe}; border: 1px solid #808080;")
```

Das sind **Anweisungen ohne Selektor**. Qt wendet sie auf das Widget
*und auf jedes Kind* an, und ein Dialog gilt als Kind seines
Elternteils. Jedes Label und jeder Knopf im Dialog bekommt dadurch
`border: 1px solid #808080` und den weißen Hintergrund.

Nachgestellt mit einem `QLabel`, das dieselbe Zeile trägt, und einem
`QColorDialog` darunter: das Ergebnis deckt sich mit dem
Bildschirmfoto.

**Die allgemeine Regel dahinter:** eine Regel *mit* Selektor
(`QToolButton { … }`) trifft nur passende Widgets und ist ungefährlich.
Eine Regel *ohne* Selektor (`background-color: …;`) trifft alles
darunter. `pcl/components/standard.py` kennt das bereits und schreibt
beim `Panel` ausdrücklich `QFrame#… { … }` mit der Begründung im
Kommentar — nur an den übrigen Stellen ist es nicht angewandt.

**Naheliegende Behebung:** als Elternteil `self.window()` übergeben.
Dann hängt der Dialog am Fenster und erbt nur dessen Stylesheet.

**Noch zu prüfen:**

- Ob die Farbe danach weiterhin richtig übernommen wird, und ob der
  Dialog mittig auf dem richtigen Bildschirm erscheint.
- Ob die `border`-Zeile auf dem Farbknopf überhaupt nötig ist, oder ob
  ein Rahmen über `setFrameShape` dasselbe ohne Stylesheet leistet —
  dann verschwindet die Ursache statt nur ihre Wirkung.
- Ob ein Test das festhalten kann: etwa, dass kein `setStyleSheet` ohne
  Selektor auf einem Widget steht, das einen Dialog öffnet.

---

## 2. Welche Stellen geprüft sind und welche nicht

**Geprüft und in Ordnung** — diese Stylesheets tragen einen Selektor
und kaskadieren deshalb nicht schädlich:

| Datei | Zeile | Warum unbedenklich |
|---|---|---|
| `ide/shell/explorer.py` | 179 | `QToolButton { … }`, trifft kein Menü darunter |
| `pcl/components/standard.py` | 486 | `Panel` schreibt `QFrame#… { … }` |
| `ide/shell/hauptfenster.py` | 295, 2023 | gilt fürs ganze Fenster, so gewollt |
| `ide/diagramm/fenster.py` | 199 | dasselbe fürs Diagrammfenster |

**Ohne Selektor, aber ohne Kinder** — heute harmlos, beim nächsten
Umbau nicht mehr:

| Datei | Zeile | Widget |
|---|---|---|
| `ide/shell/hauptfenster.py` | 609 | Prüfungsmodus-Anzeige |
| `ide/ladeanzeige.py` | 86 | Standzeile im Startbild |
| `ide/shell/startbild.py` | 181, 194, 236, 242 | Überschriften und Einträge |
| `ide/designer/canvas.py` | 529, 572 | Auswahlrahmen und Anfasser |
| `pcl/components/standard.py` | 116, 156 | `Label` und `Edit` |

**Noch nicht angesehen** — acht Dialoge, die ein Widget als Elternteil
bekommen. Beim Hauptfenster ist das gewollt; die übrigen sind
ungeprüft:

| Datei | Zeile | Dialog |
|---|---|---|
| `ide/database/panel.py` | 143, 209, 253, 272 | Datei wählen, CSV und SQL exportieren |
| `ide/project/neu_dialog.py` | 74 | Übergeordneter Ordner |
| `ide/inspector/eigenschaften_tabelle.py` | 282, 296 | Zeileneditor und Menü-Editor |
| `ide/diagramm/canvas.py` | 786, 828 | Formeditor und Klassendialog |

**Noch zu prüfen:** jeden dieser Dialoge einmal öffnen und ansehen.
Der Fehler ist nur am Bild zu erkennen — kein Test schlägt an, und die
Dialoge funktionieren ja.

---

## 3. Die Druckvorschau zeigt das Diagramm winzig und mit zerlaufener Schrift

**Beobachtet:** „Datei → Drucken …" im Diagramm-Editor zeigt eine
Vorschau, in der fast nichts zu sehen ist: eine große graue Fläche, die
Zoomanzeige steht auf „0,0 %", und vom Diagramm ist nur ein Fleck
übrig.

**Nachgestellt** mit `konto_klassen.pdiag` und einem
`QPrintPreviewWidget`. Es sind **zwei** Fehler, die zusammenfallen.

### 3a. Das Diagramm wird 3,7 cm breit gedruckt statt 20 cm

`ide/diagramm/export.py`, Zeile 312:

```python
faktor = min(1.0, breite / bereich.width(), hoehe / bereich.height())
```

Die `1.0` bedeutet „verkleinert nur, vergrößert nie". Das ist für den
Bildschirm gedacht, wo ein Punkt ein Punkt ist. Ein Drucker rechnet
aber in 600 dpi:

| | |
|---|---|
| Inhalt des Diagramms | 884 × 456 Punkte |
| Druckseite | 4818 × 6876 Punkte bei 600 dpi |
| Faktor mit der Grenze | **1,00** → 18 % der Seitenbreite, **3,7 cm** |
| Faktor ohne die Grenze | 5,45 → 100 % der Seitenbreite, **20,4 cm** |

Streicht man die Grenze, füllt das Diagramm die Seite — nachgestellt
und angesehen.

### 3b. Die Schrift skaliert nicht mit

Auch mit richtiger Geometrie bleibt der Text unbrauchbar: Namen laufen
aus ihren Kästen, Zeilen überlagern sich, von einer Notiz ist nur das
erste Wort zu sehen.

Der Grund: die Schriften werden in **Punkt** angelegt
(`QFont(_SCHRIFT, groesse)` in `zeichnen.py`, `struktogramm.py`,
`tabelle.py`). Qt rechnet Punkt über die Auflösung des Ausgabegeräts in
Gerätepunkte um — bei 600 dpi also 6,25-mal so groß wie bei den 96 dpi
des Bildschirms. Der Maßstab des Malers vergrößert danach noch einmal.
Die Kästen wachsen mit dem einen Faktor, die Schrift mit beiden.

**Der Vergleich, der es zeigt:** der PDF-Export hat dasselbe Problem
nicht, und zwar weil `als_pdf` in `export.py` ausdrücklich auf 96 dpi
stellt — mit dem Kommentar „dann entspricht eine PDF-Einheit genau
einem Pixel der Zeichenfläche". Beim Drucken fehlt dieser Schritt.

**Richtung für die Behebung:** beim Drucken denselben Weg gehen wie
beim PDF — das Koordinatensystem vor dem Zeichnen auf 96 dpi bringen
(`maler.scale(96 / drucker.resolution(), …)`) und erst darauf den
Anpassungsfaktor rechnen. Dann skalieren Geometrie und Schrift
gemeinsam, und die Auflösung des Druckers bleibt trotzdem erhalten.

**Noch zu prüfen:**

- Ob die Vorschau danach auch einen sinnvollen Zoomwert anzeigt; „0,0 %"
  ist noch nicht erklärt und könnte ein dritter, eigener Punkt sein.
- Struktogramm und Entscheidungstabelle gehen durch dieselbe Funktion
  und sind noch nicht gedruckt worden.
- Querformat, denn dort greift der Faktor über die andere Kante.
- Ob ein Test das festhalten kann, etwa: auf eine Seite gezeichnet muss
  der belegte Bereich mindestens die halbe Seitenbreite einnehmen.
- Die PNG- und SVG-Exporte sehen richtig aus (in dieser Sitzung
  angesehen), das PDF wurde nur auf seine Dateigröße geprüft — einmal
  öffnen und ansehen.

---

## 4. Die Lizenzseite des Installers ist nie angesehen worden

**Beobachtet:** Die Textdateien `tools/lizenz_vorlagen/*.txt` sind
geprüft — Umlaute, Byte-Order-Mark, Inhalt. Wie sie im Installer
**aussehen**, ist nie jemand nachgegangen.

**Warum nicht:** Die Abnahme läuft über eine stille Installation
(`/VERYSILENT`), bei der keine Seite erscheint. Ein Bildschirmfoto des
Assistenten braucht eine angemeldete, interaktive Sitzung; die stand
bei den bisherigen Durchgängen nicht zur Verfügung.

**Noch zu prüfen:** Den Installer einmal von Hand durchklicken und
nachsehen, ob Lizenz- und Hinweisseite vollständig, mit richtigen
Umlauten und ohne abgeschnittene Zeilen erscheinen.

---

## 5. Welcher Test in den Dokumente-Ordner schreibt, ist unbekannt

**Beobachtet:** Nach einigen Testläufen standen 27 Ordner im
Projektstamm — `01_Begruessung`, `01_Begruessung 2`, `… 3` für alle
neun Beispiele. Sie entstehen, weil `beispiel_kopieren` seine
Arbeitskopie unter `Dokumente\Natter` ablegt und das Repository auf
diesem Rechner genau dort liegt. `ruff check .` scheiterte daran.

**Was getan wurde:** Eine Fixture in `tests/conftest.py` leitet
`Path.home()` für jeden Test in ein temporäres Verzeichnis um. Seither
tritt es nicht mehr auf.

**Was offen ist:** Welcher Test es ausgelöst hat, wurde nie gefunden.
Die naheliegenden Kandidaten prüfen alle ordentlich mit `tmp_path`.
Die Fixture behandelt die Wirkung, nicht die Ursache.

**Es passiert weiterhin.** Am 20. September entstanden zwei weitere
Kopien (`06_Kontoverwaltung` um 17:18, `06_Kontoverwaltung 2` um
17:33), obwohl die Fixture längst wirkte. Es ist also **kein Test**,
sondern etwas außerhalb des Testlaufs. Ausgeschlossen sind inzwischen:

- die Testläufe selbst, denn dort greift die Fixture,
- das Laden eines Diagramms: `Diagramm.laden` kopiert nichts. Dieselbe
  Probe zweimal laufen lassen - beim zweiten Mal entstand keine
  weitere Kopie,
- die naheliegenden Tests, die alle ordentlich mit `tmp_path` arbeiten.

**Noch zu prüfen:** Ob es die installierte `Natter.exe` ist, die
während der Abnahme 60 Sekunden lief - der Zeitpunkt 17:18 liegt nahe
an einem solchen Lauf. Falls ja, legt Natter beim Start unter
Umständen eine Beispielkopie an, ohne dass jemand darauf geklickt hat.
Das wäre kein Schönheitsfehler mehr, sondern ein Fehler im Programm:
auf einem Schulrechner entstünde bei jedem Start ein weiterer Ordner
im Dokumente-Ordner.

Der Weg dorthin: die installierte Natter starten, nichts anklicken,
und nachsehen, ob im Ordner „Dokumente/Natter“ etwas Neues steht.

---

## 6. Prozesszeiten sind auf diesem Rechner nicht messbar

**Beobachtet:** Weder `Get-Process | Select CPU` noch die
WMI-Zähler `UserModeTime`/`KernelModeTime` liefern etwas anderes als
null — auch nicht für Prozesse, die nachweislich rechnen. Beim
erfolgreichen Auslieferungsbau standen sie genauso auf null wie beim
hängenden Testlauf.

**Folge:** „Null CPU-Zuwachs" taugt hier nicht als Beleg für einen
Stillstand. Zweimal führte das fast zu einer Fehldiagnose: einmal
wurde ein gesunder Lauf für hängend gehalten, einmal wäre ein echter
Hänger beinahe mit der falschen Begründung erklärt worden.

**Was stattdessen trägt:** ob das Protokoll fortschreitet, und der
Vergleich mit der bekannten Normaldauer (Testlauf 3:30–4:00,
Auslieferungsbau rund 10 Minuten).

**Noch zu prüfen:** Ob es an der Sandbox liegt oder an
Windows-Berechtigungen. Ein verlässlicher Zähler wäre nützlich, weil
die Laufzeit-Angaben sonst nur aus Erfahrung stammen.

---

## 7. Der Starter braucht die Hälfte der Startzeit

**Beobachtet:** Vom Doppelklick bis zum Fenster vergehen rund 1,65
Sekunden. Davon entfallen etwa 790 Millisekunden auf `Natter.exe`,
bevor überhaupt Python anläuft — der Starter entpackt sich und fährt
dann eine zweite Python hoch.

**Entschieden:** Der Starter bleibt, wie er ist. `Natter.exe` behält
sein eigenes Symbol, seine Versionsangabe und seine Signatur; die
Zeit wird dafür in Kauf genommen.

Hier nur festgehalten, damit die Frage nicht in einem halben Jahr noch
einmal von vorn aufgemacht wird. Gemessene Alternativen waren:
`--onedir` statt `--onefile` (spart 200 ms, kostet 15,8 MB und einen
Ordner neben der Exe) und die Verknüpfung direkt auf `pythonw.exe`
(spart 790 ms, kostet das eigene signierte `Natter.exe`).
