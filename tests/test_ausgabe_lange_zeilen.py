"""Überlange Zeilen und Ausgabe ohne Zeilenende (Punkt 275).

Bis 0.3.6 las `AusgabeLeser` zeilenweise ohne Grenze. `print(zahlen)`
mit einer großen Liste legte eine einzige Zeile mit Millionen Zeichen
ins Panel „Ausgabe“, und jedes Neuzeichnen hielt Natter sekundenlang
an. Eine Schleife mit `print(i, end=" ")` zeigte gar nichts, bis das
Programm endete, und sammelte bis dahin alles im Speicher.

Der Kindprozess, der das im Echten nachstellt, steht in
`test_ausgabe_ohne_zeilenende.py`; hier genügen ein Textstrom und ein
Rohr ohne zweiten Prozess.
"""

from __future__ import annotations

import io
import os
import threading

from ide.shell.hintergrund import ZEILEN_GRENZE, AusgabeLeser


class _Programm:
    """Ein Programm, dessen Ausgabe `stdout` ist."""

    def __init__(self, stdout) -> None:
        self.stdout = stdout

    def poll(self) -> int | None:
        return None

    def kill(self) -> None:
        pass


def test_eine_riesige_zeile_kommt_in_stuecken_an(qtbot) -> None:
    """So sieht `print(list(range(1_000_000)))` für den Leser aus."""
    text = str(list(range(200_000)))
    leser = AusgabeLeser(_Programm(io.StringIO(text + "\nende\n")))
    leser.run()
    zeilen, verdraengt = leser.abholen()

    assert verdraengt == 0
    assert max(len(zeile) for zeile in zeilen) <= ZEILEN_GRENZE
    assert "".join(zeilen[:-1]) == text
    assert zeilen[-1] == "ende"


def test_zeilenenden_aller_art_und_leere_zeilen(qtbot) -> None:
    text = "eins\r\nzwei\n\nfortschritt\rdrei"
    leser = AusgabeLeser(_Programm(io.StringIO(text)))
    leser.run()
    assert leser.abholen() == (
        ["eins", "zwei", "fortschritt", "drei"],
        0,
    )


def test_ausgabe_ohne_zeilenende_erscheint_waehrend_das_rohr_offen_ist(
    qtbot,
) -> None:
    """Ein Rohr, in das jemand ohne Zeilenende schreibt und das offen
    bleibt, wie bei `print(i, end=" ")` in einer Schleife. Der Leser
    gibt nach `ZEILEN_GRENZE` Zeichen ab, statt auf ein Zeilenende zu
    warten, das nie kommt."""
    lesen, schreiben = os.pipe()
    strom = open(lesen, encoding="utf-8", errors="replace")
    leser = AusgabeLeser(_Programm(strom))
    leser.start()
    try:
        # Ein Umlaut mitten im Text: seine zwei Bytes dürfen auf zwei
        # Lesevorgänge verteilt ankommen.
        stueck = ("ä" + "x" * 99).encode("utf-8")
        schreiber = threading.Thread(
            target=lambda: [
                os.write(schreiben, stueck) for _ in range(50)
            ]
        )
        schreiber.start()
        schreiber.join(5)

        gesammelt: list[str] = []

        def zwei_zeilen() -> bool:
            gesammelt.extend(leser.abholen()[0])
            return len(gesammelt) >= 2

        qtbot.waitUntil(zwei_zeilen, timeout=5000)
        assert all(len(zeile) == ZEILEN_GRENZE for zeile in gesammelt)
        assert gesammelt[0] == ("ä" + "x" * 99) * 20
    finally:
        os.close(schreiben)
        assert leser.wait(5000)
        strom.close()
    rest = "".join(leser.abholen()[0])
    assert len("".join(gesammelt) + rest) == 50 * 100


def test_das_panel_kuerzt_eine_ueberlange_zeile_sichtbar(
    hauptfenster,
) -> None:
    """Eine Zeile, die nicht über den Leser kommt, wird im Panel
    gekürzt, und dahinter steht, wie lang sie war."""
    fenster = hauptfenster
    fenster._ausgabe_zeilen_anhaengen(["y" * 1_000_000, "kurz"])
    liste = fenster.ausgabe_liste
    lang = liste.item(liste.count() - 2).text()
    assert len(lang) < ZEILEN_GRENZE + 60
    assert lang.endswith("… (gekürzt, 1.000.000 Zeichen)")
    assert liste.item(liste.count() - 1).text().endswith("  kurz")
