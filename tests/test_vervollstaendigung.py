"""Tests für die Quelltext-Vervollständigung (M11, Abschnitt 2.2).
Headless, gegen echtes jedi.

Zwei Dinge sind hier das Eigentliche und werden deshalb am genauesten
geprüft: die Reihenfolge (die eigenen Komponenten des Formulars
ganz oben) und die deutsche Erklärung zu jedem Eintrag. jedi allein
liefert eine alphabetische Liste nackter Namen – damit ist jemandem,
der gerade anfängt, nicht geholfen.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from ide.shell.quelltexteditor import QuelltextEditor
from ide.shell.vervollstaendigung import (
    MINDESTZEICHEN,
    RANG_DATEI,
    RANG_KOMPONENTE,
    RANG_PCL,
    definition,
    eigene_komponenten,
    parameterhilfe,
    parameterhilfe_anzeige,
    vorschlaege,
)

FORMULAR = """from pcl import Form, Button, Label


class Form1(Form):
    def create_components(self):
        self.b_start = Button(self)
        self.l_ausgabe = Label(self)
        self.zaehler = 0

    def b_start_click(self, sender):
        self.b_start
"""


def _taste(taste, text: str = "", strg: bool = False) -> QKeyEvent:
    return QKeyEvent(
        QEvent.Type.KeyPress,
        taste,
        Qt.KeyboardModifier.ControlModifier if strg else Qt.KeyboardModifier.NoModifier,
        text,
    )


@pytest.fixture
def editor(qtbot) -> QuelltextEditor:
    """Wirklich gezeigt: die Vorschlagsliste hängt seit der
    Sichtprüfung im Viewport statt in einem eigenen Fenster, und ein
    Kind eines unsichtbaren Widgets ist selbst unsichtbar. Ein Test,
    der den Editor nicht zeigt, könnte über `isVisible()` also gar
    nichts aussagen."""
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.setPlainText(FORMULAR)
    editor.resize(700, 420)
    editor.show()
    return editor


def _cursor_ans_ende(editor: QuelltextEditor) -> None:
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor.setTextCursor(cursor)


# -- Was gefunden wird ---------------------------------------------------


def test_die_eigenen_komponenten_werden_erkannt() -> None:
    gefunden = eigene_komponenten(FORMULAR)

    assert gefunden["b_start"] == "Button"
    assert gefunden["l_ausgabe"] == "Label"
    # `self.zaehler = 0` ist keine Komponente - kein Aufruf dahinter
    assert "zaehler" not in gefunden


def test_die_eigenen_komponenten_stehen_ganz_oben() -> None:
    """Der häufigste Fall im Unterricht: `self.` und dann der Name
    einer Komponente, die man selbst aufs Formular gelegt hat."""
    gefunden = vorschlaege(FORMULAR, 11, 13, "u_main.py")

    namen = [v.name for v in gefunden]
    assert namen[:2] == ["b_start", "l_ausgabe"]
    assert all(v.rang == RANG_KOMPONENTE for v in gefunden[:2])


def test_die_eigenschaften_einer_komponente_kommen_danach() -> None:
    quelle = FORMULAR.replace("        self.b_start\n", "        self.b_start.\n")

    gefunden = vorschlaege(quelle, 11, 21, "u_main.py")

    namen = [v.name for v in gefunden]
    assert "caption" in namen
    assert "on_click" in namen
    assert all(v.rang == RANG_PCL for v in gefunden if v.name in ("caption", "width"))


def test_interne_namen_bleiben_draussen() -> None:
    """In Python heißt ein führender Unterstrich „geht dich nichts an“.
    Zwischen `caption` und `width` wären `_qwidget` und
    `_bei_prop_aenderung` nicht nur Rauschen, sondern eine Einladung,
    an den Innereien zu drehen."""
    quelle = FORMULAR.replace("        self.b_start\n", "        self.b_start.\n")

    gefunden = vorschlaege(quelle, 11, 21, "u_main.py")

    assert not [v for v in gefunden if v.name.startswith("_")]


def test_was_sonst_in_der_datei_steht_kommt_zuletzt() -> None:
    gefunden = vorschlaege(FORMULAR, 11, 13, "u_main.py")

    eigene = next(v for v in gefunden if v.name == "b_start_click")
    assert eigene.rang == RANG_DATEI


# -- Die deutsche Erklärung ----------------------------------------------


def test_jede_pcl_eigenschaft_bringt_ihren_deutschen_hilfetext() -> None:
    """jedi findet dazu nichts: die `pcl`-Eigenschaften sind
    Deskriptoren, ihr `doc=` steht nicht im Docstring."""
    quelle = FORMULAR.replace("        self.b_start\n", "        self.b_start.\n")

    gefunden = {v.name: v for v in vorschlaege(quelle, 11, 21, "u_main.py")}

    assert gefunden["caption"].erklaerung == "Beschriftung des Buttons"
    assert "Pixeln" in gefunden["width"].erklaerung
    assert gefunden["on_click"].erklaerung


def test_eine_eigene_komponente_nennt_ihren_typ() -> None:
    """„b_start“ sagt einer Schülerin wenig, „Button auf diesem
    Formular“ sagt ihr, was sie damit machen kann."""
    gefunden = {v.name: v for v in vorschlaege(FORMULAR, 11, 13, "u_main.py")}

    assert gefunden["b_start"].erklaerung == "Button auf diesem Formular"
    assert gefunden["l_ausgabe"].erklaerung == "Label auf diesem Formular"


def test_schluesselwoerter_werden_auf_deutsch_erklaert() -> None:
    """Pythons eigene Hilfe ist englisch und für die Zielgruppe
    unbrauchbar."""
    quelle = "for zahl in range(3):\n    pri"

    gefunden = {v.name: v for v in vorschlaege(quelle, 2, 7)}

    assert "print" in gefunden
    assert gefunden["print"].erklaerung


def test_die_anzeige_zeigt_signatur_und_erklaerung() -> None:
    quelle = FORMULAR.replace("        self.b_start\n", "        self.b_start.\n")

    caption = next(v for v in vorschlaege(quelle, 11, 21, "u_main.py") if v.name == "caption")

    assert "caption" in caption.anzeige
    assert "Beschriftung" in caption.anzeige


# -- Robustheit ----------------------------------------------------------


def test_kaputter_quelltext_unterbricht_die_eingabe_nicht() -> None:
    """Eine halb getippte Zeile ist syntaktisch fast immer kaputt – und
    das ist der Normalfall beim Tippen, nicht die Ausnahme. jedi kommt
    damit selbst zurecht und bietet dann die globalen Namen an; wichtig
    ist nur, dass nichts hochgeht."""
    gefunden = vorschlaege("def (((", 1, 7)

    assert isinstance(gefunden, list)


def test_eine_leere_datei_stuerzt_nicht_ab() -> None:
    assert isinstance(vorschlaege("", 1, 0), list)


def test_ein_fehler_in_jedi_bleibt_folgenlos(monkeypatch: pytest.MonkeyPatch) -> None:
    """Der eigentliche Schutz: geht in der Vervollständigung selbst
    etwas schief, darf die Schülerin davon nichts merken – schon gar
    nicht mitten im Tippen."""
    import jedi

    def _kaputt(*args: object, **kwargs: object) -> None:
        raise RuntimeError("kaputt")

    monkeypatch.setattr(jedi, "Script", _kaputt)

    assert vorschlaege("os.", 1, 3) == []
    assert parameterhilfe("print(", 1, 6) == ""


def test_die_liste_bleibt_kurz() -> None:
    """Eine Liste mit dreihundert Einträgen liest niemand."""
    gefunden = vorschlaege("import os\nos.", 2, 3, hoechstzahl=5)

    assert len(gefunden) <= 5


# -- Parameterhilfe ------------------------------------------------------


def test_die_parameterhilfe_nennt_die_erwarteten_parameter() -> None:
    quelle = "def flaeche(breite, hoehe):\n    return breite * hoehe\n\nflaeche("

    hilfe = parameterhilfe(quelle, 4, 8)

    assert "breite" in hilfe and "hoehe" in hilfe


def test_ohne_klammer_gibt_es_keine_parameterhilfe() -> None:
    assert parameterhilfe("a = 1\n", 1, 5) == ""


# -- Im Editor -----------------------------------------------------------


def test_erst_ab_zwei_zeichen_erscheint_die_liste(editor: QuelltextEditor) -> None:
    """Ab einem Zeichen springt sie ständig auf und stört mehr, als sie
    hilft."""
    editor.setPlainText("import os\no")
    _cursor_ans_ende(editor)

    editor.vorschlaege_anzeigen()

    assert editor.vorschlagsliste.isVisible() is False
    assert MINDESTZEICHEN == 2


def test_ab_zwei_zeichen_erscheint_sie(editor: QuelltextEditor) -> None:
    editor.setPlainText("import os\nos")
    _cursor_ans_ende(editor)

    anzahl = editor.vorschlaege_anzeigen()

    assert anzahl > 0
    assert editor.vorschlagsliste.isVisible() is True


def test_nach_einem_punkt_erscheint_sie_auch_ohne_zeichen(
    editor: QuelltextEditor,
) -> None:
    """Genau dort braucht man sie am meisten."""
    editor.setPlainText(FORMULAR.replace("        self.b_start\n", "        self.b_start.\n"))
    _cursor_ans_ende(editor)
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.Up)
    cursor.movePosition(cursor.MoveOperation.EndOfLine)
    editor.setTextCursor(cursor)

    assert editor.vorschlaege_anzeigen() > 0


def test_escape_schliesst_die_liste(editor: QuelltextEditor) -> None:
    editor.setPlainText("import os\nos")
    _cursor_ans_ende(editor)
    editor.vorschlaege_anzeigen()

    editor.keyPressEvent(_taste(Qt.Key.Key_Escape))

    assert editor.vorschlagsliste.isVisible() is False


def test_eingabe_uebernimmt_statt_eine_zeile_einzufuegen(
    editor: QuelltextEditor,
) -> None:
    """Sonst würde Eingabe eine neue Zeile einfügen und die Liste bliebe
    stehen."""
    editor.setPlainText("zaehlerstand = 1\nzaeh")
    _cursor_ans_ende(editor)
    editor.vorschlaege_anzeigen()
    vorher = editor.document().blockCount()

    editor.keyPressEvent(_taste(Qt.Key.Key_Return))

    assert editor.document().blockCount() == vorher
    assert editor.document().findBlockByNumber(1).text() == "zaehlerstand"
    assert editor.vorschlagsliste.isVisible() is False


def test_das_getippte_wird_ersetzt_nicht_verdoppelt(
    editor: QuelltextEditor,
) -> None:
    editor.setPlainText("zaehlerstand = 1\nzaeh")
    _cursor_ans_ende(editor)
    editor.vorschlaege_anzeigen()

    editor.vorschlag_uebernehmen()

    assert "zaehzaehlerstand" not in editor.toPlainText()


def test_ohne_offene_liste_faengt_eingabe_eine_neue_zeile_an(
    editor: QuelltextEditor,
) -> None:
    """Gegenprobe: die Liste darf die Eingabetaste nur beanspruchen,
    solange sie wirklich offen ist."""
    editor.setPlainText("a = 1")
    _cursor_ans_ende(editor)
    vorher = editor.document().blockCount()

    editor.keyPressEvent(_taste(Qt.Key.Key_Return))

    assert editor.document().blockCount() == vorher + 1


def test_strg_leertaste_erzwingt_die_liste(editor: QuelltextEditor) -> None:
    editor.setPlainText("import os\no")
    _cursor_ans_ende(editor)

    editor.keyPressEvent(_taste(Qt.Key.Key_Space, " ", strg=True))

    assert editor.vorschlagsliste.isVisible() is True


def test_abgeschaltet_erscheint_nichts(editor: QuelltextEditor) -> None:
    editor.setPlainText("import os\nos")
    _cursor_ans_ende(editor)

    editor.vervollstaendigung_setzen(False)

    assert editor.vorschlaege_anzeigen() == 0
    assert editor.vorschlagsliste.isVisible() is False


def test_die_liste_bleibt_im_fenster(editor: QuelltextEditor) -> None:
    """Am unteren Rand klappt sie nach oben auf – sonst stünde sie halb
    außerhalb und wäre nicht zu lesen."""
    editor.setPlainText("import os\n" + "\n" * 40 + "os")
    _cursor_ans_ende(editor)

    editor.vorschlaege_anzeigen()

    rahmen = editor.vorschlagsliste.geometry()
    assert rahmen.top() >= 0
    assert rahmen.bottom() <= editor.viewport().height() + 1
    assert rahmen.right() <= editor.viewport().width() + 1


def test_ein_ereignis_zeigt_seinen_namen_nicht_seinen_typ() -> None:
    """Fund aus der Sichtprüfung: in der Liste stand „NoneType()   –
    Wird beim Klicken ausgelöst“. jedi liefert für ein Ereignis die
    Signatur des Standardwerts (`None`), nicht den Namen – und niemand
    hätte erraten, dass das `on_click` ist."""
    quelle = FORMULAR.replace("        self.b_start\n", "        self.b_start.\n")

    on_click = next(v for v in vorschlaege(quelle, 11, 21, "u_main.py") if v.name == "on_click")

    assert "NoneType" not in on_click.anzeige
    assert on_click.anzeige.startswith("on_click")


# -- Keine Einstellung aus dem Dateisystem (Punkt 277) ------------------


@pytest.mark.parametrize("ort", ["projektordner", "elternordner"])
def test_eine_jedi_einstellung_startet_kein_fremdes_programm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, ort: str
) -> None:
    """Eine `.jedi/project.json` mit `environment_path` im
    Projektordner oder in einem Ordner darüber: jedi startete die dort
    genannte `python.exe`, sobald jemand tippte oder F12 drückte.
    Mitgeschnitten wird jeder Start über `subprocess.Popen`; ein Start
    der Probe wird abgefangen statt ausgeführt."""
    probe = tmp_path / "probe"
    probe.mkdir()
    (probe / "python.exe").write_bytes(b"MZ")
    eltern = tmp_path / "eltern"
    projekt = eltern / "projekt"
    projekt.mkdir(parents=True)
    einstellung = projekt if ort == "projektordner" else eltern
    (einstellung / ".jedi").mkdir()
    (einstellung / ".jedi" / "project.json").write_text(
        json.dumps(
            [1, {"path": str(einstellung), "environment_path": str(probe)}]
        ),
        encoding="utf-8",
    )
    unit = projekt / "u_main.py"
    quelle = (
        "def flaeche(breite, hoehe):\n"
        "    return breite * hoehe\n\n"
        "flaeche(\n"
        "fla"
    )
    unit.write_text(quelle, encoding="utf-8")

    gestartet: list[str] = []
    echtes_popen = subprocess.Popen

    def mitschneiden(args, *weitere, **benannte):  # noqa: ANN001, ANN202
        if isinstance(args, (list, tuple)):
            text = " ".join(map(str, args))
        else:
            text = str(args)
        if str(probe).lower() in text.lower():
            gestartet.append(text)
            raise OSError("Probe wird nicht gestartet")
        return echtes_popen(args, *weitere, **benannte)

    monkeypatch.setattr(subprocess, "Popen", mitschneiden)

    gefunden = vorschlaege(quelle, 5, 3, unit)
    hilfe = parameterhilfe_anzeige(quelle, 4, 8, unit)
    fundstelle = definition(quelle, 4, 1, unit, projekt=projekt)

    assert gestartet == []
    assert "flaeche" in [v.name for v in gefunden]
    assert "breite" in hilfe
    assert fundstelle is not None and fundstelle.zeile == 1
