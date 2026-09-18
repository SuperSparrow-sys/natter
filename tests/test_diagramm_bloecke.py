"""Tests für ide/diagramm/bloecke.py und ide/diagramm/struktogramm.py:
Blockbaum und Nassi-Shneiderman-Layout (M9, Schritt 9).

Die Baumoperationen brauchen kein Qt; das Layout schon (Schriftmaße),
läuft aber headless.
"""

from __future__ import annotations

import pytest

from ide.diagramm.bloecke import (
    Einfuegestelle,
    alle_bloecke,
    einfuegen,
    elternteil,
    entfernen,
    fall_entfernen,
    fall_hinzufuegen,
    ist_nachfahre,
    kinder,
    neue_id,
    neuer_block,
)
from ide.diagramm.struktogramm import (
    MINDESTHOEHE,
    STANDARDBREITE,
    struktogramm_layout,
)


def _leer() -> dict:
    return {
        "format": "pdiag/1",
        "type": "struktogramm",
        "name": "ampel_zeichnen",
        "page": {"size": "A4", "orientation": "portrait"},
        "style": "modern-light",
        "root": {"id": "b0", "kind": "sequence", "children": []},
    }


def _mit_bloecken(*arten: str) -> dict:
    daten = _leer()
    for art in arten:
        einfuegen(
            Einfuegestelle(daten["root"], "children", 999),
            neuer_block(daten, art),
        )
    return daten


# -- Baum ----------------------------------------------------------------


def test_neuer_block_bekommt_eine_freie_kennung() -> None:
    daten = _mit_bloecken("statement", "statement")

    kennungen = [block["id"] for block in alle_bloecke(daten)]

    assert len(set(kennungen)) == len(kennungen)
    assert neue_id(daten) not in kennungen


def test_neue_verzweigung_hat_beide_zweige() -> None:
    block = neuer_block(_leer(), "branch")

    assert block["then"] == [] and block["else"] == []


def test_neue_mehrfachauswahl_hat_zwei_faelle() -> None:
    """Mit nur einem Fall wäre es keine Auswahl."""
    block = neuer_block(_leer(), "multi_branch")

    assert len(block["cases"]) == 2


def test_einfuegen_setzt_den_block_an_die_gewuenschte_stelle() -> None:
    daten = _mit_bloecken("statement", "statement")
    neu = neuer_block(daten, "call")

    einfuegen(Einfuegestelle(daten["root"], "children", 1), neu)

    assert daten["root"]["children"][1] is neu


def test_einfuegen_in_einen_zweig() -> None:
    daten = _mit_bloecken("branch")
    verzweigung = daten["root"]["children"][0]
    neu = neuer_block(daten, "statement")

    einfuegen(Einfuegestelle(verzweigung, "else", 0), neu)

    assert verzweigung["else"] == [neu]
    assert verzweigung["then"] == []


def test_einfuegen_in_einen_fall_der_mehrfachauswahl() -> None:
    daten = _mit_bloecken("multi_branch")
    auswahl = daten["root"]["children"][0]
    neu = neuer_block(daten, "statement")

    einfuegen(Einfuegestelle(auswahl, "children", 0, fall=1), neu)

    assert auswahl["cases"][1]["children"] == [neu]
    assert auswahl["cases"][0]["children"] == []


def test_entfernen_gibt_die_alte_stelle_zurueck() -> None:
    """Damit „Rückgängig“ den Block genau dorthin zurücksetzen kann."""
    daten = _mit_bloecken("statement", "call", "jump")
    mitte = daten["root"]["children"][1]

    stelle = entfernen(daten, mitte)

    assert stelle is not None and stelle.index == 1
    assert mitte not in daten["root"]["children"]

    einfuegen(stelle, mitte)
    assert daten["root"]["children"][1] is mitte


def test_entfernen_nimmt_den_inhalt_mit() -> None:
    daten = _mit_bloecken("head_loop")
    schleife = daten["root"]["children"][0]
    innen = neuer_block(daten, "statement")
    einfuegen(Einfuegestelle(schleife, "children", 0), innen)

    entfernen(daten, schleife)

    assert alle_bloecke(daten) == [daten["root"]]
    assert schleife["children"] == [innen]


