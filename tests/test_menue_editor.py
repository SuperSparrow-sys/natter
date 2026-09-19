"""Tests für `ide/inspector/menue_editor.py` und die Wege dorthin:
Objektinspektor, Designer, `.pfm` und erzeugter Quelltext. Headless.

Siehe `docs/arbeitspakete/M15.md`, Schritt 1.
"""

import json

from ide.codegen.design import design_code_erzeugen
from ide.designer.canvas import DesignerCanvas
from ide.designer.pfm_schreiben import formular_als_pfm_speichern
from ide.inspector.menue_editor import OHNE_BESCHRIFTUNG, TRENNLINIE_TEXT, MenueEditor
from pcl import Form, MainMenu

MENUE = [
    {
        "name": "mi_datei",
        "caption": "&Datei",
        "children": [
            {"name": "mi_neu", "caption": "&Neu", "shortcut": "Strg+N"},
            {"name": "mi_ende", "caption": "B&eenden"},
        ],
    },
    {"name": "mi_hilfe", "caption": "&Hilfe"},
]


class _Formular(Form):
    def create_components(self) -> None:
        self.mm_haupt = MainMenu(self)
        self.mm_haupt.entries = MENUE


def _editor(qtbot, eintraege=None) -> MenueEditor:
    editor = MenueEditor(MENUE if eintraege is None else eintraege)
    qtbot.addWidget(editor)
    return editor


def _waehlen(editor: MenueEditor, *pfad: int) -> None:
    zeile = editor.baum.topLevelItem(pfad[0])
    for weiter in pfad[1:]:
        zeile = zeile.child(weiter)
    editor.baum.setCurrentItem(zeile)


# -- Der Baum -----------------------------------------------------------


def test_der_baum_zeigt_die_eintraege_mit_ihren_untereintraegen(qtbot) -> None:
    editor = _editor(qtbot)

    assert editor.baum.topLevelItemCount() == 2
    assert editor.baum.topLevelItem(0).childCount() == 2
    assert editor.baum.topLevelItem(0).text(0) == "&Datei"


def test_das_tastenkuerzel_steht_in_der_zeile(qtbot) -> None:
    editor = _editor(qtbot)

    assert editor.baum.topLevelItem(0).child(0).text(0) == "&Neu\tStrg+N"


def test_ein_eintrag_ohne_beschriftung_ist_trotzdem_anklickbar(qtbot) -> None:
    """Eine leere Zeile wäre im Baum nicht zu sehen und damit nicht zu
    treffen."""
    editor = _editor(qtbot, [{"name": "mi_leer"}])

    assert editor.baum.topLevelItem(0).text(0) == OHNE_BESCHRIFTUNG


def test_eine_trennlinie_sieht_im_baum_auch_wie_eine_aus(qtbot) -> None:
    editor = _editor(qtbot, [{"separator": True}])

    assert editor.baum.topLevelItem(0).text(0) == TRENNLINIE_TEXT


# -- Anlegen, Umsortieren, Löschen --------------------------------------


def test_neu_legt_auf_derselben_ebene_an(qtbot) -> None:
    editor = _editor(qtbot)
    _waehlen(editor, 0)

    editor._neu()

    assert [e["caption"] for e in editor.entwurf] == ["&Datei", "Neuer Eintrag", "&Hilfe"]


def test_untereintrag_haengt_unter_den_ausgewaehlten(qtbot) -> None:
    editor = _editor(qtbot)
    _waehlen(editor, 1)

    editor._untereintrag()

    assert [e["caption"] for e in editor.entwurf[1]["children"]] == ["Neuer Eintrag"]


def test_unter_einen_untereintrag_geht_nichts_mehr(qtbot) -> None:
    """Menüs gehen bis zur zweiten Ebene. Ein grauer Knopf ist
    ehrlicher als ein Eintrag, der später beim Speichern abgelehnt
    wird."""
    editor = _editor(qtbot)
    _waehlen(editor, 0, 0)

    assert editor.unter_knopf.isEnabled() is False
    editor._untereintrag()
    assert editor.entwurf[0]["children"][0]["children"] == []


def test_eine_trennlinie_kommt_hinter_den_ausgewaehlten(qtbot) -> None:
    editor = _editor(qtbot)
    _waehlen(editor, 0)

    editor._trennlinie()

    assert editor.entwurf[1]["separator"] is True


def test_loeschen_nimmt_den_ausgewaehlten_weg(qtbot) -> None:
    editor = _editor(qtbot)
    _waehlen(editor, 0, 1)

    editor._loeschen()

    assert [e["caption"] for e in editor.entwurf[0]["children"]] == ["&Neu"]


def test_umsortieren_vertauscht_zwei_eintraege(qtbot) -> None:
    editor = _editor(qtbot)
    _waehlen(editor, 0)

    editor._schieben(1)

    assert [e["caption"] for e in editor.entwurf] == ["&Hilfe", "&Datei"]


def test_umsortieren_ueber_den_rand_hinaus_tut_nichts(qtbot) -> None:
    editor = _editor(qtbot)
    _waehlen(editor, 0)

    editor._schieben(-1)

    assert [e["caption"] for e in editor.entwurf] == ["&Datei", "&Hilfe"]


