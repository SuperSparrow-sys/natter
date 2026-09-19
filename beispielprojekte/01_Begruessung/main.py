# Stufe 1 von 9 - dein allererstes Programm.
#
# Ein Konsolenprogramm redet über das schwarze Fenster mit dir:
#   print(...)  schreibt eine Zeile hinein
#   input(...)  wartet, bis du etwas tippst und Enter drückst
#
# Drücke F9, um das Programm zu starten.

print("Hallo! Ich bin Natter.")
print()

# Was input() zurückgibt, merken wir uns unter einem Namen.
# So ein Name heißt Variable - hier heißt er "name".
name = input("Wie heißt du? ")

# Ein f davor macht aus dem Text eine Schablone: alles in geschweiften
# Klammern wird durch den Wert der Variablen ersetzt.
print(f"Freut mich, {name}!")
print()

# input() liefert immer Text. Damit wir rechnen können, macht int()
# eine ganze Zahl daraus.
alter_text = input("Wie alt bist du? ")
alter = int(alter_text)

print(f"In 10 Jahren bist du {alter + 10}.")
print(f"Dein Name hat {len(name)} Buchstaben.")
print()

print("Probiere es aus: ändere den Text oben und starte noch einmal.")
