"""Form: Basisklasse für Fenster.

Siehe README.md, Abschnitt 4.3, 5.2. `create_components()` wird
vom generierten `u_*_design.py` überschrieben und erzeugt beim Aufruf die
Kind-Komponenten (z. B. ``self.b_ein = Button(self)``).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenuBar, QWidget

from pcl.properties import Event, Komponente, Prop
from pcl.theme import qss_erzeugen


class Form(Komponente):
    """Basisklasse aller Formulare.

    Eigene Attribute (``self.ampel = Ampel()``) bleiben erlaubt – die
    Sperre gegen unbekannte Eigenschaften aus `Komponente` gilt nur für
    Komponenten, die auf dem Formular platziert werden (Abschnitt 5.0).
    """

    neue_attribute_erlaubt = True

    caption = Prop(str, "Form1", kategorie="Darstellung", doc="Fenstertitel")
    width = Prop(int, 480, kategorie="Layout", doc="Fensterbreite in Pixeln")
    height = Prop(int, 360, kategorie="Layout", doc="Fensterhöhe in Pixeln")
    theme = Prop(
        str, "system", kategorie="Darstellung", doc="Farbschema: system, light oder dark"
    )
    color = Prop(
        str, "", kategorie="Darstellung", doc="Hintergrundfarbe als #RRGGBB, leer = Theme-Standard"
    )

    on_create = Event(doc="Wird unmittelbar vor der ersten Anzeige ausgelöst")

    def __init__(self) -> None:
        self._qwidget = QWidget()
        self._menueleiste: QMenuBar | None = None
        self._qwidget.setWindowTitle(self.caption)
        self._qwidget.resize(self.width, self.height)
        self._stylesheet_aktualisieren()
        self.create_components()
        if self.on_create is not None:
            self.on_create(self)

    def _stylesheet_aktualisieren(self) -> None:
        # `color` wird als zweiter, für "QWidget" spezifischerer Regelblock
        # angehängt statt die Eigenschaft in qss_erzeugen() einzumischen -
        # überschreibt bei Bedarf nur background-color, der Rest des
        # Theme-Stylesheets bleibt unangetastet.
        stylesheet = qss_erzeugen(self.theme)
        if self.color:
            stylesheet += f"\nQWidget {{ background-color: {self.color}; }}"
        self._qwidget.setStyleSheet(stylesheet)

    def create_components(self) -> None:
        """Erzeugt die Kind-Komponenten. Wird vom generierten
        `u_*_design.py` überschrieben (Abschnitt 4.3)."""

    def _bei_prop_aenderung(self, name: str, wert: Any) -> None:
        if name == "caption":
            self._qwidget.setWindowTitle(wert)
        elif name in ("width", "height"):
            self._groesse_anwenden()
        elif name in ("theme", "color"):
            self._stylesheet_aktualisieren()

    def _groesse_anwenden(self) -> None:
        """Setzt die Fenstergröße aus `width`/`height`.

        `height` ist die Höhe des Arbeitsbereichs, wie `top` bei
        einer Komponente. Liegt ein Menü auf dem Formular, kommt seine
        Leiste obendrauf – sonst schrumpfte das Fenster bei einem
        `self.height = 400` zur Laufzeit um die Leistenhöhe, und die
        unterste Zeile verschwände.
        """
        self._qwidget.resize(self.width, self.height + self._leistenhoehe())

    def _leistenhoehe(self) -> int:
        from pcl.components.menus import MENUELEISTE_HOEHE

        return MENUELEISTE_HOEHE if self._menueleiste is not None else 0

    def _menue_komponenten(self) -> list[Any]:
        """Die `MainMenu`-Komponenten auf diesem Formular.

        Der Import steht in der Methode, nicht oben: `pcl.components`
        baut auf `pcl.form` auf, und ein Import in die andere Richtung
        wäre ein Ring.
        """
        from pcl.components.menus import MainMenu

        return [wert for wert in vars(self).values() if isinstance(wert, MainMenu)]

    def _menueleiste_aufbauen(self) -> None:
        """Baut die Menüleiste, falls ein `MainMenu` auf dem Formular
        liegt – und verschiebt den Arbeitsbereich um ihre Höhe nach
        unten.

        Warum erst hier und nicht, sobald das Menü erzeugt wird: zu
        diesem Zeitpunkt stehen alle Komponenten fest. Würde die
        Leiste schon beim Erzeugen des Menüs Platz schaffen, käme es
        darauf an, ob das Menü vor oder nach den Knöpfen angelegt
        wurde – und `create_components()` legt sie in der Reihenfolge
        an, in der sie zufällig in der `.pfm` stehen.

        Verschoben wird der Inhalt statt die Leiste darüberzulegen,
        weil Lazarus es genauso macht: ``Top = 0`` ist dort der obere
        Rand des Arbeitsbereichs, nicht des Fensters. Wer einen Knopf
        an den oberen Rand setzt, findet ihn im laufenden Programm
        auch dort wieder und nicht hinter dem Menü.
        """
        from pcl.components.menus import MENUELEISTE_HOEHE

        menues = self._menue_komponenten()
        if not menues or self._menueleiste is not None:
            return

        self._menueleiste = QMenuBar(self._qwidget)
        self._menueleiste.setGeometry(0, 0, self._qwidget.width(), MENUELEISTE_HOEHE)
        for kind in self._qwidget.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
            if kind is not self._menueleiste:
                kind.move(kind.x(), kind.y() + MENUELEISTE_HOEHE)
        self._groesse_anwenden()
        self._menueleiste.show()

        for menue in menues:
            menue.in_leiste_aufbauen(self._menueleiste)

    def show(self) -> None:
        self._menueleiste_aufbauen()
        self._qwidget.show()

    def close(self) -> None:
        """Entspricht `Close` aus der LCL."""
        self._qwidget.close()
