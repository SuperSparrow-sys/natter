"""Eine Unit löschen heißt: auch das Hintergründige verschwindet.

Grundsatz des Nutzers (September 2026): „alles was zum Projekt gehört
muss als Schüler in den Dateien hinzufügbar sein und der Rest muss
automatisch hinzugefügt und gelöscht werden in den anderen Dateien im
Hintergrund".

Eine Unit mit Formular besteht aus drei Dateien, von denen der
Projekt-Explorer nur zwei zeigt:

    u_ampel.py          der Code, den die Schülerin schreibt
    u_ampel.pfm         das Formular
    u_ampel_design.py   erzeugt, deshalb ausgeblendet

Gelöscht wurde bisher nur die angeklickte Datei. Zurück blieb erzeugter
Code zu einem Formular, das es nicht mehr gibt - im Explorer unsichtbar
und damit von Hand auch nicht wegzubekommen.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PySide6.QtWidgets import QMessageBox

from ide.project.projekt import Projekt
from ide.shell.hauptfenster import HauptFenster


@pytest.fixture
def projekt(tmp_path: Path) -> Projekt:
    """Eine Kopie eines mitgelieferten Beispiels - die Vorlage im
    Repository darf ein Test nie anfassen (AGENTS.md)."""
    quelle = Path("beispielprojekte/04_CookieKlicker")
    ziel = tmp_path / "CookieKlicker"
    shutil.copytree(quelle, ziel, ignore=shutil.ignore_patterns("__pycache__"))

    # Eine zweite Unit mit Formular, die gelöscht werden darf, ohne dem
    # Projekt sein Hauptformular zu nehmen.
    for endung, inhalt in (
        (
            ".py",
            "from u_zweit_design import Form2Design\n\n\nclass Form2(Form2Design):\n    pass\n",
        ),
        (".pfm", '{"format": "pfm/1", "class": "Form2", "type": "Form", "properties": {}}\n'),
        ("_design.py", "# erzeugt\n"),
    ):
        (ziel / f"u_zweit{endung}").write_text(inhalt, encoding="utf-8")

    return Projekt.laden(ziel)


def test_die_erzeugten_dateien_gehoeren_dazu(projekt: Projekt) -> None:
    namen = [p.name for p in projekt.zusammengehoerige_dateien(projekt.ordner / "u_zweit.py")]

    assert namen == ["u_zweit.pfm", "u_zweit.py", "u_zweit_design.py"]


def test_auch_vom_formular_aus_gefunden(projekt: Projekt) -> None:
    """Im Explorer steht die Unit unter „Units", das Formular unter
    „Formulare" - von beiden aus muss dasselbe gemeint sein."""
    namen = [p.name for p in projekt.zusammengehoerige_dateien(projekt.ordner / "u_zweit.pfm")]

    assert namen == ["u_zweit.pfm", "u_zweit.py", "u_zweit_design.py"]


def test_eine_unit_ohne_formular_bleibt_allein(projekt: Projekt) -> None:
    """Der Gegentest: eine reine Code-Unit zieht nichts mit."""
    (projekt.ordner / "u_hilfe.py").write_text("WERT = 1\n", encoding="utf-8")

    namen = [p.name for p in projekt.zusammengehoerige_dateien(projekt.ordner / "u_hilfe.py")]

    assert namen == ["u_hilfe.py"]


def test_loeschen_raeumt_alle_drei_dateien_weg(projekt: Projekt, monkeypatch, qtbot) -> None:
    """Der eigentliche Punkt, über das Hauptfenster gefahren."""
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )
    # Nicht in den echten Papierkorb des Nutzers greifen.
    monkeypatch.setattr("ide.shell.hauptfenster.in_den_papierkorb", lambda pfad: False)

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen_gemeldet(projekt.ordner)

    fenster._unit_loeschen(projekt.ordner / "u_zweit.py")

    assert not (projekt.ordner / "u_zweit.py").exists()
    assert not (projekt.ordner / "u_zweit.pfm").exists()
    assert not (projekt.ordner / "u_zweit_design.py").exists()


def test_das_hauptformular_bleibt_unberuehrt(projekt: Projekt, monkeypatch, qtbot) -> None:
    """Die Gegenprobe zum Test darüber: gelöscht wird genau eine Unit,
    nicht alles, was ähnlich heißt."""
    monkeypatch.setattr(
        QMessageBox,
        "question",
        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes),
    )
    monkeypatch.setattr("ide.shell.hauptfenster.in_den_papierkorb", lambda pfad: False)

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen_gemeldet(projekt.ordner)

    fenster._unit_loeschen(projekt.ordner / "u_zweit.py")

    assert (projekt.ordner / "u_main.py").exists()
    assert (projekt.ordner / "u_main.pfm").exists()
    assert (projekt.ordner / "u_main_design.py").exists()
