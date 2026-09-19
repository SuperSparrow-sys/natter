"""Tests für das Auspacken von `Picture.Data` (`ide/import_lfm/bilder.py`,
docs/arbeitspakete/M8.md, Schritt 3).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.import_lfm.bilder import LfmBildFehler, bild_aus_binaerblock
from ide.import_lfm.parser import parse_lfm

_REFERENZ = Path(__file__).resolve().parent / "daten" / "lazarus"

_PNG = bytes.fromhex(
    "89504E470D0A1A0A0000000D4948445200000001000000010806000000"
    "1F15C4890000000A49444154789C6300010000050001"
    "0D0A2DB40000000049454E44AE426082"
)


def _binaerblock(klassenname: str, daten: bytes) -> str:
    """Baut einen Lazarus-`Picture.Data`-Block wie in der `.lfm`:
    ShortString-Klassenname, 4 Byte Länge (Little-Endian), Bilddaten."""
    roh = (
        bytes([len(klassenname)])
        + klassenname.encode("ascii")
        + len(daten).to_bytes(4, "little")
        + daten
    )
    return roh.hex().upper()


def test_png_wird_mit_klassenname_und_endung_ausgepackt() -> None:
    bild = bild_aus_binaerblock(_binaerblock("TPortableNetworkGraphic", _PNG))

    assert bild.klassenname == "TPortableNetworkGraphic"
    assert bild.endung == ".png"
    assert bild.daten == _PNG


def test_hex_darf_ueber_mehrere_zeilen_verteilt_sein() -> None:
    hex_text = _binaerblock("TBitmap", b"BM" + b"\x00" * 10)
    zerlegt = "\n".join(hex_text[i : i + 16] for i in range(0, len(hex_text), 16))

    assert bild_aus_binaerblock(zerlegt).endung == ".bmp"


def test_unbekannter_klassenname_wird_an_der_signatur_erkannt() -> None:
    bild = bild_aus_binaerblock(_binaerblock("TIrgendwasGraphic", _PNG))

    assert bild.endung == ".png"


def test_unbekanntes_format_meldet_fehler() -> None:
    with pytest.raises(LfmBildFehler, match="Unbekanntes Bildformat"):
        bild_aus_binaerblock(_binaerblock("TIrgendwasGraphic", b"nichts dergleichen"))


def test_abgeschnittener_block_meldet_fehler() -> None:
    vollstaendig = _binaerblock("TPortableNetworkGraphic", _PNG)
    with pytest.raises(LfmBildFehler, match="unvollständig"):
        bild_aus_binaerblock(vollstaendig[:-20])


def test_kein_hex_meldet_fehler() -> None:
    with pytest.raises(LfmBildFehler, match="Hex-Block"):
        bild_aus_binaerblock("kein hex")


def test_echtes_lfm_l_pet_liefert_ein_gueltiges_png() -> None:
    """Gegen eine echte Lazarus-Datei aus `tests/daten/lazarus/`.

    Die Vorlage stammt aus einem Schülerprojekt und trug ein PNG von
    knapp drei Megabyte in sich - genau der Fall, für den der
    Binärblock-Leser da ist. Im Repository liegt sie mit einem winzigen
    Bild an derselben Stelle: geprüft wird das Format, nicht die
    Dateigröße, und sechs Megabyte Testdaten wären dafür ein hoher
    Preis (M14).
    """
    objekt = parse_lfm((_REFERENZ / "l_Pet" / "u_main.lfm").read_text(encoding="utf-8"))
    image = next(kind for kind in objekt["children"] if kind["name"] == "Image1")

    bild = bild_aus_binaerblock(image["properties"]["Picture.Data"]["binaer"])

    assert bild.klassenname == "TPortableNetworkGraphic"
    assert bild.endung == ".png"
    assert bild.daten.startswith(b"\x89PNG\r\n\x1a\n")
    # Eine gültige PNG-Datei, nicht bloß ein Bytehaufen.
    assert b"IEND" in bild.daten  # der Abschlussblock einer PNG-Datei


def test_echtes_lfm_cookie_klicker_liefert_jpeg() -> None:
    objekt = parse_lfm(
        (_REFERENZ / "d_Cookie_klicker" / "unit1.lfm").read_text(encoding="utf-8")
    )
    image = next(kind for kind in objekt["children"] if kind["name"] == "i_Cookie1")

    bild = bild_aus_binaerblock(image["properties"]["Picture.Data"]["binaer"])

    assert bild.endung == ".jpg"
    assert bild.daten.startswith(b"\xff\xd8\xff")
