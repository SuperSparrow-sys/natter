"""Klassen-/Eigenschaftszuordnung `.lfm` → `.pfm` (Abschnitt 15).

Wandelt das Ergebnis von `ide.import_lfm.parser.parse_lfm()` in ein
`.pfm`-kompatibles `dict` um (validierbar gegen
`schemas/pfm.schema.json`).

Umfang, bewusst eingeschränkt (siehe docs/arbeitspakete/M8.md,
Schritt 2): nicht unterstützte Komponenten/Eigenschaften werden nur im
Importbericht vermerkt, nicht als Platzhalter angelegt (es gibt noch
keine generische Platzhalter-Komponente in `pcl`). Container-Komponenten
(`TRadioGroup`, `TGroupBox`, `TPanel`) haben in `pcl` keine Entsprechung;
sie und ihre Kinder landen im Importbericht. `Cells`-Sammlungen eines
`TStringGrid` werden ebenfalls nur gemeldet.

Bilder aus `Picture.Data` werden über `ide.import_lfm.bilder` dekodiert
und im Ergebnis mitgeliefert (`LfmImportErgebnis.bilder`); das Schreiben
nach `assets/` erledigt die aufrufende Stelle. Die Pascal-Rümpfe selbst
liest `ide.import_lfm.pascal`; hier wird nur festgehalten, welcher
Lazarus-Handler zu welcher erzeugten Python-Methode gehört
(`LfmImportErgebnis.handler_quellen`).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import pcl
from ide.import_lfm.bilder import LfmBild, LfmBildFehler, bild_aus_binaerblock
from pcl.properties import VERSCHACHTELTE_EIGENSCHAFTEN

# Klasse in der `.lfm` -> pcl-Komponente. Nur die im Kursmaterial
# (tests/daten/lfm/) tatsächlich verwendeten Typen (siehe
# docs/komponenten.md).
_KLASSEN: dict[str, str] = {
    "TButton": "Button",
    "TLabel": "Label",
    "TEdit": "Edit",
    "TShape": "Shape",
    "TStringGrid": "StringGrid",
    "TCheckBox": "CheckBox",
    "TRadioButton": "RadioButton",
    "TMemo": "Memo",
    "TListBox": "ListBox",
    "TComboBox": "ComboBox",
    "TScrollBar": "ScrollBar",
    "TImage": "Image",
    "TTimer": "Timer",
}

# Formen (TShape.Shape) -> pcl Shape.shape.
_FORMEN: dict[str, str] = {
    "stRectangle": "rectangle",
    "stSquare": "rectangle",
    "stCircle": "circle",
    "stEllipse": "circle",
    "stRoundSquare": "rounded_rectangle",
    "stRoundRect": "rounded_rectangle",
}

# clXxx-Konstanten. clBlack/clGray/clSilver/clYellow kommen tatsächlich
# in tests/daten/lfm/ vor, der Rest ist die übliche Farbpalette für
# zukünftige Importe.
_FARBEN: dict[str, str] = {
    "clBlack": "#000000",
    "clMaroon": "#800000",
    "clGreen": "#008000",
    "clOlive": "#808000",
    "clNavy": "#000080",
    "clPurple": "#800080",
    "clTeal": "#008080",
    "clGray": "#808080",
    "clSilver": "#c0c0c0",
    "clRed": "#ff0000",
    "clLime": "#00ff00",
    "clYellow": "#ffff00",
    "clBlue": "#0000ff",
    "clFuchsia": "#ff00ff",
    "clAqua": "#00ffff",
    "clWhite": "#ffffff",
    "clMoneyGreen": "#c0dcc0",
    "clCream": "#fffbf0",
    "clBtnFace": "#f0f0f0",
    "clWindow": "#ffffff",
}


class LfmZuordnungError(ValueError):
    """Ein Eigenschaftswert konnte nicht umgewandelt werden."""


def _bool_konvertieren(wert: Any) -> bool:
    if isinstance(wert, bool):
        return wert
    if wert in ("True", "true"):
        return True
    if wert in ("False", "false"):
        return False
    raise LfmZuordnungError(f"Kein Wahrheitswert: {wert!r}")


def _farbe_konvertieren(wert: Any) -> str:
    if isinstance(wert, str) and wert.startswith("cl"):
        hex_wert = _FARBEN.get(wert)
        if hex_wert is None:
            raise LfmZuordnungError(f"Unbekannte Farbkonstante: {wert}")
        return hex_wert
    if isinstance(wert, str) and wert.startswith("$"):
        # Lazarus-Hex ist $00BBGGRR: die letzten beiden Ziffern sind Rot,
        # nicht die ersten (umgekehrte Reihenfolge zu #RRGGBB).
        zahl = int(wert[1:], 16)
        r, g, b = zahl & 0xFF, (zahl >> 8) & 0xFF, (zahl >> 16) & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"
    raise LfmZuordnungError(f"Keine erkannte Farbe: {wert!r}")


def _form_konvertieren(wert: Any) -> str:
    if wert not in _FORMEN:
        raise LfmZuordnungError(f"Unbekannte Shape-Form: {wert!r}")
    return _FORMEN[wert]


def _sammlung_konvertieren(wert: Any) -> list[str]:
    """`Items.Strings = ('7' '19')` -> `["7", "19"]` (der Parser liefert
    solche Sammlungen bereits als Liste)."""
    if not isinstance(wert, list) or not all(isinstance(zeile, str) for zeile in wert):
        raise LfmZuordnungError(f"Keine Zeichenkettenliste: {wert!r}")
    return wert


def _schriftgroesse_aus_hoehe(wert: Any) -> int:
    """Lazarus' `Font.Height` ist eine negative Pixelhöhe; `pcl` rechnet
    wie Lazarus' `Font.Size` in Punkt (bei 96 dpi: 1 pt = 4/3 px)."""
    if not isinstance(wert, int):
        raise LfmZuordnungError(f"Keine Schrifthöhe: {wert!r}")
    return round(abs(wert) * 0.75)


