"""Jede Eigenschaft jeder Komponente einmal von Hand geändert (M11, 3).

Der Arbeitsauftrag lautet wörtlich: „jede `pcl`-Komponente auf ein
Formular setzen, jede ihrer Eigenschaften im Objektinspektor ändern, das
Programm starten und nachsehen, ob die Änderung auch wirklich ankommt“.
Das Platzieren war geprüft, das Ändern jeder einzelnen Eigenschaft
nicht.

Diesen Weg geht der Test hier, und zwar nicht abgekürzt über
`setattr`, sondern über die Zelle im Objektinspektor. Dazwischen liegt
mehr, als man denkt: die Tabelle wandelt den eingetippten Text in den
Typ der Eigenschaft, setzt ihn live, meldet ihn an den Designer, der
schreibt die `.pfm` und erzeugt daraus `u_*_design.py` neu. Erst diese
Datei führt das Schülerprogramm beim Start aus. Jedes Glied dieser
Kette ist schon einmal gerissen, ohne dass der Designer selbst etwas
davon gemerkt hätte.

Für jede Eigenschaft wird geprüft:

* die Zeile steht im Objektinspektor,
* Zelle und Komponente sind sich nach der Eingabe einig,
* der Wert steht am Live-Objekt, in der `.pfm` und im Programm, das
  aus der erzeugten Design-Datei entsteht,
* der Designer sieht aus wie das Programm: das Qt-Widget der
  geänderten Komponente muss Pixel für Pixel dem Widget entsprechen,
  das das Programm baut. Die beiden entstehen auf verschiedenen Wegen
  (`_bei_prop_aenderung` gegen `_qwidget_erzeugen`); fehlt die
  Eigenschaft in einem davon, fällt es hier auf.

Aufgeteilt wird je Komponente, nicht je Eigenschaft. Designer und
Objektinspektor entstehen einmal je Komponente; danach wird jede
Eigenschaft geändert, geprüft und wieder auf ihren Ausgangswert
gesetzt, damit die nächste vom selben Stand ausgeht wie in einem
eigenen Aufbau. Befunde werden gesammelt und am Ende mit Komponente
und Eigenschaft gemeldet, statt beim ersten abzubrechen. Bis Punkt 223
war der Test je Eigenschaft aufgeteilt: 1 410 Fälle, die Designer,
Inspektor und Codeerzeugung jedes Mal neu aufbauten und zusammen neun
Minuten brauchten.
"""

from __future__ import annotations

import json
import sys
import types
from datetime import date, time
from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from ide.designer.canvas import DesignerCanvas
from ide.inspector.eigenschaften_tabelle import EigenschaftenTabelle
from ide.inspector.objektinspektor import Objektinspektor
from ide.palette.palette import ALLE_KOMPONENTEN
from pcl.form import Form
from pcl.properties import (
    SAMMLUNGS_EIGENSCHAFTEN,
    VERSCHACHTELTE_EIGENSCHAFTEN,
    VERWEIS_EIGENSCHAFTEN,
    eigenschaften,
    text_aus_wert,
    wert_aus_text,
    wert_lesen,
)

#: Alle Komponenten, die sich überhaupt auf ein Formular setzen lassen.
#: Über `ALLE_KOMPONENTEN` statt über namentlich genannte Reiter: so
#: läuft eine später ergänzte Komponente hier von selbst mit, statt
#: still durchzurutschen. Die `DB*`-Komponenten gehören dazu, seit ihre
#: Datenquelle freiwillig ist - der Designer erzeugt Komponenten mit
#: `typ(formular)` allein.
PALETTE = ALLE_KOMPONENTEN

#: Eigenschaften mit einer festen Auswahl oder einem festen Format. Ein
#: beliebiger Text („shape-neu“) wäre kein Wert, den ein Mensch je
#: eintippen würde, und sagte über den Weg durch die Kette nichts aus.
BESONDERE_WERTE: dict[str, Any] = {
    "shape": "circle",
    "kind": "line",
    "color": "#ffcc00",
    "pen_color": "#3366cc",
    "brush_color": "#22aa55",
    "border_color": "#aa3366",
    "font_name": "Courier New",
    "font_color": "#e53935",
    "alignment": "right",
    "decimals": 3,
    # Ein Index braucht einen Eintrag, auf den er zeigt - deshalb
    # bekommt jede Komponente mit `items` unten erst drei Stück.
    "item_index": 1,
}

#: Vorrat für Komponenten mit `items`: ohne Einträge wäre `item_index`
#: nicht sinnvoll prüfbar. `RadioGroup` setzt einen Index ohne Option
#: auf -1 zurück, weil eine Auswahl, die niemand sieht, schlimmer wäre
#: als keine.
VORRAT = ["Apfel", "Birne", "Kirsche"]


