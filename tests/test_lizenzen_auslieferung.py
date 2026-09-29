"""Lizenzen der ausgelieferten Pakete (Punkt 24 der offenen Punkte).

Geprüft wird an nachgebauten dist-info-Ordnern in `tmp_path`, nicht an
`dist\\Natter`: der Test soll auch ohne einen Bau laufen.
"""

from __future__ import annotations

from email.message import Message
from pathlib import Path

import pytest

from tools import ide_paketieren
from tools.ide_paketieren import (
    _qt_nur_gpl_entfernen,
    lizenz_einordnen,
    lizenzen_pruefen,
)


def _metadaten(**felder: str | list[str]) -> Message:
    nachricht = Message()
    for schluessel, wert in felder.items():
        schluessel = schluessel.replace("_", "-")
        for eintrag in wert if isinstance(wert, list) else [wert]:
            nachricht[schluessel] = eintrag
    return nachricht


def _paket_anlegen(site_packages: Path, name: str, *zeilen: str) -> None:
    info = site_packages / f"{name}-1.0.dist-info"
    info.mkdir(parents=True)
    kopf = ["Metadata-Version: 2.4", f"Name: {name}", "Version: 1.0"]
    (info / "METADATA").write_text(
        "\n".join([*kopf, *zeilen]) + "\n", encoding="utf-8"
    )


@pytest.mark.parametrize(
    ("felder", "erwartet"),
    [
        ({"License_Expression": "MIT"}, "erlaubt"),
        ({"License_Expression": "Apache-2.0 OR BSD-3-Clause"}, "erlaubt"),
        (
            {"License_Expression": "BSD-3-Clause AND 0BSD AND MIT AND Zlib"},
            "erlaubt",
        ),
        ({"License_Expression": "MIT AND GPL-3.0-only"}, "gpl"),
        ({"License_Expression": "GPL-3.0-or-later"}, "gpl"),
        ({"License_Expression": "AGPL-3.0-only"}, "gpl"),
        # PySide6: LGPL als eine der Wahlmöglichkeiten genügt.
        (
            {"License": "LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only"},
            "erlaubt",
        ),
        # PyInstaller: das kleine "or" trennt nichts.
        (
            {"License": "GPLv2-or-later with a special exception"},
            "gpl",
        ),
        # matplotlib: in License steht Fließtext, der Klassifikator
        # entscheidet.
        (
            {
                "License": "License agreement for matplotlib versions",
                "Classifier": [
                    "License :: OSI Approved :: "
                    "Python Software Foundation License"
                ],
            },
            "erlaubt",
        ),
        (
            {
                "Classifier": [
                    "License :: OSI Approved :: GNU Lesser General "
                    "Public License v3 (LGPLv3)"
                ]
            },
            "erlaubt",
        ),
        (
            {
                "Classifier": [
                    "License :: OSI Approved :: GNU General Public "
                    "License v2 (GPLv2)"
                ]
            },
            "gpl",
        ),
        ({"License": "Proprietär"}, "unbekannt"),
        ({}, "unbekannt"),
    ],
)
def test_lizenz_wird_eingeordnet(
    felder: dict[str, str | list[str]], erwartet: str
) -> None:
    assert lizenz_einordnen(_metadaten(**felder)) == erwartet


def test_ein_gpl_paket_wird_beanstandet(tmp_path: Path) -> None:
    _paket_anlegen(tmp_path, "frei", "License-Expression: MIT")
    _paket_anlegen(tmp_path, "streng", "License-Expression: GPL-3.0-only")
    _paket_anlegen(tmp_path, "raetsel")

    assert lizenzen_pruefen(tmp_path) == [
        "raetsel: Lizenz lässt sich aus den Metadaten nicht ablesen",
        "streng: steht unter GPL",
    ]


def test_pyinstaller_und_natter_selbst_sind_ausgenommen(
    tmp_path: Path,
) -> None:
    _paket_anlegen(
        tmp_path,
        "pyinstaller",
        "License: GPLv2-or-later with a special exception",
    )
    _paket_anlegen(tmp_path, "natter", "License: Natter - Private Lizenz")

    assert lizenzen_pruefen(tmp_path) == []


