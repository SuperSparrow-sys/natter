# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **658**.

## Ein neuer Punkt

```markdown
## 658. Kurz, was nicht stimmt

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

## 653. Klappmenü-Kürzel wirken nicht an Komponenten, die in einer Liste stehen

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand f163469. Rückschritt durch Punkt 623 (Commit 3f1ed41).

**Beobachtet:** Ein Formular legt drei Knöpfe in einer Schleife an und speichert sie in `self.knoepfe`. Jeder bekommt `k.popup_menu = self.pm`, und das Klappmenü hat den Eintrag „Löschen“ mit „Strg+K“. Der Fokus liegt auf `knoepfe[1]`, dann wird Strg+K gedrückt: Die Methode wird nicht aufgerufen (`Aufrufe: []`). Auf dem Stand 2376f1d lief sie (`Aufrufe: [1]`). Der Rechtsklick öffnet das Menü weiterhin, nur das Kürzel bleibt ohne Wirkung und ohne Meldung. Komponenten in Listen sind im Unterricht üblich, etwa bei einem Spielfeld aus Knöpfen.

**Ursache:** nachgewiesen. `PopupMenu._komponenten` in `pcl/components/menus.py` (Zeile 766 bis 779) sucht die zugeordneten Komponenten nur unter `vars(self._formular)`. Eine Komponente, die nur in einer Liste oder einem Wörterbuch steht, findet es dort nicht, und `_menue_erneuern` meldet für sie kein Kürzel an. Seit Punkt 623 gilt ein Klappmenü-Kürzel nur noch an den Komponenten, die `_komponenten` liefert. Vorher galt es im ganzen Fenster.

**Zu tun:** Die zugeordneten Komponenten über die Zuordnung selbst bestimmen, etwa indem der Setter `popup_menu` die Komponente beim Klappmenü einträgt, oder über alle Kind-Widgets des Formulars. Erledigt, wenn ein Test mit Knöpfen in einer Liste das Kürzel an jedem Knopf auslöst.

## 654. Klassen-Code: Startwert „0,5“ wird bei modelliertem Konstruktor still zum Tupel

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand f163469. Rückschritt durch Punkt 606 (Commit 30729ea): seitdem entsteht die Zuweisung, vorher fehlte sie ganz.

**Beobachtet:** Die Klasse `Konto` hat die Attribute `-inhaber: str` und `-zins: float = 0,5` und die Operation `+__init__(inhaber: str)`. Erzeugt wird `self.__zins = 0,5`. Natter meldet nichts, und `vars(Konto("Anna"))` ergibt `{'_Konto__inhaber': 'Anna', '_Konto__zins': (0, 5)}`. Eine Rechnung mit dem Zinssatz bricht dann mit `TypeError` ab. Ohne modellierten Konstruktor meldet Natter in diesem Fall richtig „Der erzeugte Code lässt sich nicht übersetzen“. „0,5“ mit Komma ist die Schreibweise, die eine Schülerin von sich aus wählt.

**Ursache:** nachgewiesen. `_zuweisungen_fuer_init` in `ide/diagramm/klassen_code.py` (um Zeile 490) übernimmt den Startwert unverändert. Die Prüfung über `ausdruck_pruefen` und `ungueltige_namen` lässt „0,5“ durch, weil es als Python-Ausdruck gültig ist, nämlich als Tupel. Dasselbe gilt für ein Klassenattribut mit „0,5“.

**Zu tun:** Einen Startwert, der als Tupel aus Zahlen gelesen würde, wie im Struktogramm als Kommazahl schreiben oder mit einer Meldung ablehnen, die auf das Komma hinweist. Erledigt, wenn ein Test mit „0,5“ bei modelliertem Konstruktor entweder `0.5` erzeugt oder eine Meldung bekommt.

## 655. Struktogramm-Code: Bedingungen mit „und“, „oder“, „nicht“ werden zu `if False`

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand f163469. Kein Rückschritt, auf 2376f1d ebenso.

**Beobachtet:** Die Verzweigung „jahr % 4 = 0 und jahr % 100 != 0 oder jahr % 400 = 0“ (Schaltjahr) ergibt `# jahr % 4 = 0 und …` und darunter `if False:`. Ebenso wird „x > 0 UND x < 10“ zu `if False:`. Das erzeugte Programm läuft, nimmt aber immer den Nein-Zweig. Über dem Code steht nur, dass eine Zeile nicht übernommen wurde. Im Struktogramm sind „und“, „oder“ und „nicht“ die übliche Schreibweise für zusammengesetzte Bedingungen. „wahr“, „falsch“, „←“ und ein einzelnes „=“ übersetzt Natter schon, diese drei Wörter nicht.

