"""Tests für ide/testrunner/ausfuehrung.py: Tests als eigener Prozess
ausführen, strukturiertes Ergebnis statt Textausgabe (Abschnitt 8.6).
Siehe Arbeitspaket M4, Schritt 7.
"""

from __future__ import annotations

import ctypes
import os
import sys
import time
from pathlib import Path

import pytest

from ide.testrunner import tests_ausfuehren as ausfuehren

_TESTDATEI_INHALT = '''\
import unittest


class TestBeispiel(unittest.TestCase):
    def test_bestehend(self):
        self.assertEqual(2 + 2, 4)

    def test_fehlschlagend(self):
        self.assertEqual(45, 50)

    def test_wirft_fehler(self):
        raise RuntimeError("kaputt")
'''


def _projekt_mit_testdatei(tmp_path: Path) -> Path:
    (tmp_path / "test_beispiel.py").write_text(_TESTDATEI_INHALT, encoding="utf-8")
    return tmp_path


def test_entdeckt_und_fuehrt_alle_tests_aus(tmp_path: Path) -> None:
    projekt = _projekt_mit_testdatei(tmp_path)
    ergebnisse = ausfuehren(projekt)

    namen = {e.id.rsplit(".", 1)[-1]: e for e in ergebnisse}
    assert set(namen) == {"test_bestehend", "test_fehlschlagend", "test_wirft_fehler"}
    assert namen["test_bestehend"].status == "bestanden"
    assert namen["test_fehlschlagend"].status == "fehlgeschlagen"
    assert namen["test_wirft_fehler"].status == "fehler"


def test_soll_ist_werden_bei_assertequal_fehlschlag_extrahiert(tmp_path: Path) -> None:
    projekt = _projekt_mit_testdatei(tmp_path)
    ergebnisse = ausfuehren(projekt)

    fehlschlag = next(e for e in ergebnisse if e.id.endswith("test_fehlschlagend"))
    assert fehlschlag.soll == "50"
    assert fehlschlag.ist == "45"


_SAMMLUNGEN_INHALT = '''\
import unittest


class TestSammlungen(unittest.TestCase):
    def test_liste(self):
        self.assertEqual(sorted([3, 1, 2]), [1, 2, 4])

    def test_tupel(self):
        self.assertEqual((1, 2), (1, 2, 3))

    def test_folge(self):
        self.assertSequenceEqual([1], (2,))

    def test_menge(self):
        self.assertEqual({1, 2}, {1, 3})

    def test_woerterbuch(self):
        self.assertEqual({"a": 1}, {"a": 2})

    def test_mehrzeiliger_text(self):
        self.assertEqual("a\\nb", "a\\nc")

    def test_liste_mit_eigener_meldung(self):
        self.assertEqual([3], [4], "falsch sortiert")
'''


@pytest.fixture(scope="module")
def sammlungen_ergebnisse(tmp_path_factory: pytest.TempPathFactory):
    projekt = tmp_path_factory.mktemp("sammlungen")
    (projekt / "test_sammlungen.py").write_text(
        _SAMMLUNGEN_INHALT, encoding="utf-8"
    )
    return {e.id.rsplit(".", 1)[-1]: e for e in ausfuehren(projekt)}


@pytest.mark.parametrize(
    ("test", "soll", "ist"),
    [
        ("test_liste", "[1, 2, 4]", "[1, 2, 3]"),
        ("test_tupel", "(1, 2, 3)", "(1, 2)"),
        ("test_folge", "(2,)", "[1]"),
        ("test_menge", "{1, 3}", "{1, 2}"),
        ("test_woerterbuch", "{'a': 2}", "{'a': 1}"),
        ("test_mehrzeiliger_text", "'a\\nc'", "'a\\nb'"),
        ("test_liste_mit_eigener_meldung", "[4]", "[3]"),
    ],
)
def test_soll_ist_bei_sammlungen_ohne_vorsatz_von_unittest(
    sammlungen_ergebnisse, test: str, soll: str, ist: str
) -> None:
    """Bei Folgen schreibt unittest „Lists differ: “ und Ähnliches vor
    den Vergleich, bei Mengen nennt die Meldung die Werte gar nicht.
    Soll und Ist zeigen trotzdem nur die Werte."""
    ergebnis = sammlungen_ergebnisse[test]
    assert ergebnis.status == "fehlgeschlagen"
    assert (ergebnis.soll, ergebnis.ist) == (soll, ist)


