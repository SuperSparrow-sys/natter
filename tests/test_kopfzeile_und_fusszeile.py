"""Die Kopfzeile bietet nur an, was geht - die Fußzeile warnt.

Punkte 18 und 19 der offenen Punkte.

Ohne offenes Projekt und ohne laufendes Programm waren alle acht
Einträge unter „Start" anklickbar, und fünf davon taten beim
Anklicken nachweislich nichts: kein Hinweis, keine Statuszeile, kein
`else`. Der Knopf sah aus, als wäre er kaputt.

Und der Prüfungsmodus stand in der Fußzeile nur fett in der
gewöhnlichen Textfarbe. Er ändert, was Natter zulässt - wer nicht
sieht, dass er läuft, sucht den Fehler bei sich.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ide.shell.hauptfenster import HauptFenster

#: Was ohne angehaltenes Programm nichts tun kann.
NUR_BEIM_DEBUGGEN = (
    "start.pause",
    "start.fortsetzen",
    "start.einzelschritt",
    "start.prozedurschritt",
    "start.ruecksprung",
)

#: Was auch ohne laufendes Programm etwas zu sagen hat und deshalb
#: anklickbar bleibt.
SAGT_WAS_ZU_TUN_IST = ("start.mit_debugger", "start.ohne_debugger", "start.stopp")


class _Sitzung:
    """Eine angehaltene Debug-Sitzung, so weit die Kopfzeile sie
    kennt. Ein blankes `object()` genügt nicht: beim Aufräumen des
    Fensters wird `beenden()` gerufen."""

    def beenden(self) -> None:
        pass


@pytest.fixture
def fenster(qtbot) -> HauptFenster:
    f = HauptFenster()
    qtbot.addWidget(f)
    return f


# ------------------------------------------- Punkt 18: die Kopfzeile


@pytest.mark.parametrize("kennung", NUR_BEIM_DEBUGGEN)
def test_ohne_debugger_ist_der_eintrag_ausgegraut(
    fenster: HauptFenster, kennung: str
) -> None:
    assert fenster.debug_sitzung is None
    assert fenster.aktionen[kennung].qaction.isEnabled() is False


@pytest.mark.parametrize("kennung", SAGT_WAS_ZU_TUN_IST)
def test_was_etwas_zu_sagen_hat_bleibt_anklickbar(
    fenster: HauptFenster, kennung: str
) -> None:
    """Ausgegraut ist eine Auskunft, aber ein Satz ist eine bessere.
    „Kein Projekt offen. Zuerst über „Projekt → Öffnen …" eines
    laden" hilft weiter als ein graues Symbol."""
    aktion = fenster.aktionen[kennung]
    assert aktion.qaction.isEnabled() is True

    aktion.qaction.trigger()

    assert fenster.statusBar().currentMessage(), (
        f"{kennung} tut nichts und sagt auch nichts."
    )


def test_am_haltepunkt_sind_die_schritte_moeglich(fenster: HauptFenster) -> None:
    """Der Gegenbeweis: ausgegraut bleibt nicht ausgegraut."""
    fenster.debug_sitzung = _Sitzung()
    fenster._aktueller_thread_id = 1

    fenster._startaktionen_pruefen()

    for kennung in NUR_BEIM_DEBUGGEN:
        assert fenster.aktionen[kennung].qaction.isEnabled() is True, kennung


def test_nach_dem_stoppen_sind_sie_wieder_grau(fenster: HauptFenster) -> None:
    fenster.debug_sitzung = _Sitzung()
    fenster._aktueller_thread_id = 1
    fenster._startaktionen_pruefen()

    fenster.debug_sitzung = None
    fenster._aktueller_thread_id = None
    fenster._startaktionen_pruefen()

    for kennung in NUR_BEIM_DEBUGGEN:
        assert fenster.aktionen[kennung].qaction.isEnabled() is False, kennung


def test_das_menue_fuehrt_sich_beim_aufklappen_nach(fenster: HauptFenster) -> None:
    """Der Rückfallschutz: ein vergessener Aufruf an einer der fünf
    Zustandsstellen wäre sonst nicht zu bemerken."""
    fenster.debug_sitzung = _Sitzung()
    fenster._aktueller_thread_id = 1

    fenster.menue("Start").aboutToShow.emit()

    assert fenster.aktionen["start.einzelschritt"].qaction.isEnabled() is True


def test_in_der_werkzeugleiste_steht_stopp_statt_einzelschritt(
    fenster: HauptFenster,
) -> None:
    """Gebraucht wird beim Unterrichten der Stopp-Knopf. Der
    Einzelschritt liegt auf F11 und ist nur während einer
    Debug-Sitzung sinnvoll."""
    in_der_leiste = {
        aktion.id
        for aktion in fenster.aktionen
        if aktion.qaction in fenster.werkzeugleiste.actions()
    }

    assert "start.stopp" in in_der_leiste


