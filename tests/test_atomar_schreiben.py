"""Tests für `ide/atomar.py`: Projektdateien werden über eine
Nachbardatei und `os.replace` geschrieben (Punkt 236).

Nachgestellt wird ein Abbruch mitten im Schreiben: das untergeschobene
`write` schreibt die Hälfte und wirft dann einen `OSError`, wie es ein
abgezogener USB-Stick täte. Danach muss die alte Datei unverändert
daliegen, und es darf keine Zwischendatei übrig bleiben.
"""

from __future__ import annotations

import shutil
from collections.abc import Callable
from pathlib import Path

import pytest

from ide.atomar import atomar_schreiben, ordner_beschreibbar

_BEISPIELE = Path(__file__).resolve().parent.parent / "beispielprojekte"


class _AbbrechendeDatei:
    """Schreibt die Hälfte des Inhalts und bricht dann ab."""

    def __init__(self, datei) -> None:  # noqa: ANN001
        self._datei = datei

    def write(self, inhalt):  # noqa: ANN001, ANN201
        self._datei.write(inhalt[: len(inhalt) // 2])
        self._datei.flush()
        raise OSError(5, "Zugriff auf das Laufwerk abgebrochen")

    def __getattr__(self, name: str):  # noqa: ANN204
        return getattr(self._datei, name)

    def __enter__(self) -> _AbbrechendeDatei:
        return self

    def __exit__(self, *_ausnahme: object) -> None:
        self._datei.close()


@pytest.fixture
def abbrechendes_schreiben(monkeypatch: pytest.MonkeyPatch) -> None:
    echtes_open = Path.open

    def open_mit_abbruch(self: Path, mode: str = "r", *args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        datei = echtes_open(self, mode, *args, **kwargs)
        if "w" in mode:
            return _AbbrechendeDatei(datei)
        return datei

    monkeypatch.setattr(Path, "open", open_mit_abbruch)


def _pfm_speichern(ordner: Path):  # noqa: ANN202
    from ide.designer.laden import formular_fuer_designer_laden
    from ide.designer.pfm_schreiben import formular_als_pfm_speichern

    pfad = ordner / "u_main.pfm"
    formular = formular_fuer_designer_laden(pfad)
    formular.caption = "Geändert"
    return pfad, lambda: formular_als_pfm_speichern(formular, pfad)


def _design_erzeugen(ordner: Path):  # noqa: ANN202
    from ide.codegen.design import design_datei_erzeugen

    ziel = ordner / "u_main_design.py"
    return ziel, lambda: design_datei_erzeugen(ordner / "u_main.pfm", ziel)


def _projekt_speichern(ordner: Path):  # noqa: ANN202
    from ide.project.projekt import Projekt

    pfad = ordner / "03_Taschenrechner.natter"
    projekt = Projekt.laden(pfad)
    return pfad, lambda: projekt.speichern(pfad)


def _diagramm_speichern(ordner: Path):  # noqa: ANN202
    from ide.diagramm.datei import Diagramm

    quelle = (
        _BEISPIELE / "06_Kontoverwaltung" / "diagramme" / "konto_klassen.pdiag"
    )
    pfad = ordner / "konto_klassen.pdiag"
    shutil.copy(quelle, pfad)
    diagramm = Diagramm.laden(pfad)
    diagramm.daten["name"] = "Anders"
    return pfad, diagramm.speichern


def _direkt(ordner: Path):  # noqa: ANN202
    pfad = ordner / "u_main.py"
    return pfad, lambda: atomar_schreiben(pfad, "neu\n" * 200)


@pytest.mark.parametrize(
    "vorbereiten",
    [
        _pfm_speichern,
        _design_erzeugen,
        _projekt_speichern,
        _diagramm_speichern,
        _direkt,
    ],
    ids=["pfm", "design", "natter", "pdiag", "unit"],
)
def test_abbruch_beim_schreiben_laesst_die_alte_datei_stehen(
    vorbereiten: Callable,
    tmp_path: Path,
    abbrechendes_schreiben: None,
) -> None:
    ordner = tmp_path / "projekt"
    shutil.copytree(_BEISPIELE / "03_Taschenrechner", ordner)
    pfad, schreiben = vorbereiten(ordner)
    vorher = pfad.read_bytes()
    dateien_vorher = sorted(p.name for p in ordner.iterdir())

    with pytest.raises(OSError, match="abgebrochen"):
        schreiben()

    assert pfad.read_bytes() == vorher
    assert sorted(p.name for p in ordner.iterdir()) == dateien_vorher


def test_schreibt_text_wie_write_text(tmp_path: Path) -> None:
    vergleich = tmp_path / "vergleich.txt"
    vergleich.write_text("Zeile ä\nZeile 2\n", encoding="utf-8")
    ziel = tmp_path / "ziel.txt"
    ziel.write_text("alt", encoding="utf-8")

    atomar_schreiben(ziel, "Zeile ä\nZeile 2\n")

    assert ziel.read_bytes() == vergleich.read_bytes()
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "vergleich.txt",
        "ziel.txt",
    ]


def test_schreibgeschuetzte_datei_bleibt_geschuetzt(tmp_path: Path) -> None:
    ziel = tmp_path / "u_main.pfm"
    ziel.write_text("alt", encoding="utf-8")
    ziel.chmod(0o444)
    try:
        with pytest.raises(PermissionError):
            atomar_schreiben(ziel, "neu")
        assert ziel.read_text(encoding="utf-8") == "alt"
    finally:
        ziel.chmod(0o666)


def test_die_schreibprobe_legt_eine_datei_an_und_raeumt_auf(
    tmp_path: Path,
) -> None:
    """Punkt 321: ausprobiert statt über `os.access` gefragt, das
    unter Windows eine Freigabe nur zum Lesen nicht erkennt."""
    assert ordner_beschreibbar(tmp_path)
    assert list(tmp_path.iterdir()) == []
    assert not ordner_beschreibbar(tmp_path / "fehlt")
