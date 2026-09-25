# Offene Punkte

Gefundene Fehler und ungeklärte Fragen, die noch nicht behoben sind.
Jeder Eintrag nennt, was beobachtet wurde, was davon nachgewiesen ist
und was noch zu prüfen bleibt.

Erledigte Punkte werden hier gestrichen, nicht abgehakt — was drinsteht,
ist offen.

Wie die Punkte umgesetzt werden, steht in
[`umsetzungsplan.md`](umsetzungsplan.md): je Punkt die Änderung, die
Tests dazu und woran das Erledigtsein erkennbar ist.

## Stand am 25. September 2026

Zwanzig der dreiundzwanzig Punkte sind erledigt oder geklärt. Was ein
gestrichener Eintrag noch enthält, ist die Vorgeschichte: was
beobachtet wurde, was die Ursache war und woran das Ergebnis hängt.
Gelöscht wird nichts davon - beim nächsten ähnlichen Fehler ist die
Spur mehr wert als ein leeres Blatt.

Offen bleiben drei:

* **Punkt 4** — die Lizenzseite des Installers von Hand durchklicken.
  Dafür braucht es einen Menschen vor dem Bildschirm.
* **Punkt 6** — die Prozesszeiten dieses Rechners. Keine Aufgabe,
  sondern eine Einschränkung der Umgebung.
* **Punkt 21** — beim Deinstallieren bleibt ein Ordner zurück.
  Aufgefallen beim Bau von 0.3.0.

Zurückgestellt ist **Punkt 7**, die zweite Hälfte der Startzeit.

---

## 1. Stylesheets kaskadieren auf Kinder — auch auf Dialoge ~~(erledigt)~~

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

## 2. Welche Stellen geprüft sind und welche nicht ~~(erledigt)~~

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

**Geprüft — und die Antwort ist einfacher als erwartet.** Keine
dieser vier Klassen setzt überhaupt ein Stylesheet: weder
`ide/database/panel.py` noch `ide/project/neu_dialog.py`,
`ide/inspector/eigenschaften_tabelle.py` oder
`ide/diagramm/canvas.py`. Ihre Dialoge erben damit nur das Thema des
Fensters, also genau das, was sie sollen. Der Fall aus Punkt 1 war
ein anderer: dort hing der Dialog an einem Knopf, der für sich selbst
eine Farbe und einen Rahmen gesetzt hatte.

**Gehalten von** vier Tests in `tests/test_stylesheet_kaskade.py`:
einer je Datei, dass sie sich nicht selbst gestaltet, dazu einer,
dass die Liste dieser Dateien nicht veraltet ist, und einer, dass in
ihnen überhaupt noch Dialoge aufgehen - sonst wäre die Prüfung eine
Sammlung harmloser Dateien.

---

## 3. Die Druckvorschau zeigt das Diagramm winzig und mit zerlaufener Schrift ~~(erledigt)~~

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
Umlauten und ohne abgeschnittene Zeilen erscheinen. **Das bleibt
offen** - dafür braucht es einen Menschen vor dem Bildschirm, und
eine stille Installation zeigt keine Seite.

**Was sich ohne das festhalten ließ** (zwei Tests in
`tests/test_textstil.py`):

- Beide Seiten sind in `tools/natter.iss` überhaupt eingebunden
  (`LicenseFile`, `InfoBeforeFile`). Eine Seite, die niemand
  einbindet, kann noch so schön sein.
- Keine Zeile ist länger als 80 Zeichen. Inno Setup zeigt beide
  Seiten in einem Feld fester Breite; was länger ist, bricht um und
  sieht nach einem Fehler aus. Gemessen liegt die längste Zeile bei
  74 Zeichen.

Umlaute und Byte-Order-Mark prüfen bereits
`test_der_installer_liest_seine_texte_als_utf8` und die
Umlaut-Tests.

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

## 7. Der Starter braucht die Hälfte der Startzeit ~~(zurückgestellt)~~

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

## 8. Der Prüfungsmodus — alle Bedingungen an einer Stelle ~~(erledigt)~~

Der Modus wird über „Werkzeuge → Prüfungsmodus starten …" eingeschaltet
und läuft vier Stunden. Hier steht, was er leisten muss, was davon
nachgewiesen ist und was noch fehlt.

### Gilt bereits, nachgemessen

- **Er übersteht das Schließen von Natter.** Vom Nutzer ausdrücklich
  verlangt. Geprüft mit zwei getrennten Prozessen, so wie Schließen und
  Wiederöffnen: der zweite meldet `läuft: True` und eine Restzeit von
  3:59:58. Gespeichert wird nicht, *dass* der Modus an ist, sondern
  *wann er vorbei ist* — ein Schalter im Speicher wäre mit einem
  Neustart ausgehebelt.
- **Er lässt sich in der Oberfläche nicht abschalten.** `beenden()` in
  `pcl/pruefungsmodus.py` wird von der IDE nirgends aufgerufen; nur
  `starten`, `laeuft` und `restzeit_text` sind angeschlossen. Die
  Zusage im Dialog stimmt also.
- **Er läuft von selbst aus.** Niemand muss daran denken, ihn wieder
  abzuschalten, und kein Rechner bleibt über den Schultag hinaus
  eingeschränkt.
- **Keine Lösungsvorschläge.** Die Fehlermeldung sagt weiterhin, *was*
  falsch ist, aber nicht mehr, woran es liegen könnte.
- **Kein Quelltext aus Klassendiagramm und Struktogramm.**
- **Vervollständigung ohne die deutschen Erklärungen.** Die Liste
  bleibt — sie ist Schreibhilfe; „Wird beim Klicken ausgelöst" neben
  `on_click` wäre dagegen nah an der Antwort.

### Fehlt noch

- **Keine zuletzt geöffneten Dateien** auf dem Startbild
  (`ide/shell/startbild.py`).
- **Keine Beispielprojekte** im Untermenü „Datei →
  Beispielprojekte" (`ide/shell/hauptfenster.py`).

Beides ist ein Weg an fremden Code. Die Liste „Zuletzt geöffnet" führt
zu dem, was in der Stunde davor bearbeitet wurde — in einer Klausur
möglicherweise zur Lösung der Aufgabe, die gerade gestellt ist. Die
Beispielprojekte enthalten ausformulierte Lösungen zu genau den
Themen, die geprüft werden.

### Noch zu prüfen

- Was geschehen soll, wenn der Modus **während** einer laufenden
  Sitzung startet: das Startbild müsste sich dann neu aufbauen, sonst
  bleibt die Liste stehen, bis jemand das Fenster wechselt.
- Ob der Menüeintrag ganz verschwinden oder nur gesperrt sein soll.
  Gesperrt erklärt sich besser — wer ihn sucht, sieht, dass es ihn
  gibt und dass er gerade nicht geht.
- Ob auch der Projekt-Explorer betroffen ist, wenn ein fremdes Projekt
  noch offen war, als der Modus begann.
