"""Neu-Dialog: „Neues Projekt …“ (Abschnitt 7.5).

Erzeugt ein neues, leeres Projekt aus einer Vorlage in `templates/`.
`gui_db` (GUI-Anwendung mit Datenbank) folgt später zusammen mit den
SQLdb-Komponenten (M5).
"""

from __future__ import annotations

from pathlib import Path

from ide.codegen.design import design_datei_erzeugen
from ide.pfade import daten_ordner
from ide.project.projekt import Projekt

#: `daten_ordner` statt eines quellcode-relativen Pfads: in der gebauten
#: Exe liegt `templates/` im Bundle-Ordner, nicht drei Ebenen über
#: dieser Datei. Bis M12 stand hier der relative Pfad - in der
#: installierten Natter endete „Neues Projekt …“ deshalb in einem
#: FileNotFoundError, es ließ sich überhaupt kein Projekt anlegen.
_TEMPLATES_DIR = daten_ordner("templates")

VORLAGEN = ("gui", "console")


def _vorlagendatei_rendern(vorlagenordner: Path, dateiname: str, name: str) -> str:
    text = (vorlagenordner / f"{dateiname}.template").read_text(encoding="utf-8")
    return text.replace("{{name}}", name)


def projekt_erzeugen(vorlage: str, zielordner: Path, name: str) -> Projekt:
    """Erzeugt ein neues Projekt aus einer Vorlage in `zielordner` (muss
    leer sein oder noch nicht existieren) und lädt es."""
    if vorlage not in VORLAGEN:
        raise ValueError(f"Unbekannte Vorlage {vorlage!r}, erwartet: {', '.join(VORLAGEN)}.")

    zielordner.mkdir(parents=True, exist_ok=True)
    if any(zielordner.iterdir()):
        raise FileExistsError(f"{zielordner} ist nicht leer.")

    vorlagenordner = _TEMPLATES_DIR / vorlage

    natter_text = _vorlagendatei_rendern(vorlagenordner, "project.natter", name)
    (zielordner / f"{name}.natter").write_text(natter_text, encoding="utf-8")

    main_text = _vorlagendatei_rendern(vorlagenordner, "main.py", name)
    (zielordner / "main.py").write_text(main_text, encoding="utf-8")

    if vorlage == "gui":
        pfm_text = _vorlagendatei_rendern(vorlagenordner, "u_main.pfm", name)
        pfm_pfad = zielordner / "u_main.pfm"
        pfm_pfad.write_text(pfm_text, encoding="utf-8")

        design_datei_erzeugen(pfm_pfad, zielordner / "u_main_design.py")

        u_main_text = (vorlagenordner / "u_main.py.template").read_text(encoding="utf-8")
        (zielordner / "u_main.py").write_text(u_main_text, encoding="utf-8")

    return Projekt.laden(zielordner)
