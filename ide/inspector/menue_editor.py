"""Menü-Editor: der Dialog, in dem die Einträge eines `MainMenu` oder
`PopupMenu` bearbeitet werden.

Siehe Arbeitspaket M15, Schritt 1. Der Aufbau folgt
`ide/diagramm/klassendialog.py`: die Zeichenfläche ordnet an, der
Dialog füllt aus. Diese Entscheidung hat der Nutzer für die
UML-Klassen getroffen, und ein Menü ist derselbe Fall – ein Eintrag
hat Bezeichner, Beschriftung, Tastenkürzel und Untereinträge, das
bearbeitet niemand sinnvoll an Ort und Stelle auf dem Formular.

Links steht der Baum der Einträge, rechts die Felder des ausgewählten
Eintrags, darüber die Knöpfe. Unten die drei Knöpfe Schließen,
Anwenden, OK – dieselben wie im Klassendialog, damit sich
beide gleich anfühlen.

Gearbeitet wird auf einer Kopie: erst „Anwenden" oder „OK"
überträgt sie. „Schließen" verwirft, was seit dem letzten „Anwenden"
geändert wurde. Auch das ist aus dem Klassendialog übernommen.
"""

from __future__ import annotations

import copy
import re
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStyle,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from pcl.components.menus import (
    EINTRAG_VORGABE,
    doppeltes_kuerzel,
    eintrag_vollstaendig,
    kuerzel_fehler,
)

#: Rolle, unter der am Baumeintrag sein Pfad hängt: "0" für den
#: ersten Eintrag der obersten Ebene, "0.2" für dessen dritten
#: Untereintrag.
#:
#: Der Pfad und nicht der Datensatz selbst, und das hat einen Grund:
#: PySide wandelt ein `dict` beim Ablegen in den Item-Daten in eine
#: `QVariantMap` und wieder zurück. Was herauskommt, ist gleich, aber
#: nicht dasselbe Objekt - ein `gewaehlt["children"].append(...)`
#: hätte an einer Kopie gearbeitet und wäre spurlos verpufft. Genau
#: das ist hier beim Bauen passiert.
DATEN_ROLLE = Qt.ItemDataRole.UserRole

#: Was in der Baumzeile steht, wenn ein Eintrag noch keine
#: Beschriftung hat. Eine leere Zeile wäre nicht anklickbar zu sehen.
OHNE_BESCHRIFTUNG = "(ohne Beschriftung)"

TRENNLINIE_TEXT = "────────"


_UMLAUTE = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def methodenname_vorschlagen(eintrag: dict[str, Any]) -> str:
    """Der Name, den „Methode anlegen“ vorschlägt, wenn im Feld noch
    keiner steht.

    Aus dem Bezeichner des Eintrags, wie beim Reiter „Ereignisse“:
    `mi_datei_beenden` wird `mi_datei_beenden_click`. Ohne Bezeichner
    aus der Beschriftung: „B&eenden“ wird `mi_beenden_click`.
    """
    if eintrag.get("name"):
        return f"{eintrag['name']}_click"
    text = eintrag.get("caption", "").replace("&", "").lower().translate(_UMLAUTE)
    kern = re.sub(r"[^a-z0-9]+", "_", text).strip("_") or "eintrag"
    return f"mi_{kern}_click"


