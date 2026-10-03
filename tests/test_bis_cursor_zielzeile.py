"""Punkt 631: „Ausführen bis Cursor“ auf einer Leer- oder Kommentarzeile
und bei geändertem, nicht gespeichertem Text.

Auf einer Leerzeile kann Python nicht halten; debugpy legte das Ziel auf
die Anweisung davor, und das Programm hielt zu früh. Während eines Halts
zählen außerdem die Zeilen der geladenen Datei, nicht die des Editors.
"""

from __future__ import annotations

from pathlib import Path

import pytest

QUELLTEXT = (
    "for i in range(3):\n"
    "    a = i\n"
    "\n"
    "    # rechnen\n"
    "    b = a * 2\n"
)


class _Sitzung:
    """Attrappe einer laufenden Debug-Sitzung."""

    def __init__(self) -> None:
        self.ziele: list[tuple[Path, int]] = []

    def bis_cursor(self, pfad: Path, zeile: int, _faden: int) -> None:
        self.ziele.append((pfad, zeile))

    def beenden(self) -> None:
        pass


def _cursor_auf(editor, zeile: int) -> None:  # noqa: ANN001
    cursor = editor.textCursor()
    cursor.setPosition(editor.document().findBlockByNumber(zeile - 1).position())
    editor.setTextCursor(cursor)


@pytest.mark.parametrize("cursor", [3, 4], ids=["leerzeile", "kommentar"])
def test_ohne_sitzung_startet_mit_der_naechsten_anweisung(
    tmp_path: Path, hauptfenster, monkeypatch: pytest.MonkeyPatch, cursor: int
) -> None:  # noqa: ANN001
    datei = tmp_path / "probe.py"
    datei.write_text(QUELLTEXT, encoding="utf-8")
    editor = hauptfenster.datei_oeffnen(datei)
    gestartet: list = []
    monkeypatch.setattr(
        hauptfenster, "_mit_debugger_starten", lambda halten_bei=None: gestartet.append(halten_bei)
    )
    _cursor_auf(editor, cursor)

    hauptfenster._debugger_bis_cursor_aktion()

    assert gestartet == [(datei, 5)]


def test_waehrend_eines_halts_zaehlt_die_zeile_der_datei(
    tmp_path: Path, hauptfenster
) -> None:  # noqa: ANN001
    """Zwei Zeilen darüber eingefügt, nicht gespeichert: das laufende
    Programm kennt `b = a * 2` weiter als Zeile 5."""
    datei = tmp_path / "probe.py"
    datei.write_text(QUELLTEXT, encoding="utf-8")
    editor = hauptfenster.datei_oeffnen(datei)
    _cursor_auf(editor, 1)
    editor.insertPlainText("x = 0\ny = 0\n")
    sitzung = _Sitzung()
    hauptfenster.debug_sitzung = sitzung
    hauptfenster._aktueller_thread_id = 1
    try:
        _cursor_auf(editor, 5)  # die Leerzeile, im Editor jetzt Zeile 5
        hauptfenster._debugger_bis_cursor_aktion()
    finally:
        hauptfenster.debug_sitzung = None
        hauptfenster._aktueller_thread_id = None

    assert sitzung.ziele == [(datei, 5)]