def test_jeder_knopf_der_werkzeugleiste_hat_ein_symbol(fenster: HauptFenster) -> None:
    ohne = [
        a.text()
        for a in fenster.werkzeugleiste.actions()
        if not a.isSeparator() and a.icon().isNull()
    ]
    assert not ohne, f"Knöpfe ohne Symbol: {ohne}"


def test_das_symbol_fuer_den_einzelschritt_ist_kein_pfeil_auf_eine_linie() -> None:
    """Der Anlass: der blaue Pfeil nach unten auf einen Balken wurde
    als Knopf zum Herunterladen gelesen. Geprüft wird die Zeichnung,
    weil das Aussehen sonst nur auf einem Bildschirmfoto auffällt."""
    quelle = (
        Path(__file__).resolve().parent.parent
        / "ide"
        / "assets"
        / "icons"
        / "einzelschritt.svg"
    ).read_text(encoding="utf-8")

    assert "Herunterladen" in quelle, "Die Begründung fehlt im Symbol."
    # Der alte Entwurf: ein liegender Balken unten quer über das Bild.
    assert 'y="17.8"' not in quelle


# ------------------------- Punkt 18: dieselbe Regel unter „Bearbeiten"

BEARBEITEN = (
    "bearbeiten.rueckgaengig",
    "bearbeiten.wiederholen",
    "bearbeiten.ausschneiden",
    "bearbeiten.kopieren",
    "bearbeiten.einfuegen",
    "bearbeiten.alles_auswaehlen",
)


@pytest.mark.parametrize("kennung", BEARBEITEN)
def test_ohne_offenen_reiter_ist_bearbeiten_ausgegraut(
    fenster: HauptFenster, kennung: str
) -> None:
    assert fenster.aktionen[kennung].qaction.isEnabled() is False


def test_mit_offenem_editor_geht_bearbeiten_wieder(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Der Gegenbeweis - sonst hätte die Sperre alles lahmgelegt."""
    datei = tmp_path / "u_probe.py"
    datei.write_text("x = 1\n", encoding="utf-8")

    fenster.oeffnen(datei)

    for kennung in BEARBEITEN:
        assert fenster.aktionen[kennung].qaction.isEnabled() is True, kennung


def test_im_designer_geht_wenigstens_rueckgaengig(
    fenster: HauptFenster, tmp_path: Path
) -> None:
    """Der Designer hat einen eigenen Kommandostapel. Ausschneiden
    und Einfügen brauchen dort einen Texteditor und bleiben grau."""
    import shutil

    quelle = Path(__file__).resolve().parent.parent / "beispielprojekte" / "03_Taschenrechner"
    ziel = tmp_path / "03_Taschenrechner"
    shutil.copytree(quelle, ziel)
    fenster.projekt_oeffnen(ziel / "03_Taschenrechner.natter")

    fenster.designer_oeffnen(ziel / "u_main.pfm")

    assert fenster.aktionen["bearbeiten.rueckgaengig"].qaction.isEnabled() is True


# ------------------------------------------- Punkt 19: die Fußzeile


def test_die_pruefungsanzeige_ist_rot_hinterlegt(fenster: HauptFenster) -> None:
    stil = fenster.pruefungsanzeige.styleSheet()

    assert "background-color: #c42b1c" in stil
    assert "color: #ffffff" in stil


def test_sie_traegt_einen_selektor(fenster: HauptFenster) -> None:
    """Ohne Selektor gälte die Anweisung auch für jedes Kind und für
    jeden Dialog, der an diesem Label hinge (siehe
    `test_stylesheet_kaskade.py`)."""
    assert fenster.pruefungsanzeige.styleSheet().startswith("QLabel {")


def test_ohne_pruefung_steht_dort_nichts(fenster: HauptFenster) -> None:
    fenster._statusleiste_pruefung_aktualisieren()

    assert fenster.pruefungsanzeige.text() == ""
    assert fenster.pruefungsanzeige.isVisible() is False


def test_mit_pruefung_steht_das_wort_daneben(
    fenster: HauptFenster, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Auf die Farbe allein ist in einer Klasse kein Verlass."""
    import ide.shell.hauptfenster as modul

    monkeypatch.setattr(modul, "restzeit_text", lambda: "Prüfungsmodus – noch 2:45 h")
    fenster.show()

    fenster._statusleiste_pruefung_aktualisieren()

    assert "Prüfungsmodus" in fenster.pruefungsanzeige.text()
    assert fenster.pruefungsanzeige.isVisible() is True
