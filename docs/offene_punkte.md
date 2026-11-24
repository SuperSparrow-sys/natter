# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **708**.

## Ein neuer Punkt

```markdown
## 708. Kurz, was nicht stimmt

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

## 702. Klausur aus einem Beispiel: der Hinweis nennt nur eine von mehreren übernommenen Dateien, nach ihrer Änderung bleibt die Klausur im Prüfungsmodus gesperrt (hoch)

**Gemeldet:** 24. November 2026, Nachprüfung 668-701, Stand `a8fe954`.
Wiederkehr von Punkt 668.

**Beobachtet:** Klausur aus `06_Kontoverwaltung` wie in Punkt 668:
`u_main.py` geändert, `u_konto.py` und die drei Diagramme unverändert.
Beim Öffnen außerhalb des Modus kommt der neue Hinweis „„u_konto.py“ in
„Klausur“ gleicht einer Datei aus dem Beispiel „06_Kontoverwaltung“. …
Gilt es als Aufgabe für eine Prüfung, genügt eine kleine Änderung an
der Datei, etwa ein Kommentar.“ Die Lehrkraft ergänzt in `u_konto.py`
einen Kommentar und öffnet das Projekt im selben Natter-Fenster erneut:
kein weiterer Hinweis. Im Prüfungsmodus ist die Klausur trotzdem
gesperrt, jetzt mit „„Klausur“ enthält „konto_abheben.pdiag“
unverändert aus dem Beispiel …“. Der Modus läuft dann vier Stunden,
die Klausur lässt sich an diesem Tag nicht in Natter schreiben, wie in
Punkt 668. Handbuch 4 verlangt zwar, jede übernommene Datei zu ändern;
der Hinweis in Natter spricht aber von „der Datei“ und nennt nur eine.

**Ursache:** nachgewiesen. `beispiel_datei_nach_inhalt`
(`ide/shell/startbild.py:454`, Rückgabe in Zeile 479) liefert nur den
ersten Treffer; `_beispiel_inhalt_nennen`
(`ide/shell/hauptfenster.py:4939`) merkt sich in `_beispiel_hinweise`
(Zeile 4945) den Ordner, nicht die Datei, und zeigt nach der Änderung
nichts mehr. Nachweis:
`build\auswertung\nachpruefung_a8fe954\n9_klausur_zweite_datei.py`.

**Zu tun:** Der Hinweis nennt alle Dateien, die ein Beispiel unverändert
enthalten, und kommt wieder, solange noch eine übrig ist. Erledigt, wenn
der Nachweis im Hinweis `u_konto.py` und die drei Diagramme findet und
nach Änderung nur von `u_konto.py` beim nächsten Öffnen erneut einen
Hinweis mit den Diagrammen bekommt.

---

## 703. Der Hinweis „Im Prüfungsmodus gesperrt“ erscheint auch Schülerinnen und Schülern, bei jedem Start von Natter wieder (gering)

**Gemeldet:** 24. November 2026, Nachprüfung 668-701, Stand `a8fe954`.
Nebenwirkung der Behebung von Punkt 668.

**Beobachtet:** Eine Lehrkraft verteilt im normalen Unterricht eine
Aufgabe auf Grundlage von `06_Kontoverwaltung` mit unveränderter
`u_konto.py`. Jede Schülerin, die ihre Kopie öffnet, bekommt außerhalb
des Prüfungsmodus die Meldung „Im Prüfungsmodus gesperrt“ mit dem Rat,
die Datei zu ändern, wenn das Projekt „als Aufgabe für eine Prüfung“
gilt. Die Meldung richtet sich an die Lehrkraft, mit der Arbeit der
Klasse hat sie nichts zu tun. Gemerkt wird sie nur im offenen Fenster:
nach jedem Neustart von Natter kommt sie beim ersten Öffnen wieder, in
der Probe dreimal in drei Sitzungen.

**Ursache:** nachgewiesen. `projekt_oeffnen_gemeldet`
(`ide/shell/hauptfenster.py:4912`) ruft `_beispiel_inhalt_nennen` für
jedes Projekt außerhalb des Modus, gleich wer es öffnet und ob es eine
Kopie einer Aufgabe ist; `_beispiel_hinweise` (Zeile 4945) lebt nur im
Fenster. Nachweis:
`build\auswertung\nachpruefung_a8fe954\n1_beispielhinweis_bei_schuelern.py`.

**Zu tun:** Den Hinweis nicht bei der Kopie einer Aufgabe
(`aufgabe_original` gesetzt) zeigen und das Gezeigte über den Neustart
hinaus merken, etwa in den Einstellungen mit dem Fingerabdruck der
Datei. Erledigt, wenn der Nachweis für die Kopie einer Aufgabe keinen
Hinweis mehr findet und der Test zu Punkt 668 grün bleibt.

---

## 704. Nach dem Update auf diesen Stand gilt jede Kopie einer Aufgabe mit `.lehrkraft`, `build` oder `dist` als Kopie einer geänderten Aufgabe (gering)

**Gemeldet:** 24. November 2026, Nachprüfung 668-701, Stand `a8fe954`.
Nebenwirkung der Behebung von Punkt 690.

**Beobachtet:** Eine Schülerkopie, angelegt mit dem Stand vor Punkt 690
aus einer Aufgabe, deren Ordner `.lehrkraft`, `build`, `dist` oder einen
anderen versteckten Eintrag enthält: nach dem Update meldet
`aufgabe_geaendert` die Aufgabe als geändert, obwohl die Lehrkraft
nichts geändert hat. Beim nächsten Öffnen der Aufgabe kommt für jede
solche Kopie einmal „Aufgabe wurde geändert“ mit „Eigene Kopie öffnen“
und „Kopie ersetzen“. Wer „Kopie ersetzen“ wählt, bekommt die Aufgabe
neu, die eigene Arbeit liegt danach in „… (vorher)“. Ohne solche
Einträge im Aufgabenordner bleibt es still. Betroffen sind gerade die
Klassen, deren Lehrkraft Notizen in `.lehrkraft` oder eine Exe in
`dist` neben der Aufgabe liegen hat.

**Ursache:** nachgewiesen. `_NICHT_MITKOPIEREN`
(`ide/shell/startbild.py:191`) gilt auch für `_fingerabdruck` (Zeile
602). Der in `.natter-quelle` gespeicherte Fingerabdruck einer alten
Kopie enthält die jetzt weggelassenen Einträge, `neuer_aufgabenstand`
(Zeile 696) findet deshalb einen anderen Stand. Nachweis:
`build\auswertung\nachpruefung_a8fe954\n3_fingerabdruck_nach_update.py`
(alte Kopie mit der Ausschlussliste von `66d1450` nachgestellt).

**Zu tun:** Einen Fingerabdruck, der nur durch die neu weggelassenen
Einträge abweicht, als unverändert werten, etwa indem beim Vergleich
auch der Fingerabdruck nach der alten Liste gebildet wird, solange die
Kopie ihn trägt. Erledigt, wenn der Nachweis für `.lehrkraft` und
`dist` „nicht geändert“ findet und eine echte Änderung an `main.py`
weiter als Änderung erkannt wird.

---

## 705. Eine Datei außerhalb des Projekts, die vor dem Projekt geöffnet wurde, heißt im Reiter wie die Unit des Projekts (gering)

**Gemeldet:** 24. November 2026, Nachprüfung 668-701, Stand `a8fe954`.
Verweis auf Punkt 674.

**Beobachtet:** Ohne offenes Projekt `u_main.py` vom Desktop öffnen,
danach ein GUI-Projekt öffnen und dessen `u_main.py`: zwei Reiter
heißen „u_main.py“. Der Reiter der Datei vom Desktop bekommt den Ordner
nicht dazu, obwohl sie jetzt außerhalb des offenen Projekts liegt.
Punkt 674 wollte genau das verhindern, dass zwei Reiter verschiedener
Dateien gleich heißen; wird der falsche Reiter bearbeitet, startet das
Programm ohne diese Änderungen.

**Ursache:** nachgewiesen. `_reiter_titel`
(`ide/shell/hauptfenster.py:5736`) wird nur beim Öffnen der Datei,
beim Ändern-Merker und nach „Speichern unter …“ angewandt;
`projekt_oeffnen` frischt die Namen offener Reiter nicht auf. Nachweis:
`build\auswertung\nachpruefung_a8fe954\n7_reiter_ausserhalb.py`.

**Zu tun:** Nach dem Öffnen, Wechseln und Schließen eines Projekts die
Namen aller Text-Reiter mit `_reiter_titel` neu setzen. Erledigt, wenn
der Nachweis zwei verschiedene Reiternamen findet.

---

## 706. Speichern scheitert: beim Schreiben der Unit durch den Designer weiter „[Errno 2] No such file or directory“, im Diagrammfenster englischer Text (gering)

**Gemeldet:** 24. November 2026, Nachprüfung 668-701, Stand `a8fe954`.
Verweis auf Punkt 675.

**Beobachtet:** USB-Stick abgezogen oder Datenträger voll, nachgestellt
wie im Test zu Punkt 675. Doppelklick auf einen Knopf im Designer, der
die Methode in `u_main.py` anlegen will: „„u_main.py“ konnte nicht
gespeichert werden: [Errno 2] No such file or directory. Die Methode
lässt sich deshalb nicht anlegen.“, beim vollen Datenträger „[Errno 28]
No space left on device“. Beim echten Fehler steht dort zusätzlich der
Name der Zwischendatei, wie in Punkt 675 beschrieben. Das Diagrammfenster
meldet „konto_klassen.pdiag lässt sich nicht speichern: No such file or
directory.“ bzw. „No space left on device.“, ohne Fehlernummer, aber
englisch. Editor und `.pfm` melden seit Punkt 675 einen deutschen Satz.

**Ursache:** nachgewiesen. `DesignerCanvas._unit_schreiben`
(`ide/designer/canvas.py:3062`, Meldung Zeile 3074) und das Umbenennen
(Zeile 2816) setzen den Fehler unverändert ein;
`DiagrammFenster._speicherfehler_melden` (`ide/diagramm/fenster.py:1412`)
nimmt `strerror`. `schreibfehler_grund` aus `ide/atomar.py` wird dort
nicht benutzt. Nachweis:
`build\auswertung\nachpruefung_a8fe954\n11_speicherfehler_andere_wege.py`.

**Zu tun:** Auch hier `schreibfehler_grund` einsetzen, wie in
`datei_schreiben_gemeldet`. Erledigt, wenn der Nachweis in keiner der
vier Meldungen „Errno“, „.tmp“ oder einen englischen Text findet.

---

## 707. F5: bei vielen Zeilen von `print()` kommt nur ein Teil im Panel „Ausgabe“ an (gering)

**Gemeldet:** 24. November 2026, Nachprüfung 668-701, Stand `a8fe954`.
Verweis auf Punkt 686.

**Beobachtet:** Ein Programm mit Fenster gibt in `form_create` 20.000
Zeilen mit `print()` aus und schließt sich 0,1 s danach. Mit Strg+F5
stehen im Panel die letzten 5.000 Zeilen bis „Zeile 19999“ und
„Programm beendet“. Mit F5 endet die Ausgabe in drei Läufen bei „Zeile
4241“ bis „Zeile 5191“; was danach kam, fehlt ohne Hinweis, und die
letzte Zeile ist teils abgeschnitten („Zeile“). Wer die letzten Werte
einer Schleife sucht, sieht also ältere Zeilen und hält sie für das
Ende. Bei 50 und 2.000 Zeilen kam alles an. Die Oberfläche stand dabei
nie länger als 0,13 s still.

**Ursache:** Wirkung nachgewiesen, Mechanismus vermutet. Schon
`DebugSitzung._ausgabe_verarbeiten`
(`ide/debugger/debug_sitzung.py:340`) bekommt nur rund 4.200 der
20.000 Zeilen; vermutlich schickt debugpy beim Programmende die
restlichen Ereignisse `output` nicht mehr, oder sie gehen nach
`terminated` (Zeile 332) verloren. Nachweis:
`build\auswertung\nachpruefung_a8fe954\n5_printflut_unter_f5.py`.

**Zu tun:** Ursache klären. Gehen Zeilen verloren, im Panel darauf
hinweisen (etwa „Ein Teil der Ausgabe fehlt, mit Strg+F5 erscheint sie
vollständig.“) oder die Ausgabe auch unter F5 über ein Rohr lesen.
Erledigt, wenn der Nachweis mit 20.000 Zeilen unter F5 „Zeile 19999“
oder den Hinweis findet.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
