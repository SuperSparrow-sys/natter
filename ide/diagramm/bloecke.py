"""Verändern des Blockbaums eines Struktogramms (Abschnitt 13.5,
M9 Schritt 9).

Alle Operationen arbeiten auf dem rohen `.pdiag`-`dict` und brauchen
weder Qt noch ein geöffnetes Fenster – sie sind dadurch einzeln
testbar. Die Zeichenfläche verpackt sie in Kommandos, damit sie
rückgängig machbar sind.

Eine **Einfügestelle** beschreibt genau eine Lücke im Baum: die Liste,
in die eingefügt wird, und der Index darin. Weil jede Liste im Baum zu
genau einem Block gehört (`children`, `then`, `else`, `catch`,
`finally`, die `children` eines Falls oder ein Strang eines
Parallelabschnitts), reicht dafür (Elternblock, Schlüssel, Index).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

#: Standardtexte neuer Blöcke – so steht nie ein leerer Kasten da, und
#: es ist gleich zu sehen, was hineingehört.
STANDARDTEXTE = {
    "statement": "Anweisung",
    "branch": "Bedingung?",
    "multi_branch": "Auswahl",
    "count_loop": "für i von 1 bis n",
    "head_loop": "solange Bedingung",
    "foot_loop": "wiederhole bis Bedingung",
    "forever_loop": "endlos",
    "call": "Unterprogramm()",
    "jump": "Abbruch",
    "parallel": "nebenläufig",
    # Steht im Kopf des Behandlungszweigs und wandert unverändert in das
    # `except` der Codeerzeugung – deshalb ausnahmsweise kein deutscher
    # Text, sondern schon gültiges Python.
    "try": "Exception",
}

#: Schlüssel, unter denen ein Block eine einfache Kinderliste führt.
#: `cases` (Mehrfachauswahl) und `branches` (Parallelabschnitt) fehlen
#: hier bewusst: dort steckt je eine Liste **von** Listen.
KINDERSCHLUESSEL: tuple[str, ...] = ("children", "then", "else", "catch", "finally")

#: Blocktypen, in die sich weitere Blöcke einfügen lassen, mit den
#: Schlüsseln ihrer Kinderlisten.
LISTEN_JE_ART: dict[str, tuple[str, ...]] = {
    "sequence": ("children",),
    "branch": ("then", "else"),
    "count_loop": ("children",),
    "head_loop": ("children",),
    "foot_loop": ("children",),
    "forever_loop": ("children",),
    "parallel": ("branches",),
    "try": ("children", "catch", "finally"),
}


@dataclass(frozen=True)
class Einfuegestelle:
    """Eine Lücke im Baum. `fall` ist bei einer Mehrfachauswahl die
    Nummer der Spalte und bei einem Parallelabschnitt die Nummer des
    Strangs, sonst `None`."""

    eltern: dict[str, Any]
    schluessel: str
    index: int
    fall: int | None = None

    def liste(self) -> list[dict[str, Any]]:
        """Die Kinderliste, in die eingefügt wird.

        Ein Schlüssel, den der Blocktyp gar nicht kennt, ist ein Fehler
        und **kein** Grund, stillschweigend eine neue Liste anzulegen:
        vorher legte ein Tippfehler wie `"otherwise"` statt `"else"` ein
        Feld an, das keine Darstellung kennt. Der eingefügte Block war
        danach unsichtbar, stand aber in der Datei – und die
        Schema-Prüfung schlug beim nächsten Öffnen zu.
        """
        erlaubt = LISTEN_JE_ART.get(self.eltern.get("kind", ""), ("children",))
        if self.schluessel not in erlaubt:
            raise ValueError(
                f"Ein Block der Art {self.eltern.get('kind')!r} hat keine Liste "
                f"{self.schluessel!r} (erlaubt: {', '.join(erlaubt)})."
            )
        if self.fall is None:
            return self.eltern.setdefault(self.schluessel, [])
        if self.schluessel == "branches":
            straenge = self.eltern.setdefault("branches", [])
            while len(straenge) <= self.fall:
                straenge.append([])
            return straenge[self.fall]
        return (self.eltern.get("cases") or [])[self.fall].setdefault("children", [])


def neue_id(daten: dict[str, Any]) -> str:
    """Fortlaufende Kennung, die im ganzen Baum noch nicht vorkommt."""
    vergeben = {block["id"] for block in alle_bloecke(daten) if "id" in block}
    nummer = 1
    while f"b{nummer}" in vergeben:
        nummer += 1
    return f"b{nummer}"


def neuer_block(daten: dict[str, Any], art: str) -> dict[str, Any]:
    block: dict[str, Any] = {
        "id": neue_id(daten),
        "kind": art,
        "text": STANDARDTEXTE.get(art, ""),
    }
    if art == "branch":
        block["then"] = []
        block["else"] = []
    elif art == "multi_branch":
        block["cases"] = [
            {"label": "Fall 1", "children": []},
            {"label": "Fall 2", "children": []},
        ]
    elif art in ("count_loop", "head_loop", "foot_loop", "forever_loop"):
        block["children"] = []
    elif art == "parallel":
        # Zwei Stränge, weil ein Parallelabschnitt mit einem Strang
        # nichts anderes wäre als eine Folge.
        block["branches"] = [[], []]
    elif art == "try":
        block["children"] = []
        block["catch"] = []
        block["finally"] = []
    return block


def alle_bloecke(daten_oder_block: dict[str, Any]) -> list[dict[str, Any]]:
    """Alle Blöcke des Baums, Wurzel zuerst. Nimmt sowohl eine ganze
    `.pdiag` als auch einen einzelnen Block entgegen."""
    wurzel = daten_oder_block.get("root", daten_oder_block)
    if not isinstance(wurzel, dict) or "kind" not in wurzel:
        return []

    ergebnis = [wurzel]
    for kind in kinder(wurzel):
        ergebnis.extend(alle_bloecke(kind))
    return ergebnis


def kinder(block: dict[str, Any]) -> list[dict[str, Any]]:
    """Alle direkten Kindblöcke, egal in welcher Liste sie stehen."""
    ergebnis: list[dict[str, Any]] = []
    for schluessel in KINDERSCHLUESSEL:
        ergebnis.extend(block.get(schluessel) or [])
    for fall in block.get("cases") or []:
        ergebnis.extend(fall.get("children") or [])
    for strang in block.get("branches") or []:
        ergebnis.extend(strang or [])
    return ergebnis


def elternteil(
    daten: dict[str, Any], block: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]] | None:
    """Elternblock und die Liste, in der `block` steht – oder `None` für
    die Wurzel."""
    for kandidat in alle_bloecke(daten):
        for liste in _listen(kandidat):
            if any(eintrag is block for eintrag in liste):
                return kandidat, liste
    return None


def _listen(block: dict[str, Any]) -> list[list[dict[str, Any]]]:
    listen = [block[s] for s in KINDERSCHLUESSEL if isinstance(block.get(s), list)]
    listen.extend(
        fall["children"]
        for fall in block.get("cases") or []
        if isinstance(fall.get("children"), list)
    )
    listen.extend(
        strang for strang in block.get("branches") or [] if isinstance(strang, list)
    )
    return listen


def einfuegen(stelle: Einfuegestelle, block: dict[str, Any]) -> None:
    liste = stelle.liste()
    liste.insert(min(stelle.index, len(liste)), block)


def stelle_von(daten: dict[str, Any], block: dict[str, Any]) -> Einfuegestelle | None:
    """Wo `block` gerade steht – **ohne** ihn anzufassen.

    Getrennt von `entfernen()`, weil das Verschieben mit der Maus die
    alte Stelle schon kennen muss, solange der Block noch an Ort und
    Stelle ist: nur so lässt sich die Zielstelle gegen die alte
    verrechnen.
    """
    gefunden = elternteil(daten, block)
    if gefunden is None:
        return None
    eltern, liste = gefunden
    index = next(i for i, eintrag in enumerate(liste) if eintrag is block)
    schluessel, fall = _schluessel_von(eltern, liste)
    return Einfuegestelle(eltern, schluessel, index, fall)


def entfernen(daten: dict[str, Any], block: dict[str, Any]) -> Einfuegestelle | None:
    """Nimmt `block` samt Inhalt aus dem Baum und gibt die Stelle
    zurück, an der er stand – damit „Rückgängig“ ihn wieder genau
    dorthin setzen kann."""
    stelle = stelle_von(daten, block)
    if stelle is None:
        return None
    stelle.liste().pop(stelle.index)
    return stelle


def _schluessel_von(
    eltern: dict[str, Any], liste: list[dict[str, Any]]
) -> tuple[str, int | None]:
    for schluessel in KINDERSCHLUESSEL:
        if eltern.get(schluessel) is liste:
            return schluessel, None
    for nummer, fall in enumerate(eltern.get("cases") or []):
        if fall.get("children") is liste:
            return "children", nummer
    for nummer, strang in enumerate(eltern.get("branches") or []):
        if strang is liste:
            return "branches", nummer
    raise ValueError("Liste gehört nicht zu diesem Block.")


def fall_hinzufuegen(block: dict[str, Any], beschriftung: str | None = None) -> dict[str, Any]:
    """Eine Spalte an eine Mehrfachauswahl anhängen (Abschnitt 13.5:
    „Fälle über Plus/Minus am Block hinzufügen/entfernen“)."""
    faelle = block.setdefault("cases", [])
    fall = {"label": beschriftung or f"Fall {len(faelle) + 1}", "children": []}
    faelle.append(fall)
    return fall


def fall_entfernen(block: dict[str, Any], nummer: int) -> dict[str, Any] | None:
    """Letzte verbleibende Spalte wird nicht entfernt – eine
    Mehrfachauswahl ohne Fall wäre kein sinnvoller Block."""
    faelle = block.get("cases") or []
    if len(faelle) <= 1 or not (0 <= nummer < len(faelle)):
        return None
    return faelle.pop(nummer)


def ist_nachfahre(block: dict[str, Any], moeglicher_nachfahre: dict[str, Any]) -> bool:
    """Verhindert, dass ein Block in sich selbst gezogen wird – der Baum
    hätte danach einen Zyklus und das Layout liefe endlos."""
    return any(eintrag is moeglicher_nachfahre for eintrag in alle_bloecke(block)[1:])