# Eigenschaften, die auf mehrere pcl-Eigenschaften zugleich
# abbilden (`Font.Style = [fsBold, fsItalic]` -> `font_bold`/`font_italic`).
_SCHRIFTSTILE: dict[str, str] = {"fsBold": "font_bold", "fsItalic": "font_italic"}


def _schriftstil_konvertieren(wert: Any, name: str, warnungen: list[str]) -> dict[str, bool]:
    stile = wert if isinstance(wert, list) else [wert]
    ergebnis: dict[str, bool] = {}
    for stil in stile:
        pcl_name = _SCHRIFTSTILE.get(stil)
        if pcl_name is None:
            warnungen.append(f"{name}: Schriftstil {stil} wird nicht unterstützt.")
            continue
        ergebnis[pcl_name] = True
    return ergebnis


# Eigenschaft in der `.lfm` -> (pcl-Eigenschaft, Konverter). Klassenunabhängig
# (Namen wie "Caption" bedeuten in jeder Klasse dasselbe pcl-Prop).
_EIGENSCHAFTEN: dict[str, tuple[str, Any]] = {
    "Caption": ("caption", str),
    "Left": ("left", int),
    "Top": ("top", int),
    "Width": ("width", int),
    "Height": ("height", int),
    "Enabled": ("enabled", _bool_konvertieren),
    "Checked": ("checked", _bool_konvertieren),
    "Text": ("text", str),
    "ReadOnly": ("read_only", _bool_konvertieren),
    "ItemIndex": ("item_index", int),
    "RowCount": ("row_count", int),
    "ColCount": ("col_count", int),
    "Color": ("color", _farbe_konvertieren),
    "Brush.Color": ("brush_color", _farbe_konvertieren),
    "Shape": ("shape", _form_konvertieren),
    "Min": ("minimum", int),
    "Max": ("maximum", int),
    "Position": ("position", int),
    "Items.Strings": ("items", _sammlung_konvertieren),
    "Lines.Strings": ("lines", _sammlung_konvertieren),
    "Font.Name": ("font_name", str),
    "Font.Height": ("font_size", _schriftgroesse_aus_hoehe),
    "Font.Size": ("font_size", int),
    "Interval": ("interval", int),
}

