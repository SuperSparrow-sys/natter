# Natter für Lehrkräfte

Diese Seite beschreibt, was Natter kann und welche Tasten wo wirken.
Sie setzt keine Programmierkenntnisse voraus und erklärt nicht, wie
Natter gebaut ist — nur, was davon im Unterricht ankommt.

Natter ist eine Entwicklungsumgebung für Python. Die Oberfläche wird
gezeichnet statt getippt, der Code ist gewöhnliches Python, und alle
Texte sind deutsch. Zielsystem ist Windows 10 oder neuer.

---

## 1. Einrichten

### 1.1 Auf einem einzelnen Rechner

`Natter-Setup.exe` doppelklicken. Der Installer braucht **keine
Administratorrechte**: er legt Natter unter

```
C:\Users\<Anmeldename>\AppData\Local\Programs\Natter
```

ab, also im Benutzerprofil. Auf einem Schulrechner mit
eingeschränktem Konto funktioniert das ohne Rückfrage bei der
Systembetreuung.

Während der Installation sind zwei Angaben zu machen:

| Frage im Installer | Empfehlung |
|---|---|
| Zielordner | unverändert lassen |
| Desktop-Symbol anlegen | nach Geschmack |
| `.natter`-Dateien mit Natter verknüpfen | **ankreuzen**, dann öffnet ein Doppelklick auf eine Projektdatei das Projekt |

### 1.2 Die Warnung von Windows beim ersten Start

Beim Doppelklick auf die Setup-Datei meldet sich Windows unter
Umständen mit **„Der Computer wurde durch Windows geschützt"**
(SmartScreen). Das ist keine Fehlfunktion und kein Hinweis auf
Schadsoftware.

Der Grund: Natter ist mit einem **selbst ausgestellten Zertifikat**
signiert. Ein von Microsoft anerkanntes Zertifikat kostet mehrere
hundert Euro im Jahr, die ein Schulprojekt nicht aufbringt. Die
Signatur belegt deshalb nicht, *wer* Natter gebaut hat, wohl aber,
**dass die Datei seit dem Bau unverändert ist**.

So geht es weiter: auf **„Weitere Informationen"** klicken, dann auf
**„Trotzdem ausführen"**.

Wer prüfen möchte, ob die Datei unterwegs verändert wurde, kann das in
der PowerShell tun:

```powershell
Get-AuthenticodeSignature "C:\Pfad\zu\Natter-Setup.exe" | Format-List Status, SignerCertificate
```

`Status : Valid` bedeutet: die Datei ist unverändert. Als Aussteller
muss `CN=Natter Codesignatur` erscheinen.

### 1.3 Auf vielen Rechnern gleichzeitig

Für einen Computerraum lässt sich der Installer ohne jede Rückfrage
ausführen:

