"""Die Sperrdatei eines geöffneten Projekts (Punkt 286,
`ide/project/sperre.py`)."""

from __future__ import annotations

import os
from pathlib import Path

from ide.project import sperre

#: Eine Prozessnummer, die es nicht gibt.
_TOT = 2**31 - 4


def _eintragen(ordner: Path, pid: int, start: int) -> None:
    (ordner / sperre.SPERRDATEI).write_text(
        f"{pid} {start}\n", encoding="utf-8"
    )


def test_eigene_sperre_zaehlt_nicht(tmp_path: Path) -> None:
    sperre.sperren(tmp_path)
    assert (tmp_path / sperre.SPERRDATEI).is_file()
    assert sperre.anderer_prozess(tmp_path) is None
    sperre.freigeben(tmp_path)
    assert not (tmp_path / sperre.SPERRDATEI).exists()


def test_sperre_eines_laufenden_prozesses_wird_erkannt(
    tmp_path: Path,
) -> None:
    eltern = os.getppid()
    _eintragen(tmp_path, eltern, sperre._startzeit(eltern) or 0)

    assert sperre.anderer_prozess(tmp_path) == eltern
    # Die Sperre des anderen bleibt beim Freigeben liegen.
    sperre.freigeben(tmp_path)
    assert (tmp_path / sperre.SPERRDATEI).exists()


def test_liegengebliebene_sperre_wird_uebergangen(tmp_path: Path) -> None:
    assert sperre.anderer_prozess(tmp_path) is None
    _eintragen(tmp_path, _TOT, 1)
    assert sperre.anderer_prozess(tmp_path) is None
    # Dieselbe Nummer, aber ein anderer Prozess: nach einem Neustart
    # vergibt Windows die Nummern neu.
    eltern = os.getppid()
    start = sperre._startzeit(eltern)
    if start:
        _eintragen(tmp_path, eltern, start + 1)
        assert sperre.anderer_prozess(tmp_path) is None
    (tmp_path / sperre.SPERRDATEI).write_text("kaputt", encoding="utf-8")
    assert sperre.anderer_prozess(tmp_path) is None


def test_sperre_nennt_rechner_und_konto_und_wird_erneuert(
    tmp_path: Path,
) -> None:
    """Punkt 322: Rechner, Konto und Zeit stehen in der Sperrdatei, und
    nur die eigene wird erneuert und freigegeben."""
    datei = tmp_path / sperre.SPERRDATEI
    sperre.sperren(tmp_path)
    text = datei.read_text(encoding="utf-8")
    assert f"rechner={sperre.rechnername()}" in text
    assert f"konto={sperre.kontoname()}" in text
    datei.write_text(
        text.replace("erneuert=", "erneuert=1"), encoding="utf-8"
    )
    sperre.erneuern(tmp_path)
    assert datei.read_text(encoding="utf-8") != text.replace(
        "erneuert=", "erneuert=1"
    )

    # Dieselbe Prozessnummer an einem anderen Rechner ist ein anderes
    # Natter: es zählt, und seine Sperre bleibt unberührt.
    fremd = f"{os.getpid()} 1\nrechner=PC-R07\nerneuert=100\n"
    datei.write_text(fremd, encoding="utf-8")
    wer = sperre.anderer_besitzer(tmp_path, jetzt=100 + 60)
    assert wer is not None and wer.anderer_rechner
    assert sperre.anderer_besitzer(
        tmp_path, jetzt=100 + sperre.ZEITGRENZE + 1
    ) is None
    sperre.erneuern(tmp_path)
    sperre.freigeben(tmp_path)
    assert datei.read_text(encoding="utf-8") == fremd
