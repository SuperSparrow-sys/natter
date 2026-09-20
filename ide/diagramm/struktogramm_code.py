"""Struktogramm als Python-Quelltext ausgeben (M9 Schritt 14).

Reine Funktionen ohne Qt: die Zielauswahl (Fenster oder Datei) liegt im
Diagrammfenster, hier steht nur die Übersetzung Blockbaum → Python.
Dadurch ist sie einzeln testbar, und eine zweite Zielsprache wäre
später ein zweites Modul daneben statt ein Umbau (Abschnitt 14.4).

Der Blocktext wird nicht übersetzt. Struktogramme werden im
Unterricht in Pseudocode beschriftet; ein halbautomatischer Übersetzer
würde mehr Verwirrung stiften, als er hilft. Stattdessen entscheidet
`ast.parse`, ob eine Beschriftung schon Python ist: wenn ja, wandert
sie unverändert in den Quelltext, wenn nein, wird sie zum Kommentar und
in `Ergebnis.nicht_uebernommen` mitgezählt. Der erzeugte Code ist
dadurch immer gültiges Python, und es ist sofort zu sehen, was von
Hand nachzuziehen ist.
"""

from __future__ import annotations

import ast
import keyword
import textwrap
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

STUFE = "    "

#: Platzhalter für eine Bedingung, die kein Python ist. `False` und
#: nicht `True`, damit ein Schleifenkörper nicht versehentlich endlos
#: läuft und ein Zweig nicht so tut, als wäre er genommen worden.
PLATZHALTER_BEDINGUNG = "False"

#: Fallback-Name, wenn das Struktogramm keinen brauchbaren Namen trägt.
STANDARDNAME = "struktogramm"

#: Beschriftungen, die den „sonst“-Fall einer Mehrfachauswahl meinen.
SONST = frozenset({"sonst", "andernfalls", "default", "_"})

#: Aussprünge, die im Unterricht üblich sind. Was hier nicht steht und
#: auch kein Python ist, wird zu `break` – der häufigste Fall.
AUSSPRUENGE = {
    "abbruch": "break",
    "abbrechen": "break",
    "break": "break",
    "verlassen": "break",
    "schleife verlassen": "break",
    "ende": "break",
    "weiter": "continue",
    "continue": "continue",
    "nächster durchlauf": "continue",
    "return": "return",
    "rücksprung": "return",
    "zurück": "return",
}


@dataclass
class Ergebnis:
    """Erzeugter Quelltext samt der Zeilen, die kein Python waren."""

    text: str
    nicht_uebernommen: list[str] = field(default_factory=list)

    @property
    def anzahl(self) -> int:
        return len(self.nicht_uebernommen)

    def meldung(self) -> str:
        """Satz für den Kopf des Ausgabefensters. Leer, wenn alles
        übernommen werden konnte – dann gibt es nichts zu melden."""
        if not self.nicht_uebernommen:
            return ""
        if self.anzahl == 1:
            return "1 Zeile konnte nicht übernommen werden."
        return f"{self.anzahl} Zeilen konnten nicht übernommen werden."


def als_python(daten: dict[str, Any], block: dict[str, Any] | None = None) -> Ergebnis:
    """Übersetzt ein Struktogramm nach Python.

    Ist `block` gesetzt, entsteht nur dieser Block samt allem, was in
    ihm steckt – ein Schnipsel zum Kopieren, ohne Funktionskopf. Sonst
    das ganze Struktogramm, eingepackt in eine Funktion mit dem Namen
    aus `daten["name"]`.
    """
    # Beim Schnipsel darf ein Aussprung `break` bleiben: er wird in
    # einen bestehenden Zusammenhang eingefügt, der die Schleife
    # mitbringt. Im ganzen Struktogramm steht dagegen fest, was eine
    # Schleife ist und was nicht.
    schreiber = _Schreiber(in_schleife=block is not None)
    if block is not None:
        schreiber.folge(_bloecke_von(block), 0)
        if not schreiber.anweisungen:
            # Ein Schnipsel aus lauter Kommentaren wäre kein gültiges
            # Python, sobald ihn jemand einfügt.
            schreiber.zeile("pass", 0)
    else:
        schreiber.zeile(f"def {funktionsname(daten.get('name'))}():", 0)
        schreiber.koerper(_bloecke_von(daten.get("root") or {}), 1)
    return Ergebnis("\n".join(schreiber.zeilen) + "\n", schreiber.nicht_uebernommen)


def funktionsname(roh: Any) -> str:
    """Der Name des Struktogramms als Bezeichner. Leerzeichen und
    Bindestriche werden zu Unterstrichen; was danach kein gültiger
    Bezeichner ist, bekommt einen neutralen Namen."""
    name = str(roh or "").strip().replace(" ", "_").replace("-", "_")
    if not name.isidentifier() or keyword.iskeyword(name):
        return STANDARDNAME
    return name


