"""Qts eigene Oberflächentexte auf Deutsch (M11, Abschnitt 4).

Natter ist durchgehend deutsch – bis auf das, was **Qt** selbst
beisteuert, und das ist mehr, als es zunächst aussieht:

* die Tastenkürzel in jedem Menü: „Ctrl+S“ statt „Strg+S“, „Del“ statt
  „Entf“, „Alt+Up“ statt „Alt+Hoch“. Eine Schülerin sucht auf ihrer
  Tastatur nach einer Taste namens „Ctrl“
* die Knöpfe in jedem Standarddialog: „Cancel“ statt „Abbrechen“,
  „Yes“/„No“ statt „Ja“/„Nein“
* der Datei-Öffnen-Dialog, das Kontextmenü jedes Textfelds
  („Undo“/„Redo“/„Select All“), die Rechtschreib- und Suchdialoge

Qt bringt die deutsche Übersetzung mit (`qtbase_de.qm`), lädt sie aber
nicht von selbst. Dieses Modul tut es, einmal beim Start.

**Die Übersetzung muss am Leben bleiben.** Ein `QTranslator`, der nur
in einer lokalen Variablen steht, wird nach `installTranslator` wieder
eingesammelt – die Oberfläche fällt dann ohne Fehlermeldung ins
Englische zurück. Die geladenen Übersetzer stehen deshalb in
`_UEBERSETZER`.
"""

from __future__ import annotations

from PySide6.QtCore import QLibraryInfo, QTranslator
from PySide6.QtWidgets import QApplication

#: Hält die Übersetzer am Leben, solange das Programm läuft.
_UEBERSETZER: list[QTranslator] = []

#: Welche Übersetzungsdateien geladen werden. `qtbase` trägt die
#: Kerntexte (Kürzel, Standardknöpfe, Dateidialog); `qt` ist die
#: Sammeldatei älterer Qt-Fassungen und schadet nicht, wenn sie fehlt.
DATEIEN = ("qtbase_de", "qt_de")


def mehrzahl(anzahl: int, einzahl: str, mehrzahl_form: str | None = None) -> str:
    """„1 Regel", aber „3 Regeln" - die Zahl mit dem passenden Wort.

    Klingt nach einer Kleinigkeit und ist trotzdem der Unterschied
    zwischen einer Oberfläche, die jemand gebaut hat, und einer, die
    Zeichenketten zusammenklebt. In der Statusleiste des
    Diagramm-Editors stand real „2 Zeilen │ 1 Regeln"; bei den
    Layout-Hinweisen daneben war es von Anfang an richtig.

    Ohne `mehrzahl_form` wird ein „n" angehängt - das trägt Regel/Regeln
    und Zeile/Zeilen, nicht aber Form/Formen oder Block/Blöcke; die
    bekommen ihre Mehrzahl mitgegeben.
    """
    wort = einzahl if anzahl == 1 else (mehrzahl_form or f"{einzahl}n")
    return f"{anzahl} {wort}"


def deutsch_einschalten(app: QApplication | None = None) -> int:
    """Lädt Qts deutsche Oberflächentexte. Liefert, wie viele Dateien
    geladen wurden.

    Fehlt die Übersetzung (etwa in einer schlank gepackten Exe), bleibt
    die Oberfläche englisch, aber nichts geht kaputt: Qts Texte sind
    Beiwerk, die Meldungen von Natter selbst stehen ohnehin auf
    Deutsch im Quelltext.
    """
    app = app or QApplication.instance()
    if app is None:
        return 0
    if _UEBERSETZER:
        return len(_UEBERSETZER)

    ordner = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    for name in DATEIEN:
        uebersetzer = QTranslator()
        if uebersetzer.load(name, ordner):
            app.installTranslator(uebersetzer)
            _UEBERSETZER.append(uebersetzer)
    return len(_UEBERSETZER)