_EREIGNISSE: dict[str, str] = {
    "OnClick": "on_click",
    "OnChange": "on_change",
    "OnCreate": "on_create",
    "OnTimer": "on_timer",
}


def _schlange(text: str) -> str:
    """camelCase/PascalCase -> snake_case, idempotent für bereits-snake
    Text (deckt sich mit der bestehenden Namenskonvention im Projekt,
    z. B. `b_einschalten`)."""
    return re.sub(r"(?<!^)(?<!_)(?=[A-Z])", "_", text).lower()


def _handler_konvertieren(ereignis_schluessel: str, handler: str) -> str:
    """`OnClick`/`b_startClick` -> `b_start_click` (der Ereignisname
    hängt direkt am Komponentennamen; das Ergebnis deckt
    sich mit der tatsächlichen Methodenbenennung in den bestehenden
    `beispielprojekte/*/u_main.py`, z. B. `FormCreate` -> `form_create`)."""
    if ereignis_schluessel.startswith("On"):
        suffix = ereignis_schluessel[2:]
    else:
        suffix = ereignis_schluessel
    praefix = handler[: -len(suffix)] if handler.endswith(suffix) else handler
    return f"{_schlange(praefix)}_{suffix.lower()}"


def _eigenschaft_moeglich(pcl_klasse: str, pcl_name: str) -> bool:
    """Ob die Zielkomponente diese Eigenschaft überhaupt besitzt.

    Die Zuordnungstabelle oben ist bewusst klassenunabhängig (`Caption`
    heißt überall `caption`). Ohne diese Prüfung entstand daraus eine
    `.pfm`, die beim Öffnen abstürzt - real passiert mit `TMemo.ReadOnly`
    aus `f_Pizza`: `read_only` gab es nur an `Edit`, und der Designer
    brach mit `NatterUnbekannteEigenschaftError` ab, statt den Import
    einfach im Bericht zu vermerken."""
    klasse = getattr(pcl, pcl_klasse, None)
    if klasse is None:
        return False
    verschachtelt = VERSCHACHTELTE_EIGENSCHAFTEN.get(pcl_name)
    if verschachtelt is not None:
        return hasattr(klasse, verschachtelt.attribut)
    return hasattr(klasse, pcl_name)


@dataclass
class LfmImportErgebnis:
    pfm: dict[str, Any]
    warnungen: list[str] = field(default_factory=list)
    # Python-Methodenname -> Name des Handlers in der `.lfm`/`.pas`
    # (z. B. `"b_start_click"` -> `"b_startClick"`), damit der zugehörige
    # Pascal-Rumpf in der `.pas` gefunden wird.
    handler_quellen: dict[str, str] = field(default_factory=dict)
    # Komponentenname -> ausgepacktes Bild aus `Picture.Data`.
    bilder: dict[str, LfmBild] = field(default_factory=dict)


def lfm_zu_pfm(lfm_objekt: dict[str, Any]) -> LfmImportErgebnis:
    """Wandelt das Ergebnis von `parse_lfm()` in ein `.pfm`-`dict` um."""
    warnungen: list[str] = []
    handler_quellen: dict[str, str] = {}
    bilder: dict[str, LfmBild] = {}
    eigenschaften, ereignisse = _eigenschaften_umwandeln(
        lfm_objekt["properties"],
        warnungen,
        ist_form=True,
        handler_quellen=handler_quellen,
        bilder=bilder,
    )
    pfm: dict[str, Any] = {
        "format": "pfm/1",
        "class": lfm_objekt["name"],
        "type": "Form",
        "properties": eigenschaften,
    }
    if ereignisse:
        pfm["events"] = ereignisse

    kinder = []
    for lfm_kind in lfm_objekt.get("children", []):
        pfm_kind = _kind_umwandeln(lfm_kind, warnungen, handler_quellen, bilder)
        if pfm_kind is not None:
            kinder.append(pfm_kind)
    pfm["children"] = kinder

    return LfmImportErgebnis(
        pfm=pfm, warnungen=warnungen, handler_quellen=handler_quellen, bilder=bilder
    )