def test_der_bau_bricht_bei_einem_gpl_paket_ab(tmp_path: Path) -> None:
    site_packages = tmp_path / "site-packages"
    _paket_anlegen(site_packages, "streng", "License-Expression: GPL-3.0-only")

    with pytest.raises(RuntimeError, match="streng: steht unter GPL"):
        ide_paketieren._lizenzen_sammeln(site_packages, tmp_path / "Lizenzen")
    assert not (tmp_path / "Lizenzen").exists()


def test_lizenztexte_kommen_aus_der_mitgelieferten_python(
    tmp_path: Path,
) -> None:
    """Jedes Paket in site-packages bekommt einen Ordner unter
    Lizenzen, nicht nur die aus einer festen Liste."""
    site_packages = tmp_path / "site-packages"
    _paket_anlegen(site_packages, "abhaengigkeit", "License-Expression: MIT")
    info = site_packages / "abhaengigkeit-1.0.dist-info"
    (info / "licenses").mkdir()
    (info / "licenses" / "LICENSE").write_text("MIT-Text", encoding="utf-8")
    (info / "RECORD").write_text(
        "abhaengigkeit-1.0.dist-info/METADATA,,\n"
        "abhaengigkeit-1.0.dist-info/licenses/LICENSE,,\n",
        encoding="utf-8",
    )
    _paket_anlegen(site_packages, "ohne-datei", "License-Expression: BSD-3-Clause")

    ziel = tmp_path / "Lizenzen"
    ide_paketieren._lizenzen_sammeln(site_packages, ziel)

    assert (ziel / "abhaengigkeit" / "LICENSE").read_text(
        encoding="utf-8"
    ) == "MIT-Text"
    assert "BSD-3-Clause" in (
        ziel / "ohne-datei" / "LIZENZ_HINWEIS.txt"
    ).read_text(encoding="utf-8")
    assert (ziel / "LGPL-3.0.txt").is_file()
    assert not (ziel / "INSTALLER_LIZENZ.txt").exists()


def test_qt_module_unter_gpl_werden_entfernt(tmp_path: Path) -> None:
    pyside = tmp_path / "PySide6"
    behalten = [
        "Qt6Core.dll",
        "QtWidgets.pyd",
        "QtGraphicalEffects.pyd",
        "glue/qtcore.cpp",
        "include/QtGui/qtgui.h",
        "qml/QtQuick/qmldir",
        "typesystems/typesystem_core.xml",
    ]
    entfernen = [
        "Qt6Charts.dll",
        "Qt6ChartsQml.dll",
        "Qt6DataVisualization.dll",
        "Qt6Graphs.dll",
        "Qt6GraphsWidgets.dll",
        "QtCharts.pyd",
        "QtCharts.pyi",
        "QtGraphsWidgets.pyi",
        "glue/qtcharts.cpp",
        "include/QtCharts/qchart.h",
        "metatypes/qt6datavisualizationqml_metatypes.json",
        "qml/QtGraphs/qmldir",
        "typesystems/typesystem_charts.xml",
        "typesystems/datavisualization_common.xml",
    ]
    for name in [*behalten, *entfernen]:
        datei = pyside / name
        datei.parent.mkdir(parents=True, exist_ok=True)
        datei.write_bytes(b"")

    _qt_nur_gpl_entfernen(tmp_path)

    for name in behalten:
        assert (pyside / name).exists(), name
    for name in entfernen:
        assert not (pyside / name).exists(), name
    assert not (pyside / "include" / "QtCharts").exists()
    assert not (pyside / "qml" / "QtGraphs").exists()


def test_die_entwicklungsumgebung_hat_kein_ungeprueftes_paket() -> None:
    """Was im Entwicklungsbaum als Laufzeit-Abhängigkeit steht, landet
    auch in der Auslieferung. Fällt hier ein Paket auf, bricht später
    der Bau ab - besser, es zeigt sich schon beim Testlauf."""
    import sysconfig

    site_packages = Path(sysconfig.get_paths()["purelib"])
    erlaubte_nur_im_baum = {
        # Test- und Entwicklungswerkzeuge, die nicht mit ausgeliefert
        # werden.
        "pytest-qt",
    }
    beanstandungen = [
        zeile
        for zeile in lizenzen_pruefen(site_packages)
        if zeile.split(":")[0].lower() not in erlaubte_nur_im_baum
    ]
    assert beanstandungen == []
