"""Diagramm-Editor (Abschnitt 13, Arbeitspaket M9)."""

from ide.diagramm.datei import FORMEN_TYPEN, Diagramm
from ide.diagramm.fenster import DiagrammFenster
from ide.diagramm.neu import MVP_TYPEN, TYP_BESCHRIFTUNGEN, diagramm_erzeugen, leeres_diagramm

__all__ = [
    "FORMEN_TYPEN",
    "MVP_TYPEN",
    "TYP_BESCHRIFTUNGEN",
    "Diagramm",
    "DiagrammFenster",
    "diagramm_erzeugen",
    "leeres_diagramm",
]
