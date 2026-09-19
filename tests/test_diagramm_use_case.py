"""Tests für das Use-Case-Diagramm (M9, „Danach“). Headless.

Es teilt sich Zeichenfläche, Auswahl und Verbindungs-Maschinerie mit
dem Klassendiagramm; geprüft wird deshalb vor allem das, was neu ist:
der Formenkatalog, die Darstellung und die Stereotypen «include» und
«extend».
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage, QPainter

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.canvas import DiagrammCanvas
from ide.diagramm.formen import (
    form_art,
    formen_fuer,
    verbindungen_fuer,
    verbindungs_art,
)
from ide.diagramm.neu import MVP_TYPEN
from ide.diagramm.stil import stil as stil_zu_namen
from ide.diagramm.zeichnen import (
    form_zeichnen,
    mindesthoehe,
    verbindung_zeichnen,
    verbindungsbeschriftungen_zeichnen,
)


@pytest.fixture
def flaeche(tmp_path: Path) -> DiagrammCanvas:
    fenster = DiagrammFenster(diagramm_erzeugen("use_case", tmp_path / "u.pdiag", "Ausleihe"))
    return fenster.zeichenflaeche


def _gemalt(shape: dict, stil_name: str = "modern-light") -> set[str]:
    """Die Farben, die diese Form wirklich aufs Bild bringt."""
    stil = stil_zu_namen(stil_name)
    bild = QImage(400, 300, QImage.Format.Format_RGB32)
    bild.fill(QColor(stil.hintergrund))
    maler = QPainter(bild)
    form_zeichnen(maler, shape, stil)
    maler.end()
    return {
        bild.pixelColor(x, y).name()
        for x in range(0, bild.width(), 2)
        for y in range(0, bild.height(), 2)
    }


# -- Katalog -------------------------------------------------------------


def test_die_palette_bietet_die_vier_formen() -> None:
    kinds = [form.kind for form in formen_fuer("use_case")]

    assert kinds == ["actor", "use_case", "system_boundary", "note"]


def test_die_palette_bietet_die_vier_beziehungen() -> None:
    kinds = [art.kind for art in verbindungen_fuer("use_case")]

    assert kinds == ["association", "include", "extend", "generalization"]


def test_notiz_und_assoziation_sind_dieselben_objekte_wie_im_klassendiagramm() -> None:
    """`form_art()` sucht über `kind`. Zwei Einträge mit derselben
    Kennung würden sich gegenseitig überschreiben, ohne dass es
    auffällt."""
    klassen_notiz = next(f for f in formen_fuer("class") if f.kind == "note")
    use_case_notiz = next(f for f in formen_fuer("use_case") if f.kind == "note")

    assert klassen_notiz is use_case_notiz
    assert form_art("note") is klassen_notiz


def test_include_und_extend_sind_gestrichelt_mit_pfeil() -> None:
    """UML-Notation: beide sind Abhängigkeiten."""
    for kind in ("include", "extend"):
        art = verbindungs_art(kind)
        assert art.gestrichelt is True
        assert art.spitze_am_ziel == "offen"
        assert art.stereotyp == kind


def test_der_typ_laesst_sich_neu_anlegen() -> None:
    assert "use_case" in MVP_TYPEN


# -- Darstellung ---------------------------------------------------------


@pytest.mark.parametrize("kind", ["actor", "use_case", "system_boundary"])
def test_jede_form_malt_wirklich_etwas(flaeche: DiagrammCanvas, kind: str) -> None:
    form = flaeche.form_platzieren(kind, 200, 150)
    form["x"], form["y"] = 40, 40

    farben = _gemalt(form)

    assert len(farben) > 1, f"{kind} malt nur den Hintergrund"


def test_der_akteur_bleibt_ein_strichmaennchen(flaeche: DiagrammCanvas) -> None:
    """Würde das Männchen mit der Form mitwachsen, wäre ein breit
    gezogener Akteur ein grotesk breites Strichmännchen – in UML hat es
    aber immer dieselbe Gestalt."""
    from ide.diagramm.zeichnen import AKTEUR_HOEHE

    schmal = flaeche.form_platzieren("actor", 200, 150)
    schmal["x"], schmal["y"] = 20, 20
    schmal["name"] = "Bibliothekarin"

    assert mindesthoehe(schmal) > AKTEUR_HOEHE


def test_der_anwendungsfall_traegt_seinen_namen(flaeche: DiagrammCanvas) -> None:
    form = flaeche.form_platzieren("use_case", 200, 150)
    form["x"], form["y"] = 40, 40
    form["name"] = "Buch ausleihen"

    stil = stil_zu_namen("modern-light")
    ohne = _gemalt({**form, "name": ""})
    mit = _gemalt(form)

    assert QColor(stil.text).name() in mit
    assert len(mit) > len(ohne)


def test_die_systemgrenze_ist_nicht_gefuellt(flaeche: DiagrammCanvas) -> None:
    """Sie liegt hinter den Fällen; eine Füllung würde sie verdecken,
    sobald jemand die Grenze nach vorn holt."""
    stil = stil_zu_namen("modern-light")
    grenze = flaeche.form_platzieren("system_boundary", 200, 150)
    grenze["x"], grenze["y"] = 20, 20
    grenze["w"], grenze["h"] = 300, 200

    farben = _gemalt(grenze)

    assert QColor(stil.fuellung).name() not in farben


def test_kein_hinweis_zu_schmal_fuer_die_neuen_formen(flaeche: DiagrammCanvas) -> None:
    """Alle drei brechen ihren Text um – eine Mindestbreite würde sie
    reihenweise fälschlich als „zu schmal“ melden (derselbe Fehler war
    bei Notiz und Paket schon einmal im Screenshot aufgefallen)."""
    from ide.diagramm.zeichnen import mindestbreite

    for kind in ("actor", "use_case", "system_boundary"):
        form = flaeche.form_platzieren(kind, 200, 150)
        form["name"] = "Ein sehr langer Name, der garantiert nicht passt"
        assert mindestbreite(form) == 0.0


# -- Stereotypen ---------------------------------------------------------


@pytest.mark.parametrize("kind", ["include", "extend"])
def test_der_stereotyp_steht_wirklich_auf_der_linie(flaeche: DiagrammCanvas, kind: str) -> None:
    """Ohne ihn sähe eine «include»-Beziehung wie eine gewöhnliche
    Abhängigkeit aus. Geprüft am gemalten Bild, nicht am Datenmodell."""
    stil = stil_zu_namen("modern-light")
    quelle = flaeche.form_platzieren("use_case", 100, 150)
    ziel = flaeche.form_platzieren("use_case", 340, 150)
    verbindung = flaeche.verbindung_erstellen(kind, quelle, ziel)

    def textpixel(v: dict) -> int:
        bild = QImage(480, 300, QImage.Format.Format_RGB32)
        bild.fill(QColor(stil.hintergrund))
        maler = QPainter(bild)
        # Beides, wie die Zeichenfläche es auch tut: der Stereotyp
        # gehört zu den Beschriftungen und wird nach den Formen gemalt.
        verbindung_zeichnen(maler, v, quelle, ziel, stil)
        verbindungsbeschriftungen_zeichnen(maler, v, quelle, ziel, stil)
        maler.end()
        return sum(
            bild.pixelColor(x, y).name() == QColor(stil.text).name()
            for x in range(bild.width())
            for y in range(bild.height())
        )

    # Gegenprobe mit einer gewöhnlichen Abhängigkeit: die sieht genauso
    # aus, nur ohne den Stereotyp. Gezählt werden Pixel in der
    # **genauen** Textfarbe; durch die Kantenglättung sind das nur
    # wenige, aber bei der Abhängigkeit muss es exakt null sein.
    ohne = dict(verbindung)
    ohne["kind"] = "dependency"
    assert textpixel(ohne) == 0
    assert textpixel(verbindung) > 0


def test_die_assoziation_bekommt_keinen_stereotyp() -> None:
    assert verbindungs_art("association").stereotyp == ""


# -- Fenster -------------------------------------------------------------


def test_das_fenster_zeigt_die_formen_palette(tmp_path: Path) -> None:
    fenster = DiagrammFenster(diagramm_erzeugen("use_case", tmp_path / "f.pdiag", "f"))

    assert fenster.palette is not None
    beschriftungen = [form.beschriftung for form in formen_fuer("use_case")]
    assert "Akteur" in beschriftungen


def test_anordnen_geht_auch_hier(tmp_path: Path) -> None:
    """Use-Case-Diagramme benutzen dieselbe Zeichenfläche – Ausrichten
    und Gruppieren müssen deshalb ohne Zutun funktionieren."""
    fenster = DiagrammFenster(diagramm_erzeugen("use_case", tmp_path / "a.pdiag", "a"))
    flaeche = fenster.zeichenflaeche
    erster = flaeche.form_platzieren("use_case", 100, 100)
    zweiter = flaeche.form_platzieren("use_case", 400, 300)
    flaeche._auswaehlen(erster)
    flaeche.auswahl_umschalten(zweiter)

    assert flaeche.ausrichten("links") is True
    assert erster["x"] == zweiter["x"]


def test_speichern_und_laden(tmp_path: Path) -> None:
    from ide.diagramm.datei import Diagramm

    pfad = tmp_path / "s.pdiag"
    fenster = DiagrammFenster(diagramm_erzeugen("use_case", pfad, "Ausleihe"))
    flaeche = fenster.zeichenflaeche
    akteur = flaeche.form_platzieren("actor", 100, 100)
    fall = flaeche.form_platzieren("use_case", 300, 100)
    flaeche.verbindung_erstellen("include", fall, akteur)
    fenster.speichern()

    geladen = Diagramm.laden(pfad)

    assert geladen.typ == "use_case"
    assert {f["kind"] for f in geladen.daten["shapes"]} == {"actor", "use_case"}
    assert geladen.daten["connectors"][0]["kind"] == "include"


# -- Aus der Sichtprüfung ------------------------------------------------


def test_der_stereotyp_verschwindet_nicht_unter_einer_form(
    flaeche: DiagrammCanvas,
) -> None:
    """Erster Fund: bei einer «extend»-Beziehung, deren Linie hinter
    einem anderen Anwendungsfall vorbeiläuft, lag die Mitte genau in
    dessen Ellipse – und der Stereotyp verschwand darunter. Derselbe
    Fehler wie seinerzeit bei den Multiplizitäten."""
    stil = stil_zu_namen("modern-light")
    oben = flaeche.form_platzieren("use_case", 240, 60)
    dazwischen = flaeche.form_platzieren("use_case", 240, 200)
    unten = flaeche.form_platzieren("use_case", 240, 340)
    # Ohne Namen: sonst zählte der Test die Beschriftung der Formen mit
    # und könnte gar nicht merken, ob der Stereotyp fehlt.
    for form in (oben, dazwischen, unten):
        form["name"] = ""
    verbindung = flaeche.verbindung_erstellen("extend", unten, oben)

    bild = QImage(480, 420, QImage.Format.Format_RGB32)
    bild.fill(QColor(stil.hintergrund))
    maler = QPainter(bild)
    verbindung_zeichnen(maler, verbindung, unten, oben, stil)
    for form in (oben, dazwischen, unten):
        form_zeichnen(maler, form, stil)
    verbindungsbeschriftungen_zeichnen(maler, verbindung, unten, oben, stil)
    maler.end()

    textfarbe = QColor(stil.text).name()
    treffer = sum(
        bild.pixelColor(x, y).name() == textfarbe
        for x in range(bild.width())
        for y in range(bild.height())
    )
    assert treffer > 0, "der Stereotyp liegt unter der Form"


def test_eine_systemgrenze_voller_faelle_ist_kein_layout_fehler(
    flaeche: DiagrammCanvas,
) -> None:
    """Zweiter Fund: das Use-Case-Diagramm hatte von Anfang an so viele
    Warnungen wie Fälle. Eine Systemgrenze, die Anwendungsfälle umgibt,
    ist kein Versehen, sondern genau ihr Zweck."""
    grenze = flaeche.form_platzieren("system_boundary", 400, 260)
    grenze["x"], grenze["y"], grenze["w"], grenze["h"] = 100, 60, 400, 300
    fall = flaeche.form_platzieren("use_case", 300, 200)
    fall["x"], fall["y"], fall["w"], fall["h"] = 160, 120, 176, 72

    hinweise = flaeche.hinweise_aktualisieren()

    assert not [h for h in hinweise if h.regel == "ueberlappung"], [h.meldung for h in hinweise]


def test_eine_nur_angeschnittene_form_wird_weiterhin_gemeldet(
    flaeche: DiagrammCanvas,
) -> None:
    """Gegenprobe: hängt ein Fall halb aus der Grenze heraus, ist das
    wirklich ein Versehen."""
    grenze = flaeche.form_platzieren("system_boundary", 400, 260)
    grenze["x"], grenze["y"], grenze["w"], grenze["h"] = 100, 60, 400, 300
    fall = flaeche.form_platzieren("use_case", 300, 200)
    fall["x"], fall["y"], fall["w"], fall["h"] = 420, 120, 176, 72

    hinweise = flaeche.hinweise_aktualisieren()

    assert [h for h in hinweise if h.regel == "ueberlappung"]


def test_der_stereotyp_laesst_sich_wegziehen(flaeche: DiagrammCanvas) -> None:
    """Dritter Fund: neben der Linie landet «extend» mitunter trotzdem
    auf einem anderen Anwendungsfall und zerschneidet dessen Namen. Er
    teilt sich `label_offsets` mit den Multiplizitäten und damit auch
    deren Bedienung – wegziehen geht also wie dort."""
    from ide.diagramm.zeichnen import beschriftungs_rechtecke

    oben = flaeche.form_platzieren("use_case", 240, 60)
    unten = flaeche.form_platzieren("use_case", 240, 340)
    verbindung = flaeche.verbindung_erstellen("extend", unten, oben)

    vorher = beschriftungs_rechtecke(verbindung, unten, oben)["stereotyp"].center()
    verbindung["label_offsets"] = {"stereotyp": [60, -30]}
    nachher = beschriftungs_rechtecke(verbindung, unten, oben)["stereotyp"].center()

    assert nachher.x() - vorher.x() == pytest.approx(60)
    assert nachher.y() - vorher.y() == pytest.approx(-30)

    # Und er ist dort auch anklickbar - sonst könnte man ihn nicht fassen
    getroffen = flaeche.beschriftung_bei(nachher.x(), nachher.y())
    assert getroffen == (verbindung, "stereotyp")


def test_der_stereotyp_liegt_nicht_auf_der_linie(flaeche: DiagrammCanvas) -> None:
    """Genau auf der Linie sah es aus, als wäre sie durchtrennt."""
    from ide.diagramm.zeichnen import beschriftungs_rechtecke, verbindungs_punkte

    links = flaeche.form_platzieren("use_case", 100, 200)
    rechts = flaeche.form_platzieren("use_case", 400, 200)
    verbindung = flaeche.verbindung_erstellen("include", links, rechts)

    kasten = beschriftungs_rechtecke(verbindung, links, rechts)["stereotyp"]
    punkte = verbindungs_punkte(verbindung, links, rechts)
    linie_y = (punkte[0].y() + punkte[-1].y()) / 2

    assert not (kasten.top() < linie_y < kasten.bottom())
