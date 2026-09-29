"""Objektinspektor: Komponentenbaum + Reiter Eigenschaften/Ereignisse.

Siehe README.md, Abschnitt 7.6.
"""

from __future__ import annotations

from functools import partial
from typing import Any

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ide.inspector.eigenschaften_tabelle import EigenschaftenTabelle
from ide.inspector.ereignisse_tabelle import EreignisseTabelle
from ide.inspector.komponentenbaum import KOMPONENTE_ROLLE, Komponentenbaum
from ide.inspector.menue_editor import menue_methode_anlegen
from pcl.form import Form


class Objektinspektor(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._formular: Form | None = None
        self._canvas: Any = None

        self.baum = Komponentenbaum()
        self.baum.currentItemChanged.connect(self._bei_auswahl)

        self.eigenschaften_tabelle = EigenschaftenTabelle()
        self.ereignisse_tabelle = EreignisseTabelle()

        # Umschalter über der Tabelle: alphabetisch oder nach
        # Kategorie. Zwei Knöpfe statt eines Häkchens, damit beide
        # Möglichkeiten zu sehen sind und nicht nur eine.
        self.alphabetisch_knopf = QToolButton()
        self.alphabetisch_knopf.setText("A–Z")
        self.alphabetisch_knopf.setToolTip("Eigenschaften alphabetisch")
        self.kategorie_knopf = QToolButton()
        self.kategorie_knopf.setText("Kategorie")
        self.kategorie_knopf.setToolTip("Eigenschaften nach Kategorie gruppiert")
        self._sortierung = QButtonGroup(self)
        self._sortierung.setExclusive(True)
        for knopf in (self.alphabetisch_knopf, self.kategorie_knopf):
            knopf.setCheckable(True)
            knopf.setAutoRaise(True)
            self._sortierung.addButton(knopf)
        nach_kategorie = self._einstellungen().value(
            "inspektor/nach_kategorie", False, type=bool
        )
        (self.kategorie_knopf if nach_kategorie else self.alphabetisch_knopf).setChecked(True)
        self.eigenschaften_tabelle.ansicht_setzen(nach_kategorie)
        self.kategorie_knopf.toggled.connect(self._sortierung_umschalten)

        leiste = QHBoxLayout()
        leiste.setContentsMargins(0, 0, 0, 0)
        leiste.addWidget(self.alphabetisch_knopf)
        leiste.addWidget(self.kategorie_knopf)
        leiste.addStretch(1)
        eigenschaften_seite = QWidget()
        seite = QVBoxLayout(eigenschaften_seite)
        seite.setContentsMargins(0, 0, 0, 0)
        seite.setSpacing(2)
        seite.addLayout(leiste)
        seite.addWidget(self.eigenschaften_tabelle, 1)

        self.reiter = QTabWidget()
        self.reiter.addTab(eigenschaften_seite, "Eigenschaften")
        self.reiter.addTab(self.ereignisse_tabelle, "Ereignisse")
        self._knapp = False
        self._kopf_hoechstens = (
            self.eigenschaften_tabelle.horizontalHeader().maximumHeight()
        )

        # Warum eine Eingabe abgelehnt wurde. Die Tabelle setzte die
        # Zelle bei einem ungültigen Wert schon immer zurück, sagte
        # aber nirgends, weshalb - die Eingabe verschwand einfach.
        self.meldung = QLabel()
        self.meldung.setWordWrap(True)
        self.meldung.setObjectName("inspektor_meldung")
        self.meldung.hide()
        self.eigenschaften_tabelle.fehlertext_geaendert.connect(
            self._meldung_zeigen
        )

        self._layout = QVBoxLayout(self)
        self._layout.addWidget(self.baum, 1)
        self._layout.addWidget(self.reiter, 2)
        self._layout.addWidget(self.meldung)
        self._raender = self._layout.contentsMargins()

    @property
    def knapp(self) -> bool:
        return self._knapp

    def knapp_setzen(self, knapp: bool) -> None:
        """Bei wenig Fensterhöhe geht mehr Platz an die Eigenschaften
        (Punkt 437).

        Der Baum behielt sonst ein Drittel der Höhe, und bei 1280 × 800
        mit 150 % blieb unter „Eigenschaft | Wert“ keine Zeile übrig.
        Knapp heißt: schmale Ränder, der Baum bekommt ein Viertel statt
        eines Drittels, und Zeilen und Spaltenköpfe der Tabellen werden
        so hoch wie die Schrift mit etwas Luft statt so hoch wie ein
        Auswahlfeld (30 Pixel).

        Die Knöpfe „A–Z“ und „Kategorie“ bleiben über der Tabelle. In
        der Reiterleiste daneben fehlten bei 278 Pixel Breite rund 40,
        und „Ereignisse“ wäre hinter Pfeilen verschwunden."""
        if knapp == self._knapp:
            return
        self._knapp = knapp
        if knapp:
            self._layout.setContentsMargins(2, 2, 2, 2)
            self._layout.setStretch(1, 3)
        else:
            self._layout.setContentsMargins(self._raender)
            self._layout.setStretch(1, 2)
        hoehe = self.fontMetrics().height() + 5
        for tabelle in (self.eigenschaften_tabelle, self.ereignisse_tabelle):
            kopf = tabelle.horizontalHeader()
            if knapp:
                tabelle.verticalHeader().setDefaultSectionSize(hoehe)
                kopf.setFixedHeight(hoehe + 2)
            else:
                tabelle.verticalHeader().resetDefaultSectionSize()
                kopf.setMinimumHeight(0)
                kopf.setMaximumHeight(self._kopf_hoechstens)

    @staticmethod
    def _einstellungen() -> QSettings:
        """Dieselbe Datei wie die übrigen Einstellungen der IDE
        (`ide/shell/hauptfenster.py`)."""
        return QSettings(
            QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Natter", "Natter-IDE"
        )

    def _sortierung_umschalten(self, nach_kategorie: bool) -> None:
        self.eigenschaften_tabelle.ansicht_setzen(nach_kategorie)
        self._einstellungen().setValue("inspektor/nach_kategorie", nach_kategorie)

    def _meldung_zeigen(self, text: str) -> None:
        self.meldung.setText(text)
        self.meldung.setVisible(bool(text))

    @property
    def formular(self) -> Form | None:
        return self._formular

    def formular_anzeigen(self, formular: Form, canvas: Any = None) -> None:
        """`canvas` (der zugehörige `DesignerCanvas`, Abschnitt 7.7) wird
        nur für die Zeile „name“ im Eigenschaften-Reiter gebraucht –
        Umbenennen läuft über `canvas.komponente_umbenennen()` (Undo,
        `.pfm`-Aktualisierung). Ohne `canvas` bleibt die Zeile weg."""
        self._formular = formular
        self._canvas = canvas
        self.baum.formular_anzeigen(formular)
        if self.baum.topLevelItemCount() > 0:
            self.baum.setCurrentItem(self.baum.topLevelItem(0))

    def leeren(self) -> None:
        """Zeigt kein Formular mehr, etwa nach „Projekt schließen“
        (Punkt 306)."""
        self._formular = None
        self._canvas = None
        self.baum.clear()
        for tabelle in (self.eigenschaften_tabelle, self.ereignisse_tabelle):
            tabelle._komponente = None
            tabelle.clearSpans()
            tabelle.setRowCount(0)
        self._meldung_zeigen("")

    def _bei_auswahl(self, aktuell, vorherig) -> None:
        if aktuell is None:
            return
        komponente = aktuell.data(0, KOMPONENTE_ROLLE)
        self._eigenschaften_anzeigen(komponente)

    def _eigenschaften_anzeigen(self, komponente: Any) -> None:
        name = self._canvas.name_von(komponente) if self._canvas is not None else None
        name_setzen = (
            (lambda neuer_name: self._canvas.komponente_umbenennen(komponente, neuer_name))
            if self._canvas is not None
            else None
        )
        bei_aenderung = self._canvas.eigenschaft_uebernehmen if self._canvas is not None else None
        self.eigenschaften_tabelle.komponente_anzeigen(
            komponente,
            name=name,
            name_setzen=name_setzen,
            bei_aenderung=bei_aenderung,
            # An den Designer gebunden und nicht an den Inspektor:
            # hielte die Tabelle eine Methode des Inspektors, hielten
            # beide einander fest.
            menue_methode_anlegen=(
                partial(menue_methode_anlegen, self._canvas)
                if self._canvas is not None
                else None
            ),
        )
        # Dieselbe Meldung wie bei den Eigenschaften: eine hier gewählte
        # Verknüpfung muss in die `.pfm` und den erzeugten Code, sonst
        # tut der Knopf im gestarteten Programm nichts (M12).
        # `methode_anlegen`: ein Doppelklick auf eine Zeile im Reiter
        # „Ereignisse" schreibt die Methode in die Unit. Die Tabelle
        # kennt die Datei nicht - der Designer schon.
        anlegen = (
            self._canvas.ereignis_handler_erzeugen if self._canvas is not None else None
        )
        self.ereignisse_tabelle.anzeigen(
            komponente, self._formular, bei_aenderung, methode_anlegen=anlegen
        )
