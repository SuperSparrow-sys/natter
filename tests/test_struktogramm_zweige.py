"""Beschriftung der Zweige einer Verzweigung (Punkt 62 der offenen
Punkte).

Das Format kannte eigene Beschriftungen unter `labels`, gezeichnet
wurden sie auch - ändern ließen sie sich nur in der Datei. Jetzt über
Doppelklick auf die Beschriftung, das Kontextmenü und das Menü
„Block“, jeweils rückgängig machbar.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QInputDialog

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.bloecke import Einfuegestelle
from ide.diagramm.datei import Diagramm
from ide.diagramm.struktogramm_canvas import VERSATZ, StruktogrammCanvas


@pytest.fixture
def flaeche(qtbot, tmp_path: Path) -> StruktogrammCanvas:  # noqa: ANN001
    diagramm = diagramm_erzeugen("struktogramm", tmp_path / "s.pdiag", "pruefen")
    return StruktogrammCanvas(diagramm)


def _verzweigung(flaeche: StruktogrammCanvas) -> dict:
    return flaeche.block_einfuegen(
        "branch", Einfuegestelle(flaeche.wurzel, "children", 0)
    )


def _beschriftungen(flaeche: StruktogrammCanvas, block: dict) -> list[str]:
    kasten = next(k for k in flaeche._layout_erneuern().alle() if k.block is block)
    return [text for text, _ in kasten.zweige]


def _ecke(flaeche: StruktogrammCanvas, block: dict, links: bool) -> QPointF:
    """Mitte der Stelle, an der die Beschriftung eines Zweigs steht."""
    kasten = next(k for k in flaeche._layout_erneuern().alle() if k.block is block)
    kopf = kasten.kopf
    x = kopf.left() + 10 if links else kopf.right() - 10
    return QPointF(x + VERSATZ, kopf.bottom() - 6 + VERSATZ)


def _antwort(monkeypatch: pytest.MonkeyPatch, text: str) -> list[str]:
    """Legt die Antwort des Eingabedialogs fest und merkt sich, was er
    vorgeschlagen hat."""
    vorschlaege: list[str] = []

    def eingabe(*_a, text: str = "", **_k):  # noqa: ANN202
        vorschlaege.append(text)
        return antwort, True

    antwort = text
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(eingabe))
    return vorschlaege


def test_ohne_eigene_beschriftung_ja_und_nein(flaeche: StruktogrammCanvas) -> None:
    block = _verzweigung(flaeche)

    assert _beschriftungen(flaeche, block) == ["ja", "nein"]


def test_beide_zweige_lassen_sich_beschriften(flaeche: StruktogrammCanvas) -> None:
    block = _verzweigung(flaeche)

    flaeche.zweig_beschriften(block, "then", "wahr")
    flaeche.zweig_beschriften(block, "else", "falsch")

    assert block["labels"] == {"then": "wahr", "else": "falsch"}
    assert _beschriftungen(flaeche, block) == ["wahr", "falsch"]


def test_rueckgaengig_nimmt_die_beschriftung_zurueck(
    flaeche: StruktogrammCanvas, tmp_path: Path
) -> None:
    """Vorher gab es kein `labels`. Danach darf dort auch nicht `None`
    stehen - die Schema-Prüfung beim Speichern lehnte das ab."""
    block = _verzweigung(flaeche)
    flaeche.zweig_beschriften(block, "then", "wahr")

    flaeche.rueckgaengig()

    assert "labels" not in block
    flaeche.diagramm.speichern()
    assert Diagramm.laden(flaeche.diagramm.pfad).daten["root"]["children"][0].get(
        "labels"
    ) is None

    flaeche.wiederholen()
    assert block["labels"] == {"then": "wahr"}


def test_leer_oder_vorgabe_entfernt_den_eintrag(flaeche: StruktogrammCanvas) -> None:
    block = _verzweigung(flaeche)
    flaeche.zweig_beschriften(block, "then", "wahr")
    flaeche.zweig_beschriften(block, "else", "falsch")

    flaeche.zweig_beschriften(block, "then", "")
    flaeche.zweig_beschriften(block, "else", "nein")

    assert "labels" not in block
    assert _beschriftungen(flaeche, block) == ["ja", "nein"]


def test_doppelklick_auf_die_beschriftung_fragt_nach_dem_zweig(
    flaeche: StruktogrammCanvas, monkeypatch: pytest.MonkeyPatch
) -> None:
    block = _verzweigung(flaeche)
    vorschlaege = _antwort(monkeypatch, "sonst")

    punkt = _ecke(flaeche, block, links=False)
    flaeche.mouseDoubleClickEvent(
        QMouseEvent(
            QEvent.Type.MouseButtonDblClick,
            punkt,
            punkt,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )

    assert vorschlaege == ["nein"]
    assert block["labels"] == {"else": "sonst"}
    # Der Text der Bedingung bleibt dabei unberührt
    assert block["text"] == "Bedingung?"


def test_kontextmenue_beschriftet_den_zweig_unter_der_maus(
    flaeche: StruktogrammCanvas, monkeypatch: pytest.MonkeyPatch
) -> None:
    block = _verzweigung(flaeche)
    _antwort(monkeypatch, "gerade")

    punkt = _ecke(flaeche, block, links=True)
    menue = flaeche.kontextmenue_fuer(punkt.x(), punkt.y())
    eintrag = next(a for a in menue.actions() if "Zweig" in a.text())

    assert eintrag.text() == "Zweig „ja“ beschriften …"
    eintrag.trigger()
    assert block["labels"] == {"then": "gerade"}


def test_kontextmenue_in_einem_zweig_nimmt_dessen_seite(
    flaeche: StruktogrammCanvas, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Auch mit der rechten Maustaste auf eine Anweisung im rechten
    Zweig gibt es den Eintrag - für diesen Zweig."""
    block = _verzweigung(flaeche)
    innen = flaeche.block_einfuegen(
        "statement", Einfuegestelle(block, "else", 0)
    )
    kasten = next(k for k in flaeche._layout_erneuern().alle() if k.block is innen)
    _antwort(monkeypatch, "ungerade")

    mitte = kasten.rechteck.center()
    menue = flaeche.kontextmenue_fuer(mitte.x() + VERSATZ, mitte.y() + VERSATZ)
    next(a for a in menue.actions() if "Zweig" in a.text()).trigger()

    assert block["labels"] == {"else": "ungerade"}


def test_menue_block_beschriftet_beide_zweige(
    qtbot, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    fenster = DiagrammFenster(
        diagramm_erzeugen("struktogramm", tmp_path / "m.pdiag", "pruefen")
    )
    flaeche = fenster.zeichenflaeche
    block = _verzweigung(flaeche)
    flaeche.auswaehlen(None)
    fenster._blockmenue_aktualisieren()
    assert not fenster.aktionen["Block/Linken Zweig beschriften …"].isEnabled()

    flaeche.auswaehlen(block)
    fenster._blockmenue_aktualisieren()
    _antwort(monkeypatch, "wahr")
    fenster.aktionen["Block/Linken Zweig beschriften …"].trigger()
    _antwort(monkeypatch, "falsch")
    fenster.aktionen["Block/Rechten Zweig beschriften …"].trigger()

    assert block["labels"] == {"then": "wahr", "else": "falsch"}
