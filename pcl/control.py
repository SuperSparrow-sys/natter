"""Control: Basisklasse aller platzierbaren pcl-Komponenten mit Qt-Anbindung.

Siehe README.md, Abschnitt 5. Verbindet den Prop-Zugriff aus
`pcl.properties` mit einem echten QWidget: eine Zuweisung wie
``self.b_ok.caption = "OK"`` ändert sofort die Anzeige (live). Konkrete
Komponenten (Button, Label, Shape, ...) folgen in M1, Schritt 3.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QWidget

from pcl.font import Font
from pcl.properties import Komponente, Prop


class Control(Komponente):
    """Gemeinsame Basis aller auf einem Formular platzierten Komponenten."""

    #: Ob die Komponente nur im Designer zu sehen ist.
    #:
    #: Manche Komponenten haben nichts anzuzeigen - ein Zeitgeber etwa
    #: tickt nur. Im Designer braucht man sie trotzdem: man muss sie
    #: anklicken können, um im Objektinspektor ihr Intervall
    #: einzustellen. Lazarus löst das seit jeher mit einem kleinen
    #: Symbol auf dem Formular, das im laufenden Programm verschwindet;
    #: genau das macht diese Angabe.
    #:
    #: Der Rest der IDE braucht dafür keine Sonderfälle: solche
    #: Komponenten sind gewöhnliche `Control`s und tauchen damit von
    #: selbst im Komponentenbaum, im Objektinspektor und in der `.pfm`
    #: auf.
    nur_im_designer = False

    left = Prop(int, 0, kategorie="Layout", doc="Position von links in Pixeln")
    top = Prop(int, 0, kategorie="Layout", doc="Position von oben in Pixeln")
    width = Prop(int, 75, kategorie="Layout", doc="Breite in Pixeln")
    height = Prop(int, 25, kategorie="Layout", doc="Höhe in Pixeln")
    enabled = Prop(
        bool, True, kategorie="Verhalten", doc="Legt fest, ob die Komponente bedienbar ist"
    )

    def __init__(self, parent: Komponente | None = None) -> None:
        # `parent=None` für eine Komponente, die im Code erzeugt wird
        # und auf keinem Formular liegt (ein Zeitgeber etwa). Das Widget
        # entsteht trotzdem - so braucht der Rest der Klasse keine
        # Sonderfälle -, es bleibt nur elternlos und ungezeigt.
        eltern_widget: QWidget | None = parent._qwidget if parent is not None else None
        self._font = Font(self)
        self._qwidget: QWidget = self._qwidget_erzeugen(eltern_widget)
        self._geometrie_anwenden()
        self._qwidget.setEnabled(self.enabled)
        if type(self).nur_im_designer:
            # `hide()` ausdrücklich: ein Kind-Widget erscheint sonst
            # von selbst, sobald das Fenster geöffnet wird - der
            # Zeitgeber stünde dann als kleine Uhr im fertigen
            # Schülerprogramm.
            self._qwidget.hide()
        elif parent is not None:
            self._qwidget.show()

    @property
    def font(self) -> Font:
        """Schriftart der Komponente (wie `TFont` in Lazarus), z. B.
        ``self.m_zettel.font.size = 12``."""
        return self._font

    def _eigenes_qss_anwenden(self) -> None:
        """Setzt das komponenteneigene Stylesheet aus allen Beiträgen neu.

        Bündelt Schrift (`font`) und Hintergrundfarbe (`Label.color`,
        `Edit.color`) an einer Stelle: beide schreiben auf dasselbe
        `setStyleSheet` der Komponente und hätten sich sonst gegenseitig
        gelöscht."""
        self._qwidget.setStyleSheet(" ".join(self._qss_teile()))

    def _qss_teile(self) -> list[str]:
        """QSS-Anweisungen dieser Komponente. Unterklassen mit eigener
        Darstellung (z. B. `Label.color`) hängen ihre Anweisungen an."""
        return self._font.qss_teile()

    def _qwidget_erzeugen(self, eltern_widget: QWidget) -> QWidget:
        """Erzeugt das zugehörige QWidget. Von konkreten Komponenten
        überschrieben (z. B. `Button` erzeugt ein `QPushButton`)."""
        raise NotImplementedError("Konkrete Komponenten erzeugen ihr eigenes QWidget")

    def _geometrie_anwenden(self) -> None:
        self._qwidget.setGeometry(self.left, self.top, self.width, self.height)

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        if name in ("left", "top", "width", "height"):
            self._geometrie_anwenden()
        elif name == "enabled":
            self._qwidget.setEnabled(wert)

    def nach_vorne_bringen(self) -> None:
        """Holt die Komponente vor alle überlappenden Geschwister-
        Komponenten (Z-Ebene, wie Lazarus' `BringToFront`) - z. B. ein
        `Label`, das über einer `Shape` liegen soll."""
        self._qwidget.raise_()

    def nach_hinten_schicken(self) -> None:
        """Schickt die Komponente hinter alle überlappenden Geschwister-
        Komponenten (wie Lazarus' `SendToBack`)."""
        self._qwidget.lower()
