"""Punkt 419: Haltepunkte je Projekt in den Einstellungen, höchstens
für die zuletzt benutzten 20 Projekte."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings

from ide.shell.haltepunkte_ablage import (
    HALTEPUNKTE_MAX,
    haltepunkte_laden,
    haltepunkte_speichern,
)


def _einstellungen() -> QSettings:
    # `_qsettings_isoliert` in conftest.py leitet diesen Ort in
    # `tmp_path` um.
    return QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope,
        "Natter", "Natter-IDE",
    )


def _speichern(einstellungen: QSettings, ordner: Path) -> None:
    ordner.mkdir(parents=True, exist_ok=True)
    haltepunkte_speichern(
        einstellungen, ordner / "t.natter", ordner,
        {str(ordner / "main.py"): ({3}, {3: "x > 1"})},
    )


def test_hoechstens_20_projekte_die_aeltesten_fallen_heraus(
    tmp_path: Path,
) -> None:
    einstellungen = _einstellungen()
    ordner = [tmp_path / f"p{i}" for i in range(HALTEPUNKTE_MAX + 2)]
    for o in ordner:
        _speichern(einstellungen, o)
    # p1 noch einmal benutzt: es rückt nach vorn und bleibt.
    _speichern(einstellungen, ordner[1])
    _speichern(einstellungen, tmp_path / "neu")

    gemerkt = [
        o for o in ordner
        if haltepunkte_laden(einstellungen, o / "t.natter", o)
    ]
    assert HALTEPUNKTE_MAX == 20
    assert gemerkt == [ordner[1], *ordner[4:]]
    assert len(gemerkt) == HALTEPUNKTE_MAX - 1
    assert haltepunkte_laden(einstellungen, ordner[1] / "t.natter", ordner[1]) == {
        str(ordner[1] / "main.py"): ({3}, {3: "x > 1"})
    }


def test_ohne_haltepunkte_verschwindet_der_eintrag(tmp_path: Path) -> None:
    einstellungen = _einstellungen()
    _speichern(einstellungen, tmp_path / "p")
    haltepunkte_speichern(
        einstellungen, tmp_path / "p" / "t.natter", tmp_path / "p", {}
    )

    assert haltepunkte_laden(
        einstellungen, tmp_path / "p" / "t.natter", tmp_path / "p"
    ) == {}
