"""Punkt 278: „Start → Stopp“ und das Schließen von Natter beenden
auch, was das Programm selbst gestartet hat.

Bis 0.3.6 trafen beide mit `Popen.kill()` nur den einen Prozess des
Programms. Ein über `os.system` gestarteter Prozess lief weiter,
hielt das Rohr zum Panel „Ausgabe“ offen, und der `AusgabeLeser` las
weiter. Ging das Hauptfenster in diesem Zustand zu, endete Natter mit
`0xC0000409`, weil ein noch laufender `QThread` zerstört wurde.

Punkt 281: dasselbe, wenn das Programm selbst schon zu Ende ist und
nur sein Enkel noch lebt. `taskkill /T` findet ihn dann nicht mehr;
erst das Auftragsobjekt, in dem das Programm läuft, erreicht ihn.
"""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

#: Startet `enkel.py` über die Eingabeaufforderung und wartet darauf.
#: Die äußeren Anführungszeichen braucht `cmd /c`, sobald der Befehl
#: selbst mit einem Anführungszeichen beginnt.
_PROGRAMM_MIT_OS_SYSTEM = """\
import os
import sys
from pathlib import Path

enkel = Path(__file__).with_name("enkel.py")
print("gestartet", flush=True)
os.system(f'""{sys.executable}" "{enkel}""')
"""

#: Startet `enkel.py` und endet sofort. Der Enkel erbt das Rohr zum
#: Panel „Ausgabe“ und hält es offen, obwohl das Programm schon zu
#: Ende ist.
_PROGRAMM_OHNE_WARTEN = """\
import subprocess
import sys
from pathlib import Path

enkel = Path(__file__).with_name("enkel.py")
print("gestartet", flush=True)
subprocess.Popen([sys.executable, str(enkel)])
"""

_ENKEL = """\
import os
import time
from pathlib import Path

ziel = Path(__file__).with_name("enkel.pid")
zwischen = ziel.with_suffix(".tmp")
zwischen.write_text(str(os.getpid()), encoding="utf-8")
os.replace(zwischen, ziel)
print("enkel laeuft", flush=True)
time.sleep(120)
"""


def _projekt_anlegen(ordner: Path, programm: str) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(programm, encoding="utf-8")
    (ordner / "enkel.py").write_text(_ENKEL, encoding="utf-8")
    daten = {
        "format": "natter-project/1",
        "name": "Enkel",
        "type": "gui",
        "main": "main.py",
    }
    pfad = ordner / "enkel.natter"
    pfad.write_text(json.dumps(daten), encoding="utf-8")
    return pfad


def _prozess_lebt(pid: int) -> bool:
    kernel32 = ctypes.windll.kernel32
    griff = kernel32.OpenProcess(0x1000, False, pid)
    if not griff:
        return False
    try:
        code = ctypes.c_ulong()
        kernel32.GetExitCodeProcess(griff, ctypes.byref(code))
        return code.value == 259  # STILL_ACTIVE
    finally:
        kernel32.CloseHandle(griff)


def _enkel_abwarten(ordner: Path, zeitlimit: float = 30.0) -> int:
    datei = ordner / "enkel.pid"
    ende = time.monotonic() + zeitlimit
    while time.monotonic() < ende:
        QApplication.processEvents()
        try:
            return int(datei.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            time.sleep(0.05)
    raise AssertionError("Der Enkelprozess ist nie angelaufen")


def _verschwunden(pid: int, zeitlimit: float = 10.0) -> bool:
    ende = time.monotonic() + zeitlimit
    while time.monotonic() < ende:
        if not _prozess_lebt(pid):
            return True
        time.sleep(0.1)
    return False


def _aufraeumen(pid: int | None) -> None:
    """Hinterlässt auch bei einem Fehlschlag keinen Prozess."""
    if pid is not None and _prozess_lebt(pid):
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/T", "/F"],
            capture_output=True,
            check=False,
            timeout=30,
        )


pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="prüft Windows-Prozesse"
)

#: Der Interpreter hinter dem der virtuellen Umgebung. Deren
#: `python.exe` ist unter uv nur ein Starter, der den eigentlichen
#: Interpreter in einem Job-Objekt startet; wer den Starter beendet,
#: beendet damit alles darunter. Die gebaute Natter startet den
#: Interpreter direkt, und nur so zeigt sich, was `kill()` stehen
#: lässt.
_INTERPRETER = getattr(sys, "_base_executable", sys.executable)


def _programmende_abwarten(fenster, prozess: subprocess.Popen) -> None:
    """Wartet, bis das Programm zu Ende ist und das Hauptfenster das
    bemerkt hat."""
    prozess.wait(30)
    ende = time.monotonic() + 30
    while fenster.laufender_prozess is not None:
        assert time.monotonic() < ende, "Das Programmende blieb unbemerkt."
        QApplication.processEvents()
        time.sleep(0.05)


@pytest.mark.parametrize("weg", ["stopp", "schliessen"])
@pytest.mark.parametrize(
    ("fall", "programm"),
    [
        ("wartend", _PROGRAMM_MIT_OS_SYSTEM),
        ("vorzeitig", _PROGRAMM_OHNE_WARTEN),
    ],
    ids=["wartend", "vorzeitig"],
)
def test_stopp_und_schliessen_beenden_den_enkel(
    tmp_path: Path,
    hauptfenster,
    weg: str,
    fall: str,
    programm: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`vorzeitig`: das Programm ist schon zu Ende, bevor „Stopp“
    kommt; nur sein Enkel lebt noch (Punkt 281)."""
    import ide.run.starter as starter

    monkeypatch.setattr(starter, "python_befehl", lambda: [_INTERPRETER])
    fenster = hauptfenster
    fenster.projekt_oeffnen(_projekt_anlegen(tmp_path / "p", programm))
    fenster._projekt_starten_aktion()
    prozess = fenster.laufender_prozess
    assert prozess is not None, fenster.statusBar().currentMessage()
    enkel: int | None = None
    try:
        enkel = _enkel_abwarten(tmp_path / "p")
        leser = fenster._ausgabe_leser
        assert leser is not None
        if fall == "vorzeitig":
            _programmende_abwarten(fenster, prozess)
            assert _prozess_lebt(enkel)

        if weg == "stopp":
            fenster._debugger_stoppen_aktion()
        else:
            fenster.kindprozesse_beenden()

        prozess.wait(10)
        assert _verschwunden(enkel), "Der Enkelprozess läuft noch."
        assert leser.wait(5000), "Der Leser liest noch."
        assert fenster._ausgabe_leser is None or not leser.laeuft()
    finally:
        _aufraeumen(enkel)
        if prozess.poll() is None:
            prozess.kill()
        prozess.wait(10)


_SKRIPT = """\
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication

ordner = Path(sys.argv[1])
heim = Path(sys.argv[2])
QSettings.setDefaultFormat(QSettings.Format.IniFormat)
QSettings.setPath(
    QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(heim)
)
Path.home = staticmethod(lambda: heim)

import ide.pfade
import pcl.pruefungsmodus

ide.pfade.dokumente_ordner = lambda: heim / "Dokumente"
pcl.pruefungsmodus._weitere_ablagen = lambda: []

import ide.run.starter

ide.run.starter.python_befehl = lambda: [sys.argv[3]]

from ide.shell.hauptfenster import HauptFenster

# Das Programm läuft beim Schließen noch, und Natter fragt, ob es
# enden soll (Punkt 433). Ohne Antwort wartete die Frage in diesem
# Prozess auf einen Klick, der nie kommt. Die Antwort ist „Beenden und
# schließen“; geprüft wird, was danach vom Programm übrig bleibt.
HauptFenster._laufendes_programm_fragen = lambda self: True


def main():
    # Wie in `ide/main.py`: das Fenster ist eine lokale Variable und
    # verschwindet mit dem Ende von `main()` samt allem, was an ihm
    # hängt.
    app = QApplication([])
    fenster = HauptFenster()
    fenster.show()
    fenster.projekt_oeffnen(ordner / "enkel.natter")
    fenster._projekt_starten_aktion()

    def pruefen():
        if (ordner / "enkel.pid").is_file() and (
            ordner.name != "vorzeitig" or fenster.laufender_prozess is None
        ):
            fenster.close()
            app.quit()
        else:
            QTimer.singleShot(50, pruefen)

    QTimer.singleShot(50, pruefen)
    return app.exec()


sys.exit(main())
"""


@pytest.mark.parametrize(
    ("fall", "programm"),
    [
        ("wartend", _PROGRAMM_MIT_OS_SYSTEM),
        ("vorzeitig", _PROGRAMM_OHNE_WARTEN),
    ],
)
def test_natter_endet_beim_schliessen_ohne_fehlercode(
    tmp_path: Path, fall: str, programm: str
) -> None:
    """Die Prüfung aus „Zu tun“ in einem eigenen Prozess.

    `wartend`: das Programm wartet auf seinen Enkel; beide sind nach
    dem Schließen weg. `vorzeitig`: das Programm ist schon zu Ende,
    nur sein Enkel hält das Rohr noch. Über den Baum kommt Natter an
    ihn nicht mehr heran, über das Auftragsobjekt schon (Punkt 281);
    bis dahin las der Leser weiter und durfte nur das Ende von
    Natter nicht aufhalten."""
    projekt = tmp_path / fall
    _projekt_anlegen(projekt, programm)
    heim = tmp_path / "heim"
    heim.mkdir()
    skript = tmp_path / "schliessen.py"
    skript.write_text(textwrap.dedent(_SKRIPT), encoding="utf-8")
    umgebung = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    wurzel = Path(__file__).resolve().parents[1]
    umgebung["PYTHONPATH"] = str(wurzel)

    enkel: int | None = None
    try:
        lauf = subprocess.run(
            [
                sys.executable,
                str(skript),
                str(projekt),
                str(heim),
                _INTERPRETER,
            ],
            cwd=wurzel,
            env=umgebung,
            capture_output=True,
            timeout=120,
            check=False,
        )
        enkel = int((projekt / "enkel.pid").read_text(encoding="utf-8"))
        assert lauf.returncode == 0, (
            f"Rückgabewert {lauf.returncode:#x}: "
            + lauf.stderr.decode(errors="replace")
        )
        assert _verschwunden(enkel), "Der Enkelprozess läuft noch."
    finally:
        if enkel is None:
            try:
                enkel = int(
                    (projekt / "enkel.pid").read_text(encoding="utf-8")
                )
            except (OSError, ValueError):
                pass
        _aufraeumen(enkel)


@pytest.mark.parametrize("konsole", [False, True])
def test_prozessbaum_beenden_erreicht_den_enkel_eines_beendeten_programms(
    tmp_path: Path, konsole: bool
) -> None:
    """Punkt 281 ohne Hauptfenster, einmal auch mit eigenem
    Konsolenfenster wie bei einem Konsolenprogramm. Das Fenster
    bleibt verborgen, damit der Testlauf keins aufgehen lässt."""
    from ide.prozess import auftrag_von, auftrag_zuweisen, prozessbaum_beenden

    ordner = tmp_path / "p"
    _projekt_anlegen(ordner, _PROGRAMM_OHNE_WARTEN)
    optionen: dict = {}
    if konsole:
        optionen["creationflags"] = subprocess.CREATE_NEW_CONSOLE
        optionen["startupinfo"] = subprocess.STARTUPINFO(
            dwFlags=subprocess.STARTF_USESHOWWINDOW, wShowWindow=0
        )
    prozess = subprocess.Popen(
        [_INTERPRETER, "main.py"],
        cwd=ordner,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **optionen,
    )
    enkel: int | None = None
    try:
        auftrag = auftrag_zuweisen(prozess)
        assert auftrag is not None
        assert auftrag_von(prozess) is auftrag
        enkel = _enkel_abwarten(ordner)
        prozess.wait(30)
        assert _prozess_lebt(enkel)
        assert auftrag.laeuft_noch()

        prozessbaum_beenden(prozess)

        assert _verschwunden(enkel), "Der Enkelprozess läuft noch."
        assert not auftrag.laeuft_noch()
    finally:
        _aufraeumen(enkel)
        if prozess.poll() is None:
            prozess.kill()
        prozess.wait(10)


#: Startet einen gewöhnlichen Enkel und öffnet dann eine Verknüpfung
#: mit `open_url`. Mit „ohne“ als Argument öffnet `open_url` wie vor
#: Punkt 285 im eigenen Prozess (Gegenprobe).
_PROGRAMM_MIT_OPEN_URL = """\
import subprocess
import sys
import time
from pathlib import Path

import pcl.files
from pcl import open_url

if sys.argv[1:] == ["ohne"]:
    pcl.files._ausserhalb_des_auftrags_oeffnen = lambda ziel: False
enkel = Path(__file__).with_name("enkel.py")
subprocess.Popen([sys.executable, str(enkel)])
open_url("geoeffnet.lnk")
time.sleep(120)
"""

#: Das „zuständige Programm“: die Verknüpfung `geoeffnet.lnk` startet
#: es, so wie die Shell zu einer Adresse den Browser startet.
_GEOEFFNET = """\
import os
import time
from pathlib import Path

ziel = Path(__file__).with_name("geoeffnet.pid")
zwischen = ziel.with_suffix(".tmp")
zwischen.write_text(str(os.getpid()), encoding="utf-8")
os.replace(zwischen, ziel)
time.sleep(120)
"""


def _verknuepfung_anlegen(datei: Path, ziel: Path, argument: Path) -> None:
    befehl = (
        "$v = (New-Object -ComObject WScript.Shell)"
        f".CreateShortcut('{datei}'); "
        f"$v.TargetPath = '{ziel}'; "
        f"$v.Arguments = '\"{argument}\"'; "
        "$v.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         befehl],
        capture_output=True,
        check=True,
        timeout=60,
    )


def _pid_abwarten(datei: Path, zeitlimit: float = 30.0) -> int:
    ende = time.monotonic() + zeitlimit
    while time.monotonic() < ende:
        try:
            return int(datei.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            time.sleep(0.05)
    raise AssertionError(f"{datei.name} ist nie entstanden")


@pytest.mark.parametrize(
    "herausgeloest", [True, False], ids=["mit", "ohne"]
)
def test_ein_mit_open_url_geoeffnetes_programm_uebersteht_stopp(
    tmp_path: Path, herausgeloest: bool
) -> None:
    """Punkt 285: was `open_url` öffnet, gehört nicht zum Programm
    und bleibt nach dem Ende des Auftrags offen; ein gewöhnlicher
    Enkel endet. Die Gegenprobe öffnet ohne den Explorer; dann endet
    das geöffnete Programm mit dem Auftrag."""
    from ide.prozess import (
        auftrag_zuweisen,
        ohne_konsole,
        prozessbaum_beenden,
    )

    ordner = tmp_path / "p"
    _projekt_anlegen(ordner, _PROGRAMM_MIT_OPEN_URL)
    (ordner / "geoeffnet.py").write_text(_GEOEFFNET, encoding="utf-8")
    _verknuepfung_anlegen(
        ordner / "geoeffnet.lnk",
        Path(_INTERPRETER).with_name("pythonw.exe"),
        ordner / "geoeffnet.py",
    )
    wurzel = Path(__file__).resolve().parents[1]
    pakete = [p for p in sys.path if p.endswith("site-packages")]
    umgebung = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join([str(wurzel), *pakete]),
        QT_QPA_PLATFORM="offscreen",
    )
    # Manche Umgebungen setzen BROWSER (etwa auf „true“), damit nichts
    # aufgeht; `webbrowser` öffnet dann gar nichts, und die Gegenprobe
    # fände das geöffnete Programm nie.
    umgebung.pop("BROWSER", None)
    argumente = [] if herausgeloest else ["ohne"]
    prozess = subprocess.Popen(
        [_INTERPRETER, "main.py", *argumente],
        cwd=ordner,
        env=umgebung,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        **ohne_konsole(),
    )
    enkel: int | None = None
    geoeffnet: int | None = None
    try:
        auftrag = auftrag_zuweisen(prozess)
        assert auftrag is not None
        enkel = _pid_abwarten(ordner / "enkel.pid")
        geoeffnet = _pid_abwarten(ordner / "geoeffnet.pid")
        assert _prozess_lebt(enkel)
        assert _prozess_lebt(geoeffnet)

        prozessbaum_beenden(prozess)

        assert _verschwunden(enkel), "Der Enkelprozess läuft noch."
        if herausgeloest:
            time.sleep(0.5)
            assert _prozess_lebt(geoeffnet), (
                "Das geöffnete Programm wurde mit beendet."
            )
        else:
            assert _verschwunden(geoeffnet)
    finally:
        _aufraeumen(enkel)
        _aufraeumen(geoeffnet)
        if prozess.poll() is None:
            prozess.kill()
        prozess.wait(10)


@pytest.mark.skipif(sys.platform != "win32", reason="nur unter Windows")
@pytest.mark.parametrize("explorer_startet", [True, False])
def test_im_auftrag_oeffnet_der_explorer_der_anmeldung(
    monkeypatch: pytest.MonkeyPatch, explorer_startet: bool
) -> None:
    """Punkt 285: in einem Auftragsobjekt geht die Adresse an einen
    neuen Explorer, damit der Browser nicht mit „Stopp“ endet.
    Startet der Explorer nicht, öffnet der eigene Prozess."""
    import webbrowser

    import pcl.files as files

    gestartet: list[list[str]] = []
    geoeffnet: list[str] = []

    def starten(argumente: list[str], **_k: object) -> None:
        if not explorer_startet:
            raise OSError("verweigert")
        gestartet.append(argumente)

    monkeypatch.setattr(files, "_in_einem_auftrag", lambda: True)
    monkeypatch.setattr(subprocess, "Popen", starten)
    monkeypatch.setattr(webbrowser, "open", geoeffnet.append)

    from pcl import open_url

    open_url("https://example.com/seite")

    if explorer_startet:
        assert [Path(a[0]).name.lower() for a in gestartet] == ["explorer.exe"]
        assert gestartet[0][1] == "https://example.com/seite"
        assert geoeffnet == []
    else:
        assert geoeffnet == ["https://example.com/seite"]


@pytest.mark.skipif(sys.platform != "win32", reason="nur unter Windows")
def test_ein_programm_im_auftrag_erkennt_ihn() -> None:
    """`_in_einem_auftrag` gegen ein echtes Auftragsobjekt, wie Natter
    es für ein gestartetes Programm anlegt."""
    from ide.prozess import auftrag_zuweisen, prozessbaum_beenden

    kind = subprocess.Popen(
        [
            sys.executable, "-c",
            "import sys; sys.stdin.readline(); "
            "from pcl.files import _in_einem_auftrag; "
            "print(_in_einem_auftrag())",
        ],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    try:
        assert auftrag_zuweisen(kind) is not None
        ausgabe, _ = kind.communicate("los\n", timeout=60)
    finally:
        prozessbaum_beenden(kind)
    assert ausgabe.strip() == "True"