def _probewert(typ: type, name: str, alt: Any) -> Any:
    """Ein Wert, der sich vom bisherigen unterscheidet."""
    if name in BESONDERE_WERTE:
        return BESONDERE_WERTE[name]
    if typ is date:
        # Ein anderer Tag als der Standard (1.1.2026) - und einer mit
        # zweistelligem Tag und Monat, damit ein abgeschnittenes Format
        # auffiele.
        return date(2026, 11, 23)
    if typ is time:
        return time(17, 45)
    if typ is bool:
        return not alt
    if typ is int:
        return (alt or 0) + 7
    if typ is float:
        return (alt or 0.0) + 2.5
    if typ is list:
        return ["eins", "zwei"]
    return f"{name}-neu"


class _LeeresFormular(Form):
    def create_components(self) -> None:
        pass


def _alle_eigenschaften(typ: type) -> list[str]:
    """Alles, was der Objektinspektor zu dieser Komponente anzeigen
    muss: die echten `Prop`s, die aufklappbaren Untereigenschaften
    (`font.bold`) und die Sammlungen (`items`, `lines`)."""
    return sorted(
        [
            *eigenschaften(typ),
            *[
                name
                for name, eintrag in VERSCHACHTELTE_EIGENSCHAFTEN.items()
                if hasattr(typ, eintrag.attribut)
            ],
            *[name for name in SAMMLUNGS_EIGENSCHAFTEN if hasattr(typ, name)],
        ]
    )


def _zeile(tabelle: EigenschaftenTabelle, name: str) -> int | None:
    for zeile in range(tabelle.rowCount()):
        element = tabelle.item(zeile, 0)
        if element is not None and element.text() == name:
            return zeile
    return None


def _bearbeitbare_zeilen(tabelle: EigenschaftenTabelle) -> list[str]:
    """Die Zeilen, in die sich etwas eingeben lässt: ein Textfeld gibt
    es bei `ItemIsEditable`, ein Häkchen nur, wenn wirklich ein
    `CheckStateRole` gesetzt wurde. Überschriften der Kategorien
    haben keine Wertzelle."""
    namen = []
    for zeile in range(tabelle.rowCount()):
        name, wert = tabelle.item(zeile, 0), tabelle.item(zeile, 1)
        if name is None or wert is None:
            continue
        bearbeitbar = bool(wert.flags() & Qt.ItemFlag.ItemIsEditable)
        hat_haekchen = wert.data(Qt.ItemDataRole.CheckStateRole) is not None
        if bearbeitbar or hat_haekchen:
            namen.append(name.text())
    return namen


def _bild_ablegen(tmp_path: Path) -> str:
    """Eine Bilddatei, die es gibt, sonst lehnt der Objektinspektor sie
    ab (Punkt 57). Neben dem Ordner der `.pfm`, nicht darin: ein Bild
    im Projektordner stünde relativ in der Datei, und dieser Test führt
    den erzeugten Code nicht im Projektordner aus."""
    ordner = tmp_path.parent / f"{tmp_path.name}_bild"
    ordner.mkdir(exist_ok=True)
    bild = QPixmap(30, 20)
    bild.fill(Qt.GlobalColor.darkGreen)
    assert bild.save(str(ordner / "probe.png"))
    return str(ordner / "probe.png")


def _zelle_setzen(
    tabelle: EigenschaftenTabelle, eigenschaft: str, art: type, neu: Any
) -> None:
    """Gibt `neu` so ein, wie es eine Hand tut."""
    element = tabelle.item(_zeile(tabelle, eigenschaft), 1)
    if art is bool:
        element.setCheckState(
            Qt.CheckState.Checked if neu else Qt.CheckState.Unchecked
        )
    elif art is list:
        # Sammlungen gehen im Betrieb über den Doppelklick-Dialog; der
        # wartet auf einen Knopfdruck, deshalb hier sein Ergebnis.
        tabelle._wert_setzen(eigenschaft, neu)
    else:
        # `text_aus_wert`, nicht `str`: in die Zelle wird getippt, was
        # ein Mensch tippt - ein Datum also deutsch als `23.11.2026`
        # und nicht als `2026-11-23`.
        element.setText(text_aus_wert(neu))


def _zelle_und_komponente_einig(
    tabelle: EigenschaftenTabelle, eigenschaft: str, art: type
) -> str:
    """Leer, wenn die Zelle zeigt, was die Komponente führt, sonst der
    Befund.

    Manche Komponenten berichtigen einen Wert, statt ihn abzulehnen:
    `RadioGroup.item_index = 6` ohne sechste Option fällt auf -1
    zurück. Zeigte der Inspektor dann weiter die 6, stünde dort etwas,
    das es nicht gibt."""
    if art is list:
        return ""
    element = tabelle.item(_zeile(tabelle, eigenschaft), 1)
    jetzt = tabelle._wert_lesen(eigenschaft)
    if art is bool:
        gezeigt: Any = element.checkState() == Qt.CheckState.Checked
    else:
        gezeigt = wert_aus_text(art, element.text())
    if gezeigt != jetzt:
        return f"Zelle zeigt {gezeigt!r}, die Komponente führt {jetzt!r}"
    return ""


