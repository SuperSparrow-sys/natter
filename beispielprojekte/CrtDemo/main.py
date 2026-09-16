"""CrtDemo: Konsolenprojekt, das jede `pcl.crt`-Funktion benutzt
(Abschnitt 9, M6 Schritt 2 - Abnahme). Reines Skript ohne Formular, wie
Konsolenprojekte im Konzept vorgesehen sind.
"""

from pcl.crt import (
    beep,
    clr_scr,
    delay,
    goto_xy,
    key_pressed,
    read_key,
    text_background,
    text_color,
)


def main() -> None:
    clr_scr()
    text_background("blue")
    text_color("yellow")
    goto_xy(5, 2)
    print("CRT-Demo")

    text_color("white")
    text_background("black")
    goto_xy(1, 4)
    print("Drücke eine beliebige Taste ...")

    beep()
    while not key_pressed():
        delay(50)
    taste = read_key()

    goto_xy(1, 6)
    print(f"Du hast {taste!r} gedrückt.")


if __name__ == "__main__":
    main()
