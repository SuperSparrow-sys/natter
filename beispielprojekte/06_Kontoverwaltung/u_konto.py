# Eine eigene Klasse - das erste Mal in diesem Lehrgang.
#
# Bisher lagen alle Daten als einzelne Variablen im Formular herum
# (self.kekse, self.pro_klick, ...). Ein Konto besteht aber aus
# mehreren Angaben, die zusammengehören: Nummer, Inhaber, Stand. Eine
# Klasse fasst sie zu einem Ding zusammen - und legt gleich fest, was
# man mit diesem Ding tun darf.
#
# Das ist der Kern der Objektorientierung: nicht "Daten und Funktionen",
# sondern "Daten und die Regeln, die für sie gelten".


class NichtGenugGeld(Exception):
    """Wird ausgelöst, wenn mehr abgehoben werden soll als da ist.

    Eine eigene Fehlerart statt `return False`: so kann der Aufrufer
    nicht vergessen, das Ergebnis zu prüfen.
    """


class Konto:
    def __init__(self, nummer: int, inhaber: str, stand: float = 0.0) -> None:
        self.nummer = nummer
        self.inhaber = inhaber
        self.stand = stand

    def einzahlen(self, betrag: float) -> None:
        if betrag <= 0:
            raise ValueError("Einzahlen geht nur mit einem Betrag über null.")
        self.stand += betrag

    def abheben(self, betrag: float) -> None:
        if betrag <= 0:
            raise ValueError("Abheben geht nur mit einem Betrag über null.")
        if betrag > self.stand:
            raise NichtGenugGeld(
                f"Auf Konto {self.nummer} liegen nur {self.stand:.2f} Euro."
            )
        self.stand -= betrag

    def __repr__(self) -> str:
        return f"Konto({self.nummer}, {self.inhaber!r}, {self.stand:.2f})"
