"""Die Beispielprojekte werden bedient, nicht nur geladen.

Anlass : der Nutzer bat darum, „die ganzen
Programmierfehler" in den Beispielen zu beheben, „wie in der Auswahl von
dem regressions Formel". Dieser eine Fehler war nach zwei Minuten
Durchspielen sichtbar und hätte von keinem der vorhandenen Tests
gefunden werden können: sie prüften, dass jedes Projekt startet und
dass die erzeugten Dateien zum Formular passen - nicht, ob beim Klicken
das Richtige herauskommt.

Die Tests hier gehen deshalb den Weg einer Schülerin: Felder füllen,
Knöpfe drücken, Auswahl wechseln, und nachsehen, was auf dem Formular
steht. Ausgelöst wird über das Qt-Widget, wo es um die Ereigniskette
geht (ein Klick in eine Liste), und über die Methode, wo es um das
Rechnen geht.

Geschrieben wird dabei nichts: die Projekte werden nur gelesen und
bedient, keine Datei im Repository verändert.
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

BEISPIELE = Path(__file__).resolve().parent.parent / "beispielprojekte"

#: Jedes hier gebaute Formular bleibt bis zum Ende des Testlaufs am
#: Leben. Das ist Absicht und war teuer gelernt: mit
#: `qtbot.addWidget(...)` löscht Qt das C++-Widget am Testende, während
#: die Python-Objekte der Komponenten noch stehen. Der Müllsammler räumt
#: sie irgendwann später weg - mitten in einem ganz anderen Test -, und
#: dessen `processEvents()` fällt dann über „libshiboken: Internal C++
#: object (_KlickbaresLabel) already deleted". Genau so sind 33
#: Debugger- und Diagramm-Tests umgefallen, die mit diesen Beispielen
#: nichts zu tun haben. Wer nichts zerstört, hat das Problem nicht; ein
#: paar Formulare im Speicher kosten nichts.
_AM_LEBEN: list[object] = []


@pytest.fixture
def beispiel(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """Baut das Formular eines Beispielprojekts, wie sein `main.py` es täte.

    Der Projektordner muss auf `sys.path` und das Arbeitsverzeichnis
    sein - die Projekte finden ihre Daten relativ zu sich selbst.
    Danach wird beides zurückgedreht, damit sich zwei Projekte im selben
    Testlauf nicht in die Quere kommen: alle nennen ihr Hauptmodul
    `u_main`.
    """

    def laden(projekt: str):
        ordner = BEISPIELE / projekt
        monkeypatch.syspath_prepend(str(ordner))
        monkeypatch.chdir(ordner)
        for name in [n for n in sys.modules if n.startswith("u_")]:
            sys.modules.pop(name, None)
        modul = importlib.import_module("u_main")
        formular = modul.Form1()
        _AM_LEBEN.append(formular)
        if hasattr(formular, "form_create"):
            formular.form_create(formular)
        return modul, formular

    yield laden

    for name in [n for n in sys.modules if n.startswith("u_")]:
        sys.modules.pop(name, None)


# -- Stufe 3: der Taschenrechner ----------------------------------------


@pytest.fixture
def rechner(beispiel):
    _modul, formular = beispiel("03_Taschenrechner")
    return formular


@pytest.mark.parametrize(
    ("a", "b", "knopf", "erwartet"),
    [
        ("7", "3", "b_plus_click", "Ergebnis: 7 + 3 = 10"),
        ("7", "3", "b_minus_click", "Ergebnis: 7 - 3 = 4"),
        ("7", "3", "b_mal_click", "Ergebnis: 7 * 3 = 21"),
        ("7", "2", "b_geteilt_click", "Ergebnis: 7 / 2 = 3,5"),
        ("-4", "9", "b_plus_click", "Ergebnis: -4 + 9 = 5"),
    ],
)
def test_der_rechner_rechnet_richtig(rechner, a, b, knopf, erwartet) -> None:
    rechner.e_zahl1.text = a
    rechner.e_zahl2.text = b

    getattr(rechner, knopf)(rechner)

    assert rechner.l_ergebnis.caption == erwartet


def test_der_rechner_nimmt_das_deutsche_dezimalkomma(rechner) -> None:
    """„2,5" ist das, was eine Schülerin tippt. Früher kam
 darauf „Bitte in beide Felder eine Zahl schreiben." - obwohl genau
 das getan worden war. Alle späteren Stufen nahmen das Komma
 längst an."""
    rechner.e_zahl1.text = "2,5"
    rechner.e_zahl2.text = "0,5"

    rechner.b_mal_click(rechner)

    assert rechner.l_ergebnis.caption == "Ergebnis: 2,5 * 0,5 = 1,25"


def test_das_ergebnis_steht_ebenfalls_mit_komma_da(rechner) -> None:
    """Eingabe mit Komma und Ausgabe mit Punkt in derselben Zeile sieht
    aus wie ein Fehler."""
    rechner.e_zahl1.text = "1"
    rechner.e_zahl2.text = "4"

    rechner.b_geteilt_click(rechner)

    assert rechner.l_ergebnis.caption == "Ergebnis: 1 / 4 = 0,25"


def test_teilen_durch_null_wird_abgefangen(rechner) -> None:
    rechner.e_zahl1.text = "7"
    rechner.e_zahl2.text = "0"

    rechner.b_geteilt_click(rechner)

    assert rechner.l_ergebnis.caption == "Durch null kann man nicht teilen."


@pytest.mark.parametrize(("a", "b"), [("abc", "3"), ("", ""), ("1", "zwei")])
def test_was_keine_zahl_ist_wird_freundlich_abgelehnt(rechner, a, b) -> None:
    rechner.e_zahl1.text = a
    rechner.e_zahl2.text = b

    rechner.b_plus_click(rechner)

    assert rechner.l_ergebnis.caption == "Bitte in beide Felder eine Zahl schreiben."


# -- Stufe 8: die Regression --------------------------------------------


def test_die_regression_zeigt_zu_jeder_art_ihre_eigene_formel(beispiel) -> None:
    """Der Fehler, nach dem der Nutzer gefragt hat. Ein Klick auf
    „polynomial" zeigte die lineare Formel, „exponentiell" die
    polynomiale - die Anzeige hinkte der Auswahl einen Schritt
    hinterher. Die Ursache lag in `pcl.ComboBox` (siehe
    `test_components_listen.py`); hier steht, wie es sich im Programm
    ausgewirkt hat."""
    modul, formular = beispiel("08_Regression")

    formeln = {}
    for index, art in enumerate(modul.ARTEN):
        formular.cb_art._qwidget.setCurrentIndex(index)
        formeln[art] = formular.l_formel.caption

    assert len(set(formeln.values())) == len(modul.ARTEN), (
        f"Zwei Arten zeigen dieselbe Formel: {formeln}"
    )
    assert "·x²" in formeln["polynomial"]
    assert "e^(" in formeln["exponentiell"]
    assert "ln(x)" in formeln["logarithmisch"]


def test_die_regression_sagt_zu_jeder_art_etwas_vorher(beispiel) -> None:
    modul, formular = beispiel("08_Regression")

    for index in range(len(modul.ARTEN)):
        formular.cb_art._qwidget.setCurrentIndex(index)

        assert "Schuhgröße" in formular.l_ergebnis.caption
        assert 0.0 <= formular.ergebnis.bestimmtheitsmass <= 1.0


def test_die_regression_zeigt_ihre_zahlen_deutsch(beispiel) -> None:
    """Die Formel kommt mit Komma aus `pcl`; daneben stand das
    Bestimmtheitsmaß mit Punkt."""
    _modul, formular = beispiel("08_Regression")

    assert "." not in formular.l_guete.caption
    assert "," in formular.l_guete.caption
    assert "." not in formular.l_ergebnis.caption


# -- Stufe 7: die CSV-Auswertung ----------------------------------------


def test_die_csv_auswertung_zeigt_zu_jedem_ort_seine_daten(beispiel) -> None:
    """Derselbe ComboBox-Fehler wie in Stufe 8: die Auswertung gehörte
    zum vorher gewählten Ort."""
    _modul, formular = beispiel("07_CsvAuswertung")

    for index in range(formular.cb_ort._qwidget.count()):
        ort = formular.cb_ort._qwidget.itemText(index)
        formular.cb_ort._qwidget.setCurrentIndex(index)

        assert formular.l_ergebnis.caption.startswith(ort)
        eigene = [z for z in formular.zeilen if z["Ort"] == ort]
        assert formular.sg_tabelle.row_count == len(eigene) + 1
        assert formular.sg_tabelle.cells[0, 1] == eigene[0]["Monat"]


def test_die_csv_auswertung_rechnet_deutsch(beispiel) -> None:
    _modul, formular = beispiel("07_CsvAuswertung")

    assert "Mittelwert 9,7 °C" in formular.l_ergebnis.caption


# -- Stufe 6: die Kontoverwaltung ---------------------------------------


def test_geldbetraege_stehen_mit_komma_da(monkeypatch: pytest.MonkeyPatch) -> None:
    """Geld ohne Dezimalkomma liest sich in einem deutschen Programm
    falsch - „120.50 Euro" ist keine Schreibweise, die jemand benutzt.

    Geprüft an `u_konto` allein: die Klasse trägt die Regel, das
    Formular zeigt sie nur an. Ein Formular wird hier nicht gebraucht,
    und `06_Kontoverwaltung` legte beim Aufbauen seine `konten.sqlite`
    im Repository an."""
    monkeypatch.syspath_prepend(str(BEISPIELE / "06_Kontoverwaltung"))
    for name in [n for n in sys.modules if n.startswith("u_")]:
        sys.modules.pop(name, None)

    u_konto = importlib.import_module("u_konto")

    assert u_konto.euro(120.5) == "120,50"
    assert u_konto.euro(0) == "0,00"

    konto = u_konto.Konto(1, "Anna", 120.5)
    with pytest.raises(u_konto.NichtGenugGeld) as fehler:
        konto.abheben(999)
    assert "120,50 Euro" in str(fehler.value)

    for name in [n for n in sys.modules if n.startswith("u_")]:
        sys.modules.pop(name, None)


# -- Stufe 5: die Bildergalerie -----------------------------------------


def test_die_galerie_zeigt_zum_gewaehlten_eintrag_das_passende_bild(beispiel) -> None:
    _modul, formular = beispiel("05_Bildergalerie")

    for index in range(len(formular.bilder)):
        formular.lb_bilder._qwidget.setCurrentRow(index)
        name = formular.bilder[index].name

        assert Path(formular.i_vorschau.picture.pfad).name == name
        assert formular.l_info.caption.startswith(name)


def test_die_galerie_nennt_die_dateigroesse_deutsch(beispiel) -> None:
    _modul, formular = beispiel("05_Bildergalerie")

    formular.lb_bilder._qwidget.setCurrentRow(0)
    kopf = formular.l_info.caption.splitlines()[0]

    assert "," in kopf and "kB" in kopf


def test_die_galerie_ueberlebt_das_leerraeumen(beispiel) -> None:
    _modul, formular = beispiel("05_Bildergalerie")

    while formular.bilder:
        formular.lb_bilder._qwidget.setCurrentRow(0)
        formular.b_entfernen_click(formular)

    assert formular.l_info.caption == "Die Galerie ist leer."
    assert formular.i_vorschau.picture.pfad is None

    formular.b_entfernen_click(formular)  # darf nicht abstürzen


# -- Stufe 4: der Cookie-Klicker ----------------------------------------


def test_der_klicker_zaehlt_und_baut_aus(beispiel) -> None:
    modul, formular = beispiel("04_CookieKlicker")

    formular.kekse = 100
    formular.b_teig_click(formular)
    assert formular.kekse == 100 - modul.TEIG_PREIS
    assert formular.pro_klick == 2

    formular.kekse = 5
    formular.b_teig_click(formular)
    assert "fehlen" in formular.l_hinweis.caption

    formular.kekse = 100
    formular.b_helfer_click(formular)
    assert formular.t_helfer.enabled is True
    vorher = formular.kekse
    formular.t_helfer_timer(formular)
    assert formular.kekse == vorher + formular.helfer


@pytest.mark.parametrize(
    ("kekse", "rang"),
    [
        (0, "Anfänger"),
        (9, "Anfänger"),
        (10, "Lehrling"),
        (50, "Geselle"),
        (100, "Profi"),
        (200, "Meisterbäcker"),
        (500, "Großbäckerei"),
    ],
)
def test_der_klicker_vergibt_die_raenge_an_den_richtigen_grenzen(
    beispiel, kekse, rang
) -> None:
    _modul, formular = beispiel("04_CookieKlicker")

    formular.kekse = kekse

    assert formular.rang() == rang


def test_neu_anfangen_stellt_alles_zurueck(beispiel) -> None:
    _modul, formular = beispiel("04_CookieKlicker")

    formular.kekse = 300
    formular.pro_klick = 5
    formular.helfer = 3
    formular.t_helfer.enabled = True

    formular.b_neu_click(formular)

    assert (formular.kekse, formular.pro_klick, formular.helfer) == (0, 1, 0)
    assert formular.t_helfer.enabled is False


# -- Stufe 1: das Konsolenprogramm --------------------------------------


def test_ein_konsolenprogramm_laeuft_ueber_seine_main() -> None:
    """Gestartet wird `main.py` - genau wie F9 es tut. Der Import darin
    muss `u_main.py` auch wirklich ausführen."""
    lauf = subprocess.run(
        [sys.executable, "main.py"],
        cwd=BEISPIELE / "01_Begruessung",
        input="Anna\n17\n",
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )

    assert lauf.returncode == 0, lauf.stderr
    assert "Freut mich, Anna!" in lauf.stdout
    assert "In 10 Jahren bist du 27." in lauf.stdout
