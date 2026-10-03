# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **536**.

## Ein neuer Punkt

```markdown
## 536. Kurz, was nicht stimmt

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

## 534. Testlauf: Zugriffsverletzung beim Einrichten eines Tests nach einem Hauptfenster

**Gemeldet:** 3. Oktober 2026, Teststufe „prozess/debugger/rundlauf“ mit `-n 8`; Entwicklungsstand `65ac170` und die Änderungen der Punkte 521 bis 533.

**Beobachtet:** `tests/test_explorer_formular_diagramm_loeschen.py` bricht gelegentlich mit „Windows fatal exception: access violation“ ab. Der Absturz kommt in `pytestqt`, `_process_events`, beim Einrichten des vierten oder fünften Tests, also beim Abarbeiten von Ereignissen, die vom vorigen, schon geschlossenen Hauptfenster übrig sind. Gezählt, jeweils die ganze Datei einzeln gestartet: auf `HEAD` (`65ac170`, eigener Arbeitsbaum) 1 von 34 Läufen, mit den Änderungen 8 von 56. Ob der Unterschied echt ist, ist offen; `read_only` am StringGrid von Beispiel 06 ist es nicht (mit und ohne gleich oft). Mit einem Python-Ereignisfilter, der jedes Ereignis mitschreibt, trat er in 20 Läufen nicht auf.

**Ursache:** noch offen. Vermutlich ein Qt-Objekt, das zerstört wird, während noch ein Ereignis für es aussteht.

**Zu tun:** Den Empfänger des letzten Ereignisses vor dem Absturz bestimmen (etwa mit einem nativen Absturzabbild), die Ursache beheben. Erledigt, wenn die Datei 50-mal hintereinander ohne Absturz durchläuft.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
