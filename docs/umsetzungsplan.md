# Umsetzungsplan zu den offenen Punkten

Zu jedem Punkt aus [`offene_punkte.md`](offene_punkte.md): was geändert
wird, womit es geprüft wird und woran erkennbar ist, dass es erledigt
ist. Die Reihenfolge ist nicht die der Nummern, sondern die der
Abhängigkeiten.

Zwei Punkte stehen nicht darin: **Punkt 5** ist geklärt, **Punkt 7** ist
entschieden.

Grundregel für jeden Schritt: `ruff check` sauber, alle Tests grün, und
der Schritt ist für sich abgeschlossen. Kein Schritt lässt einen
halbfertigen Zustand zurück.

---

## Stufe 1 — Fehler, die heute etwas kaputt machen

Vier kleine Eingriffe mit sichtbarer Wirkung. Sie hängen voneinander
nicht ab und lassen sich einzeln abschließen.

### 1.1 Punkt 13 — Der Ereignis-Filter rechnet mit der falschen Signatur

**Änderung.** `ide/inspector/ereignisse_tabelle.py`:
`passende_methoden()` bekommt das Ereignis übergeben und liest die
erwartete Parameterzahl aus `EREIGNIS_PARAMETER`:
`1 + len(EREIGNIS_PARAMETER.get(ereignis_name, ()))`. Damit ist die
Liste je Zeile eine andere, was richtig ist — eine Methode für
`on_click` passt nicht auf `on_mouse_down`.

**Tests** in `tests/test_ereignisse_tabelle.py`:

- `test_eine_maus_methode_wird_angeboten` — ein Formular mit
  `(self, sender, x, y)`; der Eintrag steht im Auswahlfeld von
  `on_mouse_down`.
- `test_eine_klick_methode_steht_nicht_bei_mouse_down` — dieselbe
  Tabelle, `(self, sender)` erscheint **nicht** bei `on_mouse_down`.
- `test_die_zellen_methoden_des_stringgrid_werden_angeboten` —
  `on_select_cell` mit `(self, sender, spalte, zeile)`, `on_edit_cell`
  mit drei Parametern.
- Der vorhandene Test für `on_click` bleibt unverändert und belegt,
  dass sich nichts verschlechtert hat.

**Abnahme.** Im Objektinspektor lässt sich eine von Hand geschriebene
Maus-Methode auswählen. Vorher war das Feld dort immer leer.

### 1.2 Punkt 13 — Der Reiter legt Methoden an

**Änderung.** Doppelklick auf eine Zeile im Reiter „Ereignisse" legt
die Methode an, wenn es sie noch nicht gibt, und springt sonst hin.
Die Tabelle kennt das Formular, aber nicht die Unit-Datei; sie meldet
deshalb ein Signal `methode_gewuenscht(ereignis_name, methodenname)`,
und das Hauptfenster schreibt über `handler_methode_einfuegen()` aus
`ide/codegen/ereignis.py` — dieselbe Funktion, die der Doppelklick im
Designer benutzt. Der Name folgt derselben Regel:
`<komponente>_<ereignis ohne on_>`.

**Tests** in `tests/test_ereignisse_tabelle.py` und
`tests/test_ereignis_verknuepfung.py`:

- `test_doppelklick_legt_die_methode_an` — Unit in `tmp_path`, danach
  steht `def i_bild_mouse_down(self, sender, x, y):` darin.
- `test_die_signatur_stimmt_zum_ereignis` — für jedes Ereignis aus
  `EREIGNIS_PARAMETER` die erwarteten Parameter, über `ast` geprüft
  statt über Textsuche.
- `test_eine_vorhandene_methode_wird_nicht_zweimal_angelegt` — zweiter
  Doppelklick ändert die Datei nicht.
- `test_ohne_offene_unit_kommt_eine_meldung` — kein stilles Nichts.

**Abnahme.** Ein Schüler kann `on_mouse_down` verknüpfen, ohne eine
Zeile Code von Hand zu schreiben.

