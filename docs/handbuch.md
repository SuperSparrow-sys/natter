# Natter-Handbuch

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
eingeschränktem Konto geht das ohne Rückfrage bei der
Systembetreuung, solange dort nicht AppLocker oder eine
Softwareeinschränkung nur Programme aus `C:\Windows` und
`C:\Program Files` starten lässt. Unter solchen Regeln startet eine
Installation im Profil nicht; dann installiert die Systembetreuung
Natter für alle Benutzer (Abschnitt 1.4). Für einen Computerraum ist
das ohnehin der vorgesehene Weg.

Während der Installation fragt das Setup nach diesen Angaben:

| Frage im Installer | Empfehlung |
|---|---|
| Installationsart wählen: „Nur für das angemeldete Konto (empfohlen)“ oder für alle Benutzer | auf einem eigenen Rechner das angemeldete Konto; im Computerraum alle Benutzer (siehe unten) |
| Zielordner | unverändert lassen |
| Desktop-Symbol anlegen | nach Geschmack |
| `.natter`-Dateien mit Natter verknüpfen | **ankreuzen**, dann öffnet ein Doppelklick auf eine Projektdatei das Projekt |

Die beiden Installationsarten unterscheiden sich so:

| | Nur für das angemeldete Konto | Für alle Benutzer |
|---|---|---|
| Ort | `%LOCALAPPDATA%\Programs\Natter` | `C:\Program Files\Natter` |
| Rechte beim Installieren | keine besonderen | Administratorrechte |
| Wer Natter sieht | nur dieses Konto | jedes Konto des Rechners |
| „Pakete → Paket installieren …“ | geht | nur mit Administratorrechten, für Schülerkonten also nicht |

Bei der Installation für alle Benutzer ist der Programmordner für
gewöhnliche Konten schreibgeschützt. Pakete, die im Unterricht
gebraucht werden, installiert dann die Systembetreuung einmal mit
Administratorrechten; Natter meldet sonst beim Nachinstallieren, dass
der Ordner schreibgeschützt ist.

### 1.2 Eine Voraussetzung, die vorher zu prüfen ist

Auf einem Rechner mit eingeschalteter **intelligenter App-Steuerung**
(Smart App Control) startet Natter nicht. Nachzusehen ist das unter
Einstellungen → Datenschutz und Sicherheit → Windows-Sicherheit →
App- und Browsersteuerung.

Diese Prüfung fragt für jede einzelne Datei bei Microsoft nach, ob sie
dort bekannt ist. Ein selbst ausgestelltes Zertifikat zählt dabei
nicht mit — Windows führt eine so signierte Datei im Protokoll als
unsigniert, auch wenn sie ordnungsgemäß signiert und das Zertifikat
eingetragen ist. Ein Programm wie Natter besteht aus über achthundert
solcher Dateien, und es genügt, dass eine davon abgewiesen wird.

Der Normalfall auf zentral verwalteten Schulrechnern (Intune, Domäne)
ist, dass die App-Steuerung aus ist; dasselbe gilt für alles, was von
Windows 10 heraufgestuft wurde. Betroffen sind vor allem frisch
aufgesetzte Einzelgeräte. Dort bleibt nur, die App-Steuerung
auszuschalten — was Microsoft nur in eine Richtung zulässt: einmal
aus, bleibt sie aus, bis Windows neu aufgesetzt wird.

### 1.3 Die Warnung von Windows beim ersten Start

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

### 1.4 Auf vielen Rechnern gleichzeitig

Für einen Computerraum wird Natter für alle Benutzer installiert,
ohne jede Rückfrage und mit Administratorrechten, etwa über die
Softwareverteilung der Schule:

```powershell
Natter-Setup.exe /ALLUSERS /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

Natter liegt danach unter `C:\Program Files\Natter` und steht in
jedem Konto im Startmenü. Es erscheint kein Fenster, kein Dialog,
keine Rückfrage. Der Rückgabewert `0` bedeutet Erfolg. Mit
`/LOG=C:\Pfad\setup.log` wird ein Protokoll geschrieben.

Ohne `/ALLUSERS` installiert das Setup nur für das Konto, unter dem
es läuft, auch mit Administratorrechten. Unter dem Konto einer
Lehrkraft hätte dann nur diese Lehrkraft Natter. Läuft das Setup ohne
`/ALLUSERS` unter dem Systemkonto, wie bei den meisten
Softwareverteilungen, bricht es ab, statt Natter in das Profil des
Systemkontos zu legen: der Rückgabewert ist dann nicht `0`, und im
Protokoll steht der Grund.

Desktop-Symbol und `.natter`-Verknüpfung legt eine stille
Installation immer an. Abwählen lässt sich das mit `/MERGETASKS`,
zum Beispiel ohne Desktop-Symbol:

```powershell
Natter-Setup.exe /ALLUSERS /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /MERGETASKS="!desktopicon"
```

Mit `/MERGETASKS="!desktopicon,!natterverknuepfung"` entfallen beide.

Ein Update wird genauso eingespielt: die neue Setup-Datei mit
denselben Schaltern über die alte Installation laufen lassen. Dateien
einer früheren Fassung, die es nicht mehr gibt, werden dabei
entfernt.

Für die Erkennungsregel einer Softwareverteilung (Intune, baramundi,
opsi) taugen zwei Merkmale. Der Deinstallationseintrag

```
HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{961DA420-CA63-4436-9023-9CA411B620DA}_is1
```

trägt im Wert `DisplayVersion` die installierte Fassung, dreiteilig
wie `1.2.3`; verglichen wird sie als Versionsnummer, nicht als Text.
Bei einer Installation nur für ein Konto steht derselbe Schlüssel
unter `HKEY_CURRENT_USER`. Außerdem trägt
`C:\Program Files\Natter\Natter.exe` die Fassung als Dateiversion
(Eigenschaften → Details), vierteilig mit einer `0` am Ende.

### Von Installationen je Konto auf eine für alle Benutzer umstellen

Wurde Natter früher in jedem Schülerkonto einzeln installiert, liegt
in jedem dieser Konten eine eigene Fassung unter
`%LOCALAPPDATA%\Programs\Natter`. Eine Installation mit `/ALLUSERS`
entfernt sie nicht, und im jeweiligen Konto hat die alte Fassung
Vorrang: ein Doppelklick auf eine `.natter`-Datei startet sie, unter
AppLocker also eine gesperrte Exe, und im Startmenü steht Natter
zweimal. Updates über die Softwareverteilung erreichen sie nie, und
je Konto bleiben rund 1,2 GB belegt.

Die alten Fassungen werden deshalb beim Umstieg in jedem Konto
entfernt. Das geht nur im Konto selbst, dafür ohne
Administratorrechte, am einfachsten als Anmeldeskript, etwa über eine
Gruppenrichtlinie unter Benutzerkonfiguration → Richtlinien →
Windows-Einstellungen → Skripts → Anmelden:

```bat
if exist "%LOCALAPPDATA%\Programs\Natter\unins000.exe" "%LOCALAPPDATA%\Programs\Natter\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

Projekte und Einstellungen bleiben dabei erhalten (Abschnitt 1.5).
Sobald sich jedes Konto einmal angemeldet hat, kann das Skript wieder
weg. Das Setup selbst sieht nur das Konto, unter dem es läuft; findet
es dort eine zweite Installation, steht das im Protokoll. Ob in einem
Konto noch eine alte Fassung liegt, zeigt auch `Natter-pruefen.cmd`
aus dem Paket für die Schule: der Bericht nennt dann beide.

### Rechner mit AppLocker oder Softwareeinschränkung