def menue_methode_anlegen(canvas: Any, methodenname: str) -> bool:
    """Schreibt die Methode eines Menüeintrags in die Unit des
    Formulars, das `canvas` (ein `DesignerCanvas`) zeigt.

    Dasselbe wie ein Doppelklick auf dem Reiter „Ereignisse“, nur ohne
    Verknüpfung am Objekt: ein Menüeintrag trägt den Namen der
    Methode, nicht die Methode selbst. Danach springt der Editor hin,
    wie nach jedem anderen angelegten Ereignis. Eine Methode, die es
    schon gibt, bleibt, wie sie ist.

    Liefert, ob die Methode danach in der Unit steht. Bei einem
    Schreibschutz, einer nicht lesbaren Unit oder einem Syntaxfehler
    erscheint stattdessen eine Meldung.
    """
    unit_pfad = getattr(canvas, "unit_pfad", None)
    if unit_pfad is None or not unit_pfad.exists():
        return False
    from ide.codegen.ereignis import handler_methode_einfuegen

    # Dieselben Prüfungen wie beim Doppelklick im Reiter „Ereignisse“:
    # eine schreibgeschützte oder nicht in UTF-8 gespeicherte Unit
    # endete bis zu den Punkten 255 und 256 in der allgemeinen
    # Fehlermeldung.
    folge = "Die Methode lässt sich deshalb nicht anlegen."
    meldung = canvas._unit_nicht_beschreibbar(folge)
    if meldung is not None:
        canvas._meldung_zeigen(meldung)
        return False
    quelltext = canvas._unit_lesen_oder_melden(folge)
    if quelltext is None:
        return False
    # Auch die offenen Editoren: eine ungespeicherte, angefangene
    # Zeile dort ließ sonst das spätere Einfügen in den Editor
    # scheitern, nachdem die Datei die Methode schon hatte.
    meldung = canvas._syntaxfehler_melden(
        [
            quelltext,
            *(e.toPlainText() for e in canvas._offene_unit_editoren()),
        ],
        "Die Methode lässt sich erst anlegen, wenn er behoben ist.",
    )
    if meldung is not None:
        canvas._meldung_zeigen(meldung)
        return False
    klassenname = type(canvas.formular).__name__
    neu = handler_methode_einfuegen(quelltext, klassenname, methodenname)
    if neu != quelltext and not canvas._unit_schreiben(neu, folge):
        return False
    canvas._methode_melden(methodenname, "on_click")
    return True


def _alle_eintraege(eintraege: list[dict[str, Any]]):  # noqa: ANN202
    for eintrag in eintraege:
        yield eintrag
        yield from _alle_eintraege(eintrag["children"])


def _zeilentext(eintrag: dict[str, Any]) -> str:
    if eintrag.get("separator"):
        return TRENNLINIE_TEXT
    beschriftung = eintrag.get("caption") or OHNE_BESCHRIFTUNG
    kuerzel = eintrag.get("shortcut")
    return f"{beschriftung}\t{kuerzel}" if kuerzel else beschriftung