### 1.3 Punkt 12 — Ein langer Text im Label verschwindet

**Änderung.** `pcl/components/standard.py`: `Label` bekommt eine
Eigenschaft `word_wrap` (Standard `True`) und setzt
`setWordWrap()`. Standard `True`, weil ein abgeschnittener Text immer
falsch ist; als `Prop` sichtbar, damit die Entscheidung im
Objektinspektor steht.

**Tests** in `tests/test_components.py` und `tests/test_schemas.py`:

- `test_ein_langer_text_wird_umgebrochen` — Label mit fester Breite,
  langer Text; `QLabel.wordWrap()` ist wahr und die gerenderte Höhe
  überschreitet eine Zeile.
- `test_word_wrap_laesst_sich_abschalten`.
- `test_word_wrap_steht_im_objektinspektor` — die Eigenschaft
  erscheint in `eigenschaften(Label)`.
- `docs/komponenten.md` und `schemas/pfm.schema.json` mitziehen; der
  vorhandene Test, der Doku gegen Code prüft, greift dann von selbst.

**Abnahme.** Der Text im Obst-Sortierer steht vollständig da.

### 1.4 Punkt 1 — Der Farbdialog erbt das Stylesheet des Farbknopfs

**Änderung.** `ide/diagramm/eigenschaften.py`: `self.window()` statt
`self` als Elternteil. Zusätzlich prüfen, ob der Rahmen am Farbknopf
über `setFrameShape` statt über ein Stylesheet gehen kann — dann
verschwindet die Ursache und nicht nur die Wirkung.

**Tests** in `tests/test_diagramm_eigenschaften.py`:

- `test_der_farbdialog_haengt_am_fenster` — der Elternteil des
  Dialogs ist ein Fenster, kein Farbknopf.
- `test_kein_stylesheet_ohne_selektor_auf_einem_dialogeltern` — eine
  allgemeine Prüfung über `ide/`: jedes `setStyleSheet` mit einer
  Anweisung ohne Selektor wird gegen eine Liste bekannter,
  unbedenklicher Stellen gehalten. Damit fällt die nächste
  Wiederholung beim Testlauf auf und nicht erst auf einem
  Bildschirmfoto.

**Abnahme.** Der Farbdialog sieht aus wie ein Dialog.

---

## Stufe 2 — Was fehlt

### 2.1 Punkt 14 — Das Formular kennt die Maus

**Änderung.** `pcl/form.py`: `on_click`, `on_double_click`,
`on_mouse_down`, `on_mouse_move`, `on_mouse_up`. Die Koordinaten zählen
ab der linken oberen Ecke des **Arbeitsbereichs**, wie `Top = 0` es
schon tut — sonst wird an der falschen Stelle gezeichnet, sobald eine
Menüleiste da ist. Ob `Form` dafür von `Control` erben kann, ist im
ersten Schritt zu entscheiden; der Maus-Filter aus `pcl/control.py`
lässt sich auch einzeln anhängen, und das ist der kleinere Eingriff.

**Tests** in `tests/test_control_form.py` und
`tests/test_maus_ereignisse.py`:

- `test_das_formular_hat_die_maus_ereignisse` — `ereignisse(Form)`
  enthält alle fünf.
- `test_die_koordinaten_zaehlen_ab_dem_arbeitsbereich` — Formular mit
  Menüleiste, ein Klick an bekannter Stelle, die gemeldeten Werte
  stimmen mit denen einer Komponente an derselben Stelle überein.
- `test_ohne_gedrueckte_taste_kommt_kein_mouse_move` — oder das
  Gegenteil, je nach Entscheidung; festgehalten wird, was gilt.
- `test_das_formular_erscheint_im_reiter_ereignisse` — zusammen mit
  1.1 und 1.2, sonst nützt es niemandem.

**Abnahme.** Ein Zeichenprogramm ohne `PaintBox` über der ganzen
Fläche.

