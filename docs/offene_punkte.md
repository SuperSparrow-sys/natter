# Offene Punkte

Gefundene Fehler und ungeklärte Fragen, die noch nicht behoben sind.
Jeder Eintrag nennt, was beobachtet wurde, was davon nachgewiesen ist
und was noch zu prüfen bleibt.

Erledigte Punkte werden hier gestrichen, nicht abgehakt — was drinsteht,
ist offen.

Wie die Punkte umgesetzt werden, steht in
[`umsetzungsplan.md`](umsetzungsplan.md): je Punkt die Änderung, die
Tests dazu und woran das Erledigtsein erkennbar ist.

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

## 8. Der Prüfungsmodus — alle Bedingungen an einer Stelle

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

---

## 11. Alle sichtbaren Texte durchgehen

**Vorgabe des Nutzers:** Die Texte sollen überall überprüft werden —
nicht nur dort, wo gerade etwas auffiel.

**Der Anlass:** Im Obst-Sortierer (Stufe 9) steht

> Die 100 Bäume haben abgestimmt: Apfel 59%, Banane 0%, Orange 41%.
> […] Der Wald antwortet trotzdem, und zwar mit der ähnlichsten Sorte.

und daneben „Worauf der Wald achtet:". Der Einwand des Nutzers: mit
„Wald" ist nichts anzufangen, und abstimmen kann er auch nicht. Das
Bild erklärt nichts — es setzt voraus, dass man schon weiß, was ein
Random Forest ist, und behauptet nebenbei, ein Programm habe eine
Meinung.

Was stattdessen dasteht, muss die Sache benennen: wie viele der
Einzelentscheidungen auf welche Sorte fielen, und dass das Verfahren
immer eine Antwort liefert, auch für eine Frucht, die es nicht gibt.

**Im selben Absatz steht noch eine Floskel:** „Das im Blick zu behalten
ist der wichtigste Teil." Dieselbe Sorte wie „die Vorhersage steht auf
festem Boden", die schon aus Stufe 8 entfernt wurde.

**Umfang der Aufgabe:** Jeder Text, den jemand liest — die sichtbaren
Texte aller neun Beispielprojekte, die Meldungen der IDE, die
Hilfeseiten, die Projektvorlagen und die Texte des Installers.

**Noch zu prüfen:**

- Ob sich Bilder und Vergleiche finden lassen, die dasselbe Problem
  haben: etwas wird anschaulich gemacht, das dadurch nicht klarer
  wird, oder ein Programm bekommt Absichten angedichtet.
- Ob die Fachbegriffe stehenbleiben sollen, wo sie richtig sind.
  „Random Forest" ist der Name des Verfahrens und gehört in den Text;
  „der Wald antwortet" ist es nicht.
- `tests/test_textstil.py` prüft bisher direkte Anrede, Umlaute und
  Markdown-Reste. Ob sich diese Sorte überhaupt maschinell fassen
  lässt, ist offen — vermutlich hilft nur, alles einmal zu lesen.

---

## 12. Ein langer Text im Label wird abgeschnitten

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

## 13. Die Maus-Ereignisse lassen sich im Objektinspektor nicht verknüpfen

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

## 14. Das Formular selbst kennt die Maus nicht

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

---

## 15. Nachweisen, dass die Panels wirklich etwas anzeigen

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
- Ob die Panels beim Beenden des Programms geleert werden oder den
  letzten Stand behalten. Beides ist vertretbar, aber es sollte
  entschieden sein.

---

## 16. Den Quelltext als PDF herunterladen können

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

---

## 17. Hilfeseiten und Markdown-Ansicht sind ungestaltet

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
