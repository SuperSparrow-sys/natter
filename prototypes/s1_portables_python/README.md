# S1 – Portables Python + PySide6/WebEngine

Prüft: Fenster mit WebEngine startet aus einer relokierbaren
Standalone-Python-Distribution; Ordner verschieben und erneut starten
funktioniert (Abschnitt 17.3, 23.3).

Dies ist bewusst **kein** `uv run`-Test aus dem normalen Entwicklungs-venv
(eine venv ist genau das, was hier vermieden werden soll, siehe 17.3),
sondern eine eigenständige, verschiebbare Python-Kopie.

## Schritte (auf dem Windows-Laptop)

1. Relokierbare Distribution besorgen, z. B. über `uv`:

   ```
   uv python install 3.13 --install-dir C:\temp\s1-test\python-standalone
   ```

   (Alternativ direkt eine `python-build-standalone`-Release von
   github.com/astral-sh/python-build-standalone verwenden – das ist die
   Grundlage, die auch `uv` selbst nutzt.)

2. Auf den **Desktop** kopieren, z. B. nach
   `C:\Users\<Name>\Desktop\s1-test\`.

3. PySide6 in genau diese Kopie installieren (keine venv, kein `uv run`):

   ```
   C:\Users\<Name>\Desktop\s1-test\python-standalone\python.exe -m pip install PySide6
   ```

4. Starten:

   ```
   C:\Users\<Name>\Desktop\s1-test\python-standalone\python.exe test_fenster.py
   ```

   (`test_fenster.py` aus diesem Ordner dorthin kopieren oder mit vollem
   Pfad aufrufen.)

5. **Ordner verschieben:** `s1-test` z. B. auf einen USB-Stick oder in
   `C:\Natter-Test\` verschieben, erneut mit Schritt 4 starten.

## Erfolgskriterium

- Fenster mit dem WebEngine-Inhalt öffnet sich in Schritt 4.
- Nach dem Verschieben in Schritt 5 startet es unverändert wieder – keine
  Fehlermeldung über absolute Pfade, keine Neuinstallation nötig.

Ergebnis (bitte eintragen): **offen**