def test_der_verschobene_eintrag_bleibt_ausgewaehlt(qtbot) -> None:
    """Sonst müsste man nach jedem Klick auf ▼ neu auswählen, um noch
    einmal zu schieben."""
    editor = _editor(qtbot)
    _waehlen(editor, 0)

    editor._schieben(1)

    assert editor._gewaehlter_eintrag()["caption"] == "&Datei"


# -- Die Felder ---------------------------------------------------------


def test_die_felder_zeigen_den_ausgewaehlten_eintrag(qtbot) -> None:
    editor = _editor(qtbot)

    _waehlen(editor, 0, 0)

    assert editor.feld_name.text() == "mi_neu"
    assert editor.feld_shortcut.text() == "Strg+N"


def test_tippen_wirkt_sofort_auf_den_datensatz_und_die_zeile(qtbot) -> None:
    editor = _editor(qtbot)
    _waehlen(editor, 1)

    editor.feld_caption.setText("&Extras")

    assert editor.entwurf[1]["caption"] == "&Extras"
    assert editor.baum.topLevelItem(1).text(0) == "&Extras"


def test_eine_trennlinie_hat_keine_felder_auszufuellen(qtbot) -> None:
    editor = _editor(qtbot, [{"separator": True}])

    _waehlen(editor, 0)

    assert editor.eintragsdaten.isEnabled() is False


# -- Anwenden, Schließen ------------------------------------------------


def test_ohne_anwenden_bleibt_das_ergebnis_wie_vorher(qtbot) -> None:
    editor = _editor(qtbot)
    _waehlen(editor, 0)
    editor.feld_caption.setText("&Geändert")

    assert editor.uebernommen is False
    assert [e["caption"] for e in editor.eintraege()] == ["&Datei", "&Hilfe"]


def test_anwenden_uebernimmt_ohne_zu_schliessen(qtbot) -> None:
    editor = _editor(qtbot)
    _waehlen(editor, 0)
    editor.feld_caption.setText("&Geändert")

    editor.anwenden()

    assert editor.uebernommen is True
    assert [e["caption"] for e in editor.eintraege()] == ["&Geändert", "&Hilfe"]


def test_nach_anwenden_weitergeaendertes_bleibt_draussen(qtbot) -> None:
    """„Schließen" verwirft, was seit dem letzten „Anwenden" geändert
    wurde – dieselbe Regel wie im Klassendialog des Diagramm-Editors."""
    editor = _editor(qtbot)
    _waehlen(editor, 0)
    editor.feld_caption.setText("&Erst")
    editor.anwenden()
    editor.feld_caption.setText("&Dann")

    assert [e["caption"] for e in editor.eintraege()] == ["&Erst", "&Hilfe"]


def test_der_editor_arbeitet_auf_einer_kopie(qtbot) -> None:
    ausgangslage = json.dumps(MENUE, sort_keys=True)
    editor = _editor(qtbot)
    _waehlen(editor, 0)

    editor.feld_caption.setText("&Kaputt")

    assert json.dumps(MENUE, sort_keys=True) == ausgangslage


# -- Der Weg über den Designer ------------------------------------------


def test_doppelklick_auf_ein_menue_oeffnet_den_editor(qtbot, monkeypatch) -> None:
    """Ein Menü hat kein Standardereignis. Ohne diesen Weg täte ein
    Doppelklick auf sein Symbol gar nichts – so ein stummer Klick ist
    genau das, was in M11 aufgeräumt wurde."""
    formular = _Formular()
    qtbot.addWidget(formular._qwidget)
    canvas = DesignerCanvas(formular)
    geoeffnet: list[list] = []

    def gefaelschter_editor(eintraege, eltern=None):
        geoeffnet.append(eintraege)
        return _FertigerEditor([{"caption": "&Neu gebaut"}])

    monkeypatch.setattr("ide.inspector.menue_editor.MenueEditor", gefaelschter_editor)

    assert canvas.menue_bearbeiten(formular.mm_haupt) is True
    assert [e["caption"] for e in geoeffnet[0]] == ["&Datei", "&Hilfe"]
    assert [e["caption"] for e in formular.mm_haupt.entries] == ["&Neu gebaut"]


def test_ein_dialogdurchgang_ist_ein_undo_schritt(qtbot, monkeypatch) -> None:
    formular = _Formular()
    qtbot.addWidget(formular._qwidget)
    canvas = DesignerCanvas(formular)
    monkeypatch.setattr(
        "ide.inspector.menue_editor.MenueEditor",
        lambda *_a, **_k: _FertigerEditor([{"caption": "&A"}, {"caption": "&B"}]),
    )

    canvas.menue_bearbeiten(formular.mm_haupt)
    canvas.rueckgaengig()

    assert [e["caption"] for e in formular.mm_haupt.entries] == ["&Datei", "&Hilfe"]