def test_fehler_hat_keine_soll_ist_werte(tmp_path: Path) -> None:
    projekt = _projekt_mit_testdatei(tmp_path)
    ergebnisse = ausfuehren(projekt)

    fehler = next(e for e in ergebnisse if e.id.endswith("test_wirft_fehler"))
    assert fehler.soll is None
    assert fehler.ist is None
    assert fehler.nachricht == "kaputt"


def test_jeder_test_hat_eine_dauer_ab_0(tmp_path: Path) -> None:
    projekt = _projekt_mit_testdatei(tmp_path)
    ergebnisse = ausfuehren(projekt)

    assert all(e.dauer >= 0 for e in ergebnisse)


def test_ziel_beschraenkt_auf_eine_einzelne_methode(tmp_path: Path) -> None:
    projekt = _projekt_mit_testdatei(tmp_path)
    ergebnisse = ausfuehren(projekt, ziel="test_beispiel.TestBeispiel.test_bestehend")

    assert len(ergebnisse) == 1
    assert ergebnisse[0].id.endswith("test_bestehend")


def test_leerer_projektordner_liefert_keine_ergebnisse(tmp_path: Path) -> None:
    assert ausfuehren(tmp_path) == []


def test_print_im_geprueften_code_stoert_den_testlauf_nicht(
    tmp_path: Path,
) -> None:
    """Punkt 142: die Ausgabe des geprüften Codes stand vor dem JSON,
    und der ganze Lauf scheiterte mit einem JSONDecodeError."""
    (tmp_path / "u_rechnen.py").write_text(
        "def doppelt(x):\n"
        "    print('rechne', x)\n"
        "    return 2 * x\n",
        encoding="utf-8",
    )
    (tmp_path / "test_rechnen.py").write_text(
        "import unittest\n"
        "from u_rechnen import doppelt\n"
        "\n"
        "print('beim Import')\n"
        "\n"
        "class TestRechnen(unittest.TestCase):\n"
        "    def test_doppelt(self):\n"
        "        print('Größe', doppelt(3))\n"
        "        self.assertEqual(doppelt(3), 6)\n",
        encoding="utf-8",
    )

    ergebnisse = ausfuehren(tmp_path)

    assert [(e.id, e.status) for e in ergebnisse] == [
        ("test_rechnen.TestRechnen.test_doppelt", "bestanden")
    ]


def _prozess_lebt(pid: int) -> bool:
    """Unter Windows über `OpenProcess`/`GetExitCodeProcess`, sonst
    über `os.kill(pid, 0)`."""
    if sys.platform != "win32":
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True
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


def test_zeitgrenze_beendet_auch_einen_gestarteten_prozess(
    tmp_path: Path,
) -> None:
    """Punkt 247: ein Test startet einen langen Prozess und hängt dann.
    Das Ergebnis kam erst, als der gestartete Prozess endete, und
    bei einem Prozess ohne Ende kam es nie."""
    (tmp_path / "test_haengt.py").write_text(
        "import subprocess, sys, unittest\n"
        "\n"
        "class TestHaengt(unittest.TestCase):\n"
        "    def test_startet_und_haengt(self):\n"
        "        kind = subprocess.Popen(\n"
        "            [sys.executable, '-c', 'import time; time.sleep(40)']\n"
        "        )\n"
        "        with open('kind.pid', 'w') as datei:\n"
        "            datei.write(str(kind.pid))\n"
        "        while True:\n"
        "            pass\n",
        encoding="utf-8",
    )

    beginn = time.monotonic()
    ergebnisse = ausfuehren(tmp_path, zeitlimit=4)
    dauer = time.monotonic() - beginn

    assert dauer < 15
    assert [e.status for e in ergebnisse] == ["fehler"]
    assert "Nach 4 Sekunden abgebrochen" in ergebnisse[0].nachricht
    kind_pid = int((tmp_path / "kind.pid").read_text())
    assert not _prozess_lebt(kind_pid)