def _programm_starten(pfm: Path, zaehler: str) -> tuple[Any, Any]:
    """Führt die erzeugte Design-Datei aus - den Code, den das
    Schülerprogramm beim Start ausführt - und liefert das Formular und
    die Komponente darauf.

    Das Formular muss mit heraus: es hält das Qt-Widget der Komponente
    am Leben. Ohne diese Referenz räumt Python es weg („Internal C++
    object already deleted“).

    Übersetzt wird aus dem Quelltext, nicht über den Import: die Datei
    wird hier mehrmals in derselben Sekunde neu geschrieben, oft mit
    gleicher Länge (`anchors.left = False` gegen `anchors.right =
    True`), und der Import hielte dann den Bytecode im `__pycache__`
    für aktuell und führte die vorige Fassung aus."""
    design = pfm.parent / f"{pfm.stem}_design.py"
    assert design.exists(), "Der Designer hat keinen Code erzeugt."
    modul = types.ModuleType(f"rundlauf_{zaehler}")
    modul.__file__ = str(design)
    sys.modules[modul.__name__] = modul
    try:
        code = compile(design.read_text(encoding="utf-8"), str(design), "exec")
        exec(code, modul.__dict__)  # noqa: S102
        formular = modul._LeeresFormularDesign()
    finally:
        del sys.modules[modul.__name__]
    komponente = next(
        wert for wert in vars(formular).values() if hasattr(wert, "_qwidget")
    )
    return formular, komponente


def _bild(komponente: Any) -> Any:
    """Das Bild des Qt-Widgets von `komponente`.

    Zweimal gezeichnet: ein Widget, das nicht auf dem Bildschirm steht,
    ordnet sich erst beim Zeichnen neu an. Nach `StringGrid.row_count =
    12` bekam die Zeilenleiste im Designer erst beim zweiten Zeichnen
    die Breite für zweistellige Nummern, im frisch gebauten Programm
    schon beim ersten - ein Unterschied, den auf dem Bildschirm niemand
    sieht, weil dort ohnehin oft gezeichnet wird."""
    komponente._qwidget.grab()
    return komponente._qwidget.grab().toImage()


