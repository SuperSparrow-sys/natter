"""Punkt 541: Eine SVG lädt keine Dateien von außen nach."""

from __future__ import annotations

import base64
from pathlib import Path

import pytest
from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QColor, QImage

from pcl.bilddatei import bild_laden, svg_ohne_verweise


def _rotes_png(pfad: Path | None = None) -> bytes:
    bild = QImage(4, 4, QImage.Format.Format_RGB32)
    bild.fill(QColor("#ff0000"))
    daten = QByteArray()
    puffer = QBuffer(daten)
    puffer.open(QIODevice.OpenModeFlag.WriteOnly)
    bild.save(puffer, "PNG")
    roh = bytes(daten.data())
    if pfad is not None:
        pfad.write_bytes(roh)
    return roh


def _svg(href: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        'xmlns:xlink="http://www.w3.org/1999/xlink" width="4" height="4">'
        f'<image x="0" y="0" width="4" height="4" xlink:href="{href}"/></svg>'
    )


@pytest.mark.parametrize("innen", [False, True])
def test_eine_svg_zeigt_nur_was_in_ihr_steht(tmp_path: Path, innen: bool) -> None:
    draussen = tmp_path / "draussen"
    draussen.mkdir()
    _rotes_png(draussen / "rot.png")
    projekt = tmp_path / "projekt"
    projekt.mkdir()
    if innen:
        href = "data:image/png;base64," + base64.b64encode(_rotes_png()).decode()
    else:
        href = str(draussen / "rot.png")
    (projekt / "bild.svg").write_text(_svg(href), encoding="utf-8")

    farbe = bild_laden(projekt / "bild.svg").toImage().pixelColor(1, 1).name()

    assert (farbe == "#ff0000") is innen


def test_auch_netzpfade_stylesheets_und_entitaeten_fallen_weg() -> None:
    text = (
        '<?xml-stylesheet href="//server/s.css"?>'
        '<!DOCTYPE svg [<!ENTITY x SYSTEM "//server/x">]>'
        '<svg><use href="//server/b.svg#a"/>'
        '<rect style="fill: url(//server/m.svg#v)"/>'
        '<use href="#innen"/></svg>'
    )

    sauber = svg_ohne_verweise(text)

    assert "server" not in sauber
    assert 'href="#innen"' in sauber
