"""Simuliert den Start eines Schülerprogramms: nur pakete_projekt und
pakete_zusatz im Suchpfad.

Ausführen mit: python -I -S starte_schuelerprogramm.py
Siehe prototypes/s4_getrennte_paketordner/README.md.
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER / "pakete_projekt"))
sys.path.insert(0, str(HIER / "pakete_zusatz"))

import nur_projekt  # noqa: E402
import nur_zusatz  # noqa: E402

print(f"OK: nur_projekt importiert ({nur_projekt.markierung})")
print(f"OK: nur_zusatz importiert ({nur_zusatz.markierung})")

try:
    __import__("nur_ide")
except ModuleNotFoundError:
    print("OK: nur_ide ist wie erwartet NICHT importierbar")
else:
    print("FEHLER: nur_ide war importierbar, sollte es aber nicht sein")
