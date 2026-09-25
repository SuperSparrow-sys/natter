"""Tests für ide/inspector/ereignisse_tabelle.py: EreignisseTabelle.
Headless. Siehe Arbeitspaket M3, Schritt 2.
"""

from ide.inspector.ereignisse_tabelle import KEIN_HANDLER, EreignisseTabelle
from pcl import Button, Form


class _Formular(Form):
    def create_components(self) -> None:
        self.b_ein = Button(self)

    def b_ein_click(self, sender) -> None:
        pass

    def b_ein_mouse_down(self, sender, x, y) -> None:
        pass

    def unpassende_methode(self, a, b) -> None:
        pass


def test_zeigt_alle_ereignisse_der_komponente() -> None:
    formular = _Formular()
    tabelle = EreignisseTabelle()

    tabelle.anzeigen(formular.b_ein, formular)

    gezeigt = [tabelle.item(z, 0).text() for z in range(tabelle.rowCount())]

    # Seit M15 hat jede sichtbare Komponente die fünf Maus-Ereignisse
    # (vorher stand hier nur `on_click` des Buttons).
    assert gezeigt == [
        "on_click",
        "on_double_click",
        "on_mouse_down",
        "on_mouse_move",
        "on_mouse_up",
    ]


def test_dropdown_enthaelt_nur_passende_methoden() -> None:
    formular = _Formular()
    tabelle = EreignisseTabelle()

    tabelle.anzeigen(formular.b_ein, formular)

    auswahl = tabelle.cellWidget(0, 1)
    eintraege = [auswahl.itemText(i) for i in range(auswahl.count())]
    assert "b_ein_click" in eintraege
    assert "unpassende_methode" not in eintraege
    assert KEIN_HANDLER in eintraege


def test_ohne_verknuepften_handler_zeigt_kein_handler() -> None:
    formular = _Formular()
    tabelle = EreignisseTabelle()

    tabelle.anzeigen(formular.b_ein, formular)

    auswahl = tabelle.cellWidget(0, 1)
    assert auswahl.currentText() == KEIN_HANDLER


def test_auswahl_verknuepft_den_handler_und_er_wird_beim_klick_aufgerufen() -> None:
    aufgerufen = []

    class _FormularMitAufzeichnung(Form):
        def create_components(self) -> None:
            self.b_ein = Button(self)

        def b_ein_click(self, sender) -> None:
            aufgerufen.append(sender)

    formular = _FormularMitAufzeichnung()
    tabelle = EreignisseTabelle()
    tabelle.anzeigen(formular.b_ein, formular)

    auswahl = tabelle.cellWidget(0, 1)
    auswahl.setCurrentText("b_ein_click")

    assert formular.b_ein.on_click == formular.b_ein_click

    formular.b_ein._qwidget.click()
    assert aufgerufen == [formular.b_ein]


def test_bereits_gesetzter_handler_wird_vorausgewaehlt() -> None:
    formular = _Formular()
    formular.b_ein.on_click = formular.b_ein_click
    tabelle = EreignisseTabelle()

    tabelle.anzeigen(formular.b_ein, formular)

    auswahl = tabelle.cellWidget(0, 1)
    assert auswahl.currentText() == "b_ein_click"


def test_kein_handler_ausgewaehlt_entfernt_die_verknuepfung() -> None:
    formular = _Formular()
    formular.b_ein.on_click = formular.b_ein_click
    tabelle = EreignisseTabelle()
    tabelle.anzeigen(formular.b_ein, formular)

    auswahl = tabelle.cellWidget(0, 1)
    auswahl.setCurrentText(KEIN_HANDLER)

    assert formular.b_ein.on_click is None


# --------------------------------------------- Signatur je Ereignis
#
# Bis September 2026 liess der Filter nur Methoden mit genau einem
# Parameter ausser `self` durch. Das stimmte, solange jedes Ereignis
# `(self, sender)` war. Die Maus-Ereignisse aus M15 uebergeben `x` und
# `y` - eine richtig geschriebene Methode fiel damit durch den Filter
# und erschien nie im Auswahlfeld, ohne jede Meldung.


def _auswahl_fuer(tabelle: EreignisseTabelle, ereignis: str):
    for zeile in range(tabelle.rowCount()):
        if tabelle.item(zeile, 0).text() == ereignis:
            return tabelle.cellWidget(zeile, 1)
    raise AssertionError(f"Zeile {ereignis} gibt es nicht")


def _eintraege(auswahl) -> list[str]:
    return [auswahl.itemText(i) for i in range(auswahl.count())]


def test_eine_maus_methode_wird_angeboten() -> None:
    """Der eigentliche Fehler: sie wurde es nicht."""
    formular = _Formular()
    tabelle = EreignisseTabelle()

    tabelle.anzeigen(formular.b_ein, formular)

    assert "b_ein_mouse_down" in _eintraege(_auswahl_fuer(tabelle, "on_mouse_down"))


