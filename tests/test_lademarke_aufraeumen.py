"""Die Markendateien der Ladeanzeige bleiben nicht liegen (Punkt 314).

Ein Konsolenprogramm legt bei seiner ersten Ausgabe eine leere
Markendatei an (Punkt 271). Bis 0.3.6 vergaß das Hauptfenster ihren
Pfad, sobald die Ladeanzeige endete. Schrieb das Programm erst danach
etwas, etwa nach der Zeitgrenze, entstand die Datei trotzdem und blieb
im Temp-Ordner liegen; auf dem Prüfrechner lagen 19 Stück.

Die Programme sind echte Prozesse mit eigenem Konsolenfenster. Der
Ordner der Marken ist auf `tmp_path` umgelenkt.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import pytest

from ide.run import ladeanzeige

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="Konsolenfenster gibt es nur unter Windows"
)

#: Schreibt erst nach der Zeitgrenze und läuft dann weiter.
SPAET_UND_WEITER = """\
import time

time.sleep(2)
print("spät", flush=True)
time.sleep(60)
"""

#: Schreibt erst nach der Zeitgrenze und endet dann ohne die Pause der
#: Hülle.
SPAET_UND_ENDE = """\
import os
import time

time.sleep(2)
print("spät", flush=True)
time.sleep(1.5)
os._exit(0)
"""

#: Endet, ohne etwas auszugeben.
OHNE_AUSGABE = """\
import os
import time

time.sleep(0.5)
os._exit(0)
"""

#: Lädt so lange, dass „Stopp“ während des Ladens kommt.
LANGE_LADEN = """\
import time

time.sleep(60)
"""


def _projekt(ordner: Path, quelltext: str) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(quelltext, encoding="utf-8")
    (ordner / "test.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Marke",
                "type": "console",
                "main": "main.py",
            }
        ),
        encoding="utf-8",
    )
    return ordner / "test.natter"


def _marken(ordner: Path) -> list[str]:
    return sorted(p.name for p in ordner.glob("natter-geladen-*"))


@pytest.fixture
def markenordner(tmp_path: Path, monkeypatch) -> Path:  # noqa: ANN001
    ordner = tmp_path / "temp"
    ordner.mkdir()
    monkeypatch.setattr(ladeanzeige, "lademarken_ordner", lambda: ordner)
    return ordner


@pytest.mark.timeout(180)
@pytest.mark.parametrize(
    ("quelltext", "zeitgrenze", "ende"),
    [
        pytest.param(SPAET_UND_WEITER, True, "stopp", id="zeitgrenze-stopp"),
        pytest.param(SPAET_UND_ENDE, True, "selbst", id="zeitgrenze-ende"),
        pytest.param(OHNE_AUSGABE, False, "selbst", id="ohne-ausgabe"),
        pytest.param(LANGE_LADEN, False, "stopp", id="stopp-beim-laden"),
    ],
)
def test_nach_dem_programm_ist_keine_marke_uebrig(
    hauptfenster,
    qtbot,
    tmp_path: Path,
    markenordner: Path,
    monkeypatch,
    quelltext: str,
    zeitgrenze: bool,
    ende: str,
) -> None:  # noqa: ANN001
    from ide.shell import hauptfenster as modul

    if zeitgrenze:
        monkeypatch.setattr(modul, "_LADE_GRENZE_S", 1)
    fenster = hauptfenster
    fenster.projekt_oeffnen(_projekt(tmp_path / "p", quelltext))

    fenster._projekt_starten_aktion()
    assert fenster.laufender_prozess is not None
    assert fenster.laedt_programm()

    if zeitgrenze:
        qtbot.waitUntil(lambda: not fenster.laedt_programm(), timeout=30_000)
        assert "noch kein Fenster" in fenster.statusBar().currentMessage()
        # Erst nach der Zeitgrenze schreibt das Programm und legt die
        # Marke an.
        qtbot.waitUntil(lambda: bool(_marken(markenordner)), timeout=60_000)

    if ende == "stopp":
        fenster._debugger_stoppen_aktion()
        assert fenster.laufender_prozess is None
    else:
        qtbot.waitUntil(
            lambda: fenster.laufender_prozess is None, timeout=60_000
        )

    assert not fenster.laedt_programm()
    assert _marken(markenordner) == []


def test_beim_start_verschwinden_nur_alte_marken(
    markenordner: Path,
) -> None:
    alt = markenordner / "natter-geladen-alt"
    jung = markenordner / "natter-geladen-jung"
    fremd = markenordner / "etwas-anderes"
    for datei in (alt, jung, fremd):
        datei.write_bytes(b"")
    vor_zwei_tagen = time.time() - 2 * 24 * 60 * 60
    os.utime(alt, (vor_zwei_tagen, vor_zwei_tagen))
    os.utime(fremd, (vor_zwei_tagen, vor_zwei_tagen))

    assert ladeanzeige.alte_lademarken_entfernen() == 1

    assert not alt.exists()
    assert jung.exists(), "Eine junge Marke kann einem laufenden Natter gehören."
    assert fremd.exists()
