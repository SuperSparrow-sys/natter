"""Konto: reine Kontoverwaltungslogik, originalgetreu aus
`referenz/lazarus/n_konto/u_tkonto.pas` übernommen (Ein-/Auszahlen,
Überweisen). Die Datenbankanbindung (M5, Abschnitt 10) kommt separat in
`u_main.py` dazu - `Konto` selbst bleibt reines Python ohne
Datenbankzugriff, wie im Original.
"""

from __future__ import annotations


class Konto:
    def __init__(self, kontonr: str, besitzer: str, kontostand: float) -> None:
        self.kontonr = kontonr
        self.besitzer = besitzer
        self.kontostand = kontostand

    def get_besitzer(self) -> str:
        return self.besitzer

    def get_kontonr(self) -> str:
        return self.kontonr

    def get_kontostand(self) -> float:
        return self.kontostand

    def set_besitzer(self, besitzer: str) -> None:
        self.besitzer = besitzer

    def einzahlen(self, betrag: float) -> None:
        self.kontostand += betrag

    def abheben(self, betrag: float) -> None:
        # Original (u_tkonto.pas) ruft bei zu wenig Geld showMessage()
        # direkt aus dem Modell auf - hier sauberer getrennt: die Logik
        # meldet den Fehler, die Oberfläche (u_main.py) entscheidet, wie
        # sie ihn anzeigt.
        if betrag > self.kontostand:
            raise ValueError("Nicht genügend Geld vorhanden!")
        self.kontostand -= betrag

    def ueberweisen(self, betrag: float, zielkonto: Konto) -> None:
        self.abheben(betrag)
        zielkonto.einzahlen(betrag)
