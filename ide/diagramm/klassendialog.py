"""Eigenschaften-Dialog für UML-Klassen (Abschnitt 13.4,
M9 Schritt 12).

entschieden, mit Bildschirmfotos des
Dia-Dialogs „Eigenschaften: UML – Class“ belegt: die Inhalte einer
Klasse werden nicht direkt auf der Zeichenfläche bearbeitet,
sondern hier. Die Zeichenfläche bleibt für das Anordnen zuständig
(platzieren, verschieben, Größe, verbinden), der Dialog für den Inhalt.

Notiz und Paket bekommen keinen Dialog – sie haben nur ein
Textfeld und werden weiterhin direkt beschriftet. Struktogramm und
Entscheidungstabelle ebenso.

Der Dialog arbeitet auf einer Kopie der Form. Erst „Anwenden“ bzw.
„OK“ überträgt sie; „Schließen“ verwirft alles seit dem letzten
Anwenden. Dadurch ist ein Dialogdurchgang genau ein Undo-Schritt, egal
wie viele Felder geändert wurden.
"""

from __future__ import annotations

import copy
from typing import Any

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ide.diagramm.uml_modell import (
    RICHTUNGEN,
    SICHTBARKEITEN,
    VERERBUNGSARTEN,
    attribut_zeile,
    operation_zeile,
)

#: Deutsche Beschriftungen für die Auswahllisten. Intern bleiben die
#: englischen Schlüssel, weil sie so in der `.pdiag` stehen.
SICHTBARKEIT_TEXT = {
    "public": "Public",
    "private": "Private",
    "protected": "Protected",
    "implementation": "Implementation",
}
VERERBUNG_TEXT = {"abstract": "Abstrakt", "virtual": "Virtuell", "leaf": "Endgültig"}
RICHTUNG_TEXT = {
    "undefined": "Undefiniert",
    "in": "Hinein",
    "out": "Hinaus",
    "inout": "Beides",
}


def _auswahl(werte: tuple[str, ...], texte: dict[str, str]) -> QComboBox:
    feld = QComboBox()
    for wert in werte:
        feld.addItem(texte[wert], wert)
    return feld


class _Liste(QWidget):
    """Liste mit den vier Knöpfen Neu/Löschen/Hoch/Runter – im
    Dia-Dialog kommt dieses Muster dreimal vor (Attribute, Operationen,
    Parameter, Vorlagen), deshalb einmal gebaut."""

    def __init__(self, beschriftung: str = "") -> None:
        super().__init__()
        self.liste = QListWidget()
        self.neu = QPushButton("&Neu")
        self.loeschen = QPushButton("&Löschen")
        self.hoch = QPushButton("&Hoch")
        self.runter = QPushButton("&Runter")

        knopfspalte = QVBoxLayout()
        for knopf in (self.neu, self.loeschen, self.hoch, self.runter):
            knopfspalte.addWidget(knopf)
        knopfspalte.addStretch(1)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if beschriftung:
            spalte = QVBoxLayout()
            spalte.addWidget(QLabel(beschriftung))
            spalte.addWidget(self.liste)
            layout.addLayout(spalte, 1)
        else:
            layout.addWidget(self.liste, 1)
        layout.addLayout(knopfspalte)

    def fuellen(self, texte: list[str], auswahl: int | None) -> None:
        self.liste.blockSignals(True)
        self.liste.clear()
        self.liste.addItems(texte)
        if auswahl is not None and 0 <= auswahl < len(texte):
            self.liste.setCurrentRow(auswahl)
        self.liste.blockSignals(False)