Viele Schulträger lassen auf Schülerrechnern nur Programme aus
`C:\Windows` und `C:\Program Files` starten, über AppLocker oder eine
Richtlinie für Softwareeinschränkung. Die Standardregeln von
AppLocker sind so angelegt. Eine Installation nur für das angemeldete
Konto unter `%LOCALAPPDATA%\Programs\Natter` startet dort nicht,
schon `Natter.exe` wird abgewiesen. Die Installation für alle
Benutzer mit `/ALLUSERS` legt Natter nach `C:\Program Files\Natter`
und erfüllt diese Regeln ohne weitere Ausnahme.

Diese Programme startet Natter; eine Regel, die nach Programmen
statt nach Ordnern freigibt, braucht alle:

| Programm | wofür |
|---|---|
| `Natter.exe` | der Start von Natter |
| `python\pythonw.exe` | die Oberfläche von Natter und „Pakete“ |
| `python\python.exe` | Schülerprogramme, Debugger und der Exe-Export mit PyInstaller |
| `python\Scripts\ruff.exe` | die Prüfung vor dem Start |
| `unins000.exe` | das Entfernen |
| `powershell.exe` (Windows) | das Signieren beim Exe-Export |
| `taskkill.exe` (Windows) | das Beenden eines Schülerprogramms |

Die ersten fünf liegen im Programmordner von Natter. Ist
`powershell.exe` für Schülerkonten gesperrt, entsteht beim Export
trotzdem eine Exe, nur ohne Signatur.

Werden auch DLL-Regeln durchgesetzt: Natter lädt Bibliotheken nur aus
seinem Programmordner, aus `starter\` (für `Natter.exe`) und aus
`python\` samt `python\DLLs\`.

Eine mit „Projekt → Als Exe exportieren …“ gebaute Exe liegt im
Projekt unter `Dokumente`, im Unterordner `dist`. Unter diesen
Regeln startet sie nur mit einer eigenen Regel für diesen Ordner.
In Natter selbst läuft das Programm über „Start → Starten“ wie
bisher; die Exe ist für die Weitergabe gedacht.

### Der erste Start dauert länger

Nach einer Installation oder einem Update braucht der erste Start
deutlich länger als alle folgenden. Gemessen mit 0.4.1 auf einem
Rechner mit Windows Defender: rund 16 Sekunden bis zum Hauptfenster
statt 1,5. Nach einer Sekunde steht das Fenster „Natter startet …“,
nach rund 5 Sekunden das Ladebild mit der Versionsnummer. Der Grund
ist der Virenschutz von Windows: er prüft jede neu geschriebene Datei
beim ersten Öffnen, und Natter bringt rund 30 000 Dateien mit. Ab dem
zweiten Start sind sie geprüft.

Dasselbe gilt für das erste Programm, das große Bibliotheken lädt.
Das Beispiel 09_ObstSortierer (scikit-learn, matplotlib) brauchte beim
ersten Start 76 Sekunden bis zu seinem Fenster, beim zweiten 6,5.

Für den Unterricht heißt das: nach dem ersten Doppelklick abwarten
und nicht ein zweites Mal klicken. Wer Natter nach dem Installieren
einmal startet und wieder schließt, etwa über „Natter starten“ auf der
letzten Seite des Installers, erspart der Klasse die Wartezeit; wer
dazu einmal das Beispiel 09_ObstSortierer startet, auch die für
scikit-learn und matplotlib.

Eine Ausnahme im Virenschutz für den Programmordner beseitigt die
Wartezeit ganz. Sinnvoll ist sie nur bei einer Installation für alle
Benutzer unter `C:\Program Files\Natter`, in die Schülerkonten nicht
schreiben können. Den Ordner einer Installation für das eigene Konto
(`%LOCALAPPDATA%\Programs\Natter`) kann jedes Programm des Kontos
verändern; ihn vom Virenschutz auszunehmen, öffnet eine Lücke.

### 1.5 Entfernen

Über **Einstellungen → Apps → Installierte Apps → Natter → Deinstallieren**,
oder still. Bei einer Installation nur für das angemeldete Konto
genügt das Konto selbst:

```powershell
"C:\Users\<Anmeldename>\AppData\Local\Programs\Natter\unins000.exe" /VERYSILENT
```

Bei einer Installation für alle Benutzer liegt der Uninstaller im
Programmordner, und der Aufruf braucht Administratorrechte:

```powershell
"C:\Program Files\Natter\unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
```

**Die Projekte der Schülerinnen und Schüler bleiben dabei erhalten.**
Sie liegen nicht im Programmordner, sondern unter `Dokumente`.

Entfernt werden der Programmordner, der Eintrag im Startmenü, das
Desktop-Symbol und die `.natter`-Verknüpfung. In jedem Konto, das
Natter benutzt hat, bleibt Folgendes stehen:

| Was | Wo |
|---|---|
| Projekte und Arbeitskopien der Beispiele | `Dokumente\Natter` |
| Einstellungen | `%APPDATA%\Natter` |
| Vermerk des Prüfungsmodus | `%LOCALAPPDATA%\Natter` und `HKEY_CURRENT_USER\Software\Natter\Pruefungsmodus` |
| Zertifikat „Natter Programme dieses Rechners“ aus dem Exe-Export | Zertifikatspeicher des Kontos: Eigene Zertifikate, Vertrauenswürdige Stammzertifizierungsstellen, Vertrauenswürdige Herausgeber |

Der Vermerk des Prüfungsmodus bleibt absichtlich stehen, sonst
beendete ein Deinstallieren einen laufenden Modus. Nach dessen Ende
wirkt er nicht mehr und lässt sich zusammen mit den beiden Ordnern
löschen.

Das Zertifikat aus dem Exe-Export (siehe 3.5) nimmt
`Zertifikat-entfernen.cmd` aus dem Paket für die Schule heraus,
aufgerufen im jeweiligen Konto und ohne Administratorrechte:

```powershell
Zertifikat-entfernen.cmd -Exportzertifikate
```

Für den Stammspeicher fragt Windows dabei noch einmal nach. Von Hand
geht es über `certmgr.msc`: in den drei genannten Ordnern die
Einträge „Natter Programme dieses Rechners“ löschen.

---

## 2. Wo die Dateien liegen

| Was | Wo |
|---|---|
| Natter selbst, nur für das angemeldete Konto installiert | `%LOCALAPPDATA%\Programs\Natter` |
| Natter selbst, für alle Benutzer installiert (`/ALLUSERS`) | `C:\Program Files\Natter` |
| Einstellungen | `%APPDATA%\Natter` |
| Vermerk des Prüfungsmodus | `%LOCALAPPDATA%\Natter` und `HKEY_CURRENT_USER\Software\Natter\Pruefungsmodus` |
| Arbeitskopien der Beispiele | `Dokumente\Natter\Beispielprojekte` |
| Eigene Projekte | dort, wo sie beim Anlegen hingelegt werden — vorgeschlagen wird `Dokumente\Natter` |
| Sicherung ungespeicherter Änderungen | im Projektordner als `<Projektname>.natter-sicherung`, nur solange etwas ungespeichert ist (Abschnitt 6) |

Welcher Ordner „Dokumente" ist, erfragt Natter beim System. Ist er
auf OneDrive oder ein Netzlaufwerk umgeleitet — auf Schulrechnern die
Regel —, folgt Natter dorthin.

**Programmordner und Schülerdaten sind getrennt.** Ein neu
aufgesetzter Rechner, ein Update oder eine Deinstallation rühren die
Projekte nicht an. Umgekehrt kann ein Schüler nichts an Natter
kaputtmachen.

Ein Projekt ist immer ein **Ordner**, kein Einzeldokument. Darin
liegt eine `.natter`-Datei — die wird doppelgeklickt. Zum Einsammeln
oder Sichern wird der ganze Ordner kopiert oder gezippt.

Ein Projektordner geht überall auf, wo er liegt. Kopiert oder
verschoben, auch bei einem Umzug der Heimatlaufwerke auf einen neuen
Server, bleibt er ein gewöhnliches Projekt; wem der Ordner laut
Windows gehört, spielt keine Rolle. Nur wo Natter nicht schreiben
darf, bietet es eine eigene Kopie unter `Dokumente\Natter` an
(Abschnitt 3.6).

---

## 3. Was Natter kann

### 3.1 Oberflächen zeichnen statt tippen

Ein Fenster entsteht aus Komponenten der Palette am oberen Rand:
Knöpfe, Textfelder, Beschriftungen, Listen, Tabellen, Bilder,
Zeitgeber und weitere. Eine Komponente wird in der Palette
angeklickt und dann an der gewünschten Stelle ins Formular geklickt;
ein Doppelklick in der Palette setzt sie in die Mitte des Formulars.
Ziehen aus der Palette gibt es nicht. Im **Objektinspektor**
rechts werden Beschriftung, Größe, Farbe und Verhalten eingestellt.

Ein Doppelklick auf eine Komponente legt die zugehörige Methode im
Quelltext an und springt dorthin. Der Schüler schreibt hinein, was
passieren soll.

Was im Objektinspektor eingestellt wird, heißt im Code genauso. Wer
dort `caption` sieht, schreibt im Code `self.b_ok.caption`.

Ein weiteres Fenster entsteht über „Datei → Neues Formular …“. Es
öffnet sich nicht von selbst, sondern aus einem anderen Formular
heraus, etwa mit einem Knopf:

```python
from u_form2 import Form2

