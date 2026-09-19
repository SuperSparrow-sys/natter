"""Dekodiert `Picture.Data`-Binärblöcke einer `.lfm` (Abschnitt 15,
docs/arbeitspakete/M8.md, Schritt 3).

Das Lazarus-Containerformat um die eigentlichen Bilddaten ist der
Delphi/LCL-`TPersistent`-Stream:

1. ein Byte: Länge des Klassennamens (Pascal-`ShortString`),
2. der Klassenname als ASCII, z. B. ``TPortableNetworkGraphic``,
3. vier Byte: Länge der Bilddaten, vorzeichenlos, Little-Endian,
4. die Bilddatei selbst, Byte für Byte (eine vollständige PNG-/BMP-/
   JPEG-Datei).

Nachgeprüft an `tests/daten/lazarus/l_Pet/u_main.lfm`:
``1754506F727461626C654E6574776F726B47726170686963A1C62D0089504E47…``
→ ``0x17`` = 23 Zeichen ``TPortableNetworkGraphic``, ``A1C62D00`` =
2 999 969 Byte, danach die PNG-Signatur ``89 50 4E 47``.
"""

from __future__ import annotations

from dataclasses import dataclass

# Lazarus-Grafikklasse -> Dateiendung.
_ENDUNGEN: dict[str, str] = {
    "TPortableNetworkGraphic": ".png",
    "TBitmap": ".bmp",
    "TJPEGImage": ".jpg",
    "TJpegImage": ".jpg",
    "TGIFImage": ".gif",
    "TIcon": ".ico",
    "TPixmap": ".xpm",
    "TTiffImage": ".tif",
    "TPortableAnyMapGraphic": ".pnm",
}

# Erkennung an den ersten Bytes, falls der Klassenname unbekannt ist.
_SIGNATUREN: tuple[tuple[bytes, str], ...] = (
    (b"\x89PNG\r\n\x1a\n", ".png"),
    (b"BM", ".bmp"),
    (b"\xff\xd8\xff", ".jpg"),
    (b"GIF8", ".gif"),
    (b"II*\x00", ".tif"),
    (b"MM\x00*", ".tif"),
)


class LfmBildFehler(ValueError):
    """Der `Picture.Data`-Block ließ sich nicht dekodieren."""


@dataclass
class LfmBild:
    """Ein aus `Picture.Data` ausgepacktes Bild."""

    klassenname: str
    endung: str
    daten: bytes


def _endung_bestimmen(klassenname: str, daten: bytes) -> str:
    endung = _ENDUNGEN.get(klassenname)
    if endung is not None:
        return endung
    for signatur, gefundene_endung in _SIGNATUREN:
        if daten.startswith(signatur):
            return gefundene_endung
    raise LfmBildFehler(f"Unbekanntes Bildformat: {klassenname!r}")


def bild_aus_binaerblock(hex_text: str) -> LfmBild:
    """Packt einen `Picture.Data`-Block aus. `hex_text` ist der reine
    Hex-Text, den `ide.import_lfm.parser` unter dem Schlüssel `"binaer"`
    liefert."""
    bereinigt = "".join(hex_text.split())
    try:
        rohdaten = bytes.fromhex(bereinigt)
    except ValueError as fehler:
        raise LfmBildFehler(f"Kein gültiger Hex-Block: {fehler}") from fehler

    if not rohdaten:
        raise LfmBildFehler("Leerer Picture.Data-Block.")

    namenslaenge = rohdaten[0]
    name_ende = 1 + namenslaenge
    if len(rohdaten) < name_ende + 4:
        raise LfmBildFehler("Picture.Data endet mitten im Vorspann.")
    try:
        klassenname = rohdaten[1:name_ende].decode("ascii")
    except UnicodeDecodeError as fehler:
        raise LfmBildFehler(f"Klassenname nicht lesbar: {fehler}") from fehler

    laenge = int.from_bytes(rohdaten[name_ende : name_ende + 4], "little")
    daten = rohdaten[name_ende + 4 : name_ende + 4 + laenge]
    if len(daten) < laenge:
        raise LfmBildFehler(
            f"Picture.Data ist unvollständig: {laenge} Byte angekündigt, "
            f"{len(daten)} Byte vorhanden."
        )

    return LfmBild(
        klassenname=klassenname,
        endung=_endung_bestimmen(klassenname, daten),
        daten=daten,
    )
