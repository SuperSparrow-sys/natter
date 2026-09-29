"""Projekt: lädt/speichert `.natter`-Projektdateien.

Siehe README.md, Abschnitt 4.1, 23.2. Die Liste der Units und
Formulare wird aus dem Ordnerinhalt ermittelt statt nur aus der
`.natter` gelesen, weil beim Einbinden einer Unit (Abschnitt 7.4) keine
zusätzliche Eintragung in der Projektdatei vorgesehen ist.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ide.atomar import atomar_schreiben
from ide.pfade import daten_ordner
from ide.project.sicherung import ENDUNG as SICHERUNG_ENDUNG
from ide.schema import json_datei_lesen
from ide.schema import pruefen as schema_pruefen

_SCHEMAS_DIR = daten_ordner("schemas")
_PROJECT_SCHEMA = json.loads((_SCHEMAS_DIR / "project.schema.json").read_text(encoding="utf-8"))


_GESTRICHENER_EXPORT = {"product_name", "version", "include_data_dir", "target"}


def _alte_angaben_angleichen(daten: Any) -> Any:
    """Liest eine Projektdatei aus der Zeit vor Punkt 83.

    Damals kannte das Schema noch den Projekttyp `gui_db` und bei der
    Datenbank den Treiber `mysql` samt `connection_ref`. Beides ist
    gestrichen; eine alte Datei soll sich trotzdem öffnen lassen. Aus
    `gui_db` wird `gui` - es war ein Programm mit Fenster -, und eine
    Datenbankangabe, die es so nicht mehr gibt, fällt weg. Geschrieben
    wird die Datei dabei nicht; das geschieht erst beim nächsten
    Speichern.

    Ebenso gestrichen sind die Export-Angaben `product_name`,
    `version`, `include_data_dir` und `target` (Punkt 206). Der Export
    hat sie nie gelesen; eine Datei, in der sie noch stehen, lässt sich
    weiter öffnen, die Angaben fallen weg.
    """
    if not isinstance(daten, dict):
        return daten
    daten = dict(daten)
    if daten.get("type") == "gui_db":
        daten["type"] = "gui"
    datenbank = daten.get("database")
    if isinstance(datenbank, dict):
        if datenbank.get("driver") != "sqlite3":
            del daten["database"]
        elif "connection_ref" in datenbank:
            daten["database"] = {
                name: wert for name, wert in datenbank.items() if name != "connection_ref"
            }
    export = daten.get("export")
    if isinstance(export, dict):
        daten["export"] = {
            name: wert for name, wert in export.items() if name not in _GESTRICHENER_EXPORT
        }
    return daten


class ProjektdateiUngueltig(ValueError):
    """Eine `.natter`, deren Namen oder Pfade aus dem Projektordner
    hinausführen. Die Meldung ist deutsch und für die Oberfläche
    gedacht."""


#: Was in einem Dateinamen unter Windows nicht stehen darf, dazu die
#: beiden Pfadtrenner. Dieselbe Regel steht als `pattern` im Schema.
_NICHT_IM_DATEINAMEN = frozenset('<>:"/\\|?*')


def ist_reiner_dateiname(text: object) -> bool:
    """Ob `text` ein einzelner Dateiname ist, der im Ordner bleibt, in
    den er eingesetzt wird: kein Pfadtrenner, kein Laufwerk, weder `.`
    noch `..`, kein Steuerzeichen und kein Punkt oder Leerzeichen am
    Ende, das Windows stillschweigend abschneidet."""
    if not isinstance(text, str) or not text:
        return False
    if text[-1] in ". ":
        return False
    return not any(
        zeichen in _NICHT_IM_DATEINAMEN or ord(zeichen) < 32
        for zeichen in text
    )


def _namen_pruefen(daten: Any) -> None:
    """Lehnt eine Projektdatei ab, deren `name`, `main` oder
    `main_form` kein reiner Dateiname ist (Punkt 250).

    Der Name wird zum Dateinamen der `.natter` und der Exe, `main` und
    `main_form` zu Pfaden im Projektordner. Mit `..\\` oder einem
    absoluten Pfad zeigten sie vorher auf Dateien außerhalb des
    Projekts, die der Exe-Export dort schrieb, signierte oder beim
    Aufräumen löschte. Andere Typen als Text überlässt diese Prüfung
    dem Schema.
    """
    if not isinstance(daten, dict):
        return
    for schluessel, was in (
        ("name", "Der Projektname"),
        ("main", "Die Startdatei"),
        ("main_form", "Das Hauptformular"),
    ):
        wert = daten.get(schluessel)
        if not isinstance(wert, str):
            continue
        if schluessel == "main_form" and wert == "":
            continue
        if not ist_reiner_dateiname(wert):
            raise ProjektdateiUngueltig(
                f"{was} „{wert}“ ist kein einfacher Dateiname im "
                "Projektordner. Pfadangaben wie „..\\“ oder ein "
                "Laufwerk sind darin nicht erlaubt."
            )


def ist_verknuepfung(pfad: Path) -> bool:
    """Ob `pfad` eine symbolische Verknüpfung oder eine
    Verzeichnisverknüpfung (Junction) ist. Im Zweifel, wenn sich das
    nicht feststellen lässt, ja."""
    try:
        return pfad.is_symlink() or pfad.is_junction()
    except OSError:
        return True


def _durchlaufen(ordner: Path) -> tuple[list[Path], bool]:
    """Die Dateien unter `ordner` und ob dabei Verknüpfungen übergangen
    wurden (Punkt 252).

    `Path.rglob` und `os.walk` folgen unter Windows einer Junction wie
    einem gewöhnlichen Ordner, und eine Junction lässt sich ohne
    Verwaltungsrechte anlegen. Zeigte eine im Projektordner auf einen
    fremden Ordner, landeten dessen Dateien in der ZIP und im
    Explorer; zeigte sie auf den Projektordner selbst, lief die Suche
    im Kreis, bis die Pfade zu lang wurden. Deshalb wird hier keine
    Verknüpfung betreten und keine verknüpfte Datei aufgenommen.
    """
    dateien: list[Path] = []
    uebergangen = False
    for wurzel, ordnernamen, dateinamen in os.walk(ordner):
        basis = Path(wurzel)
        behalten = []
        for name in sorted(ordnernamen):
            if ist_verknuepfung(basis / name):
                uebergangen = True
            else:
                behalten.append(name)
        ordnernamen[:] = behalten
        for name in sorted(dateinamen):
            pfad = basis / name
            if ist_verknuepfung(pfad):
                uebergangen = True
            else:
                dateien.append(pfad)
    return dateien, uebergangen


def dateien_im_ordner(ordner: Path) -> list[Path]:
    """Alle Dateien unter `ordner`, auch in Unterordnern, ohne einer
    Verknüpfung oder Junction zu folgen."""
    return _durchlaufen(Path(ordner))[0]


def enthaelt_verknuepfung(ordner: Path) -> bool:
    """Ob unter `ordner` eine Verknüpfung oder Junction liegt."""
    return _durchlaufen(Path(ordner))[1]


@dataclass
class Projekt:
    ordner: Path
    daten: dict[str, Any]

    @property
    def name(self) -> str:
        return self.daten["name"]

    @property
    def typ(self) -> str:
        return self.daten["type"]

    @property
    def haupt_datei(self) -> Path:
        return self.ordner / self.daten["main"]

    @property
    def haupt_unit(self) -> str | None:
        """Die Unit, die das Programm trägt – ohne `.py`.

        Bei einem GUI-Projekt das Hauptformular aus der `.natter`, bei
        einem Konsolenprojekt immer `u_main`: dort steht kein
        `main_form` in der Projektdatei, aber `main.py` importiert
        genau diesen Namen. Sie umzubenennen oder zu löschen hieße,
        das Projekt unstartbar zu machen - der Explorer bietet für sie
        deshalb kein „Umbenennen …"/„Löschen …" an."""
        if self.typ == "console":
            return "u_main"
        return self.daten.get("main_form")

    @classmethod
    def laden(cls, pfad: Path) -> Projekt:
        """`pfad` ist entweder die `.natter`-Datei selbst oder ihr
        Ordner (dann wird die erste `.natter`-Datei darin verwendet)."""
        if pfad.is_dir():
            kandidaten = sorted(pfad.glob("*.natter"))
            if not kandidaten:
                raise FileNotFoundError(f"Keine .natter-Datei in {pfad} gefunden.")
            pfad = kandidaten[0]

        daten = _alte_angaben_angleichen(json_datei_lesen(pfad))
        _namen_pruefen(daten)
        schema_pruefen(daten, _PROJECT_SCHEMA)
        return cls(ordner=pfad.parent, daten=daten)

    def speichern(self, pfad: Path | None = None) -> None:
        _namen_pruefen(self.daten)
        schema_pruefen(self.daten, _PROJECT_SCHEMA)
        ziel = pfad if pfad is not None else self.ordner / f"{self.name}.natter"
        atomar_schreiben(
            ziel,
            json.dumps(self.daten, indent=2, ensure_ascii=False) + "\n",
        )

    def units(self) -> list[Path]:
        """Die Units, an denen gearbeitet wird.

 Ohne die automatisch erzeugten `*_design.py` (Abschnitt 4.1:
 nicht bearbeiten) und ohne die Startdatei (`main`): die schreibt
 Natter beim Anlegen, danach ändert sie niemand mehr (M12).

 Das gilt für jeden Projekttyp, auch für Konsolenprojekte. Dort stand der
 ganze Schülercode früher in `main.py` selbst - die Startdatei war damit
 zugleich ausgeblendet und der einzige Quelltext, und die ersten beiden
 Lehrgangsstufen öffneten sich mit einem völlig leeren Projekt-Explorer.
 Die Antwort darauf ist nicht, die Startdatei zu zeigen, sondern dass
 auch ein Konsolenprojekt eine `u_main.py` hat (Gewünscht: „Jedes Projekt
 braucht eine Main um zu starten und eine u_main wo der Schüler Code drin
 steht"). `main.py` ist überall nur der Starter.

 Für Namenskollisionen ist `alle_python_dateien` gemeint, nicht
 diese Liste - sonst ließe sich eine Unit auf den Namen der
 Startdatei umbenennen und diese damit überschreiben."""
        versteckt = {self.haupt_datei.name}
        return sorted(
            p
            for p in self.ordner.glob("*.py")
            if not p.name.endswith("_design.py") and p.name not in versteckt
        )

    def alle_python_dateien(self) -> list[Path]:
        """Jede `.py` im Projektordner, auch die erzeugten und die
        Startdatei - für Namensprüfungen."""
        return sorted(self.ordner.glob("*.py"))

    def formulare(self) -> list[Path]:
        """Alle Formularbeschreibungen (`.pfm`) im Projektordner."""
        return sorted(self.ordner.glob("*.pfm"))

    def zusammengehoerige_dateien(self, pfad: Path) -> list[Path]:
        """Alle Dateien, die zu `pfad` gehören - die sichtbare und die
 im Hintergrund erzeugten.

 Eine Unit mit Formular besteht aus drei Dateien, von denen eine
 Schülerin nur zwei zu sehen bekommt: `u_ampel.py` (ihr Code),
 `u_ampel.pfm` (das Formular) und `u_ampel_design.py` (erzeugt,
 deshalb im Explorer ausgeblendet). Wer die Unit löscht, meint
 alle drei - bliebe die erzeugte Datei liegen, stünde im
 Projektordner Code zu einem Formular, das es nicht mehr gibt.

 Grundsatz des Nutzers : hinzugefügt wird in den
 Dateien, die man sieht; alles Übrige führt Natter im
 Hintergrund nach - „und der Rest muss automatisch hinzugefügt
 und gelöscht werden in den anderen Dateien im Hintergrund".
 """
        pfad = Path(pfad)
        stamm = pfad.stem
        if pfad.suffix == ".py" and stamm.endswith("_design"):
            stamm = stamm[: -len("_design")]

        kandidaten = [
            self.ordner / f"{stamm}.py",
            self.ordner / f"{stamm}.pfm",
            self.ordner / f"{stamm}_design.py",
        ]
        # `pfad` selbst immer mit - auch wenn es etwas ist, das nicht in
        # dieses Namensschema passt.
        gefunden = [p for p in kandidaten if p.exists()]
        if pfad.exists() and pfad not in gefunden:
            gefunden.append(pfad)
        return sorted(gefunden)

    def weitere_dateien(self) -> list[Path]:
        """Dateien des Projekts, die weder Unit noch Formular noch
        Diagramm sind - Daten, Texte, Bilder, Datenbanken (Punkt 104).
        Auch aus Unterordnern wie `daten/` oder `bilder/`. Was Natter
        selbst erzeugt oder verwaltet, fehlt: Python-Dateien, `.pfm`,
        `.pdiag`, die Projektdatei und Zwischenablagen wie
        `__pycache__`. Verknüpfungen und Junctions werden nicht
        betreten (Punkt 252). Die Sicherung ungespeicherter Änderungen
        fehlt ebenfalls (Punkt 344)."""
        ausgelassen = {
            ".py", ".pyc", ".pfm", ".pdiag", ".natter", SICHERUNG_ENDUNG
        }
        ergebnis = []
        for pfad in dateien_im_ordner(self.ordner):
            teile = pfad.relative_to(self.ordner).parts
            if any(t.startswith((".", "__")) or t in ("build", "dist") for t in teile):
                continue
            if pfad.is_file() and pfad.suffix.lower() not in ausgelassen:
                ergebnis.append(pfad)
        return sorted(ergebnis, key=lambda p: str(p.relative_to(self.ordner)).lower())

    def diagramme(self) -> list[Path]:
        """Alle Diagramme (`.pdiag`) im Unterordner `diagramme/`
        (Abschnitt 13.1 – anders als Formulare/Units liegen sie nicht
        im Projektwurzelordner)."""
        ordner = self.diagramm_ordner
        return sorted(ordner.glob("*.pdiag")) if ordner.is_dir() else []

    @property
    def diagramm_ordner(self) -> Path:
        return self.ordner / "diagramme"
