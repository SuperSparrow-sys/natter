"""Tests für `pcl.analyse.regression` (M10, Punkt 5).

Die Erwartungswerte sind von Hand nachgerechnet: jede Reihe liegt exakt
auf der Kurve, die sie beschreiben soll, damit Steigung, Achsenabschnitt
und R² ohne numerische Unschärfe feststehen (Arbeitspaket: „eine exakt
auf einer Geraden liegende Reihe muss R² = 1 ergeben“).
"""

from __future__ import annotations

import math

import pytest

from pcl.analyse import ARTEN, regression
from pcl.errors import NatterDatenError

# -- Linear --------------------------------------------------------------


def test_linear_trifft_die_von_hand_gerechnete_gerade() -> None:
    # y = 2x + 1 für x = 1..4 ergibt 3, 5, 7, 9.
    ergebnis = regression([1, 2, 3, 4], [3, 5, 7, 9])

    assert ergebnis.steigung == pytest.approx(2.0)
    assert ergebnis.achsenabschnitt == pytest.approx(1.0)
    assert ergebnis.formel == "y = 2,00·x + 1,00"


def test_punkte_genau_auf_einer_geraden_ergeben_bestimmtheitsmass_eins() -> None:
    ergebnis = regression([1, 2, 3, 4], [3, 5, 7, 9])

    assert ergebnis.bestimmtheitsmass == 1.0


def test_streuende_punkte_ergeben_ein_bestimmtheitsmass_unter_eins() -> None:
    # (1|5), (2|5), (3|6): Ausgleichsgerade y = 0,5x + 4,333...
    # Restquadrate 1/6, Gesamtstreuung 2/3 -> R² = 1 - (1/6)/(2/3) = 0,75.
    ergebnis = regression([1, 2, 3], [5, 5, 6])

    assert ergebnis.bestimmtheitsmass == pytest.approx(0.75)


def test_fallende_gerade_bekommt_ein_minus_statt_plus_minus() -> None:
    ergebnis = regression([1, 2, 3], [5, 3, 1])

    assert ergebnis.formel == "y = -2,00·x + 7,00"


def test_vorhersage_liefert_bei_einer_zahl_eine_zahl() -> None:
    ergebnis = regression([1, 2, 3, 4], [3, 5, 7, 9])

    wert = ergebnis.vorhersage(10)

    assert isinstance(wert, float)
    assert wert == pytest.approx(21.0)


def test_vorhersage_liefert_bei_einer_reihe_eine_liste_von_zahlen() -> None:
    ergebnis = regression([1, 2, 3, 4], [3, 5, 7, 9])

    werte = ergebnis.vorhersage([10, 11])

    assert isinstance(werte, list)
    assert werte == pytest.approx([21.0, 23.0])


def test_rechenrauschen_steht_nicht_in_der_formel() -> None:
    # y = 2x geht exakt durch den Ursprung; numpy.polyfit liefert für den
    # Achsenabschnitt aber ein Rauschen in der Größenordnung 1e-16.
    ergebnis = regression([1, 2, 3], [2, 4, 6])

    assert ergebnis.achsenabschnitt == 0.0
    assert ergebnis.formel == "y = 2,00·x"


# -- Polynomial ----------------------------------------------------------


def test_polynomial_grad_zwei_findet_die_normalparabel() -> None:
    ergebnis = regression([1, 2, 3, 4, 5], [1, 4, 9, 16, 25], "polynomial")

    assert ergebnis.grad == 2
    assert ergebnis.koeffizienten[0] == pytest.approx(1.0)
    assert ergebnis.formel == "y = 1,00·x²"
    assert ergebnis.bestimmtheitsmass == 1.0


def test_polynomial_grad_drei_findet_die_kubische_kurve() -> None:
    # y = x³ - 2x für x = -2..2 ergibt -4, 1, 0, -1, 4.
    x = [-2, -1, 0, 1, 2]
    y = [wert**3 - 2 * wert for wert in x]

    ergebnis = regression(x, y, "polynomial", grad=3)

    assert ergebnis.koeffizienten[0] == pytest.approx(1.0)
    assert ergebnis.formel == "y = 1,00·x³ - 2,00·x"
    assert ergebnis.bestimmtheitsmass == pytest.approx(1.0)


def test_polynomial_meldet_einen_unvorgesehenen_grad_auf_deutsch() -> None:
    with pytest.raises(NatterDatenError, match="Grad 2 oder 3"):
        regression([1, 2, 3, 4, 5], [1, 4, 9, 16, 25], "polynomial", grad=7)


def test_polynomiale_steigung_ist_der_koeffizient_des_linearen_glieds() -> None:
    # y = x² + 3x + 5.
    x = [0, 1, 2, 3]
    y = [wert**2 + 3 * wert + 5 for wert in x]

    ergebnis = regression(x, y, "polynomial")

    assert ergebnis.steigung == pytest.approx(3.0)
    assert ergebnis.achsenabschnitt == pytest.approx(5.0)


