"""Erzeugt die Formular-Unit (`u_main.py`) zu einem importierten
Lazarus-Formular (Abschnitt 15, docs/arbeitspakete/M8.md, Schritt 3).

Die `.lfm` nennt nur die Namen der Ereignis-Handler; der Pascal-Code
steht in der gleichnamigen `.pas`. Diese Unit legt für jeden Handler
eine leere Python-Methode an und schreibt den zugehörigen Pascal-Rumpf
als Kommentar darüber – bewusst keine automatische Übersetzung nach
Python (Abschnitt 15: der Import ist Umstiegshilfe, das Übersetzen ist
die eigentliche Unterrichtsaufgabe).

Bilder aus `Picture.Data` liegen nach dem Import als Dateien in
`assets/`. Weil die `.pfm` die Eigenschaft `picture` (noch) nicht
speichern kann, setzt die erzeugte Unit sie in einer
`create_components()`-Erweiterung im Code – damit zeigt das gestartete
Programm die Bilder wirklich an.
"""

from __future__ import annotations

from typing import Any

from ide.import_lfm.pascal import rumpf_als_kommentar

_EINRUECKUNG = "    "


def _handler_namen(pfm: dict[str, Any]) -> list[str]:
    """Alle in der `.pfm` referenzierten Handler-Methoden, Formular
    zuerst, danach die Kinder in Reihenfolge – ohne Doppelte."""
    namen: list[str] = []
    for handler in pfm.get("events", {}).values():
        if handler not in namen:
            namen.append(handler)
    for kind in pfm.get("children", []):
        for handler in kind.get("events", {}).values():
            if handler not in namen:
                namen.append(handler)
    return namen


def _bilder_zeilen(bild_pfade: dict[str, str]) -> list[str]:
    zeilen = [
        f"{_EINRUECKUNG}def create_components(self):",
        f"{_EINRUECKUNG * 2}super().create_components()",
        f"{_EINRUECKUNG * 2}# Bilder aus dem Lazarus-Import (Picture.Data), nach assets/",
        f"{_EINRUECKUNG * 2}# ausgepackt. Die .pfm speichert die Eigenschaft `picture` noch",
        f"{_EINRUECKUNG * 2}# nicht, deshalb steht die Zuweisung hier im Code.",
    ]
    for komponente, pfad in bild_pfade.items():
        zeilen.append(f'{_EINRUECKUNG * 2}self.{komponente}.picture.load_from_file("{pfad}")')
    return zeilen


def unit_quelltext_erzeugen(
    pfm: dict[str, Any],
    *,
    design_modul: str,
    pascal_ruempfe: dict[str, list[str]] | None = None,
    handler_quellen: dict[str, str] | None = None,
    pas_dateiname: str = "",
    bild_pfade: dict[str, str] | None = None,
) -> str:
    """Erzeugt den Quelltext der Formular-Unit.

    `pascal_ruempfe` sind die Rümpfe aus `pascal.prozedur_ruempfe_lesen()`
    (Schlüssel: Lazarus-Methodenname), `handler_quellen` die Zuordnung
    Python-Methodenname → Lazarus-Methodenname aus
    `zuordnung.lfm_zu_pfm()`. Fehlt beides, entstehen leere Methoden."""
    pascal_ruempfe = pascal_ruempfe or {}
    handler_quellen = handler_quellen or {}
    bild_pfade = bild_pfade or {}

    klassenname = pfm["class"]
    zeilen: list[str] = [
        f"from {design_modul} import {klassenname}Design",
        "",
        "",
        f"class {klassenname}({klassenname}Design):",
    ]

    bloecke: list[list[str]] = []
    if bild_pfade:
        bloecke.append(_bilder_zeilen(bild_pfade))

    for methodenname in _handler_namen(pfm):
        block = [f"{_EINRUECKUNG}def {methodenname}(self, sender):"]
        lazarus_name = handler_quellen.get(methodenname, "")
        rumpf = pascal_ruempfe.get(lazarus_name)
        if rumpf:
            herkunft = f" aus {pas_dateiname}" if pas_dateiname else ""
            block.append(
                f"{_EINRUECKUNG * 2}# Pascal-Rumpf von {lazarus_name}{herkunft} (Lazarus-Import),"
            )
            block.append(f"{_EINRUECKUNG * 2}# bitte nach Python übersetzen:")
            block.extend(rumpf_als_kommentar(rumpf, einrueckung=_EINRUECKUNG * 2))
        block.append(f"{_EINRUECKUNG * 2}pass")
        bloecke.append(block)

    if not bloecke:
        zeilen.append(f"{_EINRUECKUNG}pass")
    for nummer, block in enumerate(bloecke):
        if nummer:
            zeilen.append("")
        zeilen.extend(block)

    return "\n".join(zeilen) + "\n"
