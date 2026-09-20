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

## 5. Die Ordner im Projektstamm sind die Arbeit des Nutzers ~~(geklärt)~~

**Geklärt am 20. September, 17:38.** Es war nie ein Test und nie ein
Fehler im Programm.

`beispiel_kopieren` legt die Arbeitskopie eines Beispiels im Ordner
„Dokumente/Natter“ an. Auf **diesem** Rechner liegt das Repository
selbst genau dort, und Windows unterscheidet keine Groß- und
Kleinschreibung. Jede Arbeitskopie landet damit im Projektstamm.

Der Nachweis: um 17:38 lief Natter, und es entstanden
`06_Kontoverwaltung` (eine frische Arbeitskopie) und
`06_Kontoverwaltung 2` mit `u_konto_klassen.py` darin — der Datei,
die der Nutzer im selben Augenblick aus dem Klassendiagramm erzeugt
hat.

**Was daraus folgt:**

- Die Fixture in `tests/conftest.py` bleibt trotzdem richtig: kein
  Test hat im echten Heimverzeichnis etwas zu suchen.
- `.gitignore` deckt jetzt auch die durchnummerierten Kopien ab
  (`... 2`, `... 3`). Sie sind echte Arbeit und dürfen weder
  eingecheckt noch weggeräumt werden. Beinahe wäre genau das
  passiert.
- **Für die Entwicklung heißt das:** auf diesem Rechner nie
  `git add -A` blind ausführen und nie Ordner im Stamm löschen, die
  nach einem Beispiel aussehen — es kann die laufende Arbeit sein.

**Offen bleibt eine Kleinigkeit:** `06_Kontoverwaltung 2` enthält nur
`u_konto_klassen.py` und sonst nichts. Die erzeugte Klassendatei ist
also nicht in das offene Projekt gewandert, sondern in einen eigenen,
sonst leeren Ordner. Das gehört zu Punkt 10 und ist dort noch zu
prüfen.

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

---

## 8. Der Prüfungsmodus zeigt weiterhin fremde Projekte

**Vorgabe des Nutzers:** Im Prüfungsmodus sollen auf dem Startbild
**keine zuletzt geöffneten Dateien** und **keine Beispielprojekte**
erscheinen.

**Warum das zählt:** Beides ist ein Weg an fremden Code. Die Liste
„Zuletzt geöffnet“ führt zu dem, was in der Stunde davor bearbeitet
wurde — in einer Klausur möglicherweise zur Lösung einer Aufgabe, die
gerade gestellt ist. Die Beispielprojekte enthalten ausformulierte
Lösungen zu genau den Themen, die geprüft werden.

**Betroffen sind zwei Stellen:**

- `ide/shell/startbild.py`, Abschnitt „Zuletzt geöffnet“
- `ide/shell/hauptfenster.py`, das Untermenü „Datei →
  Beispielprojekte“

Der Modus selbst liegt in `pcl/pruefungsmodus.py` und lässt sich
über `pruefungsmodus_laeuft()` abfragen — so machen es die
Fehlermeldungen und die Vervollständigung schon.

**Noch zu prüfen:**

- Was geschehen soll, wenn der Modus **während** einer laufenden
  Sitzung startet: das Startbild müsste sich dann neu aufbauen, sonst
  bleibt die Liste stehen, bis jemand das Fenster wechselt.
- Ob der Menüeintrag ganz verschwinden oder nur abgeschaltet sein
  soll. Abgeschaltet erklärt sich besser — wer ihn sucht, sieht, dass
  es ihn gibt und dass er gerade gesperrt ist.
- Ob auch der Projekt-Explorer betroffen ist, wenn ein fremdes Projekt
  noch offen war, als der Modus begann.

---

## 9. Im Diagramm-Editor überdecken sich die Bereiche

**Beobachtet:** Nach einem Neustart steht die Übersichtskarte
(`ide/diagramm/minimap.py`) an der falschen Stelle. Auf dem
Bildschirmfoto schiebt sich der Palettenbereich über die
Zeichenfläche, ein leeres weißes Feld liegt über dem Lineal, und von
den Einträgen links ist nur die halbe Beschriftung zu sehen
(„…endiagramm“, „…rbeiten“, „…ndungen“).

**Was dazu bekannt ist:** Das Hauptfenster merkt sich sein Layout über
`saveState()`/`restoreState()` unter dem Schlüssel `fenster/layout`.
Für das Diagrammfenster ist nichts dergleichen zu finden — es baut
seine Bereiche bei jedem Öffnen neu auf. Die Vermutung liegt nahe,
dass die Größen dabei nicht zur Fenstergröße passen; nachgemessen
ist das aber nicht.

**Noch zu prüfen:**

- Ob die Übersichtskarte ein eigener Bereich ist oder auf der
  Zeichenfläche liegt, und woran ihre Stelle hängt.
- Ob das Diagrammfenster sein Layout merken soll wie das Hauptfenster.
  Falls ja, brauchen seine Bereiche einen `objectName`, sonst
  speichert Qt nichts.
