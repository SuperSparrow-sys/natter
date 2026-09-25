# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **34**.

## Ein neuer Punkt

```markdown
## 34. Kurz, was nicht stimmt

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

**Behoben ab 0.3.3:** `paketieren()` kopiert `LICENSE` in den
Programmordner, und die Rauchprobe (Schritt 6) bricht ab, wenn sie
fehlt. Offen bleibt nur das Durchklicken.


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

**Stand 25. September 2026 (Schülerweg 0.3.3, Teil 1):** `--no-cache`
und die `[UninstallDelete]`-Regel sind in Commit `d1db77a`. Der
Uninstaller von 0.3.0 ließ erwartungsgemäß `.ruff_cache` mit fünf
Dateien und damit den Ordner stehen. Eine frisch installierte 0.3.3
ließ sich restlos entfernen, allerdings ohne dass vorher die Prüfung
vor dem Start gelaufen war. Der eigentliche Nachweis, also
Deinstallation nach Benutzung, folgt in Teil 2 (Schritt N).


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

**Umgesetzt in Commit `9a83164`, nachgeprüft am Bau 0.3.3 (25. September
2026, Schülerweg Teil 1):** Der Bau meldet „35 Qt-Einträge unter GPL
entfernt", `Lizenzen\` hat 51 Einträge (0.3.2: 28), in einer frischen
Installation scheitert `import PySide6.QtCharts`. Der Test wird bei
einem eingetragenen GPL-Paket rot
(`tests/test_lizenzen_auslieferung.py`). Offen bleibt der Weg über
ein Update: wer 0.3.2 auf 0.3.3 aktualisiert, behält die Module
(Punkt 28). Bis Punkt 28 erledigt ist, bleibt dieser Punkt offen.

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

**Nachgeprüft an 0.3.3 (25. September 2026, Schülerweg Teil 1,
Schritt 8):** Das Setup von 0.3.2 über einer installierten 0.3.0 und
das von 0.3.3 über 0.3.2 zeigen dieselben acht Seiten wie bei einer
Erstinstallation: Sprachauswahl, Willkommen („wird jetzt Natter
Version 0.3.3 … installieren"), Lizenz, Hinweis, Zielordner,
Startmenü, Zusatzaufgaben, Bereit. Die vorhandene Fassung wird
nirgends genannt; Zielordner und Startmenü sind aus der vorhandenen
Installation vorbelegt. Dass beim Update auch Dateien liegen bleiben,
steht als eigener Punkt 28. Belege: `docs/auswertung/schuelerweg_0.3.3.md`.

---

## 27. Die Integritätsprüfung entfällt still, wenn `manifest.json` fehlt oder unlesbar ist

**Gemeldet:** 25. September 2026, Schülerweg 0.3.3, Teil 1,
Schritt 11, an der installierten Fassung.

**Beobachtet:** Mit veränderter `pcl\crt.py` erscheint beim Start
„Natter wurde verändert" mit der Datei und „Trotzdem starten?" - wie
vorgesehen. Wird zusätzlich `manifest.json` gelöscht, startet Natter
ohne jede Meldung. Dasselbe, wenn `manifest.json` nur unlesbar ist
(`{ kein json`). `installation_pruefen()` liefert in beiden Fällen
`None`, für die schnelle wie für die vollständige Prüfung. „Werkzeuge
→ Umgebung prüfen" meldet dann „Keine Prüfung möglich: Natter läuft
nicht aus einer gebauten Installation" - in einer gebauten
Installation.

**Ursache:** nachgewiesen. `programmordner()` in
`ide/integritaet/start_pruefung.py` erkennt die Installation am
Vorhandensein von `manifest.json`; fehlt die Datei, gilt der Ordner
als Entwicklungsbaum. `installation_pruefen()` fängt `ManifestFehler`
ab und gibt ebenfalls `None` zurück, also auch bei unlesbarer Datei
oder unbekanntem Format. Der Docstring nennt ein fehlendes Manifest
ausdrücklich „keinen Manipulationsverdacht". Wer eine Datei im
Programmordner verändert, kann die Prüfung damit durch Löschen einer
zweiten Datei abschalten.

**Zu tun:** Die Installation an etwas erkennen, das sich nicht mit
dem Manifest zusammen entfernen lässt, etwa am Ort
(`python\pythonw.exe` neben `Natter.exe`) oder an einer Marke im
Starter. In einer erkannten Installation sind fehlendes, unlesbares
und unbekanntes Manifest Abweichungen mit eigener Meldung. Erledigt,
wenn die drei Fälle aus der Auswertung (Kerndatei verändert, Manifest
entfernt, Manifest unlesbar) je eine Warnung zeigen und der
Entwicklungsbaum weiter ohne Warnung startet.

---

## 28. Ein Update lässt Dateien der alten Fassung in `site-packages` liegen

**Gemeldet:** 25. September 2026, Schülerweg 0.3.3, Teil 1, Schritt 8.

**Beobachtet:** 0.3.2 installiert, 0.3.3 still darüber installiert.
Danach liegen 30 223 Dateien im Programmordner, bei einer frischen
0.3.3 sind es 30 075. Die 148 zusätzlichen Dateien:

- 141 Dateien der Qt-Module Charts, Data Visualization und Graphs
  (`Qt6Charts.dll`, `QtCharts.pyd`, `qml\QtCharts\…` und so weiter).
  `import PySide6.QtCharts` gelingt nach dem Update wieder. Genau diese
  Module entfernt der Bau seit 0.3.3, weil sie nur unter GPL stehen
  (Punkt 24); wer aktualisiert statt neu installiert, behält sie.
- 7 Dateien `natter-0.3.2.dist-info` neben `natter-0.3.3.dist-info`.
  `importlib.metadata.version("natter")` und `pip list` melden danach
  0.3.2. Natter selbst zeigt 0.3.3, weil es die Nummer aus
  `ide/main.py` liest.

Die vollständige Prüfung unter „Werkzeuge → Umgebung prüfen" meldet
trotzdem „alle Programmdateien unverändert".

**Ursache:** nachgewiesen. `[InstallDelete]` in `tools/natter.iss`
leert nur die sieben Ordner, die Natter selbst in `site-packages`
mitbringt, nicht die Fremdpakete und nicht die `dist-info` von Natter.
Das Manifest lässt Fremdpakete in `site-packages` bewusst aus, damit
pip dort nachinstallieren darf; Altdateien fallen deshalb nicht als
„fremd" auf.

**Zu tun:** Beim Update `{app}\python` vollständig ersetzen (siehe
Punkt 26, dort auch die Frage nach Paketen, die über „Pakete"
nachinstalliert wurden), mindestens aber die entfernten Qt-Module und
alte `natter-*.dist-info` per `[InstallDelete]` löschen. Erledigt,
wenn nach einem Update von 0.3.2 die Dateiliste der einer frischen
Installation entspricht (bis auf die Uninstaller-Dateien) und
`import PySide6.QtCharts` scheitert.

---

## 29. `Zertifikat-eintragen` lässt den verlangten Vergleich des Fingerabdrucks nicht zu

**Gemeldet:** 25. September 2026, Schülerweg 0.3.3, Teil 1, Schritt 5
(gelesen, nicht ausgeführt).

**Beobachtet:** `ZUERST-LESEN.txt` verlangt: „Vor dem Eintragen
deshalb den Fingerabdruck vergleichen, den das Skript anzeigt …
Stimmt er nicht ueberein, nicht eintragen und nachfragen."
`Zertifikat-eintragen.ps1` zeigt Aussteller, Gültigkeit und
Fingerabdruck an und trägt unmittelbar danach in beide Speicher ein,
ohne anzuhalten. Den Vergleich kann eine Lehrkraft erst anstellen,
wenn das Zertifikat schon eingetragen ist.

**Ursache:** nachgewiesen, `tools/paket/Zertifikat-eintragen.ps1`:
zwischen der Ausgabe des Fingerabdrucks und `Import-Certificate` steht
keine Rückfrage.

**Zu tun:** Nach der Anzeige nachfragen („Stimmt der Fingerabdruck mit
dem in ZUERST-LESEN.txt überein? (J/N)") und bei Nein ohne Eintrag
beenden; alternativ den erwarteten Fingerabdruck im Skript
hinterlegen und bei Abweichung abbrechen. Erledigt, wenn ein
untergeschobenes anderes `.cer` nicht mehr eingetragen wird, ohne dass
jemand es bestätigt.

---

## 30. Der Installer spricht mit „Sie" an

**Gemeldet:** 25. September 2026, Schülerweg 0.3.3, Teil 1, Schritte 8
und 13.

**Beobachtet:** Die Seiten des Setup-Assistenten enthalten 19 Stellen
mit „Sie" oder „Ihr": „Wählen Sie die Sprache aus", „auf Ihrem
Computer installieren", „Sie sollten alle anderen Anwendungen
beenden", „Lesen Sie bitte …", „Klicken Sie auf ‚Weiter'". AGENTS.md
schließt die Textseiten des Installers ausdrücklich in die Regel ein,
niemanden anzusprechen. Vor der Willkommensseite fragt das Setup
außerdem nach der Sprache (Deutsch oder Englisch).

**Ursache:** nachgewiesen. Die Texte sind die Standardmeldungen von
Inno Setup aus `compiler:Languages\German.isl`; `tools/natter.iss`
überschreibt keine davon. `tests/test_textstil.py` prüft die eigenen
Textseiten unter `tools/lizenz_vorlagen/` und `natter.iss` selbst
(auf Verweise auf fremde Werkzeuge), aber nicht die Meldungen, die
Inno Setup aus `German.isl` mitbringt. Die Sprachauswahl
erscheint, weil zwei Sprachen eingetragen sind und
`ShowLanguageDialog` nicht gesetzt ist.

**Zu tun:** Die angezeigten Meldungen in einem `[Messages]`-Abschnitt
(oder einer eigenen `.isl`) unpersönlich fassen, etwa „Natter 0.3.3
wird jetzt installiert." und „Zum Fortfahren auf ‚Weiter' klicken.";
die Sprachauswahl abschalten oder nur Deutsch eintragen. Ein Test,
der die überschriebenen Meldungen mit derselben Regel prüft wie die
übrigen Texte. Erledigt, wenn ein Durchlauf aller Seiten ohne „Sie"
und „Ihr" auskommt.

---

## 31. `Natter-pruefen` meldet eine fehlende Installation als „unvollständig"

**Gemeldet:** 25. September 2026, Schülerweg 0.3.3, Teil 1, Schritt 5.

**Beobachtet:** Ohne installierte Natter schreibt der Bericht
„Programmordner vorhanden: False" und darunter „Die Installation ist
unvollstaendig - python\python.exe fehlt. Natter neu installieren."
Eine Installation gibt es aber gar nicht. Gesucht wird außerdem nur
unter `%LOCALAPPDATA%\Programs\Natter`; eine Installation für alle
Benutzer unter `C:\Program Files\Natter` würde genauso gemeldet.

**Ursache:** nachgewiesen, `tools/paket/Natter-pruefen.ps1`: der Pfad
ist fest eingetragen, und die beiden Fälle „Ordner fehlt" und „Ordner
da, Python fehlt" teilen sich eine Meldung.

**Zu tun:** Den Installationsort aus dem Deinstallationseintrag lesen
(`…\Uninstall\{961DA420-CA63-4436-9023-9CA411B620DA}_is1`,
`InstallLocation`, unter HKCU und HKLM) und die Fälle trennen: „Natter
ist für dieses Konto nicht installiert" gegenüber „Die Installation
ist unvollständig". Erledigt, wenn beide Fälle ihre eigene Meldung
bekommen und eine systemweite Installation gefunden wird.

---

## 32. Der Auslieferungsbau prüft mit ruff auch nicht eingecheckte Ordner

**Gemeldet:** 25. September 2026, Schülerweg 0.3.3, Teil 1, Schritt 3.

**Beobachtet:** Der erste Bauversuch brach in Schritt 3 ab. `ruff
check .` hatte eine Sicherungskopie von Schülerprojekten unter
`build\auswertung\sicherung\` mitgeprüft und dort `I001` gemeldet -
dieselbe Regel, die für `beispielprojekte/**` ausdrücklich
abgeschaltet ist. Schritt 1 meldet `build/` zugleich als nicht
eingecheckt.

**Ursache:** nachgewiesen. `_ruff_pruefen()` in
`tools/auslieferung_bauen.py` ruft `ruff check .` auf. Die Ordner, die
der Bau selbst unter `build\` anlegt (`bau-cache`, `python-download`),
tragen je eine eigene `.gitignore` mit `*` und sind damit für git und
ruff ausgenommen. `build/` als Ganzes steht aber weder in der
`.gitignore` des Repositorys noch in einer `exclude`-Liste von ruff;
jeder andere Ordner dort wird mitgeprüft.

**Zu tun:** `build/` in die `.gitignore` des Repositorys aufnehmen
(ruff beachtet sie) oder `extend-exclude = ["build"]` in
`pyproject.toml`. Erledigt, wenn ein Ordner mit fehlerhaften `.py`
unter `build\` den Bau nicht mehr aufhält und Schritt 1 ihn nicht mehr
meldet.

---

## 33. Kleinere Befunde aus dem Schülerweg 0.3.3, Teil 1

**Gemeldet:** 25. September 2026, Schülerweg 0.3.3, Teil 1.

**Beobachtet:**

- Das Ladebild zeigt bei jedem Start „Projekt wird geöffnet …", auch
  wenn kein Projekt übergeben wurde (`ide/main.py`, `starten()`: die
  Meldung steht vor `_projekt_aus_argv_oeffnen`, ohne Prüfung).
- `ZUERST-LESEN.txt` nennt die Setup-Datei fest mit „(275 MB)",
  tatsächlich sind es 276,4 MB, und schreibt „die Datei kommt von
  einem Stick", obwohl die ZIP über GitHub verteilt wird.
- „Werkzeuge → Umgebung prüfen" läuft im GUI-Thread; das Fenster
  reagiert für die Dauer der Prüfung (2,4 s) nicht.
- Ausgeliefert wird Python 3.13.15, getestet wird im Entwicklungsbaum
  mit 3.13.14. `uv.lock` legt die Patch-Version von Python nicht fest;
  die Rauchprobe in Schritt 6 fängt grobe Folgen ab.

**Ursache:** jeweils wie oben angegeben.

**Zu tun:** Die Meldung im Ladebild nur zeigen, wenn ein `.natter`
übergeben wurde; die Größe in `ZUERST-LESEN.txt` beim Bau einsetzen
oder weglassen und den Satz zum Stick allgemein fassen; die
vollständige Prüfung in einen Hintergrund-Thread legen; die
Python-Version für Bau und Entwicklungsbaum aus derselben Quelle
nehmen. Erledigt, wenn die vier Stellen behoben oder einzeln
begründet zurückgestellt sind.

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
