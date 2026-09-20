# Stufe 2 von 9 - das Programm trifft Entscheidungen und wiederholt sich.
#
# Neu gegenüber Stufe 1:
#   import         holt fertige Bausteine dazu (hier den Zufall)
#   while          wiederholt etwas, solange eine Bedingung stimmt
#   if / elif / else   entscheidet zwischen mehreren Fällen
#   +=             zählt eine Variable hoch
#
# Das ist schon ein richtiges Spiel: Das Programm zieht eine
# Zufallszahl, nimmt Rateversuche entgegen und antwortet darauf
# "zu klein" oder "zu groß".

import random

GRENZE = 100
MAX_VERSUCHE = 7

gesucht = random.randint(1, GRENZE)
versuche = 0

print("Ich denke an eine Zahl zwischen 1 und", GRENZE, end=".\n")
print(f"Du hast {MAX_VERSUCHE} Versuche.")
print()

# Die Schleife läuft, solange beides gilt: noch Versuche übrig
# und noch nicht getroffen.
getroffen = False
while versuche < MAX_VERSUCHE and not getroffen:
    eingabe = input("Deine Zahl: ")
    versuche += 1

    # isdigit() prüft, ob wirklich nur Ziffern getippt wurden.
    # Ohne diese Prüfung würde int("abc") das Programm abbrechen.
    if not eingabe.isdigit():
        print("Das war keine Zahl. Dieser Versuch zählt trotzdem.")
        continue

    tipp = int(eingabe)

    if tipp < gesucht:
        print("Zu klein.")
    elif tipp > gesucht:
        print("Zu groß.")
    else:
        getroffen = True

    print(f"  (Versuch {versuche} von {MAX_VERSUCHE})")
    print()

if getroffen:
    print(f"Getroffen! Die Zahl war {gesucht} - du hast {versuche} Versuche gebraucht.")
else:
    print(f"Aufgebraucht. Die Zahl war {gesucht}.")

print()
print("Aufgabe: Ändere GRENZE auf 1000. Wie viele Versuche brauchst du dann?")
