# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **27**.

## Ein neuer Punkt

```markdown
## 27. Kurz, was nicht stimmt

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

## 4. Die Lizenzseite des Installers ist nie angesehen worden

**Beobachtet:** Die Textdateien `tools/lizenz_vorlagen/*.txt` sind
geprüft — Umlaute, Byte-Order-Mark, Inhalt. Wie sie im Installer
**aussehen**, ist nie jemand nachgegangen.

**Warum nicht:** Die Abnahme läuft über eine stille Installation
(`/VERYSILENT`), bei der keine Seite erscheint. Ein Bildschirmfoto des
Assistenten braucht eine angemeldete, interaktive Sitzung; die stand
bei den bisherigen Durchgängen nicht zur Verfügung.

**Noch zu prüfen:** Den Installer einmal von Hand durchklicken und
nachsehen, ob Lizenz- und Hinweisseite vollständig, mit richtigen
Umlauten und ohne abgeschnittene Zeilen erscheinen. **Das bleibt
offen** - dafür braucht es einen Menschen vor dem Bildschirm, und
eine stille Installation zeigt keine Seite.

**Was sich ohne das festhalten ließ** (zwei Tests in
`tests/test_textstil.py`):

- Beide Seiten sind in `tools/natter.iss` überhaupt eingebunden
  (`LicenseFile`, `InfoBeforeFile`). Eine Seite, die niemand
  einbindet, kann noch so schön sein.
- Keine Zeile ist länger als 80 Zeichen. Inno Setup zeigt beide
  Seiten in einem Feld fester Breite; was länger ist, bricht um und
  sieht nach einem Fehler aus. Gemessen liegt die längste Zeile bei
  74 Zeichen.

Umlaute und Byte-Order-Mark prüfen bereits
`test_der_installer_liest_seine_texte_als_utf8` und die
Umlaut-Tests.

**Nachgewiesen ohne Durchklicken (25. September 2026):** Die
Lizenzseite sagt „Die vollständige Lizenz steht nach der Installation
in der Datei LICENSE im Installationsordner." Dort liegt keine: der
Installationsordner enthält nur `Natter.exe`, `python\`, `Lizenzen\`
und `manifest.json`; Natters `LICENSE` steckt nur in
`python\Lib\site-packages\natter-<Version>.dist-info\licenses\`.
Entweder die Datei beim Paketieren nach `{app}\LICENSE` kopieren oder
den Satz ändern. Das lässt sich ohne Durchklicken beheben; das
Durchklicken selbst bleibt.


---

## 6. Prozesszeiten sind auf diesem Rechner nicht messbar

**Beobachtet:** Weder `Get-Process | Select CPU` noch die
WMI-Zähler `UserModeTime`/`KernelModeTime` liefern etwas anderes als
null — auch nicht für Prozesse, die nachweislich rechnen. Beim
erfolgreichen Auslieferungsbau standen sie genauso auf null wie beim
hängenden Testlauf.

**Folge:** „Null CPU-Zuwachs" taugt hier nicht als Beleg für einen
Stillstand. Zweimal führte das fast zu einer Fehldiagnose: einmal
wurde ein gesunder Lauf für hängend gehalten, einmal wäre ein echter
Hänger beinahe mit der falschen Begründung erklärt worden.

**Was stattdessen trägt:** ob das Protokoll fortschreitet, und der
Vergleich mit der bekannten Normaldauer (Testlauf 3:30–4:00,
Auslieferungsbau rund 10 Minuten).

**Noch zu prüfen:** Ob es an der Sandbox liegt oder an
Windows-Berechtigungen. Ein verlässlicher Zähler wäre nützlich, weil
die Laufzeit-Angaben sonst nur aus Erfahrung stammen.


---

## 21. Nach dem Deinstallieren bleibt ein Ordner zurück

**Beobachtet:** Beim Durchgang zu 0.3.0 entfernte der Uninstaller
30.375 Dateien und ließ acht liegen — einen `.ruff_cache` im
Programmordner, und damit den Ordner selbst.

**Ursache — nachgewiesen.** Den Cache legt die Prüfung vor dem Start
an, also während des Unterrichts und lange nach der Installation.
Inno Setup entfernt beim Deinstallieren, was es selbst geschrieben
hat; alles andere bleibt. Derselbe Fall wie beim Uninstaller im
Manifest (siehe Arbeitspaket M13), nur andersherum.

**Was das bedeutet:** Wer Natter entfernt, findet unter
`%LOCALAPPDATA%\Programs\Natter` weiterhin einen Ordner. Auf einem
Schulrechner, der zwischen zwei Halbjahren aufgeräumt wird, sieht das
nach einer halben Deinstallation aus.

**Woher der Cache kommt — nachgewiesen (25. September 2026).**
`projekt_pruefen()` in `ide/run/pruefung.py` ruft `ruff check`
ohne Arbeitsordner und ohne `--no-cache` auf. ruff legt seinen Cache
dann im Arbeitsordner von Natter an, und das ist der Programmordner.
Der Cache bringt der Prüfung nichts: sie läuft über ein kleines
Schülerprojekt und ist ohnehin schnell.

**Zu tun:**

- Die Ursache: `--no-cache` in `projekt_pruefen()`. Dann entsteht kein
  `.ruff_cache` mehr, weder im Programmordner noch sonst wo.
- Als Netz dahinter eine `[UninstallDelete]`-Regel für
  `{app}\.ruff_cache` in `tools/natter.iss`. Nicht für `{app}` selbst:
  wählt jemand beim Installieren einen Ordner wie `Dokumente`, würde
  eine solche Regel ihn beim Entfernen leeren.
- Nachsehen, was die IDE sonst noch neben sich schreibt: `__pycache__`
  in `site-packages` entsteht beim ersten Import und dürfte dasselbe
  Problem haben. Beim Bau von 0.2.0 waren es über achtzig `.pyc`.
- Prüfen, ob eine solche Regel etwas löscht, das ein Schüler dort
  abgelegt hat. Im Programmordner hat er nichts zu suchen, aber
  „nichts zu suchen" ist kein Beweis.


---

## 24. Die Auslieferung enthält GPL-Module, und Lizenztexte fehlen

**Gemeldet:** 25. September 2026, beim Zusammenfassen der
Planungsunterlagen in `docs/bericht.md`, Fassung 0.3.2.

**Beobachtet:** AGENTS.md und `docs/bericht.md`, Abschnitt 5, verlangen
nur Abhängigkeiten mit freizügiger Lizenz oder LGPL, kein PyQt und
keine GPL-only-Module von Qt wie Qt Charts. Geplant war dafür ein Test,
der die Pakete der Auslieferung mit ihrer Lizenz auflistet und bei GPL
fehlschlägt. Diesen Test gibt es nicht; kein Test im Repository nennt
„GPL".

**Ursache:** nachgewiesen - der Test stand nur im Plan (früher
`entwicklung.md`, Abschnitte 17.7 und 19) und wurde nie geschrieben.
`_lizenzen_sammeln()` in `tools/ide_paketieren.py` sammelt die
Lizenztexte und warnt bei fehlender Angabe, prüft aber nicht, welche
Lizenz es ist.

**Nachgemessen in `dist\Natter` (Fassung 0.3.2):**

- **Qt Charts, Qt Data Visualization und Qt Graphs werden
  ausgeliefert.** In `site-packages\PySide6` liegen `Qt6Charts.dll`,
  `Qt6ChartsQml.dll`, `Qt6DataVisualization.dll`,
  `Qt6DataVisualizationQml.dll`, `Qt6Graphs.dll`,
  `Qt6GraphsWidgets.dll` und die passenden `.pyd`/`.pyi`. Sie kommen
  mit `PySide6_Addons` und stehen nur unter GPL-3.0 oder einer
  kaufbaren Lizenz, nicht unter LGPL. Natter benutzt sie nicht; die
  frühere Planung sagte, sie würden aus dem Paket entfernt - das ist
  nie umgesetzt worden.
- **32 von rund 50 mitgelieferten Paketen haben keinen Lizenztext in
  `Lizenzen\`**, darunter PyInstaller, jedi, cryptography, Pillow,
  fontTools, contourpy, attrs, packaging und setuptools. MIT, BSD und
  Apache verlangen, dass der Lizenztext bei der Weitergabe dabei ist.
  Ursache: `_LAUFZEIT_PAKETE` in `tools/ide_paketieren.py` ist eine
  von Hand gepflegte Liste; laut ihrem Kommentar steckt PyInstaller
  „nicht in der gebauten Exe", was seit M13 nicht mehr stimmt.
- **PyInstaller steht unter GPL-2.0** mit einer Ausnahme für die
  erzeugten Programme. Natter braucht es für „Als Exe exportieren".
  Die Regel in AGENTS.md („nur freizügige Lizenzen oder LGPL") deckt
  das nicht ab; die Lizenzseite des Installers nennt es bereits.

**Zu tun:**

- Die Qt-Module Charts, DataVisualization und Graphs nach dem
  Auspacken entfernen, wie Tcl/Tk (`_tcl_tk_entfernen()`), und in der
  Rauchprobe (Schritt 6) prüfen, dass sie fehlen.
- Lizenztexte für **jedes** Paket der mitgelieferten Python sammeln,
  aus den Metadaten der installierten Pakete statt aus einer Liste.
- Ein Test, der für jedes Laufzeitpaket die Lizenz liest und bei GPL,
  AGPL oder unbekannter Lizenz fehlschlägt. Erlaubt: LGPL, die
  Doppellizenzen von PySide6/shiboken6 („LGPL-3.0 OR GPL"), und
  PyInstaller als ausdrücklich genannte Ausnahme - sofern das so
  entschieden wird.
- Erledigt, wenn die drei Module in `dist\Natter` fehlen, jedes Paket
  einen Lizenztext in `Lizenzen\` hat und der Test bei einem
  absichtlich eingetragenen GPL-Paket rot wird.

---

## 26. Ein Update erkennt die vorhandene Fassung nicht sichtbar

**Gemeldet:** 25. September 2026, vom Nutzer: „Wenn bereits ein
Natter-Programm installiert ist, soll die Exe das erkennen und sagen:
Update auf Version … Dabei sollen die veränderten Daten entweder
komplett gelöscht oder ersetzt werden."

**Stand heute (`tools/natter.iss`):** Die Grundlage ist da. Die feste
`AppId` lässt Inno Setup eine vorhandene Installation erkennen und
deren Ordner wieder vorschlagen, und `[InstallDelete]` leert vor dem
Kopieren die sieben Ordner, die Natter selbst in `site-packages`
mitbringt (`ide`, `pcl`, `docs` …). Es fehlt:

- Kein Hinweis auf das Update. Der Assistent sieht genauso aus wie
  bei einer Erstinstallation; die installierte Fassung wird nirgends
  genannt.
- Zielordner und Startmenü-Ordner werden bei einem Update erneut
  abgefragt (`DisableDirPage=no`, `DisableProgramGroupPage=no`).
- Kein Schutz gegen eine ältere Fassung über einer neueren.
- Die mitgelieferte Python wird nur überschrieben. Bringt eine neue
  Fassung etwa ein neueres numpy mit, bleiben Dateien der alten
  Paketversion liegen, die es in der neuen nicht mehr gibt - ein
  gemischter Stand, der erst beim Import auffällt. Dieselbe Sorte
  Befund wie beim Update auf 0.2.0 (`docs/bericht.md`, Abschnitt 8).

**Wie es in der Praxis gelöst wird** (Inno-Setup-Installer wie VS
Code, Git für Windows, Notepad++):

- Dieselbe `AppId` für alle Fassungen; Inno übernimmt dann Ordner,
  Startmenü und Zusatzaufgaben der vorhandenen Installation.
- `DisableDirPage=auto` und `DisableProgramGroupPage=auto`: bei einem
  Update entfallen die Seiten, bei einer Erstinstallation erscheinen
  sie.
- Die installierte Fassung aus der Registrierung lesen
  (`…\Uninstall\{AppId}_is1`, Wert `DisplayVersion`, unter HKCU oder
  HKLM) und im `[Code]`-Abschnitt auf der Willkommensseite nennen:
  „Natter 0.3.2 ist installiert und wird auf 0.3.3 aktualisiert. Die
  Projekte bleiben erhalten." Ist die installierte Fassung neuer,
  nachfragen oder abbrechen.
- Den Programmordner vollständig ersetzen, weil alles, was einem
  Benutzer gehört, woanders liegt: Projekte unter `Dokumente\Natter`,
  Einstellungen unter `%APPDATA%\Natter`. Zwei übliche Wege: den
  Anwendungsordner vor dem Kopieren leeren (`[InstallDelete]` mit
  `filesandordirs` für `{app}\python`), oder die alte Fassung vorher
  still über ihren eigenen Uninstaller entfernen. Der erste Weg ist
  der schlichtere und behält die Startmenü-Einträge.
- Eine laufende Natter vorher schließen (`CloseApplications`, Inno
  nutzt dafür den Neustart-Manager von Windows).

**Zu klären:** Über das Menü „Pakete" nachinstallierte Pakete liegen
in `{app}\python` und gingen beim vollständigen Ersetzen verloren. Die
Update-Meldung muss das sagen, oder die Liste der nachinstallierten
Pakete wird vorher gesichert und danach wieder eingespielt.

**Zu tun:** Hinweis auf der Willkommensseite mit alter und neuer
Nummer, Ordner-Seiten bei einem Update überspringen, Schutz gegen
eine ältere Fassung, `{app}\python` vor dem Kopieren vollständig
leeren, laufende Natter schließen. Erledigt, wenn ein Update von
0.3.2 auf die neue Fassung den Hinweis zeigt, danach keine Datei der
alten Fassung mehr im Programmordner liegt und Projekte und
Einstellungen unberührt sind.

---

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

## 7. Der Starter braucht die Hälfte der Startzeit ~~(zurückgestellt)~~

**Beobachtet:** Vom Doppelklick bis zum Fenster vergehen rund 1,65
Sekunden. Davon entfallen etwa 790 Millisekunden auf `Natter.exe`,
bevor überhaupt Python anläuft — der Starter entpackt sich und fährt
dann eine zweite Python hoch.

**Entschieden:** Der Starter bleibt, wie er ist. `Natter.exe` behält
sein eigenes Symbol, seine Versionsangabe und seine Signatur; die
Zeit wird dafür in Kauf genommen.

Hier nur festgehalten, damit die Frage nicht in einem halben Jahr noch
einmal von vorn aufgemacht wird. Gemessene Alternativen waren:
`--onedir` statt `--onefile` (spart 200 ms, kostet 15,8 MB und einen
Ordner neben der Exe) und die Verknüpfung direkt auf `pythonw.exe`
(spart 790 ms, kostet das eigene signierte `Natter.exe`).
