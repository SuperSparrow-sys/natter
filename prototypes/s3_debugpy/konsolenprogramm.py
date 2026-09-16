"""S3: Konsolenprogramm für den debugpy-Test.

Siehe prototypes/s3_debugpy/README.md.
"""

summe = 0
anzahl = 0

for i in range(3):
    text = input(f"Zahl {i + 1} von 3: ")
    zahl = int(text)
    summe += zahl
    anzahl += 1  # <- hier Breakpoint setzen

mittelwert = summe / anzahl
print(f"Summe: {summe}, Mittelwert: {mittelwert}")
input("Programm beendet. Taste drücken zum Schließen.")
