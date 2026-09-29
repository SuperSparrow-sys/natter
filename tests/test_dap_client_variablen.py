"""Tests für ide/debugger/dap_client.py: Variablen und Aufrufstapel
(Abschnitt 8.1). Gegen echtes `debugpy`, kein Mock. Siehe
Arbeitspaket M4, Schritt 5.
"""

from __future__ import annotations

from pathlib import Path

from ide.debugger import DapClient

_REPO_WURZEL = Path(__file__).resolve().parent.parent


def _skript_schreiben(tmp_path: Path, inhalt: str) -> Path:
    skript = tmp_path / "ziel.py"
    skript.write_text(inhalt, encoding="utf-8")
    return skript


def test_stapel_variablen_und_ausdruck_an_einem_halt(tmp_path: Path) -> None:
    """Ein Halt zwei Aufrufe tief. Der Aufrufstapel zeigt nur eigenen
    Code, die lokalen Variablen der Modulebene stimmen mit dem
    Programmzustand überein, und ein überwachter Ausdruck wird im
    aktuellen Frame ausgewertet."""
    skript = _skript_schreiben(
        tmp_path,
        "zahl = 42\n"
        'text = "hallo"\n'
        "\n"
        "def innen():\n"
        "    marker = 1  # Zeile 5, Breakpoint\n"
        "    return marker\n"
        "\n"
        "def aussen():\n"
        "    return innen()\n"
        "\n"
        "aussen()\n",
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [5]})
        ereignis = client.angehalten_abwarten()

        stapel = client.aufrufstapel_lesen(ereignis["threadId"])
        namen = [frame["name"] for frame in stapel]
        assert namen == ["innen", "aussen", "<module>"]
        assert all(Path(f["source"]["path"]) == skript for f in stapel)

        bereiche = client.bereiche_lesen(stapel[-1]["id"])
        locals_bereich = next(b for b in bereiche if b["name"] == "Locals")
        variablen = client.variablen_lesen(locals_bereich["variablesReference"])
        werte = {v["name"]: v["value"] for v in variablen}
        assert werte["zahl"] == "42"
        assert werte["text"] == "'hallo'"

        ergebnis = client.auswerten("zahl + 1", stapel[0]["id"])
        assert ergebnis["result"] == "43"
    finally:
        client.beenden()


def test_komponenten_variablen_zeigen_nur_props_und_events(tmp_path: Path) -> None:
    skript = _skript_schreiben(
        tmp_path,
        "import sys\n"
        f"sys.path.insert(0, {str(_REPO_WURZEL)!r})\n"
        "from PySide6.QtWidgets import QApplication\n"
        "from pcl import Form, Button\n\n"
        "app = QApplication([])\n\n"
        "class MeinFormular(Form):\n"
        "    def create_components(self) -> None:\n"
        "        self.b_ein = Button(self)\n"
        "        self.b_ein.caption = 'Einschalten'\n\n"
        "formular = MeinFormular()\n"
        "marker = 1  # Breakpoint-Zeile\n",
    )
    client = DapClient()
    try:
        client.starten(skript, arbeitsordner=tmp_path, anfangs_breakpoints={skript: [14]})
        ereignis = client.angehalten_abwarten()
        stapel = client.aufrufstapel_lesen(ereignis["threadId"])
        bereiche = client.bereiche_lesen(stapel[0]["id"])
        locals_bereich = next(b for b in bereiche if b["name"] == "Locals")
        variablen = client.variablen_lesen(locals_bereich["variablesReference"])
        formular_var = next(v for v in variablen if v["name"] == "formular")

        gefiltert = client.komponenten_variablen_lesen(formular_var["variablesReference"])

        namen = {v["name"] for v in gefiltert}
        assert "caption" in namen
        assert "width" in namen
        assert "on_create" in namen
        assert "_qwidget" not in namen
        assert "neue_attribute_erlaubt" not in namen
        assert "special variables" not in namen
    finally:
        client.beenden()
