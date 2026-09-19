"""Fehler, die bis M12 gar keine deutsche Meldung bekamen.

`fehlermeldung_erzeugen()` liefert `None`, wenn kein Katalogeintrag zum
Ausnahmetyp passt – und dann zeigt das Schülerprogramm den englischen
Traceback. Bei der Durchsicht „Was sieht eine Lernende?“ fielen sechs
Fälle auf, die im Unterricht wirklich vorkommen und genau dort landeten:

* `ModuleNotFoundError` – die Unit heißt `u_Ampel.py`, im Import steht
  `u_ampel`. Unter Windows fällt das beim Dateinamen nicht auf, beim
  Import schon. Oder das Paket ist gar nicht installiert.
* `RecursionError` – Rekursion steht auf dem Lehrplan, und der erste
  Versuch endet fast immer hier.
* `AssertionError` – aus einem `assert` im eigenen Code und aus jeder
  fehlgeschlagenen Prüfung in einer Test-Unit.
* `FileExistsError` und die übrigen `OSError` ohne eigenen Eintrag.
* `OverflowError` neben der Division durch 0.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.debugger.fehlerkatalog import fehlermeldung_erzeugen


def _meldung(fehler: BaseException):
    meldung = fehlermeldung_erzeugen(fehler)
    assert meldung is not None, (
        f"{type(fehler).__name__} hat keinen Katalogeintrag – die Schülerin "
        f"sähe hier den englischen Traceback."
    )
    return meldung


def _ausgeloest(aufruf) -> BaseException:
    try:
        aufruf()
    except BaseException as fehler:  # noqa: BLE001 - genau darum geht es
        return fehler
    raise AssertionError("Der Aufruf hat gar keinen Fehler ausgelöst.")


def test_eine_fehlende_unit_nennt_ihren_namen() -> None:
    meldung = _meldung(_ausgeloest(lambda: __import__("u_gibtsnicht")))

    assert "u_gibtsnicht" in meldung.was
    assert "Unit oder Paket" in meldung.ueberschrift


def test_der_name_bleibt_klein_geschrieben() -> None:
    """Aus `u_ampel` darf nicht `U_ampel` werden – es geht in dieser
    Meldung gerade um Groß- und Kleinschreibung."""
    meldung = _meldung(_ausgeloest(lambda: __import__("u_ampel_gibtsnicht")))

    assert "u_ampel_gibtsnicht" in meldung.was
    assert "U_ampel_gibtsnicht" not in meldung.was


def test_die_leitfrage_nennt_beide_faelle() -> None:
    meldung = _meldung(_ausgeloest(lambda: __import__("u_gibtsnicht")))

    assert "Kleinschreibung" in meldung.pruefe  # eigene Unit falsch geschrieben
    assert "Paket installieren" in meldung.pruefe  # Paket fehlt


def test_endlose_rekursion_wird_erklaert() -> None:
    def tief(n: int = 0) -> int:
        return tief(n + 1)

    meldung = _meldung(_ausgeloest(tief))

    assert "Rekursion" in meldung.ueberschrift
    assert "beendet" in meldung.was
    assert "Abbruch" in meldung.pruefe


def test_eine_fehlgeschlagene_behauptung_zitiert_ihren_text() -> None:
    def behaupten() -> None:
        assert 1 == 2, "zwei ist nicht eins"

    meldung = _meldung(_ausgeloest(behaupten))

    assert "Behauptung" in meldung.ueberschrift
    assert "zwei ist nicht eins" in meldung.was


def test_eine_behauptung_ohne_text_kommt_auch_durch() -> None:
    def behaupten() -> None:
        assert 1 == 2

    meldung = _meldung(_ausgeloest(behaupten))

    assert "assert" in meldung.was


def test_ein_uebriger_dateifehler_bekommt_den_rueckfall(tmp_path: Path) -> None:
    datei = tmp_path / "da.txt"
    datei.write_text("x", encoding="utf-8")

    meldung = _meldung(_ausgeloest(lambda: datei.open("x")))

    assert "Dateizugriff" in meldung.ueberschrift
    assert "da.txt" in meldung.was


def test_ein_ueberlauf_bekommt_den_rechen_rueckfall() -> None:
    meldung = _meldung(_ausgeloest(lambda: 2.0**100000))

    assert "Rechnung" in meldung.ueberschrift
    assert "Zahlen" in meldung.pruefe


@pytest.mark.parametrize(
    ("aufruf", "erwartete_ueberschrift"),
    [
        (lambda: 1 / 0, "Division durch 0"),
        (lambda: open("gibtsnicht_12345.txt"), "Datei nicht gefunden"),
    ],
    ids=["division", "datei_fehlt"],
)
def test_die_genaueren_eintraege_gehen_weiterhin_vor(
    aufruf, erwartete_ueberschrift: str
) -> None:
    """`OSError` und `ArithmeticError` sind Rückfälle. Sie dürfen die
    genaueren Einträge ihrer Unterklassen nicht verdecken."""
    meldung = _meldung(_ausgeloest(aufruf))

    assert erwartete_ueberschrift in meldung.ueberschrift


def test_dateinamen_stehen_in_deutschen_anfuehrungszeichen() -> None:
    """Python zitiert mit `'…'`; in einer deutschen Meldung steht „…“.
    Beides gemischt sah aus wie ein Versehen."""
    meldung = _meldung(_ausgeloest(lambda: open("gibtsnicht_12345.txt")))

    assert "„gibtsnicht_12345.txt“" in meldung.was
    assert "'gibtsnicht_12345.txt'" not in meldung.was


def test_gemischte_tabs_und_leerzeichen_zeigen_auf_die_passende_ansicht() -> None:
    """Der einzige Fehler, den man im Editor nicht sehen kann - Natter
    hat seit M11 eine Ansicht dafür, die Meldung nennt sie jetzt."""
    quelle = "def f():" + chr(10) + chr(9) + "x = 1" + chr(10) + "        y = 2" + chr(10)

    fehler = _ausgeloest(lambda: compile(quelle, "u_test.py", "exec"))
    meldung = _meldung(fehler)

    assert type(fehler).__name__ == "TabError"
    assert "Tabulatoren" in meldung.was
    assert "Leerzeichen anzeigen" in meldung.pruefe
