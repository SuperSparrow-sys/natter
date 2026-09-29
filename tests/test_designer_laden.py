"""Tests für ide/designer/laden.py: formular_fuer_designer_laden(). Siehe
Arbeitspaket M3, Schritt 3. Gegen die echte
`beispielprojekte/04_CookieKlicker/u_main.pfm` geprüft.
"""

from pathlib import Path

from ide.designer import DesignerCanvas, formular_fuer_designer_laden

_PFM = (
    Path(__file__).resolve().parent.parent / "beispielprojekte" / "04_CookieKlicker" / "u_main.pfm"
)


def test_laedt_form_mit_allen_kindern_und_werten_aus_der_pfm() -> None:
    formular = formular_fuer_designer_laden(_PFM)

    assert formular.caption == "Cookie-Klicker"
    assert formular.b_teig.caption == "Besserer Teig"
    assert formular.i_keks.width == 300
    assert formular.t_helfer.interval == 1000


def test_referenzierte_handler_existieren_als_wirkungslose_platzhalter() -> None:
    formular = formular_fuer_designer_laden(_PFM)

    # löst weder AttributeError (fehlende Methode) noch eine echte
    # Programmwirkung aus - reine Designer-Vorschau (Abschnitt 4.2)
    formular.b_teig.on_click(formular.b_teig)


def test_platzhalter_tragen_den_echten_handlernamen() -> None:
    """Regressionstest: die Platzhalter waren zuerst anonyme Lambdas mit
    `__name__ == "<lambda>"`, das brach das Zurückschreiben in die .pfm
    (ide/designer/pfm_schreiben.py liest `handler.__name__` aus)."""
    formular = formular_fuer_designer_laden(_PFM)

    assert formular.on_create.__name__ == "form_create"
    assert formular.b_teig.on_click.__name__ == "b_teig_click"


def test_kann_in_einen_designer_canvas_eingehaengt_werden() -> None:
    formular = formular_fuer_designer_laden(_PFM)
    canvas = DesignerCanvas(formular)

    getroffen = canvas.klick_bei(
        formular.b_teig.left + 5, formular.b_teig.top + 5
    )

    assert getroffen is formular.b_teig


def _pfm_mit_knopf_im_panel(tmp_path: Path, unit: str) -> Path:
    """Ein Knopf in einem Panel, dessen Methode `b_innen_click` in der
    Unit fehlt (Punkt 115)."""
    import json

    pfm = {
        "format": "pfm/1",
        "class": "Form1",
        "type": "Form",
        "properties": {"width": 300, "height": 200},
        "children": [
            {
                "name": "p_feld",
                "type": "Panel",
                "properties": {"left": 8, "top": 8, "width": 200, "height": 120},
                "children": [
                    {
                        "name": "b_innen",
                        "type": "Button",
                        "properties": {"left": 8, "top": 8},
                        "events": {"on_click": "b_innen_click"},
                    }
                ],
            }
        ],
    }
    pfm_pfad = tmp_path / "u_main.pfm"
    pfm_pfad.write_text(json.dumps(pfm), encoding="utf-8")
    (tmp_path / "u_main.py").write_text(unit, encoding="utf-8")
    return pfm_pfad


def test_fehlende_methode_eines_knopfs_im_panel(tmp_path: Path) -> None:
    pfm_pfad = _pfm_mit_knopf_im_panel(
        tmp_path,
        "from u_main_design import Form1Design\n\n\n"
        "class Form1(Form1Design):\n    pass\n",
    )

    formular = formular_fuer_designer_laden(pfm_pfad)

    assert formular.b_innen.on_click.__name__ == "b_innen_click"


def test_unit_mit_syntaxfehler_und_knopf_im_panel(tmp_path: Path) -> None:
    pfm_pfad = _pfm_mit_knopf_im_panel(
        tmp_path,
        "class Form1(Form1Design)\n    def b_innen_click(self, sender):\n"
        "        pass\n",
    )

    formular = formular_fuer_designer_laden(pfm_pfad)

    assert formular.b_innen.on_click.__name__ == "b_innen_click"


def test_bildpfad_auf_anderen_rechner_bleibt_im_designer_unberuehrt(
    tmp_path: Path, monkeypatch
) -> None:
    """Punkt 334: ein UNC-Pfad als `icon` oder `picture` in der `.pfm`
    führt im Designer zu keinem Zugriff auf diesen Pfad, ein Bild im
    Projektordner wird weiter geladen. Die Adresse ist eine
    Dokumentationsadresse und wird nie aufgerufen: `QPixmap`, `QIcon`
    und `Path.exists` sind durch Aufzeichner ersetzt."""
    import json
    import shutil

    from PySide6.QtGui import QIcon, QPixmap

    import pcl.components.additional as additional
    import pcl.form

    ordner = tmp_path / "Keks"
    shutil.copytree(_PFM.parent, ordner)
    (ordner / "assets").mkdir(exist_ok=True)
    probe = QPixmap(4, 4)
    probe.fill()
    probe.save(str(ordner / "assets" / "probe.png"))
    pfm_pfad = ordner / "u_main.pfm"
    pfm = json.loads(pfm_pfad.read_text(encoding="utf-8"))
    unc = "//192.0.2.1/bilder/symbol.png".replace("/", "\\")
    pfm["properties"]["icon"] = unc
    for kind in pfm["children"]:
        if kind["name"] == "i_keks":
            kind["properties"]["picture"] = unc
    pfm["children"].append({
        "name": "i_probe",
        "type": "Image",
        "properties": {"picture": "assets/probe.png"},
        "events": {},
    })
    pfm_pfad.write_text(json.dumps(pfm), encoding="utf-8")

    angefasst: list[str] = []

    def pixmap(*args):
        angefasst.extend(a for a in args if isinstance(a, str))
        if any("192.0.2.1" in str(a) for a in args):
            return QPixmap()
        return QPixmap(*args)

    def icon(*args):
        angefasst.extend(a for a in args if isinstance(a, str))
        return QIcon()

    echtes_exists = Path.exists

    def exists(self, *args, **kwargs):
        angefasst.append(str(self))
        if "192.0.2.1" in str(self):
            return False
        return echtes_exists(self, *args, **kwargs)

    echtes_resolve = Path.resolve

    def resolve(self, *args, **kwargs):
        if "192.0.2.1" in str(self):
            angefasst.append(str(self))
            return self
        return echtes_resolve(self, *args, **kwargs)

    monkeypatch.setattr(additional, "QPixmap", pixmap)
    monkeypatch.setattr(pcl.form, "QIcon", icon)
    monkeypatch.setattr(Path, "exists", exists)
    monkeypatch.setattr(Path, "resolve", resolve)

    formular = formular_fuer_designer_laden(pfm_pfad)

    assert [p for p in angefasst if "192.0.2.1" in p] == []
    assert formular.i_keks.picture.file == unc
    assert formular.i_keks.picture.original.isNull()
    assert not formular.i_probe.picture.original.isNull()