- **Wie weit der Schutz reicht, und das ehrlich benannt.** Der
  Zeitpunkt steht in einer gewöhnlichen Ini-Datei im Benutzerprofil.
  Wer sie bearbeiten kann, kann den Modus beenden. Für den
  Unterrichtsgebrauch genügt das; eine Prüfungsumgebung im Sinne einer
  gesicherten Abnahme ist es nicht, und das sollte irgendwo stehen,
  damit niemand sich darauf verlässt.

## 9. Im Diagramm-Editor überdecken sich die Bereiche ~~(erledigt)~~

**Beobachtet:** Nach einem Neustart steht die Übersichtskarte
(`ide/diagramm/minimap.py`) an der falschen Stelle. Ein leeres weißes
Feld liegt über dem Lineal, und von den Einträgen links ist nur die
halbe Beschriftung zu sehen („…endiagramm“, „…rbeiten“,
„…ndungen“).

**Ursache — nachgewiesen. Es waren drei, nicht eine.**

1. Die Minimap hing am `QScrollArea`, wurde aber nach den Maßen
   seines Viewports verschoben. Ein `move()` gilt im
   Koordinatensystem des Elternteils, und die beiden unterscheiden
   sich um die Rahmenbreite.
2. `_minimap_einpassen()` lief nur beim Rollen und beim Zoomen, nicht
   beim Ändern der Fenstergröße. Nach einem Neustart mit anderer
   Größe saß die Karte dort, wo sie beim letzten Mal gerechnet worden
   war.
3. Bei einem schmalen Fenster wurde die berechnete Ecke negativ
   (`Breite − 160 − 12`), und die Karte ragte links über den Rand
   hinaus — genau der weiße Kasten über dem Lineal.

Die abgeschnittenen Beschriftungen haben eine eigene Ursache: Qt
verteilt die Breite der Seitenbereiche nach dem Platzbedarf ihres
Inhalts, und keiner der beiden hatte eine Untergrenze. Gemessen war
der Eigenschaften-Bereich 106 Pixel breit, während sein Titel 86
Pixel braucht — nach Abzug der Knöpfe blieben 63 Pixel Textfeld, und
aus „Eigenschaften“ wurde „Eigen…“. Wird der Trenner nach außen
gezogen, trifft es umgekehrt die Palette.

**Geändert.** Die Minimap hängt jetzt am Viewport, ein Ereignisfilter
führt sie bei jeder Größenänderung nach, und passt sie nicht mehr
hin, verschwindet sie, statt herauszuragen. Jeder Seitenbereich hat
eine Mindestbreite, die mit der Systemschrift mitwächst
(`DOCK_MINDESTBREITE`).

**Gehalten von** `tests/test_diagramm_minimap_lage.py` (sechs Tests)
und vier weiteren in `tests/test_diagramm_fenster.py`. Der Platz für
den Titeltext wird dort nicht geschätzt, sondern beim Stil erfragt
(`SE_DockWidgetTitleBarText`); `minimumSizeHint()` taugt dafür nicht,
weil der das Kürzen bereits einplant.

**Nicht gemacht:** Das Diagrammfenster merkt sich sein Layout weiter
nicht (kein `saveState()`). Die Bereiche haben zwar einen
`objectName`, aber ein gespeicherter Zustand würde eine einmal
verschobene Aufteilung auch dann wiederherstellen, wenn sie nicht
mehr passt — und die Mindestbreite löst das Beobachtete bereits.

---

## 10. Der erzeugte Quelltext landet nicht im großen Editor ~~(erledigt)~~

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

---

## 11. Alle sichtbaren Texte durchgehen ~~(erledigt)~~

**Vorgabe des Nutzers:** Die Texte sollen überall überprüft werden —
nicht nur dort, wo gerade etwas auffiel.

**Der Anlass** war der Obst-Sortierer: „Die 100 Bäume haben
abgestimmt", „Der Wald antwortet trotzdem", „Worauf der Wald achtet"
und „Das im Blick zu behalten ist der wichtigste Teil". Mit „Wald"
ist nichts anzufangen, und abstimmen kann er auch nicht.

**Durchgegangen wurden** die sichtbaren Texte aller neun
Beispielprojekte samt ihrer Kopfkommentare, die statischen
Beschriftungen aus den `.pfm`-Dateien, die Projektvorlagen, die
Hilfeseiten, der Fehlerkatalog und die Texte des Installers.

**Gefunden und geändert:**

- Der Obst-Sortierer nennt jetzt die Sache: „So haben die 100
  Entscheidungsbäume entschieden: Apfel 59, Banane 0, Orange 41."
  Die Anzahl statt des Prozentsatzes, weil sie sagt, wie die Antwort
  zustande kommt. Der Wald ist überall weg, „Random Forest" als Name
  des Verfahrens geblieben.
- Im Zahlenraten stand ein Satz, der beim Entfernen der Anrede
  zerbrochen war: „Natter denkt sich eine Zahl aus, geraten wird, und
  antwortet …". Er war weder richtig noch verständlich, und ein
  Programm denkt sich auch nichts aus.
- **Im allerersten Beispielprogramm stand die falsche Taste.**
  „Drücke F9, um das Programm zu starten" — gestartet wird mit F5, F9
  ist in Natter nicht belegt. Das trifft die Schülerin in der ersten
  Minute der ersten Stunde.
- `erste_schritte.md` schickte zu den Beispielprojekten „vom
  Startbild". Die stehen seit dem Umbau unter „Datei →
  Beispielprojekte"; der Modulkommentar von `startbild.py` versprach
  sie ebenfalls noch und sprach von zehn statt neun.
- Der Fehlerkatalog erklärte Einrückung mit „Python nutzt Einrückung
  statt begin…end". Wer Pascal nicht kennt, lernt daraus nichts.
