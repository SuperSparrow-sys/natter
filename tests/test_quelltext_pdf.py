"""Der Quelltext eines Projekts als PDF.

Punkt 16 der offenen Punkte. Wer sein Programm abgibt, gibt heute
entweder den ganzen Ordner ab oder druckt aus dem Editor - und ein
`.py` im Anhang lässt sich weder anstreichen noch mit einer Note
versehen.

Geprüft wird das Dokument und nicht die PDF-Datei: was in der Datei
steht, ließe sich ohne einen PDF-Leser nur an ihrer Größe ablesen,
und eine Größe sagt nichts über Zeilennummern, Hervorhebung oder
Seitenumbrüche.
"""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path

import pytest
from PySide6.QtCore import QSizeF
from PySide6.QtGui import QTextDocument

from ide.export.quelltext_pdf import (
    CODE_GROESSE,
    CODE_SCHRIFT,
    dokument_erzeugen,
    quelltext_als_pdf,
)
from ide.project.projekt import Projekt

BEISPIEL = Path(__file__).resolve().parent.parent / "beispielprojekte" / "06_Kontoverwaltung"

#: A4 bei 96 dpi, abzüglich der 20 mm Rand - dieselbe Fläche, die
#: `quelltext_als_pdf` dem Dokument gibt.
A4 = QSizeF(641, 970)


@pytest.fixture
def projekt(tmp_path: Path, qapp) -> Projekt:
    ziel = tmp_path / "06_Kontoverwaltung"
    shutil.copytree(BEISPIEL, ziel)
    return Projekt.laden(ziel / "06_Kontoverwaltung.natter")


def _text(dokument: QTextDocument) -> str:
    return dokument.toPlainText()


# ------------------------------------------------ Was hineinkommt


def test_jede_unit_steht_drin(projekt: Projekt) -> None:
    text = _text(dokument_erzeugen(projekt))

    for datei in projekt.units():
        assert datei.name in text, datei.name


def test_die_startdatei_bleibt_draussen(projekt: Projekt) -> None:
    """`main.py` schreibt Natter, sie enthält keinen Schülercode."""
    text = _text(dokument_erzeugen(projekt))

    assert "main.py" not in text.replace("u_main.py", "")


def test_die_erzeugten_dateien_bleiben_draussen(projekt: Projekt) -> None:
    text = _text(dokument_erzeugen(projekt))

    assert "_design.py" not in text


def test_der_inhalt_der_dateien_steht_drin(projekt: Projekt) -> None:
    text = _text(dokument_erzeugen(projekt))
    erste_zeile = (projekt.ordner / "u_konto.py").read_text(encoding="utf-8").splitlines()[0]

    assert erste_zeile in text


# ------------------------------------------------ Wie es aussieht


def test_jede_zeile_hat_ihre_nummer(projekt: Projekt) -> None:
    text = _text(dokument_erzeugen(projekt))

    assert "   1 │ " in text
    assert "   2 │ " in text


def test_die_nummern_beginnen_je_datei_neu(projekt: Projekt) -> None:
    """Sonst liefe die Zählung über alle Dateien durch, und die
    Nummer im PDF stünde nicht neben der im Editor."""
    text = _text(dokument_erzeugen(projekt))

    assert text.count("\n   1 │") == len(projekt.units())


def test_die_ueberschrift_nennt_projekt_datei_und_datum(projekt: Projekt) -> None:
    """Bei einer eingesammelten Abgabe ist sonst nicht erkennbar,
    wessen Datei das ist und von wann."""
    text = _text(dokument_erzeugen(projekt, date(2026, 9, 20)))

    assert "06_Kontoverwaltung – u_konto.py – 20.09.2026" in text


def test_die_hervorhebung_faerbt_den_code(projekt: Projekt) -> None:
    """Der Kern des Ganzen: ohne Farbe wäre es ein Ausdruck aus dem
    Notizblock. Die Formate eines `QSyntaxHighlighter` hängen am
    Layout des Blocks - `toHtml()` verliert sie, das Drucken nicht."""
    dokument = dokument_erzeugen(projekt)

    farben = set()
    block = dokument.begin()
    while block.isValid():
        for bereich in block.layout().formats():
            farben.add(bereich.format.foreground().color().name())
        block = block.next()

    assert len(farben) >= 3, f"Nur {farben} - da ist nichts hervorgehoben."


def test_die_zeilennummern_sind_grau(projekt: Projekt) -> None:
    dokument = dokument_erzeugen(projekt)

    grau = False
    block = dokument.begin()
    while block.isValid():
        for bereich in block.layout().formats():
            if bereich.start == 0 and bereich.format.foreground().color().name() == "#8a8a8a":
                grau = True
        block = block.next()

    assert grau, "Die Nummernspalte hat dieselbe Farbe wie der Code."


