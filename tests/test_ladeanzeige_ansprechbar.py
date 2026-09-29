"""Die Ladeanzeige bleibt beim Laden der Module ansprechbar (Punkt 414).

Beim ersten Start nach einer Installation dauerte allein der Import
des Hauptfensters 7 s. In der Zeit holte der Faden der Oberfläche keine
Nachricht ab, Windows hielt die Ladeanzeige nach 5 s für hängend und
zeigte statt ihres Inhalts eine weiße Fläche.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer

from ide.ladeanzeige import ansprechbar_beim_laden

#: Fünf Module, die einander laden; jedes braucht 0,3 s.
_KETTE = 5


def _langsame_module(ordner: Path, praefix: str) -> str:
    for nummer in range(_KETTE):
        weiter = (
            f"import {praefix}{nummer + 1}\n" if nummer + 1 < _KETTE else ""
        )
        (ordner / f"{praefix}{nummer}.py").write_text(
            f"import time\ntime.sleep(0.3)\n{weiter}", encoding="utf-8",
        )
    return f"{praefix}0"


def test_beim_import_holt_die_anzeige_ihre_nachrichten_ab(
    qapp, tmp_path: Path, monkeypatch,  # noqa: ANN001
) -> None:
    monkeypatch.syspath_prepend(str(tmp_path))
    erstes = _langsame_module(tmp_path, "natter_probe_langsam_")
    schlaege = []
    uhr = QTimer()
    uhr.timeout.connect(lambda: schlaege.append(1))
    uhr.start(50)
    try:
        with ansprechbar_beim_laden():
            __import__(erstes)
        # Gezählt, bevor die Ereignisschleife wieder läuft: jeder
        # Schlag ist beim Import angekommen.
        waehrend = len(schlaege)
    finally:
        uhr.stop()
        for name in [n for n in sys.modules if n.startswith("natter_probe_")]:
            del sys.modules[name]
    assert waehrend >= 3, f"nur {waehrend} Schläge in 1,5 s Import"


def test_ausserhalb_des_ladens_bleibt_der_import_unberuehrt(
    qapp, tmp_path: Path, monkeypatch,  # noqa: ANN001
) -> None:
    """Der Prüfhaken bleibt nach dem ersten Laden eingehängt; danach
    darf er beim Import nichts mehr abholen."""
    with ansprechbar_beim_laden():
        pass
    monkeypatch.syspath_prepend(str(tmp_path))
    erstes = _langsame_module(tmp_path, "natter_probe_danach_")
    schlaege = []
    uhr = QTimer()
    uhr.timeout.connect(lambda: schlaege.append(1))
    uhr.start(50)
    try:
        __import__(erstes)
        waehrend = len(schlaege)
    finally:
        uhr.stop()
        for name in [n for n in sys.modules if n.startswith("natter_probe_")]:
            del sys.modules[name]
    assert waehrend == 0
