# Prüfbericht – Funktionsprüfung der Oberfläche

**Stand:** 19. September 2026 · **Natter 0.1.0** · Windows 11, Qt 6.11.2

Zu Arbeitspaket M11, Abschnitt 3. Der Anlass steht dort: in M9 haben
Bildschirmfotos und zurückgelesene PDFs **sieben** Fehler gefunden, die
alle Tests bestanden hatten, und die drei Fehlermeldungen des Nutzers
(Rollen, Menü-Abstürze, Zwischenablage) waren keine Testlücke, sondern
eine Lücke zwischen Test und echter Bedienung.

Geprüft wird deshalb nicht der Quelltext, sondern die Bedienung: jeder
Eintrag wird **ausgelöst**, jede Kachel **abgelegt**, jedes Dock
**geschlossen und wieder geöffnet**.

## Was geprüft wird

| Bereich | Anzahl | Wo |
|---|---|---|
| Menüeinträge der Haupt-IDE | 53 (alle aktiv) | `tests/test_ide_funktionspruefung.py` |
| Knöpfe der Werkzeugleiste | 8 | ebenda |
| Docks (schließen + wiederherstellen) | 5 | ebenda |
| Kacheln der Komponentenpalette | 20 | ebenda |
| Diagrammarten mit eigenem Menü | 7 | `tests/test_diagramm_menue_ausloesen.py` |
| Formen und Verbindungen der Diagramm-Paletten | 48 | `tests/test_diagramm_*` |

Die Liste wird **aus der Oberfläche gelesen**, nicht von Hand gepflegt:
aus der Menüleiste, der Werkzeugleiste und der Palette. Ein neuer
Menüeintrag ist damit vom nächsten Testlauf an mitgeprüft, ohne dass
jemand daran denken muss.

## Ergebnis

Alle 53 Menüeinträge, alle 8 Knöpfe der Werkzeugleiste, alle 5 Docks und
alle 20 Palettenkacheln ließen sich auslösen bzw. bedienen, ohne dass
eine Ausnahme hochkam. Ebenso die Menüs aller sieben Diagrammarten.

## Vier Einträge sind aus dem Rundlauf ausgenommen

Nicht, weil sie nicht funktionierten, sondern weil sie **wirklich etwas
tun**, das in einem Testlauf nichts zu suchen hat:

| Eintrag | Grund |
|---|---|
| Starten / Starten ohne Debugger | startet einen echten Python-Prozess; ohne die Ausnahme bliebe nach jedem Testlauf ein Programm samt Debugger zurück. Eigens geprüft mit stillgelegtem Starter |
| Alle Tests ausführen | startet pytest. **Innerhalb** von pytest ist das eine Endlosschleife – der Lauf blieb real stehen, bis das Zeitlimit ihn abbrach |
| Als Exe exportieren … | baut wirklich eine Exe, das dauert Minuten |

## Was die Prüfung gefunden hat

**Keine Abstürze**, aber drei Stellen, an denen der Rundlauf stehen
blieb, weil ein modaler Dialog headless nie zurückkommt. Jede davon
musste einzeln gefunden werden, indem der Lauf **vor** jedem Eintrag
meldet, welcher gerade dran ist:

| Eintrag | Dialog |
|---|---|
| Suchen → Gehe zu Zeile … | `QInputDialog.getInt` |
| Hilfe → Über Natter | `QMessageBox.about` |
| Projekt → Alle Tests ausführen | pytest in pytest |

Das sind **keine** Fehler im Programm – in echter Bedienung ist ein
modaler Dialog genau richtig. Aber sie sind der Grund, warum diese Art
Prüfung vorher nicht existierte: ein einziger nicht stillgelegter Dialog
lässt den ganzen Testlauf hängen, ohne zu sagen, woran.

## Was diese Prüfung **nicht** abdeckt

Ehrlich aufgeschrieben, damit der Bericht nicht mehr verspricht, als er
hält:

- Sie prüft, dass ein Eintrag **nicht abstürzt**, nicht dass er das
  Richtige tut. Dafür gibt es die fachlichen Tests daneben
- Dialoge werden stillgelegt, als hätte man abgebrochen; der Weg durch
  einen ausgefüllten Dialog ist nicht mitgeprüft
- Kontextmenüs sind noch nicht dabei
- „Jede Eigenschaft jeder Komponente im Objektinspektor ändern und
  nachsehen, ob die Änderung ankommt“ (M11, Abschnitt 3) steht noch aus

## Bildschirmfotos

Bewusst **nicht** im Repository. Der Nutzer hat im September 2026
festgelegt, dass sie Arbeitsmaterial sind: angesehen, ausgewertet,
danach gelöscht. Was sie gefunden haben, steht als Text in den
Commit-Nachrichten und in den Arbeitspaketen – dort ist es auch in
einem Jahr noch lesbar.