- **Dass alles lesbar ist**: keine abgeschnittenen Beschriftungen,
  keine Bereiche, die sich überdecken, und das bei kleiner
  Fenstergröße genauso wie bei großer.
- Ob es auch auftritt, wenn das Fenster zum ersten Mal überhaupt
  geöffnet wird — also ohne gespeicherten Zustand.

---

## 10. Der erzeugte Quelltext landet nicht im großen Editor

**Beobachtet:** „Quelltext erzeugen“ im Diagramm-Editor zeigt das
Ergebnis in einem eigenen Fenster mit den Knöpfen „Kopieren“,
„Speichern unter …“ und „Schließen“.

**Was fehlt:** Wer „Speichern unter …“ wählt, schreibt die Datei —
und danach passiert nichts. `speichern_unter()` in
`ide/diagramm/codefenster.py` gibt den Pfad zurück, aber niemand
öffnet ihn. Die Schülerin muss die eben geschriebene Datei von Hand
im Projekt-Explorer suchen.

**Gewünscht:** Das Schreiben muss **immer** funktionieren, und die
geschriebene Datei muss **immer** anschließend im großen Editor
erscheinen.

**Wie es gelöst werden soll.** Drei Teile, und der erste ist schon da.

**1. Der Ort.** `_vorschlag_fuer_unit()` in `ide/diagramm/fenster.py`
rechnet den richtigen Ordner bereits aus: eine Ebene über
`diagramme/`, also der Projektordner. Dort sucht `Projekt.units` mit
`ordner.glob("*.py")` — eine Datei, die dort liegt, ist damit
automatisch eine Unit. Im Kommentar steht sogar, warum: ein früherer
Vorschlag `units/` landete an einer Stelle, die das Projekt nie
ansieht, und die Klasse war nirgends wiederzufinden.

Nur der Dialog hinter „Speichern unter …" benutzt das nicht. Er
beginnt in gar keinem Ordner — und genau so ist die erzeugte Klasse am
20. September in einem eigenen, sonst leeren Ordner gelandet. Er muss
in diesem Ordner beginnen.

**2. Die Nachricht ans Hauptfenster.** Der Diagramm-Editor ist ein
eigenes Fenster und kennt das Hauptfenster nicht. Er soll es auch
nicht kennen müssen — stattdessen ein Signal:

    datei_geschrieben = Signal(Path)

`hauptfenster.diagramm_oeffnen()` hält beim Öffnen ohnehin schon eine
Verbindung zum Fenster (`_offene_diagramme`) und kann es dort
anschließen. Das ist das Muster, das im Projekt überall gilt: der
Projekt-Explorer meldet `umbenennen_angefordert` und
`loeschen_angefordert` genauso, statt selbst zu handeln.

**3. Was das Hauptfenster dann tut.** Zwei Aufrufe, beide gibt es
schon:

    self.explorer.projekt_anzeigen(self.projekt)   # Liste neu aufbauen
    self.datei_oeffnen(pfad)                       # Reiter im Editor

`projekt_anzeigen` wird an sechs anderen Stellen genauso gerufen, etwa
nach „Neues Diagramm". Der Explorer liest seine Liste bei jedem Aufruf
frisch von der Platte; es braucht dafür nichts Neues.

**Warum kein `QFileSystemWatcher` auf den Projektordner.** Das wäre
die allgemeinere Lösung und fänge auch Dateien ab, die von außen
dazukommen. Es wäre aber auch die aufwendigere: ein Beobachter, der
bei jedem Speichern anschlägt, während der Editor selbst schreibt, und
eine Liste, die sich unter der Hand neu aufbaut. Das Signal löst das
vorliegende Problem vollständig und lässt sich prüfen. Ein Beobachter
kann später dazukommen, wenn er gebraucht wird.

**Noch zu prüfen:**

- Ob der Weg über `in_datei_schreiben()` gehen soll, das es im selben
  Modul schon gibt: es fragt nach, statt eine vorhandene Datei
  stillschweigend zu überschreiben — wer eine Klasse zweimal erzeugt,
  soll seine ausformulierten Methodenrümpfe nicht verlieren.
- Wohin die Datei standardmäßig gehört. Der Dialog beginnt heute in
  keinem bestimmten Ordner; der Projektordner wäre die naheliegende
  Vorgabe.
- Wie das Diagrammfenster an das Hauptfenster meldet, dass es eine
  Datei gibt. Es ist ein eigenes Fenster und kennt das Hauptfenster
  nicht — ein Signal wäre der Weg, wie es der Projekt-Explorer schon
  macht.
- Was geschehen soll, wenn die Datei außerhalb des offenen Projekts
  liegt: dann gehört sie in einen Reiter, aber nicht in den
  Projekt-Explorer.
- Ob das Schreiben auch dann funktioniert, wenn der Ordner
  schreibgeschützt ist — auf einem Schulrechner keine Seltenheit. Die
  Meldung muss dann sagen, was los ist.
