"""Komponentenpalette mit Reitern Standard/Zusätzlich.

Siehe README.md, Abschnitt 7.3. Nur die bisher in `pcl`
umgesetzten Komponenten; `Allgemein`, `Dialoge`, `Datensteuerung`,
`Datenzugriff`, `System` folgen, sobald es dort etwas zu platzieren
gibt (Abschnitt 5.2). Ein eigener Reiter `Diagramm` lohnt sich mit
einer einzigen Komponente noch nicht – `Chart` steht deshalb unter
„Zusätzlich“.

Optik wie in Lazarus: ein einzeiliger, horizontal scrollbarer Streifen
aus reinen Symbol-Kacheln je Reiter (kein Fließtext unter dem Symbol),
der Komponentenname erscheint als Tooltip beim Überfahren mit der Maus.

**Die Reiter stehen in `REITER`, und zwar nur dort** (M15). Vorher
standen sie an drei Stellen: hier als zwei Konstanten, im
`__init__` als zwei Zuweisungen, und im Hauptfenster als vier
`connect`-Aufrufe auf genau diese beiden Listen. Ein dritter Reiter
wäre dadurch stumm geblieben – die Kacheln wären zu sehen gewesen,
ließen sich aber nicht aufs Formular legen. Das war der Grund, den
Zeitgeber und `TrackBar`/`ProgressBar` in „Zusätzlich“ zu zwängen,
obwohl sie in Lazarus eigene Reiter haben. Wer jetzt einen Reiter
ergänzt, trägt ihn in `REITER` ein und ist fertig: das Hauptfenster
verbindet `palette.listen`, und die Prüfungen laufen über
`ALLE_KOMPONENTEN`.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QTabWidget

from ide.assets import symbol
from pcl.components.additional import (
    FloatSpinEdit,
    Image,
    ProgressBar,
    Shape,
    SpinEdit,
    StringGrid,
    TrackBar,
)
from pcl.components.chart import Chart
from pcl.components.menus import MainMenu, PopupMenu
from pcl.components.standard import (
    Button,
    CheckBox,
    ComboBox,
    Edit,
    GroupBox,
    Label,
    ListBox,
    Memo,
    Panel,
    RadioButton,
    RadioGroup,
    ScrollBar,
)
from pcl.components.system import Timer

TYP_ROLLE = Qt.ItemDataRole.UserRole
# Nutzer-Feedback (September 2026): insgesamt kompakter, näher an
# Lazarus' eigener, schmaler Symbolleiste (~24px Symbole).
_SYMBOL_GROESSE = QSize(22, 22)
_KACHEL_GROESSE = QSize(32, 32)

STANDARD_KOMPONENTEN = (
    Button,
    Label,
    Edit,
    Memo,
    CheckBox,
    RadioButton,
    ListBox,
    ComboBox,
    ScrollBar,
    # Die drei Behälter stehen wie in Lazarus im Reiter „Standard“ und
    # dort am Ende - sie kommen im Unterricht später dran als Knopf und
    # Textfeld, und die Reihenfolge der bisherigen Kacheln soll sich
    # nicht verschieben.
    GroupBox,
    Panel,
    RadioGroup,
    # Die beiden Menüs stehen in Lazarus ebenfalls im Reiter
    # „Standard" und dort ganz am Ende. Sie zeigen auf dem Formular
    # nur ihr Symbol; die Leiste erscheint erst im laufenden Programm
    # (M15, Schritt 1).
    MainMenu,
    PopupMenu,
)

ZUSAETZLICH_KOMPONENTEN = (
    StringGrid,
    Image,
    Shape,
    # „Zusätzlich“ statt „Standard“: ein Diagramm ist kein Grundbaustein
    # wie Knopf oder Textfeld (M10, Punkt 1).
    Chart,
    # `TrackBar` und `ProgressBar` gehören in Lazarus in den Reiter
    # „Common Controls“. Sie bleiben vorerst hier: ein eigener Reiter
    # für zwei Kacheln lohnt sich nicht. Möglich wäre er seit M15 -
    # dort ist die Verdrahtung auf alle Reiter umgestellt worden.
    SpinEdit,
    FloatSpinEdit,
    TrackBar,
    ProgressBar,
    # Ein Zeitgeber ist die einzige Komponente hier, die nichts
    # anzeigt - auf dem Formular steht nur sein Symbol, das im
    # laufenden Programm verschwindet (Nutzer-Hinweis September 2026:
    # „der Timer muss als Komponente auch mit rein, der ist wichtig").
    # In Lazarus hat er einen eigenen Reiter „System"; hier steht er
    # bei den übrigen, solange er dort allein stünde.
    Timer,
)


#: Die Reiter der Palette, in der Reihenfolge, in der sie erscheinen.
#: Einzige Stelle, an der ein Reiter steht – siehe Modulkopf.
REITER: tuple[tuple[str, tuple[type, ...]], ...] = (
    ("Standard", STANDARD_KOMPONENTEN),
    ("Zusätzlich", ZUSAETZLICH_KOMPONENTEN),
)

#: Jede Komponente, die sich auf ein Formular legen lässt. Prüfungen,
#: die „alle Komponenten“ meinen (Eigenschaften-Rundlauf, Tooltips,
#: Symbole), gehen hierüber und erfassen damit auch einen später
#: hinzugekommenen Reiter.
ALLE_KOMPONENTEN: tuple[type, ...] = tuple(
    typ for _, komponenten in REITER for typ in komponenten
)

def kurzbeschreibung(typ: type) -> str:
    """Der Text, der beim Überfahren einer Kachel erscheint: Name und
    erster Satz aus dem Docstring der Komponente.

    Bis dahin stand dort nur „Button“ – also genau das, was man auf dem
    Symbol ohnehin vermutet. Wer „ScrollBar“ von „TrackBar“ nicht
    unterscheiden kann, war damit keinen Schritt weiter (M11,
    Abschnitt 4).

    Der Satz wird aus dem Docstring **geholt** statt hier noch einmal
    aufgeschrieben – eine zweite Beschreibung wäre nach der ersten
    Änderung an der Komponente falsch. Der Hinweis auf das zugrunde
    liegende Qt-Widget fällt weg: beim Bauen eines Formulars hilft er
    niemandem.
    """
    text = " ".join((typ.__doc__ or "").split()).replace("`", "")
    text = text.split("Qt-Basis")[0].strip()
    satz = text.split(". ")[0].strip().rstrip(".")
    return f"{typ.__name__} – {satz}" if satz else typ.__name__


class Komponentenpalette(QTabWidget):
    def __init__(self) -> None:
        super().__init__()
        #: Alle Kachel-Listen in der Reihenfolge der Reiter. Das
        #: Hauptfenster verbindet seine Klick-Signale hierüber, damit
        #: ein neuer Reiter nicht stumm bleibt.
        self.listen: tuple[QListWidget, ...] = tuple(
            self._liste_erzeugen(komponenten) for _, komponenten in REITER
        )
        for (beschriftung, _), liste in zip(REITER, self.listen, strict=True):
            self.addTab(liste, beschriftung)
        # Kompakter, einzeiliger Streifen wie in Lazarus statt einer
        # beliebig hoch wachsenden Liste.
        self.setMaximumHeight(_KACHEL_GROESSE.height() + 34)

    @property
    def standard_liste(self) -> QListWidget:
        """Der Reiter „Standard“. Bleibt als eigener Name erhalten,
        weil ihn Tests und die Tastaturbedienung ansprechen."""
        return self.liste_zu("Standard")

    @property
    def zusaetzlich_liste(self) -> QListWidget:
        """Der Reiter „Zusätzlich“, siehe `standard_liste`."""
        return self.liste_zu("Zusätzlich")

    def liste_zu(self, beschriftung: str) -> QListWidget:
        """Die Kachel-Liste des Reiters mit dieser Beschriftung."""
        for (name, _), liste in zip(REITER, self.listen, strict=True):
            if name == beschriftung:
                return liste
        raise KeyError(f"Kein Palettenreiter {beschriftung!r}.")

    def _liste_erzeugen(self, komponenten: tuple[type, ...]) -> QListWidget:
        liste = QListWidget()
        liste.setViewMode(QListWidget.ViewMode.IconMode)
        liste.setFlow(QListWidget.Flow.LeftToRight)
        liste.setWrapping(False)
        liste.setResizeMode(QListWidget.ResizeMode.Fixed)
        liste.setMovement(QListWidget.Movement.Static)
        liste.setIconSize(_SYMBOL_GROESSE)
        liste.setGridSize(_KACHEL_GROESSE)
        liste.setUniformItemSizes(True)
        liste.setSpacing(1)
        liste.setFixedHeight(_KACHEL_GROESSE.height() + 6)
        liste.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        liste.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        for typ in komponenten:
            eintrag = QListWidgetItem(symbol(f"komponente_{typ.__name__.lower()}"), "")
            eintrag.setData(TYP_ROLLE, typ)
            eintrag.setToolTip(kurzbeschreibung(typ))
            liste.addItem(eintrag)
        return liste

    def symbole_erneuern(self, theme: str = "system") -> None:
        """Lädt die Palettensymbole im angegebenen Theme neu – nötig nach
        „Ansicht → Design", weil ein `QIcon` sich seine Farben merkt."""
        for seite in range(self.count()):
            liste = self.widget(seite)
            if not isinstance(liste, QListWidget):
                continue
            for zeile in range(liste.count()):
                eintrag = liste.item(zeile)
                typ = eintrag.data(TYP_ROLLE)
                if typ is not None:
                    eintrag.setIcon(
                        symbol(f"komponente_{typ.__name__.lower()}", theme)
                    )

    def ausgewaehlter_typ(self) -> type | None:
        """Der in der aktiven Palettenseite ausgewählte Komponententyp,
        oder `None`, wenn nichts ausgewählt ist."""
        liste = self.currentWidget()
        if not isinstance(liste, QListWidget):
            return None
        eintrag = liste.currentItem()
        return eintrag.data(TYP_ROLLE) if eintrag is not None else None