class KlassenDialog(QDialog):
    """Der Dialog aus Abschnitt 13.4 mit fünf Reitern."""

    def __init__(self, shape: dict[str, Any], eltern: QWidget | None = None) -> None:
        super().__init__(eltern)
        self.setWindowTitle("Eigenschaften: UML – Klasse")
        self.ziel = shape
        #: Alles läuft auf der Kopie; erst „Anwenden“ überträgt sie.
        self.entwurf: dict[str, Any] = copy.deepcopy(shape)
        self.uebernommen = False

        self.reiter = QTabWidget()
        self.reiter.addTab(self._reiter_klasse(), "&Klasse")
        self.reiter.addTab(self._reiter_attribute(), "&Attribute")
        self.reiter.addTab(self._reiter_operationen(), "&Operationen")
        self.reiter.addTab(self._reiter_vorlagen(), "&Vorlagen")
        self.reiter.addTab(self._reiter_stil(), "&Stil")

        self.knoepfe = QDialogButtonBox()
        self.schliessen_knopf = self.knoepfe.addButton(
            "&Schließen", QDialogButtonBox.ButtonRole.RejectRole
        )
        self.anwenden_knopf = self.knoepfe.addButton(
            "&Anwenden", QDialogButtonBox.ButtonRole.ApplyRole
        )
        self.ok_knopf = self.knoepfe.addButton(
            "&OK", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.schliessen_knopf.clicked.connect(self.reject)
        self.anwenden_knopf.clicked.connect(self.anwenden)
        self.ok_knopf.clicked.connect(self._ok)

        layout = QVBoxLayout(self)
        layout.addWidget(self.reiter)
        layout.addWidget(self.knoepfe)
        self.resize(640, 520)

        self._anzeigen()

    # -- Reiter „Klasse“ -------------------------------------------------

    def _reiter_klasse(self) -> QWidget:
        seite = QWidget()
        self.klassenname = QLineEdit()
        self.stereotyp = QLineEdit()
        self.kommentar = QPlainTextEdit()
        self.kommentar.setFixedHeight(70)

        self.abstrakt = QCheckBox("Abstrakt")
        self.attribute_sichtbar = QCheckBox("Attribute sichtbar")
        self.operationen_sichtbar = QCheckBox("Operationen sichtbar")
        self.operationen_umbrechen = QCheckBox("Operationen umbrechen")
        self.kommentare_sichtbar = QCheckBox("Kommentare sichtbar")
        self.doku_anzeigen = QCheckBox("Dokumentationsauszeichnung anzeigen")
        self.attribute_unterdruecken = QCheckBox("Attribute unterdrücken")
        self.operationen_unterdruecken = QCheckBox("Operationen unterdrücken")

        self.umbruch_operationen = QSpinBox()
        self.umbruch_operationen.setRange(0, 999)
        self.umbruch_kommentare = QSpinBox()
        self.umbruch_kommentare.setRange(0, 999)

        oben = QFormLayout()
        oben.addRow("Klassenname:", self.klassenname)
        oben.addRow("Stereotyp:", self.stereotyp)
        oben.addRow("Kommentar:", self.kommentar)

        links = QVBoxLayout()
        for feld in (
            self.abstrakt,
            self.attribute_sichtbar,
            self.operationen_sichtbar,
            self.operationen_umbrechen,
            self.kommentare_sichtbar,
            self.doku_anzeigen,
        ):
            links.addWidget(feld)
        links.addStretch(1)

        rechts = QFormLayout()
        rechts.addRow(self.attribute_unterdruecken)
        rechts.addRow(self.operationen_unterdruecken)
        rechts.addRow("Umbruch nach dieser Länge:", self.umbruch_operationen)
        rechts.addRow("Umbruch nach dieser Länge:", self.umbruch_kommentare)

        unten = QHBoxLayout()
        unten.addLayout(links, 1)
        unten.addLayout(rechts, 1)

        layout = QVBoxLayout(seite)
        layout.addLayout(oben)
        layout.addLayout(unten)
        layout.addStretch(1)

        # Jede Änderung wandert sofort in den Entwurf. Ohne das ginge
        # sie verloren, sobald ein anderer Reiter die Anzeige auffrischt
        # (real passiert: Klassennamen tippen, dann ein Attribut
        # anlegen - der Name stand wieder auf dem alten Wert).
        for feld in (self.klassenname, self.stereotyp):
            feld.textChanged.connect(self._kopf_uebernehmen)
        self.kommentar.textChanged.connect(self._kopf_uebernehmen)
        for schalter in (
            self.abstrakt,
            self.attribute_sichtbar,
            self.operationen_sichtbar,
            self.operationen_umbrechen,
            self.kommentare_sichtbar,
            self.doku_anzeigen,
            self.attribute_unterdruecken,
            self.operationen_unterdruecken,
        ):
            schalter.toggled.connect(self._kopf_uebernehmen)
        self.umbruch_operationen.valueChanged.connect(self._kopf_uebernehmen)
        self.umbruch_kommentare.valueChanged.connect(self._kopf_uebernehmen)
        return seite

    def _kopf_uebernehmen(self) -> None:
        if getattr(self, "_laeuft", False):
            return
        self.entwurf.update(self._kopfwerte())

    def _kopfwerte(self) -> dict[str, Any]:
        return {
            "name": self.klassenname.text(),
            "stereotype": self.stereotyp.text(),
            "comment": self.kommentar.toPlainText(),
            "abstract": self.abstrakt.isChecked(),
            "attributes_visible": self.attribute_sichtbar.isChecked(),
            "operations_visible": self.operationen_sichtbar.isChecked(),
            "attributes_suppressed": self.attribute_unterdruecken.isChecked(),
            "operations_suppressed": self.operationen_unterdruecken.isChecked(),
            "comments_visible": self.kommentare_sichtbar.isChecked(),
            "wrap_operations": self.operationen_umbrechen.isChecked(),
            "wrap_after_operations": self.umbruch_operationen.value(),
            "wrap_after_comments": self.umbruch_kommentare.value(),
            "show_documentation": self.doku_anzeigen.isChecked(),
        }

    # -- Reiter „Attribute“ ----------------------------------------------

    def _reiter_attribute(self) -> QWidget:
        seite = QWidget()
        self.attributliste = _Liste()
        self.attribut_name = QLineEdit()
        self.attribut_typ = QLineEdit()
        self.attribut_wert = QLineEdit()
        self.attribut_kommentar = QPlainTextEdit()
        self.attribut_kommentar.setFixedHeight(56)
        self.attribut_sichtbarkeit = _auswahl(SICHTBARKEITEN, SICHTBARKEIT_TEXT)
        self.attribut_klassenbereich = QCheckBox("Klassen-Gültigkeitsbereich")

        self.attributdaten = QGroupBox("Attributdaten")
        formular = QFormLayout(self.attributdaten)
        formular.addRow("Name:", self.attribut_name)
        formular.addRow("Typ:", self.attribut_typ)
        formular.addRow("Wert:", self.attribut_wert)
        formular.addRow("Kommentar:", self.attribut_kommentar)
        formular.addRow("Sichtbarkeit:", self.attribut_sichtbarkeit)
        formular.addRow(self.attribut_klassenbereich)

        layout = QVBoxLayout(seite)
        layout.addWidget(self.attributliste, 1)
        layout.addWidget(self.attributdaten)

        self.attributliste.neu.clicked.connect(self._attribut_neu)
        self.attributliste.loeschen.clicked.connect(self._attribut_loeschen)
        self.attributliste.hoch.clicked.connect(lambda: self._attribut_schieben(-1))
        self.attributliste.runter.clicked.connect(lambda: self._attribut_schieben(1))
        self.attributliste.liste.currentRowChanged.connect(self._attribut_gewaehlt)
        for feld in (self.attribut_name, self.attribut_typ, self.attribut_wert):
            feld.textChanged.connect(self._attribut_uebernehmen)
        self.attribut_kommentar.textChanged.connect(self._attribut_uebernehmen)
        self.attribut_sichtbarkeit.currentIndexChanged.connect(self._attribut_uebernehmen)
        self.attribut_klassenbereich.toggled.connect(self._attribut_uebernehmen)
        return seite

    # -- Reiter „Operationen“ --------------------------------------------

    def _reiter_operationen(self) -> QWidget:
        seite = QWidget()
        self.operationsliste = _Liste()
        self.operation_name = QLineEdit()
        self.operation_typ = QLineEdit()
        self.operation_stereotyp = QLineEdit()
        self.operation_kommentar = QPlainTextEdit()
        self.operation_kommentar.setFixedHeight(48)
        self.operation_sichtbarkeit = _auswahl(SICHTBARKEITEN, SICHTBARKEIT_TEXT)
        self.operation_vererbung = _auswahl(VERERBUNGSARTEN, VERERBUNG_TEXT)
        self.operation_klassenbereich = QCheckBox("Klassen-Gültigkeitsbereich")
        self.operation_anfrage = QCheckBox("Anfrage")

        self.operationsdaten = QGroupBox("Operationsdaten")
        links = QFormLayout()
        links.addRow("Name:", self.operation_name)
        links.addRow("Typ:", self.operation_typ)
        links.addRow("Stereotyp:", self.operation_stereotyp)
        rechts = QFormLayout()
        rechts.addRow("Sichtbarkeit:", self.operation_sichtbarkeit)
        rechts.addRow("Typ der Vererbung:", self.operation_vererbung)
        rechts.addRow(self.operation_klassenbereich)
        rechts.addRow(self.operation_anfrage)
        rechts.addRow("Kommentar:", self.operation_kommentar)
        daten_layout = QHBoxLayout(self.operationsdaten)
        daten_layout.addLayout(links, 1)
        daten_layout.addLayout(rechts, 1)

        # Parameter der ausgewählten Operation
        self.parameterliste = _Liste("Parameter:")
        self.parameter_name = QLineEdit()
        self.parameter_typ = QLineEdit()
        self.parameter_vorgabe = QLineEdit()
        self.parameter_kommentar = QPlainTextEdit()
        self.parameter_kommentar.setFixedHeight(48)
        self.parameter_richtung = _auswahl(RICHTUNGEN, RICHTUNG_TEXT)

        self.parameterdaten = QGroupBox("Parameterdaten")
        p_links = QFormLayout()
        p_links.addRow("Name:", self.parameter_name)
        p_links.addRow("Typ:", self.parameter_typ)
        p_links.addRow("Vorgabewert:", self.parameter_vorgabe)
        p_rechts = QFormLayout()
        p_rechts.addRow("Richtung:", self.parameter_richtung)
        p_rechts.addRow("Kommentar:", self.parameter_kommentar)
        p_layout = QHBoxLayout(self.parameterdaten)
        p_layout.addLayout(p_links, 1)
        p_layout.addLayout(p_rechts, 1)

        layout = QVBoxLayout(seite)
        layout.addWidget(self.operationsliste, 1)
        layout.addWidget(self.operationsdaten)
        layout.addWidget(self.parameterliste)
        layout.addWidget(self.parameterdaten)

        self.operationsliste.neu.clicked.connect(self._operation_neu)
        self.operationsliste.loeschen.clicked.connect(self._operation_loeschen)
        self.operationsliste.hoch.clicked.connect(lambda: self._operation_schieben(-1))
        self.operationsliste.runter.clicked.connect(lambda: self._operation_schieben(1))
        self.operationsliste.liste.currentRowChanged.connect(self._operation_gewaehlt)
        for feld in (self.operation_name, self.operation_typ, self.operation_stereotyp):
            feld.textChanged.connect(self._operation_uebernehmen)
        self.operation_kommentar.textChanged.connect(self._operation_uebernehmen)
        self.operation_sichtbarkeit.currentIndexChanged.connect(self._operation_uebernehmen)
        self.operation_vererbung.currentIndexChanged.connect(self._operation_uebernehmen)
        self.operation_klassenbereich.toggled.connect(self._operation_uebernehmen)
        self.operation_anfrage.toggled.connect(self._operation_uebernehmen)

        self.parameterliste.neu.clicked.connect(self._parameter_neu)
        self.parameterliste.loeschen.clicked.connect(self._parameter_loeschen)
        self.parameterliste.hoch.clicked.connect(lambda: self._parameter_schieben(-1))
        self.parameterliste.runter.clicked.connect(lambda: self._parameter_schieben(1))
        self.parameterliste.liste.currentRowChanged.connect(self._parameter_gewaehlt)
        for feld in (self.parameter_name, self.parameter_typ, self.parameter_vorgabe):
            feld.textChanged.connect(self._parameter_uebernehmen)
        self.parameter_kommentar.textChanged.connect(self._parameter_uebernehmen)
        self.parameter_richtung.currentIndexChanged.connect(self._parameter_uebernehmen)
        return seite

    # -- Reiter „Vorlagen“ -----------------------------------------------

    def _reiter_vorlagen(self) -> QWidget:
        seite = QWidget()
        self.vorlageklasse = QCheckBox("Vorlageklasse")
        self.vorlagenliste = _Liste()
        self.vorlage_name = QLineEdit()
        self.vorlage_typ = QLineEdit()

        self.vorlagendaten = QGroupBox("Formelle Parameterdaten")
        formular = QFormLayout(self.vorlagendaten)
        formular.addRow("Name:", self.vorlage_name)
        formular.addRow("Typ:", self.vorlage_typ)

        layout = QVBoxLayout(seite)
        layout.addWidget(self.vorlageklasse)
        layout.addWidget(self.vorlagenliste, 1)
        layout.addWidget(self.vorlagendaten)

        self.vorlageklasse.toggled.connect(self._vorlage_schalter)
        self.vorlagenliste.neu.clicked.connect(self._vorlage_neu)
        self.vorlagenliste.loeschen.clicked.connect(self._vorlage_loeschen)
        self.vorlagenliste.hoch.clicked.connect(lambda: self._vorlage_schieben(-1))
        self.vorlagenliste.runter.clicked.connect(lambda: self._vorlage_schieben(1))
        self.vorlagenliste.liste.currentRowChanged.connect(self._vorlage_gewaehlt)
        for feld in (self.vorlage_name, self.vorlage_typ):
            feld.textChanged.connect(self._vorlage_uebernehmen)
        return seite

    # -- Reiter „Stil“ ---------------------------------------------------

    def _reiter_stil(self) -> QWidget:
        """Füllung, Linie und Schriftgröße. Position und Größe bleiben im
        Eigenschaften-Bereich rechts – die braucht man beim Anordnen
        laufend, dafür will niemand einen Dialog öffnen."""
        seite = QWidget()
        self.fuellfarbe = QLineEdit()
        self.fuellfarbe.setPlaceholderText("(Stilvorlage)")
        self.linienfarbe = QLineEdit()
        self.linienfarbe.setPlaceholderText("(Stilvorlage)")
        self.schriftgroesse = QSpinBox()
        self.schriftgroesse.setRange(0, 48)
        self.schriftgroesse.setSpecialValueText("(Stilvorlage)")

        formular = QFormLayout(seite)
        formular.addRow("Füllung (#RRGGBB):", self.fuellfarbe)
        formular.addRow("Linie (#RRGGBB):", self.linienfarbe)
        formular.addRow("Schriftgröße:", self.schriftgroesse)
        return seite

    # -- Anzeige ----------------------------------------------------------

    def _anzeigen(self) -> None:
        """Füllt alle Felder aus dem Entwurf. `_laeuft` verhindert, dass
        das Befüllen selbst wieder Änderungen einträgt."""
        self._laeuft = True
        try:
            e = self.entwurf
            self.klassenname.setText(str(e.get("name", "")))
            self.stereotyp.setText(str(e.get("stereotype", "")))
            self.kommentar.setPlainText(str(e.get("comment", "")))
            self.abstrakt.setChecked(
                bool(e.get("abstract")) or e.get("kind") == "abstract_class"
            )
            self.attribute_sichtbar.setChecked(e.get("attributes_visible", True))
            self.operationen_sichtbar.setChecked(e.get("operations_visible", True))
            self.operationen_umbrechen.setChecked(e.get("wrap_operations", False))
            self.kommentare_sichtbar.setChecked(e.get("comments_visible", False))
            self.doku_anzeigen.setChecked(e.get("show_documentation", False))
            self.attribute_unterdruecken.setChecked(e.get("attributes_suppressed", False))
            self.operationen_unterdruecken.setChecked(
                e.get("operations_suppressed", False)
            )
            self.umbruch_operationen.setValue(int(e.get("wrap_after_operations", 40)))
            self.umbruch_kommentare.setValue(int(e.get("wrap_after_comments", 17)))

            self.attributliste.fuellen(
                [attribut_zeile(a) for a in e.get("attributes") or []],
                self.attributliste.liste.currentRow(),
            )
            self.operationsliste.fuellen(
                [operation_zeile(o) for o in e.get("operations") or []],
                self.operationsliste.liste.currentRow(),
            )
            self.vorlageklasse.setChecked(bool(e.get("template")))
            self.vorlagenliste.fuellen(
                [str(v.get("name", "")) for v in e.get("template_parameters") or []],
                self.vorlagenliste.liste.currentRow(),
            )

            self.fuellfarbe.setText(str(e.get("fill", "")))
            self.linienfarbe.setText(str(e.get("line", "")))
            self.schriftgroesse.setValue(int(e.get("font_size", 0) or 0))
        finally:
            self._laeuft = False

        self._attribut_gewaehlt(self.attributliste.liste.currentRow())
        self._operation_gewaehlt(self.operationsliste.liste.currentRow())
        self._vorlage_gewaehlt(self.vorlagenliste.liste.currentRow())

    # -- Attribute --------------------------------------------------------

    def _attribute(self) -> list[dict[str, Any]]:
        return self.entwurf.setdefault("attributes", [])

    def _aktuelles_attribut(self) -> dict[str, Any] | None:
        zeile = self.attributliste.liste.currentRow()
        attribute = self._attribute()
        return attribute[zeile] if 0 <= zeile < len(attribute) else None

    def _attribut_neu(self) -> None:
        self._attribute().append({"name": "attribut", "visibility": "private"})
        self._anzeigen()
        self.attributliste.liste.setCurrentRow(len(self._attribute()) - 1)

    def _attribut_loeschen(self) -> None:
        zeile = self.attributliste.liste.currentRow()
        if 0 <= zeile < len(self._attribute()):
            self._attribute().pop(zeile)
            self._anzeigen()

    def _attribut_schieben(self, richtung: int) -> None:
        zeile = self.attributliste.liste.currentRow()
        ziel = zeile + richtung
        attribute = self._attribute()
        if 0 <= zeile < len(attribute) and 0 <= ziel < len(attribute):
            attribute[zeile], attribute[ziel] = attribute[ziel], attribute[zeile]
            self._anzeigen()
            self.attributliste.liste.setCurrentRow(ziel)

    def _attribut_gewaehlt(self, zeile: int) -> None:
        attribut = self._aktuelles_attribut()
        self.attributdaten.setEnabled(attribut is not None)
        if attribut is None:
            return
        self._laeuft = True
        try:
            self.attribut_name.setText(str(attribut.get("name", "")))
            self.attribut_typ.setText(str(attribut.get("type", "")))
            self.attribut_wert.setText(str(attribut.get("value", "")))
            self.attribut_kommentar.setPlainText(str(attribut.get("comment", "")))
            self.attribut_sichtbarkeit.setCurrentIndex(
                max(0, self.attribut_sichtbarkeit.findData(
                    attribut.get("visibility", "public")))
            )
            self.attribut_klassenbereich.setChecked(bool(attribut.get("class_scope")))
        finally:
            self._laeuft = False

    def _attribut_uebernehmen(self) -> None:
        if self._laeuft:
            return
        attribut = self._aktuelles_attribut()
        if attribut is None:
            return
        attribut["name"] = self.attribut_name.text()
        attribut["type"] = self.attribut_typ.text()
        attribut["value"] = self.attribut_wert.text()
        attribut["comment"] = self.attribut_kommentar.toPlainText()
        attribut["visibility"] = self.attribut_sichtbarkeit.currentData()
        attribut["class_scope"] = self.attribut_klassenbereich.isChecked()
        self._zeile_auffrischen(self.attributliste, attribut_zeile(attribut))

    # -- Operationen ------------------------------------------------------

    def _operationen(self) -> list[dict[str, Any]]:
        return self.entwurf.setdefault("operations", [])

    def _aktuelle_operation(self) -> dict[str, Any] | None:
        zeile = self.operationsliste.liste.currentRow()
        operationen = self._operationen()
        return operationen[zeile] if 0 <= zeile < len(operationen) else None

    def _operation_neu(self) -> None:
        self._operationen().append(
            {"name": "operation", "visibility": "public", "parameters": []}
        )
        self._anzeigen()
        self.operationsliste.liste.setCurrentRow(len(self._operationen()) - 1)

    def _operation_loeschen(self) -> None:
        zeile = self.operationsliste.liste.currentRow()
        if 0 <= zeile < len(self._operationen()):
            self._operationen().pop(zeile)
            self._anzeigen()

    def _operation_schieben(self, richtung: int) -> None:
        zeile = self.operationsliste.liste.currentRow()
        ziel = zeile + richtung
        operationen = self._operationen()
        if 0 <= zeile < len(operationen) and 0 <= ziel < len(operationen):
            operationen[zeile], operationen[ziel] = operationen[ziel], operationen[zeile]
            self._anzeigen()
            self.operationsliste.liste.setCurrentRow(ziel)

    def _operation_gewaehlt(self, zeile: int) -> None:
        operation = self._aktuelle_operation()
        self.operationsdaten.setEnabled(operation is not None)
        self.parameterliste.setEnabled(operation is not None)
        if operation is None:
            self.parameterliste.fuellen([], None)
            self.parameterdaten.setEnabled(False)
            return
        self._laeuft = True
        try:
            self.operation_name.setText(str(operation.get("name", "")))
            self.operation_typ.setText(str(operation.get("type", "")))
            self.operation_stereotyp.setText(str(operation.get("stereotype", "")))
            self.operation_kommentar.setPlainText(str(operation.get("comment", "")))
            self.operation_sichtbarkeit.setCurrentIndex(
                max(0, self.operation_sichtbarkeit.findData(
                    operation.get("visibility", "public")))
            )
            self.operation_vererbung.setCurrentIndex(
                max(0, self.operation_vererbung.findData(
                    operation.get("inheritance", "leaf")))
            )
            self.operation_klassenbereich.setChecked(bool(operation.get("class_scope")))
            self.operation_anfrage.setChecked(bool(operation.get("query")))
            self.parameterliste.fuellen(
                [str(p.get("name", "")) for p in operation.get("parameters") or []], None
            )
        finally:
            self._laeuft = False
        self._parameter_gewaehlt(self.parameterliste.liste.currentRow())

    def _operation_uebernehmen(self) -> None:
        if self._laeuft:
            return
        operation = self._aktuelle_operation()
        if operation is None:
            return
        operation["name"] = self.operation_name.text()
        operation["type"] = self.operation_typ.text()
        operation["stereotype"] = self.operation_stereotyp.text()
        operation["comment"] = self.operation_kommentar.toPlainText()
        operation["visibility"] = self.operation_sichtbarkeit.currentData()
        operation["inheritance"] = self.operation_vererbung.currentData()
        operation["class_scope"] = self.operation_klassenbereich.isChecked()
        operation["query"] = self.operation_anfrage.isChecked()
        self._zeile_auffrischen(self.operationsliste, operation_zeile(operation))

    # -- Parameter --------------------------------------------------------

    def _parameter(self) -> list[dict[str, Any]]:
        operation = self._aktuelle_operation()
        return operation.setdefault("parameters", []) if operation else []

    def _aktueller_parameter(self) -> dict[str, Any] | None:
        zeile = self.parameterliste.liste.currentRow()
        parameter = self._parameter()
        return parameter[zeile] if 0 <= zeile < len(parameter) else None

    def _parameter_neu(self) -> None:
        if self._aktuelle_operation() is None:
            return
        self._parameter().append({"name": "parameter"})
        self._operation_gewaehlt(self.operationsliste.liste.currentRow())
        self.parameterliste.liste.setCurrentRow(len(self._parameter()) - 1)
        self._operation_uebernehmen()

    def _parameter_loeschen(self) -> None:
        zeile = self.parameterliste.liste.currentRow()
        if 0 <= zeile < len(self._parameter()):
            self._parameter().pop(zeile)
            self._operation_gewaehlt(self.operationsliste.liste.currentRow())
            self._operation_uebernehmen()

    def _parameter_schieben(self, richtung: int) -> None:
        zeile = self.parameterliste.liste.currentRow()
        ziel = zeile + richtung
        parameter = self._parameter()
        if 0 <= zeile < len(parameter) and 0 <= ziel < len(parameter):
            parameter[zeile], parameter[ziel] = parameter[ziel], parameter[zeile]
            self._operation_gewaehlt(self.operationsliste.liste.currentRow())
            self.parameterliste.liste.setCurrentRow(ziel)
            self._operation_uebernehmen()

    def _parameter_gewaehlt(self, zeile: int) -> None:
        parameter = self._aktueller_parameter()
        self.parameterdaten.setEnabled(parameter is not None)
        if parameter is None:
            return
        self._laeuft = True
        try:
            self.parameter_name.setText(str(parameter.get("name", "")))
            self.parameter_typ.setText(str(parameter.get("type", "")))
            self.parameter_vorgabe.setText(str(parameter.get("default", "")))
            self.parameter_kommentar.setPlainText(str(parameter.get("comment", "")))
            self.parameter_richtung.setCurrentIndex(
                max(0, self.parameter_richtung.findData(
                    parameter.get("direction", "undefined")))
            )
        finally:
            self._laeuft = False

    def _parameter_uebernehmen(self) -> None:
        if self._laeuft:
            return
        parameter = self._aktueller_parameter()
        if parameter is None:
            return
        parameter["name"] = self.parameter_name.text()
        parameter["type"] = self.parameter_typ.text()
        parameter["default"] = self.parameter_vorgabe.text()
        parameter["comment"] = self.parameter_kommentar.toPlainText()
        parameter["direction"] = self.parameter_richtung.currentData()
        self._zeile_auffrischen(self.parameterliste, parameter["name"])
        operation = self._aktuelle_operation()
        if operation is not None:
            self._zeile_auffrischen(self.operationsliste, operation_zeile(operation))

    # -- Vorlagen ---------------------------------------------------------

    def _vorlagen(self) -> list[dict[str, Any]]:
        return self.entwurf.setdefault("template_parameters", [])

    def _aktuelle_vorlage(self) -> dict[str, Any] | None:
        zeile = self.vorlagenliste.liste.currentRow()
        vorlagen = self._vorlagen()
        return vorlagen[zeile] if 0 <= zeile < len(vorlagen) else None

    def _vorlage_schalter(self, an: bool) -> None:
        if self._laeuft:
            return
        self.entwurf["template"] = an

    def _vorlage_neu(self) -> None:
        self._vorlagen().append({"name": "T"})
        self._anzeigen()
        self.vorlagenliste.liste.setCurrentRow(len(self._vorlagen()) - 1)

    def _vorlage_loeschen(self) -> None:
        zeile = self.vorlagenliste.liste.currentRow()
        if 0 <= zeile < len(self._vorlagen()):
            self._vorlagen().pop(zeile)
            self._anzeigen()

    def _vorlage_schieben(self, richtung: int) -> None:
        zeile = self.vorlagenliste.liste.currentRow()
        ziel = zeile + richtung
        vorlagen = self._vorlagen()
        if 0 <= zeile < len(vorlagen) and 0 <= ziel < len(vorlagen):
            vorlagen[zeile], vorlagen[ziel] = vorlagen[ziel], vorlagen[zeile]
            self._anzeigen()
            self.vorlagenliste.liste.setCurrentRow(ziel)

    def _vorlage_gewaehlt(self, zeile: int) -> None:
        vorlage = self._aktuelle_vorlage()
        self.vorlagendaten.setEnabled(vorlage is not None)
        if vorlage is None:
            return
        self._laeuft = True
        try:
            self.vorlage_name.setText(str(vorlage.get("name", "")))
            self.vorlage_typ.setText(str(vorlage.get("type", "")))
        finally:
            self._laeuft = False

    def _vorlage_uebernehmen(self) -> None:
        if self._laeuft:
            return
        vorlage = self._aktuelle_vorlage()
        if vorlage is None:
            return
        vorlage["name"] = self.vorlage_name.text()
        vorlage["type"] = self.vorlage_typ.text()
        self._zeile_auffrischen(self.vorlagenliste, vorlage["name"])

    # -- Hilfen -----------------------------------------------------------

    def _zeile_auffrischen(self, liste: _Liste, text: str) -> None:
        """Die Listenzeile mitziehen, während getippt wird – sonst sähe
        man die Wirkung erst nach einem Wechsel."""
        eintrag = liste.liste.currentItem()
        if eintrag is not None:
            eintrag.setText(text)

    # -- Übernehmen -------------------------------------------------------

    def ergebnis(self) -> dict[str, Any]:
        """Die geänderten Werte – genau das, was als ein
        Undo-Kommando auf die Form angewandt wird."""
        e = dict(self.entwurf)
        e.update(self._kopfwerte())
        e["template"] = self.vorlageklasse.isChecked()

        # Leer heißt „Stilvorlage“. Bewusst als leerer Wert statt als
        # fehlender Schlüssel: die Änderung läuft über ein
        # `WerteKommando`, und das kann Schlüssel nur setzen, nicht
        # entfernen – ein entferntes `fill` käme beim Zurücknehmen nicht
        # wieder. `zeichnen.fuellfarbe()` fällt bei einem leeren Wert
        # ohnehin auf die Vorlage zurück.
        e["fill"] = self.fuellfarbe.text().strip()
        e["line"] = self.linienfarbe.text().strip()
        e["font_size"] = self.schriftgroesse.value()
        return e

    def anwenden(self) -> dict[str, Any]:
        """„Anwenden“: übernehmen, aber offen bleiben."""
        self.uebernommen = True
        werte = self.ergebnis()
        self.entwurf = copy.deepcopy(werte)
        self.angewendet(werte)
        return werte

    def angewendet(self, werte: dict[str, Any]) -> None:
        """Haken für den Aufrufer – die Zeichenfläche hängt hier ihr
        Undo-Kommando ein. Standardmäßig passiert nichts."""

    def _ok(self) -> None:
        self.anwenden()
        self.accept()
