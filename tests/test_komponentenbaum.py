"""Tests für ide/inspector/komponentenbaum.py: Komponentenbaum. Headless.
Siehe docs/arbeitspakete/M3.md, Schritt 2.
"""

from ide.inspector.komponentenbaum import KOMPONENTE_ROLLE, Komponentenbaum
from pcl import Button, Form, Shape


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)
        self.s_rot = Shape(self)


def test_wurzel_ist_das_formular() -> None:
    formular = _Formular()
    baum = Komponentenbaum()

    baum.formular_anzeigen(formular)

    assert baum.topLevelItemCount() == 1
    wurzel = baum.topLevelItem(0)
    assert wurzel.text(0) == "_Formular: Form"
    assert wurzel.data(0, KOMPONENTE_ROLLE) is formular


def test_kinder_in_erzeugungsreihenfolge_mit_typ() -> None:
    formular = _Formular()
    baum = Komponentenbaum()

    baum.formular_anzeigen(formular)

    wurzel = baum.topLevelItem(0)
    assert wurzel.childCount() == 2
    assert wurzel.child(0).text(0) == "b_ein: Button"
    assert wurzel.child(0).data(0, KOMPONENTE_ROLLE) is formular.b_ein
    assert wurzel.child(1).text(0) == "s_rot: Shape"
    assert wurzel.child(1).data(0, KOMPONENTE_ROLLE) is formular.s_rot


def test_erneutes_anzeigen_ersetzt_den_baum() -> None:
    formular = _Formular()
    baum = Komponentenbaum()

    baum.formular_anzeigen(formular)
    baum.formular_anzeigen(formular)

    assert baum.topLevelItemCount() == 1
    assert baum.topLevelItem(0).childCount() == 2


# ------------------------------------------------------------- Symbole
#
# Der Komponentenbaum blieb bei M15 eine Textliste, waehrend die Palette
# daneben ihre Symbole bekam. Auf einem Formular mit fuenfzehn Kindern
# ist "b_ok: Button" in einer Spalte gleich langer Zeilen schwerer zu
# finden als ein Knopf-Symbol - und die Zuordnung zur Palette geht dabei
# ganz verloren.


def test_jede_zeile_traegt_ein_symbol() -> None:
    baum = Komponentenbaum()

    baum.formular_anzeigen(_Formular())

    wurzel = baum.topLevelItem(0)
    assert not wurzel.icon(0).isNull(), "Das Formular selbst hat keines"
    for i in range(wurzel.childCount()):
        kind = wurzel.child(i)
        assert not kind.icon(0).isNull(), kind.text(0)


def test_die_symbolnamen_sind_dieselben_wie_in_der_palette() -> None:
    """Beide leiten den Namen aus dem Klassennamen ab. Eine Liste, die
    auseinanderlaufen kann, gibt es bewusst nicht - deshalb wird hier
    die Regel geprueft, nicht eine Zuordnung."""
    from ide.inspector.komponentenbaum import symbolname
    from ide.palette.palette import ALLE_KOMPONENTEN

    formular = _Formular()
    assert symbolname(formular.b_ein) == "komponente_button"
    assert symbolname(formular) == "komponente_form"

    from pathlib import Path

    vorhanden = {p.stem for p in Path("ide/assets/icons").glob("komponente_*.svg")}
    fehlen = [t.__name__ for t in ALLE_KOMPONENTEN if symbolname(t(formular)) not in vorhanden]
    assert not fehlen, f"Ohne Symbol: {fehlen}"


def test_nach_einem_themewechsel_steht_der_baum_noch() -> None:
    """Ein `QIcon` merkt sich seine Farben - deshalb wird der Baum neu
    aufgebaut. Dabei darf er nicht leer zurueckbleiben."""
    baum = Komponentenbaum()
    baum.formular_anzeigen(_Formular())

    baum.symbole_erneuern("dark")

    wurzel = baum.topLevelItem(0)
    assert wurzel.childCount() == 2
    assert not wurzel.child(0).icon(0).isNull()


def test_ohne_formular_tut_ein_themewechsel_nichts() -> None:
    Komponentenbaum().symbole_erneuern("dark")
