"""Alles mit der Tastatur allein (M11, Abschnitt 4).

Mit der Maus zu arbeiten ist eine Annahme, keine Selbstverständlichkeit.
An mehreren Stellen war die Maus bis hierher der einzige Weg: Qt meldet
`itemDoubleClicked` nur bei einem echten Doppelklick, nicht bei der
Eingabetaste. Wer den Projekt-Explorer mit Tab erreichte und mit den
Pfeiltasten durchging, kam also nicht weiter – die Datei ging nicht auf.
Dasselbe galt für die Komponentenpalette, den Testbaum, das Panel
„Variablen“ und den Zeileneditor für `items`/`lines` im Objektinspektor.

`itemActivated` meldet **beides**, Doppelklick und Eingabetaste. Die
Tests hier lösen deshalb genau dieses Signal aus – und zwar über eine
echte Tastenbetätigung, nicht über `emit()`, sonst prüften sie nur sich
selbst.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import QSettings, Qt
from PySide6.QtTest import QTest

from ide.inspector import EigenschaftenTabelle
from ide.palette.palette import Komponentenpalette
from ide.shell.explorer import ProjektExplorer
from ide.shell.hauptfenster import HauptFenster
from pcl import Form, ListBox


@pytest.fixture
def einstellungen(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> QSettings:
    datei = QSettings(str(tmp_path / "ide.ini"), QSettings.Format.IniFormat)
    import pcl.pruefungsmodus as modul

    monkeypatch.setattr(modul, "einstellungen", lambda: datei)
    return datei


def _projekt_anlegen(ordner: Path) -> Path:
    ordner.mkdir(parents=True, exist_ok=True)
    (ordner / "main.py").write_text("print('hallo')\n", encoding="utf-8")
    (ordner / "u_hilfe.py").write_text("def rechne(a):\n    return a\n", encoding="utf-8")
    (ordner / "test.natter").write_text(
        json.dumps(
            {
                "format": "natter-project/1",
                "name": "Tastaturtest",
                "type": "console",
                "main": "main.py",
            }
        ),
        encoding="utf-8",
    )
    return ordner


def test_die_eingabetaste_oeffnet_eine_unit_im_explorer(
    einstellungen: QSettings, qtbot, tmp_path: Path
) -> None:
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(_projekt_anlegen(tmp_path / "p"))
    fenster.show()
    vorher = fenster.editor_tabs.count()

    baum: ProjektExplorer = fenster.explorer
    baum.setFocus()
    baum.setCurrentItem(baum.units_gruppe.child(0))
    QTest.keyClick(baum, Qt.Key.Key_Return)

    assert fenster.editor_tabs.count() == vorher + 1


def test_die_eingabetaste_in_der_palette_loest_das_platzieren_aus(
    einstellungen: QSettings, qtbot
) -> None:
    """Ohne offenen Designer sagt Natter, was fehlt – diese Meldung ist
    hier der Beleg, dass die Taste beim Platzieren angekommen ist."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.show()
    palette: Komponentenpalette = fenster.palette

    liste = palette.standard_liste
    liste.setFocus()
    liste.setCurrentRow(0)
    QTest.keyClick(liste, Qt.Key.Key_Return)

    assert "Formular-Designer" in fenster.statusBar().currentMessage()


class _Formular(Form):
    def create_components(self) -> None:
        self.l_auswahl = ListBox(self)


def test_die_eingabetaste_oeffnet_den_zeileneditor(
    qtbot, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`items` und `lines` sind nicht in der Zelle bearbeitbar, sondern
    nur über den Zeileneditor – und der hing allein am Doppelklick."""
    import ide.inspector.eigenschaften_tabelle as modul

    formular = _Formular()
    tabelle = EigenschaftenTabelle()
    qtbot.addWidget(tabelle)
    tabelle.komponente_anzeigen(formular.l_auswahl)

    geoeffnet: list[str] = []

    class _Dialogattrappe:
        DialogCode = modul.SammlungDialog.DialogCode

        def __init__(self, name, zeilen, eltern=None):
            geoeffnet.append(name)

        def exec(self):
            return self.DialogCode.Rejected

    monkeypatch.setattr(modul, "SammlungDialog", _Dialogattrappe)

    zeile = next(
        z for z in range(tabelle.rowCount()) if tabelle.item(z, 0).text() == "items"
    )
    tabelle.setCurrentCell(zeile, 1)
    tabelle.setFocus()
    QTest.keyClick(tabelle, Qt.Key.Key_Return)

    assert geoeffnet == ["items"], "Die Eingabetaste hat den Zeileneditor nicht geöffnet."


def test_jede_stelle_mit_maus_reaktion_reagiert_auch_auf_die_taste(
    einstellungen: QSettings, qtbot
) -> None:
    """Der Rundlauf über alle Listen und Bäume, an denen ein Klick etwas
    auslöst: keiner davon darf nur `itemDoubleClicked` kennen."""
    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    # `receivers()` erwartet die C++-Signatur mit vorangestellter 2
    # (Qts alte SIGNAL()-Schreibweise), die je nach Baum-/Listenart
    # anders lautet.
    listen = (
        (fenster.explorer, "2itemActivated(QTreeWidgetItem*,int)"),
        (fenster.palette.standard_liste, "2itemActivated(QListWidgetItem*)"),
        (fenster.palette.zusaetzlich_liste, "2itemActivated(QListWidgetItem*)"),
        (fenster.meldungen_liste, "2itemActivated(QListWidgetItem*)"),
        (fenster.variablen_baum, "2itemActivated(QTreeWidgetItem*,int)"),
        (fenster.aufrufstapel_liste, "2itemActivated(QListWidgetItem*)"),
        (fenster.tests_baum, "2itemActivated(QTreeWidgetItem*,int)"),
        (
            fenster.objektinspektor.eigenschaften_tabelle,
            "2itemActivated(QTableWidgetItem*)",
        ),
    )

    for widget, signatur in listen:
        name = type(widget).__name__
        assert widget.receivers(signatur) > 0, (
            f"{name} reagiert nicht auf die Eingabetaste"
        )
