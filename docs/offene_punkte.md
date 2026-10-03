# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **540**.

## Ein neuer Punkt

```markdown
## 540. Kurz, was nicht stimmt

**Gemeldet:** Datum, wo es auffiel (Fenster, Menü, Beispielprojekt),
Natter-Version.

**Beobachtet:** Was passiert ist und was stattdessen zu erwarten war.
Wörtlich übernommene Meldungen in Anführungszeichen.

**Ursache:** noch offen - oder nachgewiesen, mit Datei und Zeile.

**Zu tun:** Was geändert werden muss und woran das Erledigtsein zu
erkennen ist.
```

---

# Offen

## 536. Eine Unit oder ein Formular darf heißen wie ein Python-Modul und verdeckt es

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `fe45604`.

**Beobachtet:** In `02_Zahlenraten` (Kopie) wird eine neue Unit über „⋮ → Umbenennen …“ in `random` umbenannt. Natter nimmt den Namen an („„u_neu1.py“ zu „random.py“ umbenannt“). Die Prüfung vor dem Start meldet nichts, und das Programm bricht beim Start ab: „AttributeError: module 'random' has no attribute 'randint' (consider renaming …random.py since it has the same name as the standard library module …)“. `import random` in `u_main.py` holt jetzt die eigene Datei. Dasselbe gilt für `math`, `time`, `string` und ebenso für `pcl`, womit jedes Formular-Projekt bricht. Im Unterricht liegen solche Namen nahe: eine Unit `random` für eine Übung mit Zufallszahlen. Punkt 445 hat dasselbe Problem nur für Debugger und Exe-Export gelöst; das Schülerprogramm selbst bleibt betroffen.

**Ursache:** nachgewiesen. `_unit_umbenennen` (`ide/shell/hauptfenster.py`, um Zeile 3258) prüft nur `isidentifier()`, `keyword.iskeyword()` und die Endung `_design`; `_formularname_fehler` (um Zeile 2421) prüft für „Neues Formular …“ und das Umbenennen eines Formulars ebenso nur diese Punkte. `sys.stdlib_module_names` und die Namen installierter Pakete wie `pcl` werden nicht abgefragt, und `projekt_pruefen` (`ide/run/pruefung.py`) kennt keine Regel dafür.

**Zu tun:** Beim Anlegen und Umbenennen von Units und Formularen einen Namen ablehnen, der ein Modul der Standardbibliothek oder ein mitgeliefertes Paket (`pcl`, `pandas`, `matplotlib` …) verdeckt, mit einem Satz, der den Grund nennt und einen Namen wie `u_random` vorschlägt; für eine von außen hineinkopierte Datei mit solchem Namen einen Hinweis in der Prüfung vor dem Start. Erledigt, wenn ein Test das Umbenennen in `random` und das Anlegen eines Formulars `math` abgelehnt sieht.

## 537. Rückgängig nach dem Anlegen einer Ereignis-Methode lässt die leere Methode in der Unit stehen

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `fe45604`.

**Beobachtet:** Im Designer (Kopie von `03_Taschenrechner`) legt ein Doppelklick auf `l_titel` die Methode `l_titel_click` mit dem Rumpf „Hier steht, was passieren soll.“ in `u_main.py` an und verknüpft sie in der `.pfm`. Ein Strg+Z nimmt die Verknüpfung zurück, der Rückgängig-Stapel ist danach leer, die leere Methode steht aber weiter in der Unit. Ebenso bleibt die leere Methode stehen, wenn die Komponente danach gelöscht wird. Nach einer längeren Folge mit vollständigem Rückgängig ist die `.pfm` wieder wie vorher, die Unit nicht. So ein Rest stand bis zum 3. Oktober 2026 eingecheckt in `beispielprojekte/09_ObstSortierer/u_main.py` (`ch_streuung_click`, Punkt 531).

