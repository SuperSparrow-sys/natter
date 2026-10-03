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

**Ursache:** zur Hälfte nachgewiesen.

1. Die Erfassung der Qt-Meldungen durch pytest-qt. Es hängt für jeden Test einen eigenen Handler ein und setzt danach den vorigen wieder ein; beim Einrichten des nächsten Tests arbeitet es die Ereignisse ab, bevor der neue Handler steht. Eine Qt-Meldung aus dem Abbau des vorigen Fensters (offscreen etwa „This plugin does not support raise()“) ließ den Prozess dann abstürzen. Mit `--no-qt-log` sank die Rate von etwa einem in sechs Läufen auf 1 von 40. Kein Test braucht die Fixture `qtlog`; seit 3. Oktober 2026 steht `--no-qt-log` in `addopts` (`pyproject.toml`).
2. Der Rest liegt in C++. `_fenster_des_tests_aufraeumen` in `tests/conftest.py` arbeitet jetzt nach dem Löschen der Fenster auch die übrigen Ereignisse ab; seitdem kommt der verbleibende Absturz (1 von 60 Läufen) dort, im Abbau nach `test_formular_loeschen_ueber_seine_unit`, und nicht mehr neben dem nächsten Hauptfenster. Ein Protokoll aller Python-Aufrufe zeigt davor keinen Python-Rückruf mehr. Geprüft und ausgeschlossen: das StringGrid mit `read_only` aus Beispiel 06, die Speicherbereinigung (mit erzwungenem `gc.collect()` nach jedem Test 2 von 30), ein doppeltes Löschen aus Python (nach dem Löschen des Formulars sind Formular, Anfasser, Rahmen und Raster ungültig und keines gehört noch Python), Nebenfäden (nur der von pytest-timeout und der Leser von jedi laufen).

**Zu tun:** Mit einem nativen Debugger (WinDbg/cdb) den C++-Aufrufstapel des verbleibenden Absturzes lesen und die Ursache beheben. Erledigt, wenn die Datei 100-mal hintereinander ohne Absturz durchläuft.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
