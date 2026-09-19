"""Tests für das Startbild (M11, Abschnitt 4). Headless.

Vom Nutzer ausdrücklich gefordert: „Ich brauche einen Startbildschirm."
Bis dahin sah jemand beim allerersten Start ein leeres graues Feld –
weder die zehn mitgelieferten Beispielprojekte noch einen Weg, selbst
eines anzulegen.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from ide.shell.hauptfenster import HauptFenster
from ide.shell.startbild import (
    ZULETZT_MAX,
    Startbild,
    beispiel_kopieren,
    beispielprojekte,
    zuletzt_geoeffnet,
    zuletzt_merken,
)

BEISPIELE = Path(__file__).resolve().parent.parent / "beispielprojekte"


@pytest.fixture
def einstellungen(tmp_path: Path) -> QSettings:
    """Eigene Einstellungsdatei je Test – sonst schriebe der Test in
    die echten Einstellungen des Nutzers."""
    return QSettings(str(tmp_path / "test.ini"), QSettings.Format.IniFormat)


# -- Zuletzt geöffnet ----------------------------------------------------


def test_am_anfang_ist_die_liste_leer(einstellungen: QSettings) -> None:
    assert zuletzt_geoeffnet(einstellungen) == []


def test_ein_geoeffnetes_projekt_steht_vorn(einstellungen: QSettings, tmp_path: Path) -> None:
    erstes = tmp_path / "a" / "a.natter"
    zweites = tmp_path / "b" / "b.natter"
    for pfad in (erstes, zweites):
        pfad.parent.mkdir()
        pfad.write_text("{}", encoding="utf-8")

    zuletzt_merken(einstellungen, erstes)
    zuletzt_merken(einstellungen, zweites)

    assert zuletzt_geoeffnet(einstellungen)[0] == zweites


def test_dasselbe_projekt_steht_nur_einmal_darin(einstellungen: QSettings, tmp_path: Path) -> None:
    pfad = tmp_path / "a" / "a.natter"
    pfad.parent.mkdir()
    pfad.write_text("{}", encoding="utf-8")

    zuletzt_merken(einstellungen, pfad)
    zuletzt_merken(einstellungen, pfad)

    assert len(zuletzt_geoeffnet(einstellungen)) == 1


def test_die_liste_bleibt_kurz(einstellungen: QSettings, tmp_path: Path) -> None:
    """Mehr als acht wären auf einem Schulrechner ohnehin nicht
    wiederzuerkennen."""
    for nummer in range(ZULETZT_MAX + 4):
        pfad = tmp_path / f"p{nummer}" / f"p{nummer}.natter"
        pfad.parent.mkdir()
        pfad.write_text("{}", encoding="utf-8")
        zuletzt_merken(einstellungen, pfad)

    assert len(zuletzt_geoeffnet(einstellungen)) == ZULETZT_MAX


def test_ein_geloeschtes_projekt_faellt_heraus(einstellungen: QSettings, tmp_path: Path) -> None:
    """Ein Eintrag, der ins Leere zeigt, wäre schlimmer als keiner: man
    klickt darauf und bekommt eine Fehlermeldung."""
    pfad = tmp_path / "weg" / "weg.natter"
    pfad.parent.mkdir()
    pfad.write_text("{}", encoding="utf-8")
    zuletzt_merken(einstellungen, pfad)

    shutil.rmtree(pfad.parent)

    assert zuletzt_geoeffnet(einstellungen) == []


# -- Beispiele -----------------------------------------------------------


def test_alle_beispielprojekte_werden_gefunden() -> None:
    gefunden = {pfad.parent.name for pfad in beispielprojekte()}
    vorhanden = {ordner.name for ordner in BEISPIELE.iterdir() if ordner.is_dir()}

    assert gefunden == vorhanden
    assert len(gefunden) >= 10


def test_ein_beispiel_wird_kopiert_statt_geoeffnet(tmp_path: Path) -> None:
    """In einer installierten Natter liegen die Beispiele im
    Programmordner, und dort darf eine Schülerin nicht schreiben."""
    quelle = next(pfad for pfad in beispielprojekte() if pfad.parent.name == "Garten")

    kopie = beispiel_kopieren(quelle, tmp_path)

    assert kopie.exists()
    assert kopie.parent.parent == tmp_path
    assert kopie.parent != quelle.parent
    assert (kopie.parent / "u_main.py").exists()


def test_das_original_bleibt_unberuehrt(tmp_path: Path) -> None:
    quelle = next(pfad for pfad in beispielprojekte() if pfad.parent.name == "Garten")
    vorher = sorted(p.name for p in quelle.parent.iterdir())

    kopie = beispiel_kopieren(quelle, tmp_path)
    (kopie.parent / "neu.txt").write_text("x", encoding="utf-8")

    assert sorted(p.name for p in quelle.parent.iterdir()) == vorher


def test_eine_zweite_kopie_ueberschreibt_die_erste_nicht(tmp_path: Path) -> None:
    """Wer gestern am Beispiel „Ampel" gearbeitet hat, bekommt heute
    „Ampel 2" statt seine Arbeit zurückgesetzt."""
    quelle = next(pfad for pfad in beispielprojekte() if pfad.parent.name == "Ampel")
    erste = beispiel_kopieren(quelle, tmp_path)
    (erste.parent / "meine_arbeit.py").write_text("print(1)", encoding="utf-8")

    zweite = beispiel_kopieren(quelle, tmp_path)

    assert zweite.parent != erste.parent
    assert (erste.parent / "meine_arbeit.py").exists()


