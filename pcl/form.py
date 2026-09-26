"""Form: Basisklasse für Fenster.

Siehe README.md, Abschnitt 4.3, 5.2. `create_components()` wird
vom generierten `u_*_design.py` überschrieben und erzeugt beim Aufruf die
Kind-Komponenten (z. B. ``self.b_ein = Button(self)``).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenuBar, QWidget

from pcl.control import _MausFilter
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

    # Die Maus auf der freien Fläche. Ein Formular hatte bis September
    # 2026 nur `on_create`, und wer ein Zeichenprogramm oder ein
    # kleines Spiel bauen wollte, musste ein `Panel` über das ganze
    # Fenster legen und dessen Ereignisse nehmen - ein Umweg, den man
    # kennen muss und der nirgends steht.
    #
    # Die Ereignisse kommen einzeln dazu und nicht über einen Wechsel
    # der Basisklasse: `Control` bringt `left`, `top` und `parent`
    # mit, und nichts davon hat für ein Fenster dieselbe Bedeutung.
    # Der Ereignisfilter aus `pcl/control.py` ist ohnehin allgemein
    # gehalten - er braucht nur `_maus_melden` und
    # `_ereignis_ausloesen`.
    on_click = Event(doc="Klick auf die freie Fläche des Formulars")
    on_double_click = Event(doc="Doppelklick auf die freie Fläche")
    on_mouse_down = Event(doc="Maustaste auf der Fläche gedrückt (x, y)")
    on_mouse_move = Event(doc="Maus über der Fläche bewegt (x, y)")
    on_mouse_up = Event(doc="Maustaste auf der Fläche losgelassen (x, y)")

    #: Der Ereignisfilter prüft das, um ein `on_click` nicht doppelt
    #: zu melden. Ein Formular hat kein eigenes Qt-Signal dafür.
    _klick_kommt_vom_widget = False

    def __init__(self) -> None:
        self._qwidget = QWidget()
        self._menueleiste: QMenuBar | None = None
        self._qwidget.setWindowTitle(self.caption)
        self._qwidget.resize(self.width, self.height)
        self._stylesheet_aktualisieren()

        # Der Filter muss am Objekt hängen bleiben: ein QObject ohne
        # Eltern und ohne Referenz wird eingesammelt, und die
        # Ereignisse kämen nie an. Dieselbe Begründung wie in
        # `pcl/control.py`.
        self._maus_filter = _MausFilter(self)
        self._qwidget.installEventFilter(self._maus_filter)
        # Ohne das meldet Qt eine Bewegung nur bei gedrückter Taste.
        # Eine Positionsanzeige braucht sie aber auch ohne - und wer
        # nur beim Ziehen zeichnen will, fragt im Handler nach.
        self._qwidget.setMouseTracking(True)

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
        if self._menueleiste is not None:
            self._menueleiste.resize(self.width, self._menueleiste.height())

    def _maus_melden(self, name: str, ereignis: Any) -> None:
        """Wie in `Komponente`, aber gezählt ab dem Arbeitsbereich.

        Eine Menüleiste liegt im selben Widget und schiebt jede
        platzierte Komponente um ihre Höhe nach unten - `top = 0` ist
        in Natter der obere Rand unterhalb der Leiste. Die Maus muss
        demselben Maß folgen, sonst zeichnet ein Programm um die Höhe
        der Menüleiste daneben.

        Ein Zeiger über der Menüleiste selbst ergibt ein negatives y.
        Das ist ehrlicher als eine abgeschnittene Null: dort ist die
        Fläche nicht, auf die gezeichnet wird.
        """
        stelle = ereignis.position()
        self._ereignis_ausloesen(
            name, int(stelle.x()), int(stelle.y()) - self._leistenhoehe()
        )

    def _leistenhoehe(self) -> int:
        if self._menueleiste is None:
            return 0
        return self._menueleiste.height()

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
        damit ``Top = 0`` den oberen Rand des Arbeitsbereichs meint und
        nicht den des Fensters. Wer einen Knopf
        an den oberen Rand setzt, findet ihn im laufenden Programm
        auch dort wieder und nicht hinter dem Menü.
        """
        from pcl.components.menus import MENUELEISTE_HOEHE

        menues = self._menue_komponenten()
        if not menues or self._menueleiste is not None:
            return

        leiste = QMenuBar(self._qwidget)
        for menue in menues:
            menue.in_leiste_aufbauen(leiste)
        # Erst die Einträge, dann messen: wie hoch ein Eintrag ist,
        # hängt von Windows-Stil und Schriftgröße ab.
        hoehe = max(MENUELEISTE_HOEHE, leiste.sizeHint().height())
        leiste.setGeometry(0, 0, self._qwidget.width(), hoehe)
        for kind in self._qwidget.findChildren(QWidget, options=Qt.FindDirectChildrenOnly):
            if kind is not leiste:
                kind.move(kind.x(), kind.y() + hoehe)
        self._menueleiste = leiste
        self._groesse_anwenden()
        leiste.show()

    def show(self) -> None:
        self._menueleiste_aufbauen()
        self._qwidget.show()

    def close(self) -> None:
        """Schließt das Fenster."""
        self._qwidget.close()
