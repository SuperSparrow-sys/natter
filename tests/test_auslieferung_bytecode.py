"""Der Bau liefert die mitgelieferte Python mit Bytecode aus (Punkt 270).

Ohne ihn übersetzte Python beim ersten Start eines Programms mit
scikit-learn oder pandas tausende Dateien, schrieb sie in den
Programmordner, und Defender prüfte jede: über dreißig Sekunden bis zum
Fenster. Unter `Program Files` kann Python die `.pyc` gar nicht
schreiben, dann wäre jeder Start so langsam.

Die Tests bauen eine kleine Nachbildung von `dist\\Natter\\python\\Lib`
in `tmp_path` und übersetzen sie mit dem Befehl, den der Bau benutzt;
übersetzt wird mit der Python, unter der die Tests laufen.
"""

from __future__ import annotations

import marshal
import py_compile
import sys
from pathlib import Path

import pytest

from tools import ide_paketieren as paket

SP = "Lib/site-packages"


def _legen(ordner: Path, pfad: str, inhalt: str = "x = 1\n") -> Path:
    ziel = ordner / pfad
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(inhalt, encoding="utf-8")
    return ziel


@pytest.fixture
def python(tmp_path: Path) -> Path:
    """Die Nachbildung: Standardbibliothek, Natters Code, ein fremdes
    Paket und die Datenordner, die der Bau nach `site-packages`
    kopiert."""
    ordner = tmp_path / "Natter" / "python"
    _legen(ordner, "Lib/os.py")
    _legen(ordner, "Lib/json/__init__.py")
    _legen(ordner, f"{SP}/ide/main.py", "def start():\n    return 1\n")
    _legen(ordner, f"{SP}/pcl/application.py")
    _legen(ordner, f"{SP}/numpy/__init__.py")
    _legen(ordner, f"{SP}/beispielprojekte/06_Konto/u_main.py")
    # Eine Vorlage mit Platzhalter ist kein gültiges Python.
    _legen(ordner, f"{SP}/templates/formular.py", "class {{name}}:\n")
    return ordner / "python.exe"


_BEFEHL = paket.bytecode_befehl


def _mit_dieser_python(
    python: Path, dateien: list[str] | None = None
) -> list[str]:
    befehl = _BEFEHL(python, dateien)
    return [sys.executable, *befehl[1:]]


class _Sammler:
    def __init__(self) -> None:
        self.zeilen: list[str] = []

    def zeile(self, text: str) -> None:
        self.zeilen.append(text.rstrip())


@pytest.fixture
def melder(monkeypatch: pytest.MonkeyPatch) -> _Sammler:
    sammler = _Sammler()
    monkeypatch.setattr(paket, "_melder", sammler)
    monkeypatch.setattr(paket, "bytecode_befehl", _mit_dieser_python)
    return sammler


def test_jede_py_der_python_bekommt_eine_pyc(python: Path, melder) -> None:  # noqa: ANN001
    lib = python.parent / "Lib"
    assert paket.bytecode_luecken(lib)  # vorher fehlt alles

    paket._bytecode_erzeugen(python)

    assert paket.bytecode_luecken(lib) == []
    assert any("ohne .pyc geblieben: 0" in z for z in melder.zeilen)


def test_der_bytecode_haengt_nicht_an_zeitstempeln(python: Path, melder) -> None:  # noqa: ANN001
    """Der Installer rundet Zeitstempel auf zwei Sekunden. Eine `.pyc`
    mit Zeitstempel passte danach oft nicht mehr zur `.py`."""
    paket._bytecode_erzeugen(python)

    for pyc in (python.parent / "Lib").rglob("*.pyc"):
        kopf = pyc.read_bytes()[4:8]
        assert int.from_bytes(kopf, "little") == 0b01, pyc


def test_bytecode_von_pip_wird_ersetzt(python: Path, melder) -> None:  # noqa: ANN001
    """pip legt beim Installieren schon `.pyc` mit Zeitstempel an. Ohne
    `-f` ließe `compileall` sie liegen, und `site-packages` bliebe
    abhängig vom Zeitstempel."""
    numpy = python.parent / SP / "numpy" / "__init__.py"
    py_compile.compile(
        str(numpy),
        invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP,
    )
    assert numpy in paket.bytecode_luecken(python.parent / "Lib")

    paket._bytecode_erzeugen(python)

    assert numpy not in paket.bytecode_luecken(python.parent / "Lib")


def test_beispiele_und_vorlagen_bleiben_ohne_bytecode(
    python: Path, melder  # noqa: ANN001
) -> None:
    """Für die Datenordner gilt weiter `NIE_AUSLIEFERN`: eine `.pyc`
    in einem Beispiel ginge mit jeder Kopie an die Schülerin."""
    paket._bytecode_erzeugen(python)

    site_packages = python.parent / SP
    for ordner in paket.OHNE_BYTECODE:
        assert not list((site_packages / ordner).rglob("*.pyc")), ordner
    assert "*.pyc" in paket.NIE_AUSLIEFERN
    assert "__pycache__" in paket.NIE_AUSLIEFERN


