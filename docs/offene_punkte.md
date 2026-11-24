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

## 788. Ein Formular, das sich nicht schreiben ließ, geht beim Schließen von Natter ohne Nachfrage verloren

**Gemeldet:** 24. November 2026, Prüfung E (Schülersicht, Sicherung), Stand `42d5478`.

**Beobachtet:** GUI-Projekt, Designer offen, die `.pfm` lässt sich nicht schreiben (USB-Stick gezogen, Netzlaufwerk weg, Datei gesperrt). Nach dem Platzieren eines Knopfs kommt einmal die Meldung „„u_main.pfm“ konnte nicht gespeichert werden …“, der Reiter heißt „u_main (Designer) ●“. Wird danach das Fenster von Natter geschlossen, kommt keine Frage: Natter geht zu, die Änderung ist weg, die `.pfm` ist auf dem alten Stand. Beim Schließen des einzelnen Reiters wird dagegen gefragt (Punkt 235). Bei **Projekt → Projekt schließen** kommt nur die Frage des Reiters; „Abbrechen“ darin schließt das Projekt trotzdem, und der Designer-Reiter mit „●“ bleibt ohne Projekt stehen. In die Sicherung `<Projekt>.natter-sicherung` kommt die Formularänderung nie, auch nach einem Absturz ist sie verloren.

**Ursache:** nachgewiesen (`build/auswertung/pruefung_42d5478/E/788_formular_schliessen.py`). `_ungespeicherte_namen` in `ide/shell/hauptfenster.py:6729` zählt nur Editoren und Diagramme, nicht Designer mit `ungespeichert`; `closeEvent` (Zeile 6688) fragt nur danach. `_vorheriges_projekt_schliessen` fragt ebenso nicht nach Designern und überlässt sie `_reiter_schliessen_wenn` (Zeile 4774), das die Antwort „Abbrechen“ von `_tab_schliessen` nicht auswertet. `_sicherung_eintraege` (Zeile 6868) kennt nur Editoren und Diagramme.

**Zu tun:** Designer mit nicht geschriebener Änderung gehören in die gemeinsame Nachfrage beim Schließen des Fensters, beim Schließen und beim Wechsel des Projekts; „Abbrechen“ lässt das Projekt offen. Ihr Formular kommt als eigener Eintrag in die Sicherung. Erledigt, wenn der Nachweis die Frage beim Schließen findet, nach „Abbrechen“ Projekt und Reiter offen bleiben und die Sicherung die `.pfm` enthält.

---

## 789. „Speichern unter …“ an einen Ort außerhalb des Projekts lässt den Reiter still dort weiterarbeiten

**Gemeldet:** 24. November 2026, Prüfung E (Schülersicht, Datei wiederfinden), Stand `42d5478`.

**Beobachtet:** `u_main.py` geändert und mit **Datei → Speichern unter …** versehentlich auf den Desktop gelegt. Der Reiter heißt weiter „u_main.py“ und schreibt ab jetzt auf den Desktop. Die Unit im Projektordner bleibt auf dem alten Stand; das Programm startet diesen Stand, und die Abgabe-ZIP enthält ihn. Was danach getippt wird, kommt nicht mehr in die Sicherung des Projekts. Ein Doppelklick auf `u_main.py` im Projekt-Explorer öffnet einen zweiten Reiter mit demselben Namen und dem alten Text. Die Statusleiste nennt nur „Gespeichert als C:\…\Desktop\u_main.py.“; ein Hinweis, dass die Datei jetzt nicht mehr zum Projekt gehört, fehlt.

**Ursache:** nachgewiesen (`build/auswertung/pruefung_42d5478/E/789_speichern_unter_desktop.py`). `editor_speichern_unter` in `ide/shell/hauptfenster.py:5527` setzt den Pfad des Reiters ohne Prüfung auf das neue Ziel; `_sicherung_eintraege` (Zeile 6868) lässt Dateien außerhalb des Projektordners aus.

**Zu tun:** Liegt das Ziel außerhalb des offenen Projekts, vorher darauf hinweisen, dass das Programm weiter die Unit im Projekt benutzt, und den Reiter so beschriften, dass er sich von der Unit des Projekts unterscheidet (etwa mit dem Ordner). Erledigt, wenn der Nachweis die Nachfrage findet und zwei Reiter verschiedener Dateien nicht mehr gleich heißen.

---

## 790. Speichern auf einem abgezogenen USB-Stick oder vollen Datenträger meldet englischen Rohtext mit dem Namen der Zwischendatei

**Gemeldet:** 24. November 2026, Prüfung E (Schülersicht, Störungen beim Speichern), Stand `42d5478`.

**Beobachtet:** Projektordner während der Arbeit entfernt (USB-Stick gezogen), dann Strg+S: „„u_main.py“ konnte nicht gespeichert werden: [Errno 2] No such file or directory: 'C:\…\.u_main.py.25268.tmp'“. Bei vollem Datenträger: „[Errno 28] No space left on device“. Die Zwischendatei kennt niemand, der Text ist englisch, und unter „Häufige Gründe“ fehlt der volle Datenträger. Anders als bei verweigertem Schreibrecht wird kein „Speichern unter …“ angeboten, obwohl das hier der einzige Weg ist, den Text zu retten. Die alte Datei bleibt erhalten, der Text steht weiter im Editor, eine Zwischendatei bleibt nicht liegen. Dieselbe Rohmeldung zeigt der Designer, wenn er die `.pfm` nicht schreiben kann. Eine Datei, die ein anderes Programm offen hält, wird dagegen verständlich gemeldet und bietet „Speichern unter …“ an.

