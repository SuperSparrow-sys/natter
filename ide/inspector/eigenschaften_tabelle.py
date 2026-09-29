"""EigenschaftenTabelle: zeigt und bearbeitet die `Prop`-Eigenschaften
einer Komponente – Reiter „Eigenschaften“ des Objektinspektors.

Siehe README.md, Abschnitt 5.0 (Eigenschaften-System, Editor je
Datentyp) und 7.6 (Objektinspektor). Live-Wirkung entsteht automatisch,
weil `Prop.__set__` (`pcl/properties.py`) das zugehörige Qt-Widget sofort
aktualisiert (`_bei_prop_aenderung`-Hook) – die Tabelle ruft dafür nur
`setattr` (bzw. bei aufklappbaren Untereigenschaften wie
`Shape.brush.color` denselben Mechanismus eine Ebene tiefer) auf, mehr
nicht.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFontDialog,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QWidget,
)

from ide.inspector.menue_editor import MenueEditor
from ide.inspector.sammlung_dialog import SammlungDialog
from pcl.errors import NatterPropertyError
from pcl.properties import (
    ART_BILD,
    ART_FARBE,
    ART_SCHRIFT,
    BAUM_DOKU,
    BAUM_EIGENSCHAFTEN,
    SAMMLUNGS_DOKU,
    SAMMLUNGS_EIGENSCHAFTEN,
    VERSCHACHTELTE_EIGENSCHAFTEN,
    VERWEIS_DOKU,
    VERWEIS_EIGENSCHAFTEN,
    eigenschaften,
    text_aus_wert,
    wert_aus_text,
    wert_lesen,
    wert_setzen,
)

_SPALTE_NAME = 0
_SPALTE_WERT = 1

#: Was in der Zeile `popup_menu` steht, solange kein Klappmenü
#: zugeordnet ist - dieselbe Schreibweise wie auf dem Reiter
#: „Ereignisse“.
KEIN_VERWEIS = "(kein)"
_NAME_ROLLE = Qt.ItemDataRole.UserRole

# Sentinel für die "Name"-Zeile (Bezeichner im Code, z. B. "b_anmelden") -
# keine echte Prop, deshalb ein eigener Marker statt eines Eigenschafts-
# namens in _NAME_ROLLE.
_NAME_ZEILE = object()

#: Hilfetext der Zeile „name“. Sie ist keine `Prop` und hat deshalb
#: auch keinen `doc` – dabei ist gerade sie erklärungsbedürftig, weil
#: „name“ und „caption“ leicht verwechselt werden.
_NAME_DOKU = (
    "Der Bezeichner im Quelltext, z. B. b_anmelden – nicht der "
    "angezeigte Text (das ist „caption“ bzw. „text“)."
)


def bilddatei_erfragen(eltern: QWidget, startordner: Path | None) -> str:
    """Fragt nach einer Bilddatei; leer, wenn abgebrochen wurde.

    Eine eigene Funktion, damit Tests sie ersetzen können - ein
    Dateidialog wartet sonst auf einen Klick, der nie kommt.
    """
    from ide.designer.bilder import BILD_ENDUNGEN

    muster = " ".join(f"*{endung}" for endung in BILD_ENDUNGEN)
    pfad, _ = QFileDialog.getOpenFileName(
        eltern,
        "Bild auswählen",
        str(startordner or ""),
        f"Bilder ({muster})",
    )
    return pfad


def farbe_erfragen(eltern: QWidget, alt: str) -> str | None:
    """Der Farbwähler hinter „…“; `None`, wenn abgebrochen wurde."""
    farbe = QColorDialog.getColor(QColor(alt or "#ffffff"), eltern, "Farbe auswählen")
    if not farbe.isValid():
        return None
    return farbe.name()


def schrift_erfragen(eltern: QWidget, alt: str) -> str | None:
    """Die Schriftauswahl hinter „…“. Übernommen wird nur der Name der
    Schrift; Größe und Stil haben ihre eigenen Zeilen."""
    ok, schrift = QFontDialog.getFont(QFont(alt), eltern, "Schriftart auswählen")
    if not ok:
        return None
    return schrift.family()


class _WertMitKnopf(QWidget):
    """Textfeld mit einem Knopf „…“ daneben - der Editor für Werte,
    die sich eintippen, aber bequemer in einem Dialog wählen lassen.

    `waehlen` öffnet den Dialog und liefert den neuen Text oder
    `None`; `fertig` übernimmt den Wert in die Tabelle.
    """

    def __init__(
        self,
        eltern: QWidget,
        waehlen: Callable[[str], str | None],
        fertig: Callable[[QWidget], None],
    ) -> None:
        super().__init__(eltern)
        self.feld = QLineEdit(self)
        self.feld.setFrame(False)
        self.knopf = QToolButton(self)
        self.knopf.setText("…")
        self.knopf.setToolTip("Auswählen")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.feld, 1)
        layout.addWidget(self.knopf)
        self.setFocusProxy(self.feld)
        self._waehlen = waehlen
        self._fertig = fertig
        self.knopf.clicked.connect(self.dialog_oeffnen)

    def dialog_oeffnen(self) -> None:
        neu = self._waehlen(self.feld.text())
        if neu is None:
            return
        self.feld.setText(neu)
        self._fertig(self)


class _EditorDelegat(QStyledItemDelegate):
    """Legt für jede Zeile den passenden Editor an.

    Die Textzelle bleibt für alles, was keine eigene Art hat. Ein
    Delegat statt eines Dialogs auf Doppelklick: der Doppelklick
    öffnet bei einer bearbeitbaren Zelle ohnehin den Zelleneditor,
    und ein Dialog obendrauf käme mit ihm ins Gehege.
    """

    def __init__(self, tabelle: EigenschaftenTabelle) -> None:
        # Die Tabelle nur als Eltern, nicht zusätzlich als Attribut:
        # sonst hielten Tabelle und Delegat einander fest, und die
        # Tabelle verschwände nicht mehr beim letzten Verweis, sondern
        # irgendwann später in der Müllabfuhr - mitten in einer
        # anderen Qt-Operation. Genau das hat die Testreihe mit einem
        # Absturz beendet.
        super().__init__(tabelle)

    def _tabelle(self) -> EigenschaftenTabelle:
        return self.parent()

    def createEditor(self, eltern, option, index):  # noqa: N802
        name = index.data(_NAME_ROLLE)
        tabelle = self._tabelle()
        werte = tabelle.werte_von(name)
        if werte:
            auswahl = QComboBox(eltern)
            auswahl.addItems([str(wert) for wert in werte])
            # Eine Wahl in der Liste gilt sofort, ohne dass danach noch
            # jemand die Eingabetaste drücken muss.
            auswahl.activated.connect(partial(self._auswahl_uebernehmen, auswahl))
            return auswahl
        art = tabelle.art_von(name)
        if art not in (ART_BILD, ART_FARBE, ART_SCHRIFT):
            return super().createEditor(eltern, option, index)
        return _WertMitKnopf(eltern, partial(self._waehlen, art), self._uebernehmen)

    def _waehlen(self, art: str, alt: str) -> str | None:
        """Der Dialog hinter „…“, je nach Art der Eigenschaft."""
        tabelle = self._tabelle()
        if art == ART_BILD:
            return tabelle.bild_erfragen()
        if art == ART_FARBE:
            return farbe_erfragen(tabelle, alt)
        return schrift_erfragen(tabelle, alt)

    def _auswahl_uebernehmen(self, auswahl: QComboBox, _nummer: int) -> None:
        self._uebernehmen(auswahl)

    def _uebernehmen(self, editor: QWidget) -> None:
        self.commitData.emit(editor)
        self.closeEditor.emit(editor)

    def setEditorData(self, editor, index) -> None:  # noqa: N802
        if isinstance(editor, QComboBox):
            editor.setCurrentText(index.data(Qt.ItemDataRole.DisplayRole) or "")
            return
        if isinstance(editor, _WertMitKnopf):
            editor.feld.setText(index.data(Qt.ItemDataRole.DisplayRole) or "")
            return
        super().setEditorData(editor, index)

    def setModelData(self, editor, model, index) -> None:  # noqa: N802
        if isinstance(editor, QComboBox):
            model.setData(index, editor.currentText())
            return
        if isinstance(editor, _WertMitKnopf):
            model.setData(index, editor.feld.text())
            return
        super().setModelData(editor, model, index)


class EigenschaftenTabelle(QTableWidget):
    #: Meldet jede Änderung von `fehlertext`, damit der Objektinspektor
    #: sie unter der Tabelle anzeigt. Leer heißt: alles in Ordnung.
    fehlertext_geaendert = Signal(str)

    def __init__(self) -> None:
        self._fehlertext = ""
        super().__init__(0, 2)
        self.setHorizontalHeaderLabels(["Eigenschaft", "Wert"])
        # Ohne Zeilennummern: niemand spricht eine Eigenschaft als
        # „Nummer 3" an. Die Spalte kostete nur Platz - links vom Namen,
        # genau dort, wo der Dock auf einem Schulrechner am
        # knappsten ist (M15, Abschnitt 6).
        self.verticalHeader().setVisible(False)
        # Die Wertspalte füllt den Rest der Breite - sonst endete die
        # Tabelle mitten im Dock, und rechts davon stand leerer Grund,
        # während „Kontoverwalt…" nebenan abgeschnitten war. Der
        # Projekt-Explorer macht es seit jeher so.
        kopf = self.horizontalHeader()
        kopf.setStretchLastSection(True)
        kopf.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self._komponente: Any = None
        #: Nach Kategorie gruppiert statt alphabetisch. Umgeschaltet
        #: und gemerkt wird das im Objektinspektor.
        self.nach_kategorie = False
        self._bei_aenderung: Callable[[Any, str, Any, Any], None] | None = None
        self._name_setzen: Callable[[str], None] | None = None
        self._menue_methode_anlegen: Callable[[str], None] | None = None
        self._aktueller_name: str | None = None
        self._aktualisierung_laeuft = False
        self.itemChanged.connect(self._bei_zellenaenderung)
        # `itemActivated` meldet Doppelklick und Eingabetaste -
        # der Zeileneditor für `items`/`lines` war sonst nur mit der
        # Maus erreichbar (M11, Abschnitt 4).
        self.itemActivated.connect(self._bei_doppelklick)
        self.setItemDelegateForColumn(_SPALTE_WERT, _EditorDelegat(self))

    def komponente_anzeigen(
        self,
        komponente: Any,
        *,
        name: str | None = None,
        name_setzen: Callable[[str], None] | None = None,
        bei_aenderung: Callable[[Any, str, Any, Any], None] | None = None,
        menue_methode_anlegen: Callable[[str], None] | None = None,
    ) -> None:
        """Füllt die Tabelle mit allen Eigenschaften von `komponente`:
        den `Prop`s, den aufklappbaren Untereigenschaften (`brush.color`
        als `brush_color`), den Sammlungen, den Menübäumen und den
        Verweisen auf andere Komponenten.

        Sortiert wird alphabetisch oder nach Kategorie, je nach
        `nach_kategorie` (Abschnitt 7.6).

        `name`/`name_setzen` zeigen zusätzlich ganz oben die Zeile
        „name“, den Bezeichner im erzeugten Code (`b_anmelden`), getrennt
        von `caption`/`text`, dem angezeigten Text. Ohne beide Argumente
        (außerhalb eines offenen Designers) bleibt die Zeile weg, weil es
        dann nichts umzubenennen gibt."""
        self._aktualisierung_laeuft = True
        self.fehlertext = ""
        self._komponente = komponente
        self._bei_aenderung = bei_aenderung
        self._name_setzen = name_setzen
        self._menue_methode_anlegen = menue_methode_anlegen
        self._aktueller_name = name
        self._neu_aufbauen()

    def _neu_aufbauen(self) -> None:
        """Baut die Zeilen für die angezeigte Komponente auf - beim
        Anzeigen und nach dem Umschalten der Sortierung."""
        komponente = self._komponente
        name = self._aktueller_name
        self._aktualisierung_laeuft = True
        self.clearSpans()
        props = eigenschaften(type(komponente))
        verschachtelt = [
            eigenschaft_name
            for eigenschaft_name, eintrag in VERSCHACHTELTE_EIGENSCHAFTEN.items()
            if hasattr(komponente, eintrag.attribut)
        ]
        sammlungen = [name for name in SAMMLUNGS_EIGENSCHAFTEN if hasattr(komponente, name)]
        # `hasattr(type(...))` statt `hasattr(komponente, ...)`: ein
        # Baum liefert auch dann eine (leere) Liste, wenn die
        # Komponente ihn gar nicht kennt - nur die Klasse weiß es.
        baeume = [name for name in BAUM_EIGENSCHAFTEN if hasattr(type(komponente), name)]
        # Ein Zeitgeber oder ein Menü ist im Programm nicht zu sehen;
        # ein Klappmenü auf die rechte Maustaste hätte dort nichts, auf
        # dem es aufklappen könnte.
        verweise = [
            name
            for name in VERWEIS_EIGENSCHAFTEN
            if hasattr(type(komponente), name)
            and not getattr(type(komponente), "nur_im_designer", False)
        ]
        namen = sorted([*props, *verschachtelt, *sammlungen, *baeume, *verweise])
        gruppen: list[tuple[str | None, list[str]]] = [(None, namen)]
        if self.nach_kategorie:
            nach_gruppe: dict[str, list[str]] = {}
            for eigenschaft_name in namen:
                nach_gruppe.setdefault(self.kategorie_von(eigenschaft_name), []).append(
                    eigenschaft_name
                )
            gruppen = [(kategorie, nach_gruppe[kategorie]) for kategorie in sorted(nach_gruppe)]
        zeigt_name_zeile = name is not None and self._name_setzen is not None
        ueberschriften = len(gruppen) if self.nach_kategorie else 0
        self.setRowCount(len(namen) + ueberschriften + (1 if zeigt_name_zeile else 0))

        zeile = 0
        if zeigt_name_zeile:
            self._zeile_anlegen(zeile, "name", _NAME_ZEILE)
            self.item(zeile, _SPALTE_WERT).setText(name)
            zeile += 1

        for kategorie, gruppe in gruppen:
            if kategorie is not None:
                self._ueberschrift_anlegen(zeile, kategorie)
                zeile += 1
            for eigenschaft_name in gruppe:
                self._zeile_anlegen(zeile, eigenschaft_name, eigenschaft_name)
                wert_element = self.item(zeile, _SPALTE_WERT)
                self._zelle_aus_komponente_fuellen(
                    wert_element, self._typ_von(eigenschaft_name), eigenschaft_name
                )
                zeile += 1

        self._aktualisierung_laeuft = False

    def ansicht_setzen(self, nach_kategorie: bool) -> None:
        """Schaltet zwischen alphabetischer Liste und Gruppen nach
        Kategorie um und baut die Zeilen neu auf."""
        if nach_kategorie == self.nach_kategorie:
            return
        self.nach_kategorie = nach_kategorie
        if self._komponente is not None:
            self._neu_aufbauen()

    def kategorie_von(self, name: str) -> str:
        """Die Gruppe einer Zeile in der Ansicht nach Kategorie."""
        if name in SAMMLUNGS_EIGENSCHAFTEN or name in BAUM_EIGENSCHAFTEN:
            return "Daten"
        if name in VERWEIS_EIGENSCHAFTEN:
            return "Verhalten"
        verschachtelt = VERSCHACHTELTE_EIGENSCHAFTEN.get(name)
        if verschachtelt is not None:
            return verschachtelt.kategorie
        prop = eigenschaften(type(self._komponente)).get(name)
        return prop.kategorie if prop is not None else "Allgemein"

    def _ueberschrift_anlegen(self, zeile: int, kategorie: str) -> None:
        """Eine Zwischenzeile mit dem Namen der Kategorie, über beide
        Spalten. Sie lässt sich weder bearbeiten noch auswählen."""
        ueberschrift = QTableWidgetItem(kategorie)
        ueberschrift.setFlags(Qt.ItemFlag.ItemIsEnabled)
        schrift = ueberschrift.font()
        schrift.setBold(True)
        ueberschrift.setFont(schrift)
        self.setItem(zeile, _SPALTE_NAME, ueberschrift)
        leer = QTableWidgetItem()
        leer.setFlags(Qt.ItemFlag.ItemIsEnabled)
        self.setItem(zeile, _SPALTE_WERT, leer)
        self.setSpan(zeile, _SPALTE_NAME, 1, 2)

    @property
    def fehlertext(self) -> str:
        """Warum die letzte Eingabe abgelehnt wurde, leer wenn nicht."""
        return self._fehlertext

    @fehlertext.setter
    def fehlertext(self, text: str) -> None:
        if text == self._fehlertext:
            return
        self._fehlertext = text
        self.fehlertext_geaendert.emit(text)

    def wert_pruefen(self, name: str, wert: Any) -> str:
        """Warum `wert` für diese Eigenschaft nicht taugt, oder leer.

        Geprüft wird vor dem Setzen. Was die Komponente selbst
        ablehnt (`NatterPropertyError`), fängt `_bei_zellenaenderung`
        danach ab; hier stehen die Fälle, die sie klaglos hinnähme.
        """
        art = self.art_von(name)
        if art == ART_FARBE:
            if not wert:
                if self._standardwert_von(name) == "":
                    return ""
                return f"{name} braucht eine Farbe, z. B. #ff8800 für Orange."
            if not QColor.isValidColorName(wert):
                return (
                    f"„{wert}“ ist keine Farbe. Erwartet wird #RRGGBB, "
                    "z. B. #ff8800 für Orange."
                )
        if art == ART_BILD and wert:
            pfad = Path(wert)
            ordner = self.projektordner()
            if not pfad.is_absolute() and ordner is not None:
                pfad = ordner / pfad
            if not pfad.is_file():
                return f"Die Bilddatei „{wert}“ gibt es nicht."
        return ""

    def _standardwert_von(self, name: str) -> Any:
        verschachtelt = VERSCHACHTELTE_EIGENSCHAFTEN.get(name)
        if verschachtelt is not None:
            return verschachtelt.standardwert
        prop = eigenschaften(type(self._komponente)).get(name)
        return prop.standardwert if prop is not None else None

    def werte_von(self, name: Any) -> tuple[Any, ...]:
        """Die feste Auswahl einer Eigenschaft (`Prop.werte`), leer,
        wenn jeder Wert ihres Typs erlaubt ist."""
        if not isinstance(name, str):
            return ()
        if name in VERWEIS_EIGENSCHAFTEN:
            return (KEIN_VERWEIS, *self.klappmenues())
        prop = eigenschaften(type(self._komponente)).get(name)
        return prop.werte if prop is not None else ()

    def art_von(self, name: Any) -> str:
        """Welcher Editor zu dieser Zeile gehört (`Prop.art`), leer für
        die gewöhnliche Textzelle."""
        if not isinstance(name, str):
            return ""
        verschachtelt = VERSCHACHTELTE_EIGENSCHAFTEN.get(name)
        if verschachtelt is not None:
            return verschachtelt.art
        prop = eigenschaften(type(self._komponente)).get(name)
        return getattr(prop, "art", "") if prop is not None else ""

    def _formular(self) -> Any:
        komponente = self._komponente
        formular = getattr(komponente, "_formular", None)
        return formular() if callable(formular) else komponente

    def klappmenues(self) -> list[str]:
        """Die Namen aller Klappmenüs auf dem Formular - die Auswahl
        in der Zeile `popup_menu`."""
        from pcl.components.menus import PopupMenu

        formular = self._formular()
        if formular is None:
            return []
        return sorted(
            name
            for name, wert in vars(formular).items()
            if isinstance(wert, PopupMenu)
        )

    def _verweis_name(self, ziel: Any) -> str:
        if ziel is None:
            return KEIN_VERWEIS
        formular = self._formular()
        for name, wert in vars(formular).items() if formular is not None else ():
            if wert is ziel:
                return name
        return KEIN_VERWEIS

    def _verweis_aufloesen(self, text: str) -> Any:
        """Die Komponente zum Namen in der Zelle; `ValueError` mit
        deutscher Meldung, wenn es kein solches Klappmenü gibt."""
        text = text.strip()
        if text in ("", KEIN_VERWEIS):
            return None
        if text not in self.klappmenues():
            raise ValueError(f"Auf dem Formular gibt es kein Klappmenü „{text}“.")
        return getattr(self._formular(), text)

    def projektordner(self) -> Path | None:
        """Der Projektordner des angezeigten Formulars, den der
        Designer beim Laden vermerkt; `None` außerhalb des Designers."""
        ordner = getattr(self._formular(), "_projektordner", None)
        return Path(ordner) if ordner is not None else None

    def bild_erfragen(self) -> str | None:
        """Der Dialog hinter „…“ in der Zeile `picture`.

        Ein Bild außerhalb des Projekts wird nach `assets/` kopiert,
        wie beim Ziehen in den Designer; in der Zelle steht danach
        der Pfad relativ zum Projektordner. Nur so findet das
        gestartete Programm das Bild auch auf einem anderen Rechner.
        """
        ordner = self.projektordner()
        pfad = bilddatei_erfragen(self, ordner)
        if not pfad:
            return None
        if ordner is None:
            return pfad
        from ide.designer.bilder import bild_in_assets_uebernehmen

        _, relativ = bild_in_assets_uebernehmen(Path(pfad), ordner)
        return relativ

    def _typ_von(self, name: str) -> type:
        if name in SAMMLUNGS_EIGENSCHAFTEN or name in BAUM_EIGENSCHAFTEN:
            return list
        if name in VERWEIS_EIGENSCHAFTEN:
            return object
        verschachtelt = VERSCHACHTELTE_EIGENSCHAFTEN.get(name)
        if verschachtelt is not None:
            return verschachtelt.typ
        return eigenschaften(type(self._komponente))[name].typ

    def _zeile_anlegen(self, zeile: int, anzeige_name: str, rollen_wert: Any) -> None:
        # Jede Zeile trägt ihren Hilfetext als Kurzhinweis (M11,
        # Abschnitt 4). Die Texte stehen seit jeher an den Eigenschaften
        # selbst (`Prop(doc=...)`), wurden aber nirgends angezeigt -
        # „increment“, „frequency“ oder „item_index“ musste man raten.
        hinweis = self.hilfetext(anzeige_name if rollen_wert is not _NAME_ZEILE else "name")
        name_element = QTableWidgetItem(anzeige_name)
        name_element.setFlags(name_element.flags() & ~Qt.ItemFlag.ItemIsEditable)
        name_element.setToolTip(hinweis)
        self.setItem(zeile, _SPALTE_NAME, name_element)

        wert_element = QTableWidgetItem()
        wert_element.setData(_NAME_ROLLE, rollen_wert)
        wert_element.setToolTip(hinweis)
        self.setItem(zeile, _SPALTE_WERT, wert_element)

    def hilfetext(self, name: str) -> str:
        """Der Hilfetext zu einer Zeile – aus derselben Quelle, aus der
        auch die Komponenten-Referenz ihn nimmt."""
        if name == "name":
            return _NAME_DOKU
        if name in SAMMLUNGS_EIGENSCHAFTEN:
            return SAMMLUNGS_DOKU.get(name, "")
        if name in BAUM_EIGENSCHAFTEN:
            return BAUM_DOKU.get(name, "")
        if name in VERWEIS_EIGENSCHAFTEN:
            return VERWEIS_DOKU.get(name, "")
        verschachtelt = VERSCHACHTELTE_EIGENSCHAFTEN.get(name)
        if verschachtelt is not None:
            return verschachtelt.doc
        prop = eigenschaften(type(self._komponente)).get(name)
        return prop.doc if prop is not None else ""

    def _wert_lesen(self, name: str) -> Any:
        return wert_lesen(self._komponente, name)

    def _wert_setzen(self, name: str, wert: Any) -> None:
        """Setzt den Wert live und meldet die Änderung weiter, damit der
        Designer sie in die `.pfm` und den generierten Code übernimmt.

        Ohne diese Meldung änderte eine Eingabe im Objektinspektor real
        nur das Live-Objekt: die Anzeige stimmte sofort, die `.pfm` und
        `u_*_design.py` blieben aber unverändert – die Änderung war nach
        dem nächsten Öffnen weg und erreichte das laufende Programm nie."""
        alter_wert = wert_lesen(self._komponente, name)
        wert_setzen(self._komponente, name, wert)
        if self._bei_aenderung is not None:
            self._bei_aenderung(self._komponente, name, alter_wert, wert)

    def _zelle_aus_komponente_fuellen(
        self, element: QTableWidgetItem, typ: type, name: str
    ) -> None:
        wert = self._wert_lesen(name)
        if name in VERWEIS_EIGENSCHAFTEN:
            element.setText(self._verweis_name(wert))
        elif typ is bool:
            element.setFlags(
                (element.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                & ~Qt.ItemFlag.ItemIsEditable
            )
            element.setCheckState(Qt.CheckState.Checked if wert else Qt.CheckState.Unchecked)
        elif typ is list:
            # Nicht direkt in der Zelle bearbeitbar, sondern per
            # Doppelklick über `SammlungDialog` (dort „…“-Knopf).
            element.setFlags(element.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # Singular und Plural: „(1 Einträge)" stand real in der
            # Zeile, sobald ein Menü genau einen obersten Eintrag hatte.
            anzahl = len(wert)
            if not anzahl:
                element.setText("(leer)")
            elif anzahl == 1:
                element.setText("(1 Eintrag)")
            else:
                element.setText(f"({anzahl} Einträge)")
        else:
            # `text_aus_wert` statt `str`: ein Datum steht deutsch in der
            # Zelle (`20.09.2026`), nicht als `2026-09-20`.
            element.setText(text_aus_wert(wert))

    def _bei_zellenaenderung(self, element: QTableWidgetItem) -> None:
        if self._aktualisierung_laeuft or element.column() != _SPALTE_WERT:
            return

        name = element.data(_NAME_ROLLE)
        if name is None:
            return  # Überschrift einer Kategorie
        if name is _NAME_ZEILE:
            self._name_zeile_bearbeiten(element)
            return

        typ = self._typ_von(name)
        if typ is list:
            return  # nur über den Doppelklick-Dialog änderbar

        if name in VERWEIS_EIGENSCHAFTEN:
            try:
                neuer_wert: Any = self._verweis_aufloesen(element.text())
            except ValueError as fehler:
                self.fehlertext = str(fehler)
                self._zelle_zuruecksetzen(element, typ, name)
                return
        elif typ is bool:
            neuer_wert = element.checkState() == Qt.CheckState.Checked
        else:
            try:
                neuer_wert = wert_aus_text(typ, element.text())
            except (ValueError, TypeError):
                self.fehlertext = f"{element.text()!r} ist keine gültige Eingabe für {name}."
                self._zelle_zuruecksetzen(element, typ, name)
                return
            meldung = self.wert_pruefen(name, neuer_wert)
            if meldung:
                self.fehlertext = meldung
                self._zelle_zuruecksetzen(element, typ, name)
                return

        try:
            self._wert_setzen(name, neuer_wert)
        except NatterPropertyError as fehler:
            self.fehlertext = str(fehler)
            self._zelle_zuruecksetzen(element, typ, name)
            return

        # Manche Komponenten berichtigen einen Wert, statt ihn
        # abzulehnen: `RadioGroup.item_index = 6` ohne sechste Option
        # fällt auf -1 zurück, weil eine Auswahl, die niemand sieht,
        # schlimmer wäre. Ohne diesen Abgleich stünde in der Zelle
        # weiter die 6, während die Komponente längst -1 führt - der
        # Objektinspektor zeigte etwas an, das es nicht gibt.
        #
        # Dasselbe, wenn nur die Schreibweise abweicht: „0.5“ wird
        # angenommen und steht danach als „0,5“ da wie jede andere
        # Kommazahl in der Tabelle.
        if self._wert_lesen(name) != neuer_wert or (
            typ is float and element.text() != text_aus_wert(neuer_wert)
        ):
            self._zelle_zuruecksetzen(element, typ, name)

        self.fehlertext = ""

    def _bei_doppelklick(self, element: QTableWidgetItem) -> None:
        """Öffnet den passenden Editor – das ist der „…“-Knopf in
        der Wertspalte.

        Für Sammlungen (`items`, `lines`) den Zeileneditor, für Bäume
        (`entries`) den Menü-Editor. Beide sind modal und liefern die
        fertige Liste zurück; die Unterscheidung steht nur hier.
        """
        name = element.data(_NAME_ROLLE)
        if name in BAUM_EIGENSCHAFTEN:
            self._menue_bearbeiten(element, name)
            return
        if name not in SAMMLUNGS_EIGENSCHAFTEN:
            return
        dialog = SammlungDialog(name, self._wert_lesen(name), self)
        if dialog.exec() != SammlungDialog.DialogCode.Accepted:
            return
        self._wert_setzen(name, dialog.zeilen())
        self._zelle_zuruecksetzen(element, list, name)
        self.fehlertext = ""

    def _menue_bearbeiten(self, element: QTableWidgetItem, name: str) -> None:
        """Der Menü-Editor hinter der Zeile `entries`.

        Übernommen wird auch nach „Schließen", sofern vorher
        „Anwenden" gedrückt wurde – sonst wäre „Anwenden" ein Knopf,
        dessen Wirkung beim Schließen wieder verschwindet.
        """
        dialog = MenueEditor(
            self._wert_lesen(name), self, methode_anlegen=self._menue_methode_anlegen
        )
        angenommen = dialog.exec() == MenueEditor.DialogCode.Accepted
        if not angenommen and not dialog.uebernommen:
            return
        self._wert_setzen(name, dialog.eintraege())
        self._zelle_zuruecksetzen(element, list, name)
        self.fehlertext = ""

    def _name_zeile_bearbeiten(self, element: QTableWidgetItem) -> None:
        """Zeile „name“ (Bezeichner im Code, Rückmeldung September
 2026): Umbenennen läuft über `DesignerCanvas.komponente_umbenennen`
 (Undo, `.pfm`/Code-Aktualisierung), nicht über `setattr` – deshalb
 der eigene `name_setzen`-Rückruf statt `_wert_setzen`."""
        neuer_name = element.text()
        try:
            self._name_setzen(neuer_name)
        except (ValueError, TypeError) as fehler:
            # `TypeError` auch: die Typprüfung eines Props meldet sich
            # so, und ohne diesen Zweig landete sie in der allgemeinen
            # Fehlermeldung der IDE (Punkt 113).
            self.fehlertext = str(fehler)
            self._aktualisierung_laeuft = True
            element.setText(self._aktueller_name)
            self._aktualisierung_laeuft = False
            return
        self._aktueller_name = neuer_name
        self.fehlertext = ""

    def _zelle_zuruecksetzen(self, element: QTableWidgetItem, typ: type, name: str) -> None:
        self._aktualisierung_laeuft = True
        self._zelle_aus_komponente_fuellen(element, typ, name)
        self._aktualisierung_laeuft = False