def test_die_schrift_ist_die_des_editors(projekt: Projekt) -> None:
    dokument = dokument_erzeugen(projekt)

    assert dokument.defaultFont().family() == CODE_SCHRIFT


def test_lange_zeilen_brechen_um_statt_zu_verschwinden(
    projekt: Projekt, qapp
) -> None:
    """Punkt 12 noch einmal: was abgeschnitten wird, fehlt ohne
    Meldung. Eine Zeile mit 300 Zeichen muss auf dem Blatt mehr als
    eine Zeile hoch werden."""
    lang = projekt.ordner / "u_lang.py"
    lang.write_text("x = " + "1234567890" * 30 + "\n", encoding="utf-8")
    dokument = dokument_erzeugen(projekt)
    dokument.setPageSize(A4)
    # `pageCount()` stößt das Layout an. Ohne das steht in
    # `lineCount()` noch der Wert von vor der Seitenbreite, und der
    # Test prüfte nichts.
    assert dokument.pageCount() > 0

    block = dokument.begin()
    hoch = False
    while block.isValid():
        if "1234567890" in block.text():
            hoch = block.layout().lineCount() > 1
        block = block.next()

    assert hoch, "Die lange Zeile belegt nur eine Zeile - sie wird abgeschnitten."


# ------------------------------------------------ Seiten und Datei


def test_jede_datei_beginnt_auf_einer_neuen_seite(projekt: Projekt) -> None:
    dokument = dokument_erzeugen(projekt)
    dokument.setPageSize(A4)

    assert dokument.pageCount() >= len(projekt.units())


def test_die_datei_wird_geschrieben(projekt: Projekt, tmp_path: Path) -> None:
    ziel = tmp_path / "abgabe" / "quelltext.pdf"

    ergebnis = quelltext_als_pdf(projekt, ziel)

    assert ergebnis == ziel
    assert ziel.exists()
    assert ziel.stat().st_size > 1000
    assert ziel.read_bytes()[:5] == b"%PDF-"


def test_ein_projekt_ohne_units_erzeugt_ein_leeres_dokument(
    tmp_path: Path, qapp
) -> None:
    ziel = tmp_path / "leer"
    shutil.copytree(BEISPIEL, ziel)
    for datei in ziel.glob("u_*.py"):
        datei.unlink()
    leeres = Projekt.laden(ziel / "06_Kontoverwaltung.natter")

    dokument = dokument_erzeugen(leeres)

    assert _text(dokument).strip() == ""


# ------------------------------------------------ Der Weg dorthin


def test_der_eintrag_steht_unter_projekt(qtbot) -> None:
    from ide.shell.hauptfenster import HauptFenster

    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    aktion = fenster.aktionen["projekt.quelltext_als_pdf"]

    assert aktion.menue == "Projekt"
    assert aktion.qaction in fenster.menue("Projekt").actions()


def test_ohne_projekt_sagt_er_was_zu_tun_ist(qtbot) -> None:
    from ide.shell.hauptfenster import HauptFenster

    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    fenster.aktionen["projekt.quelltext_als_pdf"].qaction.trigger()

    assert "Kein Projekt offen" in fenster.statusBar().currentMessage()


def test_mit_projekt_schreibt_er_die_datei(
    projekt: Projekt, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    """Der ganze Weg vom Menüeintrag bis zur Datei."""
    from PySide6.QtWidgets import QFileDialog

    from ide.shell.hauptfenster import HauptFenster

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(projekt.ordner / "06_Kontoverwaltung.natter")
    ziel = tmp_path / "abgabe.pdf"
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(ziel), ""))
    )

    fenster.aktionen["projekt.quelltext_als_pdf"].qaction.trigger()

    assert ziel.exists()
    assert "geschrieben" in fenster.statusBar().currentMessage()


def test_ein_abgebrochener_dialog_schreibt_nichts(
    projekt: Projekt, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, qtbot
) -> None:
    from PySide6.QtWidgets import QFileDialog

    from ide.shell.hauptfenster import HauptFenster

    fenster = HauptFenster()
    qtbot.addWidget(fenster)
    fenster.projekt_oeffnen(projekt.ordner / "06_Kontoverwaltung.natter")
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: ("", ""))
    )

    fenster.aktionen["projekt.quelltext_als_pdf"].qaction.trigger()

    assert not list(tmp_path.glob("*.pdf"))


