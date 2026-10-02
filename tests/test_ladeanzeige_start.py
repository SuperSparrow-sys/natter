"""Die Ladeanzeige zwischen Start und erstem Fenster (Punkt 271).

Bis 0.3.6 stand nach F5 nur „… gestartet“ in der Statusleiste, bis
das Programmfenster erschien. Bei einem Programm, das lange lädt, sah
das aus, als sei nichts passiert, und wer ungeduldig war, startete ein
zweites Mal.

Die Programme hier sind echte Python-Prozesse (`subprocess.Popen` im
Starter), die absichtlich langsam starten. Das Programm mit Fenster
stellt die Qt-Plattform für sich auf „windows“ zurück: unter
„offscreen“ entstünde kein Fenster, das Windows kennt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from ide.run.ladeanzeige import hat_sichtbares_fenster

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="Fenster werden über Windows gefunden"
)

LANGSAMES_FENSTER = """\
import os
import time

from PySide6.QtWidgets import QApplication, QLabel

os.environ["QT_QPA_PLATFORM"] = "windows"
time.sleep(2)
anwendung = QApplication([])
schild = QLabel("geladen")
schild.show()
anwendung.exec()
"""

OHNE_FENSTER = """\
import time

time.sleep(1.5)
"""

LANGSAME_KONSOLE = """\
import time