@pytest.mark.skipif(sys.platform != "win32", reason="prüft Windows-Prozesse")
def test_ein_vom_test_gestarteter_prozess_endet_mit_dem_lauf(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Punkt 281: ein Test startet einen Prozess und endet sofort.
    Der Harness läuft in einem Auftragsobjekt; mit seinem Ende endet
    auch, was der Test hinterlassen hat.

    Gestartet wird der Interpreter hinter dem der virtuellen
    Umgebung. Deren `python.exe` ist unter uv ein Starter mit eigenem
    Auftragsobjekt, das beim Ende des Starters schon alles beendet,
    und dann bewiese der Test nichts."""
    monkeypatch.setattr(
        sys, "executable", getattr(sys, "_base_executable", sys.executable)
    )
    (tmp_path / "test_startet.py").write_text(
        "import subprocess, sys, unittest\n"
        "\n"
        "class TestStartet(unittest.TestCase):\n"
        "    def test_startet_und_endet(self):\n"
        "        kind = subprocess.Popen(\n"
        "            [sys.executable, '-c', 'import time; time.sleep(40)']\n"
        "        )\n"
        "        with open('kind.pid', 'w') as datei:\n"
        "            datei.write(str(kind.pid))\n",
        encoding="utf-8",
    )
    kind_pid: int | None = None
    try:
        ergebnisse = ausfuehren(tmp_path, zeitlimit=30)
        assert [e.status for e in ergebnisse] == ["bestanden"]
        kind_pid = int((tmp_path / "kind.pid").read_text())
        ende = time.monotonic() + 10
        while _prozess_lebt(kind_pid) and time.monotonic() < ende:
            time.sleep(0.1)
        assert not _prozess_lebt(kind_pid), "Der gestartete Prozess läuft noch."
    finally:
        if kind_pid is not None and _prozess_lebt(kind_pid):
            os.kill(kind_pid, 9)


_SCHEITERNDER_TEST = (
    "import unittest\n"
    "\n"
    "class TestB(unittest.TestCase):\n"
    "    def test_vergleich(self):\n"
    "        self.assertEqual(2, 3)\n"
)


@pytest.mark.parametrize(
    ("inhalt", "erwartete_id", "erwartet"),
    [
        pytest.param(
            "import unittest\n"
            "from pcl import Form\n"
            "\n"
            "class TestA(unittest.TestCase):\n"
            "    def test_formular(self):\n"
            "        Form()\n",
            "test_a.TestA.test_formular",
            ["während dieses Tests", "0xC0000409", "QApplication"],
            id="formular_ohne_qapplication",
        ),
        pytest.param(
            "import os, unittest\n"
            "\n"
            "class TestA(unittest.TestCase):\n"
            "    def test_beendet(self):\n"
            "        os._exit(3)\n",
            "test_a.TestA.test_beendet",
            ["während dieses Tests", "Rückgabewert 3"],
            id="os_exit_im_test",
        ),
        pytest.param(
            "import os\n"
            "os._exit(3)\n",
            "test_a",
            ["beim Laden der Testdatei test_a.py", "Rückgabewert 3"],
            id="os_exit_beim_laden",
        ),
    ],
)
def test_absturz_nimmt_die_anderen_ergebnisse_nicht_mit(
    tmp_path: Path, inhalt: str, erwartete_id: str, erwartet: list[str]
) -> None:
    """Punkt 425: stürzte der Testprozess ab, fielen alle Ergebnisse
    weg, und der Test-Explorer meldete „0 Tests gelaufen“."""
    (tmp_path / "test_a.py").write_text(inhalt, encoding="utf-8")
    (tmp_path / "test_b.py").write_text(
        _SCHEITERNDER_TEST, encoding="utf-8"
    )

    ergebnisse = ausfuehren(tmp_path, zeitlimit=60)

    nach_id = {e.id: e for e in ergebnisse}
    assert set(nach_id) == {erwartete_id, "test_b.TestB.test_vergleich"}
    assert nach_id["test_b.TestB.test_vergleich"].status == "fehlgeschlagen"
    abbruch = nach_id[erwartete_id]
    assert abbruch.status == "fehler"
    assert "abgebrochen" in abbruch.nachricht
    for teil in erwartet:
        assert teil in abbruch.nachricht


def test_unlesbares_ergebnis_wird_deutsch_gemeldet(tmp_path: Path) -> None:
    """Punkt 425: stand hinter der letzten Marke kein gültiges JSON,
    endete der Lauf mit einem englischen JSONDecodeError."""
    (tmp_path / "test_kaputt.py").write_text(
        "import atexit, os, unittest\n"
        "\n"
        "atexit.register(\n"
        "    lambda: os.write(1, b'@@natter-testergebnis@@{kaputt\\n')\n"
        ")\n"
        "\n"
        "class TestKaputt(unittest.TestCase):\n"
        "    def test_x(self):\n"
        "        pass\n",
        encoding="utf-8",
    )

    ergebnisse = ausfuehren(tmp_path)

    assert [(e.id, e.status) for e in ergebnisse] == [
        ("test_kaputt.TestKaputt.test_x", "bestanden"),
        ("Testlauf", "fehler"),
    ]
    assert "ließ sich nicht lesen" in ergebnisse[1].nachricht
