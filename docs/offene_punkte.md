# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **668**.

## Ein neuer Punkt

```markdown
## 668. Kurz, was nicht stimmt

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

## 758. Eine Klausur auf Grundlage eines Beispiels lässt sich im Prüfungsmodus nicht öffnen

**Gemeldet:** 24. November 2026, Prüfung D (Sicht der Lehrkraft),
Stand `42d5478`.

**Beobachtet:** Eine Lehrkraft baut eine Klausur aus
`06_Kontoverwaltung`: Ordner und Projektdatei heißen „Klausur“,
`u_main.py` trägt die Aufgabe, die Klasse `u_konto.py` und das
Klassendiagramm bleiben unverändert, weil sie erweitert werden sollen.
Die Klausur liegt in einem Tauschordner nur zum Lesen. Im
Prüfungsmodus öffnet eine Schülerin sie über „Projekt öffnen …“. Statt
der eigenen Kopie kommt „Beispielprojekt gesperrt“ mit dem Text
„„Klausur“ ist ein mitgeliefertes Beispielprojekt oder eine Kopie
davon. Während des Prüfungsmodus nicht verfügbar. Er läuft nach vier
Stunden von selbst aus.“ Das Projekt geht nicht auf, eine Kopie
entsteht nicht. Der Modus lässt sich vier Stunden lang nicht beenden,
die Klausur kann an diesem Tag also nicht in Natter geschrieben
werden. Die Meldung nennt nicht, welche Datei die Sperre auslöst, und
vorher prüfen kann die Lehrkraft das nur, indem sie den Modus im
eigenen Konto für vier Stunden einschaltet. Handbuch 4 beschreibt die
Erkennung am Inhalt, sagt aber nicht, dass eine Aufgabe mit einer
unveränderten Unit oder einem unveränderten Diagramm aus einem
Beispiel davon getroffen wird.

**Ursache:** nachgewiesen: `beispiel_nach_inhalt` in
`ide/shell/startbild.py:431` erkennt den Ordner an `u_konto.py`,
`_beispiel_projektordner` in `ide/shell/hauptfenster.py:644` sperrt ihn
deshalb. Nachweis:
`build\auswertung\pruefung_42d5478\D\758_klausur_aus_beispiel.py`.

**Zu tun:** Die Lehrkraft muss vor der Klausur erfahren, dass Natter
ihre Aufgabe im Prüfungsmodus sperren wird, und die Meldung im Modus
muss die auslösende Datei nennen. Handbuch 4 nennt den Fall bei den
Hinweisen für die Aufsicht. Erledigt, wenn die Probe entweder die
Klausur im Prüfungsmodus als eigene Kopie öffnet oder Natter beim
Öffnen der Aufgabe außerhalb des Modus darauf hinweist und die Meldung
im Modus `u_konto.py` nennt.

## 759. Lösung und Notizen der Lehrkraft im Aufgabenordner landen in jeder Schülerkopie

**Gemeldet:** 24. November 2026, Prüfung D (Sicht der Lehrkraft),
Stand `42d5478`.

**Beobachtet:** Im Aufgabenordner „Ampel“ eines Tauschordners nur zum
Lesen liegen neben der Aufgabe `loesung.py`, ein versteckter Ordner
`.lehrkraft` mit einer Notiz zur Bewertung, ein Unterordner `loesung`
mit einer fertigen `u_main.py` und der Ordner `dist` mit einer Exe aus
„Als Exe exportieren“. „Eigene Kopie öffnen“ kopiert alles davon nach
`Dokumente\Natter\Ampel`. Der Projekt-Explorer der Schülerin zeigt
`loesung.py` unter „Units“, die übrigen Dateien liegen im Ordner und
sind im Windows-Explorer zu sehen. Die Abgabe-ZIP lässt versteckte
Einträge, `build` und `dist` weg, die Kopie der Aufgabe nicht.
Handbuch 3.6 sagt nicht, dass Lösung und Notizen nicht in den
Aufgabenordner gehören.

**Ursache:** nachgewiesen: `_NICHT_MITKOPIEREN` in
`ide/shell/startbild.py:187` nimmt nur `__pycache__`, `*.pyc`,
Sperrdatei, Quelldatei und Sicherung aus; `zip_schreiben` in
`ide/shell/hauptfenster.py:771` lässt zusätzlich versteckte Einträge,
`build` und `dist` weg. `Projekt.units` in `ide/project/projekt.py:232`
zeigt jede `.py` im Projektordner. Nachweis:
`build\auswertung\pruefung_42d5478\D\759_loesung_in_kopie.py`.

**Zu tun:** Beim Kopieren einer Aufgabe dieselben Einträge weglassen
wie in der Abgabe-ZIP und in Handbuch 3.6 festhalten, dass alles
Übrige im Aufgabenordner zu jeder Schülerin kopiert wird. Erledigt,
wenn die Probe in der Kopie weder `.lehrkraft` noch `dist` findet und
das Handbuch den Satz enthält.

## 760. Druckt die Lehrkraft eingesammelte Abgaben als Quelltext-PDF, steht ihr eigener Name darauf

**Gemeldet:** 24. November 2026, Prüfung D (Sicht der Lehrkraft),
Stand `42d5478`.

**Beobachtet:** Die Lehrkraft entpackt zwei Abgaben
(`Ampel - schueler01 - PC-R01.zip`, `Ampel - schueler02 - PC-R02.zip`),
öffnet sie nacheinander und wählt „Projekt → Quelltext als PDF …“. Die
Kopfzeile beider PDFs lautet „Ampel – u_main.py – <Name der Lehrkraft>
– 24.11.2026“: der Name kommt aus der Anmeldung am Rechner der
Lehrkraft, der Projektname ist bei der ganzen Klasse gleich, und der
Ordnername der Abgabe mit dem Konto der Schülerin steht nirgends.
Beim Entpacken in einen gemeinsamen Ordner schlägt Natter für beide
Abgaben denselben Dateinamen `Ampel Quelltext.pdf` vor. Handbuch 3.6
begründet die Kopfzeile damit, dass bei zwanzig eingesammelten
Abgaben sonst nicht zu erkennen ist, welche zu wem gehört; das gilt
nur, wenn die Schülerinnen das PDF selbst erzeugen.

**Ursache:** nachgewiesen: `quelltext_als_pdf` in
`ide/export/quelltext_pdf.py:344` nimmt `anmeldename()` des
angemeldeten Kontos, `seitenkoepfe` (Zeile 289) den Projektnamen aus
der `.natter`; `_quelltext_als_pdf_aktion` in
`ide/shell/hauptfenster.py:2752` schlägt `<Projektname> Quelltext.pdf`
vor. Nachweis:
`build\auswertung\pruefung_42d5478\D\760_pdf_kopfzeile.py`.

**Zu tun:** Bei einer entpackten Abgabe muss Kopfzeile und
vorgeschlagener Dateiname die Abgabe erkennen lassen, etwa über den
Namen ihres Ordners. Erledigt, wenn die Probe für die beiden Abgaben
verschiedene Dateinamen vorgeschlagen bekommt und in jeder Kopfzeile
das Konto der Schülerin steht.

## 761. Am Beamer mit 1280 × 800 bei 125 % ist im Designer schon das Formular eines neuen Projekts abgeschnitten

**Gemeldet:** 24. November 2026, Prüfung D (Sicht der Lehrkraft),
Stand `42d5478`.

**Beobachtet:** Hauptfenster mit dem Beispiel 03_Taschenrechner im
Designer, logische Fenstergröße abzüglich Taskleiste und Titelleiste.
Sichtbare Fläche des Designers:

| Beamer 1280 × 800 | Fenster | Designer sichtbar |
|---|---|---|
| 100 % | 1280 × 720 | 872 × 424 |
| 125 % | 1024 × 576 | 604 × 280 |
| 150 % | 853 × 480 | 433 × 172 |
| 125 %, Oberfläche 14 pt | 1024 × 576 | 604 × 239 |

Ein neues GUI-Projekt hat ein Formular von 480 × 360, der
Taschenrechner 520 × 340, die Beispiele 04 bis 09 sind 560 bis 640
hoch. Bei 125 % fehlen dem leeren Formular 80 Pixel Höhe, beim
Taschenrechner liegen die Rechenknöpfe bei 150 % unter dem Rand
(`beamer_125_designer.png`, `beamer_150_designer.png`). Die
Vergrößerung der Oberfläche, die Handbuch 6 („Schrift am Beamer zu
klein“) empfiehlt, nimmt dem Designer weitere 41 Pixel. Komponentenpalette
und Panels belegen zusammen rund 200 Pixel Höhe. Punkt 348 hat das nur
für Konsolenprojekte gelöst.

**Ursache:** nachgewiesen: Aufteilung der Docks in
`ide/shell/hauptfenster.py`, geprüft wird sie nur für 1366 × 768
(`tests/test_schulrechner_layout.py`). Nachweis:
`build\auswertung\pruefung_42d5478\D\761_beamer_designer.py` mit den
Bildschirmfotos `beamer_*.png` daneben.

**Zu tun:** Dem Designer bei kleiner logischer Fenstergröße mehr Höhe
lassen. Erledigt, wenn die Probe bei 1024 × 576 eine sichtbare
Designerfläche von mindestens 480 × 360 misst, ohne dass ein Dock von
Hand geschlossen wurde.

## 762. „Datei → Zuletzt geöffnet“ zeigt eingesammelte Abgaben alle unter demselben Namen

**Gemeldet:** 24. November 2026, Prüfung D (Sicht der Lehrkraft),
Stand `42d5478`.

**Beobachtet:** Die Lehrkraft öffnet vier entpackte Abgaben
nacheinander. Die Startseite listet sie als
„Ampel - schueler04 - PC-R04“ bis „Ampel - schueler01 - PC-R01“, das
Menü „Datei → Zuletzt geöffnet“ viermal als „Ampel“. Welcher Eintrag zu
wem gehört, steht nur in der Statuszeile beim Überfahren.

**Ursache:** nachgewiesen: `_zuletzt_menue_aufbauen` in
`ide/shell/hauptfenster.py:6301` beschriftet mit `pfad.stem`, dem Namen
der Projektdatei; die Startseite nimmt `eindeutige_namen` aus
`ide/shell/startbild.py:156` mit dem Ordnernamen. Nachweis:
`build\auswertung\pruefung_42d5478\D\762_zuletzt_menue.py`.

**Zu tun:** Das Menü so beschriften wie die Startseite. Erledigt, wenn
die Probe vier verschiedene Einträge findet.

## 763. Gleichnamige Aufgaben aus verschiedenen Wochen bekommen je nach Reihenfolge „Aufgabe“ oder „Aufgabe 2“

**Gemeldet:** 24. November 2026, Prüfung D (Sicht der Lehrkraft),
Stand `42d5478`.

**Beobachtet:** Die Lehrkraft legt jede Woche einen Ordner an,
`Tausch\8b\Woche1\Aufgabe` und `Tausch\8b\Woche2\Aufgabe`. Ben öffnet
beide, Anna fehlte in Woche 1 und öffnet nur Woche 2. Bens Kopie von
Woche 2 heißt `Aufgabe 2`, Annas `Aufgabe`. Die Abgaben zu Woche 2
heißen damit „Aufgabe 2 - ben - PC-R01“ und „Aufgabe - anna - PC-R01“;
Annas trägt denselben Namensanfang wie Bens Abgabe aus Woche 1. Aus dem
Namen einer Abgabe lässt sich nicht ablesen, zu welcher Woche sie
gehört.

**Ursache:** nachgewiesen: `aufgabe_kopieren` in
`ide/shell/startbild.py:760` benennt die Kopie nach dem Ordner der
Aufgabe und zählt bei einem belegten Namen hoch; `abgabe_name` in
`ide/shell/hauptfenster.py:680` übernimmt den Ordnernamen der Kopie.
Nachweis:
`build\auswertung\pruefung_42d5478\D\763_gleichnamige_aufgaben.py`.

**Zu tun:** Die Kopie einer Aufgabe so benennen, dass gleichnamige
Aufgaben aus verschiedenen Ordnern unterscheidbar bleiben, oder in
Handbuch 3.6 eindeutige Ordnernamen für Aufgaben verlangen. Erledigt,
wenn die Probe für Woche 2 bei beiden Konten denselben Namensanfang
findet oder das Handbuch den Satz enthält.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
