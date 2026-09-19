"""Natter benutzt seine eigene Python - und nur die (M13).

Auf einem Rechner, auf dem schon mit Python gearbeitet wurde, stehen
Umgebungsvariablen herum, die auf eine **andere** Installation zeigen.
Die unauffälligste davon ist `PYTHONUSERBASE`: aus ihr rechnet *jede*
Python 3.13 ihr Benutzer-Paketverzeichnis aus, auch eine frisch
ausgepackte. Die sieht dann die Pakete des fremden Rechners als ihre
eigenen.

Beim Bau der Auslieferung hat genau das zugeschlagen. `pip` meldete
Zeile für Zeile „Requirement already satisfied", installierte nur
Natter selbst und gab 0 zurück - der Bau lief fehlerfrei durch. In der
fertigen Auslieferung fehlten `ruff`, `scipy`, `scikit-learn`,
`cryptography`, `setuptools` und ein Dutzend weiterer Pakete, und damit
die Prüfung vor dem Start, die Integritätsprüfung und der Exe-Export.
Gemerkt hat es niemand, bis die Pakete in `dist` nachgezählt wurden.

Dieselbe Falle steht auf dem Schulrechner: findet die ausgelieferte
Python dort eine fremde PySide6-Fassung, geht Natter auf einem Rechner
kaputt, an dem nie jemand etwas geändert hat. Deshalb prüft dieser Test
**beide** Seiten - den Bau und den Starter.
"""

from __future__ import annotations

import pytest

from tools.ide_paketieren import _saubere_umgebung
from tools.launcher import eigene_umgebung

#: Alle zeigen auf eine fremde Python-Installation.
FREMDE = ("PYTHONPATH", "PYTHONHOME", "PYTHONUSERBASE", "VIRTUAL_ENV")

#: Beide Seiten müssen dasselbe tun; der Test beschreibt sie gemeinsam.
UMGEBUNGEN = {"Bau": _saubere_umgebung, "Starter": eigene_umgebung}


@pytest.fixture
def verseuchte_umgebung(monkeypatch: pytest.MonkeyPatch) -> None:
    """So sieht die Umgebung auf einem Rechner aus, auf dem schon eine
    andere Python steht."""
    for name in FREMDE:
        monkeypatch.setenv(name, r"C:\woanders")
    monkeypatch.setenv("PATH", r"C:\Windows\system32")


@pytest.mark.parametrize("seite", sorted(UMGEBUNGEN))
@pytest.mark.parametrize("name", FREMDE)
def test_der_verweis_auf_fremdes_python_faellt_weg(
    seite: str, name: str, verseuchte_umgebung: None
) -> None:
    assert name not in UMGEBUNGEN[seite](), (
        f"{name} zeigt auf eine fremde Python-Installation und darf "
        f"({seite}) nicht durchgereicht werden."
    )


@pytest.mark.parametrize("seite", sorted(UMGEBUNGEN))
def test_das_benutzerverzeichnis_ist_abgeschaltet(seite: str, verseuchte_umgebung: None) -> None:
    """`PYTHONUSERBASE` zu löschen genügt nicht: das
    Benutzer-Paketverzeichnis hat auch ohne sie einen Vorgabewert."""
    assert UMGEBUNGEN[seite]().get("PYTHONNOUSERSITE") == "1"


@pytest.mark.parametrize("seite", sorted(UMGEBUNGEN))
def test_der_rest_der_umgebung_bleibt(seite: str, verseuchte_umgebung: None) -> None:
    """Nur die vier Verweise sollen weg. `PATH`, Proxy-Einstellungen
    und was die Schule sonst setzt, werden gebraucht - unter anderem
    damit Nachinstallieren über das Menü „Pakete" funktioniert."""
    assert UMGEBUNGEN[seite]()["PATH"] == r"C:\Windows\system32"
