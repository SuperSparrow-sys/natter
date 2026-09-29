---
description: Unabhängige Prüfung des Unterbaus von Natter auf Sicherheit, Absturzsicherheit und Datenintegrität; Befunde in docs/offene_punkte.md eintragen
---

# Sicherheitsprüfung: Hält der Unterbau?

Natter ist eine Python-Entwicklungsumgebung für den Informatikunterricht
(Quelltext unter `ide/`, Komponentenbibliothek `pcl/`, Starter und Bau
unter `tools/`, Beispielprojekte unter `beispielprojekte/`, Schemas
unter `schemas/`). Aufgabe ist eine unabhängige Prüfung des Unterbaus,
nicht der Oberfläche: Was lässt sich missbrauchen, was bricht ab, was
geht kaputt, wenn etwas schiefgeht? Nichts reparieren.

## Ohne Vorwissen anfangen

`docs/offene_punkte.md`, `docs/erledigte_punkte.md`, `docs/bericht.md`
und alles unter `docs/auswertung/` erst am Ende lesen, beim Abgleich.
Die Prüfung soll nicht dort suchen, wo schon gesucht wurde.

Maßstab sind drei Lagen:

- Eine Schülerin, die neugierig oder übermütig ist und ausprobiert,
  was geht: seltsame Dateinamen, riesige Dateien, Endlosschleifen,
  Programme, die Tausende Fenster oder Prozesse öffnen.
- Eine Schülerin, die im Prüfungsmodus an die Beispiellösungen, an
  fremde Abgaben oder ins Internet will.
- Ein Schulrechner mit eingeschränktem Konto, Netzlaufwerk als
  Dokumente-Ordner, Virenscanner, abgeschaltetem Netz, knappem
  Speicher und einem Stromausfall mitten im Speichern.

## Wonach gesucht wird

1. Ausführung fremden Codes: Stellen, an denen Inhalte aus Dateien
   (`.natter`, `.pfm`, `.pdiag`, `.lfm`, CSV, Einstellungen, ZIP)
   ausgeführt oder ungeprüft interpretiert werden - `eval`, `exec`,
   `pickle`, `yaml.load`, `subprocess` mit `shell=True`, Befehle, die
   aus Dateiinhalten zusammengesetzt werden, Importe aus dem
   Arbeitsordner, die eine gleichnamige Datei unterschieben könnte.
2. Dateisystem: Pfade aus Dateien oder Eingaben, die aus dem
   Projektordner hinausführen (`..`, absolute Pfade, Laufwerke,
   UNC-Pfade, Verknüpfungen), Entpacken von ZIP-Dateien, Überschreiben
   fremder Dateien, Löschen außerhalb des Projekts, reservierte
   Windows-Namen, sehr lange Pfade.
3. Absturzsicherheit: Ausnahmen ohne Behandlung im Hauptfaden und in
   Hintergrundfäden, Qt-Objekte, die aus dem falschen Faden oder nach
   dem Löschen benutzt werden, Rekursion ohne Grenze, Speicher, der
   mit der Laufzeit wächst, Unterprozesse ohne Zeitgrenze, Rohre, die
   voll laufen oder von Kindprozessen geerbt werden, Prozesse, die
   nach dem Beenden übrig bleiben.
4. Datenintegrität: Speichern, das bei Abbruch eine halbe Datei
   hinterlässt (nicht atomar), gleichzeitiges Schreiben aus zwei
   Stellen, Kodierungen (UTF-8, BOM, ANSI), beschädigte oder
   handbearbeitete Projektdateien, Schemaversionen, die nicht geprüft
   werden, Rückgängig-Stapel, die nach einem Fehler nicht mehr zum
   Inhalt passen.
5. Prüfungsmodus und Einschränkungen: Wege an den Sperren vorbei
   (Menüs, Tastenkürzel, Befehlspalette, Drag & Drop, Kommandozeile,
   Dateiverknüpfung, Einstellungsdatei), Zeitangaben, die sich durch
   Uhrverstellen umgehen lassen, und ob das dokumentierte Verhalten
   zur Umsetzung passt.
6. Auslieferung und Integrität: Signaturprüfung und Manifest beim
   Start, was bei einer veränderten oder fehlenden Datei passiert,
   ob private Schlüssel oder Zugangsdaten irgendwo im Repository, im
   Paket oder in Protokollen landen, Rechte des Installers, Schreiben
   in den Programmordner, Updates über eine ältere Fassung, der
   Exe-Export von Schülerprogrammen.
7. Netz und Pakete: Paketinstallation (`pip`), Downloads, Adressen,
   die aus Eingaben entstehen, Verhalten ohne Netz, Zertifikatsprüfung.
