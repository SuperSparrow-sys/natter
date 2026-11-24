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

## 728. Eine `.pfm` mit falschem Grundaufbau öffnet sich mit der Absturzmeldung statt mit „beschädigt“

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** Eine `.pfm`, die nur `[]` oder `7` enthält, deren `properties` eine Zahl ist oder deren `children` keine Liste ist, wirft beim Öffnen über den Projekt-Explorer `AttributeError` („'list' object has no attribute 'get'“) bzw. `TypeError` („'float' object is not iterable“). Erwartet ist die Statuszeile „… lässt sich nicht öffnen, die Datei ist beschädigt“; in der installierten Fassung kommt die allgemeine Meldung „In Natter ist etwas schiefgegangen“.

**Ursache:** nachgewiesen. `formular_fuer_designer_laden` ruft `_zahlen_pruefen` (`ide/designer/laden.py:192-206`, Aufruf in Zeile 212) vor der Schema-Prüfung auf; die Funktion setzt ein Objekt mit `properties` als Objekt und `children` als Liste voraus. Die `except`-Liste in `HauptFenster.oeffnen` (`ide/shell/hauptfenster.py:8641-8644`) kennt weder `AttributeError` noch `TypeError`. Nachweis: `build/auswertung/pruefung_42d5478/C/728_pfm_grundaufbau.py` (4 Fälle).

**Zu tun:** Die Grundform prüfen, bevor `_zahlen_pruefen` läuft, oder das Schema zuerst anwenden. Erledigt, wenn alle vier Fälle des Nachweises „beschädigt“ melden.

## 729. Werte in einer `.pfm`, die das Schema zulässt, ergeben ungültigen Formular-Code

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** Vier Fälle enden beim Öffnen im Designer in der Absturzmeldung statt in „beschädigt“: `NaN` oder `Infinity` als Wert (Python liest beides als JSON) ergibt im erzeugten Code `nan` und `NameError`; ein Menüeintrag, der nur `children` hat, ergibt `{, "children": [` und `SyntaxError`; `children` eines Menüeintrags als Zahl ergibt `TypeError`; ein Eigenschaftswert mit 500 ineinander liegenden Listen ergibt `RecursionError`. Der letzte Fall ist die Lücke in Punkt 548: dort ist nur die Tiefe der Komponenten begrenzt.

**Ursache:** nachgewiesen. `_python_literal` (`ide/codegen/design.py:150-184`) schreibt Kommazahlen mit `repr` und steigt ohne Grenze in Listen und Objekte ab; `_eintrag_zeilen` (Zeile 241-247) setzt den Kopf eines Eintrags auch ohne Felder vor `"children"` zusammen und geht in Zeile 263 ungeprüft über `children`. `_tiefe_pruefen` (Zeile 109-120) zählt nur `children` der Komponenten. Nachweis: `build/auswertung/pruefung_42d5478/C/729_pfm_codeerzeugung.py`.

**Zu tun:** Nicht endliche Zahlen, Menüeinträge ohne Beschriftung, `children` ohne Liste und zu tiefe Werte in `pfm_pruefen` ablehnen. Erledigt, wenn alle vier Fälle des Nachweises „beschädigt“ melden.

## 730. Ein Diagramm mit einer Lage oder Größe über 2.147.483.647 öffnet sich mit der Absturzmeldung

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** Ein `.pdiag`, in dem bei einer Form `h` = `1e308` oder `w` bzw. `x` = `2147483648` steht, lässt sich nicht öffnen: `OverflowError` beim Bau des Diagrammfensters, weitere aus der Ereignisschleife beim Zeichnen. Erwartet ist „beschädigt“ wie bei einer `.pfm` mit zu großer Zahl (Punkt 444). Der Export als Bild scheitert an einer Form mit `y` unter -2.147.483.648 ebenso.

**Ursache:** nachgewiesen. Das Schema begrenzt die Zahlen nicht; `setMinimumSize` in `ide/diagramm/zoom.py:84` und `QSize` in `ide/diagramm/export.py:211` nehmen nur 32-Bit-Werte. `HauptFenster.oeffnen` (`ide/shell/hauptfenster.py:8641-8644`) fängt `OverflowError` nicht. Nachweis: `build/auswertung/pruefung_42d5478/C/730_pdiag_grosse_zahl.py`.

**Zu tun:** Lage und Größe beim Laden auf einen Bereich begrenzen oder die Datei als beschädigt melden. Erledigt, wenn die drei Fälle des Nachweises „beschädigt“ melden.