def test_elternteil_findet_den_umgebenden_block() -> None:
    daten = _mit_bloecken("branch")
    verzweigung = daten["root"]["children"][0]
    innen = neuer_block(daten, "statement")
    einfuegen(Einfuegestelle(verzweigung, "then", 0), innen)

    eltern, liste = elternteil(daten, innen)

    assert eltern is verzweigung
    assert liste is verzweigung["then"]


def test_wurzel_hat_keinen_elternteil() -> None:
    daten = _leer()

    assert elternteil(daten, daten["root"]) is None


def test_kinder_sammelt_aus_allen_listen() -> None:
    daten = _leer()
    verzweigung = neuer_block(daten, "branch")
    ja = neuer_block(daten, "statement")
    nein = neuer_block(daten, "call")
    einfuegen(Einfuegestelle(verzweigung, "then", 0), ja)
    einfuegen(Einfuegestelle(verzweigung, "else", 0), nein)

    assert kinder(verzweigung) == [ja, nein]


def test_block_kann_nicht_in_sich_selbst_gezogen_werden(  # Zyklus im Baum
) -> None:
    daten = _leer()
    aussen = neuer_block(daten, "head_loop")
    innen = neuer_block(daten, "statement")
    einfuegen(Einfuegestelle(aussen, "children", 0), innen)

    assert ist_nachfahre(aussen, innen) is True
    assert ist_nachfahre(innen, aussen) is False


# -- Fälle der Mehrfachauswahl -------------------------------------------


def test_fall_hinzufuegen_haengt_eine_spalte_an() -> None:
    daten = _mit_bloecken("multi_branch")
    auswahl = daten["root"]["children"][0]

    fall_hinzufuegen(auswahl)

    assert len(auswahl["cases"]) == 3
    assert auswahl["cases"][-1]["label"] == "Fall 3"


def test_fall_entfernen_nimmt_die_spalte_weg() -> None:
    daten = _mit_bloecken("multi_branch")
    auswahl = daten["root"]["children"][0]
    fall_hinzufuegen(auswahl)

    fall_entfernen(auswahl, 0)

    assert [f["label"] for f in auswahl["cases"]] == ["Fall 2", "Fall 3"]


def test_letzter_fall_bleibt_stehen() -> None:
    """Eine Mehrfachauswahl ohne Fall wäre kein sinnvoller Block."""
    daten = _mit_bloecken("multi_branch")
    auswahl = daten["root"]["children"][0]
    fall_entfernen(auswahl, 0)

    assert fall_entfernen(auswahl, 0) is None
    assert len(auswahl["cases"]) == 1


# -- Layout --------------------------------------------------------------


def test_leeres_struktogramm_hat_trotzdem_hoehe() -> None:
    """Sonst gäbe es keine Fläche, in die der erste Block gezogen
    werden kann."""
    wurzel = struktogramm_layout(_leer())

    assert wurzel.rechteck.height() >= MINDESTHOEHE
    assert wurzel.rechteck.width() == STANDARDBREITE


def test_bloecke_liegen_untereinander_ohne_luecke() -> None:
    daten = _mit_bloecken("statement", "statement", "call")

    kaesten = struktogramm_layout(daten).kinder

    for oberer, unterer in zip(kaesten, kaesten[1:], strict=False):
        assert oberer.rechteck.bottom() == pytest.approx(unterer.rechteck.top())


def test_alle_bloecke_nutzen_die_volle_breite() -> None:
    daten = _mit_bloecken("statement", "head_loop")

    for kasten in struktogramm_layout(daten).kinder:
        assert kasten.rechteck.left() == 0
        assert kasten.rechteck.width() == pytest.approx(STANDARDBREITE)


def test_verzweigung_teilt_die_breite_auf_beide_zweige() -> None:
    daten = _mit_bloecken("branch")
    verzweigung = daten["root"]["children"][0]
    einfuegen(Einfuegestelle(verzweigung, "then", 0), neuer_block(daten, "statement"))
    einfuegen(Einfuegestelle(verzweigung, "else", 0), neuer_block(daten, "call"))

    kasten = struktogramm_layout(daten).kinder[0]
    ja, nein = kasten.kinder

    assert ja.rechteck.width() == pytest.approx(nein.rechteck.width())
    assert ja.rechteck.right() == pytest.approx(nein.rechteck.left())


