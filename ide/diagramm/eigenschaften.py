"""Eigenschaften-Bereich rechts im Diagramm-Fenster (Abschnitt 13.2).

Zeigt für die ausgewählte Form Position/Größe, Füllung, Linie und
Schriftgröße, für eine ausgewählte Verbindung ihre Beschriftungen
(Multiplizitäten/Rollen). Jede Änderung läuft über den Kommando-Stapel
der Zeichenfläche, ist also genauso rückgängig machbar wie eine
Änderung mit der Maus.

Aufgebaut wie der Objektinspektor des Formular-Designers
(`ide/inspector/eigenschaften_tabelle.py`), aber eigenständig:
Diagrammformen sind schlichte `dict`s, keine `pcl`-Komponenten mit
`Prop`-Deskriptoren.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ide.diagramm.kommandos import WerteKommando
from ide.diagramm.stil import stil as stil_zu_namen
from ide.diagramm.uml_modell import formname
from ide.diagramm.zeichnen import fuellfarbe, randfarbe, schriftgroesse

_GEOMETRIE = (("x", "Links"), ("y", "Oben"), ("w", "Breite"), ("h", "Höhe"))


class FarbKnopf(QPushButton):
    """Knopf, der seine Farbe zeigt und beim Klick den Farbdialog
    öffnet. `farbe` bleibt `None`, solange die Stilvorlage gilt."""

    def __init__(self) -> None:
        super().__init__()
        self.farbe: str | None = None
        self.setFixedHeight(22)

    def farbe_zeigen(self, farbe: str, eigen: bool) -> None:
        self.farbe = farbe if eigen else None
        self.setStyleSheet(f"background-color: {farbe}; border: 1px solid #808080;")
        self.setText("" if eigen else "(Stilvorlage)")

    def farbe_waehlen(self) -> str | None:
        gewaehlt = QColorDialog.getColor(QColor(self.farbe or "#ffffff"), self)
        return gewaehlt.name() if gewaehlt.isValid() else None


class EigenschaftenPanel(QWidget):
    def __init__(self, canvas) -> None:
        super().__init__()
        self.canvas = canvas
        self._laeuft = False  # verhindert Rückkopplung beim Befüllen

        self.hinweis = QLabel("Nichts ausgewählt")
        self.hinweis.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hinweis.setWordWrap(True)

        self.formular = QWidget()
        self._layout = QFormLayout(self.formular)
        self._layout.setContentsMargins(6, 6, 6, 6)

        self.felder: dict[str, QWidget] = {}
        for name, beschriftung in _GEOMETRIE:
            feld = QSpinBox()
            feld.setRange(-9999, 9999)
            feld.valueChanged.connect(lambda wert, n=name: self._geometrie_setzen(n, wert))
            self.felder[name] = feld
            self._layout.addRow(beschriftung, feld)

        self.fuellung = FarbKnopf()
        self.fuellung.clicked.connect(lambda: self._farbe_setzen("fill", self.fuellung))
        self._layout.addRow("Füllung", self.fuellung)

        self.linie = FarbKnopf()
        self.linie.clicked.connect(lambda: self._farbe_setzen("line", self.linie))
        self._layout.addRow("Linie", self.linie)

        self.schrift = QDoubleSpinBox()
        self.schrift.setRange(6, 48)
        self.schrift.setSingleStep(1)
        self.schrift.setSuffix(" pt")
        self.schrift.valueChanged.connect(self._schrift_setzen)
        self._layout.addRow("Schrift", self.schrift)

        self.beschriftung_von = QLineEdit()
        self.beschriftung_von.editingFinished.connect(
            lambda: self._label_setzen("from", self.beschriftung_von)
        )
        self._layout.addRow("Ende Quelle", self.beschriftung_von)

        self.beschriftung_zu = QLineEdit()
        self.beschriftung_zu.editingFinished.connect(
            lambda: self._label_setzen("to", self.beschriftung_zu)
        )
        self._layout.addRow("Ende Ziel", self.beschriftung_zu)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.hinweis)
        layout.addWidget(self.formular)
        layout.addStretch(1)

        self.aktualisieren()

    # -- Anzeige --------------------------------------------------------

    @property
    def form(self) -> dict[str, Any] | None:
        return self.canvas.ausgewaehlte_form

    @property
    def verbindung(self) -> dict[str, Any] | None:
        return self.canvas.ausgewaehlte_verbindung

    def aktualisieren(self) -> None:
        """Übernimmt die aktuelle Auswahl der Zeichenfläche."""
        self._laeuft = True
        try:
            form, verbindung = self.form, self.verbindung
            self.formular.setVisible(form is not None or verbindung is not None)

            for name, _ in _GEOMETRIE:
                self._zeile_zeigen(self.felder[name], form is not None)
            for widget in (self.fuellung, self.linie, self.schrift):
                self._zeile_zeigen(widget, form is not None)
            for widget in (self.beschriftung_von, self.beschriftung_zu):
                self._zeile_zeigen(widget, verbindung is not None)

            if form is not None:
                self.hinweis.setText(self._formtitel(form))
                for name, _ in _GEOMETRIE:
                    self.felder[name].setValue(int(form[name]))
                stil = stil_zu_namen(self.canvas.diagramm.stil)
                self.fuellung.farbe_zeigen(fuellfarbe(form, stil), "fill" in form)
                self.linie.farbe_zeigen(randfarbe(form, stil), "line" in form)
                self.schrift.setValue(schriftgroesse(form))
            elif verbindung is not None:
                self.hinweis.setText(f"Verbindung: {verbindung['kind']}")
                labels = verbindung.get("labels") or {}
                self.beschriftung_von.setText(str(labels.get("from", "")))
                self.beschriftung_zu.setText(str(labels.get("to", "")))
            else:
                self.hinweis.setText("Nichts ausgewählt")
        finally:
            self._laeuft = False

    def _zeile_zeigen(self, feld: QWidget, sichtbar: bool) -> None:
        feld.setVisible(sichtbar)
        beschriftung = self._layout.labelForField(feld)
        if beschriftung is not None:
            beschriftung.setVisible(sichtbar)

    def _formtitel(self, form: dict[str, Any]) -> str:
        name = formname(form) or form["kind"]
        return f"Form: {name}"

    # -- Ändern ---------------------------------------------------------

    def _anwenden(self, ziel: dict[str, Any], werte: dict[str, Any]) -> None:
        if self._laeuft or ziel is None:
            return
        if all(ziel.get(name) == wert for name, wert in werte.items()):
            return
        self.canvas.kommandos.ausfuehren(WerteKommando(ziel, werte))
        self.canvas.geaendert.emit()
        self.canvas.update()
        self.aktualisieren()

    def _geometrie_setzen(self, name: str, wert: int) -> None:
        self._anwenden(self.form, {name: wert})

    def _schrift_setzen(self, wert: float) -> None:
        self._anwenden(self.form, {"font_size": wert})

    def _farbe_setzen(self, schluessel: str, knopf: FarbKnopf) -> None:
        if self.form is None:
            return
        farbe = knopf.farbe_waehlen()
        if farbe is not None:
            self._anwenden(self.form, {schluessel: farbe})

    def _label_setzen(self, schluessel: str, feld: QLineEdit) -> None:
        verbindung = self.verbindung
        if verbindung is None:
            return
        labels = dict(verbindung.get("labels") or {})
        if labels.get(schluessel, "") == feld.text():
            return
        labels[schluessel] = feld.text()
        self._anwenden(verbindung, {"labels": labels})

    # -- Stil übertragen -------------------------------------------------

    def stil_uebertragen(self, von: dict[str, Any], auf: dict[str, Any]) -> None:
        """„Format → Stil übertragen“ (Abschnitt 13.3): Füllung, Linie
        und Schriftgröße einer Form auf eine andere übernehmen."""
        werte = {
            schluessel: von[schluessel]
            for schluessel in ("fill", "line", "font_size")
            if schluessel in von
        }
        if werte:
            self._anwenden(auf, werte)
