"""Tests für die CSV-Tabellenansicht (Abschnitt 11.5). Siehe
docs/arbeitspakete/M5.md, Schritt 7. Headless.
"""

from __future__ import annotations

from pathlib import Path

from ide.viewers import CsvAnsicht, csv_erkennen


def test_csv_erkennen_utf8_mit_komma(tmp_path: Path) -> None:
    datei = tmp_path / "schueler.csv"
    datei.write_text("name,ort\nAnna,Köln\n", encoding="utf-8")

    trennzeichen, zeichensatz = csv_erkennen(datei)

    assert trennzeichen == ","
    assert zeichensatz == "utf-8"


def test_csv_erkennen_excel_export_windows1252_semikolon(tmp_path: Path) -> None:
    datei = tmp_path / "verkauf.csv"
    datei.write_bytes("name;ort\nAnna;Köln\n".encode("cp1252"))

    trennzeichen, zeichensatz = csv_erkennen(datei)

    assert trennzeichen == ";"
    assert zeichensatz == "cp1252"


def test_csvansicht_zeigt_kopfzeile_und_daten(tmp_path: Path) -> None:
    datei = tmp_path / "schueler.csv"
    datei.write_text("name,punkte\nAnna,12\nBo,7\n", encoding="utf-8")

    ansicht = CsvAnsicht(datei)

    assert ansicht.tabelle.columnCount() == 2
    assert ansicht.tabelle.rowCount() == 2
    assert ansicht.tabelle.horizontalHeaderItem(0).text() == "name"
    assert ansicht.tabelle.item(0, 0).text() == "Anna"


def test_csvansicht_aendert_die_datei_nicht(tmp_path: Path) -> None:
    datei = tmp_path / "schueler.csv"
    inhalt = "name,punkte\nAnna,12\n"
    datei.write_text(inhalt, encoding="utf-8")

    CsvAnsicht(datei)

    assert datei.read_text(encoding="utf-8") == inhalt


def test_csvansicht_filter_versteckt_nicht_passende_zeilen(tmp_path: Path) -> None:
    datei = tmp_path / "schueler.csv"
    datei.write_text("name,punkte\nAnna,12\nBo,7\n", encoding="utf-8")
    ansicht = CsvAnsicht(datei)

    ansicht._filter.setText("anna")

    assert ansicht.tabelle.isRowHidden(0) is False
    assert ansicht.tabelle.isRowHidden(1) is True


def test_csvansicht_als_text_umschalten_zeigt_rohtext(tmp_path: Path) -> None:
    datei = tmp_path / "schueler.csv"
    datei.write_text("name,punkte\nAnna,12\n", encoding="utf-8")
    ansicht = CsvAnsicht(datei)

    ansicht._umschalt_knopf.setChecked(True)

    assert ansicht._stapel.currentWidget() is ansicht._text
    assert "Anna" in ansicht._text.toPlainText()
