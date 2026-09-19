# Stufe 3 von 9 - das erste Programm mit einer Oberfläche.
#
# Neu gegenüber den Konsolenprogrammen:
#   Die Eingabe steht nicht mehr in input(), sondern in einem Feld auf
#   dem Formular. Statt von oben nach unten durchzulaufen, wartet das
#   Programm auf ein Ereignis - hier auf einen Klick.
#
# Wie du eine neue Schaltfläche anlegst:
#   1. Doppelklick auf u_main.pfm öffnet den Designer.
#   2. Button aus der Palette aufs Formular ziehen.
#   3. Doppelklick auf den Button - Natter legt die Methode hier an.

from u_main_design import Form1Design


class Form1(Form1Design):
    # Vier Knöpfe, vier Methoden - aber gerechnet wird nur an einer
    # Stelle. Doppelter Code wäre viermal derselbe Fehler.
    def b_plus_click(self, sender) -> None:
        self.rechnen("+")

    def b_minus_click(self, sender) -> None:
        self.rechnen("-")

    def b_mal_click(self, sender) -> None:
        self.rechnen("*")

    def b_geteilt_click(self, sender) -> None:
        self.rechnen("/")

    def rechnen(self, zeichen: str) -> None:
        """Liest beide Felder, rechnet und zeigt das Ergebnis an."""
        # Was im Feld steht, ist Text. float() macht eine Kommazahl
        # daraus - und wirft einen Fehler, wenn da "abc" steht.
        try:
            a = float(self.e_zahl1.text)
            b = float(self.e_zahl2.text)
        except ValueError:
            self.l_ergebnis.caption = "Bitte in beide Felder eine Zahl schreiben."
            return

        if zeichen == "+":
            ergebnis = a + b
        elif zeichen == "-":
            ergebnis = a - b
        elif zeichen == "*":
            ergebnis = a * b
        else:
            # Teilen durch null geht nicht - das muss das Programm
            # abfangen, sonst bricht es ab.
            if b == 0:
                self.l_ergebnis.caption = "Durch null kann man nicht teilen."
                return
            ergebnis = a / b

        self.l_ergebnis.caption = f"Ergebnis: {a:g} {zeichen} {b:g} = {ergebnis:g}"
