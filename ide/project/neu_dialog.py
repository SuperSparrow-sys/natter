"""„Neues Projekt …“-Dialog (Abschnitt 7.2, 7.5): Vorlage, Name und
Zielordner abfragen, dann `ide.project.neu.projekt_erzeugen` aufrufen.

Bisher gab es zwar die reine Logik (`projekt_erzeugen`, seit M2), aber
keine Möglichkeit, ein neues Projekt tatsächlich aus der laufenden IDE
heraus anzulegen (Gewünscht: „ist da alles?“ beim
Blick auf das Projekt-Menü) – dieser Dialog schließt die Lücke.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ide.pfade import dialog_startordner, natter_ordner
from ide.project.neu import VORLAGEN, name_pruefen

_VORLAGEN_ANZEIGE = {
    "gui": "GUI-Anwendung",
    "console": "Konsolenanwendung",
}


def _vorhanden_hinweis(projektordner: Path, name: str) -> str | None:
    """Der Hinweis, wenn es `projektordner` schon gibt und er nicht
    leer ist, sonst `None`.

    `projekt_erzeugen` legt nur in einem leeren oder neuen Ordner an.
    Bis 0.4.2 stellte es das erst fest, nachdem der Dialog zu war; die
    Meldung stand dann in der Statusleiste, und Vorlage und Name
    mussten noch einmal eingegeben werden (Punkt 432). Aufgabennamen
    wie „Aufgabe1“ wiederholen sich im Unterricht oft."""
    try:
        if not projektordner.exists():
            return None
        belegt = not projektordner.is_dir() or any(projektordner.iterdir())
    except OSError:
        # Was sich nicht lesen lässt, meldet `projekt_erzeugen` mit
        # seinem eigenen Grund.
        return None
    if not belegt:
        return None
    if projektordner.is_dir() and any(projektordner.glob("*.natter")):
        return (
            f"Ein Projekt „{name}“ gibt es in diesem Ordner schon. "
            "Einen anderen Namen wählen oder das vorhandene über "
            "„Projekt → Projekt öffnen …“ laden."
        )
    return (
        f"In diesem Ordner gibt es schon etwas mit dem Namen „{name}“. "
        "Einen anderen Namen wählen."
    )


class NeuesProjektDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Neues Projekt")
        self.setMinimumWidth(420)

        self.vorlage_auswahl = QComboBox()
        for vorlage in VORLAGEN:
            self.vorlage_auswahl.addItem(_VORLAGEN_ANZEIGE.get(vorlage, vorlage), vorlage)

        self.name_eingabe = QLineEdit()
        self.name_eingabe.setPlaceholderText("z. B. Ampel")

        self.ordner_eingabe = QLineEdit()
        self.ordner_eingabe.setPlaceholderText("Übergeordneter Ordner")
        # Mit Vorgabe statt leer: sonst muss sich jede Schülerin beim
        # ersten Projekt einen Ordner suchen, und die Projekte einer
        # Klasse liegen danach an zehn verschiedenen Stellen. Dorthin
        # legt Natter auch die Arbeitskopien der Beispiele.
        self.ordner_eingabe.setText(str(natter_ordner()))
        self.ordner_knopf = QPushButton("Durchsuchen …")
        self.ordner_knopf.clicked.connect(self._ordner_waehlen)
        ordner_zeile = QHBoxLayout()
        ordner_zeile.addWidget(self.ordner_eingabe)
        ordner_zeile.addWidget(self.ordner_knopf)
        ordner_widget = QWidget()
        ordner_widget.setLayout(ordner_zeile)

        formular = QFormLayout()
        formular.addRow("Vorlage:", self.vorlage_auswahl)
        formular.addRow("Name:", self.name_eingabe)
        formular.addRow("Ordner:", ordner_widget)

        # Hinweis im Dialog statt eines weiteren Meldungsfensters: der
        # Name lässt sich gleich darüber korrigieren.
        self.hinweis = QLabel()
        self.hinweis.setWordWrap(True)
        self.hinweis.setStyleSheet("QLabel { color: #c0392b; }")
        self.hinweis.hide()

        self.knopfleiste = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.knopfleiste.accepted.connect(self.accept)
        self.knopfleiste.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(formular)
        layout.addWidget(self.hinweis)
        layout.addWidget(self.knopfleiste)

    def accept(self) -> None:
        """Schließt den Dialog nur mit einem Namen, aus dem sich ein
        Ordner anlegen lässt, und mit einem Ordner.

        Ein leeres Feld bekommt denselben Hinweis im Dialog wie ein
        ungültiger Name. Bis 0.3.x schloss sich der Dialog, und die
        Meldung stand danach nur noch in der Statusleiste. Ebenso ein
        Name, unter dem es im Ordner schon etwas gibt."""
        name = self.name_eingabe.text().strip()
        ordner = self.ordner_eingabe.text().strip()
        if not name:
            self._hinweis_zeigen(
                "Das Projekt braucht einen Namen.",
                self.name_eingabe,
            )
            return
        hinweis = name_pruefen(name)
        if hinweis is not None:
            self._hinweis_zeigen(hinweis, self.name_eingabe)
            return
        if not ordner:
            self._hinweis_zeigen(
                "Das Projekt braucht einen Ordner, in dem es "
                "angelegt wird.",
                self.ordner_eingabe,
            )
            return
        hinweis = _vorhanden_hinweis(Path(ordner) / name, name)
        if hinweis is not None:
            self._hinweis_zeigen(hinweis, self.name_eingabe)
            return
        super().accept()

    def _hinweis_zeigen(self, text: str, feld: QLineEdit) -> None:
        self.hinweis.setText(text)
        self.hinweis.show()
        feld.setFocus()
        # Markiert, damit der nächste Tastendruck den Inhalt ersetzt.
        feld.selectAll()

    def _ordner_waehlen(self) -> None:
        ordner = QFileDialog.getExistingDirectory(
            self,
            "Übergeordneter Ordner",
            str(dialog_startordner(self.ordner_eingabe.text().strip())),
        )
        if ordner:
            self.ordner_eingabe.setText(ordner)

    def werte(self) -> tuple[str, Path, str] | None:
        """`(vorlage, projektordner, name)`, oder `None`, wenn Name oder
        Ordner fehlen. `projektordner` ist `ordner/name` – der eigentliche,
        neu anzulegende Projektordner (siehe `projekt_erzeugen()`)."""
        name = self.name_eingabe.text().strip()
        ordner = self.ordner_eingabe.text().strip()
        if not name or not ordner:
            return None
        vorlage = self.vorlage_auswahl.currentData()
        return vorlage, Path(ordner) / name, name
