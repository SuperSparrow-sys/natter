# Stufe 4 von 9 - Bilder, ein Zeitgeber und ein Spielstand.
#
# Neu gegenüber Stufe 3:
#   Bilder         self.i_keks.picture.load_from_file(...)
#   anklickbar     auch ein Bild hat on_click, nicht nur ein Knopf
#   Zustand        Zahlen, die sich das Formular über die ganze
#                  Spielzeit merkt (self.kekse, self.pro_klick, ...)
#   Timer          macht etwas von allein, hier jede Sekunde. Er liegt
#                  im Designer als kleine Uhr auf dem Formular und ist
#                  im laufenden Programm unsichtbar.
#
# Die Idee stammt aus einem Lazarus-Projekt und ist hier ausgebaut:
# Ausbaustufen, Helfer, die von selbst backen, und ein Risikoknopf.

import random
from pathlib import Path

from u_main_design import Form1Design

# Der Ordner, in dem diese Datei liegt - so findet das Programm seine
# Bilder auch dann, wenn es aus einem anderen Ordner gestartet wird.
BILDER = Path(__file__).parent / "bilder"

# Preise und Wirkung der beiden Ausbaustufen.
TEIG_PREIS = 25
HELFER_PREIS = 50

# Ab wie vielen Keksen welcher Rang gilt. Von oben nach unten gelesen
# gewinnt der erste Eintrag, dessen Grenze erreicht ist.
RAENGE = [
    (500, "Großbäckerei"),
    (200, "Meisterbäcker"),
    (100, "Profi"),
    (50, "Geselle"),
    (10, "Lehrling"),
    (0, "Anfänger"),
]


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        """Läuft einmal beim Start - hier wird alles aufgeräumt."""
        self.i_stil_hell.picture.load_from_file(str(BILDER / "keks_hell.png"))
        self.i_stil_dunkel.picture.load_from_file(str(BILDER / "keks_dunkel.png"))
        self.i_stil_bunt.picture.load_from_file(str(BILDER / "keks_bunt.png"))
        self.neu_anfangen()

    # -- Spielstand ------------------------------------------------

    def neu_anfangen(self) -> None:
        self.kekse = 0
        self.pro_klick = 1
        self.helfer = 0
        self.stil = "keks_hell.png"
        self.t_helfer.enabled = False
        self.keks_zeigen(self.stil)
        self.anzeigen()

    def anzeigen(self) -> None:
        """Schreibt den Spielstand in die Beschriftungen."""
        self.l_punkte.caption = f"{self.kekse} Kekse"
        self.l_rang.caption = f"Rang: {self.rang()}"
        self.l_werte.caption = f"Pro Klick: {self.pro_klick}   Helfer: {self.helfer}"
        self.b_teig.caption = f"Besserer Teig ({TEIG_PREIS} Kekse)"
        self.b_helfer.caption = f"Helfer anstellen ({HELFER_PREIS} Kekse)"

    def rang(self) -> str:
        for grenze, name in RAENGE:
            if self.kekse >= grenze:
                return name
        return "Anfänger"

    def keks_zeigen(self, dateiname: str) -> None:
        self.i_keks.picture.load_from_file(str(BILDER / dateiname))

    # -- Klicken ---------------------------------------------------

    def i_keks_click(self, sender) -> None:
        self.kekse += self.pro_klick

        # Ab und zu erwischt man den bösen Keks - dann ist alles weg.
        # random.randint(1, 20) == 1 heißt: in einem von zwanzig Fällen.
        if random.randint(1, 20) == 1:
            self.kekse = 0
            self.pro_klick = 1
            self.helfer = 0
            self.t_helfer.enabled = False
            self.keks_zeigen("keks_boese.png")
            self.l_hinweis.caption = "Der böse Keks! Alles weg."
        else:
            self.keks_zeigen(self.stil)
            self.l_hinweis.caption = "Klicke auf den Keks."

        self.anzeigen()

    # -- Ausbauen --------------------------------------------------

    def b_teig_click(self, sender) -> None:
        if self.kekse < TEIG_PREIS:
            self.l_hinweis.caption = f"Dafür fehlen {TEIG_PREIS - self.kekse} Kekse."
            return
        self.kekse -= TEIG_PREIS
        self.pro_klick += 1
        self.l_hinweis.caption = f"Jetzt gibt es {self.pro_klick} Kekse pro Klick."
        self.anzeigen()

    def b_helfer_click(self, sender) -> None:
        if self.kekse < HELFER_PREIS:
            self.l_hinweis.caption = f"Dafür fehlen {HELFER_PREIS - self.kekse} Kekse."
            return
        self.kekse -= HELFER_PREIS
        self.helfer += 1
        # Sobald der erste Helfer da ist, darf der Zeitgeber laufen.
        self.t_helfer.enabled = True
        self.l_hinweis.caption = f"{self.helfer} Helfer backen jetzt mit."
        self.anzeigen()

    def t_helfer_timer(self, sender) -> None:
        """Der Zeitgeber ruft das jede Sekunde auf."""
        self.kekse += self.helfer
        self.anzeigen()

    # -- Risiko und Neustart ---------------------------------------

    def b_risiko_click(self, sender) -> None:
        if self.kekse == 0:
            self.l_hinweis.caption = "Erst einmal Kekse sammeln."
            return
        if random.randint(1, 2) == 1:
            self.kekse *= 2
            self.l_hinweis.caption = "Gewonnen - doppelt so viele Kekse!"
        else:
            self.kekse = 0
            self.l_hinweis.caption = "Verloren. Alles weg."
        self.anzeigen()

    def b_neu_click(self, sender) -> None:
        self.neu_anfangen()
        self.l_hinweis.caption = "Klicke auf den Keks."

    # -- Aussehen umstellen ----------------------------------------

    def i_stil_hell_click(self, sender) -> None:
        self.stil_waehlen("keks_hell.png")

    def i_stil_dunkel_click(self, sender) -> None:
        self.stil_waehlen("keks_dunkel.png")

    def i_stil_bunt_click(self, sender) -> None:
        self.stil_waehlen("keks_bunt.png")

    def stil_waehlen(self, dateiname: str) -> None:
        self.stil = dateiname
        self.keks_zeigen(dateiname)
