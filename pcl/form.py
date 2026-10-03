"""Form: Basisklasse für Fenster.

Siehe README.md, Abschnitt 4.3, 5.2. `create_components()` wird
vom generierten `u_*_design.py` überschrieben und erzeugt beim Aufruf die
Kind-Komponenten (z. B. ``self.b_ein = Button(self)``).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QEvent, QEventLoop, QObject, QPoint, Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import QMenuBar, QWidget

from pcl import taskleiste
from pcl.control import _MausFilter
from pcl.properties import ART_BILD, ART_FARBE, Event, Komponente, Prop
from pcl.theme import qss_erzeugen

#: Die Werte von `Form.position`: mitten auf den Bildschirm oder an
#: die Stelle, die `left` und `top` angeben.
POSITIONEN = ("screen_center", "designed")

#: Die gezeigten Formulare, bis sie geschlossen werden. Ohne diesen
#: Verweis räumte die Speicherbereinigung ein Formular ab, das nur in
#: einer einfachen Variablen stand, und das Fenster verschwände zu
#: einem beliebigen späteren Zeitpunkt (Punkt 214). Schlüssel ist
#: `id(formular)`.
_offene_formulare: dict[int, Form] = {}


class _FensterFilter(_MausFilter):
    """Der Filter aus `pcl/control.py`, dazu das Schließen des
    Fensters. Nur ein Fenster wird geschlossen; eine Komponente
    bekommt dieses Ereignis nie.

    Verschwindet das Fenster, endet auch ein laufendes `show_modal()`.
    Liefert `on_close` den Wert False, bleibt es offen.
    """

    def eventFilter(self, objekt: QObject, ereignis: QEvent) -> bool:  # noqa: N802
        if self._control is None:
            return False
        if ereignis.type() == QEvent.Type.Close:
            # Gibt `on_close` False zurück, bleibt das Fenster offen:
            # die Rückfrage „Wirklich beenden?“ braucht das.
            if self._control._ereignis_ausloesen("on_close") is False:
                ereignis.ignore()
                return True
        elif ereignis.type() in (QEvent.Type.Resize, QEvent.Type.Move):
            self._control._fensterlage_uebernehmen()
        elif ereignis.type() == QEvent.Type.Hide:
            # Über `getattr`: beim Einsammeln einer Formularklasse, die
            # in einer Funktion entstand, räumt Python die Klasse vor
            # dem Fenster ab, und die Methode ist nicht mehr zu finden.
            beenden = getattr(self._control, "_modal_beenden", None)
            if beenden is not None:
                beenden()
            geschlossen = getattr(self._control, "_geschlossen", None)
            if geschlossen is not None:
                geschlossen()
        return super().eventFilter(objekt, ereignis)


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
        str,
        "system",
        kategorie="Darstellung",
        doc="Farbschema: system, light oder dark",
        werte=("system", "light", "dark"),
    )
    color = Prop(
        str,
        "",
        kategorie="Darstellung",
        doc="Hintergrundfarbe als #RRGGBB, leer = Theme-Standard",
        art=ART_FARBE,
    )
    position = Prop(
        str,
        "screen_center",
        kategorie="Layout",
        doc="Wo das Fenster erscheint: screen_center (Bildschirmmitte) "
        "oder designed (an left und top)",
        werte=POSITIONEN,
    )
    left = Prop(
        int,
        0,
        kategorie="Layout",
        doc="Abstand des Fensters vom linken Bildschirmrand in Pixeln "
        "(bei position = designed)",
    )
    top = Prop(
        int,
        0,
        kategorie="Layout",
        doc="Abstand des Fensters vom oberen Bildschirmrand in Pixeln "
        "(bei position = designed)",
    )
    icon = Prop(
        str,
        "",
        kategorie="Darstellung",
        doc="Bilddatei für das Fenstersymbol, z. B. assets/symbol.png",
        art=ART_BILD,
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

    # Die Tastatur. Das Formular hört jede Taste in seinem Fenster,
    # auch wenn gerade ein Eingabefeld oder ein Knopf den Fokus hat;
    # eine Komponente hört nur die Tasten, die sie selbst mit dem
    # Fokus bekommt. Beide melden sich, zuerst das Formular. Ein
    # Spiel mit Pfeiltasten schreibt seinen Handler deshalb an das
    # Formular und nicht an die Spielfigur.
    on_key_press = Event(
        doc="Tastendruck irgendwo im Fenster; bekommt den Namen der Taste"
    )
    on_close = Event(doc="Wird beim Schließen des Fensters ausgelöst")

    #: Was ein Doppelklick auf das Formular im Designer anlegt. Seit
    #: `on_close` dazukam, hat das Formular zwei eigene Ereignisse, und
    #: der Designer fände ohne diese Angabe keines.
    standard_ereignis = "on_create"

    #: Der Ereignisfilter prüft das, um ein `on_click` nicht doppelt
    #: zu melden. Ein Formular hat kein eigenes Qt-Signal dafür.
    _klick_kommt_vom_widget = False

    #: Ob das Formular im Designer steht statt im laufenden Programm.
    #: Setzt der Designer beim Laden (`ide/designer/laden.py`). Eine
    #: Komponente mit `visible = False` bleibt dort sichtbar, und ein
    #: Menüeintrag, dessen Methode es noch nicht gibt, ist dort kein
    #: Fehler.
    _entwurfsansicht = False

    def __init__(self) -> None:
        self._qwidget = QWidget()
        self._menueleiste: QMenuBar | None = None
        self._modal_schleife: QEventLoop | None = None
        #: Die Timer auf dem Formular; sie tragen sich selbst ein.
        self._zeitgeber: list[Any] = []
        self._qwidget.setWindowTitle(self.caption)
        self._qwidget.resize(self.width, self.height)
        self._stylesheet_aktualisieren()

        # Der Filter muss am Objekt hängen bleiben: ein QObject ohne
        # Eltern und ohne Referenz wird eingesammelt, und die
        # Ereignisse kämen nie an. Dieselbe Begründung wie in
        # `pcl/control.py`.
        self._maus_filter = _FensterFilter(self)
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
        elif name in ("left", "top"):
            if self._ist_fenster() and self._qwidget.isVisible():
                self._qwidget.move(self.left, self.top)
        elif name == "icon":
            self._symbol_anwenden()

    def _formular(self) -> Form:
        """Das Formular selbst - dieselbe Frage, die eine Komponente
        über ihre Elternkette beantwortet."""
        return self

    def _ist_fenster(self) -> bool:
        """Ob das Formular ein eigenes Fenster ist. Im Designer liegt es
        auf der Zeichenfläche, und `left`/`top` dürfen es dort nicht
        verschieben."""
        return not self._entwurfsansicht and self._qwidget.isWindow()

    def _symbol_anwenden(self) -> None:
        if not self.icon:
            self._qwidget.setWindowIcon(QIcon())
            return
        # Dieselbe Suche wie beim Bild eines `Image`: im Arbeitsordner,
        # im Projektordner und neben dem gestarteten Hauptprogramm.
        from pcl.bilddatei import bild_laden
        from pcl.components.additional import _bilddatei_finden

        self._qwidget.setWindowIcon(QIcon(bild_laden(_bilddatei_finden(self.icon, self))))

    def _position_anwenden(self) -> None:
        """Setzt das Fenster vor dem ersten Zeigen an seinen Platz.

        Bei `screen_center` in die Mitte des Hauptbildschirms; `left`
        und `top` geben danach wieder, wo es tatsächlich steht.
        """
        if not self._ist_fenster():
            return
        if self.position == "designed":
            self._qwidget.move(self.left, self.top)
            return
        # Nicht `self._qwidget.screen()`: bei einem Fenster, das noch
        # nie gezeigt wurde, beschädigte diese Abfrage den Speicher.
        # Wurde ein zweites Formular gezeigt, geschlossen und dann
        # aufgeräumt, stürzte das Programm später an einer beliebigen
        # Stelle ab (Punkt 137).
        bildschirm = QGuiApplication.primaryScreen()
        if bildschirm is None:
            return
        flaeche = bildschirm.availableGeometry()
        groesse = self._qwidget.frameGeometry().size()
        ecke = flaeche.center() - QPoint(groesse.width() // 2, groesse.height() // 2)
        self._qwidget.move(ecke)
        self.__dict__["_prop_left"] = self._qwidget.x()
        self.__dict__["_prop_top"] = self._qwidget.y()

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

    def _fensterlage_uebernehmen(self) -> None:
        """Führt `width`, `height`, `left` und `top` nach, wenn das
        Fenster größer gezogen, maximiert oder verschoben wurde.

        Still, ohne `_bei_prop_aenderung`: das Fenster hat die Werte
        schon. Bis dahin lieferte `self.width` nach dem Vergrößern
        weiter den Wert aus dem Designer, und ein `self.height = 500`
        setzte die Breite auf ihn zurück. `height` zählt wie überall
        ohne die Menüleiste.

        Nur solange das Fenster zu sehen ist. Beim ersten Zeigen
        schickt Qt die Größe, die das Programm selbst gesetzt hat;
        die Menüleiste kann da ihre endgültige Höhe noch nicht haben.
        """
        if not self._ist_fenster() or not self._qwidget.isVisible():
            return
        self.__dict__["_prop_width"] = self._qwidget.width()
        self.__dict__["_prop_height"] = self._qwidget.height() - self._leistenhoehe()
        self.__dict__["_prop_left"] = self._qwidget.x()
        self.__dict__["_prop_top"] = self._qwidget.y()

    def _maus_melden(self, name: str, stelle: Any) -> None:
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
        self._ereignis_ausloesen(
            name, int(stelle.x()), int(stelle.y()) - self._leistenhoehe()
        )

    def _taste_melden(self, name: str) -> None:
        """Eine Taste, die das Fenster selbst bekommt - dann, wenn
        keine Komponente den Fokus hat."""
        self._ereignis_ausloesen("on_key_press", name)

    def _eingabetaste(self) -> None:
        """Die Eingabetaste, während keine Komponente den Fokus hat."""
        self._standardknopf_druecken()

    def _standardknopf_druecken(self) -> None:
        """Klickt den Knopf mit `default = True`, wenn er bedienbar
        und zu sehen ist.

        Qt kennt einen Standardknopf nur in Dialogfenstern, ein
        Formular ist keins. Deshalb sucht das Formular ihn selbst.
        """
        from pcl.components.standard import Button

        for wert in list(vars(self).values()):
            if (
                isinstance(wert, Button)
                and wert.default
                and wert.visible
                and wert._qwidget.isEnabled()
                and (wert._qwidget.isVisible() or not self._qwidget.isVisible())
            ):
                wert._qwidget.click()
                return

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
        """Zeigt das Fenster. Das Programm läuft danach sofort weiter,
        und beide Fenster lassen sich bedienen."""
        self._menueleiste_aufbauen()
        if not self._qwidget.isVisible():
            self._position_anwenden()
            # Vor dem ersten Zeigen: Windows liest den Namen für die
            # Taskleiste, wenn der Knopf entsteht (Punkt 469). Nur in
            # einem Programm und nur für ein eigenes Fenster; `winId`
            # machte ein eingebettetes Formular sonst zu einem.
            if taskleiste.kennung_gesetzt and self._qwidget.isWindow():
                taskleiste.fenster_benennen(int(self._qwidget.winId()))
        _offene_formulare[id(self)] = self
        self._zeitgeber_schalten(an=True)
        self._qwidget.show()

    def show_modal(self) -> None:
        """Zeigt das Fenster und wartet, bis es geschlossen ist.

        Solange es offen ist, lassen sich die anderen Fenster des
        Programms nicht bedienen. Die Zeile nach ``show_modal()`` läuft
        erst, wenn es wieder zu ist, und kann dann lesen, was darin
        eingetragen wurde::

            dialog = FormEinstellungen()
            dialog.show_modal()
            self.l_name.caption = dialog.e_name.text
        """
        self._qwidget.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.show()
        schleife = QEventLoop()
        self._modal_schleife = schleife
        try:
            # Schon geschlossen, bevor die Schleife läuft (etwa in
            # `on_create`): dann gibt es nichts zu warten.
            if self._qwidget.isVisible():
                schleife.exec()
        finally:
            self._modal_schleife = None
            self._qwidget.setWindowModality(Qt.WindowModality.NonModal)

    def _modal_beenden(self) -> None:
        # Über `__dict__`: beim Aufräumen eines Formulars sind seine
        # Attribute schon fort, wenn Qt das Fenster als verborgen meldet.
        schleife = self.__dict__.get("_modal_schleife")
        # Ein verkleinertes Fenster meldet sich auch als verborgen, ist
        # für Qt aber weiter sichtbar. Es ist nicht geschlossen.
        if schleife is not None and not self._qwidget.isVisible():
            schleife.quit()

    def _geschlossen(self) -> None:
        """Räumt hinter einem geschlossenen Fenster auf: die Timer
        halten an, und das Formular darf wieder eingesammelt werden.

        Qt meldet auch ein verkleinertes Fenster als verborgen; es
        bleibt aber sichtbar und ist nicht geschlossen.

        Beim Beenden des Programms räumt Qt die Fenster ab, bevor
        Python das Formular abräumt; dann ist das Qt-Fenster schon
        fort, und es bleibt nur, das Formular freizugeben.
        """
        try:
            if self.__dict__["_qwidget"].isVisible():
                return
            self._zeitgeber_schalten(an=False)
        except (KeyError, RuntimeError):
            pass
        _offene_formulare.pop(id(self), None)

    def _zeitgeber_schalten(self, *, an: bool) -> None:
        """Hält die Timer des Formulars an oder lässt die laufen, bei
        denen `enabled` gesetzt ist (Punkt 215). Ein Timer, der schon
        läuft, wird nicht neu gestartet und behält seinen Takt."""
        from pcl.components.system import Timer

        alle = list(self.__dict__.get("_zeitgeber", ()))
        # Ein Timer ohne Formular (`self.t_uhr = Timer()`) trägt sich
        # nirgends ein; als Attribut gehört er trotzdem zum Formular.
        alle += [
            wert
            for wert in self.__dict__.values()
            if isinstance(wert, Timer) and wert.eltern is None
        ]
        for zeitgeber in alle:
            if not an:
                zeitgeber._qtimer.stop()
            elif zeitgeber._darf_laufen() and not zeitgeber._qtimer.isActive():
                zeitgeber._qtimer.start()

    def close(self) -> None:
        """Schließt das Fenster."""
        self._qwidget.close()
