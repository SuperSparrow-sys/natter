"""Beispielkopien werden wiederverwendet, und das Formular folgt dem
Design von Natter.

Zwei Meldungen aus der Praxis, die beide nach einem Datenverlust
aussahen, ohne einer zu sein:

- Jedes erneute Öffnen eines Beispiels legte eine weitere Kopie an
  („08_Regression 2", „08_Regression 3" …). Die Arbeit von gestern lag
  in der ersten, geöffnet wurde eine frische, und die Liste „Zuletzt
  geöffnet" zeigte zwei gleich benannte Projekte.
- Nach dem Umschalten von Dunkel auf Hell blieben Designer und
  gestartetes Programm dunkel. Das Formular steht auf `theme =
  "system"`, und „system" fragte Windows - nicht Natter.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

import pcl.theme
from ide.shell.hauptfenster import HauptFenster
from ide.shell.startbild import (
    beispiel_kopieren,
    beispiel_original,
    beispiel_zuruecksetzen,
    beispielprojekte,
    ist_beispiel_original,
)
from pcl.theme import theme_aufloesen

_HELL = "#ffffff"
_DUNKEL = "#1e1e1e"


def _beispiel(name: str) -> Path:
    return next(p for p in beispielprojekte() if p.parent.name == name)


@pytest.fixture
def windows_dunkel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows steht auf dunkel. Unter `offscreen` lässt sich das
    Farbschema nicht umstellen, deshalb wird die Abfrage ersetzt."""
    monkeypatch.setattr(pcl.theme, "_farbschema_des_systems", lambda: "dark")


# --------------------------------------------- Kopien der Beispiele


def test_ein_zweites_oeffnen_nimmt_die_vorhandene_kopie() -> None:
    """Die Arbeit von gestern liegt in der ersten Kopie. Eine zweite
    daneben sähe aus, als sei sie verloren."""
    erste = beispiel_kopieren(_beispiel("04_CookieKlicker"))
    (erste.parent / "u_main.py").write_text("# meine Arbeit\n", encoding="utf-8")

    zweite = beispiel_kopieren(_beispiel("04_CookieKlicker"))

    assert zweite == erste
    assert (zweite.parent / "u_main.py").read_text(encoding="utf-8") == "# meine Arbeit\n"
    assert [p.name for p in erste.parent.parent.iterdir()] == ["04_CookieKlicker"]


def test_ein_fremder_ordner_gleichen_namens_wird_nicht_uebernommen(
    tmp_path: Path,
) -> None:
    """Heißt ein eigenes Projekt zufällig wie ein Beispiel, bleibt es
    unangetastet - erkannt wird eine Kopie an ihrer Projektdatei, nicht
    am Ordnernamen."""
    wurzel = tmp_path / "Natter"
    fremd = wurzel / "04_CookieKlicker"
    fremd.mkdir(parents=True)
    (fremd / "mein_spiel.natter").write_text("{}", encoding="utf-8")

    kopie = beispiel_kopieren(_beispiel("04_CookieKlicker"), wurzel)

    assert kopie.parent.name == "04_CookieKlicker 2"
    assert (fremd / "mein_spiel.natter").exists()


def test_eine_kopie_kennt_ihr_original() -> None:
    kopie = beispiel_kopieren(_beispiel("08_Regression"))

    assert beispiel_original(kopie.parent) == _beispiel("08_Regression").parent


def test_ein_eigenes_projekt_hat_kein_original(tmp_path: Path) -> None:
    eigenes = tmp_path / "Mein Projekt"
    eigenes.mkdir()
    (eigenes / "Mein Projekt.natter").write_text("{}", encoding="utf-8")

    assert beispiel_original(eigenes) is None


def test_das_original_selbst_ist_keine_kopie() -> None:
    original = _beispiel("08_Regression")

    assert ist_beispiel_original(original)
    assert beispiel_original(original.parent) is None


def test_zuruecksetzen_stellt_den_ausgangszustand_her() -> None:
    kopie = beispiel_kopieren(_beispiel("01_Begruessung"))
    (kopie.parent / "u_main.py").write_text("kaputt\n", encoding="utf-8")
    (kopie.parent / "notizen.txt").write_text("neu\n", encoding="utf-8")
    original = _beispiel("01_Begruessung").parent

    beispiel_zuruecksetzen(kopie.parent)

    assert (kopie.parent / "u_main.py").read_bytes() == (original / "u_main.py").read_bytes()
    assert not (kopie.parent / "notizen.txt").exists()


def test_zuruecksetzen_verweigert_ein_eigenes_projekt(tmp_path: Path) -> None:
    """Ohne Original gibt es nichts, worauf zurückgesetzt werden
    könnte - und gelöscht wird dann erst recht nichts."""
    eigenes = tmp_path / "Mein Projekt"
    eigenes.mkdir()
    (eigenes / "u_main.py").write_text("wichtig\n", encoding="utf-8")

    with pytest.raises(ValueError):
        beispiel_zuruecksetzen(eigenes)

    assert (eigenes / "u_main.py").read_text(encoding="utf-8") == "wichtig\n"


