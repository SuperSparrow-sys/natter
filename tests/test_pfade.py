"""Der Dokumente-Ordner wird erfragt, nicht geraten.

Punkt 20 der offenen Punkte. `Path.home() / "Documents"` stimmt auf
einem Rechner mit OneDrive nicht - und das ist auf Schulrechnern wie
auf privaten die Regel:

    Windows sagt:  C:\\Users\\…\\OneDrive\\Dokumente
    Natter riet:   C:\\Users\\…\\Documents

Natter legte damit einen zweiten Ordner an, den im Explorer niemand
findet. Auf dem Rechner, auf dem es auffiel, lag unter dem geratenen
Pfad sogar der Entwicklungsbaum von Natter selbst, und die
Arbeitskopien der Beispiele landeten zwischen `ide`, `pcl` und
`docs`.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

from ide.pfade import NATTER_ORDNER, dokumente_ordner, natter_ordner
from ide.shell.startbild import beispiel_kopieren

BEISPIEL = (
    Path(__file__).resolve().parent.parent
    / "beispielprojekte"
    / "03_Taschenrechner"
    / "03_Taschenrechner.natter"
)


def test_der_ordner_existiert_wirklich() -> None:
    """Der eigentliche Punkt: ein Pfad, den es nicht gibt, ist
    geraten. Windows nennt nur Ordner, die es angelegt hat."""
    ordner = dokumente_ordner()

    assert ordner.is_dir(), f"{ordner} gibt es nicht."


@pytest.mark.skipif(sys.platform != "win32", reason="Nur Windows kennt diese Ordner.")
def test_windows_wird_gefragt_und_nicht_das_benutzerprofil_geraten() -> None:
    """Stimmen beide überein, sagt der Test nichts aus - dann ist der
    Dokumente-Ordner eben nicht umgeleitet. Er darf aber nie einfach
    `~/Documents` zurückgeben, ohne gefragt zu haben."""
    import ctypes

    zeiger = ctypes.c_wchar_p()
    kennung = ctypes.create_unicode_buffer("{FDD39AD0-238F-46AF-ADB4-6C85480369C7}")
    from ide.pfade import _guid

    ergebnis = ctypes.windll.shell32.SHGetKnownFolderPath(
        ctypes.byref(_guid(kennung.value)), 0, None, ctypes.byref(zeiger)
    )
    assert ergebnis == 0
    erwartet = Path(zeiger.value)
    ctypes.windll.ole32.CoTaskMemFree(zeiger)

    assert dokumente_ordner() == erwartet


def test_der_natter_ordner_liegt_unter_den_dokumenten() -> None:
    """Über das Modul gefragt und nicht über den importierten Namen:
    die Testumgebung lenkt `dokumente_ordner` auf ein temporäres
    Verzeichnis um, damit kein Testlauf in den echten
    Dokumente-Ordner schreibt. Geprüft wird hier die Beziehung der
    beiden, nicht der absolute Pfad."""
    import ide.pfade

    assert natter_ordner().parent == ide.pfade.dokumente_ordner()
    assert natter_ordner().name == NATTER_ORDNER


def test_nachsehen_legt_keinen_ordner_an(tmp_path: Path) -> None:
    """Wer nur fragt, wo etwas hingehört, soll keinen leeren Ordner
    hinterlassen."""
    vorher = natter_ordner().exists()

    natter_ordner()

    assert natter_ordner().exists() == vorher


# --------------------------------- Die Beispiele landen dort, nicht im Repository


def test_eine_beispielkopie_geht_in_den_ordner_der_kopien(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import ide.shell.startbild as modul

    ziel = tmp_path / "Natter" / "Beispielprojekte"
    monkeypatch.setattr(modul, "beispielkopien_ordner", lambda: ziel)

    kopie = beispiel_kopieren(BEISPIEL)

    assert kopie.parent.parent == ziel
    assert kopie.exists()
    shutil.rmtree(kopie.parent)


def test_sie_landet_nicht_im_entwicklungsbaum() -> None:
    """Der Fall, um den es ging: auf diesem Rechner heißt der
    Entwicklungsordner `Documents/natter`, und Windows unterscheidet
    bei Dateinamen nicht zwischen Groß- und Kleinschreibung."""
    entwicklungsbaum = Path(__file__).resolve().parent.parent

    ziel = natter_ordner().resolve()

    assert ziel != entwicklungsbaum, (
        "Die Arbeitskopien landen im Entwicklungsbaum von Natter."
    )
    assert entwicklungsbaum not in ziel.parents
