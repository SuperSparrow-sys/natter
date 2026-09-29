"""Einrückung und Zeilenhervorhebung in den Baumansichten.

Nutzer-Hinweis (M11): Die Dateien im Projekt-Explorer sollen unter
ihrer Gruppenüberschrift eingerückt stehen – aber beim Überfahren mit
der Maus darf links kein Kästchen mit blauem Rand auftauchen.

Beides hängt zusammen: Qt malt die Hover- und die Auswahlfläche einer
Baumzeile zweimal, einmal für den Eintrag (`::item`) und einmal für den
Einrückungsbereich davor (`::branch`). Solange beide Flächen
halbdurchsichtig waren, lagen im überlappenden Teil zwei Schichten
übereinander – das ergab genau dieses dunklere Kästchen. Deshalb war
die Einrückung früher ganz abgeschaltet.
"""

from __future__ import annotations

import re

import pytest

from ide.inspector.komponentenbaum import Komponentenbaum
from ide.shell.explorer import ProjektExplorer
from ide.shell.theme import _ueber_grund, ide_qss_erzeugen

DESIGNS = ("light", "dark")


def _regel(qss: str, auswahl: str) -> str:
    """Der Rumpf des Regelblocks zu `auswahl`."""
    treffer = re.search(
        re.escape(auswahl) + r"[^{}]*\{([^}]*)\}",
        qss,
    )
    assert treffer is not None, f"Regel {auswahl} fehlt im Stylesheet"
    return treffer.group(1)


@pytest.mark.parametrize("design", DESIGNS)
def test_einrueckungsbereich_und_eintrag_sind_gleich_hell(design: str) -> None:
    """Dieselbe Farbe für beide Flächen – dann ist es gleichgültig, wie
    oft Qt dieselbe Stelle malt."""
    qss = ide_qss_erzeugen(design)

    for zustand in ("hover", "selected"):
        eintrag = _regel(qss, f"QTreeView::item:{zustand}")
        zweig = _regel(qss, f"QTreeView::branch:{zustand}")
        farbe = re.search(r"background-color:\s*([^;]+);", eintrag).group(1)
        assert f"background-color: {farbe};" in zweig


@pytest.mark.parametrize("design", DESIGNS)
def test_die_hervorhebung_ist_deckend(design: str) -> None:
    """Eine halbdurchsichtige Farbe würde sich beim zweiten Malen mit
    sich selbst mischen und dort dunkler wirken."""
    qss = ide_qss_erzeugen(design)

    for auswahl in (
        "QTreeView::item:hover",
        "QTreeView::item:selected",
        "QTreeView::branch:hover",
        "QTreeView::branch:selected",
    ):
        rumpf = _regel(qss, auswahl)
        assert "rgba(" not in rumpf, f"{auswahl} ist halbdurchsichtig"


def test_ueber_grund_mischt_zu_einer_deckenden_farbe() -> None:
    assert _ueber_grund("#ffffff", 0.0, "#000000") == "#000000"
    assert _ueber_grund("#ffffff", 1.0, "#000000") == "#ffffff"
    assert _ueber_grund("#ffffff", 0.5, "#000000") == "#808080"


def test_die_dateien_stehen_eingerueckt(qtbot) -> None:
    baum = ProjektExplorer()
    qtbot.addWidget(baum)

    assert baum.indentation() > 0


def test_der_objektinspektor_rueckt_ebenfalls_ein(qtbot) -> None:
    """Dort war die Einrückung nie abgeschaltet – der Test hält nur
    fest, dass sie es auch nicht wird."""
    baum = Komponentenbaum()
    qtbot.addWidget(baum)

    assert baum.indentation() > 0
