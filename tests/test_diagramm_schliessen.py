"""Punkt 111: ein geändertes Diagramm schließt nicht mehr ohne Frage.

Vorher schloss das Fenster über „Datei → Schließen“ und über das X
sofort, und die `.pdiag` blieb auf dem alten Stand. Geprüft werden
die drei Antworten auf die Frage und ein Speichern, das scheitert.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from ide.diagramm import Diagramm, DiagrammFenster, diagramm_erzeugen

_ANTWORT = QMessageBox.StandardButton


def _geaendertes_fenster(tmp_path: Path) -> DiagrammFenster:
    fenster = DiagrammFenster(
        diagramm_erzeugen("class", tmp_path / "a.pdiag", "Testdiagramm")
    )
    fenster.zeichenflaeche.form_platzieren("class", 40, 40)
    assert fenster.geaendert
    assert fenster.windowTitle().startswith("*")
    return fenster


def _formen_in_datei(tmp_path: Path) -> int:
    return len(Diagramm.laden(tmp_path / "a.pdiag").daten["shapes"])


def _antwort_vorgeben(monkeypatch, antwort) -> list[int]:  # noqa: ANN001
    gefragt: list[int] = []

    def fragen(self) -> QMessageBox.StandardButton:  # noqa: ANN001
        gefragt.append(1)
        return antwort

    monkeypatch.setattr(DiagrammFenster, "_vor_dem_schliessen_fragen", fragen)
    return gefragt


def test_abbrechen_laesst_das_fenster_offen(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    fenster = _geaendertes_fenster(tmp_path)
    fenster.show()
    gefragt = _antwort_vorgeben(monkeypatch, _ANTWORT.Cancel)

    assert fenster.close() is False

    assert gefragt == [1]
    assert fenster.isVisible()
    assert fenster.geaendert
    assert _formen_in_datei(tmp_path) == 0


def test_speichern_schreibt_und_schliesst(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    fenster = _geaendertes_fenster(tmp_path)
    _antwort_vorgeben(monkeypatch, _ANTWORT.Save)

    assert fenster.close() is True

    assert _formen_in_datei(tmp_path) == 1


def test_verwerfen_schliesst_ohne_zu_schreiben(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    fenster = _geaendertes_fenster(tmp_path)
    _antwort_vorgeben(monkeypatch, _ANTWORT.Discard)

    assert fenster.close() is True

    assert _formen_in_datei(tmp_path) == 0


def test_ungeaendertes_diagramm_schliesst_ohne_frage(
    tmp_path: Path, monkeypatch  # noqa: ANN001
) -> None:
    fenster = DiagrammFenster(
        diagramm_erzeugen("class", tmp_path / "a.pdiag", "Testdiagramm")
    )
    gefragt = _antwort_vorgeben(monkeypatch, _ANTWORT.Cancel)

    assert fenster.close() is True
    assert gefragt == []


def test_datei_schliessen_fragt_ebenfalls(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    fenster = _geaendertes_fenster(tmp_path)
    fenster.show()
    gefragt = _antwort_vorgeben(monkeypatch, _ANTWORT.Cancel)

    fenster.aktionen["Datei/Schließen"].trigger()

    assert gefragt == [1]
    assert fenster.isVisible()


def test_gescheitertes_speichern_meldet_und_haelt_das_fenster_offen(
    tmp_path: Path, monkeypatch  # noqa: ANN001
) -> None:
    fenster = _geaendertes_fenster(tmp_path)
    fenster.show()
    _antwort_vorgeben(monkeypatch, _ANTWORT.Save)
    gemeldet: list[str] = []
    monkeypatch.setattr(
        DiagrammFenster,
        "_speicherfehler_melden",
        lambda self, pfad, fehler: gemeldet.append(pfad.name),
    )

    def scheitern(self, pfad=None) -> None:  # noqa: ANN001
        raise PermissionError(13, "Zugriff verweigert")

    monkeypatch.setattr(Diagramm, "speichern", scheitern)

    assert fenster.close() is False

    assert gemeldet == ["a.pdiag"]
    assert fenster.isVisible()
    assert fenster.geaendert


def test_speichern_unter_meldet_einen_fehler(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    fenster = _geaendertes_fenster(tmp_path)
    gemeldet: list[str] = []
    monkeypatch.setattr(
        DiagrammFenster,
        "_speicherfehler_melden",
        lambda self, pfad, fehler: gemeldet.append(pfad.name),
    )

    def scheitern(self, pfad=None) -> None:  # noqa: ANN001
        raise OSError(28, "Kein Platz")

    monkeypatch.setattr(Diagramm, "speichern", scheitern)

    assert fenster.speichern_unter(tmp_path / "b.pdiag") is None
    assert gemeldet == ["b.pdiag"]
    assert fenster.geaendert


def test_nach_gescheitertem_speichern_geht_es_mit_speichern_unter_weiter(
    tmp_path: Path, monkeypatch  # noqa: ANN001
) -> None:
    """Punkt 505: ein Diagramm aus einem schreibgeschützten Ordner der
    Lehrkraft ließ sich ändern, aber nicht speichern, und die Meldung
    bot nur „OK“. Jetzt führt sie zu „Speichern unter …“."""
    fenster = _geaendertes_fenster(tmp_path)
    original = Diagramm.speichern
    gemeldet: list[str] = []

    def nur_original_scheitert(self, pfad=None) -> None:  # noqa: ANN001
        if pfad is None:
            raise PermissionError(13, "Die Datei ist schreibgeschützt")
        original(self, pfad)

    monkeypatch.setattr(Diagramm, "speichern", nur_original_scheitert)
    monkeypatch.setattr(
        DiagrammFenster,
        "_speicherfehler_melden",
        lambda self, pfad, fehler: gemeldet.append(pfad.name) or True,
    )
    ziel = tmp_path / "eigenes" / "kopie.pdiag"
    monkeypatch.setattr(
        "ide.diagramm.fenster.QFileDialog.getSaveFileName",
        lambda *a, **k: (str(ziel), ""),
    )

    assert fenster.speichern() is True

    assert gemeldet == ["a.pdiag"]
    assert ziel.is_file()
    assert not fenster.geaendert
