---
description: Unabhängige Prüfung von Installation, Aktualisierung, Administration und Übertragbarkeit von Natter an Schulen; Befunde in docs/offene_punkte.md eintragen
---

# Betrieb: Lässt sich Natter an einer Schule einrichten und pflegen?

Natter ist eine Python-Entwicklungsumgebung für den Informatikunterricht
(Installer in `tools/natter.iss`, Bau in `tools/auslieferung_bauen.py`
und `tools/ide_paketieren.py`, Starter `tools/launcher.py`, Paket für
Lehrkräfte unter `tools/paket/`). Aufgabe ist eine unabhängige Prüfung
des Betriebs: Installieren, Verteilen, Aktualisieren, Entfernen, und
wie sich Natter in einer typischen Schul-IT verhält. Nichts reparieren.

## Ohne Vorwissen anfangen

`docs/offene_punkte.md`, `docs/erledigte_punkte.md` und `docs/bericht.md`
erst am Ende lesen, beim Abgleich.

Maßstab sind zwei Personen:

- Eine Lehrkraft, die zugleich IT-Beauftragte der Schule ist, wenig
  Zeit hat und Natter auf 30 Rechnern eines Computerraums einrichten
  will, ohne jeden einzeln anzufassen.
- Ein Dienstleister des Schulträgers mit Softwareverteilung (Intune,
  baramundi, opsi, Gruppenrichtlinien), Schülerkonten ohne
  Verwaltungsrechte, auf den Server umgeleitetem Ordner „Dokumente“,
  Wächterkarte oder Zurücksetzen nach jeder Stunde.

## Wonach gesucht wird

1. Installation: für einen Benutzer und für alle Benutzer, still
   (`/VERYSILENT`, `/ALLUSERS`, `/DIR=`), aus einer Softwareverteilung,
   ohne Netz, mit langem oder Umlaut-Pfad, auf einem zweiten Laufwerk.
   Welche Rechte braucht was? Was steht nach der Installation wo?
2. Erster Start je Konto: Was passiert beim ersten Start eines neuen
   Schülerkontos (Profil frisch, Einstellungen fehlen, Ordner
   „Dokumente\Natter“ fehlt, Dokumente auf einem Netzlaufwerk)?
3. Aktualisierung: über jede ältere Fassung, bei laufender Natter, bei
   offenen Projekten, mit nachinstallierten Paketen; bleiben
   Einstellungen und Projekte erhalten?
4. Deinstallation: Was bleibt übrig (Programmordner, Profile,
   Registrierung, Dateizuordnung, Startmenü)? Werden Projekte der
   Schülerinnen verschont?
5. Eingeschränkte Konten: Natter und Schülerprogramme ohne
   Verwaltungsrechte, mit schreibgeschütztem Programmordner, mit
   AppLocker bzw. intelligenter App-Steuerung, mit Virenscanner, ohne
   Schreibrecht auf `%TEMP%` außerhalb des Profils.
6. Zurücksetzen und Wächterkarte: Was geht verloren, was hängt, wenn
   das Profil nach jeder Stunde zurückgesetzt wird? Ist der
   Prüfungsmodus damit vereinbar?
7. Verteilung von Aufgaben und Abgaben: Wie kommt ein Projekt von der
   Lehrkraft zu 30 Schülerinnen und zurück (ZIP, Netzlaufwerk,
   LernSax)? Wo bricht das (Pfade, Sperren, doppelte Namen)?
8. Übertragbarkeit: Windows 10 und 11, 64 Bit, verschiedene
   Bildschirme und Skalierungen, deutsche und englische
   Windows-Sprache, Benutzernamen mit Umlaut und Leerzeichen.
9. Dokumentation für den Betrieb: Steht in `tools/paket/ZUERST-LESEN.txt`,
   im Handbuch und im README, was eine IT-Beauftragte braucht (stille
   Installation, Pfade, Rechte, Zertifikat, Ausnahmen für den
   Virenscanner, Prüfungsmodus)?

## Wie gearbeitet wird

- Am Code und an der gebauten Fassung prüfen, soweit ohne Eingriff ins
  System möglich: `tools/natter.iss` lesen, `dist\Natter` und
  `dist\installer` nur lesen, Starter und Python aus einer Kopie in
  einem eigenen Ordner unter `%TEMP%` starten, Konten und Rechte über
  Umgebungsvariablen und Kopien nachstellen. Nichts installieren,
  deinstallieren oder an Windows ändern; was sich nur so prüfen ließe,
  als „nicht geprüft, Grund“ nennen.
- Jeden Befund belegen: Datei und Zeile, Befehl und Ausgabe oder
  Ablauf in Schritten.
- Gewichten nach Folgen im Schulalltag: was eine ganze Klasse
  aufhält, zuerst.
- Nichts im Repository ändern außer `docs/offene_punkte.md`. Nichts
  bauen. `tools/signieren/` weder öffnen noch durchsuchen. Jede
  Warteschleife und jeder Hintergrundlauf bekommt eine Zeitgrenze;
  Temp-Ordner am Ende löschen.

## Abgleich und Eintragen

Erst jetzt `docs/offene_punkte.md` und `docs/erledigte_punkte.md`
lesen, Bekanntes weglassen. Jeden Befund als eigenen Punkt unter
„Offen“ vor „Zurückgestellt“, mit der nächsten freien Nummer, Aufbau
wie die Vorlage oben in der Datei (Gemeldet: Datum, Betriebsprüfung,
Commit).

Reihenfolge: was die Einrichtung eines Raums verhindert, zuerst; dann
was bei jeder Stunde stört; dann Dokumentationslücken. Für die Texte
gelten die Regeln aus `AGENTS.md`; `uv run pytest -q
tests/test_textstil.py` muss danach grün sein.

## Abschluss

`docs/offene_punkte.md` committen (nur diese Datei, mit ausdrücklichem
Pfad) und pushen. Tabelle: Nummer, Titel, Art (Installation, erster
Start, Aktualisierung, Deinstallation, Rechte, Zurücksetzen, Verteilung,
Übertragbarkeit, Dokumentation), Schwere, belegt oder vermutet, dazu
die Liste dessen, was ohne Eingriff ins System nicht geprüft werden
konnte. Findet sich nichts, keinen Commit anlegen und das ausdrücklich
sagen.