### 2.2 Punkt 8 — Der Prüfungsmodus verbirgt fremden Code

**Änderung.** `ide/shell/startbild.py` lässt den Abschnitt „Zuletzt
geöffnet" weg, wenn `pruefungsmodus_laeuft()`.
`ide/shell/hauptfenster.py` sperrt das Untermenü
„Beispielprojekte" — gesperrt und nicht verschwunden, damit erkennbar
bleibt, dass es das gibt und dass es gerade nicht geht. Dazu ein
Aufbau des Startbilds beim Einschalten des Modus, sonst bleibt die
Liste stehen.

**Tests** in `tests/test_pruefungsmodus.py`:

- `test_im_pruefungsmodus_fehlt_zuletzt_geoeffnet`
- `test_im_pruefungsmodus_ist_das_beispielmenue_gesperrt`
- `test_nach_dem_einschalten_baut_sich_das_startbild_neu_auf`
- `test_danach_ist_beides_wieder_da` — mit abgelaufenem Modus, damit
  nicht eine Sperre zurückbleibt.
- Die vorhandenen Tests zum Überleben eines Neustarts bleiben; sie
  belegen die Bedingung, die schon gilt.

**Abnahme.** Auf dem Startbild steht in einer Klausur nichts, was zu
fremdem Code führt.

### 2.3 Punkt 10 — Der erzeugte Quelltext landet im Editor

**Änderung.** `ide/diagramm/codefenster.py`: der Dialog hinter
„Speichern unter …" beginnt im Projektordner, den
`_vorschlag_fuer_unit()` schon ausrechnet, und geht über
`in_datei_schreiben()` — das fragt nach, statt eine vorhandene Datei
stillschweigend zu überschreiben. `ide/diagramm/fenster.py` meldet
`datei_geschrieben(Path)`. `ide/shell/hauptfenster.py` verbindet das
beim Öffnen des Diagrammfensters und ruft
`explorer.projekt_anzeigen()` und `datei_oeffnen()`.

**Tests** in `tests/test_diagramm_codefenster.py` und
`tests/test_hauptfenster_diagramme.py`:

- `test_der_dialog_beginnt_im_projektordner`
- `test_das_fenster_meldet_die_geschriebene_datei`
- `test_die_datei_steht_danach_im_explorer`
- `test_die_datei_ist_danach_als_reiter_offen`
- `test_eine_vorhandene_datei_wird_nicht_still_ueberschrieben`
- `test_eine_datei_ausserhalb_des_projekts_kommt_nur_in_den_reiter`

**Abnahme.** Wer eine Klasse aus dem Diagramm erzeugt, findet sie
danach links im Explorer und offen im Editor.

### 2.4 Punkt 16 — Der Quelltext als PDF

**Änderung.** Neues Modul `ide/export/quelltext_pdf.py`: baut aus
`Projekt.units()` ein `QTextDocument` — Überschrift je Datei,
Seitenumbruch dazwischen, Zeilennummern, Hervorhebung über
`PythonHervorhebung`, immer mit den Farben des hellen Themas — und
schreibt es über `QPdfWriter`. Menüeintrag „Projekt → Quelltext als
PDF exportieren …". Der Lauf gehört in den Hintergrund
(`Hintergrundarbeit`), wie der Exe-Export.

**Tests** in `tests/test_quelltext_pdf.py`:

- `test_nur_die_u_dateien_kommen_hinein` — `main.py` und
  `u_main_design.py` fehlen; geprüft über die Textstellen im
  erzeugten Dokument, nicht über die Dateigröße.
- `test_jede_datei_bekommt_eine_ueberschrift`
- `test_zeilennummern_stehen_dabei`
- `test_die_farben_sind_die_des_hellen_themas` — auch dann, wenn das
  dunkle eingestellt ist.
- `test_eine_lange_zeile_wird_umgebrochen_und_nicht_abgeschnitten` —
  die Lehre aus Punkt 12.