time.sleep(2)
print("fertig geladen")
"""


def _projekt(ordner: Path, quelltext: str, typ: str = "gui") -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(quelltext, encoding="utf-8")
    (ordner / "test.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Langsam",
                "type": typ,
                "main": "main.py",
            }
        ),
        encoding="utf-8",
    )
    return ordner / "test.natter"


def _anzeige_sichtbar(fenster) -> bool:  # noqa: ANN001
    anzeige = fenster._lade_anzeige
    return anzeige is not None and not anzeige.isHidden()


def test_die_anzeige_laeuft_bis_zum_ersten_fenster(
    hauptfenster, qtbot, tmp_path: Path
) -> None:  # noqa: ANN001
    fenster = hauptfenster
    fenster.projekt_oeffnen(_projekt(tmp_path / "p", LANGSAMES_FENSTER))

    fenster._projekt_starten_aktion()
    prozess = fenster.laufender_prozess
    assert prozess is not None
    assert fenster.laedt_programm()
    assert _anzeige_sichtbar(fenster)
    assert fenster._lade_text.text().startswith("Programm wird geladen … ")
    assert fenster._lade_text.text().endswith(" s")

    # Ein zweiter Start während des Ladens startet nichts.
    fenster._projekt_starten_aktion()
    assert fenster.laufender_prozess is prozess
    assert "wird noch geladen" in fenster.statusBar().currentMessage()

    qtbot.waitUntil(lambda: not fenster.laedt_programm(), timeout=60_000)

    assert not _anzeige_sichtbar(fenster)
    assert prozess.poll() is None, "Das Programm hätte noch laufen sollen."
    assert hat_sichtbares_fenster(prozess.pid)


def test_mit_debugger_laeuft_die_anzeige_ebenso(
    hauptfenster, qtbot, tmp_path: Path
) -> None:  # noqa: ANN001
    """F5: der Prozess entsteht erst im Nebenfaden der Sitzung; bis
    dahin zählt die Anzeige schon."""
    fenster = hauptfenster
    fenster.projekt_oeffnen(_projekt(tmp_path / "p", LANGSAMES_FENSTER))

    fenster._projekt_mit_debugger_starten_aktion()
    assert fenster.laedt_programm()

    fenster._projekt_mit_debugger_starten_aktion()
    assert "läuft bereits" in fenster.statusBar().currentMessage()

    qtbot.waitUntil(lambda: not fenster.laedt_programm(), timeout=60_000)

    prozess = fenster.debug_sitzung.client.prozess
    assert prozess.poll() is None
    assert hat_sichtbares_fenster(prozess.pid)


def test_ein_zweites_f5_startet_auch_den_debugger_nicht(
    hauptfenster, tmp_path: Path
) -> None:  # noqa: ANN001
    fenster = hauptfenster
    fenster.projekt_oeffnen(_projekt(tmp_path / "p", LANGSAMES_FENSTER))

    fenster._projekt_starten_aktion()
    assert fenster.laedt_programm()

    fenster._projekt_mit_debugger_starten_aktion()

    assert fenster.debug_sitzung is None
    assert "wird noch geladen" in fenster.statusBar().currentMessage()


def test_endet_das_programm_vorher_verschwindet_die_anzeige(
    hauptfenster, qtbot, tmp_path: Path
) -> None:  # noqa: ANN001
    fenster = hauptfenster
    fenster.projekt_oeffnen(_projekt(tmp_path / "p", OHNE_FENSTER))

    fenster._projekt_starten_aktion()
    assert fenster.laedt_programm()

    qtbot.waitUntil(lambda: not fenster.laedt_programm(), timeout=60_000)
    assert not _anzeige_sichtbar(fenster)
    qtbot.waitUntil(lambda: fenster.laufender_prozess is None, timeout=10_000)


def test_ein_konsolenprogramm_laedt_bis_zur_ersten_ausgabe(
    hauptfenster, qtbot, tmp_path: Path
) -> None:  # noqa: ANN001
    """Das Konsolenfenster ist sofort da und zählt nicht; die Anzeige
    endet mit der ersten Zeile, die das Programm schreibt."""
    fenster = hauptfenster
    fenster.projekt_oeffnen(
        _projekt(tmp_path / "k", LANGSAME_KONSOLE, typ="console")
    )

    fenster._projekt_starten_aktion()
    prozess = fenster.laufender_prozess
    marke = fenster._lademarke
    assert marke is not None
    qtbot.wait(1000)
    assert fenster.laedt_programm(), "Die Anzeige endete vor der ersten Ausgabe."

    qtbot.waitUntil(lambda: not fenster.laedt_programm(), timeout=60_000)

    # Die Hülle wartet nach dem Programm auf die Eingabetaste; das
    # Programm läuft also noch, und die Anzeige endete wegen der
    # Ausgabe, nicht wegen des Programmendes.
    assert prozess.poll() is None
    assert not marke.exists(), "Die Marke bleibt nicht im Temp-Ordner liegen."


def test_ein_fertiges_konsolenprogramm_haelt_den_naechsten_start_nicht_auf(
    hauptfenster, qtbot, tmp_path: Path
) -> None:  # noqa: ANN001
    """Nach dem Programmende wartet das Konsolenfenster auf die
    Eingabetaste, der Prozess lebt also noch. Natter lehnte den
    nächsten Start mit „läuft bereits“ ab. Ein Programm, das wirklich
    noch läuft, wird weiter abgelehnt."""
    fenster = hauptfenster
    fenster.projekt_oeffnen(
        _projekt(tmp_path / "k", 'print("fertig")\n', typ="console")
    )

    fenster._projekt_starten_aktion()
    erster = fenster.laufender_prozess
    qtbot.waitUntil(fenster._programm_wartet_nur_noch, timeout=60_000)
    qtbot.waitUntil(
        lambda: any(
            "wartet auf die Eingabetaste" in fenster.ausgabe_liste.item(i).text()
            for i in range(fenster.ausgabe_liste.count())
        ),
        timeout=5_000,
    )
    assert erster.poll() is None

    fenster._projekt_starten_aktion()

    assert fenster.laufender_prozess is not erster
    assert fenster.laufender_prozess is not None
    erster.wait(timeout=10)


def test_ein_laufendes_konsolenprogramm_wird_weiter_abgelehnt(
    hauptfenster, qtbot, tmp_path: Path
) -> None:  # noqa: ANN001
    fenster = hauptfenster
    fenster.projekt_oeffnen(
        _projekt(tmp_path / "k", "import time\ntime.sleep(30)\n", typ="console")
    )

    fenster._projekt_starten_aktion()
    erster = fenster.laufender_prozess
    qtbot.wait(500)
    fenster._projekt_starten_aktion()

    assert fenster.laufender_prozess is erster
    assert "läuft bereits" in fenster.statusBar().currentMessage()


def test_eine_einzelne_datei_ohne_projekt_laesst_sich_starten(
    hauptfenster, qtbot, tmp_path: Path
) -> None:  # noqa: ANN001
    """Eine Aufgabe als einzelne `aufgabe.py`: F5 und Strg+F5 meldeten
    nur „Kein Projekt offen“. Im Ordner entsteht dabei nichts."""
    fenster = hauptfenster
    aufgabe = tmp_path / "aufgabe.py"
    aufgabe.write_text("open('lief.txt', 'w').write('ja')\n", encoding="utf-8")
    fenster.datei_oeffnen(aufgabe)
    assert fenster.projekt is None

    fenster._mit_debugger_starten()

    assert fenster.laufender_prozess is not None
    assert "ohne Debugger" in fenster.statusBar().currentMessage()
    qtbot.waitUntil(fenster._programm_wartet_nur_noch, timeout=60_000)
    assert (tmp_path / "lief.txt").read_text() == "ja"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["aufgabe.py", "lief.txt"]


def test_strg_f5_mit_haltepunkt_sagt_dass_er_nicht_wirkt(
    hauptfenster, qtbot, tmp_path: Path
) -> None:  # noqa: ANN001
    """Das schlichte grüne Dreieck startet ohne Debugger; ein gesetzter
    Haltepunkt schien dann kaputt (Punkt 464). Die beiden Ordner der
    Werkzeugleiste sind seither auch verschiedene Bilder."""
    fenster = hauptfenster
    fenster.projekt_oeffnen(
        _projekt(tmp_path / "k", "x = 1\nprint(x)\n", typ="console")
    )
    editor = fenster.datei_oeffnen(tmp_path / "k" / "main.py")
    editor.breakpoints = {1}

    fenster._projekt_starten_aktion()

    assert "Haltepunkte wirken nur" in fenster.statusBar().currentMessage()
    oeffnen = fenster.aktionen["datei.oeffnen"].symbol
    projekt = fenster.aktionen["projekt.oeffnen"].symbol
    ordner = Path(__file__).resolve().parent.parent / "ide" / "assets" / "icons"
    assert (ordner / f"{oeffnen}.svg").read_text(encoding="utf-8") != (
        ordner / f"{projekt}.svg"
    ).read_text(encoding="utf-8")
    assert "Blatt" in (ordner / f"{oeffnen}.svg").read_text(encoding="utf-8")