## 731. Ein unpassender Wert in der Einstellungsdatei verhindert den Start

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** Steht in `Natter-IDE.ini` `thema=dunkel` (statt `dark`), `layout=abc` oder `fuer_konsole_verborgen=@Rect(0 0 1 1)`, entsteht das Hauptfenster nicht: `NatterPropertyError` „theme erwartet 'system', 'light' oder 'dark' …“ bzw. `TypeError` aus `restoreState` und `set()`. Natter startet dann gar nicht, bis jemand die Datei von Hand berichtigt oder löscht; an einem Schulrechner kann das eine Schülerin nicht.

**Ursache:** nachgewiesen. `HauptFenster.__init__` übernimmt `design/thema` ungeprüft (`ide/shell/hauptfenster.py:1067`, geprüft erst in `pcl/theme/__init__.py:79` über `_stil_anwenden`), gibt `fenster/layout` ohne Typprüfung an `restoreState` (Zeile 1493-1495) und macht aus `fenster/fuer_konsole_verborgen` ohne Prüfung eine Menge (Zeile 1498-1503). Für `fenster/geometrie` gibt es diese Prüfung schon (Zeile 6629-6633). Nachweis: `build/auswertung/pruefung_42d5478/C/731_einstellungen_start.py` (3 Fälle).

**Zu tun:** Jeden gelesenen Wert auf Typ und erlaubte Werte prüfen und sonst den Standard nehmen. Erledigt, wenn das Hauptfenster in allen drei Fällen entsteht.

## 732. CSV-Import: ein Feld mit mehr als 4300 Ziffern endet in der Absturzmeldung

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** „CSV importieren …“ im Datenbank-Panel mit einer Datei, in der ein Feld aus 5000 Ziffern besteht, wirft `ValueError: Exceeds the limit (4300 digits) for integer string conversion` statt „Die CSV-Datei ließ sich nicht importieren“. Die übrigen 123 Abwandlungen der Probe (leer, BOM, ANSI, UTF-16, Binärmüll, 3000 Spalten, Felder von 2 MB) melden sich richtig.

**Ursache:** nachgewiesen. `_zahlenart` (`ide/database/panel.py:110`) ruft `int(wert)` für jede Ziffernfolge; `_csv_importieren_dialog` (Zeile 1267-1268) fängt `ValueError` nicht. Nachweis: `build/auswertung/pruefung_42d5478/C/732_csv_lange_zahl.py`.

**Zu tun:** Ziffernfolgen über 19 Stellen ohne Umwandlung als Text werten. Erledigt, wenn der Nachweis besteht und die Spalte als TEXT angelegt wird.

## 733. StringGrid: `row_count` und `col_count` ohne Obergrenze belegen beliebig viel Speicher

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** `row_count = 10**7` belegt im Schülerprogramm 1,2 GB und braucht 4 Sekunden; `row_count = 2**31` wuchs über 3 GB, bis die Probe den Prozess beendete. Ein Tippfehler in einer Eingabe, aus der die Zeilenzahl kommt, legt so einen Schulrechner lahm. Punkt 356 hat den Speicher je Zeile verkleinert, Punkt 449 die Untergrenze eingeführt; eine Obergrenze fehlt.

**Ursache:** nachgewiesen. `row_count` und `col_count` (`pcl/components/additional.py:281-286`) haben nur `minimum=0`; `_bei_prop_aenderung` (Zeile 411-414) reicht jeden Wert an `setRowCount`/`setColumnCount` weiter. Nachweis: `build/auswertung/pruefung_42d5478/C/733_stringgrid_zeilenzahl.py`, Messreihe in `sg.log`.

**Zu tun:** Eine Höchstzahl festlegen und darüber mit `NatterPropertyError` und deutscher Meldung ablehnen, in `docs/komponenten.md` nennen. Erledigt, wenn der Nachweis besteht.

## 734. Zahlen außerhalb des Bereichs von Qt: rohes `OverflowError`, und der Wert bleibt in der Eigenschaft stehen

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** `self.lbl.left = 2**31` im Schülerprogramm endet in `OverflowError` ohne Text; danach liefert `lbl.left` den neuen Wert, das Widget steht am alten Platz. Dasselbe gilt für 470 Kombinationen aus Komponente und Eigenschaft (Lage und Größe aller Komponenten, `minimum`/`maximum`/`position`, `item_index`, `Timer.interval`, `Edit.max_length`, `FloatSpinEdit.decimals`). Andere unpassende Werte lehnt `Prop` mit deutscher Meldung ab, bevor etwas gespeichert ist. Zusätzlich: `FloatSpinEdit.minimum = float("nan")` löst `on_change` rund 250-mal aus und endet in `RecursionError`.

