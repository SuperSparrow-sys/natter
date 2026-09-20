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
    assert len(gefunden) == 9  # der Lehrgang, siehe test_beispiellehrgang.py


def test_ein_beispiel_wird_kopiert_statt_geoeffnet(tmp_path: Path) -> None:
    """In einer installierten Natter liegen die Beispiele im
    Programmordner, und dort darf eine Schülerin nicht schreiben."""
    quelle = next(pfad for pfad in beispielprojekte() if pfad.parent.name == "05_Bildergalerie")

    kopie = beispiel_kopieren(quelle, tmp_path)

    assert kopie.exists()
    assert kopie.parent.parent == tmp_path
    assert kopie.parent != quelle.parent
    assert (kopie.parent / "u_main.py").exists()


def test_das_original_bleibt_unberuehrt(tmp_path: Path) -> None:
    quelle = next(pfad for pfad in beispielprojekte() if pfad.parent.name == "05_Bildergalerie")
    vorher = sorted(p.name for p in quelle.parent.iterdir())

    kopie = beispiel_kopieren(quelle, tmp_path)
    (kopie.parent / "neu.txt").write_text("x", encoding="utf-8")

    assert sorted(p.name for p in quelle.parent.iterdir()) == vorher


def test_eine_zweite_kopie_ueberschreibt_die_erste_nicht(tmp_path: Path) -> None:
    """Wer gestern an einem Beispiel gearbeitet hat, bekommt heute eine
    zweite Kopie daneben statt seine Arbeit zurückgesetzt."""
    quelle = next(
        pfad for pfad in beispielprojekte() if pfad.parent.name == "05_Bildergalerie"
    )
    erste = beispiel_kopieren(quelle, tmp_path)
    (erste.parent / "meine_arbeit.py").write_text("print(1)", encoding="utf-8")

    zweite = beispiel_kopieren(quelle, tmp_path)

    assert zweite.parent != erste.parent
    assert (erste.parent / "meine_arbeit.py").exists()


def test_die_kopie_nimmt_keinen_bytecode_mit(tmp_path: Path) -> None:
    """`__pycache__` eines fremden Rechners ist Müll, den niemand
    braucht."""
    quelle = next(pfad for pfad in beispielprojekte() if pfad.parent.name == "05_Bildergalerie")

    kopie = beispiel_kopieren(quelle, tmp_path)

    assert not list(kopie.parent.rglob("__pycache__"))
    assert not list(kopie.parent.rglob("*.pyc"))


# -- Das Bild selbst -----------------------------------------------------


def test_das_startbild_bietet_die_drei_wege(einstellungen: QSettings) -> None:
    bild = Startbild(einstellungen)

    for erwartet in ("neues_projekt", "projekt_oeffnen", "erste_schritte"):
        assert erwartet in bild.knoepfe


def test_die_beispiele_stehen_nicht_mehr_auf_dem_startbild(
    einstellungen: QSettings,
) -> None:
    """Sie sind seit September 2026 ein Untermenü unter „Datei“.

    Auf dem Startbild nahmen die neun Einträge den meisten Platz ein -
    und waren nach dem ersten geöffneten Projekt nicht mehr
    erreichbar, weil das Startbild dann verschwand. Geprüft wird das
    Menü in `tests/test_beispiele_im_dateimenue.py`.
    """
    bild = Startbild(einstellungen)

    assert not [name for name in bild.knoepfe if name.startswith("beispiel:")]


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
    quelle = BEISPIELE / "05_Bildergalerie"
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


# -- Aussehen beim Darüberfahren -------------------------------------------
#
# Gewünscht: „schaue nochmal aufs hover, die schrift
# darf nicht weis werden". Die Einträge des Startbilds verschwanden beim
# Darüberfahren: die allgemeine Regel `QPushButton:hover` setzt weiße
# Schrift, weil dort ein Akzent-Hintergrund dahinterliegt - der kam hier
# aber nicht, weil das eigene Stylesheet des Eintrags
# `background: transparent` setzt und damit gewinnt. Übrig blieb weiße
# Schrift auf weißem Grund.


def _farbe(hex_wert: str) -> tuple[int, int, int]:
    hex_wert = hex_wert.lstrip("#")
    return tuple(int(hex_wert[i : i + 2], 16) for i in (0, 2, 4))


def _helligkeit(hex_wert: str) -> float:
    """Wahrgenommene Helligkeit 0..255 (Rec. 601)."""
    rot, gruen, blau = _farbe(hex_wert)
    return 0.299 * rot + 0.587 * gruen + 0.114 * blau


def _regel(qss: str, selektor: str) -> str:
    """Der Block hinter `selektor` aus einem Stylesheet."""
    anfang = qss.index(selektor + " {")
    return qss[anfang : qss.index("}", anfang)]


def test_der_eintrag_traegt_den_objektnamen_des_themas(qtbot) -> None:
    """Nur über den Objektnamen greift die theme-abhängige Regel; ohne
    ihn bliebe es bei der allgemeinen mit der weißen Schrift."""
    from ide.shell.startbild import _Abschnitt
    from ide.shell.theme import STARTBILD_EINTRAG

    abschnitt = _Abschnitt("Beispiele")
    qtbot.addWidget(abschnitt)
    knopf = abschnitt.knopf_hinzufuegen("Ampel", "Tooltip", lambda: None)

    assert knopf.objectName() == STARTBILD_EINTRAG


def test_das_eigene_stylesheet_faerbt_nicht_selbst() -> None:
    """Die Farben gehören ins IDE-weite QSS, wo das eingestellte Thema
    bekannt ist. Eine eigene Hover-Regel hier würde die dortige
    verdecken, sobald jemand sie erweitert."""
    from ide.shell.startbild import _EINTRAG_STIL

    assert ":hover" not in _EINTRAG_STIL
    assert "color" not in _EINTRAG_STIL


@pytest.mark.parametrize("thema", ["light", "dark"])
def test_beim_darueberfahren_bleibt_die_schrift_lesbar(thema: str) -> None:
    """Der eigentliche Punkt: die Schrift darf nicht weiß werden - und
    allgemeiner: sie muss sich vom Hintergrund abheben."""
    from ide.shell.theme import STARTBILD_EINTRAG, ide_qss_erzeugen
    from pcl.theme import _tokens_laden

    farben = _tokens_laden()["color"][thema]
    qss = ide_qss_erzeugen(thema)
    regel = _regel(qss, f"QPushButton#{STARTBILD_EINTRAG}:hover")

    assert "#ffffff" not in regel.lower()
    assert f"color: {farben['accent']}" in regel
    # Der Eintrag liegt durchsichtig auf dem Fensterhintergrund.
    abstand = abs(_helligkeit(farben["accent"]) - _helligkeit(farben["bg"]))
    assert abstand > 40, (
        f"Die Schrift beim Darüberfahren hebt sich im Thema {thema} kaum "
        f"vom Hintergrund ab (Helligkeitsabstand {abstand:.0f})."
    )
