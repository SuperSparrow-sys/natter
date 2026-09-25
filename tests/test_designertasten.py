"""Die aufgeschriebenen Designertasten tun wirklich etwas.

Punkt 11 der offenen Punkte. Beim Durchgehen der Texte fiel auf, dass
`docs/handbuch.md` Tasten des Designers beschreibt, die in
der Übersicht unter „Hilfe" fehlten - dort standen nur die Kürzel aus
den Menüs und die des Quelltexteditors. Wer eine Komponente genau
setzen will, schiebt sie deshalb mit der Maus.

Dieselbe Begründung wie bei `EDITORTASTEN`: eine Übersicht, die
etwas Falsches verspricht, schickt jemanden auf die Suche nach einem
Fehler, den es nicht gibt. Jede Zeile wird deshalb hier gegen den
Designer gehalten.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent

from ide.designer.canvas import RASTER, DesignerCanvas
from ide.inspector.komponentenbaum import kind_komponenten
from ide.shell.tastenkuerzel import DESIGNERTASTEN, als_markdown
from pcl import Button, Form


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)
        self.b_ein.left = 100
        self.b_ein.top = 100
        self.b_ein.width = 80
        self.b_ein.height = 30


def _canvas() -> tuple[DesignerCanvas, object]:
    formular = _Formular()
    canvas = DesignerCanvas(formular)
    canvas._auswaehlen(formular.b_ein)
    return canvas, formular.b_ein


def _taste(taste, modifikatoren=Qt.KeyboardModifier.NoModifier) -> QKeyEvent:
    return QKeyEvent(QEvent.Type.KeyPress, taste, modifikatoren)


# -- Jede Zeile der Liste einzeln ----------------------------------------


def test_pfeiltaste_verschiebt_um_ein_raster() -> None:
    canvas, knopf = _canvas()

    assert canvas._tastatur_verarbeiten(_taste(Qt.Key.Key_Right)) is True

    assert knopf.left == 100 + RASTER


def test_alt_pfeiltaste_verschiebt_um_einen_punkt() -> None:
    canvas, knopf = _canvas()

    canvas._tastatur_verarbeiten(
        _taste(Qt.Key.Key_Right, Qt.KeyboardModifier.AltModifier)
    )

    assert knopf.left == 101


def test_umschalt_pfeiltaste_aendert_die_groesse() -> None:
    canvas, knopf = _canvas()
    vorher = knopf.width

    canvas._tastatur_verarbeiten(
        _taste(Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
    )

    assert knopf.width == vorher + RASTER
    assert knopf.left == 100, "verschoben statt vergrößert"


def test_strg_d_dupliziert() -> None:
    canvas, _knopf = _canvas()
    vorher = len(kind_komponenten(canvas.formular))

    canvas._tastatur_verarbeiten(
        _taste(Qt.Key.Key_D, Qt.KeyboardModifier.ControlModifier)
    )

    assert len(kind_komponenten(canvas.formular)) == vorher + 1


def test_entf_loescht() -> None:
    canvas, _knopf = _canvas()
    vorher = len(kind_komponenten(canvas.formular))

    canvas._tastatur_verarbeiten(_taste(Qt.Key.Key_Delete))

    assert len(kind_komponenten(canvas.formular)) == vorher - 1


def test_f2_oeffnet_den_menue_editor_nur_bei_einem_menue() -> None:
    """Bei einem Knopf gibt es nichts zu bearbeiten - dann darf die
    Taste auch nichts abfangen."""
    canvas, _knopf = _canvas()

    assert canvas._tastatur_verarbeiten(_taste(Qt.Key.Key_F2)) is False


# -- Die Liste steht auch in der Übersicht -------------------------------


def test_die_designertasten_stehen_in_der_uebersicht() -> None:
    from ide.actions import Aktionsregister

    text = als_markdown(Aktionsregister())

    assert "Nur im Formular-Designer" in text
    for taste, _zweck in DESIGNERTASTEN:
        assert taste in text, taste


def test_die_liste_ist_vollstaendig_genug() -> None:
    """Sonst prüften die Tests oben eine Liste mit einem Eintrag."""
    assert len(DESIGNERTASTEN) >= 6