**Ursache:** nachgewiesen (`build/auswertung/pruefung_42d5478/E/790_speicherfehler_meldung.py`). `datei_schreiben_gemeldet` in `ide/shell/hauptfenster.py:5911` setzt im Zweig für `OSError` den Text des Fehlers unverändert ein und reicht `unter` nicht weiter; ebenso `DesignerCanvas.speichern` in `ide/designer/canvas.py:3176`. Punkt 321 hatte das nur für `PermissionError` geändert.

**Zu tun:** Für fehlenden Ordner, Laufwerk oder Netzpfad und für vollen Datenträger einen deutschen Satz ohne die Zwischendatei, dazu „Speichern unter …“ wie beim verweigerten Schreiben. Erledigt, wenn der Nachweis kein „Errno“ und kein „.tmp“ mehr findet und das Angebot erscheint.

---

## 791. Eine Änderung nur an einem Diagramm kommt erst nach bis zu zwei Minuten in die Sicherung

**Gemeldet:** 24. November 2026, Prüfung E (Schülersicht, Sicherung), Stand `42d5478`.

**Beobachtet:** Struktogramm oder Klassendiagramm geändert, keine Unit angefasst, Natter sieben Sekunden später hart beendet (`taskkill /F`, wie Task-Manager oder Stromausfall). Im Projektordner liegt keine Sicherung, beim nächsten Öffnen kommt keine Frage, die Änderung ist verloren. Mit einer gleichzeitig geänderten Unit kommt das Diagramm mit in die Sicherung und wird vollständig wiederhergestellt. Punkt 473 hat den Zwei-Minuten-Takt für Diagramme bewusst gelassen; wer eine Stunde lang nur ein Struktogramm zeichnet, verliert bei einem Absturz aber bis zu zwei Minuten Arbeit.

**Ursache:** nachgewiesen (`build/auswertung/pruefung_42d5478/E/791_diagramm_sicherung.py`, echter harter Abbruch in `probe_hart_beenden.py` im selben Ordner). Nur `contentsChanged` der Editoren startet `_sicherung_bald` (`ide/shell/hauptfenster.py:5447`); `DiagrammFenster._bei_aenderung` (`ide/diagramm/fenster.py:678`) meldet dem Hauptfenster nichts.

**Zu tun:** Jede Änderung in einem Diagrammfenster startet `_sicherung_bald` wie eine Änderung im Editor. Handbuch Abschnitt 6 entsprechend anpassen. Erledigt, wenn der Nachweis nach einer Diagrammänderung die laufende Uhr findet und der harte Abbruch das Diagramm anbietet.

---

## 792. „Projekt schließen“ beendet ein laufendes Programm ohne Nachfrage, ein Projektwechsel lässt es weiterlaufen

**Gemeldet:** 24. November 2026, Prüfung E (Schülersicht, Fehlgriffe), Stand `42d5478`.

**Beobachtet:** Programm läuft, dann **Projekt → Projekt schließen**: das Programm wird ohne Frage beendet, was darin eingegeben war, ist weg. Beim Schließen des Fensters fragt Natter seit Punkt 433 („Das Programm läuft noch. Beenden und Natter schließen?“). Beim Öffnen eines anderen Projekts wird weder gefragt noch beendet; das Programm des alten Projekts läuft neben dem neuen weiter.

**Ursache:** nachgewiesen (`build/auswertung/pruefung_42d5478/E/792_projekt_schliessen_programm.py`). `projekt_schliessen` in `ide/shell/hauptfenster.py:4334` ruft `kindprozesse_beenden` ohne `_laufendes_programm_fragen`; `projekt_oeffnen` (Zeile 4259) tut keins von beiden.

**Zu tun:** Schließen und Wechseln des Projekts fragen bei laufendem Programm wie das Schließen des Fensters; nach „Beenden“ endet das Programm in beiden Fällen, nach „Abbrechen“ bleibt alles, wie es war. Erledigt, wenn der Nachweis in beiden Fällen die Frage findet.

---

## 793. Beim Löschen einer Unit geht ihr ungespeicherter Text verloren, obwohl die Nachfrage den Papierkorb verspricht

**Gemeldet:** 24. November 2026, Prüfung E (Schülersicht, Fehlgriffe), Stand `42d5478`.

**Beobachtet:** Unit `u_rechnen.py` geöffnet, Zeilen getippt, nicht gespeichert, dann im Projekt-Explorer **⋮ → Löschen …**. Die Nachfrage lautet „„u_rechnen.py“ wirklich löschen? Die Dateien landen im Papierkorb und lassen sich von dort zurückholen.“ Im Papierkorb liegt der Stand der Platte; der getippte Text ist weder dort noch in der Sicherung. Wer die falsche Unit erwischt, bekommt aus dem Papierkorb nur einen älteren Stand zurück, und die Nachfrage sagt nichts davon.

**Ursache:** nachgewiesen (`build/auswertung/pruefung_42d5478/E/793_unit_loeschen_ungespeichert.py`). `_unit_loeschen` in `ide/shell/hauptfenster.py:3886` schließt den Reiter über `_reiter_schliessen_wenn`, das den Editor vorher als unverändert setzt; die Nachfrage (Zeile 3875) prüft nicht, ob die Unit ungespeichert offen ist.

**Zu tun:** Ist die Unit mit ungespeicherten Änderungen offen, steht das in der Nachfrage, und in den Papierkorb kommt der Text aus dem Editor. Erledigt, wenn der Nachweis den getippten Text im Papierkorb und den Hinweis in der Nachfrage findet.

# Zurückgestellt

Bewusst nicht jetzt, mit Begründung. Beim Abarbeiten der Liste werden diese Punkte übergangen, bis jemand sie wieder hervorholt.

Zurzeit keine.
