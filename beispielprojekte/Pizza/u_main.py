"""Eigener Formular-Code (Abschnitt 4.3). Das Formular selbst stammt aus
`referenz/lazarus/f_Pizza/unit1.lfm` und wurde über „Werkzeuge → Lazarus-
Formular importieren …“ übernommen; die Logik ist aus `unit1.pas`
nachgebildet (der Pascal-Rumpf wird nicht mitimportiert, siehe
docs/arbeitspakete/M8.md, Schritt 3).

Zwei bewusste Abweichungen vom Original, beide dort unfertig geblieben:
die Eingabefelder für eigene Sorte und eigenen Grundpreis wurden im
Pascal-Code nie ausgelesen, und `Font.size` wurde beim Hinzufügen jedes
Mal hart auf 12 zurückgesetzt, was die Schriftgrößen-Bildlaufleiste
wieder aufhob.
"""

from u_main_design import Form1Design

# Sortenliste wie im Original (dort zwei parallele Arrays kurzName /
# kurzPreis, die in FormCreate zeilenweise gefüllt werden).
KURZWAHL = (
    ("Hawaii", 8.50),
    ("Napoli", 8.50),
    ("Spinatta", 8.50),
    ("Quadro", 8.50),
    ("Fugi", 8.50),
    ("Stabilo", 8.50),
    ("L`Figgo", 8.50),
    ("Crinto Romana", 8.50),
    ("Quadro Fromaggi", 8.50),
    ("Spinno", 8.50),
)

GROESSEN = (
    ("rb_small", "Small", 0.8),
    ("rb_normal", "Normal", 1.0),
    ("rb_XL", "XL", 1.2),
    ("rb_XXL", "XXL", 1.4),
    ("rb_XXXL", "XXXL", 1.5),
)

AUFPREIS_KAESERAND = 1.99
AUFPREIS_KNOBLAUCH = 0.50
MEHRWERTSTEUER = (0.07, 0.19)


class Form1(Form1Design):
    def form_create(self, sender) -> None:
        self.lb_KurzWahl.items = [
            f"{name} ({preis:.2f} EUR)".replace(".", ",") for name, preis in KURZWAHL
        ]
        self.lb_KurzWahl.item_index = 0
        self.m_zettel.font.size = self.sb_behinderung.position

    def b_hinzufuegen_click(self, sender) -> None:
        sorte, preis = self._sorte_und_grundpreis()
        if sorte is None:
            self.m_zettel.lines.add("Bitte eine Pizza wählen oder eingeben.")
            return

        groesse, faktor = self._groesse()
        preis *= faktor
        if self.c_kaese.checked:
            preis += AUFPREIS_KAESERAND
        if self.c_knoblauch.checked:
            preis += AUFPREIS_KNOBLAUCH
        preis *= 1 + MEHRWERTSTEUER[self.cb_mws.item_index]

        betrag = f"{preis:.2f}".replace(".", ",")
        self.m_zettel.lines.add(f"Pizza {sorte} {groesse} - {betrag} EUR")

    def b_zettel_leer_click(self, sender) -> None:
        self.m_zettel.lines.clear()

    def sb_behinderung_change(self, sender) -> None:
        self.m_zettel.font.size = self.sb_behinderung.position

    def _sorte_und_grundpreis(self) -> tuple[str | None, float]:
        """Eigene Eingabe hat Vorrang vor der Kurzwahl-Liste."""
        eigene_sorte = self.e_eingabeSorte.text.strip()
        if eigene_sorte:
            return eigene_sorte, self._eigener_grundpreis()

        index = self.lb_KurzWahl.item_index
        if 0 <= index < len(KURZWAHL):
            return KURZWAHL[index]
        return None, 0.0

    def _eigener_grundpreis(self) -> float:
        eingabe = self.e_Grundpreis.text.strip().replace(",", ".")
        try:
            return float(eingabe)
        except ValueError:
            return KURZWAHL[0][1]

    def _groesse(self) -> tuple[str, float]:
        for name, beschriftung, faktor in GROESSEN:
            if getattr(self, name).checked:
                return beschriftung, faktor
        return "Normal", 1.0
