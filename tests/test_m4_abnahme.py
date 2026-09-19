"""Abnahmetest für M4 (docs/arbeitspakete/M4.md, Schritt 8): für jeden
Fehlerkatalog-Eintrag ein Beispielprogramm, das genau diesen Fehler
auslöst; ein Beispielprojekt (Ampel) mit Breakpoint in einem
Ereignis-Handler anhalten und Variablen prüfen. Die dritte
Abnahme-Anforderung („Testdatei mit Soll-/Ist-Anzeige im Test-Explorer“)
ist bereits durch `tests/test_hauptfenster_testexplorer.py` vollständig
abgedeckt, wird hier nicht dupliziert.

Gegen echtes `debugpy`, kein Mock. Die Ampel-Beispieldatei wird wie in
AGENTS.md vorgeschrieben aus `beispielprojekte/04_CookieKlicker/` in `tmp_path`
kopiert statt sie direkt zu verwenden.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from ide.debugger import fehlermeldung_erzeugen
from ide.shell.hauptfenster import HauptFenster
from tests.conftest import DEBUG_ZEITGRENZE

_PROJEKT_ORDNER = Path(__file__).resolve().parent.parent / "beispielprojekte" / "04_CookieKlicker"


def _ausloesen(f):
    try:
        f()
    except BaseException as fehler:  # noqa: BLE001 - genau das wird geprüft
        return fehler
    raise AssertionError("f() hat keine Ausnahme ausgelöst")


def _unbound_local_beispiel():
    x = x + 1  # noqa: F821 - genau das soll UnboundLocalError auslösen
    return x


# Ein Beispielprogramm je Katalogeintrag aus Schritt 2 (Abschnitt 8.5,
# MVP-Auszug) - jedes löst genau diesen Fehler aus.
_BEISPIELE = {
    "ZeroDivisionError": lambda: 1 / 0,
    "UnboundLocalError": _unbound_local_beispiel,
    "NameError": lambda: _nicht_definiert,  # noqa: F821
    "AttributeError": lambda: (1).nicht_vorhanden,
    "TypeError": lambda: "text" + 1,
    "ValueError": lambda: int("abc"),
    "IndexError": lambda: [1, 2][10],
    "KeyError": lambda: {"a": 1}["b"],
    "FileNotFoundError": lambda: open("es_gibt_mich_nicht.txt", encoding="utf-8"),
    "UnicodeDecodeError": lambda: b"\xff\xfe".decode("utf-8"),
    "SyntaxError": lambda: compile("def f(:\n pass\n", "<test>", "exec"),
}


def test_jeder_fehlerkatalog_eintrag_hat_ein_funktionierendes_beispielprogramm() -> None:
    for name, beispiel in _BEISPIELE.items():
        meldung = fehlermeldung_erzeugen(_ausloesen(beispiel))
        assert meldung is not None, f"kein Katalogeintrag für {name}"
        assert name in meldung.ueberschrift
        assert meldung.was
        assert meldung.pruefe
        assert "did you mean" not in meldung.was.lower()


def test_breakpoint_in_ereignis_handler_haelt_an_und_zeigt_self(
    qtbot, tmp_path: Path
) -> None:
    kopie = tmp_path / "04_CookieKlicker"
    shutil.copytree(_PROJEKT_ORDNER, kopie)

    fenster = HauptFenster()
    fenster.projekt_oeffnen(kopie / "04_CookieKlicker.natter")

    # form_create() läuft automatisch beim Start, ohne Klick nötig -
    # exakt "Breakpoint in einem Ereignis-Handler" aus der Abnahme.
    u_main = kopie / "u_main.py"
    editor = fenster.datei_oeffnen(u_main)
    zeile = next(
        i + 1
        for i, zeile in enumerate(u_main.read_text(encoding="utf-8").split("\n"))
        if "self.neu_anfangen()" in zeile
    )
    editor.breakpoint_umschalten(zeile)

    fenster._projekt_mit_debugger_starten_aktion()
    qtbot.waitUntil(lambda: fenster._aktueller_thread_id is not None, timeout=DEBUG_ZEITGRENZE)

    try:
        # Der Grund steht auf Deutsch da (M11, Abschnitt 4); das DAP
        # liefert ihn als „breakpoint“.
        assert "Angehalten: an einem Haltepunkt" in fenster.statusBar().currentMessage()
        qtbot.waitUntil(
        lambda: fenster.variablen_baum.topLevelItemCount() > 0,
        timeout=DEBUG_ZEITGRENZE,
    )

        namen = [
            fenster.variablen_baum.topLevelItem(i).text(0)
            for i in range(fenster.variablen_baum.topLevelItemCount())
        ]
        assert "self" in namen
    finally:
        fenster._debugger_stoppen_aktion()
