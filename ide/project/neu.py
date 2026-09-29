"""Neu-Dialog: „Neues Projekt …“ (Abschnitt 7.5).

Erzeugt ein neues, leeres Projekt aus einer Vorlage in `templates/`:
`gui` für ein Programm mit Fenster, `console` für eines mit `print()`
und `input()`. Eine Datenbank braucht keinen eigenen Projekttyp; sie
ist eine Zeile Code (`SQLite3Connection("daten.sqlite")`).

Jedes Projekt bekommt beides: `main.py` und `u_main.py` – auch ein
Konsolenprojekt. `main.py` startet nur, `u_main.py` trägt den Code der
Schülerin. Der Grundsatz stammt vom Nutzer : „Main.py
ist nur dafür da um das Script zu starten. Alles was programmiert
werden muss passiert in u_main.py … denn Schüler sollen nicht in die
Main py schauen aber ja trotzdem Code schreiben."

Bis dahin hatte ein Konsolenprojekt nur `main.py`, und der ganze
Schülercode stand darin. Damit stand die Startdatei zugleich auf der
Liste der ausgeblendeten Dateien und auf der des Quelltexts – ein
Widerspruch, der die ersten beiden Lehrgangsstufen mit einem leeren
Projekt-Explorer öffnen ließ.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ide.atomar import atomar_schreiben
from ide.codegen.design import design_datei_erzeugen
from ide.pfade import daten_ordner
from ide.project.projekt import Projekt

#: `daten_ordner` statt eines eigenen relativen Pfads: wo die
#: mitgelieferten Ordner liegen, steht an einer einzigen Stelle. Bis
#: M12 stand hier ein relativer Pfad, der im damaligen Bundle nicht
#: stimmte - in der installierten Natter endete „Neues Projekt …“ in
#: einem FileNotFoundError, es ließ sich überhaupt kein Projekt anlegen.
_TEMPLATES_DIR = daten_ordner("templates")

VORLAGEN = ("gui", "console")

#: Zeichen, die Windows in Datei- und Ordnernamen nicht zulässt.
#: Schrägstrich und Rückstrich gehören dazu; mit ihnen würde aus dem
#: Namen ein verschachtelter Pfad.
_VERBOTENE_ZEICHEN = '<>:"/\\|?*'

#: Gerätenamen, die Windows als Datei- oder Ordnernamen nicht
#: annimmt, auch nicht mit Endung.
_RESERVIERTE_NAMEN = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def name_pruefen(name: str) -> str | None:
    """Prüft einen Projektnamen, bevor daraus ein Ordner wird. Gibt
    einen deutschen Hinweis zurück, wenn der Name nicht geht, sonst
    `None`."""
    if not name.strip():
        return "Der Projektname fehlt."
    verboten = sorted({z for z in name if z in _VERBOTENE_ZEICHEN})
    if verboten:
        zeichen = " ".join(verboten)
        return (
            f"Der Projektname darf diese Zeichen nicht enthalten: {zeichen}"
        )
    if any(ord(z) < 32 for z in name):
        return "Der Projektname enthält ein Steuerzeichen."
    if name.endswith((".", " ")):
        return (
            "Der Projektname darf nicht mit einem Punkt oder einem "
            "Leerzeichen enden."
        )
    if name.split(".")[0].strip().upper() in _RESERVIERTE_NAMEN:
        return (
            f"„{name}“ ist unter Windows als Name reserviert und lässt "
            f"sich nicht als Ordner anlegen."
        )
    return None


def _vorlagendatei_rendern(vorlagenordner: Path, dateiname: str, name: str) -> str:
    text = (vorlagenordner / f"{dateiname}.template").read_text(encoding="utf-8")
    # Der Name steht in den Vorlagen innerhalb von Anführungszeichen,
    # in JSON ("name": "{{name}}") wie in Python (print("…")). Die
    # JSON-Maskierung ist auch in einer Python-Zeichenkette gültig, ein
    # Anführungszeichen oder Rückstrich im Namen zerbricht so keine der
    # beiden Dateien.
    maskiert = json.dumps(name, ensure_ascii=False)[1:-1]
    return text.replace("{{name}}", maskiert)


def projekt_erzeugen(vorlage: str, zielordner: Path, name: str) -> Projekt:
    """Erzeugt ein neues Projekt aus einer Vorlage in `zielordner` (muss
    leer sein oder noch nicht existieren) und lädt es."""
    if vorlage not in VORLAGEN:
        raise ValueError(f"Unbekannte Vorlage {vorlage!r}, erwartet: {', '.join(VORLAGEN)}.")

    hinweis = name_pruefen(name)
    if hinweis is not None:
        raise ValueError(hinweis)

    neu_angelegt = not zielordner.exists()
    zielordner.mkdir(parents=True, exist_ok=True)
    if any(zielordner.iterdir()):
        raise FileExistsError(f"{zielordner} ist nicht leer.")

    try:
        _dateien_schreiben(vorlage, zielordner, name)
    except OSError:
        # Ein halb angelegtes Projekt ließe sich weder öffnen noch unter
        # demselben Namen neu anlegen, weil der Ordner nicht leer ist.
        if neu_angelegt:
            shutil.rmtree(zielordner, ignore_errors=True)
        raise

    return Projekt.laden(zielordner)


def _dateien_schreiben(vorlage: str, zielordner: Path, name: str) -> None:
    vorlagenordner = _TEMPLATES_DIR / vorlage

    natter_text = _vorlagendatei_rendern(vorlagenordner, "project.natter", name)
    atomar_schreiben(zielordner / f"{name}.natter", natter_text, encoding="utf-8")

    main_text = _vorlagendatei_rendern(vorlagenordner, "main.py", name)
    atomar_schreiben(zielordner / "main.py", main_text, encoding="utf-8")

    u_main_text = _vorlagendatei_rendern(vorlagenordner, "u_main.py", name)
    atomar_schreiben(zielordner / "u_main.py", u_main_text, encoding="utf-8")

    if vorlage == "gui":
        pfm_text = _vorlagendatei_rendern(vorlagenordner, "u_main.pfm", name)
        pfm_pfad = zielordner / "u_main.pfm"
        atomar_schreiben(pfm_pfad, pfm_text, encoding="utf-8")

        design_datei_erzeugen(pfm_pfad, zielordner / "u_main_design.py")