```powershell
Natter-Setup.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

Es erscheint kein Fenster, kein Dialog, keine Rückfrage. Der
Rückgabewert `0` bedeutet Erfolg. Mit `/LOG=C:\Pfad\setup.log` wird
ein Protokoll geschrieben.

Ein Update wird genauso eingespielt: die neue Setup-Datei über die
alte Installation laufen lassen. Dateien einer früheren Fassung, die
es nicht mehr gibt, werden dabei entfernt.

### 1.4 Entfernen

Über **Einstellungen → Apps → Installierte Apps → Natter → Deinstallieren**,
oder still:

```powershell
"C:\Users\<Anmeldename>\AppData\Local\Programs\Natter\unins000.exe" /VERYSILENT
```

**Die Projekte der Schülerinnen und Schüler bleiben dabei erhalten.**
Sie liegen nicht im Programmordner, sondern unter `Dokumente`.

---

## 2. Wo die Dateien liegen

| Was | Wo |
|---|---|
| Natter selbst | `%LOCALAPPDATA%\Programs\Natter` |
| Arbeitskopien der Beispiele | `Dokumente\Natter` |
| Eigene Projekte | dort, wo sie beim Anlegen hingelegt werden — vorgeschlagen wird `Dokumente` |

**Programmordner und Schülerdaten sind getrennt.** Ein neu
aufgesetzter Rechner, ein Update oder eine Deinstallation rühren die
Projekte nicht an. Umgekehrt kann ein Schüler nichts an Natter
kaputtmachen.

Ein Projekt ist immer ein **Ordner**, kein Einzeldokument. Darin
liegt eine `.natter`-Datei — die wird doppelgeklickt. Zum Einsammeln
oder Sichern wird der ganze Ordner kopiert oder gezippt.

---

## 3. Was Natter kann

### 3.1 Oberflächen zeichnen statt tippen

Ein Fenster entsteht, indem Komponenten aus der Palette am oberen Rand
auf das Formular gezogen werden: Knöpfe, Textfelder, Beschriftungen,
Listen, Tabellen, Bilder, Zeitgeber und weitere. Im **Objektinspektor**
rechts werden Beschriftung, Größe, Farbe und Verhalten eingestellt.

Ein Doppelklick auf eine Komponente legt die zugehörige Methode im
Quelltext an und springt dorthin. Der Schüler schreibt hinein, was
passieren soll.

Was im Objektinspektor eingestellt wird, heißt im Code genauso. Wer
dort `caption` sieht, schreibt im Code `self.b_ok.caption`.

### 3.2 Zwei Arten von Projekten

Beim Anlegen wird zwischen zwei Vorlagen gewählt:

- **GUI-Projekt** — ein Fenster mit Komponenten. Ein- und Ausgabe
  laufen über die Oberfläche.
- **Konsolenprojekt** — läuft in einem schwarzen Fenster mit `print()`
  und `input()`, wie ein klassisches Einsteigerprogramm.

Beide bestehen aus einer `main.py`, die nur startet, und einer
`u_main.py`, in der der Schülercode steht. Im Projekt-Explorer links
ist nur zu sehen, was auch bearbeitet werden soll.

### 3.3 Starten, anhalten, nachsehen

`F5` startet mit Debugger, `Strg+F5` ohne. Vor dem Start prüft Natter
das Projekt und meldet Fehler in verständlichem Deutsch, mit Datei und
Zeile. Ein Klick auf die Meldung springt an die Stelle.

Im Debugger lässt sich Zeile für Zeile durchgehen (`F11` hinein,
`F10` darüber hinweg), und im Panel **Variablen** ist zu sehen, was
gerade in welcher Variablen steht.

### 3.4 Modellieren

Natter bringt einen Diagramm-Editor mit für

- **Klassendiagramme** (UML),
- **Struktogramme** (Nassi-Shneiderman),
- **Entscheidungstabellen**.

Aus einem Klassendiagramm kann Natter das Gerüst der Klassen erzeugen,
aus einem Struktogramm das Gerüst einer Funktion. Jedes Diagramm lässt
sich als PNG, SVG oder PDF exportieren, etwa für ein Arbeitsblatt
oder eine Abgabe.

### 3.5 Das fertige Programm weitergeben

**Projekt → Als Exe exportieren …** baut aus dem Projekt eine einzelne
`.exe`, die auf einem Windows-Rechner ohne Python läuft. Sie lässt
sich weitergeben, ohne vorher etwas entpacken zu müssen.

Der Export dauert je nach Projekt eine halbe bis eine Minute. Natter
bleibt währenddessen bedienbar; unten rechts läuft ein Ladebalken.

### 3.6 Testen

Ein Projekt kann Testdateien enthalten (**Datei → Neue Test-Unit**).
**Projekt → Alle Tests ausführen** zeigt im Panel **Tests**, was
besteht und was nicht. Die Ergebnisse lassen sich als HTML
exportieren.

---

## 4. Der Prüfungsmodus

**Werkzeuge → Prüfungsmodus starten …**

Für **vier Stunden** ab dem Einschalten gilt dann:

- Fehlermeldungen sagen weiterhin, *was* falsch ist, aber nicht mehr,
  woran es liegen könnte — kein Lösungsvorschlag.
- Aus Klassendiagramm und Struktogramm lässt sich kein Quelltext mehr
  erzeugen.
- Die Vervollständigung im Editor bleibt, aber ohne die deutschen
  Erklärungen daneben.

Alles andere bleibt: zeichnen, starten, schrittweise ausführen,
deutsche Meldungen.

Zwei Eigenschaften sind für die Aufsicht wichtig:

1. **Er übersteht einen Neustart von Natter.** Schließen und wieder
   öffnen hebelt ihn nicht aus.
2. **Er läuft von selbst aus.** Niemand muss daran denken, ihn wieder
   abzuschalten, und kein Rechner bleibt über den Schultag hinaus
   eingeschränkt.

---

## 5. Tastenkürzel

Alles geht auch über die Menüs. In Natter selbst steht die vollständige
Liste unter **Hilfe → Tastenkürzel-Übersicht**; sie wird aus dem
Programm erzeugt und ist damit immer aktuell.

### Datei und Bearbeiten

| Taste | Was passiert |
|---|---|
| `Strg+O` | Projekt öffnen |
| `Strg+P` | Unit öffnen |
| `Strg+N` | Neue Unit |
| `Strg+S` | Speichern |
| `Strg+Z` | Rückgängig |
| `Strg+Y` | Wiederholen |
| `Strg+X` / `Strg+C` / `Strg+V` | Ausschneiden, Kopieren, Einfügen |
| `Strg+A` | Alles auswählen |

### Suchen

| Taste | Was passiert |
|---|---|
| `Strg+F` | Suchen |
| `Strg+G` | Gehe zu Zeile |

### Starten und Debuggen

| Taste | Was passiert |
|---|---|
| `F5` | Starten |
| `Strg+F5` | Starten ohne Debugger |
| `Umschalt+F5` | Stopp |
| `F11` | Einzelschritt — in die Funktion hinein |
| `F10` | Prozedurschritt — über die Funktion hinweg |
| `Umschalt+F11` | Ausführen bis Rücksprung |

### Bewegen im Programm

| Taste | Was passiert |
|---|---|
| `Umschalt+F12` | Zwischen Formular und Code wechseln |
| `F12` | Zur Definition des Namens unter dem Cursor springen |
| `Strg+Tab` | Nächster Reiter |
| `Strg+Umschalt+Tab` | Vorheriger Reiter |

### Nur im Quelltexteditor

| Taste | Was passiert |
|---|---|
| `Strg+#` | Zeile aus- oder einkommentieren |
| `Strg+D` | Zeile darunter noch einmal einfügen |
| `Alt+Pfeil hoch/runter` | Zeile nach oben oder unten schieben |
| `Strg+Leertaste` | Vervollständigung erzwingen |
| `Strg+Mausrad` | Schrift größer oder kleiner |
| `Tab` | vier Leerzeichen, nie ein Tabulatorzeichen |
| Klick links im Zeilenrand | Haltepunkt setzen oder entfernen |
| Klick rechts im Zeilenrand | Klasse oder Funktion zuklappen |