# -- Exponentiell --------------------------------------------------------


def test_exponentiell_findet_verdopplung_je_schritt() -> None:
    # y = 2·2^x = 2·e^(ln2·x) für x = 0..3 ergibt 2, 4, 8, 16.
    ergebnis = regression([0, 1, 2, 3], [2, 4, 8, 16], "exponentiell")

    assert ergebnis.achsenabschnitt == pytest.approx(2.0)
    assert ergebnis.steigung == pytest.approx(math.log(2))
    assert ergebnis.bestimmtheitsmass == pytest.approx(1.0)
    assert ergebnis.formel == "y = 2,00·e^(0,69·x)"


def test_exponentielle_vorhersage_setzt_die_kurve_fort() -> None:
    ergebnis = regression([0, 1, 2, 3], [2, 4, 8, 16], "exponentiell")

    assert ergebnis.vorhersage(4) == pytest.approx(32.0)


def test_exponentiell_meldet_nicht_positive_y_werte_auf_deutsch() -> None:
    with pytest.raises(NatterDatenError, match="y-Werte größer als 0"):
        regression([1, 2, 3], [1, 0, 3], "exponentiell")


# -- Logarithmisch -------------------------------------------------------


def test_logarithmisch_findet_die_kurve_durch_die_punkte() -> None:
    # y = 3·ln(x) + 1.
    x = [1, 2, 4, 8]
    y = [3 * math.log(wert) + 1 for wert in x]

    ergebnis = regression(x, y, "logarithmisch")

    assert ergebnis.steigung == pytest.approx(3.0)
    assert ergebnis.achsenabschnitt == pytest.approx(1.0)
    assert ergebnis.bestimmtheitsmass == pytest.approx(1.0)
    assert ergebnis.formel == "y = 3,00·ln(x) + 1,00"


def test_logarithmisch_meldet_nicht_positive_x_werte_auf_deutsch() -> None:
    with pytest.raises(NatterDatenError, match="x-Werte größer als 0"):
        regression([0, 1, 2], [1, 2, 3], "logarithmisch")


def test_logarithmische_vorhersage_lehnt_x_kleiner_gleich_null_ab() -> None:
    ergebnis = regression([1, 2, 4, 8], [1, 2, 3, 4], "logarithmisch")

    with pytest.raises(NatterDatenError, match="größer als 0"):
        ergebnis.vorhersage(0)


# -- Fehlerfälle ---------------------------------------------------------


def test_zu_wenige_punkte_ergeben_eine_deutsche_meldung() -> None:
    with pytest.raises(NatterDatenError, match="mindestens 2 Punkte"):
        regression([1], [2])


def test_zu_wenige_punkte_fuer_den_gewaehlten_grad() -> None:
    with pytest.raises(NatterDatenError, match="mindestens 4 Punkte"):
        regression([1, 2, 3], [1, 2, 3], "polynomial", grad=3)


def test_senkrechte_punktwolke_ergibt_eine_deutsche_meldung() -> None:
    with pytest.raises(NatterDatenError, match="senkrechte Punktwolke"):
        regression([2, 2, 2], [1, 5, 9])


def test_zu_wenige_verschiedene_x_werte_ergeben_eine_deutsche_meldung() -> None:
    # Drei Punkte, aber nur zwei x-Stellen: durch sie passen beliebig
    # viele Parabeln. numpy.polyfit warnt hier nur (RankWarning) und
    # rechnet weiter.
    with pytest.raises(NatterDatenError, match="verschiedene x-Werte"):
        regression([1, 1, 2], [1, 2, 3], "polynomial")


def test_unterschiedlich_lange_reihen_ergeben_eine_deutsche_meldung() -> None:
    with pytest.raises(NatterDatenError, match="2 x-Werte und 3 y-Werte"):
        regression([1, 2], [1, 2, 3])


def test_unbekannte_art_nennt_die_moeglichen_arten() -> None:
    with pytest.raises(NatterDatenError) as fehler:
        regression([1, 2], [1, 2], "quadratisch")

    for art in ARTEN:
        assert art in str(fehler.value)


def test_text_statt_zahlen_ergibt_eine_deutsche_meldung() -> None:
    with pytest.raises(NatterDatenError, match="müssen Zahlen sein"):
        regression([1, 2, 3], ["eins", "zwei", "drei"])


def test_dezimalkomma_wird_im_hinweis_erwaehnt() -> None:
    # Häufigster Anfängerfehler mit deutschen Daten.
    with pytest.raises(NatterDatenError, match="3,5 dagegen nicht"):
        regression([1, 2, 3], ["1,5", "2,5", "3,5"])


def test_fehlender_wert_ergibt_eine_deutsche_meldung() -> None:
    with pytest.raises(NatterDatenError, match="fehlenden oder unendlichen"):
        regression([1, 2, 3], [1.0, float("nan"), 3.0])
