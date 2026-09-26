# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **47**.

## Ein neuer Punkt

```markdown
## 47. Kurz, was nicht stimmt

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

## 46. Der Signaturtest läuft im CI nicht, und ein Debugger-Test wackelt dort

**Gemeldet:** 26. September 2026, GitHub-Actions-Läufe zu `250930c`
bis `18432cd`.

**Beobachtet:**

- `test_schritt_10_meldet_eine_signierte_vorlage` in
  `tests/test_auslieferung_bauen.py` braucht eine Datei, deren Kopie
  `Get-AuthenticodeSignature` als `Valid` meldet. Auf dem Runner
  (Windows Server) gilt keine der Kandidaten als gültig signiert,
  weder `notepad.exe` noch `pwsh.exe` noch `git.exe`. Der Test wird
  dort übersprungen („keine Datei mit eingebetteter Signatur
  gefunden“); lokal läuft er und ist grün. Die Prüfung von Schritt 10
  auf signierte Vorlagen wird damit im CI nicht getestet.
- `test_variablen_panel_kommt_beim_halt_nach_vorne` in
  `tests/test_hauptfenster_debugger.py` lief in Lauf 18432cd in die
  Zeitgrenze von 45 Sekunden, bevor debugpy am Haltepunkt hielt. Der
  Code war derselbe wie im grünen Lauf davor; die Wiederholung des
  Jobs war grün.

**Ursache:** für den ersten Teil vermutlich die Zertifikatsprüfung auf
dem Runner (Katalogsignaturen, Sperrlisten ohne Netz), nicht
nachgewiesen. Für den zweiten noch offen; ein langsamer Runner liegt
nahe.

**Zu tun:** Für den Signaturtest eine Datei finden, die auch auf dem
Runner `Valid` ist, ohne dafür ein Zertifikat in einen Windows-Speicher
einzutragen. Beim Debugger-Test beobachten, ob er wieder ausfällt;
wenn ja, die Startzeit von debugpy auf dem Runner messen. Erledigt,
wenn der Signaturtest im CI läuft und der Debugger-Test in zehn
Läufen hintereinander grün ist.

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
