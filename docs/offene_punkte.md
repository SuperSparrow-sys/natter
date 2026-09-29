# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **425**.

## Ein neuer Punkt

```markdown
## 425. Kurz, was nicht stimmt

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

## 416. Ein Knopf der Taskleiste zeigt noch das leere Fenstersymbol

**Gemeldet:** 29. September 2026, Prüfung der neu gebauten Fassung 0.4.2 (`build\auswertung\042b\`, Bilder `03_e_taskleiste_drittel2.png`, `03_i_taskleiste_aus_bildschirm_lupe.png`), nicht sicher belegt.

**Beobachtet:** Im ersten Programmlauf nach der Installation zeigte einer von zwei Knöpfen (vermutlich die IDE) das leere Fenstersymbol, der andere die Natter. In zwei Wiederholungen zeigten beide die Natter. Titelleiste und `WM_GETICON` liefern die Natter, das Symbol der Fensterklasse ist weiter leer. Beide Knöpfe heißen über UI Automation „Python – 1 aktives Fenster“.

**Ursache:** noch offen. Möglich: Die Taskleiste liest beim ersten Erscheinen das Symbol der Fensterklasse, bevor Qt das Fenstersymbol setzt; die Beschriftung kommt von `pythonw.exe`, weil weder IDE noch Programm eine eigene `AppUserModelID` setzen.

**Zu tun:** Am ersten Start nach einer Installation nachprüfen. Bestätigt es sich: ein eigenes `AppUserModelID` für IDE und Programme und das Symbol früh setzen. Erledigt, wenn ein Bildschirmfoto der Taskleiste beim ersten Programmlauf die Natter zeigt.

**Umgesetzt (29. September 2026), Nachweis steht aus.** IDE und Programme melden sich unter eigener Kennung bei Windows an, bevor ein Fenster entsteht: `anwendungs_kennung_setzen()` in `ide/main.py` setzt `Natter.IDE` als Erstes in `starten()`, `pcl.Application` setzt `Natter.Programm` (in einer exportierten Exe keine). Die Verknüpfungen im Startmenü und auf dem Schreibtisch tragen in `tools/natter.iss` dieselbe Kennung `Natter.IDE`. Darüber findet die Taskleiste Namen und Symbol der Verknüpfung, statt beides aus `pythonw.exe` zu nehmen. Außerdem setzt `anwendung_erzeugen()` das Symbol der Anwendung vor dem ersten Fenster; bis 0.4.2 setzte es nur das Hauptfenster für sich. Tests in `tests/test_taskleiste.py`. Im Entwicklungsbaum geprüft: `GetCurrentProcessExplicitAppUserModelID` liefert in beiden Prozessen die Kennung, der Knopf der IDE zeigt die Natter. Er heißt dort noch „Python“, weil es ohne Setup keine Verknüpfung mit der Kennung gibt. Offen ist nur das Bildschirmfoto am ersten Start nach einer Installation der nächsten Fassung.

## 423. Der Exe-Export signiert ohne Rückfrage mit jedem Codesignatur-Zertifikat, das im Konto liegt

**Gemeldet:** 29. September 2026, Sicherheitsprüfung, Entwicklungsstand `94200dc`.

**Beobachtet:** „Als Exe exportieren“ signiert die Exe mit dem ersten Zertifikat aus `Cert:\CurrentUser\My`, das zum Codesignieren taugt, einen privaten Schlüssel hat, noch gilt und dem das Konto vertraut. Das Natter-eigene Zertifikat „Natter Programme dieses Rechners“ wird nur vorgezogen; fehlt es, nimmt der Export jedes andere. Liegt im Konto einer Lehrkraft oder der Systembetreuung das Codesignatur-Zertifikat der Schule, etwa für Skripte oder für Regeln nach Herausgeber in AppLocker, bekommt ein exportiertes Schülerprogramm ohne Nachfrage diese Signatur und damit den Herausgeber der Schule. Die Rückmeldung lautet nur „Signiert - die Exe nennt jetzt einen Herausgeber.“ und nennt nicht, welcher. Das Handbuch (Abschnitt zum Exe-Export) beschreibt nur das eigene Zertifikat. Zu erwarten wäre, dass Natter ohne ausdrückliche Wahl nur mit dem eigenen Zertifikat signiert. Nachgestellt mit einem Ersatz für `_powershell`, der ein fremdes Zertifikat `SCHULE123` als vorhanden und vertraut meldet: `signieren_wenn_moeglich(..., anlegen=True)` signiert damit, `vor_dem_anlegen` wird nicht aufgerufen, Ergebnis `signiert=True`.

**Ursache:** nachgewiesen. `vorhandenes_zertifikat()` in `ide/export/signatur.py` (Zeile 191-220) sortiert mit `Sort-Object { $_.Subject -eq 'CN=Natter Programme dieses Rechners' }` nur um und gibt sonst das erste vertraute Zertifikat zurück. `signieren_wenn_moeglich()` (Zeile 535-553) signiert damit ohne Rückfrage; der Docstring von `ide/export/signatur.py` nennt „ein Zertifikat, das die Lehrkraft dort eingerichtet hat“ ausdrücklich als Quelle.

**Zu tun:** Ohne ausdrückliche Einstellung nur mit dem Zertifikat `CN=Natter Programme dieses Rechners` signieren. Soll ein anderes erlaubt sein, dann nur nach einer Wahl in den Einstellungen, und die Rückmeldung nach dem Export nennt den Herausgeber. Erledigt, wenn ein Test mit einem fremden, vertrauten Zertifikat im Konto keine Signatur mit diesem ergibt und das Handbuch das Verhalten beschreibt.

## 424. Ohne Netz meldet „Paket installieren …“ nach anderthalb Minuten auf Englisch, das Paket gebe es nicht

**Gemeldet:** 29. September 2026, Sicherheitsprüfung, Entwicklungsstand `94200dc`.

**Beobachtet:** Ist das Netz nicht erreichbar oder verwirft ein Proxy die Verbindung ohne Antwort, wiederholt `pip` den Abruf fünfmal mit je 15 Sekunden Wartezeit. Gemessen mit `pip install --dry-run` und einem Proxy auf der nicht erreichbaren Adresse `192.0.2.1`: 106 Sekunden. Danach steht in Statuszeile und Panel „Meldungen“ die Rohausgabe von `pip`, darunter „WARNING: Retrying (Retry(total=0 …)) after connection broken by 'ConnectTimeoutError …'“ und am Ende „ERROR: Could not find a version that satisfies the requirement … ERROR: No matching distribution found for …“. Die letzte Zeile liest sich so, als sei der Paketname falsch; dass keine Verbindung zustande kam, steht nur englisch in den Zeilen davor. Während der ganzen Zeit sind die anderen Vorgänge im Hintergrund gesperrt (`_hintergrund_frei`), also auch Testlauf, Exe-Export und „Als ZIP speichern“. Zu erwarten wäre eine deutsche Meldung, die fehlendes Netz von einem unbekannten Paketnamen unterscheidet, und eine kürzere Wartezeit.

**Ursache:** nachgewiesen. `paket_installieren()` in `ide/env/pakete.py` (Zeile 68-77) ruft `pip install` ohne `--timeout`, `--retries` oder eine eigene Zeitgrenze auf. `_mit_rechtehinweis()` (Zeile 80-91) ergänzt nur fehlende Schreibrechte; jede andere Ausgabe von `pip` geht unverändert über `_hintergrund_fehler()` in `ide/shell/hauptfenster.py` (Zeile 2860-2873) an die Oberfläche.

**Zu tun:** `pip` mit kürzerer Wartezeit und weniger Wiederholungen aufrufen und die Ausgabe auswerten: Verbindungsfehler als „Keine Verbindung zum Paketverzeichnis …“ melden, einen unbekannten Namen als solchen, jeweils auf Deutsch; die Rohausgabe höchstens im Panel „Meldungen“. Erledigt, wenn ein Test mit einem nicht erreichbaren Proxy die deutsche Meldung zur Verbindung ergibt und der Vorgang in weniger als 30 Sekunden endet.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
