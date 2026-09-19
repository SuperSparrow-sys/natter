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

    # Zwei kleine Helfer, die zusammengehören: Python rechnet mit dem
    # Punkt, wir schreiben das Komma. Beim Lesen wird getauscht, beim
    # Schreiben zurückgetauscht.

    def zahl(self, text: str) -> float:
        """Macht aus dem Text im Feld eine Zahl: "2,5" -> 2.5.

        `float()` versteht nur den Punkt. Wir schreiben Zahlen aber mit
        Komma, und genau das tippt man auch ein.
        """
        return float(text.replace(",", "."))

    def text(self, wert: float) -> str:
        """Macht aus einer Zahl deutschen Text: 3.5 -> "3,5".

        Ohne diesen Schritt stünde im Ergebnis ein Punkt, obwohl man
        eben ein Komma eingetippt hat - das sieht aus wie ein Fehler.
        """
        return f"{wert:g}".replace(".", ",")

    def rechnen(self, zeichen: str) -> None:
        """Liest beide Felder, rechnet und zeigt das Ergebnis an."""
        # Was im Feld steht, ist Text - auch dann, wenn eine Zahl
        # darin steht. `self.zahl(...)` macht eine Zahl daraus und
        # wirft einen Fehler, wenn da "abc" steht.
        try:
            a = self.zahl(self.e_zahl1.text)
            b = self.zahl(self.e_zahl2.text)
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

        self.l_ergebnis.caption = (
            f"Ergebnis: {self.text(a)} {zeichen} {self.text(b)} = {self.text(ergebnis)}"
        )