class _Aufbau:
    """Designer, Objektinspektor und `.pfm` für eine Komponente."""

    def __init__(self, tmp_path: Path, typ: type) -> None:
        self.tmp_path = tmp_path
        self.typ = typ
        self.pfm = tmp_path / "u_haupt.pfm"
        self.formular = _LeeresFormular()
        self.canvas = DesignerCanvas(self.formular, pfm_pfad=self.pfm)
        self.komponente = self.canvas.komponente_platzieren(typ, 0, 0)
        self.inspektor = Objektinspektor()
        self.inspektor.formular_anzeigen(self.formular, self.canvas)
        self.inspektor.baum.setCurrentItem(
            self.inspektor.baum.topLevelItem(0).child(0)
        )
        self.tabelle = self.inspektor.eigenschaften_tabelle
        if hasattr(typ, "items"):
            self.tabelle._wert_setzen("items", VORRAT)
        self._laeufe = 0
        self.ausgangsstand = {
            name: wert_lesen(self.komponente, name)
            for name in _alle_eigenschaften(typ)
        }

    def probewert(self, eigenschaft: str, art: type) -> Any:
        neu = _probewert(
            art, eigenschaft, wert_lesen(self.komponente, eigenschaft)
        )
        if eigenschaft == "text" and hasattr(self.typ, "items"):
            # Eine Auswahlliste zeigt nur Texte aus ihren Einträgen,
            # und `text` gibt seit Punkt 175 wieder, was zu sehen ist.
            neu = VORRAT[2]
        if eigenschaft == "picture":
            neu = _bild_ablegen(self.tmp_path)
        return neu

    def pruefen(self, eigenschaft: str) -> list[str]:
        """Ändert `eigenschaft` im Inspektor und liefert die Befunde."""
        tabelle = self.tabelle
        if _zeile(tabelle, eigenschaft) is None:
            return ["steht nicht im Objektinspektor"]
        art = tabelle._typ_von(eigenschaft)
        try:
            return self._aendern(eigenschaft, art)
        finally:
            self._zuruecksetzen()

    def _aendern(self, eigenschaft: str, art: type) -> list[str]:
        tabelle = self.tabelle
        neu = self.probewert(eigenschaft, art)

        _zelle_setzen(tabelle, eigenschaft, art, neu)

        befunde = []
        if tabelle.fehlertext:
            befunde.append(f"Eingabe abgewiesen: {tabelle.fehlertext}")
        if abweichung := _zelle_und_komponente_einig(tabelle, eigenschaft, art):
            befunde.append(abweichung)

        # 1. am Live-Objekt, das der Designer zeigt
        live = wert_lesen(self.komponente, eigenschaft)
        if live != neu:
            befunde.append(f"im Designer {live!r} statt {neu!r}")

        # 2. in der .pfm, der einzigen Quelle des Designers
        self.canvas.jetzt_schreiben()
        kind = json.loads(self.pfm.read_text(encoding="utf-8"))["children"][0]
        if eigenschaft not in kind["properties"]:
            befunde.append("fehlt in der .pfm")

        # 3. im Programm, das aus der erzeugten Design-Datei entsteht,
        # und dort mit demselben Bild wie im Designer
        self._laeufe += 1
        formular, im_programm = _programm_starten(
            self.pfm, f"{self.typ.__name__}_{self._laeufe}"
        )
        im_lauf = wert_lesen(im_programm, eigenschaft)
        if im_lauf != neu:
            befunde.append(f"im Programm {im_lauf!r} statt {neu!r}")
        # Der Auswahlrahmen gehört nicht zum Bild der Komponente.
        self.canvas._auswaehlen(self.formular)
        if _bild(self.komponente) != _bild(im_programm):
            befunde.append("der Designer zeigt ein anderes Bild als das Programm")
        formular.close()

        if eigenschaft == "item_index":
            befunde.extend(self._index_ohne_eintrag(art))
        return befunde

    def _index_ohne_eintrag(self, art: type) -> list[str]:
        """Ein Index, zu dem es keinen Eintrag gibt. Die Komponente darf
        ihn ablehnen oder berichtigen, die Zelle muss danach aber
        zeigen, was gilt."""
        self.tabelle.item(_zeile(self.tabelle, "item_index"), 1).setText(
            str(len(VORRAT) + 3)
        )
        abweichung = _zelle_und_komponente_einig(self.tabelle, "item_index", art)
        return [f"Index ohne Eintrag: {abweichung}"] if abweichung else []

    def _zuruecksetzen(self) -> None:
        """Stellt den Ausgangsstand wieder her, über denselben Weg in
        die `.pfm`, damit die nächste Eigenschaft davon ausgeht wie in
        einem eigenen Aufbau.

        Alle Eigenschaften, nicht nur die geänderte: manche ziehen
        andere mit. `TrackBar.min = 7` schiebt `position` auf 7, und
        `min` allein zurückzusetzen ließe sie dort stehen. Mehrere
        Durchgänge, weil die Reihenfolge zählen kann - `position`
        zurück auf 0 geht erst, wenn `min` wieder 0 ist."""
        for _ in range(3):
            abweichend = [
                name
                for name, wert in self.ausgangsstand.items()
                if wert_lesen(self.komponente, name) != wert
            ]
            if not abweichend:
                break
            for name in abweichend:
                self.tabelle._wert_setzen(name, self.ausgangsstand[name])
        for name in self.ausgangsstand:
            zeile = _zeile(self.tabelle, name)
            if zeile is not None:
                self.tabelle._zelle_zuruecksetzen(
                    self.tabelle.item(zeile, 1), self.tabelle._typ_von(name), name
                )
        self.tabelle.fehlertext = ""


@pytest.mark.parametrize("typ", PALETTE, ids=[typ.__name__ for typ in PALETTE])
def test_jede_eigenschaft_kommt_im_programm_an_und_sieht_gleich_aus(
    tmp_path: Path, typ: type
) -> None:
    aufbau = _Aufbau(tmp_path, typ)
    namen = _alle_eigenschaften(typ)
    befunde: list[str] = []

    # Umgekehrt darf der Inspektor keine Zeile zeigen, die hier nicht
    # durchläuft - sonst fiele eine neue Eigenschaft still heraus.
    # `name` benennt die Komponente um, die Verweise haben eigene Tests
    # (`tests/test_klappmenue_zuordnen.py`).
    ausnahmen = {"name", *VERWEIS_EIGENSCHAFTEN}
    for zeile in _bearbeitbare_zeilen(aufbau.tabelle):
        if zeile not in namen and zeile not in ausnahmen:
            befunde.append(f"{typ.__name__}.{zeile}: läuft hier nicht mit")

    for eigenschaft in namen:
        try:
            gefunden = aufbau.pruefen(eigenschaft)
        except Exception as fehler:  # noqa: BLE001 - als Befund melden
            gefunden = [f"{type(fehler).__name__}: {fehler}"]
        befunde.extend(f"{typ.__name__}.{eigenschaft}: {b}" for b in gefunden)

    assert not befunde, "\n".join(befunde)
