"""Die Wache für lange Läufe (`tools/wache.py`) erkennt verwaiste und
hängende Prozesse, stille Arbeitsbäume und die Entpackordner alter
Starter."""

from __future__ import annotations

import os
import time

from tools import wache
from tools.wache import Prozess


def _p(pid, eltern, name, befehl, minuten=1.0) -> Prozess:  # noqa: ANN001
    return Prozess(pid=pid, eltern=eltern, name=name, befehl=befehl, minuten=minuten)


REPO = str(wache.WURZEL)


def test_ein_prozess_ohne_elternteil_ist_verwaist() -> None:
    prozesse = [_p(10, 999, "python.exe", f"{REPO}\\.venv\\Scripts\\python.exe x.py")]

    befunde = wache.prozesse_bewerten(prozesse, lebend={10}, eigene=set())

    assert [b.art for b in befunde] == ["verwaist"]
    assert befunde[0].pid == 10


def test_fremde_prozesse_zaehlen_nicht() -> None:
    prozesse = [_p(10, 999, "python.exe", r"C:\anderes\programm.py", minuten=500)]

    assert wache.prozesse_bewerten(prozesse, lebend={10}, eigene=set()) == []


def test_ein_wartender_debugger_haengt_nach_fuenf_minuten() -> None:
    befehl = f"{REPO}\\.venv\\Scripts\\python.exe -m debugpy --listen 5678 --wait-for-client a.py"
    frisch = [_p(10, 1, "python.exe", befehl, minuten=2)]
    alt = [_p(10, 1, "python.exe", befehl, minuten=12)]

    assert wache.prozesse_bewerten(frisch, lebend={1, 10}, eigene=set()) == []
    assert [b.art for b in wache.prozesse_bewerten(alt, lebend={1, 10}, eigene=set())] == [
        "hängend"
    ]


def test_eine_alte_warteschleife_haengt() -> None:
    befehl = f'bash -c "until grep -q passed {REPO}\\x.txt; do sleep 3; done"'
    prozesse = [_p(20, 1, "bash.exe", befehl, minuten=45)]

    befunde = wache.prozesse_bewerten(prozesse, lebend={1, 20}, eigene=set())

    assert [b.art for b in befunde] == ["hängend"]


def test_die_wache_selbst_zaehlt_nie() -> None:
    prozesse = [_p(30, 999, "python.exe", f"{REPO}\\.venv\\Scripts\\python.exe -m tools.wache")]

    assert wache.prozesse_bewerten(prozesse, lebend={30}, eigene={30}) == []


def test_ein_stiller_arbeitsbaum_wird_gemeldet(tmp_path) -> None:
    baeume = tmp_path / "worktrees"
    aktiv = baeume / "agent-aktiv"
    still = baeume / "agent-still"
    for ordner in (aktiv, still):
        ordner.mkdir(parents=True)
        (ordner / "datei.py").write_text("x = 1\n", encoding="utf-8")
    vor_einer_stunde = time.time() - 3600
    os.utime(still / "datei.py", (vor_einer_stunde, vor_einer_stunde))
    # Eine frisch geänderte Datei in .venv zählt nicht als Arbeit.
    (still / ".venv").mkdir()
    (still / ".venv" / "neu.txt").write_text("", encoding="utf-8")

    befunde, _ = wache.arbeitsbaeume_bewerten(baeume, still_minuten=10)

    assert [b.text.split()[1] for b in befunde] == ["agent-still"]


def test_ein_alter_probeordner_wird_gemeldet(tmp_path) -> None:
    alt = tmp_path / "natter_probe_alt"
    neu = tmp_path / "natter_probe_neu"
    alt.mkdir()
    neu.mkdir()
    vor_drei_stunden = time.time() - 3 * 3600
    os.utime(alt, (vor_drei_stunden, vor_drei_stunden))

    befunde = wache.probeordner_bewerten(tmp_path)

    assert len(befunde) == 1
    assert "natter_probe_alt" in befunde[0].text

def _entpackt(temp, name, alter_minuten, fremd=False):  # noqa: ANN001, ANN202
    ordner = temp / name
    ordner.mkdir()
    (ordner / "python313.dll").write_bytes(b"MZ" * 3)
    (ordner / "base_library.zip").write_bytes(b"PK")
    if fremd:
        # Eine exportierte Schüler-Exe bringt mehr mit, etwa PySide6.
        (ordner / "PySide6").mkdir()
        (ordner / "PySide6" / "QtCore.pyd").write_bytes(b"MZ")
    zeit = time.time() - alter_minuten * 60
    os.utime(ordner, (zeit, zeit))
    return ordner


def test_nur_alte_entpackordner_eines_natter_starters_werden_entfernt(
    tmp_path,  # noqa: ANN001
) -> None:
    """Punkt 399: ein hart beendeter Einzeldatei-Starter ließ je rund
    18 MB in `%TEMP%\\_MEI…` zurück. Die Wache entfernt nur Ordner,
    deren Inhalt genau dem eines Natter-Starters entspricht, die älter
    als eine Stunde sind und deren Python kein laufender Starter mehr
    geladen hat. Ein Ordner einer fremden Exe bleibt, auch wenn er alt
    ist."""
    natter = {"python313.dll": 6, "base_library.zip": 2}
    alt = _entpackt(tmp_path, "_MEI1001", 120)
    frisch = _entpackt(tmp_path, "_MEI1002", 5)
    fremd = _entpackt(tmp_path, "_MEI1003", 120, fremd=True)
    belegt = _entpackt(tmp_path, "_MEI1004", 120)

    befunde = wache.entpackordner_bewerten(tmp_path, [natter])
    assert sorted(b.ordner.name for b in befunde) == ["_MEI1001", "_MEI1004"]
    assert wache.entpackordner_bewerten(tmp_path, []) == []

    # Eine geöffnete DLL lässt sich unter Windows nicht löschen, wie
    # die geladene eines laufenden Starters.
    with (belegt / "python313.dll").open("rb"):
        zeilen = wache.aufraeumen(wache.Bericht(befunde=befunde))

    assert not alt.exists()
    assert frisch.exists() and fremd.exists()
    assert (belegt / "base_library.zip").is_file()
    assert any(z.startswith("in Gebrauch") and "_MEI1004" in z for z in zeilen)


def test_ohne_eingepackte_dateien_gibt_es_keinen_starterinhalt(
    tmp_path,  # noqa: ANN001
) -> None:
    """Ein Ordner-Starter wie `Natter.exe` seit Punkt 399 und jede
    andere Datei ohne Archiv von PyInstaller entpacken nichts."""
    import sys
    from pathlib import Path

    keine = tmp_path / "Natter.exe"
    keine.write_bytes(b"MZ kein Archiv")

    assert wache.starter_inhalt(keine) is None
    assert wache.starter_inhalt(Path(sys.executable)) is None
