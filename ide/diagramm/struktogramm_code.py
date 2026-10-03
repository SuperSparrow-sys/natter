"""Struktogramm als Python-Quelltext ausgeben (M9 Schritt 14).

Reine Funktionen ohne Qt: die Zielauswahl (Fenster oder Datei) liegt im
Diagrammfenster, hier steht nur die Übersetzung Blockbaum → Python.
Dadurch ist sie einzeln testbar, und eine zweite Zielsprache wäre
später ein zweites Modul daneben statt ein Umbau (Abschnitt 14.4).

Der Blocktext wird nicht übersetzt. Struktogramme werden im
Unterricht in Pseudocode beschriftet; ein halbautomatischer Übersetzer
würde mehr Verwirrung stiften, als er hilft. Stattdessen entscheidet
`ast.parse`, ob eine Beschriftung schon Python ist. Nur die Zusätze
aus den Vorgabetexten („Bedingung?“, „solange …“, „wiederhole bis …“,
„für …“) fallen vorher weg, und die Zählschleife „i von 1 bis 10“
wird zu `range`. Ist sie Python, wandert sie unverändert in den
Quelltext, sonst wird sie zum Kommentar und in
`Ergebnis.nicht_uebernommen` mitgezählt. Der erzeugte Code ist
dadurch immer gültiges Python, und es ist sofort zu sehen, was von
Hand nachzuziehen ist.
"""

from __future__ import annotations

import ast
import builtins
import keyword
import re
import textwrap
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from ide.diagramm.bloecke import MEHRFACH, SONST, STANDARDTEXTE

STUFE = "    "

#: Platzhalter für eine Bedingung, die kein Python ist. `False` und
#: nicht `True`, damit ein Schleifenkörper nicht versehentlich endlos
#: läuft und ein Zweig nicht so tut, als wäre er genommen worden.
PLATZHALTER_BEDINGUNG = "False"

#: Fallback-Name, wenn das Struktogramm keinen brauchbaren Namen trägt.
STANDARDNAME = "struktogramm"

#: Womit eine Beschriftung beginnt, die den Ausdruck im Kopf nur
#: fortsetzt: „< 0“ unter dem Kopf „x“ heißt `x < 0`.
_VERGLEICHSANFAENGE = ("<", ">", "==", "!=", "in ", "not in ", "is ")

#: Wie eine Schleifenbedingung im Struktogramm oft beginnt. Die
#: Vorgabetexte neuer Blöcke lauten „solange Bedingung“ und „wiederhole
#: bis Bedingung“, die einer Verzweigung „Bedingung?“. Wer dem Muster
#: folgt und „solange x < 10“ schreibt, bekam bis Punkt 156
#: `while False:`, weil das Ganze kein Python ist. Die Zusätze werden
#: deshalb vor der Prüfung abgeschnitten.
_SCHLEIFENZUSATZ = re.compile(
    r"^(?:(?P<solange>(?:wiederhole\s+)?solange)"
    r"|(?P<bis>(?:wiederhole\s+)?bis))"
    r"\s+(?P<rest>.+)$",
    re.IGNORECASE,
)

#: Kopf einer Zählschleife, wie ihn der Vorgabetext „für i von 1 bis
#: n“ vormacht. Bis Punkt 284 wurde daraus `for _ in range(0):`, weil
#: das Ganze kein Python ist, und der Rumpf lief nie.
#: „für“ am Anfang eines Schleifenkopfs, auch „für jedes x in liste“:
#: das Wort davor fällt nur weg, wenn danach „Name in …“ folgt. Ein
#: Name „jede“ in „for jede in liste“ bleibt so stehen.
_FUER = re.compile(
    r"^(?:für|fuer|for)\s+(?:(?:jedes|jede|jeden|jeder)\s+(?=\w+\s+in\s))?"
    r"(?P<rest>.+)$",
    re.IGNORECASE,
)

#: „Eingabe: zahl“ und „Ausgabe: zahl“, wie Ein- und Ausgabe im
#: Struktogramm üblicherweise geschrieben werden. Für Python ist das
#: eine Annotation ohne Wert: gültig, aber ohne jede Wirkung.
_EIN_AUSGABE = re.compile(
    r"^\s*(?P<art>eingabe|ausgabe)\s*:\s*(?P<rest>.+?)\s*$",
    re.IGNORECASE,
)
#: Eine Zuweisung, wie sie im Struktogramm geschrieben wird: „x ← 5“
#: oder „x := 5“. Links ein Name, auch mit Index oder Attribut
#: („liste[i] ← 0“, „self.summe := 0“). „<-“ gehört nicht dazu: „x <- 5“
#: ist in Python schon ein Vergleich mit -5.
#: Mehrere Ziele mit Komma wie beim Tausch „a, b ← b, a“ gehören dazu
#: (Punkt 665).
_ZIEL = r"[^\W\d]\w*(?:\.\w+|\[[^\]]*\])*"
_ZUWEISUNG = re.compile(
    rf"^\s*(?P<ziel>{_ZIEL}(?:\s*,\s*{_ZIEL})*)"
    r"\s*(?:←|:=)\s*(?P<wert>.+?)\s*$"
)
_VON_BIS = re.compile(
    r"^(?P<name>\w+)\s*(?:\s(?:von|from)\s|:?=)\s*(?P<von>.+?)"
    r"\s+(?:bis|to)\s+(?P<bis>.+?)"
    # Ein Komma vor „Schrittweite“ ist erlaubt (Punkt 604).
    r"(?:\s*,?\s+(?:schrittweite|schritt|step)\s+(?P<schritt>.+))?$",
    re.IGNORECASE,
)

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