**Ursache:** nachgewiesen. `ide/diagramm/struktogramm_code.py` kennt keine Übersetzung der Wörter „und“, „oder“ und „nicht“. Ein `grep` nach ihnen findet nichts. `_bedingungstext` und `_als_ausdruck` (um Zeile 1246) verwerfen die Bedingung deshalb als Nicht-Python und setzen den Platzhalter `False` ein.

**Zu tun:** „und“, „oder“ und „nicht“ als ganze Wörter außerhalb von Texten in Anführungszeichen, unabhängig von Groß- und Kleinschreibung, in `and`, `or` und `not` übersetzen, wenn der Name im Struktogramm keinen Wert bekommt, und im Handbuch nennen. Erledigt, wenn ein Test das Schaltjahr-Struktogramm ausführt und für 2000, 1900 und 2024 das richtige Ergebnis bekommt.

## 656. Struktogramm-Code: eine Eingabe, die nur als Listenindex dient, bleibt Text

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand f163469. Bezug: Punkt 643, dessen Kriterium nur den Fall mit zusätzlichem Vergleich „i < 3?“ abdeckt. Kein Rückschritt.

**Beobachtet:** „Eingabe: i“, „liste ← [1, 2, 3]“, „Ausgabe: liste[i]“ ergibt `i = input("i? ")` und `print(liste[i])`. Ausgeführt endet das mit `TypeError: list indices must be integers or slices, not str`. Das Handbuch (Abschnitt zum Diagramm-Editor) sagt, `zahl_lesen` sorge dafür, „dass eine eingelesene Zahl auch als Listenindex taugt“.

**Ursache:** nachgewiesen. `_als_zahl_benutzt` in `ide/diagramm/struktogramm_code.py` (Zeile 1041 bis 1067) zählt einen Namen nur neben Rechen- und Vergleichszeichen als Zahl. Ein Name in eckigen Klammern hinter einem anderen Namen zählt nicht.

**Zu tun:** Einen Namen, der als Index `name[i]` benutzt wird, als Zahl werten. Erledigt, wenn ein Test das Beispiel oben mit der Eingabe 1 ausführt und „2“ ausgegeben wird.

## 657. Debugger: Haltezeile steht nach einer Änderung im Halt auf der falschen Zeile

**Gemeldet:** 3. Oktober 2026, Durchsicht vor 0.4.4, Stand f163469. Kein Rückschritt, wird aber erst seit Punkt 645 sichtbar, weil Haltepunkte nach einer Änderung im Halt jetzt an der richtigen Stelle halten.

**Beobachtet:** Mit echtem debugpy in einem Konsolenprojekt geprüft. Das Programm hält auf `summe = summe + i`. Oben wird eine Kommentarzeile eingefügt, dann ein Haltepunkt auf `x = i * 2` gesetzt (im Editor Zeile 5), Strg+S gedrückt und fortgesetzt. debugpy hält richtig an `x = i * 2`, gemeldet als Zeile 4 der geladenen Datei. Die gelbe Haltezeile und der Cursor stehen im Editor aber auf Zeile 4, also auf `summe = summe + i`. Im Aufrufstapel springt ein Klick ebenso eine Zeile zu hoch.

**Ursache:** nachgewiesen. `_haltezeile_zeigen` in `ide/shell/hauptfenster.py` (Zeile 9741 bis 9759) übernimmt `frame["line"]` unverändert. Punkt 645 rechnet nur in eine Richtung um, vom Editor auf den geladenen Text (`_zeilen_zur_datei(..., geladen=True)`). Für Zeilen, die debugpy meldet, fehlt die Umrechnung in die Gegenrichtung.

**Zu tun:** Zeilen aus Stapelrahmen über die umgekehrte Zuordnung auf den Editortext abbilden, für die Haltezeile, den Cursor beim Halt und den Aufrufstapel. Erledigt, wenn ein Test nach eingefügter Zeile im Halt die gelbe Zeile auf der Anweisung zeigt, an der das Programm hält.


# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
