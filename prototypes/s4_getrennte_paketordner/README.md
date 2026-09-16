# S4 – Getrennte Paketordner statt venv

Prüft: Der Starter setzt beim Start der IDE nur `pakete-ide` in den
Suchpfad, beim Start eines Schülerprogramms nur `pakete-projekt` (und
`pakete-zusatz`) – isolierter Modus, keine Benutzer-Site-Packages, keine
Umgebungsvariablen von außen (Abschnitt 17.3).

Dieser Prototyp bildet das mit zwei winzigen Test-Paketen nach, ganz ohne
echtes PySide6, damit er überall ohne Zusatzinstallation läuft.

## Aufbau

```
pakete_ide/nur_ide.py          # "gehört" nur zur IDE
pakete_projekt/nur_projekt.py  # "gehört" nur zu Schülerprogrammen
starte_ide.py                  # simuliert Start der IDE
starte_schuelerprogramm.py     # simuliert Start eines Schülerprogramms
```

## Ausführen

Aus dem Ordner `prototypes/s4_getrennte_paketordner/`:

```
python -I -S starte_ide.py
python -I -S starte_schuelerprogramm.py
```

`-I` (isolierter Modus) ignoriert `PYTHONPATH` und Benutzer-Site-Packages,
`-S` unterdrückt zusätzlich den automatischen `site`-Import; beide Skripte
setzen ihren jeweiligen Paketordner selbst über `sys.path`, genau wie es der
echte Natter-Starter tun soll.

## Erfolgskriterium

- `starte_ide.py`: `nur_ide` lässt sich importieren, `nur_projekt` **nicht**
  (`ModuleNotFoundError`).
- `starte_schuelerprogramm.py`: `nur_projekt` lässt sich importieren,
  `nur_ide` **nicht**.
- Ein zusätzlich in `pakete_zusatz/` installiertes Paket ist nur für
  Schülerprogramme sichtbar (hier durch ein drittes Beispielpaket
  nachgestellt).

Ergebnis (bitte eintragen): **offen**