def b_oeffnen_click(self, sender):
    self.form2 = Form2()
    self.form2.show()
```

Das steht auch oben in der neu angelegten Unit.

### 3.2 Zwei Arten von Projekten

Beim Anlegen wird zwischen zwei Vorlagen gewählt:

- **GUI-Anwendung** — ein Fenster mit Komponenten. Ein- und Ausgabe
  laufen über die Oberfläche.
- **Konsolenanwendung** — läuft in einem schwarzen Fenster mit `print()`
  und `input()`, wie ein klassisches Einsteigerprogramm.

Beide bestehen aus einer `main.py`, die nur startet, und einer
`u_main.py`, in der der Schülercode steht. Im Projekt-Explorer links
ist nur zu sehen, was auch bearbeitet werden soll.

Ein Konsolenprojekt hat kein Formular. Komponentenpalette und
Objektinspektor sind dort deshalb ausgeblendet, und der Editor hat
die Breite für sich. Sie erscheinen wieder, sobald ein Formular im
Designer offen ist oder ein GUI-Projekt geöffnet wird. Über das Menü
**Ansicht** lassen sie sich jederzeit auch von Hand einblenden.

### 3.3 Starten, anhalten, nachsehen

`F5` startet mit Debugger, `Strg+F5` ohne. Vor dem Start prüft Natter
das Projekt und meldet Fehler in verständlichem Deutsch, mit Datei und
Zeile. Ein Klick auf die Meldung springt an die Stelle.

Es läuft immer nur ein Programm. Solange eines läuft, mit oder ohne
Debugger, startet weder `F5` noch `Strg+F5` ein zweites; beendet wird
es über **Start → Stopp**. Wird Natter geschlossen, während das
Programm noch läuft, fragt Natter vorher, ob es mit beendet werden
soll. Ein fertiges Konsolenprogramm, dessen Fenster nur noch auf die
Eingabetaste wartet, zählt nicht mehr als laufend: der nächste Start
schließt das Fenster und startet neu.

Ist kein Projekt offen, startet `F5` oder `Strg+F5` die `.py`-Datei im
aktiven Reiter als Konsolenprogramm, etwa eine Aufgabe, die als
einzelne Datei ausgeteilt wurde. Den Debugger und die Prüfung vor dem
Start gibt es dabei nicht; dafür braucht es ein Projekt.

Im Debugger lässt sich Zeile für Zeile durchgehen (`F11` hinein,
`F10` darüber hinweg), und im Panel **Variablen** ist zu sehen, was
gerade in welcher Variablen steht.

### 3.4 Modellieren

Natter bringt einen Diagramm-Editor mit für

- **Klassendiagramme** (UML),
- **Struktogramme** (Nassi-Shneiderman),
- **Entscheidungstabellen**,
- **Use-Case-, Aktivitäts-, Zustands- und Sequenzdiagramme** (UML).

Angelegt wird ein Diagramm über „Datei → Neues Diagramm …“. Im
Diagramm-Editor öffnet `F1` diesen Abschnitt.

**Ein Struktogramm zeichnen.** Links steht die Palette mit den
Blöcken: Anweisung, Verzweigung, Schleifen, Unterprogrammaufruf,
Aussprung und die Auswahlen. Ein Klick auf einen Block in der Palette und danach ein
Klick auf eine Einfügestelle im Struktogramm setzt ihn dorthin. Die
Einfügestellen liegen zwischen den Blöcken und in den leeren Feldern
einer Verzweigung oder Schleife; ein Block, der in eine Schleife oder
einen Zweig gesetzt wird, steht damit in ihr. So entsteht die
Verschachtelung, Block für Block. Ein Doppelklick auf einen Block
beschriftet ihn: eine Anweisung wie `summe = summe + i`, eine
Bedingung wie `x > 0` oder ein Schleifenkopf wie `für i von 1 bis 10`.
Ein Block lässt sich mit der Maus an eine andere Einfügestelle ziehen,
`Entf` löscht ihn samt Inhalt.

**Ein Klassendiagramm zeichnen.** Eine Klasse aus der Palette
anklicken und dann auf die Zeichenfläche klicken. Name, Attribute und
Operationen stehen im Eigenschaften-Dialog: Doppelklick auf die Klasse
oder Rechtsklick und „Eigenschaften …“. Für eine Beziehung die
Verbindungsart in der Palette wählen (etwa Assoziation oder
Vererbung) und von Klasse zu Klasse ziehen.

Für eine Auswahl mit mehr als zwei Wegen gibt es im Struktogramm zwei
Blöcke:

- Die **Mehrfachauswahl** trägt in jeder Spalte einen Wert oder eine
  Bedingung, etwa `x < 0`, `x = 0` und `x > 0`.
- Die **Fallauswahl** (case of) trägt im Kopf einen Ausdruck, etwa
  `note`, und in den Spalten dessen Werte `1`, `2`, `3`. Die letzte
  Spalte „sonst“ gilt für alle übrigen Werte.

Weitere Fälle kommen über das Menü „Block“, die rechte Maustaste oder
die Taste `+` dazu, `-` nimmt einen weg. Ein Doppelklick auf die
Beschriftung eines Falls ändert sie. Ein neuer Fall wird immer vor
„sonst“ eingefügt. Auf demselben Weg bekommt ein Parallelabschnitt
weitere Stränge; zwei bleiben immer stehen. Die Zweige einer einfachen Verzweigung heißen
zunächst „ja“ und „nein“; ein Doppelklick auf eine der beiden
Beschriftungen ändert sie.

Aus einem Klassendiagramm kann Natter das Gerüst der Klassen erzeugen,
aus einem Struktogramm das Gerüst einer Funktion. Aus einer
Fallauswahl wird dabei `match`/`case`, aus einer Mehrfachauswahl mit
Bedingungen eine Kette aus `if`, `elif` und `else`. Jedes Diagramm lässt
sich als PNG, SVG oder PDF exportieren, etwa für ein Arbeitsblatt
oder eine Abgabe. Blattgröße (A3, A4, A5) und Hoch- oder Querformat
für PDF und Druck stehen unter „Datei → Seite einrichten …“.

Im Diagramm-Editor stellt `Strg+0` wie im Quelltexteditor die normale
Größe (100 %) wieder her. **Ansicht → Alles anzeigen**
verkleinert so weit, dass das ganze Diagramm zu sehen ist.

### 3.5 Das fertige Programm weitergeben

**Projekt → Als Exe exportieren …** baut aus dem Projekt eine einzelne
`.exe`, die auf einem Windows-Rechner ohne Python läuft. Sie lässt
sich weitergeben, ohne vorher etwas entpacken zu müssen.

Der Export dauert je nach Projekt eine halbe bis eine Minute. Natter
bleibt währenddessen bedienbar; unten rechts läuft ein Ladebalken.

Natter signiert die Exe, damit Windows sie nicht als Programm eines
unbekannten Herausgebers führt. Beim ersten Export in einem Konto
legt Natter dafür das Zertifikat „Natter Programme dieses Rechners“
an. Es gilt nur für dieses Konto, sein Schlüssel verlässt den Rechner
nicht, und es läuft nach fünf Jahren ab. Damit Windows ihm vertraut,
trägt Natter es als Stammzertifikat des Kontos ein, und Windows
fragt dazu mit einer Sicherheitswarnung, ob ein Zertifikat von
„Natter Programme dieses Rechners“ installiert werden soll. Vorher
kündigt Natter die Warnung in einem eigenen Fenster an und sagt, was
„Ja“ und „Nein“ bewirken; der Export geht erst nach „OK“ weiter. Mit
„Ja“ wird die Exe signiert, und die Frage kommt in diesem Konto
nicht wieder.

Mit „Nein“, oder wo eine Richtlinie Benutzern das Eintragen von
Stammzertifikaten verbietet, entsteht die Exe ohne Signatur. Sie
läuft trotzdem, Windows nennt nur keinen Herausgeber. Die
Statuszeile meldet dann „Exe erstellt, ohne Signatur“, und der
ganze Grund steht im Panel „Meldungen“. Natter nimmt das nicht
eingetragene Zertifikat gleich wieder heraus und fragt bei den
folgenden Exporten nicht erneut. Darunter steht im Panel der Eintrag
„Beim nächsten Export wieder nach dem Zertifikat fragen“. Ein Klick
darauf hebt das auf, und beim nächsten Export fragt Windows wieder.
Festgehalten
ist das „Nein“ in der Datei
`%LOCALAPPDATA%\Natter\zertifikat_abgelehnt.txt`; sie zu löschen,
wirkt genauso.

Auf Rechnern, deren Profile beim Abmelden oder Neustart
zurückgesetzt werden (Wächterkarte, verbindliche oder temporäre
Profile), ist das Zertifikat danach weg. Die Warnung kommt dann beim
ersten Export nach jeder Anmeldung wieder, bei jeder Schülerin und
jedem Schüler. Ein „Nein“ hilft dort nicht auf Dauer, denn der
Vermerk darüber liegt ebenfalls im Profil. Wie sich das Zertifikat
wieder entfernen lässt, steht in 1.5.

Signiert wird nur mit „Natter Programme dieses Rechners“. Andere
Zertifikate zur Codesignatur im Konto nimmt Natter nicht, auch wenn
der Rechner ihnen vertraut, etwa das Zertifikat der Schule aus einer
eigenen Zertifizierungsstelle, mit dem eine Lehrkraft Skripte
signiert oder auf das sich Regeln nach Herausgeber in AppLocker
stützen. Ein Schülerprogramm trüge sonst den Herausgeber der Schule.
Eine Einstellung, die ein anderes Zertifikat zulässt, gibt es nicht.

### 3.6 Eine Aufgabe verteilen und die Abgaben einsammeln

Ein Projektordner geht in Natter dort auf, wo er liegt, gleich wer
ihn angelegt oder dorthin kopiert hat: im Ordner „Dokumente“, auf dem
Heimatlaufwerk, in einem Klassenordner, unter „Downloads“ oder auf
einem USB-Stick. Nur wo Natter nicht schreiben darf, bietet es eine
eigene Kopie an.

Aufgaben werden deshalb über einen Ordner verteilt, in dem die Klasse
nur lesen darf, etwa eine Freigabe, auf der nur die Lehrkraft das
Schreibrecht hat. Beim Öffnen einer Aufgabe dort bietet Natter mit
dem Knopf **Eigene Kopie öffnen** an, das Projekt nach
`Dokumente\Natter` zu kopieren und die Kopie zu öffnen. Jede
Schülerin arbeitet so in ihrer eigenen Kopie, und die Aufgabe bleibt
unverändert. In einem Ordner, in den die ganze Klasse schreiben darf,
kommt diese Frage nicht: dort arbeitet, wer die Aufgabe öffnet, im
Original, und alle anderen sehen die Änderungen.

Teilt eine Schulsoftware den Ordner in das Heimatlaufwerk jeder
Schülerin aus und sammelt ihn später wieder ein, ist das kein
Sonderfall: der ausgeteilte Ordner geht ohne Frage an seinem Ort auf,
und eingesammelt wird genau das, was darin gespeichert wurde.

Der zweite Knopf in der Frage öffnet das Projekt an seinem Ort:
**Nur ansehen**, wenn der Ordner kein Schreibrecht hat; **Trotzdem
hier öffnen**, wenn das Projekt gerade an einem anderen Rechner in
einem anderen Konto offen ist, denn dann kommt die Frage ebenfalls.
Sie kommt bei jedem Öffnen, auch über „Zuletzt geöffnet“; die Antwort
wird nicht gespeichert.

Eine Ausnahme sind ZIP-Dateien, die direkt geöffnet werden. Wird die
`.natter` in einer ZIP-Datei doppelgeklickt, legt der Explorer sie
nur vorläufig in einen Ordner wie `%TEMP%\Temp1_Ampel.zip` und räumt
ihn später wieder weg. 7-Zip und WinRAR tun dasselbe mit Ordnern wie
`%TEMP%\7zO4A1B2C3D` und `%TEMP%\Rar$DIa12345.6789` und löschen sie
schon beim Schließen des Archivs. Natter bietet dort die Kopie nach
`Dokumente\Natter` an und nennt den Grund; der zweite Knopf heißt
**Hier öffnen**. Wurde nur die `.natter` herausgeholt und fehlen
`main.py` oder die Unit, geht das Projekt nicht auf, und eine Meldung
sagt, dass die ZIP-Datei zuerst vollständig entpackt werden muss, im
Explorer mit „Alle extrahieren …“. Ein vollständig entpackter Ordner,
auch unter „Downloads“, geht ohne Frage auf.

Liegt unter `Dokumente\Natter` schon eine Kopie derselben Aufgabe und
bietet Natter beim Öffnen die Kopie an, wird diese vorhandene Kopie
geöffnet; die Arbeit vom letzten Mal bleibt so erhalten. In einem
Ordner mit Schreibrecht kommt das Angebot nicht, auch wenn es dort
schon eine Kopie gibt, etwa aus einer Fassung bis 0.3.6, die sie auch
in beschreibbaren Klassenordnern anlegte. Die Aufgabe geht dann an
ihrem Ort auf, und die Statuszeile nennt den Ordner der eigenen
Kopie. Die Kopie selbst öffnet „Projekt öffnen …“ oder „Zuletzt
geöffnet“. Ob
die Aufgabe dabei über einen Laufwerksbuchstaben wie `K:` oder über
den Netzpfad wie `\\server\tausch` geöffnet wird, spielt keine Rolle.
Wurde die
Aufgabe inzwischen geändert, etwa weil die Lehrkraft einen Fehler
berichtigt hat, fragt Natter in einer einzigen Frage, ob die eigene
Kopie geöffnet oder durch den neuen Stand ersetzt werden soll.
Vorgewählt ist **Eigene Kopie öffnen**; danach fragt Natter zu diesem
Stand der Aufgabe nicht noch einmal, erst nach der nächsten Änderung.
Bei **Kopie ersetzen** kommt der bisherige Stand der Kopie in einen
Ordner daneben, etwa `Ampel (vorher)`, und die Frage nennt ihn.
Ein eigenes Projekt gleichen Namens oder eine gleichnamige Aufgabe aus einem anderen Ordner bleibt unberührt, und
die Kopie bekommt eine Nummer („Ampel 2“). Woher eine Kopie stammt,
steht in der Datei `.natter-quelle` in ihrem Ordner. Die Kopie ist
immer beschreibbar, auch wenn die Dateien der Aufgabe schreibgeschützt
sind. Liegt die Aufgabe direkt in der Wurzel einer Freigabe, etwa
`\\server\klausur\Klausur.natter`, heißt der Ordner der Kopie wie die
Projektdatei, und kopiert werden nur die Dateien und der Ordner
`diagramme`, keine anderen Unterordner.
Scheitert das Kopieren, etwa weil eine Datei der Aufgabe gerade in
Excel offen ist oder der Speicherplatz auf dem Heimatlaufwerk nicht
reicht, bleibt unter `Dokumente\Natter` kein angefangener Ordner
liegen; eine gesperrte Datei nennt die Meldung. Der nächste Versuch
legt die Kopie unter dem ursprünglichen Namen an.
Mit **Nur ansehen** geht das Projekt im Ordner ohne Schreibrecht auf,
und Änderungen lassen sich dort nicht speichern. Scheitert das
Speichern, bietet die Meldung die eigene Kopie noch einmal an; der
ungespeicherte Text aus den Editoren kommt dabei mit. Gab es die
Kopie schon, bleiben ihre Dateien unverändert: der Text aus dem
Original steht dann im Editor der Kopie als Änderung, die noch nicht
gespeichert ist, und **Rückgängig** stellt den Stand der Kopie wieder
her.

Soll eine Kopie von vorn beginnen, setzt **Projekt → Auf Original
zurücksetzen …** sie auf den jetzigen Stand der Aufgabe zurück, wie
bei einem Beispiel, auch im Prüfungsmodus. Der bisherige Stand der
Kopie kommt dabei in einen Ordner daneben, etwa `Ampel (vorher)`;
Natter fragt vorher nach und nennt ihn. Gibt es in der Kopie
ungespeicherte Änderungen, fragt Natter danach wie beim Schließen des
Projekts: **Speichern** nimmt sie in den Ordner mit dem bisherigen
Stand mit, **Verwerfen** lässt sie weg, und **Abbrechen** lässt die
Kopie unverändert. Erst danach gehen die Reiter und Diagrammfenster
der Kopie zu. Hält ein anderes Programm eine Datei der Kopie offen,
etwa Excel eine CSV, bleibt die Kopie unverändert, die Reiter gehen
wieder auf, und eine Meldung nennt die Datei. Lässt sich danach eine der schon beiseitegelegten Dateien
nicht an ihren Platz zurückschieben, etwa weil ein Virenscanner sie
gerade prüft, nennt die Meldung den Ordner neben der Kopie, in dem
sie liegt; von dort lässt sie sich zurückkopieren. Dasselbe gilt für
**Kopie ersetzen** nach einer geänderten Aufgabe.

Ist ein Projekt im eigenen Konto noch an einem anderen Rechner als
geöffnet eingetragen, war Natter dort meist nicht beendet worden,
etwa nach einem Absturz. Natter weist darauf hin und öffnet das
Projekt ohne Kopie; ist es am anderen Rechner nicht mehr offen, lässt
sich gefahrlos weiterarbeiten.


**Projekt → Quelltext als PDF …** schreibt den Quelltext des ganzen
Projekts in eine PDF-Datei: eine Datei je Seite, mit Zeilennummern
und derselben Einfärbung wie im Editor, auf A4 mit 20 mm Rand zum
Anstreichen. In der Kopfzeile jeder Seite stehen Projektname,
Dateiname, der Name aus der Windows-Anmeldung, das Datum und „Seite
n von m“, auch auf der zweiten und dritten Seite einer langen Datei
— bei zwanzig eingesammelten Abgaben ist sonst nicht zu erkennen,
welche zu wem gehört.

Ausgegeben wird jede Python-Datei des Projekts, die im Explorer
unter „Units“ steht, also auch Testdateien wie `test_neu1.py`. Die
Startdatei und die aus dem Designer erzeugten Dateien bleiben
draußen. Vorher speichert Natter alle geänderten Dateien, damit das
PDF den Stand aus dem Editor zeigt.

Das PDF ersetzt den Projektordner nicht — wer das Programm laufen
lassen will, braucht weiterhin den ganzen Ordner. Zum Anstreichen und
Benoten ist es gedacht.

Den ganzen Ordner in einer Datei liefert **Projekt → Als ZIP
speichern …**. Vorgeschlagen wird der Projektname mit dem
Windows-Anmeldenamen und dem Rechnernamen, etwa
`Aufgabe3 - mueller.anna - PC-R12.zip`, neben dem Projektordner; der
Ordner in der ZIP heißt genauso, sodass sich eingesammelte Abgaben
nebeneinander entpacken lassen. Der Rechnername steht dabei, weil
manche Schulen mit einem Konto für alle arbeiten: ohne ihn hießen
alle Abgaben einer Klasse gleich, und jede ersetzte im
Einsammelordner die vorige. Bei einem solchen Konto verrät der Name
nur den Platz, nicht die Person; wer an welchem Rechner saß, muss
die Lehrkraft dann selbst festhalten, oder der Name der Schülerin
wird im Dialog von Hand ergänzt. Wird dieselbe Aufgabe später an
einem anderen Rechner noch einmal abgegeben, liegen beide ZIPs
nebeneinander; die neuere hat das spätere Änderungsdatum. Der Speicherort lässt sich im Dialog ändern, etwa auf
einen USB-Stick oder ein Tauschlaufwerk. Vorher speichert Natter alle
geänderten Dateien. Lässt sich eine davon nicht speichern, entsteht
keine ZIP, denn sie enthielte einen älteren Stand als den im Editor.
In der ZIP steht alles, was zum Projekt gehört, auch Bilder und eine
Datenbankdatei. Was beim Starten und Exportieren von selbst entsteht
(`__pycache__`, `build`, `dist`) und versteckte Ordner wie `.git`
bleiben draußen. Die Statuszeile nennt danach die Zahl der Dateien.
Lässt sich eine Datei des Projekts nicht lesen, meist weil sie noch
in einem anderen Programm offen ist, etwa eine CSV in Excel, entsteht
keine ZIP. Ein Fenster nennt die Datei; nach dem Schließen dort lässt
sich die ZIP noch einmal speichern.

Die ZIP entsteht nebenher, Natter bleibt dabei bedienbar. Wird Natter
geschlossen, bevor sie fertig ist, bleibt das Fenster offen, bis sie
gespeichert ist, und meldet dann in einem eigenen Fenster, ob die
Abgabe entstanden ist. Länger als eine Minute wartet Natter nicht:
danach hört das Packen auf, am Ziel wird nichts angelegt, und die
Meldung sagt das.

Eine eingesammelte ZIP wird in einen eigenen Ordner entpackt und
dort über **Projekt → Projekt öffnen …** mit der `.natter`-Datei
geöffnet. Die Abgabe geht ohne Frage an Ort und Stelle auf, auch
unter „Downloads“, und Anmerkungen beim Korrigieren stehen in der
Abgabe selbst.

### 3.7 Testen

Ein Projekt kann Testdateien enthalten (**Datei → Neue Test-Unit**).
**Projekt → Alle Tests ausführen** zeigt im Panel **Tests**, was
besteht und was nicht. Die Ergebnisse lassen sich als HTML
exportieren.

In einem Konsolenprojekt steht das Programm in der Funktion `main()`
von `u_main.py`, die `main.py` aufruft. Eine Testdatei kann deshalb
mit `from u_main import verdoppeln` eine eigene Funktion prüfen, ohne
dass beim Laden das ganze Programm startet. Code, der außerhalb von
Funktionen steht, läuft dagegen schon beim Import; ruft er `input()`
auf, meldet der Testlauf, dass sich die Testdatei nicht laden lässt.

### 3.8 Mit einer Datenbank arbeiten

Natter arbeitet mit SQLite: die Datenbank ist eine einzelne Datei im
Projektordner, ohne Server und ohne Zugangsdaten. Das Beispiel
„06 Kontoverwaltung“ zeigt den ganzen Weg.

**Ansicht → Datenbank** öffnet das Panel dazu. Es liegt als Reiter
neben den Panels unten im Fenster. In das Feld oben kommt der
Dateiname, etwa `schule.sqlite`. Ein Name ohne Pfad gilt im
Projektordner. **Verbinden** öffnet die Datei; gibt es sie noch
nicht, fragt Natter, ob eine neue, leere Datenbank angelegt werden
soll. Ohne Dateinamen verbindet das Panel nicht, denn eine Datenbank
ohne Datei wäre beim Trennen samt ihren Tabellen verloren.

Tabellen entstehen mit SQL im Eingabefeld und **Ausführen**. Mehrere
Anweisungen, jede mit einem Semikolon abgeschlossen, laufen der Reihe
nach, etwa ein ganzes Arbeitsblatt auf einmal:

```sql
CREATE TABLE schueler (
    id    INTEGER PRIMARY KEY AUTOINCREMENT,
    name  TEXT NOT NULL,
    note  INTEGER
);
INSERT INTO schueler (name, note) VALUES ('Anna', 2), ('Ben', 1);
SELECT * FROM schueler;
```

Angezeigt wird das Ergebnis der letzten Anweisung. Scheitert eine,
hält das Panel dort an und nennt ihre Nummer; die Anweisungen davor
sind dann schon ausgeführt. Ist im Feld etwas markiert, läuft nur
die Markierung.

Links zeigt der Baum die Tabellen mit ihren Spalten, rechts steht das
Ergebnis eines `SELECT`, darüber die Rückmeldung wie „2 Zeilen.“ oder
eine Fehlermeldung. Die Knöpfe unter dem Baum übernehmen eine
CSV-Datei als Tabelle und speichern die im Baum gewählte Tabelle als
CSV oder als SQL-Datei. **Trennen** gibt die Datei wieder frei; solange
das Panel verbunden ist, lässt Windows sie weder löschen noch
umbenennen.

Im Programm öffnet `SQLite3Connection` dieselbe Datei, am besten in
`form_create`. Für die Anzeige im Formular gibt es im Reiter
„Datenbank“ der Palette ein `DBGrid`. Am kürzesten füllt es
`show_rows`:

```python
from pcl import SQLite3Connection

