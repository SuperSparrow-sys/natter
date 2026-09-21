"""Das Paket für die Schule ist vollständig.

Die Fassung 0.3.0 wurde von Hand gepackt, und zwei der neun Dateien
fehlten: das Skript zum Prüfen und das zum Zurücknehmen des
Zertifikats. Aufgefallen ist es erst, als jemand danach suchte - einem
ZIP sieht man nicht an, was nicht darin ist. Deshalb steht die Liste
jetzt an einer Stelle im Quelltext, und diese Tests halten sie mit der
Beschreibung in `tools/paket/README.md` zusammen.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from tools import paket_bauen

WURZEL = Path(__file__).resolve().parent.parent


# --------------------------------------------- Die Liste stimmt


def test_die_liste_und_die_beschreibung_nennen_dieselben_dateien() -> None:
    """Zwei Listen, die auseinanderlaufen können, sind schlimmer als
    eine: die Beschreibung liest jemand, der das Paket weitergibt."""
    beschreibung = (WURZEL / "tools" / "paket" / "README.md").read_text(
        encoding="utf-8"
    )

    genannt = {
        zeile.split("|")[1].strip().strip("`")
        for zeile in beschreibung.splitlines()
        if zeile.startswith("| `")
    }
    aufgelistet = {name for name, _ in paket_bauen._INHALT}
    aufgelistet |= {"Handbuch.md", "Handbuch.html", "Lizenzen\\"}

    assert genannt == aufgelistet


def test_die_skripte_gehoeren_alle_ins_paket() -> None:
    """Eintragen allein genügt nicht: wer Vertrauen vergibt, muss es
    zurücknehmen können, und wer einen Fehler sucht, braucht etwas zum
    Nachsehen."""
    namen = {name for name, _ in paket_bauen._INHALT}

    assert "Zertifikat-eintragen.ps1" in namen
    assert "Zertifikat-entfernen.ps1" in namen
    assert "Natter-pruefen.ps1" in namen


def test_der_private_schluessel_ist_nicht_dabei() -> None:
    """Ins Paket gehört der öffentliche Teil. Wer die `.pfx` hätte,
    könnte im Namen von Natter signieren, auf jedem Rechner, der das
    Zertifikat eingetragen hat."""
    for name, quelle in paket_bauen._INHALT:
        assert not name.endswith(".pfx")
        assert quelle.suffix != ".pfx"


# --------------------------------------------- Das Handbuch


def test_ueberschriften_und_absaetze() -> None:
    html = paket_bauen.handbuch_als_html("# Titel\n\nEin Satz.\n", "T")

    assert "<h1>Titel</h1>" in html
    assert "<p>Ein Satz.</p>" in html


def test_tabellen_bekommen_eine_kopfzeile() -> None:
    quelle = "| Datei | Woher |\n|---|---|\n| `a.txt` | hier |\n"

    html = paket_bauen.handbuch_als_html(quelle, "T")

    assert "<th>Datei</th><th>Woher</th>" in html
    assert "<td><code>a.txt</code></td><td>hier</td>" in html
    assert "---" not in html


def test_codebloecke_bleiben_unveraendert() -> None:
    quelle = "```\nuv run python main.py\n```\n"

    html = paket_bauen.handbuch_als_html(quelle, "T")

    assert "<pre>uv run python main.py</pre>" in html


def test_spitze_klammern_werden_entschaerft() -> None:
    """Sonst verschwindet ein Pfad wie `<Benutzer>` beim Anzeigen."""
    html = paket_bauen.handbuch_als_html("Pfad: C:\\<Benutzer>\\Natter\n", "T")

    assert "&lt;Benutzer&gt;" in html


def test_das_handbuch_laesst_sich_umsetzen() -> None:
    """Gegen die echte Datei und nicht nur gegen Schnipsel: sie ist
    das, was im Paket landet."""
    markdown = (WURZEL / "docs" / "fuer_lehrkraefte.md").read_text(encoding="utf-8")

    html = paket_bauen.handbuch_als_html(markdown, "Natter für Lehrkräfte")

    assert html.startswith("<!DOCTYPE html>")
    assert html.rstrip().endswith("</html>")
    assert "<table>" in html
    assert "<pre>" in html
    # Nichts von der Auszeichnung darf ungewandelt durchrutschen.
    assert "\n| " not in html
    assert "\n## " not in html


# --------------------------------------------- Das ZIP


def test_das_zip_traegt_die_versionsnummer(tmp_path: Path) -> None:
    """Auf einem Stick liegen sonst zwei Fassungen nebeneinander,
    denen man nicht ansieht, welche die neuere ist."""
    ordner = tmp_path / "paket"
    ordner.mkdir()
    (ordner / "ZUERST-LESEN.txt").write_text("egal", encoding="utf-8")

    archiv = paket_bauen.zip_bauen("0.3.1", ordner=ordner)

    assert archiv.name == "Natter-0.3.1-fuer-Lehrkraefte.zip"


def test_das_zip_enthaelt_die_unterordner(tmp_path: Path) -> None:
    ordner = tmp_path / "paket"
    (ordner / "Lizenzen").mkdir(parents=True)
    (ordner / "ZUERST-LESEN.txt").write_text("egal", encoding="utf-8")
    (ordner / "Lizenzen" / "numpy.txt").write_text("egal", encoding="utf-8")

    archiv = paket_bauen.zip_bauen("0.3.1", ordner=ordner)

    with zipfile.ZipFile(archiv) as offen:
        namen = set(offen.namelist())

    assert "ZUERST-LESEN.txt" in namen
    assert "Lizenzen/numpy.txt" in namen


def test_ein_zweiter_lauf_ersetzt_das_alte_zip(tmp_path: Path) -> None:
    """Sonst bliebe ein ZIP mit dem Stand von vorhin liegen und trüge
    trotzdem die neue Nummer im Namen."""
    ordner = tmp_path / "paket"
    ordner.mkdir()
    (ordner / "ZUERST-LESEN.txt").write_text("alt", encoding="utf-8")
    paket_bauen.zip_bauen("0.3.1", ordner=ordner)

    (ordner / "ZUERST-LESEN.txt").write_text("neu", encoding="utf-8")
    archiv = paket_bauen.zip_bauen("0.3.1", ordner=ordner)

    with zipfile.ZipFile(archiv) as offen:
        assert offen.read("ZUERST-LESEN.txt") == b"neu"


def test_fehlende_dateien_brechen_den_bau_ab(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Lieber kein Paket als eines, dem etwas fehlt - genau das ist
    bei 0.3.0 passiert."""
    monkeypatch.setattr(
        paket_bauen,
        "_INHALT",
        (("Fehlt.txt", tmp_path / "gibtsnicht.txt"),),
    )

    with pytest.raises(paket_bauen.PaketFehler) as fehler:
        paket_bauen.paket_bauen(ziel=tmp_path / "raus")

    assert "gibtsnicht.txt" in str(fehler.value)
