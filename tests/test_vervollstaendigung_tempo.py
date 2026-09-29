"""Tippen in einer langen Unit bleibt flüssig (Punkt 313).

Bis 0.3.6 rechnete jedi nach jedem Buchstaben die Vorschläge im
Hauptfaden aus und las dafür die ganze Datei. In einer Unit mit 5.000
Zeilen kostete jeder Tastendruck im Median 310 ms, einzelne bis 1,5 s.
Jetzt wartet der Editor eine kurze Tipp-Pause ab und rechnet in einem
Nebenfaden; ein Ergebnis, das nicht mehr zum Text passt, verfällt.
"""

from __future__ import annotations

import statistics
import time

import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtTest import QTest

from ide.shell import vervollstaendigung as v
from ide.shell.quelltexteditor import QuelltextEditor

#: Was getippt wird. Ein Name mit zwei Punkten, wie er in einem
#: Formular ständig vorkommt.
EINGABE = "self.l_ausgabe.cap"


def _unit(zeilen: int) -> str:
    """Eine Unit mit der Klasse `Form1`, zwei Komponenten und so vielen
    Methoden, dass `zeilen` Zeilen zusammenkommen. Am Ende steht eine
    angefangene Methode, in deren Rumpf getippt wird."""
    teile = [
        "from pcl import Button, Form, Label",
        "",
        "",
        "class Form1(Form):",
        "    def __init__(self) -> None:",
        "        super().__init__()",
        "        self.l_ausgabe = Label(self)",
        "        self.b_start = Button(self)",
        "",
    ]
    nummer = 0
    while len(teile) < zeilen - 2:
        teile += [
            f"    def methode_{nummer}(self, wert: int) -> int:",
            f"        ergebnis = wert * {nummer}",
            "        self.l_ausgabe.caption = str(ergebnis)",
            "        return ergebnis",
            "",
        ]
        nummer += 1
    teile += ["    def neu(self) -> None:", "        "]
    return "\n".join(teile)


def _warten(ms: int) -> None:
    """Wartet in einer echten Ereignisschleife wie `app.exec()`.

    `QTest.qWait` und `qtbot.waitUntil` geben die Sperre des
    Interpreters in der Wartezeit nicht ab; der Nebenfaden mit jedi
    käme dabei kaum voran, und der Test sähe das Tippen während der
    Rechnung gar nicht.
    """
    schleife = QEventLoop()
    QTimer.singleShot(ms, schleife.quit)
    schleife.exec()


def _zeilen(editor: QuelltextEditor) -> list[str]:
    liste = editor.vorschlagsliste
    return [liste.item(i).text() for i in range(liste.count())]


@pytest.mark.timeout(300)
def test_ein_tastendruck_wartet_nicht_auf_jedi(qtbot) -> None:  # noqa: ANN001
    # Den ersten, langsamen Aufruf von jedi vorwegnehmen, wie es das
    # Aufwärmen beim Start von Natter tut.
    v.vorschlaege("pri", 1, 3)
    editor = QuelltextEditor()
    qtbot.addWidget(editor)
    editor.resize(700, 400)
    editor.show()
    editor.setPlainText(_unit(5000))
    cursor = editor.textCursor()
    cursor.movePosition(cursor.MoveOperation.End)
    editor.setTextCursor(cursor)
    assert editor.blockCount() >= 5000

    dauer = []
    for nummer, zeichen in enumerate(EINGABE):
        beginn = time.perf_counter()
        QTest.keyClick(editor, zeichen)
        dauer.append(time.perf_counter() - beginn)
        # Nach jedem vierten Zeichen eine Pause wie beim Nachdenken:
        # dann rechnet jedi im Hintergrund, während schon die nächsten
        # Zeichen kommen.
        _warten(250 if nummer % 4 == 3 else 30)

    median = statistics.median(dauer)
    groesste = max(dauer)
    messwerte = ", ".join(f"{d * 1000:.0f}" for d in dauer)
    assert median < 0.030, f"Median {median * 1000:.0f} ms ({messwerte})"
    assert groesste < 0.100, f"Höchstwert {groesste * 1000:.0f} ms ({messwerte})"

    # Nach der Pause erscheint die Liste weiterhin, mit dem Richtigen
    # oben.
    ende = time.monotonic() + 30
    while not editor.vorschlagsliste.isVisible() and time.monotonic() < ende:
        _warten(20)
    assert editor.vorschlagsliste.isVisible()
    assert editor.textCursor().block().text().endswith(EINGABE)
    assert _zeilen(editor)[0].startswith("caption")
