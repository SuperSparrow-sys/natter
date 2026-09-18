"""Löst jeden aktiven Menüeintrag des Diagramm-Fensters wirklich aus.

Vom Nutzer gemeldet: „Datei → Exportieren …“, „Speichern unter …“ und
„Drucken …“ stürzten ab mit

    TypeError: argument should be a str or an os.PathLike object …
    not 'bool'

Ursache war eine ganze Fehlerklasse, nicht ein einzelner Tippfehler:
`QAction.triggered` schickt immer ein `checked`-Flag mit. Eine Methode,
deren erster Parameter optional ist (`pfad=None`, `drucker=None`),
bekommt dadurch `False` hineingereicht statt gar nichts. Die alten
Tests riefen `fenster.exportieren(pfad)` direkt auf und gingen deshalb
nie durch die Signalverbindung.

Dieser Test geht den Weg, den auch ein Klick nimmt: `aktion.trigger()`.
Dialoge werden dabei stillgelegt, damit nichts stehen bleibt.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QColorDialog, QFileDialog, QInputDialog

from ide.diagramm import DiagrammFenster, diagramm_erzeugen

#: Einträge, die bewusst ein Fenster schließen oder einen echten
#: Systemdialog brauchen – die werden einzeln geprüft, nicht im Rundlauf.
AUSGENOMMEN = {"Datei/Schließen", "Datei/Drucken …"}


@pytest.fixture(autouse=True)
def _dialoge_stilllegen(monkeypatch: pytest.MonkeyPatch) -> None:
    """Jeder Dialog verhält sich, als hätte der Nutzer abgebrochen."""
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", ""))
    )
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName", staticmethod(lambda *a, **k: ("", ""))
    )
    monkeypatch.setattr(QInputDialog, "getText", staticmethod(lambda *a, **k: ("", False)))
    monkeypatch.setattr(QColorDialog, "getColor", staticmethod(lambda *a, **k: None))


def _fenster(tmp_path: Path, typ: str) -> DiagrammFenster:
    return DiagrammFenster(diagramm_erzeugen(typ, tmp_path / f"{typ}.pdiag", typ))


@pytest.mark.parametrize("typ", ["class", "struktogramm", "entscheidungstabelle"])
def test_jeder_aktive_menueeintrag_laesst_sich_ausloesen(tmp_path: Path, typ: str) -> None:
    """Der eigentliche Regressionstest: nichts darf beim Auslösen
    hochgehen."""
    fenster = _fenster(tmp_path, typ)

    ausgeloest = 0
    for pfad, aktion in fenster.aktionen.items():
        if pfad in AUSGENOMMEN or not aktion.isEnabled() or aktion.menu() is not None:
            continue
        aktion.trigger()  # würde bei der alten Verdrahtung TypeError werfen
        ausgeloest += 1

    assert ausgeloest > 5


def test_exportieren_ueber_das_menue_stuerzt_nicht_ab(tmp_path: Path) -> None:
    """Genau der gemeldete Absturz: `triggered` reichte `False` als
    `pfad` durch."""
    fenster = _fenster(tmp_path, "class")

    fenster.aktionen["Datei/Exportieren …"].trigger()

    # Abgebrochener Dialog -> keine Datei, keine Ausnahme
    assert list(tmp_path.glob("*.png")) == []


def test_speichern_unter_ueber_das_menue_stuerzt_nicht_ab(tmp_path: Path) -> None:
    fenster = _fenster(tmp_path, "class")
    vorher = fenster.diagramm.pfad

    fenster.aktionen["Datei/Speichern unter …"].trigger()

    assert fenster.diagramm.pfad == vorher


@pytest.mark.drucker
def test_drucken_ueber_das_menue_stuerzt_nicht_ab(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Hier hätte `QPainter(False)` zugeschlagen. Der Vorschaudialog
    wird durch eine Attrappe ersetzt, damit nichts stehen bleibt."""
    import ide.diagramm.fenster as fenster_modul

    geoeffnet: list[object] = []

    class _Attrappe:
        def __init__(self, drucker, eltern=None) -> None:
            geoeffnet.append(drucker)

        def setWindowTitle(self, _titel: str) -> None: ...

        @property
        def paintRequested(self):
            class _Signal:
                def connect(self, _rueckruf) -> None: ...

            return _Signal()

        def exec(self) -> int:
            return 0

    monkeypatch.setattr(fenster_modul, "QPrintPreviewDialog", _Attrappe)
    fenster = _fenster(tmp_path, "class")

    fenster.aktionen["Datei/Drucken …"].trigger()

    # Der Vorschau wurde ein echter Drucker übergeben, kein `False`
    assert geoeffnet and geoeffnet[0] is not False


def test_menueeintraege_ohne_parameter_bleiben_verschont(tmp_path: Path) -> None:
    """Gegenprobe: `speichern()` hat keinen Parameter, PySide6 lässt das
    `checked`-Flag dort weg – der Eintrag muss also wirklich speichern."""
    fenster = _fenster(tmp_path, "class")
    fenster.zeichenflaeche.form_platzieren("class", 200, 200)

    fenster.aktionen["Datei/Speichern"].trigger()

    assert fenster.diagramm.pfad.exists()
    assert "gespeichert" in fenster.statusBar().currentMessage()
