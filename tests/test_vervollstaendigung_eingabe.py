"""Die Vervollständigung beim Tippen: vom Anfang eines Namens bis in die
Klammern hinein.

Gewünscht war: bei `pri` schon `print(` anbieten, bei `bank_ab` die
eigene Funktion `bank_abheben_konto` samt Parametern, und beim Tippen
in die Klammern hinein zeigen, welche Parameter mit welchem Typ
erwartet werden. Im Prüfungsmodus nichts davon.
"""

from __future__ import annotations

import pytest
from PySide6.QtTest import QTest

from ide.shell import vervollstaendigung as v
from ide.shell.quelltexteditor import QuelltextEditor

QUELLTEXT = '''def bank_abheben_konto(konto: str, betrag: float) -> bool:
    """Hebt einen Betrag vom Konto ab."""
    return betrag > 0


'''


def _editor(qtbot, text: str = QUELLTEXT) -> QuelltextEditor:  # noqa: ANN001
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.resize(700, 400)
    editor.show()
    editor.setPlainText(text)
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor.setTextCursor(cursor)
    return editor


def _zeilen(editor: QuelltextEditor) -> list[str]:
    liste = editor.vorschlagsliste
    return [liste.item(i).text() for i in range(liste.count())]


# --------------------------------------------- Die Liste


def test_pri_bietet_print_an(qtbot) -> None:  # noqa: ANN001
    editor = _editor(qtbot)

    QTest.keyClicks(editor, "pri")

    assert editor.vorschlagsliste.isVisible()
    assert _zeilen(editor)[0].startswith("print(")


def test_die_eigene_funktion_steht_mit_parametern_da(qtbot) -> None:  # noqa: ANN001
    editor = _editor(qtbot)

    QTest.keyClicks(editor, "bank_ab")

    assert _zeilen(editor)[0].startswith("bank_abheben_konto(konto: str, betrag: float)")


def test_die_eigene_erklaerung_steht_daneben(qtbot) -> None:  # noqa: ANN001
    """Der Docstring der eigenen Funktion ist deutsch - den hat die
    Schülerin selbst geschrieben."""
    editor = _editor(qtbot)

    QTest.keyClicks(editor, "bank_ab")

    assert "Hebt einen Betrag vom Konto ab." in _zeilen(editor)[0]


def test_python_selbst_spricht_nicht_englisch() -> None:
    """jedi liefert die Hilfetexte der Standardbibliothek auf Englisch.
    Neben `print` stand „Prints the values to a stream, or to
    sys.stdout by default." - in einer Oberfläche, in der sonst alles
    deutsch ist."""
    gefunden = v.vorschlaege("pri", 1, 3)

    assert gefunden[0].name == "print"
    assert "Prints" not in gefunden[0].erklaerung
    assert gefunden[0].erklaerung == v.PYTHON_HILFE["print"]


def test_ohne_deutsche_erklaerung_bleibt_es_bei_der_unterschrift() -> None:
    """Lieber keine Erklärung als eine englische."""
    gefunden = [g for g in v.vorschlaege("import math\nmath.fl", 2, 7) if g.name == "floor"]

    assert gefunden
    assert gefunden[0].erklaerung == ""


# --------------------------------------------- Übernehmen


def test_eine_funktion_kommt_mit_klammern(qtbot) -> None:  # noqa: ANN001
    editor = _editor(qtbot)
    QTest.keyClicks(editor, "pri")

    editor.vorschlag_uebernehmen()

    zeile = editor.textCursor().block().text()
    assert zeile == "print()"
    assert editor.textCursor().positionInBlock() == len("print(")


def test_eine_vorhandene_klammer_wird_nicht_verdoppelt(qtbot) -> None:  # noqa: ANN001
    """Wer vor einer schon stehenden Klammer einen Namen austauscht,
    will keine zweite."""
    editor = _editor(qtbot, QUELLTEXT + "(1)")
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.StartOfBlock)
    editor.setTextCursor(cursor)
    QTest.keyClicks(editor, "pri")

    editor.vorschlag_uebernehmen()

    assert editor.textCursor().block().text() == "print(1)"


def test_eine_variable_kommt_ohne_klammern(qtbot) -> None:  # noqa: ANN001
    editor = _editor(qtbot, "kontostand = 5\n")
    QTest.keyClicks(editor, "kont")

    editor.vorschlag_uebernehmen()

    assert editor.textCursor().block().text() == "kontostand"


# --------------------------------------------- In den Klammern


def test_die_klammer_zeigt_die_parameter(qtbot) -> None:  # noqa: ANN001
    """Beim Tippen von `(` schließt der Editor die Klammer selbst. Bis
    September 2026 war der Tastendruck damit erledigt, und die
    Parameterhilfe, die an ihm hing, kam nie an die Reihe."""
    editor = _editor(qtbot)

    QTest.keyClicks(editor, "bank_abheben_konto(")

    assert "betrag: float" in editor.letzte_parameterhilfe


def test_der_aktuelle_parameter_ist_hervorgehoben(qtbot) -> None:  # noqa: ANN001
    editor = _editor(qtbot)

    QTest.keyClicks(editor, 'bank_abheben_konto("A", ')

    assert "<b><u>betrag: float</u></b>" in editor.letzte_parameterhilfe
    assert "<b><u>konto" not in editor.letzte_parameterhilfe


def test_die_parameterhilfe_nennt_rueckgabe_und_erklaerung() -> None:
    hilfe = v.parameterhilfe_anzeige(QUELLTEXT + "bank_abheben_konto(", 6, 19)

    assert "→ bool" in hilfe
    assert "Hebt einen Betrag vom Konto ab." in hilfe


def test_ohne_typangabe_steht_nur_der_name() -> None:
    """Ohne Annotation kennt niemand den Typ - erfunden wird keiner."""
    code = "def zahlen(a, b=2):\n    return a\n\nzahlen("

    hilfe = v.parameterhilfe_anzeige(code, 4, 7)

    assert "<b><u>a</u></b>" in hilfe
    assert "b=2" in hilfe


# --------------------------------------------- Prüfungsmodus und Tempo


def test_im_pruefungsmodus_zeigt_die_klammer_nichts(
    qtbot, monkeypatch: pytest.MonkeyPatch  # noqa: ANN001
) -> None:
    import ide.shell.quelltexteditor as editor_modul

    monkeypatch.setattr(editor_modul, "pruefungsmodus_laeuft", lambda: True)
    editor = _editor(qtbot)

    QTest.keyClicks(editor, "bank_abheben_konto(")

    assert editor.letzte_parameterhilfe == ""
    assert not editor.vorschlagsliste.isVisible()


def test_das_aufwaermen_laeuft_nur_einmal(monkeypatch: pytest.MonkeyPatch) -> None:
    """jedi braucht beim ersten Aufruf ein bis zwei Sekunden. Das
    Aufwärmen nimmt sie beim Start im Hintergrund vorweg - einmal je
    Programmlauf, nicht bei jedem Fenster."""
    gestartet: list[bool] = []
    monkeypatch.setattr(v, "_aufgewaermt", False)
    monkeypatch.setattr(v, "_aufwaermen_im_hintergrund", lambda: gestartet.append(True))

    v.aufwaermen()
    v.aufwaermen()

    assert gestartet == [True]