#: Liest eine Eingabe ein. Eine eingetippte Zahl wird Zahl, auch mit
#: Komma: „8“ wird 8, „2,5“ wird 2.5. Alles andere bleibt Text. Steht
#: vor dem Unterprogramm, sobald es eine „Eingabe:“ gibt.
#:
#: Bis 0.4.3 entstand `input(…)`, und „zahl > 0“ brach mit `TypeError`
#: ab. Danach riet der Erzeuger aus dem übrigen Struktogramm, ob eine
#: Eingabe eine Zahl sein soll (Punkte 579, 601, 622, 643, 656, 659).
#: Jede Regel dafür fand neue Fälle, in denen sie falsch riet, zuletzt
#: Namen, die beim Sortieren zu Zahlen werden sollten (Punkt 662). Was
#: getippt wurde, weiß erst das laufende Programm; deshalb entscheidet
#: es dort.
EINGABE_LESEN = [
    "def eingabe_lesen(frage):",
    '    """Liest eine Eingabe: eine Zahl wird Zahl („8“ wird 8, „2,5“',
    '    wird 2.5), alles andere bleibt Text."""',
    "    text = input(frage).strip()",
    '    ziffern = text.lstrip("+-").replace(",", ".", 1).replace(".", "", 1)',
    "    if not ziffern.isdecimal():",
    "        return text",
    '    if "," in text or "." in text:',
    '        return float(text.replace(",", "."))',
    "    return int(text)",
]


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
            return (
                "1 Zeile konnte nicht übernommen werden und steht als "
                "Kommentar im Code."
            )
        return (
            f"{self.anzahl} Zeilen konnten nicht übernommen werden und "
            "stehen als Kommentar im Code."
        )


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
    wurzel = block if block is not None else (daten.get("root") or {})
    schreiber.zugewiesen = _zugewiesene_namen(wurzel)
    # Ein Schnipsel wird in fremden Code eingefügt; dort können Namen
    # einen Wert haben, die das Struktogramm nicht kennt.
    schreiber.namen_pruefen = block is None
    if block is not None:
        schreiber.folge(_bloecke_von(block), 0)
        if not schreiber.anweisungen:
            # Ein Schnipsel aus lauter Kommentaren wäre kein gültiges
            # Python, sobald ihn jemand einfügt.
            schreiber.zeile("pass", 0)
    else:
        schreiber.zeile(f"def {funktionsname(daten.get('name'))}():", 0)
        schreiber.koerper(_bloecke_von(daten.get("root") or {}), 1)
        schreiber.uebersetzbar_machen()
    zeilen = schreiber.zeilen
    if schreiber.eingabe_lesen:
        zeilen = [*EINGABE_LESEN, "", *([""] if block is None else []), *zeilen]
    return Ergebnis("\n".join(zeilen) + "\n", schreiber.nicht_uebernommen)


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
        #: Die Abbruchbedingung, wenn die innerste Schleife eine
        #: Fußschleife ist, sonst `None`. Ein „weiter“ darin prüft sie
        #: vor dem `continue` (Punkt 157).
        self.fussbedingung: str | None = None
        self.nicht_uebernommen: list[str] = []
        #: Zahl der erzeugten Anweisungen – Kommentare zählen nicht
        #: mit, denn ein Zweig aus lauter Kommentaren braucht trotzdem
        #: ein `pass`.
        self.anweisungen = 0
        #: Wo die unverändert übernommenen Beschriftungen stehen:
        #: (erste Zeile, Zeile dahinter, Tiefe). Scheitert das
        #: Übersetzen des Ganzen an einer davon, wird sie nachträglich
        #: zum Kommentar.
        self.uebernommen: list[tuple[int, int, int]] = []
        #: Namen, die im Struktogramm wie Zahlen benutzt werden; ihre
        #: Eingabe wird zur Zahl (Punkt 579).
        #: Ob eine „Eingabe:“ vorkommt und `eingabe_lesen` braucht.
        self.eingabe_lesen = False
        #: Namen, die im Struktogramm einen Wert bekommen (Punkt 581).
        self.zugewiesen: set[str] = set()
        #: Ob Namen ohne Wert als Pseudocode gelten (Punkt 602).
        self.namen_pruefen = False

    def uebersetzbar_machen(self) -> None:
        """Übersetzt das Ergebnis und macht jede übernommene
        Beschriftung, an der das scheitert, zum Kommentar.

        Manche Fehler zeigen sich erst im Zusammenhang, etwa `global
        x` nach einer Zuweisung an `x` in einem früheren Block. Jeder
        Block für sich ist gültig, zusammen nicht (Punkt 128). Das
        `pass` hinter dem Kommentar hält einen Zweig gültig, der sonst
        leer bliebe.
        """
        for _ in range(len(self.uebernommen) + 1):
            try:
                compile("\n".join(self.zeilen) + "\n", "<struktogramm>", "exec")
            except SyntaxError as fehler:
                stelle = (fehler.lineno or 0) - 1
            else:
                return
            treffer = next(
                (b for b in self.uebernommen if b[0] <= stelle < b[1]), None
            )
            if treffer is None:
                return
            anfang, ende, tiefe = treffer
            roh = [z.strip() for z in self.zeilen[anfang:ende] if z.strip()]
            ersatz = [f"{STUFE * tiefe}# {z}" for z in roh]
            ersatz.append(f"{STUFE * tiefe}pass")
            self.nicht_uebernommen.extend(roh)
            self.zeilen[anfang:ende] = ersatz
            verschiebung = len(ersatz) - (ende - anfang)
            self.uebernommen = [
                (
                    a + verschiebung if a >= ende else a,
                    e + verschiebung if e >= ende else e,
                    t,
                )
                for a, e, t in self.uebernommen
                if (a, e, t) != treffer
            ]

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
    def in_einer_schleife(self, fussbedingung: str | None = None) -> Iterator[None]:
        """Solange das gilt, darf ein Aussprung `break` heißen."""
        vorher = self.in_schleife, self.fussbedingung
        self.in_schleife = True
        self.fussbedingung = fussbedingung
        try:
            yield
        finally:
            self.in_schleife, self.fussbedingung = vorher

    def koerper(self, bloecke: list[dict[str, Any]], tiefe: int) -> None:
        """Ein Zweig oder Schleifenkörper. Kam keine Anweisung dabei
        heraus – weil er leer war oder nur Pseudocode enthielt –, steht
        dort `pass`."""
        vorher = self.anweisungen
        self.folge(bloecke, tiefe)
        if self.anweisungen == vorher:
            self.zeile("pass", tiefe)

    def _logik_ohne_wert(self, roh: Any, ausdruck: str) -> bool:
        """Ob ein Kopf mit „und“, „oder“ oder „nicht“ nach der Übersetzung
        einen Namen liest, der im Struktogramm keinen Wert bekommt.
        „nicht fertig“ ohne Zuweisung an `fertig` ist dann Pseudocode,
        kein `not fertig`, das mit NameError abbräche (Punkt 658). Nur
        im ganzen Struktogramm: in einem Schnipsel kommen Werte von
        außen, wie bei `_unbekannte_namen`."""
        return (
            self.namen_pruefen
            and _hat_logikwort(_einzeilig(roh, logik=False))
            and bool(_namen_ohne_wert(ausdruck, self.zugewiesen))
        )

    def bedingung(
        self,
        roh: str,
        tiefe: int,
        platzhalter: str = PLATZHALTER_BEDINGUNG,
        abbruch: bool | None = None,
    ) -> str:
        """Ausdruck für einen Kopf. Pseudocode passt in keine Bedingung,
        also wandert er als Kommentar darüber und der Kopf bekommt den
        Platzhalter – der Code bleibt so ausführbar.

        `abbruch` sagt, wofür die Bedingung in einer Schleife steht:
        `False` im Kopf (die Schleife läuft, solange sie gilt), `True`
        am Fuß (die Schleife endet, wenn sie gilt). Außerhalb einer
        Schleife ist es `None`."""
        text = _bedingungstext(roh, abbruch)
        if text is not None:
            text = _wahrheitswerte(text, self.zugewiesen)
            if not self._logik_ohne_wert(roh, text):
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
        elif art in MEHRFACH:
            self._mehrfachauswahl(block, tiefe)
        elif art == "count_loop":
            self._zaehlschleife(block, tiefe)
        elif art == "head_loop":
            kopf = self.bedingung(block.get("text", ""), tiefe, abbruch=False)
            self.zeile(f"while {kopf}:", tiefe)
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
        # Ein `break` in einem gewöhnlichen Anweisungsblock wird wie
        # ein Aussprung behandelt: außerhalb einer Schleife verlässt
        # er das Unterprogramm (Punkt 128).
        if text.strip() in ("break", "continue"):
            self._springen(text.strip(), tiefe)
            return
        text = "\n".join(_kommazahlen(zeile) for zeile in text.split("\n"))
        zeilen = [z for z in textwrap.dedent(text).splitlines() if z.strip()]
        if len(zeilen) > 1 and self._zeilenweise(text, zeilen):
            # Ein Block aus mehreren Zeilen wie „Eingabe: a“ und
            # „Eingabe: b“ oder „x ← 1“ und „y ← 2“ wird Zeile für
            # Zeile übersetzt. Bis Punkt 603 galt die Übersetzung von
            # Ein-/Ausgabe und Zuweisung nur für einzeilige Blöcke.
            for zeile in zeilen:
                self._anweisung(zeile, tiefe)
            return
        ein_aus = (
            _EIN_AUSGABE.match(text) if "\n" not in text.strip() else None
        )
        if ein_aus is not None:
            uebersetzt = _ein_ausgabe_als_python(ein_aus)
            if uebersetzt is not None:
                text = uebersetzt
                self.eingabe_lesen = (
                    self.eingabe_lesen or "eingabe_lesen(" in uebersetzt
                )
        # „zahl ← zahl - 1“ und „zahl := zahl - 1“ werden zu
        # `zahl = zahl - 1` (Punkt 481). Als Kommentar übernommen lief
        # ein Countdown sonst endlos.
        zuweisung = (
            _ZUWEISUNG.match(text) if "\n" not in text.strip() else None
        )
        if zuweisung is not None:
            umgeschrieben = f"{zuweisung['ziel']} = {zuweisung['wert']}"
            if _ist_anweisung(umgeschrieben, self.in_schleife):
                text = umgeschrieben
        text = _wahrheitswerte(text, self.zugewiesen)
        if (
            _nur_annotation(text)
            or not _ist_anweisung(text, self.in_schleife)
            or self._pseudocode(text)
        ):
            # Eine Annotation ohne Wert („Ergebnis: summe“) ließe
            # Python gelten; sie bewirkte im Programm aber nichts, und
            # die Schülerin hielte die Zeile für übersetzt. Ebenso ein
            # bloßer Name wie die Vorgabe „Anweisung“ (Punkt 602).
            self.verworfen(text, tiefe)
            return
        anfang = len(self.zeilen)
        for zeile in textwrap.dedent(text).strip("\n").splitlines():
            self.zeilen.append(STUFE * tiefe + zeile if zeile.strip() else "")
        self.uebernommen.append((anfang, len(self.zeilen), tiefe))
        self.anweisungen += 1

    def _zeilenweise(self, text: str, zeilen: list[str]) -> bool:
        """Ob ein mehrzeiliger Block Zeile für Zeile übersetzt wird: wenn
        keine Zeile eingerückt ist und er als Ganzes kein Python ist
        oder eine Zeile Ein-/Ausgabe, Zuweisung mit Pfeil oder eine
        Annotation ohne Wert ist. Ein mehrzeiliger Python-Block mit
        Einrückung bleibt zusammen."""
        if any(z[:1].isspace() for z in zeilen):
            return False
        if not _ist_anweisung(text, self.in_schleife):
            return True
        return any(
            _EIN_AUSGABE.match(z) or _ZUWEISUNG.match(z) or _nur_annotation(z)
            for z in zeilen
        )

    def _pseudocode(self, code: str) -> bool:
        """Ob eine Anweisung, die Python annimmt, trotzdem Pseudocode ist
        (Punkt 602): ein bloßer Name, die unveränderte Vorgabe
        „Unterprogramm()“ oder - im ganzen Struktogramm, nicht im
        Schnipsel - ein Name als Wert, der nirgends einen Wert bekommt."""
        if _nur_ein_name(code):
            return True
        if _einzeilig(code) == STANDARDTEXTE["call"]:
            return True
        return self.namen_pruefen and bool(_unbekannte_namen(code, self.zugewiesen))

    def _aussprung(self, roh: str, tiefe: int) -> None:
        wort = str(roh).strip().lower()
        if wort in AUSSPRUENGE:
            self._springen(AUSSPRUENGE[wort], tiefe)
            return
        # Nur echte Aussprünge wie „return summe“ wandern als Python in
        # den Code. „Ende (Abbruch)“ nahm Python als Aufruf an, und der
        # Lauf endete mit `NameError` (Punkt 602).
        if _ist_aussprung(roh) and _ist_anweisung(roh, self.in_schleife):
            self._anweisung(roh, tiefe)
            return
        self.verworfen(roh, tiefe)
        self._springen("break", tiefe)

    def _springen(self, wort: str, tiefe: int) -> None:
        """Schreibt einen Aussprung.

        In einer Fußschleife steht die Abbruchbedingung am Ende des
        Rumpfs. Ein bloßes `continue` spränge an ihr vorbei, und die
        Schleife endete nie (Punkt 157); im Struktogramm führt „weiter“
        dagegen zur Prüfung am Fuß. Deshalb steht dieselbe Prüfung
        direkt vor dem `continue`."""
        wort = self._sprungwort(wort)
        if wort == "continue" and self.fussbedingung is not None:
            self.zeile(f"if {self.fussbedingung}:", tiefe)
            self.zeile("break", tiefe + 1)
        self.zeile(wort, tiefe)

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
        kopf = _zaehlkopf(block.get("text", ""), "n" in self.zugewiesen)
        if kopf is not None:
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
        # Hier ist `True` der sichere Platzhalter: eine Fußschleife, die
        # nie abbricht, wäre schlimmer als eine, die einmal läuft.
        vorab = _bedingungstext(block.get("text", ""), abbruch=True)
        vorab = _wahrheitswerte(vorab, self.zugewiesen) if vorab else "True"
        if self._logik_ohne_wert(block.get("text", ""), vorab):
            vorab = "True"
        with self.in_einer_schleife(fussbedingung=vorab):
            self.folge(block.get("children") or [], tiefe + 1)
        bedingung = self.bedingung(
            block.get("text", ""), tiefe + 1, platzhalter="True", abbruch=True
        )
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
        # Ein „sonst“-Fall gilt, wo er auch steht; im Code kommt er
        # ans Ende. In der Mitte entstand sonst `elif x == sonst:`
        # (Punkt 581).
        sonst = [
            f for f in faelle
            if _einzeilig(str(f.get("label", ""))).lower() in SONST
        ]
        if sonst:
            faelle = [f for f in faelle if f is not sonst[0]] + [sonst[0]]
        ausdruck = _einzeilig(block.get("text", ""))
        etiketten = [self._fall_beschriftung(fall) for fall in faelle]
        muster = [
            etikett
            for nummer, etikett in enumerate(etiketten)
            if not _ist_sonst(etikett, nummer == len(etiketten) - 1)
        ]
        if _ist_ausdruck(ausdruck) and all(
            _ist_einfacher_wert(wert) and _ist_muster(ausdruck, wert)
            for e in muster
            for wert in _alternativen(e)
        ):
            self._match(faelle, etiketten, ausdruck, tiefe)
        else:
            self._wenn_kette(faelle, etiketten, ausdruck, tiefe)

    def _fall_beschriftung(self, fall: dict[str, Any]) -> str:
        """Die Beschriftung eines Falls als Python. Ein Fall aus Wörtern
        mit „und“, „oder“ oder „nicht“, dessen Namen im Struktogramm
        keinen Wert bekommen, ist ein Text wie „nicht bestanden“; aus ihm
        wurde sonst `not bestanden` und beim Lauf NameError (Punkt 658)."""
        roh = _einzeilig(str(fall.get("label", "")), logik=False)
        etikett = _logikwoerter(roh)
        if (
            self.namen_pruefen
            and etikett != roh
            and all(wort.isidentifier() for wort in roh.split())
            and _namen_ohne_wert(etikett, self.zugewiesen)
        ):
            return repr(roh)
        return self._fall_als_text(etikett)

    def _fall_als_text(self, etikett: str) -> str:
        """Ein Fall wie „rot“ unter dem Kopf `farbe` meint den Text
        „rot“, nicht eine Variable `rot`, die es nicht gibt. Bis
        Punkt 602 entstand `farbe == rot` und beim Lauf `NameError`.
        Ein Name, der im Struktogramm einen Wert bekommt oder eingebaut
        ist, bleibt ein Name. Großbuchstaben allein machen keinen Namen:
        „J“ und „N“ sind die Texte einer Ja/Nein-Abfrage (Punkt 642).
        „wahr“ und „falsch“ werden `True` und `False` (Punkt 641)."""
        if etikett.lower() in _WAHRHEITSWERTE and etikett not in self.zugewiesen:
            return _WAHRHEITSWERTE[etikett.lower()]
        if (
            not self.namen_pruefen
            or not etikett.isidentifier()
            or keyword.iskeyword(etikett)
            or etikett.lower() in SONST
            or etikett in self.zugewiesen
            or etikett in _EINGEBAUT
        ):
            return etikett
        return repr(etikett)

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
            muster = (
                "_"
                if _ist_sonst(etikett, letzter)
                else " | ".join(_alternativen(etikett))
            )
            self.zeile(f"case {muster}:", tiefe + 1)
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
        vergleicht.

        Eine Beschriftung, die schon selbst eine Bedingung ist
        („x < 0“), wird unverändert übernommen, eine mit einem
        Vergleich am Anfang („< 0“) an den Ausdruck im Kopf gehängt.
        Bis dahin entstand aus „x < 0“ unter dem Kopf „x“ die Zeile
        `if x == x < 0:`. Der Kopf wird nur dann als ungültig
        vermerkt, wenn ein Fall ihn wirklich braucht; eine
        Mehrfachauswahl nur aus Bedingungen trägt im Kopf oft bloß
        eine Überschrift.
        """
        gueltig = _ist_ausdruck(ausdruck)
        braucht_kopf = any(
            not (_ist_bedingung(etikett) or _gleichheit(etikett))
            for nummer, etikett in enumerate(etiketten)
            if not _ist_sonst(etikett, nummer == len(etiketten) - 1)
        )
        if braucht_kopf and not gueltig:
            self.verworfen(ausdruck, tiefe)
        for nummer, (fall, etikett) in enumerate(zip(faelle, etiketten, strict=False)):
            letzter = nummer == len(faelle) - 1
            if _ist_sonst(etikett, letzter) and nummer > 0:
                self.zeile("else:", tiefe)
            else:
                schluessel = "if" if nummer == 0 else "elif"
                vergleich = _wahrheitswerte(
                    self._vergleich(ausdruck, etikett, gueltig, tiefe), self.zugewiesen
                )
                if not _ist_kopf(vergleich) or self._logik_ohne_wert(
                    fall.get("label", ""), vergleich
                ):
                    # Kein Kopf darf Code ergeben, der sich nicht
                    # übersetzen lässt (Punkt 637) oder mit NameError
                    # abbricht (Punkt 658).
                    self.verworfen(etikett, tiefe)
                    vergleich = PLATZHALTER_BEDINGUNG
                self.zeile(f"{schluessel} {vergleich}:", tiefe)
            self.koerper(fall.get("children") or [], tiefe + 1)

    def _vergleich(self, ausdruck: str, etikett: str, gueltig: bool, tiefe: int) -> str:
        if _ist_bedingung(etikett):
            return etikett
        gleich = _gleichheit(etikett)
        if gleich is not None:
            return gleich
        if etikett.startswith("=") and not etikett.startswith("=="):
            # „= 0“ unter dem Kopf „x“ heißt `x == 0`; der Fall ging
            # sonst verloren (Punkt 581).
            etikett = "==" + etikett[1:]
        if etikett.startswith(_VERGLEICHSANFAENGE):
            fortgesetzt = f"{ausdruck} {etikett}"
            if gueltig and _ist_ausdruck(fortgesetzt):
                return fortgesetzt
            self.verworfen(etikett, tiefe)
            return PLATZHALTER_BEDINGUNG
        if not _ist_ausdruck(etikett):
            self.verworfen(etikett, tiefe)
            return PLATZHALTER_BEDINGUNG
        if not gueltig:
            return PLATZHALTER_BEDINGUNG
        if len(_alternativen(etikett)) > 1:
            # „1, 2“ heißt „1 oder 2“. Mit `==` davor entstand
            # `x == 1, 2`, und das lässt sich nicht übersetzen.
            return f"{ausdruck} in ({etikett})"
        return f"{ausdruck} == {etikett}"


# -- Prüfungen -----------------------------------------------------------


def _einzeilig(roh: Any, logik: bool = True) -> str:
    """Kopftexte werden in eine Zeile gezogen: ein Umbruch mitten in
    einer Bedingung würde die Einrückung der Ausgabe zerreißen.

    Ein Kommentar mit „#“ fällt dabei weg. Er stand sonst vor dem
    Doppelpunkt, den der Kopf angehängt bekommt, und aus „x > 0 #
    positiv“ wurde `if x > 0 # positiv:` (Punkt 636)."""
    zeilen = [_ohne_kommentar(zeile) for zeile in str(roh or "").splitlines()]
    text = _kommazahlen(" ".join(" ".join(zeilen).split()))
    return _logikwoerter(text) if logik else text


#: „und“, „oder“ und „nicht“, wie im Struktogramm üblich geschrieben.
_LOGIKWOERTER = {"und": "and", "oder": "or", "nicht": "not"}


def _logikwoerter(text: str) -> str:
    """Schreibt „und“, „oder“ und „nicht“ als `and`, `or` und `not`,
    als ganze Wörter und unabhängig von Groß- und Kleinschreibung.

    Eine Bedingung wie „jahr % 4 = 0 und jahr % 100 != 0“ war für
    Python kein Ausdruck und wurde zum Platzhalter `False`; das
    Programm nahm dann immer den Nein-Zweig (Punkt 655). Ersetzt werden
    nur Namen, nie Wörter in einem Text in Anführungszeichen. Lässt
    sich der Text nicht zerlegen, bleibt er, wie er ist. Angewandt wird
    das nur auf Köpfe und Fälle, nicht auf Anweisungen: aus „Ausgabe:
    nicht gefunden“ würde sonst `print(not gefunden)`."""
    if not re.search(r"\b(?:und|oder|nicht)\b", text, re.IGNORECASE):
        return text
    import io
    import tokenize

    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError, IndentationError):
        return text
    stellen = [
        (token.start[1], token.end[1], _LOGIKWOERTER[token.string.lower()])
        for token in tokens
        if token.type == tokenize.NAME and token.start[0] == 1
        and token.string.lower() in _LOGIKWOERTER
    ]
    for anfang, ende, ersatz in reversed(stellen):
        text = text[:anfang] + ersatz + text[ende:]
    return text


#: Eine Kommazahl wie „2,5“: genau ein Komma zwischen zwei Ziffernfolgen,
#: nicht Teil eines Namens und nicht Teil einer Aufzählung wie „1,2,3“.
_KOMMAZAHL = re.compile(r"(?<![\w.,])\d+,\d+(?![\w,])")


def _kommazahlen(text: str) -> str:
    """Schreibt Kommazahlen mit Punkt: „x > 2,5“ wird `x > 2.5`.

    Python las „2,5“ als zwei Werte. Hinter `if` ergab das einen
    Syntaxfehler, „preis ← 2,5“ ein Tupel, und „Ausgabe: 2,5 * x“ gab
    „2 10“ aus (Punkt 637). Umgeschrieben wird nur außerhalb von
    Klammern und Texten in Anführungszeichen und nur, wenn die Ziffern
    direkt am Komma stehen: in `randint(1,6)` trennt das Komma zwei
    Werte, „1, 2“ mit Leerzeichen bleibt eine Aufzählung."""
    if "," not in text:
        return text
    offen = []
    tiefe = 0
    zeichen_davor = None
    for zeichen in text:
        if zeichen_davor in ("'", '"'):
            offen.append(False)
            if zeichen == zeichen_davor:
                zeichen_davor = None
            continue
        offen.append(tiefe == 0)
        if zeichen in ("'", '"'):
            zeichen_davor = zeichen
        elif zeichen in "([{":
            tiefe += 1
        elif zeichen in ")]}":
            tiefe = max(0, tiefe - 1)
    teile = []
    ende = 0
    for treffer in _KOMMAZAHL.finditer(text):
        komma = text.index(",", treffer.start())
        if not offen[komma]:
            continue
        teile.append(text[ende:komma] + ".")
        ende = komma + 1
    teile.append(text[ende:])
    return "".join(teile)


def _ohne_kommentar(zeile: str) -> str:
    """`zeile` ohne einen Kommentar mit „#“. Ein „#“ in einem Text in
    Anführungszeichen bleibt; lässt sich die Zeile nicht zerlegen,
    bleibt sie, wie sie ist."""
    if "#" not in zeile:
        return zeile
    import io
    import tokenize

    try:
        for token in tokenize.generate_tokens(io.StringIO(zeile).readline):
            if token.type == tokenize.COMMENT:
                return zeile[: token.start[1]].rstrip()
    except (tokenize.TokenError, SyntaxError, IndentationError):
        pass
    return zeile


def _ein_ausgabe_als_python(treffer: re.Match[str]) -> str | None:
    """„Eingabe: zahl“ als `zahl = eingabe_lesen("zahl? ")`,
    „Ausgabe: zahl“ als `print(zahl)` - oder `None`, wenn hinter dem
    Doppelpunkt kein Name bzw. kein Ausdruck steht. Ob die Eingabe Zahl
    oder Text ist, entscheidet `eingabe_lesen` beim Lauf."""
    rest = treffer.group("rest")
    if treffer.group("art").lower() == "eingabe":
        if not rest.isidentifier() or keyword.iskeyword(rest):
            return None
        return f'{rest} = eingabe_lesen("{rest}? ")'
    if not _ist_ausdruck(rest):
        return None
    return f"print({rest})"


def _texte(knoten: Any) -> Iterator[str]:
    """Alle Beschriftungen unter `knoten`, gleich in welchem Feld."""
    if isinstance(knoten, dict):
        for wert in knoten.values():
            yield from _texte(wert)
    elif isinstance(knoten, list):
        for wert in knoten:
            yield from _texte(wert)
    elif isinstance(knoten, str):
        yield knoten


_NAME = re.compile(r"[A-Za-z_ÄÖÜäöüß][\wÄÖÜäöüß]*")


def _zugewiesene_namen(wurzel: dict[str, Any]) -> set[str]:
    """Die Namen, die im Struktogramm einen Wert bekommen: hinter
    „Eingabe:“, vor einer Zuweisung und als Laufvariable einer
    Zählschleife („für i von 1 bis 10“, „für jedes x in liste“).

    Bei „Vorname, Nachname = name.split()“ zählen beide Namen, ebenso
    bei „für a, b in paare“. Bis Punkt 640 zählte nur der erste, und
    „Ausgabe: Nachname“ wurde als Pseudocode zum Kommentar."""
    namen = set()
    for text in _texte(wurzel):
        for zeile in text.splitlines():
            namen |= _ziele_einer_zeile(zeile)
            treffer = re.match(
                r"\s*(?:eingabe\s*:\s*(\w+)|(\w+)\s*(?:=(?!=)|←|:=)"
                r"|(?:(?:für|fuer|for)\s+(?:(?:jedes|jede|jeden|jeder)\s+)?)?"
                r"(\w+)\s+(?:von|from|in)\s)",
                zeile,
                re.IGNORECASE,
            )
            if treffer:
                namen.add(treffer.group(1) or treffer.group(2) or treffer.group(3))
    return namen


def _ziele_einer_zeile(zeile: str) -> set[str]:
    """Die Namen, die `zeile` als Python einen Wert gibt, auch mehrere
    bei einer Tupel-Zuweisung oder einer Zählschleife mit „für a, b in
    …“."""
    namen = set()
    fuer = re.match(
        r"\s*(?:für|fuer|for)\s+(?:(?:jedes|jede|jeden|jeder)\s+)?(.+?)\s+in\s",
        zeile,
        re.IGNORECASE,
    )
    if fuer:
        namen |= {
            teil.strip() for teil in fuer.group(1).split(",")
            if teil.strip().isidentifier()
        }
    try:
        baum = ast.parse(re.sub(r"←|:=", "=", zeile).strip())
    except (SyntaxError, ValueError):
        return namen
    return namen | {
        knoten.id for knoten in ast.walk(baum)
        if isinstance(knoten, ast.Name) and isinstance(knoten.ctx, ast.Store)
    }


#: „wahr“ und „falsch“, wie im Struktogramm üblich geschrieben.
_WAHRHEITSWERTE = {"wahr": "True", "falsch": "False"}


def _wahrheitswerte(code: str, zugewiesen: set[str]) -> str:
    """Setzt `True` und `False` für die Namen „wahr“ und „falsch“ ein,
    sofern sie im Struktogramm nicht selbst einen Wert bekommen.
    „fertig ← falsch“ ergab sonst `fertig = falsch` und beim Lauf
    einen `NameError` (Punkt 602). Text in Anführungszeichen bleibt
    unberührt, weil nur Namen im Syntaxbaum ersetzt werden."""
    gesucht = {
        name for name in _WAHRHEITSWERTE
        if name not in zugewiesen and re.search(rf"\b{name}\b", code, re.IGNORECASE)
    }
    if not gesucht:
        return code
    try:
        baum = ast.parse(textwrap.dedent(code))
    except (SyntaxError, ValueError):
        return code
    stellen = [
        knoten for knoten in ast.walk(baum)
        if isinstance(knoten, ast.Name) and knoten.id.lower() in gesucht
        and isinstance(knoten.ctx, ast.Load)
    ]
    if not stellen:
        return code
    zeilen = textwrap.dedent(code).splitlines()
    # Von hinten ersetzen, damit die Spalten davor stimmen bleiben.
    for knoten in sorted(stellen, key=lambda k: (k.lineno, k.col_offset), reverse=True):
        zeile = zeilen[knoten.lineno - 1]
        zeilen[knoten.lineno - 1] = (
            zeile[: knoten.col_offset]
            + _WAHRHEITSWERTE[knoten.id.lower()]
            + zeile[knoten.end_col_offset:]
        )
    return "\n".join(zeilen)


#: Namen, die es in jedem Programm gibt.
_EINGEBAUT = frozenset(dir(builtins)) | {"self"}


def _hat_logikwort(text: str) -> bool:
    """Ob „und“, „oder“ oder „nicht“ als Wort in `text` steht."""
    return bool(re.search(r"\b(?:und|oder|nicht)\b", text, re.IGNORECASE))


def _namen_ohne_wert(ausdruck: str, bekannt: set[str]) -> list[str]:
    """Die Namen, die `ausdruck` als Wert liest, die im Struktogramm aber
    nirgends einen Wert bekommen und auch nicht eingebaut sind. Namen,
    die aufgerufen werden oder vor einem Punkt stehen, zählen nicht:
    das sind Funktionen und Objekte des Programms."""
    try:
        baum = ast.parse(ausdruck, mode="eval")
    except (SyntaxError, ValueError):
        return []
    ausgenommen = {
        knoten.func.id for knoten in ast.walk(baum)
        if isinstance(knoten, ast.Call) and isinstance(knoten.func, ast.Name)
    } | {
        knoten.value.id for knoten in ast.walk(baum)
        if isinstance(knoten, ast.Attribute) and isinstance(knoten.value, ast.Name)
    }
    return [
        knoten.id for knoten in ast.walk(baum)
        if isinstance(knoten, ast.Name) and isinstance(knoten.ctx, ast.Load)
        and knoten.id not in bekannt and knoten.id not in _EINGEBAUT
        and knoten.id not in ausgenommen
    ]


def _unbekannte_namen(code: str, bekannt: set[str]) -> list[str]:
    """Die großgeschriebenen Namen in `code`, die als Wert benutzt
    werden, im Struktogramm aber nirgends einen Wert bekommen und auch
    nicht eingebaut sind - deutsche Hauptwörter wie „Abbruch“ oder
    „Initialisierung“. „Ende (Abbruch)“ ist für Python ein Aufruf von
    `Ende` mit dem Wert `Abbruch`; `Abbruch` hat nie einen Wert, die
    Zeile ist Pseudocode (Punkt 602).

    Kleingeschriebene Namen wie `summe` oder `n` bleiben: ein
    Struktogramm beschreibt oft einen Ausschnitt, dessen Werte von
    außen kommen. Ausgenommen sind auch Namen, die aufgerufen werden
    oder vor einem Punkt stehen (eine Funktion oder ein Objekt des
    Programms), und Konstanten in Großbuchstaben."""
    try:
        baum = ast.parse(textwrap.dedent(code))
    except (SyntaxError, ValueError):
        return []
    gebunden = {
        knoten.id for knoten in ast.walk(baum)
        if isinstance(knoten, ast.Name) and not isinstance(knoten.ctx, ast.Load)
    } | {knoten.arg for knoten in ast.walk(baum) if isinstance(knoten, ast.arg)}
    ausgenommen = {
        knoten.func.id for knoten in ast.walk(baum)
        if isinstance(knoten, ast.Call) and isinstance(knoten.func, ast.Name)
    } | {
        knoten.value.id for knoten in ast.walk(baum)
        if isinstance(knoten, ast.Attribute) and isinstance(knoten.value, ast.Name)
    } | {
        # Hinter `raise` steht eine Ausnahmeklasse des Programms wie
        # „NichtGenugGeld“, kein Hauptwort (Punkt 640).
        name.id
        for knoten in ast.walk(baum) if isinstance(knoten, ast.Raise)
        for teil in (knoten.exc, knoten.cause) if teil is not None
        for name in ast.walk(teil) if isinstance(name, ast.Name)
    }
    unbekannt = []
    for knoten in ast.walk(baum):
        if not (isinstance(knoten, ast.Name) and isinstance(knoten.ctx, ast.Load)):
            continue
        name = knoten.id
        if (
            name in bekannt or name in gebunden or name in ausgenommen
            or name in _EINGEBAUT or name.isupper() or not name[0].isupper()
        ):
            continue
        unbekannt.append(name)
    return unbekannt


def _ist_aussprung(code: str) -> bool:
    """Ob `code` ein Aussprung in Python ist: `return`, `break`,
    `continue`, `raise` oder der Aufruf von `exit`, `quit` oder
    `sys.exit`."""
    try:
        baum = ast.parse(textwrap.dedent(str(code)).strip())
    except (SyntaxError, ValueError):
        return False
    if len(baum.body) != 1:
        return False
    anweisung = baum.body[0]
    if isinstance(anweisung, ast.Return | ast.Break | ast.Continue | ast.Raise):
        return True
    if isinstance(anweisung, ast.Expr) and isinstance(anweisung.value, ast.Call):
        aufruf = ast.unparse(anweisung.value.func)
        return aufruf in ("exit", "quit", "sys.exit")
    return False


def _nur_ein_name(code: str) -> bool:
    """Ob `code` nur aus einem Namen besteht, etwa der Vorgabe
    „Anweisung“ oder „Initialisierung“. Als Anweisung bewirkt ein
    Name nichts."""
    try:
        baum = ast.parse(textwrap.dedent(code))
    except (SyntaxError, ValueError):
        return False
    return (
        len(baum.body) == 1
        and isinstance(baum.body[0], ast.Expr)
        and isinstance(baum.body[0].value, ast.Name)
    )


def _nur_annotation(quelltext: str) -> bool:
    """Ob `quelltext` nur aus einer Annotation ohne Wert besteht."""
    try:
        baum = ast.parse(textwrap.dedent(str(quelltext)))
    except (SyntaxError, ValueError):
        return False
    return len(baum.body) == 1 and (
        isinstance(baum.body[0], ast.AnnAssign) and baum.body[0].value is None
    )


def _ist_anweisung(quelltext: str, in_schleife: bool = True) -> bool:
    """Prüft auf Anweisungsebene – und zwar innerhalb einer Funktion,
    weil `return` sonst schon daran scheiterte, dass es dort nicht
    stehen darf. Die Schleife drumherum gibt es nur, wenn die
    Anweisung auch im erzeugten Code in einer steht; sonst wäre ein
    `break` hier gültig und dort nicht.

    Übersetzt wird mit `compile()` statt nur mit `ast.parse`: `await`
    außerhalb einer async-Funktion, `break` außerhalb einer Schleife
    und `nonlocal` ohne äußere Funktion fallen erst beim Übersetzen
    auf (Punkt 128)."""
    if in_schleife:
        text = textwrap.indent(textwrap.dedent(str(quelltext)), STUFE * 2)
        huelle = f"def _huelle():\n{STUFE}while True:\n{text}"
    else:
        text = textwrap.indent(textwrap.dedent(str(quelltext)), STUFE)
        huelle = f"def _huelle():\n{text}"
    try:
        compile(huelle, "<struktogramm>", "exec")
    except (SyntaxError, ValueError):
        return False
    return True


def _bedingungstext(roh: Any, abbruch: bool | None = None) -> str | None:
    """Die Bedingung als Python-Ausdruck oder `None`, wenn sie keiner
    ist. Ohne Nebenwirkung, damit die Fußschleife ihre Bedingung schon
    vor dem Rumpf kennt.

    Ein „?“ am Ende fällt weg. In einer Schleife auch „solange“ und
    „bis“ am Anfang (Punkt 156); passt das Wort nicht zur Art der
    Bedingung („bis“ im Kopf, „solange“ am Fuß), wird sie verneint.

    Ein einzelnes Gleichheitszeichen wie in `x = 0` wird dabei zu
    `==`, wie schon in der Mehrfachauswahl (Punkt 212).
    """
    text = _einzeilig(roh)
    ausdruck = _als_ausdruck(text)
    if ausdruck is not None:
        return ausdruck
    ohne_frage = text.rstrip("?").rstrip()
    ausdruck = _als_ausdruck(ohne_frage)
    if ohne_frage != text and ausdruck is not None:
        return None if _unausgefuellt(ausdruck) else ausdruck
    if abbruch is None:
        return None
    treffer = _SCHLEIFENZUSATZ.match(ohne_frage)
    if treffer is None:
        return None
    rest = _als_ausdruck(treffer.group("rest"))
    if rest is None or _unausgefuellt(rest):
        return None
    if abbruch == bool(treffer.group("bis")):
        return rest
    return f"not {rest}" if rest.isidentifier() else f"not ({rest})"


def _als_ausdruck(text: str) -> str | None:
    """Der Text als Kopf einer Bedingung, notfalls mit `==` statt eines
    einzelnen `=`; `None`, wenn beides nicht geht. „x > 2, 5“ ist für
    Python ein Tupel und als Ausdruck gültig, hinter `if` aber nicht
    (Punkt 637)."""
    if _ist_ausdruck(text) and _ist_kopf(text):
        return text
    gleich = _gleichheit(text)
    return gleich if gleich is not None and _ist_kopf(gleich) else None


def _ist_kopf(text: str) -> bool:
    """Ob `text` hinter `if` oder `while` stehen kann."""
    try:
        ast.parse(f"if {text}:\n{STUFE}pass")
    except (SyntaxError, ValueError):
        return False
    return True


def _unausgefuellt(rest: str) -> bool:
    """Steht nach dem Abschneiden nur das Wort aus dem Vorgabetext da?
    `Bedingung` wäre ein gültiger Name, beim Ausführen aber ein
    `NameError`; ein unausgefüllter Block bleibt deshalb Kommentar mit
    Platzhalter."""
    return rest.strip().lower() == "bedingung"


def _ist_muster(ausdruck: str, etikett: str) -> bool:
    """Lässt sich `case etikett:` übersetzen? `...` und `a().b` sind
    Ausdrücke, aber keine Muster; aus ihnen entstand bis Punkt 177 ein
    Syntaxfehler."""
    return _ist_anweisung(
        f"match {ausdruck}:\n{STUFE}case {etikett}:\n{STUFE * 2}pass"
    )


def _ist_ausdruck(text: str) -> bool:
    try:
        ast.parse(text, mode="eval")
    except (SyntaxError, ValueError):
        return False
    return True


def _ist_bedingung(text: str) -> bool:
    """Ist die Beschriftung eines Falls schon eine ganze Bedingung,
    etwa `x < 0`, `a and b` oder `not fertig`?"""
    try:
        knoten = ast.parse(text, mode="eval").body
    except (SyntaxError, ValueError):
        return False
    if isinstance(knoten, ast.Compare | ast.BoolOp):
        return True
    return isinstance(knoten, ast.UnaryOp) and isinstance(knoten.op, ast.Not)


def _gleichheit(text: str) -> str | None:
    """„x = 0“ als Bedingung: im Struktogramm üblich geschrieben, in
    Python eine Zuweisung. Ein einzelnes Gleichheitszeichen wird zu
    `==`, wenn daraus eine Bedingung wird; sonst `None`."""
    ersetzt = re.sub(r"(?<![<>=!])=(?!=)", "==", text)
    if ersetzt != text and _ist_bedingung(ersetzt):
        return ersetzt
    return None


def _ist_sonst(etikett: str, letzter: bool) -> bool:
    """Nur der letzte Fall darf der „sonst“-Fall sein: ein `case _` oder
    `else:` in der Mitte macht alles danach unerreichbar, und Python
    lehnt das beim Übersetzen ab."""
    return letzter and etikett.strip().lower() in SONST


def _alternativen(etikett: str) -> list[str]:
    """Die Werte einer Beschriftung wie „1, 2“, die im Struktogramm
    mehrere Werte in einem Fall zusammenfasst (Punkt 282).

    Python liest „1, 2“ als Tupel. Hinter `case` ist das ein
    Sequenzmuster, das nur auf `(1, 2)` passt; `x = 1` landete
    deshalb ohne jede Meldung im „sonst“-Fall. Die Werte werden
    einzeln zurückgegeben, damit daraus `case 1 | 2:` wird. Eine
    Beschriftung in Klammern bleibt ein Tupel, und alles andere
    kommt als einziger Eintrag zurück."""
    text = etikett.strip()
    if text.startswith(("(", "[")):
        return [etikett]
    try:
        knoten = ast.parse(text, mode="eval").body
    except (SyntaxError, ValueError):
        return [etikett]
    if not isinstance(knoten, ast.Tuple) or len(knoten.elts) < 2:
        return [etikett]
    werte = [ast.get_source_segment(text, e) for e in knoten.elts]
    if any(w is None for w in werte):
        return [etikett]
    return [str(w) for w in werte]


def _zaehlkopf(roh: Any, n_bekannt: bool = False) -> str | None:
    """Was in einer Zählschleife hinter `for` steht, oder `None`, wenn
    der Text keine Schleife ergibt.

    Ein „für“ oder „for“ am Anfang fällt weg. „i von 1 bis 10“ (auch
    „i = 1 bis 10“ und mit „Schrittweite 2“) wird zu `i in range(1,
    10 + 1)`, denn im Struktogramm zählt die Schleife bis
    einschließlich 10. Der unveränderte Vorgabetext „für i von 1 bis
    n“ bleibt Platzhalter: `n` gibt es im Programm meist nicht, und
    der Aufruf bräche mit `NameError` ab (Punkt 284) - es sei denn,
    `n` bekommt im Struktogramm einen Wert, etwa über „Eingabe: n“
    (Punkt 581)."""
    text = _einzeilig(roh)
    if not text or (text == STANDARDTEXTE["count_loop"] and not n_bekannt):
        return None
    treffer = _FUER.match(text)
    rest = treffer.group("rest") if treffer else text
    for kandidat in (rest, _von_bis(rest)):
        if kandidat and _ist_anweisung(f"for {kandidat}:\n{STUFE}pass"):
            return kandidat
    return None


def _von_bis(text: str) -> str | None:
    """„i von a bis b“ als `i in range(a, b + 1)`, mit Schrittweite
    als drittes Argument. Bei negativer Schrittweite zählt die
    Schleife abwärts, und die Grenze wird zu `b - 1`."""
    treffer = _VON_BIS.match(text)
    if treffer is None:
        return None
    name = treffer.group("name")
    von = treffer.group("von").strip()
    bis = treffer.group("bis").strip()
    schritt = (treffer.group("schritt") or "").strip()
    if not name.isidentifier() or keyword.iskeyword(name):
        return None
    if not all(_ist_grenze(t) for t in (von, bis, schritt or "1")):
        return None
    anfang, ende = _ganze_zahl(von), _ganze_zahl(bis)
    if not schritt and anfang is not None and ende is not None:
        # „i von 10 bis 1“ zählt abwärts. Mit `range(10, 2)` lief der
        # Rumpf kein einziges Mal (Punkt 482). Nur bei festen Zahlen:
        # bei „von 1 bis n“ steht erst zur Laufzeit fest, was größer ist.
        if anfang > ende:
            schritt = "-1"
    # „(-1)“ ist ebenso abwärts wie „-1“ (Punkt 581).
    wert = _ganze_zahl(schritt) if schritt else None
    abwaerts = schritt.lstrip("( ").startswith("-") or (wert is not None and wert < 0)
    grenze = f"{_als_summand(bis)} {'-' if abwaerts else '+'} 1"
    argumente = [von, grenze] + ([schritt] if schritt else [])
    return f"{name} in range({', '.join(argumente)})"


def _ist_grenze(text: str) -> bool:
    """Ob `text` als Grenze oder Schrittweite von `range` taugt: ein
    Ausdruck, aber kein Tupel und keine Kommazahl. „0,5“ las Python als
    Tupel, und aus „von 0,5 bis 2“ wurde `range(0,5, 2 + 1)`, aus „bis
    2,5“ ein `TypeError` (Punkt 604). `range` zählt nur ganze Zahlen;
    solche Köpfe werden zum Kommentar."""
    try:
        knoten = ast.parse(text, mode="eval").body
    except (SyntaxError, ValueError):
        return False
    if isinstance(knoten, ast.UnaryOp):
        knoten = knoten.operand
    if isinstance(knoten, ast.Tuple):
        return False
    return not (isinstance(knoten, ast.Constant) and isinstance(knoten.value, float))


def _ganze_zahl(text: str) -> int | None:
    """Der Wert, wenn `text` eine ganze Zahl ist, auch mit Minus."""
    try:
        wert = ast.literal_eval(text)
    except (ValueError, SyntaxError, TypeError):
        return None
    if isinstance(wert, bool) or not isinstance(wert, int):
        return None
    return wert


def _als_summand(ausdruck: str) -> str:
    """Klammert den Ausdruck, wenn ein angehängtes `+ 1` sonst nur an
    einem Teil davon hinge, etwa bei `a if b else c`."""
    knoten = ast.parse(ausdruck, mode="eval").body
    einfach = (
        ast.Name, ast.Constant, ast.Attribute, ast.Call, ast.Subscript
    )
    if isinstance(knoten, einfach):
        return ausdruck
    if isinstance(knoten, ast.BinOp) and isinstance(
        knoten.op,
        ast.Add | ast.Sub | ast.Mult | ast.Div | ast.FloorDiv
        | ast.Mod | ast.Pow,
    ):
        return ausdruck
    return f"({ausdruck})"


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
