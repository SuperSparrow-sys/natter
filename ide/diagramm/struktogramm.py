"""Layout und Zeichnen von Struktogrammen nach Nassi-Shneiderman
(Abschnitt 13.5, M9 Schritt 9).

Ein Struktogramm hat **keine** frei platzierten Formen mit Koordinaten,
sondern einen Blockbaum (`root` in der `.pdiag`, siehe
`schemas/pdiag.schema.json`). Die Geometrie wird deshalb bei jedem
Zeichnen aus dem Baum gerechnet, statt gespeichert zu werden – dadurch
kann der Rahmen gar nicht erst aufbrechen, egal wie tief verschachtelt
wird, und das Verschieben eines Blocks ist eine reine Baumoperation.

Diese Datei kennt nur Geometrie und Malerei. Das Verändern des Baums
steht in `ide/diagramm/bloecke.py`, die Bedienung in
`ide/diagramm/struktogramm_canvas.py` – dieselbe Dreiteilung wie beim
Klassendiagramm (`zeichnen.py` / `kommandos.py` / `canvas.py`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QFontMetricsF, QPainter, QPen

from ide.diagramm.stil import Stil

LINIENBREITE = 1.5
INNENABSTAND = 6
#: Einrückung des Schleifenkörpers – der schmale Streifen links, an dem
#: man eine Schleife auf einen Blick erkennt.
EINRUECKUNG = 20
#: Mindesthöhe eines einzelnen Blocks, auch wenn sein Text leer ist.
MINDESTHOEHE = 28
#: Startbreite eines neuen Struktogramms.
STANDARDBREITE = 560
#: Höhe der Kopfzeile mit dem Namen. Nassi und Shneiderman schreiben den
#: Namen des Algorithmus über den Block – ohne ihn ist auf einem
#: ausgedruckten Blatt nicht zu erkennen, zu welcher Methode das
#: Struktogramm gehört.
KOPFHOEHE = 30

_SCHRIFT = "Segoe UI"

#: Blocktypen, die selbst wieder Blöcke enthalten können.
BEHAELTER = (
    "sequence",
    "branch",
    "multi_branch",
    "count_loop",
    "head_loop",
    "foot_loop",
    "forever_loop",
    "parallel",
    "try",
)

#: Blocktypen mit Schleifenkopf oben – die Endlosschleife unterscheidet
#: sich nur dadurch, dass in ihrem Kopf keine Bedingung steht.
KOPFSCHLEIFEN = ("count_loop", "head_loop", "forever_loop")

#: Die drei Abschnitte eines Try-Blocks: Datenschlüssel und Aufschrift
#: des Bandes, das darüber steht.
TRY_ABSCHNITTE: tuple[tuple[str, str], ...] = (
    ("children", "Versuch"),
    ("catch", "Behandlung"),
    ("finally", "Abschluss"),
)

BLOCK_BESCHRIFTUNGEN = {
    "statement": "Anweisung",
    "branch": "Verzweigung",
    "multi_branch": "Mehrfachauswahl",
    "count_loop": "Zählschleife",
    "head_loop": "Kopfgesteuerte Schleife",
    "foot_loop": "Fußgesteuerte Schleife",
    "forever_loop": "Endlosschleife",
    "call": "Unterprogrammaufruf",
    "jump": "Aussprung",
    "parallel": "Parallelabschnitt",
    "try": "Fehlerbehandlung",
}


def _schrift(groesse: int = 9) -> QFont:
    return QFont(_SCHRIFT, groesse)


def _zeilenhoehe() -> float:
    return QFontMetricsF(_schrift()).height()


def texthoehe(text: str, breite: float) -> float:
    """Höhe, die `text` umbrochen in `breite` einnimmt."""
    innen = max(1.0, breite - 2 * INNENABSTAND)
    metriken = QFontMetricsF(_schrift())
    return metriken.boundingRect(
        QRectF(0, 0, innen, 10_000),
        int(Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap),
        text or "",
    ).height()


@dataclass
class Kasten:
    """Ein Block mit seiner ausgerechneten Geometrie. `kopf` ist der
    Bereich mit dem eigenen Text (Bedingung, Schleifenkopf); bei einer
    einfachen Anweisung ist er das ganze Rechteck."""

    block: dict[str, Any]
    rechteck: QRectF
    kopf: QRectF
    kinder: list[Kasten] = field(default_factory=list)
    #: Beschriftungen der Zweige einer Verzweigung/Mehrfachauswahl,
    #: jeweils mit dem Rechteck, über dem sie stehen.
    zweige: list[tuple[str, QRectF]] = field(default_factory=list)

    def alle(self) -> list[Kasten]:
        """Dieser Kasten und alle darunter – für Treffersuche und
        Zeichnen."""
        ergebnis = [self]
        for kind in self.kinder:
            ergebnis.extend(kind.alle())
        return ergebnis


# -- Layout --------------------------------------------------------------


def _kinder(block: dict[str, Any], schluessel: str) -> list[dict[str, Any]]:
    return block.get(schluessel) or []


def _folge_layout(
    bloecke: list[dict[str, Any]], x: float, y: float, breite: float
) -> tuple[list[Kasten], float]:
    """Blöcke untereinander. Gibt die Kästen und die Gesamthöhe zurück.
    Eine leere Folge bekommt trotzdem Höhe, sonst gäbe es keinen Platz,
    den ersten Block hineinzuziehen."""
    if not bloecke:
        return [], MINDESTHOEHE

    kaesten = []
    hoehe = 0.0
    for block in bloecke:
        kasten = layout(block, x, y + hoehe, breite)
        kaesten.append(kasten)
        hoehe += kasten.rechteck.height()
    return kaesten, hoehe


def layout(block: dict[str, Any], x: float, y: float, breite: float) -> Kasten:
    """Rechnet die Geometrie eines Blocks und aller seiner Kinder aus."""
    art = block.get("kind", "statement")
    if art == "sequence":
        kinder, hoehe = _folge_layout(_kinder(block, "children"), x, y, breite)
        rechteck = QRectF(x, y, breite, hoehe)
        return Kasten(block, rechteck, rechteck, kinder)

    if art == "branch":
        return _verzweigung_layout(block, x, y, breite)
    if art == "multi_branch":
        return _mehrfachauswahl_layout(block, x, y, breite)
    if art in KOPFSCHLEIFEN:
        return _schleife_layout(block, x, y, breite, fuss=False)
    if art == "foot_loop":
        return _schleife_layout(block, x, y, breite, fuss=True)
    if art == "parallel":
        return _parallel_layout(block, x, y, breite)
    if art == "try":
        return _try_layout(block, x, y, breite)

    # statement, call, jump: ein einfacher Kasten
    hoehe = max(MINDESTHOEHE, texthoehe(block.get("text", ""), breite) + 2 * INNENABSTAND)
    rechteck = QRectF(x, y, breite, hoehe)
    return Kasten(block, rechteck, rechteck)


def _verzweigung_layout(block: dict[str, Any], x: float, y: float, breite: float) -> Kasten:
    """Bedingung im Dreiecksfeld oben, darunter Ja- und Nein-Zweig
    nebeneinander (Abschnitt 13.5)."""
    kopfhoehe = max(
        MINDESTHOEHE, texthoehe(block.get("text", ""), breite / 2) + 2 * INNENABSTAND
    )
    kopf = QRectF(x, y, breite, kopfhoehe)

    haelfte = breite / 2
    ja, ja_hoehe = _folge_layout(_kinder(block, "then"), x, y + kopfhoehe, haelfte)
    nein, nein_hoehe = _folge_layout(
        _kinder(block, "else"), x + haelfte, y + kopfhoehe, breite - haelfte
    )
    zweighoehe = max(ja_hoehe, nein_hoehe)
    _auf_hoehe_ziehen(ja, zweighoehe)
    _auf_hoehe_ziehen(nein, zweighoehe)

    labels = block.get("labels") or {}
    return Kasten(
        block,
        QRectF(x, y, breite, kopfhoehe + zweighoehe),
        kopf,
        [*ja, *nein],
        [
            (str(labels.get("then", "ja")), QRectF(x, y + kopfhoehe, haelfte, zweighoehe)),
            (
                str(labels.get("else", "nein")),
                QRectF(x + haelfte, y + kopfhoehe, breite - haelfte, zweighoehe),
            ),
        ],
    )


def _mehrfachauswahl_layout(
    block: dict[str, Any], x: float, y: float, breite: float
) -> Kasten:
    """Kopf mit dem Ausdruck, darunter eine Spalte je Fall."""
    faelle = block.get("cases") or []
    kopfhoehe = max(MINDESTHOEHE, texthoehe(block.get("text", ""), breite) + 2 * INNENABSTAND)
    kopf = QRectF(x, y, breite, kopfhoehe)
    if not faelle:
        return Kasten(block, QRectF(x, y, breite, kopfhoehe + MINDESTHOEHE), kopf)

    spaltenbreite = breite / len(faelle)
    beschriftungshoehe = _zeilenhoehe() + 2 * INNENABSTAND
    spalten: list[tuple[list[Kasten], float]] = []
    for nummer, fall in enumerate(faelle):
        spalten.append(
            _folge_layout(
                fall.get("children") or [],
                x + nummer * spaltenbreite,
                y + kopfhoehe + beschriftungshoehe,
                spaltenbreite,
            )
        )

    inhaltshoehe = max((hoehe for _, hoehe in spalten), default=MINDESTHOEHE)
    kinder: list[Kasten] = []
    zweige: list[tuple[str, QRectF]] = []
    for nummer, (kaesten, _) in enumerate(spalten):
        _auf_hoehe_ziehen(kaesten, inhaltshoehe)
        kinder.extend(kaesten)
        zweige.append(
            (
                str(faelle[nummer].get("label", "")),
                QRectF(
                    x + nummer * spaltenbreite,
                    y + kopfhoehe,
                    spaltenbreite,
                    beschriftungshoehe + inhaltshoehe,
                ),
            )
        )

    return Kasten(
        block,
        QRectF(x, y, breite, kopfhoehe + beschriftungshoehe + inhaltshoehe),
        kopf,
        kinder,
        zweige,
    )


def _schleife_layout(
    block: dict[str, Any], x: float, y: float, breite: float, fuss: bool
) -> Kasten:
    """Schleifenkopf (bzw. -fuß) über die volle Breite, der Körper
    daneben eingerückt – der schmale Streifen links macht die Schleife
    auf einen Blick erkennbar."""
    kopfhoehe = max(MINDESTHOEHE, texthoehe(block.get("text", ""), breite) + 2 * INNENABSTAND)
    koerperbreite = breite - EINRUECKUNG

    koerper_y = y if fuss else y + kopfhoehe
    kinder, koerperhoehe = _folge_layout(
        _kinder(block, "children"), x + EINRUECKUNG, koerper_y, koerperbreite
    )
    kopf = QRectF(x, y + koerperhoehe if fuss else y, breite, kopfhoehe)
    return Kasten(block, QRectF(x, y, breite, kopfhoehe + koerperhoehe), kopf, kinder)


def _bandhoehe(beschriftung: str, breite: float) -> float:
    """Höhe des Bandes über einem Abschnitt des Try-Blocks. Das Zeichnen
    rechnet sie aus derselben Aufschrift noch einmal aus, statt sie im
    Kasten mitzuschleppen."""
    return max(
        _zeilenhoehe() + 2 * INNENABSTAND, texthoehe(beschriftung, breite) + 2 * INNENABSTAND
    )


def _parallel_layout(block: dict[str, Any], x: float, y: float, breite: float) -> Kasten:
    """Kopfband, darunter die Stränge nebeneinander – wie eine
    Mehrfachauswahl, nur ohne Beschriftung je Spalte, weil kein Strang
    vor dem anderen ausgewählt wird."""
    straenge = block.get("branches") or []
    kopfhoehe = max(MINDESTHOEHE, texthoehe(block.get("text", ""), breite) + 2 * INNENABSTAND)
    kopf = QRectF(x, y, breite, kopfhoehe)
    if not straenge:
        return Kasten(block, QRectF(x, y, breite, kopfhoehe + MINDESTHOEHE), kopf)

    strangbreite = breite / len(straenge)
    spalten = [
        _folge_layout(strang or [], x + nummer * strangbreite, y + kopfhoehe, strangbreite)
        for nummer, strang in enumerate(straenge)
    ]
    inhaltshoehe = max(hoehe for _, hoehe in spalten)

    kinder: list[Kasten] = []
    zweige: list[tuple[str, QRectF]] = []
    for nummer, (kaesten, _) in enumerate(spalten):
        _auf_hoehe_ziehen(kaesten, inhaltshoehe)
        kinder.extend(kaesten)
        zweige.append(
            ("", QRectF(x + nummer * strangbreite, y + kopfhoehe, strangbreite, inhaltshoehe))
        )

    return Kasten(
        block, QRectF(x, y, breite, kopfhoehe + inhaltshoehe), kopf, kinder, zweige
    )


def _try_layout(block: dict[str, Any], x: float, y: float, breite: float) -> Kasten:
    """Drei Abschnitte übereinander, jeder mit einem Band darüber. Der
    Behandlungszweig trägt zusätzlich den Blocktext, weil dort steht,
    welcher Fehler abgefangen wird."""
    kinder: list[Kasten] = []
    zweige: list[tuple[str, QRectF]] = []
    kopf = QRectF(x, y, breite, MINDESTHOEHE)
    hoehe = 0.0
    for nummer, (schluessel, name) in enumerate(TRY_ABSCHNITTE):
        beschriftung = _try_aufschrift(block, schluessel, name)
        bandhoehe = _bandhoehe(beschriftung, breite)
        if nummer == 0:
            # Das Band des Versuchs ist der Kopf des Blocks.
            kopf = QRectF(x, y, breite, bandhoehe)
        kaesten, koerperhoehe = _folge_layout(
            _kinder(block, schluessel), x, y + hoehe + bandhoehe, breite
        )
        kinder.extend(kaesten)
        zweige.append((beschriftung, QRectF(x, y + hoehe, breite, bandhoehe + koerperhoehe)))
        hoehe += bandhoehe + koerperhoehe

    return Kasten(block, QRectF(x, y, breite, hoehe), kopf, kinder, zweige)


def _try_aufschrift(block: dict[str, Any], schluessel: str, name: str) -> str:
    if schluessel != "catch":
        return name
    text = str(block.get("text", "")).strip()
    return f"{name}: {text}" if text else name


def _auf_hoehe_ziehen(kaesten: list[Kasten], hoehe: float) -> None:
    """Der letzte Block einer Spalte wird bis zur Höhe der Nachbarspalte
    verlängert, damit unten kein Loch im Rahmen bleibt."""
    if not kaesten:
        return
    oben = kaesten[0].rechteck.top()
    fehlt = hoehe - (kaesten[-1].rechteck.bottom() - oben)
    if fehlt > 0:
        _wachsen(kaesten[-1], fehlt)


def _wachsen(kasten: Kasten, zusatz: float) -> None:
    """Verlängert einen Kasten nach unten – und mit ihm den jeweils
    letzten seiner Kinder, damit auch verschachtelte Rahmen dicht
    bleiben."""
    kasten.rechteck.setHeight(kasten.rechteck.height() + zusatz)
    art = kasten.block.get("kind")
    if art in ("statement", "call", "jump"):
        kasten.kopf = QRectF(kasten.rechteck)
        return
    if art == "try":
        _try_wachsen(kasten, zusatz)
        return
    if art == "foot_loop":
        # Der Schleifenfuß sitzt unten und muss mitwandern, sonst stünde
        # die Bedingung nach dem Wachsen mitten im Block.
        kasten.kopf.translate(0, zusatz)
    if kasten.kinder:
        for spalte in _spalten(kasten):
            _wachsen(spalte[-1], zusatz)
    for nummer, (text, rechteck) in enumerate(kasten.zweige):
        kasten.zweige[nummer] = (
            text,
            QRectF(rechteck.x(), rechteck.y(), rechteck.width(), rechteck.height() + zusatz),
        )


def _try_wachsen(kasten: Kasten, zusatz: float) -> None:
    """Beim Try-Block liegen die Abschnitte übereinander statt
    nebeneinander: der zusätzliche Platz gehört deshalb allein dem
    untersten Abschnitt, nicht jeder Spalte."""
    kasten.zweige[-1] = (
        kasten.zweige[-1][0],
        QRectF(kasten.zweige[-1][1]).adjusted(0, 0, 0, zusatz),
    )
    abschluss = _kinder(kasten.block, TRY_ABSCHNITTE[-1][0])
    letzte = [k for k in kasten.kinder if any(k.block is block for block in abschluss)]
    if letzte:
        _wachsen(letzte[-1], zusatz)


def _spalten(kasten: Kasten) -> list[list[Kasten]]:
    """Gruppiert die Kinder eines Kastens nach ihrer x-Position – bei
    Verzweigung und Mehrfachauswahl liegen mehrere Spalten
    nebeneinander, die alle unten bündig enden müssen."""
    nach_x: dict[float, list[Kasten]] = {}
    for kind in kasten.kinder:
        nach_x.setdefault(kind.rechteck.left(), []).append(kind)
    return [sorted(spalte, key=lambda k: k.rechteck.top()) for spalte in nach_x.values()]


def kopfzeile(daten: dict[str, Any]) -> str:
    """Der Name über dem Struktogramm – leer, wenn keiner gesetzt ist."""
    return str(daten.get("name") or "").strip()


def struktogramm_layout(daten: dict[str, Any], breite: float = STANDARDBREITE) -> Kasten:
    """Layout des ganzen Struktogramms aus einer `.pdiag`.

    Hat das Diagramm einen Namen, beginnt der Block erst unterhalb der
    Kopfzeile. Das Layout **kennt** den Versatz also schon – dadurch
    stimmen Zeichnen und Trefferprüfung von allein überein, statt den
    Versatz an zwei Stellen einzurechnen.
    """
    wurzel = daten.get("root") or {"id": "b0", "kind": "sequence", "children": []}
    oben = KOPFHOEHE if kopfzeile(daten) else 0
    return layout(wurzel, 0, oben, breite)


# -- Zeichnen ------------------------------------------------------------


def _stift(stil: Stil) -> QPen:
    stift = QPen(QColor(stil.rand))
    stift.setWidthF(LINIENBREITE)
    stift.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    return stift


def kasten_zeichnen(
    maler: QPainter, kasten: Kasten, stil: Stil, ausgewaehlt: dict[str, Any] | None = None
) -> None:
    """Malt einen Kasten und alles darunter."""
    maler.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    art = kasten.block.get("kind", "statement")

    if art != "sequence":
        maler.setPen(_stift(stil))
        maler.setBrush(QBrush(QColor(stil.fuellung)))
        maler.drawRect(kasten.rechteck)

    if art == "branch":
        _verzweigung_zeichnen(maler, kasten, stil)
    elif art == "multi_branch":
        _mehrfachauswahl_zeichnen(maler, kasten, stil)
    elif art in (*KOPFSCHLEIFEN, "foot_loop"):
        _schleife_zeichnen(maler, kasten, stil)
    elif art == "parallel":
        _parallel_zeichnen(maler, kasten, stil)
    elif art == "try":
        _try_zeichnen(maler, kasten, stil)
    elif art in ("statement", "call", "jump"):
        _anweisung_zeichnen(maler, kasten, stil, art)

    for kind in kasten.kinder:
        kasten_zeichnen(maler, kind, stil, ausgewaehlt)

    if ausgewaehlt is not None and kasten.block is ausgewaehlt:
        stift = QPen(QColor(stil.akzent))
        stift.setWidthF(2.0)
        maler.setPen(stift)
        maler.setBrush(Qt.BrushStyle.NoBrush)
        maler.drawRect(kasten.rechteck.adjusted(1, 1, -1, -1))


def _text_zeichnen(
    maler: QPainter,
    stil: Stil,
    rechteck: QRectF,
    text: str,
    ausrichtung: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignLeft,
) -> None:
    maler.setPen(QColor(stil.text))
    maler.setFont(_schrift())
    maler.drawText(
        rechteck.adjusted(INNENABSTAND, INNENABSTAND, -INNENABSTAND, -INNENABSTAND),
        int(ausrichtung | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap),
        text or "",
    )


def _anweisung_zeichnen(maler: QPainter, kasten: Kasten, stil: Stil, art: str) -> None:
    text = kasten.block.get("text", "")
    if art == "call":
        # Unterprogrammaufruf: zwei senkrechte Striche wie im Flussdiagramm
        maler.setPen(_stift(stil))
        for versatz in (EINRUECKUNG / 2, kasten.rechteck.width() - EINRUECKUNG / 2):
            maler.drawLine(
                QPointF(kasten.rechteck.left() + versatz, kasten.rechteck.top()),
                QPointF(kasten.rechteck.left() + versatz, kasten.rechteck.bottom()),
            )
        _text_zeichnen(
            maler,
            stil,
            kasten.rechteck.adjusted(EINRUECKUNG / 2, 0, -EINRUECKUNG / 2, 0),
            text,
            Qt.AlignmentFlag.AlignHCenter,
        )
        return
    if art == "jump":
        _text_zeichnen(maler, stil, kasten.rechteck, text, Qt.AlignmentFlag.AlignHCenter)
        return
    _text_zeichnen(maler, stil, kasten.rechteck, text)


def _verzweigung_zeichnen(maler: QPainter, kasten: Kasten, stil: Stil) -> None:
    kopf = kasten.kopf
    maler.setPen(_stift(stil))
    # Die beiden Schrägen des Bedingungsdreiecks
    mitte = QPointF(kopf.center().x(), kopf.bottom())
    maler.drawLine(QPointF(kopf.left(), kopf.top()), mitte)
    maler.drawLine(QPointF(kopf.right(), kopf.top()), mitte)
    maler.drawLine(QPointF(kopf.left(), kopf.bottom()), QPointF(kopf.right(), kopf.bottom()))

    _text_zeichnen(
        maler,
        stil,
        QRectF(kopf.center().x() - kopf.width() / 4, kopf.top(), kopf.width() / 2, kopf.height()),
        kasten.block.get("text", ""),
        Qt.AlignmentFlag.AlignHCenter,
    )

    maler.setPen(QColor(stil.text))
    maler.setFont(_schrift(8))
    for nummer, (beschriftung, bereich) in enumerate(kasten.zweige):
        ecke = QRectF(
            bereich.left(),
            kopf.bottom() - _zeilenhoehe() - 2,
            bereich.width(),
            _zeilenhoehe(),
        )
        maler.drawText(
            ecke.adjusted(4, 0, -4, 0),
            int(
                (
                    Qt.AlignmentFlag.AlignLeft
                    if nummer == 0
                    else Qt.AlignmentFlag.AlignRight
                )
                | Qt.AlignmentFlag.AlignVCenter
            ),
            beschriftung,
        )
        maler.setPen(_stift(stil))
        maler.drawLine(
            QPointF(bereich.left(), bereich.top()),
            QPointF(bereich.left(), bereich.bottom()),
        )
        maler.setPen(QColor(stil.text))


def _mehrfachauswahl_zeichnen(maler: QPainter, kasten: Kasten, stil: Stil) -> None:
    kopf = kasten.kopf
    _text_zeichnen(maler, stil, kopf, kasten.block.get("text", ""), Qt.AlignmentFlag.AlignHCenter)
    maler.setPen(_stift(stil))
    maler.drawLine(QPointF(kopf.left(), kopf.bottom()), QPointF(kopf.right(), kopf.bottom()))

    beschriftungshoehe = _zeilenhoehe() + 2 * INNENABSTAND
    for beschriftung, bereich in kasten.zweige:
        maler.setPen(_stift(stil))
        maler.drawLine(
            QPointF(bereich.left(), bereich.top()),
            QPointF(bereich.left(), bereich.bottom()),
        )
        maler.drawLine(
            QPointF(bereich.left(), bereich.top() + beschriftungshoehe),
            QPointF(bereich.right(), bereich.top() + beschriftungshoehe),
        )
        _text_zeichnen(
            maler,
            stil,
            QRectF(bereich.left(), bereich.top(), bereich.width(), beschriftungshoehe),
            beschriftung,
            Qt.AlignmentFlag.AlignHCenter,
        )


def _parallel_zeichnen(maler: QPainter, kasten: Kasten, stil: Stil) -> None:
    """Kopfband mit doppelter Linie – die zweite Linie unterscheidet den
    Parallelabschnitt auf einen Blick von einer Mehrfachauswahl."""
    kopf = kasten.kopf
    _text_zeichnen(maler, stil, kopf, kasten.block.get("text", ""), Qt.AlignmentFlag.AlignHCenter)
    maler.setPen(_stift(stil))
    for versatz in (0, 3):
        maler.drawLine(
            QPointF(kopf.left(), kopf.bottom() - versatz),
            QPointF(kopf.right(), kopf.bottom() - versatz),
        )
    for nummer, (_, bereich) in enumerate(kasten.zweige):
        if nummer == 0:
            continue  # die linke Kante ist schon der Rahmen des Blocks
        maler.drawLine(
            QPointF(bereich.left(), bereich.top()),
            QPointF(bereich.left(), bereich.bottom()),
        )


def _try_zeichnen(maler: QPainter, kasten: Kasten, stil: Stil) -> None:
    """Über jedem der drei Abschnitte ein Band mit seiner Aufschrift."""
    for beschriftung, bereich in kasten.zweige:
        bandhoehe = _bandhoehe(beschriftung, bereich.width())
        _text_zeichnen(
            maler,
            stil,
            QRectF(bereich.left(), bereich.top(), bereich.width(), bandhoehe),
            beschriftung,
        )
        maler.setPen(_stift(stil))
        maler.drawLine(
            QPointF(bereich.left(), bereich.top()),
            QPointF(bereich.right(), bereich.top()),
        )
        maler.drawLine(
            QPointF(bereich.left(), bereich.top() + bandhoehe),
            QPointF(bereich.right(), bereich.top() + bandhoehe),
        )


def _schleife_zeichnen(maler: QPainter, kasten: Kasten, stil: Stil) -> None:
    _text_zeichnen(maler, stil, kasten.kopf, kasten.block.get("text", ""))
    maler.setPen(_stift(stil))
    if kasten.block.get("kind") == "foot_loop":
        maler.drawLine(
            QPointF(kasten.kopf.left(), kasten.kopf.top()),
            QPointF(kasten.kopf.right(), kasten.kopf.top()),
        )
    else:
        maler.drawLine(
            QPointF(kasten.kopf.left(), kasten.kopf.bottom()),
            QPointF(kasten.kopf.right(), kasten.kopf.bottom()),
        )


def struktogramm_zeichnen(
    maler: QPainter,
    daten: dict[str, Any],
    stil: Stil,
    breite: float = STANDARDBREITE,
    ausgewaehlt: dict[str, Any] | None = None,
) -> Kasten:
    """Malt das ganze Struktogramm und gibt sein Layout zurück (die
    Zeichenfläche braucht es gleich wieder für die Treffersuche)."""
    wurzel = struktogramm_layout(daten, breite)
    _kopfzeile_zeichnen(maler, daten, wurzel, stil)
    kasten_zeichnen(maler, wurzel, stil, ausgewaehlt)
    return wurzel


def _kopfzeile_zeichnen(
    maler: QPainter, daten: dict[str, Any], wurzel: Kasten, stil: Stil
) -> None:
    """Der Name des Struktogramms als hinterlegte Zeile darüber.

    `stil.kopf` statt `stil.trennlinie` als Hinterlegung: in der
    Schwarz-Weiß-Vorlage ist die Trennlinie schwarz, und eine damit
    gefüllte Kopfzeile verschluckte den schwarzen Text vollständig –
    derselbe Fehler war in der Entscheidungstabelle schon einmal im PDF
    aufgefallen.
    """
    name = kopfzeile(daten)
    if not name:
        return
    rechteck = QRectF(
        wurzel.rechteck.left(), 0, wurzel.rechteck.width(), KOPFHOEHE
    )
    maler.setPen(_stift(stil))
    maler.setBrush(QBrush(QColor(stil.kopf)))
    maler.drawRect(rechteck)

    schrift = _schrift(10)
    schrift.setBold(True)
    maler.setFont(schrift)
    maler.setPen(QColor(stil.text))
    maler.drawText(
        rechteck.adjusted(INNENABSTAND, 0, -INNENABSTAND, 0),
        Qt.AlignmentFlag.AlignCenter,
        name,
    )
