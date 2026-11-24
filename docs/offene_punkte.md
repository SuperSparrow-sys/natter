# Offene Punkte

Fehler und Aufgaben, die noch zu erledigen sind. Was hier steht, wird
abgearbeitet; was erledigt ist, wandert mit Ursache und Änderung nach
[`erledigte_punkte.md`](erledigte_punkte.md). Dort bleibt auch die
ganze Vorgeschichte der früheren Punkte stehen, damit sich bei einem
ähnlichen Fehler nachlesen lässt, was schon geprüft wurde.

Die Nummern laufen durch und werden nicht neu vergeben. Der nächste
Punkt bekommt die **668**.

## Ein neuer Punkt

```markdown
## 668. Kurz, was nicht stimmt

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

## 668. Eine `.pfm` hebt mit `_projektordner` die Bildpfad-Sperre des Designers wieder auf

**Gemeldet:** 24. November 2026, Prüfung A, Entwicklungsstand `42d5478`.

**Beobachtet:** Seit Punkt 334 lädt der Designer Bilder nur aus dem
Projektordner, damit das Öffnen einer fremden `.pfm` keine Verbindung
zu einem anderen Rechner aufbaut. Den Projektordner entnimmt er dem
Attribut `_projektordner` am Formular. Eine `.pfm` kann dieses
Attribut unter `properties` des Formulars selbst setzen, auf `null`
oder auf einen beliebigen Ordner. Danach lädt der Designer ein Bild
von jedem Pfad, auch einem Netzpfad. Wer eine Abgabe oder ein Projekt
aus fremder Hand im Designer öffnet, verbindet sich damit wieder mit
einem Rechner, den der Absender bestimmt, samt Anmeldeversuch mit dem
Windows-Konto und der Wartezeit aus Punkt 334. Nachgestellt mit einem
Bild in einem Nachbarordner des Projekts: ohne die Angabe bleibt die
Vorschau leer, mit `"_projektordner": null` oder mit dem Nachbarordner
erscheint das Bild. Dieselbe Lücke erlaubt jedes andere interne
Attribut mit Unterstrich, am Formular wie an jeder Komponente
(`_entwurfsansicht`, `_qwidget`, `_eltern` …); die Werte bleiben
Literale, aber der Designer arbeitet danach mit verbogenen Interna.

**Ursache:** nachgewiesen. `ide/codegen/design.py`, Zeilen 95-96
(`_eintrag_pruefen`) verlangt für Eigenschaftsnamen nur einen
Bezeichner, auch einen mit `_` am Anfang. `pcl/properties.py`, Zeile
576, nimmt jeden Namen mit `_` ohne Prüfung an. `ide/designer/laden.py`,
Zeile 227, setzt `_projektordner` an der Klasse; die Zuweisung aus der
`.pfm` im erzeugten `create_components` überdeckt es am Objekt.
`pcl/components/additional.py`, Zeilen 457-461 (`_bilddatei_finden`),
gibt bei `None` einen absoluten Pfad unverändert zurück. Nachweis:
`build/auswertung/pruefung_42d5478/A/668_projektordner_aus_pfm.py`.

**Zu tun:** Eigenschaftsnamen in einer `.pfm` auf die Eigenschaften
beschränken, die die jeweilige Komponente öffentlich anbietet (kein
`_` am Anfang, deklariert in `pcl`), und eine andere Angabe als
beschädigt melden. Erledigt, wenn ein Test eine `.pfm` mit
`_projektordner` am Formular als beschädigt ablehnt und ein Bild
außerhalb des Projektordners im Designer weiterhin nicht geladen wird.

## 669. Prüfungsmodus: Test-Explorer und Fäden zeigen Pythons Namensvorschlag „Did you mean“

**Gemeldet:** 24. November 2026, Prüfung A, Entwicklungsstand `42d5478`.

**Beobachtet:** Laut Handbuch, Abschnitt 4, gibt es im Prüfungsmodus
keinen Lösungsvorschlag, und der Fehlerkatalog entfernt dafür Pythons
eigenes „Did you mean …?“. Zwei Wege zeigen es trotzdem:

1. Lässt sich eine Testdatei nicht laden, weil die geprüfte Unit beim
   Import scheitert, steht im Test-Explorer der rohe Traceback. Bei
   einem Tippfehler auf oberster Ebene der Unit endet er mit
   „NameError: name 'pirnt' is not defined. Did you mean: 'print'?“.
   Das trifft gerade die Lage, in der eine Lehrkraft zur Klausur eine
   Testdatei austeilt.
2. Eine Ausnahme in einem Faden des Schülerprogramms geht an
   `sys.excepthook` vorbei und landet mit demselben Vorschlag roh auf
   der Fehlerausgabe, bei einem Programm mit Fenster also im Panel
   „Ausgabe“.

**Ursache:** nachgewiesen. `ide/testrunner/harness.py`, Zeile 284
(`addError` für `_FailedTest`) und Zeilen 348-360
(`ladefehler_meldung` hängt den Traceback unverändert an, auch im
Modus). `pcl/fehleranzeige.py`, Zeilen 88-95, hängt nur
`sys.excepthook` ein, nicht `threading.excepthook`. Nachweis:
`build/auswertung/pruefung_42d5478/A/669_testlauf_vorschlag.py`.

**Zu tun:** Im Ladefehler des Testlaufs Pythons Vorschläge wie im
Fehlerkatalog entfernen (`_vorschlaege_entfernen`), mindestens im
Prüfungsmodus, und für Fäden `threading.excepthook` auf dieselbe
Meldung wie `sys.excepthook` lenken. Erledigt, wenn ein Test mit
vorgetäuschtem Prüfungsmodus für eine Unit mit `pirnt` auf oberster
Ebene und für einen Faden mit demselben Fehler keinen Text „Did you
mean“ mehr findet.

## 670. NaN und Infinity aus einer `.pfm` landen als Name statt als Literal im erzeugten Quelltext

**Gemeldet:** 24. November 2026, Prüfung A, Entwicklungsstand `42d5478`.

**Beobachtet:** `json.loads` nimmt `NaN`, `Infinity` und `-Infinity`
an. Steht so ein Wert in einer `.pfm`, schreibt die Codeerzeugung
`self.b_ok.left = nan` bzw. `= inf` in den Quelltext, also einen Namen
und kein Literal. Beim Öffnen im Designer endet das mit `NameError`;
den fangen weder das Laden noch `oeffnen` ab, und statt „die Datei ist
beschädigt“ erscheint die Meldung für einen internen Fehler. Eine so
gespeicherte `u_*_design.py` bricht beim Programmstart ebenso ab.
Ausführbarer Code entsteht dabei nicht, weil `nan` und `inf` nirgends
definiert sind; es ist aber die einzige Stelle, an der ein Wert aus
der `.pfm` nicht als Literal im Quelltext steht.

**Ursache:** nachgewiesen. `ide/codegen/design.py`, Zeile 183
(`return repr(wert)` für Zahlen), `ide/schema.py`, Zeile 104
(`json.loads` ohne `parse_constant`). Abgefangen wird in
`ide/designer/laden.py`, Zeilen 241-251, und
`ide/shell/hauptfenster.py`, Zeile 8643, kein `NameError`. Nachweis:
`build/auswertung/pruefung_42d5478/A/670_nan_als_name.py`.

**Zu tun:** Nicht endliche Zahlen beim Lesen einer `.pfm` ablehnen
(`parse_constant` oder Prüfung in `pfm_pruefen`) und als beschädigt
melden. Erledigt, wenn ein Test eine `.pfm` mit `NaN` und eine mit
`Infinity` im Designer als beschädigt meldet und
`design_code_erzeugen` für sie keinen Quelltext liefert.

## 671. Die Integritätsprüfung beim Start läuft erst, nachdem die IDE geladen und das Hauptfenster gebaut ist

**Gemeldet:** 24. November 2026, Prüfung A, Entwicklungsstand `42d5478`.

**Beobachtet:** `starten()` baut zuerst Anwendung und Hauptfenster und
prüft danach die Installation. Bis dahin sind 157 Module aus `ide` und
`pcl` geladen und ausgeführt, darunter `ide.shell.hauptfenster`,
`pcl.pruefungsmodus` und `pcl.fehlerkatalog`, also genau die Dateien,
die die schnelle Prüfung ansehen soll. Eine veränderte Datei unter
ihnen läuft damit, bevor die Meldung „Natter wurde verändert“
erscheinen kann, und kann die Prüfung selbst ausschalten. Bei einer
Installation für alle Benutzer braucht eine solche Änderung
Verwaltungsrechte. Bei der Installation nur für das angemeldete Konto
kann jedes Programm dieses Kontos in den Programmordner schreiben;
dort ist die Meldung die einzige Rückmeldung über eine Veränderung.

**Ursache:** nachgewiesen. `ide/main.py`, Zeile 199 (`erstellen`)
vor Zeile 208 (`integritaet_bestaetigen`); `erstellen` importiert in
Zeile 138 das Hauptfenster und baut es in Zeile 142. Nachweis:
`build/auswertung/pruefung_42d5478/A/671_integritaet_nach_import.py`.

**Zu tun:** Die Prüfung vor dem Import des Hauptfensters ausführen,
nur mit dem, was dafür nötig ist (`ide.integritaet`, `cryptography`,
Qt für die Meldung), und die schon geladenen Module dabei mit
aufnehmen. Erledigt, wenn ein Test zeigt, dass beim Aufruf von
`installation_pruefen` während des Starts `ide.shell.hauptfenster`
noch nicht in `sys.modules` steht.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
