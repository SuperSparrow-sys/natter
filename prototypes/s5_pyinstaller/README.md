# S5 – PyInstaller aus dem portablen Python

Prüft: die erzeugte Exe läuft auf einem Rechner ohne Python (Abschnitt
23.3). Baut auf S1 auf (portable Python-Kopie).

## Schritte (auf dem Windows-Laptop)

1. In der portablen Python-Kopie aus S1 (oder einer neuen Testkopie)
   installieren:

   ```
   <portables-python>\python.exe -m pip install PySide6 pandas pyinstaller
   ```

2. Bauen (Ordner-Variante, siehe Abschnitt 16 – Standard ist Ordner statt
   Einzeldatei):

   ```
   <portables-python>\python.exe -m PyInstaller --name S5Test --windowed schuelerprogramm.py
   ```

3. Den erzeugten Ordner `dist\S5Test\` auf einen **anderen Rechner ohne
   installiertes Python** kopieren (oder zumindest in eine komplett neue,
   leere Umgebung/VM) und `S5Test.exe` dort starten.

## Erfolgskriterium

- Fenster öffnet sich auf dem Zielrechner ohne Python-Installation, zeigt
  die pandas-Tabelle korrekt an.
- Kein Nachinstallieren von irgendetwas auf dem Zielrechner nötig.

Ergebnis (bitte eintragen): **offen**
