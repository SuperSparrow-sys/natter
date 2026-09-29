"""Lädt SVG-Symbole aus `ide/assets/icons/` als `QIcon` – für
Werkzeugleiste, Fenster-Icon und Palette/Baum (Abschnitt 7.3, 7.9).
Symbolnamen entsprechen den Dateinamen ohne `.svg`, siehe `Aktion.symbol`
in `ide/actions/register.py`.

=====================================================================
Symbolraster (M11, Abschnitt 1 – verbindlich für jedes neue Symbol)
=====================================================================

Vorgabe des Nutzers: filigraner als bisher und etwas bunter. Ein Symbol
soll ein kleines Bild der Sache sein (gefüllte Fläche mit Kontur),
keine reine Strichzeichnung.

Fläche und Innenabstand

* `viewBox="0 0 24 24"`, keine `width`/`height` am `<svg>` – die Größe
  bestimmt immer der Aufrufer (Werkzeugleiste 18 px, Palette 22 px).
* Alles Sichtbare liegt zwischen 2 und 22, also in einer Zeichenfläche
  von 20 × 20 – einschließlich der halben Strichbreite. Der Rand von
  2 px verhindert, dass Qt beim Skalieren Kanten abschneidet.
* Ausgenommen sind die drei `tab_schliessen*.svg` (`tab_schliessen`,
  `tab_schliessen_hell`, `tab_schliessen_dunkel`): 16 × 16 statt
  24 × 24, siehe unten. Der Satz nannte lange nur die erste davon –
  inzwischen sind es drei.

Strichstärken (vier, mehr nicht – `tests/test_assets_symbole.py`
lässt keine andere durch)

* `1,0` Binnenlinie – Textzeilen, Gitternetz, Details *innerhalb*
  einer gefüllten Fläche.
* `1,2` Kontur – umschließt eine gefüllte Fläche. Die Fläche trägt
  das Bild, die Kontur muss es nicht auch noch tun; deshalb dünner als
  die früheren durchgehenden 1,6.
* `1,5` Strich – freistehende Linien und Bögen. Sie haben keine
  Füllung hinter sich und würden bei 16 px sonst verschwinden.
* `2,0` Marke – eine Linie, die für sich allein die Bedeutung trägt
  (das Häkchen der CheckBox). In der Sichtprüfung blieb davon bei 1,5
  nur ein blasser Schatten übrig: eine schräge Linie verliert beim
  Herunterrechnen die halbe Deckung, weil sie sich über zwei Pixelreihen
  verteilt.

Für Pfeilspitzen und Dreiecke gilt keine Strichstärke: sie werden
als Fläche gezeichnet, nie als Winkelstrich. Bei 16 px wurde aus dem
Winkelstrich sonst ein Fleck – gemessen am Aufklapppfeil der ComboBox
und an der Spitze von „Rückgängig“, die dadurch von „Wiederholen“ nicht
mehr zu unterscheiden war.

`stroke-linecap="round"` und `stroke-linejoin="round"` an allen freien
Strichen; das hält die Enden bei 16 px rund statt ausgefranst.

Eckenradius

* `2` an großen Flächen (Fenster, Knopf, Kasten),
* `1` bis `1,5` an kleinen Flächen (Rollbalkengriff, Zellen),
* `0` an bewusst eckigen Formen (Balken eines Diagramms, Etikett).

Gefüllt oder gestrichen

* Jedes Symbol hat einen tragenden Körper, gefüllt und in seiner
  Bedeutungsfarbe. Nur Zeiger/Pfeile/Schrift stehen ohne Füllung.
* Flächen ab etwa 6 px Kantenlänge bekommen eine Kontur: `tinte` bei
  hellen Flächen (`papier`, `grau`), sonst die zugehörige
  `*_tief`-Schattierung.
* Kleine Marken (Punkte, Balken, Häkchen) stehen ohne Kontur – bei
  16 px würde sie die Marke zulaufen lassen.
* Keine Verläufe, keine Schatten, kein `opacity`. Beides überlebt das
  Herunterrechnen auf 16 px nicht und macht das Umfärben unmöglich.

Farben

Nur die Werte aus `FARBEN` (siehe unten) dürfen in einer `.svg` stehen –
`tests/test_assets_symbole.py` prüft das. Jede Farbe hat einen Wert für
das helle und einen für das dunkle Theme; die Datei selbst enthält immer
den hellen Wert, damit sie in jedem Betrachter richtig aussieht, und
`symbol()` tauscht ihn im dunklen Theme aus (siehe unten).

=====================================================================
Warum nicht `currentColor`
=====================================================================

M11 schlug `currentColor` statt der fest eingetragenen Farbe vor. Das
funktioniert in Qt nicht – gemessen mit Qt 6.11.2, offscreen:

===========================================================  ===========
`fill="currentColor"`, geladen über `QIcon(pfad)`             schwarz
dito, nachdem die Palette auf Rot gesetzt wurde               schwarz
dito, gerendert mit rot vorbelegtem `QPainter`                schwarz
`<svg color="#ff0000">` + `fill="currentColor"`               rot
Hex-Wert im Quelltext ersetzt, dann gerendert                 rot
===========================================================  ===========

`currentColor` löst Qt also nur gegen ein `color`-Attribut innerhalb
derselben Datei auf, nie gegen Palette oder Painter. Die Farbe bliebe
damit genauso einbetoniert wie vorher, nur unter anderem Namen – und
mehrfarbige Symbole gingen gar nicht.

Der Weg, der wirklich wirkt, ist deshalb: den Quelltext der `.svg` beim
Laden umfärben (`_umgefaerbt`) und das Ergebnis über eine eigene
`QIconEngine` rendern. Die Engine hält das SVG als Vektor, das Symbol
bleibt damit bei jeder Größe scharf, ohne dass irgendwo eine umgefärbte
Datei auf die Platte geschrieben werden muss.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path

# Muss vor der ersten QIcon(...)-Erstellung aus einer .svg-Datei importiert
# werden, sonst bleibt das Icon leer (isNull()==True) - der SVG-Icon-Engine-
# Plugin (qsvgicon) wird sonst nicht registriert, obwohl er installiert ist.
from PySide6 import QtSvg  # noqa: F401
from PySide6.QtCore import QByteArray, QRect, QSize, Qt
from PySide6.QtGui import QIcon, QIconEngine, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_ICON_ORDNER = Path(__file__).resolve().parent / "icons"

#: Die Farbpalette der Symbole: Name -> (heller Wert, dunkler Wert).
#:
#: In der `.svg`-Datei steht immer der helle Wert. `symbol()` ersetzt
#: ihn im dunklen Theme durch den dunklen. Die Akzentfarben stammen aus
#: `design/tokens.json` (`accent`, `success`, `danger`, `chart`), damit
#: Symbole und Oberfläche dieselbe Handschrift haben.
FARBEN: dict[str, tuple[str, str]] = {
    # Umriss und tragende Linien. Im dunklen Theme fast weiß - das ist die
    # eine Farbe, die zwingend umschalten muss.
    "tinte": ("#37474f", "#dbe3e8"),
    # Zurücktretende Binnenzeichnung (Textzeilen, Gitter).
    "tinte_hell": ("#7b8f9a", "#94a4ad"),
    # Helle Füllfläche: Blatt, Eingabefeld, Fensterinneres. Bewusst *nicht*
    # reines Weiß, damit sie sich beim Umfärben von "signal" (Marke auf
    # kräftigem Grund, bleibt in beiden Themes weiß) unterscheiden lässt.
    "papier": ("#f7f9fa", "#2f383d"),
    "signal": ("#ffffff", "#ffffff"),
    # Akzent (= tokens.json color.*.accent): Bedienelemente, Auswahl.
    "blau": ("#0067c0", "#4cc2ff"),
    "blau_tief": ("#004c8c", "#1d7fb0"),
    # Zustimmung/Start (= color.*.success).
    "gruen": ("#1e8e3e", "#5ec46b"),
    "gruen_tief": ("#14682c", "#2f8f45"),
    # Ordner, Hinweis.
    "gelb": ("#f2b134", "#e9b64a"),
    "gelb_tief": ("#c98f1e", "#a9801f"),
    # Abbruch, Haltepunkt, Fehler (= color.*.danger).
    "rot": ("#c42b1c", "#ff6a5f"),
    # Struktur/Behälter (= color.*.chart[3]).
    "lila": ("#8764b8", "#b99bea"),
    # Neutrale Flächen ohne eigene Bedeutung.
    "grau": ("#90a4ae", "#61727b"),
    # Theme-neutral: gilt in hell wie dunkel. Nur für `tab_schliessen.svg`,
    # das `ide/shell/theme.py` als `image: url(...)` direkt ins QSS
    # einbindet - diese eine Datei liest Qt am Umfärben vorbei und muss
    # deshalb von sich aus in beiden Themes lesbar sein.
    "neutral": ("#8a8a8a", "#8a8a8a"),
}

#: Theme-Wert (Spaltenindex) je aufgelöstem Theme-Namen.
_SPALTE = {"light": 0, "dark": 1}

#: `#rrggbb` – alles andere (`none`, benannte Farben) bleibt unangetastet.
_HEX = re.compile(r"#[0-9a-fA-F]{6}")

#: Größen, die `QIcon.availableSizes()` meldet. Gerendert wird trotzdem
#: bei jeder angefragten Größe frisch aus dem Vektor.
_GROESSEN = (16, 18, 20, 22, 24, 32, 48, 64, 128, 256)


#: Heller Hex-Wert -> (hell, dunkel). Nachschlagerichtung des Umfärbens,
#: denn in der Datei steht immer der helle Wert.
_FARBEN_NACH_HELL: dict[str, tuple[str, str]] = {
    hell.lower(): (hell, dunkel) for hell, dunkel in FARBEN.values()
}


def theme_ermitteln(theme: str = "system") -> str:
    """Löst `theme` auf `light` oder `dark` auf.

    `light`/`dark` werden durchgereicht. Bei `system` entscheidet die
    Wahl des Nutzers unter „Ansicht → Design“, die das Hauptfenster in
    `QSettings("Natter", "Natter-IDE")` unter `design/thema` ablegt; erst
    wenn dort ebenfalls `system` steht, zählt das Farbschema des
    Betriebssystems (`pcl.theme.theme_aufloesen`).

    Ohne diesen Umweg hätte ein Schüler, der auf einem hell
    eingestellten Schulrechner in Natter „Dunkel“ wählt, eine dunkle
    Oberfläche mit Symbolen fürs helle Theme – also dunkle Umrisse auf
    dunklem Grund. Ein sauberer Weg über eine Benachrichtigung aus
    `ide/shell/` wäre denkbar, würde aber Dateien außerhalb von
    `ide/assets/` berühren (siehe Bericht zu M11, Abschnitt 1).
    """
    from pcl.theme import theme_aufloesen

    if theme in ("light", "dark"):
        return theme
    from PySide6.QtCore import QSettings

    einstellungen = QSettings(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, "Natter", "Natter-IDE"
    )
    gewaehlt = einstellungen.value("design/thema", "system")
    if gewaehlt in ("light", "dark"):
        return gewaehlt
    return theme_aufloesen("system")


def farbkarte(theme: str) -> dict[str, str]:
    """Liefert die Ersetzungstabelle heller Hex-Wert -> Wert für `theme`
    (`light`/`dark`/`system`). Im hellen Theme ist sie die Identität."""
    spalte = _SPALTE[theme_ermitteln(theme)]
    return {hell: werte[spalte] for hell, werte in _FARBEN_NACH_HELL.items()}


def _umgefaerbt(svg_text: str, karte: dict[str, str]) -> str:
    """Tauscht jeden Hex-Wert in einem Durchgang gegen den Wert aus
    `karte`. Ein Durchgang, damit keine Ersetzung das Ergebnis einer
    vorherigen noch einmal trifft."""
    return _HEX.sub(lambda treffer: karte.get(treffer.group(0).lower(), treffer.group(0)), svg_text)


class _SvgSymbolEngine(QIconEngine):
    """Rendert ein bereits umgefärbtes SVG bei jeder angefragten Größe
    frisch aus dem Vektor.

    Qt bietet keinen Weg, einem `QIcon` ein SVG aus dem Speicher
    mitzugeben – `QIcon(pfad)` will eine Datei. Eine Leiter fertiger
    `QPixmap` wäre die Alternative, sähe aber oberhalb der größten
    vorgehaltenen Stufe weich aus (nachgemessen: `QIcon` skaliert dann
    die 128er hoch). Diese Engine hält stattdessen den Vektor.
    """

    def __init__(self, daten: bytes) -> None:
        super().__init__()
        self._daten = bytes(daten)

    def paint(self, painter: QPainter, rect: QRect, mode, state) -> None:  # noqa: ARG002
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        QSvgRenderer(QByteArray(self._daten)).render(painter, rect)

    def pixmap(self, size: QSize, mode, state) -> QPixmap:
        bild = QPixmap(size)
        bild.fill(Qt.GlobalColor.transparent)
        maler = QPainter(bild)
        self.paint(maler, QRect(0, 0, size.width(), size.height()), mode, state)
        maler.end()
        return bild

    def actualSize(self, size: QSize, mode, state) -> QSize:  # noqa: ARG002
        return size

    def availableSizes(self, mode=None, state=None) -> list[QSize]:  # noqa: ARG002
        return [QSize(kante, kante) for kante in _GROESSEN]

    def clone(self) -> QIconEngine:
        return _SvgSymbolEngine(self._daten)


@cache
def _symbol_fuer_theme(name: str, theme: str) -> QIcon:
    """Eigentliche Arbeit von `symbol()`, zusätzlich nach dem aufgelösten
    Theme zwischengespeichert – ein Wechsel Hell/Dunkel liefert damit ein
    neu eingefärbtes Symbol und nicht das alte aus dem Cache."""
    svg_pfad = _ICON_ORDNER / f"{name}.svg"
    if svg_pfad.exists():
        text = _umgefaerbt(svg_pfad.read_text(encoding="utf-8"), farbkarte(theme))
        return QIcon(_SvgSymbolEngine(text.encode("utf-8")))
    for endung in (".ico", ".png"):
        pfad = _ICON_ORDNER / f"{name}{endung}"
        if pfad.exists():
            return QIcon(str(pfad))
    return QIcon()


def symbol(name: str, theme: str = "system") -> QIcon:
    """Liefert das Symbol `name` (Dateiname ohne Endung) – zuerst als
 `.svg`, dann als `.ico` (mehrere von Hand für kleine Größen
 nachgeschärfte Stufen, z. B. `app.ico` - eine einzelne PNG-Quelle
 roh herunterskaliert verwäscht bei 16-32px die dünne schwarze
 Kontur zu einem Farbklumpen, gemeldet anhand
 eines Zoom-Screenshots), zuletzt als `.png` gesucht. Unbekannter
 Name liefert ein leeres `QIcon` statt eines Fehlers – Aufrufer
 müssen kein Symbol angeben (`Aktion.symbol` ist standardmäßig
 leer).

 `.svg`-Symbole werden dabei nach `FARBEN` umgefärbt: `theme` ist
 `light`, `dark` oder `system` (Voreinstellung – dann entscheidet die
 Design-Wahl des Nutzers, siehe `theme_ermitteln`). `.ico`/`.png` sind
 Rasterbilder und bleiben wie sie sind.
 """
    if not name:
        return QIcon()
    return _symbol_fuer_theme(name, theme_ermitteln(theme))
