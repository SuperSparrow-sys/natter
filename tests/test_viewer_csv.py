"""Tests für die CSV-Tabellenansicht (Abschnitt 11.5). Siehe
Arbeitspaket M5, Schritt 7. Headless.
"""

from __future__ import annotations

import gc
import threading
import time
import weakref
from itertools import pairwise
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt, QTimer
from PySide6.QtTest import QTest

from ide.viewers import CsvAnsicht, csv_erkennen


def _zelle(ansicht: CsvAnsicht, zeile: int, spalte: int) -> str:
    modell = ansicht.tabelle.model()
    return modell.index(zeile, spalte).data()


def _sichtbare_zeilen(ansicht: CsvAnsicht) -> list[int]:
    """Nummern der sichtbaren Zeilen der Tabelle, gleich ob der Filter
    Zeilen ausblendet oder aus dem Modell nimmt."""
    tabelle = ansicht.tabelle
    return [
        zeile for zeile in range(tabelle.model().rowCount())
        if not tabelle.isRowHidden(zeile)
    ]


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

    modell = ansicht.tabelle.model()
    assert modell.columnCount() == 2
    assert modell.rowCount() == 2
    assert modell.headerData(0, Qt.Orientation.Horizontal) == "name"
    assert _zelle(ansicht, 0, 0) == "Anna"


def test_csvansicht_aendert_die_datei_nicht(tmp_path: Path) -> None:
    datei = tmp_path / "schueler.csv"
    inhalt = "name,punkte\nAnna,12\n"
    datei.write_text(inhalt, encoding="utf-8")

    CsvAnsicht(datei)

    assert datei.read_text(encoding="utf-8") == inhalt


def test_csvansicht_filter_versteckt_nicht_passende_zeilen(
    tmp_path: Path, qtbot,  # noqa: ANN001
) -> None:
    datei = tmp_path / "schueler.csv"
    datei.write_text("name,punkte\nAnna,12\nBo,7\n", encoding="utf-8")
    ansicht = CsvAnsicht(datei)
    qtbot.addWidget(ansicht)

    ansicht._filter.setText("anna")

    qtbot.waitUntil(lambda: len(_sichtbare_zeilen(ansicht)) == 1)
    zeile = _sichtbare_zeilen(ansicht)[0]
    assert _zelle(ansicht, zeile, 0) == "Anna"


def test_csvansicht_als_text_umschalten_zeigt_rohtext(tmp_path: Path) -> None:
    datei = tmp_path / "schueler.csv"
    datei.write_text("name,punkte\nAnna,12\n", encoding="utf-8")
    ansicht = CsvAnsicht(datei)

    ansicht._umschalt_knopf.setChecked(True)

    assert ansicht._stapel.currentWidget() is ansicht._text
    assert "Anna" in ansicht._text.toPlainText()


def test_csvansicht_bleibt_mit_100000_zeilen_bedienbar(
    tmp_path: Path, qtbot,  # noqa: ANN001
) -> None:
    """Punkt 311: Öffnen unter 3 s, Sortieren und jeder Tastendruck im
    Filter unter 1 s, und eine Uhr im selben Faden setzt nie länger als
    1 s aus. Vorher dauerte der zweite Tastendruck 26 s und das
    Sortieren 36 s, und das Fenster stand so lange."""
    zeilen = [
        [
            str(nummer),
            f"Name {nummer % 997}",
            f"Ort {nummer % 101}",
            f"{nummer // 4},{nummer % 4 * 25}",
            f"2026-01-{nummer % 28 + 1:02d}",
        ]
        for nummer in range(100_000)
    ]
    datei = tmp_path / "gross.csv"
    datei.write_text(
        "nr;name;ort;wert;datum\n"
        + "".join(";".join(zeile) + "\n" for zeile in zeilen),
        encoding="utf-8",
    )

    beginn = time.perf_counter()
    ansicht = CsvAnsicht(datei)
    dauer_oeffnen = time.perf_counter() - beginn
    qtbot.addWidget(ansicht)
    ansicht.resize(800, 600)
    ansicht.show()

    schlaege: list[float] = []
    uhr = QTimer()
    uhr.setInterval(20)
    uhr.timeout.connect(lambda: schlaege.append(time.perf_counter()))
    uhr.start()
    qtbot.wait(100)

    beginn = time.perf_counter()
    ansicht.tabelle.sortByColumn(1, Qt.SortOrder.DescendingOrder)
    dauer_sortieren = time.perf_counter() - beginn
    qtbot.wait(100)
    assert _zelle(ansicht, 0, 1) == max(zeile[1] for zeile in zeilen)

    dauer_tasten = []
    for eingabe in ("4", "42"):
        erwartet = sum(
            any(eingabe in zelle.lower() for zelle in zeile)
            for zeile in zeilen
        )
        beginn = time.perf_counter()
        QTest.keyClick(ansicht._filter, eingabe[-1])
        qtbot.waitUntil(
            lambda erwartet=erwartet:
                len(_sichtbare_zeilen(ansicht)) == erwartet,
            timeout=10_000,
        )
        dauer_tasten.append(time.perf_counter() - beginn)
    qtbot.wait(100)
    uhr.stop()

    laengste_pause = max(
        spaeter - frueher for frueher, spaeter in pairwise(schlaege)
    )
    assert dauer_oeffnen < 3.0, dauer_oeffnen
    assert dauer_sortieren < 1.0, dauer_sortieren
    assert max(dauer_tasten) < 1.0, dauer_tasten
    assert laengste_pause < 1.0, laengste_pause