def _bloecke_von(block: dict[str, Any]) -> list[dict[str, Any]]:
    """Eine Folge liefert ihre Kinder, jeder andere Block sich selbst –
    so ist die Wurzel nur ein Sonderfall und kein eigener Zweig."""
    if block.get("kind") == "sequence":
        return block.get("children") or []
    return [block] if block.get("kind") else []


class _Schreiber:
    """Sammelt die Zeilen und nebenbei alles, was nicht übernommen
    werden konnte."""

    def __init__(self, in_schleife: bool = False) -> None:
        self.zeilen: list[str] = []
        #: Steht der Schreiber gerade in einem Schleifenkörper? Außerhalb
        #: wäre `break` zwar geparst, aber nicht übersetzbar – dort wird
        #: aus dem Aussprung ein `return`.
        self.in_schleife = in_schleife
        self.nicht_uebernommen: list[str] = []
        #: Zahl der erzeugten Anweisungen – Kommentare zählen nicht
        #: mit, denn ein Zweig aus lauter Kommentaren braucht trotzdem
        #: ein `pass`.
        self.anweisungen = 0

    # -- Bausteine ------------------------------------------------------

    def zeile(self, text: str, tiefe: int) -> None:
        self.zeilen.append(STUFE * tiefe + text)
        self.anweisungen += 1

    def kommentar(self, text: str, tiefe: int) -> None:
        self.zeilen.append(f"{STUFE * tiefe}# {text}")

    def verworfen(self, roh: str, tiefe: int) -> None:
        """Was kein Python ist, wird zum Kommentar und gezählt."""
        for zeile in [z.strip() for z in str(roh).splitlines() if z.strip()] or [""]:
            self.nicht_uebernommen.append(zeile)
            self.kommentar(zeile, tiefe)

    def folge(self, bloecke: list[dict[str, Any]], tiefe: int) -> None:
        for block in bloecke:
            self.block(block, tiefe)

    @contextmanager
    def in_einer_schleife(self) -> Iterator[None]:
        """Solange das gilt, darf ein Aussprung `break` heißen."""
        vorher = self.in_schleife
        self.in_schleife = True
        try:
            yield
        finally:
            self.in_schleife = vorher

    def koerper(self, bloecke: list[dict[str, Any]], tiefe: int) -> None:
        """Ein Zweig oder Schleifenkörper. Kam keine Anweisung dabei
        heraus – weil er leer war oder nur Pseudocode enthielt –, steht
        dort `pass`."""
        vorher = self.anweisungen
        self.folge(bloecke, tiefe)
        if self.anweisungen == vorher:
            self.zeile("pass", tiefe)

    def bedingung(self, roh: str, tiefe: int, platzhalter: str = PLATZHALTER_BEDINGUNG) -> str:
        """Ausdruck für einen Kopf. Pseudocode passt in keine Bedingung,
        also wandert er als Kommentar darüber und der Kopf bekommt den
        Platzhalter – der Code bleibt so ausführbar."""
        text = _einzeilig(roh)
        if _ist_ausdruck(text):
            return text
        self.verworfen(roh, tiefe)
        return platzhalter

    # -- Blöcke ---------------------------------------------------------

    def block(self, block: dict[str, Any], tiefe: int) -> None:
        art = block.get("kind", "statement")
        if art == "sequence":
            self.folge(block.get("children") or [], tiefe)
        elif art == "branch":
            self._verzweigung(block, tiefe)
        elif art == "multi_branch":
            self._mehrfachauswahl(block, tiefe)
        elif art == "count_loop":
            self._zaehlschleife(block, tiefe)
        elif art == "head_loop":
            self.zeile(f"while {self.bedingung(block.get('text', ''), tiefe)}:", tiefe)
            with self.in_einer_schleife():
                self.koerper(block.get("children") or [], tiefe + 1)
        elif art == "foot_loop":
            self._fussschleife(block, tiefe)
        elif art == "forever_loop":
            # Der Kopf trägt keine Bedingung, sein Text ist nur Aufschrift.
            self.zeile("while True:", tiefe)
            with self.in_einer_schleife():
                self.koerper(block.get("children") or [], tiefe + 1)
        elif art == "parallel":
            self._parallel(block, tiefe)
        elif art == "try":
            self._versuch(block, tiefe)
        elif art == "jump":
            self._aussprung(block.get("text", ""), tiefe)
        else:
            # statement und call: die Zeile bzw. der Aufruf selbst
            self._anweisung(block.get("text", ""), tiefe)

    def _anweisung(self, roh: str, tiefe: int) -> None:
        text = str(roh)
        if not text.strip():
            return
        if not _ist_anweisung(text):
            self.verworfen(text, tiefe)
            return
        for zeile in textwrap.dedent(text).strip("\n").splitlines():
            self.zeilen.append(STUFE * tiefe + zeile if zeile.strip() else "")
        self.anweisungen += 1

    def _aussprung(self, roh: str, tiefe: int) -> None:
        wort = str(roh).strip().lower()
        if wort in AUSSPRUENGE:
            self.zeile(self._sprungwort(AUSSPRUENGE[wort]), tiefe)
            return
        if _ist_anweisung(roh):  # z. B. „return summe“
            self._anweisung(roh, tiefe)
            return
        self.verworfen(roh, tiefe)
        self.zeile(self._sprungwort("break"), tiefe)

    def _sprungwort(self, wort: str) -> str:
        """Außerhalb jeder Schleife ist `break` zwar syntaktisch da,
        lässt sich aber nicht übersetzen – dort bleibt nur, das
        Unterprogramm zu verlassen."""
        if wort in ("break", "continue") and not self.in_schleife:
            return "return"
        return wort

    def _verzweigung(self, block: dict[str, Any], tiefe: int) -> None:
        self.zeile(f"if {self.bedingung(block.get('text', ''), tiefe)}:", tiefe)
        self.koerper(block.get("then") or [], tiefe + 1)
        # Ein leeres `else: pass` wäre reines Rauschen – im Struktogramm
        # ist der Nein-Zweig immer gezeichnet, im Code nicht nötig.
        if block.get("else"):
            self.zeile("else:", tiefe)
            self.koerper(block["else"], tiefe + 1)

    def _zaehlschleife(self, block: dict[str, Any], tiefe: int) -> None:
        kopf = _einzeilig(block.get("text", ""))
        if kopf and _ist_anweisung(f"for {kopf}:\n    pass"):
            self.zeile(f"for {kopf}:", tiefe)
        else:
            self.verworfen(block.get("text", ""), tiefe)
            # `range(0)` statt eines geratenen Bereichs: die Schleife
            # läuft dann gar nicht, statt heimlich falsch zu laufen.
            self.zeile("for _ in range(0):", tiefe)
        with self.in_einer_schleife():
            self.koerper(block.get("children") or [], tiefe + 1)

    def _fussschleife(self, block: dict[str, Any], tiefe: int) -> None:
        """Die Bedingung steht unten und beendet die Schleife, also
        `while True:` mit einem Abbruch am Fuß."""
        self.zeile("while True:", tiefe)
        with self.in_einer_schleife():
            self.folge(block.get("children") or [], tiefe + 1)
        # Hier ist `True` der sichere Platzhalter: eine Fußschleife, die
        # nie abbricht, wäre schlimmer als eine, die einmal läuft.
        bedingung = self.bedingung(block.get("text", ""), tiefe + 1, platzhalter="True")
        self.zeile(f"if {bedingung}:", tiefe + 1)
        self.zeile("break", tiefe + 2)

    def _parallel(self, block: dict[str, Any], tiefe: int) -> None:
        """Echte Nebenläufigkeit zu erzeugen wäre für die Zielgruppe
        irreführend (Abschnitt 14.4) – die Stränge laufen nacheinander,
        und ein Kommentar sagt, wie sie gemeint sind."""
        text = str(block.get("text", "")).strip()
        aufschrift = f"Parallelabschnitt „{text}“" if text else "Parallelabschnitt"
        self.kommentar(f"{aufschrift} – nebenläufig gedacht, hier nacheinander", tiefe)
        for nummer, strang in enumerate(block.get("branches") or [], start=1):
            self.kommentar(f"Strang {nummer}", tiefe)
            self.folge(strang or [], tiefe)

    def _versuch(self, block: dict[str, Any], tiefe: int) -> None:
        self.zeile("try:", tiefe)
        self.koerper(block.get("children") or [], tiefe + 1)
        self.zeile(f"except {self._fehler(block.get('text', ''), tiefe)}:", tiefe)
        self.koerper(block.get("catch") or [], tiefe + 1)
        # `finally:` nur, wenn der Abschluss auch gefüllt ist – leer
        # wäre es eine Zeile, die nichts erklärt.
        if block.get("finally"):
            self.zeile("finally:", tiefe)
            self.koerper(block["finally"], tiefe + 1)

    def _fehler(self, roh: str, tiefe: int) -> str:
        """Der Blocktext benennt den abzufangenden Fehler. Was dort kein
        Python ist, fängt als `Exception` alles ab."""
        text = _einzeilig(roh)
        if not text:
            return "Exception"
        if _ist_anweisung(f"try:\n    pass\nexcept {text}:\n    pass"):
            return text
        self.verworfen(roh, tiefe)
        return "Exception"

    def _mehrfachauswahl(self, block: dict[str, Any], tiefe: int) -> None:
        faelle = block.get("cases") or []
        if not faelle:
            return
        ausdruck = _einzeilig(block.get("text", ""))
        etiketten = [_einzeilig(str(fall.get("label", ""))) for fall in faelle]
        muster = [
            etikett
            for nummer, etikett in enumerate(etiketten)
            if not _ist_sonst(etikett, nummer == len(etiketten) - 1)
        ]
        if _ist_ausdruck(ausdruck) and all(_ist_einfacher_wert(e) for e in muster):
            self._match(faelle, etiketten, ausdruck, tiefe)
        else:
            self._wenn_kette(faelle, etiketten, ausdruck, tiefe)

    def _match(
        self,
        faelle: list[dict[str, Any]],
        etiketten: list[str],
        ausdruck: str,
        tiefe: int,
    ) -> None:
        self.zeile(f"match {ausdruck}:", tiefe)
        for nummer, (fall, etikett) in enumerate(zip(faelle, etiketten, strict=False)):
            letzter = nummer == len(faelle) - 1
            self.zeile(f"case {'_' if _ist_sonst(etikett, letzter) else etikett}:", tiefe + 1)
            self.koerper(fall.get("children") or [], tiefe + 2)

    def _wenn_kette(
        self,
        faelle: list[dict[str, Any]],
        etiketten: list[str],
        ausdruck: str,
        tiefe: int,
    ) -> None:
        """Fallback für Fälle, die keine einfachen Werte sind: eine
        Kette aus `if`/`elif`, die den Ausdruck mit jedem Fall
        vergleicht."""
        gueltig = _ist_ausdruck(ausdruck)
        if not gueltig:
            self.verworfen(ausdruck, tiefe)
        for nummer, (fall, etikett) in enumerate(zip(faelle, etiketten, strict=False)):
            letzter = nummer == len(faelle) - 1
            if _ist_sonst(etikett, letzter) and nummer > 0:
                self.zeile("else:", tiefe)
            else:
                schluessel = "if" if nummer == 0 else "elif"
                vergleich = self._vergleich(ausdruck, etikett, gueltig, tiefe)
                self.zeile(f"{schluessel} {vergleich}:", tiefe)
            self.koerper(fall.get("children") or [], tiefe + 1)

    def _vergleich(self, ausdruck: str, etikett: str, gueltig: bool, tiefe: int) -> str:
        if not _ist_ausdruck(etikett):
            self.verworfen(etikett, tiefe)
            return PLATZHALTER_BEDINGUNG
        if not gueltig:
            return PLATZHALTER_BEDINGUNG
        return f"{ausdruck} == {etikett}"


