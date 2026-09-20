"""Die Beispielprojekte stehen unter „Datei → Beispielprojekte“.

Vorgabe des Nutzers: die Seite für die Beispielprojekte gehört „unter
Datei oben in der Kopfzeile mit allen aufgelisteten Projekten. nicht in
der normalen Oberfläche“.

Vorher waren sie ein Abschnitt auf dem Startbild. Dort nahmen die neun
Einträge den meisten Platz ein, und nach dem ersten geöffneten Projekt
kam niemand mehr an sie heran: das Startbild verschwand, sobald ein
Reiter offen war.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.shell.hauptfenster import HauptFenster
from ide.shell.startbild import beispielprojekte


def _beispiel_menue(fenster: HauptFenster):
    for aktion in fenster.menue("Datei").actions():
        if aktion.text() == "Beispielprojekte":
            return aktion.menu()
    return None


def test_das_untermenue_steht_im_menue_datei(qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    assert _beispiel_menue(fenster) is not None, "Kein Untermenü „Beispielprojekte“"


def test_alle_beispiele_stehen_darin(qtbot) -> None:
    """Alle, nicht eine Auswahl - der Lehrgang ist als Reihe gedacht."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    eintraege = [a.text() for a in _beispiel_menue(fenster).actions()]
    erwartet = [p.parent.name for p in beispielprojekte()]

    assert eintraege == erwartet
    assert len(eintraege) >= 9


def test_ein_eintrag_oeffnet_eine_arbeitskopie(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Geöffnet wird eine Kopie, nicht das Original im Programmordner:
    dort darf eine Schülerin nicht schreiben, und beim nächsten Mal
    soll das Beispiel wieder im Ursprungszustand dastehen."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))

    erster = _beispiel_menue(fenster).actions()[0]
    erster.trigger()

    assert fenster.projekt is not None
    kopie = fenster.projekt.ordner
    assert tmp_path in kopie.parents, f"{kopie} liegt nicht im Dokumente-Ordner"
    assert (kopie / "main.py").is_file()


def test_jeder_eintrag_erklaert_sich_in_der_statuszeile(qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    for aktion in _beispiel_menue(fenster).actions():
        assert "kopiert" in aktion.statusTip()