- `test_das_pdf_ist_lesbar` — mit einem PDF-Leser gegenprüfen, dass
  der Text tatsächlich darin steht. Eine Datei, die nur groß genug
  ist, beweist nichts.

**Abnahme.** Ein PDF, das sich ausdrucken und anstreichen lässt.

---

## Stufe 3 — Darstellung

### 3.1 Punkt 17 — Hilfeseiten und Markdown

**Änderung.** `ide/viewers/hilfe_ansicht.py` geht über den
Zwischenschritt HTML (`QTextDocument.setMarkdown` → `toHtml()` →
`setDefaultStyleSheet` → `setHtml`) und bekommt eine Vorlage:
Zeilenabstand 160 %, Höchstbreite 70–90 Zeichen, Abstände zwischen
Absätzen und über Überschriften, `border-collapse` und Innenabstand in
Tabellenzellen, abgesetzte Codeblöcke (`pre` mit Hintergrund und
Innenabstand), festgelegte Fließtextschrift. Die Schriftstärke wird am
Bildschirm entschieden, nicht hier.

**Tests** in `tests/test_hilfe_ansicht.py` und
`tests/test_markdown_ansicht.py`:

- `test_der_umweg_ueber_html_verliert_nichts` — Tabellen, Listen,
  Verweise, Codeblöcke und Überschriften sind nach dem Umweg noch da.
  Das ist der Test, der vor dem Umbau geschrieben gehört: geht dabei
  etwas verloren, ist der Weg falsch.
- `test_die_vorlage_greift` — der Zeilenabstand eines Absatzes ist
  größer als die Schrifthöhe.
- `test_tabellenzellen_haben_innenabstand`
- `test_ein_codeblock_ist_abgesetzt`
- `test_code_stellen_haben_eine_schrift_die_es_gibt` — der vorhandene
  Test bleibt und belegt, dass der Umbau die alte Reparatur nicht
  zunichtemacht.

**Abnahme.** Eine Hilfeseite, die man am Stück liest, ohne die Zeile
zu verlieren.

### 3.2 Punkt 3 — Die Druckvorschau

**Änderung.** `ide/diagramm/fenster.py`, `_auf_drucker_zeichnen()`:
das Koordinatensystem vor dem Zeichnen auf 96 dpi bringen
(`maler.scale(96 / drucker.resolution(), …)`) und erst darauf den
Anpassungsfaktor rechnen. Die `1.0`-Grenze in
`ide/diagramm/export.py` fällt für den Druckweg weg. Damit skalieren
Geometrie und Schrift gemeinsam — denselben Weg geht `als_pdf` seit
jeher.

**Tests** in `tests/test_diagramm_export.py`:

- `test_das_diagramm_fuellt_die_seite` — auf eine Seite gezeichnet
  belegt der Inhalt mindestens die halbe Breite. Mit dem heutigen
  Stand schlägt der Test fehl (18 %), das ist der Beleg.
- `test_die_schrift_bleibt_in_ihrem_kasten` — die Textbreite aus
  `QFontMetrics` passt in die gezeichnete Form.
- `test_querformat_rechnet_ueber_die_andere_kante`
- `test_struktogramm_und_entscheidungstabelle_gehen_denselben_weg`
- `test_das_pdf_bleibt_unveraendert` — es war nie kaputt und soll es
  nicht werden.

**Abnahme.** Ein gedrucktes Klassendiagramm füllt das Blatt und ist
lesbar.

### 3.3 Punkt 9 — Die Bereiche im Diagramm-Editor ~~(erledigt)~~

**Änderung.** Zuerst messen, dann ändern: welche Bereiche es gibt, ob
die Übersichtskarte ein eigener Dock ist, und ob das Fenster sein
Layout merken soll. Falls ja, brauchen die Bereiche einen
`objectName`, sonst speichert Qt nichts. Erst danach die Größen.

**Tests** in `tests/test_diagramm_fenster.py`:

