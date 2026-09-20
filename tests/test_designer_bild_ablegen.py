"""Tests für Drag & Drop einer Bilddatei in den Formular-Designer
(Abschnitt 11.4, docs/arbeitspakete/M5.md „Zurückgestellt“).

Alle mutierenden Tests laufen gegen `.pfm`-Dateien in `tmp_path` –
niemals gegen eingecheckte Beispielprojekte (AGENTS.md).
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap

from ide.designer.bilder import bild_in_assets_uebernehmen, ist_bilddatei
from ide.designer.canvas import DesignerCanvas
from ide.designer.laden import formular_fuer_designer_laden
from ide.inspector.komponentenbaum import kind_komponenten
from pcl.components.additional import Image
from pcl.components.standard import Button

_PFM = {
    "format": "pfm/1",
    "class": "Form1",
    "type": "Form",
    "properties": {"caption": "Form1", "width": 400, "height": 300},
    "children": [
        {
            "name": "b_start",
            "type": "Button",
            "properties": {"left": 10, "top": 10, "width": 80, "height": 25},
        }
    ],
}


def _bild_schreiben(pfad: Path, breite: int = 40, hoehe: int = 20) -> Path:
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pixmap = QPixmap(breite, hoehe)
    pixmap.fill(Qt.GlobalColor.red)
    assert pixmap.save(str(pfad))
    return pfad


def _kinder(canvas: DesignerCanvas) -> list:
    return list(kind_komponenten(canvas.formular))


def _canvas(tmp_path: Path) -> DesignerCanvas:
    """Designer auf einem Projektordner `tmp_path/projekt`. Die
    abgelegten Bilder liegen bewusst daneben in `tmp_path/extern`, damit
    die Kopie nach `assets/` überhaupt greift (eine Datei, die schon im
    Projekt liegt, wird absichtlich nicht kopiert)."""
    projekt = tmp_path / "projekt"
    projekt.mkdir(exist_ok=True)
    pfm_pfad = projekt / "u_main.pfm"
    pfm_pfad.write_text(json.dumps(_PFM), encoding="utf-8")
    return DesignerCanvas(formular_fuer_designer_laden(pfm_pfad), pfm_pfad=pfm_pfad)


# -- reine Dateiarbeit (ide/designer/bilder.py) ---------------------------


def test_ist_bilddatei_erkennt_endungen() -> None:
    assert ist_bilddatei(Path("a/b/cookie.PNG"))
    assert ist_bilddatei(Path("cookie.jpeg"))
    assert not ist_bilddatei(Path("cookie.txt"))
    assert not ist_bilddatei(Path("cookie"))


def test_bild_wird_nach_assets_kopiert(tmp_path: Path) -> None:
    projekt = tmp_path / "projekt"
    projekt.mkdir()
    quelle = _bild_schreiben(tmp_path / "cookie.png")

    absolut, relativ = bild_in_assets_uebernehmen(quelle, projekt)

    assert relativ == "assets/cookie.png"
    assert absolut == (projekt / "assets" / "cookie.png").resolve()
    assert absolut.read_bytes() == quelle.read_bytes()


def test_bild_im_projekt_wird_nicht_kopiert(tmp_path: Path) -> None:
    projekt = tmp_path / "projekt"
    (projekt / "assets").mkdir(parents=True)
    quelle = _bild_schreiben(projekt / "assets" / "cookie.png")

    absolut, relativ = bild_in_assets_uebernehmen(quelle, projekt)

    assert relativ == "assets/cookie.png"
    assert absolut == quelle.resolve()
    assert list((projekt / "assets").iterdir()) == [quelle]


def test_gleicher_name_mit_anderem_inhalt_bekommt_neuen_namen(tmp_path: Path) -> None:
    projekt = tmp_path / "projekt"
    (projekt / "assets").mkdir(parents=True)
    _bild_schreiben(projekt / "assets" / "cookie.png", 10, 10)
    andere = _bild_schreiben(tmp_path / "cookie.png", 40, 20)

    _, relativ = bild_in_assets_uebernehmen(andere, projekt)

    assert relativ == "assets/cookie_2.png"
    assert (projekt / "assets" / "cookie.png").exists()


def test_gleicher_name_mit_gleichem_inhalt_wird_wiederverwendet(tmp_path: Path) -> None:
    projekt = tmp_path / "projekt"
    (projekt / "assets").mkdir(parents=True)
    quelle = _bild_schreiben(tmp_path / "cookie.png")
    (projekt / "assets" / "cookie.png").write_bytes(quelle.read_bytes())

    _, relativ = bild_in_assets_uebernehmen(quelle, projekt)

    assert relativ == "assets/cookie.png"
    assert len(list((projekt / "assets").iterdir())) == 1


# -- Designer (ide/designer/canvas.py) ------------------------------------


def test_ablegen_auf_leerer_flaeche_erzeugt_image_komponente(tmp_path: Path) -> None:
    canvas = _canvas(tmp_path)
    quelle = _bild_schreiben(tmp_path / "extern" / "cookie.png")

    komponente = canvas.bild_ablegen(quelle, 120, 80)

    assert isinstance(komponente, Image)
    assert (komponente.left, komponente.top) == (120, 80)
    # Größe aus den echten Bildmaßen, nicht die Palettengröße 100x100
    assert (komponente.width, komponente.height) == (40, 20)
    kopie = tmp_path / "projekt" / "assets" / "cookie.png"
    assert komponente.picture.pfad == str(kopie.resolve())
    assert kopie.exists()


def test_ablegen_schreibt_die_komponente_in_die_pfm(tmp_path: Path) -> None:
    canvas = _canvas(tmp_path)
    quelle = _bild_schreiben(tmp_path / "extern" / "cookie.png")

    canvas.bild_ablegen(quelle, 120, 80)

    daten = json.loads((tmp_path / "projekt" / "u_main.pfm").read_text(encoding="utf-8"))
    bilder = [kind for kind in daten["children"] if kind["type"] == "Image"]
    assert len(bilder) == 1
    assert bilder[0]["properties"]["left"] == 120
    assert bilder[0]["properties"]["width"] == 40


def test_ablegen_ist_rueckgaengig_machbar(tmp_path: Path) -> None:
    canvas = _canvas(tmp_path)
    quelle = _bild_schreiben(tmp_path / "extern" / "cookie.png")

    komponente = canvas.bild_ablegen(quelle, 120, 80)
    name = canvas.name_von(komponente)
    canvas.rueckgaengig()

    assert canvas.name_von(komponente) is None
    daten = json.loads((tmp_path / "projekt" / "u_main.pfm").read_text(encoding="utf-8"))
    assert all(kind["name"] != name for kind in daten["children"])


def test_ablegen_auf_vorhandenem_image_tauscht_nur_das_bild(tmp_path: Path) -> None:
    canvas = _canvas(tmp_path)
    erstes = _bild_schreiben(tmp_path / "extern" / "a.png", 40, 20)
    zweites = _bild_schreiben(tmp_path / "extern" / "b.png", 60, 30)

    komponente = canvas.bild_ablegen(erstes, 100, 100)
    anzahl_vorher = len(list(canvas.formular._qwidget.children()))

    getroffen = canvas.bild_ablegen(zweites, 110, 105)

    assert getroffen is komponente
    assert komponente.picture.pfad.endswith("b.png")
    # keine zweite Komponente entstanden
    assert len(list(canvas.formular._qwidget.children())) == anzahl_vorher


def test_bildtausch_ist_rueckgaengig_machbar(tmp_path: Path) -> None:
    canvas = _canvas(tmp_path)
    erstes = _bild_schreiben(tmp_path / "extern" / "a.png")
    zweites = _bild_schreiben(tmp_path / "extern" / "b.png", 60, 30)
    komponente = canvas.bild_ablegen(erstes, 100, 100)

    canvas.bild_ablegen(zweites, 110, 105)
    canvas.rueckgaengig()

    assert komponente.picture.pfad.endswith("a.png")


def test_ablegen_auf_anderer_komponente_erzeugt_eine_neue_image_komponente(
    tmp_path: Path,
) -> None:
    """Ein Button unter dem Mauszeiger bekommt kein Bild – dort entsteht
    eine neue `Image`-Komponente."""
    canvas = _canvas(tmp_path)
    quelle = _bild_schreiben(tmp_path / "extern" / "cookie.png")

    komponente = canvas.bild_ablegen(quelle, 20, 20)

    assert isinstance(komponente, Image)
    assert isinstance(canvas.formular.b_start, Button)


def test_sehr_grosses_bild_wird_auf_240_px_begrenzt(tmp_path: Path) -> None:
    canvas = _canvas(tmp_path)
    quelle = _bild_schreiben(tmp_path / "extern" / "gross.png", 1000, 500)

    komponente = canvas.bild_ablegen(quelle, 10, 10)

    assert (komponente.width, komponente.height) == (240, 120)


def test_beobachter_bekommt_den_projektrelativen_pfad(tmp_path: Path) -> None:
    canvas = _canvas(tmp_path)
    gemeldet: list[str] = []
    canvas.bild_beobachten(gemeldet.append)
    quelle = _bild_schreiben(tmp_path / "extern" / "cookie.png")

    canvas.bild_ablegen(quelle, 10, 10)

    assert gemeldet == ["assets/cookie.png"]


# -- echte Qt-Drag-&-Drop-Ereignisse --------------------------------------


# Qt-Ereignisse übernehmen das QMimeData nicht; ohne diese Liste räumt
# Python es weg, während das Ereignis noch darauf zeigt - der Testlauf
# stürzte dann mit einer Zugriffsverletzung ab statt zu scheitern.
_MIME_AM_LEBEN: list[QMimeData] = []


def _mime(*pfade: Path) -> QMimeData:
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(pfad)) for pfad in pfade])
    _MIME_AM_LEBEN.append(mime)
    return mime


def test_dragenter_wird_fuer_bilddateien_angenommen(tmp_path: Path) -> None:
    canvas = _canvas(tmp_path)
    quelle = _bild_schreiben(tmp_path / "extern" / "cookie.png")
    ereignis = QDragEnterEvent(
        QPoint(50, 50),
        Qt.DropAction.CopyAction,
        _mime(quelle),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    assert canvas.eventFilter(canvas.formular._qwidget, ereignis) is True
    assert ereignis.isAccepted()


def test_dragenter_wird_fuer_andere_dateien_abgelehnt(tmp_path: Path) -> None:
    canvas = _canvas(tmp_path)
    textdatei = tmp_path / "notiz.txt"
    textdatei.write_text("kein Bild", encoding="utf-8")
    ereignis = QDragEnterEvent(
        QPoint(50, 50),
        Qt.DropAction.CopyAction,
        _mime(textdatei),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    assert canvas.eventFilter(canvas.formular._qwidget, ereignis) is False


def test_echtes_drop_ereignis_legt_das_bild_ab(tmp_path: Path) -> None:
    canvas = _canvas(tmp_path)
    quelle = _bild_schreiben(tmp_path / "extern" / "cookie.png")
    ereignis = QDropEvent(
        QPointF(150, 90),
        Qt.DropAction.CopyAction,
        _mime(quelle),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    assert canvas.eventFilter(canvas.formular._qwidget, ereignis) is True
    bilder = [k for _, k in _kinder(canvas) if isinstance(k, Image)]
    assert len(bilder) == 1
    # Eingerastet am 8px-Raster: aus (150, 90) wird (152, 88).
    assert (bilder[0].left, bilder[0].top) == (152, 88)


def test_drop_mehrerer_bilder_erzeugt_versetzte_komponenten(tmp_path: Path) -> None:
    canvas = _canvas(tmp_path)
    erstes = _bild_schreiben(tmp_path / "extern" / "a.png")
    zweites = _bild_schreiben(tmp_path / "extern" / "b.png", 60, 30)
    ereignis = QDropEvent(
        QPointF(100, 100),
        Qt.DropAction.CopyAction,
        _mime(erstes, zweites),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )

    canvas.eventFilter(canvas.formular._qwidget, ereignis)

    bilder = sorted(
        (k for _, k in _kinder(canvas) if isinstance(k, Image)), key=lambda k: k.left
    )
    assert [(b.left, b.top) for b in bilder] == [(96, 96), (112, 112)]


def test_ohne_pfm_pfad_wird_nicht_kopiert(tmp_path: Path) -> None:
    """Designer-Vorschau ohne zugrunde liegende `.pfm` (z. B. in Tests):
    kein Projektordner, also auch kein `assets/`."""
    pfm_pfad = tmp_path / "projekt" / "u_main.pfm"
    pfm_pfad.parent.mkdir(parents=True, exist_ok=True)
    pfm_pfad.write_text(json.dumps(_PFM), encoding="utf-8")
    canvas = DesignerCanvas(formular_fuer_designer_laden(pfm_pfad))
    quelle = _bild_schreiben(tmp_path / "extern" / "cookie.png")

    komponente = canvas.bild_ablegen(quelle, 10, 10)

    assert komponente.picture.pfad == str(quelle.resolve())
    assert not (tmp_path / "projekt" / "assets").exists()