def test_eine_gewoehnliche_komponente_bleibt_unberuehrt(qtbot) -> None:
    from pcl import Button

    formular = _Formular()
    qtbot.addWidget(formular._qwidget)
    canvas = DesignerCanvas(formular)

    assert canvas.menue_bearbeiten(Button(formular)) is False


class _FertigerEditor:
    """Ein Editor, der sofort mit OK und einem festen Ergebnis
    zurückkommt – headless lässt sich `exec()` nicht bedienen."""

    def __init__(self, eintraege: list) -> None:
        self._eintraege = eintraege
        self.uebernommen = True

    def exec(self) -> int:
        return int(MenueEditor.DialogCode.Accepted)

    def eintraege(self) -> list:
        return self._eintraege


# -- .pfm und erzeugter Quelltext ---------------------------------------


def test_die_pfm_traegt_die_eintraege_knapp(tmp_path) -> None:
    """Stünde hinter jedem Eintrag dreimal die Vorgabe, wäre die Datei
    für einen Menschen nicht mehr zu lesen."""
    formular = _Formular()
    ziel = tmp_path / "u_main.pfm"

    formular_als_pfm_speichern(formular, ziel)

    daten = json.loads(ziel.read_text(encoding="utf-8"))
    menue = next(k for k in daten["children"] if k["type"] == "MainMenu")
    assert menue["properties"]["entries"] == MENUE


def test_ein_menue_ohne_eintraege_steht_nicht_in_der_pfm(tmp_path) -> None:
    class Leer(Form):
        def create_components(self) -> None:
            self.mm_haupt = MainMenu(self)

    ziel = tmp_path / "u_main.pfm"
    formular_als_pfm_speichern(Leer(), ziel)

    daten = json.loads(ziel.read_text(encoding="utf-8"))
    menue = next(k for k in daten["children"] if k["type"] == "MainMenu")
    assert "entries" not in menue["properties"]


def test_der_erzeugte_code_weist_die_eintraege_zu() -> None:
    pfm = {
        "format": "pfm/1",
        "class": "UMain",
        "type": "Form",
        "properties": {},
        "children": [
            {
                "name": "mm_haupt",
                "type": "MainMenu",
                "properties": {"entries": [{"caption": "&Datei"}]},
            }
        ],
    }

    quelltext = design_code_erzeugen(pfm, "u_main.pfm")

    assert "self.mm_haupt.entries = [" in quelltext
    assert '{"caption": "&Datei"},' in quelltext


def test_ein_menue_mit_untereintraegen_steht_nicht_in_einer_zeile() -> None:
    """Drei Untermenüs ergaben sonst eine Zeile von über 800 Zeichen.
    Gelesen wird `u_*_design.py` selten - aber wenn, dann weil etwas
    klemmt."""
    pfm = {
        "format": "pfm/1",
        "class": "UMain",
        "type": "Form",
        "properties": {},
        "children": [
            {
                "name": "mm_haupt",
                "type": "MainMenu",
                "properties": {
                    "entries": [
                        {
                            "caption": "&Datei",
                            "children": [{"caption": "&Neu"}, {"caption": "&Ende"}],
                        }
                    ]
                },
            }
        ],
    }

    zeilen = design_code_erzeugen(pfm, "u_main.pfm").splitlines()

    assert max(len(zeile) for zeile in zeilen) < 100
    assert '                {"caption": "&Neu"},' in zeilen


def test_der_erzeugte_code_ist_bei_gleicher_pfm_immer_derselbe() -> None:
    """Sonst meldete Git bei jedem Speichern eine Änderung, die gar
    keine ist – die Schlüssel eines `dict` stehen deshalb sortiert."""
    pfm = {
        "format": "pfm/1",
        "class": "UMain",
        "type": "Form",
        "properties": {},
        "children": [
            {
                "name": "mm_haupt",
                "type": "MainMenu",
                "properties": {
                    "entries": [{"shortcut": "Strg+N", "caption": "&Neu", "name": "mi_neu"}]
                },
            }
        ],
    }

    quelltext = design_code_erzeugen(pfm, "u_main.pfm")

    assert '{"caption": "&Neu", "name": "mi_neu", "shortcut": "Strg+N"},' in quelltext


def test_der_erzeugte_code_laeuft_wirklich(tmp_path) -> None:
    """Ein Quelltext, der aussieht wie Python, ist noch keiner. Dieser
    Test führt ihn aus und sieht im fertigen Fenster nach."""
    pfm = {
        "format": "pfm/1",
        "class": "UMain",
        "type": "Form",
        "properties": {},
        "children": [
            {
                "name": "mm_haupt",
                "type": "MainMenu",
                "properties": {
                    "entries": [{"caption": "&Datei", "children": [{"caption": "&Beenden"}]}]
                },
            }
        ],
    }
    quelltext = design_code_erzeugen(pfm, "u_main.pfm")

    umgebung: dict = {}
    exec(compile(quelltext, "u_main_design.py", "exec"), umgebung)  # noqa: S102
    formular = umgebung["UMainDesign"]()
    formular.show()

    assert [a.text() for a in formular._menueleiste.actions()] == ["&Datei"]