class MenueEditor(QDialog):
    """Der Menü-Editor. `eintraege` ist der Baum, wie ihn
    `MainMenu.entries` liefert."""

    def __init__(
        self,
        eintraege: list[dict[str, Any]],
        eltern: QWidget | None = None,
        methode_anlegen: Callable[[str], bool | None] | None = None,
    ) -> None:
        super().__init__(eltern)
        self.setWindowTitle("Menü bearbeiten")
        #: Schreibt die Methode in die Unit - dieselbe Arbeit wie ein
        #: Doppelklick auf dem Reiter „Ereignisse“. Kommt vom Designer;
        #: ohne ihn (kein Formular mit Unit) bleibt der Knopf grau.
        self._methode_anlegen = methode_anlegen
        #: Alles läuft auf der Kopie; erst „Anwenden“ überträgt sie.
        #: Vollständig aufgefüllt, weil die `.pfm` nur trägt, was vom
        #: Standard abweicht - der Editor setzt jedes Feld voraus.
        self.entwurf: list[dict[str, Any]] = [eintrag_vollstaendig(e) for e in eintraege]
        self.uebernommen = False
        self.ergebnis: list[dict[str, Any]] = copy.deepcopy(self.entwurf)

        self.baum = QTreeWidget()
        self.baum.setHeaderLabels(["Eintrag"])
        self.baum.setRootIsDecorated(True)

        self.neu_knopf = QPushButton("&Neu")
        self.unter_knopf = QPushButton("&Untereintrag")
        self.trenner_knopf = QPushButton("&Trennlinie")
        self.loeschen_knopf = QPushButton("&Löschen")
        # Pfeile als Symbole des Stils statt als Zeichen „▲“ und „▼“:
        # die zeichnete die Schrift als kleine, kaum erkennbare
        # Klötzchen, und die feste Breite von 32 Pixeln war bei 150 %
        # zu schmal (Punkt 502).
        stil = self.style()
        self.hoch_knopf = QPushButton(
            stil.standardIcon(QStyle.StandardPixmap.SP_ArrowUp), ""
        )
        self.runter_knopf = QPushButton(
            stil.standardIcon(QStyle.StandardPixmap.SP_ArrowDown), ""
        )
        self.hoch_knopf.setToolTip("Eintrag nach oben schieben")
        self.runter_knopf.setToolTip("Eintrag nach unten schieben")
        self.hoch_knopf.setAccessibleName("Nach oben")
        self.runter_knopf.setAccessibleName("Nach unten")

        knopfreihe = QHBoxLayout()
        for knopf in (
            self.neu_knopf,
            self.unter_knopf,
            self.trenner_knopf,
            self.loeschen_knopf,
            self.hoch_knopf,
            self.runter_knopf,
        ):
            knopfreihe.addWidget(knopf)
        knopfreihe.addStretch(1)

        self.feld_name = QLineEdit()
        self.feld_caption = QLineEdit()
        self.feld_shortcut = QLineEdit()
        self.feld_on_click = QLineEdit()
        self.feld_enabled = QCheckBox("Bedienbar")
        self.feld_visible = QCheckBox("Sichtbar")
        self.feld_checkable = QCheckBox("Ankreuzbar")
        self.feld_checked = QCheckBox("Angekreuzt")
        self.feld_checkable.setToolTip(
            "Ein Klick setzt oder entfernt das Häkchen, z. B. für „Raster anzeigen“"
        )
        self.kuerzel_hinweis = QLabel()
        self.kuerzel_hinweis.setWordWrap(True)
        self.kuerzel_hinweis.setStyleSheet("QLabel { color: #c0392b; }")
        self.kuerzel_hinweis.hide()

        self.feld_name.setToolTip("Bezeichner im Quelltext, z. B. mi_datei_beenden")
        self.feld_caption.setToolTip(
            "Was dasteht. Ein & macht den nächsten Buchstaben zum Zugriffsbuchstaben"
        )
        self.feld_shortcut.setToolTip("Tastenkürzel, z. B. Strg+Q")
        self.feld_on_click.setToolTip("Name der Methode, die beim Anklicken laufen soll")
        self.anlegen_knopf = QPushButton("&Methode anlegen")
        self.anlegen_knopf.setToolTip(
            "Legt die Methode im Quelltext des Formulars an und springt dorthin"
        )
        self.anlegen_knopf.setEnabled(methode_anlegen is not None)
        self.anlegen_knopf.clicked.connect(self.methode_anlegen)

        self.eintragsdaten = QGroupBox("Eintragsdaten")
        formular = QFormLayout(self.eintragsdaten)
        formular.addRow("Name:", self.feld_name)
        formular.addRow("Beschriftung:", self.feld_caption)
        formular.addRow("Tastenkürzel:", self.feld_shortcut)
        formular.addRow("", self.kuerzel_hinweis)
        # Der Knopf in eigener Zeile: neben ihm blieb für den Namen der
        # Methode nur ein winziges Feld (Punkt 502).
        formular.addRow("Beim Anklicken:", self.feld_on_click)
        formular.addRow("", self.anlegen_knopf)
        formular.addRow(self.feld_enabled)
        formular.addRow(self.feld_visible)
        formular.addRow(self.feld_checkable)
        formular.addRow(self.feld_checked)

        self.knoepfe = QDialogButtonBox()
        # „Abbrechen“ wie im Klassendialog (Punkt 309): bei „Schließen“
        # blieb offen, ob die Änderungen verloren gehen (Punkt 502).
        self.abbrechen_knopf = self.knoepfe.addButton(
            "Abbrechen", QDialogButtonBox.ButtonRole.RejectRole
        )
        self.anwenden_knopf = self.knoepfe.addButton(
            "&Anwenden", QDialogButtonBox.ButtonRole.ApplyRole
        )
        self.ok_knopf = self.knoepfe.addButton("&OK", QDialogButtonBox.ButtonRole.AcceptRole)
        self.abbrechen_knopf.clicked.connect(self.reject)
        self.anwenden_knopf.clicked.connect(self.anwenden)
        self.ok_knopf.clicked.connect(self._ok)

        rechts = QVBoxLayout()
        rechts.addWidget(self.eintragsdaten)
        rechts.addStretch(1)

        mitte = QHBoxLayout()
        mitte.addWidget(self.baum, 1)
        mitte.addLayout(rechts, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(knopfreihe)
        layout.addLayout(mitte, 1)
        layout.addWidget(self.knoepfe)
        self.resize(620, 420)

        self.neu_knopf.clicked.connect(self._neu)
        self.unter_knopf.clicked.connect(self._untereintrag)
        self.trenner_knopf.clicked.connect(self._trennlinie)
        self.loeschen_knopf.clicked.connect(self._loeschen)
        self.hoch_knopf.clicked.connect(lambda: self._schieben(-1))
        self.runter_knopf.clicked.connect(lambda: self._schieben(1))
        self.baum.currentItemChanged.connect(lambda *_: self._auswahl_gewechselt())
        for feld in (self.feld_name, self.feld_caption, self.feld_shortcut, self.feld_on_click):
            feld.textChanged.connect(self._felder_uebernehmen)
        self.feld_enabled.toggled.connect(self._felder_uebernehmen)
        self.feld_visible.toggled.connect(self._felder_uebernehmen)
        self.feld_checkable.toggled.connect(self._felder_uebernehmen)
        self.feld_checked.toggled.connect(self._felder_uebernehmen)

        self._fuellen()
        # Ein Menü aus einer älteren Fassung kann zwei gleiche Kürzel
        # tragen; dann wirkt nur das erste. Gesagt wird es gleich beim
        # Öffnen, geändert werden muss es vor „Anwenden“ (Punkt 639).
        self._kuerzel_hinweis_zeigen(doppeltes_kuerzel(self.entwurf))

    # -- Baum ------------------------------------------------------------

    def _fuellen(self, auswahl: tuple[int, ...] | None = None) -> None:
        """Baut den Baum aus `self.entwurf` neu auf.

        Neu statt nachgeführt: der Baum ist klein, und ein
        nachgeführter Baum ist die Stelle, an der Anzeige und Daten
        auseinanderlaufen.
        """
        self.baum.blockSignals(True)
        self.baum.clear()
        gewaehlt = None
        for nummer, eintrag in enumerate(self.entwurf):
            zeile = self._zeile_bauen(eintrag, (nummer,))
            self.baum.addTopLevelItem(zeile)
            if auswahl == (nummer,):
                gewaehlt = zeile
            for kindnummer, kind in enumerate(eintrag["children"]):
                kindzeile = self._zeile_bauen(kind, (nummer, kindnummer))
                zeile.addChild(kindzeile)
                if auswahl == (nummer, kindnummer):
                    gewaehlt = kindzeile
            zeile.setExpanded(True)
        self.baum.blockSignals(False)
        if gewaehlt is not None:
            self.baum.setCurrentItem(gewaehlt)
        elif self.baum.topLevelItemCount():
            self.baum.setCurrentItem(self.baum.topLevelItem(0))
        else:
            self._auswahl_gewechselt()

    def _zeile_bauen(self, eintrag: dict[str, Any], pfad: tuple[int, ...]) -> QTreeWidgetItem:
        zeile = QTreeWidgetItem([_zeilentext(eintrag)])
        zeile.setData(0, DATEN_ROLLE, ".".join(str(teil) for teil in pfad))
        return zeile

    def _gewaehlter_pfad(self) -> tuple[int, ...] | None:
        zeile = self.baum.currentItem()
        if zeile is None:
            return None
        return tuple(int(teil) for teil in str(zeile.data(0, DATEN_ROLLE)).split("."))

    def _liste_zu(self, pfad: tuple[int, ...]) -> list[dict[str, Any]]:
        """Die Liste, in der der Eintrag mit diesem Pfad steht –
        oberste Ebene oder die Untereinträge seines Elternteils."""
        if len(pfad) == 1:
            return self.entwurf
        return self.entwurf[pfad[0]]["children"]

    def _gewaehlter_eintrag(self) -> dict[str, Any] | None:
        pfad = self._gewaehlter_pfad()
        if pfad is None:
            return None
        return self._liste_zu(pfad)[pfad[-1]]

    # -- Knöpfe ----------------------------------------------------------

    def _neuer_eintrag(self, **felder: Any) -> dict[str, Any]:
        return eintrag_vollstaendig({**dict(EINTRAG_VORGABE), **felder})

    def _einfuegen(self, **felder: Any) -> None:
        """Setzt einen neuen Eintrag hinter den ausgewählten – auf
        derselben Ebene – oder ans Ende, wenn nichts ausgewählt ist."""
        pfad = self._gewaehlter_pfad()
        neu = self._neuer_eintrag(**felder)
        if pfad is None:
            self.entwurf.append(neu)
            self._fuellen((len(self.entwurf) - 1,))
            return
        liste = self._liste_zu(pfad)
        stelle = pfad[-1] + 1
        liste.insert(stelle, neu)
        self._fuellen(pfad[:-1] + (stelle,))

    def _neu(self) -> None:
        self._einfuegen(caption="Neuer Eintrag")

    def _untereintrag(self) -> None:
        """Hängt einen Eintrag unter den ausgewählten.

        Nur unter einen Eintrag der obersten Ebene: Menüs gehen hier
        bis zur zweiten Ebene, und ein grauer Knopf ist ehrlicher als
        ein Eintrag, der später beim Speichern abgelehnt wird.
        """
        pfad = self._gewaehlter_pfad()
        if pfad is None or len(pfad) != 1:
            return
        kinder = self.entwurf[pfad[0]]["children"]
        kinder.append(self._neuer_eintrag(caption="Neuer Eintrag"))
        self._fuellen((pfad[0], len(kinder) - 1))

    def _trennlinie(self) -> None:
        self._einfuegen(separator=True)

    def _loeschen(self) -> None:
        pfad = self._gewaehlter_pfad()
        if pfad is None:
            return
        del self._liste_zu(pfad)[pfad[-1]]
        self._fuellen()

    def _schieben(self, richtung: int) -> None:
        pfad = self._gewaehlter_pfad()
        if pfad is None:
            return
        liste = self._liste_zu(pfad)
        alt = pfad[-1]
        neu = alt + richtung
        if not 0 <= neu < len(liste):
            return
        liste[alt], liste[neu] = liste[neu], liste[alt]
        self._fuellen(pfad[:-1] + (neu,))

    # -- Felder ----------------------------------------------------------

    def _auswahl_gewechselt(self) -> None:
        eintrag = self._gewaehlter_eintrag()
        vorhanden = eintrag is not None
        trennlinie = bool(eintrag and eintrag["separator"])

        # Eine Trennlinie hat weder Beschriftung noch Ereignis. Die
        # Felder auszugrauen ist klarer, als Eingaben anzunehmen, die
        # später niemand sieht.
        self.eintragsdaten.setEnabled(vorhanden and not trennlinie)
        pfad = self._gewaehlter_pfad()
        self.unter_knopf.setEnabled(bool(pfad is not None and len(pfad) == 1 and not trennlinie))
        self.loeschen_knopf.setEnabled(vorhanden)

        felder = (
            self.feld_name,
            self.feld_caption,
            self.feld_shortcut,
            self.feld_on_click,
            self.feld_enabled,
            self.feld_visible,
            self.feld_checkable,
            self.feld_checked,
        )
        for feld in felder:
            feld.blockSignals(True)
        if eintrag is None:
            for feld in felder[:4]:
                feld.clear()
            self.feld_enabled.setChecked(True)
            self.feld_visible.setChecked(True)
            self.feld_checkable.setChecked(False)
            self.feld_checked.setChecked(False)
        else:
            self.feld_name.setText(eintrag["name"])
            self.feld_caption.setText(eintrag["caption"])
            self.feld_shortcut.setText(eintrag["shortcut"])
            self.feld_on_click.setText(eintrag["on_click"])
            self.feld_enabled.setChecked(eintrag["enabled"])
            self.feld_visible.setChecked(eintrag.get("visible", True))
            self.feld_checkable.setChecked(
                eintrag.get("checkable", False) or eintrag["checked"]
            )
            self.feld_checked.setChecked(eintrag["checked"])
        for feld in felder:
            feld.blockSignals(False)
        self.feld_checked.setEnabled(self.feld_checkable.isChecked())

    def _felder_uebernehmen(self) -> None:
        eintrag = self._gewaehlter_eintrag()
        if eintrag is None:
            return
        eintrag["name"] = self.feld_name.text()
        eintrag["caption"] = self.feld_caption.text()
        eintrag["shortcut"] = self.feld_shortcut.text()
        eintrag["on_click"] = self.feld_on_click.text()
        eintrag["enabled"] = self.feld_enabled.isChecked()
        eintrag["visible"] = self.feld_visible.isChecked()
        eintrag["checkable"] = self.feld_checkable.isChecked()
        # Ohne „Ankreuzbar“ gibt es kein Häkchen. Sonst machte ein
        # stehengebliebenes `checked` den Eintrag wieder ankreuzbar
        # (Punkt 588).
        if not eintrag["checkable"] and self.feld_checked.isChecked():
            self.feld_checked.blockSignals(True)
            self.feld_checked.setChecked(False)
            self.feld_checked.blockSignals(False)
        self.feld_checked.setEnabled(eintrag["checkable"])
        eintrag["checked"] = self.feld_checked.isChecked()
        self._kuerzel_hinweis_zeigen(
            kuerzel_fehler(eintrag["shortcut"]) or doppeltes_kuerzel(self.entwurf)
        )
        zeile = self.baum.currentItem()
        if zeile is not None:
            zeile.setText(0, _zeilentext(eintrag))

    def methode_anlegen(self) -> None:
        """Legt die Methode für „Beim Anklicken“ an.

        Steht im Feld noch nichts, kommt ein Name aus dem Bezeichner
        des Eintrags hinein. Eine Methode, die es schon gibt, schreibt
        der Designer kein zweites Mal - dann springt er nur hin.
        """
        eintrag = self._gewaehlter_eintrag()
        if eintrag is None or self._methode_anlegen is None:
            return
        name = self.feld_on_click.text().strip() or methodenname_vorschlagen(eintrag)
        if not name.isidentifier():
            QMessageBox.warning(
                self,
                "Methode anlegen",
                f"„{name}“ ist kein gültiger Methodenname. Erlaubt sind "
                "Buchstaben, Ziffern und _, am Anfang keine Ziffer.",
            )
            return
        # Der Name kommt erst ins Feld, wenn die Methode steht. Sonst
        # verwiese der Eintrag nach „OK“ auf eine Methode, die es nicht
        # gibt, weil die Unit schreibgeschützt war (Punkt 255).
        if self._methode_anlegen(name) is not False:
            self.feld_on_click.setText(name)

    # -- Abschluss -------------------------------------------------------

    def _kuerzel_hinweis_zeigen(self, fehler: str | None) -> None:
        self.kuerzel_hinweis.setText(fehler or "")
        self.kuerzel_hinweis.setVisible(fehler is not None)

    def anwenden(self) -> bool:
        """Übernimmt den Entwurf, ohne den Dialog zu schließen.

        Ein Tastenkürzel, das sich nicht umsetzen lässt, hält das auf:
        das Menü nähme die Einträge sonst nicht an (Punkt 561)."""
        for eintrag in _alle_eintraege(self.entwurf):
            fehler = kuerzel_fehler(eintrag.get("shortcut", ""))
            if fehler is not None:
                self._kuerzel_hinweis_zeigen(fehler)
                return False
        # Zwei Einträge mit derselben Taste lösten keinen aus (Punkt 633).
        doppelt = doppeltes_kuerzel(self.entwurf)
        if doppelt is not None:
            self._kuerzel_hinweis_zeigen(doppelt)
            return False
        self.ergebnis = copy.deepcopy(self.entwurf)
        self.uebernommen = True
        return True

    def _ok(self) -> None:
        if self.anwenden():
            self.accept()

    def eintraege(self) -> list[dict[str, Any]]:
        """Die übernommenen Einträge – nach „Schließen" ohne
        vorheriges „Anwenden" also der Stand von vorher."""
        return self.ergebnis
