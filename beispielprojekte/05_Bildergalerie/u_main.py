# Stufe 5 von 9 - Dateien von der Festplatte holen.
#
# Neu gegenüber Stufe 4:
#   open_dialog()  öffnet den Windows-Dialog „Datei öffnen"
#   Liste          eine Python-Liste merkt sich, was dazugekommen ist
#   ListBox        zeigt diese Liste an; on_change meldet die Auswahl
#   Path           rechnet mit Dateinamen, statt Text zusammenzukleben
#
# Wichtig am Aufbau: die Liste der Bilder steht in `self.bilder` - also
# in Python. Die ListBox *zeigt* sie nur. Wer beides getrennt hält,
# muss nie raten, welche von beiden gerade recht hat.

from pathlib import Path

from pcl import open_dialog, show_message
from u_main_design import Form1Design

# Die Galerie startet nicht leer: die Kekse aus Stufe 4 liegen gleich
# nebenan und geben etwas zum Anschauen, bevor eigene Bilder da sind.
MITGELIEFERT = Path(__file__).parent.parent / "04_CookieKlicker" / "bilder"


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        # `self.bilder` sind vollständige Pfade, die ListBox zeigt nur
        # die Dateinamen - sonst stünde dort dreimal derselbe lange
        # Ordner.
        self.bilder: list[Path] = []
        if MITGELIEFERT.is_dir():
            self.bilder = sorted(MITGELIEFERT.glob("*.png"))
        self.liste_auffrischen()

    def liste_auffrischen(self) -> None:
        """Schreibt `self.bilder` in die ListBox."""
        self.lb_bilder.items = [pfad.name for pfad in self.bilder]
        if self.bilder:
            self.lb_bilder.item_index = 0
        else:
            self.i_vorschau.picture.clear()
            self.l_info.caption = "Die Galerie ist leer."

    # -- Hinzufügen und Entfernen ----------------------------------

    def b_hinzufuegen_click(self, sender) -> None:
        pfad_text = open_dialog("Bild auswählen")

        # Bei Abbruch kommt ein leerer Text zurück - dann ist nichts zu
        # tun. Diese Prüfung braucht jeder Dialog.
        if not pfad_text:
            return

        pfad = Path(pfad_text)
        if pfad in self.bilder:
            show_message("Dieses Bild ist schon in der Galerie.")
            return

        self.bilder.append(pfad)
        self.liste_auffrischen()
        self.lb_bilder.item_index = len(self.bilder) - 1

    def b_entfernen_click(self, sender) -> None:
        nummer = self.lb_bilder.item_index
        if nummer < 0:
            return

        # Aus der Liste nehmen, nicht von der Festplatte löschen - die
        # Galerie zeigt Bilder, sie verwaltet sie nicht.
        del self.bilder[nummer]
        self.liste_auffrischen()

    # -- Auswahl ---------------------------------------------------

    def lb_bilder_change(self, sender) -> None:
        """Läuft, sobald in der Liste ein anderer Eintrag angeklickt
        wird."""
        nummer = self.lb_bilder.item_index
        if nummer < 0 or nummer >= len(self.bilder):
            return

        pfad = self.bilder[nummer]
        self.i_vorschau.picture.load_from_file(str(pfad))

        # Dateigröße in Kilobyte, auf eine Stelle gerundet.
        groesse = pfad.stat().st_size / 1024
        self.l_info.caption = f"{pfad.name}  -  {groesse:.1f} kB\n{pfad.parent}"
