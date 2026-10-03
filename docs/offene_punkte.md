# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **481**.

## Ein neuer Punkt

```markdown
## 481. Kurz, was nicht stimmt

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

## 475. Ohne Auswahl liefert `items[item_index]` still den letzten Eintrag

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `58d8df5`.

**Beobachtet:** Ist in einer `ListBox`, `ComboBox` oder `RadioGroup` nichts gewählt, ist `item_index` gleich -1. Die übliche Zeile `self.l_x.caption = self.lb_x.items[self.lb_x.item_index]` zeigt dann den letzten Eintrag an, ohne Fehler: bei den Einträgen a, b, c steht „c“ da, obwohl niemand etwas gewählt hat. Seit Punkt 166 gilt das auch für einen zu großen Index, der jetzt -1 wird; vorher endete er wenigstens mit einem `IndexError`.

**Ursache:** nachgewiesen. `Strings.__getitem__` (`pcl/strings.py`) reicht den Index an die Python-Liste weiter, und dort zählt -1 vom Ende. Probe: `k.items = ["a", "b", "c"]; k.item_index = 5; k.items[k.item_index]` ergibt `'c'` für alle drei Komponenten.

**Zu tun:** `Strings` lehnt einen negativen Index mit einer deutschen Meldung ab, die bei -1 sagt, dass nichts ausgewählt ist. Erledigt, wenn ein Test für alle drei Komponenten ohne Auswahl die Meldung statt des letzten Eintrags bekommt.

---

## 476. `ComboBox.item_index` behält negative Werte außer -1

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `58d8df5`.

**Beobachtet:** `cb.item_index = -2` bei den Einträgen a, b, c: angezeigt wird keine Auswahl, `cb.item_index` liest aber -2, und `cb.items[cb.item_index]` ergibt „b“. `ListBox` und `RadioGroup` setzen denselben Wert auf -1.

**Ursache:** nachgewiesen. `ComboBox._bei_prop_aenderung` (`pcl/components/standard.py`, Abschnitt `item_index`) ruft nur `setCurrentIndex` auf und liest die tatsächliche Auswahl nicht zurück, anders als die `ListBox` seit Punkt 166.

**Zu tun:** Nach `setCurrentIndex` den tatsächlichen Index übernehmen. Erledigt, wenn ein Test für `-2` den Wert -1 liest.

---

## 477. Farben werden im Code nicht geprüft

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `58d8df5`.

**Beobachtet:** `self.l_x.color = "rot"`, `"blau"`, `"ff0000"` oder `"#12"` wird ohne Meldung angenommen und bewirkt nichts. Ebenso bei `Edit.color`, `Panel.color`, der Farbe des Formulars und `Shape.brush.color`. `self.l_x.font.color = "rot"` dagegen meldet „„rot“ ist keine Farbe. Erwartet wird #RRGGBB, z. B. #e53935 für Rot.“, und der Objektinspektor lehnt ungültige Farben ebenfalls ab.

**Ursache:** nachgewiesen. Ein `Prop` mit `art=ART_FARBE` (`pcl/properties.py`) prüft nur den Typ `str`; die Prüfung mit `QColor.isValidColorName` steht nur in `Font.color` (`pcl/font.py`) und in `EigenschaftenTabelle` (`ide/inspector/eigenschaften_tabelle.py`). Ungültige Farben übergeht Qt im Stylesheet ohne Meldung.

**Zu tun:** Jede Farbeigenschaft prüft beim Setzen wie `font.color` und meldet eine ungültige Farbe auf Deutsch. Erledigt, wenn ein Test für jede Farbeigenschaft „rot“ mit dieser Meldung ablehnt und „#ff0000“ annimmt.

---

## 478. `Label.color` zeigt nichts, solange `transparent` gilt

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `58d8df5`.

**Beobachtet:** Ein Label ist von Haus aus durchsichtig. `self.l_x.color = "#ff0000"` im Code oder eine Farbe im Objektinspektor ändert deshalb nichts; erst `transparent = False` dazu zeigt den Hintergrund. Der Hinweis steht nur im Tooltip der Eigenschaft („nur bei transparent=False“).

**Ursache:** nachgewiesen. `Label._qss_teile` (`pcl/components/standard.py`) setzt den Hintergrund nur bei `not self.transparent and self.color`.

**Zu tun:** Eine gesetzte Farbe schaltet `transparent` aus, im Code wie im Objektinspektor; `transparent = True` danach macht das Label wieder durchsichtig. Erledigt, wenn ein Test nach `color = "#ff0000"` den Hintergrund im Stylesheet findet und `docs/komponenten.md` das beschreibt.

---

## 479. `zahl("1,234.5")` ergibt 1,2345

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `58d8df5`.

**Beobachtet:** Eine englisch geschriebene Zahl mit Komma als Tausendertrennung und Punkt als Dezimalzeichen wird still als 1,2345 gelesen. Erwartet wäre 1234,5 oder eine Meldung, dass die Schreibweise nicht eindeutig ist.

**Ursache:** nachgewiesen. `zahl` (`pcl/zahlen.py`) entfernt bei Punkt und Komma zugleich immer die Punkte, ohne auf ihre Reihenfolge zu sehen.

**Zu tun:** Steht der Punkt hinter dem letzten Komma, ist die Zahl keine deutsche Schreibweise; `zahl` meldet das. Erledigt, wenn ein Test „1,234.5“ mit Meldung ablehnt und „1.234,5“ weiter 1234,5 ergibt.

---

## 480. Die Meldung zu `None` lautet „ein NoneType (NoneType)“

**Gemeldet:** 3. Oktober 2026, Durchsicht, Entwicklungsstand `58d8df5`.

**Beobachtet:** `self.l_x.caption = None`, etwa das Ergebnis einer Funktion ohne `return`, meldet „Label.caption erwartet einen Text (str), erhalten wurde ein NoneType (NoneType).“ Wer Python gerade lernt, kennt `NoneType` nicht und erfährt nicht, dass nichts zurückgegeben wurde.

**Ursache:** nachgewiesen. `_TYPNAMEN` in `pcl/properties.py` hat keinen Eintrag für `type(None)`; `typ_beschreibung` fällt auf den Namen der Klasse zurück.

**Zu tun:** Ein Eintrag für `None`, etwa „kein Wert (None)“, und in der Meldung der Hinweis, dass eine Funktion ohne `return` `None` liefert. Erledigt, wenn ein Test diese Meldung findet.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
