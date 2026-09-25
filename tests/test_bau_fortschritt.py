"""Fortschrittsanzeige und Abkürzungen beim Bau der Auslieferung.

Der Bau dauert eine halbe Stunde und mehr. Die Anzeige soll zeigen,
wo er steht, ohne dass etwas davon ins Ergebnis eingreift. Die
Abkürzungen - Tests nicht doppelt, Signaturen aus dem
Zwischenspeicher - dürfen nur greifen, wo sich das Ergebnis dadurch
nicht ändern kann.
"""

from __future__ import annotations

import io
import json
import sys
import zipfile
from pathlib import Path

import pytest

from tools import auslieferung_bauen as bau
from tools import ide_paketieren as paket
from tools import paket_bauen
from tools.fortschritt import Anzeige, Bauzeiten, KonsolenMelder, _balken, ausfuehren


@pytest.fixture(autouse=True)
def _bauordner_umgelenkt(tmp_path_factory, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kein Test schreibt nach `build/bau-cache` oder `dist/`. Ein
    Teststempel dort ließe den nächsten echten Bau glauben, die Tests
    seien schon grün gewesen; eine Zeitdatei verdürbe seine Schätzung.
    Beim Schreiben dieser Tests genau so passiert."""
    ordner = tmp_path_factory.mktemp("bau")
    monkeypatch.setattr(bau, "_BAU_CACHE", ordner / "bau-cache")
    monkeypatch.setattr(bau, "_TEST_STEMPEL", ordner / "bau-cache" / "tests.json")
    monkeypatch.setattr(bau, "_PROTOKOLL", ordner / "auslieferung.log")
    monkeypatch.setattr(paket, "_SIGNATUR_ABLAGE", ordner / "signaturen")


# --------------------------------------------- Die Anzeige


def _anzeige(tmp_path: Path, *, live: bool = False) -> tuple[Anzeige, io.StringIO]:
    strom = io.StringIO()
    anzeige = Anzeige(
        11, tmp_path / "bau.log", Bauzeiten(tmp_path / "zeiten.json"), ausgabe=strom, live=live
    )
    return anzeige, strom


def test_ohne_konsole_gibt_es_zeilen_statt_balken(tmp_path: Path) -> None:
    """Ein Protokoll voller Steuerzeichen liest niemand."""
    anzeige, strom = _anzeige(tmp_path)

    anzeige.schritt(4, "pytest")
    anzeige.anteil(0.5)
    anzeige.schritt_beendet()
    anzeige.beenden()

    text = strom.getvalue()
    assert "[4/11] pytest" in text
    assert "fertig nach" in text
    assert "\x1b[" not in text


def test_jede_rohzeile_steht_im_protokoll(tmp_path: Path) -> None:
    """Auf dem Bildschirm nur der letzte Hinweis, im Protokoll alles."""
    anzeige, strom = _anzeige(tmp_path)
    anzeige.schritt(5, "dist\\Natter bauen")

    anzeige.zeile("Collecting numpy==2.5.3")
    anzeige.zeile("Collecting pandas==3.0.5")
    anzeige.beenden()

    protokoll = (tmp_path / "bau.log").read_text(encoding="utf-8")
    assert "Collecting numpy" in protokoll
    assert "Collecting pandas" in protokoll
    assert "Collecting" not in strom.getvalue()


def test_ein_fehler_nennt_schritt_und_protokoll(tmp_path: Path) -> None:
    anzeige, strom = _anzeige(tmp_path)
    anzeige.schritt(8, "Installer kompilieren")

    anzeige.fehler("Inno Setup fehlgeschlagen:\nError on line 12")
    anzeige.beenden()

    text = strom.getvalue()
    assert "Schritt 8/11" in text
    assert "Error on line 12" in text
    assert str(tmp_path / "bau.log") in text


def test_die_balken_zeichnen_sich_in_einer_konsole(tmp_path: Path) -> None:
    anzeige, strom = _anzeige(tmp_path, live=True)

    anzeige.schritt(8, "Installer kompilieren")
    anzeige.stand(15000, 30000, "Dateien")
    anzeige._zeichnen()
    anzeige.beenden()

    text = strom.getvalue()
    assert "Gesamt" in text
    assert "15000/30000 Dateien" in text
    assert "noch ~" in text


def test_ein_balken_ist_immer_gleich_breit() -> None:
    """Sonst springt die Prozentzahl dahinter hin und her."""
    for anteil in (0.0, 0.013, 0.5, 0.999, 1.0, 1.7):
        sichtbar = "".join(
            zeichen for zeichen in _balken(anteil, 30, "") if zeichen not in "\x1b[0m9"
        )
        assert len(sichtbar) == 30, anteil


def test_eine_nicht_darstellbare_marke_bricht_nichts_ab(tmp_path: Path) -> None:
    """Eine Windows-Konsole auf Codepage 1252 kennt kein „✓"."""
    strom = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    anzeige = Anzeige(
        11, tmp_path / "bau.log", Bauzeiten(tmp_path / "z.json"), ausgabe=strom, live=False
    )
    anzeige.schritt(1, "Arbeitsbaum ansehen")

    anzeige.fehler("kaputt ✗")
    anzeige.beenden()


# --------------------------------------------- Die Schätzung


def test_ohne_gemessene_zeiten_gelten_die_vorgaben(tmp_path: Path) -> None:
    zeiten = Bauzeiten(tmp_path / "gibtsnicht.json")

    assert zeiten.werte["4"] > 60


def test_eine_kaputte_zeitdatei_wird_uebergangen(tmp_path: Path) -> None:
    (tmp_path / "zeiten.json").write_text("{kein json", encoding="utf-8")

    assert Bauzeiten(tmp_path / "zeiten.json").werte["4"] > 60


def test_ein_beendeter_schritt_liefert_die_naechste_schaetzung(tmp_path: Path) -> None:
    """Gemerkt wird sofort, nicht erst am Ende - bricht der Bau in
    Schritt 8 ab, sind die ersten sieben trotzdem gemessen."""
    anzeige, _ = _anzeige(tmp_path)
    anzeige.schritt(3, "ruff check")
    anzeige.schritt_beendet()

    gelesen = json.loads((tmp_path / "zeiten.json").read_text(encoding="utf-8"))
    assert gelesen["3"] < 5


def test_ein_uebersprungener_schritt_verdirbt_die_schaetzung_nicht(tmp_path: Path) -> None:
    """Übersprungene Tests dauern null Sekunden. Als Messwert
    gespeichert, schätzte der nächste Lauf die Tests auf null."""
    anzeige, _ = _anzeige(tmp_path)
    anzeige.schritt(4, "pytest")
    anzeige.schritt_beendet(uebersprungen=True)

    assert Bauzeiten(tmp_path / "zeiten.json").werte["4"] > 60


def test_abschnitte_werden_einzeln_gemessen(tmp_path: Path) -> None:
    anzeige, _ = _anzeige(tmp_path)
    anzeige.schritt(5, "dist\\Natter bauen")
    anzeige.phasen_ankuendigen([("Pakete installieren", 240), ("Signieren", 190)])

    anzeige.phase("Pakete installieren")
    anzeige.phase("Signieren")
    anzeige.schritt_beendet()

    werte = Bauzeiten(tmp_path / "zeiten.json").werte
    assert "5:Pakete installieren" in werte
    assert "5:Signieren" in werte


# --------------------------------------------- Ausführen mit Weitergabe


class _Sammler(KonsolenMelder):
    def __init__(self) -> None:
        self.zeilen: list[str] = []

    def zeile(self, text: str) -> None:
        self.zeilen.append(text.rstrip())


def test_jede_zeile_kommt_sofort_an() -> None:
    sammler = _Sammler()
    gezaehlt: list[str] = []

    code, ausgabe = ausfuehren(
        [sys.executable, "-c", "print('eins'); print('zwei')"],
        sammler,
        zeile_auswerten=gezaehlt.append,
    )

    assert code == 0
    assert sammler.zeilen == ["eins", "zwei"]
    assert len(gezaehlt) == 2
    assert "zwei" in ausgabe


def test_fehlerausgaben_stehen_an_ihrer_stelle() -> None:
    """stderr läuft mit stdout zusammen: eine Fehlermeldung gehört
    dorthin, wo sie auftrat."""
    sammler = _Sammler()

    code, _ = ausfuehren(
        [sys.executable, "-c", "import sys; print('vorher', flush=True); sys.exit('kaputt')"],
        sammler,
    )

    assert code == 1
    assert sammler.zeilen == ["vorher", "kaputt"]


# --------------------------------------------- Schritt 4: Tests


def test_der_prozentwert_von_pytest_wird_zum_balken(monkeypatch: pytest.MonkeyPatch) -> None:
    gemeldet: list[float] = []
    melder = type("M", (), {"anteil": lambda _s, w: gemeldet.append(w)})()
    monkeypatch.setattr(bau, "_anzeige", melder)

    bau._prozent_von_pytest("........................ [ 58%]\n")
    bau._prozent_von_pytest("........................\n")

    assert gemeldet == [0.58]


def test_mit_offenen_aenderungen_gibt_es_keinen_teststand(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Liegt etwas nicht eingecheckt im Baum, ist nicht sicher, was
    die Tests sähen - dann laufen sie."""
    antworten = {"status": " M ide/main.py", "rev-parse": "abc"}
    monkeypatch.setattr(bau, "_git", lambda *a: antworten[a[0]])

    assert bau._teststand() is None


def test_ein_sauberer_baum_hat_einen_teststand(monkeypatch: pytest.MonkeyPatch) -> None:
    antworten = {"status": "", "rev-parse": "abc123"}
    monkeypatch.setattr(bau, "_git", lambda *a: antworten[a[0]])

    erster = bau._teststand()
    antworten["rev-parse"] = "def456"

    assert erster is not None
    assert bau._teststand() != erster


def test_derselbe_gruene_stand_wird_nicht_noch_einmal_getestet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gelaufen: list[bool] = []
    monkeypatch.setattr(bau, "_teststand", lambda: "stand-1")
    monkeypatch.setattr(
        bau, "_laufen_lassen", lambda *a, **k: (gelaufen.append(True), "4112 passed")[1]
    )

    bau._tests_laufen_lassen()
    bau._tests_laufen_lassen()

    assert len(gelaufen) == 1


def test_alle_tests_laesst_sie_trotzdem_laufen(monkeypatch: pytest.MonkeyPatch) -> None:
    gelaufen: list[bool] = []
    monkeypatch.setattr(bau, "_teststand", lambda: "stand-1")
    monkeypatch.setattr(
        bau, "_laufen_lassen", lambda *a, **k: (gelaufen.append(True), "4112 passed")[1]
    )

    bau._tests_laufen_lassen()
    bau._tests_laufen_lassen(immer=True)

    assert len(gelaufen) == 2


def test_ein_anderer_stand_wird_getestet(monkeypatch: pytest.MonkeyPatch) -> None:
    gelaufen: list[bool] = []
    staende = iter(["stand-1", "stand-2"])
    monkeypatch.setattr(bau, "_teststand", lambda: next(staende))
    monkeypatch.setattr(
        bau, "_laufen_lassen", lambda *a, **k: (gelaufen.append(True), "4112 passed")[1]
    )

    bau._tests_laufen_lassen()
    bau._tests_laufen_lassen()

    assert len(gelaufen) == 2


def test_ein_roter_lauf_wird_nicht_gemerkt(monkeypatch: pytest.MonkeyPatch) -> None:
    """Scheitert pytest, wirft `_laufen_lassen` - der Stempel darf
    dann nicht entstehen, sonst wäre der nächste Lauf „schon grün"."""
    monkeypatch.setattr(bau, "_teststand", lambda: "stand-1")

    def scheitern(*_a, **_k):  # noqa: ANN202
        raise bau.BauFehler("pytest fehlgeschlagen")

    monkeypatch.setattr(bau, "_laufen_lassen", scheitern)

    with pytest.raises(bau.BauFehler):
        bau._tests_laufen_lassen()

    assert not bau._TEST_STEMPEL.exists()


# --------------------------------------------- Schritt 10


def test_die_signaturpruefung_zaehlt_und_sammelt_luecken(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("a.dll", "b.pyd", "c.exe", "liesmich.txt"):
        (tmp_path / name).write_bytes(b"x")

    def ausfuehren_ersatz(_befehl, _melder, *, zeile_auswerten):  # noqa: ANN001, ANN202
        for zeile in ("OK", "LUECKE C:\\x\\b.pyd", "OK"):
            zeile_auswerten(zeile + "\n")
        return 0, ""

    gemeldet: list[tuple[int, int]] = []
    monkeypatch.setattr(bau, "ausfuehren", ausfuehren_ersatz)
    monkeypatch.setattr(
        bau,
        "_anzeige",
        type("M", (), {"stand": lambda _s, e, g, _e="": gemeldet.append((e, g))})(),
    )

    luecken = bau._luecken_in_den_signaturen(tmp_path)

    assert luecken == ["C:\\x\\b.pyd"]
    assert gemeldet[-1] == (3, 3)


# --------------------------------------------- Signaturen wiederverwenden


class _SignierErsatz:
    """Signiert, indem es eine Marke anhängt - wie eine echte Signatur
    ändert das die Bytes. Zählt, wie oft es gebraucht wurde."""

    MARKE = b"<signiert>"

    def __init__(self) -> None:
        self.signiert: list[str] = []

    def __call__(self, ordner: Path) -> None:
        for datei in paket._binaerdateien(ordner):
            inhalt = datei.read_bytes()
            if not inhalt.endswith(self.MARKE):
                datei.write_bytes(inhalt + self.MARKE)
                self.signiert.append(datei.name)


@pytest.fixture
def signieren(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _SignierErsatz:
    ersatz = _SignierErsatz()
    monkeypatch.setattr(paket, "_alles_signieren", ersatz)
    monkeypatch.setattr(paket, "_fingerabdruck_des_zertifikats", lambda: "A" * 40)
    monkeypatch.setattr(paket, "_SIGNATUR_ABLAGE", tmp_path / "ablage")
    monkeypatch.setattr(paket, "_melder", _Sammler())
    return ersatz


def _frischer_bau(ordner: Path, dateien: dict[str, bytes]) -> Path:
    if ordner.exists():
        import shutil

        shutil.rmtree(ordner)
    ordner.mkdir(parents=True)
    for name, inhalt in dateien.items():
        (ordner / name).write_bytes(inhalt)
    return ordner


def test_ein_zweiter_bau_signiert_unveraenderte_dateien_nicht_neu(
    tmp_path: Path, signieren: _SignierErsatz
) -> None:
    dateien = {"numpy.pyd": b"numpy", "pandas.pyd": b"pandas"}

    paket._signieren_mit_zwischenspeicher(_frischer_bau(tmp_path / "dist", dateien))
    assert sorted(signieren.signiert) == ["numpy.pyd", "pandas.pyd"]

    signieren.signiert.clear()
    ordner = _frischer_bau(tmp_path / "dist", dateien)
    paket._signieren_mit_zwischenspeicher(ordner)

    assert signieren.signiert == []
    assert (ordner / "numpy.pyd").read_bytes() == b"numpy" + _SignierErsatz.MARKE


def test_eine_geaenderte_datei_wird_neu_signiert(
    tmp_path: Path, signieren: _SignierErsatz
) -> None:
    """Eine neue Paketversion hat eine andere Prüfsumme - an ihr darf
    keine alte Signatur landen."""
    paket._signieren_mit_zwischenspeicher(
        _frischer_bau(tmp_path / "dist", {"numpy.pyd": b"numpy 2.5.3"})
    )
    signieren.signiert.clear()

    ordner = _frischer_bau(tmp_path / "dist", {"numpy.pyd": b"numpy 2.6.0"})
    paket._signieren_mit_zwischenspeicher(ordner)

    assert signieren.signiert == ["numpy.pyd"]
    assert (ordner / "numpy.pyd").read_bytes() == b"numpy 2.6.0" + _SignierErsatz.MARKE


def test_ein_neues_zertifikat_bekommt_eine_eigene_ablage(
    tmp_path: Path, signieren: _SignierErsatz, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Eine Signatur mit dem alten Zertifikat passt nicht zum neuen."""
    dateien = {"numpy.pyd": b"numpy"}
    paket._signieren_mit_zwischenspeicher(_frischer_bau(tmp_path / "dist", dateien))
    signieren.signiert.clear()

    monkeypatch.setattr(paket, "_fingerabdruck_des_zertifikats", lambda: "B" * 40)
    paket._signieren_mit_zwischenspeicher(_frischer_bau(tmp_path / "dist", dateien))

    assert signieren.signiert == ["numpy.pyd"]


def test_fremd_signierte_dateien_landen_nicht_in_der_ablage(
    tmp_path: Path, signieren: _SignierErsatz
) -> None:
    """Was schon signiert ankommt - Qt, Microsoft -, ändert sich beim
    Signieren nicht und braucht keinen Eintrag."""
    ordner = _frischer_bau(
        tmp_path / "dist", {"qt.dll": b"qt" + _SignierErsatz.MARKE, "numpy.pyd": b"numpy"}
    )

    paket._signieren_mit_zwischenspeicher(ordner)

    assert len(list((tmp_path / "ablage" / ("A" * 40)).glob("*.bin"))) == 1


def test_veraltete_eintraege_werden_aufgeraeumt(
    tmp_path: Path, signieren: _SignierErsatz
) -> None:
    """Sonst wüchse die Ablage mit jedem Update um die nächsten paar
    hundert Megabyte."""
    paket._signieren_mit_zwischenspeicher(
        _frischer_bau(tmp_path / "dist", {"numpy.pyd": b"numpy alt"})
    )
    paket._signieren_mit_zwischenspeicher(
        _frischer_bau(tmp_path / "dist", {"numpy.pyd": b"numpy neu"})
    )

    assert len(list((tmp_path / "ablage" / ("A" * 40)).glob("*.bin"))) == 1


def test_ohne_zertifikat_wird_nur_signiert(
    tmp_path: Path, signieren: _SignierErsatz, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(paket, "_fingerabdruck_des_zertifikats", lambda: None)

    paket._signieren_mit_zwischenspeicher(
        _frischer_bau(tmp_path / "dist", {"numpy.pyd": b"numpy"})
    )

    assert signieren.signiert == ["numpy.pyd"]
    assert not (tmp_path / "ablage").exists()


def test_signierte_endungen_stehen_nur_einmal() -> None:
    assert bau._SIGNIERTE_ENDUNGEN is paket.SIGNIERTE_ENDUNGEN


# --------------------------------------------- Schritt 11


def test_die_setup_datei_wird_im_zip_nur_abgelegt(tmp_path: Path) -> None:
    """Sie ist schon mit LZMA gepackt; Deflate kostete nur Zeit."""
    ordner = tmp_path / "paket"
    ordner.mkdir()
    (ordner / "Natter-Setup.exe").write_bytes(b"MZ" * 1000)
    (ordner / "ZUERST-LESEN.txt").write_text("Text " * 200, encoding="utf-8")

    archiv = paket_bauen.zip_bauen("0.3.2", ordner=ordner)

    with zipfile.ZipFile(archiv) as offen:
        assert offen.getinfo("Natter-Setup.exe").compress_type == zipfile.ZIP_STORED
        assert offen.getinfo("ZUERST-LESEN.txt").compress_type == zipfile.ZIP_DEFLATED


def test_das_zip_meldet_seinen_fortschritt(tmp_path: Path) -> None:
    ordner = tmp_path / "paket"
    ordner.mkdir()
    (ordner / "a.txt").write_bytes(b"a" * 300)
    (ordner / "b.txt").write_bytes(b"b" * 700)
    gemeldet: list[tuple[int, int]] = []

    paket_bauen.zip_bauen(
        "0.3.2", ordner=ordner, fortschritt=lambda f, g: gemeldet.append((f, g))
    )

    assert gemeldet == [(300, 1000), (1000, 1000)]
