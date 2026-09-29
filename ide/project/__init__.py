"""Projektmodell: `.natter`-Projektdateien laden/speichern, Units und
Formulare aus dem Projektordner ermitteln (Abschnitt 4.1, 23.2)."""

from ide.project.neu import projekt_erzeugen
from ide.project.projekt import Projekt

__all__ = ["Projekt", "projekt_erzeugen"]
