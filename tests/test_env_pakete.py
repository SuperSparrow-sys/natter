"""Tests für die Paketverwaltung (Abschnitt 7.2, 18). Siehe
Arbeitspaket M7, Schritt 3. `subprocess.run` wird gemockt -
echte `pip`-Aufrufe (Netzwerk/Installation) gehören nicht in die
automatisierte Testsuite.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

from ide.env import PaketFehler, installierte_pakete, paket_installieren, paketliste_exportieren


def _ergebnis(
    *, stdout: str = "", stderr: str = "", returncode: int = 0
) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_installierte_pakete_parst_echte_pip_list_json_ausgabe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pip_ausgabe = '[{"name": "pytest", "version": "8.0.0"}, {"name": "ruff", "version": "0.8.1"}]'
    monkeypatch.setattr(
        "ide.env.pakete.subprocess.run", lambda *a, **k: _ergebnis(stdout=pip_ausgabe)
    )

    pakete = installierte_pakete()

    assert pakete[0].name == "pytest"
    assert pakete[0].version == "8.0.0"
    assert pakete[1].name == "ruff"


def test_installierte_pakete_bei_pip_fehler_loest_paketfehler_statt_abzustuerzen(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Echter Absturz: `check=True` ließ eine
 unbehandelte `subprocess.CalledProcessError` bis zur IDE
 durchschlagen, wenn `pip list` fehlschlug - jetzt wie
 `paket_installieren` ein sauberer `PaketFehler`."""
    monkeypatch.setattr(
        "ide.env.pakete.subprocess.run",
        lambda *a, **k: _ergebnis(returncode=1, stderr="ERROR: pip ist kaputt"),
    )

    with pytest.raises(PaketFehler, match="pip ist kaputt"):
        installierte_pakete()


def test_paket_installieren_ruft_pip_install_mit_dem_richtigen_namen_auf(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    aufgerufen = []

    def fake_run(befehl, **kwargs):
        aufgerufen.append(befehl)
        return _ergebnis(stdout="Successfully installed requests-2.31.0")

    monkeypatch.setattr("ide.env.pakete.subprocess.run", fake_run)

    ausgabe = paket_installieren("requests")

    assert aufgerufen[0][3] == "install"
    assert aufgerufen[0][-1] == "requests"
    assert "Successfully installed" in ausgabe


_OHNE_VERBINDUNG = (
    "WARNING: Retrying (Retry(total=0, connect=None, read=None, "
    "redirect=None, status=None)) after connection broken by "
    "'ConnectTimeoutError(<HTTPSConnection(host='192.0.2.1', port=9) "
    "at 0x1>, 'Connection to 192.0.2.1 timed out. (connect "
    "timeout=5.0)')': /simple/nicht-da/\n"
    "ERROR: Could not find a version that satisfies the requirement "
    "nicht-da (from versions: none)\n"
    "ERROR: No matching distribution found for nicht-da\n"
)
_UNBEKANNT = (
    "ERROR: Could not find a version that satisfies the requirement "
    "nicht-da (from versions: none)\n"
    "ERROR: No matching distribution found for nicht-da\n"
)


@pytest.mark.parametrize(
    ("stderr", "erwartet"),
    [
        (_OHNE_VERBINDUNG, "Keine Verbindung zum Paketverzeichnis"),
        (_UNBEKANNT, "gibt es im Paketverzeichnis nicht"),
    ],
    ids=["ohne_verbindung", "unbekannter_name"],
)
def test_paket_installieren_meldet_den_grund_auf_deutsch(
    monkeypatch: pytest.MonkeyPatch, stderr: str, erwartet: str
) -> None:
    """Punkt 424: ohne Verbindung endete die Meldung mit „No matching
    distribution found“, als wäre der Name falsch. Beide Fälle haben
    jetzt einen eigenen deutschen Satz, und die Ausgabe von `pip`
    steht getrennt davon."""
    monkeypatch.setattr(
        "ide.env.pakete.subprocess.run",
        lambda *a, **k: _ergebnis(returncode=1, stderr=stderr),
    )

    with pytest.raises(PaketFehler) as fehler:
        paket_installieren("nicht-da")

    assert erwartet in str(fehler.value)
    assert "„nicht-da“" in str(fehler.value)
    assert "ERROR" not in str(fehler.value)
    assert "No matching distribution" in fehler.value.rohausgabe


@pytest.mark.timeout(90)
def test_ohne_netz_endet_die_installation_bald_mit_deutscher_meldung(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Punkt 424: hinter einem Proxy, der nicht antwortet, brauchte
    `pip` mit seinen Vorgaben 106 Sekunden. Der Proxy steht hier auf
    192.0.2.1, einer Adresse, die für Dokumentation reserviert ist und
    nirgends hinführt; ins Netz geht der Test also nicht. Eine eigene
    Grenze beendet `pip`, falls es doch länger braucht, damit kein
    Prozess übrig bleibt."""
    proxy = "http://192.0.2.1:9"
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
        monkeypatch.setenv(name, proxy)
    for name in ("NO_PROXY", "no_proxy", "PIP_INDEX_URL", "PIP_PROXY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PIP_CONFIG_FILE", os.devnull)

    echt = subprocess.run

    def mit_grenze(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        return echt(*args, **{**kwargs, "timeout": 45})

    monkeypatch.setattr("ide.env.pakete.subprocess.run", mit_grenze)

    beginn = time.monotonic()
    with pytest.raises(PaketFehler) as fehler:
        paket_installieren("natter-gibt-es-nicht-424")
    dauer = time.monotonic() - beginn

    assert "Keine Verbindung zum Paketverzeichnis" in str(fehler.value)
    assert dauer < 30, f"{dauer:.0f} Sekunden"


def test_paketliste_exportieren_bei_pip_fehler_loest_paketfehler_aus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "ide.env.pakete.subprocess.run",
        lambda *a, **k: _ergebnis(returncode=1, stderr="ERROR: pip ist kaputt"),
    )

    with pytest.raises(PaketFehler, match="pip ist kaputt"):
        paketliste_exportieren(tmp_path / "requirements.txt")


def test_paketliste_exportieren_schreibt_pip_freeze_ausgabe(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pip_ausgabe = "pandas==2.2.0\nnumpy==1.26.0\n"
    monkeypatch.setattr(
        "ide.env.pakete.subprocess.run", lambda *a, **k: _ergebnis(stdout=pip_ausgabe)
    )
    ziel = tmp_path / "requirements.txt"

    paketliste_exportieren(ziel)

    assert ziel.read_text(encoding="utf-8") == pip_ausgabe
