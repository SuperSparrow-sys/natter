# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **495**.

## Ein neuer Punkt

```markdown
## 495. Kurz, was nicht stimmt

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

## 492. Diagramm: Hin- und Rückweg zwischen zwei Formen liegen übereinander

**Gemeldet:** 3. Oktober 2026, Durchsicht Diagramm-Editor aus Schülersicht, Entwicklungsstand `ee342d5`.

**Beobachtet:** Zustandsdiagramm einer Ampel mit den Übergängen Rot → Grün und Grün → Rot, Aktivitätsdiagramm mit Verzweigung → „Wasser nachfüllen“ und zurück. Beide Linien liegen genau aufeinander und sehen aus wie ein einziger Doppelpfeil; Beschriftungen an beiden Übergängen würden sich überdecken. Ein Doppelklick auf eine der Linien setzt einen Knickpunkt und trennt sie, darauf kommt aber niemand ohne Hinweis.

**Ursache:** nachgewiesen. `verbindungs_punkte` in `ide/diagramm/zeichnen.py` zieht jede Verbindung ohne Knickpunkte vom Rand der Quelle zum Rand des Ziels auf der Linie zwischen den Mittelpunkten. Von einer gegenläufigen Verbindung weiß die Funktion nichts; sie wird an acht Stellen aufgerufen (Zeichnen, Treffer, Beschriftungen, Export).

**Zu tun:** Zwei Verbindungen zwischen denselben Formen ohne Knickpunkte leicht gegeneinander versetzt zeichnen, etwa je eine Linienbreite zur eigenen linken Seite, ohne das Dateiformat zu ändern. Erledigt, wenn im Bild einer Ampel mit Hin- und Rückweg zwei getrennte Pfeile zu sehen sind und ein Test den Abstand der beiden Linien prüft.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
