"""Die neun Beispielprojekte als Lehrgang (M14).

Auftrag des Nutzers : „schreibe nun für das Projekt die
Beispiele, indem du von vorne nach hinten immer kompliziertere Dinge
machst, als eine Art Einführung in die Programmierung. Am Schluss dann
Regression und davor CSV, davor GUI und am Anfang nur Konsole."
Dazu: mehr SQL, Bilder-Import, der ausgebaute Cookie-Klicker und zum
Schluss ein Random Forest.

Aus einer losen Sammlung von elf Beispielen ist damit eine Reihenfolge
geworden. Diese Reihenfolge ist kein Beiwerk, sondern der Inhalt: jede
Stufe bringt genau eine neue Idee dazu, und die Nummer im Ordnernamen
macht das im Explorer und auf dem Startbild sichtbar.

Geprüft wird hier, was ein Lehrgang nicht verlieren darf: dass es alle
Stufen gibt, dass sie in der gedachten Reihenfolge schwieriger werden,
dass jedes Projekt wirklich startet - und dass die erzeugten
Hintergrunddateien zu den Formularen passen. Das Letzte ist die
häufigste Art, wie ein Beispielprojekt still kaputtgeht: jemand ändert
das Formular und vergisst, die `u_main_design.py` neu erzeugen zu
lassen.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PySide6.QtCore import Qt

from ide.codegen.design import design_code_erzeugen
from ide.project.projekt import Projekt

BEISPIELE = Path(__file__).resolve().parent.parent / "beispielprojekte"

#: Der Lehrgang in der gedachten Reihenfolge: Ordner, Art, und was auf
#: dieser Stufe neu dazukommt.
LEHRGANG = [
    ("01_Begruessung", "console", "Ein- und Ausgabe, Variablen"),
    ("02_Zahlenraten", "console", "Verzweigung, Schleife, Zufall"),
    ("03_Taschenrechner", "gui", "Formular, Knopf, Ereignis"),
    ("04_CookieKlicker", "gui", "Bilder, Zeitgeber, Spielstand"),
    ("05_Bildergalerie", "gui", "Dateien von der Festplatte holen"),
    ("06_Kontoverwaltung", "gui", "eigene Klassen und eine SQL-Datenbank"),
    ("07_CsvAuswertung", "gui", "CSV lesen und schreiben, auswerten"),
    ("08_Regression", "gui", "aus Daten eine Regel ableiten"),
    ("09_ObstSortierer", "gui", "Random Forest mit scikit-learn"),
]

NAMEN = [name for name, _, _ in LEHRGANG]
GUI_PROJEKTE = [name for name, art, _ in LEHRGANG if art == "gui"]


def test_es_gibt_genau_diese_neun_projekte() -> None:
    """Kein Rest aus der alten, ungeordneten Sammlung."""
    vorhanden = sorted(p.name for p in BEISPIELE.iterdir() if p.is_dir())

    assert vorhanden == NAMEN


def test_die_nummerierung_gibt_die_reihenfolge_vor() -> None:
    """Alphabetisch sortiert ist auch didaktisch sortiert - darauf
    verlassen sich Explorer und Startbild, die beide nur sortieren."""
    assert sorted(NAMEN) == NAMEN


def test_am_anfang_steht_die_konsole_am_ende_die_oberflaeche() -> None:
    """Zwei Konsolenprojekte zum Einstieg, danach nur noch Oberfläche -
    genau so hat der Nutzer es vorgegeben."""
    arten = [art for _, art, _ in LEHRGANG]

    assert arten[:2] == ["console", "console"]
    assert set(arten[2:]) == {"gui"}


def test_die_schwierigen_themen_stehen_hinten() -> None:
    """CSV vor Regression, Regression vor maschinellem Lernen."""
    assert NAMEN.index("07_CsvAuswertung") < NAMEN.index("08_Regression")
    assert NAMEN.index("08_Regression") < NAMEN.index("09_ObstSortierer")


@pytest.mark.parametrize(("name", "art", "_neu"), LEHRGANG, ids=NAMEN)
def test_das_projekt_laesst_sich_laden(name: str, art: str, _neu: str) -> None:
    projekt = Projekt.laden(BEISPIELE / name)

    assert projekt.name == name
    assert projekt.typ == art
    assert projekt.haupt_datei.is_file()


@pytest.mark.parametrize("name", NAMEN)
def test_jede_datei_ist_gueltiges_python(name: str) -> None:
    """Ein Beispiel, das nicht einmal übersetzt, ist schlimmer als
    keins - der Anfänger sucht den Fehler bei sich."""
    for datei in sorted((BEISPIELE / name).glob("*.py")):
        quelltext = datei.read_text(encoding="utf-8")
        compile(quelltext, str(datei), "exec")


@pytest.mark.parametrize("name", GUI_PROJEKTE)
def test_die_erzeugte_design_datei_passt_zum_formular(name: str) -> None:
    """Der häufigste stille Schaden: das Formular wird geändert, die
    erzeugte Datei bleibt stehen. Im Designer sieht dann alles richtig
    aus, das laufende Programm zeigt aber den alten Stand."""
    ordner = BEISPIELE / name
    pfm = ordner / "u_main.pfm"
    erzeugt = (ordner / "u_main_design.py").read_text(encoding="utf-8")

    erwartet = design_code_erzeugen(json.loads(pfm.read_text(encoding="utf-8")), pfm.name)

    assert erzeugt == erwartet, (
        f"{name}: u_main_design.py ist nicht mehr auf dem Stand von u_main.pfm. "
        f"Einmal im Designer speichern erzeugt sie neu."
    )


@pytest.mark.parametrize("name", GUI_PROJEKTE)
def test_das_formular_laesst_sich_wirklich_oeffnen(name: str, qtbot, monkeypatch, tmp_path) -> None:
    """Der eigentliche Beweis: das Projekt wird gestartet wie durch F9,
    nur ohne Fenster. Ein Beispiel, das beim Öffnen abstürzt, fällt hier
    auf und nicht erst im Unterricht.

    Gearbeitet wird auf einer Kopie (AGENTS.md: eingecheckte
    Beispiele nie im Test verändern). Das ist hier nicht nur Form:
    `06_Kontoverwaltung` legt beim Öffnen seine `konten.sqlite` an, und
    die hätte sonst im Repository gelegen.
    """
    import shutil
    import sys

    ordner = tmp_path / name
    shutil.copytree(BEISPIELE / name, ordner, ignore=shutil.ignore_patterns("__pycache__"))
    monkeypatch.chdir(ordner)
    monkeypatch.syspath_prepend(str(ordner))
    # Die Module heißen in jedem Projekt gleich - eine Fassung aus einem
    # vorherigen Durchlauf würde sonst gewinnen.
    for modul in ("u_main", "u_main_design", "u_konto"):
        monkeypatch.delitem(sys.modules, modul, raising=False)

    import u_main

    formular = u_main.Form1()
    qtbot.addWidget(formular._qwidget)

    assert formular._qwidget is not None


@pytest.mark.parametrize("name", NAMEN)
def test_jedes_projekt_erklaert_seine_stufe(name: str) -> None:
    """Oben in der Datei, die der Schüler zuerst öffnet, steht, um die
    wievielte Stufe es geht und was neu ist. Ohne diesen Faden ist es
    wieder nur eine Sammlung."""
    kopf = (BEISPIELE / name / "u_main.py").read_text(encoding="utf-8")[:400]

    nummer = int(name[:2])
    assert f"Stufe {nummer} von 9" in kopf


# -- Was der Projekt-Explorer bei jedem Beispiel zeigt -------------------
#
# Anlass (Nutzer-Auftrag): "Prüfe ob bei allen
# Beispielprogrammen die Units alle korrekt gezeigt werden und ob auch
# die Diagramme und Struktogramme richtig gezeigt werden. Das soll bei
# allen der Fall sein."
#
# Dabei kam heraus: die beiden Konsolenstufen öffneten sich mit einem
# voellig leeren Explorer. Ihre einzige Datei war `main.py`, und die
# ist als Startdatei ausgeblendet - dort stand aber der ganze
# Schülercode. Die Antwort darauf war nicht, die Startdatei zu zeigen,
# sondern der Grundsatz des Nutzers: "Jedes Projekt braucht eine Main um
# zu starten und eine u_main wo der Schüler Code drin steht." Seither
# haben auch Konsolenprojekte eine `u_main.py`, und `main.py` ist
# überall nur noch der Starter.


@pytest.mark.parametrize("name", NAMEN)
def test_der_explorer_zeigt_bei_jedem_beispiel_etwas(name: str, qtbot) -> None:
    from ide.shell.explorer import ProjektExplorer

    baum = ProjektExplorer()
    qtbot.addWidget(baum)
    baum.projekt_anzeigen(Projekt.laden(BEISPIELE / name))

    eintraege = [
        gruppe.child(i).text(0)
        for gruppe in (baum.formulare_gruppe, baum.units_gruppe, baum.diagramme_gruppe)
        for i in range(gruppe.childCount())
    ]
    assert eintraege, f"{name}: der Projekt-Explorer ist leer"


@pytest.mark.parametrize("name", NAMEN)
def test_jede_sichtbare_gruppe_hat_auch_eintraege(name: str, qtbot) -> None:
    """Keine fette Überschrift ohne einen einzigen Eintrag darunter -
    das sieht aus, als wäre etwas kaputtgegangen."""
    from ide.shell.explorer import ProjektExplorer

    baum = ProjektExplorer()
    qtbot.addWidget(baum)
    baum.projekt_anzeigen(Projekt.laden(BEISPIELE / name))

    for gruppe in (baum.formulare_gruppe, baum.units_gruppe, baum.diagramme_gruppe):
        if not gruppe.isHidden():
            assert gruppe.childCount(), f"{name}: Gruppe {gruppe.text(0)!r} ist leer"


@pytest.mark.parametrize("name", NAMEN)
def test_jede_eigene_python_datei_steht_im_explorer(name: str, qtbot) -> None:
    """Jede Datei, an der gearbeitet wird, muss erreichbar sein - als
    Unit-Eintrag oder als Formular-Eintrag (eine Formular-Unit steht
    bewusst als ein Eintrag da, wie im Projektinspektor von
    Lazarus)."""
    from ide.shell.explorer import ProjektExplorer

    projekt = Projekt.laden(BEISPIELE / name)
    baum = ProjektExplorer()
    qtbot.addWidget(baum)
    baum.projekt_anzeigen(projekt)

    erreichbar = {
        Path(gruppe.child(i).data(0, Qt.ItemDataRole.UserRole)).stem
        for gruppe in (baum.formulare_gruppe, baum.units_gruppe)
        for i in range(gruppe.childCount())
    }
    for pfad in projekt.units():
        assert pfad.stem in erreichbar, f"{name}: {pfad.name} ist im Explorer nicht zu finden"


def test_die_diagramme_der_kontoverwaltung_stehen_im_explorer(qtbot) -> None:
    """Das einzige Beispiel mit Diagrammen - Struktogramm,
    Entscheidungstabelle und Klassendiagramm."""
    from ide.shell.explorer import ProjektExplorer

    baum = ProjektExplorer()
    qtbot.addWidget(baum)
    baum.projekt_anzeigen(Projekt.laden(BEISPIELE / "06_Kontoverwaltung"))

    gezeigt = [
        baum.diagramme_gruppe.child(i).text(0)
        for i in range(baum.diagramme_gruppe.childCount())
    ]
    assert gezeigt == ["konto_abheben", "konto_entscheidung", "konto_klassen"]


@pytest.mark.parametrize(
    ("datei", "typ"),
    [
        ("konto_abheben", "struktogramm"),
        ("konto_entscheidung", "entscheidungstabelle"),
        ("konto_klassen", "class"),
    ],
)
def test_jedes_diagramm_laesst_sich_wirklich_oeffnen(datei: str, typ: str, qtbot) -> None:
    """Nicht nur laden: das Fenster aufbauen und nachsehen, dass auf der
    Zeichenfläche wirklich etwas steht."""
    from ide.diagramm.datei import Diagramm
    from ide.diagramm.fenster import DiagrammFenster

    pfad = BEISPIELE / "06_Kontoverwaltung" / "diagramme" / f"{datei}.pdiag"
    diagramm = Diagramm.laden(pfad)
    assert diagramm.typ == typ

    fenster = DiagrammFenster(diagramm)
    qtbot.addWidget(fenster)
    fenster.resize(1000, 720)

    bild = fenster.grab().toImage()
    gezeichnet = sum(
        1
        for y in range(0, bild.height(), 6)
        for x in range(0, bild.width(), 6)
        if bild.pixelColor(x, y).name() not in ("#ffffff", "#f3f3f3")
    )
    assert gezeichnet > 200, f"{datei}: das Fenster ist praktisch leer"


# -- Jedes Projekt: winzige main.py, grosse u_main.py -------------------


@pytest.mark.parametrize("name", NAMEN)
def test_jedes_projekt_hat_eine_main_und_eine_u_main(name: str) -> None:
    ordner = BEISPIELE / name
    assert (ordner / "main.py").is_file(), f"{name}: main.py fehlt"
    assert (ordner / "u_main.py").is_file(), f"{name}: u_main.py fehlt"


@pytest.mark.parametrize("name", NAMEN)
def test_die_main_startet_nur_und_enthaelt_keinen_unterricht(name: str) -> None:
    """"Main.py ist nur dafür da um das Script zu starten. Alles was
    programmiert werden muss passiert in u_main.py" - Nutzer, September
    2026. Gemessen an Zeilen, die wirklich etwas tun."""
    zeilen = [
        z.strip()
        for z in (BEISPIELE / name / "main.py").read_text(encoding="utf-8").splitlines()
        if z.strip() and not z.strip().startswith("#")
    ]
    assert len(zeilen) <= 5, f"{name}: main.py tut zu viel ({len(zeilen)} Zeilen)"


@pytest.mark.parametrize("name", NAMEN)
def test_die_main_steht_in_keinem_explorer(name: str, qtbot) -> None:
    """Schüler sollen nicht in die main.py schauen müssen - also darf
    sie auch nirgends im Baum auftauchen."""
    from ide.shell.explorer import ProjektExplorer

    baum = ProjektExplorer()
    qtbot.addWidget(baum)
    baum.projekt_anzeigen(Projekt.laden(BEISPIELE / name))

    gezeigt = {
        gruppe.child(i).text(0)
        for gruppe in (baum.formulare_gruppe, baum.units_gruppe, baum.diagramme_gruppe)
        for i in range(gruppe.childCount())
    }
    assert "main.py" not in gezeigt


@pytest.mark.parametrize("name", NAMEN)
def test_der_schuelercode_kommt_ohne_qt_aus(name: str) -> None:
    """Befuellt wird über die Komponenten selbst - `self.l_x.caption =
    "..."` - und nie über Qt. Eigenschaft im Objektinspektor und
    Attribut im Code sind dasselbe; das ist der Kern des Konzepts."""
    verboten = ("PySide6", "QtWidgets", "_qwidget", ".setText(", ".setValue(")
    for datei in sorted((BEISPIELE / name).glob("u_*.py")):
        if datei.name.endswith("_design.py"):
            continue  # erzeugt, nicht vom Schüler
        text = datei.read_text(encoding="utf-8")
        for wort in verboten:
            assert wort not in text, f"{name}/{datei.name}: {wort} gehoert nicht in Schuelercode"