def test_der_pfad_des_baurechners_steht_nicht_im_bytecode(
    python: Path, melder  # noqa: ANN001
) -> None:
    paket._bytecode_erzeugen(python)

    pyc = next((python.parent / SP / "ide" / "__pycache__").glob("main.*.pyc"))
    code = marshal.loads(pyc.read_bytes()[16:])
    assert not Path(code.co_filename).is_absolute()
    assert Path(code.co_filename).parts[:2] == ("python", "Lib")


def test_ein_punkt_im_modulnamen_ist_keine_luecke(
    python: Path, melder  # noqa: ANN001
) -> None:
    """PyInstallers Hooks heißen etwa `hook-lxml.etree.py`; ihre `.pyc`
    hat einen Punkt mehr im Namen."""
    hook = _legen(python.parent, f"{SP}/hooks/hook-lxml.etree.py")

    paket._bytecode_erzeugen(python)

    assert hook not in paket.bytecode_luecken(python.parent / "Lib")
    assert paket.bytecode_luecken(python.parent / "Lib") == []


def test_ein_fehler_in_einem_fremden_paket_ist_nur_eine_warnung(
    python: Path, melder  # noqa: ANN001
) -> None:
    _legen(python.parent, f"{SP}/altpaket/beispiel.py", "print 'alt'\n")

    paket._bytecode_erzeugen(python)

    assert any(
        z.startswith("Warnung:") and "altpaket" in z for z in melder.zeilen
    )


def test_ein_fehler_in_natters_eigenem_code_bricht_den_bau_ab(
    python: Path, melder  # noqa: ANN001
) -> None:
    _legen(python.parent, f"{SP}/pcl/kaputt.py", "def (:\n")

    with pytest.raises(RuntimeError, match="Bytecode"):
        paket._bytecode_erzeugen(python)


def test_der_befehl_hat_eine_zeitgrenze(
    python: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    aufrufe: list[dict] = []

    def ausfuehren_ersatz(befehl, melder, **optionen):  # noqa: ANN001, ANN202
        aufrufe.append(optionen)
        return 0, ""

    monkeypatch.setattr(paket, "ausfuehren", ausfuehren_ersatz)
    monkeypatch.setattr(paket, "_melder", _Sammler())

    paket._bytecode_erzeugen(python)

    assert 0 < aufrufe[0]["zeitgrenze"] <= 3600


def test_eine_gesperrte_pyc_wird_allein_noch_einmal_uebersetzt(
    python: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mit `-f` und mehreren Prozessen ersetzt `compileall` auch
    `.pyc`, die seine Helfer gerade lesen. Windows verweigert das
    Ersetzen dann; beim Ausprobieren traf es jedes Mal ein, zwei
    Dateien der Standardbibliothek."""
    gesperrt = str(python.parent / "Lib" / "bz2.py")
    befehle: list[list[str]] = []

    def ausfuehren_ersatz(befehl, melder, **optionen):  # noqa: ANN001, ANN202
        befehle.append(befehl)
        if len(befehle) == 1:
            meldung = gesperrt.replace("\\", "\\\\")
            return 1, (
                f"*** Error compiling '{meldung}'...\n"
                "PermissionError: [WinError 5] Zugriff verweigert\n"
            )
        return 0, ""

    monkeypatch.setattr(paket, "ausfuehren", ausfuehren_ersatz)
    sammler = _Sammler()
    monkeypatch.setattr(paket, "_melder", sammler)

    paket._bytecode_erzeugen(python)

    assert len(befehle) == 2
    assert befehle[1][-1] == gesperrt
    assert "-j" not in befehle[1]
    assert not any(z.startswith("Warnung:") for z in sammler.zeilen)


def test_eine_zeitueberschreitung_bricht_den_bau_ab(
    python: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    def haengt(befehl, melder, **optionen):  # noqa: ANN001, ANN202
        raise subprocess.TimeoutExpired(befehl, optionen["zeitgrenze"])

    monkeypatch.setattr(paket, "ausfuehren", haengt)
    monkeypatch.setattr(paket, "_melder", _Sammler())

    with pytest.raises(RuntimeError, match="abgebrochen"):
        paket._bytecode_erzeugen(python)


def test_der_bytecode_entsteht_vor_signatur_und_manifest() -> None:
    """Das Manifest erfasst die `.pyc`. Entstünden sie danach, meldete
    schon der erste Start eine veränderte Installation."""
    phasen = [name for name, _dauer in paket._PHASEN]
    assert phasen.index("Bytecode erzeugen") < phasen.index("Signieren")
    assert phasen.index("Bytecode erzeugen") < phasen.index("Prüfsummen")

    import inspect

    quelle = inspect.getsource(paket.paketieren)
    assert (
        quelle.index("_bytecode_erzeugen(")
        < quelle.index("_signieren_mit_zwischenspeicher(")
        < quelle.index("_manifest_schreiben(")
    )
