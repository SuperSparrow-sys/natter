# Offene Punkte

Gefundene Fehler und ungeklärte Fragen, die noch nicht behoben sind.
Jeder Eintrag nennt, was beobachtet wurde, was davon nachgewiesen ist
und was noch zu prüfen bleibt.

Erledigte Punkte werden hier gestrichen, nicht abgehakt — was drinsteht,
ist offen.

---

## 1. Der Farbauswahl-Dialog bekommt Kästchen um jede Beschriftung

**Beobachtet:** Im Diagramm-Editor öffnet „Farbe wählen" den
Farbauswahl-Dialog. Dort hat jede Beschriftung und jeder Knopf einen
grauen Rahmen, die Texte wirken ausgegraut, und der Dialog sieht aus,
als wäre er abgeschaltet.

**Ursache — nachgewiesen.** `ide/diagramm/eigenschaften.py`, Zeile 56:

```python
gewaehlt = QColorDialog.getColor(QColor(self.farbe or "#ffffff"), self)
```

Als Elternteil wird `self` übergeben, also das Farbfeld. Auf dem steht
zwei Methoden weiter oben:

```python
self.setStyleSheet(f"background-color: {farbe}; border: 1px solid #808080;")
```

Qt vererbt ein Stylesheet an alle Kinder, und ein Dialog gilt als Kind
seines Elternteils. Jedes Label und jeder Knopf im Dialog bekommt
dadurch `border: 1px solid #808080`.

Nachgestellt mit einem `QLabel`, das dieselbe Zeile trägt, und einem
`QColorDialog` darunter: das Ergebnis deckt sich mit dem Bildschirmfoto.

**Naheliegende Behebung:** als Elternteil `self.window()` übergeben
statt `self`. Dann hängt der Dialog am Fenster und erbt nur dessen
Stylesheet.

**Noch zu prüfen:**

- Ob die Farbe danach weiterhin richtig übernommen wird.
- Ob der Dialog auf dem richtigen Bildschirm und mittig erscheint.
- Ob die `border`-Zeile auf dem Farbfeld überhaupt nötig ist, oder ob
  ein `QFrame` mit `setFrameShape` dasselbe ohne Stylesheet leistet —
  dann verschwindet die Ursache statt nur ihre Wirkung.

---

## 2. Dieselbe Falle bei acht weiteren Dialogen

**Beobachtet:** Nicht geprüft, nur gefunden. Acht weitere Stellen
übergeben `self` als Elternteil an einen Dialog:

| Datei | Zeile | Dialog |
|---|---|---|
| `ide/database/panel.py` | 143 | Datenbankdatei wählen |
| `ide/database/panel.py` | 209 | CSV-Datei wählen |
| `ide/database/panel.py` | 253 | CSV exportieren |
| `ide/database/panel.py` | 272 | SQL-Dump exportieren |
| `ide/project/neu_dialog.py` | 74 | Übergeordneter Ordner |
| `ide/shell/hauptfenster.py` | 1067 | Öffnen |
| `ide/shell/hauptfenster.py` | 1963 | Gehe zu Zeile |
| `ide/shell/hauptfenster.py` | 2772 | Paket installieren |

**Noch zu prüfen:** Ob das jeweilige `self` ein eigenes Stylesheet
trägt. Beim Hauptfenster ist das der Fall (`ide_qss_erzeugen`), dort
ist es aber gewollt — der Dialog soll aussehen wie die IDE. Gefährlich
ist nur der Fall aus Punkt 1: ein Elternteil, dessen Stylesheet für
genau ein kleines Widget gedacht war.

Das ließe sich einmal grundsätzlich prüfen: jeden Dialog aufmachen,
ansehen, und wo nötig auf `self.window()` umstellen.

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