def test_beide_zweige_enden_unten_buendig() -> None:
    """Abschnitt 13.5: der Rahmen muss geschlossen bleiben – der kürzere
    Zweig wird auf die Höhe des längeren gezogen."""
    daten = _mit_bloecken("branch")
    verzweigung = daten["root"]["children"][0]
    einfuegen(Einfuegestelle(verzweigung, "then", 0), neuer_block(daten, "statement"))
    for _ in range(3):
        einfuegen(Einfuegestelle(verzweigung, "else", 0), neuer_block(daten, "statement"))

    kasten = struktogramm_layout(daten).kinder[0]
    # je Spalte den untersten Block nehmen - Zwischenblöcke enden
    # natürlich weiter oben
    spalten: dict[float, float] = {}
    for kind in kasten.kinder:
        links = round(kind.rechteck.left(), 3)
        spalten[links] = max(spalten.get(links, 0), kind.rechteck.bottom())

    assert len(spalten) == 2
    for unterkante in spalten.values():
        assert unterkante == pytest.approx(kasten.rechteck.bottom())


def test_schleifenkoerper_ist_eingerueckt() -> None:
    daten = _mit_bloecken("head_loop")
    schleife = daten["root"]["children"][0]
    einfuegen(Einfuegestelle(schleife, "children", 0), neuer_block(daten, "statement"))

    kasten = struktogramm_layout(daten).kinder[0]
    koerper = kasten.kinder[0]

    assert koerper.rechteck.left() > kasten.rechteck.left()
    assert koerper.rechteck.right() == pytest.approx(kasten.rechteck.right())


def test_kopfgesteuerte_schleife_hat_den_kopf_oben() -> None:
    daten = _mit_bloecken("head_loop")
    schleife = daten["root"]["children"][0]
    einfuegen(Einfuegestelle(schleife, "children", 0), neuer_block(daten, "statement"))

    kasten = struktogramm_layout(daten).kinder[0]

    assert kasten.kopf.top() == pytest.approx(kasten.rechteck.top())


def test_fussgesteuerte_schleife_hat_den_kopf_unten() -> None:
    daten = _mit_bloecken("foot_loop")
    schleife = daten["root"]["children"][0]
    einfuegen(Einfuegestelle(schleife, "children", 0), neuer_block(daten, "statement"))

    kasten = struktogramm_layout(daten).kinder[0]

    assert kasten.kopf.bottom() == pytest.approx(kasten.rechteck.bottom())


def test_mehrfachauswahl_bekommt_eine_spalte_je_fall() -> None:
    daten = _mit_bloecken("multi_branch")
    auswahl = daten["root"]["children"][0]
    fall_hinzufuegen(auswahl)

    kasten = struktogramm_layout(daten).kinder[0]

    assert len(kasten.zweige) == 3
    breiten = {round(bereich.width(), 3) for _, bereich in kasten.zweige}
    assert len(breiten) == 1


def test_verschachtelung_bleibt_im_rahmen() -> None:
    """Eine Schleife in einem Zweig einer Verzweigung darf nicht über
    den Rand ihres Zweigs hinauslaufen."""
    daten = _mit_bloecken("branch")
    verzweigung = daten["root"]["children"][0]
    schleife = neuer_block(daten, "head_loop")
    einfuegen(Einfuegestelle(verzweigung, "then", 0), schleife)
    einfuegen(Einfuegestelle(schleife, "children", 0), neuer_block(daten, "statement"))

    wurzel = struktogramm_layout(daten)
    aussen = wurzel.kinder[0]

    for kasten in wurzel.alle():
        assert kasten.rechteck.left() >= aussen.rechteck.left() - 0.01
        assert kasten.rechteck.right() <= aussen.rechteck.right() + 0.01
        assert kasten.rechteck.bottom() <= aussen.rechteck.bottom() + 0.01


def test_langer_text_macht_den_block_hoeher() -> None:
    daten = _mit_bloecken("statement")
    kurz = struktogramm_layout(daten).kinder[0].rechteck.height()

    daten["root"]["children"][0]["text"] = "sehr langer Text " * 20
    lang = struktogramm_layout(daten).kinder[0].rechteck.height()

    assert lang > kurz
