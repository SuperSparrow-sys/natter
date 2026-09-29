"""Ein Stylesheet ohne Selektor gilt auch für jedes Kind.

Im September 2026 hing der Farbdialog des Diagramm-Editors am
Farbknopf, und auf dem stand

    background-color: #ffffff; border: 1px solid #808080;

ohne Selektor. Qt wendet solche Anweisungen auf das Widget *und auf
jedes Kind* an, und ein Dialog gilt als Kind seines Elternteils. Jede
Beschriftung und jeder Knopf im Farbdialog bekam dadurch einen grauen
Rahmen; der Dialog sah aus, als wäre er abgeschaltet.

Der Fehler war nur auf einem Bildschirmfoto zu erkennen - kein Test
schlug an, und der Dialog funktionierte ja. Diese Datei fängt die
nächste Wiederholung beim Testlauf ab.

`pcl/components/standard.py` kannte die Falle schon: das `Panel`
schreibt seine Füllfarbe ausdrücklich als `QFrame#… { … }` und
begründet das im Kommentar. An den übrigen Stellen war sie nur nicht
angewandt.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

WURZEL = Path(__file__).resolve().parent.parent

#: Eine Anweisung ohne Selektor sieht so aus: `name: wert;` und keine
#: geschweifte Klammer davor oder dahinter.
_MIT_SELEKTOR = re.compile(r"[{}]")


def _python_dateien() -> list[Path]:
    dateien = []
    for teil in ("ide", "pcl"):
        for pfad in sorted((WURZEL / teil).rglob("*.py")):
            if "__pycache__" not in pfad.parts:
                dateien.append(pfad)
    return dateien


def _stylesheet_aufrufe(pfad: Path) -> list[tuple[int, str, bool]]:
    """Jeder `setStyleSheet`-Aufruf: Zeile, Ziel und ob mit Selektor.

    Über den Syntaxbaum und nicht über eine Textsuche: nur so ist
    erkennbar, ob auf `self` oder auf einem anderen Widget gesetzt
    wird, und ob der Text eine geschweifte Klammer trägt.
    """
    try:
        baum = ast.parse(pfad.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover - kaputte Datei faellt anderswo auf
        return []

    treffer = []
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Call):
            continue
        if not isinstance(knoten.func, ast.Attribute) or knoten.func.attr != "setStyleSheet":
            continue
        ziel = ast.unparse(knoten.func.value)
        text = " ".join(
            teil.value if isinstance(teil, ast.Constant) and isinstance(teil.value, str) else ""
            for argument in knoten.args
            for teil in ast.walk(argument)
        )
        treffer.append((knoten.lineno, ziel, bool(_MIT_SELEKTOR.search(text))))
    return treffer


#: Stellen ohne Selektor, die geprüft und für unbedenklich befunden
#: wurden: sie sitzen auf einem Widget ohne Kinder, oder sie gelten
#: dem ganzen Fenster und sollen es auch.
#:
#: Wer hier etwas hinzufügt, hat vorher nachgesehen, ob darunter ein
#: Dialog aufgehen kann.
ERLAUBT = {
    ("ide/shell/hauptfenster.py", "self"),  # ganzes Fenster, gewollt
    ("ide/diagramm/fenster.py", "self"),  # dasselbe für das Diagrammfenster
    ("ide/ladeanzeige.py", "self._stand"),  # ein Label auf dem Startbild
    ("ide/shell/startbild.py", "ueberschrift"),
    ("ide/shell/startbild.py", "knopf"),
    ("ide/shell/startbild.py", "gruss"),
    ("ide/shell/startbild.py", "untertitel"),
    ("ide/designer/canvas.py", "kante"),  # Auswahlrahmen
    ("ide/designer/canvas.py", "anfasser"),  # Größenanfasser
    ("pcl/control.py", "self._qwidget"),  # die Komponente selbst
    ("pcl/form.py", "self._qwidget"),  # das Formular
}


@pytest.mark.parametrize("pfad", _python_dateien(), ids=lambda p: p.name)
def test_kein_unbedachtes_stylesheet_ohne_selektor(pfad: Path) -> None:
    relativ = pfad.relative_to(WURZEL).as_posix()
    unerwartet = [
        f"{relativ}:{zeile} auf {ziel}"
        for zeile, ziel, mit_selektor in _stylesheet_aufrufe(pfad)
        if not mit_selektor and (relativ, ziel) not in ERLAUBT
    ]

    assert not unerwartet, (
        "Stylesheet ohne Selektor an einer ungeprüften Stelle:\n"
        + "\n".join(unerwartet)
        + "\n\nEntweder einen Selektor schreiben (`QPushButton { … }`) oder die "
        "Stelle in ERLAUBT eintragen - nachdem nachgesehen wurde, ob darunter "
        "ein Dialog aufgehen kann."
    )


def test_die_liste_der_ausnahmen_ist_nicht_veraltet() -> None:
    """Sonst schützte der Test oben eine Stelle, die es nicht mehr gibt."""
    vorhanden = set()
    for pfad in _python_dateien():
        relativ = pfad.relative_to(WURZEL).as_posix()
        for _zeile, ziel, mit_selektor in _stylesheet_aufrufe(pfad):
            if not mit_selektor:
                vorhanden.add((relativ, ziel))

    veraltet = ERLAUBT - vorhanden
    assert not veraltet, f"Ausnahmen, die es nicht mehr gibt: {sorted(veraltet)}"


# ------------------------------------------- Dialoge und ihre Eltern
#
# Punkt 2 der offenen Punkte: acht Dialoge bekommen ein Widget als
# Elternteil statt eines Fensters. Beim Hauptfenster ist das gewollt -
# der Dialog soll aussehen wie die IDE. Gefaehrlich ist nur der Fall
# aus Punkt 1: ein Elternteil, dessen Stylesheet fuer genau ein
# kleines Widget gedacht war.

_DIALOG_AUFRUFE = (
    "getColor",
    "getOpenFileName",
    "getSaveFileName",
    "getExistingDirectory",
    "getText",
    "getInt",
)


def _dialog_eltern(pfad: Path) -> list[tuple[int, str, str]]:
    """Zeile, Dialogart und Ausdruck des Elternteils."""
    try:
        baum = ast.parse(pfad.read_text(encoding="utf-8"))
    except SyntaxError:  # pragma: no cover
        return []

    treffer = []
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Call) or not isinstance(knoten.func, ast.Attribute):
            continue
        if knoten.func.attr not in _DIALOG_AUFRUFE or not knoten.args:
            continue
        eltern = next(
            (ast.unparse(a) for a in knoten.args if ast.unparse(a) in ("self", "self.window()")),
            "",
        )
        if eltern:
            treffer.append((knoten.lineno, knoten.func.attr, eltern))
    return treffer


def test_kein_dialog_haengt_an_einem_eigens_gestalteten_widget() -> None:
    """Ein Dialog erbt das Stylesheet seines Elternteils.

    Haengt er an einem Widget, das ein eigenes Stylesheet ohne
    Selektor traegt, bekommt jedes Label und jeder Knopf darin dessen
    Anweisungen. Genau so sah der Farbdialog aus, als er noch am
    Farbknopf hing.
    """
    # Ein Fenster, das sein eigenes Thema setzt, zaehlt nicht: dort
    # soll der Dialog genau dieses Thema erben. Erkennbar daran, dass
    # die Stelle in ERLAUBT steht - dort ist sie mit der Begruendung
    # "ganzes Fenster, gewollt" eingetragen.
    gestaltete_klassen = set()
    for pfad in _python_dateien():
        relativ = pfad.relative_to(WURZEL).as_posix()
        for _zeile, ziel, mit_selektor in _stylesheet_aufrufe(pfad):
            if ziel == "self" and not mit_selektor and (relativ, ziel) not in ERLAUBT:
                gestaltete_klassen.add(relativ)

    treffer = []
    for pfad in _python_dateien():
        relativ = pfad.relative_to(WURZEL).as_posix()
        if relativ not in gestaltete_klassen:
            continue
        for zeile, art, eltern in _dialog_eltern(pfad):
            if eltern == "self":
                treffer.append(f"{relativ}:{zeile} {art} an self")

    assert not treffer, (
        "Dialog an einem Widget mit eigenem Stylesheet ohne Selektor:\n"
        + "\n".join(treffer)
        + "\n\n`self.window()` als Elternteil nehmen."
    )


def test_der_farbdialog_haengt_am_fenster() -> None:
    """Der Fall, um den es ging - hier namentlich festgehalten."""
    quelle = (WURZEL / "ide" / "diagramm" / "eigenschaften.py").read_text(encoding="utf-8")

    assert "QColorDialog.getColor(QColor(self.farbe or \"#ffffff\"), self.window())" in quelle
    assert "getColor(QColor(self.farbe or \"#ffffff\"), self)" not in quelle


# ------------------------------- Punkt 2: die acht ungeprüften Dialoge
#
# Aufgeschrieben waren acht Stellen, an denen ein Dialog ein Widget als
# Elternteil bekommt, und die Frage, ob dort dasselbe passiert wie beim
# Farbdialog. Die Antwort ist nein, und zwar aus einem Grund, der sich
# festhalten lässt: keine dieser vier Klassen setzt überhaupt ein
# Stylesheet. Ihre Dialoge erben damit nur das Thema des Fensters -
# genau das, was sie sollen.

#: Die Dateien aus der Liste in `docs/erledigte_punkte.md`, Punkt 2.
DIALOG_ELTERN = (
    "ide/database/panel.py",
    "ide/project/neu_dialog.py",
    "ide/inspector/eigenschaften_tabelle.py",
    "ide/diagramm/canvas.py",
)


@pytest.mark.parametrize("relativ", DIALOG_ELTERN)
def test_diese_dialogeltern_setzen_gar_kein_stylesheet(relativ: str) -> None:
    pfad = WURZEL / relativ
    aufrufe = _stylesheet_aufrufe(pfad)

    auf_sich_selbst = [
        f"Zeile {zeile}" for zeile, ziel, _mit in aufrufe if ziel == "self"
    ]
    assert not auf_sich_selbst, (
        f"{relativ} gestaltet sich jetzt selbst: {auf_sich_selbst}. "
        f"Damit erben seine Dialoge diese Anweisungen - siehe Punkt 1."
    )


def test_die_liste_dieser_dateien_ist_nicht_veraltet() -> None:
    """Sonst prüfte der Test oben eine Datei, die es nicht mehr gibt."""
    for relativ in DIALOG_ELTERN:
        assert (WURZEL / relativ).is_file(), relativ


def test_in_jeder_dieser_dateien_geht_wirklich_ein_dialog_auf() -> None:
    """Sonst wäre die Liste oben eine Sammlung harmloser Dateien und
    sagte nichts über Dialoge aus."""
    ohne = [
        relativ
        for relativ in DIALOG_ELTERN
        if not _dialog_eltern(WURZEL / relativ)
        and "Dialog(" not in (WURZEL / relativ).read_text(encoding="utf-8")
    ]
    assert not ohne, f"Keine Dialoge (mehr) in: {ohne}"
