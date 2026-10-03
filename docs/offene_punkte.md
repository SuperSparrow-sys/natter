# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **475**.

## Ein neuer Punkt

```markdown
## 475. Kurz, was nicht stimmt

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

## 469. Der Knopf eines gestarteten Programms heißt in der Taskleiste „Python“

**Gemeldet:** 2. Oktober 2026, Prüfung der installierten Fassung 0.4.3 (`build\auswertung\043\`, Bild `03_e_taskleiste_knopf2_lupe.png`).

**Beobachtet:** Beim ersten Programmlauf nach der Installation zeigt der Knopf des Programms die Natter, heißt über UI Automation aber „Python – 1 aktives Fenster“. Der Knopf der IDE heißt seit Punkt 416 „Natter“.

**Ursache:** vermutet. `pcl.Application` meldet sich unter der Kennung `Natter.Programm` an. Für sie gibt es keine Verknüpfung, aus der Windows einen Namen nehmen könnte, deshalb gilt die Dateibeschreibung von `python.exe`.

**Zu tun:** Der Kennung einen Anzeigenamen geben, etwa über einen Eintrag `HKCU\Software\Classes\AppUserModelId\Natter.Programm` (`DisplayName`, `IconUri`), den das Setup schreibt und die Deinstallation entfernt. Erledigt, wenn ein Bildschirmfoto der Taskleiste beim Programmlauf einen Knopf mit einem Namen zeigt, der zu Natter gehört.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
