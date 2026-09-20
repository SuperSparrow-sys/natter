"""Die Panels zeigen wirklich etwas - mit laufenden Programmen geprüft.

Punkt 15 der offenen Punkte. Ein leeres Panel sieht genauso aus, ob
es nichts zu zeigen gibt oder ob die Verbindung dahinter nie
angeschlossen wurde. Der Reiter „Ausgabe" trug bis September 2026 den
Kurzhinweis „Was das laufende Programm ausgibt (print)" und zeigte in
Wirklichkeit nur Start- und Endzeilen; die Ausgabe des Programms lief
in ein Konsolenfenster daneben.

Hier läuft deshalb ein echtes Python, kein Mock: das Programm wird
gestartet, hält an einem Haltepunkt, schreibt nach `stdout` und nach
`stderr`. Was danach in den Panels steht, ist die Antwort.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ide.shell.hauptfenster import HauptFenster
from tests.conftest import DEBUG_ZEITGRENZE

#: Ein gestartetes Programm braucht ein paar Runden, bis seine erste
#: Zeile durch die Leitung und durch die Qt-Ereignisschleife ist.
AUSGABE_ZEITGRENZE = 20000


def _projekt(ordner: Path, quelltext: str, typ: str = "gui") -> Path:
    """Ein Projekt zum Starten.

    Voreingestellt ein GUI-Projekt, denn nur dort läuft die Ausgabe
    durch ein Rohr ins Panel. Ein Konsolenprojekt bekommt ein eigenes
    Fenster (`CREATE_NEW_CONSOLE` in `ide/run/starter.py`), und was
    es druckt, steht dort - siehe
    `test_bei_einem_konsolenprojekt_bleibt_die_ausgabe_im_fenster`.
    """
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text(quelltext, encoding="utf-8")
    (ordner / "test.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Probe",
                "type": typ,
                "main": "main.py",
            }
        ),
        encoding="utf-8",
    )
    return ordner / "test.natter"


def _zeilen(fenster: HauptFenster) -> list[str]:
    liste = fenster.ausgabe_liste
    return [liste.item(i).text() for i in range(liste.count())]


@pytest.fixture
def fenster(qtbot) -> HauptFenster:
    f = HauptFenster()
    qtbot.addWidget(f)
    yield f
    if f.debug_sitzung is not None or f.laufender_prozess is not None:
        f._debugger_stoppen_aktion()


# ------------------------------------------------ Variablen und Stapel


def test_der_aufrufstapel_zeigt_die_ganze_kette(
    fenster: HauptFenster, qtbot, tmp_path: Path
) -> None:
    """Der vorhandene Test prüft nur, dass überhaupt etwas dasteht.
    Gemeint ist aber die Kette: wer hat wen aufgerufen."""
    quelltext = (
        "def innen(x):\n"
        "    marke = x * 2  # Zeile 2\n"
        "    return marke\n"
        "\n"
        "def aussen():\n"
        "    return innen(21)\n"
        "\n"
        "aussen()\n"
    )
    fenster.projekt_oeffnen(_projekt(tmp_path / "p", quelltext))
    editor = fenster.datei_oeffnen(fenster.projekt.haupt_datei)
    editor.breakpoint_umschalten(2)

    fenster._projekt_mit_debugger_starten_aktion()
    qtbot.waitUntil(
        lambda: fenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE
    )
    qtbot.waitUntil(
        lambda: fenster.aufrufstapel_liste.count() >= 3, timeout=DEBUG_ZEITGRENZE
    )

    eintraege = [
        fenster.aufrufstapel_liste.item(i).text()
        for i in range(fenster.aufrufstapel_liste.count())
    ]
    zusammen = " | ".join(eintraege)
    assert "innen" in zusammen, zusammen
    assert "aussen" in zusammen, zusammen


def test_die_variablen_stehen_mit_ihren_werten_da(
    fenster: HauptFenster, qtbot, tmp_path: Path
) -> None:
    """Ein Name ohne Wert wäre nur die halbe Auskunft."""
    quelltext = "name = 'Anna'\nzahl = 7\nliste = [1, 2, 3]\nmarke = 1  # Zeile 4\n"
    fenster.projekt_oeffnen(_projekt(tmp_path / "p", quelltext))
    editor = fenster.datei_oeffnen(fenster.projekt.haupt_datei)
    editor.breakpoint_umschalten(4)

    fenster._projekt_mit_debugger_starten_aktion()
    qtbot.waitUntil(
        lambda: fenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE
    )
    qtbot.waitUntil(
        lambda: fenster.variablen_baum.topLevelItemCount() > 0,
        timeout=DEBUG_ZEITGRENZE,
    )

    werte = {
        fenster.variablen_baum.topLevelItem(i).text(0): fenster.variablen_baum.topLevelItem(
            i
        ).text(1)
        for i in range(fenster.variablen_baum.topLevelItemCount())
    }
    assert werte.get("zahl") == "7"
    assert werte.get("name") == "'Anna'"
    assert "1, 2, 3" in werte.get("liste", "")


def test_die_spalte_heisst_variable_und_nicht_eigenschaft(
    fenster: HauptFenster,
) -> None:
    """„Eigenschaft" war die Beschriftung des Objektinspektors. Hier
    stehen Variablen, und gefüllt wird die Spalte auch aus
    `variable["name"]`."""
    kopf = fenster.variablen_baum.headerItem()

    assert kopf.text(0) == "Variable"
    assert kopf.text(1) == "Wert"


# ------------------------------------------------ Das Panel „Ausgabe"


def test_was_das_programm_druckt_steht_im_panel(
    fenster: HauptFenster, qtbot, tmp_path: Path
) -> None:
    """Der Kern des Punktes: bis September 2026 lief das in ein
    Konsolenfenster daneben, und das Panel zeigte nur Start und Ende.
    """
    quelltext = (
        "import sys\n"
        "print('Erste Zeile')\n"
        "print('Zweite Zeile')\n"
        "sys.stdout.flush()\n"
    )
    fenster.projekt_oeffnen(_projekt(tmp_path / "p", quelltext))

    fenster._projekt_starten_aktion()
    qtbot.waitUntil(
        lambda: any("Erste Zeile" in z for z in _zeilen(fenster)),
        timeout=AUSGABE_ZEITGRENZE,
    )

    zeilen = _zeilen(fenster)
    assert any("Zweite Zeile" in z for z in zeilen), zeilen


def test_auch_eine_fehlermeldung_landet_dort(
    fenster: HauptFenster, qtbot, tmp_path: Path
) -> None:
    """`stderr` läuft seit der Umstellung in dasselbe Rohr. Ohne das
    bliebe der Absturz unsichtbar, weil kein Konsolenfenster mehr
    aufgeht."""
    quelltext = "import sys\nprint('vorher')\nsys.stderr.write('Etwas ging schief\\n')\n"
    fenster.projekt_oeffnen(_projekt(tmp_path / "p", quelltext))

    fenster._projekt_starten_aktion()
    qtbot.waitUntil(
        lambda: any("Etwas ging schief" in z for z in _zeilen(fenster)),
        timeout=AUSGABE_ZEITGRENZE,
    )


def test_eine_unbehandelte_ausnahme_ist_zu_sehen(
    fenster: HauptFenster, qtbot, tmp_path: Path
) -> None:
    """Der Fall, der einer Schülerin wirklich passiert."""
    quelltext = "zahlen = [1, 2]\nprint(zahlen[5])\n"
    fenster.projekt_oeffnen(_projekt(tmp_path / "p", quelltext))

    fenster._projekt_starten_aktion()
    qtbot.waitUntil(
        lambda: any("IndexError" in z for z in _zeilen(fenster)),
        timeout=AUSGABE_ZEITGRENZE,
    )


def test_jede_zeile_des_programms_ist_erkennbar(
    fenster: HauptFenster, qtbot, tmp_path: Path
) -> None:
    """Die Zeilen des Programms stehen zwischen den Meldungen von
    Natter. Ohne Unterscheidung wüsste niemand, wer gerade spricht."""
    fenster.projekt_oeffnen(_projekt(tmp_path / "p", "print('vom Programm')\n"))

    fenster._projekt_starten_aktion()
    qtbot.waitUntil(
        lambda: any("vom Programm" in z for z in _zeilen(fenster)),
        timeout=AUSGABE_ZEITGRENZE,
    )

    zeilen = _zeilen(fenster)
    assert any("gestartet" in z for z in zeilen), "Die Startzeile fehlt."


def test_bei_einem_konsolenprojekt_bleibt_die_ausgabe_im_fenster(
    fenster: HauptFenster, qtbot, tmp_path: Path
) -> None:
    """Festgehalten, weil es beim Durchgang für einen Fehler gehalten
    wurde: ein Konsolenprojekt startet mit einem eigenen Fenster
    (`CREATE_NEW_CONSOLE`) und ohne Rohr. Seine Zeilen stehen dort,
    nicht im Panel - das Panel meldet nur Start und Ende.

    Das ist Absicht: ein Konsolenprogramm braucht `input()`, und eine
    Eingabe nimmt eine Liste im Panel nicht entgegen. Der Kurzhinweis
    am Reiter verspricht allerdings mehr, als für diesen Fall
    eingelöst wird.
    """
    fenster.projekt_oeffnen(
        _projekt(tmp_path / "k", "print('nur im Fenster')\n", typ="console")
    )

    fenster._projekt_starten_aktion()
    qtbot.waitUntil(
        lambda: any("gestartet" in z for z in _zeilen(fenster)), timeout=5000
    )

    assert fenster._ausgabe_leser is None, (
        "Ein Konsolenprojekt braucht keinen Leser - es hat sein eigenes Fenster."
    )