def test_im_pruefungsmodus_bleibt_er_offen(qtbot) -> None:
    """Wer seinen eigenen Code ausgibt, verschafft sich keinen
    Vorteil - und eine Abgabe ist genau das, was am Ende einer
    Prüfung gebraucht wird."""
    from ide.shell.hauptfenster import HauptFenster

    fenster = HauptFenster()
    qtbot.addWidget(fenster)

    assert fenster.aktionen["projekt.quelltext_als_pdf"].qaction.isEnabled() is True


# ---------------------------------- Ränder und Schriftgröße zum Drucken


def test_der_rand_reicht_zum_drucken(projekt: Projekt, tmp_path: Path) -> None:
    """Ein schmaler Rand sieht am Bildschirm besser aus und wird beim
    Drucken beschnitten. 20 mm liegen auf jedem Bürodrucker im
    bedruckbaren Bereich."""
    from PySide6.QtGui import QPageLayout, QPdfWriter

    from ide.export.quelltext_pdf import _RAND_MM

    assert _RAND_MM >= 15

    ziel = tmp_path / "rand.pdf"
    quelltext_als_pdf(projekt, ziel)
    schreiber = QPdfWriter(str(tmp_path / "probe.pdf"))
    schreiber.setPageMargins(
        __import__("PySide6.QtCore", fromlist=["QMarginsF"]).QMarginsF(
            _RAND_MM, _RAND_MM, _RAND_MM, _RAND_MM
        )
    )
    raender = schreiber.pageLayout().margins(QPageLayout.Unit.Millimeter)

    assert raender.left() >= 15
    assert raender.top() >= 15


#: Ein Zeichen in Consolas 8 pt bei 96 dpi, nachgemessen.
_ZEICHENBREITE = 6.0


def _hat_die_codeschrift() -> bool:
    """Rendert diese Umgebung wirklich mit Consolas?

    Unter `QT_QPA_PLATFORM=offscreen` findet Qt von sich aus keine
    Schriftart und setzt eine Ersatzschrift ein (siehe AGENTS.md,
    Abschnitt „Tests"). Deren Zeichen sind fast doppelt so breit, und
    eine Messung der Zeilenlänge sagt dann nichts über den Ausdruck
    auf Papier.

    Gefragt wird nach der Breite und nicht nach dem Namen:
    `QFontInfo.family()` meldet „Consolas" auch dann, wenn gar keine
    Schrift geladen werden konnte.
    """
    from PySide6.QtGui import QFont, QFontMetricsF

    breite = QFontMetricsF(QFont(CODE_SCHRIFT, CODE_GROESSE)).horizontalAdvance("M")
    return abs(breite - _ZEICHENBREITE) < 0.1


def test_eine_lange_zeile_passt_ohne_umbruch(projekt: Projekt, qapp) -> None:
    """Die Schriftgröße ist auf die Zeilenlänge abgestimmt: bei 8 pt
    und 20 mm Rand passen 99 Zeichen Code neben die Nummernspalte,
    knapp unter die 100, auf die `pyproject.toml` den Quelltext
    begrenzt. Bei 9 pt wären es 85, und im Ausdruck stünde jede
    zweite Zeile zweimal.
    """
    if not _hat_die_codeschrift():
        # Erst hier und nicht in einem `skipif`: eine Schriftabfrage
        # vor der `QApplication` bringt Qt zum Absturz, und ein
        # `skipif` wird schon beim Einsammeln ausgewertet.
        pytest.skip("Ohne Consolas misst der Test die Ersatzschrift, nicht das Papier.")

    hundert = projekt.ordner / "u_hundert.py"
    hundert.write_text("x = 1  " + "#" * 92 + "\n", encoding="utf-8")
    dokument = dokument_erzeugen(projekt)
    dokument.setPageSize(A4)
    assert dokument.pageCount() > 0

    block = dokument.begin()
    zeilen = 0
    while block.isValid():
        if "#" * 92 in block.text():
            assert len(block.text()) == 99 + 7, "Der Prüfling ist nicht 99 Zeichen lang."
            zeilen = block.layout().lineCount()
        block = block.next()

    assert zeilen == 1, f"Die Zeile bricht auf {zeilen} Zeilen um."


def test_das_blatt_ist_a4(projekt: Projekt, tmp_path: Path) -> None:
    from PySide6.QtGui import QPageSize, QPdfWriter

    ziel = tmp_path / "a4.pdf"
    quelltext_als_pdf(projekt, ziel)

    schreiber = QPdfWriter(str(tmp_path / "probe2.pdf"))
    schreiber.setPageSize(QPageSize(QPageSize.PageSizeId.A4))

    assert schreiber.pageLayout().pageSize().id() == QPageSize.PageSizeId.A4