def form_create(self, sender):
    self.db = SQLite3Connection("schule.sqlite")
    self.dbg_schueler.show_rows(
        self.db.query("SELECT name, note FROM schueler")
    )
```

Soll im Formular auch geblättert und geändert werden, kommen
`DBNavigator`, `DBEdit` und eine Datenquelle aus `SQLQuery` und
`DataSource` dazu. Die Komponenten-Referenz beschreibt das unter
„Datenbank“ und „Die Data Controls“.

---

## 4. Der Prüfungsmodus

**Werkzeuge → Prüfungsmodus starten …**

Für **vier Stunden** ab dem Einschalten gilt dann:

- Fehlermeldungen sagen weiterhin, *was* falsch ist, aber nicht mehr,
  woran es liegen könnte — kein Lösungsvorschlag. Dasselbe gilt für
  die Funde der Design-Prüfung und die Layout-Hinweise im
  Diagrammfenster.
- Aus Klassendiagramm und Struktogramm lässt sich kein Quelltext mehr
  erzeugen.
- Die Vervollständigung im Editor ist aus: keine Vorschlagsliste beim
  Tippen und keine Parameterhilfe beim Öffnen einer Klammer.
- „Datei → Zuletzt geöffnet“, die Liste auf der Startseite und
  „Datei → Beispielprojekte“ sind gesperrt; die Beispiele enthalten
  ausgearbeitete Lösungen. Ein Projekt lässt sich weiter über
  „Projekt öffnen …“ aus seinem Ordner laden; ein Beispielprojekt
  oder seine Kopie in `Dokumente\Natter\Beispielprojekte` nicht, und
  über „Datei → Öffnen …“ auch keine einzelne Datei daraus.
  „Projekt → Auf Original zurücksetzen …“ geht nur noch bei der
  eigenen Kopie einer Aufgabe, nicht bei einem Beispiel und nicht
  bei einer Kopie, deren Datei `.natter-quelle` auf ein Beispiel
  zeigt, auch wenn Groß- und Kleinschreibung abweichen. Eine solche
  Kopie legt Natter nur von einem Ordner ohne Schreibrecht an
  (Abschnitt 3.6); die Klausur wird deshalb über einen Ordner
  verteilt, in dem die Klasse nur lesen darf. Ist beim
  Einschalten ein Beispiel offen, schließt Natter es samt seinen
  Reitern; geänderte Dateien werden vorher gespeichert. Eine Kopie
  erkennt Natter am Namen ihrer Projektdatei und am Inhalt ihrer
  Units und Diagramme, auch wenn Ordner und Projektdatei umbenannt
  wurden oder eine Unit einzeln unter anderem Namen liegt. Eine
  Unit, die gegenüber dem Beispiel auch nur in einem Zeichen
  abweicht, erkennt Natter nicht mehr. Gesperrt sind die Wege in
  Natter, nicht die Dateien selbst: die Originale liegen lesbar im
  Programmordner und lassen sich mit jedem Editor öffnen.

Die rote Anzeige unten rechts zeigt die Restzeit und verschwindet,
sobald der Modus ausgelaufen ist; die gesperrten Einträge sind dann
ohne Neustart wieder frei.

Alles andere bleibt: zeichnen, starten, schrittweise ausführen,
deutsche Meldungen.

Drei Eigenschaften sind für die Aufsicht wichtig:

1. **Er übersteht einen Neustart von Natter.** Schließen und wieder
   öffnen hebelt ihn nicht aus.
2. **Er läuft von selbst aus.** Niemand muss daran denken, ihn wieder
   abzuschalten, und kein Rechner bleibt über den Schultag hinaus
   eingeschränkt.
3. **Er lässt sich nicht vorzeitig beenden.** Es gibt keinen
   Menüeintrag zum Ausschalten, auch nicht für die Lehrkraft, und
   `pcl` bietet keine Funktion dafür an. Ein zweiter Start verlängert
   und verkürzt ihn nicht.
   Wer ihn nur ausprobieren will, schaltet ihn deshalb besser nicht
   an einem Rechner ein, auf dem am selben Tag noch mit
   Lösungsvorschlägen gearbeitet werden soll.

Natter braucht für den Modus keine Verwaltungsrechte und legt nichts
außerhalb des Benutzerprofils ab. Beginn und Ende stehen als
Weltzeit (UTC) an drei Stellen des angemeldeten Kontos: in
`%APPDATA%\Natter\Natter-IDE.ini`, in
`%LOCALAPPDATA%\Natter\pruefungsmodus.txt` und in der Registry unter
`HKEY_CURRENT_USER\Software\Natter\Pruefungsmodus`. Jeder Eintrag
trägt einen Prüfwert, der an das angemeldete Windows-Konto gebunden
ist; eine Umgebungsvariable wie `USERNAME` ändert daran nichts. Der
Modus läuft, solange eine dieser Stellen einen gültigen Eintrag hat; eine gelöschte oder veränderte Stelle
stellt Natter beim nächsten Nachsehen wieder her. Eine andere
Zeitzone ändert nichts, und länger als vier Stunden ab dem
Einschalten dauert er nie.

Die Grenze: ohne Verwaltungsrechte lässt sich nicht verhindern, dass
jemand, der alle drei Stellen kennt, sie gezielt löscht oder durch
abgelaufene Einträge ersetzt. Dann ist der Modus vorbei. Gegen
Schülerinnen und Schüler mit einem gewöhnlichen Konto, die nicht
wissen, wo die Einträge stehen, hält er, solange das Profil nicht
zurückgesetzt wird (siehe unten); gegen jemanden, der diese
Stellen kennt und löscht, nicht. Dasselbe gilt für ein Programm,
das in Natter gestartet wird und die drei Stellen überschreibt: jedes
Python-Programm kann das, und über `pcl.pruefungsmodus` erreicht es
sie, ohne ihren Ort zu kennen. Wo das nicht genügt, braucht es eine
Sperre, die die Schule mit Verwaltungsrechten einrichtet, etwa
ein eigenes Prüfungskonto.

Eine zweite Grenze folgt aus demselben Grund: der Modus ist an das
Profil des Kontos gebunden. Auf Rechnern mit Wächterkarte, mit
verbindlichen oder temporären Profilen oder mit einem Profil, das
bei jeder Abmeldung zurückgesetzt wird, verschwinden alle drei
Stellen beim Abmelden und beim Neustart des Rechners. Wer sich
während der Klausur ab- und wieder anmeldet oder den Rechner neu
startet, arbeitet danach ohne Prüfungsmodus. Eingeschaltet wird er
außerdem in jedem Konto einzeln; er gilt nicht für den Rechner und
nicht für andere Konten.

Für die Aufsicht heißt das in solchen Räumen:

- den Modus an jedem Rechner einschalten, nachdem sich dort die
  Schülerin oder der Schüler angemeldet hat,
- auf die rote Anzeige unten rechts achten: fehlt sie, läuft der
  Modus nicht,
- nach einer Abmeldung oder einem Neustart den Modus erneut
  einschalten. Die vier Stunden beginnen dann von vorn.

---

## 5. Tastenkürzel

Alles geht auch über die Menüs. In Natter selbst steht die vollständige
Liste unter **Hilfe → Tastenkürzel-Übersicht**; sie wird aus dem
Programm erzeugt und ist damit immer aktuell.

Die Menüs öffnen sich auch mit `Alt` und dem unterstrichenen
Buchstaben im Menütitel: `Alt+D` für **Datei**, `Alt+B` für
**Bearbeiten**, `Alt+T` für **Start**, `Alt+H` für **Hilfe**. Im
Diagramm-Editor gilt dasselbe für seine eigenen Menüs.

### Datei und Bearbeiten

| Taste | Was passiert |
|---|---|
| `Strg+O` | Projekt öffnen |
| `Strg+P` | Unit öffnen |
| `Strg+N` | Neue Unit |
| `Strg+S` | Speichern |
| `Strg+W` | Reiter schließen |
| `Strg+Umschalt+S` | Alle geänderten Dateien speichern |
| `Strg+Umschalt+P` | Befehl suchen: jeden Befehl über seinen Namen finden |
| `Strg+Z` | Rückgängig |
| `Strg+Y` | Wiederholen |
| `Strg+X` / `Strg+C` / `Strg+V` | Ausschneiden, Kopieren, Einfügen |
| `Strg+A` | Alles auswählen |

### Suchen

| Taste | Was passiert |
|---|---|
| `Strg+F` | Suchen |
| `F3` | Weitersuchen, ohne den Suchdialog zu öffnen |
| `Umschalt+F3` | Zurücksuchen |
| `Strg+Umschalt+F` | In allen Dateien des Projekts suchen |
| `Alt+Links` | Zurück an die Stelle vor dem letzten Sprung (F12, Suchtreffer) |
| `Strg+G` | Zu Zeile springen |

### Hilfe

| Taste | Was passiert |
|---|---|
| `F1` | Hilfe zur Auswahl: die Komponenten-Referenz an der Stelle der im Designer gewählten Komponente oder der Klasse unter dem Cursor, sonst dieses Handbuch |
| `Strg+F` in einer Hilfeseite | In der Seite suchen; Eingabe sucht weiter, Esc schließt die Suchleiste |

### Starten und Debuggen

| Taste | Was passiert |
|---|---|
| `F5` | Starten |
| `Strg+F5` | Starten ohne Debugger |
| `Umschalt+F5` | Stopp |
| `F11` | Einzelschritt — in die Funktion hinein |
| `F10` | Prozedurschritt — über die Funktion hinweg |
| `Umschalt+F11` | Ausführen bis Rücksprung |
| `F4` | Ausführen bis Cursor — startet das Programm, falls es noch nicht läuft |

„Start → Pause“ hält auch ein Programm an, das in einer Schleife
festhängt und nie an einem Haltepunkt vorbeikommt.

Haltepunkte und ihre Bedingungen bleiben erhalten, wenn ein Reiter,
das Projekt oder Natter geschlossen wird. Natter merkt sie sich je
Benutzer für die letzten 20 Projekte und nicht im Projektordner; eine
Kopie des Ordners, etwa für eine Klasse, hat deshalb keine.

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
| `Strg+D` | Zeile duplizieren: die Zeile darunter noch einmal einfügen |
| `Alt+Pfeil hoch`, `Alt+Pfeil runter` | Zeile nach oben schieben, Zeile nach unten schieben |
| `Strg+Leertaste` | Vervollständigung erzwingen |
| `Strg+Mausrad`, `Strg+Plus`, `Strg+Minus` | Schrift größer oder kleiner, gilt für alle Editoren und die Panels „Ausgabe“ und „Meldungen“ und bleibt gemerkt |
| `Strg+0` | Normale Schriftgröße |
| `Tab` | vier Leerzeichen, nie ein Tabulatorzeichen |
| `Tab` bei markierten Zeilen | alle um eine Ebene einrücken |
| `Umschalt+Tab` | um eine Ebene ausrücken |
| Klick links im Zeilenrand | Haltepunkt setzen oder entfernen |
| Klick rechts im Zeilenrand | Klasse oder Funktion zuklappen |

Die rechte Maustaste im Editor zeigt dieselben Befehle als Menü, dazu
„Alles zuklappen“ und „Alles aufklappen“. Beides steht auch im Menü
„Quelltext“.

### Nur im Formular-Designer

| Taste | Was passiert |
|---|---|
| Pfeiltasten | Komponente um einen Rasterschritt verschieben |
| `Alt+Pfeil` | um genau einen Bildpunkt verschieben |
| `Umschalt+Pfeil` | Größe ändern |
| `Entf` | Komponente löschen |
| `Strg+D` | Komponente duplizieren |
| `F2` | Menü-Editor öffnen, bei einem MainMenu oder PopupMenu |
| Doppelklick | Ereignis-Methode anlegen und hinspringen |
| `Strg`- oder `Umschalt`-Klick | weitere Komponente zur Auswahl nehmen oder herausnehmen |
| Ziehen auf der freien Fläche | Rahmen aufziehen, alles darin auswählen |
| `Strg+A` | alle Komponenten auswählen |
| `Strg+C`, `Strg+X`, `Strg+V` | Komponenten kopieren, ausschneiden, einfügen, auch in ein anderes Formular |

Pfeiltasten, auch mit `Umschalt`, `Entf`, `Strg+D` und Ziehen wirken
auf die ganze Auswahl. Wird eine Komponente auf ein Panel oder eine
GroupBox gezogen, liegt sie danach darin, auch wenn mehrere zugleich
gezogen werden. Eingefügte Komponenten behalten ihre Ereignisse und
ihr Klappmenü, wenn es die Methode und das Menü im Zielformular gibt;
im selben Formular ist das immer so. Die rechte Maustaste ändert die
Tab-Reihenfolge und die Rasterweite (4, 8 oder 16 Pixel). Sind
mehrere Komponenten
ausgewählt, richtet „Ausrichten“ sie an den Kanten der zuletzt
angeklickten aus, verteilt sie gleichmäßig oder gibt ihnen deren
Breite oder Höhe.

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

### „Failed to load Python DLL“ beim Start

`Natter.exe` läuft nur zusammen mit den Ordnern `starter\` und
`python\` daneben im Programmordner. Fehlt `starter\`, meldet
Windows beim Start auf Englisch „Failed to load Python DLL“ mit einem
Pfad zu `python313.dll`, bevor Natter selbst etwas sagen kann. Das
passiert, wenn `Natter.exe` allein auf den Desktop oder einen
USB-Stick kopiert wurde, wenn eine Softwareverteilung nur einzelne
Dateien übernimmt oder wenn ein Virenscanner eine Datei aus
`starter\` in Quarantäne genommen hat. Auf dem Desktop gehört eine
Verknüpfung, keine Kopie; sonst hilft, Natter neu zu installieren.

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

### Ein Formular oder Diagramm zu viel

Units, Formulare und Diagramme haben im Projekt-Explorer einen
„⋮“-Knopf mit **Umbenennen …** und **Löschen …**; dasselbe Menü
liegt auf der rechten Maustaste. Bei einem Formular gelten beide
Befehle für die `.pfm`, die Unit und die erzeugte Datei zugleich,
und beim Umbenennen werden die Importe in den anderen Units
angepasst. Gelöschte Dateien landen im Papierkorb. Hat das Laufwerk
keinen, etwa ein Netzlaufwerk oder ein USB-Stick, sagt die Nachfrage
vorher, dass die Dateien endgültig gelöscht werden. Das Hauptformular,
das `main.py` startet, lässt sich weder umbenennen noch löschen.

### Zurück zur Startseite

**Ansicht → Startseite** führt von einem offenen Projekt zurück zum
Begrüßungsbildschirm, ohne etwas zu schließen. Derselbe Eintrag führt
wieder zurück in die Arbeit.

**Projekt → Projekt schließen** schließt das Projekt dagegen ganz,
etwa am Stundenende, bevor die nächste Klasse an den Rechner kommt.
Ungespeicherte Änderungen werden vorher erfragt wie beim Wechsel zu
einem anderen Projekt. Danach sind die Reiter und Diagrammfenster des
Projekts zu, Projekt-Explorer und Objektinspektor leer, und die
Startseite steht vorn.

### Ungespeicherter Text nach Abmelden oder Absturz

Solange in einem Projekt etwas ungespeichert ist, legt Natter alle
zwei Minuten eine Sicherung in den Projektordner, dazu noch einmal
unmittelbar vor der Frage nach dem Speichern beim Abmelden oder
Herunterfahren. Die Datei heißt wie das Projekt mit der Endung
`.natter-sicherung`, etwa `Ampel.natter-sicherung`, und enthält den
ungespeicherten Text jeder geänderten Unit und jedes geänderten
Diagramms. Wird gespeichert oder verworfen, verschwindet sie wieder,
ebenso beim Schließen des Projekts.

Liegt beim Öffnen eines Projekts noch eine Sicherung darin, etwa
weil bei Windows „Trotzdem abmelden“ gewählt wurde oder der Rechner
ausgegangen ist, nennt Natter die betroffenen Dateien und die Uhrzeit
der Sicherung. **Wiederherstellen** öffnet sie mit dem gesicherten
Text als ungespeicherte Änderung; auf die Platte kommt er erst mit
**Speichern**, und `Strg+Z` holt den Stand der Datei zurück.
**Verwerfen** löscht die Sicherung. Wurde eine Datei nach der
Sicherung noch anderswo geändert, steht das in der Frage, und
**Speichern** fragt vor dem Überschreiben nach.

Im Projekt-Explorer erscheint die Sicherung nicht, und sie kommt
weder in die Abgabe-ZIP noch in eine exportierte Exe oder in die
Kopie einer Aufgabe.

Ist ein Projekt in zwei Natter-Fenstern offen, sichert jedes Fenster
seine eigenen Dateien in dieselbe Datei, und keines entfernt, was das
andere gesichert hat. Was ein noch offenes Fenster gesichert hat,
bietet ein anderes nicht an. War das Projekt zuletzt an einem
anderen Rechner im selben Konto offen, etwa weil der Rechner im
vorigen Raum ausgegangen ist, bietet Natter dessen Sicherung an; der
Hinweis auf den anderen Rechner kommt danach. Stammt sie aus einem
anderen Konto, bleibt sie liegen und wird nicht angeboten, solange
die Sperrdatei jenen Rechner noch als Besitzer nennt, also bis eine
halbe Stunde, nachdem Natter dort zuletzt lief.

### Schrift am Beamer zu klein

`Strg+Plus` vergrößert den Quelltext und zugleich die Panels
„Ausgabe“ und „Meldungen“, also auch die Ausgabe eines laufenden
Programms, dazu die Panels des Debuggers („Variablen“, „Überwachen“,
„Aufrufstapel“) und offene Hilfeseiten wie „Erste Schritte“. Die ganze Oberfläche mit Menüs, Projekt-Explorer und
Objektinspektor wird unter **Werkzeuge → Einstellungen … →
Schriftgröße der Oberfläche** größer. Beide Einstellungen bleiben
über einen Neustart hinweg erhalten.

Natter merkt sich außerdem Größe und Lage des Fensters. Beim ersten
Start öffnet es maximiert; stand es zuletzt auf einem Bildschirm, der
nicht mehr angeschlossen ist, erscheint es maximiert auf dem
Hauptbildschirm.

---

## 7. Für den Einstieg im Unterricht

Unter **Datei → Beispielprojekte** stehen elf Projekte, die
aufeinander aufbauen — von der Begrüßung über Taschenrechner und
Bildergalerie bis zu Datenbank, CSV-Auswertung und einer kleinen
Regression. Die beiden letzten, „Notizbuch“ (Menü, Textdatei,
zweites Fenster) und „Malen“ (Zeichenfläche und Maus), setzen nur
den Taschenrechner voraus.

Ein angeklicktes Beispiel wird **als Arbeitskopie** nach
`Dokumente\Natter\Beispielprojekte` gelegt und dort geöffnet.
Das Original bleibt unverändert, und die eigenen Projekte eine Ebene
darüber bleiben unter sich.

Wird dasselbe Beispiel später noch einmal gewählt, öffnet Natter die
vorhandene Kopie mit dem Stand der letzten Stunde, statt eine weitere
anzulegen. Soll die Aufgabe von vorn beginnen, setzt **Projekt → Auf
Original zurücksetzen …** das geöffnete Beispiel auf den
Auslieferungszustand zurück. Alle Änderungen daran
gehen dabei verloren; Natter fragt vorher nach.

Für Schülerinnen und Schüler gibt es unter **Hilfe → Erste Schritte**
eine Anleitung, die in zehn Minuten vom leeren Bildschirm zum
laufenden Programm führt. **Hilfe → Komponenten-Referenz** listet jede
Komponente mit ihren Eigenschaften und Ereignissen auf. Dieses
Handbuch steht in Natter unter **Hilfe → Handbuch**.