def test_csvansicht_haelt_bei_grossen_dateien_nicht_an(
    tmp_path: Path, qtbot,  # noqa: ANN001
) -> None:
    """Punkt 355: mit einer Million Zeilen hielten das Neuladen einer
    sortierten Tabelle, das Umschalten auf den Text und das Öffnen
    einer Datei mit offenem Anführungszeichen das Fenster jeweils
    mehrere Sekunden an. Eine 20-ms-Uhr im selben Faden darf jetzt nie
    länger als 2,5 s aussetzen. Geprüft mit 400.000 Zeilen, damit der
    Test kurz bleibt; gegen den alten Stand setzte die Uhr damit 6 s
    aus. Beim Messen mit einer Million Zeilen blieb sie allein unter
    0,6 s; in der vollen Suite mit
    acht Prozessen erreichte sie 1,15 s."""
    zeilen = [
        f"{n};Name {n % 997};{n // 4},{n % 4 * 25};Ort {n % 101}\n"
        for n in range(400_000)
    ]
    datei = tmp_path / "gross.csv"
    datei.write_text("Nr;Name;Wert;Ort\n" + "".join(zeilen), encoding="utf-8")
    zeilen[0] = "0;Neu;0,0;Ort 0\n"
    geaendert = "Nr;Name;Wert;Ort\n" + "".join(zeilen)
    zeilen[5] = '5;"Name 5;1,25;Ort 5\n'
    offen = tmp_path / "offen.csv"
    offen.write_text("Nr;Name;Wert;Ort\n" + "".join(zeilen), encoding="utf-8")
    del zeilen

    ansicht = CsvAnsicht(datei)
    qtbot.addWidget(ansicht)
    ansicht.resize(800, 600)
    ansicht.show()
    ansicht.tabelle.sortByColumn(2, Qt.SortOrder.AscendingOrder)

    schlaege: list[float] = []
    uhr = QTimer()
    uhr.setInterval(20)
    uhr.timeout.connect(lambda: schlaege.append(time.perf_counter()))
    uhr.start()
    qtbot.wait(100)

    datei.write_text(geaendert, encoding="utf-8")
    qtbot.waitUntil(lambda: _zelle(ansicht, 0, 1) == "Neu", timeout=60_000)
    qtbot.wait(100)
    ansicht._umschalt_knopf.click()
    qtbot.wait(100)
    zweite = CsvAnsicht(offen)
    qtbot.addWidget(zweite)
    zweite.show()
    qtbot.wait(100)
    uhr.stop()

    laengste_pause = max(
        spaeter - frueher for frueher, spaeter in pairwise(schlaege)
    )
    assert laengste_pause < 2.5, laengste_pause
    assert "ersten 50.000 Zeilen" in ansicht.hinweis
    assert "Ab Zeile 7 " in zweite.hinweis
    assert zweite._stapel.currentWidget() is zweite._text


