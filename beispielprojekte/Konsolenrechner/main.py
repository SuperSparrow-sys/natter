"""Konsolenrechner: Übungsprojekt für den Projekttyp "console"
(Abschnitt 7.8) - reine Ein-/Ausgabe über `input()`/`print()`, ganz
ohne GUI-Komponenten. Für Schüler, die von einfachen Lazarus-
Konsolenprogrammen (ReadLn/WriteLn) auf Python umsteigen. `pcl.crt`
(Farben, Cursorsteuerung) zeigt stattdessen beispielprojekte/CrtDemo.
"""


def berechnen(a: float, operator: str, b: float) -> float | None:
    """Liefert das Ergebnis oder `None` bei unbekanntem Operator/
    Division durch 0 (dann wird die Fehlermeldung schon hier
    ausgegeben, damit `main()` einfach bleibt)."""
    if operator == "+":
        return a + b
    if operator == "-":
        return a - b
    if operator == "*":
        return a * b
    if operator == "/":
        if b == 0:
            print("Division durch 0 ist nicht erlaubt.")
            return None
        return a / b
    print(f"Unbekannter Operator: {operator!r} (erlaubt: + - * /)")
    return None


def main() -> None:
    print("Konsolenrechner")
    print("Eingabe im Format 'Zahl Operator Zahl', z. B. '3 + 4'.")
    print("'ende' beendet das Programm.\n")

    while True:
        eingabe = input("Rechnung: ").strip()
        if eingabe.lower() == "ende":
            print("Bis bald!")
            break

        teile = eingabe.split()
        if len(teile) != 3:
            print("Bitte genau 'Zahl Operator Zahl' eingeben.")
            continue

        text_a, operator, text_b = teile
        try:
            a = float(text_a)
            b = float(text_b)
        except ValueError:
            print("Das sind keine gültigen Zahlen.")
            continue

        ergebnis = berechnen(a, operator, b)
        if ergebnis is not None:
            print(f"Ergebnis: {ergebnis}")


if __name__ == "__main__":
    main()