### Nur im Formular-Designer

| Taste | Was passiert |
|---|---|
| Pfeiltasten | Komponente um einen Rasterschritt verschieben |
| `Alt+Pfeil` | um genau einen Bildpunkt verschieben |
| `Umschalt+Pfeil` | Größe ändern |
| `Entf` | Komponente löschen |
| `Strg+D` | Komponente verdoppeln |
| Doppelklick | Ereignis-Methode anlegen und hinspringen |

---

## 6. Wenn etwas nicht stimmt

### „Natter wurde verändert"

Natter prüft bei jedem Start, ob seine eigenen Programmdateien noch so
sind wie beim Bau. Weicht etwas ab, erscheint diese Meldung mit dem
Namen der betroffenen Datei.

**Eigene Projekte sind davon nie betroffen** — sie liegen außerhalb des
Programmordners. Abhilfe: Natter neu installieren und dabei den alten
Programmordner ersetzen. Bleibt die Meldung, liegt es vermutlich an
einem Virenscanner, der eine Datei in Quarantäne genommen hat; dann
hilft die Systembetreuung weiter.

Die Prüfung blockiert den Start nicht, sondern fragt. Wer „Ja" wählt,
arbeitet weiter.

### Das Programm startet nicht, es erscheint eine Liste von Meldungen

Das ist die Prüfung vor dem Start. Ein Syntaxfehler oder ein
unbekannter Name verhindert den Start — dort würde das Programm
ohnehin abstürzen. Ein ungenutzter Import ist dagegen nur ein
Hinweis; das Programm läuft trotzdem.

### Ein Schüler findet seine Datei nicht

Im Projekt-Explorer ist absichtlich nur zu sehen, was bearbeitet
werden soll. `main.py` und die aus dem Formular erzeugte Datei werden
von Natter geschrieben und stehen deshalb nicht in der Liste. Über
**Projekt → Startdatei anzeigen** lassen sie sich trotzdem ansehen.

### Zurück zur Startseite

**Ansicht → Startseite** führt von einem offenen Projekt zurück zum
Begrüßungsbildschirm, ohne etwas zu schließen. Derselbe Eintrag führt
wieder zurück in die Arbeit.

---

## 7. Für den Einstieg im Unterricht

Unter **Datei → Beispielprojekte** stehen neun Projekte, die
aufeinander aufbauen — von der Begrüßung über Taschenrechner und
Bildergalerie bis zu Datenbank, CSV-Auswertung und einer kleinen
Regression.

Ein angeklicktes Beispiel wird **als Arbeitskopie** nach
`Dokumente\Natter` gelegt und dort geöffnet. Das Original bleibt
unverändert, und dieselbe Aufgabe kann in der nächsten Stunde noch
einmal von vorn begonnen werden.

Für Schülerinnen und Schüler gibt es unter **Hilfe → Erste Schritte**
eine Anleitung, die in zehn Minuten vom leeren Bildschirm zum
laufenden Programm führt. **Hilfe → Komponenten-Referenz** listet jede
Komponente mit ihren Eigenschaften und Ereignissen auf.
