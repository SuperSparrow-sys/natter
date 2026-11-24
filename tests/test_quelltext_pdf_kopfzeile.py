"""Quelltext als PDF: die Kopfzeile steht auf jeder Seite, nicht nur
über dem Anfang einer Datei. Lose Blätter aus einer eingesammelten
Abgabe lassen sich sonst nicht zuordnen."""

from __future__ import annotations

import re
import shutil
from datetime import date
from pathlib import Path

import pytest

import ide.export.quelltext_pdf as modul
from ide.project.projekt import Projekt

BEISPIEL = (
    Path(__file__).resolve().parent.parent
    / "beispielprojekte"
    / "01_Begruessung"
)


@pytest.fixture
def projekt(tmp_path: Path, qapp) -> Projekt:
    ziel = tmp_path / "01_Begruessung"
    shutil.copytree(BEISPIEL, ziel)
    # Eine Unit mit 200 Zeilen ergibt drei Seiten.
    zeilen = [f"zahl_{i} = {i}" for i in range(200)]
    (ziel / "u_main.py").write_text("\n".join(zeilen) + "\n", encoding="utf-8")
    return Projekt.laden(ziel / "01_Begruessung.natter")


def _seiten_im_pdf(pfad: Path) -> int:
    return len(re.findall(rb"/Type\s*/Page(?![s\w])", pfad.read_bytes()))


def test_jede_seite_hat_datei_name_und_seitenzahl(
    projekt: Projekt, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gezeichnet: list[tuple[str, str]] = []
    echt = modul._kopfzeile_zeichnen

    def mitschreiben(maler, breite, links, rechts) -> None:  # noqa: ANN001
        gezeichnet.append((links, rechts))
        echt(maler, breite, links, rechts)

    monkeypatch.setattr(modul, "_kopfzeile_zeichnen", mitschreiben)
    ziel = tmp_path / "abgabe.pdf"

    modul.quelltext_als_pdf(
        projekt, ziel, date(2026, 9, 28), name="Anna Muster"
    )

    seiten = _seiten_im_pdf(ziel)
    assert seiten >= 3
    assert len(gezeichnet) == seiten
    for nummer, (links, rechts) in enumerate(gezeichnet, 1):
        assert "u_main.py" in links
        assert "01_Begruessung" in links
        assert "Anna Muster" in links
        assert "28.09.2026" in links
        assert rechts == f"Seite {nummer} von {seiten}"


def test_seitenkoepfe_folgen_der_datei(projekt: Projekt) -> None:
    (projekt.ordner / "u_zweite.py").write_text(
        "x = 1\n", encoding="utf-8"
    )
    projekt = Projekt.laden(projekt.ordner / "01_Begruessung.natter")
    dokument = modul.dokument_erzeugen(projekt)
    from PySide6.QtCore import QSizeF

    dokument.setPageSize(QSizeF(641, 940))

    koepfe = modul.seitenkoepfe(projekt, dokument, name="")

    dateien = [links.split(" – ")[1] for links, _ in koepfe]
    assert dateien.count("u_main.py") >= 3
    assert dateien[-1] == "u_zweite.py"
    assert dateien == sorted(dateien, key=dateien.index)


def test_ohne_namen_kommt_die_anmeldung(projekt: Projekt) -> None:
    assert modul.anmeldename()


def test_das_pdf_landet_am_vorschlag_nicht_unter_den_exportdaten(
    tmp_path: Path, monkeypatch, hauptfenster
) -> None:  # noqa: ANN001
    """Punkt 586: vorgeschlagen war der Projektordner, und der nächste
    Exe-Export nahm das PDF als Programmdaten mit."""
    from PySide6.QtWidgets import QFileDialog

    from ide.export.exporter import _daten_dateien_des_projekts
    from ide.project.neu import projekt_erzeugen

    projekt = projekt_erzeugen("console", tmp_path, "Statistik")
    hauptfenster.projekt_oeffnen(projekt.ordner / "Statistik.natter")
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda _e, _t, vorschlag, _f: (vorschlag, "")),
    )

    hauptfenster._quelltext_als_pdf_aktion()

    pdf = projekt.ordner.parent / "Statistik Quelltext.pdf"
    assert pdf.exists(), hauptfenster.statusBar().currentMessage()
    daten = _daten_dateien_des_projekts(hauptfenster.projekt)
    assert not [p for p in daten if p.suffix == ".pdf"]


@pytest.mark.parametrize(
    ("ordnername", "erwartet", "lehrkraft_im_kopf"),
    [
        ("Ampel - schueler01 - PC-R01", "Ampel - schueler01 - PC-R01", False),
        ("Ampel", "Ampel", True),
    ],
    ids=["abgabe", "eigenes_projekt"],
)
def test_eine_abgabe_traegt_ihren_ordner_statt_der_lehrkraft(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    qapp,  # noqa: ANN001
    ordnername: str,
    erwartet: str,
    lehrkraft_im_kopf: bool,
) -> None:
    """Punkt 697: Druckte die Lehrkraft eingesammelte Abgaben, stand
    ihr eigener Name in jeder Kopfzeile, und der Projektname ist bei
    der ganzen Klasse gleich."""
    from ide.project.neu import projekt_erzeugen

    projekt_erzeugen("console", tmp_path / ordnername, "Ampel")
    projekt = Projekt.laden(tmp_path / ordnername / "Ampel.natter")
    monkeypatch.setattr(modul, "anmeldename", lambda: "Frau Lehrkraft")
    gezeichnet: list[str] = []
    monkeypatch.setattr(
        modul, "_kopfzeile_zeichnen",
        lambda maler, breite, links, rechts: gezeichnet.append(links),
    )

    modul.quelltext_als_pdf(projekt, tmp_path / "a.pdf", date(2026, 11, 24))

    assert gezeichnet
    for links in gezeichnet:
        assert links.startswith(f"{erwartet} – u_main.py")
        assert ("Frau Lehrkraft" in links) is lehrkraft_im_kopf


def test_zwei_abgaben_bekommen_verschiedene_vorschlaege(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, hauptfenster
) -> None:  # noqa: ANN001
    """Punkt 697: beide Abgaben bekamen „Ampel Quelltext.pdf“
    vorgeschlagen und ersetzten einander im gemeinsamen Ordner."""
    from PySide6.QtWidgets import QFileDialog

    from ide.project.neu import projekt_erzeugen

    vorschlaege: list[str] = []
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(
            lambda _e, _t, vorschlag, _f: (vorschlaege.append(vorschlag), ("", ""))[1]
        ),
    )
    for konto in ("schueler01", "schueler02"):
        ordner = tmp_path / f"Ampel - {konto} - PC-R01"
        projekt_erzeugen("console", ordner, "Ampel")
        hauptfenster.projekt_oeffnen(ordner / "Ampel.natter")
        hauptfenster._quelltext_als_pdf_aktion()

    assert [Path(v).name for v in vorschlaege] == [
        "Ampel - schueler01 - PC-R01 Quelltext.pdf",
        "Ampel - schueler02 - PC-R01 Quelltext.pdf",
    ]
