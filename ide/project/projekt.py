"""Projekt: lädt/speichert `.natter`-Projektdateien.

Siehe README.md, Abschnitt 4.1, 23.2. Die Liste der Units und
Formulare wird aus dem Ordnerinhalt ermittelt statt nur aus der
`.natter` gelesen, weil beim Einbinden einer Unit (Abschnitt 7.4) keine
zusätzliche Eintragung in der Projektdatei vorgesehen ist.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ide.pfade import daten_ordner
from ide.schema import pruefen as schema_pruefen

_SCHEMAS_DIR = daten_ordner("schemas")
_PROJECT_SCHEMA = json.loads((_SCHEMAS_DIR / "project.schema.json").read_text(encoding="utf-8"))


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

        daten = json.loads(pfad.read_text(encoding="utf-8"))
        schema_pruefen(daten, _PROJECT_SCHEMA)
        return cls(ordner=pfad.parent, daten=daten)

    def speichern(self, pfad: Path | None = None) -> None:
        schema_pruefen(self.daten, _PROJECT_SCHEMA)
        ziel = pfad if pfad is not None else self.ordner / f"{self.name}.natter"
        ziel.write_text(
            json.dumps(self.daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
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

    def diagramme(self) -> list[Path]:
        """Alle Diagramme (`.pdiag`) im Unterordner `diagramme/`
        (Abschnitt 13.1 – anders als Formulare/Units liegen sie nicht
        im Projektwurzelordner)."""
        ordner = self.diagramm_ordner
        return sorted(ordner.glob("*.pdiag")) if ordner.is_dir() else []

    @property
    def diagramm_ordner(self) -> Path:
        return self.ordner / "diagramme"