8. Datenbankanbindung, in der IDE (Datenbank-Panel, CSV-Import,
   Tabellenansicht) wie in den Programmen der Schülerinnen (`pcl`:
   Verbindung, `SQLQuery`, `DataSource`, `DBGrid`, `DBEdit`,
   `DBComboBox`, `DBNavigator`, `to_dataframe`/`load_dataframe`):
   - SQL, das aus Eingaben, Tabellen- oder Spaltennamen
     zusammengesetzt wird, statt mit Platzhaltern; Namen mit
     Leerzeichen, Anführungszeichen, Umlauten oder Schlüsselwörtern.
   - Verbindungen und Dateisperren: SQLite-Dateien, die nach dem
     Schließen eines Fensters, einem Fehler oder dem Programmende
     gesperrt bleiben; zwei Verbindungen auf dieselbe Datei (IDE und
     laufendes Programm gleichzeitig); Datenbank auf einem
     Netzlaufwerk oder in einem schreibgeschützten Ordner.
   - Transaktionen: Änderungen, die ohne `commit` verloren gehen oder
     halb geschrieben bleiben; Abbruch mitten in einem Import;
     Rückgängig im Panel, das nicht zur Datenbank passt.
   - Datensatzzeiger und Datensteuerelemente: Einfügen, Löschen und
     Bearbeiten über `DBNavigator` und `DBGrid`, leere Tabellen,
     gelöschte Zeilen, gleichzeitige Änderung aus Code und Oberfläche,
     `NULL`-Werte, Typen (Zahlen mit Dezimalkomma, Datum, Text in
     Zahlspalten, sehr lange Texte, Binärdaten).
   - Umfang: sehr große Tabellen oder Abfragen, die die Oberfläche
     anhalten oder den Speicher füllen; Abfragen ohne Ende.
   - Dateien: beschädigte oder gar keine SQLite-Dateien, eine andere
     Datei mit Endung `.sqlite`, fremde Datenbanken mit Triggern oder
     Ansichten, `ATTACH` auf Dateien außerhalb des Projekts.
   - Zugangsdaten: dass nirgends Passwörter gespeichert werden (weder
     in `.pfm`, `.natter`, Einstellungen noch Protokollen) und dass
     keine Reste gestrichener Server-Anbindungen mehr erreichbar sind.
   - Meldungen: ob Datenbankfehler deutsch und verständlich ankommen
     oder als englische Rohmeldung oder Absturz.

## Wie gearbeitet wird

- Jeden Befund am Code belegen: Datei und Zeile, dazu ein Nachweis -
  ein kurzer Aufruf mit `uv run python -c …` in einem eigenen Ordner
  unter `%TEMP%`, ein Test mit `QT_QPA_PLATFORM=offscreen` oder ein
  `grep`. Was sich nicht belegen lässt, als „vermutet“ kennzeichnen
  oder weglassen.
- Proben ohne Schaden: keine echten Schadprogramme, keine Proben gegen
  fremde Rechner oder Dienste, nichts außerhalb von `%TEMP%` und einer
  Kopie des Projekts verändern. Für Proben mit dem Hauptfenster
  `uv run pytest -p tests.conftest <datei> --rootdir=.`, damit die
  echten Einstellungen unberührt bleiben.
- Nichts im Repository ändern außer `docs/offene_punkte.md`. Nichts
  bauen, nichts installieren, nichts an Windows ändern,
  `tools/signieren/` nicht öffnen.
- Lange Läufe mit Zeitgrenze und Ausgabe in eine Datei, keine volle
  Testsuite.
- Gewichtet wird nach der Lage an einer Schule: Was eine Schülerin mit
  Bordmitteln auslösen kann, wiegt schwerer als ein Angriff, der
  Verwaltungsrechte voraussetzt. Befunde, die nur mit Verwaltungsrechten
  oder physischem Zugriff auf den Rechner gehen, nur nennen, wenn sie
  über das hinausgehen, was diese Rechte ohnehin erlauben.

## Abgleich und Eintragen

Erst jetzt `docs/offene_punkte.md` und `docs/erledigte_punkte.md`
lesen. Befunde, die dort schon stehen, weglassen; steht dort ein Punkt
als erledigt, der Fehler ist aber noch da, als neuen Punkt eintragen und
auf den alten verweisen.

Jeden verbleibenden Befund als eigenen Punkt in `docs/offene_punkte.md`
unter „Offen“ eintragen, vor „Zurückgestellt“, mit der Nummer, die oben
in der Datei als nächste genannt ist, und diese Nummer danach
hochzählen. Aufbau wie die Vorlage oben in der Datei:

```markdown
## 123. Kurz, was nicht stimmt

**Gemeldet:** Datum, Sicherheitsprüfung, Entwicklungsstand (Commit).

**Beobachtet:** Was passiert und was stattdessen zu erwarten wäre.

**Ursache:** nachgewiesen, mit Datei und Zeile - oder vermutet.

**Zu tun:** Was geändert werden muss und woran das Erledigtsein zu
erkennen ist.
```

Reihenfolge nach Schwere: Ausführung fremden Codes und Umgehen des
Prüfungsmodus zuerst, dann Datenverlust und Abstürze, dann Hänger,
Speicher- und Prozesslecks, dann alles Übrige.

Für die Texte gelten die Regeln aus `AGENTS.md`: niemanden mit „du“
oder „Sie“ ansprechen, keine bildhaften Schlusswendungen, keine
Fettschrift und keine Zuschreibungs-Etiketten in Kommentaren, keine
Vergleiche mit anderen Entwicklungsumgebungen. Einen Weg, der sich
missbrauchen lässt, so beschreiben, dass er sich beheben lässt, aber
ohne Schritt-für-Schritt-Anleitung zum Ausnutzen. `uv run pytest -q
tests/test_textstil.py` muss danach grün sein.

## Abschluss

`docs/offene_punkte.md` committen (nur diese Datei, mit ausdrücklichem
Pfad) und pushen. Zum Schluss eine Tabelle ausgeben: Nummer, Titel,
Art (Codeausführung, Prüfungsmodus, Dateisystem, Datenverlust, Absturz,
Hänger, Leck, Integrität, Netz, Datenbank, Datensteuerelement), Schwere (hoch, mittel,
gering), belegt oder vermutet. Findet sich nichts, keinen Commit
anlegen und das ausdrücklich sagen.