def test_csvansicht_meldet_offenes_anfuehrungszeichen_statt_abzustuerzen(
    tmp_path: Path, qtbot,  # noqa: ANN001
) -> None:
    """Punkt 326: ein Feld mit offenem Anführungszeichen machte den
    Rest der Datei zu einem Feld über 128 KB, und `csv.reader` brach
    im Konstruktor ab. Jetzt nennt die Hinweiszeile die Zeile, die
    Tabelle behält die Zeilen davor, und die Rohansicht zeigt den
    ganzen Text."""
    datei = tmp_path / "messung.csv"
    datei.write_text(
        "name;wert;notiz\nZeile 1;1;a\nZeile 2;2;b\nZeile 3;3;\"5 Zoll\n"
        + "".join(f"Zeile {n};{n};x\n" for n in range(4, 20_000)),
        encoding="utf-8",
    )

    ansicht = CsvAnsicht(datei)
    qtbot.addWidget(ansicht)

    assert "Ab Zeile 4 " in ansicht.hinweis
    assert "Anführungszeichen" in ansicht.hinweis
    assert ansicht.tabelle.model().rowCount() == 2
    assert ansicht._stapel.currentWidget() is ansicht._text
    assert "Zeile 19999;19999;x" in ansicht._text.toPlainText()


def test_csvansicht_sortiert_zahlen_nach_wert(
    tmp_path: Path, qtbot,  # noqa: ANN001
) -> None:
    """Punkt 329: Zahlen, auch mit Dezimalkomma, nach Wert und vor
    Texten, leere Zellen am Ende; absteigend bleiben sie dort."""
    datei = tmp_path / "noten.csv"
    datei.write_text(
        "Name;Punkte;Schnitt\n"
        'Anna;9;"2,5"\nBo;10;"11,25"\nCem;100;3\nDana;25;"1,75"\n'
        "Eli;;fehlt\n",
        encoding="utf-8",
    )
    ansicht = CsvAnsicht(datei)
    qtbot.addWidget(ansicht)
    tabelle = ansicht.tabelle

    def spalte(nummer: int) -> list[str]:
        return [
            _zelle(ansicht, zeile, nummer)
            for zeile in range(tabelle.model().rowCount())
        ]

    tabelle.sortByColumn(1, Qt.SortOrder.AscendingOrder)
    assert spalte(1) == ["9", "10", "25", "100", ""]
    tabelle.sortByColumn(1, Qt.SortOrder.DescendingOrder)
    assert spalte(1) == ["100", "25", "10", "9", ""]
    tabelle.sortByColumn(2, Qt.SortOrder.AscendingOrder)
    assert spalte(2) == ["1,75", "2,5", "3", "11,25", "fehlt"]


def test_csvansicht_sortiert_text_wie_ein_woerterbuch(
    tmp_path: Path, qtbot,  # noqa: ANN001
) -> None:
    """Umlaute standen hinter „Z“, kleine Anfangsbuchstaben hinter
    allen großen."""
    datei = tmp_path / "klasse.csv"
    datei.write_text(
        "Name\nZimmer\nÖzdemir\nanna\nBauer\nÄrger\nulla\n",
        encoding="utf-8",
    )
    ansicht = CsvAnsicht(datei)
    qtbot.addWidget(ansicht)
    tabelle = ansicht.tabelle

    tabelle.sortByColumn(0, Qt.SortOrder.AscendingOrder)

    assert [
        _zelle(ansicht, zeile, 0) for zeile in range(tabelle.model().rowCount())
    ] == ["anna", "Ärger", "Bauer", "Özdemir", "ulla", "Zimmer"]


def test_csvansicht_laedt_nach_aenderung_der_datei_neu(
    tmp_path: Path, qtbot,  # noqa: ANN001
) -> None:
    """Punkt 330: schreibt ein Programm die offene Datei neu, zeigt die
    Tabelle den neuen Inhalt; Filter und Sortierung bleiben."""
    datei = tmp_path / "punkte.csv"
    datei.write_text(
        "name;punkte\nAnna;12\nBo;7\nCem;30\nAnnika;5\n", encoding="utf-8",
    )
    ansicht = CsvAnsicht(datei)
    qtbot.addWidget(ansicht)
    ansicht.tabelle.sortByColumn(1, Qt.SortOrder.AscendingOrder)
    ansicht._filter.setText("ann")
    qtbot.waitUntil(lambda: ansicht.tabelle.model().rowCount() == 2)

    datei.write_text(
        "name;punkte\nAnna;12\nBo;7\nAnnette;100\nHanna;8\nAnnika;5\n",
        encoding="utf-8",
    )

    qtbot.waitUntil(
        lambda: ansicht.tabelle.model().rowCount() == 4, timeout=5_000,
    )
    assert [_zelle(ansicht, zeile, 0) for zeile in range(4)] == [
        "Annika", "Hanna", "Anna", "Annette",
    ]
    kopfleiste = ansicht.tabelle.horizontalHeader()
    assert kopfleiste.sortIndicatorSection() == 1
    assert ansicht._filter.text() == "ann"