def test_die_kopie_nimmt_keinen_bytecode_mit(tmp_path: Path) -> None:
    """`__pycache__` eines fremden Rechners ist Müll, den niemand
    braucht."""
    quelle = next(pfad for pfad in beispielprojekte() if pfad.parent.name == "Garten")

    kopie = beispiel_kopieren(quelle, tmp_path)

    assert not list(kopie.parent.rglob("__pycache__"))
    assert not list(kopie.parent.rglob("*.pyc"))


# -- Das Bild selbst -----------------------------------------------------


def test_das_startbild_bietet_die_drei_wege(einstellungen: QSettings) -> None:
    bild = Startbild(einstellungen)

    for erwartet in ("neues_projekt", "projekt_oeffnen", "erste_schritte"):
        assert erwartet in bild.knoepfe


def test_das_startbild_zeigt_die_beispiele(einstellungen: QSettings) -> None:
    """Die zehn Beispielprojekte sind da, aber bis jetzt fand sie
    niemand."""
    bild = Startbild(einstellungen)

    beispiele = [name for name in bild.knoepfe if name.startswith("beispiel:")]
    assert len(beispiele) >= 10


def test_ohne_zuletzt_geoeffnete_fehlt_der_abschnitt(
    einstellungen: QSettings,
) -> None:
    """Ein leerer Abschnitt „Zuletzt geöffnet" beim allerersten Start
    wäre eine Überschrift über nichts."""
    bild = Startbild(einstellungen)

    assert not [name for name in bild.knoepfe if name.startswith("zuletzt:")]


def test_nach_einem_projekt_erscheint_der_abschnitt(
    einstellungen: QSettings, tmp_path: Path
) -> None:
    pfad = tmp_path / "Meins" / "meins.natter"
    pfad.parent.mkdir()
    pfad.write_text("{}", encoding="utf-8")
    zuletzt_merken(einstellungen, pfad)

    bild = Startbild(einstellungen)

    assert "zuletzt:Meins" in bild.knoepfe


def test_jeder_knopf_hat_einen_tooltip(einstellungen: QSettings) -> None:
    """M11, Abschnitt 4: Tooltips überall. Ein Knopf ohne Erklärung ist
    für jemanden, der Natter zum ersten Mal sieht, eine Zumutung."""
    bild = Startbild(einstellungen)

    for name, knopf in bild.knoepfe.items():
        assert knopf.toolTip().strip(), f"{name} hat keinen Tooltip"


# -- Im Hauptfenster -----------------------------------------------------


def test_beim_start_steht_das_startbild_in_der_mitte(qtbot) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    assert fenster.mitte.currentWidget() is fenster.startbild


def test_mit_geoeffneter_datei_weicht_es_den_tabs(qtbot, tmp_path: Path) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    datei = tmp_path / "u_test.py"
    datei.write_text("a = 1\n", encoding="utf-8")

    fenster.datei_oeffnen(datei)

    assert fenster.mitte.currentWidget() is fenster.editor_tabs


def test_nach_dem_schliessen_des_letzten_tabs_kommt_es_zurueck(qtbot, tmp_path: Path) -> None:
    """Sonst stünde man wieder vor einer leeren Fläche – genau dem
    Zustand, den das Startbild abschaffen soll."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    datei = tmp_path / "u_test.py"
    datei.write_text("a = 1\n", encoding="utf-8")
    fenster.datei_oeffnen(datei)

    fenster.editor_tabs.removeTab(0)

    assert fenster.mitte.currentWidget() is fenster.startbild


def test_ein_geoeffnetes_projekt_landet_im_startbild(qtbot, tmp_path: Path) -> None:
    quelle = BEISPIELE / "Garten"
    ziel = tmp_path / "Garten"
    shutil.copytree(quelle, ziel, ignore=shutil.ignore_patterns("__pycache__"))
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster.projekt_oeffnen(next(ziel.glob("*.natter")))

    assert "zuletzt:Garten" in fenster.startbild.knoepfe


def test_die_anleitung_erste_schritte_gibt_es_wirklich() -> None:
    """Das Startbild bietet sie an – eine Schaltfläche, die auf eine
    fehlende Datei zeigt, wäre schlimmer als keine."""
    from ide.pfade import daten_ordner

    assert (daten_ordner("docs") / "erste_schritte.md").exists()


# -- Aus der Sichtprüfung ------------------------------------------------


def test_zwei_projekte_mit_gleichem_namen_sind_unterscheidbar(tmp_path: Path) -> None:
    """Fund aus der Sichtprüfung: unter „Zuletzt geöffnet" standen zwei
    „Garten" untereinander – eine Kopie des Beispiels und das Original.
    Zwei gleich beschriftete Einträge sind ein Ratespiel."""
    from ide.shell.startbild import eindeutige_namen

    erster = tmp_path / "Schule" / "Garten" / "g.natter"
    zweiter = tmp_path / "Zuhause" / "Garten" / "g.natter"
    dritter = tmp_path / "Zuhause" / "Ampel" / "a.natter"

    namen = eindeutige_namen([erster, zweiter, dritter])

    assert namen[0] != namen[1]
    assert "Schule" in namen[0] and "Zuhause" in namen[1]
    # Ein eindeutiger Name bleibt schlicht
    assert namen[2] == "Ampel"


def test_ein_einzelner_name_bleibt_kurz(tmp_path: Path) -> None:
    from ide.shell.startbild import eindeutige_namen

    assert eindeutige_namen([tmp_path / "Ampel" / "a.natter"]) == ["Ampel"]