# -- Prüfungen -----------------------------------------------------------


def _einzeilig(roh: Any) -> str:
    """Kopftexte werden in eine Zeile gezogen: ein Umbruch mitten in
    einer Bedingung würde die Einrückung der Ausgabe zerreißen."""
    return " ".join(str(roh or "").split())


def _ist_anweisung(quelltext: str) -> bool:
    """Prüft auf Anweisungsebene – und zwar innerhalb von Funktion und
    Schleife, weil `return` und `break` sonst schon daran scheiterten,
    dass sie dort nicht stehen dürfen."""
    text = textwrap.indent(textwrap.dedent(str(quelltext)), STUFE * 2)
    try:
        ast.parse(f"def _huelle():\n{STUFE}while True:\n{text}")
    except (SyntaxError, ValueError):
        return False
    return True


def _ist_ausdruck(text: str) -> bool:
    try:
        ast.parse(text, mode="eval")
    except (SyntaxError, ValueError):
        return False
    return True


def _ist_sonst(etikett: str, letzter: bool) -> bool:
    """Nur der letzte Fall darf der „sonst“-Fall sein: ein `case _` oder
    `else:` in der Mitte macht alles danach unerreichbar, und Python
    lehnt das beim Übersetzen ab."""
    return letzter and etikett.strip().lower() in SONST


def _ist_einfacher_wert(text: str) -> bool:
    """Taugt die Beschriftung als `case`-Muster? Nur Literale (auch in
    Tupeln) und Punktnamen wie `Farbe.ROT`. Ein bloßer Name wäre
    syntaktisch erlaubt, würde als Capture-Muster aber alles auffangen –
    genau das, was niemand erwartet, der `Fall 1` hinschreibt."""
    try:
        knoten = ast.parse(text, mode="eval").body
    except (SyntaxError, ValueError):
        return False
    if isinstance(knoten, ast.Constant | ast.Attribute):
        return True
    if isinstance(knoten, ast.UnaryOp) and isinstance(knoten.op, ast.USub):
        return isinstance(knoten.operand, ast.Constant)
    if isinstance(knoten, ast.Tuple):
        return all(isinstance(eintrag, ast.Constant) for eintrag in knoten.elts)
    return False
