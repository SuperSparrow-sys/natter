"""Tests für den Entscheidungstabellen-Editor (M9, Schritt 10).
Headless.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent

from ide.diagramm import DiagrammFenster, diagramm_erzeugen
from ide.diagramm.tabelle import (
    AKTIONSWERTE,
    BEDINGUNGSWERTE,
    regelanzahl,
    tabellengroesse,
    wert,
    zellen,
)
from ide.diagramm.tabelle_canvas import VERSATZ, TabellenCanvas


@pytest.fixture
def flaeche(tmp_path: Path) -> TabellenCanvas:
    diagramm = diagramm_erzeugen("entscheidungstabelle", tmp_path / "t.pdiag", "ampel")
    flaeche = TabellenCanvas(diagramm)
    # Startzustand: zwei Bedingungen, zwei Aktionen, drei Regeln
    daten = diagramm.daten
    daten["conditions"] = [
        {"text": "Ampel eingeschaltet?", "values": ["J", "J", "N"]},
        {"text": "Taster gedrückt?", "values": ["J", "N", "*"]},
    ]
    daten["actions"] = [
        {"text": "auf grün schalten", "values": ["X", "", ""]},
        {"text": "gelb blinken", "values": ["", "", "X"]},
    ]
    return flaeche


def _klick(x: float, y: float) -> QMouseEvent:
    return QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(x, y),
        QPointF(x, y),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


def _zelle(flaeche: TabellenCanvas, teil: str, zeile: int, spalte: int):
    return next(
        z
        for z in zellen(flaeche.diagramm.daten, VERSATZ, VERSATZ)
        if z.teil == teil and z.zeile == zeile and z.spalte == spalte
    )


# -- Geometrie -----------------------------------------------------------


def test_regelanzahl_richtet_sich_nach_der_laengsten_zeile(flaeche: TabellenCanvas) -> None:
    assert regelanzahl(flaeche.diagramm.daten) == 3


def test_verkuerzte_zeile_bringt_die_tabelle_nicht_durcheinander(
    flaeche: TabellenCanvas,
) -> None:
    """Eine von Hand bearbeitete Datei darf den Editor nicht kippen."""
    flaeche.diagramm.daten["actions"][0]["values"] = ["X"]

    assert regelanzahl(flaeche.diagramm.daten) == 3
    assert wert(flaeche.diagramm.daten["actions"][0], 2) == ""


def test_tabelle_waechst_mit_zeilen_und_regeln(flaeche: TabellenCanvas) -> None:
    vorher = tabellengroesse(flaeche.diagramm.daten)

    flaeche.zeile_hinzufuegen("conditions")
    flaeche.regel_hinzufuegen()

    nachher = tabellengroesse(flaeche.diagramm.daten)
    assert nachher[0] > vorher[0] and nachher[1] > vorher[1]


def test_jede_zeile_hat_eine_textzelle_und_eine_zelle_je_regel(
    flaeche: TabellenCanvas,
) -> None:
    bedingungszellen = [z for z in zellen(flaeche.diagramm.daten) if z.teil == "conditions"]

    assert len(bedingungszellen) == 2 * (1 + 3)


# -- Zellen schalten -----------------------------------------------------


def test_bedingungszelle_laeuft_durch_j_n_stern_leer(flaeche: TabellenCanvas) -> None:
    """Abschnitt 13.5: „Bedingungsteil J → N → * → leer“."""
    zeile = flaeche.diagramm.daten["conditions"][0]
    zeile["values"][0] = ""
    zelle = _zelle(flaeche, "conditions", 0, 0)

    gesehen = []
    for _ in range(len(BEDINGUNGSWERTE)):
        flaeche.zelle_schalten(zelle)
        gesehen.append(wert(zeile, 0))

    assert gesehen == ["J", "N", "*", ""]


def test_aktionszelle_kennt_nur_x_und_leer(flaeche: TabellenCanvas) -> None:
    zeile = flaeche.diagramm.daten["actions"][0]
    zeile["values"][0] = ""
    zelle = _zelle(flaeche, "actions", 0, 0)

    flaeche.zelle_schalten(zelle)
    assert wert(zeile, 0) == "X"
    flaeche.zelle_schalten(zelle)
    assert wert(zeile, 0) == ""
    assert set(AKTIONSWERTE) == {"X", ""}


def test_schalten_ist_rueckgaengig_machbar(flaeche: TabellenCanvas) -> None:
    zeile = flaeche.diagramm.daten["conditions"][0]
    vorher = wert(zeile, 1)

    flaeche.zelle_schalten(_zelle(flaeche, "conditions", 0, 1))
    flaeche.rueckgaengig()

    assert wert(zeile, 1) == vorher


def test_klick_auf_eine_zelle_schaltet_sie(flaeche: TabellenCanvas) -> None:
    zelle = _zelle(flaeche, "conditions", 1, 2)
    vorher = wert(flaeche.diagramm.daten["conditions"][1], 2)

    flaeche.mousePressEvent(_klick(zelle.rechteck.center().x(), zelle.rechteck.center().y()))

    assert wert(flaeche.diagramm.daten["conditions"][1], 2) != vorher
    assert flaeche.ausgewaehlte_zelle == zelle


def test_klick_auf_die_textspalte_schaltet_nichts(flaeche: TabellenCanvas) -> None:
    """Sonst würde beim Anwählen einer Zeile aus Versehen ein Wert
    verstellt."""
    zelle = _zelle(flaeche, "conditions", 0, -1)
    vorher = dict(flaeche.diagramm.daten["conditions"][0])

    flaeche.mousePressEvent(_klick(zelle.rechteck.center().x(), zelle.rechteck.center().y()))

    assert flaeche.diagramm.daten["conditions"][0] == vorher
    assert flaeche.ausgewaehlte_zelle == zelle


def test_leertaste_schaltet_die_ausgewaehlte_zelle(flaeche: TabellenCanvas) -> None:
    zelle = _zelle(flaeche, "conditions", 0, 0)
    flaeche.auswaehlen(zelle)
    vorher = wert(flaeche.diagramm.daten["conditions"][0], 0)

    flaeche.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Space, Qt.KeyboardModifier.NoModifier)
    )

    assert wert(flaeche.diagramm.daten["conditions"][0], 0) != vorher


# -- Zeilen --------------------------------------------------------------


def test_zeile_hinzufuegen_bekommt_gleich_viele_werte(flaeche: TabellenCanvas) -> None:
    neue = flaeche.zeile_hinzufuegen("conditions")

    assert len(neue["values"]) == 3
    assert flaeche.diagramm.daten["conditions"][-1] is neue


def test_zeile_entfernen_und_rueckgaengig(flaeche: TabellenCanvas) -> None:
    erste = flaeche.diagramm.daten["conditions"][0]

    flaeche.zeile_entfernen("conditions", 0)
    assert flaeche.diagramm.daten["conditions"][0]["text"] == "Taster gedrückt?"

    flaeche.rueckgaengig()
    assert flaeche.diagramm.daten["conditions"][0] is erste


def test_entf_loescht_die_zeile_der_ausgewaehlten_zelle(flaeche: TabellenCanvas) -> None:
    flaeche.auswaehlen(_zelle(flaeche, "actions", 1, 0))

    flaeche.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
    )

    assert len(flaeche.diagramm.daten["actions"]) == 1


def test_text_setzen_ist_rueckgaengig_machbar(flaeche: TabellenCanvas) -> None:
    zeile = flaeche.diagramm.daten["conditions"][0]

    flaeche.text_setzen(zeile, "Ampel an?")
    assert zeile["text"] == "Ampel an?"

    flaeche.rueckgaengig()
    assert zeile["text"] == "Ampel eingeschaltet?"


# -- Regeln (Spalten) ----------------------------------------------------


def test_regel_hinzufuegen_verlaengert_alle_zeilen(flaeche: TabellenCanvas) -> None:
    """Sonst liefen Bedingungs- und Aktionsteil auseinander."""
    flaeche.regel_hinzufuegen()

    daten = flaeche.diagramm.daten
    for zeile in [*daten["conditions"], *daten["actions"]]:
        assert len(zeile["values"]) == 4


def test_regel_entfernen_nimmt_die_spalte_aus_allen_zeilen(
    flaeche: TabellenCanvas,
) -> None:
    flaeche.regel_entfernen(0)

    daten = flaeche.diagramm.daten
    assert daten["conditions"][0]["values"] == ["J", "N"]
    assert daten["actions"][0]["values"] == ["", ""]


def test_regel_entfernen_ist_rueckgaengig_machbar(flaeche: TabellenCanvas) -> None:
    vorher = [list(z["values"]) for z in flaeche.diagramm.daten["conditions"]]

    flaeche.regel_entfernen(1)
    flaeche.rueckgaengig()

    assert [z["values"] for z in flaeche.diagramm.daten["conditions"]] == vorher


def test_letzte_regel_bleibt_stehen(flaeche: TabellenCanvas) -> None:
    """Eine Tabelle ohne Regel wäre leer."""
    flaeche.regel_entfernen(0)
    flaeche.regel_entfernen(0)

    flaeche.regel_entfernen(0)

    assert regelanzahl(flaeche.diagramm.daten) == 1


def test_regel_verschieben_tauscht_die_spalte(flaeche: TabellenCanvas) -> None:
    flaeche.regel_verschieben(0, 1)

    daten = flaeche.diagramm.daten
    assert daten["conditions"][0]["values"] == ["J", "J", "N"]
    assert daten["conditions"][1]["values"] == ["N", "J", "*"]
    assert daten["actions"][0]["values"] == ["", "X", ""]


def test_regel_verschieben_ueber_den_rand_tut_nichts(flaeche: TabellenCanvas) -> None:
    vorher = [list(z["values"]) for z in flaeche.diagramm.daten["conditions"]]

    flaeche.regel_verschieben(0, -1)
    flaeche.regel_verschieben(2, 3)

    assert [z["values"] for z in flaeche.diagramm.daten["conditions"]] == vorher


def test_regel_verschieben_ist_rueckgaengig_machbar(flaeche: TabellenCanvas) -> None:
    vorher = [list(z["values"]) for z in flaeche.diagramm.daten["conditions"]]

    flaeche.regel_verschieben(0, 2)
    flaeche.rueckgaengig()

    assert [z["values"] for z in flaeche.diagramm.daten["conditions"]] == vorher


# -- Darstellung ---------------------------------------------------------


def test_kopfzeile_verschluckt_den_text_nicht(flaeche: TabellenCanvas) -> None:
    """Im PDF aufgefallen: die Kopfzeilen waren mit der Trennlinienfarbe
    gefüllt – in der Schwarz-Weiß-Vorlage ist die schwarz, „Bedingungen“,
    „Aktionen“ und die Regelnummern verschwanden also genau in der
    Vorlage, die für die Abgabe auf Papier gedacht ist."""
    from ide.diagramm.stil import MODERN_DUNKEL, MODERN_HELL, SCHWARZ_WEISS

    for stil in (MODERN_HELL, MODERN_DUNKEL, SCHWARZ_WEISS):
        assert stil.kopf != stil.text


def test_schwarz_weiss_tabelle_zeigt_ihre_ueberschriften(
    flaeche: TabellenCanvas, tmp_path: Path
) -> None:
    from PySide6.QtGui import QImage, QPainter

    from ide.diagramm.stil import SCHWARZ_WEISS
    from ide.diagramm.tabelle import KOPFHOEHE, tabelle_zeichnen, tabellengroesse

    breite, hoehe = tabellengroesse(flaeche.diagramm.daten)
    bild = QImage(int(breite), int(hoehe), QImage.Format.Format_RGB32)
    bild.fill("#ffffff")
    maler = QPainter(bild)
    tabelle_zeichnen(maler, flaeche.diagramm.daten, SCHWARZ_WEISS)
    maler.end()

    # In der Kopfzeile muss es sowohl helle als auch dunkle Pixel geben –
    # eine durchgehend schwarze Fläche hieße: Text unsichtbar.
    kopfpixel = {
        bild.pixelColor(x, y).name()
        for x in range(4, int(breite) - 4, 2)
        for y in range(4, KOPFHOEHE - 4, 2)
    }
    assert "#ffffff" in kopfpixel
    assert any(farbe != "#ffffff" for farbe in kopfpixel)


# -- Fenster -------------------------------------------------------------


@pytest.fixture
def fenster(tmp_path: Path) -> DiagrammFenster:
    return DiagrammFenster(
        diagramm_erzeugen("entscheidungstabelle", tmp_path / "t.pdiag", "ampel")
    )


def test_tabellenfenster_bekommt_die_tabellenflaeche(fenster: DiagrammFenster) -> None:
    assert isinstance(fenster.zeichenflaeche, TabellenCanvas)
    assert fenster.palette_dock is None
    assert fenster.eigenschaften_dock is None


def test_tabellenmenue_ist_vorhanden(fenster: DiagrammFenster) -> None:
    beschriftungen = [a.text() for a in fenster.menue("Tabelle").actions()]

    assert "Regel hinzufügen" in beschriftungen
    assert "Bedingung hinzufügen" in beschriftungen


def test_tabellenmenue_steht_vor_hilfe(fenster: DiagrammFenster) -> None:
    """Im Screenshot aufgefallen: „Tabelle“ landete hinter „Hilfe“, weil
    es erst nachträglich angehängt wurde."""
    menues = [a.text() for a in fenster.menuBar().actions()]

    assert menues[-2:] == ["Tabelle", "Hilfe"]


def test_menue_regel_hinzufuegen_wirkt(fenster: DiagrammFenster) -> None:
    vorher = regelanzahl(fenster.diagramm.daten)

    fenster.aktionen["Tabelle/Regel hinzufügen"].trigger()

    assert regelanzahl(fenster.diagramm.daten) == vorher + 1


def test_regel_verschieben_ohne_auswahl_meldet_das(fenster: DiagrammFenster) -> None:
    fenster.aktionen["Tabelle/Regel nach rechts"].trigger()

    assert "Keine Regel ausgewählt" in fenster.statusBar().currentMessage()


def test_statusleiste_zaehlt_zeilen_und_regeln(fenster: DiagrammFenster) -> None:
    fenster.zeichenflaeche.zeile_hinzufuegen("conditions")
    fenster._statusleiste_aktualisieren()

    meldung = fenster.statusBar().currentMessage()
    assert "3 Zeilen" in meldung and "1 Regel" in meldung


def test_die_statusleiste_zaehlt_auf_deutsch(fenster: DiagrammFenster) -> None:
    """Dort stand real „2 Zeilen │ 1 Regeln" - die Zahl im Singular,
    das Wort im Plural. Bei den Layout-Hinweisen daneben war es von
    Anfang an richtig."""
    fenster._statusleiste_aktualisieren()
    assert "1 Regel  │" in fenster.statusBar().currentMessage()

    fenster.zeichenflaeche.regel_hinzufuegen()
    fenster._statusleiste_aktualisieren()

    assert "2 Regeln" in fenster.statusBar().currentMessage()


def test_andere_diagrammtypen_haben_kein_tabellenmenue(tmp_path: Path) -> None:
    fenster = DiagrammFenster(diagramm_erzeugen("class", tmp_path / "k.pdiag", "k"))

    assert "Tabelle" not in fenster._menues


def test_tabelle_wird_gespeichert_und_geladen(fenster: DiagrammFenster) -> None:
    from ide.diagramm.datei import Diagramm

    flaeche = fenster.zeichenflaeche
    zeile = flaeche.zeile_hinzufuegen("conditions")
    flaeche.text_setzen(zeile, "Ampel eingeschaltet?")
    fenster.speichern()

    geladen = Diagramm.laden(fenster.diagramm.pfad)

    texte = [z["text"] for z in geladen.daten["conditions"]]
    assert "Ampel eingeschaltet?" in texte


def test_tabelle_laesst_sich_als_pdf_exportieren(
    fenster: DiagrammFenster, tmp_path: Path
) -> None:
    fenster.zeichenflaeche.zeile_hinzufuegen("conditions")

    pfad = fenster.exportieren(tmp_path / "tabelle.pdf")

    assert pfad.read_bytes().startswith(b"%PDF")
    assert pfad.stat().st_size > 1000
