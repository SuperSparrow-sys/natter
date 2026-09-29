"""Ein offenes Diagramm, dessen Datei sich geändert hat (Punkt 52 der
offenen Punkte).

„Datei → Öffnen …“ holte ein schon offenes Diagramm nur nach vorn, auch
wenn die Datei inzwischen anders aussah; „Quelltext → Erzeugen …“
arbeitete dann mit dem alten Stand. Ohne ungespeicherte Änderungen im
Fenster wird jetzt neu geladen, mit ungespeicherter Arbeit nicht.
"""

from __future__ import annotations

import json
from pathlib import Path

from ide.diagramm import diagramm_erzeugen


def _diagramm(tmp_path: Path) -> Path:
    pfad = tmp_path / "bank.pdiag"
    d = diagramm_erzeugen("class", pfad)
    d.daten["shapes"] = [{
        "id": "s1", "kind": "class", "x": 40, "y": 40, "w": 200, "h": 100,
        "name": "Konto", "attributes": [], "operations": [],
    }]
    d.speichern()
    return pfad


def _von_aussen_umbenennen(pfad: Path, name: str) -> None:
    daten = json.loads(pfad.read_text(encoding="utf-8"))
    daten["shapes"][0]["name"] = name
    pfad.write_text(json.dumps(daten, indent=2, ensure_ascii=False), encoding="utf-8")


def test_geaenderte_datei_wird_neu_geladen(
    qtbot, tmp_path: Path, hauptfenster_bauen
) -> None:  # noqa: ANN001
    pfad = _diagramm(tmp_path)
    fenster = hauptfenster_bauen()
    erstes = fenster.diagramm_oeffnen(pfad)
    _von_aussen_umbenennen(pfad, "Girokonto")

    zweites = fenster.diagramm_oeffnen(pfad)

    assert zweites.diagramm.daten["shapes"][0]["name"] == "Girokonto"
    assert fenster._offene_diagramme[str(pfad)] is zweites
    assert zweites is not erstes


def test_unveraenderte_datei_holt_nur_das_fenster_nach_vorn(
    qtbot, tmp_path: Path, hauptfenster_bauen
) -> None:  # noqa: ANN001
    pfad = _diagramm(tmp_path)
    fenster = hauptfenster_bauen()
    erstes = fenster.diagramm_oeffnen(pfad)

    assert fenster.diagramm_oeffnen(pfad) is erstes


def test_ungespeicherte_arbeit_wird_nicht_ueberschrieben(
    qtbot, tmp_path: Path, hauptfenster_bauen
) -> None:  # noqa: ANN001
    pfad = _diagramm(tmp_path)
    fenster = hauptfenster_bauen()
    erstes = fenster.diagramm_oeffnen(pfad)
    erstes.diagramm.daten["shapes"][0]["name"] = "Sparkonto"
    erstes._geaendert = True
    _von_aussen_umbenennen(pfad, "Girokonto")

    zweites = fenster.diagramm_oeffnen(pfad)

    assert zweites is erstes
    assert zweites.diagramm.daten["shapes"][0]["name"] == "Sparkonto"
