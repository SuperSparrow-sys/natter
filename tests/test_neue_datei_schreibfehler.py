"""Punkt 417: „Neue Unit“, „Neue Test-Unit“ und „Neues Formular …“ in
einem Ordner, in den sich nicht schreiben lässt.

Statt einer Ausnahme aus dem Menü heraus kommt die Meldung wie beim
Speichern, und im Projektordner bleibt keine halb angelegte Datei
liegen. Beim Formular scheitert je Fall eine andere der drei Dateien.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtWidgets import QInputDialog, QMessageBox

import ide.shell.hauptfenster as hauptfenster_modul
from ide.project import projekt_erzeugen


def _dateien(ordner: Path) -> set[Path]:
    return {p for p in ordner.rglob("*") if p.is_file()}


@pytest.mark.parametrize(
    ("aktion", "scheitert_beim"),
    [
        ("_neue_unit_aktion", 1),
        ("_neue_test_unit_aktion", 1),
        ("_neues_formular_aktion", 1),
        ("_neues_formular_aktion", 2),
        ("_neues_formular_aktion", 3),
    ],
)
def test_schreibfehler_wird_gemeldet_und_nichts_bleibt_liegen(
    hauptfenster, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    aktion: str, scheitert_beim: int,
) -> None:
    ordner = tmp_path / "Rechner"
    projekt_erzeugen("gui", ordner, "Rechner")
    hauptfenster.projekt_oeffnen(ordner)
    vorher = _dateien(ordner)

    echt = hauptfenster_modul.atomar_schreiben
    aufrufe: list[Path] = []

    def schreiben(pfad, inhalt, **kwargs) -> None:  # noqa: ANN001
        aufrufe.append(Path(pfad))
        if len(aufrufe) == scheitert_beim:
            raise PermissionError(13, "Zugriff verweigert", str(pfad))
        echt(pfad, inhalt, **kwargs)

    meldungen: list[str] = []
    monkeypatch.setattr(hauptfenster_modul, "atomar_schreiben", schreiben)
    monkeypatch.setattr(
        QMessageBox, "warning",
        lambda _eltern, _titel, text, *a, **k: meldungen.append(text)
        or QMessageBox.StandardButton.Ok,
    )
    monkeypatch.setattr(
        QInputDialog, "getText", lambda *a, **k: ("u_zweit", True)
    )

    getattr(hauptfenster, aktion)()

    assert len(aufrufe) == scheitert_beim
    assert len(meldungen) == 1
    assert "konnte nicht gespeichert werden" in meldungen[0]
    assert "nicht angelegt" in meldungen[0]
    assert _dateien(ordner) == vorher
