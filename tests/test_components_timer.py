"""Tests für `pcl/components/system.py`: Timer. Headless.

Vorbild ist `t_hunger: TTimer` aus `referenz/lazarus/l_Pet/u_main.lfm`
(`OnTimer = t_hungerTimer`, im Quelltext über `t_hunger.enabled := true`
geschaltet).
"""

import pytest

from pcl import Form, Timer
from pcl.control import Control
from pcl.errors import NatterPropertyError, NatterUnbekannteEigenschaftError


class _Formular(Form):
    """So entsteht ein Timer wirklich: als Attribut des Formulars, nicht
    über die Palette (`Timer` ist nicht sichtbar, siehe
    docs/komponenten.md)."""

    def create_components(self) -> None:
        self.t_ampel = Timer()
        self.t_ampel.interval = 50


def test_timer_standardwerte_entsprechen_lazarus() -> None:
    # TTimer: Enabled = True, Interval = 1000.
    zeitgeber = Timer()

    assert zeitgeber.enabled is True
    assert zeitgeber.interval == 1000
    assert zeitgeber._qtimer.interval() == 1000
    assert zeitgeber._qtimer.isActive() is True


def test_timer_interval_wirkt_sofort_auf_den_qtimer() -> None:
    zeitgeber = Timer()

    zeitgeber.interval = 250

    assert zeitgeber._qtimer.interval() == 250
    assert zeitgeber._qtimer.isActive() is True


def test_timer_enabled_false_haelt_ihn_an() -> None:
    zeitgeber = Timer()

    zeitgeber.enabled = False

    assert zeitgeber._qtimer.isActive() is False


def test_timer_laesst_sich_wieder_starten() -> None:
    zeitgeber = Timer()
    zeitgeber.enabled = False

    zeitgeber.enabled = True

    assert zeitgeber._qtimer.isActive() is True


def test_timer_on_timer_feuert_wirklich(qtbot) -> None:
    """Mit echter Ereignisschleife statt eines Aufrufs von Hand - sonst
    bliebe ungeprüft, ob `timeout` überhaupt verbunden ist."""
    zeitgeber = Timer()
    zeitgeber.interval = 20
    empfangen: list[object] = []
    zeitgeber.on_timer = lambda sender: empfangen.append(sender)

    qtbot.waitUntil(lambda: len(empfangen) >= 2, timeout=3000)

    assert empfangen[0] is zeitgeber


def test_angehaltener_timer_feuert_nicht(qtbot) -> None:
    zeitgeber = Timer()
    zeitgeber.interval = 10
    zeitgeber.enabled = False
    empfangen: list[object] = []
    zeitgeber.on_timer = lambda sender: empfangen.append(sender)

    qtbot.wait(120)

    assert empfangen == []


def test_timer_auf_einem_formular(qtbot) -> None:
    formular = _Formular()
    empfangen: list[object] = []
    formular.t_ampel.on_timer = lambda sender: empfangen.append(sender)

    qtbot.waitUntil(lambda: bool(empfangen), timeout=3000)

    assert empfangen[0] is formular.t_ampel


def test_timer_ist_keine_control_komponente() -> None:
    """Bewusst festgehalten: `Timer` ist nicht sichtbar und deshalb -
    wie `SQLite3Connection` & Co. - keine `Control`. Daraus folgt, dass
    der Designer ihn nicht kennt (siehe docs/komponenten.md, „Offene
    Punkte"). Ändert sich das, soll dieser Test daran erinnern, die
    Dokumentation mitzuziehen."""
    zeitgeber = Timer()

    assert not isinstance(zeitgeber, Control)
    assert not hasattr(zeitgeber, "left")


def test_timer_ist_nicht_in_der_palette() -> None:
    from ide.palette.palette import STANDARD_KOMPONENTEN, ZUSAETZLICH_KOMPONENTEN

    assert Timer not in STANDARD_KOMPONENTEN
    assert Timer not in ZUSAETZLICH_KOMPONENTEN


def test_timer_prueft_typen_und_unbekannte_eigenschaften() -> None:
    zeitgeber = Timer()
    with pytest.raises(NatterPropertyError):
        zeitgeber.interval = "schnell"
    with pytest.raises(NatterUnbekannteEigenschaftError):
        zeitgeber.intervall = 100