**Ursache:** nachgewiesen. `ereignis_handler_erzeugen` (`ide/designer/canvas.py`, ab Zeile 2605) schreibt die Methode direkt in die Unit und legt auf den Stapel nur ein `EigenschaftKommando` für die Verknüpfung; das Rückgängigmachen kennt die geschriebene Methode nicht.

**Zu tun:** Eine Methode, die der Designer gerade angelegt hat und deren Rumpf noch unverändert ist, beim Rückgängigmachen mit entfernen; beim Löschen einer Komponente leere, nicht mehr verknüpfte Methoden mit entfernen oder zumindest nennen. Selbst geschriebener Code bleibt immer stehen. Erledigt, wenn ein Test nach Doppelklick und Strg+Z die Unit unverändert findet.

## 538. Struktogramm: Blöcke lassen sich nur mit Strg+Ziehen kopieren, das Menü bleibt grau

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `fe45604`.

**Beobachtet:** Im Struktogramm-Editor sind „Bearbeiten → Ausschneiden“, „Kopieren“, „Einfügen“ und „Duplizieren“ auch dann ausgegraut, wenn ein Block ausgewählt ist; Strg+C, Strg+V und Strg+D wirken nicht, das Kontextmenü eines Blocks bietet nur „Beschriften …“, „Löschen“ und die Befehle für Fälle und Stränge. Kopieren geht allein, indem der Block mit gedrückter Strg-Taste an eine andere Stelle gezogen wird. Das Handbuch, Abschnitt 3.4, nennt nur das Ziehen zum Verschieben. Wer eine Ausgabe oder eine ganze Schleife ein zweites Mal braucht, muss sie neu bauen.

**Ursache:** nachgewiesen. `StruktogrammCanvas.block_kopieren` (`ide/diagramm/struktogramm_canvas.py`, Zeile 922) wird nur in `mouseReleaseEvent` (Zeile 1030) bei gedrückter Strg-Taste aufgerufen; `kontextmenue_fuer` (ab Zeile 748) und die Menüeinträge des Fensters verbinden Kopieren und Einfügen für diesen Diagrammtyp nicht. Probe: Block einfügen, auswählen, Menü „Bearbeiten“ öffnen: `Kopieren`, `Einfügen`, `Duplizieren` haben `isEnabled() == False`.

**Zu tun:** Kopieren, Ausschneiden, Einfügen (an der gewählten Einfügestelle oder hinter dem ausgewählten Block) und Duplizieren für Blöcke anbieten, mit den üblichen Tastenkürzeln, und Strg+Ziehen im Handbuch nennen. Erledigt, wenn ein Test einen Block über Strg+C und Strg+V verdoppelt und Strg+Z das zurücknimmt.

## 539. Klassendiagramm: Vorlagenparameter lassen sich einstellen, erscheinen aber nicht im Diagramm

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `fe45604`.

**Beobachtet:** Im Eigenschaften-Dialog einer Klasse lässt sich „Vorlagenklasse“ ankreuzen und ein Parameter wie `T` anlegen; gespeichert wird beides als `template` und `template_parameters`, und der Codeerzeuger verwendet es. Im gezeichneten Diagramm, im PNG- und im PDF-Export ändert sich dadurch nichts: Probe mit `als_bild` vor und nach dem Setzen von `template = True` und `template_parameters = [{"name": "T"}]` ergibt zwei gleiche Bilder (216 × 160). Wer eine Liste `Liste<T>` modelliert, sieht das im Diagramm nicht.

**Ursache:** nachgewiesen. `ide/diagramm/zeichnen.py` und `ide/diagramm/uml_modell.py` lesen `template` und `template_parameters` nicht (`grep` ohne Treffer); nur `klassendialog.py` und `klassen_code.py` tun es.

**Zu tun:** Die Parameter so zeichnen, wie es für Vorlagenklassen üblich ist (gestricheltes Kästchen an der rechten oberen Ecke der Klasse mit `T`), in Bild- und PDF-Export ebenso. Erledigt, wenn ein Test zwei verschiedene Bilder findet.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
