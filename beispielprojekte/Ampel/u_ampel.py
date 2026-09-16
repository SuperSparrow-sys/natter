"""Eigene Klasse, reines Python (Abschnitt 4.0). Nachgebildet aus
referenz/lazarus/k_Ampel/u_tampel.pas.
"""


class Ampel:
    def __init__(self, eingeschaltet: bool, zustand: int) -> None:
        self.__eingeschaltet = eingeschaltet
        self.__zustand = zustand

    def einschalten(self) -> None:
        self.__eingeschaltet = True

    def ausschalten(self) -> None:
        self.__eingeschaltet = False

    def umschalten(self) -> None:
        self.__zustand = self.__zustand % 4 + 1

    def get_zustand(self) -> int:
        return self.__zustand

    def get_eingeschaltet(self) -> bool:
        return self.__eingeschaltet