- `test_kein_bereich_ueberdeckt_einen_anderen` — die Rechtecke der
  sichtbaren Bereiche überschneiden sich nicht.
- `test_jede_beschriftung_passt_in_ihren_bereich` — über
  `QFontMetrics`, bei kleiner und bei großer Fenstergröße.
- `test_das_layout_ueberlebt_ein_schliessen_und_oeffnen`
- `test_beim_allerersten_oeffnen_stimmt_es_auch` — ohne gespeicherten
  Zustand.

**Abnahme.** Nichts überdeckt sich, und jede Beschriftung ist ganz zu
lesen.

---

## Stufe 4 — Durchgänge, die nur von Hand gehen

Diese vier lassen sich nicht in einen Test gießen; sie brauchen einen
Menschen, der hinsieht. Jeder endet mit einem Eintrag in
`offene_punkte.md` — gefunden oder nichts gefunden.

### 4.1 Punkt 15 — Die Panels zeigen wirklich etwas

Ein Programm mit Haltepunkt starten und nachsehen: stehen im Reiter
„Variablen" die Werte, im „Aufrufstapel" die Kette? Ein GUI-Programm
mit `print()` starten: kommen die Zeilen in „Ausgabe" an? Eines mit
einem Fehler: landet die Meldung ebenfalls dort? Führt ein Klick auf
eine Zeile an die richtige Stelle?

Zwei Dinge lassen sich dabei doch prüfen, und die gehören in
`tests/test_ausgabe_panel.py`:

- `test_die_programmausgabe_kommt_im_panel_an` — mit einem echten
  Unterprozess, nicht mit einer Attrappe.
- `test_die_spalte_heisst_variable` — die Überschrift
  „Eigenschaft | Wert" stammt aus dem Objektinspektor.

### 4.2 Punkt 2 — Die acht Dialoge ansehen

Jeden einmal öffnen und ansehen. Der Fehler aus Punkt 1 ist nur am
Bild zu erkennen. Was dabei auffällt, wird sofort behoben; die Prüfung
aus 1.4 fängt künftige Wiederholungen ab.

### 4.3 Punkt 11 — Alle sichtbaren Texte lesen

Die neun Beispielprojekte, die Meldungen der IDE, die Hilfeseiten, die
Vorlagen und die Texte des Installers. Gesucht wird, was schon zweimal
aufgefallen ist: bildhafte Wendungen, die nichts erklären, und Sätze,
die einem Programm Absichten andichten. Der Obst-Sortierer ist der
erste Fall — „der Wald antwortet", „die Bäume haben abgestimmt", „das
im Blick zu behalten ist der wichtigste Teil".

`tests/test_textstil.py` wächst dabei nur, wo sich etwas wirklich
maschinell fassen lässt. Eine Prüfung, die Bilder erkennen soll, wäre
eine Prüfung, die falsche Treffer meldet.

### 4.4 Punkt 4 — Die Lizenzseite des Installers

Den Installer einmal von Hand durchklicken. Braucht eine angemeldete
Sitzung und geht deshalb nicht nebenbei.

---

## Was offen bleibt

**Punkt 6** — die Prozesszeiten. Keine Aufgabe, sondern eine
Einschränkung der Umgebung. Festgehalten ist, was stattdessen trägt:
ob das Protokoll fortschreitet, und der Vergleich mit der bekannten
Normaldauer.

---

## Reihenfolge

Stufe 1 zuerst: vier kleine Eingriffe, jeder für sich abzuschließen,
jeder mit sichtbarer Wirkung. Danach Stufe 2, weil 2.1 auf 1.1 und 1.2
aufbaut — Maus-Ereignisse am Formular nützen wenig, solange sie sich
im Objektinspektor nicht verknüpfen lassen. Stufe 3 danach, weil 3.1
vor dem Umbau einen Test braucht, der belegt, dass der Umweg über HTML
nichts verliert. Stufe 4 zum Schluss, denn ein Durchgang lohnt sich
erst, wenn das Bekannte behoben ist.
