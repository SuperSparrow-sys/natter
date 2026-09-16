"""Simuliert den Start der IDE: nur pakete_ide im Suchpfad.

Ausführen mit: python -I -S starte_ide.py
Siehe prototypes/s4_getrennte_paketordner/README.md.
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER / "pakete_ide"))

import nur_ide  # noqa: E402

print(f"OK: nur_ide importiert ({nur_ide.markierung})")

for modul in ("nur_projekt", "nur_zusatz"):
    try:
        __import__(modul)
    except ModuleNotFoundError:
        print(f"OK: {modul} ist wie erwartet NICHT importierbar")
    else:
        print(f"FEHLER: {modul} war importierbar, sollte es aber nicht sein")
