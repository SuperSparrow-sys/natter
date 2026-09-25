"""Aktionsregister: eine Aktion = Menüeintrag + Werkzeugleisten-Button +
Tastenkürzel + Befehlspaletten-Eintrag, nur einmal implementiert.

Siehe README.md, Abschnitt 7.2, 7.3, 7.9, 18, `docs/bericht.md`, Abschnitt 2.3.
"""

from ide.actions.register import Aktion, AktionsKonfliktError, Aktionsregister

__all__ = ["Aktion", "Aktionsregister", "AktionsKonfliktError"]
