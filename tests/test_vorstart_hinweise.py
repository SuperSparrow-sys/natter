"""Ein ungenutzter Import verhindert den Start nicht mehr (M12).

Bis hierher verhinderte **jeder** Fund der Vorstart-Prüfung den Start.
Wer `import random` schreibt, bevor er `random` benutzt – also so, wie
man es lernt –, bekam sein Programm nicht gestartet, obwohl es
einwandfrei gelaufen wäre. Dasselbe beim Auskommentieren einer Zeile
zum Ausprobieren: die Variable darüber wird ungenutzt, und der Start ist
blockiert.

In Lazarus ist eine ungenutzte Unit im `uses` ein Hinweis, kein Fehler –
das Programm übersetzt und läuft. Genauso hier: ungenutzter Import und
ungenutzte Variable stehen im Panel „Meldungen“, das Programm startet.

Ein Syntaxfehler oder ein unbekannter Name verhindert den Start
weiterhin. Dort stürzt das Programm ohnehin ab, und die Meldung vorher
sagt mehr als der Absturz danach.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings

from ide.project import Projekt
from ide.run.pruefung import NUR_HINWEIS, RuffFund, projekt_pruefen
from ide.shell.hauptfenster import HauptFenster


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import ide.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


def _projekt(ordner: Path, quelltext: str) -> Projekt:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(quelltext, encoding="utf-8")
    (ordner / "p.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Probe",
                "type": "console",
                "main": "main.py",
            }
        ),
        encoding="utf-8",
    )
    return Projekt.laden(ordner)


def _fund(code: str) -> RuffFund:
    return RuffFund(datei=Path("main.py"), zeile=1, spalte=1, code=code, meldung="`x`")


def test_ein_ungenutzter_import_ist_nur_ein_hinweis() -> None:
    assert _fund("F401").blockiert is False


def test_eine_ungenutzte_variable_ist_nur_ein_hinweis() -> None:
    assert _fund("F841").blockiert is False


def test_ein_unbekannter_name_blockiert() -> None:
    assert _fund("F821").blockiert is True


def test_ein_syntaxfehler_blockiert() -> None:
    assert _fund("invalid-syntax").blockiert is True


def test_eine_unbekannte_regel_blockiert_vorsichtshalber() -> None:
    """Die Ausnahmen sind aufgezählt, nicht die Blocker: eine später
    hinzugefügte Regel soll den Start verhindern, bis jemand bewusst
    entscheidet, dass sie es nicht muss."""
    assert _fund("F999").blockiert is True
    assert "F999" not in NUR_HINWEIS


def test_der_ungenutzte_import_wird_wirklich_gefunden(tmp_path: Path) -> None:
    """Sonst prüfte der Test unten etwas, das gar nicht auftritt."""
    projekt = _projekt(
        tmp_path / "p", "import random" + chr(10) * 2 + 'print("Hallo")' + chr(10)
    )

    funde = projekt_pruefen(projekt)

    assert [fund.code for fund in funde] == ["F401"]


def test_mit_ungenutztem_import_startet_das_programm(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(
        _projekt(
            tmp_path / "p", "import random" + chr(10) * 2 + 'print("Hallo")' + chr(10)
        ).ordner
    )

    blockiert = fenster._vorstart_pruefung_blockiert()

    assert blockiert is False
    assert fenster.meldungen_liste.count() == 1  # der Hinweis steht trotzdem da
    meldung = fenster.statusBar().currentMessage()
    assert "läuft trotzdem" in meldung


def test_mit_einem_unbekannten_namen_startet_es_nicht(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(_projekt(tmp_path / "p", "print(zaehler)" + chr(10)).ordner)

    blockiert = fenster._vorstart_pruefung_blockiert()

    assert blockiert is True
    assert "nicht gestartet" in fenster.statusBar().currentMessage()


def test_ein_blocker_neben_hinweisen_blockiert(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    """Gezählt werden in der Meldung die Blocker, nicht alle Funde -
    sonst stünde dort eine Zahl, zu der die Erklärung nicht passt."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(
        _projekt(
            tmp_path / "p", "import random" + chr(10) + "print(zaehler)" + chr(10)
        ).ordner
    )

    blockiert = fenster._vorstart_pruefung_blockiert()

    assert blockiert is True
    assert fenster.meldungen_liste.count() == 2  # beide stehen im Panel
    assert "1 Fund" in fenster.statusBar().currentMessage()


def test_ohne_jeden_fund_bleibt_die_liste_leer(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(_projekt(tmp_path / "p", 'print("Hallo")' + chr(10)).ordner)

    assert fenster._vorstart_pruefung_blockiert() is False
    assert fenster.meldungen_liste.count() == 0