def test_csvansicht_verfaellt_ein_neuladen_nach_dem_schliessen(
    tmp_path: Path, qtbot, monkeypatch,  # noqa: ANN001
) -> None:
    """Punkt 411: der Nebenfaden hielt die Ansicht selbst und sendete
    nach ihrem Löschen an ein zerstörtes Widget; im CI endete das mit
    „access violation“. Er darf nur den Boten halten, und sein
    Ergebnis verfällt."""
    from ide.viewers import csv_ansicht

    datei = tmp_path / "punkte.csv"
    datei.write_text("name;punkte\nAnna;12\n", encoding="utf-8")
    ansicht = CsvAnsicht(datei)

    weiter = threading.Event()
    echt = csv_ansicht._datei_lesen

    def langsam(*args, **kwargs):  # noqa: ANN002, ANN003, ANN202
        weiter.wait(10)
        return echt(*args, **kwargs)

    monkeypatch.setattr(csv_ansicht, "_datei_lesen", langsam)
    ansicht._neu_laden()
    faden = next(
        f for f in threading.enumerate() if f.name == "CsvAnsicht-Neuladen"
    )

    verweis = weakref.ref(ansicht)
    ansicht.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    del ansicht
    gc.collect()
    try:
        assert verweis() is None, "der Nebenfaden hält die Ansicht"
    finally:
        weiter.set()
        faden.join(10)
    assert not faden.is_alive()
    qtbot.wait(50)


@pytest.mark.parametrize(
    ("inhalt", "hinweis", "zeilen"),
    [
        (
            'Name;Note\nAnna;2\nBen;"1\nCem;3\nDana;4\n',
            "Ab Zeile 3 ",
            1,
        ),
        ('Name;Note\nBen;"1\nCem;3', "Ab Zeile 2 ", 0),
        ('Name;Notiz\nAnna;"zwei\nZeilen; mit Semikolon"\nBen;1\n', "", 2),
        ('Name;Notiz\nAnna;"am Ende\nüber zwei Zeilen"', "", 1),
    ],
    ids=["mitten", "ein_datensatz", "gueltig_mehrzeilig", "gueltig_am_ende"],
)
def test_csvansicht_findet_offenes_anfuehrungszeichen_in_kleiner_datei(
    tmp_path: Path, qtbot,  # noqa: ANN001
    inhalt: str, hinweis: str, zeilen: int,
) -> None:
    """Punkt 347: unter 128 KB bricht `csv.reader` bei einem offenen
    Anführungszeichen nicht ab, sondern nimmt den Rest der Datei in ein
    Feld. Die Tabelle wirkte nur kürzer. Ein ordentlich geschlossenes
    Feld über mehrere Zeilen ist dagegen gültig und bleibt ohne
    Hinweis."""
    datei = tmp_path / "noten.csv"
    datei.write_text(inhalt, encoding="utf-8")

    ansicht = CsvAnsicht(datei)
    qtbot.addWidget(ansicht)

    if hinweis:
        assert ansicht.hinweis.startswith(hinweis)
        assert "Anführungszeichen" in ansicht.hinweis
    else:
        assert ansicht.hinweis == ""
    assert ansicht.tabelle.model().rowCount() == zeilen


def test_csvansicht_hinweis_und_knopf_passen_zur_ansicht(
    tmp_path: Path, qtbot,  # noqa: ANN001
) -> None:
    """Punkt 353: nach einem Lesefehler steht der Text da, der Knopf
    war gedrückt und hieß weiter „Als Text anzeigen“, und der Hinweis
    verwies auf genau diesen Knopf."""
    datei = tmp_path / "noten.csv"
    datei.write_text(
        'Name;Note\nAnna;2\nBen;"1\n'
        + "".join(f"Name {n};{n % 6 + 1}\n" for n in range(20_000)),
        encoding="utf-8",
    )
    ansicht = CsvAnsicht(datei)
    qtbot.addWidget(ansicht)

    assert ansicht._stapel.currentWidget() is ansicht._text
    assert ansicht._umschalt_knopf.text() == "Als Tabelle anzeigen"
    assert "Als Text anzeigen" not in ansicht.hinweis
    assert "als Text" in ansicht.hinweis

    ansicht._umschalt_knopf.click()

    assert ansicht._stapel.currentWidget() is ansicht.tabelle
    assert ansicht._umschalt_knopf.text() == "Als Text anzeigen"
    assert "Ab Zeile 3 " in ansicht.hinweis
    assert "als Text" not in ansicht.hinweis
