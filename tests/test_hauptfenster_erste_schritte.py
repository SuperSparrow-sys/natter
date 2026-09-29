"""Start aus dem Hauptfenster bei zwei Fehlern aus dem ersten Jahr
(Punkte 289 und 290): das Programm startet nicht, und das Panel
„Meldungen“ sagt, was fehlt.

Die Projekte entstehen aus den echten Vorlagen in `tmp_path`.
"""

from __future__ import annotations

import json
from pathlib import Path

from ide.designer.canvas import editortext_ersetzen
from ide.project.neu import projekt_erzeugen


def _meldungen(fenster) -> list[str]:  # noqa: ANN001
    liste = fenster.meldungen_liste
    return [liste.item(i).text() for i in range(liste.count())]


def test_ohne_def_main_startet_nichts_und_die_meldung_nennt_main(
    tmp_path: Path, hauptfenster
) -> None:  # noqa: ANN001
    """Bis 0.3.5 lief das Programm erst durch und meldete danach, die
    Unit „u_main“ lasse sich nicht laden. Jetzt startet es gar nicht:
    kein Prozess, also auch keine Ausgabe davor."""
    projekt = projekt_erzeugen("console", tmp_path / "p", "Hallo")
    (projekt.ordner / "u_main.py").write_text(
        'name = input("Name? ")\nprint("Hallo", name)\n', encoding="utf-8"
    )
    hauptfenster.projekt_oeffnen(projekt.ordner / "Hallo.natter")

    hauptfenster._projekt_starten_aktion()

    assert hauptfenster.laufender_prozess is None
    meldungen = _meldungen(hauptfenster)
    assert len(meldungen) == 1
    assert meldungen[0].startswith("u_main.py, Zeile 1:")
    assert "keine Funktion oder Klasse main" in meldungen[0]
    assert "nicht gestartet" in hauptfenster.statusBar().currentMessage()


def _fenster_projekt(ordner: Path) -> Path:
    projekt = projekt_erzeugen("gui", ordner, "Fenster")
    pfm_pfad = projekt.ordner / "u_main.pfm"
    pfm = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    pfm["children"].append(
        {
            "name": "button",
            "type": "Button",
            "properties": {"left": 10, "top": 10},
            "events": {"on_click": "button_click"},
        }
    )
    pfm_pfad.write_text(json.dumps(pfm), encoding="utf-8")
    return projekt.ordner


def test_nach_rueckgaengig_im_editor_startet_nichts_und_doppelklick_hilft(
    tmp_path: Path, hauptfenster
) -> None:  # noqa: ANN001
    """Der Designer fügt die Methode als gewöhnliche Bearbeitung in den
    Editor ein; Strg+Z nimmt sie wieder weg, die Verknüpfung in der
    `.pfm` bleibt. Die Prüfung vor dem Start nennt die Methode, und
    der Doppelklick auf die Komponente legt sie wieder an, auch wenn
    sie schon aus der Datei verschwunden ist."""
    ordner = _fenster_projekt(tmp_path / "p")
    unit = ordner / "u_main.py"
    hauptfenster.projekt_oeffnen(ordner / "Fenster.natter")
    editor = hauptfenster.datei_oeffnen(unit)
    ohne = editor.toPlainText()
    editortext_ersetzen(
        editor,
        ohne.replace(
            "    pass",
            "    def button_click(self, sender) -> None:\n        pass",
        ),
    )
    assert "def button_click" in editor.toPlainText()
    editor.undo()
    assert "def button_click" not in editor.toPlainText()

    hauptfenster._projekt_starten_aktion()

    assert hauptfenster.laufender_prozess is None
    meldungen = _meldungen(hauptfenster)
    assert len(meldungen) == 1
    assert "button_click" in meldungen[0]
    assert "on_click" in meldungen[0]
    assert "def button_click" not in unit.read_text(encoding="utf-8")

    # So ruft der Designer nach einem Doppelklick auf den Knopf an,
    # wenn die Verknüpfung schon besteht.
    hauptfenster._zur_methode_springen(unit, "Form1", "button_click", ())

    assert "def button_click(self, sender)" in editor.toPlainText()
    assert editor.document().isModified()
