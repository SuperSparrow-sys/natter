# Stufe 10 von 11 - ein Menü, eine Textdatei und ein zweites Fenster.
#
# Neu gegenüber den bisherigen Stufen:
#   MainMenu       eine Menüleiste mit „Datei“ und „Hilfe“. Die
#                  Einträge bearbeitet im Designer ein Doppelklick auf
#                  das Menü-Symbol.
#   Textdatei      lines.save_to_file() und lines.load_from_file()
#   Dialoge        save_dialog, open_dialog und ask_yes_no fragen nach
#                  Dateinamen und nach einer Entscheidung
#   zweites Fenster  u_info.py ist ein eigenes Formular. show_modal()
#                  zeigt es und wartet, bis es wieder zu ist.
#   anchors        das Textfeld wächst mit, wenn das Fenster größer
#                  gezogen wird (im Objektinspektor die Häkchen
#                  anchors_right und anchors_bottom)

from pathlib import Path

from pcl import ask_yes_no, open_dialog, save_dialog, show_message
from u_info import FormInfo
from u_main_design import Form1Design

TEXTDATEIEN = "Textdateien (*.txt);;Alle Dateien (*.*)"


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        # Wohin gespeichert wird. Leer, solange die Notiz noch keinen
        # Dateinamen hat - dann fragt „Speichern“ erst danach.
        self.dateiname = ""
        # Ob seit dem letzten Speichern etwas getippt wurde.
        self.geaendert = False

    def m_text_change(self, sender) -> None:
        self.geaendert = True
        self.status_zeigen()

    def status_zeigen(self) -> None:
        name = Path(self.dateiname).name if self.dateiname else "Neue Notiz"
        stern = " *" if self.geaendert else ""
        anzahl = len(self.m_text.lines)
        wort = "Zeile" if anzahl == 1 else "Zeilen"
        self.l_status.caption = f"{name}{stern} - {anzahl} {wort}"

    # -- Speichern und Laden ---------------------------------------

    def speichern_unter(self, pfad: str) -> bool:
        """Liefert False, wenn sich die Datei nicht schreiben ließ."""
        # Ein Ordner ohne Schreibrecht, ein voller USB-Stick, eine
        # Datei, die ein anderes Programm offen hält: ohne try brach
        # das Programm hier ab - und die Notiz war weg.
        try:
            self.m_text.lines.save_to_file(pfad)
        except OSError:
            show_message(
                f"{Path(pfad).name} lässt sich dort nicht speichern. "
                "Bitte einen anderen Ort wählen."
            )
            return False
        self.dateiname = pfad
        self.geaendert = False
        self.status_zeigen()
        return True

    def speichern(self) -> bool:
        """Speichert die Notiz; liefert False, wenn abgebrochen wurde."""
        if not self.dateiname:
            pfad = save_dialog("Notiz speichern", TEXTDATEIEN, "notiz.txt")
            if not pfad:
                return False
            return self.speichern_unter(pfad)
        return self.speichern_unter(self.dateiname)

    def vorher_sichern(self) -> bool:
        """Bietet an, ungespeicherte Änderungen zu sichern, bevor die
        Notiz verschwindet. Liefert False, wenn dabei abgebrochen
        wurde."""
        if not self.geaendert:
            return True
        if ask_yes_no("Die Notiz ist nicht gespeichert. Jetzt speichern?"):
            return self.speichern()
        return True

    # -- Menü ------------------------------------------------------

    def mi_neu_click(self, sender) -> None:
        if not self.vorher_sichern():
            return
        self.m_text.lines.clear()
        self.dateiname = ""
        self.geaendert = False
        self.status_zeigen()

    def mi_oeffnen_click(self, sender) -> None:
        if not self.vorher_sichern():
            return
        pfad = open_dialog("Notiz öffnen", TEXTDATEIEN)
        if not pfad:
            return
        try:
            self.m_text.lines.load_from_file(pfad)
        except OSError:
            show_message(f"{Path(pfad).name} lässt sich nicht öffnen.")
            return
        self.dateiname = pfad
        # Das Laden hat on_change ausgelöst; neu getippt ist aber noch
        # nichts.
        self.geaendert = False
        self.status_zeigen()

    def mi_speichern_click(self, sender) -> None:
        self.speichern()

    def mi_speichern_unter_click(self, sender) -> None:
        pfad = save_dialog("Notiz speichern unter", TEXTDATEIEN, self.dateiname)
        if pfad:
            self.speichern_unter(pfad)

    def mi_beenden_click(self, sender) -> None:
        # close() löst form_close aus - dort wird nach dem Speichern
        # gefragt, ganz gleich, ob über das Menü oder das Kreuz oben
        # rechts beendet wird. Liefert form_close False, bleibt das
        # Fenster offen: wer im Speicherdialog „Abbrechen“ wählt, hat
        # seine Notiz danach noch.
        self.close()

    def mi_info_click(self, sender) -> None:
        info = FormInfo()
        info.show_modal()

    def form_close(self, sender) -> bool:
        # False hält das Fenster offen.
        return self.vorher_sichern()
