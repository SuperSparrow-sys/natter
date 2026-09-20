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

## 3. Die Lizenzseite des Installers ist nie angesehen worden

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

## 4. Welcher Test in den Dokumente-Ordner schreibt, ist unbekannt

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

**Noch zu prüfen:** Einmal mit abgeschalteter Fixture laufen lassen und
mitschreiben, wer `beispiel_kopieren` ohne Zielordner aufruft. Solange
das unklar ist, kann derselbe Aufruf an anderer Stelle auch im
laufenden Programm an einer unerwarteten Stelle landen.

---

## 5. Prozesszeiten sind auf diesem Rechner nicht messbar

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

## 6. Der Starter braucht die Hälfte der Startzeit

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
