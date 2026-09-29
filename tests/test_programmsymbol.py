"""Symbol eines Programms ohne eigenes `icon` (Punkt 415).

Bis 0.4.2 zeigte Windows für ein Formular ohne `icon` ein leeres
Fenstersymbol in Titelleiste und Taskleiste. Jetzt steht dort das
Symbol von Natter; ein eigenes `icon` hat Vorrang.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from pcl import Application, Form
from pcl.theme import NATTER_SYMBOL


@pytest.fixture
def ohne_programmsymbol(qapp):  # noqa: ANN001, ANN201
    """Das Symbol der Anwendung gilt für den ganzen Testprozess; es
    wird vorher geleert und hinterher wiederhergestellt."""
    vorher = qapp.windowIcon()
    qapp.setWindowIcon(QIcon())
    yield qapp
    qapp.setWindowIcon(vorher)


def test_das_symbol_liegt_im_ordner_design() -> None:
    assert NATTER_SYMBOL.is_file()
    assert NATTER_SYMBOL.parent.name == "design"


def test_ein_formular_ohne_icon_zeigt_das_symbol_von_natter(
    ohne_programmsymbol, qtbot,  # noqa: ANN001
) -> None:
    Application()
    form = Form()
    qtbot.addWidget(form._qwidget)

    symbol = form._qwidget.windowIcon()
    assert not symbol.isNull()
    assert symbol.cacheKey() == QApplication.windowIcon().cacheKey()


def test_ein_eigenes_icon_hat_vorrang(
    ohne_programmsymbol, qtbot, tmp_path: Path,  # noqa: ANN001
) -> None:
    Application()
    eigenes = tmp_path / "eigen.png"
    QIcon(str(NATTER_SYMBOL)).pixmap(16, 16).save(str(eigenes))
    form = Form()
    qtbot.addWidget(form._qwidget)
    form.icon = str(eigenes)

    assert form._qwidget.windowIcon().cacheKey() != (
        QApplication.windowIcon().cacheKey()
    )
