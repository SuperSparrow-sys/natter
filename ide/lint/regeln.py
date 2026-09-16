"""Design-Prüfer (Abschnitt 14): regelbasierte Prüfung von Formularen,
lokal und ohne KI. Arbeitet auf dem geparsten `.pfm`-Inhalt (demselben
`dict`, das `ide.codegen.design` liest), nicht auf einem live
gerenderten Formular – Prüfungen laufen dadurch ohne Qt und ohne echtes
Rendern.

Befunde sind **Hinweise und Warnungen, keine Fehler** (Abschnitt 14):
sie blockieren nichts, weder Start noch Export.

**Umfang, bewusst eingeschränkt** (siehe docs/arbeitspakete/M7.md,
Schritt 1): Größenänderung/Skalierung fehlen (brauchen ein Anker-System
bzw. eine DPI-Simulation, die `pcl.Control` noch nicht hat);
Lesbarkeit ist auf die Kontrastprüfung der `color`-Prop beschränkt
(Mindestschriftgröße/zu viele Schriftarten brauchen eine Schriftgrößen-
/-art-Prop, die es bei `pcl`-Komponenten noch nicht gibt).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

RASTER = 8
_MINDEST_KLICKFLAECHE = 24
_KONTRAST_MINDESTVERHAELTNIS = 4.5

# Namenskonvention (Abschnitt 14): dieselben Präfixe, die im gesamten
# Projekt tatsächlich verwendet werden (siehe beispielprojekte/*).
_PRAEFIXE: dict[str, str] = {
    "Button": "b_",
    "Label": "l_",
    "Edit": "e_",
    "Shape": "s_",
    "StringGrid": "sg_",
    "Image": "i_",
    "CheckBox": "cb_",
    "RadioButton": "rb_",
    "Memo": "m_",
    "ListBox": "lb_",
    "ComboBox": "cbo_",
    "ScrollBar": "sb_",
    "Chart": "ch_",
    "DBGrid": "dbg_",
    "DBEdit": "dbe_",
    "DBText": "dbt_",
    "DBNavigator": "dbn_",
    "DBComboBox": "dbc_",
}

_EINGABE_TYPEN = ("Edit", "ComboBox", "DBEdit", "DBComboBox", "Memo", "StringGrid")
_KLICKBARE_TYPEN = ("Button", "CheckBox", "RadioButton", "ComboBox", "DBNavigator")

# Theme-Textfarben (design/tokens.json) für die Kontrastprüfung - direkt
# hier eingetragen statt aus der Datei geladen, weil sich die beiden
# Werte selten ändern und ein Import von pcl.theme hier eine unnötige
# Kopplung an dessen interne Ladefunktion wäre.
_THEME_TEXTFARBEN = {"light": "#1a1a1a", "dark": "#e8e8e8"}
_THEME_HINTERGRUNDFARBEN = {"light": "#ffffff", "dark": "#1e1e1e"}


@dataclass(frozen=True)
class Befund:
    regel: str
    kategorie: str
    schweregrad: str  # "hinweis" oder "warnung"
    komponente: str | None
    meldung: str


def _eigenschaft(objekt: dict[str, Any], name: str, standard: Any = 0) -> Any:
    return objekt.get("properties", {}).get(name, standard)


def _rechteck(komponente: dict[str, Any]) -> tuple[int, int, int, int]:
    # width/height defaulten wie pcl.Control selbst (75×25) statt auf 0 -
    # die .pfm speichert nur Eigenschaften, die vom Standardwert
    # abweichen (Abschnitt 4.2), ein Kind mit Standardgröße hat also gar
    # keinen "width"/"height"-Schlüssel.
    return (
        _eigenschaft(komponente, "left", 0),
        _eigenschaft(komponente, "top", 0),
        _eigenschaft(komponente, "width", 75),
        _eigenschaft(komponente, "height", 25),
    )


def _ueberlappen(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def pruefen(pfm: dict[str, Any], *, abgeschaltete_regeln: set[str] | None = None) -> list[Befund]:
    """Führt alle Regeln gegen `pfm` (geparster `.pfm`-Inhalt, siehe
    `schemas/pfm.schema.json`) aus. `abgeschaltete_regeln` enthält
    Regel-IDs (siehe `Befund.regel`), die übersprungen werden sollen."""
    abgeschaltete_regeln = abgeschaltete_regeln or set()
    befunde: list[Befund] = []
    for pruefung in (
        _geometrie_pruefen,
        _lesbarkeit_pruefen,
        _konsistenz_pruefen,
        _bedienbarkeit_pruefen,
        _namenskonvention_pruefen,
    ):
        befunde.extend(pruefung(pfm))
    return [b for b in befunde if b.regel not in abgeschaltete_regeln]


def _geometrie_pruefen(pfm: dict[str, Any]) -> list[Befund]:
    befunde: list[Befund] = []
    kinder = pfm.get("children", [])
    form_breite = _eigenschaft(pfm, "width", 0)
    form_hoehe = _eigenschaft(pfm, "height", 0)

    for kind in kinder:
        left, top, width, height = _rechteck(kind)
        if left < 0 or top < 0 or left + width > form_breite or top + height > form_hoehe:
            befunde.append(
                Befund(
                    "geometrie.ausserhalb_formular",
                    "Geometrie",
                    "warnung",
                    kind["name"],
                    f"{kind['name']} liegt teilweise außerhalb des Formulars.",
                )
            )
        if left % RASTER != 0 or top % RASTER != 0:
            befunde.append(
                Befund(
                    "geometrie.nicht_am_raster",
                    "Geometrie",
                    "hinweis",
                    kind["name"],
                    f"{kind['name']} steht nicht am {RASTER}px-Raster.",
                )
            )

    for i, a in enumerate(kinder):
        for b in kinder[i + 1 :]:
            if _ueberlappen(_rechteck(a), _rechteck(b)):
                befunde.append(
                    Befund(
                        "geometrie.ueberlappung",
                        "Geometrie",
                        "warnung",
                        a["name"],
                        f"{a['name']} überlappt mit {b['name']}.",
                    )
                )

    befunde.extend(_kanten_pruefen(kinder))
    befunde.extend(_abstaende_pruefen(kinder))
    return befunde


def _abstaende_pruefen(kinder: list[dict[str, Any]]) -> list[Befund]:
    """Uneinheitliche Abstände: mindestens drei Komponenten in derselben
    Zeile (ähnliche `top`-Position) mit deutlich unterschiedlichen
    horizontalen Lücken zueinander wirken ungleichmäßig verteilt."""
    befunde: list[Befund] = []
    toleranz_zeile = 4
    reihen: list[list[dict[str, Any]]] = []
    for kind in sorted(kinder, key=lambda k: _eigenschaft(k, "top", 0)):
        _, top, _, _ = _rechteck(kind)
        for reihe in reihen:
            _, reihen_top, _, _ = _rechteck(reihe[0])
            if abs(reihen_top - top) <= toleranz_zeile:
                reihe.append(kind)
                break
        else:
            reihen.append([kind])

    for reihe in reihen:
        if len(reihe) < 3:
            continue
        reihe = sorted(reihe, key=lambda k: _eigenschaft(k, "left", 0))
        luecken = []
        for a, b in zip(reihe, reihe[1:], strict=False):
            ax, _, aw, _ = _rechteck(a)
            bx, _, _, _ = _rechteck(b)
            luecken.append(bx - (ax + aw))
        if luecken and max(luecken) - min(luecken) > RASTER:
            befunde.append(
                Befund(
                    "geometrie.uneinheitliche_abstaende",
                    "Geometrie",
                    "hinweis",
                    reihe[0]["name"],
                    "Die horizontalen Abstände zwischen "
                    + ", ".join(k["name"] for k in reihe)
                    + " sind uneinheitlich.",
                )
            )
    return befunde


def _kanten_pruefen(kinder: list[dict[str, Any]]) -> list[Befund]:
    """Nicht bündige Kanten: Komponenten, deren linke Kante fast (aber
    nicht exakt) mit einer anderen übereinstimmt, wirken unabsichtlich
    verschoben."""
    befunde: list[Befund] = []
    toleranz = 3
    for i, a in enumerate(kinder):
        ax, _, _, _ = _rechteck(a)
        for b in kinder[i + 1 :]:
            bx, _, _, _ = _rechteck(b)
            differenz = abs(ax - bx)
            if 0 < differenz <= toleranz:
                befunde.append(
                    Befund(
                        "geometrie.kante_nicht_buendig",
                        "Geometrie",
                        "hinweis",
                        a["name"],
                        f"{a['name']} und {b['name']} sind fast, aber nicht genau "
                        f"linksbündig ({differenz}px Unterschied).",
                    )
                )
    return befunde


def _relative_luminanz(hex_farbe: str) -> float:
    hex_farbe = hex_farbe.lstrip("#")
    werte = (int(hex_farbe[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def kanal(c: float) -> float:
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (kanal(c) for c in werte)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _kontrastverhaeltnis(farbe1: str, farbe2: str) -> float:
    l1, l2 = _relative_luminanz(farbe1), _relative_luminanz(farbe2)
    heller, dunkler = max(l1, l2), min(l1, l2)
    return (heller + 0.05) / (dunkler + 0.05)


def _lesbarkeit_pruefen(pfm: dict[str, Any]) -> list[Befund]:
    befunde: list[Befund] = []
    for kind in [pfm, *pfm.get("children", [])]:
        farbe = _eigenschaft(kind, "color", "")
        if not farbe:
            continue
        name = kind.get("name")
        for theme in ("light", "dark"):
            verhaeltnis = _kontrastverhaeltnis(farbe, _THEME_TEXTFARBEN[theme])
            if verhaeltnis < _KONTRAST_MINDESTVERHAELTNIS:
                ziel = name or "Das Formular"
                befunde.append(
                    Befund(
                        "lesbarkeit.kontrast",
                        "Lesbarkeit",
                        "warnung",
                        name,
                        f"{ziel}: Kontrast von {farbe} zur {theme}en Textfarbe ist mit "
                        f"{verhaeltnis:.1f}:1 niedriger als die WCAG-AA-Mindestgrenze "
                        f"({_KONTRAST_MINDESTVERHAELTNIS}:1).",
                    )
                )
    return befunde


def _konsistenz_pruefen(pfm: dict[str, Any]) -> list[Befund]:
    befunde: list[Befund] = []
    kinder = pfm.get("children", [])

    buttons = [k for k in kinder if k["type"] == "Button"]
    if len(buttons) > 1:
        groessen = [(_eigenschaft(b, "width", 0), _eigenschaft(b, "height", 0)) for b in buttons]
        haeufigste = max(set(groessen), key=groessen.count)
        for button, groesse in zip(buttons, groessen, strict=True):
            if groesse != haeufigste:
                befunde.append(
                    Befund(
                        "konsistenz.button_groesse",
                        "Konsistenz",
                        "hinweis",
                        button["name"],
                        f"{button['name']} hat eine andere Größe ({groesse[0]}×{groesse[1]}) "
                        f"als die übrigen Buttons ({haeufigste[0]}×{haeufigste[1]}).",
                    )
                )

    labels = [k for k in kinder if k["type"] == "Label"]
    eingaben = [k for k in kinder if k["type"] in _EINGABE_TYPEN]
    for eingabe in eingaben:
        ex, ey, _, eh = _rechteck(eingabe)
        e_mitte = ey + eh / 2
        naechstes_label = None
        naechster_abstand = None
        for label in labels:
            lx, ly, lw, lh = _rechteck(label)
            l_mitte = ly + lh / 2
            # Absichtlich keine strikte vertikale Überlappung verlangt -
            # sonst würde ausgerechnet die Fehlausrichtung, die diese
            # Regel finden soll, die Zuordnung selbst verhindern.
            if lx + lw <= ex and abs(l_mitte - e_mitte) <= 60 and ex - (lx + lw) <= 300:
                abstand = ex - (lx + lw)
                if naechster_abstand is None or abstand < naechster_abstand:
                    naechster_abstand = abstand
                    naechstes_label = label
        if naechstes_label is not None:
            _, ly, _, _ = _rechteck(naechstes_label)
            if abs(ly - ey) > 4:
                befunde.append(
                    Befund(
                        "konsistenz.label_ausrichtung",
                        "Konsistenz",
                        "hinweis",
                        eingabe["name"],
                        f"{naechstes_label['name']} ist nicht mit {eingabe['name']} "
                        "auf gleicher Höhe ausgerichtet.",
                    )
                )
    return befunde


def _bedienbarkeit_pruefen(pfm: dict[str, Any]) -> list[Befund]:
    befunde: list[Befund] = []
    kinder = pfm.get("children", [])

    for kind in kinder:
        _, _, width, height = _rechteck(kind)
        if kind["type"] in _KLICKBARE_TYPEN and (
            width < _MINDEST_KLICKFLAECHE or height < _MINDEST_KLICKFLAECHE
        ):
            befunde.append(
                Befund(
                    "bedienbarkeit.klickflaeche",
                    "Bedienbarkeit",
                    "hinweis",
                    kind["name"],
                    f"{kind['name']} ist mit {width}×{height}px kleiner als die "
                    f"empfohlene Mindestklickfläche ({_MINDEST_KLICKFLAECHE}×"
                    f"{_MINDEST_KLICKFLAECHE}px).",
                )
            )

    labels = [k for k in kinder if k["type"] == "Label"]
    for eingabe in kinder:
        if eingabe["type"] not in _EINGABE_TYPEN:
            continue
        ex, ey, ew, eh = _rechteck(eingabe)
        hat_beschriftung = any(
            _in_der_naehe(_rechteck(label), (ex, ey, ew, eh)) for label in labels
        )
        if not hat_beschriftung:
            befunde.append(
                Befund(
                    "bedienbarkeit.ohne_beschriftung",
                    "Bedienbarkeit",
                    "hinweis",
                    eingabe["name"],
                    f"{eingabe['name']} hat kein Label in der Nähe.",
                )
            )

    befunde.extend(_tab_reihenfolge_pruefen(kinder))
    return befunde


def _in_der_naehe(
    label_rechteck: tuple[int, int, int, int],
    eingabe_rechteck: tuple[int, int, int, int],
    grenze: int = 150,
) -> bool:
    lx, ly, lw, lh = label_rechteck
    ex, ey, ew, eh = eingabe_rechteck
    links_daneben = lx + lw <= ex and (ly < ey + eh and ey < ly + lh) and ex - (lx + lw) <= grenze
    darueber = ly + lh <= ey and (lx < ex + ew and ex < lx + lw) and ey - (ly + lh) <= 40
    return links_daneben or darueber


def _tab_reihenfolge_pruefen(kinder: list[dict[str, Any]]) -> list[Befund]:
    if len(kinder) < 2:
        return []
    zeilenhoehe = 24
    erwartete_reihenfolge = sorted(
        kinder, key=lambda k: (_eigenschaft(k, "top", 0) // zeilenhoehe, _eigenschaft(k, "left", 0))
    )
    if [k["name"] for k in erwartete_reihenfolge] == [k["name"] for k in kinder]:
        return []
    return [
        Befund(
            "bedienbarkeit.tab_reihenfolge",
            "Bedienbarkeit",
            "hinweis",
            None,
            "Die Reihenfolge der Komponenten entspricht nicht der visuellen "
            "Lesereihenfolge (oben links nach unten rechts).",
        )
    ]


_STANDARDNAME_MUSTER = re.compile(r"^[a-z]+\d*$")


def _namenskonvention_pruefen(pfm: dict[str, Any]) -> list[Befund]:
    befunde: list[Befund] = []
    for kind in pfm.get("children", []):
        typ = kind["type"]
        name = kind["name"]
        praefix = _PRAEFIXE.get(typ)
        if praefix is not None and not name.startswith(praefix):
            befunde.append(
                Befund(
                    "namenskonvention.praefix",
                    "Namenskonvention",
                    "hinweis",
                    name,
                    f"{name} ({typ}) hat nicht das übliche Präfix {praefix!r}.",
                )
            )
        if _STANDARDNAME_MUSTER.fullmatch(name) and name.lower().startswith(typ.lower()):
            befunde.append(
                Befund(
                    "namenskonvention.standardname",
                    "Namenskonvention",
                    "hinweis",
                    name,
                    f"{name} sieht wie ein unveränderter Standardname aus.",
                )
            )
        beschriftung = _eigenschaft(kind, "caption", None)
        if isinstance(beschriftung, str) and re.fullmatch(rf"{re.escape(typ)}\d*", beschriftung):
            befunde.append(
                Befund(
                    "namenskonvention.standardtext",
                    "Namenskonvention",
                    "hinweis",
                    name,
                    f"{name}: Beschriftung {beschriftung!r} sieht wie ein unveränderter "
                    "Standardtext aus.",
                )
            )
    return befunde