def _kind_umwandeln(
    lfm_kind: dict[str, Any],
    warnungen: list[str],
    handler_quellen: dict[str, str],
    bilder: dict[str, LfmBild],
) -> dict[str, Any] | None:
    pcl_klasse = _KLASSEN.get(lfm_kind["class"])
    if pcl_klasse is None:
        warnungen.append(
            f"{lfm_kind['name']}: Komponententyp {lfm_kind['class']} wird nicht "
            "unterstützt, wurde nicht übernommen."
        )
        return None
    eigenschaften, ereignisse = _eigenschaften_umwandeln(
        lfm_kind["properties"],
        warnungen,
        name=lfm_kind["name"],
        pcl_klasse=pcl_klasse,
        handler_quellen=handler_quellen,
        bilder=bilder,
    )
    eintrag: dict[str, Any] = {
        "name": lfm_kind["name"],
        "type": pcl_klasse,
        "properties": eigenschaften,
    }
    if ereignisse:
        eintrag["events"] = ereignisse
    return eintrag


def _bild_uebernehmen(
    wert: Any,
    name: str,
    warnungen: list[str],
    bilder: dict[str, LfmBild] | None,
) -> None:
    """`Picture.Data` auspacken (M8, Schritt 3). Das Schreiben nach
    `assets/` übernimmt die aufrufende Stelle, damit die Zuordnung eine
    reine Datenumwandlung ohne Dateizugriff bleibt."""
    if bilder is None:
        warnungen.append(f"{name}: Eigenschaft Picture.Data wird nicht unterstützt.")
        return
    if not isinstance(wert, dict) or "binaer" not in wert:
        warnungen.append(f"{name}: Picture.Data ist kein Binärblock.")
        return
    try:
        bilder[name] = bild_aus_binaerblock(wert["binaer"])
    except LfmBildFehler as fehler:
        warnungen.append(f"{name}: Picture.Data konnte nicht ausgepackt werden - {fehler}")


def _eigenschaften_umwandeln(
    lfm_eigenschaften: dict[str, Any],
    warnungen: list[str],
    *,
    ist_form: bool = False,
    name: str = "Formular",
    pcl_klasse: str = "Form",
    handler_quellen: dict[str, str] | None = None,
    bilder: dict[str, LfmBild] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    eigenschaften: dict[str, Any] = {}
    ereignisse: dict[str, str] = {}
    for schluessel, wert in lfm_eigenschaften.items():
        if schluessel.startswith("On"):
            ereignis_name = _EREIGNISSE.get(schluessel)
            if ereignis_name is None:
                warnungen.append(f"{name}: Ereignis {schluessel} wird nicht unterstützt.")
                continue
            methodenname = _handler_konvertieren(schluessel, wert)
            ereignisse[ereignis_name] = methodenname
            if handler_quellen is not None and isinstance(wert, str):
                handler_quellen[methodenname] = wert
            continue
        if schluessel == "Picture.Data":
            _bild_uebernehmen(wert, name, warnungen, bilder)
            continue
        if ist_form and schluessel in ("Left", "Top"):
            continue  # Formulare haben in pcl keine left/top-Prop
        if schluessel == "Font.Style":
            stile = _schriftstil_konvertieren(wert, name, warnungen)
            eigenschaften.update(
                {
                    stil_name: stil_wert
                    for stil_name, stil_wert in stile.items()
                    if _eigenschaft_moeglich(pcl_klasse, stil_name)
                }
            )
            continue
        zuordnung = _EIGENSCHAFTEN.get(schluessel)
        if zuordnung is None:
            warnungen.append(f"{name}: Eigenschaft {schluessel} wird nicht unterstützt.")
            continue
        pcl_name, konverter = zuordnung
        if not _eigenschaft_moeglich(pcl_klasse, pcl_name):
            warnungen.append(
                f"{name}: Eigenschaft {schluessel} gibt es bei {pcl_klasse} nicht."
            )
            continue
        try:
            eigenschaften[pcl_name] = konverter(wert)
        except LfmZuordnungError as fehler:
            warnungen.append(f"{name}: {schluessel} = {wert!r} - {fehler}")
    return eigenschaften, ereignisse
