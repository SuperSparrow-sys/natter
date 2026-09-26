"""Design-Prüfer (Abschnitt 14): regelbasierte Prüfung von Formularen,
lokal und ohne KI. Arbeitet auf dem geparsten `.pfm`-Inhalt (demselben
`dict`, das `ide.codegen.design` liest), nicht auf einem live
gerenderten Formular – Prüfungen laufen dadurch ohne Qt und ohne echtes
Rendern.

Befunde sind Hinweise und Warnungen, keine Fehler (Abschnitt 14):
sie blockieren nichts, weder Start noch Export.

Umfang, bewusst eingeschränkt (siehe Arbeitspaket M7,
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


@dataclass(frozen=True)
class Befund:
    regel: str
    kategorie: str
    schweregrad: str  # "hinweis" oder "warnung"
    komponente: str | None
    meldung: str
    #: Was man tun kann – jeder Befund hat einen solchen Teil (M11,
    #: Abschnitt 4: „jede Meldung mit Lösungen“). `meldung` endet immer
    #: damit, damit die Oberfläche nichts zusammensetzen muss und der
    #: Prüfungsmodus (M11, Abschnitt 6) ihn an einer einzigen Stelle
    #: wieder abschneiden kann.
    loesung: str = ""


def _befund(
    regel: str,
    kategorie: str,
    schweregrad: str,
    komponente: str | None,
    was: str,
    loesung: str,
) -> Befund:
    """Baut einen `Befund`, dessen `meldung` mit dem Lösungsteil endet.

    Alle Regeln gehen hierüber; von Hand zusammengesetzte Meldungen
    hatten sonst mal einen Lösungsteil und mal keinen – genau der
    Zustand, den M11 Abschnitt 4 abstellt.
    """
    return Befund(regel, kategorie, schweregrad, komponente, f"{was} {loesung}", loesung)


def _eigenschaft(objekt: dict[str, Any], name: str, standard: Any = 0) -> Any:
    return objekt.get("properties", {}).get(name, standard)


def _standardwert(typname: str, name: str, ersatz: int) -> int:
    """Der Standardwert einer Größe, so wie ihn die pcl-Komponente selbst
    hat (`Prop.standardwert`). Die .pfm speichert nur, was davon
    abweicht; wer die Standardgröße nicht kennt, rechnet mit falschen
    Maßen."""
    import pcl

    klasse = getattr(pcl, typname, None)
    wert = getattr(getattr(klasse, name, None), "standardwert", None)
    return wert if isinstance(wert, int) else ersatz


def _formulargroesse(pfm: dict[str, Any]) -> tuple[int, int]:
    """Breite und Höhe des Formulars. Ein neu angelegtes Formular hat
    beide nicht in der .pfm; bis 0.3.3 galt es dann als 0 × 0, und die
    Design-Prüfung meldete jede Komponente als „teilweise außerhalb des
    Formulars“ (Punkt 36)."""
    return (
        _eigenschaft(pfm, "width", _standardwert("Form", "width", 480)),
        _eigenschaft(pfm, "height", _standardwert("Form", "height", 360)),
    )


def _rechteck(komponente: dict[str, Any]) -> tuple[int, int, int, int]:
    # width/height defaulten wie die Komponente selbst statt auf 0 -
    # die .pfm speichert nur Eigenschaften, die vom Standardwert
    # abweichen (Abschnitt 4.2), ein Kind mit Standardgröße hat also gar
    # keinen "width"/"height"-Schlüssel. Meist 75×25, ein Chart aber
    # 320×240.
    typ = komponente.get("type", "")
    return (
        _eigenschaft(komponente, "left", 0),
        _eigenschaft(komponente, "top", 0),
        _eigenschaft(komponente, "width", _standardwert(typ, "width", 75)),
        _eigenschaft(komponente, "height", _standardwert(typ, "height", 25)),
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
    form_breite, form_hoehe = _formulargroesse(pfm)

    for kind in kinder:
        left, top, width, height = _rechteck(kind)
        if left < 0 or top < 0 or left + width > form_breite or top + height > form_hoehe:
            befunde.append(
                _befund(
                    "geometrie.ausserhalb_formular",
                    "Geometrie",
                    "warnung",
                    kind["name"],
                    f"{kind['name']} liegt teilweise außerhalb des Formulars.",
                    "Ins Formular hineinschieben oder das Formular größer machen - "
                    "sonst fehlt sie im laufenden Programm.",
                )
            )

    for i, a in enumerate(kinder):
        for b in kinder[i + 1 :]:
            if _ueberlappen(_rechteck(a), _rechteck(b)):
                befunde.append(
                    _befund(
                        "geometrie.ueberlappung",
                        "Geometrie",
                        "warnung",
                        a["name"],
                        f"{a['name']} überlappt mit {b['name']}.",
                        "Eine der beiden verschieben oder schmaler machen, damit "
                        "beide anklickbar bleiben.",
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
                _befund(
                    "geometrie.uneinheitliche_abstaende",
                    "Geometrie",
                    "hinweis",
                    reihe[0]["name"],
                    "Die horizontalen Abstände zwischen "
                    + ", ".join(k["name"] for k in reihe)
                    + " sind uneinheitlich.",
                    "Die Lücken in der Reihe auf denselben Wert bringen.",
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
                    _befund(
                        "geometrie.kante_nicht_buendig",
                        "Geometrie",
                        "hinweis",
                        a["name"],
                        f"{a['name']} und {b['name']} sind fast, aber nicht genau "
                        f"linksbündig ({differenz}px Unterschied).",
                        "Beiden denselben „left“-Wert geben, wenn sie bündig sein sollen.",
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
                # Dezimalkomma wie überall in der Oberfläche - der
                # Befund landet im Panel „Meldungen“ und wird gelesen.
                gemessen = f"{verhaeltnis:.1f}".replace(".", ",")
                befunde.append(
                    _befund(
                        "lesbarkeit.kontrast",
                        "Lesbarkeit",
                        "warnung",
                        name,
                        f"{ziel}: Der Text hebt sich von der Farbe {farbe} zu wenig "
                        f"ab ({gemessen}:1 statt der empfohlenen "
                        f"{_KONTRAST_MINDESTVERHAELTNIS}:1 im "
                        f"{'hellen' if theme == 'light' else 'dunklen'} Design).",
                        "Eine deutlich hellere oder dunklere Farbe wählen.",
                    )
                )
    befunde.extend(_beschriftung_pruefen(pfm))
    return befunde


#: Grobe Breite je Zeichen und Rand eines Knopfs bei der Standardschrift
#: (9 pt Segoe UI). Die Prüfung läuft ohne Qt und kann nicht messen;
#: geschätzt reicht, um „Verdoppeln“ in einem 75 Pixel breiten Knopf zu
#: erkennen, den die Auswertung zu 0.3.3 abgeschnitten fand.
_ZEICHENBREITE = 7
_KNOPFRAND = 12
_MIT_BESCHRIFTUNG = ("Button", "CheckBox", "RadioButton")


def _beschriftung_pruefen(pfm: dict[str, Any]) -> list[Befund]:
    befunde: list[Befund] = []
    for kind in pfm.get("children", []):
        if kind.get("type") not in _MIT_BESCHRIFTUNG:
            continue
        text = str(_eigenschaft(kind, "caption", "")).replace("&", "")
        _, _, breite, _ = _rechteck(kind)
        noetig = len(text) * _ZEICHENBREITE + _KNOPFRAND
        if text and noetig > breite:
            befunde.append(
                _befund(
                    "lesbarkeit.text_abgeschnitten",
                    "Lesbarkeit",
                    "warnung",
                    kind["name"],
                    f"{kind['name']}: Die Beschriftung „{text}“ ist breiter als "
                    f"die Komponente ({breite} Pixel) und wird abgeschnitten.",
                    f"Die Komponente auf etwa {noetig} Pixel verbreitern oder die "
                    "Beschriftung kürzen.",
                )
            )
    return befunde


def _konsistenz_pruefen(pfm: dict[str, Any]) -> list[Befund]:
    befunde: list[Befund] = []
    kinder = pfm.get("children", [])

    buttons = [k for k in kinder if k["type"] == "Button"]
    if len(buttons) > 1:
        # Über _rechteck() statt direkt über _eigenschaft(): ein Button
        # mit der Standardgröße hat in der .pfm gar keinen
        # "width"/"height"-Schlüssel (Abschnitt 4.2), und mit der
        # Vorbelegung 0 meldete die Regel dann „hat eine andere Größe
        # (0×0)“ – eine Meldung, die den Schüler an die falsche Stelle
        # schickt. In der Sichtprüfung des Panels „Meldungen“ gefunden.
        groessen = [_rechteck(b)[2:] for b in buttons]
        haeufigste = max(set(groessen), key=groessen.count)
        for button, groesse in zip(buttons, groessen, strict=True):
            if groesse != haeufigste:
                befunde.append(
                    _befund(
                        "konsistenz.button_groesse",
                        "Konsistenz",
                        "hinweis",
                        button["name"],
                        f"{button['name']} hat eine andere Größe ({groesse[0]}×{groesse[1]}) "
                        f"als die übrigen Buttons ({haeufigste[0]}×{haeufigste[1]}).",
                        f"Auf {haeufigste[0]}×{haeufigste[1]} angleichen, wenn die "
                        f"Knöpfe gleichrangig sind.",
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
                    _befund(
                        "konsistenz.label_ausrichtung",
                        "Konsistenz",
                        "hinweis",
                        eingabe["name"],
                        f"{naechstes_label['name']} ist nicht mit {eingabe['name']} "
                        "auf gleicher Höhe ausgerichtet.",
                        "Beiden denselben „top“-Wert geben.",
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
                _befund(
                    "bedienbarkeit.klickflaeche",
                    "Bedienbarkeit",
                    "hinweis",
                    kind["name"],
                    f"{kind['name']} ist mit {width}×{height}px kleiner als die "
                    f"empfohlene Mindestklickfläche ({_MINDEST_KLICKFLAECHE}×"
                    f"{_MINDEST_KLICKFLAECHE}px).",
                    f"Auf mindestens {_MINDEST_KLICKFLAECHE}×{_MINDEST_KLICKFLAECHE}px vergrößern.",
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
                _befund(
                    "bedienbarkeit.ohne_beschriftung",
                    "Bedienbarkeit",
                    "hinweis",
                    eingabe["name"],
                    f"{eingabe['name']} hat kein Label in der Nähe.",
                    "Ein Label links daneben oder darüber setzen, damit zu sehen "
                    "ist, was einzutragen ist.",
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
        _befund(
            "bedienbarkeit.tab_reihenfolge",
            "Bedienbarkeit",
            "hinweis",
            None,
            "Die Komponenten stehen nicht in der Lesereihenfolge (oben links nach unten rechts).",
            "In dieser Reihenfolge anlegen - danach springt auch die "
            "Tabulatortaste richtig weiter.",
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
                _befund(
                    "namenskonvention.praefix",
                    "Namenskonvention",
                    "hinweis",
                    name,
                    f"{name} ({typ}) hat nicht das übliche Präfix {praefix!r}.",
                    f"Den Namen mit {praefix!r} beginnen lassen - dann ist im "
                    f"Quelltext zu sehen, um welche Art Komponente es geht.",
                )
            )
        if _STANDARDNAME_MUSTER.fullmatch(name) and name.lower().startswith(typ.lower()):
            befunde.append(
                _befund(
                    "namenskonvention.standardname",
                    "Namenskonvention",
                    "hinweis",
                    name,
                    f"{name} sieht wie ein unveränderter Standardname aus.",
                    "Einen Namen vergeben, der sagt, wofür die Komponente da ist.",
                )
            )
        beschriftung = _eigenschaft(kind, "caption", None)
        if isinstance(beschriftung, str) and re.fullmatch(rf"{re.escape(typ)}\d*", beschriftung):
            befunde.append(
                _befund(
                    "namenskonvention.standardtext",
                    "Namenskonvention",
                    "hinweis",
                    name,
                    f"{name}: Beschriftung {beschriftung!r} sieht wie ein unveränderter "
                    "Standardtext aus.",
                    "Die Beschriftung auf den Text ändern, den man später lesen soll.",
                )
            )
    return befunde