- Ein Kommentar im Menü-Editor schrieb dem Editor einen Willen zu
  („der Editor will jedes Feld vorfinden").
- Der Installer sprach von einer „Zusatzaufgabe", wo die zusätzlichen
  Aufgaben des Setups gemeint sind.

**Dabei aufgefallen, über die Textprüfung hinaus:** Die
Tastenübersicht unter „Hilfe" kannte die Tasten des Designers nicht —
weder die Pfeiltasten noch `Strg+D`, `Entf` oder `F2`. Sie stehen
weder in einem Menü noch in der Liste der Editortasten, und
`docs/fuer_lehrkraefte.md` beschrieb sie, während die Übersicht
daneben schwieg. Sie sind jetzt als `DESIGNERTASTEN` aufgeschrieben
und stehen in der Übersicht.

**Gehalten von** `tests/test_tastenkuerzel_in_texten.py`: jedes
Kürzel, das in einem gelesenen Text steht, muss es im
Aktionsregister, im Diagramm-Editor oder in den Editor- und
Designertasten wirklich geben. Der Rest der Textprüfung lässt sich
nicht in einen Test gießen — eine Prüfung, die Bilder erkennen soll,
meldet falsche Treffer. Dafür halten `tests/test_textstil.py` die
Anrede, die Umlaute und die Markdown-Reste fest, und
`tests/test_designertasten.py` hält jede aufgeschriebene
Designertaste gegen den Designer.

---

## 12. Ein langer Text im Label wird abgeschnitten ~~(erledigt)~~

**Beobachtet:** Im Obst-Sortierer endet die unterste Zeile mitten im
Satz: „Der Wald antwortet trotzdem, und zwar mit der" — der Rest fehlt
spurlos.

**Ursache — nachgewiesen.** `Label` in `pcl/components/standard.py`
ruft nirgends `setWordWrap(True)`; im ganzen `pcl` kommt der Aufruf
nicht vor. Ein `QLabel` bricht ohne ihn nicht um: was breiter ist als
das Label, wird abgeschnitten. Das betroffene Label ist 864 Punkte
breit, der Text hat rund 370 Zeichen.

**Warum das mehr ist als ein Schönheitsfehler:** Es trifft jeden, der
einen längeren Text in ein Label schreibt — also genau das, was eine
Schülerin tut, wenn sie ihr Programm erklären will. Der Text
verschwindet ohne Meldung, und im Designer sieht alles richtig aus,
solange die Beschriftung dort kurz ist.

**Noch zu prüfen:**

- Ob `setWordWrap(True)` der richtige Standard ist. Dafür spricht, dass
  ein abgeschnittener Text immer falsch ist. Dagegen, dass ein Label
  dann seine Höhe sprengt statt seine Breite — auch das fällt auf, ist
  aber sichtbar statt unsichtbar.
- Ob es eine eigene Eigenschaft `word_wrap` geben soll, wie sie andere
  Umgebungen kennen. Dann bliebe die Entscheidung bei der Schülerin,
  und der Objektinspektor zeigt sie an.
- Ob `Memo` und `StringGrid` dasselbe Problem haben.
- Ob der Design-Prüfer das melden kann: ein Text, der breiter ist als
  sein Label, ist maschinell erkennbar — `QFontMetrics` liefert die
  Breite. Das wäre eine Regel, die den Fehler findet, bevor jemand
  das Programm startet.

---

## 13. Die Maus-Ereignisse lassen sich im Objektinspektor nicht verknüpfen ~~(erledigt)~~

**Beobachtet:** Im Reiter „Ereignisse" stehen bei einem `Image` fünf
Zeilen: `on_click`, `on_double_click`, `on_mouse_down`,
`on_mouse_move`, `on_mouse_up`. Für die drei Maus-Ereignisse bleibt
das Auswahlfeld immer auf „(kein)" — auch dann, wenn die passende
Methode längst geschrieben ist.

**Ursache — nachgewiesen.** `passende_methoden()` in
`ide/inspector/ereignisse_tabelle.py` lässt nur Methoden durch, die
**genau einen** Parameter neben `self` haben:

    parameter = [p for p in signatur.parameters if p != "self"]
    if len(parameter) == 1:
        namen.append(name)

Die Maus-Ereignisse übergeben aber `x` und `y`
(`EREIGNIS_PARAMETER` in `pcl/control.py`), die Methode heißt also
`(self, sender, x, y)` und hat zwei. Dasselbe trifft `on_select_cell`
(`spalte`, `zeile`) und `on_edit_cell` (`spalte`, `zeile`, `text`) beim
`StringGrid`.

Gegengeprüft mit vier geschriebenen Methoden: angeboten werden zwei.

Der Filter stammt aus der Zeit, als alle Ereignisse `(self, sender)`
hießen — der Modulkopf sagt das auch so. Mit den Maus-Ereignissen aus
M15 und den Zellen-Ereignissen des `StringGrid` stimmt er nicht mehr.

**Behebung:** Der Filter muss die erwartete Parameterzahl vom Ereignis
ablesen statt sie zu raten. `EREIGNIS_PARAMETER` weiß sie:
`1 + len(EREIGNIS_PARAMETER.get(ereignis_name, ()))`. Damit ist die
Liste je Zeile eine andere — was richtig ist, denn eine Methode für
`on_click` passt nicht auf `on_mouse_down`.

**Noch zu prüfen:**

**Der Reiter soll Methoden auch anlegen können.** So vom Nutzer
entschieden — und zwar „nur das, was möglich ist": angeboten wird
ausschließlich, was die Komponente wirklich hat und was sich auch
verknüpfen lässt. Ein Eintrag, der nach dem Anlegen doch nicht wirkt,
wäre schlimmer als keiner.

Das Werkzeug dafür gibt es längst: `handler_methode_einfuegen()` in
`ide/codegen/ereignis.py`, das der Doppelklick im Designer benutzt. Es
schreibt die Methode mit der richtigen Signatur, denn es bekommt die
Parameter übergeben. Es ist nur nicht an den Objektinspektor
angeschlossen.

Der Name folgt derselben Regel wie beim Doppelklick:
`<komponente>_<ereignis ohne on_>`, also `i_keks_mouse_down`.

**Noch zu prüfen:**

- Wie das Anlegen ausgelöst wird. Ein Doppelklick auf die Zeile wäre
  das Naheliegende — er legt im Designer schon die Standardmethode an.
  Ein zusätzlicher Eintrag „(neue Methode)" ganz oben im Auswahlfeld
  wäre der zweite Weg und erklärt sich von selbst.
- Was geschieht, wenn es die Methode schon gibt: dann nicht noch einmal
  anlegen, sondern hinspringen. So macht es der Doppelklick im
  Designer auch.
- Ob die Unit dafür offen sein muss. Der Designer braucht `unit_pfad`;
  ohne Datei passiert dort schlicht nichts, und das sollte hier eine
  Meldung sein statt Stillschweigen.
- Ob im Auswahlfeld sichtbar werden soll, welche Signatur erwartet
  wird. Wer nicht weiß, dass `on_mouse_down` zwei Zahlen mitbringt,
  schreibt die Methode falsch und findet sie dann nicht in der Liste —
  ohne jede Meldung, woran es liegt.
- Ob der `DBNavigator` betroffen ist: er hat mehrere Ereignisse und
  kein Standardereignis, für ihn legt der Doppelklick also gar nichts
  an.

---

## 14. Das Formular selbst kennt die Maus nicht ~~(erledigt)~~

**Vorgabe des Nutzers:** Das Formular soll die Position des
Mauszeigers verfolgen können.

**Stand heute:** `Form` hat genau ein Ereignis, `on_create`. Es erbt
von `Komponente` und nicht von `Control`, und damit fehlen ihm
`on_click`, `on_double_click` und die drei Maus-Ereignisse, die jede
sichtbare Komponente seit M15 hat. Nachgesehen mit
`ereignisse(Form)` — die Liste hat einen Eintrag, die eines `Button`
fünf.

**Was das im Unterricht bedeutet:** Wer ein Zeichenprogramm oder ein
kleines Spiel bauen will, braucht den Ort des Klicks auf der Fläche —
nicht auf einem Knopf. Heute geht das nur über einen Umweg: eine
`PaintBox` oder ein `Panel` über das ganze Formular legen und dessen
Maus-Ereignisse benutzen. Das muss man wissen, und es steht nirgends.

**Noch zu prüfen:**

- Welche Ereignisse das Formular bekommen soll. `on_mouse_move` ist
  das, was „verfolgen" meint; `on_mouse_down`/`on_mouse_up` gehören
  dazu, `on_click` und `on_double_click` vermutlich auch.
- Ob `Form` dafür von `Control` erben kann oder ob die Ereignisse
  einzeln hinzukommen. `Form` ist kein Kind eines anderen Fensters und
  hat weder `left`/`top` im selben Sinn noch einen `parent` — ein
  Wechsel der Basisklasse ist also nicht nur eine Zeile.
- Ob die Koordinaten vom Arbeitsbereich aus zählen und nicht vom
  Fensterrahmen. `Top = 0` ist in Natter der obere Rand des
  Arbeitsbereichs (siehe `pcl/form.py`); die Maus-Koordinaten müssen
  demselben Maß folgen, sonst stimmt die Stelle nicht, an der etwas
  gezeichnet wird.
- Ob `on_mouse_move` ohne gedrückte Taste zu viele Ereignisse
  auslöst. Qt liefert sie nur bei gedrückter Taste, solange
  `setMouseTracking` aus ist — für ein Zeichenprogramm ist genau das
  richtig, für eine Positionsanzeige nicht.
- Ob der Objektinspektor das Formular überhaupt anzeigt: die neuen
  Zeilen müssen im Reiter „Ereignisse" erscheinen, wenn das Formular
  selbst ausgewählt ist.

**Geändert.** `Form` hat jetzt `on_click`, `on_double_click`,
`on_mouse_down`, `on_mouse_move` und `on_mouse_up`. Die Ereignisse
kommen einzeln dazu und nicht über einen Wechsel der Basisklasse:
`Control` bringt `left`, `top` und `parent` mit, und nichts davon
hat für ein Fenster dieselbe Bedeutung. Der Ereignisfilter aus
`pcl/control.py` war ohnehin allgemein gehalten - er braucht nur
`_maus_melden` und `_ereignis_ausloesen`, und die sind dafür von
`Control` nach `Komponente` gewandert.

Drei Fragen aus der Liste sind damit beantwortet:

- `setMouseTracking(True)`: eine Bewegung wird auch ohne gedrückte
  Taste gemeldet. Eine Positionsanzeige braucht das; wer nur beim
  Ziehen zeichnen will, merkt sich in `on_mouse_down` ein eigenes
  Kennzeichen.
- Die Koordinaten zählen ab dem Arbeitsbereich. Eine Menüleiste
  liegt im selben Widget und schiebt jede platzierte Komponente um
  ihre Höhe nach unten; `Form._maus_melden()` zieht dieselbe Höhe
  wieder ab, sonst zeichnete ein Programm um die Höhe der Leiste
  daneben.
- Der Objektinspektor zeigt alle sechs Ereignisse mit der richtigen
  Parameterzahl an (nachgesehen, nicht vermutet).

**Gehalten von** `tests/test_form_maus.py`, elf Tests - darunter der
Fall, dass ein Klick auf einen Knopf nicht als Klick auf das
Formular durchgeht.

---

## 15. Nachweisen, dass die Panels wirklich etwas anzeigen ~~(erledigt)~~

**Vorgabe des Nutzers:** Es soll geprüft werden, ob in den Panels auch
tatsächlich Werte ankommen — beim Reiter „Variablen" und bei den
übrigen genauso.

**Warum das nicht selbstverständlich ist:** Ein leeres Panel sieht
genauso aus, ob es nichts zu zeigen gibt oder ob die Verbindung
dahinter nie angeschlossen wurde. Der Reiter „Ausgabe" trug bis
September 2026 den Kurzhinweis „Was das laufende Programm ausgibt
(print)" und zeigte in Wirklichkeit nur Start- und Endzeilen — die
Ausgabe des Programms lief in ein Konsolenfenster daneben. Aufgefallen
ist das erst, als die Konsole verschwinden sollte.

**Woran die fünf Panels hängen:**

| Panel | Gefüllt von | In dieser Sitzung gesehen |
|---|---|---|
| Meldungen | Prüfung vor dem Start, Design-Prüfer, Importbericht, Exe-Export | ja |
| Ausgabe | Start- und Endzeilen; seit Neuestem auch `AusgabeLeser` mit dem, was das Programm schreibt | nur die Start- und Endzeilen |
| Variablen | Debugger, beim Halt an einem Haltepunkt (`hauptfenster.py`, Zeile 3246) | nein |
| Aufrufstapel | Debugger, derselbe Halt | nein |
| Tests | Testlauf über „Projekt → Alle Tests ausführen" | ja |

**Was zu tun ist:** Ein Durchgang mit einem echten Programm, bei dem
jedes Panel einmal etwas zeigen muss:

- ein Haltepunkt setzen, starten, und nachsehen, ob im Reiter
  „Variablen" die Variablen mit ihren Werten stehen und im
  „Aufrufstapel" die Aufrufkette,
- ein GUI-Programm mit `print()` starten und nachsehen, ob die Zeilen
  im Reiter „Ausgabe" ankommen. Das ist neu und bisher nur in Tests
  geprüft, nie mit einem laufenden Schülerprogramm,
- ein Programm mit einem Fehler starten und nachsehen, ob die
  Fehlermeldung ebenfalls in „Ausgabe" landet — `stderr` läuft seit
  der Umstellung in dasselbe Rohr,
- eine Zeile im Panel anklicken und prüfen, ob sie an die richtige
  Stelle im Quelltext führt.

**Dabei gleich mit zu erledigen:** Der Variablenbaum trägt die
Spaltenüberschriften **„Eigenschaft | Wert"**. Das ist die Beschriftung
des Objektinspektors; hier stehen keine Eigenschaften, sondern
Variablen. Gefüllt wird die erste Spalte auch aus `variable["name"]`.
Richtig wäre „Variable | Wert".

**Noch zu prüfen:**

- Ob ein Panel sagen soll, warum es leer ist. „Hier stehen die
  Variablen, sobald das Programm an einem Haltepunkt hält" ist eine
  Auskunft; eine leere Fläche ist keine.

**Nachgewiesen, mit laufenden Programmen statt mit Attrappen.** Der
Durchgang steht als `tests/test_panels_zeigen_werte.py` und startet
echtes Python:

- **Variablen:** `zahl` steht mit `7` da, `name` mit `'Anna'`, eine
  Liste mit ihrem Inhalt. Nicht nur Namen, sondern Werte.
- **Aufrufstapel:** bei einem Halt in `innen()`, aufgerufen aus
  `aussen()`, stehen beide in der Kette.
- **Ausgabe:** `print`-Zeilen eines GUI-Programms kommen an, ebenso
  was nach `stderr` geht, und eine unbehandelte Ausnahme ist mit
  ihrem `IndexError` zu lesen.

**Der Nebenbefund, der beinahe für einen Fehler gehalten wurde:** Bei
einem **Konsolen**projekt bleibt die Ausgabe im eigenen Fenster des
Programms und steht nicht im Panel. Das ist Absicht - ein
Konsolenprogramm braucht `input()`, und eine Eingabe nimmt eine Liste
im Panel nicht entgegen. Der Kurzhinweis am Reiter versprach es
trotzdem für jedes Programm und sagt jetzt „Start und Ende - bei
einem Programm mit Oberfläche auch, was es ausgibt".

**Erledigt:** Die Spalte im Variablenbaum heißt „Variable" statt
„Eigenschaft".

**Nicht gemacht:** Der Hinweistext in einem leeren Panel. Qt hat für
`QListWidget` und `QTreeWidget` keinen Platzhaltertext, und ein
eingefügter Eintrag wäre ein Datensatz, der keiner ist - jeder Test,
der auf `count() == 0` prüft, fiele darauf herein. Ein Label über der
Liste wäre der Weg; die Kurzhinweise an den Reitern leisten bis
dahin, was sie können.
- Ob die Panels beim Beenden des Programms geleert werden oder den
  letzten Stand behalten. Beides ist vertretbar, aber es sollte
  entschieden sein.

---

## 16. Den Quelltext als PDF herunterladen können ~~(erledigt)~~

**Vorgabe des Nutzers:** Es soll die Möglichkeit geben, den Code als
formatiertes PDF zu speichern.

**Wofür das gebraucht wird:** Eine Abgabe. Wer sein Programm abgibt,
gibt heute entweder den ganzen Ordner ab oder druckt aus dem Editor —
und ein `.py` im Anhang lässt sich weder anstreichen noch mit einer
Note versehen. Ein PDF ist das Format, das eine Lehrkraft erwartet,
und es zeigt den Code so, wie der Schüler ihn vor sich hatte.

**Was dafür schon da ist — beide Hälften:**

- Die Hervorhebung: `PythonHervorhebung` in
  `ide/shell/python_hervorhebung.py`, ein `QSyntaxHighlighter`, der im
  Editor ohnehin läuft.
- Die PDF-Ausgabe: `QPdfWriter`, benutzt in `ide/diagramm/export.py`
  für Diagramme. Dort steht auch der Kniff mit den 96 dpi, damit eine
  PDF-Einheit einem Bildschirmpunkt entspricht.

Ein `QTextDocument` trägt seine Formatierung mit und kann über
`print_()` direkt in einen `QPdfWriter` schreiben. Die Hervorhebung
lässt sich auf ein solches Dokument anwenden, ohne dass dafür ein
Editor sichtbar sein muss.

**Entschieden (vom Nutzer):**

- **Das ganze Projekt**, nicht nur die offene Datei — mit einer
  Überschrift je Datei und einem Seitenumbruch dazwischen.
- **Nur die `u_*`-Dateien.** `main.py` bleibt draußen: sie ist der
  Starter, den Natter schreibt, und enthält keinen Schülercode. Die
  erzeugten `u_*_design.py` bleiben ebenfalls draußen. `Projekt.units`
  liefert genau diese Auswahl schon heute.
- **Immer das helle Thema**, unabhängig davon, was in der IDE
  eingestellt ist. Das gilt für jeden Export: die Hervorhebung des
  dunklen Themas ist auf weißem Papier unlesbar.
- **Mit Zeilennummern.** Ohne sie lässt sich in der Besprechung nicht
  auf eine Stelle zeigen.

**Noch zu prüfen:**

- **Umbruch langer Zeilen:** ein Blatt ist schmaler als ein Bildschirm.
  Abschneiden ist keine Möglichkeit — siehe Punkt 12. Entweder
  umbrechen mit einer Kennzeichnung am Zeilenanfang, oder die Schrift
  so wählen, dass die übliche Zeilenlänge passt. Die Prüfung vor dem
  Start kennt eine Höchstlänge; daran ließe sich die Schriftgröße
  ausrichten.
- **Kopfzeile:** Projektname, Dateiname und Datum. Bei einer
  eingesammelten Abgabe ist sonst nicht erkennbar, wessen Datei das
  ist.
- **Wo der Eintrag hingehört:** „Projekt → Quelltext als PDF
  exportieren …", weil es das ganze Projekt betrifft.
- Ob der Prüfungsmodus etwas daran ändert. Vermutlich nicht — der
  Schüler exportiert seinen eigenen Code.
- Ob leere Dateien mit in das PDF gehören. Eine Überschrift über
  nichts ist unschön, ihr Fehlen aber auch verwirrend.

**Gebaut** als `ide/export/quelltext_pdf.py`, erreichbar über
„Projekt → Quelltext als PDF …". Eine Datei je Seite, Zeilennummern
in Grau, die Hervorhebung aus dem Editor, in der Kopfzeile
Projektname, Dateiname und Datum.

Zum Drucken eingerichtet: A4, 20 mm Rand ringsum, Consolas in 8
Punkt. Nachgemessen passen damit 99 Zeichen Code neben die
Nummernspalte - knapp die Zeilenlänge, auf die `pyproject.toml` den
Quelltext begrenzt. Bei 9 Punkt wären es 85 gewesen, und der
Ausdruck stünde voller Fortsetzungszeilen.

Was länger ist, bricht um und verschwindet nicht (Punkt 12). Eine
hängende Einrückung für den Rest war zuerst drin und ist wieder
heraus: sie kostete rund fünf Zeichen Breite in jeder Zeile, und
dann brachen erst recht Zeilen um, die sonst gepasst hätten. Als
Fortsetzung ist der Rest ohnehin zu erkennen - ihm fehlt die
Zeilennummer.

**Gehalten von** `tests/test_quelltext_pdf.py`, 22 Tests. Der eine,
der die Zeilenlänge misst, überspringt sich selbst, wenn in der
Umgebung keine echte Consolas liegt: unter `offscreen` setzt Qt eine
Ersatzschrift mit fast doppelt so breiten Zeichen ein, und die
Messung sagte dann nichts über das Papier.

---

## 17. Hilfeseiten und Markdown-Ansicht sind ungestaltet ~~(erledigt)~~

**Vorgabe des Nutzers:** Zeilenabstand und Schriftart sollen besser
werden, die Schrift unter anderem kräftiger.

**Beobachtet:** Ein längeres Dokument läuft über die ganze
Fensterbreite, die Zeilen stehen dicht übereinander, und in den
Tabellen kleben die Einträge an den Rahmen. Betroffen sind beide Wege,
denn sie benutzen dieselbe Klasse: die Hilfeseiten unter „Hilfe" und
jede `.md`, die jemand öffnet.

**Stand heute:** `HilfeAnsicht` in `ide/viewers/hilfe_ansicht.py` ist
ein `QTextBrowser` mit `setMarkdown()`. Eingestellt wird daran genau
eines: für Code-Stellen wird die Gattungsfamilie „monospace" durch
eine ersetzt, die es unter Windows wirklich gibt. Zeilenabstand,
Fließtextschrift, Schriftstärke, Ränder, Zeilenbreite und alles an den
Tabellen sind Qts Vorgaben.

### Der Weg dorthin — ausprobiert und nachgemessen

`document().setDefaultStyleSheet()` wirkt nur beim Einlesen von HTML;
`setMarkdown()` geht daran vorbei. Das steht schon im Modul und war
der Grund, warum die Code-Schrift von Hand über die Textblöcke gesetzt
wird.

Der Ausweg ist ein Zwischenschritt über HTML:

    zwischen = QTextDocument()
    zwischen.setMarkdown(markdown)
    self.document().setDefaultStyleSheet(vorlage)
    self.setHtml(zwischen.toHtml())

Damit greift die Vorlage. Gegenübergestellt und angesehen: mit
`setMarkdown` bleibt alles bei Qts Vorgaben, über den Umweg stehen
Zellenabstand, Rahmen, Ränder und ein Zeilenabstand von 160 %
tatsächlich im Bild.

**Die Schriftstärke lässt sich so setzen**, und zwar feiner als nur
fett. Gemessen, welche Angaben Qt annimmt:

| Angabe | Ergebnis |
|---|---|
| ohne Angabe | 400 (normal) |
| `font-weight: 500` | 500 |
| `font-weight: 600` | 600 |
| `font-weight: bold` | 700 |

`body { font-weight: 500; }` vererbt sich dabei auf die Absätze. Für
das dunkle Thema ist das der richtige Hebel: helle Schrift auf dunklem
Grund wirkt dünner als dieselbe Schrift umgekehrt, und 500 gleicht das
aus, ohne fett zu wirken.

### Was in die Vorlage gehört

- **Schriftstärke** 500 im dunklen Thema, 400 im hellen.
- **Zeilenabstand** etwa 160 %.
- **Höchstbreite** von 70 bis 90 Zeichen je Zeile; der Rest des
  Fensters bleibt Rand. Darüber verliert das Auge beim Zeilenwechsel
  den Anschluss.
- **Tabellen:** `border-collapse`, ein Rahmen statt zweier, und
  Innenabstand in den Zellen. Heute kleben die Einträge am Strich.
- **Codeblöcke absetzen.** Heute stehen sie ohne Hintergrund und ohne
  Rahmen mitten im Fließtext. In der Komponenten-Referenz steht unter
  „Vorlage pro Komponente" eine Markdown-Tabelle **absichtlich** als
  Text — sie ist die Vorlage zum Abschreiben. Ohne Absetzung sieht das
  aus wie eine Tabelle, deren Formatierung fehlt, und nicht wie ein
  Beispiel. Ausprobiert: `pre { background-color: …; padding: 10px; }`
  greift über den HTML-Umweg und setzt den Block sichtbar ab.
- **Abstand** zwischen Absätzen und über Überschriften.
- **Die Fließtextschrift** festlegen statt zu nehmen, was Qt gerade
  greift.

### Noch zu prüfen

- **Die Schriftstärke gehört am echten Bildschirm entschieden, nicht
  hier.** 500 ist ein Anhaltspunkt, keine Festlegung: der Eindruck
  „zu dünn" entsteht durch helle Schrift auf dunklem Grund, und
  zwischen 400 und 600 liegt der Unterschied zwischen kraftlos und
  klobig. Beide Themen nebeneinander ansehen und dann entscheiden.
  Die Bilder aus einem Offscreen-Lauf taugen dafür nicht — dort
  greift eine Ersatzschrift mit fehlerhaften Glyphen (siehe
  AGENTS.md, Abschnitt „Tests").
- Ob die Vorlage zum Thema passen muss. Die Farben kommen heute vom
  Widget; eine Vorlage, die Farben festschreibt, würde im dunklen
  Thema falsch aussehen. Vermutlich also nur Maße und Stärke in der
  Vorlage, Farben weiter vom Thema.
- Ob `_code_schrift_setzen()` danach noch gebraucht wird. Über HTML
  ließe sich `code { font-family: Consolas; }` in die Vorlage
  schreiben — dann fiele der Umweg über die Textblöcke weg.
- Ob die Breite mitwandert, wenn jemand die Schrift über
  `Strg+Mausrad` vergrößert.
- Ob `toHtml()` alles überträgt, was `setMarkdown` erzeugt hat:
  Tabellen, Listen, Verweise, Code-Blöcke. Ein Verlust dabei wäre
  schlimmer als das heutige Aussehen.

**Gebaut.** `stilvorlage()` in `ide/viewers/hilfe_ansicht.py`, gesetzt
über den Umweg HTML. Drin stehen Zeilenabstand 160 %, Abstände über
Überschriften und zwischen Absätzen, Tabellen mit einem Rahmen und
Innenabstand, abgesetzte Codeblöcke und die Schriftstärke 500 im
dunklen Thema gegen 400 im hellen.

Die Textbreite ist auf 720 Punkte begrenzt, der Rest des Fensters
bleibt Rand. Nicht über `max-width` - Qts Rich-Text kennt die Angabe
nicht -, sondern über die Ränder des Sichtbereichs. Dabei lauerte
eine Falle: `setViewportMargins()` löst selbst ein `resizeEvent` aus,
und die erste Fassung lief sich im Kreis, bis der Stapel überlief.
Gerechnet wird deshalb mit der Breite des Widgets, die sich dadurch
nicht ändert.

**Die offenen Fragen, beantwortet:**

- `toHtml()` überträgt alles: Überschriften, Tabellen, Zellen,
  Listen, Verweise und Codeblöcke sind danach noch da (nachgesehen,
  nicht vermutet).
- Farben bleiben draußen, bis auf die Fläche hinter Codeblöcken. Die
  Schrift- und Hintergrundfarbe kommt weiter vom Thema der IDE.
- **`_code_schrift_setzen()` fällt nicht weg.** Das war die
  Erwartung, und sie war falsch. Ohne den Nachbesserer bleiben trotz
  `code { font-family: … }` in der Vorlage 673 Stellen in
  `komponenten.md` auf „monospace" stehen, 61 in
  `fuer_lehrkraefte.md` und 25 in `erste_schritte.md`: Qt schreibt
  die Familie beim Umwandeln als Inline-Angabe ins Zeichenformat,
  und die gewinnt gegen die Vorlage.

**Nicht entschieden:** Ob 500 im dunklen Thema die richtige Stärke
ist. Am Offscreen-Bild sieht sie stimmig aus, aber dort greift eine
Ersatzschrift - das gehört am echten Bildschirm angesehen.

**Gehalten von** `tests/test_hilfe_gestaltung.py`, 16 Tests. Zwei
davon messen im fertigen Dokument und nicht in der Vorlage: dass
eine Zeile im Stylesheet steht, heißt nicht, dass Qt sie annimmt.

---

## 18. Die Kopfzeile bietet an, was gerade nicht geht ~~(erledigt)~~

**Beobachtet:** In der Werkzeugleiste steht ganz rechts ein blauer
Pfeil nach unten. Er sieht aus wie ein Knopf zum Herunterladen; er
meint „Einzelschritt".

**Nachgemessen — und der Knopf ist nicht das Hauptproblem.** Ohne
offenes Projekt und ohne laufendes Programm sind *alle* Aktionen im
Menü „Start" anklickbar: Starten, Starten ohne Debugger, Pause,
Fortsetzen, Stopp, Einzelschritt, Prozedurschritt, Ausführen bis
Rücksprung. Von ihnen tun drei beim Anklicken nachweislich gar
nichts:

```python
def _debugger_einzelschritt_aktion(self) -> None:
    if self.debug_sitzung is not None and self._aktueller_thread_id is not None:
        self.debug_sitzung.einzelschritt(self._aktueller_thread_id)
```

Kein `else`, keine Meldung, keine Statuszeile. Wer darauf klickt,
erfährt nicht, dass er zuerst starten und anhalten muss — der Knopf
sieht aus, als wäre er kaputt. „Stopp" macht es besser und sagt „Es
läuft gerade nichts, was sich stoppen ließe."

**Zu tun:**

- Jede Aktion der Kopfzeile einmal auslösen und nachsehen, was
  geschieht — Menüleiste und Werkzeugleiste, vor allem „Start".
- Was ohne laufendes Programm nichts tun kann, gehört ausgegraut.
  Ausgegraut ist eine Auskunft: „geht jetzt nicht", statt „geht
  nicht".
- Was auch ausgegraut niemandem nützt, gehört aus der Werkzeugleiste
  heraus. Einzelschritt ist der erste Kandidat: er ist nur während
  einer Debug-Sitzung sinnvoll, und dann liegt die Hand auf F11.
- Das Symbol für den Einzelschritt neu zeichnen, falls er bleibt.

**Geändert.** Fünf Einträge unter „Start" sind jetzt ausgegraut,
solange das Programm nicht an einem Haltepunkt steht: Pause,
Fortsetzen, Einzelschritt, Prozedurschritt, Ausführen bis Rücksprung.
„Starten", „Starten ohne Debugger" und „Stopp" bleiben anklickbar -
sie sagen, was stattdessen zu tun ist („Kein Projekt offen. Zuerst
über „Projekt → Öffnen …" eines laden"), und ein Satz hilft weiter
als ein graues Symbol.

Dieselbe Regel gilt jetzt unter „Bearbeiten": auch dort waren alle
sechs Einträge anklickbar, ohne dass ein Reiter offen war. Rückgängig
und Wiederholen hängen an der Zeichenfläche des Designers mit, weil
sie dort ebenfalls wirken.

In der Werkzeugleiste steht jetzt „Stopp" mit einem eigenen Symbol.
Der Einzelschritt hat ein neues bekommen: ein Pfeil, der aus der
Zeile in die nächste abbiegt, statt eines geraden Pfeils auf eine
Grundlinie - das ist anderswo das Zeichen fürs Herunterladen und
wurde auch so gelesen.

Die übrigen Menüs wurden mitgeprüft: „Suchen" und „Ansicht" sagen
bereits sauber, woran es fehlt.

**Gehalten von** `tests/test_kopfzeile_und_fusszeile.py`.

---

## 19. Der Prüfungsmodus ist in der Fußzeile nicht zu erkennen ~~(erledigt)~~

**Vorgabe des Nutzers:** In der Fußzeile soll der Prüfungsmodus rot
markiert sein.

**Warum das mehr ist als Geschmack:** Der Prüfungsmodus ändert, was
Natter zulässt — keine fremden Dateien, keine Beispielprojekte, keine
Lösungshinweise in den Fehlermeldungen. Wer nicht auf den ersten Blick
sieht, dass er läuft, sucht den Fehler bei sich. Und wer ihn aus
Versehen anlässt, merkt es erst in der nächsten Stunde.

**Noch zu prüfen:**

- Ob die Anzeige auch im dunklen Thema lesbar bleibt. Rot auf Dunkel
  braucht einen helleren Ton als Rot auf Hell.
- Ob die Farbe allein genügt oder ob das Wort daneben stehen muss.
  Rot-Grün-Sehschwäche ist in einer Klasse die Regel, nicht die
  Ausnahme.
- Wie sich die Restzeit einfügt, die dort schon steht.

**Geändert.** Die Anzeige steht rot hinterlegt mit weißer Schrift
rechts in der Statusleiste. Weiß auf diesem Rot trägt in beiden
Themen - ein Rot, das zum hellen Thema passt, verschwindet im
dunklen. Das Wort „Prüfungsmodus" steht weiter daneben, samt
Restzeit: auf die Farbe allein ist in einer Klasse kein Verlass.

---

## 20. Die Beispielkopien landen im falschen Ordner ~~(erledigt)~~

**Beobachtet:** Beim Öffnen eines Beispiels entstehen Ordner wie
`04_CookieKlicker`, `05_Bildergalerie` und `07_CsvAuswertung` mitten
im Entwicklungsverzeichnis von Natter, zwischen `ide`, `pcl`, `docs`
und `dist`.

**Ursache — nachgewiesen.** `ide/shell/startbild.py`:

```python
KOPIEN_ORDNER = Path("Documents") / "Natter"
...
wurzel = Path(ziel_wurzel) if ziel_wurzel else Path.home() / KOPIEN_ORDNER
```

Auf diesem Rechner liegt das Entwicklungsverzeichnis unter
`C:\Users\…\Documents\natter`. Windows unterscheidet bei Dateinamen
nicht zwischen Groß- und Kleinschreibung, „Natter" und „natter" sind
also derselbe Ordner — die Arbeitskopien landen im Projektstamm.

**Der schwerere Fehler steckt daneben:** `Path.home() / "Documents"`
ist geraten, nicht ermittelt. Ist der Dokumente-Ordner umgeleitet —
auf OneDrive oder auf ein Netzlaufwerk, und beides ist auf
Schulrechnern die Regel und nicht die Ausnahme —, dann zeigt dieser
Pfad ins Leere, und Natter legt einen zweiten, leeren
Dokumente-Ordner an, den im Explorer niemand findet. Den richtigen
Pfad kennt Windows selbst (`SHGetKnownFolderPath`, `FOLDERID_Documents`).

**Zu tun:**

- Den Dokumente-Ordner bei Windows erfragen statt ihn zu raten, mit
  Rückfall auf den bisherigen Pfad, falls die Abfrage nichts liefert.
- Die Kopien in einen eigenen Unterordner legen, damit sie nicht
  zwischen den eigenen Projekten liegen.
- Als Alternative vorgeschlagen: „Datei → Original wiederherstellen",
  das ein verändertes Beispiel auf den Auslieferungsstand zurücksetzt.

**Noch zu prüfen:**

- Ob derselbe geratene Pfad noch an anderen Stellen steht — beim
  Anlegen neuer Projekte, beim Exportieren, im Installer.
- Was mit den Kopien geschieht, die bereits am falschen Ort liegen.
  Sie sind die Arbeit des Nutzers und dürfen nicht verschwinden
  (siehe Punkt 5).

**Geändert.** `ide/pfade.py` fragt jetzt Windows nach dem
Dokumente-Ordner (`SHGetKnownFolderPath`, über `ctypes` aus der
Standardbibliothek) und fällt nur dann auf den alten Pfad zurück,
wenn die Abfrage nichts liefert oder das Programm nicht unter Windows
läuft. Auf dem Rechner, auf dem es auffiel, ist der Unterschied
`C:\Users\…\OneDrive\Dokumente` gegen `C:\Users\…\Documents`.

Im selben Zug schlägt „Neues Projekt …" diesen Ordner jetzt vor,
statt das Feld leer zu lassen - sonst sucht sich jede Schülerin beim
ersten Projekt einen eigenen Ort, und die Projekte einer Klasse
liegen danach an zehn verschiedenen Stellen.

**Nicht gemacht:** Die Kopien, die bereits im alten Ordner liegen,
bleiben unberührt. Sie sind die Arbeit des Nutzers (Punkt 5); Natter
verschiebt sie nicht von sich aus.

**Gehalten von** `tests/test_pfade.py`, samt der Gegenprobe, dass der
Zielordner nicht im Entwicklungsbaum liegt.

---

## 21. Nach dem Deinstallieren bleibt ein Ordner zurück

**Beobachtet:** Beim Durchgang zu 0.3.0 entfernte der Uninstaller
30.375 Dateien und ließ acht liegen — einen `.ruff_cache` im
Programmordner, und damit den Ordner selbst.

**Ursache — nachgewiesen.** Den Cache legt die Prüfung vor dem Start
an, also während des Unterrichts und lange nach der Installation.
Inno Setup entfernt beim Deinstallieren, was es selbst geschrieben
hat; alles andere bleibt. Derselbe Fall wie beim Uninstaller im
Manifest (siehe `docs/arbeitspakete/M13.md`), nur andersherum.

**Was das bedeutet:** Wer Natter entfernt, findet unter
`%LOCALAPPDATA%\Programs\Natter` weiterhin einen Ordner. Auf einem
Schulrechner, der zwischen zwei Halbjahren aufgeräumt wird, sieht das
nach einer halben Deinstallation aus.

**Zu tun:**

- Eine `[UninstallDelete]`-Regel für `{app}\.ruff_cache` in
  `tools/natter.iss`, und eine für den Ordner selbst.
- Nachsehen, was die IDE sonst noch neben sich schreibt: `__pycache__`
  in `site-packages` entsteht beim ersten Import und dürfte dasselbe
  Problem haben. Beim Bau von 0.2.0 waren es über achtzig `.pyc`.
- Prüfen, ob eine solche Regel etwas löscht, das ein Schüler dort
  abgelegt hat. Im Programmordner hat er nichts zu suchen, aber
  „nichts zu suchen" ist kein Beweis.

---

## 22. Jedes Öffnen eines Beispiels legt eine neue Kopie an ~~(erledigt)~~

**Beobachtet:** Im Entwicklungsverzeichnis stehen `04_CookieKlicker`,
`05_Bildergalerie` und `07_CsvAuswertung`. In „Zuletzt geöffnet"
erscheinen dieselben Beispiele mehrfach, einmal mit „(Natter)" und
einmal mit „(beispielprojekte)" dahinter.

**Ursache — nachgewiesen.** Drei Dinge, die zusammen so aussahen, als
entstünden laufend neue Ordner:

- Die drei Ordner im Entwicklungsverzeichnis stammen vom 20.09.
  zwischen 17:45 und 17:52, knapp drei Stunden vor der Korrektur aus
  Punkt 20. Neu angelegt wird dort seitdem nichts. Die Liste „Zuletzt
  geöffnet" führte aber weiter hinein, und in `04_CookieKlicker` wurde
  noch am 25.09. gearbeitet.
- `beispiel_kopieren()` legte bei jedem Öffnen eine weitere Kopie an,
  sobald es schon eine gab („08_Regression 2", „… 3"). Gedacht war
  das als Schutz der Arbeit von gestern. Überschrieben wurde sie
  tatsächlich nicht, aber geöffnet wurde eine frische Kopie, und die
  Arbeit lag unbemerkt im Ordner daneben.
- In der Liste standen auch die Originale unter `beispielprojekte`.
  Ein Klick darauf öffnete das Beispiel selbst, an Ort und Stelle.

**Geändert:**

- Eine vorhandene Kopie wird weiterbenutzt. Erkannt wird sie an ihrer
  Projektdatei, nicht am Ordnernamen - ein eigenes Projekt, das
  zufällig „04_CookieKlicker" heißt, bleibt unangetastet und die Kopie
  bekommt dann eine Nummer.
- Ein Original aus „Zuletzt geöffnet" oder über „Öffnen …" wird als
  Kopie geöffnet, auf demselben Weg wie über das Menü.
- **Datei → Beispielprojekte → Auf Original zurücksetzen …** ersetzt
  den Inhalt der Kopie durch das Original. Der Ordner bleibt derselbe,
  es entsteht kein neuer. Ohne diesen Eintrag gäbe es seit der
  Wiederverwendung keinen Weg mehr zurück zum Ausgangszustand.

- Die Kopien liegen in einem eigenen Unterordner,
  `Dokumente\Natter\Beispielprojekte`, und nicht mehr zwischen den
  eigenen Projekten. Eine Kopie am alten Platz direkt unter `Natter`
  zieht beim nächsten Öffnen mit ihrem Inhalt dorthin um.
- Liegt das Entwicklungsverzeichnis selbst unter `Dokumente\Natter`,
  wäre der Unterordner der Ordner der Originale. Dann bricht das
  Kopieren ab, statt das Original als seine eigene Kopie zu öffnen.

Die drei alten Kopien im Entwicklungsverzeichnis sind auf Wunsch
gelöscht.

Tests: `tests/test_beispiel_und_thema.py`.

---

## 23. Nach dem Umschalten auf Hell bleibt der Designer dunkel ~~(erledigt)~~

**Beobachtet:** Nach dem Wechsel von Dunkel auf Hell unter
„Ansicht → Design" blieben das Formular im Designer und das daraus
gestartete Programm dunkel.

**Ursache — nachgewiesen.** Zwei Stellen:

- Ein Formular steht auf `theme = "system"`, und `theme_aufloesen()`
  fragte dafür Windows. Natter auf Hell und Windows auf Dunkel ergab
  ein dunkles Formular in einer hellen Natter, im Designer wie im
  gestarteten Programm.
- Ein `Form` legt sein Stylesheet beim Erzeugen fest.
  `_design_wechseln()` frischte Editor-Tabs und Symbole auf, offene
  Designer-Formulare aber nicht; sie behielten das alte Design, bis
  der Tab neu geöffnet wurde.

**Geändert:**

- Natter setzt beim Start und bei jedem Umschalten die
  Umgebungsvariable `NATTER_THEMA` auf `light` oder `dark`.
  `theme_aufloesen("system")` richtet sich zuerst danach. Das Formular
  im Designer liest sie im Prozess von Natter, das gestartete Programm
  erbt sie.
- Steht Natter selbst auf „System", wird die Variable entfernt, und
  alles folgt Windows.
- Außerhalb von Natter, mit `python main.py` oder als exportierte Exe,
  fehlt die Variable, und es gilt wie bisher Windows.
- `_design_wechseln()` frischt offene Designer-Formulare auf.

**Was bleibt:** Ein Programm, das beim Umschalten schon läuft,
behält sein Design bis zum nächsten Start. Es ist ein eigener Prozess,
und Natter greift nicht in ihn hinein.

Tests: `tests/test_beispiel_und_thema.py`.