def test_ein_original_aus_der_liste_wird_als_kopie_geoeffnet() -> None:
    """„Zuletzt geöffnet" enthielt die Originale unter
    `beispielprojekte`. Ein Klick darauf öffnete das Beispiel selbst,
    und jede Änderung landete darin - in einer installierten Natter im
    Programmordner, in den eine Schülerin gar nicht schreiben darf."""
    fenster = HauptFenster()
    original = _beispiel("09_ObstSortierer")

    projekt = fenster.projekt_oeffnen_gemeldet(original)

    assert projekt is not None
    assert not ist_beispiel_original(projekt.ordner)
    assert beispiel_original(projekt.ordner) == original.parent


def test_das_menue_bietet_das_zuruecksetzen_nur_bei_einer_kopie_an(
    tmp_path: Path,
) -> None:
    fenster = HauptFenster()
    eintrag = fenster._beispiel_zuruecksetzen_eintrag

    assert not eintrag.isEnabled()

    fenster.beispiel_oeffnen(_beispiel("01_Begruessung"))
    assert eintrag.isEnabled()

    eigenes = tmp_path / "Eigenes"
    eigenes.mkdir()
    (eigenes / "Eigenes.natter").write_text(
        (_beispiel("01_Begruessung")).read_text(encoding="utf-8"), encoding="utf-8"
    )
    for datei in ("main.py", "u_main.py", "u_main.pfm", "u_main_design.py"):
        quelle = _beispiel("01_Begruessung").parent / datei
        if quelle.exists():
            (eigenes / datei).write_bytes(quelle.read_bytes())
    fenster.projekt_oeffnen(eigenes / "Eigenes.natter")
    assert not eintrag.isEnabled()


# --------------------------------------------- Das Design


def test_system_folgt_natter_wenn_natter_es_vorgibt(
    monkeypatch: pytest.MonkeyPatch, windows_dunkel: None
) -> None:
    monkeypatch.setenv("NATTER_THEMA", "light")
    assert theme_aufloesen("system") == "light"

    monkeypatch.setenv("NATTER_THEMA", "dark")
    assert theme_aufloesen("system") == "dark"


def test_ohne_vorgabe_folgt_system_weiter_windows(
    monkeypatch: pytest.MonkeyPatch, windows_dunkel: None
) -> None:
    """So läuft ein Programm außerhalb von Natter: `python main.py`
    oder die exportierte Exe richten sich nach Windows."""
    monkeypatch.delenv("NATTER_THEMA", raising=False)

    assert theme_aufloesen("system") == "dark"


def test_eine_unsinnige_vorgabe_wird_uebergangen(
    monkeypatch: pytest.MonkeyPatch, windows_dunkel: None
) -> None:
    monkeypatch.setenv("NATTER_THEMA", "lila")

    assert theme_aufloesen("system") == "dark"


def test_hell_in_natter_macht_den_designer_hell_auch_bei_dunklem_windows(
    tmp_path: Path, windows_dunkel: None
) -> None:
    """Der gemeldete Fall: Natter auf Hell, das Formular blieb dunkel,
    weil „system" Windows fragte."""
    kopie = beispiel_kopieren(_beispiel("04_CookieKlicker"))
    fenster = HauptFenster()
    fenster._design_wechseln("light")

    formular = fenster.designer_oeffnen(kopie.parent / "u_main.pfm")

    assert _HELL in formular._qwidget.styleSheet()
    assert _DUNKEL not in formular._qwidget.styleSheet()


def test_ein_offener_designer_zieht_beim_umschalten_mit() -> None:
    """Der zweite Teil desselben Fehlers: `_design_wechseln()` frischte
    Editor-Tabs und Symbole auf, offene Formulare aber nicht."""
    kopie = beispiel_kopieren(_beispiel("04_CookieKlicker"))
    fenster = HauptFenster()
    fenster._design_wechseln("dark")
    formular = fenster.designer_oeffnen(kopie.parent / "u_main.pfm")
    assert _DUNKEL in formular._qwidget.styleSheet()

    fenster._design_wechseln("light")

    assert _HELL in formular._qwidget.styleSheet()
    assert _DUNKEL not in formular._qwidget.styleSheet()


def test_das_gestartete_programm_erbt_das_design_von_natter() -> None:
    """Das Programm läuft als eigener Prozess und erbt die Umgebung.
    Steht Natter auf „System", gibt es nichts vorzugeben - dann soll
    auch das Programm Windows folgen."""
    fenster = HauptFenster()

    fenster._design_wechseln("light")
    assert os.environ.get("NATTER_THEMA") == "light"

    fenster._design_wechseln("dark")
    assert os.environ.get("NATTER_THEMA") == "dark"

    fenster._design_wechseln("system")
    assert "NATTER_THEMA" not in os.environ


def test_die_vorgabe_gilt_schon_ab_dem_start() -> None:
    """Sonst stimmte das erste Formular nach dem Start nicht, sondern
    erst eines nach dem ersten Umschalten."""
    fenster = HauptFenster()
    fenster._design_einstellungen.setValue("design/thema", "dark")
    fenster.close()

    HauptFenster()

    assert os.environ.get("NATTER_THEMA") == "dark"