def test_eine_klick_methode_steht_nicht_bei_mouse_down() -> None:
    """Eine Methode fuer `on_click` passt nicht auf `on_mouse_down` -
    sie bekaeme zwei Zahlen, mit denen sie nichts anfangen kann."""
    formular = _Formular()
    tabelle = EreignisseTabelle()

    tabelle.anzeigen(formular.b_ein, formular)

    assert "b_ein_click" not in _eintraege(_auswahl_fuer(tabelle, "on_mouse_down"))


def test_eine_maus_methode_steht_nicht_bei_click() -> None:
    formular = _Formular()
    tabelle = EreignisseTabelle()

    tabelle.anzeigen(formular.b_ein, formular)

    assert "b_ein_mouse_down" not in _eintraege(_auswahl_fuer(tabelle, "on_click"))


def test_die_zellen_methoden_des_stringgrid_werden_angeboten() -> None:
    """`on_select_cell` bekommt Spalte und Zeile, `on_edit_cell`
    zusaetzlich den neuen Text - drei Parameter ausser `self`."""
    from pcl.components.additional import StringGrid

    class _Tabellenformular(Form):
        def create_components(self) -> None:
            self.sg = StringGrid(self)

        def sg_select_cell(self, sender, spalte, zeile) -> None:
            pass

        def sg_edit_cell(self, sender, spalte, zeile, text) -> None:
            pass

    formular = _Tabellenformular()
    tabelle = EreignisseTabelle()
    tabelle.anzeigen(formular.sg, formular)

    assert "sg_select_cell" in _eintraege(_auswahl_fuer(tabelle, "on_select_cell"))
    assert "sg_edit_cell" in _eintraege(_auswahl_fuer(tabelle, "on_edit_cell"))
    assert "sg_edit_cell" not in _eintraege(_auswahl_fuer(tabelle, "on_select_cell"))


def test_die_erwartete_parameterzahl_stammt_aus_einer_quelle() -> None:
    """Nicht von Hand gepflegt: sie steht in `EREIGNIS_PARAMETER`."""
    from ide.inspector.ereignisse_tabelle import erwartete_parameter
    from pcl.control import EREIGNIS_PARAMETER

    assert erwartete_parameter("on_click") == 1
    for name, zusatz in EREIGNIS_PARAMETER.items():
        assert erwartete_parameter(name) == 1 + len(zusatz), name


# ------------------------------------------------- Methoden anlegen
#
# Bis September 2026 konnte der Reiter nur verknuepfen, was schon da
# war. Fuer alles ausser dem einen kennzeichnenden Ereignis - das der
# Doppelklick im Designer anlegt - blieb nur, die Methode von Hand zu
# schreiben. Jetzt legt ein Doppelklick auf die Zeile sie an.


def test_ein_doppelklick_legt_die_methode_an() -> None:
    formular = _Formular()
    tabelle = EreignisseTabelle()
    angelegt: list[tuple] = []

    def anlegen(komponente, ereignis):
        angelegt.append((komponente, ereignis))
        return f"b_ein_{ereignis.removeprefix('on_')}"

    tabelle.anzeigen(formular.b_ein, formular, methode_anlegen=anlegen)
    zeile = [
        z for z in range(tabelle.rowCount())
        if tabelle.item(z, 0).text() == "on_double_click"
    ][0]

    tabelle.cellDoubleClicked.emit(zeile, 0)

    assert angelegt == [(formular.b_ein, "on_double_click")]


def test_ohne_anleger_passiert_nichts() -> None:
    """Ohne offene Unit gibt es niemanden, der schreiben koennte."""
    formular = _Formular()
    tabelle = EreignisseTabelle()
    tabelle.anzeigen(formular.b_ein, formular)

    tabelle.cellDoubleClicked.emit(0, 0)  # darf nicht abstuerzen


def test_nach_dem_anlegen_steht_die_methode_im_auswahlfeld() -> None:
    """Sonst muesste man den Reiter erst wechseln, um sein eigenes
    Ergebnis zu sehen."""
    formular = _Formular()
    tabelle = EreignisseTabelle()

    def anlegen(komponente, ereignis):
        # So tut es der Designer auch: Methode anlegen und verknuepfen.
        def platzhalter(self, sender, x, y):
            pass

        type(formular).b_ein_mouse_up = platzhalter
        return "b_ein_mouse_up"

    tabelle.anzeigen(formular.b_ein, formular, methode_anlegen=anlegen)
    zeile = [
        z for z in range(tabelle.rowCount()) if tabelle.item(z, 0).text() == "on_mouse_up"
    ][0]

    tabelle.cellDoubleClicked.emit(zeile, 0)

    try:
        assert "b_ein_mouse_up" in _eintraege(_auswahl_fuer(tabelle, "on_mouse_up"))
    finally:
        delattr(type(formular), "b_ein_mouse_up")
