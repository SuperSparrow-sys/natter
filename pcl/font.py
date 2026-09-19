"""Font: aufklappbare Schrift-Untereigenschaft jeder Komponente.

Entspricht `TFont` in Lazarus (`Font.Name`, `Font.Size`, `Font.Style =
[fsBold]`). Siehe README.md, Abschnitt 5.0. Wie `Shape.brush`
kein eigenständiges `Prop`, sondern eine Untereigenschaft an einem festen
Attributnamen (`font`); in der `.pfm` und im Objektinspektor erscheint
sie flach als `font_name`/`font_size`/`font_bold`/`font_italic`
(`pcl.properties.VERSCHACHTELTE_EIGENSCHAFTEN`).

**Warum QSS statt `QWidget.setFont()`:** das Theme aus `pcl.theme` setzt
`font-family`/`font-size` über eine `QWidget`-QSS-Regel auf dem Formular.
In Qt schlägt ein Stylesheet immer `setFont()` – ein `setFont()` auf der
Komponente bliebe deshalb wirkungslos. Genau dieser Fehler ist in der IDE
schon einmal real aufgetreten (Editor-Schriftart, siehe docs/PLAN.md) und
wurde dort ebenfalls über eine spezifischere QSS-Regel gelöst.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pcl.errors import NatterPropertyError
from pcl.properties import typ_beschreibung

if TYPE_CHECKING:
    from pcl.control import Control


class Font:
    """Schriftart einer Komponente, z. B. ``self.m_zettel.font.size = 12``.

    Standardwerte bedeuten „wie das Formular“: `name = ""` übernimmt die
    Schriftart des Themes, `size = 0` dessen Größe.
    """

    def __init__(self, besitzer: Control) -> None:
        self._besitzer = besitzer
        self._name = ""
        self._size = 0
        self._bold = False
        self._italic = False

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, wert: str) -> None:
        self._pruefen("name", wert, str)
        self._name = wert
        self._anwenden()

    @property
    def size(self) -> int:
        return self._size

    @size.setter
    def size(self, wert: int) -> None:
        self._pruefen("size", wert, int)
        self._size = wert
        self._anwenden()

    @property
    def bold(self) -> bool:
        return self._bold

    @bold.setter
    def bold(self, wert: bool) -> None:
        self._pruefen("bold", wert, bool)
        self._bold = wert
        self._anwenden()

    @property
    def italic(self) -> bool:
        return self._italic

    @italic.setter
    def italic(self, wert: bool) -> None:
        self._pruefen("italic", wert, bool)
        self._italic = wert
        self._anwenden()

    def _pruefen(self, name: str, wert: object, typ: type) -> None:
        passt = isinstance(wert, bool) if typ is bool else (
            isinstance(wert, typ) and not isinstance(wert, bool)
        )
        if not passt:
            raise NatterPropertyError(
                f"{type(self._besitzer).__name__}.font.{name} erwartet "
                f"{typ_beschreibung(typ)}, erhalten wurde {typ_beschreibung(type(wert))}."
            )

    def qss_teile(self) -> list[str]:
        """Die QSS-Anweisungen dieser Schrift – leer, solange nichts vom
        Standard abweicht, damit die Komponente die Theme-Schrift erbt."""
        teile = []
        if self._name:
            teile.append(f'font-family: "{self._name}";')
        if self._size:
            teile.append(f"font-size: {self._size}pt;")
        if self._bold:
            teile.append("font-weight: bold;")
        if self._italic:
            teile.append("font-style: italic;")
        return teile

    def _anwenden(self) -> None:
        self._besitzer._eigenes_qss_anwenden()