**Ursache:** nachgewiesen. `Prop.__set__` (`pcl/properties.py:216`) speichert den Wert, bevor `_bei_prop_aenderung` ihn an Qt gibt (etwa `pcl/control.py:651`, `setGeometry`). Bei `FloatSpinEdit` wechseln sich `_bei_wertaenderung` (`pcl/components/additional.py:763`) und das Zurücklesen ab Zeile 783 ab, weil `nan` nie gleich `nan` ist. Nachweis: `build/auswertung/pruefung_42d5478/C/734_zahl_ausserhalb_des_bereichs.py`, Gesamtliste in `rand.log` (`probe_randwerte.py`).

**Zu tun:** Ganze Zahlen über 2.147.483.647 und unter -2.147.483.648 sowie `nan` in `Prop` mit `NatterPropertyError` ablehnen, bevor gespeichert wird. Erledigt, wenn beide Fälle des Nachweises eine deutsche Meldung bekommen und der alte Wert stehen bleibt.

## 735. Designer: ein Menü, dessen Einträge Methoden aufrufen, lässt sich nicht kopieren oder duplizieren

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** In einer Kopie von `10_Notizbuch` endet Strg+C, Strg+V oder Strg+D auf dem Hauptmenü `mm_haupt` mit `NatterUnbekannteEigenschaftError` „Der Menüeintrag „Neu“ soll beim Anklicken die Methode 'mi_neu_click' aufrufen, aber _EinfuegenDesign hat keine Methode mit diesem Namen.“, in der installierten Fassung mit der allgemeinen Meldung. Aufgefallen in 15 von 50 Zufallsfolgen der Rückgängig-Probe; ohne diesen Handgriff ergaben alle 50 Folgen nach vollständigem Rückgängig und Wiederholen genau Anfang und Ende.

**Ursache:** nachgewiesen. `_ereignisse_entfernen` (`ide/designer/canvas.py:402-405`) nimmt nur `events` heraus, nicht das `on_click` in den Menüeinträgen; `_eintraege_bauen` (um Zeile 2061) baut die Kopie in einer Zwischenklasse ohne die Methoden des Formulars, und `MainMenu.entries` prüft die Methoden, weil die Zwischenklasse kein `_entwurfsansicht` trägt (`pcl/components/menus.py:577-589`). Nachweis: `build/auswertung/pruefung_42d5478/C/735_menue_kopieren.py`, Zufallsfolgen in `probe_undo_designer.py`.

**Zu tun:** Methodennamen in Menüeinträgen wie Ereignisse behandeln: vor dem Zwischenbau herausnehmen und danach verknüpfen, wenn es die Methode im Zielformular gibt. Erledigt, wenn beide Fälle des Nachweises ein Menü mit verknüpften Einträgen ergeben.

## 736. Formular-Import (.lfm): eine Fortsetzungszeile, die mit `+'…'` beginnt, wird weiter abgelehnt (Rückfall zu Punkt 549)

**Gemeldet:** 24. November 2026, Prüfung C, Entwicklungsstand `42d5478`.

**Beobachtet:** Punkt 549 nennt unter „Beobachtet“ eine Fortsetzungszeile mit `+'…'`. Eine Beschriftung, die über zwei Zeilen geht und deren zweite Zeile mit `+'weitergeht'` beginnt, ergibt weiter „Import fehlgeschlagen: Unerwartete Zeile in Objekt 'Label1' … Ist die gewählte Datei wirklich ein Formular im .lfm-Format?“. Lange Texte stehen im `.lfm`-Format in dieser Form; ein Formular mit einem solchen Text lässt sich nicht importieren.

**Ursache:** nachgewiesen. `_zeichenkette` (`ide/import_lfm/parser.py:85-127`) erkennt `+` nur am Ende einer Zeile (Zeile 122), `_zeichenkette_lesen` sieht danach nur in der nächsten Zeile nach. Der Test zu Punkt 549 (`test_zeichenketten_wie_lazarus_sie_schreibt` in `tests/test_lfm_parser.py`) prüft nur diese Form. Nachweis: `build/auswertung/pruefung_42d5478/C/736_lfm_plus_am_zeilenanfang.py`.

**Zu tun:** Auch eine Folgezeile annehmen, die mit `+` und einer Zeichenkette beginnt. Erledigt, wenn der Nachweis besteht und der vorhandene Test weiter grün ist.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
